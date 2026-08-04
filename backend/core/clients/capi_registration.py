import httpx
import logging
import asyncio
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

async def register_with_capi() -> None:
    """Registers BYOS backend capabilities with the cAPI Universal USB layer."""
    if not settings.CAPI_BACKEND_URL:
        logger.info("[cAPI] Registration skipped: CAPI_BACKEND_URL is not set.")
        return
        
    url = f"{settings.CAPI_BACKEND_URL.rstrip('/')}/api/v1/registry/register"
    headers = {"Content-Type": "application/json"}
    if settings.CAPI_API_KEY:
        headers["Authorization"] = f"Bearer {settings.CAPI_API_KEY}"
        
    payload = {
        "service_name": "veklom-byos-backend-2",
        "capabilities": ["execution", "routing", "inference", "telemetry"],
        "telemetry_supported": True
    }
    
    import socket
    from urllib.parse import urlparse

    # DNS Fallback logic for gaierror Name resolution
    parsed = urlparse(url)
    try:
        # Try to resolve the hostname explicitly to catch DNS errors early
        socket.gethostbyname(parsed.hostname)
    except socket.gaierror:
        logger.warning(f"[cAPI] DNS resolution failed for {parsed.hostname}. Falling back to internal Docker network (capi-container).")
        # Swap hostname for 'capi-container' (default Coolify internal name)
        url = url.replace(parsed.hostname, "capi-container")

    # Retry registration periodically until success
    for attempt in range(5):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=5.0)
                if response.status_code in (200, 201):
                    logger.info("[cAPI] Successfully registered BYOS with cAPI.")
                    return
                else:
                    logger.warning(f"[cAPI] Failed to register: {response.text}")
        except Exception as e:
            logger.error(f"[cAPI] Error registering with cAPI (attempt {attempt + 1}): {type(e).__name__} - {e}")
            
        await asyncio.sleep(5)
