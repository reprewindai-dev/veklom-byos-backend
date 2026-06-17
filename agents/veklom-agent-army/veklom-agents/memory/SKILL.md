---
name: veklom-memory
description: Agent memory system powered by mem0. Load when an agent needs to store learnings, retrieve past decisions, or maintain context across sessions.
metadata:
  version: 1.0.0
  backend: mem0-self-hosted
  vector_store: pgvector (PostgreSQL already running)
  linked_files:
    - memory-schema.md
    - retrieval-guide.md
---

# Veklom Agent Memory Skill

## What This Does
Persistent memory for all 120 agents using mem0 (self-hosted).
- Every agent stores decisions, learnings, blockers
- Future sessions pick up from where the last left off
- Powered by mem0 self-hosted + pgvector in existing PostgreSQL

## Setup (run once on server)
```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11

# mem0 self-hosted (uses existing Docker stack)
pip install mem0ai
# OR use the API endpoint once wired into Veklom backend
```

## Basic Usage Per Agent
```python
from mem0 import Memory

# Initialize with existing PostgreSQL
memory = Memory.from_config({
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": "llwfyzhnft87bz6brddiax1z",  # container name
            "port": 5432,
            "database": "veklom",
            "user": "postgres",
            "password": os.getenv("POSTGRES_PASSWORD")
        }
    }
})

# Store a learning
memory.add(
    "Discovered that webhook verification fails if content-type header is missing",
    user_id="agent-001",  # agent_id as user_id
    metadata={"agent_id": "001", "category": "learning", "task": "stripe_webhooks"}
)

# Retrieve before starting a task
memories = memory.search(
    query="Stripe webhook issues",
    user_id="agent-001",
    top_k=5
)
for m in memories["results"]:
    print(f"- {m['memory']}")
```

## Memory Categories
- learning: "I discovered X works / X fails"
- decision: "I chose to implement X because Y"
- blocker: "Task blocked waiting on Agent-XXX"
- pattern: "Best practice for this domain"
- handoff: "Next session should start with..."

## When to Load Sub-Files
- Understanding schema → load memory-schema.md
- Retrieval strategies → load retrieval-guide.md
