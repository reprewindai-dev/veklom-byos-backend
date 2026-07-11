from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentDuelSession(Base):
    __tablename__ = "agent_duel_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    balance_usdc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    network: Mapped[str] = mapped_column(String(32), nullable=False, default="base")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_agent_duel_sessions_wallet_created", "wallet_address", "created_at"),
    )


class AgentDuelAuthNonce(Base):
    __tablename__ = "agent_duel_auth_nonces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nonce_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    uri: Mapped[str] = mapped_column(String(256), nullable=False)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, default=8453)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_agent_duel_auth_nonces_wallet_created", "wallet_address", "created_at"),
        Index("ix_agent_duel_auth_nonces_status_expires", "status", "expires_at"),
    )


class AgentDuelWager(Base):
    __tablename__ = "agent_duel_wagers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bet_type: Mapped[str] = mapped_column(String(16), nullable=False)
    wager_amount_usdc: Mapped[float] = mapped_column(Float, nullable=False)
    payment_signature: Mapped[str] = mapped_column(String(4096), nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    payout_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payout_usdc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    settlement_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_agent_duel_wagers_wallet_created", "wallet_address", "created_at"),
        Index("ix_agent_duel_wagers_session_created", "session_id", "created_at"),
    )


class AgentDuelLobby(Base):
    __tablename__ = "agent_duel_lobbies"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    host_wallet_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_agent_duel_lobbies_status_created", "status", "created_at"),
        Index("ix_agent_duel_lobbies_host_created", "host_wallet_address", "created_at"),
    )


class AgentDuelLobbyPlayer(Base):
    __tablename__ = "agent_duel_lobby_players"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lobby_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="joined", index=True)
    bet_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    wager_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    wager_amount_usdc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ejected_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    payout_usdc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_agent_duel_lobby_players_lobby_wallet", "lobby_id", "wallet_address"),
        Index("ix_agent_duel_lobby_players_lobby_status", "lobby_id", "status"),
    )

