CREATE TABLE IF NOT EXISTS agent_duel_sessions (
    id VARCHAR(36) PRIMARY KEY,
    wallet_address VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    balance_usdc DOUBLE PRECISION NOT NULL DEFAULT 0,
    network VARCHAR(32) NOT NULL DEFAULT 'base',
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_agent_duel_sessions_wallet_address ON agent_duel_sessions (wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_sessions_status ON agent_duel_sessions (status);
CREATE INDEX IF NOT EXISTS ix_agent_duel_sessions_wallet_created ON agent_duel_sessions (wallet_address, created_at);

CREATE TABLE IF NOT EXISTS agent_duel_wagers (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    wallet_address VARCHAR(64) NOT NULL,
    bet_type VARCHAR(16) NOT NULL,
    wager_amount_usdc DOUBLE PRECISION NOT NULL,
    payment_signature VARCHAR(4096) NOT NULL,
    signature_hash VARCHAR(128) NOT NULL,
    outcome VARCHAR(16),
    payout_multiplier DOUBLE PRECISION NOT NULL DEFAULT 0,
    payout_usdc DOUBLE PRECISION NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    settlement_tx_hash VARCHAR(128),
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_session_id ON agent_duel_wagers (session_id);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_wallet_address ON agent_duel_wagers (wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_signature_hash ON agent_duel_wagers (signature_hash);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_outcome ON agent_duel_wagers (outcome);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_status ON agent_duel_wagers (status);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_settlement_tx_hash ON agent_duel_wagers (settlement_tx_hash);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_wallet_created ON agent_duel_wagers (wallet_address, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_duel_wagers_session_created ON agent_duel_wagers (session_id, created_at);
