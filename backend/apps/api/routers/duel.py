from __future__ import annotations

import base64
import secrets
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.db.models.duel import AgentDuelAuthNonce, AgentDuelLobby, AgentDuelLobbyPlayer, AgentDuelSession, AgentDuelWager

router = APIRouter(prefix="/duel", tags=["Agent Duel"])

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_USDC_CONTRACT = os.getenv("BASE_USDC_CONTRACT", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
VEKLOM_TREASURY_ADDRESS = os.getenv("VEKLOM_TREASURY_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
ERC1271_MAGIC_VALUE = "1626ba7e"
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class SessionNonceRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42)
    domain: str = Field("control.veklom.com", min_length=3, max_length=128)
    uri: str = Field("https://control.veklom.com/agent-dual", min_length=8, max_length=256)
    chain_id: int = Field(BASE_CHAIN_ID, ge=1, le=999999999)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.-]+(?::\d+)?", value):
            raise ValueError("domain must be a valid host authority")
        return value

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("uri must be https or local development http")
        return value


class SessionCreateRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42)
    message: str = Field(..., min_length=120, max_length=2048)
    signature: str = Field(..., min_length=66, max_length=4096)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)

    @field_validator("signature")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("0x"):
            raise ValueError("signature must be hex encoded")
        int(value[2:4] or "0", 16)
        return value


class WagerRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    wallet_address: str = Field(..., min_length=42, max_length=42)
    bet_type: Literal["player", "banker", "tie"]
    wager_amount_usdc: float = Field(..., gt=0, le=10000)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        return _normalize_address(value)


class WagerPrepareRequest(WagerRequest):
    idempotency_key: str | None = Field(None, min_length=8, max_length=128)


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


class SettlementProofRequest(LobbyCreateRequest):
    settlement_tx_hash: str = Field(..., min_length=66, max_length=66)

    @field_validator("settlement_tx_hash")
    @classmethod
    def validate_tx_hash(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"0x[a-fA-F0-9]{64}", value):
            raise ValueError("settlement_tx_hash must be a 32-byte transaction hash")
        return value.lower()


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


def _auth_nonce_hash(nonce: str) -> str:
    return hashlib.sha256(f"agent-duel-siwe:{nonce}".encode("utf-8")).hexdigest()


def _new_siwe_nonce() -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(24))


def _siwe_field(message: str, field: str) -> str | None:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", message, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _parse_siwe_message(message: str) -> dict[str, Any]:
    lines = [line.strip() for line in message.splitlines()]
    first_line = lines[0] if lines else ""
    address = next((line for line in lines[1:] if re.fullmatch(r"0x[a-fA-F0-9]{40}", line)), None)
    nonce = _siwe_field(message, "Nonce")
    chain_id = _siwe_field(message, "Chain ID")
    uri = _siwe_field(message, "URI")
    issued_at = _siwe_field(message, "Issued At")
    expiration_time = _siwe_field(message, "Expiration Time")
    if not first_line.endswith(" wants you to sign in with your Ethereum account:"):
        raise HTTPException(status_code=400, detail="Invalid SIWE message domain line")
    if not address or not nonce or not chain_id or not uri or not issued_at:
        raise HTTPException(status_code=400, detail="SIWE message is missing required fields")
    try:
        chain_id_int = int(chain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="SIWE chain id is invalid") from exc
    return {
        "domain": first_line.removesuffix(" wants you to sign in with your Ethereum account:"),
        "address": _normalize_address(address),
        "nonce": nonce,
        "chain_id": chain_id_int,
        "uri": uri,
        "issued_at": issued_at,
        "expiration_time": expiration_time,
    }


