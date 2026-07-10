CREATE TABLE IF NOT EXISTS agent_duel_lobbies (
    id VARCHAR(16) PRIMARY KEY,
    host_wallet_address VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    max_players INTEGER NOT NULL DEFAULT 2,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_duel_lobbies_host_wallet_address ON agent_duel_lobbies (host_wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobbies_status ON agent_duel_lobbies (status);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobbies_status_created ON agent_duel_lobbies (status, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobbies_host_created ON agent_duel_lobbies (host_wallet_address, created_at);

CREATE TABLE IF NOT EXISTS agent_duel_lobby_players (
    id VARCHAR(36) PRIMARY KEY,
    lobby_id VARCHAR(16) NOT NULL,
    wallet_address VARCHAR(64) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'joined',
    bet_type VARCHAR(16),
    wager_id VARCHAR(36),
    wager_amount_usdc DOUBLE PRECISION NOT NULL DEFAULT 0,
    ejected_multiplier DOUBLE PRECISION,
    payout_usdc DOUBLE PRECISION NOT NULL DEFAULT 0,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_lobby_id ON agent_duel_lobby_players (lobby_id);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_wallet_address ON agent_duel_lobby_players (wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_session_id ON agent_duel_lobby_players (session_id);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_status ON agent_duel_lobby_players (status);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_wager_id ON agent_duel_lobby_players (wager_id);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_lobby_wallet ON agent_duel_lobby_players (lobby_id, wallet_address);
CREATE INDEX IF NOT EXISTS ix_agent_duel_lobby_players_lobby_status ON agent_duel_lobby_players (lobby_id, status);
