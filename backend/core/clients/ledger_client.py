import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Fetch internal URL for the Ledger Service (Node 2)
LEDGER_INTERNAL_URL = os.getenv("LEDGER_INTERNAL_URL", "http://ledger:8003")

class LedgerClient:
    """
    Unified HTTP client for Node 1 (Control) and Node 3 (CAPI) 
    to communicate securely with Node 2 (Ledger) for settlement and identity.
    """
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        
    async def _post(self, path: str, payload: dict) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{LEDGER_INTERNAL_URL}{path}", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Ledger client HTTP error {e.response.status_code} for {path}: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Ledger client connection error for {path}: {e}")
                return None

    async def verify_budget(self, workspace_id: str, cost_estimate: float) -> bool:
        """Query the ledger to see if the workspace has sufficient balance."""
        res = await self._post("/api/v1/ledger/budget/verify", {
            "workspace_id": workspace_id,
            "cost_estimate": cost_estimate
        })
        if res and res.get("allowed"):
            return True
        return False

    async def reserve_funds(self, workspace_id: str, amount: float, reason: str) -> Optional[str]:
        """Reserve funds in the wallet transaction ledger."""
        res = await self._post("/api/v1/ledger/wallet/reserve", {
            "workspace_id": workspace_id,
            "amount": amount,
            "reason": reason
        })
        return res.get("transaction_id") if res else None

    async def settle_funds(self, transaction_id: str, final_amount: float, status: str) -> bool:
        """Settle a previously reserved transaction."""
        res = await self._post("/api/v1/ledger/wallet/settle", {
            "transaction_id": transaction_id,
            "final_amount": final_amount,
            "status": status
        })
        return res.get("success", False) if res else False

    async def record_audit_log(self, workspace_id: str, agent_id: str, action: str, details: dict) -> bool:
        """Append an immutable log to the AIAuditLog ledger."""
        res = await self._post("/api/v1/ledger/audit/log", {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "action": action,
            "details": details
        })
        return res.get("success", False) if res else False

# Singleton instance
ledger_client = LedgerClient()
