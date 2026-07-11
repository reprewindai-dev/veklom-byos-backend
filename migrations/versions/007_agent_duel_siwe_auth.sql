CREATE TABLE IF NOT EXISTS agent_duel_auth_nonces (
    id VARCHAR(36) PRIMARY KEY,
    wallet_address VARCHAR(64) NOT NULL,
    nonce_hash VARCHAR(128) NOT NULL UNIQUE,
    domain VARCHAR(128) NOT NULL,
    uri VARCHAR(256) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 8453,
    message TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'issued',
    metadata_json JSON,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_duel_auth_nonces_wallet_address ON agent_duel_auth_nonces (wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_auth_nonces_nonce_hash ON agent_duel_auth_nonces (nonce_hash);
CREATE INDEX IF NOT EXISTS ix_agent_duel_auth_nonces_status ON agent_duel_auth_nonces (status);
CREATE INDEX IF NOT EXISTS ix_agent_duel_auth_nonces_wallet_created ON agent_duel_auth_nonces (wallet_address, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_duel_auth_nonces_status_expires ON agent_duel_auth_nonces (status, expires_at);
