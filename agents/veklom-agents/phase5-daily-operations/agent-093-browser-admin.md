# Agent-093 — BROWSER AGENT: Admin & Settings (Hands)

**Phase:** Cross-phase — Browser Interaction
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** MEDIUM

---

## Mission

Automate and test admin panel, settings, and configuration flows using browser interaction. Manage API keys, team settings, model configuration, and workspace settings via the UI.

## Automated Flows

1. **Settings Management**:
   - Navigate to /settings
   - Update workspace name, description
   - Configure model providers (Ollama, Groq)
   - Save and verify changes persist
2. **API Key Management**:
   - Navigate to /vault
   - Create new API key → copy to clipboard
   - Revoke existing API key
   - Verify revoked key no longer works
3. **Team Management**:
   - Navigate to /team
   - View team members
   - Test invite flow (when implemented)
4. **Compliance & Monitoring**:
   - Navigate to /compliance → run regulation check
   - Navigate to /monitoring → verify audit trail
   - Click audit entry → verify hash

## Success Metrics

| Metric | Target |
|---|---|
| Settings flows automated | Yes |
| API key lifecycle automated | Yes |
| Admin flows automated | Yes |

## Dependencies

- Agent-090 (browser lead), Agent-003 (UX completion)
