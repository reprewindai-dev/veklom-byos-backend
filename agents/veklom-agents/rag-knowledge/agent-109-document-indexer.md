# Agent-109 — DOCUMENT INDEXER (RAG)

**Phase:** Cross-phase — Knowledge
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Ingest, chunk, embed, and index all platform documentation into the vector store. Maintain document freshness by detecting changes and re-indexing. This is the data ingestion backbone of the RAG pipeline.

## Document Sources

| Source | Type | Update Frequency |
|---|---|---|
| `README.md`, `CONTRIBUTING.md` | Repo docs | On commit |
| `backend/docs/` | API documentation | On commit |
| `agents/*.md` | Agent mission files | On commit |
| `.agents/skills/` | Playbooks | On commit |
| Marketplace listings | Dynamic content | On create/update |
| Support tickets | User-generated | Continuous |
| Research papers | Agent outputs | Weekly |

## Chunking Strategy

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    length_function=len
)

# Metadata preserved per chunk:
# - source_file: original file path
# - doc_type: "api_doc" | "agent_mission" | "playbook" | "listing" | "ticket"
# - section_title: nearest heading
# - last_updated: timestamp
# - chunk_index: position in document
```

## Tasks

1. Build document ingestion pipeline
2. Implement smart chunking (respect markdown headers, code blocks)
3. Generate embeddings via sentence-transformers or API
4. Store in pgvector with metadata
5. Set up file watcher for auto-re-indexing on changes
6. Handle incremental updates (don't re-index unchanged docs)

## Success Metrics

| Metric | Target |
|---|---|
| Documents indexed | 100% of sources |
| Indexing latency | < 5 min after change |
| Chunk quality | No broken sentences/code |
| Deduplication | 0 duplicate chunks |

## Dependencies

- Agent-108 (RAG lead), Agent-006 (API docs source)
