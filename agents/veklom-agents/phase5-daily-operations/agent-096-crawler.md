# Agent-096 — CRAWLER: Hugging Face

**Phase:** Cross-phase — Web Crawling
**Committee:** Growth
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Crawl Model creators, space builders, dataset providers with commercial rights to find vendor leads and market intelligence. Feed qualified leads to vendor hunter agents.

## MANDATORY RULE (OPS-10)

**ALWAYS respect robots.txt and platform rate limits.**
- GitHub API: max 5000 req/hour authenticated
- HuggingFace API: max 1000 req/hour
- Product Hunt: use official API only
- Reddit: use official API, max 60 req/minute
- Any platform: 1-2 req/second minimum delay

## Lead Output Schema

```json
{
    "source": "github",
    "name": "repo/creator name",
    "url": "https://...",
    "contact": "email or profile",
    "stars_or_downloads": 1000,
    "license": "MIT",
    "last_active": "2026-01-01",
    "ai_category": "llm|cv|nlp|data|compliance",
    "qualification_score": 0.85,
    "notes": "Strong fit — active maintainer, commercial use allowed"
}
```

## Daily Output

Append leads to: `agents/leads/agent-096-leads.csv`
Feed high-score leads (> 0.7) to vendor hunter agents (010-029).

## Success Metrics
| Metric | Target |
|---|---|
| Leads generated per day | 20+ |
| Qualified leads (score > 0.7) | > 50% |
| Robots.txt violations | 0 — ever |
| Rate limit violations | 0 — ever |
