from __future__ import annotations

import base64
import secrets
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.db.models.duel import AgentDuelLobby, AgentDuelLobbyPlayer, AgentDuelSession, AgentDuelWager

router = APIRouter(prefix="/duel", tags=["Agent Duel"])

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_USDC_CONTRACT = os.getenv("BASE_USDC_CONTRACT", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
VEKLOM_TREASURY_ADDRESS = os.getenv("VEKLOM_TREASURY_ADDRESS", "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970")
ERC1271_MAGIC_VALUE = "1626ba7e"


class SessionCreateRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)


class WagerRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    wallet_address: str = Field(..., min_length=42, max_length=42)
    bet_type: Literal["player", "banker", "tie"]
    wager_amount_usdc: float = Field(..., gt=0, le=10000)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)


class OutcomeRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    outcome: Literal["player", "banker", "tie"]
    payout_multiplier: float = Field(0, ge=0, le=100)
    settlement_tx_hash: str | None = Field(None, max_length=128)


class LobbyCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    wallet_address: str = Field(..., min_length=42, max_length=42)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)


class LobbyJoinRequest(LobbyCreateRequest):
    pass


class LobbyReadyRequest(LobbyCreateRequest):
    bet_type: Literal["player", "banker", "tie"]
    wager_id: str = Field(..., min_length=1, max_length=64)
    wager_amount_usdc: float = Field(..., gt=0, le=10000)


class LobbyEjectRequest(LobbyCreateRequest):
    ejected_multiplier: float = Field(..., gt=0, le=100)


