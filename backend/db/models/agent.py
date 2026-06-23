from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base

HRM_TIERS = ("prime", "monitor", "sync")



class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="launch")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    users: Mapped[list["AgentUser"]] = relationship(back_populates="account")
    agents: Mapped[list["Agent"]] = relationship(back_populates="account")


class AgentUser(Base):
    """Lightweight account-scoped user for UACP V3 institutional ownership.

    Distinct from the existing User model in user.py which carries session/API-key
    relationships.  The two models coexist; this one owns the account/role axis.
    """

    __tablename__ = "agent_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped[Account] = relationship(back_populates="users")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    creator: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False)
    declared_purpose: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # HRM fields — nullable so existing rows are unaffected.
    # tier: one of HRM_TIERS ('prime'|'monitor'|'sync') or null for non-HRM agents.
    # agent_number: sequential identifier within the account's task force (e.g. 114).
    # squad_id: optional grouping tag (e.g. 'HQ-Alpha', 'Field-Bravo').
    # capabilities: JSON list of skill IDs this agent is authorised to invoke.
    hrm_tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    agent_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    squad_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    capabilities: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    pgl_genome_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    account: Mapped[Account] = relationship(back_populates="agents")
    genome_versions: Mapped[list["GenomeVersion"]] = relationship(  # noqa: F821
        back_populates="agent"
    )
    certificate: Mapped["BirthCertificate"] = relationship(  # noqa: F821
        back_populates="agent", uselist=False
    )
    ledger_events: Mapped[list["LedgerEvent"]] = relationship(  # noqa: F821
        back_populates="agent"
    )
    parent_edges: Mapped[list["LineageEdge"]] = relationship(  # noqa: F821
        back_populates="child", foreign_keys="LineageEdge.child_agent_id"
    )
    child_edges: Mapped[list["LineageEdge"]] = relationship(  # noqa: F821
        back_populates="parent", foreign_keys="LineageEdge.parent_agent_id"
    )


class AgentSkill(Base):
    """Registered agent skill.

    A skill is a named, versioned capability an agent may invoke.
    `is_available=False` means the skill is catalogued but the backend
    implementation does not exist yet.  Callers receive SKILL_MISSING if
    they attempt invocation.

    Seeded at startup (lifespan) for first-class skills like
    passive-income-engine; never auto-invoked without explicit operator call.
    """

    __tablename__ = "agent_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="0.1")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



