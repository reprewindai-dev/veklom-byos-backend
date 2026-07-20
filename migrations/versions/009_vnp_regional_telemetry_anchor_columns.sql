-- Migration 009: Ensure vnp_regional_telemetry exists with anchor columns
-- Fixes 500 error in /api/v1/vnp/metrics and nexus scorecard endpoint
-- which reference block_number, chain_id, contract_address, confirmation_state

-- Create the table if it was never created by a previous migration.
-- IF NOT EXISTS is a no-op when the table already exists.
CREATE TABLE IF NOT EXISTS vnp_regional_telemetry (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    api_id              UUID        NOT NULL REFERENCES vnp_apis(id) ON DELETE CASCADE,
    region_code         VARCHAR(50) NOT NULL,
    window_start        TIMESTAMPTZ NOT NULL,
    window_end          TIMESTAMPTZ NOT NULL,
    sample_count        INTEGER     NOT NULL,
    success_count       INTEGER     NOT NULL,
    p50_latency_ms      INTEGER     NOT NULL,
    p95_latency_ms      INTEGER     NOT NULL,
    p99_latency_ms      INTEGER     NOT NULL,
    error_rate_percent  NUMERIC(5,2) NOT NULL,
    uptime_percent      NUMERIC(5,2) NOT NULL,
    throughput_rps      INTEGER     NOT NULL DEFAULT 0,
    trust_score         NUMERIC(5,2) NOT NULL,
    provenance_hash     TEXT,
    on_chain_anchor     TEXT,
    block_number        INTEGER,
    chain_id            INTEGER,
    contract_address    VARCHAR(42),
    confirmation_state  VARCHAR(50),
    measured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- If the table already existed without the anchor columns, add them safely.
ALTER TABLE vnp_regional_telemetry
    ADD COLUMN IF NOT EXISTS block_number       INTEGER;

ALTER TABLE vnp_regional_telemetry
    ADD COLUMN IF NOT EXISTS chain_id           INTEGER;

ALTER TABLE vnp_regional_telemetry
    ADD COLUMN IF NOT EXISTS contract_address   VARCHAR(42);

ALTER TABLE vnp_regional_telemetry
    ADD COLUMN IF NOT EXISTS confirmation_state VARCHAR(50);

-- Ensure the covering index the ORM declares also exists.
CREATE INDEX IF NOT EXISTS idx_regional_telemetry_region_score
    ON vnp_regional_telemetry (region_code, trust_score, p99_latency_ms);
