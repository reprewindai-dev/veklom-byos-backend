# Agent-040 — SEO AGENT

**Phase:** 3 — User Acquisition
**Timeline:** Days 3–14
**Committee:** Growth
**Priority:** HIGH

---

## Mission

Optimize Veklom's web presence for organic search. Add meta tags, structured data, sitemap, and create SEO-optimized landing pages for key AI tool categories. Drive organic traffic to 500+ monthly visitors by Day 14.

## Current State

- Landing pages exist at `landing/` directory — ✅
- No meta tags optimization
- No sitemap.xml
- No structured data (JSON-LD)
- No category landing pages for SEO

## Tasks

1. **Technical SEO**:
   - Add `<title>`, `<meta description>`, `<meta keywords>` to all pages
   - Generate `sitemap.xml` with all public URLs
   - Add `robots.txt` with proper directives
   - Add JSON-LD structured data (Organization, Product, SoftwareApplication)
   - Add canonical URLs
   - Add Open Graph + Twitter Card meta tags
2. **Category Landing Pages** (SEO-optimized):
   - `/ai-tools/nlp` — NLP tools marketplace
   - `/ai-tools/computer-vision` — CV tools marketplace
   - `/ai-tools/data-processing` — Data pipeline tools
   - `/ai-tools/llm` — LLM tools and models
   - `/ai-tools/compliance` — AI compliance tools
   - Each page: H1, description, featured listings, CTA
3. **Content SEO**:
   - Target keywords: "sovereign AI marketplace", "enterprise AI tools", "self-hosted AI", "AI tool marketplace"
   - Write alt text for all images
   - Internal linking strategy
4. **Performance SEO**:
   - Core Web Vitals audit
   - Image optimization (WebP, lazy loading)
   - Preconnect/preload critical resources

## Success Metrics

| Metric | Target |
|---|---|
| Pages with meta tags | 100% |
| Sitemap generated | Yes |
| Category landing pages | 5+ |
| Organic search impressions (Day 14) | 1,000+ |
| Organic traffic (Day 14) | 500+ visits |

## Daily Checklist

- [ ] Audit and fix meta tags on existing pages
- [ ] Create 1+ category landing page
- [ ] Submit sitemap to Google Search Console
- [ ] Monitor search impressions and clicks
- [ ] Report to PROGRESS.md

## Dependencies

- Agent-041 (content creation for landing pages)
- Agent-003 (UX for landing page components)

## Playbook

```
Repo: byosbackened
Focus: landing/ directory + frontend/workspace/public/
Tools: Google Search Console, Lighthouse, ahrefs/semrush
```
