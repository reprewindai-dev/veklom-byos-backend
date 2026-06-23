-- Migration: 003_settlement_ledger.sql
-- Description: Creates the canonical SettlementLedger table with enum type,
-- composite indexes, and RLS policy for tenant isolation.
-- Safe to run incrementally (all statements are IF NOT EXISTS / conditional).

-- ============================================================
-- Phase 1: Create enum type and table
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'settlement_state_enum') THEN
        CREATE TYPE settlement_state_enum AS ENUM (
            'quoted',
            'locked',
            'released',
            'rejected',
            'failed',
            'debt_pending',
            'refunded'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS settlement_ledger (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id               UUID NOT NULL,
    workspace_id            UUID,

    payer_id                UUID NOT NULL,
    payee_id                UUID NOT NULL,

    asc_channel_id          VARCHAR(128),
    protected_route         VARCHAR(255) NOT NULL,
    service_name            VARCHAR(128) NOT NULL,

    currency_code           VARCHAR(16) NOT NULL DEFAULT 'USDC',
    network_id              VARCHAR(64),

    quoted_amount_minor     BIGINT NOT NULL DEFAULT 0,
    locked_amount_minor     BIGINT NOT NULL DEFAULT 0,
    released_amount_minor   BIGINT NOT NULL DEFAULT 0,

    payment_proof_hash      VARCHAR(128),
    execution_hash          VARCHAR(64) NOT NULL,
    settlement_state        settlement_state_enum NOT NULL DEFAULT 'locked',

    dedupe_key              VARCHAR(128) NOT NULL,
    request_fingerprint     VARCHAR(128),
    failure_reason          TEXT,

    metadata_json           JSONB,

    fulfilled_at            TIMESTAMPTZ,
    settled_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_settlement_ledger_tenant_dedupe_key  UNIQUE (tenant_id, dedupe_key),
    CONSTRAINT uq_settlement_ledger_execution_hash     UNIQUE (execution_hash),
    CONSTRAINT ck_settlement_quoted_nonnegative        CHECK (quoted_amount_minor >= 0),
    CONSTRAINT ck_settlement_locked_nonnegative        CHECK (locked_amount_minor >= 0),
    CONSTRAINT ck_settlement_released_nonnegative      CHECK (released_amount_minor >= 0),
    CONSTRAINT ck_settlement_released_lte_locked       CHECK (released_amount_minor <= locked_amount_minor)
);

-- ============================================================
-- Phase 2: Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS ix_settlement_tenant_id
    ON settlement_ledger (tenant_id);

CREATE INDEX IF NOT EXISTS ix_settlement_workspace_id
    ON settlement_ledger (workspace_id);

CREATE INDEX IF NOT EXISTS ix_settlement_payer_id
    ON settlement_ledger (payer_id);

CREATE INDEX IF NOT EXISTS ix_settlement_payee_id
    ON settlement_ledger (payee_id);

CREATE INDEX IF NOT EXISTS ix_settlement_asc_channel_id
    ON settlement_ledger (asc_channel_id)
    WHERE asc_channel_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_settlement_payment_proof_hash
    ON settlement_ledger (payment_proof_hash)
    WHERE payment_proof_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_settlement_state
    ON settlement_ledger (settlement_state);

-- Composite query-path indexes
CREATE INDEX IF NOT EXISTS ix_settlement_tenant_state_created
    ON settlement_ledger (tenant_id, settlement_state, created_at);

CREATE INDEX IF NOT EXISTS ix_settlement_payer_state_created
    ON settlement_ledger (payer_id, settlement_state, created_at);

CREATE INDEX IF NOT EXISTS ix_settlement_payee_state_created
    ON settlement_ledger (payee_id, settlement_state, created_at);

CREATE INDEX IF NOT EXISTS ix_settlement_route_created
    ON settlement_ledger (protected_route, created_at);

-- ============================================================
-- Phase 3: Automatic updated_at trigger
-- ============================================================

CREATE OR REPLACE FUNCTION set_settlement_ledger_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_settlement_ledger_updated_at ON settlement_ledger;
CREATE TRIGGER trg_settlement_ledger_updated_at
    BEFORE UPDATE ON settlement_ledger
    FOR EACH ROW EXECUTE PROCEDURE set_settlement_ledger_updated_at();

-- ============================================================
-- Phase 4: Row-Level Security (PostgreSQL only)
-- Assumes get_rls_db sets app.current_tenant_id per request.
-- ============================================================

ALTER TABLE settlement_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlement_ledger FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_settlement_ledger ON settlement_ledger;
CREATE POLICY tenant_isolation_settlement_ledger
ON settlement_ledger
FOR ALL
USING (
    tenant_id = current_setting('app.current_tenant_id', true)::uuid
)
WITH CHECK (
    tenant_id = current_setting('app.current_tenant_id', true)::uuid
);
