import httpx
import logging
from typing import Dict, Any, Optional
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class CAPIClient:
    """Client for communicating with the cAPI Universal USB layer."""
    
    def __init__(self):
        self.base_url = settings.CAPI_BACKEND_URL
        self.api_key = settings.CAPI_API_KEY
        self.timeout = 5.0
        
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    async def resolve_tenant_workspace(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Resolves tenant ID to a workspace ID via cAPI PGL resolution."""
        if not self.base_url:
            logger.warning("[cAPI Client] No CAPI_BACKEND_URL configured. Skipping tenant resolution.")
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/resolve/tenant/{tenant_id}",
                    headers=self._headers(),
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"[cAPI Client] Tenant resolution failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"[cAPI Client] Exception during tenant resolution: {str(e)}")
            return None
            
capi_client = CAPIClient()
