"""
The test that earns the resume bullet.

Fires N concurrent transfers at the same accounts and proves:
  1. No money is created or destroyed (total balance is invariant).
  2. No wallet ever goes negative.
  3. Cached balances always match the ledger (reconcile() returns []).
  4. Duplicate idempotency keys never double-charge.

Run:  pytest tests/test_concurrency.py -v
Requires docker compose services to be up.
"""

import asyncio
import uuid

import asyncpg
import pytest

from app.services.ledger import InsufficientFunds, execute_transfer, reconcile

DB_DSN = "postgresql://vaultly:vaultly_dev@localhost:5432/vaultly"


@pytest.fixture
async def pool():
    pool = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)
    yield pool
    await pool.close()


async def make_account(pool, starting_cents: int) -> uuid.UUID:
    async with pool.acquire() as conn:
        user_id = await conn.fetchval(
            """INSERT INTO users (email, handle, full_name, password_hash)
               VALUES ($1, $2, 'Test User', 'x') RETURNING id""",
            f"{uuid.uuid4()}@test.com", f"u_{uuid.uuid4().hex[:12]}",
        )
        account_id = await conn.fetchval(
            "INSERT INTO accounts (user_id, balance) VALUES ($1, $2) RETURNING id",
            user_id, starting_cents,
        )
        if starting_cents:
            # Seed via a system transfer so the ledger agrees with the balance.
            await conn.execute(
                """
                WITH t AS (
                    INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note)
                    SELECT $3, id, $1, $2, 'seed' FROM accounts WHERE type = 'system' LIMIT 1
                    RETURNING id
                )
                INSERT INTO ledger_entries (transfer_id, account_id, amount)
                SELECT id, $1, $2 FROM t
                """,
                account_id, starting_cents, f"seed-{account_id}",
            )
        return account_id


@pytest.mark.asyncio
async def test_concurrent_transfers_conserve_money(pool):
    """100 simultaneous $1 transfers A->B. Exactly the right amount moves."""
    a = await make_account(pool, 10_000)   # $100.00
    b = await make_account(pool, 0)

    async def send(i: int):
        try:
            return await execute_transfer(
                pool,
                idempotency_key=f"race-{a}-{i}",
                from_account=a, to_account=b, amount_cents=100,
            )
        except InsufficientFunds:
            return None

    results = await asyncio.gather(*[send(i) for i in range(100)])
    succeeded = [r for r in results if r is not None]

    async with pool.acquire() as conn:
        bal_a = await conn.fetchval("SELECT balance FROM accounts WHERE id = $1", a)
        bal_b = await conn.fetchval("SELECT balance FROM accounts WHERE id = $1", b)

    assert len(succeeded) == 100          # all funded, all should land
    assert bal_a == 0
    assert bal_b == 10_000
    assert bal_a + bal_b == 10_000        # conservation of money
    assert await reconcile(pool) == []    # ledger agrees with cache


@pytest.mark.asyncio
async def test_overdraft_impossible_under_race(pool):
    """200 transfers race for a balance that only covers 50. Never overdrawn."""
    a = await make_account(pool, 5_000)    # $50.00
    b = await make_account(pool, 0)

    async def send(i: int):
        try:
            await execute_transfer(
                pool,
                idempotency_key=f"overdraft-{a}-{i}",
                from_account=a, to_account=b, amount_cents=100,
            )
            return True
        except InsufficientFunds:
            return False

    results = await asyncio.gather(*[send(i) for i in range(200)])

    async with pool.acquire() as conn:
        bal_a = await conn.fetchval("SELECT balance FROM accounts WHERE id = $1", a)

    assert sum(results) == 50              # exactly 50 succeed
    assert bal_a == 0                      # drained to zero, never below
    assert await reconcile(pool) == []


@pytest.mark.asyncio
async def test_idempotency_prevents_double_charge(pool):
    """The same idempotency key retried 20x concurrently charges once."""
    a = await make_account(pool, 10_000)
    b = await make_account(pool, 0)
    key = f"retry-{uuid.uuid4()}"

    async def send():
        return await execute_transfer(
            pool,
            idempotency_key=key,
            from_account=a, to_account=b, amount_cents=2_500,
        )

    results = await asyncio.gather(*[send() for _ in range(20)], return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]

    async with pool.acquire() as conn:
        bal_b = await conn.fetchval("SELECT balance FROM accounts WHERE id = $1", b)

    assert bal_b == 2_500                  # charged exactly once
    assert len({r.transfer_id for r in ok}) == 1
    assert await reconcile(pool) == []
