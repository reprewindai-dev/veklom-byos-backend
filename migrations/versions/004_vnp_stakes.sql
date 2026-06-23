-- VNP Stakes Engine Ledger

CREATE TABLE IF NOT EXISTS vnp_stake_logs (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) DEFAULT '' NOT NULL,
    api_route VARCHAR(128) NOT NULL,
    stake_amount_usdc DOUBLE PRECISION DEFAULT 0.0,
    latency_ms DOUBLE PRECISION DEFAULT 0.0,
    sla_threshold_ms DOUBLE PRECISION DEFAULT 800.0,
    result VARCHAR(32) DEFAULT ''yield'',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone(''utc'', now())
);

CREATE INDEX IF NOT EXISTS ix_vnp_stake_logs_workspace_id ON vnp_stake_logs(workspace_id);
