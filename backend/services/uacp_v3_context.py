import logging
import uuid
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class UacpV3Contextualizer:
    """
    Adapter for the UACP v3 Contextual Brain (uacpv3).
    Responsible for fetching RAG data, embeddings, workspace memory,
    and agent limits before governance evaluation.
    Supports HTTP and mock modes via UACPV3_MODE.
    """

    def __init__(self):
        self.mode = settings.UACPV3_MODE.lower()
        self.base_url = settings.UACPV3_BASE_URL.rstrip("/")
        self.timeout = settings.UACPV3_TIMEOUT_MS / 1000.0
        self.gateway_secret = settings.UPSTREAM_GATEWAY_SECRET

    async def contextualize_plan(self, intent: Dict[str, Any], v2_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches the structured plan with required execution context.
        """
        logger.info(f"[V3 Context] Fetching execution context in {self.mode} mode...")
        
        if self.mode == "http":
            try:
                return await self._contextualize_http(intent, v2_plan)
            except Exception as e:
                logger.warning(f"[V3 Context] HTTP contextualization failed: {e}. Falling back to mock contextualizer.")
                return await self._contextualize_mock(intent, v2_plan)
        else:
            return await self._contextualize_mock(intent, v2_plan)

    async def _contextualize_http(self, intent: Dict[str, Any], v2_plan: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/contextualize"
        headers = {}
        if self.gateway_secret:
            headers["X-Veklom-Gateway-Secret"] = self.gateway_secret
            
        from backend.apps.api.routers.protocol import MANIFEST
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json={"intent": intent, "v2_plan": v2_plan, "manifest": MANIFEST}, 
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"[V3 Context] Successfully fetched context via HTTP.")
                return data
        except httpx.HTTPError as e:
            logger.error(f"[V3 Context] HTTP contextualization failed: {e}")
            raise HTTPException(status_code=502, detail="V3 Context Service Unavailable")

    async def _contextualize_mock(self, intent: Dict[str, Any], v2_plan: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio
        await asyncio.sleep(0.3)
        
        context_id = f"ctx_{uuid.uuid4().hex[:12]}"
        
        enriched_context = {
            "context_id": context_id,
            "status": "contextualized",
            "workspace_memory": {
                "recent_files": ["src/main.py", "README.md"],
                "active_git_branch": "main"
            },
            "rag_embeddings": [
                {"source": "documentation", "relevance": 0.95, "content": "Veklom run rules..."}
            ],
            "execution_limits": {
                "max_tokens_allowed": 8000,
                "timeout_ms": 30000
            }
        }
        
        logger.info(f"[V3 Context] Successfully generated mock context: {context_id}")
        return enriched_context