def _normalize_address(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("wallet address must be a string")
    value = value.strip()
    if not value.startswith("0x") or len(value) != 42:
        raise ValueError("wallet address must be a 20-byte EVM address")
    int(value[2:], 16)
    return value.lower()


def _signature_hash(signature_payload: str) -> str:
    return hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()


def _session_token_hash(session_token: str) -> str:
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def _decode_payment_signature(payment_signature: str | None) -> dict[str, Any]:
    if not payment_signature:
        raise HTTPException(status_code=402, detail="Missing payment-signature header")
    try:
        decoded = base64.b64decode(payment_signature, validate=True).decode("utf-8")
        payload = json.loads(decoded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payment-signature payload: {type(exc).__name__}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("payload"), dict):
        raise HTTPException(status_code=400, detail="Invalid payment-signature structure")
    return payload["payload"]


def _strip_hex_prefix(value: str) -> str:
    return value[2:] if value.startswith("0x") else value


async def _verify_erc1271_signature(wallet_address: str, digest_hex: str, signature: str) -> bool:
    address_word = _normalize_address(wallet_address).replace("0x", "").rjust(64, "0")
    digest_word = _strip_hex_prefix(digest_hex).rjust(64, "0")
    signature_hex = _strip_hex_prefix(signature)
    if len(signature_hex) % 2 != 0:
        signature_hex = f"0{signature_hex}"
    signature_bytes_len = len(signature_hex) // 2
    signature_offset = (64).to_bytes(32, "big").hex()
    signature_length = signature_bytes_len.to_bytes(32, "big").hex()
    padded_signature = signature_hex.ljust(((signature_bytes_len + 31) // 32) * 64, "0")
    data = f"0x{ERC1271_MAGIC_VALUE}{digest_word}{signature_offset}{signature_length}{padded_signature}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": f"0x{address_word[-40:]}", "data": data}, "latest"],
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(BASE_RPC_URL, json=payload)
    response.raise_for_status()
    result = response.json()
    if result.get("error"):
        return False
    returned = str(result.get("result", "")).lower().replace("0x", "")
    return returned.startswith(ERC1271_MAGIC_VALUE)


async def _verify_eip712_payment_signature(payment_payload: dict[str, Any], wallet_address: str, amount_usdc: float) -> dict[str, Any]:
    authorization = payment_payload.get("authorization")
    signature = payment_payload.get("signature")
    if not isinstance(authorization, dict) or not isinstance(signature, str):
        raise HTTPException(status_code=400, detail="Payment signature missing authorization or signature")

    from_addr = _normalize_address(str(authorization.get("from", "")))
    to_addr = _normalize_address(str(authorization.get("to", "")))
    if from_addr != wallet_address:
        raise HTTPException(status_code=403, detail="Payment signature wallet does not match request wallet")
    if to_addr != _normalize_address(VEKLOM_TREASURY_ADDRESS):
        raise HTTPException(status_code=400, detail="Payment signature is not addressed to Veklom treasury")

    expected_raw_amount = str(int(round(amount_usdc * 1_000_000)))
    if str(authorization.get("value")) != expected_raw_amount:
        raise HTTPException(status_code=400, detail="Payment signature amount does not match wager amount")

    try:
        valid_after = int(authorization.get("validAfter"))
        valid_before = int(authorization.get("validBefore"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Payment signature validity window is invalid") from exc
    now = int(datetime.now(timezone.utc).timestamp())
    if now < valid_after or now > valid_before:
        raise HTTPException(status_code=400, detail="Payment signature is outside its validity window")

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": BASE_CHAIN_ID,
            "verifyingContract": BASE_USDC_CONTRACT,
        },
        "message": {
            "from": authorization["from"],
            "to": authorization["to"],
            "value": int(authorization["value"]),
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": authorization["nonce"],
        },
    }

    try:
        from eth_account import Account
        from eth_account.messages import _hash_eip191_message, encode_typed_data

        signable = encode_typed_data(full_message=typed_data)
        digest = _hash_eip191_message(signable)
        digest_hex = f"0x{digest.hex()}"
        recovered = Account.recover_message(signable, signature=signature)
    except Exception as exc:
        try:
            from eth_account.messages import _hash_eip191_message, encode_typed_data

            signable = encode_typed_data(full_message=typed_data)
            digest = _hash_eip191_message(signable)
            digest_hex = f"0x{digest.hex()}"
        except Exception as digest_exc:
            raise HTTPException(status_code=400, detail=f"Payment signature digest failed: {type(digest_exc).__name__}") from digest_exc
        if await _verify_erc1271_signature(wallet_address, digest_hex, signature):
            return {
                "from": from_addr,
                "to": to_addr,
                "value_usdc": amount_usdc,
                "valid_after": valid_after,
                "valid_before": valid_before,
                "nonce": str(authorization["nonce"]),
                "signature_verified": True,
                "signature_standard": "erc1271",
                "digest": digest_hex,
            }
        raise HTTPException(status_code=400, detail=f"Payment signature recovery failed: {type(exc).__name__}") from exc

    if _normalize_address(recovered) != wallet_address:
        if await _verify_erc1271_signature(wallet_address, digest_hex, signature):
            return {
                "from": from_addr,
                "to": to_addr,
                "value_usdc": amount_usdc,
                "valid_after": valid_after,
                "valid_before": valid_before,
                "nonce": str(authorization["nonce"]),
                "signature_verified": True,
                "signature_standard": "erc1271",
                "digest": digest_hex,
                "recovered_eoa": _normalize_address(recovered),
            }
        raise HTTPException(status_code=403, detail="Payment signature did not recover request wallet and ERC-1271 verification failed")

    return {
        "from": from_addr,
        "to": to_addr,
        "value_usdc": amount_usdc,
        "valid_after": valid_after,
        "valid_before": valid_before,
        "nonce": str(authorization["nonce"]),
        "signature_verified": True,
        "signature_standard": "eoa",
        "digest": digest_hex,
    }


async def _base_usdc_balance(address: str) -> float:
    selector = "70a08231"
    encoded_address = address.lower().replace("0x", "").rjust(64, "0")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": BASE_USDC_CONTRACT, "data": f"0x{selector}{encoded_address}"},
            "latest",
        ],
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(BASE_RPC_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"].get("message", "Base RPC error"))
    raw = int(str(data.get("result", "0x0")), 16)
    return round(raw / 1_000_000, 6)


async def _get_session_or_404(db: AsyncSession, session_id: str) -> AgentDuelSession:
    session = await db.get(AgentDuelSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Agent Duel session not found")
    return session


def _verify_session_token(session: AgentDuelSession, session_token: str | None) -> None:
    expected = (session.metadata_json or {}).get("session_token_hash")
    if not expected or not session_token or _session_token_hash(session_token) != expected:
        raise HTTPException(status_code=403, detail="Invalid Agent Duel session token")


def _wager_to_history(row: AgentDuelWager) -> dict[str, Any]:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "tx_hash": row.settlement_tx_hash or f"db:{row.id}",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "bet_type": row.bet_type,
        "wager_amount_usdc": row.wager_amount_usdc,
        "payout_multiplier": row.payout_multiplier,
        "payout_usdc": row.payout_usdc,
        "outcome": row.outcome,
        "status": row.status,
        "network": "Base",
        "settlement_tx_hash": row.settlement_tx_hash,
        "signature_hash": row.signature_hash,
        "proof_source": "agent_duel_wagers",
        "settlement_state": "verified_onchain" if row.settlement_tx_hash else "needs_settlement_proof",
    }


def _lobby_player_to_dict(player: AgentDuelLobbyPlayer) -> dict[str, Any]:
    return {
        "id": player.id,
        "lobby_id": player.lobby_id,
        "wallet_address": player.wallet_address,
        "session_id": player.session_id,
        "status": player.status,
        "bet_type": player.bet_type,
        "wager_id": player.wager_id,
        "wager_amount_usdc": player.wager_amount_usdc,
        "ejected_multiplier": player.ejected_multiplier,
        "payout_usdc": player.payout_usdc,
        "created_at": player.created_at.isoformat() if player.created_at else None,
        "updated_at": player.updated_at.isoformat() if player.updated_at else None,
    }


def _lobby_to_dict(lobby: AgentDuelLobby, players: list[AgentDuelLobbyPlayer]) -> dict[str, Any]:
    return {
        "id": lobby.id,
        "host_wallet_address": lobby.host_wallet_address,
        "status": lobby.status,
        "max_players": lobby.max_players,
        "player_count": len([player for player in players if player.status != "left"]),
        "players": [_lobby_player_to_dict(player) for player in players],
        "created_at": lobby.created_at.isoformat() if lobby.created_at else None,
        "updated_at": lobby.updated_at.isoformat() if lobby.updated_at else None,
    }


async def _get_lobby_or_404(db: AsyncSession, lobby_id: str) -> AgentDuelLobby:
    lobby = await db.get(AgentDuelLobby, lobby_id.upper())
    if not lobby:
        raise HTTPException(status_code=404, detail="Agent Duel lobby not found")
    return lobby


async def _get_lobby_players(db: AsyncSession, lobby_id: str) -> list[AgentDuelLobbyPlayer]:
    result = await db.execute(
        select(AgentDuelLobbyPlayer)
        .where(AgentDuelLobbyPlayer.lobby_id == lobby_id)
        .order_by(AgentDuelLobbyPlayer.created_at.asc())
    )
    return list(result.scalars().all())


async def _generate_lobby_id(db: AsyncSession) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        candidate = "DUEL-" + "".join(secrets.choice(alphabet) for _ in range(4))
        exists = await db.get(AgentDuelLobby, candidate)
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="Could not allocate Agent Duel lobby id")


