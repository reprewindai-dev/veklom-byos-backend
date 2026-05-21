from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class GenomeVersion(Base):
    """Versioned, hashed snapshot of an agent's genome payload.

    Each commit to an agent's configuration creates a new row.  The
    genome_hash is a SHA-256 of the canonical JSON payload and is used
    by the Ledger worker to verify evidence integrity.
    """

    __tablename__ = "genome_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    genome_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="genome_versions")  # noqa: F821

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_genome_version_positive"),
    )
