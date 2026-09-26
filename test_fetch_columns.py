from sqlalchemy import select
from backend.db.models.ai import ModelConfig, ExecutionLog
from backend.db.models.audit import AuditLog
from backend.db.models.security import SecurityEvent

print(select(ModelConfig.id, ModelConfig.provider, ModelConfig.display_name))
print(select(ExecutionLog.id, ExecutionLog.model, ExecutionLog.provider, ExecutionLog.latency_ms, ExecutionLog.total_tokens, ExecutionLog.cost_usd, ExecutionLog.policy_flags, ExecutionLog.created_at))
print(select(AuditLog.id, AuditLog.action, AuditLog.resource_type, AuditLog.resource_id, AuditLog.user_id, AuditLog.hash_chain, AuditLog.prev_hash, AuditLog.created_at))
print(select(SecurityEvent.id, SecurityEvent.description, SecurityEvent.event_type, SecurityEvent.severity, SecurityEvent.threat_type, SecurityEvent.created_at))
