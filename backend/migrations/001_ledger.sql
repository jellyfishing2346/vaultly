-- vaultly ledger schema (double-entry bookkeeping)
--
-- Design principles:
--   1. Balances are DERIVED from ledger entries, never stored as a mutable column
--      (a cached balance column exists only as an optimization, updated in the
--      same transaction as the entries and verifiable via reconciliation).
--   2. Every transfer produces exactly two entries: a debit and a credit.
--      SUM(amount) across both entries of a transfer is always zero.
--   3. Amounts are BIGINT cents. Never floats. Never floats. Never floats.

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    handle      TEXT UNIQUE NOT NULL,          -- @username for P2P lookup
    full_name   TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    type        TEXT NOT NULL DEFAULT 'wallet'
                CHECK (type IN ('wallet', 'external', 'system')),
    -- Cached balance in cents. Optimization only — must always equal
    -- SUM(ledger_entries.amount) for this account. Verified by reconciliation.
    balance     BIGINT NOT NULL DEFAULT 0
                CHECK (type <> 'wallet' OR balance >= 0),  -- wallets can't go negative
    currency    TEXT NOT NULL DEFAULT 'USD',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_accounts_user ON accounts(user_id);

CREATE TABLE transfers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key TEXT UNIQUE NOT NULL,       -- client-supplied; retries return the original result
    from_account    UUID NOT NULL REFERENCES accounts(id),
    to_account      UUID NOT NULL REFERENCES accounts(id),
    amount          BIGINT NOT NULL CHECK (amount > 0),   -- cents
    note            TEXT,
    status          TEXT NOT NULL DEFAULT 'completed'
                    CHECK (status IN ('pending_review', 'completed', 'rejected', 'failed')),
    fraud_score     REAL,                        -- populated by the fraud service
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (from_account <> to_account)
);

CREATE INDEX idx_transfers_from ON transfers(from_account, created_at DESC);
CREATE INDEX idx_transfers_to   ON transfers(to_account, created_at DESC);

-- The ledger. Append-only: no UPDATE, no DELETE, ever.
CREATE TABLE ledger_entries (
    id          BIGSERIAL PRIMARY KEY,
    transfer_id UUID NOT NULL REFERENCES transfers(id),
    account_id  UUID NOT NULL REFERENCES accounts(id),
    -- Signed amount in cents: negative = debit, positive = credit.
    amount      BIGINT NOT NULL CHECK (amount <> 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_account ON ledger_entries(account_id, id);

-- Enforce append-only at the database level.
CREATE OR REPLACE FUNCTION forbid_ledger_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ledger_entries is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ledger_no_update BEFORE UPDATE OR DELETE ON ledger_entries
    FOR EACH ROW EXECUTE FUNCTION forbid_ledger_mutation();
