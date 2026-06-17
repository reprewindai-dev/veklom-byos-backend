# Memory Schema

## Standard Memory Entry
```json
{
  "memory": "The content of what was learned/decided",
  "user_id": "agent-001",
  "metadata": {
    "agent_id": "001",
    "category": "learning|decision|blocker|pattern|handoff",
    "task": "stripe_connect",
    "timestamp": "ISO8601",
    "confidence": 0.9,
    "source": "direct_experience|research|agent_handoff"
  }
}
```

## Session Handoff Protocol
At the END of every session, every agent MUST store:
```python
memory.add(
    f"Session summary: completed [X], next session should [Y], blockers: [Z]",
    user_id=f"agent-{agent_id}",
    metadata={"category": "handoff", "session_date": "ISO8601"}
)
```

At the START of every session, every agent MUST retrieve:
```python
memories = memory.search(
    query="recent progress blockers next steps",
    user_id=f"agent-{agent_id}",
    top_k=10
)
```

## Institutional Memory (cross-agent)
Some memories are shared across all agents:
```python
# Store as user_id="veklom_workforce" for cross-agent access
memory.add(
    "Production deploy: always use AGENT_HANDSHAKE_BRIEF_V2.md deploy protocol",
    user_id="veklom_workforce",
    metadata={"category": "pattern", "scope": "global"}
)
```
