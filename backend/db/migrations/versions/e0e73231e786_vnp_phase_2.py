"""vnp phase 2

Revision ID: e0e73231e786
Revises: 
Create Date: 2026-06-23 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e0e73231e786'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ENUM Types
    op.execute("CREATE TYPE tenant_type AS ENUM ('provider', 'customer', 'validator', 'operator');")
    op.execute("CREATE TYPE api_status AS ENUM ('active', 'degraded', 'disabled', 'pending');")
    op.execute("CREATE TYPE probe_result_state AS ENUM ('success', 'timeout', 'http_error', 'transport_error', 'dns_error', 'tls_error');")
    op.execute("CREATE TYPE incident_state AS ENUM ('open', 'acknowledged', 'resolved', 'suppressed');")
    op.execute("CREATE TYPE ledger_entry_type AS ENUM ('credit', 'debit', 'hold', 'release', 'refund', 'adjustment', 'slash', 'reward');")
    op.execute("CREATE TYPE settlement_state AS ENUM ('pending', 'posted', 'failed', 'reversed');")
    op.execute("CREATE TYPE validator_state AS ENUM ('active', 'suspended', 'challenged', 'retired');")
    op.execute("CREATE TYPE attestation_state AS ENUM ('proposed', 'accepted', 'rejected');")

    # 2. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # 3. Drop old VNP tables if they exist to replace them with the rigorous schema
    op.execute("DROP TABLE IF EXISTS vnp_audit_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_billing_usage CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_probe_metrics CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_validators CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_monitored_apis CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_accounts CASCADE;")

    # 4. Tables
    op.execute("""
    CREATE TABLE vnp_providers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        slug VARCHAR(100) UNIQUE NOT NULL,
        legal_name VARCHAR(255) NOT NULL,
        support_email VARCHAR(255),
        billing_email VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_apis (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id UUID NOT NULL REFERENCES vnp_providers(id) ON DELETE CASCADE,
        api_did VARCHAR(200) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        version VARCHAR(64) NOT NULL,
        base_url TEXT NOT NULL,
        health_path TEXT NOT NULL DEFAULT '/health',
        auth_scheme VARCHAR(50) NOT NULL,
        x402_ready BOOLEAN NOT NULL DEFAULT FALSE,
        pricing_model VARCHAR(50) NOT NULL DEFAULT 'metered',
        status api_status NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_api_regions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        api_id UUID NOT NULL REFERENCES vnp_apis(id) ON DELETE CASCADE,
        region_code VARCHAR(50) NOT NULL,
        endpoint_url TEXT NOT NULL,
        priority INT NOT NULL DEFAULT 100,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(api_id, region_code)
    );
    """)

    op.execute("""
    CREATE TABLE vnp_customers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        billing_mode VARCHAR(50) NOT NULL,
        currency CHAR(3) NOT NULL DEFAULT 'USD',
        stripe_customer_id VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_projects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        customer_id UUID NOT NULL REFERENCES vnp_customers(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        environment VARCHAR(50) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(customer_id, name, environment)
    );
    """)

    op.execute("""
    CREATE TABLE vnp_sdk_credentials (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES vnp_projects(id) ON DELETE CASCADE,
        label VARCHAR(255) NOT NULL,
        api_key_hash TEXT NOT NULL,
        public_key TEXT NOT NULL,
        scopes JSONB NOT NULL,
        expires_at TIMESTAMPTZ,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_route_policies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        customer_id UUID NOT NULL REFERENCES vnp_customers(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        max_p99_latency_ms INT,
        minimum_trust_score NUMERIC(5,2),
        allowed_regions JSONB NOT NULL DEFAULT '[]'::jsonb,
        allowed_provider_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
        weights JSONB NOT NULL,
        failover_mode VARCHAR(50) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_probe_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id VARCHAR(100) UNIQUE NOT NULL,
        worker_id VARCHAR(100) NOT NULL,
        worker_region VARCHAR(50) NOT NULL,
        runtime VARCHAR(50) NOT NULL,
        api_id UUID NOT NULL REFERENCES vnp_apis(id) ON DELETE CASCADE,
        api_region_code VARCHAR(50) NOT NULL,
        endpoint_url TEXT NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL,
        dns_ms INT,
        connect_ms INT,
        tls_ms INT,
        ttfb_ms INT,
        total_ms INT NOT NULL,
        status_code INT,
        result_state probe_result_state NOT NULL,
        success BOOLEAN NOT NULL,
        timeout BOOLEAN NOT NULL DEFAULT FALSE,
        error_class VARCHAR(100),
        signature_alg VARCHAR(20) NOT NULL,
        signature_key_id VARCHAR(100) NOT NULL,
        signature_value TEXT NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_regional_telemetry (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        api_id UUID NOT NULL REFERENCES vnp_apis(id) ON DELETE CASCADE,
        region_code VARCHAR(50) NOT NULL,
        window_start TIMESTAMPTZ NOT NULL,
        window_end TIMESTAMPTZ NOT NULL,
        sample_count INT NOT NULL,
        success_count INT NOT NULL,
        p50_latency_ms INT NOT NULL,
        p95_latency_ms INT NOT NULL,
        p99_latency_ms INT NOT NULL,
        error_rate_percent NUMERIC(5,2) NOT NULL,
        uptime_percent NUMERIC(5,2) NOT NULL,
        throughput_rps INT NOT NULL DEFAULT 0,
        trust_score NUMERIC(5,2) NOT NULL,
        measured_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_route_snapshots (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        customer_id UUID REFERENCES vnp_customers(id) ON DELETE SET NULL,
        policy_id UUID REFERENCES vnp_route_policies(id) ON DELETE SET NULL,
        requested_region VARCHAR(50),
        generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        ttl_seconds INT NOT NULL,
        snapshot JSONB NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE vnp_usage_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id VARCHAR(100) UNIQUE NOT NULL,
        customer_id UUID NOT NULL REFERENCES vnp_customers(id) ON DELETE CASCADE,
        project_id UUID NOT NULL REFERENCES vnp_projects(id) ON DELETE CASCADE,
        credential_id UUID NOT NULL REFERENCES vnp_sdk_credentials(id) ON DELETE CASCADE,
        policy_id UUID REFERENCES vnp_route_policies(id) ON DELETE SET NULL,
        request_id VARCHAR(100) NOT NULL,
        api_id UUID NOT NULL REFERENCES vnp_apis(id) ON DELETE CASCADE,
        provider_id UUID NOT NULL REFERENCES vnp_providers(id) ON DELETE CASCADE,
        provider_region VARCHAR(50) NOT NULL,
        sdk_region VARCHAR(50),
        route_snapshot_id UUID REFERENCES vnp_route_snapshots(id) ON DELETE SET NULL,
        billable_units BIGINT NOT NULL,
        unit_type VARCHAR(50) NOT NULL,
        success BOOLEAN NOT NULL,
        response_ms INT,
        http_status INT,
        retry_count INT NOT NULL DEFAULT 0,
        failover_count INT NOT NULL DEFAULT 0,
        preauth_amount_minor BIGINT,
        final_amount_minor BIGINT,
        currency CHAR(3) NOT NULL DEFAULT 'USD',
        occurred_at TIMESTAMPTZ NOT NULL,
        signature_alg VARCHAR(20) NOT NULL,
        signature_key_id VARCHAR(100) NOT NULL,
        signature_value TEXT NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_prepaid_balances (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        customer_id UUID NOT NULL REFERENCES vnp_customers(id) ON DELETE CASCADE,
        currency CHAR(3) NOT NULL,
        available_amount_minor BIGINT NOT NULL DEFAULT 0,
        reserved_amount_minor BIGINT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(customer_id, currency)
    );
    """)

    op.execute("""
    CREATE TABLE vnp_settlement_entries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        customer_id UUID REFERENCES vnp_customers(id) ON DELETE SET NULL,
        provider_id UUID REFERENCES vnp_providers(id) ON DELETE SET NULL,
        usage_event_id UUID REFERENCES vnp_usage_events(id) ON DELETE SET NULL,
        entry_type ledger_entry_type NOT NULL,
        amount_minor BIGINT NOT NULL,
        currency CHAR(3) NOT NULL,
        state settlement_state NOT NULL DEFAULT 'posted',
        reference_code VARCHAR(100),
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_validators (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        display_name VARCHAR(255) NOT NULL,
        operator_entity VARCHAR(255) NOT NULL,
        public_key TEXT NOT NULL,
        stake_currency CHAR(3) NOT NULL,
        stake_amount_minor BIGINT NOT NULL,
        state validator_state NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_attestations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        validator_id UUID NOT NULL REFERENCES vnp_validators(id) ON DELETE CASCADE,
        incident_id UUID,
        attestation_window_start TIMESTAMPTZ NOT NULL,
        attestation_window_end TIMESTAMPTZ NOT NULL,
        state attestation_state NOT NULL,
        payload JSONB NOT NULL,
        signature_value TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE vnp_incidents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        scope_type VARCHAR(50) NOT NULL,
        scope_id UUID,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        state incident_state NOT NULL DEFAULT 'open',
        severity VARCHAR(20) NOT NULL,
        opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        acknowledged_at TIMESTAMPTZ,
        resolved_at TIMESTAMPTZ
    );
    """)

    op.execute("""
    CREATE TABLE vnp_audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        actor_type tenant_type NOT NULL,
        actor_id UUID,
        action VARCHAR(100) NOT NULL,
        scope_type VARCHAR(50) NOT NULL,
        scope_id UUID,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    # 5. Indexes
    op.execute("CREATE INDEX idx_api_regions_lookup ON vnp_api_regions(api_id, region_code) WHERE active = TRUE;")
    op.execute("CREATE INDEX idx_probe_events_api_region_time ON vnp_probe_events(api_id, api_region_code, occurred_at DESC);")
    op.execute("CREATE INDEX idx_regional_telemetry_region_score ON vnp_regional_telemetry(region_code, trust_score DESC, p99_latency_ms ASC);")
    op.execute("CREATE INDEX idx_usage_events_customer_time ON vnp_usage_events(customer_id, occurred_at DESC);")
    op.execute("CREATE INDEX idx_usage_events_project_time ON vnp_usage_events(project_id, occurred_at DESC);")
    op.execute("CREATE INDEX idx_settlement_entries_customer_time ON vnp_settlement_entries(customer_id, created_at DESC);")
    op.execute("CREATE INDEX idx_route_snapshots_generated_at ON vnp_route_snapshots(generated_at DESC);")
    op.execute("CREATE INDEX idx_incidents_state_opened ON vnp_incidents(state, opened_at DESC);")
    op.execute("CREATE INDEX idx_audit_logs_scope_time ON vnp_audit_logs(scope_type, scope_id, created_at DESC);")


def downgrade() -> None:
    # Drop Indexes implicitly handled by dropping tables
    # Drop Tables
    op.execute("DROP TABLE IF EXISTS vnp_audit_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_incidents CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_attestations CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_validators CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_settlement_entries CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_prepaid_balances CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_usage_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_route_snapshots CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_regional_telemetry CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_probe_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_route_policies CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_sdk_credentials CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_projects CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_customers CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_api_regions CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_apis CASCADE;")
    op.execute("DROP TABLE IF EXISTS vnp_providers CASCADE;")

    # Drop Enums
    op.execute("DROP TYPE IF EXISTS attestation_state;")
    op.execute("DROP TYPE IF EXISTS validator_state;")
    op.execute("DROP TYPE IF EXISTS settlement_state;")
    op.execute("DROP TYPE IF EXISTS ledger_entry_type;")
    op.execute("DROP TYPE IF EXISTS incident_state;")
    op.execute("DROP TYPE IF EXISTS probe_result_state;")
    op.execute("DROP TYPE IF EXISTS api_status;")
    op.execute("DROP TYPE IF EXISTS tenant_type;")
