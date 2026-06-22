# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.ts >> Veklom smoke >> @smoke footer & DSA/Contact presence
- Location: tests/smoke.spec.ts:209:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('link', { name: /contact|dsa|legal/i }).first()
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByRole('link', { name: /contact|dsa|legal/i }).first()

```

```yaml
- navigation:
  - link "Veklom":
    - /url: /
    - img "Veklom"
  - link "Ecosystem":
    - /url: "#ecosystem"
  - link "Compare":
    - /url: "#compare"
  - link "Pricing":
    - /url: "#pricing"
  - link "Workspace":
    - /url: /workspace
  - link "◆ Operational":
    - /url: /uptime
  - link "Sign In":
    - /url: /workspace/login
- text: SOC2-Ready HIPAA-Aware GDPR-Compliant EU-Sovereign ISO27001-Aligned FedRAMP-Ready
- link "View security posture →":
  - /url: /legal/security
- img "Veklom"
- text: Sovereign AI Operating Infrastructure
- heading "The era of “trust us” AI is over. Veklom is built for “show us” AI." [level=1]
- paragraph: Veklom moves AI from uncoordinated experimentation into governed production. From prompt to plan to proof — with replayable evidence at every step.
- text: Prompt → Plan → Pipeline → Proof Humans → Workspace Developers → API Agents → Paid Routes (x402) Enterprises → Governance Layer
- link "Start a governed repo review":
  - /url: "#terminal-simulation"
- link "View deployment options":
  - /url: "#deployment-options"
- link "Open Workspace":
  - /url: /workspace
- text: ● Backend live — veklom.com 35+ teams signed up Sovereign Hetzner EU nodes BYOS ready Live Demo Interactive Simulation
- heading "Run a governed repo review" [level=2]
- paragraph: Watch Veklom test, verify, and gate an agent against a real repository — before it touches production.
- iframe
- text: The Problem
- heading "Agents are getting access to real systems. Without enough control." [level=2]
- paragraph: Engineering teams want to use AI agents — but they don't trust them near repositories, cloud tools, customer data, or production workflows. That instinct is right. Veklom answers it.
- text: 🔐
- heading "Inspected Safely" [level=3]
- paragraph: "\"Can I let an agent inspect our repo safely without risking leaks or unintended commits?\""
- text: 👁
- heading "Real-Time Telemetry" [level=3]
- paragraph: "\"Can I see exactly what the agent did, every file it read, and every API call it made?\""
- text: 🚫
- heading "Risky Path Gating" [level=3]
- paragraph: "\"Can I dynamically block risky, destructive, or out-of-scope actions before they commit?\""
- text: 🔑
- heading "Zero Key Exposure" [level=3]
- paragraph: "\"Can I isolate sensitive tokens, secrets, and provider credentials away from the frontend?\""
- text: 📋
- heading "Audit-Ready Records" [level=3]
- paragraph: "\"Can I produce a sealed, unalterable record if compliance asks why and how this agent ran?\""
- text: 🏠
- heading "Sovereign Infrastructure" [level=3]
- paragraph: "\"Can I run this runtime privately on our own infrastructure without paying public cloud taxes?\""
- text: Product & Deployment
- heading "One governed runtime. Three operating boundaries." [level=2]
- paragraph: Start hosted, move to a dedicated sovereign node, or deploy BYOS. The same Veklom core governs playground tests, command-center telemetry, policy gates, and replayable audit evidence.
- text: 01 ☁️ Hosted Workspace
- heading "Start governed immediately." [level=3]
- paragraph: Use Playground and Command Center on Veklom's managed secure cloud. Test agents, connect repositories, monitor runtime activity, and seal audit logs before production access.
- text: Instant setup Playground Command Center Audit logging
- link "Start Free Eval":
  - /url: /workspace/login
