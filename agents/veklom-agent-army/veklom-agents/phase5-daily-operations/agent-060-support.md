# Agent-060 — SUPPORT AGENT

**Phase:** 5 — Daily Operations (from Day 3)
**Committee:** Operations
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Run in-app and community support. The support bot router exists at `backend/apps/api/routers/support_bot.py`. Enhance it with FAQ knowledge base, ticket routing, escalation workflows.

## First Actions

```bash
cat backend/apps/api/routers/support_bot.py
curl -s https://veklom.com/api/v1/support/status \
  -H "Authorization: Bearer $TOKEN"
```

## Tasks

### Task 1: FAQ Knowledge Base
```python
# Create: backend/apps/api/data/faq.json
# Minimum 20 entries covering:
# - How to create API key
# - How to connect private model (Ollama/vLLM)
# - How to read audit logs
# - Billing/subscription questions
# - How to set budget limits
# - Data sovereignty — where does data go?
```

### Task 2: Auto-Response Engine
```python
GET /api/v1/support/faq?q={query}
# → semantic search over FAQ knowledge base
# → returns top 3 matches with confidence scores
# → if confidence > 0.85: auto-respond
# → if confidence < 0.85: create support ticket
```

### Task 3: Ticket System
```python
POST /api/v1/support/tickets       # create ticket
GET  /api/v1/support/tickets       # list user's tickets
GET  /api/v1/support/tickets/{id}  # single ticket + thread
POST /api/v1/support/tickets/{id}/reply  # add reply
```

### Task 4: Escalation Rules
```python
# Auto-escalate to human when:
# - Keyword: "billing", "charge", "refund", "breach", "data leak"
# - Ticket open > 24 hours without response
# - User has paying subscription (priority queue)
```

## Success Metrics
| Metric | Target |
|---|---|
| Auto-resolution rate | > 60% |
| First response time (human) | < 4 hours |
| Ticket resolution time | < 24 hours |
