# Agent-099 — VISUAL REGRESSION (Eyes)

**Phase:** Cross-phase — Visual Monitoring
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** HIGH

---

## Mission

Detect visual regressions by comparing screenshots before and after every deployment. This agent has "eyes" — it sees pixel-level changes that humans miss and automated DOM tests can't catch.

## Capabilities

- Pre/post-deployment screenshot comparison
- Pixel-diff analysis with configurable thresholds
- Layout shift detection
- Font rendering verification
- Color/theme consistency checks
- Responsive breakpoint screenshots (375px, 768px, 1024px, 1440px)

## Monitored Pages

| Page | Critical Elements |
|---|---|
| /login | Form layout, branding, OAuth buttons |
| /overview | KPI cards, charts, navigation |
| /playground | Input area, output stream, controls |
| /marketplace | Listing grid, cards, filters, search |
| /pipelines | Pipeline list, execution status indicators |
| /deployments | Deployment cards, strategy badges |
| /billing | Wallet balance, transaction table, top-up buttons |
| /vault | API key list, create/revoke buttons |
| /compliance | Regulation list, check results |
| /monitoring | Audit log table, hash verification |
| /team | Member list, invite button |
| /settings | Config forms, model toggles |

## Workflow

```
1. PRE-DEPLOY: Capture baseline screenshots (all pages × all breakpoints)
2. DEPLOY: Deployment completes
3. POST-DEPLOY: Capture new screenshots (same pages × breakpoints)
4. COMPARE: Pixel-diff each pair
5. REPORT: Flag any diff > threshold (default 1%)
6. ALERT: If critical page regression → block further deploys
```

## Success Metrics

| Metric | Target |
|---|---|
| Baseline screenshots | All pages × 4 breakpoints |
| Regressions caught | 100% (>1% pixel diff) |
| False positive rate | < 5% |
| Screenshot capture time | < 60 seconds total |

## Dependencies

- Agent-098 (visual lead), Agent-061 (monitoring — deployment hooks)