- text: 02 🔒 Sovereign Node
- heading "Run on dedicated EU hardware." [level=3]
- paragraph: Move the same governed runtime onto an isolated Hetzner EU node dedicated to your team. Keep data residency, policy gates, telemetry, and evidence under one boundary.
- text: Dedicated runtime Hetzner EU GPC decisions Custom policy gates
- link "Deploy Dedicated Node":
  - /url: /workspace/login
- text: 03 🏠 BYOS / Self-Hosted
- heading "Own the full execution boundary." [level=3]
- paragraph: Deploy Veklom inside your private VPC, on-prem environment, or dark-site infrastructure. Same policy-governed runtime, without cloud egress or provider taxes.
- text: Your servers Air-gap ready Zero cloud tax Enterprise SLA
- link "Talk to Sales":
  - /url: mailto:sales@veklom.com
- text: Machine Economy
- heading "Agents can discover, call, pay for, and verify APIs." [level=2]
- paragraph: The old internet required a human to sign up and add a card. The new pattern is different. Agents find APIs, read the listing, pay per call, receive the result, and record proof — automatically.
- text: Old Pattern human finds website ↓ signs up ↓ adds card ↓ uses API New Pattern (x402) agent finds API ↓ reads /.well-known/x402.json ↓ pays per call (USDC, Base) ↓ receives result + evidence receipt ↓ records proof on-chain 👤 Humans
- heading "Use the workspace" [level=3]
- paragraph: Playground, Command Center, Monitoring, Vault, Compliance — full governed UI.
- link "Open workspace →":
  - /url: /workspace/
- text: 💻 Developers
- heading "Use the API" [level=3]
- paragraph:
  - text: Bearer JWT. REST + SSE. OpenAPI at
  - code: /openapi.json
  - text: . MCP at
  - code: /mcp/sse
  - text: .
- link "View OpenAPI →":
  - /url: /openapi.json
- text: 🤖 Agents
- heading "Use the paid routes" [level=3]
- paragraph: No sign-up. x402 per-call micropayments (USDC on Base). Budget caps. Kill switches. Evidence receipts.
- link "Read x402 config →":
  - /url: /.well-known/x402.json
- text: 🏛 Enterprises
- heading "Use the governance layer" [level=3]
- paragraph: SOC2, HIPAA, GDPR. SHA-256 audit evidence. Kill switches. BYOS. Sovereign EU nodes.
- link "Talk to sales →":
  - /url: mailto:sales@veklom.com
- text: Ecosystem
- heading "Marketplace products built for governed execution" [level=2]
- paragraph: Available as part of the Veklom product ecosystem. High-performance modules and products built to expand your sovereign runtime limits.
- text: ⚡ Runtime Module
- heading "PY03 IronGrid API" [level=3]
- paragraph: High-performance route optimization and concurrency sandbox for agent/runtime workloads.
- text: Route optimizer Concurrency sandbox Veklom core
- link "View Repository":
  - /url: https://github.com/reprewindai-dev/pyo3-irongrid-api
- text: 🔒 Marketplace Product
- heading "Lockerphycer" [level=3]
- paragraph: A Veklom marketplace product for controlled, governed execution workflows.
- text: Governed workflows Security locker Product demo
- link "Open Lockerphycer demo":
  - /url: https://lockerphycer-git-main-dksummers-projects.vercel.app/
