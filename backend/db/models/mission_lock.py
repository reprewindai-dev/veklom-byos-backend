"""SQLAlchemy models for the Veklom Mission Lock system."""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import TypeDecorator

from backend.core.database.database import Base
from backend.core.config.settings import settings

db_url = settings.DATABASE_URL or ""
SCHEMA_NAME = "mission_lock" if "sqlite" not in db_url else None

def _uuid():
    return str(uuid.uuid4())

def _utcnow():
    return datetime.now(timezone.utc)


class TextArray(TypeDecorator):
    """Platform-independent Text Array type.
    Uses PostgreSQL native ARRAY(String) if on Postgres, falls back to JSON-serialized String/Text on SQLite.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if dialect.name == 'postgresql':
            return value
        else:
            try:
                return json.loads(value)
            except Exception:
                return []


class MissionDNA(Base):
    """1. Mission DNA: per-agent behavioral profile (immutable, auditable)."""
    __tablename__ = "mission_dna"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_mission_dna_agent_id", "agent_id"),
            Index("idx_mission_dna_tenant", "tenant_id"),
            Index("idx_mission_dna_role", "role"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_mission_dna_agent_id", "agent_id"),
            Index("idx_mission_dna_tenant", "tenant_id"),
            Index("idx_mission_dna_role", "role"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), unique=True, nullable=False)
    role = Column(String(64), nullable=False)
    dominance = Column(Float, default=0.85)
    plasticity = Column(Float, default=0.01)
    base_learning_rate = Column(Float, default=0.08)
    epsilon = Column(Float, default=0.02)
    mission_bonus = Column(Float, default=1.0)
    off_path_penalty = Column(Float, default=0.15)
    coordination_weight = Column(Float, default=0.5)
    safety_weight = Column(Float, default=1.0)
    cue_boost = Column(Float, default=0.10)
    min_dominance = Column(Float, default=0.50)
    max_epsilon = Column(Float, default=0.15)
    max_plasticity = Column(Float, default=0.05)
    allowed_actions = Column(TextArray, nullable=True)
    forbidden_actions = Column(TextArray, default=list)
    tenant_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    locked = Column(Boolean, default=False)
    version = Column(Integer, default=1)

    # Relationships
    missions = relationship("AgentMission", back_populates="dna", cascade="all, delete-orphan")
    state = relationship("MissionLockAgentState", back_populates="dna", uselist=False, cascade="all, delete-orphan")
    telemetries = relationship("EpisodeTelemetry", back_populates="dna", cascade="all, delete-orphan")
    recovery_events = relationship("RecoveryEvent", back_populates="dna", cascade="all, delete-orphan")
    runtime_state = relationship("AgentRuntimeState", back_populates="dna", uselist=False, cascade="all, delete-orphan")
    action_traces = relationship("AgentActionTrace", back_populates="dna", cascade="all, delete-orphan")
    recovery_snapshots = relationship("RecoverySnapshot", back_populates="dna", cascade="all, delete-orphan")


class AgentMission(Base):
    """2. Mission paths: the desired behavioral trajectory per agent."""
    __tablename__ = "agent_missions"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_agent_missions_agent_id", "agent_id"),
            Index("idx_agent_missions_tenant", "tenant_id"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_agent_missions_agent_id", "agent_id"),
            Index("idx_agent_missions_tenant", "tenant_id"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), unique=True, nullable=False)
    mission_name = Column(String(256), nullable=False)
    preferred_transitions = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    tenant_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # Relationship
    dna = relationship("MissionDNA", back_populates="missions")


class MissionLockAgentState(Base):
    """3. Agent state: runtime behavioral metrics (frequently updated)."""
    __tablename__ = "agent_state"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_agent_state_agent_id", "agent_id"),
            Index("idx_agent_state_last_update", "last_update"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_agent_state_agent_id", "agent_id"),
            Index("idx_agent_state_last_update", "last_update"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), unique=True, nullable=False)
    current_dominance = Column(Float, default=0.85)
    current_plasticity = Column(Float, default=0.01)
    current_epsilon = Column(Float, default=0.02)
    target_return = Column(Float, nullable=True)
    last_episode_return = Column(Float, default=0.0)
    moving_avg_return = Column(Float, default=0.0)
    path_conformance = Column(Float, default=0.0)
    steps_since_recovery = Column(Integer, default=0)
    safety_violations = Column(Integer, default=0)
    last_action = Column(String(256), nullable=True)
    last_state = Column(String(256), nullable=True)
    last_update = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationship
    dna = relationship("MissionDNA", back_populates="state")


class EpisodeTelemetry(Base):
    """4. Episode telemetry: per-episode performance and behavior."""
    __tablename__ = "episode_telemetry"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_episode_telemetry_agent_episode", "agent_id", "episode_num"),
            Index("idx_episode_telemetry_timestamp", "timestamp"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_episode_telemetry_agent_episode", "agent_id", "episode_num"),
            Index("idx_episode_telemetry_timestamp", "timestamp"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), nullable=False)
    episode_num = Column(Integer, nullable=False)
    episode_return = Column(Float, nullable=False)
    path_actions = Column(Integer, default=0)
    off_path_actions = Column(Integer, default=0)
    path_conformance = Column(Float, default=0.0)
    safety_events = Column(Integer, default=0)
    steps = Column(Integer, default=0)
    recovery_triggered = Column(Boolean, default=False)
    dominance_at_episode = Column(Float, nullable=True)
    epsilon_at_episode = Column(Float, nullable=True)
    plasticity_at_episode = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    tenant_id = Column(String(128), nullable=True)

    # Relationship
    dna = relationship("MissionDNA", back_populates="telemetries")


class TeamState(Base):
    """5. Team coordination state: multi-agent orchestration."""
    __tablename__ = "team_state"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_team_state_team_id", "team_id"),
            Index("idx_team_state_last_update", "last_update"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_team_state_team_id", "team_id"),
            Index("idx_team_state_last_update", "last_update"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    team_id = Column(String(128), nullable=False)
    phase = Column(String(64), nullable=True)
    alerts = Column(TextArray, default=list)
    shared_goal_progress = Column(Float, default=0.0)
    last_joint_actions = Column(JSON, nullable=True)
    last_update = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    tenant_id = Column(String(128), nullable=True)


class CoordinationLog(Base):
    """6. Coordination decisions: audit trail for team actions."""
    __tablename__ = "coordination_log"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_coordination_log_team_episode", "team_id", "episode_num"),
            Index("idx_coordination_log_timestamp", "timestamp"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_coordination_log_team_episode", "team_id", "episode_num"),
            Index("idx_coordination_log_timestamp", "timestamp"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    team_id = Column(String(128), nullable=False)
    episode_num = Column(Integer, nullable=True)
    state = Column(String(256), nullable=True)
    coordinated_actions = Column(JSON, nullable=False)
    local_rewards = Column(JSON, nullable=True)
    coordination_bonuses = Column(JSON, nullable=True)
    safety_penalties = Column(JSON, nullable=True)
    net_rewards = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    tenant_id = Column(String(128), nullable=True)


class RecoveryEvent(Base):
    """7. Recovery history: when and why plasticity was increased."""
    __tablename__ = "recovery_events"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_recovery_events_agent", "agent_id", "timestamp"),
            Index("idx_recovery_events_trigger", "trigger"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_recovery_events_agent", "agent_id", "timestamp"),
            Index("idx_recovery_events_trigger", "trigger"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), nullable=False)
    episode_num = Column(Integer, nullable=True)
    trigger = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    dominance_before = Column(Float, nullable=True)
    dominance_after = Column(Float, nullable=True)
    epsilon_before = Column(Float, nullable=True)
    epsilon_after = Column(Float, nullable=True)
    plasticity_before = Column(Float, nullable=True)
    plasticity_after = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    tenant_id = Column(String(128), nullable=True)

    # Relationships
    dna = relationship("MissionDNA", back_populates="recovery_events")
    snapshots = relationship("RecoverySnapshot", back_populates="recovery_event", cascade="all, delete-orphan")


class DNAAudit(Base):
    """8. Audit trail: all DNA mutations (immutability tracking)."""
    __tablename__ = "dna_audit"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_dna_audit_agent", "agent_id", "timestamp"),
            Index("idx_dna_audit_timestamp", "timestamp"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_dna_audit_agent", "agent_id", "timestamp"),
            Index("idx_dna_audit_timestamp", "timestamp"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), nullable=False)
    changed_fields = Column(JSON, nullable=False)
    old_values = Column(JSON, nullable=False)
    new_values = Column(JSON, nullable=False)
    changed_by = Column(String(256), nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    tenant_id = Column(String(128), nullable=True)


class AgentRuntimeState(Base):
    """9. Agent runtime state: Out-of-process serialization of Q-learning policy matrices."""
    __tablename__ = "agent_runtime_state"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_agent_runtime_state_agent", "agent_id"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_agent_runtime_state_agent", "agent_id"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), unique=True, nullable=False)
    target_return = Column(Float, nullable=True)
    dominant_policy_json = Column(JSON, nullable=False)
    base_policy_json = Column(JSON, nullable=False)
    last_update = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationship
    dna = relationship("MissionDNA", back_populates="runtime_state")


class AgentActionTrace(Base):
    """10. Agent action trace: Flight recorder logging of exact action sequences & conformance."""
    __tablename__ = "agent_action_trace"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_agent_action_trace_agent", "agent_id", "timestamp"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_agent_action_trace_agent", "agent_id", "timestamp"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), nullable=False)
    state = Column(String(256), nullable=False)
    action = Column(String(256), nullable=False)
    reward = Column(Float, nullable=False)
    next_state = Column(String(256), nullable=False)
    on_path = Column(Boolean, nullable=False)
    cue = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    tenant_id = Column(String(128), nullable=True)

    # Relationship
    dna = relationship("MissionDNA", back_populates="action_traces")


class IdempotencyKey(Base):
    """11. Idempotency keys: Deduplication and safety for mutating API requests."""
    __tablename__ = "idempotency_keys"
    if SCHEMA_NAME:
        __table_args__ = ({"schema": SCHEMA_NAME},)

    key = Column(String(256), primary_key=True)
    response_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class RecoverySnapshot(Base):
    """12. Recovery snapshot: Full policy and telemetry dump on drift trigger."""
    __tablename__ = "recovery_snapshot"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_recovery_snapshot_agent", "agent_id"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_recovery_snapshot_agent", "agent_id"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(64), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}mission_dna.agent_id", ondelete="CASCADE"), nullable=False)
    recovery_event_id = Column(String(36), ForeignKey(f"{SCHEMA_NAME + '.' if SCHEMA_NAME else ''}recovery_events.id", ondelete="CASCADE"), nullable=True)
    state_snapshot = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    dna = relationship("MissionDNA", back_populates="recovery_snapshots")
    recovery_event = relationship("RecoveryEvent", back_populates="snapshots")


class MetricsCache(Base):
    """13. Metrics cache: Pre-aggregated dashboard values for sub-millisecond loads."""
    __tablename__ = "metrics_cache"
    if SCHEMA_NAME:
        __table_args__ = ({"schema": SCHEMA_NAME},)

    key = Column(String(128), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TenantRole(Base):
    """14. Tenant roles: Multi-tenant tenant access registry."""
    __tablename__ = "tenant_roles"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_tenant_roles_lookup", "tenant_id", "user_id"),
            UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_tenant_roles_lookup", "tenant_id", "user_id"),
            UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(128), nullable=False)
    user_id = Column(String(256), nullable=False)
    role = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class AuthzLog(Base):
    """15. Continuous authorization log: Audit gate for all secure syscalls and compliance."""
    __tablename__ = "authz_log"
    if SCHEMA_NAME:
        __table_args__ = (
            Index("idx_authz_log_timestamp", "timestamp"),
            {"schema": SCHEMA_NAME}
        )
    else:
        __table_args__ = (
            Index("idx_authz_log_timestamp", "timestamp"),
        )

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(256), nullable=True)
    tenant_id = Column(String(128), nullable=True)
    action = Column(String(128), nullable=False)
    resource = Column(String(128), nullable=False)
    decision = Column(String(32), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
