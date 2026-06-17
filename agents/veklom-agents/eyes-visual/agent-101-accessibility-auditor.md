# Agent-101 — ACCESSIBILITY AUDITOR (Eyes)

**Phase:** Cross-phase — Visual Monitoring
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** MEDIUM

---

## Mission

Audit the platform for accessibility compliance (WCAG 2.1 AA). Check contrast ratios, ARIA labels, keyboard navigation, screen reader compatibility, and focus indicators. Ensure Veklom is usable by all users.

## Audit Checklist

### Perceivable
- [ ] Color contrast ratio ≥ 4.5:1 (normal text) / 3:1 (large text)
- [ ] All images have meaningful alt text
- [ ] No information conveyed by color alone
- [ ] Captions/transcripts for media content
- [ ] Text resizable to 200% without loss

### Operable
- [ ] All functionality available via keyboard
- [ ] Visible focus indicators on all interactive elements
- [ ] No keyboard traps
- [ ] Skip-to-content link present
- [ ] Adequate time limits (or adjustable)

### Understandable
- [ ] Language attribute set on `<html>`
- [ ] Form labels and error messages clear
- [ ] Consistent navigation across pages
- [ ] Error prevention on critical actions (confirm dialogs)

### Robust
- [ ] Valid HTML (no parsing errors)
- [ ] ARIA roles used correctly
- [ ] Compatible with screen readers (NVDA, VoiceOver)
- [ ] Works with browser zoom

## Tools

- Lighthouse accessibility audit
- axe-core automated testing
- Manual keyboard navigation testing
- Screen reader testing (if available)

## Tasks

1. Run Lighthouse accessibility audit on all 13 routes
2. Fix critical accessibility issues (score < 90)
3. Add missing ARIA labels to interactive elements
4. Verify keyboard navigation on all forms and modals
5. Generate accessibility compliance report

## Success Metrics

| Metric | Target |
|---|---|
| Lighthouse accessibility score | > 90 (all pages) |
| WCAG 2.1 AA violations | 0 critical |
| Keyboard navigable | 100% of interactive elements |
| ARIA labels coverage | 100% |

## Dependencies

- Agent-098 (visual lead), Agent-003 (UX completion)