- text: V3 Black Box
- heading "Messy intent in. Governed execution out." [level=2]
- paragraph: "Public preview: the top rail and deterministic core are visible while internal operational panes stay masked."
- text: Public preview
- iframe
- text: Governance Scope
- heading "What Veklom controls" [level=2]
- paragraph: Every agent call, repository hook, and container tool execution routes through our isolated proxy layer to ensure absolute compliance.
- text: Agent actions Every call, every single step audited Repository access Read, write, fine-grained scopes Tool execution Allow, block, or human approvals Policy gates (GPC) Enforced prior to runtime execution Runtime activity Live telemetry + historical replay Cost & tokens Per agent, per job, token limits Audit evidence SHA-256 sealed blocks of execution Boundaries Hosted → sovereign deployments Practical Application
- heading "What teams use it for" [level=2]
- paragraph: Empower platform and security teams with out-of-the-box templates designed for immediate integration.
- text: Engineering
- heading "Pre-deployment repo reviews" [level=3]
- paragraph: Connect your repository and ask an agent to review it. Veklom tells you what's verified, what's risky, what needs approval, and what gets blocked — before touching production.
- text: Engineering
- heading "AI coding-agent oversight" [level=3]
- paragraph: Let Copilot, Cursor, or custom corporate agents operate inside your codebase — with every action logged, policy-gated, and fully revertable. Stop flying blind on agent activity.
- text: Governance
- heading "LangChain / chain workflow control" [level=3]
- paragraph: Run multi-step LangChain pipelines through our GPC layer. Each node in the chain gets its own policy check, spend limit, and automated audit entry.
- text: Governance
- heading "Audit-ready execution records" [level=3]
- paragraph: "Every agent action produces a SHA-256 signed evidence block — timestamped, immutable, and exportable. Instantly answer compliance: what ran, when, and who approved it."
- text: Why Veklom
- heading "Sovereign AI should be portable, provable, and economically predictable. Veklom is built for that." [level=2]
- table:
  - rowgroup:
    - row "Capability Veklom TrueFoundry Portkey LangSmith Bedrock / Vertex":
      - columnheader "Capability"
      - columnheader "Veklom"
      - columnheader "TrueFoundry"
      - columnheader "Portkey"
      - columnheader "LangSmith"
      - columnheader "Bedrock / Vertex"
  - rowgroup:
    - row "Governed Plan Compiler (GPC) ● — — — —":
      - cell "Governed Plan Compiler (GPC)"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "—"
    - row "Pre-execution risk & policy ● — Partial — Partial":
      - cell "Pre-execution risk & policy"
      - cell "●"
      - cell "—"
      - cell "Partial"
      - cell "—"
      - cell "Partial"
    - row "Signed evidence packages ● — — — —":
      - cell "Signed evidence packages"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "—"
    - row "Replayable audit bundles ● — — — —":
      - cell "Replayable audit bundles"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "—"
    - row "BYOK + zero key exposure ● ● ● — ●":
      - cell "BYOK + zero key exposure"
      - cell "●"
      - cell "●"
      - cell "●"
      - cell "—"
      - cell "●"
    - row "Tenant-scoped workspace ● ● — — ●":
      - cell "Tenant-scoped workspace"
      - cell "●"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "●"
    - row "Private/BYOS runtime ● ● — — ●":
      - cell "Private/BYOS runtime"
      - cell "●"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "●"
    - row "Operating Reserve billing ● Subscription Token-based Subscription Pay-per-use":
      - cell "Operating Reserve billing"
      - cell "●"
      - cell "Subscription"
      - cell "Token-based"
      - cell "Subscription"
      - cell "Pay-per-use"
    - row "Marketplace with vendor payouts ● — — — Partial":
      - cell "Marketplace with vendor payouts"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "Partial"
    - row "120-agent autonomous workforce ● — — — —":
      - cell "120-agent autonomous workforce"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "—"
    - row "x402 agent micropayments (USDC) ● — — — —":
      - cell "x402 agent micropayments (USDC)"
      - cell "●"
      - cell "—"
      - cell "—"
      - cell "—"
      - cell "—"
- text: Pricing
- heading "Activate once. Fund your reserve. Pay for governed execution." [level=2]
- paragraph: No subscriptions. No token fiction. No surprise invoices.
- text: Free Evaluation $0 No card required
- list:
  - listitem: → 15 governed Playground runs
  - listitem: → 3 compare runs
  - listitem: → 20 policy tests
  - listitem: → 2 watermarked exports
  - listitem: → BYOK provider testing
  - listitem: → Tools browsing
