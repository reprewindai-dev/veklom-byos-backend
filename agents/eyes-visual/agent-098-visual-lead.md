# Agent-098 — VISUAL LEAD (Eyes)

**Phase:** Cross-phase — Visual Monitoring & Inspection
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** HIGH

---

## Mission

Lead the visual agent squad. These agents have "eyes" — they observe UIs, take screenshots, compare visual states, detect regressions, and monitor dashboards. They see what users see and catch what automated tests miss.

## Capabilities

- Screenshot capture and comparison (pixel-diff)
- Visual regression detection across deployments
- Dashboard monitoring (Grafana, custom dashboards)
- UI state verification (correct data displayed, no broken layouts)
- Accessibility audit (contrast ratios, ARIA labels, focus indicators)
- Real-time visual monitoring of production UI

## Managed Agents

| Agent | Specialization |
|---|---|
| Agent-099 | Visual Regression — screenshot diffing across deploys |
| Agent-100 | Dashboard Watcher — monitor KPI dashboards, alert on anomalies |
| Agent-101 | Accessibility Auditor — WCAG compliance, screen reader compatibility |

## Tasks

1. Coordinate visual agents (099-101) on monitoring schedules
2. Maintain baseline screenshot library for all pages
3. Define visual regression thresholds (acceptable pixel diff %)
4. Review visual test results and flag regressions
5. Generate visual QA reports with annotated screenshots

## Visual Monitoring Pattern

```python
from PIL import Image, ImageChops
import io

def compare_screenshots(baseline_path, current_path, threshold=0.01):
    baseline = Image.open(baseline_path)
    current = Image.open(current_path)
    diff = ImageChops.difference(baseline, current)
    diff_pixels = sum(1 for p in diff.getdata() if sum(p) > 30)
    total_pixels = baseline.size[0] * baseline.size[1]
    diff_ratio = diff_pixels / total_pixels
    return {
        "passed": diff_ratio < threshold,
        "diff_ratio": diff_ratio,
        "diff_pixels": diff_pixels
    }
```

## Success Metrics

| Metric | Target |
|---|---|
| Pages with visual baselines | All 13 routes |
| Visual regressions caught pre-deploy | 100% |
| Accessibility score (Lighthouse) | > 90 |
| Dashboard monitoring uptime | 24/7 |

## Dependencies

- Agent-085 (frontend QA), Agent-061 (monitoring)