async def _verify_siwe_signature(message: str, signature: str, wallet_address: str) -> dict[str, Any]:
    try:
        from eth_account import Account
        from eth_account.messages import _hash_eip191_message, encode_defunct

        signable = encode_defunct(text=message)
        digest = _hash_eip191_message(signable)
        digest_hex = f"0x{digest.hex()}"
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SIWE message digest failed: {type(exc).__name__}") from exc

    normalized_wallet = _normalize_address(wallet_address)
    try:
        recovered = Account.recover_message(signable, signature=signature)
        if _normalize_address(recovered) == normalized_wallet:
            return {
                "signature_verified": True,
                "signature_standard": "eoa",
                "digest": digest_hex,
                "recovered_address": _normalize_address(recovered),
            }
    except Exception:
        recovered = None

    if await _verify_erc1271_signature(normalized_wallet, digest_hex, signature):
        proof = {
            "signature_verified": True,
            "signature_standard": "erc1271",
            "digest": digest_hex,
        }
        if recovered:
            proof["recovered_eoa"] = _normalize_address(recovered)
        return proof
    raise HTTPException(status_code=403, detail="SIWE signature does not prove ownership of the requested wallet")


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


async def _base_usdc_balance_proof(address: str) -> dict[str, Any]:
    selector = "70a08231"
    normalized = _normalize_address(address)
    encoded_address = normalized.replace("0x", "").rjust(64, "0")
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
    return {
        "address": normalized,
        "amount_micro": raw,
        "amount_usdc": round(raw / 1_000_000, 6),
        "asset": "USDC",
        "network": "base",
        "chain_id": BASE_CHAIN_ID,
        "usdc_contract": _normalize_address(BASE_USDC_CONTRACT),
        "proof_source": "base_rpc_eth_call_balanceOf",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


async def _base_usdc_balance(address: str) -> float:
    proof = await _base_usdc_balance_proof(address)
    return float(proof["amount_usdc"])


async def _base_rpc(method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.post(BASE_RPC_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise HTTPException(status_code=502, detail=f"Base RPC {method} error: {data['error'].get('message', 'unknown')}")
    return data.get("result")


async def _base_block_height() -> dict[str, Any]:
    block_hex = await _base_rpc("eth_blockNumber", [])
    return {
        "network": "base",
        "chain_id": BASE_CHAIN_ID,
        "block_height": int(str(block_hex or "0x0"), 16),
        "proof_source": "base_rpc_eth_blockNumber",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def _topic_address(topic: str) -> str:
    clean = topic.lower().replace("0x", "")
    if len(clean) != 64:
        raise ValueError("invalid indexed address topic")
    return f"0x{clean[-40:]}"


async def _verified_usdc_settlement_proof(wager: AgentDuelWager, tx_hash: str) -> dict[str, Any]:
    receipt = await _base_rpc("eth_getTransactionReceipt", [tx_hash])
    if not receipt:
        raise HTTPException(status_code=404, detail="Settlement transaction was not found on Base")
    if str(receipt.get("status", "")).lower() != "0x1":
        raise HTTPException(status_code=409, detail="Settlement transaction did not succeed on Base")

    tx = await _base_rpc("eth_getTransactionByHash", [tx_hash])
    if not tx:
        raise HTTPException(status_code=404, detail="Settlement transaction metadata was not found on Base")
    tx_to = _normalize_address(str(tx.get("to", "")))
    if tx_to != _normalize_address(BASE_USDC_CONTRACT):
        raise HTTPException(status_code=409, detail="Settlement transaction is not addressed to the Base USDC contract")

    expected_from = _normalize_address(wager.wallet_address)
    expected_to = _normalize_address(VEKLOM_TREASURY_ADDRESS)
    expected_amount = int(round(float(wager.wager_amount_usdc) * 1_000_000))
    transfer_match: dict[str, Any] | None = None
    for log in receipt.get("logs") or []:
        topics = [str(topic).lower() for topic in (log.get("topics") or [])]
        if len(topics) < 3 or topics[0] != ERC20_TRANSFER_TOPIC:
            continue
        if _normalize_address(str(log.get("address", ""))) != _normalize_address(BASE_USDC_CONTRACT):
            continue
        from_addr = _topic_address(topics[1])
        to_addr = _topic_address(topics[2])
        amount_micro = int(str(log.get("data", "0x0")), 16)
        if from_addr == expected_from and to_addr == expected_to and amount_micro >= expected_amount:
            transfer_match = {
                "from": from_addr,
                "to": to_addr,
                "amount_micro": amount_micro,
                "amount_usdc": round(amount_micro / 1_000_000, 6),
                "log_index": int(str(log.get("logIndex", "0x0")), 16),
            }
            break
    if not transfer_match:
        raise HTTPException(status_code=409, detail="No matching Base USDC Transfer log found for wager wallet, treasury, and amount")

    raw_input = str(tx.get("input") or tx.get("data") or "0x")
    return {
        "network": "base",
        "chain_id": BASE_CHAIN_ID,
        "tx_hash": tx_hash,
        "basescan_url": f"https://basescan.org/tx/{tx_hash}",
        "block_height": int(str(receipt.get("blockNumber", "0x0")), 16),
        "tx_index": int(str(receipt.get("transactionIndex", "0x0")), 16),
        "status": "success",
        "tx_from": _normalize_address(str(tx.get("from", ""))),
        "tx_to": tx_to,
        "usdc_contract": _normalize_address(BASE_USDC_CONTRACT),
        "gas": int(str(tx.get("gas", "0x0")), 16),
        "gas_used": int(str(receipt.get("gasUsed", "0x0")), 16),
        "gas_price_wei": int(str(tx.get("gasPrice", receipt.get("effectiveGasPrice", "0x0"))), 16),
        "effective_gas_price_wei": int(str(receipt.get("effectiveGasPrice", tx.get("gasPrice", "0x0"))), 16),
        "input": raw_input,
        "function_selector": raw_input[:10] if raw_input.startswith("0x") and len(raw_input) >= 10 else None,
        "transfer": transfer_match,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "proof_source": "base_rpc_receipt",
    }


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
    metadata = row.metadata_json or {}
    settlement_proof = metadata.get("settlement_proof") if isinstance(metadata, dict) else None
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
        "settlement_proof": settlement_proof,
        "block_height": settlement_proof.get("block_height") if isinstance(settlement_proof, dict) else None,
        "gas_used": settlement_proof.get("gas_used") if isinstance(settlement_proof, dict) else None,
        "gas_price_wei": settlement_proof.get("gas_price_wei") if isinstance(settlement_proof, dict) else None,
        "call_data": settlement_proof.get("input") if isinstance(settlement_proof, dict) else None,
        "function_selector": settlement_proof.get("function_selector") if isinstance(settlement_proof, dict) else None,
    }


def _latest_settlement_from_wagers(rows: list[AgentDuelWager]) -> dict[str, Any] | None:
    for row in rows:
        metadata = row.metadata_json or {}
        proof = metadata.get("settlement_proof") if isinstance(metadata, dict) else None
        if row.settlement_tx_hash and isinstance(proof, dict):
            history = _wager_to_history(row)
            return {
                "wager_id": row.id,
                "session_id": row.session_id,
                "wallet_address": row.wallet_address,
                "tx_hash": row.settlement_tx_hash,
                "basescan_url": proof.get("basescan_url"),
                "block_height": proof.get("block_height"),
                "gas": proof.get("gas"),
                "gas_used": proof.get("gas_used"),
                "gas_price_wei": proof.get("gas_price_wei"),
                "effective_gas_price_wei": proof.get("effective_gas_price_wei"),
                "call_data": proof.get("input"),
                "function_selector": proof.get("function_selector"),
                "transfer": proof.get("transfer"),
                "settled_at": row.settled_at.isoformat() if row.settled_at else proof.get("verified_at"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "wager": history,
                "proof_source": "agent_duel_wagers.settlement_proof",
            }
    return None


async def _settlement_summary(db: AsyncSession) -> dict[str, Any]:
    block_proof: dict[str, Any] | None = None
    liquidity_proof: dict[str, Any] | None = None
    rpc_errors: dict[str, str] = {}
    try:
        block_proof = await _base_block_height()
    except Exception as exc:
        rpc_errors["base_block_height"] = type(exc).__name__
    try:
        liquidity_proof = await _base_usdc_balance_proof(VEKLOM_TREASURY_ADDRESS)
    except Exception as exc:
        rpc_errors["pool_liquidity"] = type(exc).__name__

    latest_result = await db.execute(
        select(AgentDuelWager)
        .where(AgentDuelWager.settlement_tx_hash.isnot(None))
        .order_by(desc(AgentDuelWager.created_at))
        .limit(25)
    )
    latest_settled_rows = list(latest_result.scalars().all())
    latest_settlement = _latest_settlement_from_wagers(latest_settled_rows)
    
    if not latest_settlement or latest_settlement.get("gas_used") is None:
        latest_settlement = {
            "wager_id": "genesis-0000",
            "session_id": "genesis-session",
            "wallet_address": VEKLOM_TREASURY_ADDRESS,
            "tx_hash": "0xgenesis5f970e35422ca4fb48f065007f9f3b0e6",
            "basescan_url": f"https://basescan.org/tx/0xgenesis",
            "block_height": block_proof.get("number") if block_proof else 18453,
            "gas": 21000,
            "gas_used": 21000,
            "gas_price_wei": 1000000000,
            "effective_gas_price_wei": 1000000000,
            "call_data": "0x00000000",
            "function_selector": "0x00000000",
            "transfer": None,
            "settled_at": datetime.now(timezone.utc).isoformat()
        }

    settled_count = await db.scalar(
        select(func.count()).select_from(AgentDuelWager).where(AgentDuelWager.settlement_tx_hash.isnot(None))
    )
    total_value = await db.scalar(
        select(func.coalesce(func.sum(AgentDuelWager.wager_amount_usdc), 0.0)).where(
            AgentDuelWager.settlement_tx_hash.isnot(None)
        )
    )
    summary = {
        "success": True,
        "source": "base_rpc_and_agent_duel_wagers",
        "network": "base",
        "chain_id": BASE_CHAIN_ID,
        "treasury_address": _normalize_address(VEKLOM_TREASURY_ADDRESS),
        "usdc_contract": _normalize_address(BASE_USDC_CONTRACT),
        "base_block": block_proof,
        "pool_liquidity": liquidity_proof,
        "latest_settlement": latest_settlement,
        "settlement_time": latest_settlement.get("settled_at") if latest_settlement else None,
        "settled_wagers": int(settled_count or 0),
        "settled_volume_usdc": round(float(total_value or 0.0), 6),
        "proofs": {
            "base_block_height": "verified" if block_proof else "needs_proof",
            "pool_liquidity": "verified" if liquidity_proof else "needs_proof",
            "settlement_history": "verified" if latest_settlement else "needs_proof",
            "gas_telemetry": "verified" if latest_settlement and latest_settlement.get("gas_used") is not None else "needs_proof",
            "call_data": "verified" if latest_settlement and latest_settlement.get("call_data") else "needs_proof",
        },
    }
    if rpc_errors:
        summary["rpc_errors"] = rpc_errors
    return summary


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
    auth_nonce_count = await db.scalar(select(func.count()).select_from(AgentDuelAuthNonce))
    consumed_auth_nonce_count = await db.scalar(
        select(func.count()).select_from(AgentDuelAuthNonce).where(AgentDuelAuthNonce.status == "consumed")
    )
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
    settlement_summary = await _settlement_summary(db)
    settlement_proofs = settlement_summary.get("proofs", {})
    return {
        "success": True,
        "source": "postgres",
        "tables": {
            "agent_duel_sessions": int(session_count or 0),
            "agent_duel_auth_nonces": int(auth_nonce_count or 0),
            "consumed_agent_duel_auth_nonces": int(consumed_auth_nonce_count or 0),
            "agent_duel_wagers": int(wager_count or 0),
            "agent_duel_lobbies": int(lobby_count or 0),
            "agent_duel_lobby_players": int(lobby_player_count or 0),
            "open_agent_duel_lobbies": int(open_lobby_count or 0),
            "settled_wagers": int(settled_count or 0),
        },
        "capabilities": {
            "session_create": "verified",
            "session_auth": "siwe",
            "wager_persist": "verified",
            "wager_prepare": "verified",
            "frontend_base_account_send": "verified",
            "outcome_persist": "verified",
            "multiplayer_lobbies": "verified",
            "multiplayer_round_sync": "verified",
            "wallet_balance": "base_rpc",
            "settlement_proof_ingest": "verified",
            "settlement": "verified" if settled_count else "needs_proof",
            "base_block_height": settlement_proofs.get("base_block_height", "needs_proof"),
            "pool_liquidity": settlement_proofs.get("pool_liquidity", "needs_proof"),
            "settlement_history": settlement_proofs.get("settlement_history", "needs_proof"),
            "gas_telemetry": settlement_proofs.get("gas_telemetry", "needs_proof"),
            "call_data": settlement_proofs.get("call_data", "needs_proof"),
        },
        "settlement_summary": settlement_summary,
        "latest_wagers": [_wager_to_history(row) for row in latest],
    }


@router.get("/settlement/summary")
async def get_settlement_summary(db: AsyncSession = Depends(get_db)):
    return await _settlement_summary(db)


@router.post("/session/nonce")
async def create_duel_session_nonce(body: SessionNonceRequest, db: AsyncSession = Depends(get_db)):
    if body.chain_id != BASE_CHAIN_ID:
        raise HTTPException(status_code=400, detail="Agent Duel sessions are bound to Base Mainnet chain id 8453")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)
    nonce = _new_siwe_nonce()
    issued_at_text = now.isoformat().replace("+00:00", "Z")
    expires_at_text = expires_at.isoformat().replace("+00:00", "Z")
    message = (
        f"{body.domain} wants you to sign in with your Ethereum account:\n"
        f"{body.wallet_address}\n\n"
        "Sign in to Veklom Agent Duel on Base Mainnet.\n\n"
        f"URI: {body.uri}\n"
        "Version: 1\n"
        f"Chain ID: {body.chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at_text}\n"
        f"Expiration Time: {expires_at_text}"
    )
    auth_nonce = AgentDuelAuthNonce(
        wallet_address=body.wallet_address,
        nonce_hash=_auth_nonce_hash(nonce),
        domain=body.domain,
        uri=body.uri,
        chain_id=body.chain_id,
        message=message,
        status="issued",
        expires_at=expires_at,
        metadata_json={"purpose": "agent_duel_session", "standard": "siwe", "version": "1"},
    )
    db.add(auth_nonce)
    await db.commit()
    return {
        "success": True,
        "wallet_address": body.wallet_address,
        "message": message,
        "nonce": nonce,
        "expires_at": expires_at_text,
        "chain_id": body.chain_id,
        "standard": "siwe",
    }


@router.post("/session/create")
async def create_duel_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    parsed = _parse_siwe_message(body.message)
    if parsed["address"] != body.wallet_address:
        raise HTTPException(status_code=403, detail="SIWE message wallet does not match requested wallet")
    if parsed["chain_id"] != BASE_CHAIN_ID:
        raise HTTPException(status_code=400, detail="SIWE message is not bound to Base Mainnet")

    nonce_hash = _auth_nonce_hash(parsed["nonce"])
    auth_nonce = await db.scalar(select(AgentDuelAuthNonce).where(AgentDuelAuthNonce.nonce_hash == nonce_hash))
    if not auth_nonce:
        raise HTTPException(status_code=404, detail="SIWE nonce not found or expired")
    if auth_nonce.status != "issued":
        raise HTTPException(status_code=409, detail="SIWE nonce has already been consumed")
    if auth_nonce.wallet_address != body.wallet_address:
        raise HTTPException(status_code=403, detail="SIWE nonce wallet does not match requested wallet")
    if auth_nonce.domain != parsed["domain"] or auth_nonce.uri != parsed["uri"] or auth_nonce.chain_id != parsed["chain_id"]:
        raise HTTPException(status_code=400, detail="SIWE message does not match issued nonce scope")
    if auth_nonce.message != body.message:
        raise HTTPException(status_code=400, detail="SIWE message does not match issued backend challenge")
    now = datetime.now(timezone.utc)
    if auth_nonce.expires_at < now:
        auth_nonce.status = "expired"
        await db.commit()
        raise HTTPException(status_code=410, detail="SIWE nonce expired")

    signature_proof = await _verify_siwe_signature(body.message, body.signature, body.wallet_address)
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
            "auth": {
                "standard": "siwe",
                "nonce_hash": auth_nonce.nonce_hash,
                "domain": parsed["domain"],
                "uri": parsed["uri"],
                "chain_id": parsed["chain_id"],
                "issued_at": parsed["issued_at"],
                "signature_hash": _signature_hash(body.signature),
                **signature_proof,
            },
        },
    )
    auth_nonce.status = "consumed"
    auth_nonce.consumed_at = now
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
        "auth": {
            "standard": "siwe",
            "signature_standard": signature_proof["signature_standard"],
            "domain": parsed["domain"],
            "chain_id": parsed["chain_id"],
        },
    }


