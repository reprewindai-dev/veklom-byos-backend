
-- Enable RLS for all tables with a workspace_id column
-- Note: FORCE ROW LEVEL SECURITY ensures table owners/superusers (like the app db role) are also restricted by policies

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_users ON users;
CREATE POLICY tenant_isolation_users ON users
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_api_keys ON api_keys;
CREATE POLICY tenant_isolation_api_keys ON api_keys
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_assets ON assets;
CREATE POLICY tenant_isolation_assets ON assets
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_workspace_members ON workspace_members;
CREATE POLICY tenant_isolation_workspace_members ON workspace_members
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE model_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_configs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_model_configs ON model_configs;
CREATE POLICY tenant_isolation_model_configs ON model_configs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE workspace_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_integrations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_workspace_integrations ON workspace_integrations;
CREATE POLICY tenant_isolation_workspace_integrations ON workspace_integrations
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE workspace_plugins ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_plugins FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_workspace_plugins ON workspace_plugins;
CREATE POLICY tenant_isolation_workspace_plugins ON workspace_plugins
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_execution_logs ON execution_logs;
CREATE POLICY tenant_isolation_execution_logs ON execution_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE ai_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_audit_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_ai_audit_logs ON ai_audit_logs;
CREATE POLICY tenant_isolation_ai_audit_logs ON ai_audit_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE cost_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_predictions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_cost_predictions ON cost_predictions;
CREATE POLICY tenant_isolation_cost_predictions ON cost_predictions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE routing_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE routing_decisions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_routing_decisions ON routing_decisions;
CREATE POLICY tenant_isolation_routing_decisions ON routing_decisions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE cost_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_allocations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_cost_allocations ON cost_allocations;
CREATE POLICY tenant_isolation_cost_allocations ON cost_allocations
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_budgets ON budgets;
CREATE POLICY tenant_isolation_budgets ON budgets
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE routing_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE routing_policies FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_routing_policies ON routing_policies;
CREATE POLICY tenant_isolation_routing_policies ON routing_policies
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE content_filter_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_filter_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_content_filter_logs ON content_filter_logs;
CREATE POLICY tenant_isolation_content_filter_logs ON content_filter_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE abuse_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE abuse_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_abuse_logs ON abuse_logs;
CREATE POLICY tenant_isolation_abuse_logs ON abuse_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE incident_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE incident_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_incident_logs ON incident_logs;
CREATE POLICY tenant_isolation_incident_logs ON incident_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE forecast_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_models FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_forecast_models ON forecast_models;
CREATE POLICY tenant_isolation_forecast_models ON forecast_models
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE chain_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_definitions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_chain_definitions ON chain_definitions;
CREATE POLICY tenant_isolation_chain_definitions ON chain_definitions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE chain_run_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_run_records FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_chain_run_records ON chain_run_records;
CREATE POLICY tenant_isolation_chain_run_records ON chain_run_records
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE wallet_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_transactions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_wallet_transactions ON wallet_transactions;
CREATE POLICY tenant_isolation_wallet_transactions ON wallet_transactions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_subscriptions ON subscriptions;
CREATE POLICY tenant_isolation_subscriptions ON subscriptions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE budget_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_rules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_budget_rules ON budget_rules;
CREATE POLICY tenant_isolation_budget_rules ON budget_rules
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_invoices ON invoices;
CREATE POLICY tenant_isolation_invoices ON invoices
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_payments ON payments;
CREATE POLICY tenant_isolation_payments ON payments
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_orders ON orders;
CREATE POLICY tenant_isolation_orders ON orders
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs;
CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_security_events ON security_events;
CREATE POLICY tenant_isolation_security_events ON security_events
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE compliance_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_compliance_checks ON compliance_checks;
CREATE POLICY tenant_isolation_compliance_checks ON compliance_checks
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE kill_switch_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE kill_switch_states FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_kill_switch_states ON kill_switch_states;
CREATE POLICY tenant_isolation_kill_switch_states ON kill_switch_states
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE vnp_stake_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE vnp_stake_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_vnp_stake_logs ON vnp_stake_logs;
CREATE POLICY tenant_isolation_vnp_stake_logs ON vnp_stake_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipelines FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pipelines ON pipelines;
CREATE POLICY tenant_isolation_pipelines ON pipelines
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pipeline_runs ON pipeline_runs;
CREATE POLICY tenant_isolation_pipeline_runs ON pipeline_runs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deployments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_deployments ON deployments;
CREATE POLICY tenant_isolation_deployments ON deployments
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pgl_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgl_certificates FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pgl_certificates ON pgl_certificates;
CREATE POLICY tenant_isolation_pgl_certificates ON pgl_certificates
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pgl_ledger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgl_ledger_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pgl_ledger_events ON pgl_ledger_events;
CREATE POLICY tenant_isolation_pgl_ledger_events ON pgl_ledger_events
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pgl_anchors ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgl_anchors FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pgl_anchors ON pgl_anchors;
CREATE POLICY tenant_isolation_pgl_anchors ON pgl_anchors
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE execution_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_identities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_execution_identities ON execution_identities;
CREATE POLICY tenant_isolation_execution_identities ON execution_identities
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_states FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_agent_states ON agent_states;
CREATE POLICY tenant_isolation_agent_states ON agent_states
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE agent_memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_memory_entries FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_agent_memory_entries ON agent_memory_entries;
CREATE POLICY tenant_isolation_agent_memory_entries ON agent_memory_entries
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_notifications ON notifications;
CREATE POLICY tenant_isolation_notifications ON notifications
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE provider_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_keys FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_provider_keys ON provider_keys;
CREATE POLICY tenant_isolation_provider_keys ON provider_keys
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE provider_routing_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_routing_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_provider_routing_logs ON provider_routing_logs;
CREATE POLICY tenant_isolation_provider_routing_logs ON provider_routing_logs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE playground_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playground_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_playground_sessions ON playground_sessions;
CREATE POLICY tenant_isolation_playground_sessions ON playground_sessions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE playground_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE playground_prompts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_playground_prompts ON playground_prompts;
CREATE POLICY tenant_isolation_playground_prompts ON playground_prompts
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE repo_risk_gate_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE repo_risk_gate_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_repo_risk_gate_runs ON repo_risk_gate_runs;
CREATE POLICY tenant_isolation_repo_risk_gate_runs ON repo_risk_gate_runs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE decision_frames ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_frames FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_decision_frames ON decision_frames;
CREATE POLICY tenant_isolation_decision_frames ON decision_frames
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE veklom_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE veklom_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_veklom_runs ON veklom_runs;
CREATE POLICY tenant_isolation_veklom_runs ON veklom_runs
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE tier_upgrades ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_upgrades FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_tier_upgrades ON tier_upgrades;
CREATE POLICY tenant_isolation_tier_upgrades ON tier_upgrades
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_metrics FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_usage_metrics ON usage_metrics;
CREATE POLICY tenant_isolation_usage_metrics ON usage_metrics
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE pricing_billing_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_billing_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_pricing_billing_events ON pricing_billing_events;
CREATE POLICY tenant_isolation_pricing_billing_events ON pricing_billing_events
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE rag_agent_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_agent_memory FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_rag_agent_memory ON rag_agent_memory;
CREATE POLICY tenant_isolation_rag_agent_memory ON rag_agent_memory
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE rag_document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_document_chunks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_rag_document_chunks ON rag_document_chunks;
CREATE POLICY tenant_isolation_rag_document_chunks ON rag_document_chunks
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE quarantined_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE quarantined_intents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_quarantined_intents ON quarantined_intents;
CREATE POLICY tenant_isolation_quarantined_intents ON quarantined_intents
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

ALTER TABLE veklom_agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE veklom_agent_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_veklom_agent_sessions ON veklom_agent_sessions;
CREATE POLICY tenant_isolation_veklom_agent_sessions ON veklom_agent_sessions
    USING (workspace_id = current_setting('app.workspace_id', TRUE));