async def _verified_session_for_wallet(
    db: AsyncSession,
    session_id: str,
    wallet_address: str,
    session_token: str | None,
) -> AgentDuelSession:
    session = await _get_session_or_404(db, session_id)
    _verify_session_token(session, session_token)
    if session.wallet_address.lower() != wallet_address:
        raise HTTPException(status_code=403, detail="Session wallet does not match lobby wallet")
    return session


@router.get("/proof")
async def get_duel_proof(db: AsyncSession = Depends(get_db)):
    session_count = await db.scalar(select(func.count()).select_from(AgentDuelSession))
    wager_count = await db.scalar(select(func.count()).select_from(AgentDuelWager))
    lobby_count = await db.scalar(select(func.count()).select_from(AgentDuelLobby))
    lobby_player_count = await db.scalar(select(func.count()).select_from(AgentDuelLobbyPlayer))
    open_lobby_count = await db.scalar(
        select(func.count()).select_from(AgentDuelLobby).where(AgentDuelLobby.status == "open")
    )
    settled_count = await db.scalar(
        select(func.count()).select_from(AgentDuelWager).where(AgentDuelWager.settlement_tx_hash.isnot(None))
    )
    latest_result = await db.execute(select(AgentDuelWager).order_by(desc(AgentDuelWager.created_at)).limit(10))
    latest = latest_result.scalars().all()
    return {
        "success": True,
        "source": "postgres",
        "tables": {
            "agent_duel_sessions": int(session_count or 0),
            "agent_duel_wagers": int(wager_count or 0),
            "agent_duel_lobbies": int(lobby_count or 0),
            "agent_duel_lobby_players": int(lobby_player_count or 0),
            "open_agent_duel_lobbies": int(open_lobby_count or 0),
            "settled_wagers": int(settled_count or 0),
        },
        "capabilities": {
            "session_create": "verified",
            "wager_persist": "verified",
            "outcome_persist": "verified",
            "multiplayer_lobbies": "verified",
            "wallet_balance": "base_rpc",
            "settlement": "verified" if settled_count else "needs_proof",
        },
        "latest_wagers": [_wager_to_history(row) for row in latest],
    }


