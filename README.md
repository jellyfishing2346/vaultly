# vaultly

P2P payments with a double-entry ledger and real-time ML fraud detection.

> 🚧 In active development. Live demo coming soon.

## What it does

- Send and receive money between users with a Venmo-style activity feed
- Every transfer is recorded in a **double-entry ledger** — balances are derived, never mutated, so money can't be created or destroyed by a bug
- **Idempotency keys** guarantee that retried requests never double-charge
- Concurrent transfers are safe under load: row-level locking + serializable transactions (see [concurrency tests](backend/tests/test_concurrency.py))
- Transfers are scored in real time by an XGBoost fraud model; high-risk transfers are held for review

## Architecture

```
Next.js (TypeScript, Tailwind)
        │  REST + WebSocket
        ▼
FastAPI ──► PostgreSQL (ledger: accounts, entries, transfers)
   │  └───► Redis (idempotency keys, rate limiting)
   └──────► Fraud scoring service (XGBoost)
```

## Running locally

```bash
# Start infrastructure
docker compose up -d          # Postgres + Redis

# Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

The backend will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

To seed demo data for testing:
```bash
cd backend
python seed_demo_data.py
```

This creates 4 demo users with initial balances and sample transfers:
- `alice@demo.vaultly` / `demo123`
- `bob@demo.vaultly` / `demo123`
- `charlie@demo.vaultly` / `demo123`
- `diana@demo.vaultly` / `demo123`

## The hard problem: concurrent transfers

When 100 transfers hit the same account simultaneously, how do we ensure money is never created or destroyed? This is the classic "banker's problem" made worse by concurrent requests.

### The problem

Consider account A with $100. If 100 users each try to transfer $1 from A at the exact same moment:

```
Thread 1: read balance = 100, transfer $1, write balance = 99
Thread 2: read balance = 100, transfer $1, write balance = 99  
Thread 3: read balance = 100, transfer $1, write balance = 99
...
```

**Result**: Account A has $99, but $3 was transferred. Money was created from thin air.

This is a classic TOCTOU (Time-Of-Check-Time-Of-Use) race condition. Between checking the balance and updating it, another thread can make the same check and arrive at the same wrong conclusion.

### Our solution

Vaultly solves this with three layers of protection:

#### 1. Row-level locking with deterministic ordering

```python
# Lock both accounts in a consistent order to prevent deadlocks
first, second = sorted([from_account, to_account])
rows = await conn.fetch(
    "SELECT id, balance FROM accounts WHERE id = ANY($1::uuid[]) ORDER BY id FOR UPDATE",
    [first, second],
)
```

`FOR UPDATE` locks the account rows for the duration of the transaction. No other transaction can read or modify them until this one commits. By always sorting the account IDs, we prevent deadlocks when A→B and B→A transfers race each other.

#### 2. Idempotency keys at the database layer

```sql
CREATE TABLE transfers (
    idempotency_key TEXT UNIQUE NOT NULL,  -- Enforced by UNIQUE constraint
    ...
);
```

When a client retries a request with the same idempotency key, the database's UNIQUE constraint rejects the duplicate insertion. We catch this and return the original transfer result instead of charging twice.

#### 3. Double-entry ledger with reconciliation

Every transfer creates exactly two ledger entries:
```sql
INSERT INTO ledger_entries (transfer_id, account_id, amount)
VALUES ($1, $2, -$3), ($1, $4, $3)  -- debit and credit
```

The `balance` column in accounts is just a cached value. We can verify correctness at any time:

```python
async def reconcile(pool):
    """Return accounts where cached balance ≠ sum of ledger entries."""
    rows = await pool.fetch("""
        SELECT a.id, a.balance AS cached, COALESCE(SUM(l.amount), 0) AS derived
        FROM accounts a
        LEFT JOIN ledger_entries l ON l.account_id = a.id
        GROUP BY a.id, a.balance
        HAVING a.balance <> COALESCE(SUM(l.amount), 0)
    """)
    return rows
```

If `reconcile()` returns an empty list, the books balance perfectly.

### Proof it works

Our concurrency tests (`tests/test_concurrency.py`) fire 100+ simultaneous transfers and prove:

1. **Money conservation**: Total balance never changes
2. **No overdrafts**: Account balance never goes negative  
3. **Ledger agreement**: Cached balances always match derived ledger sums
4. **Idempotency**: 20 concurrent requests with the same key charge exactly once

```bash
$ pytest tests/test_concurrency.py -v
tests/test_concurrency.py::test_concurrent_transfers_conserve_money PASSED
tests/test_concurrency.py::test_overdraft_impossible_under_race PASSED  
tests/test_concurrency.py::test_idempotency_prevents_double_charge PASSED
```

### Why this matters

Most payment systems use optimistic locking or eventually consistent eventual balances. These can drift under load. Vaultly's approach guarantees correctness even under extreme concurrency — the kind that happens during flash sales, viral payments, or when a celebrity shares their handle.

The double-entry ledger is how real banks have kept books balanced for centuries. We've just adapted it for the concurrent web.

## Roadmap

- [x] Week 1 — Ledger core: double-entry schema, transfer engine, concurrency tests
- [x] Week 2 — Auth, idempotency, REST API
- [x] Week 3 — Next.js frontend: onboarding, send money, activity feed
- [x] Week 4 — Fraud engine integration, held-for-review flow
- [x] Week 5 — Polish: loading states, error handling, mobile responsiveness, empty states
- [x] Week 6 — Deploy configuration, demo data, comprehensive documentation
