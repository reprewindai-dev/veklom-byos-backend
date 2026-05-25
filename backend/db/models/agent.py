from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base


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
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    agent_number: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True, default=None)
    hrm_role: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)

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
