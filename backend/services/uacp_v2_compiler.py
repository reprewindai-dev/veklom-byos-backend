import logging
import uuid
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class UacpV2Compiler:
    """
    Adapter for the UACP v2 Plan Compiler (uacpgemini).
    Responsible for turning raw intent into a structured, bounded plan
    before execution. Supports HTTP and mock modes via UACPGEMINI_MODE.
    """

    def __init__(self):
        self.mode = settings.UACPGEMINI_MODE.lower()
        self.base_url = settings.UACPGEMINI_BASE_URL.rstrip("/")
        self.timeout = settings.UACPGEMINI_TIMEOUT_MS / 1000.0

    async def compile_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compiles the raw intent into a bounded plan and task graph.
        """
        logger.info(f"[V2 Compiler] Compiling raw intent into bounded plan in {self.mode} mode...")
        
        if self.mode == "http":
            try:
                return await self._compile_http(intent)
            except Exception as e:
                logger.warning(f"[V2 Compiler] HTTP compilation failed: {e}. Falling back to mock compiler.")
                return await self._compile_mock(intent)
        else:
            return await self._compile_mock(intent)

    async def _compile_http(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/compile"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json={"intent": intent}, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"[V2 Compiler] Successfully compiled plan via HTTP.")
                return data
        except httpx.HTTPError as e:
            logger.error(f"[V2 Compiler] HTTP compilation failed: {e}")
            raise HTTPException(status_code=502, detail="V2 Compiler Service Unavailable")

    async def _compile_mock(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio
        await asyncio.sleep(0.5)
        
        plan_hash = f"plan_{uuid.uuid4().hex[:16]}"
        
        compiled_plan = {
            "plan_hash": plan_hash,
            "status": "compiled",
            "task_graph": {
                "nodes": [
                    {"id": "task_1", "type": "initialization", "dependencies": []},
                    {"id": "task_2", "type": "execution", "dependencies": ["task_1"]}
                ]
            },
            "required_scopes": ["read_workspace", "execute_tool"],
            "policy_checkable_frame": {
                "estimated_tokens": 1200,
                "risk_tier": "low"
            }
        }
        
        logger.info(f"[V2 Compiler] Successfully compiled mock plan with hash: {plan_hash}")
        return compiled_plan
