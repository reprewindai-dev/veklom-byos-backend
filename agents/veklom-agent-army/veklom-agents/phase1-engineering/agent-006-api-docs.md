# Agent-006 — API DOCS ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** MEDIUM
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Create public developer documentation. OpenAPI/Swagger is currently auth-gated and disabled in production. Build a public docs site at `https://veklom.com/docs`.

## First Actions

```bash
cat backend/apps/api/main.py  # find OpenAPI config, see if docs disabled
# Look for: app = FastAPI(docs_url=None...) or similar
curl -s https://veklom.com/openapi.json  # test if accessible
```

## Tasks

### Task 1: Enable Public OpenAPI
```python
# File: backend/apps/api/main.py
# Change docs endpoint to public (read-only, no auth required):
app = FastAPI(
    title="Veklom BYOS API",
    version="1.0.0",
    docs_url="/docs",          # re-enable Swagger UI
    redoc_url="/redoc",        # re-enable ReDoc
    openapi_url="/openapi.json"
)
```

### Task 2: Enrich All Route Docstrings
```python
# Every router must have summary + description:
@router.post("/exec", summary="Execute AI Inference",
    description="SSE streaming inference with policy enforcement. "
                "Supports OpenAI-compatible message format.")
async def execute(request: ExecRequest, ...):
```

### Task 3: Static Docs Site
```bash
# Generate static HTML from OpenAPI spec:
# File: scripts/generate-docs.sh
npx @redocly/cli build-docs openapi.json \
  --output frontend/sovereign-control-node/out/docs/index.html
```

### Task 4: SDK Quickstart Docs
```markdown
# Create: docs/quickstart.md
## Python SDK Quickstart
pip install veklom-sdk

from veklom import VeklomClient
client = VeklomClient(api_key="vk_...")
response = client.exec("Summarize this document")

## Authentication Guide
## Webhook Integration Guide
## Cost Management Guide
```

## Success Metrics
| Metric | Target |
|---|---|
| All 43 router endpoints documented | 100% |
| Public docs accessible at /docs | Yes |
| SDK quickstart guide | Complete |
