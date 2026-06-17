# Agent-110 — SEMANTIC SEARCH (RAG)

**Phase:** Cross-phase — Knowledge
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Build and maintain the semantic search engine. Handle query embedding, vector similarity search, hybrid search (semantic + keyword), and relevance reranking. Power both the platform search and agent knowledge retrieval.

## Search Architecture

```
Query → Preprocessing → Embedding → Vector Search (top-50)
                                         ↓
                              BM25 Keyword Search (top-50)
                                         ↓
                                   Reciprocal Rank Fusion
                                         ↓
                                  Cross-Encoder Rerank (top-10)
                                         ↓
                                    Final Results (top-5)
```

## API Endpoints

```python
# Search endpoint for agents and platform
@router.post("/api/v1/search")
async def semantic_search(
    query: str,
    doc_types: list[str] = None,  # filter by type
    top_k: int = 5,
    hybrid: bool = True,  # combine semantic + keyword
    rerank: bool = True
) -> list[SearchResult]:
    ...
```

## Search Modes

| Mode | Use Case |
|---|---|
| Semantic only | "How do I deploy a model?" — meaning-based |
| Keyword only | "error 500 stripe webhook" — exact match |
| Hybrid (default) | Best of both — most queries |
| Agent context | Agent asking for relevant mission files |

## Tasks

1. Implement vector similarity search with pgvector
2. Add BM25 keyword search alongside
3. Implement reciprocal rank fusion for hybrid results
4. Add cross-encoder reranking for precision
5. Build search API endpoint
6. Add search analytics (query logging, click-through)

## Success Metrics

| Metric | Target |
|---|---|
| Search relevance (MRR@5) | > 0.7 |
| Query latency (p95) | < 300ms |
| Hybrid vs semantic-only improvement | > 15% |
| Zero-result rate | < 5% |

## Dependencies

- Agent-108 (RAG lead), Agent-109 (document indexer — provides index)