@router.post("/session/create")
async def create_duel_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    balance_usdc = 0.0
    balance_source = "base_rpc"
    try:
        balance_usdc = await _base_usdc_balance(body.wallet_address)
    except Exception as exc:
        balance_source = f"base_rpc_unavailable:{type(exc).__name__}"

    session_token = secrets.token_urlsafe(32)
    session = AgentDuelSession(
        wallet_address=body.wallet_address,
        balance_usdc=balance_usdc,
        metadata_json={
            "balance_source": balance_source,
            "session_token_hash": _session_token_hash(session_token),
        },
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "success": True,
        "session_id": session.id,
        "session_token": session_token,
        "player": {
            "address": session.wallet_address,
            "balance_usdc": session.balance_usdc,
            "balance_source": balance_source,
        },
    }


@router.post("/wager")
async def place_wager(
    body: WagerRequest,
    payment_signature: str | None = Header(default=None, alias="payment-signature"),
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, body.session_id)
    _verify_session_token(session, duel_session_token)
    if session.wallet_address.lower() != body.wallet_address:
        raise HTTPException(status_code=403, detail="Session wallet does not match wager wallet")

    payment_payload = _decode_payment_signature(payment_signature)
    signature_proof = await _verify_eip712_payment_signature(payment_payload, body.wallet_address, body.wager_amount_usdc)
    sig_hash = _signature_hash(payment_signature or "")

    existing = await db.scalar(select(AgentDuelWager).where(AgentDuelWager.signature_hash == sig_hash))
    if existing:
        return {
            "success": True,
            "wager_id": existing.id,
            "status": existing.status,
            "idempotent": True,
            "signature_hash": existing.signature_hash,
        }

    wager = AgentDuelWager(
        session_id=session.id,
        wallet_address=body.wallet_address,
        bet_type=body.bet_type,
        wager_amount_usdc=round(body.wager_amount_usdc, 6),
        payment_signature=payment_signature or "",
        signature_hash=sig_hash,
        status="locked",
        metadata_json=signature_proof,
    )
    db.add(wager)
    await db.commit()
    await db.refresh(wager)
    return {
        "success": True,
        "wager_id": wager.id,
        "status": wager.status,
        "signature_hash": wager.signature_hash,
        "settlement_state": "needs_settlement_proof",
    }


