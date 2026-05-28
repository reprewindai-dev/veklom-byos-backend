# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.ts >> Veklom smoke >> @smoke PostHog events emit (if enabled)
- Location: tests\smoke.spec.ts:136:7

# Error details

```
Error: At least one analytics event should fire

expect(received).toBeGreaterThan(expected)

Expected: > 0
Received:   0
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - navigation [ref=e2]:
    - generic [ref=e3]:
      - link "Veklom" [ref=e4] [cursor=pointer]:
        - /url: /
        - img "Veklom" [ref=e5]
      - generic [ref=e6]:
        - link "Ecosystem" [ref=e7] [cursor=pointer]:
          - /url: "#ecosystem"
        - link "Compare" [ref=e8] [cursor=pointer]:
          - /url: "#compare"
        - link "Pricing" [ref=e9] [cursor=pointer]:
          - /url: "#pricing"
        - link "Workspace" [ref=e10] [cursor=pointer]:
          - /url: /workspace
        - link "◆ Operational" [ref=e11] [cursor=pointer]:
          - /url: /uptime
        - link "Sign In" [ref=e12] [cursor=pointer]:
          - /url: /workspace/login
  - generic [ref=e14]:
    - generic [ref=e15]: SOC2-Ready
    - generic [ref=e16]: HIPAA-Aware
    - generic [ref=e17]: GDPR-Compliant
    - generic [ref=e18]: EU-Sovereign
    - generic [ref=e19]: ISO27001-Aligned
    - generic [ref=e20]: FedRAMP-Ready
    - link "View security posture →" [ref=e21] [cursor=pointer]:
      - /url: /legal/security
  - generic [ref=e23]:
    - img "Veklom" [ref=e24]
    - text: Sovereign AI Operating Infrastructure
    - heading "The era of “trust us” AI is over. Veklom is built for “show us” AI." [level=1] [ref=e25]:
      - text: The era of “trust us” AI is over.
      - text: Veklom is built for “show us” AI.
    - paragraph [ref=e26]: Veklom moves AI from uncoordinated experimentation into governed production. From prompt to plan to proof — with replayable evidence at every step.
    - generic [ref=e27]:
      - generic [ref=e28]: Prompt
      - generic [ref=e29]: →
      - generic [ref=e30]: Plan
      - generic [ref=e31]: →
      - generic [ref=e32]: Pipeline
      - generic [ref=e33]: →
      - generic [ref=e34]: Proof
    - generic [ref=e35]:
      - generic [ref=e36]: Humans → Workspace
      - generic [ref=e37]: Developers → API
      - generic [ref=e38]: Agents → Paid Routes (x402)
      - generic [ref=e39]: Enterprises → Governance Layer
    - generic [ref=e40]:
      - link "Start a governed repo review" [ref=e41] [cursor=pointer]:
        - /url: "#terminal-simulation"
      - link "View deployment options" [ref=e42] [cursor=pointer]:
        - /url: "#deployment-options"
      - link "Open Workspace" [ref=e43] [cursor=pointer]:
        - /url: /workspace
    - generic [ref=e44]:
      - generic [ref=e45]: ● Backend live — veklom.com
      - generic [ref=e46]: 35+ teams signed up
      - generic [ref=e47]: Sovereign Hetzner EU nodes
      - generic [ref=e48]: BYOS ready
      - generic [ref=e49]: Live Demo
  - generic [ref=e51]:
    - generic [ref=e52]:
      - text: Interactive Simulation
      - heading "Run a governed repo review" [level=2] [ref=e53]
      - paragraph [ref=e54]: Watch Veklom test, verify, and gate an agent against a real repository — before it touches production.
    - iframe [ref=e56]:
      - generic [active] [ref=f1e1]:
        - banner [ref=f1e2]:
          - generic [ref=f1e3]:
            - img "UACP logo" [ref=f1e4]
            - generic [ref=f1e11]: UACP // Quantum Context Terminal
          - generic [ref=f1e13]: byosbackend v2
          - generic [ref=f1e14]: live
          - generic [ref=f1e15]: phase_locked
          - generic [ref=f1e18]: BYOS CONNECTED
          - generic [ref=f1e19]: 2026-05-28 17:25:22 UTC
          - generic [ref=f1e20]: Antigravity v4.0 // Neural Orchestration Engine
        - generic [ref=f1e21]:
          - navigation [ref=f1e22]:
            - generic [ref=f1e23]:
              - generic [ref=f1e24]: Connection Map
              - generic [ref=f1e25]:
                - generic [ref=f1e26] [cursor=pointer]:
                  - text: UACP Core
                  - generic [ref=f1e28]: ▶
                - generic [ref=f1e29]:
                  - generic [ref=f1e30] [cursor=pointer]:
                    - generic [ref=f1e31]: POST
                    - text: /autonomous/execute
                  - generic [ref=f1e32] [cursor=pointer]:
                    - generic [ref=f1e33]: GET
                    - text: /autonomous/status
                  - generic [ref=f1e34] [cursor=pointer]:
                    - generic [ref=f1e35]: POST
                    - text: /internal/uacp/v4
                  - generic [ref=f1e36] [cursor=pointer]:
                    - generic [ref=f1e37]: GET
                    - text: /internal/uacp/versions
                  - generic [ref=f1e38] [cursor=pointer]:
                    - generic [ref=f1e39]: POST
                    - text: /operators/register
                  - generic [ref=f1e40] [cursor=pointer]:
                    - generic [ref=f1e41]: GET
                    - text: /operators/capabilities
              - generic [ref=f1e43] [cursor=pointer]:
                - text: AI / Inference
                - generic [ref=f1e45]: ▶
              - generic [ref=f1e47] [cursor=pointer]:
                - text: Marketplace
                - generic [ref=f1e49]: ▶
              - generic [ref=f1e51] [cursor=pointer]:
                - text: Telemetry / Monitor
                - generic [ref=f1e53]: ▶
              - generic [ref=f1e55] [cursor=pointer]:
                - text: Safety / Control
                - generic [ref=f1e57]: ▶
              - generic [ref=f1e59] [cursor=pointer]:
                - text: Auth / Identity
                - generic [ref=f1e61]: ▶
              - generic [ref=f1e63] [cursor=pointer]:
                - text: Workspace / Data
                - generic [ref=f1e65]: ▶
          - main [ref=f1e66]:
            - generic [ref=f1e67]:
              - generic [ref=f1e68] [cursor=pointer]: Terminal
              - generic [ref=f1e69] [cursor=pointer]: MCP Trace
              - generic [ref=f1e70] [cursor=pointer]: Zeno Log
              - generic [ref=f1e71] [cursor=pointer]: Gladiator
            - generic [ref=f1e72]:
              - generic [ref=f1e73]:
                - generic [ref=f1e74]: 17:25:21.683
                - generic [ref=f1e75]: //
                - generic [ref=f1e76]: UACP Quantum Context Terminal — Antigravity v4.0
              - generic [ref=f1e77]:
                - generic [ref=f1e78]: 17:25:21.712
                - generic [ref=f1e79]: ⟶
                - generic [ref=f1e80]: Connecting to BYOS Backend — github.com/reprewindai-dev/veklom-byos-backend
              - generic [ref=f1e81]:
                - generic [ref=f1e82]: 17:25:21.802
                - generic [ref=f1e83]: ◆
                - generic [ref=f1e84]: "Transport: HTTPS + SSE | Auth: JWT Bearer | Protocol: JSON-RPC 2.0"
              - generic [ref=f1e85]:
                - generic [ref=f1e86]: 17:25:21.907
                - generic [ref=f1e87]: ✓
                - generic [ref=f1e88]: MCP Host initialized — managing 40+ context server endpoints
              - generic [ref=f1e89]:
                - generic [ref=f1e90]: 17:25:22.034
                - generic [ref=f1e91]: ✓
                - generic [ref=f1e92]: Operator registry loaded — internal_operators.py capabilities negotiated
              - generic [ref=f1e93]:
                - generic [ref=f1e94]: 17:25:22.187
                - generic [ref=f1e95]: ✓
                - generic [ref=f1e96]: UACP v0→v4 versioned control plane — internal_uacp.py active
              - generic [ref=f1e97]:
                - generic [ref=f1e98]: 17:25:22.358
                - generic [ref=f1e99]: Ψ
                - generic [ref=f1e100]: Zeno interrogation engine — N=6 cycles, efficiency 64%, leakage 1.4%
              - generic [ref=f1e101]:
                - generic [ref=f1e102]: 17:25:22.540
                - generic [ref=f1e103]: Ω
                - generic [ref=f1e104]: Gladiator speculative reasoning mesh — online
              - generic [ref=f1e106]:
                - generic [ref=f1e107]: 17:25:22.741
                - generic [ref=f1e108]: ✓
                - generic [ref=f1e109]: All systems phase_locked. Type a command or select an endpoint.
              - generic [ref=f1e110]:
                - generic [ref=f1e111]: 17:25:22.741
                - generic [ref=f1e112]: ▸
                - generic [ref=f1e113]: "Try: POST /autonomous/execute | Calibrate thousand-qubit Heron processor"
            - generic [ref=f1e114]:
              - generic [ref=f1e115]:
                - button "Autonomous" [ref=f1e116] [cursor=pointer]
                - button "MCP Dispatch" [ref=f1e117] [cursor=pointer]
                - button "Zeno Probe" [ref=f1e118] [cursor=pointer]
                - button "Gladiator" [ref=f1e119] [cursor=pointer]
                - button "Raw API" [ref=f1e120] [cursor=pointer]
              - generic [ref=f1e121]:
                - generic [ref=f1e122]: UACP>
                - textbox "Route to /autonomous/execute or describe an orchestration intent..." [ref=f1e123]
                - button "Execute" [ref=f1e124] [cursor=pointer]
              - generic [ref=f1e125]:
                - button "POST /autonomous/execute" [ref=f1e126] [cursor=pointer]
                - button "GET /autonomous/status" [ref=f1e127] [cursor=pointer]
                - button "Calibrate thousand-qubit Heron processor" [ref=f1e128] [cursor=pointer]
                - button "Optimize 10000-bit bitmap transmission" [ref=f1e129] [cursor=pointer]
                - button "GET /health" [ref=f1e130] [cursor=pointer]
          - complementary [ref=f1e131]:
            - generic [ref=f1e132]:
              - generic [ref=f1e133]: Zeno Interrogation Visualizer
              - generic [ref=f1e136]:
                - generic [ref=f1e137]:
                  - generic [ref=f1e138]: N Cycles
                  - generic [ref=f1e139]: "6"
                - generic [ref=f1e140]:
                  - generic [ref=f1e141]: Efficiency
                  - generic [ref=f1e142]: 64%
                - generic [ref=f1e143]:
                  - generic [ref=f1e144]: Leakage
                  - generic [ref=f1e145]: 1.4%
            - generic [ref=f1e147]: MCP Mesh Topology
            - generic [ref=f1e150]:
              - generic [ref=f1e151]: Sovereign Escalation Engine
              - generic [ref=f1e153]:
                - generic [ref=f1e154]:
                  - generic [ref=f1e155]: Cache Hits
                  - generic [ref=f1e156]: "18"
                - generic [ref=f1e157]:
                  - generic [ref=f1e158]: USD Saved
                  - generic [ref=f1e159]: $0.63
              - generic [ref=f1e160]:
                - generic [ref=f1e161]:
                  - generic [ref=f1e162]: Ollama Runs
                  - generic [ref=f1e163]: "5"
                - generic [ref=f1e164]:
                  - generic [ref=f1e165]: Escalations
                  - generic [ref=f1e166]: "1"
            - generic [ref=f1e167]:
              - generic [ref=f1e168]: Active Endpoint
              - generic [ref=f1e171]:
                - generic [ref=f1e172]:
                  - generic [ref=f1e173]: POST
                  - generic [ref=f1e174]: /autonomous/execute
                - generic [ref=f1e175]: UACP primary agentic entrypoint. Accepts orchestration intent, dispatches to internal UACP v0→v4 versioned control plane. Returns streaming run status via SSE.
                - generic [ref=f1e176]:
                  - generic [ref=f1e177]: UACP
                  - generic [ref=f1e178]: MCP Host
                  - generic [ref=f1e179]: SSE Stream
                  - generic [ref=f1e180]: JWT Auth
            - generic [ref=f1e181]:
              - generic [ref=f1e182]: Live Telemetry
              - generic [ref=f1e184]:
                - generic [ref=f1e185]: Zeno Eff
                - generic [ref=f1e188]: 64%
              - generic [ref=f1e189]:
                - generic [ref=f1e190]: Agent Load
                - generic [ref=f1e193]: 23%
              - generic [ref=f1e194]:
                - generic [ref=f1e195]: MCP Mesh
                - generic [ref=f1e198]: 88%
              - generic [ref=f1e199]:
                - generic [ref=f1e200]: Leakage
                - generic [ref=f1e203]: 1.4%
              - generic [ref=f1e204]:
                - generic [ref=f1e205]: API Health
                - generic [ref=f1e208]: 99%
  - generic [ref=e58]:
    - generic [ref=e59]:
      - text: The Problem
      - heading "Agents are getting access to real systems. Without enough control." [level=2] [ref=e60]:
        - text: Agents are getting access to real systems.
        - text: Without enough control.
      - paragraph [ref=e61]: Engineering teams want to use AI agents — but they don't trust them near repositories, cloud tools, customer data, or production workflows. That instinct is right. Veklom answers it.
    - generic [ref=e62]:
      - generic [ref=e63]:
        - generic [ref=e64]: 🔐
        - heading "Inspected Safely" [level=3] [ref=e65]
        - paragraph [ref=e66]: "\"Can I let an agent inspect our repo safely without risking leaks or unintended commits?\""
      - generic [ref=e67]:
        - generic [ref=e68]: 👁
        - heading "Real-Time Telemetry" [level=3] [ref=e69]
        - paragraph [ref=e70]: "\"Can I see exactly what the agent did, every file it read, and every API call it made?\""
      - generic [ref=e71]:
        - generic [ref=e72]: 🚫
        - heading "Risky Path Gating" [level=3] [ref=e73]
        - paragraph [ref=e74]: "\"Can I dynamically block risky, destructive, or out-of-scope actions before they commit?\""
      - generic [ref=e75]:
        - generic [ref=e76]: 🔑
        - heading "Zero Key Exposure" [level=3] [ref=e77]
        - paragraph [ref=e78]: "\"Can I isolate sensitive tokens, secrets, and provider credentials away from the frontend?\""
      - generic [ref=e79]:
        - generic [ref=e80]: 📋
        - heading "Audit-Ready Records" [level=3] [ref=e81]
        - paragraph [ref=e82]: "\"Can I produce a sealed, unalterable record if compliance asks why and how this agent ran?\""
      - generic [ref=e83]:
        - generic [ref=e84]: 🏠
        - heading "Sovereign Infrastructure" [level=3] [ref=e85]
        - paragraph [ref=e86]: "\"Can I run this runtime privately on our own infrastructure without paying public cloud taxes?\""
  - generic [ref=e88]:
    - generic [ref=e89]:
      - text: Product & Deployment
      - heading "One governed runtime. Three operating boundaries." [level=2] [ref=e90]
      - paragraph [ref=e91]: Start hosted, move to a dedicated sovereign node, or deploy BYOS. The same Veklom core governs playground tests, command-center telemetry, policy gates, and replayable audit evidence.
    - generic [ref=e92]:
      - generic [ref=e93]:
        - generic: "01"
        - generic [ref=e94]: ☁️
        - generic [ref=e95]: Hosted Workspace
        - heading "Start governed immediately." [level=3] [ref=e96]
        - paragraph [ref=e97]: Use Playground and Command Center on Veklom's managed secure cloud. Test agents, connect repositories, monitor runtime activity, and seal audit logs before production access.
        - generic [ref=e98]:
          - generic [ref=e99]: Instant setup
          - generic [ref=e100]: Playground
          - generic [ref=e101]: Command Center
          - generic [ref=e102]: Audit logging
        - link "Start Free Eval" [ref=e103] [cursor=pointer]:
          - /url: /workspace/login
      - generic [ref=e104]:
        - generic: "02"
        - generic [ref=e105]: 🔒
        - generic [ref=e106]: Sovereign Node
        - heading "Run on dedicated EU hardware." [level=3] [ref=e107]
        - paragraph [ref=e108]: Move the same governed runtime onto an isolated Hetzner EU node dedicated to your team. Keep data residency, policy gates, telemetry, and evidence under one boundary.
        - generic [ref=e109]:
          - generic [ref=e110]: Dedicated runtime
          - generic [ref=e111]: Hetzner EU
          - generic [ref=e112]: GPC decisions
          - generic [ref=e113]: Custom policy gates
        - link "Deploy Dedicated Node" [ref=e114] [cursor=pointer]:
          - /url: /workspace/login
      - generic [ref=e115]:
        - generic: "03"
        - generic [ref=e116]: 🏠
        - generic [ref=e117]: BYOS / Self-Hosted
        - heading "Own the full execution boundary." [level=3] [ref=e118]
        - paragraph [ref=e119]: Deploy Veklom inside your private VPC, on-prem environment, or dark-site infrastructure. Same policy-governed runtime, without cloud egress or provider taxes.
        - generic [ref=e120]:
          - generic [ref=e121]: Your servers
          - generic [ref=e122]: Air-gap ready
          - generic [ref=e123]: Zero cloud tax
          - generic [ref=e124]: Enterprise SLA
        - link "Talk to Sales" [ref=e125] [cursor=pointer]:
          - /url: mailto:sales@veklom.com
  - generic [ref=e127]:
    - generic [ref=e128]:
      - text: Machine Economy
      - heading "Agents can discover, call, pay for, and verify APIs." [level=2] [ref=e129]
      - paragraph [ref=e130]: The old internet required a human to sign up and add a card. The new pattern is different. Agents find APIs, read the listing, pay per call, receive the result, and record proof — automatically.
    - generic [ref=e131]:
      - generic [ref=e132]:
        - generic [ref=e133]: Old Pattern
        - generic [ref=e134]:
          - generic [ref=e135]: human finds website
          - generic [ref=e136]: ↓
          - generic [ref=e137]: signs up
          - generic [ref=e138]: ↓
          - generic [ref=e139]: adds card
          - generic [ref=e140]: ↓
          - generic [ref=e141]: uses API
      - generic [ref=e142]:
        - generic [ref=e143]: New Pattern (x402)
        - generic [ref=e144]:
          - generic [ref=e145]: agent finds API
          - generic [ref=e146]: ↓
          - generic [ref=e147]: reads /.well-known/x402.json
          - generic [ref=e148]: ↓
          - generic [ref=e149]: pays per call (USDC, Base)
          - generic [ref=e150]: ↓
          - generic [ref=e151]: receives result + evidence receipt
          - generic [ref=e152]: ↓
          - generic [ref=e153]: records proof on-chain
    - generic [ref=e154]:
      - generic [ref=e155]:
        - generic [ref=e156]: 👤
        - generic [ref=e157]: Humans
        - heading "Use the workspace" [level=3] [ref=e158]
        - paragraph [ref=e159]: Playground, Command Center, Monitoring, Vault, Compliance — full governed UI.
        - link "Open workspace →" [ref=e160] [cursor=pointer]:
          - /url: /workspace/
      - generic [ref=e161]:
        - generic [ref=e162]: 💻
        - generic [ref=e163]: Developers
        - heading "Use the API" [level=3] [ref=e164]
        - paragraph [ref=e165]:
          - text: Bearer JWT. REST + SSE. OpenAPI at
          - code [ref=e166]: /openapi.json
          - text: . MCP at
          - code [ref=e167]: /mcp/sse
          - text: .
        - link "View OpenAPI →" [ref=e168] [cursor=pointer]:
          - /url: /openapi.json
      - generic [ref=e169]:
        - generic [ref=e170]: 🤖
        - generic [ref=e171]: Agents
        - heading "Use the paid routes" [level=3] [ref=e172]
        - paragraph [ref=e173]: No sign-up. x402 per-call micropayments (USDC on Base). Budget caps. Kill switches. Evidence receipts.
        - link "Read x402 config →" [ref=e174] [cursor=pointer]:
          - /url: /.well-known/x402.json
      - generic [ref=e175]:
        - generic [ref=e176]: 🏛
        - generic [ref=e177]: Enterprises
        - heading "Use the governance layer" [level=3] [ref=e178]
        - paragraph [ref=e179]: SOC2, HIPAA, GDPR. SHA-256 audit evidence. Kill switches. BYOS. Sovereign EU nodes.
        - link "Talk to sales →" [ref=e180] [cursor=pointer]:
          - /url: mailto:sales@veklom.com
  - generic [ref=e182]:
    - generic [ref=e183]:
      - text: Ecosystem
      - heading "Marketplace products built for governed execution" [level=2] [ref=e184]
      - paragraph [ref=e185]: Available as part of the Veklom product ecosystem. High-performance modules and products built to expand your sovereign runtime limits.
    - generic [ref=e186]:
      - generic [ref=e187]:
        - generic [ref=e188]: ⚡
        - generic [ref=e189]: Runtime Module
        - heading "PY03 IronGrid API" [level=3] [ref=e190]
        - paragraph [ref=e191]: High-performance route optimization and concurrency sandbox for agent/runtime workloads.
        - generic [ref=e192]:
          - generic [ref=e193]: Route optimizer
          - generic [ref=e194]: Concurrency sandbox
          - generic [ref=e195]: Veklom core
        - link "View Repository" [ref=e196] [cursor=pointer]:
          - /url: https://github.com/reprewindai-dev/pyo3-irongrid-api
      - generic [ref=e197]:
        - generic [ref=e198]: 🔒
        - generic [ref=e199]: Marketplace Product
        - heading "Lockerphycer" [level=3] [ref=e200]
        - paragraph [ref=e201]: A Veklom marketplace product for controlled, governed execution workflows.
        - generic [ref=e202]:
          - generic [ref=e203]: Governed workflows
          - generic [ref=e204]: Security locker
          - generic [ref=e205]: Product demo
        - link "Open Lockerphycer demo" [ref=e206] [cursor=pointer]:
          - /url: https://lockerphycer-git-main-dksummers-projects.vercel.app/
  - generic [ref=e208]:
    - generic [ref=e209]:
      - text: V3 Black Box
      - heading "Messy intent in. Governed execution out." [level=2] [ref=e210]
      - paragraph [ref=e211]: "Public preview: the top rail and deterministic core are visible while internal operational panes stay masked."
    - generic "Veklom V3 public preview" [ref=e212]:
      - generic [ref=e213]: Public preview
      - iframe [ref=e217]
  - generic [ref=e220]:
    - generic [ref=e221]:
      - text: Governance Scope
      - heading "What Veklom controls" [level=2] [ref=e222]
      - paragraph [ref=e223]: Every agent call, repository hook, and container tool execution routes through our isolated proxy layer to ensure absolute compliance.
      - generic [ref=e224]:
        - generic [ref=e225]:
          - generic [ref=e226]: Agent actions
          - generic [ref=e228]: Every call, every single step audited
        - generic [ref=e229]:
          - generic [ref=e230]: Repository access
          - generic [ref=e232]: Read, write, fine-grained scopes
        - generic [ref=e233]:
          - generic [ref=e234]: Tool execution
          - generic [ref=e236]: Allow, block, or human approvals
        - generic [ref=e237]:
          - generic [ref=e238]: Policy gates (GPC)
          - generic [ref=e240]: Enforced prior to runtime execution
        - generic [ref=e241]:
          - generic [ref=e242]: Runtime activity
          - generic [ref=e244]: Live telemetry + historical replay
        - generic [ref=e245]:
          - generic [ref=e246]: Cost & tokens
          - generic [ref=e248]: Per agent, per job, token limits
        - generic [ref=e249]:
          - generic [ref=e250]: Audit evidence
          - generic [ref=e252]: SHA-256 sealed blocks of execution
        - generic [ref=e253]:
          - generic [ref=e254]: Boundaries
          - generic [ref=e256]: Hosted → sovereign deployments
    - generic [ref=e257]:
      - text: Practical Application
      - heading "What teams use it for" [level=2] [ref=e258]
      - paragraph [ref=e259]: Empower platform and security teams with out-of-the-box templates designed for immediate integration.
      - generic [ref=e260]:
        - generic [ref=e261]:
          - generic [ref=e262]: Engineering
          - heading "Pre-deployment repo reviews" [level=3] [ref=e263]
          - paragraph [ref=e264]: Connect your repository and ask an agent to review it. Veklom tells you what's verified, what's risky, what needs approval, and what gets blocked — before touching production.
        - generic [ref=e265]:
          - generic [ref=e266]: Engineering
          - heading "AI coding-agent oversight" [level=3] [ref=e267]
          - paragraph [ref=e268]: Let Copilot, Cursor, or custom corporate agents operate inside your codebase — with every action logged, policy-gated, and fully revertable. Stop flying blind on agent activity.
        - generic [ref=e269]:
          - generic [ref=e270]: Governance
          - heading "LangChain / chain workflow control" [level=3] [ref=e271]
          - paragraph [ref=e272]: Run multi-step LangChain pipelines through our GPC layer. Each node in the chain gets its own policy check, spend limit, and automated audit entry.
        - generic [ref=e273]:
          - generic [ref=e274]: Governance
          - heading "Audit-ready execution records" [level=3] [ref=e275]
          - paragraph [ref=e276]: "Every agent action produces a SHA-256 signed evidence block — timestamped, immutable, and exportable. Instantly answer compliance: what ran, when, and who approved it."
  - generic [ref=e278]:
    - generic [ref=e279]:
      - text: Why Veklom
      - heading "Sovereign AI should be portable, provable, and economically predictable. Veklom is built for that." [level=2] [ref=e280]:
        - text: Sovereign AI should be portable, provable, and economically predictable.
        - text: Veklom is built for that.
    - table [ref=e282]:
      - rowgroup [ref=e283]:
        - row "Capability Veklom TrueFoundry Portkey LangSmith Bedrock / Vertex" [ref=e284]:
          - columnheader "Capability" [ref=e285]
          - columnheader "Veklom" [ref=e286]
          - columnheader "TrueFoundry" [ref=e287]
          - columnheader "Portkey" [ref=e288]
          - columnheader "LangSmith" [ref=e289]
          - columnheader "Bedrock / Vertex" [ref=e290]
      - rowgroup [ref=e291]:
        - row "Governed Plan Compiler (GPC) ● — — — —" [ref=e292]:
          - cell "Governed Plan Compiler (GPC)" [ref=e293]
          - cell "●" [ref=e294]
          - cell "—" [ref=e295]
          - cell "—" [ref=e296]
          - cell "—" [ref=e297]
          - cell "—" [ref=e298]
        - row "Pre-execution risk & policy ● — Partial — Partial" [ref=e299]:
          - cell "Pre-execution risk & policy" [ref=e300]
          - cell "●" [ref=e301]
          - cell "—" [ref=e302]
          - cell "Partial" [ref=e303]
          - cell "—" [ref=e304]
          - cell "Partial" [ref=e305]
        - row "Signed evidence packages ● — — — —" [ref=e306]:
          - cell "Signed evidence packages" [ref=e307]
          - cell "●" [ref=e308]
          - cell "—" [ref=e309]
          - cell "—" [ref=e310]
          - cell "—" [ref=e311]
          - cell "—" [ref=e312]
        - row "Replayable audit bundles ● — — — —" [ref=e313]:
          - cell "Replayable audit bundles" [ref=e314]
          - cell "●" [ref=e315]
          - cell "—" [ref=e316]
          - cell "—" [ref=e317]
          - cell "—" [ref=e318]
          - cell "—" [ref=e319]
        - row "BYOK + zero key exposure ● ● ● — ●" [ref=e320]:
          - cell "BYOK + zero key exposure" [ref=e321]
          - cell "●" [ref=e322]
          - cell "●" [ref=e323]
          - cell "●" [ref=e324]
          - cell "—" [ref=e325]
          - cell "●" [ref=e326]
        - row "Tenant-scoped workspace ● ● — — ●" [ref=e327]:
          - cell "Tenant-scoped workspace" [ref=e328]
          - cell "●" [ref=e329]
          - cell "●" [ref=e330]
          - cell "—" [ref=e331]
          - cell "—" [ref=e332]
          - cell "●" [ref=e333]
        - row "Private/BYOS runtime ● ● — — ●" [ref=e334]:
          - cell "Private/BYOS runtime" [ref=e335]
          - cell "●" [ref=e336]
          - cell "●" [ref=e337]
          - cell "—" [ref=e338]
          - cell "—" [ref=e339]
          - cell "●" [ref=e340]
        - row "Operating Reserve billing ● Subscription Token-based Subscription Pay-per-use" [ref=e341]:
          - cell "Operating Reserve billing" [ref=e342]
          - cell "●" [ref=e343]
          - cell "Subscription" [ref=e344]
          - cell "Token-based" [ref=e345]
          - cell "Subscription" [ref=e346]
          - cell "Pay-per-use" [ref=e347]
        - row "Marketplace with vendor payouts ● — — — Partial" [ref=e348]:
          - cell "Marketplace with vendor payouts" [ref=e349]
          - cell "●" [ref=e350]
          - cell "—" [ref=e351]
          - cell "—" [ref=e352]
          - cell "—" [ref=e353]
          - cell "Partial" [ref=e354]
        - row "120-agent autonomous workforce ● — — — —" [ref=e355]:
          - cell "120-agent autonomous workforce" [ref=e356]
          - cell "●" [ref=e357]
          - cell "—" [ref=e358]
          - cell "—" [ref=e359]
          - cell "—" [ref=e360]
          - cell "—" [ref=e361]
        - row "x402 agent micropayments (USDC) ● — — — —" [ref=e362]:
          - cell "x402 agent micropayments (USDC)" [ref=e363]
          - cell "●" [ref=e364]
          - cell "—" [ref=e365]
          - cell "—" [ref=e366]
          - cell "—" [ref=e367]
          - cell "—" [ref=e368]
  - generic [ref=e370]:
    - generic [ref=e371]:
      - text: Pricing
      - heading "Activate once. Fund your reserve. Pay for governed execution." [level=2] [ref=e372]
      - paragraph [ref=e373]: No subscriptions. No token fiction. No surprise invoices.
    - generic [ref=e374]:
      - generic [ref=e375]:
        - text: Free Evaluation
        - generic [ref=e376]: $0
        - generic [ref=e377]: No card required
        - list [ref=e378]:
          - listitem [ref=e379]: → 15 governed Playground runs
          - listitem [ref=e380]: → 3 compare runs
          - listitem [ref=e381]: → 20 policy tests
          - listitem [ref=e382]: → 2 watermarked exports
          - listitem [ref=e383]: → BYOK provider testing
          - listitem [ref=e384]: → Tools browsing
        - link "Start Free →" [ref=e385] [cursor=pointer]:
          - /url: /workspace/login
      - generic [ref=e386]:
        - generic [ref=e387]:
          - generic [ref=e388]: Founding
          - generic [ref=e389]: Most chosen
        - generic [ref=e390]: $395
        - generic [ref=e391]: One-time activation + $150 min reserve
        - list [ref=e392]:
          - listitem [ref=e393]: → Playground run — $0.25
          - listitem [ref=e394]: → Compare run — $0.75
          - listitem [ref=e395]: → UACP compile — $1.50
          - listitem [ref=e396]: → Pipeline test — $0.25
          - listitem [ref=e397]: → Endpoint test — $0.50
          - listitem [ref=e398]: → BYOK Gov Calls — $6/1,000
          - listitem [ref=e399]: → Managed Gov Calls — $12/1,000
        - link "Activate →" [ref=e400] [cursor=pointer]:
          - /url: /workspace/login
      - generic [ref=e401]:
        - text: Standard
        - generic [ref=e402]: $795
        - generic [ref=e403]: One-time activation + $300 min reserve
        - list [ref=e404]:
          - listitem [ref=e405]: → Playground run — $0.40
          - listitem [ref=e406]: → Compare run — $1.20
          - listitem [ref=e407]: → UACP compile — $2.00
          - listitem [ref=e408]: → Pipeline test — $0.40
          - listitem [ref=e409]: → Endpoint test — $0.80
          - listitem [ref=e410]: → BYOK Gov Calls — $8/1,000
          - listitem [ref=e411]: → Managed Gov Calls — $16/1,000
        - link "Activate →" [ref=e412] [cursor=pointer]:
          - /url: /workspace/login
      - generic [ref=e413]:
        - text: Regulated / Enterprise
        - generic [ref=e414]: $2,500+
        - generic [ref=e415]: Private terms + $2,500 min reserve
        - list [ref=e416]:
          - listitem [ref=e417]: → BYOK Gov Calls — $10/1,000
          - listitem [ref=e418]: → Managed Gov Calls — $20/1,000
          - listitem [ref=e419]: → Private deployment
          - listitem [ref=e420]: → Procurement & security review
          - listitem [ref=e421]: → Custom SLA
        - link "Talk to Sales →" [ref=e422] [cursor=pointer]:
          - /url: mailto:sales@veklom.com
  - generic [ref=e424]:
    - generic [ref=e425]:
      - text: Transparency Pulse
      - heading "Live platform metrics" [level=2] [ref=e426]
      - paragraph [ref=e427]: Refreshes every 60 seconds. Real data from GET /api/v1/platform/pulse
    - generic [ref=e428]:
      - generic [ref=e429]:
        - generic [ref=e430]: "1524"
        - generic [ref=e431]: Total users
        - generic [ref=e432]: +14.5% (30d)
      - generic [ref=e433]:
        - generic [ref=e434]: "42"
        - generic [ref=e435]: Active listings
        - generic [ref=e436]: +3 (7d)
      - generic [ref=e437]:
        - generic [ref=e438]: "8412"
        - generic [ref=e439]: Tool installs
        - generic [ref=e440]: 28 active tools
      - generic [ref=e441]:
        - generic [ref=e442]: "12053"
        - generic [ref=e443]: GPC compiles
  - generic [ref=e445]:
    - text: Get Started
    - heading "We want to use agents. We just don't trust them near production yet." [level=2] [ref=e446]
    - paragraph [ref=e447]: Good. Run them through Veklom first. Test, govern, and prove AI execution — before anything matters.
    - generic [ref=e448]:
      - link "Start a governed review" [ref=e449] [cursor=pointer]:
        - /url: /workspace/login
      - link "Read the docs" [ref=e450] [cursor=pointer]:
        - /url: /docs
  - generic [ref=e452]:
    - generic [ref=e453]:
      - text: Feedback
      - heading "Tell us what you think" [level=2] [ref=e454]
      - paragraph [ref=e455]: Report a bug, suggest a feature, or just say hi.
    - generic [ref=e456]:
      - combobox [ref=e457]:
        - option "Bug Report" [selected]
        - option "Suggestion"
        - option "General Feedback"
      - textbox "Subject" [ref=e458]
      - textbox "Describe your feedback..." [ref=e459]
      - button "Submit →" [ref=e460] [cursor=pointer]
  - contentinfo [ref=e461]:
    - generic [ref=e463]:
      - generic [ref=e464]:
        - link "Veklom Hub" [ref=e465] [cursor=pointer]:
          - /url: /
          - text: Veklom
          - generic [ref=e466]: Hub
        - paragraph [ref=e467]:
          - text: Sovereign Control Node
          - text: © Veklom
      - generic [ref=e468]:
        - heading "Product" [level=4] [ref=e469]
        - link "Workspace" [ref=e470] [cursor=pointer]:
          - /url: /workspace
        - link "Pricing" [ref=e471] [cursor=pointer]:
          - /url: "#pricing"
        - link "API Docs" [ref=e472] [cursor=pointer]:
          - /url: /docs
      - generic [ref=e473]:
        - heading "Resources" [level=4] [ref=e474]
        - link "Status" [ref=e475] [cursor=pointer]:
          - /url: /uptime
        - link "Docs" [ref=e476] [cursor=pointer]:
          - /url: /docs
        - link "Feedback" [ref=e477] [cursor=pointer]:
          - /url: "#feedback"
      - generic [ref=e478]:
        - heading "Legal" [level=4] [ref=e479]
        - link "Terms" [ref=e480] [cursor=pointer]:
          - /url: /legal/terms
        - link "Privacy" [ref=e481] [cursor=pointer]:
          - /url: /legal/privacy
        - link "Security" [ref=e482] [cursor=pointer]:
          - /url: mailto:security@veklom.com
```

