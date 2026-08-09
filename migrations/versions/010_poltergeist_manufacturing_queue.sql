-- Migration 010: Poltergeist Manufacturing Queue
-- Creates the durable state machine tables for the Poltergeist
-- capability manufacturing lifecycle (DETECTED → QUEUED → IN_PROGRESS → VALIDATED → BOUND → FAILED).
-- Each job is write-once on creation; status transitions are recorded in manufacturing_transitions
-- as an append-only audit log.

CREATE TABLE IF NOT EXISTS manufacturing_jobs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    target_repository   TEXT        NOT NULL,
    target_commit       TEXT        NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'DETECTED',
    metadata            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient worker polling by status
CREATE INDEX IF NOT EXISTS ix_manufacturing_jobs_status
    ON manufacturing_jobs (status);

-- Index for repository-scoped queries (dedup checks)
CREATE INDEX IF NOT EXISTS ix_manufacturing_jobs_target_repository
    ON manufacturing_jobs (target_repository);

-- Append-only transition log for every status change
CREATE TABLE IF NOT EXISTS manufacturing_transitions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID        NOT NULL REFERENCES manufacturing_jobs(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status   TEXT        NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient history lookup per job
CREATE INDEX IF NOT EXISTS ix_manufacturing_transitions_job_id
    ON manufacturing_transitions (job_id);

-- Capability haunt state (hot resolution tracking per workspace fingerprint)
CREATE TABLE IF NOT EXISTS capability_haunt_states (
    id                          VARCHAR(36) PRIMARY KEY,
    workspace_id                VARCHAR(36) NOT NULL,
    fingerprint                 VARCHAR(255) NOT NULL UNIQUE,
    status                      VARCHAR(32)  NOT NULL DEFAULT 'idle',
    heartbeat                   INTEGER      NOT NULL DEFAULT 0,
    queued_revision             INTEGER      NOT NULL DEFAULT 1,
    freshest_artifact_revision  INTEGER      NOT NULL DEFAULT 0,
    manifest                    JSONB        NOT NULL DEFAULT '{}',
    verification_results        JSONB        NOT NULL DEFAULT '{}',
    error_log                   TEXT         NOT NULL DEFAULT '',
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_capability_haunt_states_workspace_id
    ON capability_haunt_states (workspace_id);

-- Capability ghost (permanent system-of-record for successfully built capabilities)
CREATE TABLE IF NOT EXISTS capability_ghosts (
    id               VARCHAR(36) PRIMARY KEY,
    workspace_id     VARCHAR(36) NOT NULL,
    fingerprint      VARCHAR(255) NOT NULL,
    revision         INTEGER      NOT NULL,
    manifest         JSONB        NOT NULL DEFAULT '{}',
    artifact_pointer VARCHAR(1024) NOT NULL DEFAULT '',
    evidence_pointer VARCHAR(1024) NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_capability_ghosts_workspace_id
    ON capability_ghosts (workspace_id);

CREATE INDEX IF NOT EXISTS ix_capability_ghosts_fingerprint
    ON capability_ghosts (fingerprint);
