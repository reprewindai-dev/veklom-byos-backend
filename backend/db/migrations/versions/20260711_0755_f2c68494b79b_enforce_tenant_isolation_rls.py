"""enforce_tenant_isolation_rls

Revision ID: f2c68494b79b
Revises: e1f84351b689
Create Date: 2026-07-11 07:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2c68494b79b'
down_revision: Union[str, None] = 'e1f84351b689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = [
    'abuse_logs', 'agent_evaluations', 'agent_executions', 'agent_guardrails', 
    'agent_memories', 'agent_memory_entries', 'agent_states', 'agent_swarms', 
    'agent_traces', 'agents', 'ai_audit_logs', 'alert_rules', 'alerts', 
    'api_keys', 'assets', 'audit_logs', 'authority_bundles', 'authority_runs', 
    'browser_actions', 'budget_rules', 'budgets', 'chain_definitions', 
    'chain_run_records', 'compliance_checks', 'content_filter_logs', 
    'conversation_contexts', 'cost_allocations', 'cost_predictions', 
    'decision_frames', 'deployments', 'evidence_packs', 
    'execution_logs', 'forecast_models', 'governed_runs', 'incident_logs', 
    'invoices', 'kill_switch_states', 'knowledge_sources', 'knowledge_templates', 
    'llm_routers', 'mcp_connections', 'mcp_tools', 'memory_entries', 'metrics', 
    'model_configs', 'notifications', 'orders', 'payments', 'performance_logs', 
    'pgl_certificates', 'pgl_ledger_events', 'pipeline_runs', 'pipelines', 
    'playground_prompts', 'playground_sessions', 'pricing_billing_events', 
    'provider_keys', 'provider_routing_logs', 'quarantined_intents', 
    'rag_agent_memory', 'rag_document_chunks', 'repo_risk_gate_runs', 
    'resource_usage', 'routing_decisions', 'routing_policies', 
    'safety_incidents', 'security_events', 'subscriptions', 'tier_upgrades', 
    'usage_metrics', 'users', 'veklom_agent_sessions', 'veklom_runs', 
    'vnp_stake_logs', 'wallet_transactions', 'workspace_integrations', 
    'workspace_members', 'workspace_plugins'
]

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in TENANT_TABLES:
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "workspace_id" not in columns:
            continue
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name};")
        op.execute(f"""
        CREATE POLICY tenant_isolation ON {table_name}
        USING (
          workspace_id::text = current_setting('app.workspace_id', true)
        )
        WITH CHECK (
          workspace_id::text = current_setting('app.workspace_id', true)
        );
        """)

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in TENANT_TABLES:
        if not inspector.has_table(table_name):
            continue
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name};")
        op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")