# Test source

```ts
  52  |       page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  53  |       await expect(page.locator('body')).toBeVisible();
  54  |       expect(errors, `no landing JS errors on ${url}`).toHaveLength(0);
  55  |     }
  56  |   });
  57  | 
  58  |   test('@smoke auth: login/signup flow', async ({ page }) => {
  59  |     // Adjust selectors to your real forms.
  60  |     await page.goto(`${BASE}/signup`);
  61  |     await page.fill('input[type="email"]', process.env.TEST_EMAIL || 'smoke+signup@example.com');
  62  |     await page.fill('input[type="password"]', process.env.TEST_PASSWORD || 'Playwright!234');
  63  |     await page.getByRole('button', { name: /sign up|create/i }).click();
  64  | 
  65  |     // TODO: replace with your post-signup landing selector
  66  |     await page.waitForLoadState('networkidle');
  67  |     // Accept either direct workspace or email verification interstitial
  68  |     const workspace = page.getByRole('heading', { name: /workspace|command center|dashboard/i });
  69  |     await expect(workspace.or(page.getByText(/verify|check your email/i))).toBeVisible();
  70  | 
  71  |     // Try login as well (idempotent if already signed up)
  72  |     await page.goto(`${BASE}/login`);
  73  |     await page.fill('input[type="email"]', process.env.TEST_EMAIL || 'smoke+signup@example.com');
  74  |     await page.fill('input[type="password"]', process.env.TEST_PASSWORD || 'Playwright!234');
  75  |     await page.getByRole('button', { name: /sign in|log in/i }).click();
  76  |     await page.waitForLoadState('networkidle');
  77  |     await expect(page.getByRole('main')).toBeVisible();
  78  |   });
  79  | 
  80  |   test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
  81  |     await page.goto(`${BASE}/workspace`);
  82  |     await page.waitForLoadState('networkidle');
  83  | 
  84  |     // Check that the key apps/sections at least render
  85  |     const expected = [
  86  |       /terminal|console/i,
  87  |       /marketplace|apps/i,
  88  |       /pipelines?|workflow/i,
  89  |       /billing|subscription/i
  90  |     ];
  91  |     for (const pattern of expected) {
  92  |       await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 });
  93  |     }
  94  | 
  95  |     // Try a simple no-op job/run button if present
  96  |     const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
  97  |     if (await runBtn.isVisible().catch(() => false)) {
  98  |       await runBtn.click();
  99  |       await page.waitForTimeout(1000);
  100 |       await expect(page.locator('body')).toBeVisible();
  101 |     }
  102 |   });
  103 | 
  104 |   test('@smoke footer & DSA/Contact presence', async ({ page }) => {
  105 |     await page.goto(BASE);
  106 |     await page.getByRole('contentinfo'); // footer landmark
  107 |     const footerLinks = [
  108 |       /terms|tos/i,
  109 |       /privacy/i,
  110 |       /status/i,
  111 |       /contact|dsa|legal/i
  112 |     ];
  113 |     for (const l of footerLinks) {
  114 |       await expect(page.getByRole('link', { name: l }).first()).toBeVisible();
  115 |     }
  116 |   });
  117 | 
  118 |   test('@smoke headers: CSP/TLS/CORS sane', async ({ request }) => {
  119 |     const resp = await request.get(BASE, { ignoreHTTPSErrors: true });
  120 |     expect(resp.ok()).toBeTruthy();
  121 | 
  122 |     const csp = resp.headers()['content-security-policy'];
  123 |     expect(csp, 'CSP present').toBeTruthy();
  124 | 
  125 |     const hsts = resp.headers()['strict-transport-security'];
  126 |     expect(hsts || '', 'HSTS present').toMatch(/max-age=\d+/i);
  127 | 
  128 |     const cors = resp.headers()['access-control-allow-origin'];
  129 |     // Allow either specific origin or wildcard on API only
  130 |     expect(cors === undefined || cors === '*' || /^https?:\/\//.test(cors)).toBeTruthy();
  131 | 
  132 |     const frame = resp.headers()['x-frame-options'];
  133 |     expect((frame || '').toUpperCase()).toMatch(/SAMEORIGIN|DENY/);
  134 |   });
  135 | 
  136 |   test('@smoke PostHog events emit (if enabled)', async ({ page }) => {
  137 |     // Skip if no key configured on site or in env
  138 |     await page.route('**/capture/*', route => {
  139 |       // Let it pass; we'll inspect later
  140 |       route.continue();
  141 |     });
  142 |     const requests: { url: string; body?: string }[] = [];
  143 |     page.on('requestfinished', async req => {
  144 |       if (req.url().includes('/capture/') || req.url().includes('/e/')) {
  145 |         let body = '';
  146 |         try { body = (await req.postData()) || ''; } catch {}
  147 |         requests.push({ url: req.url(), body });
  148 |       }
  149 |     });
  150 |     await page.goto(BASE);
  151 |     await page.waitForTimeout(1500);
> 152 |     expect(requests.length, 'At least one analytics event should fire').toBeGreaterThan(0);
      |                                                                         ^ Error: At least one analytics event should fire
  153 |   });
  154 | 
  155 |   test('@smoke known failing endpoints return expected failures', async ({ request }) => {
  156 |     test.skip(failingList.length === 0, 'No FAILING_ENDPOINTS provided');
  157 |     for (const item of failingList) {
  158 |       // Format: "METHOD /path"
  159 |       const [method, path] = item.split(/\s+/);
  160 |       const url = path.startsWith('http') ? path : `${API}${path}`;
  161 |       const resp = await request.fetch(url, { method: method as any });
  162 |       // Expect 4xx/5xx (adjust as needed)
  163 |       expect(String(resp.status())).toMatch(/^(400|401|403|404|409|422|500|502|503)$/);
  164 |     }
  165 |   });
  166 | 
  167 |   test('@smoke auth required for workspace-scoped status', async ({ request }) => {
  168 |     const r = await request.get(endpoints.statusDataWorkspace);
  169 |     expect([401, 403]).toContain(r.status());
  170 |   });
  171 | });
  172 | 
```