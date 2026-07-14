import base64
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


REGION = os.getenv("VNP_REGION", "unknown")
SOFTWARE_VERSION = os.getenv("VNP_SOFTWARE_VERSION", "vnp-edge-probe:v1.1")
KEY_DIR = Path(os.getenv("VNP_KEY_DIR", "/state"))
KEY_FILE = KEY_DIR / "ed25519_private.pem"

app = FastAPI(title="VNP Edge Probe", version=SOFTWARE_VERSION)


class ProbeRequest(BaseModel):
    target_url: str = Field(default="https://api.veklom.com/health", max_length=512)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def load_or_create_private_key() -> ed25519.Ed25519PrivateKey:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        return serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)

    private_key = ed25519.Ed25519PrivateKey.generate()
    KEY_FILE.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(KEY_FILE, 0o600)
    return private_key


PRIVATE_KEY = load_or_create_private_key()
PUBLIC_KEY = PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
PUBLIC_KEY_B64 = base64.b64encode(PUBLIC_KEY).decode("ascii")
KEY_ID = f"vnp-edge:{REGION}:{hashlib.sha256(PUBLIC_KEY).hexdigest()[:16]}"


def sign_payload(payload: dict[str, Any]) -> dict[str, str]:
    signature = PRIVATE_KEY.sign(canonicalize(payload))
    return {
        "alg": "Ed25519",
        "key_id": KEY_ID,
        "public_key": PUBLIC_KEY_B64,
        "sig": base64.b64encode(signature).decode("ascii"),
    }


def require_hub_key(x_veklom_hub_key: str | None) -> None:
    expected = os.getenv("HUB_SECRET_KEY") or os.getenv("VNP_HUB_SECRET_KEY")
    if not expected or x_veklom_hub_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "region": REGION,
        "software_version": SOFTWARE_VERSION,
        "key_id": KEY_ID,
    }


@app.get("/identity")
async def identity(x_veklom_hub_key: str | None = Header(default=None)):
    require_hub_key(x_veklom_hub_key)
    payload = {
        "region": REGION,
        "software_version": SOFTWARE_VERSION,
        "key_id": KEY_ID,
        "public_key": PUBLIC_KEY_B64,
        "timestamp": utc_now(),
    }
    payload["signature"] = sign_payload(payload)
    return payload


@app.post("/probe/ping")
async def probe_ping(
    body: ProbeRequest,
    x_veklom_hub_key: str | None = Header(default=None),
):
    require_hub_key(x_veklom_hub_key)

    started_at = utc_now()
    started_monotonic = time.monotonic()
    status_code = None
    error_code = None
    success = False
    response_fingerprint = None

    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(str(body.target_url), timeout=8.0)
        status_code = response.status_code
        success = response.status_code in (200, 401, 403)
        response_fingerprint = hashlib.sha256(response.content[:512]).hexdigest()
    except Exception as exc:
        error_code = type(exc).__name__

    completed_at = utc_now()
    total_ms = int((time.monotonic() - started_monotonic) * 1000)
    payload = {
        "observation_id": f"{REGION}:{int(time.time() * 1000)}:{uuid.uuid4().hex[:8]}",
        "region": REGION,
        "status": "active" if success else "degraded",
        "target_url": str(body.target_url),
        "started_at": started_at,
        "completed_at": completed_at,
        "software_version": SOFTWARE_VERSION,
        "measurement": {
            "total_ms": total_ms,
            "status_code": status_code,
            "success": success,
            "error_code": error_code,
            "response_fingerprint": response_fingerprint,
        },
    }
    payload["signature"] = sign_payload(payload)
    return payload