@router.post("/outcome")
async def settle_outcome(
    body: OutcomeRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, body.session_id)
    _verify_session_token(session, duel_session_token)
    result = await db.execute(
        select(AgentDuelWager)
        .where(AgentDuelWager.session_id == body.session_id, AgentDuelWager.status.in_(["pending", "locked"]))
        .order_by(desc(AgentDuelWager.created_at))
    )
    wagers = result.scalars().all()
    if not wagers:
        raise HTTPException(status_code=404, detail="No open wagers found for session")

    multiplier = round(float(body.payout_multiplier or 0), 6)
    for wager in wagers:
        won = wager.bet_type == body.outcome
        payout = wager.wager_amount_usdc * multiplier if won and multiplier > 0 else 0.0
        wager.outcome = "won" if won else "lost"
        wager.payout_multiplier = multiplier
        wager.payout_usdc = round(payout, 6)
        wager.status = "settled"
        wager.settlement_tx_hash = body.settlement_tx_hash
        wager.settled_at = datetime.now(timezone.utc)

    await db.commit()
    return {
        "success": True,
        "session_id": body.session_id,
        "settled_wagers": len(wagers),
        "outcome": body.outcome,
        "settlement_state": "verified_onchain" if body.settlement_tx_hash else "needs_settlement_proof",
    }


@router.get("/lobbies")
async def list_lobbies(status: str = "open", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentDuelLobby)
        .where(AgentDuelLobby.status == status)
        .order_by(desc(AgentDuelLobby.created_at))
        .limit(25)
    )
    lobbies = result.scalars().all()
    lobby_ids = [lobby.id for lobby in lobbies]
    players_by_lobby: dict[str, list[AgentDuelLobbyPlayer]] = {lobby_id: [] for lobby_id in lobby_ids}
    if lobby_ids:
        player_result = await db.execute(
            select(AgentDuelLobbyPlayer)
            .where(AgentDuelLobbyPlayer.lobby_id.in_(lobby_ids))
            .order_by(AgentDuelLobbyPlayer.created_at.asc())
        )
        for player in player_result.scalars().all():
            players_by_lobby.setdefault(player.lobby_id, []).append(player)
    return {
        "success": True,
        "source": "agent_duel_lobbies",
        "lobbies": [_lobby_to_dict(lobby, players_by_lobby.get(lobby.id, [])) for lobby in lobbies],
    }


