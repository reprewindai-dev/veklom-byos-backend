-- Mission Lock Agent Control Plane Unified Schema (15 Tables)
-- Deploy to Postgres on your Hetzner instance or test with local fallback
-- Tracks behavioral stickiness, agent DNA, runtime policies, and audit trails

CREATE SCHEMA IF NOT EXISTS mission_lock;

-- 1. Mission DNA: per-agent behavioral profile (immutable, auditable)
CREATE TABLE IF NOT EXISTS mission_lock.mission_dna (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL UNIQUE,
    role VARCHAR(64) NOT NULL,
    dominance FLOAT8 DEFAULT 0.85 CHECK (dominance >= 0.5 AND dominance <= 1.0),
    plasticity FLOAT8 DEFAULT 0.01 CHECK (plasticity >= 0.001 AND plasticity <= 0.05),
    base_learning_rate FLOAT8 DEFAULT 0.08 CHECK (base_learning_rate > 0),
    epsilon FLOAT8 DEFAULT 0.02 CHECK (epsilon >= 0.001 AND epsilon <= 0.2),
    mission_bonus FLOAT8 DEFAULT 1.0,
    off_path_penalty FLOAT8 DEFAULT 0.15,
    coordination_weight FLOAT8 DEFAULT 0.5 CHECK (coordination_weight >= 0 AND coordination_weight <= 1.0),
    safety_weight FLOAT8 DEFAULT 1.0,
    cue_boost FLOAT8 DEFAULT 0.10,
    min_dominance FLOAT8 DEFAULT 0.50,
    max_epsilon FLOAT8 DEFAULT 0.15,
    max_plasticity FLOAT8 DEFAULT 0.05,
    allowed_actions TEXT[] DEFAULT NULL,
    forbidden_actions TEXT[] DEFAULT ARRAY[]::TEXT[],
    tenant_id VARCHAR(128),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    locked BOOLEAN DEFAULT FALSE,
    version INT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_mission_dna_agent_id ON mission_lock.mission_dna(agent_id);
CREATE INDEX IF NOT EXISTS idx_mission_dna_tenant ON mission_lock.mission_dna(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mission_dna_role ON mission_lock.mission_dna(role);

-- 2. Mission paths: the desired behavioral trajectory per agent
CREATE TABLE IF NOT EXISTS mission_lock.agent_missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL UNIQUE,
    mission_name VARCHAR(256) NOT NULL,
    preferred_transitions JSONB NOT NULL,
    description TEXT,
    tenant_id VARCHAR(128),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    version INT DEFAULT 1,
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_missions_agent_id ON mission_lock.agent_missions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_missions_tenant ON mission_lock.agent_missions(tenant_id);

-- 3. Agent state: runtime behavioral metrics (frequently updated)
CREATE TABLE IF NOT EXISTS mission_lock.agent_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL UNIQUE,
    current_dominance FLOAT8 DEFAULT 0.85,
    current_plasticity FLOAT8 DEFAULT 0.01,
    current_epsilon FLOAT8 DEFAULT 0.02,
    target_return FLOAT8 DEFAULT NULL,
    last_episode_return FLOAT8 DEFAULT 0.0,
    moving_avg_return FLOAT8 DEFAULT 0.0,
    path_conformance FLOAT8 DEFAULT 0.0,
    steps_since_recovery INT DEFAULT 0,
    safety_violations INT DEFAULT 0,
    last_action VARCHAR(256),
    last_state VARCHAR(256),
    last_update TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_state_agent_id ON mission_lock.agent_state(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_state_last_update ON mission_lock.agent_state(last_update DESC);

-- 4. Episode telemetry: per-episode performance and behavior
CREATE TABLE IF NOT EXISTS mission_lock.episode_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    episode_num INT NOT NULL,
    episode_return FLOAT8 NOT NULL,
    path_actions INT DEFAULT 0,
    off_path_actions INT DEFAULT 0,
    path_conformance FLOAT8 DEFAULT 0.0,
    safety_events INT DEFAULT 0,
    steps INT DEFAULT 0,
    recovery_triggered BOOLEAN DEFAULT FALSE,
    dominance_at_episode FLOAT8,
    epsilon_at_episode FLOAT8,
    plasticity_at_episode FLOAT8,
    timestamp TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episode_telemetry_agent_episode ON mission_lock.episode_telemetry(agent_id, episode_num DESC);
CREATE INDEX IF NOT EXISTS idx_episode_telemetry_timestamp ON mission_lock.episode_telemetry(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episode_telemetry_recovery ON mission_lock.episode_telemetry(recovery_triggered) WHERE recovery_triggered = TRUE;

-- 5. Team coordination state: multi-agent orchestration
CREATE TABLE IF NOT EXISTS mission_lock.team_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(128) NOT NULL,
    phase VARCHAR(64),
    alerts TEXT[] DEFAULT ARRAY[]::TEXT[],
    shared_goal_progress FLOAT8 DEFAULT 0.0,
    last_joint_actions JSONB,
    last_update TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS idx_team_state_team_id ON mission_lock.team_state(team_id);
CREATE INDEX IF NOT EXISTS idx_team_state_last_update ON mission_lock.team_state(last_update DESC);

-- 6. Coordination decisions: audit trail for team actions
CREATE TABLE IF NOT EXISTS mission_lock.coordination_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(128) NOT NULL,
    episode_num INT,
    state VARCHAR(256),
    coordinated_actions JSONB NOT NULL,
    local_rewards JSONB,
    coordination_bonuses JSONB,
    safety_penalties JSONB,
    net_rewards JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS idx_coordination_log_team_episode ON mission_lock.coordination_log(team_id, episode_num DESC);
CREATE INDEX IF NOT EXISTS idx_coordination_log_timestamp ON mission_lock.coordination_log(timestamp DESC);

-- 7. Recovery history: when and why plasticity was increased
CREATE TABLE IF NOT EXISTS mission_lock.recovery_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    episode_num INT,
    trigger VARCHAR(64),
    reason TEXT,
    dominance_before FLOAT8,
    dominance_after FLOAT8,
    epsilon_before FLOAT8,
    epsilon_after FLOAT8,
    plasticity_before FLOAT8,
    plasticity_after FLOAT8,
    timestamp TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recovery_events_agent ON mission_lock.recovery_events(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_recovery_events_trigger ON mission_lock.recovery_events(trigger);

-- 8. Audit trail: all DNA mutations (immutability tracking)
CREATE TABLE IF NOT EXISTS mission_lock.dna_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    changed_fields JSONB NOT NULL,
    old_values JSONB NOT NULL,
    new_values JSONB NOT NULL,
    changed_by VARCHAR(256),
    reason TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS idx_dna_audit_agent ON mission_lock.dna_audit(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dna_audit_timestamp ON mission_lock.dna_audit(timestamp DESC);

-- 9. Agent runtime state: Out-of-process serialization of Q-learning policy matrices
CREATE TABLE IF NOT EXISTS mission_lock.agent_runtime_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL UNIQUE,
    target_return FLOAT8,
    dominant_policy_json JSONB NOT NULL,
    base_policy_json JSONB NOT NULL,
    last_update TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_state_agent ON mission_lock.agent_runtime_state(agent_id);

-- 10. Agent action trace: Flight recorder logging of exact action sequences & conformance
CREATE TABLE IF NOT EXISTS mission_lock.agent_action_trace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    state VARCHAR(256) NOT NULL,
    action VARCHAR(256) NOT NULL,
    reward FLOAT8 NOT NULL,
    next_state VARCHAR(256) NOT NULL,
    on_path BOOLEAN NOT NULL,
    cue BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT NOW(),
    tenant_id VARCHAR(128),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_action_trace_agent ON mission_lock.agent_action_trace(agent_id, timestamp DESC);

-- 11. Idempotency keys: Deduplication and safety for mutating API requests
CREATE TABLE IF NOT EXISTS mission_lock.idempotency_keys (
    key VARCHAR(256) PRIMARY KEY,
    response_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 12. Recovery snapshot: Full policy and telemetry dump on drift trigger
CREATE TABLE IF NOT EXISTS mission_lock.recovery_snapshot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    recovery_event_id UUID,
    state_snapshot JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (agent_id) REFERENCES mission_lock.mission_dna(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (recovery_event_id) REFERENCES mission_lock.recovery_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recovery_snapshot_agent ON mission_lock.recovery_snapshot(agent_id);

-- 13. Metrics cache: Pre-aggregated dashboard values for sub-millisecond loads
CREATE TABLE IF NOT EXISTS mission_lock.metrics_cache (
    key VARCHAR(128) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 14. Tenant roles: Multi-tenant tenant access registry
CREATE TABLE IF NOT EXISTS mission_lock.tenant_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(256) NOT NULL,
    role VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_roles_lookup ON mission_lock.tenant_roles(tenant_id, user_id);

-- 15. Continuous authorization log: Audit gate for all secure syscalls and compliance
CREATE TABLE IF NOT EXISTS mission_lock.authz_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(256),
    tenant_id VARCHAR(128),
    action VARCHAR(128) NOT NULL,
    resource VARCHAR(128) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_authz_log_timestamp ON mission_lock.authz_log(timestamp DESC);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION mission_lock.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_mission_dna_timestamp ON mission_lock.mission_dna;
CREATE TRIGGER update_mission_dna_timestamp
BEFORE UPDATE ON mission_lock.mission_dna
FOR EACH ROW EXECUTE FUNCTION mission_lock.update_timestamp();

DROP TRIGGER IF EXISTS update_agent_missions_timestamp ON mission_lock.agent_missions;
CREATE TRIGGER update_agent_missions_timestamp
BEFORE UPDATE ON mission_lock.agent_missions
FOR EACH ROW EXECUTE FUNCTION mission_lock.update_timestamp();
