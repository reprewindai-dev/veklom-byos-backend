import asyncio
import os
import multiprocessing
import uvicorn

async def _serve() -> None:
    port = int(os.getenv("PORT", "80"))
    workers = int(os.getenv("MAX_WORKERS", multiprocessing.cpu_count() * 2 + 1))

    config = uvicorn.Config(
        "backend.apps.api.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(_serve())
