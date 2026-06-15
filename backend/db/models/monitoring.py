"""Monitoring system models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(32), default="count")  # count, percent, ms, mb, etc.
    tags = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, index=True)
    
    # Create composite index for efficient time-series queries
    __table_args__ = (
        Index('idx_metrics_workspace_name_time', 'workspace_id', 'name', 'timestamp'),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    rule_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    severity = Column(String(32), default="warning")  # info, warning, error, critical
    status = Column(String(32), default="active")  # active, resolved, suppressed
    metric_name = Column(String(128), nullable=False)
    threshold_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    triggered_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)  # User ID who resolved
    alert_metadata = Column(JSON, default=dict)
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    metric_name = Column(String(128), nullable=False)
    condition = Column(String(32), nullable=False)  # gt, lt, eq, gte, lte
    threshold = Column(Float, nullable=False)
    severity = Column(String(32), default="warning")
    enabled = Column(Boolean, default=True)
    evaluation_interval_seconds = Column(Integer, default=300)  # 5 minutes
    notification_channels = Column(JSON, default=list)  # email, slack, webhook, etc.
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    alerts = relationship("Alert", back_populates="rule")


class SystemHealth(Base):
    __tablename__ = "system_health"

    id = Column(String(36), primary_key=True, default=_uuid)
    component = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False)  # healthy, degraded, unhealthy
    latency_ms = Column(Float, nullable=True)
    error_rate = Column(Float, default=0.0)
    last_check = Column(DateTime(timezone=True), default=_utcnow, index=True)
    alert_metadata = Column(JSON, default=dict)
    
    # Create composite index
    __table_args__ = (
        Index('idx_health_component_time', 'component', 'last_check'),
    )


class PerformanceLog(Base):
    __tablename__ = "performance_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(16), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    user_id = Column(String(36), nullable=True, index=True)
    request_size_bytes = Column(Integer, default=0)
    response_size_bytes = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, index=True)
    alert_metadata = Column(JSON, default=dict)
    
    # Create composite indexes
    __table_args__ = (
        Index('idx_perf_workspace_endpoint_time', 'workspace_id', 'endpoint', 'timestamp'),
        Index('idx_perf_status_time', 'status_code', 'timestamp'),
    )


class ResourceUsage(Base):
    __tablename__ = "resource_usage"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)  # cpu, memory, disk, network
    resource_name = Column(String(128), nullable=False)  # server name, container, etc.
    usage_percent = Column(Float, nullable=False)
    available_units = Column(Float, nullable=True)
    total_units = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, index=True)
    alert_metadata = Column(JSON, default=dict)
    
    # Create composite index
    __table_args__ = (
        Index('idx_resource_type_time', 'resource_type', 'timestamp'),
    )
