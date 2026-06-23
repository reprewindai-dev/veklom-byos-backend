from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base


class GenomeVersion(Base):
    """Versioned, hashed snapshot of an agent's genome payload.

    Each commit to an agent's configuration creates a new row.  The
    genome_hash is a SHA-256 of the canonical JSON payload and is used
    by the Ledger worker to verify evidence integrity.
    """

    __tablename__ = "genome_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    pgl_identity_id: Mapped[str] = mapped_column(ForeignKey("pgl_identities.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    genome_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(String(255))
    
    # Merkle trees & layer hashing
    model_layer_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_layer_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_layer_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    watchtower_layer_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    task_profile_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    merkle_root: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    parent_genome_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="genome_versions")  # noqa: F821
    pgl_identity: Mapped["PGLIdentity"] = relationship()  # noqa: F821

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_genome_version_positive"),
    )
