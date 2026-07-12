import logging
from typing import Callable, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class CappoPolicyMiddleware(BaseHTTPMiddleware):
    """
    CAPPO 2.0 Zero-Trust Policy Middleware.
    Sits above AmphotericMiddleware. Enforces strict default-deny rules
    for missing identity, missing policy, or missing attestation on governed routes.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        # Only enforce CAPPO on governed execution routes
        governed_prefixes = ("/api/v1/cappo", "/api/v1/capi")
        is_governed = any(path.startswith(prefix) for prefix in governed_prefixes)
        
        if not is_governed:
            return await call_next(request)
            
        # Extract Amphoteric contexts
        transport = getattr(request.state, "transport", None)
        trace = getattr(request.state, "trace", None)
        
        if not transport or not trace:
            logger.error(f"[CAPPO] VETO: Missing amphoteric context on {path}")
            return self._build_deny_response("MISSING_AMPHOTERIC_CONTEXT", "Request lacks required transport/trace contexts.")
            
        # 1. Identity Check
        if not transport.spiffe_verified:
            if not getattr(settings, "DEBUG_MOCK_SPIFFE", False):
                logger.error(f"[CAPPO] VETO: Unverified SPIFFE identity on {path}")
                return self._build_deny_response("MISSING_SPIFFE_IDENTITY", "Cryptographic identity could not be verified by SPIRE.")
                
        # 2. RepoGate Attestation Check
        # Suppose trace context holds repogate attestation state
        if trace.repo_gate_status != "verified":
            if not getattr(settings, "DEBUG_MOCK_REPOGATE", False):
                logger.error(f"[CAPPO] VETO: Missing RepoGate attestation on {path}")
                return self._build_deny_response("MISSING_REPOGATE_ATTESTATION", "Request lacks verified RepoGate attestation.")

        # Let the route handler run. The route handler will run the full 9-Phase evaluate_intent_governed 
        # engine for deep payload/budget evaluation.
        response = await call_next(request)
        return response

    def _build_deny_response(self, code: str, message: str) -> JSONResponse:
        """Constructs a deterministic, clean evidence record of the denial."""
        import uuid
        from datetime import datetime, timezone
        
        evidence_id = f"EV-DENY-{uuid.uuid4().hex[:8]}"
        return JSONResponse(
            status_code=403,
            content={
                "status": "security_blocked",
                "error_code": code,
                "message": message,
                "evidence_record": {
                    "id": evidence_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "verdict": "DENIED",
                    "reason": code,
                    "enforcer": "cappo_policy_middleware_v2"
                }
            }
        )
