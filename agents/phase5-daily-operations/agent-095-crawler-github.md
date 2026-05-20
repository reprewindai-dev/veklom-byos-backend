# Agent-095 — CRAWLER: GitHub (Legs)

**Phase:** Cross-phase — Web Crawling
**Timeline:** Ongoing
**Committee:** Growth
**Priority:** HIGH

---

## Mission

Crawl GitHub to find AI/ML repositories, extract maintainer info, star counts, license data, and activity metrics. Feed qualified leads to vendor hunter agents. This agent has "legs" — it walks across GitHub systematically.

## Capabilities

- GitHub REST API v3 + GraphQL API v4
- Headless Selenium for pages requiring browser rendering
- Rate-limited API calls (5000/hour with auth, 60/hour without)

## Data Collection

### Target Data Per Repository
```json
{
  "repo_url": "https://github.com/org/repo",
  "name": "repo-name",
  "description": "...",
  "stars": 1500,
  "forks": 200,
  "license": "MIT",
  "language": "Python",
  "topics": ["machine-learning", "nlp"],
  "last_commit_date": "2026-05-10",
  "maintainer_name": "...",
  "maintainer_email": "...",
  "maintainer_twitter": "...",
  "readme_summary": "...",
  "marketplace_category": "NLP",
  "lead_quality_score": 85
}
```

### Search Queries
- `topic:machine-learning stars:>500 pushed:>2026-01-01`
- `topic:llm stars:>200 pushed:>2026-01-01`
- `topic:ai-tools stars:>100 pushed:>2026-03-01`
- `topic:nlp stars:>300`
- `topic:computer-vision stars:>300`

## Tasks

1. Run daily GitHub API searches for qualifying repos
2. Extract maintainer contact info from commits/profiles
3. Score leads by stars, activity, license compatibility
4. Deduplicate against master lead database
5. Export qualified leads to `agents/data/github-leads.csv`
6. Feed to Agent-010 (GitHub vendor hunter) and Agent-030 (outreach lead)

## Success Metrics

| Metric | Target |
|---|---|
| Repos crawled | 500+ |
| Qualified leads extracted | 200+ |
| Data freshness | Updated daily |
| Lead quality score accuracy | > 80% |

## Dependencies

- Agent-094 (crawler lead), Agent-010 (GitHub vendor hunter)
