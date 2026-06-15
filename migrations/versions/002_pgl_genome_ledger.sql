-- Migration: 002_pgl_genome_ledger.sql
-- Description: Adds Merkle and governance columns, creates certificates, risk profiles, outcomes, high performers, policy versions and enforcement bundles tables.

-- 1. Enhance genome_versions table
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS model_layer_hash VARCHAR(128);
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS prompt_layer_hash VARCHAR(128);
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS policy_layer_hash VARCHAR(128);
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS watchtower_layer_hash VARCHAR(128);
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS task_profile_hash VARCHAR(128);
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS merkle_root VARCHAR(128) UNIQUE;
ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS parent_genome_ids JSON;

CREATE INDEX IF NOT EXISTS idx_genome_merkle_root ON genome_versions(merkle_root);

-- 2. Enhance ledger_events table
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS trace_id VARCHAR(64);
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS policy_version VARCHAR(32);
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS constitution_version VARCHAR(32);
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS override_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS override_reason VARCHAR(512);
ALTER TABLE ledger_events ADD COLUMN IF NOT EXISTS genome_hash VARCHAR(128);

CREATE INDEX IF NOT EXISTS idx_ledger_trace_id ON ledger_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_ledger_genome_hash ON ledger_events(genome_hash);

-- 3. Create execution_certificates table
CREATE TABLE IF NOT EXISTS execution_certificates (
    id VARCHAR(36) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL UNIQUE,
    genome_hash VARCHAR(128) NOT NULL,
    input_hash VARCHAR(128) NOT NULL,
    output_hash VARCHAR(128) NOT NULL,
    watchtower_results JSON NOT NULL,
    governance_tier VARCHAR(32) NOT NULL,
    governance_overhead_ms INTEGER NOT NULL DEFAULT 0,
    policy_version VARCHAR(32),
    constitution_version VARCHAR(32),
    certificate_jwt TEXT NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cert_trace_id ON execution_certificates(trace_id);
CREATE INDEX IF NOT EXISTS idx_cert_genome_hash ON execution_certificates(genome_hash);

-- 4. Create org_risk_profiles table
CREATE TABLE IF NOT EXISTS org_risk_profiles (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL UNIQUE,
    abuse_score DOUBLE PRECISION DEFAULT 0.0,
    override_abuse_score DOUBLE PRECISION DEFAULT 0.0,
    payment_risk_score DOUBLE PRECISION DEFAULT 0.0,
    injection_attempts INTEGER DEFAULT 0,
    composite_risk DOUBLE PRECISION DEFAULT 0.0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risk_org_id ON org_risk_profiles(org_id);

-- 5. Create outcome_feedback table
CREATE TABLE IF NOT EXISTS outcome_feedback (
    id VARCHAR(36) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL UNIQUE,
    accepted BOOLEAN DEFAULT TRUE,
    user_rating INTEGER,
    feedback_text TEXT,
    actual_outcome JSON,
    predicted_outcome JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_trace_id ON outcome_feedback(trace_id);

-- 6. Create high_performer_entries table
CREATE TABLE IF NOT EXISTS high_performer_entries (
    id VARCHAR(36) PRIMARY KEY,
    task_type VARCHAR(64) NOT NULL,
    output_signature VARCHAR(128) NOT NULL,
    performance_score DOUBLE PRECISION DEFAULT 1.0,
    genome_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_high_perf_genome ON high_performer_entries(genome_hash);
CREATE INDEX IF NOT EXISTS idx_high_perf_task ON high_performer_entries(task_type);

-- 7. Create policy_versions table
CREATE TABLE IF NOT EXISTS policy_versions (
    id VARCHAR(36) PRIMARY KEY,
    version VARCHAR(32) NOT NULL UNIQUE,
    policies JSON NOT NULL,
    approved_by VARCHAR(64),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policy_version ON policy_versions(version);

-- 8. Create enforcement_bundles table
CREATE TABLE IF NOT EXISTS enforcement_bundles (
    id VARCHAR(36) PRIMARY KEY,
    policy_version VARCHAR(32) NOT NULL,
    constitution_version VARCHAR(32) NOT NULL,
    bundle_hash VARCHAR(128) NOT NULL UNIQUE,
    regression_passed BOOLEAN DEFAULT TRUE,
    compiled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bundle_hash ON enforcement_bundles(bundle_hash);
