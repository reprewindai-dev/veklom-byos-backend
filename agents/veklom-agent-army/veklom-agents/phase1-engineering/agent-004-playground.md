# Agent-004 — PLAYGROUND ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Enhance the playground demo to convert visitors. The SSE streaming endpoint `/api/v1/demo/pipeline/run` works. Add preset prompts, share functionality, and upgrade CTAs.

## First Actions

```bash
cat backend/apps/api/routers/demo.py
# Test the live endpoint:
curl -N -X POST https://veklom.com/api/v1/demo/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze this text for sentiment"}'
```

## Tasks

### Task 1: Preset Prompt Library
```python
# Add to backend/apps/api/routers/demo.py
GET /api/v1/demo/presets
# Returns curated prompts showcasing Veklom capabilities:
PRESETS = [
    {"id": "compliance", "label": "HIPAA Compliance Check", 
     "prompt": "Check this patient record for PHI exposure: [sample text]"},
    {"id": "routing", "label": "Autonomous Model Routing",
     "prompt": "Route this workload to the optimal model based on cost and quality"},
    {"id": "audit", "label": "Tamper-Evident Audit Log",
     "prompt": "Generate an auditable decision log for this AI inference"},
    {"id": "sovereign", "label": "Sovereign Data Processing",
     "prompt": "Process this enterprise document with full data sovereignty"},
    {"id": "pipeline", "label": "Multi-Step Pipeline",
     "prompt": "Run a 3-step pipeline: extract → analyze → summarize"},
]
```

### Task 2: Shareable Demo Links
```python
POST /api/v1/demo/share
# body: { prompt, result_snapshot }
# Returns: { share_id, share_url }
# Share URL: https://veklom.com/demo?share={id}

GET /api/v1/demo/share/{id}
# Returns saved demo snapshot
```

### Task 3: Demo Usage Tracking
```python
# Log every demo run (no PII) for conversion analytics:
POST /api/v1/telemetry  # already exists — use it
# { event: "demo_run", preset_used, duration_ms, converted_to_signup }
```

### Task 4: Rate Limiting for Demo
```python
# Demo endpoint: 10 requests/hour/IP (unauthenticated)
# Authenticated: 50 requests/hour
# Over limit → return 429 with signup CTA in response body
```

## Success Metrics
| Metric | Target |
|---|---|
| Preset prompts available | 5+ |
| Share link generation | < 200ms |
| Demo → signup conversion | > 5% |
