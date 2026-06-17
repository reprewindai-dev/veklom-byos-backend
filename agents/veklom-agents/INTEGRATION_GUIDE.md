# Integration Guide — How Everything Connects

## The 4-Layer Stack

```
Layer 1: BIRTH (GnomLedger)
  ↓ agent identity, lineage, jurisdiction, risk class
  ↓ hash-chained ledger events
  ↓ compliance packets for regulators

Layer 2: SKILLS (SKILL.md progressive disclosure)
  ↓ governance/SKILL.md
  ↓ engineering/SKILL.md → links to deploy-runbook.md, api-reference.md, etc.
  ↓ Each agent loads ONLY the skills for its committee
  ↓ Sub-files loaded on-demand (progressive disclosure)

Layer 3: MEMORY (mem0 self-hosted)
  ↓ Per-agent memory namespace (user_id = "agent_XXX")
  ↓ Shared institutional memory (user_id = "veklom_workforce")
  ↓ Session handoffs, learnings, decisions, blockers
  ↓ Powered by pgvector in existing PostgreSQL

Layer 4: AUTHORITY (authority bundles)
  ↓ Per-role MCP tool grants
  ↓ Denied tools list (least privilege)
  ↓ Approval-required tools (human-in-loop)
  ↓ All calls audit-logged
```

## How to Spin Up an Agent (Devin/Claude Code)

```bash
# 1. Read AGENT_HANDSHAKE_BRIEF_V2.md FIRST (always)
cat agents/AGENT_HANDSHAKE_BRIEF_V2.md

# 2. Read your mission file
cat agents/[phase]/agent-XXX-[role].md

# 3. Load your committee skill
# (It tells you which sub-files to load for your task)

# 4. Retrieve memory from last session
curl -X POST https://veklom.com/api/v1/agent-memory/XXX/recall   -H "Authorization: Bearer $TOKEN"   -d '{"query": "recent progress blockers next steps"}'

# 5. Check your authority bundle
cat agents/authority-bundles/auth_[your_bundle].json

# 6. Execute tasks

# 7. Store session memory before ending
curl -X POST https://veklom.com/api/v1/agent-memory/XXX/remember   -H "Authorization: Bearer $TOKEN"   -d '{"content": "Completed X, next session do Y", "category": "handoff"}'

# 8. Update PROGRESS.md
```

## OpenRouter Multi-Model Execution

```bash
# Run any agent
OPENROUTER_API_KEY=sk-or-... npx tsx agents/enforcement/agent_runner.ts \
  --agent agent-001 \
  --task "Complete Stripe Connect webhook verification"

# Model selection is automatic per agent role
# Engineer agents: claude-sonnet-4-5
# Commander: claude-opus-4-5
# Research: openrouter/auto (best model for task)
# Growth: gemini-2.5-flash (fast, cheap)
```

## mem0 Memory Deployment

```bash
# Deploy on Hetzner (uses existing PostgreSQL)
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11

pip install mem0ai
pip install mem0ai[nlp]
python -m spacy download en_core_web_sm

# Wire into backend:
cp agents/memory/veklom_memory_backend.py backend/apps/api/services/agent_memory.py
# Add router to main.py
# Set env vars: OPENAI_API_KEY (for embeddings)
```

## GnomLedger Integration

```bash
# Register each agent's birth certificate
# Use birth-certificate-schema.md as the template
# Store in: github.com/reprewindai-dev/gnomledger

# For each agent:
# 1. Fill schema with agent identity fields
# 2. Generate SHA-256 hash of genome content
# 3. Create birth_registration ledger event
# 4. Submit to GnomLedger
```

## Browser-Use Integration (for browser agents 090-093)

```bash
pip install browser-use
playwright install chromium

# Each browser agent uses:
from browser_use import Browser
browser = Browser()
# → navigates https://veklom.com
# → fills forms, clicks buttons, captures screenshots
# → stores evidence in playwright-report/agent-09X/
```

## RAGFlow Integration (for RAG agents 108-113)

```bash
# RAGFlow for document indexing
# Deploy via Docker or use the API
# Agent-109 (Document Indexer) points at:
# - agents/*.md (all mission files)
# - backend/docs/ (API docs)
# - support tickets (via Agent-060)
# - marketplace listings

# RAGFlow provides: chunking, embedding, retrieval
# Agent-112 (Agent Memory) handles: cross-session agent context
```

## Authority Bundle Enforcement (UACP)

```
Every tool call route:
1. Agent calls tool via MCP
2. UACP checks: is tool in agent's authority_bundle.allowed_tools?
3. If denied: reject, log violation to Agent-079
4. If approval_required: pause, notify approver, wait
5. If allowed: execute, log to audit trail
6. Audit event appended to agent's GnomLedger
```
