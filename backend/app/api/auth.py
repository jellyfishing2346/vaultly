"""Auth: signup and login."""

import asyncpg
from fastapi import APIRouter, HTTPException

from app.core.deps import DB
from app.core.security import create_access_token, hash_password, verify_password
from app.models.schemas import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

SIGNUP_BONUS_CENTS = 10_000  # $100 demo money so new users can play immediately


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, db: DB):
    async with db.acquire() as conn:
        async with conn.transaction():
            try:
                user_id = await conn.fetchval(
                    """INSERT INTO users (email, handle, full_name, password_hash)
                       VALUES ($1, $2, $3, $4) RETURNING id""",
                    body.email.lower(), body.handle, body.full_name,
                    hash_password(body.password),
                )
            except asyncpg.UniqueViolationError as e:
                field = "handle" if "handle" in str(e) else "email"
                raise HTTPException(409, f"That {field} is already taken")

            account_id = await conn.fetchval(
                "INSERT INTO accounts (user_id, balance) VALUES ($1, $2) RETURNING id",
                user_id, SIGNUP_BONUS_CENTS,
            )
            # Seed the bonus through the ledger so the books stay balanced.
            await conn.execute(
                """
                WITH sys AS (SELECT id FROM accounts WHERE type = 'system' LIMIT 1),
                t AS (
                    INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note)
                    SELECT 'signup-bonus-' || $1::text, sys.id, $1::uuid, $2, 'Welcome bonus'
                    FROM sys RETURNING id, from_account, to_account, amount
                )
                INSERT INTO ledger_entries (transfer_id, account_id, amount)
                SELECT id, from_account, -amount FROM t
                UNION ALL
                SELECT id, to_account, amount FROM t
                """,
                str(account_id), SIGNUP_BONUS_CENTS,
            )
            await conn.execute(
                "UPDATE accounts SET balance = balance - $1 WHERE type = 'system'",
                SIGNUP_BONUS_CENTS,
            )

    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DB):
    row = await db.fetchrow(
        "SELECT id, password_hash FROM users WHERE email = $1", body.email.lower()
    )
    # Verify even when the user doesn't exist to keep timing uniform.
    ok = verify_password(body.password, row["password_hash"] if row else "$2b$12$" + "x" * 53)
    if not row or not ok:
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(row["id"]))
