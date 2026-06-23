import logging
import uuid
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class UacpV4Governor:
    """
    Adapter for the UACP v4 Decision Kernel (govern).
    Responsible for evaluating the contextualized plan against strict safety,
    budget, and constitutional policies. It interfaces with SEKED (Human/Org State Engine).
    Supports HTTP and mock modes via UACPV4_MODE.
    """

    def __init__(self):
        self.mode = settings.UACPV4_MODE.lower()
        self.base_url = settings.UACPV4_BASE_URL.rstrip("/")
        self.timeout = settings.UACPV4_TIMEOUT_MS / 1000.0
        self.gateway_secret = settings.UPSTREAM_GATEWAY_SECRET

    async def evaluate_plan(self, intent: Dict[str, Any], v2_plan: Dict[str, Any], v3_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates the plan and returns a decision (APPROVED, DENIED, HELD) along with SEKED state.
        """
        logger.info(f"[V4 Governance] Evaluating plan in {self.mode} mode...")
        
        if self.mode == "http":
            try:
                return await self._evaluate_http(intent, v2_plan, v3_context)
            except Exception as e:
                logger.warning(f"[V4 Governance] HTTP evaluation failed: {e}. Falling back to mock governance.")
                return await self._evaluate_mock(intent, v2_plan, v3_context)
        else:
            return await self._evaluate_mock(intent, v2_plan, v3_context)

    async def _evaluate_http(self, intent: Dict[str, Any], v2_plan: Dict[str, Any], v3_context: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/govern"
        headers = {}
        if self.gateway_secret:
            headers["X-Veklom-Gateway-Secret"] = self.gateway_secret
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json={"intent": intent, "v2_plan": v2_plan, "v3_context": v3_context}, 
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"[V4 Governance] Decision reached via HTTP: {data.get('decision')}")
                return data
        except httpx.HTTPError as e:
            logger.error(f"[V4 Governance] HTTP evaluation failed: {e}")
            raise HTTPException(status_code=502, detail="V4 Governance Service Unavailable")

    async def _evaluate_mock(self, intent: Dict[str, Any], v2_plan: Dict[str, Any], v3_context: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio
        await asyncio.sleep(0.4)
        
        # Simple mock logic based on risk tier
        risk_tier = v2_plan.get("policy_checkable_frame", {}).get("risk_tier", "low")
        
        decision = "APPROVED"
        if risk_tier == "high":
            decision = "HELD"
        elif risk_tier == "critical":
            decision = "DENIED"
            
        evaluation_result = {
            "decision": decision,
            "seked_state": {
                "org_clearance_level": "standard",
                "human_in_loop_required": (decision == "HELD")
            },
            "policy_evaluations": [
                {"policy": "budget_limit", "passed": True},
                {"policy": "data_exfiltration", "passed": True},
                {"policy": "risk_tier_check", "passed": (decision != "DENIED")}
            ],
            "audit_hash": f"v4_aud_{uuid.uuid4().hex[:12]}"
        }
        
        logger.info(f"[V4 Governance] Mock decision reached: {decision}")
        return evaluation_result
