# 💰 Vaultly

**P2P payments with a double-entry ledger and real-time ML fraud detection**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)

> 🚧 In active development. Live demo coming soon.

---

## ✨ What It Does

Vaultly is a peer-to-peer payment system that prioritizes **financial correctness** over everything else. Every transfer is recorded in a double-entry ledger, ensuring money can never be created or destroyed by bugs — even under extreme concurrency.

### Key Features

- **💸 Venmo-Style Transfers** — Send and receive money with an intuitive activity feed
- **📗 Double-Entry Ledger** — Balances are derived, never mutated, so money can't be created or destroyed by bugs
- **🔒 Idempotency Keys** — Retried requests never double-charge
- **⚡ Concurrent-Safe** — Row-level locking + serializable transactions handle 100+ simultaneous transfers
- **🤖 Real-Time Fraud Detection** — XGBoost model scores transfers; high-risk transfers are held for review

---

## 🏗️ Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Next.js App   │◄────────┤    FastAPI      │
│  (Frontend)     │ REST+WS │   (Backend)     │
└─────────────────┘         └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌──────────┐    ┌──────────┐    ┌──────────────┐
             │PostgreSQL│    │  Redis   │    │XGBoost Model │
             │  Ledger  │    │ Cache    │    │Fraud Scoring │
             └──────────┘    └──────────┘    └──────────────┘
```

### Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI, PostgreSQL, Redis
- **ML**: XGBoost for real-time fraud detection
- **Infrastructure**: Docker Compose

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 18+ and npm

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/vaultly.git
cd vaultly

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Install frontend dependencies (new terminal)
cd frontend
npm install
npm run dev
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Seed Demo Data

```bash
cd backend
python seed_demo_data.py
```

This creates 4 demo users with $100 each:

| Email | Handle | Password |
|-------|--------|----------|
| alice@demo.vaultly | alice | demo123 |
| bob@demo.vaultly | bob | demo123 |
| charlie@demo.vaultly | charlie | demo123 |
| diana@demo.vaultly | diana | demo123 |

---

## 🧠 The Hard Problem: Concurrent Transfers

When 100 transfers hit the same account simultaneously, how do we ensure money is never created or destroyed? This is the classic "banker's problem" made worse by concurrent requests.

### The Problem

Consider account A with $100. If 100 users each try to transfer $1 from A at the exact same moment:

```
Thread 1: read balance = 100, transfer $1, write balance = 99
Thread 2: read balance = 100, transfer $1, write balance = 99  
Thread 3: read balance = 100, transfer $1, write balance = 99
...
```

**Result**: Account A has $99, but $3 was transferred. Money was created from thin air.

This is a classic TOCTOU (Time-Of-Check-Time-Of-Use) race condition.

### Our Solution

Vaultly solves this with three layers of protection:

#### 1. Row-Level Locking with Deterministic Ordering

```python
# Lock both accounts in a consistent order to prevent deadlocks
first, second = sorted([from_account, to_account])
rows = await conn.fetch(
    "SELECT id, balance FROM accounts WHERE id = ANY($1::uuid[]) ORDER BY id FOR UPDATE",
    [first, second],
)
```

`FOR UPDATE` locks the account rows for the duration of the transaction. By always sorting the account IDs, we prevent deadlocks when A→B and B→A transfers race each other.

#### 2. Idempotency Keys at the Database Layer

```sql
CREATE TABLE transfers (
    idempotency_key TEXT UNIQUE NOT NULL,  -- Enforced by UNIQUE constraint
    ...
);
```

When a client retries a request with the same idempotency key, the database's UNIQUE constraint rejects the duplicate insertion. We catch this and return the original transfer result instead of charging twice.

#### 3. Double-Entry Ledger with Reconciliation

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

### Proof It Works

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

### Why This Matters

Most payment systems use optimistic locking or eventually consistent balances. These can drift under load. Vaultly's approach guarantees correctness even under extreme concurrency — the kind that happens during flash sales, viral payments, or when a celebrity shares their handle.

The double-entry ledger is how real banks have kept books balanced for centuries. We've just adapted it for the concurrent web.

---

## 📚 Documentation

- **[Architecture](ARCHITECTURE.md)** — Detailed system architecture and design decisions
- **[API Documentation](API.md)** — Complete API reference with examples
- **[Deployment Guide](DEPLOYMENT.md)** — Production deployment instructions
- **[Contributing](CONTRIBUTING.md)** — How to contribute to Vaultly
- **[Changelog](CHANGELOG.md)** — Version history and changes

---

## 🗺️ Roadmap

- [x] Week 1 — Ledger core: double-entry schema, transfer engine, concurrency tests
- [x] Week 2 — Auth, idempotency, REST API
- [x] Week 3 — Next.js frontend: onboarding, send money, activity feed
- [x] Week 4 — Fraud engine integration, held-for-review flow
- [x] Week 5 — Polish: loading states, error handling, mobile responsiveness, empty states
- [x] Week 6 — Deploy configuration, demo data, comprehensive documentation

### Planned Features

- [ ] WebSocket support for real-time updates
- [ ] Multi-currency support
- [ ] Recurring transfers
- [ ] Bill splitting
- [ ] Mobile applications (iOS/Android)
- [ ] Advanced fraud detection features

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Concurrency tests
pytest tests/test_concurrency.py -v

# Frontend tests
cd frontend
npm test
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas where we need help:
- Frontend: Mobile responsiveness, additional payment features
- Backend: Additional fraud detection features, performance optimization
- Documentation: Tutorials, examples, API documentation
- Testing: End-to-end tests, load testing
- DevOps: CI/CD improvements, deployment automation

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Double-entry bookkeeping principles used by banks for centuries
- Stripe's idempotency key convention
- The FastAPI and Next.js communities
- The open-source financial systems community

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/vaultly/issues)
- **Documentation**: [docs.vaultly.com](https://docs.vaultly.com) (coming soon)
- **Email**: support@vaultly.com (coming soon)

---

**Built with ❤️ for financial correctness**

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
