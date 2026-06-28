import re

with open("backend/apps/api/routers/capi.py", "r") as f:
    content = f.read()

# Add asyncio import
if "import asyncio" not in content:
    content = content.replace("import uuid", "import uuid\nimport asyncio\nfrom fastapi.responses import StreamingResponse")

# Update evaluate_intent_governed signature
content = content.replace(
    "async def evaluate_intent_governed(\n    intent: ExecutionIntent,\n    db: AsyncSession,\n    workspace_id: str\n) -> Tuple[bool, str, int, dict]:",
    "async def evaluate_intent_governed(\n    intent: ExecutionIntent,\n    db: AsyncSession,\n    workspace_id: str,\n    q: asyncio.Queue = None\n) -> Tuple[bool, str, int, dict]:"
)

# Replace @router.post("/execute", response_model=ExecutionReceipt)
content = content.replace(
    "@router.post(\"/execute\", response_model=ExecutionReceipt)",
    "@router.post(\"/execute\")"
)

with open("backend/apps/api/routers/capi.py", "w") as f:
    f.write(content)