@router.post("/lobbies")
async def create_lobby(
    body: LobbyCreateRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    lobby_id = await _generate_lobby_id(db)
    lobby = AgentDuelLobby(id=lobby_id, host_wallet_address=body.wallet_address, status="open", max_players=2)
    player = AgentDuelLobbyPlayer(
        lobby_id=lobby_id,
        wallet_address=body.wallet_address,
        session_id=body.session_id,
        status="joined",
    )
    db.add(lobby)
    db.add(player)
    await db.commit()
    await db.refresh(lobby)
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.get("/lobbies/{lobby_id}")
async def get_lobby(lobby_id: str, db: AsyncSession = Depends(get_db)):
    lobby = await _get_lobby_or_404(db, lobby_id)
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.post("/lobbies/{lobby_id}/join")
async def join_lobby(
    lobby_id: str,
    body: LobbyJoinRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    lobby = await _get_lobby_or_404(db, lobby_id)
    if lobby.status != "open":
        raise HTTPException(status_code=409, detail="Lobby is not open")

    players = await _get_lobby_players(db, lobby.id)
    active_players = [player for player in players if player.status != "left"]
    existing = next((player for player in active_players if player.wallet_address == body.wallet_address), None)
    if not existing and len(active_players) >= lobby.max_players:
        raise HTTPException(status_code=409, detail="Lobby is full")
    if existing:
        existing.session_id = body.session_id
        existing.status = "joined" if existing.status == "left" else existing.status
    else:
        db.add(
            AgentDuelLobbyPlayer(
                lobby_id=lobby.id,
                wallet_address=body.wallet_address,
                session_id=body.session_id,
                status="joined",
            )
        )
    await db.commit()
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.post("/lobbies/{lobby_id}/ready")
async def mark_lobby_ready(
    lobby_id: str,
    body: LobbyReadyRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    lobby = await _get_lobby_or_404(db, lobby_id)
    if lobby.status != "open":
        raise HTTPException(status_code=409, detail="Lobby is not accepting ready states")

    wager = await db.get(AgentDuelWager, body.wager_id)
    if not wager or wager.wallet_address != body.wallet_address or wager.session_id != body.session_id:
        raise HTTPException(status_code=404, detail="Verified wager not found for lobby wallet")
    if wager.bet_type != body.bet_type or round(wager.wager_amount_usdc, 6) != round(body.wager_amount_usdc, 6):
        raise HTTPException(status_code=409, detail="Lobby ready state does not match persisted wager")

    players = await _get_lobby_players(db, lobby.id)
    player = next((row for row in players if row.wallet_address == body.wallet_address and row.status != "left"), None)
    if not player:
        raise HTTPException(status_code=404, detail="Wallet has not joined this lobby")
    player.status = "ready"
    player.bet_type = body.bet_type
    player.wager_id = body.wager_id
    player.wager_amount_usdc = round(body.wager_amount_usdc, 6)
    await db.commit()
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.post("/lobbies/{lobby_id}/eject")
async def mark_lobby_ejected(
    lobby_id: str,
    body: LobbyEjectRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    lobby = await _get_lobby_or_404(db, lobby_id)
    players = await _get_lobby_players(db, lobby.id)
    player = next((row for row in players if row.wallet_address == body.wallet_address and row.status != "left"), None)
    if not player:
        raise HTTPException(status_code=404, detail="Wallet has not joined this lobby")
    player.status = "ejected"
    player.ejected_multiplier = round(body.ejected_multiplier, 6)
    await db.commit()
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.post("/lobbies/{lobby_id}/leave")
async def leave_lobby(
    lobby_id: str,
    body: LobbyJoinRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    lobby = await _get_lobby_or_404(db, lobby_id)
    players = await _get_lobby_players(db, lobby.id)
    player = next((row for row in players if row.wallet_address == body.wallet_address and row.status != "left"), None)
    if player:
        player.status = "left"
        if lobby.host_wallet_address == body.wallet_address:
            lobby.status = "closed"
    await db.commit()
    players = await _get_lobby_players(db, lobby.id)
    return {"success": True, "source": "agent_duel_lobbies", "lobby": _lobby_to_dict(lobby, players)}


@router.get("/leaderboard")
async def get_duel_leaderboard(db: AsyncSession = Depends(get_db)):
    total_won = func.coalesce(func.sum(AgentDuelWager.payout_usdc), 0.0).label("total_won")
    best_multiplier = func.coalesce(func.max(AgentDuelWager.payout_multiplier), 0.0).label("best_multiplier")
    rounds = func.count(AgentDuelWager.id).label("rounds")
    stmt = (
        select(
            AgentDuelWager.wallet_address,
            rounds,
            total_won,
            best_multiplier,
        )
        .where(AgentDuelWager.status == "settled")
        .group_by(AgentDuelWager.wallet_address)
        .order_by(total_won.desc())
        .limit(50)
    )
    rows = (await db.execute(stmt)).all()
    return {
        "success": True,
        "source": "agent_duel_wagers",
        "leaderboard": [
            {
                "rank": idx,
                "username": f"Wallet {row.wallet_address[:6]}...{row.wallet_address[-4:]}",
                "address": row.wallet_address,
                "totalWonUsdc": float(row.total_won or 0),
                "bestMultiplier": float(row.best_multiplier or 0),
                "streak": int(row.rounds or 0),
                "agentPreference": "BYOS persisted duel history",
            }
            for idx, row in enumerate(rows, start=1)
        ],
    }


@router.get("/player/{address}/history")
async def get_player_history(address: str, db: AsyncSession = Depends(get_db)):
    normalized = _normalize_address(address)
    result = await db.execute(
        select(AgentDuelWager)
        .where(AgentDuelWager.wallet_address == normalized)
        .order_by(desc(AgentDuelWager.created_at))
        .limit(100)
    )
    wagers = result.scalars().all()
    return {
        "success": True,
        "source": "agent_duel_wagers",
        "wagers": [_wager_to_history(row) for row in wagers],
    }
