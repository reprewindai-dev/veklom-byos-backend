import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/security", tags=["Security Posture"])

NOT_VERIFIED = "NOT_VERIFIED"
OBSERVED = "OBSERVED"
UNAVAILABLE = "UNAVAILABLE"
UNCONFIGURED = "UNCONFIGURED"
REACHABLE_NOT_VERIFIED = "REACHABLE_NOT_VERIFIED"


def get_kernel_isolation_status() -> dict:
    """Report only the Linux capability state observable in this process.

    Effective capabilities are not proof of gVisor, seccomp, namespace isolation,
    kernel-patch level, or mitigation of a named vulnerability.
    """
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith("CapEff:"):
                    cap_eff = line.split(":", 1)[1].strip()
                    return {
                        "status": OBSERVED,
                        "cap_eff_hex": cap_eff,
                        "zero_effective_capabilities": cap_eff == "0000000000000000",
                        "isolation_runtime": NOT_VERIFIED,
                        "threat_mitigation": NOT_VERIFIED,
                    }
    except OSError:
        pass

    return {
        "status": UNAVAILABLE,
        "cap_eff_hex": None,
        "zero_effective_capabilities": None,
        "isolation_runtime": NOT_VERIFIED,
        "threat_mitigation": NOT_VERIFIED,
    }


def get_proxy_status() -> dict:
    """Do not infer the live ingress/proxy from application source."""
    return {
        "status": NOT_VERIFIED,
        "active_proxy": None,
        "traefik_routing_verified": False,
        "request_desync_mitigation": NOT_VERIFIED,
        "evidence_required": "live ingress configuration and routed HTTP verification",
    }


def get_supply_chain_status() -> dict:
    """Source presence alone does not prove CI/security controls executed."""
    return {
        "status": NOT_VERIFIED,
        "ast_scanning_active": None,
        "dynamic_eval_blocked": None,
        "dependency_scan_verified": False,
        "secret_scan_verified": False,
        "codeql_verified": False,
        "evidence_required": "current-head security workflow results",
    }


def get_ollama_sanitization_status() -> dict:
    """Describe intended configuration without claiming downstream enforcement."""
    return {
        "status": NOT_VERIFIED,
        "middleware": None,
        "context_retention": NOT_VERIFIED,
        "keep_alive_zero_verified": False,
        "evidence_required": "deployed CAPPO request/response evidence",
    }


async def check_lockerphycer_health() -> dict:
    """Perform a bounded reachability probe without promoting security claims."""
    base_url = os.getenv("LOCKERPHYCER_URL")
    if not base_url:
        return {
            "status": UNCONFIGURED,
            "reachable": False,
            "http_status": None,
            "protocol_identity_verified": False,
            "ids_active": NOT_VERIFIED,
        }

    try:
        async with httpx.AsyncClient(timeout=1.0, follow_redirects=False) as client:
            response = await client.get(f"{base_url.rstrip('/')}/health")
        return {
            "status": REACHABLE_NOT_VERIFIED if response.is_success else UNAVAILABLE,
            "reachable": response.is_success,
            "http_status": response.status_code,
            "protocol_identity_verified": False,
            "ids_active": NOT_VERIFIED,
        }
    except httpx.HTTPError:
        return {
            "status": UNAVAILABLE,
            "reachable": False,
            "http_status": None,
            "protocol_identity_verified": False,
            "ids_active": NOT_VERIFIED,
        }


@router.get("/posture")
async def get_security_posture():
    """Return observed evidence and explicit verification gaps only."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": NOT_VERIFIED,
        "verified_runtime_state": {},
        "unverified_claims": [
            "container isolation runtime",
            "Traefik routing",
            "supply-chain security workflow execution",
            "Ollama context sanitization",
            "Lockerphycer protocol identity and IDS state",
        ],
        "observations": {
            "kernel_capabilities": get_kernel_isolation_status(),
            "proxy_security": get_proxy_status(),
            "supply_chain_defense": get_supply_chain_status(),
            "ollama_context": get_ollama_sanitization_status(),
            "lockerphycer": await check_lockerphycer_health(),
        },
    }
