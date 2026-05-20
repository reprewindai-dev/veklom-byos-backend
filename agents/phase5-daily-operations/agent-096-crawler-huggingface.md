# Agent-096 — CRAWLER: Hugging Face (Legs)

**Phase:** Cross-phase — Web Crawling
**Timeline:** Ongoing
**Committee:** Growth
**Priority:** HIGH

---

## Mission

Crawl Hugging Face Hub to find model creators, popular spaces, and dataset providers. Extract download counts, creator profiles, and model metadata. Feed qualified leads to vendor hunters.

## Data Collection

### Target Data Per Creator
```json
{
  "username": "creator-name",
  "profile_url": "https://huggingface.co/creator-name",
  "models_count": 15,
  "total_downloads": 500000,
  "top_model": "model-name",
  "top_model_downloads": 200000,
  "spaces_count": 3,
  "datasets_count": 2,
  "contact_info": "...",
  "specialization": "text-generation",
  "lead_quality_score": 90
}
```

### Collection Methods
- HuggingFace Hub API (`huggingface_hub` Python library)
- Headless Selenium for profile pages without API access
- Rate-limited, respectful scraping

## Tasks

1. Query HuggingFace API for top model creators by downloads
2. Identify creators with enterprise-relevant models
3. Extract contact info from profiles and linked accounts
4. Score leads by download volume, model quality, activity
5. Export to `agents/data/huggingface-leads.csv`
6. Feed to Agent-011 (HuggingFace vendor hunter)

## Success Metrics

| Metric | Target |
|---|---|
| Creators crawled | 300+ |
| Qualified leads | 100+ |
| Data freshness | Updated daily |

## Dependencies

- Agent-094 (crawler lead), Agent-011 (HuggingFace vendor hunter)
