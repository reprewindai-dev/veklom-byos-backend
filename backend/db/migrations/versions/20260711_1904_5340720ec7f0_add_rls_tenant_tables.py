"""add_rls_tenant_tables

Revision ID: 5340720ec7f0
Revises: fa72be9b2ba0
Create Date: 2026-07-11 19:04:39.029843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5340720ec7f0'
down_revision: Union[str, None] = 'fa72be9b2ba0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tenant_tables = [
        'abuse_logs', 'age_verifications', 'agent_evaluations', 'agent_executions', 'agent_guardrails', 'agent_memories', 'agent_memory_entries', 'agent_states', 'agent_swarms', 'agent_traces', 'agents', 'ai_audit_logs', 'alert_rules', 'alerts', 'api_keys', 'assets', 'audit_logs', 'authority_bundles', 'authority_decisions', 'authority_runs', 'browser_actions', 'budget_rules', 'budgets', 'chain_definitions', 'chain_run_records', 'compliance_checks', 'content_filter_logs', 'conversation_contexts', 'cost_allocations', 'cost_predictions', 'decision_frames', 'deployments', 'evidence_packs', 'execution_identities', 'execution_logs', 'forecast_models', 'governed_runs', 'incident_logs', 'invoices', 'kill_switch_states', 'knowledge_chunks', 'knowledge_sources', 'knowledge_templates', 'ledger', 'llm_routers', 'mcp_connections', 'mcp_tools', 'memory_entries', 'metrics', 'model_configs', 'notifications', 'orders', 'payments', 'performance_logs', 'pgl_anchors', 'pgl_certificates', 'pgl_identities', 'pgl_ledger_events', 'pipeline_runs', 'pipelines', 'playground_prompts', 'playground_sessions', 'pricing_billing_events', 'pricing_tiers', 'provider_decision_audit_logs', 'provider_keys', 'provider_routing_logs', 'quarantined_intents', 'rag_agent_memory', 'rag_document_chunks', 'recon_findings', 'resource_usage', 'routing_decisions', 'routing_policies', 'safety_incidents', 'security_events', 'sessions', 'subscriptions', 'system_health', 'tier_features', 'tier_upgrades', 'tool_definitions', 'usage_metrics', 'users', 'veklom_agent_sessions', 'veklom_ledger_entries', 'veklom_mesh_incidents', 'veklom_runs', 'veklom_session_transitions', 'vnp_alert_configs', 'vnp_api_regions', 'vnp_apis', 'vnp_attestations', 'vnp_audit_logs', 'vnp_claim_requests', 'vnp_claimed_apis', 'vnp_customers', 'vnp_incidents', 'vnp_metrics_realtime', 'vnp_prepaid_balances', 'vnp_probe_events', 'vnp_projects', 'vnp_providers', 'vnp_regional_telemetry', 'vnp_route_policies', 'vnp_route_snapshots', 'vnp_sdk_credentials', 'vnp_settlement_entries', 'vnp_stake_logs', 'vnp_usage_events', 'vnp_validators', 'wallet_transactions', 'webhook_dead_letter', 'webhook_receipts', 'workspace_integrations', 'workspace_members', 'workspace_plugins', 'workspace_provider_credentials'
    ]

    from sqlalchemy.engine import reflection
    from sqlalchemy.exc import NoSuchTableError
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)

    for table in tenant_tables:
        try:
            columns = [c['name'] for c in inspector.get_columns(table)]
        except NoSuchTableError:
            continue
            
        if 'workspace_id' not in columns:
            continue
            
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        
        # Policy: Only allow access if workspace_id matches current_setting('app.workspace_id', true)
        # We also allow access if app.bypass_rls is 'on' for background tasks / super users.
        policy_sql = f"""
        CREATE POLICY tenant_isolation_policy ON {table}
        AS PERMISSIVE FOR ALL
        USING (
            current_setting('app.bypass_rls', true) = 'on'
            OR workspace_id::text = current_setting('app.workspace_id', true)
        )
        WITH CHECK (
            current_setting('app.bypass_rls', true) = 'on'
            OR workspace_id::text = current_setting('app.workspace_id', true)
        );
        """
        op.execute(policy_sql)

def downgrade() -> None:
    tenant_tables = [
        'abuse_logs', 'age_verifications', 'agent_evaluations', 'agent_executions', 'agent_guardrails', 'agent_memories', 'agent_memory_entries', 'agent_states', 'agent_swarms', 'agent_traces', 'agents', 'ai_audit_logs', 'alert_rules', 'alerts', 'api_keys', 'assets', 'audit_logs', 'authority_bundles', 'authority_decisions', 'authority_runs', 'browser_actions', 'budget_rules', 'budgets', 'chain_definitions', 'chain_run_records', 'compliance_checks', 'content_filter_logs', 'conversation_contexts', 'cost_allocations', 'cost_predictions', 'decision_frames', 'deployments', 'evidence_packs', 'execution_identities', 'execution_logs', 'forecast_models', 'governed_runs', 'incident_logs', 'invoices', 'kill_switch_states', 'knowledge_chunks', 'knowledge_sources', 'knowledge_templates', 'ledger', 'llm_routers', 'mcp_connections', 'mcp_tools', 'memory_entries', 'metrics', 'model_configs', 'notifications', 'orders', 'payments', 'performance_logs', 'pgl_anchors', 'pgl_certificates', 'pgl_identities', 'pgl_ledger_events', 'pipeline_runs', 'pipelines', 'playground_prompts', 'playground_sessions', 'pricing_billing_events', 'pricing_tiers', 'provider_decision_audit_logs', 'provider_keys', 'provider_routing_logs', 'quarantined_intents', 'rag_agent_memory', 'rag_document_chunks', 'recon_findings', 'resource_usage', 'routing_decisions', 'routing_policies', 'safety_incidents', 'security_events', 'sessions', 'subscriptions', 'system_health', 'tier_features', 'tier_upgrades', 'tool_definitions', 'usage_metrics', 'users', 'veklom_agent_sessions', 'veklom_ledger_entries', 'veklom_mesh_incidents', 'veklom_runs', 'veklom_session_transitions', 'vnp_alert_configs', 'vnp_api_regions', 'vnp_apis', 'vnp_attestations', 'vnp_audit_logs', 'vnp_claim_requests', 'vnp_claimed_apis', 'vnp_customers', 'vnp_incidents', 'vnp_metrics_realtime', 'vnp_prepaid_balances', 'vnp_probe_events', 'vnp_projects', 'vnp_providers', 'vnp_regional_telemetry', 'vnp_route_policies', 'vnp_route_snapshots', 'vnp_sdk_credentials', 'vnp_settlement_entries', 'vnp_stake_logs', 'vnp_usage_events', 'vnp_validators', 'wallet_transactions', 'webhook_dead_letter', 'webhook_receipts', 'workspace_integrations', 'workspace_members', 'workspace_plugins', 'workspace_provider_credentials'
    ]

    for table in tenant_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
