"""Admin endpoints for reviewing held transfers."""

import uuid
from fastapi import APIRouter, HTTPException

from app.core.deps import DB

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/transfers/pending")
async def list_pending_transfers(db: DB):
    """List all transfers pending review."""
    rows = await db.fetch(
        """
        SELECT t.id, t.amount, t.note, t.fraud_score, t.created_at,
               u_from.handle as from_handle, u_from.full_name as from_name,
               u_to.handle as to_handle, u_to.full_name as to_name
        FROM transfers t
        JOIN accounts a_from ON a_from.id = t.from_account
        JOIN accounts a_to ON a_to.id = t.to_account
        JOIN users u_from ON u_from.id = a_from.user_id
        JOIN users u_to ON u_to.id = a_to.user_id
        WHERE t.status = 'pending_review'
        ORDER BY t.created_at DESC
        """
    )
    return [dict(r) for r in rows]


@router.post("/transfers/{transfer_id}/approve")
async def approve_transfer(transfer_id: uuid.UUID, db: DB):
    """Approve a held transfer and execute it."""
    async with db.acquire() as conn:
        async with conn.transaction():
            # Get the pending transfer
            transfer = await conn.fetchrow(
                "SELECT * FROM transfers WHERE id = $1 AND status = 'pending_review'",
                transfer_id,
            )
            if not transfer:
                raise HTTPException(404, "Transfer not found or not pending")
            
            # Check if funds are still available
            from_balance = await conn.fetchval(
                "SELECT balance FROM accounts WHERE id = $1",
                transfer["from_account"],
            )
            if from_balance < transfer["amount"]:
                # Reject if insufficient funds
                await conn.execute(
                    "UPDATE transfers SET status = 'rejected' WHERE id = $1",
                    transfer_id,
                )
                raise HTTPException(422, "Insufficient funds - transfer rejected")
            
            # Lock both accounts to prevent race conditions
            first, second = sorted([transfer["from_account"], transfer["to_account"]])
            await conn.fetch(
                """
                SELECT id, balance FROM accounts
                WHERE id = ANY($1::uuid[])
                ORDER BY id
                FOR UPDATE
                """,
                [first, second],
            )
            
            # Double-check balance with lock held
            from_balance_locked = await conn.fetchval(
                "SELECT balance FROM accounts WHERE id = $1",
                transfer["from_account"],
            )
            if from_balance_locked < transfer["amount"]:
                await conn.execute(
                    "UPDATE transfers SET status = 'rejected' WHERE id = $1",
                    transfer_id,
                )
                raise HTTPException(422, "Insufficient funds - transfer rejected")
            
            # Create ledger entries
            await conn.execute(
                """
                INSERT INTO ledger_entries (transfer_id, account_id, amount)
                VALUES ($1, $2, $3), ($1, $4, $5)
                """,
                transfer_id,
                transfer["from_account"],
                -transfer["amount"],
                transfer["to_account"],
                transfer["amount"],
            )
            
            # Update balances
            await conn.execute(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1",
                transfer["from_account"],
                transfer["amount"],
            )
            await conn.execute(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1",
                transfer["to_account"],
                transfer["amount"],
            )
            
            # Update transfer status
            await conn.execute(
                "UPDATE transfers SET status = 'completed' WHERE id = $1",
                transfer_id,
            )
            
            return {"status": "approved", "transfer_id": transfer_id}


@router.post("/transfers/{transfer_id}/reject")
async def reject_transfer(transfer_id: uuid.UUID, db: DB, reason: str | None = None):
    """Reject a held transfer."""
    async with db.acquire() as conn:
        transfer = await conn.fetchrow(
            "SELECT * FROM transfers WHERE id = $1 AND status = 'pending_review'",
            transfer_id,
        )
        if not transfer:
            raise HTTPException(404, "Transfer not found or not pending")
        
        await conn.execute(
            "UPDATE transfers SET status = 'rejected' WHERE id = $1",
            transfer_id,
        )
        
        return {"status": "rejected", "transfer_id": transfer_id, "reason": reason}
