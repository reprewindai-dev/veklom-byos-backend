"""Provider key management and routing audit models."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class ProviderKey(Base):
    """Tenant-scoped encrypted provider API keys (BYOK).

    Keys are stored encrypted with Fernet (AES-128-CBC + HMAC).
    Raw key values NEVER appear in logs or API responses.

    Role rules:
      - OWNER / ADMIN role (is_founder_tenant=True): can see/use all owner-configured keys
      - Customer tenants: can only use their own BYOK keys or Ollama (default)
    """
    __tablename__ = "provider_keys"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    provider = Column(String(64), nullable=False)          # ollama|groq|openai|gemini|huggingface|anthropic
    label = Column(String(128), default="")                # human name e.g. "My Groq Key"
    key_encrypted = Column(Text, nullable=False)            # Fernet-encrypted ciphertext
    key_prefix = Column(String(16), default="")             # first 6 chars for UI display only
    extra_config = Column(JSON, default=dict)               # e.g. {"base_url": "...", "model": "..."}

    is_active = Column(Boolean, default=True)
    is_founder_key = Column(Boolean, default=False)        # True = owner-configured, never shown to customers
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ProviderRoutingLog(Base):
    """Audit log for every provider selection decision.

    Records WHY Ollama was used vs why escalation happened,
    which keys were selected, and the outcome.
    """
    __tablename__ = "provider_routing_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), default="", index=True)
    user_id = Column(String(36), default="", index=True)
    exec_log_id = Column(String(36), default="", index=True)  # FK to exec_logs.id

    provider_selected = Column(String(64), default="ollama")
    model_selected = Column(String(128), default="")
    escalated = Column(Boolean, default=False)           # True = moved beyond Ollama
    escalation_reason = Column(String(256), default="")  # e.g. "tool_support_required"
    provider_chain_tried = Column(JSON, default=list)    # ordered list of providers attempted
    key_source = Column(String(32), default="owner")     # owner|byok|default
    key_id = Column(String(36), default="")              # ProviderKey.id if BYOK
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_detail = Column(Text, default="")
    request_metadata = Column(JSON, default=dict)        # model hint, context size, tool_calls, etc.
    created_at = Column(DateTime(timezone=True), default=_utcnow)
