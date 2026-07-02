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
docker compose up -d          # Postgres + Redis
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## The hard problem: concurrent transfers

*(Writeup coming in Week 1 — how the ledger stays consistent when 100 transfers hit the same account simultaneously.)*

## Roadmap

- [ ] Week 1 — Ledger core: double-entry schema, transfer engine, concurrency tests
- [ ] Week 2 — Auth, idempotency, REST API
- [ ] Week 3 — Next.js frontend: onboarding, send money, activity feed
- [ ] Week 4 — Fraud engine integration, held-for-review flow
- [ ] Week 5 — Polish: optimistic UI, bill splitting, mobile
- [ ] Week 6 — Deploy (Vercel + AWS), demo accounts, writeup