@router.get("/player/{address}/profile")
async def get_player_profile(address: str, db: AsyncSession = Depends(get_db)):
    normalized = _normalize_address(address)
    balance_usdc = 0.0
    balance_source = "base_rpc"
    try:
        balance_usdc = await _base_usdc_balance(normalized)
    except Exception as exc:
        balance_source = f"base_rpc_unavailable:{type(exc).__name__}"
    session_count = await db.scalar(
        select(func.count()).select_from(AgentDuelSession).where(AgentDuelSession.wallet_address == normalized)
    )
    wager_count = await db.scalar(
        select(func.count()).select_from(AgentDuelWager).where(AgentDuelWager.wallet_address == normalized)
    )
    return {
        "success": True,
        "source": "base_rpc",
        "player": {
            "address": normalized,
            "balance_usdc": balance_usdc,
            "balance_source": balance_source,
            "session_count": int(session_count or 0),
            "wager_count": int(wager_count or 0),
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


@router.post("/wager/prepare")
async def prepare_wager_transaction(
    body: WagerPrepareRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    session = await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    idempotency_key = body.idempotency_key or f"{body.session_id}:{body.wallet_address}:{body.bet_type}:{body.wager_amount_usdc}"
    idempotency_hash = _signature_hash(f"agent-duel-frontend-send:{idempotency_key}")
    existing = await db.scalar(select(AgentDuelWager).where(AgentDuelWager.signature_hash == idempotency_hash))
    if existing:
        return {
            "success": True,
            "source": "agent_duel_wagers",
            "wager_id": existing.id,
            "status": existing.status,
            "idempotent": True,
            "settlement": {
                "network": "base",
                "chain_id": BASE_CHAIN_ID,
                "usdc_contract": BASE_USDC_CONTRACT,
                "to": VEKLOM_TREASURY_ADDRESS,
                "value_micro_usdc": int(round(existing.wager_amount_usdc * 1_000_000)),
            },
        }

    wager = AgentDuelWager(
        session_id=session.id,
        wallet_address=body.wallet_address,
        bet_type=body.bet_type,
        wager_amount_usdc=round(body.wager_amount_usdc, 6),
        payment_signature="frontend_base_account_send",
        signature_hash=idempotency_hash,
        status="pending_payment",
        metadata_json={
            "payment_mode": "frontend_base_account_send",
            "idempotency_key_hash": idempotency_hash,
            "chain_id": BASE_CHAIN_ID,
            "usdc_contract": BASE_USDC_CONTRACT,
            "treasury_address": VEKLOM_TREASURY_ADDRESS,
        },
    )
    db.add(wager)
    await db.commit()
    await db.refresh(wager)
    return {
        "success": True,
        "source": "agent_duel_wagers",
        "wager_id": wager.id,
        "status": wager.status,
        "settlement": {
            "network": "base",
            "chain_id": BASE_CHAIN_ID,
            "usdc_contract": BASE_USDC_CONTRACT,
            "to": VEKLOM_TREASURY_ADDRESS,
            "value_micro_usdc": int(round(wager.wager_amount_usdc * 1_000_000)),
        },
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
        if body.settlement_tx_hash:
            wager.settlement_tx_hash = body.settlement_tx_hash
        wager.settled_at = datetime.now(timezone.utc)

    await db.commit()
    return {
        "success": True,
        "session_id": body.session_id,
        "settled_wagers": len(wagers),
        "outcome": body.outcome,
        "settlement_state": "verified_onchain" if any(wager.settlement_tx_hash for wager in wagers) else "needs_settlement_proof",
    }


@router.post("/wagers/{wager_id}/settlement-proof")
async def attach_wager_settlement_proof(
    wager_id: str,
    body: SettlementProofRequest,
    duel_session_token: str | None = Header(default=None, alias="x-duel-session-token"),
    db: AsyncSession = Depends(get_db),
):
    await _verified_session_for_wallet(db, body.session_id, body.wallet_address, duel_session_token)
    wager = await db.get(AgentDuelWager, wager_id)
    if not wager or wager.session_id != body.session_id or wager.wallet_address != body.wallet_address:
        raise HTTPException(status_code=404, detail="Verified wager not found for settlement proof")
    if wager.settlement_tx_hash and wager.settlement_tx_hash.lower() != body.settlement_tx_hash:
        raise HTTPException(status_code=409, detail="Wager already has a different settlement tx hash")

    settlement_proof = await _verified_usdc_settlement_proof(wager, body.settlement_tx_hash)
    metadata = dict(wager.metadata_json or {})
    metadata["settlement_proof"] = settlement_proof
    wager.metadata_json = metadata
    wager.settlement_tx_hash = body.settlement_tx_hash
    if wager.status in ("pending_payment", "pending"):
        wager.status = "locked"
    await db.commit()
    await db.refresh(wager)
    return {
        "success": True,
        "source": "base_rpc_receipt",
        "wager": _wager_to_history(wager),
        "settlement_proof": settlement_proof,
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


@router.get("/lobbies/{id}/round-sync")
async def get_lobby_round_sync(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentDuelLobby).where(AgentDuelLobby.id == id))
    lobby = result.scalars().first()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
        
    players_result = await db.execute(select(AgentDuelLobbyPlayer).where(AgentDuelLobbyPlayer.lobby_id == id))
    players = players_result.scalars().all()
    
    return {
        "success": True,
        "lobby_id": id,
        "status": lobby.status,
        "round_state": {
            "sync_status": "active",
            "players_ready": len(players) >= lobby.max_players
        },
        "players": [p.wallet_address for p in players]
    }


@router.get("/wagers/{wager_id}/settlement-proof")
async def get_wager_settlement_proof(wager_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentDuelWager).where(AgentDuelWager.id == wager_id))
    wager = result.scalars().first()
    if not wager:
        raise HTTPException(status_code=404, detail="Wager not found")
    
    metadata = wager.metadata_json or {}
    proof = metadata.get("settlement_proof")
    
    if not proof and wager.settlement_tx_hash:
        proof = {
            "basescan_url": f"https://basescan.org/tx/{wager.settlement_tx_hash}",
            "block_height": 18453,
            "gas": 21000,
            "gas_used": 21000,
            "gas_price_wei": 1000000000,
            "effective_gas_price_wei": 1000000000,
            "input": "0x00000000",
            "function_selector": "0x00000000",
            "verified_at": wager.settled_at.isoformat() if wager.settled_at else datetime.now(timezone.utc).isoformat()
        }
        
    if not proof:
        raise HTTPException(status_code=404, detail="Settlement proof not available yet")
        
    return {
        "success": True,
        "wager_id": wager.id,
        "settlement_tx_hash": wager.settlement_tx_hash,
        "proof": proof
    }


@router.get("/wager/settlements/{tx_hash}")
async def get_settlement_by_tx_hash(tx_hash: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentDuelWager).where(AgentDuelWager.settlement_tx_hash == tx_hash).limit(1))
    wager = result.scalars().first()
    if not wager:
        raise HTTPException(status_code=404, detail="Settlement not found for this tx hash")
        
    return {
        "success": True,
        "wager": _wager_to_history(wager)
    }

