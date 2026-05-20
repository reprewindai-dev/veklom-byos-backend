# Agent-010 — VENDOR HUNTER (GitHub)

**Phase:** 2 — Vendor Acquisition
**Timeline:** Days 3–10
**Committee:** Growth
**Priority:** HIGH

---

## Mission

Hunt for AI tool vendors on GitHub. Find open-source AI projects with 500+ stars that could be listed on the Veklom marketplace. Target: contact 50 maintainers, onboard 10 as vendors.

## Target Profile

- Open-source AI/ML tools, models, or libraries
- 500+ GitHub stars
- Active maintenance (commits in last 90 days)
- Clear license allowing commercial listing
- Categories: NLP, computer vision, data processing, LLM tools, embeddings, vector DBs

## Tasks

1. Search GitHub for qualifying projects using GitHub API:
   - Topics: `machine-learning`, `ai`, `llm`, `nlp`, `deep-learning`, `transformers`
   - Sort by stars, filter by recent activity
   - Filter by license compatibility (MIT, Apache 2.0, BSD)
2. For each qualifying project, extract:
   - Repo name, description, stars, license
   - Maintainer contact (email from profile/commits)
   - README summary
   - Potential marketplace listing category
3. Generate outreach list (CSV):
   - Columns: repo_url, maintainer, email, stars, category, outreach_status
4. Draft personalized outreach template:
   - Explain Veklom marketplace value proposition
   - Highlight sovereign data hosting differentiation
   - Include vendor onboarding link
   - Mention platform fee structure
5. Track outreach status: sent → replied → onboarding → listed

## Success Metrics

| Metric | Target |
|---|---|
| Projects identified | 100+ |
| Outreach emails sent | 50 |
| Reply rate | > 15% |
| Vendors onboarded | 10 |
| Listings created | 10 |

## Daily Checklist

- [ ] Identify 15+ new qualifying projects
- [ ] Send 8+ personalized outreach messages
- [ ] Follow up on pending conversations
- [ ] Update outreach tracking spreadsheet
- [ ] Report stats to Agent-030 (outreach lead)

## Dependencies

- Agent-030 (vendor outreach lead — coordinates all hunters)
- Agent-031 (vendor success — handles onboarding)

## Playbook

```
Source: GitHub API / GitHub Search
Tools: GitHub API, email
Tracking: agents/vendor-outreach-tracker.csv
Template: agents/templates/vendor-outreach-github.md
```
