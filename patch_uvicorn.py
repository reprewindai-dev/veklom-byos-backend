import re

with open("backend/apps/api/dualstack_server.py", "r") as f:
    content = f.read()

# Add worker parameter to Uvicorn config
new_config = """
    import multiprocessing
    workers = int(os.getenv("MAX_WORKERS", multiprocessing.cpu_count() * 2 + 1))

    config = uvicorn.Config(
        "backend.apps.api.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
"""

content = re.sub(
    r'    config = uvicorn\.Config\([\s\S]*?forwarded_allow_ips="\*"\n    \)',
    new_config.strip(),
    content
)

with open("backend/apps/api/dualstack_server.py", "w") as f:
    f.write(content)