- link "Start Free →":
  - /url: /workspace/login
- text: Founding Most chosen $395 One-time activation + $150 min reserve
- list:
  - listitem: → Playground run — $0.25
  - listitem: → Compare run — $0.75
  - listitem: → UACP compile — $1.50
  - listitem: → Pipeline test — $0.25
  - listitem: → Endpoint test — $0.50
  - listitem: → BYOK Gov Calls — $6/1,000
  - listitem: → Managed Gov Calls — $12/1,000
- link "Activate →":
  - /url: /workspace/login
- text: Standard $795 One-time activation + $300 min reserve
- list:
  - listitem: → Playground run — $0.40
  - listitem: → Compare run — $1.20
  - listitem: → UACP compile — $2.00
  - listitem: → Pipeline test — $0.40
  - listitem: → Endpoint test — $0.80
  - listitem: → BYOK Gov Calls — $8/1,000
  - listitem: → Managed Gov Calls — $16/1,000
- link "Activate →":
  - /url: /workspace/login
- text: Regulated / Enterprise $2,500+ Private terms + $2,500 min reserve
- list:
  - listitem: → BYOK Gov Calls — $10/1,000
  - listitem: → Managed Gov Calls — $20/1,000
  - listitem: → Private deployment
  - listitem: → Procurement & security review
  - listitem: → Custom SLA
- link "Talk to Sales →":
  - /url: mailto:sales@veklom.com
- text: Transparency Pulse
- heading "Live platform metrics" [level=2]
- paragraph: Refreshes every 60 seconds. Real data from GET /api/v1/platform/pulse
- text: Total users undefined% (30d) 0 Active listings +0 (7d) Tool installs undefined active tools GPC compiles Get Started
- heading "We want to use agents. We just don't trust them near production yet." [level=2]
- paragraph: Good. Run them through Veklom first. Test, govern, and prove AI execution — before anything matters.
- link "Start a governed review":
  - /url: /workspace/login
- link "Read the docs":
  - /url: /docs
- text: Feedback
- heading "Tell us what you think" [level=2]
- paragraph: Report a bug, suggest a feature, or just say hi.
- combobox:
  - option "Bug Report" [selected]
  - option "Suggestion"
  - option "General Feedback"
- textbox "Subject"
- textbox "Describe your feedback..."
- button "Submit →"
- contentinfo:
  - link "Veklom Hub":
    - /url: /
  - paragraph: Sovereign Control Node © Veklom
  - heading "Product" [level=4]
  - link "Workspace":
    - /url: /workspace
  - link "Pricing":
    - /url: "#pricing"
  - link "API Docs":
    - /url: /docs
  - heading "Resources" [level=4]
  - link "Status":
    - /url: /uptime
  - link "Docs":
    - /url: /docs
  - link "Feedback":
    - /url: "#feedback"
  - heading "Legal" [level=4]
  - link "Terms":
    - /url: /legal/terms
  - link "Privacy":
    - /url: /legal/privacy
  - link "Security":
    - /url: mailto:security@veklom.com
