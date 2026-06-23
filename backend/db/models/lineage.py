from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base


class BirthCertificate(Base):
    """Immutable provenance document issued at agent registration.

    Stores the genome_hash at birth, optional parent agent IDs (for
    fork/clone lineage), and a document_uri pointing to the off-chain
    PDF/JSON certificate stored in object storage.
    """

    __tablename__ = "birth_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id"), unique=True, nullable=False
    )
    pgl_identity_id: Mapped[str] = mapped_column(ForeignKey("pgl_identities.id"), nullable=False, index=True)
    certificate_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    genome_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    document_uri: Mapped[str | None] = mapped_column(String(512))
    parent_agent_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="certificate")  # noqa: F821
    pgl_identity: Mapped["PGLIdentity"] = relationship()  # noqa: F821


class LineageEdge(Base):
    """Directed parent→child relationship between agents.

    A parent agent can have many children (fork/spawn).  A child records
    all parents it was derived from.  The Builder Arbiter uses this graph
    to block circular lineage before approving a new agent registration.
    """

    __tablename__ = "lineage_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    child_agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    parent_pgl_id: Mapped[str] = mapped_column(
        ForeignKey("pgl_identities.id"), nullable=False, index=True
    )
    child_pgl_id: Mapped[str] = mapped_column(
        ForeignKey("pgl_identities.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    parent: Mapped["Agent"] = relationship(  # noqa: F821
        back_populates="child_edges", foreign_keys=[parent_agent_id]
    )
    child: Mapped["Agent"] = relationship(  # noqa: F821
        back_populates="parent_edges", foreign_keys=[child_agent_id]
    )
    parent_pgl: Mapped["PGLIdentity"] = relationship(  # noqa: F821
        foreign_keys=[parent_pgl_id]
    )
    child_pgl: Mapped["PGLIdentity"] = relationship(  # noqa: F821
        foreign_keys=[child_pgl_id]
    )
