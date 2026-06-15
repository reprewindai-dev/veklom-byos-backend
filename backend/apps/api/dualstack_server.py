import asyncio
import os
import uvicorn

async def _serve() -> None:
    port = int(os.getenv("PORT", "8088"))
    config = uvicorn.Config(
        "backend.apps.api.main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(_serve())
