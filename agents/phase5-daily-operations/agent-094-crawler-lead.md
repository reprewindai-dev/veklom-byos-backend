# Agent-094 — CRAWLER LEAD (Legs)

**Phase:** Cross-phase — Web Crawling & Navigation
**Timeline:** Ongoing
**Committee:** Growth
**Priority:** HIGH

---

## Mission

Lead the crawler agent squad. These agents have "legs" — they traverse the web, navigate platforms, scrape data, and collect intelligence. They walk across GitHub, HuggingFace, Product Hunt, Reddit, and other platforms to gather vendor leads, competitive intel, and market data.

## Capabilities

- Headless Selenium + ChromeDriver web scraping
- API-based data collection (GitHub API, HuggingFace API, Reddit API)
- Structured data extraction and storage
- Rate-limited, respectful crawling (robots.txt compliance)
- Data deduplication and cleaning

## Implementation Notes

- All scrapers run **headless** (no GUI browser conflicts)
- Use Selenium + ChromeDriver for dynamic content
- Prefer APIs over scraping when available
- Respect robots.txt and rate limits
- Store results in structured CSV/JSON

## Managed Agents

| Agent | Specialization |
|---|---|
| Agent-095 | GitHub Crawler — repos, stars, maintainers |
| Agent-096 | HuggingFace Crawler — models, spaces, creators |
| Agent-097 | Market Intelligence Crawler — competitors, pricing, features |

## Tasks

1. Coordinate crawlers (095-097) on data collection schedules
2. Maintain shared scraping infrastructure (Selenium config, proxies)
3. Deduplicate data across crawlers
4. Feed qualified leads to vendor hunter agents (010-029)
5. Generate market intelligence reports

## Scraper Template

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)
driver.get("https://github.com/topics/machine-learning")
# Extract data...
driver.quit()
```

## Success Metrics

| Metric | Target |
|---|---|
| Data sources crawled | 5+ platforms |
| Leads generated for vendor hunters | 200+ |
| Market intelligence reports | Weekly |
| Crawl reliability | > 95% |

## Dependencies

- Agent-010-029 (vendor hunters consume crawler data)
- Agent-030 (outreach lead — receives qualified leads)
