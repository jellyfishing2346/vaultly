"""Transfers: the money-moving endpoint.

Idempotency follows the Stripe convention: the client supplies an
Idempotency-Key header; retrying with the same key returns the original
result instead of charging twice. The uniqueness is enforced at the
database layer (see services/ledger.py), so this survives concurrent
retries, not just sequential ones.
"""

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.core.deps import DB, CurrentUser, Redis
from app.models.schemas import ActivityItem, TransferRequest, TransferResponse
from app.services.fraud import FraudEngine
from app.services.ledger import InsufficientFunds, execute_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])


async def check_rate_limit(redis, user_id) -> None:
    """Fixed-window rate limit: N transfers per minute per user."""
    key = f"ratelimit:transfers:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.RATE_LIMIT_TRANSFERS_PER_MINUTE:
        raise HTTPException(429, "Too many transfers; slow down and retry shortly")


@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(
    body: TransferRequest,
    db: DB,
    redis: Redis,
    user_id: CurrentUser,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=100),
):
    await check_rate_limit(redis, user_id)

    async with db.acquire() as conn:
        from_account = await conn.fetchval(
            "SELECT id FROM accounts WHERE user_id = $1 AND type = 'wallet'", user_id
        )
        recipient = await conn.fetchrow(
            """SELECT a.id, u.id as user_id FROM accounts a
               JOIN users u ON u.id = a.user_id
               WHERE u.handle = $1 AND a.type = 'wallet'""",
            body.to_handle,
        )
    if recipient is None:
        raise HTTPException(404, f"No user with handle @{body.to_handle}")
    if recipient["id"] == from_account:
        raise HTTPException(400, "You can't send money to yourself")

    # Fraud scoring
    fraud_engine = FraudEngine(db)
    fraud_score = await fraud_engine.score_transfer(
        from_user_id=user_id,
        to_user_id=recipient["user_id"],
        amount_cents=body.amount,
        note=body.note,
    )
    
    # If high fraud score, hold for review
    if fraud_score.should_hold:
        # Create a pending transfer instead of executing immediately
        async with db.acquire() as conn:
            transfer_id = await conn.fetchval(
                """
                INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note, status, fraud_score)
                VALUES ($1, $2, $3, $4, $5, 'pending_review', $6)
                RETURNING id
                """,
                f"{user_id}:{idempotency_key}",
                from_account,
                recipient["id"],
                body.amount,
                body.note,
                fraud_score.score,
            )
        
        return TransferResponse(
            id=transfer_id,
            status="pending_review",
            amount=body.amount,
            note=body.note,
            replayed=False,
        )

    try:
        result = await execute_transfer(
            db,
            idempotency_key=f"{user_id}:{idempotency_key}",  # scope keys per user
            from_account=from_account,
            to_account=recipient["id"],
            amount_cents=body.amount,
            note=body.note,
        )
    except InsufficientFunds:
        raise HTTPException(422, "Insufficient balance")

    return TransferResponse(
        id=result.transfer_id,
        status=result.status,
        amount=body.amount,
        note=body.note,
        replayed=result.replayed,
    )


@router.get("/activity", response_model=list[ActivityItem])
async def activity_feed(db: DB, user_id: CurrentUser, limit: int = 25):
    limit = min(max(limit, 1), 100)
    rows = await db.fetch(
        """
        SELECT t.id, t.amount, t.note, t.status, t.created_at,
               CASE WHEN fa.user_id = $1 THEN 'sent' ELSE 'received' END AS direction,
               cu.handle AS counterparty_handle,
               cu.full_name AS counterparty_name
        FROM transfers t
        JOIN accounts fa ON fa.id = t.from_account
        JOIN accounts ta ON ta.id = t.to_account
        JOIN users cu ON cu.id = CASE WHEN fa.user_id = $1 THEN ta.user_id ELSE fa.user_id END
        WHERE (fa.user_id = $1 OR ta.user_id = $1)
          AND fa.type <> 'system' AND ta.type <> 'system'
        ORDER BY t.created_at DESC
        LIMIT $2
        """,
        user_id, limit,
    )
    return [ActivityItem(**dict(r)) for r in rows]