```

# Test source

```ts
  119 |       await gotoDuringRollout(page, url, url);
  120 |       await expect(page.locator('body')).toBeVisible();
  121 |       expect(errors, `no landing JS errors on ${url}`).toHaveLength(0);
  122 |     }
  123 |   });
  124 |
  125 |   test('@smoke auth: login/signup flow', async ({ page }) => {
  126 |     page.on('console', msg => console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`));
  127 |     page.on('request', req => console.log(`[Browser Request] ${req.method()} ${req.url()}`));
  128 |     page.on('response', res => console.log(`[Browser Response] ${res.status()} ${res.url()}`));
  129 |
  130 |     // Navigate to login (redirects to /workspace/login in the SPA)
  131 |     await gotoDuringRollout(page, `${BASE}/login`, 'login route');
  132 |     await page.waitForLoadState('networkidle');
  133 |
  134 |     // The control plane is a Next App Router export, not a Vite SPA; assert the rendered auth shell.
  135 |     await expect(page.locator('main')).toBeVisible({ timeout: 15000 });
  136 |     await expect(page.getByText(/welcome back|sovereign sign-in|sign in/i).first()).toBeVisible({ timeout: 15000 });
  137 |
  138 |     // Look for any sign-up / register link or button (flexible selector)
  139 |     const signUpTrigger = page
  140 |       .getByRole('button', { name: /sign.?up|register|create.?account/i })
  141 |       .or(page.getByRole('link', { name: /sign.?up|register|create.?account/i }))
  142 |       .or(page.locator('[id*="tab-up"], [id*="tab-signup"], [data-tab="signup"]'))
  143 |       .first();
  144 |
  145 |     const signUpVisible = await signUpTrigger.isVisible().catch(() => false);
  146 |     if (signUpVisible) {
  147 |       await signUpTrigger.click();
  148 |       await page.waitForTimeout(500);
  149 |     }
  150 |
  151 |     // Try to fill an email field if present (best-effort; SPA may require different flow)
  152 |     const emailInput = page.locator('input[type="email"], input[name="email"], #vk-email').first();
  153 |     const emailVisible = await emailInput.isVisible().catch(() => false);
  154 |     if (emailVisible) {
  155 |       const testEmail = process.env.TEST_EMAIL || `smoke+signup${Date.now()}@example.com`;
  156 |       await emailInput.fill(testEmail);
  157 |       const passInput = page.locator('input[type="password"], #vk-pass').first();
  158 |       if (await passInput.isVisible().catch(() => false)) {
  159 |         await passInput.fill(process.env.TEST_PASSWORD || 'Playwright!234');
  160 |       }
  161 |       // Submit if a submit button is present
  162 |       const submitBtn = page.locator('#vk-submit, button[type="submit"]').first();
  163 |       if (await submitBtn.isVisible().catch(() => false)) {
  164 |         await submitBtn.click({ force: true });
  165 |         await page.waitForTimeout(2000);
  166 |       }
  167 |     }
  168 |
  169 |     // Final assertion: page body should still be alive
  170 |     await expect(page.locator('body')).toBeVisible();
  171 |   });
  172 |
  173 |   test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
  174 |     await gotoDuringRollout(page, `${BASE}/workspace`, 'workspace route');
  175 |     await page.waitForLoadState('networkidle');
  176 |
  177 |     // The workspace route may redirect unauthenticated users into the Next auth shell.
  178 |     await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
  179 |     await expect(page.locator('main, nav, [role="navigation"]').first()).toBeVisible({ timeout: 15000 });
  180 |
  181 |     // If the workspace sidebar is visible, check for key nav items.
  182 |     // If the user is unauthenticated the control plane shows a login screen — skip nav checks.
  183 |     const navVisible = await page.locator('nav, [role="navigation"]').first().isVisible().catch(() => false);
  184 |     if (navVisible) {
  185 |       const expected = [
  186 |         /terminal|console/i,
  187 |         /marketplace|apps/i,
  188 |         /pipelines?|workflow/i,
  189 |         /billing|subscription/i
  190 |       ];
  191 |       for (const pattern of expected) {
  192 |         await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 });
  193 |       }
  194 |
  195 |       // Try a simple no-op job/run button if present
  196 |       const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
  197 |       if (await runBtn.isVisible().catch(() => false)) {
  198 |         await runBtn.click();
  199 |         await page.waitForTimeout(1000);
  200 |         await expect(page.locator('body')).toBeVisible();
  201 |       }
  202 |     } else {
  203 |       // Unauthenticated: control plane loaded but shows login; that's acceptable for smoke.
  204 |       console.log('Workspace loaded in unauthenticated state; skipping nav element checks.');
  205 |       await expect(page.locator('body')).toBeVisible();
  206 |     }
  207 |   });
  208 |
  209 |   test('@smoke footer & DSA/Contact presence', async ({ page }) => {
  210 |     await gotoDuringRollout(page, BASE, 'public landing');
  211 |     await page.getByRole('contentinfo'); // footer landmark
  212 |     const footerLinks = [
  213 |       /terms|tos/i,
  214 |       /privacy/i,
  215 |       /status/i,
  216 |       /contact|dsa|legal/i
  217 |     ];
  218 |     for (const l of footerLinks) {
> 219 |       await expect(page.getByRole('link', { name: l }).first()).toBeVisible();
      |                                                                 ^ Error: expect(locator).toBeVisible() failed
  220 |     }
  221 |   });
  222 |
  223 |   test('@smoke headers: CSP/TLS/CORS sane', async ({ request }) => {
  224 |     const resp = await waitForResponseStatus(request, BASE, [200], 'public landing headers');
  225 |
  226 |     const csp = resp.headers()['content-security-policy'];
  227 |     expect(csp, 'CSP present').toBeTruthy();
  228 |
  229 |     const hsts = resp.headers()['strict-transport-security'];
  230 |     expect(hsts || '', 'HSTS present').toMatch(/max-age=\d+/i);
  231 |
  232 |     const cors = resp.headers()['access-control-allow-origin'];
  233 |     // Allow either specific origin or wildcard on API only
  234 |     expect(cors === undefined || cors === '*' || /^https?:\/\//.test(cors)).toBeTruthy();
  235 |
  236 |     const frame = resp.headers()['x-frame-options'];
  237 |     expect((frame || '').toUpperCase()).toMatch(/SAMEORIGIN|DENY/);
  238 |   });
  239 |
  240 |   test('@smoke PostHog events emit (if enabled)', async ({ page }) => {
  241 |     // Skip if no key configured on site or in env
  242 |     await page.route('**/capture/*', route => {
  243 |       // Let it pass; we'll inspect later
  244 |       route.continue();
  245 |     });
  246 |     const requests: { url: string; body?: string }[] = [];
  247 |     page.on('requestfinished', async req => {
  248 |       if (req.url().includes('/capture/') || req.url().includes('/e/')) {
  249 |         let body = '';
  250 |         try { body = (await req.postData()) || ''; } catch {}
  251 |         requests.push({ url: req.url(), body });
  252 |       }
  253 |     });
  254 |     await gotoDuringRollout(page, BASE, 'public landing analytics');
  255 |     await page.waitForTimeout(1500);
  256 |     if (requests.length === 0) {
  257 |       console.warn('PostHog is not enabled or not emitting events (likely REPLACE_ME_POSTHOG_KEY is active)');
  258 |       test.skip();
  259 |     } else {
  260 |       expect(requests.length, 'At least one analytics event should fire').toBeGreaterThan(0);
  261 |     }
  262 |   });
  263 |
  264 |   test('@smoke known failing endpoints return expected failures', async ({ request }) => {
  265 |     test.skip(failingList.length === 0, 'No FAILING_ENDPOINTS provided');
  266 |     for (const item of failingList) {
  267 |       // Format: "METHOD /path"
  268 |       const [method, path] = item.split(/\s+/);
  269 |       const url = path.startsWith('http') ? path : `${API}${path}`;
  270 |       const resp = await request.fetch(url, { method: method as any });
  271 |       // Expect 4xx/5xx (adjust as needed)
  272 |       expect(String(resp.status())).toMatch(/^(400|401|403|404|409|422|500|502|503)$/);
  273 |     }
  274 |   });
  275 |
  276 |   test('@smoke auth required for workspace-scoped status', async ({ request }) => {
  277 |     const r = await request.get(endpoints.statusDataWorkspace);
  278 |     // Backend must return 401 or 403 for unauthenticated access (not 200, not 503)
  279 |     expect([401, 403]).toContain(r.status());
  280 |   });
  281 | });
  282 |
```