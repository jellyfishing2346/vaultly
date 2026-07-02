"""
Transfer engine: the only code path that moves money.

Concurrency strategy:
  - Lock both account rows with SELECT ... FOR UPDATE, always in a
    deterministic order (sorted by account id) to prevent deadlocks when
    A->B and B->A transfers race each other.
  - Insert the transfer row first; the UNIQUE constraint on idempotency_key
    makes retried requests fail fast, and we return the original transfer.
  - Write both ledger entries and update cached balances in the SAME
    transaction. Either everything commits or nothing does.
"""

import uuid

import asyncpg


class InsufficientFunds(Exception):
    pass


class TransferResult:
    def __init__(self, transfer_id: uuid.UUID, status: str, replayed: bool = False):
        self.transfer_id = transfer_id
        self.status = status
        self.replayed = replayed  # True if this idempotency key was already processed


async def execute_transfer(
    pool: asyncpg.Pool,
    *,
    idempotency_key: str,
    from_account: uuid.UUID,
    to_account: uuid.UUID,
    amount_cents: int,
    note: str | None = None,
) -> TransferResult:
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    if from_account == to_account:
        raise ValueError("cannot transfer to self")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Idempotency check: if this key exists, return the original result.
            existing = await conn.fetchrow(
                "SELECT id, status FROM transfers WHERE idempotency_key = $1",
                idempotency_key,
            )
            if existing:
                return TransferResult(existing["id"], existing["status"], replayed=True)

            # 2. Lock both accounts in deterministic order to avoid deadlock.
            first, second = sorted([from_account, to_account])
            rows = await conn.fetch(
                """
                SELECT id, balance FROM accounts
                WHERE id = ANY($1::uuid[])
                ORDER BY id
                FOR UPDATE
                """,
                [first, second],
            )
            balances = {r["id"]: r["balance"] for r in rows}
            if len(balances) != 2:
                raise ValueError("account not found")

            # 3. Check funds while holding the lock — no TOCTOU race possible.
            if balances[from_account] < amount_cents:
                raise InsufficientFunds(
                    f"balance {balances[from_account]} < {amount_cents}"
                )

            # 4. Record the transfer.
            transfer_id = await conn.fetchval(
                """
                INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                idempotency_key, from_account, to_account, amount_cents, note,
            )

            # 5. Double-entry: two rows that sum to zero.
            await conn.execute(
                """
                INSERT INTO ledger_entries (transfer_id, account_id, amount)
                VALUES ($1, $2, $3), ($1, $4, $5)
                """,
                transfer_id, from_account, -amount_cents, to_account, amount_cents,
            )

            # 6. Update cached balances inside the same transaction.
            await conn.execute(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1",
                from_account, amount_cents,
            )
            await conn.execute(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1",
                to_account, amount_cents,
            )

            return TransferResult(transfer_id, "completed")


async def reconcile(pool: asyncpg.Pool) -> list[dict]:
    """Return accounts whose cached balance disagrees with the ledger.

    An empty list means the books balance. Run this in tests and as a
    scheduled job in production.
    """
    rows = await pool.fetch(
        """
        SELECT a.id,
               a.balance                    AS cached,
               COALESCE(SUM(l.amount), 0)  AS derived
        FROM accounts a
        LEFT JOIN ledger_entries l ON l.account_id = a.id
        GROUP BY a.id, a.balance
        HAVING a.balance <> COALESCE(SUM(l.amount), 0)
        """
    )
    return [dict(r) for r in rows]
