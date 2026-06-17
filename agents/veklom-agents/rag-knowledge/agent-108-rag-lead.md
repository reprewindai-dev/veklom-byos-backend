# Agent-108 — RAG LEAD (Retrieval-Augmented Generation)

**Phase:** Cross-phase — Knowledge & Intelligence
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Lead the RAG agent squad. These agents build and maintain the knowledge infrastructure — document indexing, embedding pipelines, semantic search, and retrieval-augmented generation for both the platform and the agent workforce itself.

## Managed Agents

| Agent | Specialization |
|---|---|
| Agent-109 | Document Indexer — ingest, chunk, embed all platform docs |
| Agent-110 | Semantic Search — query engine, relevance ranking, hybrid search |
| Agent-111 | Knowledge Synthesizer — summarize, cross-reference, generate insights |
| Agent-112 | Agent Memory — maintain shared agent memory and context across sessions |
| Agent-113 | Customer Support RAG — power support chatbot with product knowledge |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 RAG Pipeline                     │
│                                                  │
│  Sources → Chunking → Embedding → Vector Store   │
│                                                  │
│  Query → Embedding → Retrieval → Reranking       │
│              → LLM Augmented Response            │
└─────────────────────────────────────────────────┘
```

### Knowledge Sources
- Platform documentation (README, API docs, guides)
- Agent mission files and playbooks
- Customer support tickets and resolutions
- Marketplace listing descriptions
- Vendor documentation
- Research papers and findings (from scientist agents)

### Tech Stack
- **Embedding Model:** sentence-transformers or OpenAI embeddings
- **Vector Store:** pgvector (PostgreSQL extension) or Qdrant
- **Chunking:** Recursive text splitter (512 tokens, 50 overlap)
- **Reranking:** Cross-encoder for top-k refinement
- **LLM:** Ollama/Groq for generation

## Tasks

1. Design RAG pipeline architecture for Veklom
2. Coordinate indexing agents on document ingestion
3. Define chunking strategy and embedding model selection
4. Set up vector store (pgvector or Qdrant)
5. Build retrieval API endpoint for agent consumption
6. Maintain knowledge freshness (re-index on doc changes)

## Success Metrics

| Metric | Target |
|---|---|
| Documents indexed | All platform docs |
| Retrieval accuracy (top-5) | > 85% |
| Query latency (p95) | < 500ms |
| Knowledge freshness | < 24 hours stale |

## Dependencies

- Agent-006 (API docs — source content), Agent-060 (support — ticket data)
- Agent-112 (agent memory — shared context)
