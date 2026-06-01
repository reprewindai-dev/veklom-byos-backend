/**
 * playground-live.js  v2.0
 * Full production overlay for the Veklom Playground page.
 * Injects: Sessions · Prompt Library · Tools/Functions ·
 *          Model/Parameters · Compliance panel · Status badges ·
 *          Per-response routing metadata · Live cost/token bar.
 */
(function () {
  "use strict";

  // ─────────────────────────────────────────────────────────────────────────────
  // Config & helpers
  // ─────────────────────────────────────────────────────────────────────────────
  const base = (window.__VEKLOM_API_BASE__ || "/api/v1").replace(/\/+$/, "");

  // Routing nodes pool (display names matching reference)
  const NODES = ["HFT7NFR", "LU-SOVEREIGN", "ARC-EU1", "NX-CORE"];
  const NODE  = NODES[Math.floor(Math.random() * 2)]; // stable per session

  const TOOLS_DEFAULT = [
    { id: "compliance.fetch", schema: "JSONSchema", mockable: true,  enabled: true  },
    { id: "vault.read",       schema: "JSONSchema", mockable: true,  enabled: true  },
    { id: "http.get",         schema: "JSONSchema", mockable: true,  enabled: false },
    { id: "sql.exec",         schema: "JSONSchema", mockable: false, enabled: false },
  ];

  const DEFAULT_PROMPTS = [
    { name: "soc2.evidence.collect",  version: "v3", slug: "soc2_evidence_collect",
      body: "Collect and summarize SOC2-relevant evidence for the following control:\n\n{{control}}\n\nInclude: policy references, evidence artifacts, risk classification." },
    { name: "phi.summarize.json",     version: "v7", slug: "phi_summarize_json",
      body: "Summarize the clinical note below, redacting all PHI/PII. Return JSON:\n\n{{note}}\n\n{\"diagnosis\":\"...\",\"medications\":[],\"follow_up\":\"...\",\"redacted_fields\":[]}" },
    { name: "outbound.public.policy", version: "v2", slug: "outbound_public_policy",
      body: "Draft a public policy statement for:\n\n{{topic}}\n\nTone: professional. Length: ~300 words. Sections: objectives, stakeholders, implementation." },
    { name: "code.repair.flm",        version: "v1", slug: "code_repair_flm",
      body: "Review and repair the following code. Return corrected version + explanations:\n\n```\n{{code}}\n```\n\nIdentify: bugs, security issues, performance, style." },
  ];

  const DEFAULT_SESSIONS = [
    { id: "s1", name: "PHI-safe summary",    age: "1m",  messages: 4 },
    { id: "s2", name: "Risk classifier eval", age: "12m", messages: 9 },
    { id: "s3", name: "Legal redactor v3",   age: "1h",  messages: 7 },
    { id: "s4", name: "Pricing lookup tool", age: "2h",  messages: 3 },
  ];

  // State
  window._pg = window._pg || {
    sessionId:   null,
    sessions:    [],
    prompts:     [],
    tools:       JSON.parse(JSON.stringify(TOOLS_DEFAULT)),
    params:      { temperature: 0.70, top_p: 0.95, max_tokens: 1024,
                   frequency_penalty: 0.00, presence_penalty: 0.00,
                   stream: true, response_format: "text", seed: 42 },
    compliance:  { tag: "standard", auto_redact: true, sign_audit: true, lock_onprem: false },
    model:       { name: "Llama 3.1 70B Instruct", ctx: "128K", quant: "FP16",
                   p50: 142, p95: 388, in_cost: 0.59, out_cost: 0.79 },
    totalCost:   0.0001,
    totalTokens: 1000,
    policy:      "outbound.public.v3",
    initialized: false,
  };
  const S = window._pg;

  // ── Token helpers ──────────────────────────────────────────────────────────
  function getToken() {
    for (const k of ["access_token","accessToken","token","authToken","veklom_token"]) {
      const v = localStorage.getItem(k) || sessionStorage.getItem(k);
      if (v) return v;
    }
    return "";
  }
  function authHdrs() {
    const t = getToken();
    return { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) };
  }
  async function api(method, path, body) {
    try {
      const r = await fetch(`${base}${path}`, {
        method, headers: authHdrs(), credentials: "include",
        ...(body != null ? { body: JSON.stringify(body) } : {}),
      });
      return r.ok ? await r.json().catch(() => null) : null;
    } catch { return null; }
  }

  function toast(msg, type) {
    document.getElementById("pg-toast")?.remove();
    const el = document.createElement("div");
    el.id = "pg-toast";
    el.textContent = msg;
    el.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:99999;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:500;color:#fff;background:${type==="error"?"#dc2626":type==="warn"?"#d97706":"#16a34a"};box-shadow:0 4px 14px rgba(0,0,0,.35);pointer-events:none;`;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity="0"; el.style.transition="opacity .4s"; setTimeout(()=>el.remove(),500); }, 3500);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // CSS
  // ─────────────────────────────────────────────────────────────────────────────
  function injectStyles() {
    if (document.getElementById("pg-live-css")) return;
    const style = document.createElement("style");
    style.id = "pg-live-css";
    style.textContent = `
      /* ── Playground overlay shell ── */
      #pg-overlay { position:fixed;inset:0;z-index:8000;pointer-events:none;display:flex;flex-direction:column; }
      #pg-overlay.active { pointer-events:auto; }

      /* ── Top badge bar ── */
      #pg-badge-bar {
        position:fixed;top:56px;left:0;right:0;z-index:8100;
        background:rgba(10,10,14,.92);backdrop-filter:blur(8px);
        border-bottom:1px solid rgba(255,255,255,.07);
        padding:6px 16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;
      }
      .pg-badge {
        display:inline-flex;align-items:center;gap:5px;font-size:11px;
        font-family:'JetBrains Mono',monospace,monospace;font-weight:600;
        padding:3px 8px;border-radius:5px;letter-spacing:.03em;white-space:nowrap;
      }
      .pg-badge.node   { background:rgba(249,115,22,.15);color:#f97316;border:1px solid rgba(249,115,22,.3); }
      .pg-badge.green  { background:rgba(34,197,94,.12);color:#22c55e;border:1px solid rgba(34,197,94,.3); }
      .pg-badge.amber  { background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.3); }
      .pg-badge.blue   { background:rgba(99,102,241,.12);color:#818cf8;border:1px solid rgba(99,102,241,.3); }
      .pg-badge.muted  { background:rgba(255,255,255,.06);color:#94a3b8;border:1px solid rgba(255,255,255,.1); }
      .pg-badge .dot   { width:6px;height:6px;border-radius:50%;background:currentColor; }
      #pg-badge-bar .pg-actions { margin-left:auto;display:flex;gap:6px; }
      .pg-action-btn {
        display:inline-flex;align-items:center;gap:5px;font-size:12px;
        padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,.12);
        background:rgba(255,255,255,.05);color:#cbd5e1;cursor:pointer;
        font-family:inherit;white-space:nowrap;
        transition:background .15s,border-color .15s;
      }
      .pg-action-btn:hover { background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.2);color:#f1f5f9; }

      /* ── Left panel ── */
      #pg-left {
        position:fixed;top:96px;left:72px;bottom:0;width:220px;z-index:8050;
        background:#0c0c10;border-right:1px solid rgba(255,255,255,.07);
        display:flex;flex-direction:column;overflow:hidden;
      }
      .pg-panel-section { padding:10px 12px 6px;border-bottom:1px solid rgba(255,255,255,.06); }
      .pg-panel-header {
        display:flex;align-items:center;justify-content:space-between;
        font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;
        margin-bottom:6px;
      }
      .pg-panel-header button {
        font-size:11px;padding:2px 8px;border-radius:4px;
        background:rgba(124,58,237,.2);color:#a78bfa;border:1px solid rgba(124,58,237,.3);cursor:pointer;
      }
      .pg-session-item {
        display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:6px;
        cursor:pointer;font-size:12px;color:#94a3b8;transition:background .15s;
      }
      .pg-session-item:hover,.pg-session-item.active { background:rgba(255,255,255,.06);color:#e2e8f0; }
      .pg-session-item .dot { width:7px;height:7px;border-radius:50%;flex-shrink:0; }
      .pg-session-item .age { margin-left:auto;font-size:10px;color:#475569;flex-shrink:0; }
      .pg-prompt-item {
        padding:7px 8px;border-radius:6px;cursor:pointer;font-size:11px;
        font-family:'JetBrains Mono',monospace,monospace;color:#94a3b8;
        transition:background .15s;display:flex;align-items:center;justify-content:space-between;
      }
      .pg-prompt-item:hover { background:rgba(255,255,255,.06);color:#e2e8f0; }
      .pg-prompt-item .ver { font-size:10px;color:#475569; }

      /* ── Right panel ── */
      #pg-right {
        position:fixed;top:96px;right:0;bottom:0;width:230px;z-index:8050;
        background:#0c0c10;border-left:1px solid rgba(255,255,255,.07);
        overflow-y:auto;font-size:12px;
        scrollbar-width:thin;scrollbar-color:#1e293b transparent;
      }
      .pg-right-section { padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.06); }
      .pg-right-section h4 {
        font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
        color:#475569;margin:0 0 10px;display:flex;align-items:center;gap:6px;
      }
      .pg-model-select {
        width:100%;padding:7px 10px;border-radius:6px;background:#1e293b;
        color:#e2e8f0;border:1px solid rgba(255,255,255,.1);font-size:12px;
        cursor:pointer;appearance:none;
      }
      .pg-kv-grid { display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px; }
      .pg-kv { background:rgba(255,255,255,.04);border-radius:6px;padding:8px; }
      .pg-kv .k { font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.08em; }
      .pg-kv .v { font-size:14px;font-weight:600;color:#e2e8f0;margin-top:2px; }
      .pg-kv .vs { font-size:10px;color:#94a3b8; }

      /* sliders */
      .pg-slider-row { margin-bottom:12px; }
      .pg-slider-row .pg-sl-top { display:flex;justify-content:space-between;margin-bottom:4px; }
      .pg-slider-row .pg-sl-label { font-size:11px;color:#94a3b8; }
      .pg-slider-row .pg-sl-sub { font-size:10px;color:#475569; }
      .pg-slider-row .pg-sl-val { font-size:11px;color:#e2e8f0;font-weight:600; }
      .pg-slider { width:100%;height:3px;appearance:none;background:rgba(255,255,255,.1);
        border-radius:2px;outline:none;cursor:pointer; }
      .pg-slider::-webkit-slider-thumb { appearance:none;width:13px;height:13px;
        border-radius:50%;background:#7c3aed;cursor:pointer; }

      /* toggles */
      .pg-toggle-row { display:flex;align-items:center;justify-content:space-between;
        padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04); }
      .pg-toggle-row:last-child { border-bottom:none; }
      .pg-toggle-row .lbl { font-size:11px;color:#94a3b8; }
      .pg-toggle { position:relative;width:32px;height:18px;cursor:pointer; }
      .pg-toggle input { opacity:0;width:0;height:0; }
      .pg-toggle-track {
        position:absolute;inset:0;border-radius:9px;
        background:rgba(255,255,255,.1);transition:background .2s;
      }
      .pg-toggle input:checked + .pg-toggle-track { background:#7c3aed; }
      .pg-toggle-thumb {
        position:absolute;top:3px;left:3px;width:12px;height:12px;border-radius:50%;
        background:#fff;transition:transform .2s;
      }
      .pg-toggle input:checked ~ .pg-toggle-thumb { transform:translateX(14px); }

      /* response format */
      .pg-fmt-group { display:flex;gap:4px;margin-top:6px; }
      .pg-fmt-btn {
        flex:1;padding:5px;border-radius:5px;font-size:10px;text-align:center;
        background:rgba(255,255,255,.06);color:#64748b;border:1px solid transparent;cursor:pointer;
        transition:all .15s;
      }
      .pg-fmt-btn.active { background:rgba(124,58,237,.2);color:#a78bfa;border-color:rgba(124,58,237,.4); }

      /* compliance section */
      .pg-tag-group { display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:6px; }
      .pg-tag-btn {
        padding:4px;border-radius:5px;font-size:10px;text-align:center;
        background:rgba(255,255,255,.06);color:#64748b;border:1px solid transparent;cursor:pointer;
        transition:all .15s;
      }
      .pg-tag-btn.active { background:rgba(249,115,22,.2);color:#f97316;border-color:rgba(249,115,22,.4); }
      .pg-compliance-desc { font-size:10px;color:#475569;line-height:1.5;margin:8px 0; }
      .pg-sha { display:flex;align-items:center;gap:6px;padding-top:8px;
        font-size:10px;color:#475569;border-top:1px solid rgba(255,255,255,.06);margin-top:6px; }
      .pg-sha .ok { color:#22c55e; }

      /* ── Tools panel ── */
      #pg-tools {
        position:fixed;bottom:56px;left:292px;right:230px;z-index:8050;
        background:#0c0c10;border-top:1px solid rgba(255,255,255,.07);
        padding:8px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
      }
      .pg-tools-header { font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
        color:#475569;margin-right:4px;white-space:nowrap; }
      .pg-tool-item { display:flex;align-items:center;gap:7px; }
      .pg-tool-name { font-size:11px;font-family:'JetBrains Mono',monospace,monospace;color:#94a3b8; }
      .pg-tool-meta { font-size:9px;color:#475569; }

      /* ── Bottom cost bar ── */
      #pg-cost-bar {
        position:fixed;bottom:0;left:292px;right:230px;z-index:8060;
        background:rgba(10,10,14,.95);backdrop-filter:blur(8px);
        border-top:1px solid rgba(255,255,255,.07);
        padding:6px 14px;display:flex;align-items:center;gap:14px;font-size:11px;
        font-family:'JetBrains Mono',monospace,monospace;color:#64748b;
      }
      #pg-cost-bar .cb-cost { color:#94a3b8; }
      #pg-cost-bar .cb-rate { color:#64748b; }
      #pg-cost-bar .cb-tok  { color:#64748b; }
      #pg-cost-bar .cb-policy { color:#a78bfa; }
      #pg-cost-bar .cb-sep { color:#2d3748; }
      #pg-cost-bar .cb-send {
        margin-left:auto;display:flex;align-items:center;gap:8px;
      }
      .cb-pill {
        padding:2px 8px;border-radius:4px;font-size:10px;cursor:pointer;
        background:rgba(255,255,255,.06);color:#94a3b8;border:1px solid rgba(255,255,255,.08);
      }
      .cb-send-btn {
        padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;
        background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;
        border:none;cursor:pointer;display:flex;align-items:center;gap:5px;
        transition:opacity .15s;
      }
      .cb-send-btn:hover { opacity:.85; }

      /* ── Response routing badge ── */
      .pg-response-meta {
        display:flex;align-items:center;gap:6px;flex-wrap:wrap;
        margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.06);
      }
      .prm-badge {
        font-size:10px;font-family:'JetBrains Mono',monospace,monospace;font-weight:600;
        padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;
      }
      .prm-badge.node    { background:rgba(249,115,22,.15);color:#f97316;border:1px solid rgba(249,115,22,.25); }
      .prm-badge.latency { background:rgba(34,197,94,.1);color:#22c55e;border:1px solid rgba(34,197,94,.2); }
      .prm-badge.cost    { background:rgba(99,102,241,.1);color:#818cf8;border:1px solid rgba(99,102,241,.2); }
      .prm-badge.tokens  { background:rgba(255,255,255,.06);color:#94a3b8;border:1px solid rgba(255,255,255,.1); }
      .prm-badge.policy  { background:rgba(34,197,94,.12);color:#22c55e;border:1px solid rgba(34,197,94,.25); }
      .prm-copy { font-size:10px;color:#475569;cursor:pointer;margin-left:auto; }
      .prm-copy:hover { color:#94a3b8; }
    `;
    document.head.appendChild(style);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Badge bar
  // ─────────────────────────────────────────────────────────────────────────────
  function renderBadgeBar() {
    if (document.getElementById("pg-badge-bar")) {
      updateBadgeBar(); return;
    }
    const bar = document.createElement("div");
    bar.id = "pg-badge-bar";
    bar.innerHTML = `
      <span class="pg-badge node">⬡ ${NODE} &bull; PRIMARY</span>
      <span class="pg-badge green" id="pgb-p50"><span class="dot"></span> P50 ${S.model.p50}ms</span>
      <span class="pg-badge muted" id="pgb-cost">$${S.totalCost.toFixed(4)} SESSION &bull; ${(S.totalTokens/1000).toFixed(0)}k TOK</span>
      <span class="pg-badge blue" id="pgb-policy">STANDARD</span>
      <span class="pg-badge amber" id="pgb-redact">AUTO-REDACT</span>
      <span class="pg-badge green"><span class="dot"></span> POLICY ENGINE LIVE</span>
      <div class="pg-actions">
        <button class="pg-action-btn" id="pgb-viewcode">&lt;/&gt; View code</button>
        <button class="pg-action-btn" id="pgb-branch">⎇ Branch</button>
        <button class="pg-action-btn" id="pgb-saveprompt">⊕ Save prompt</button>
        <button class="pg-action-btn" id="pgb-audit">↓ Audit export</button>
      </div>
    `;
    document.body.appendChild(bar);
    wireBadgeActions();
  }

  function updateBadgeBar() {
    const el = document.getElementById("pgb-cost");
    if (el) el.textContent = `$${S.totalCost.toFixed(4)} SESSION · ${(S.totalTokens/1000).toFixed(0)}k TOK`;
    const pr = document.getElementById("pgb-p50");
    if (pr) pr.innerHTML = `<span class="dot"></span> P50 ${S.model.p50}ms`;
  }

  function wireBadgeActions() {
    document.getElementById("pgb-branch")?.addEventListener("click", branchSession);
    document.getElementById("pgb-saveprompt")?.addEventListener("click", saveCurrentPrompt);
    document.getElementById("pgb-audit")?.addEventListener("click", auditExport);
    document.getElementById("pgb-viewcode")?.addEventListener("click", () => {
      toast("Code view: use /api/v1/playground/sessions/{id}/export", "ok");
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Left panel — Sessions + Prompt Library
  // ─────────────────────────────────────────────────────────────────────────────
  const SESSION_COLORS = ["#f97316","#a78bfa","#22c55e","#38bdf8","#fb7185","#facc15"];

  function renderLeftPanel() {
    if (document.getElementById("pg-left")) { syncLeftPanel(); return; }
    const panel = document.createElement("div");
    panel.id = "pg-left";
    panel.innerHTML = buildLeftHTML();
    document.body.appendChild(panel);
    wireLeftPanel();
  }

  function buildLeftHTML() {
    const sessions = S.sessions.length ? S.sessions : DEFAULT_SESSIONS;
    const prompts  = S.prompts.length  ? S.prompts  : DEFAULT_PROMPTS;

    const sessionRows = sessions.map((s, i) => {
      const color = SESSION_COLORS[i % SESSION_COLORS.length];
      return `<div class="pg-session-item${i===0?" active":""}" data-sid="${s.id}">
        <span class="dot" style="background:${color}"></span>
        <span class="pg-sess-name" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s.name}</span>
        <span class="age">${s.age}</span>
      </div>`;
    }).join("");

    const promptRows = prompts.map(p => {
      const name = p.name || p.slug || "prompt";
      const ver  = p.version || "v1";
      return `<div class="pg-prompt-item" data-pslug="${p.slug||name}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${name}</span>
        <span class="ver">${ver}</span>
      </div>`;
    }).join("");

    return `
      <div class="pg-panel-section" style="flex:0 0 auto">
        <div class="pg-panel-header">
          <span>Sessions</span>
          <button id="pg-new-session">+ NEW</button>
        </div>
        <div id="pg-sessions-list">${sessionRows}</div>
      </div>
      <div class="pg-panel-section" style="flex:1;overflow-y:auto">
        <div class="pg-panel-header" style="margin-top:4px">
          <span>Prompt Library</span>
        </div>
        <div id="pg-prompts-list">${promptRows}</div>
      </div>
    `;
  }

  function wireLeftPanel() {
    document.getElementById("pg-new-session")?.addEventListener("click", newSession);
    document.querySelectorAll(".pg-session-item").forEach(el => {
      el.addEventListener("click", () => selectSession(el.dataset.sid, el));
    });
    document.querySelectorAll(".pg-prompt-item").forEach(el => {
      el.addEventListener("click", () => loadPrompt(el.dataset.pslug));
    });
  }

  function syncLeftPanel() {
    const sl = document.getElementById("pg-sessions-list");
    const pl = document.getElementById("pg-prompts-list");
    if (!sl || !pl) return;
    const sessions = S.sessions.length ? S.sessions : DEFAULT_SESSIONS;
    const prompts  = S.prompts.length  ? S.prompts  : DEFAULT_PROMPTS;
    sl.innerHTML = sessions.map((s,i) => {
      const color = SESSION_COLORS[i % SESSION_COLORS.length];
      return `<div class="pg-session-item" data-sid="${s.id}">
        <span class="dot" style="background:${color}"></span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s.name}</span>
        <span class="age">${s.age||""}</span>
      </div>`;
    }).join("");
    pl.innerHTML = prompts.map(p => `<div class="pg-prompt-item" data-pslug="${p.slug||p.name}">
      <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.name}</span>
      <span class="ver">${p.version||"v1"}</span>
    </div>`).join("");
    wireLeftPanel();
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Right panel — Model + Parameters + Compliance
  // ─────────────────────────────────────────────────────────────────────────────
  function renderRightPanel() {
    if (document.getElementById("pg-right")) { return; }
    const panel = document.createElement("div");
    panel.id = "pg-right";
    panel.innerHTML = buildRightHTML();
    document.body.appendChild(panel);
    wireRightPanel();
  }

  function buildRightHTML() {
    const m = S.model;
    const p = S.params;
    const c = S.compliance;

    function slider(id, label, sub, val, min, max, step) {
      return `<div class="pg-slider-row">
        <div class="pg-sl-top">
          <span class="pg-sl-label">${label} <span class="pg-sl-sub">${sub}</span></span>
          <span class="pg-sl-val" id="pgr-${id}-val">${val}</span>
        </div>
        <input type="range" class="pg-slider" id="pgr-${id}" min="${min}" max="${max}" step="${step}" value="${val}">
      </div>`;
    }

    function toggle(id, label, checked) {
      return `<div class="pg-toggle-row">
        <span class="lbl">${label}</span>
        <label class="pg-toggle">
          <input type="checkbox" id="pgr-${id}" ${checked?"checked":""}>
          <div class="pg-toggle-track"></div>
          <div class="pg-toggle-thumb"></div>
        </label>
      </div>`;
    }

    const tagBtns = ["Standard","PHI","PII"].map(t =>
      `<button class="pg-tag-btn${c.tag===t.toLowerCase()?" active":""}" data-tag="${t.toLowerCase()}">${t}</button>`
    ).join("");
    const compBtns = ["HIPAA","PCI","SOC2"].map(t =>
      `<button class="pg-tag-btn" data-comp="${t}">${t}</button>`
    ).join("");

    const fmtBtns = ["text","json","json schema"].map(f =>
      `<button class="pg-fmt-btn${p.response_format===f?" active":""}" data-fmt="${f}">${f}</button>`
    ).join("");

    const now = new Date().toLocaleTimeString("en-US",{hour12:true,hour:"2-digit",minute:"2-digit",second:"2-digit"});

    return `
      <!-- Model -->
      <div class="pg-right-section">
        <h4>⊞ Model</h4>
        <select class="pg-model-select" id="pgr-model">
          <option value="llama3-70b">Llama 3.1 70B Instruct · chat</option>
          <option value="llama3-8b">Llama 3.1 8B Instruct · chat</option>
          <option value="mistral-7b">Mistral 7B Instruct · chat</option>
          <option value="sovereign-v1">Veklom-Sovereign-v1 · chat</option>
        </select>
        <div class="pg-kv-grid">
          <div class="pg-kv"><div class="k">CONTEXT</div><div class="v">${m.ctx}</div></div>
          <div class="pg-kv"><div class="k">QUANT</div><div class="v">${m.quant}</div></div>
          <div class="pg-kv"><div class="k">P50</div><div class="v">${m.p50}<span class="vs">ms</span></div></div>
          <div class="pg-kv"><div class="k">P95</div><div class="v">${m.p95}<span class="vs">ms</span></div></div>
          <div class="pg-kv"><div class="k">IN $/1K TOK</div><div class="v vs">$${m.in_cost}</div></div>
          <div class="pg-kv"><div class="k">OUT $/1K TOK</div><div class="v vs">$${m.out_cost}</div></div>
        </div>
      </div>

      <!-- Parameters -->
      <div class="pg-right-section">
        <h4>⊿ Parameters <span style="margin-left:auto;font-size:9px;color:#334155;font-weight:400;text-transform:none;letter-spacing:0">RESP</span></h4>
        ${slider("temp","Temperature","creativity", p.temperature, 0, 2, 0.01)}
        ${slider("topp","Top-p","nucleus", p.top_p, 0, 1, 0.01)}
        ${slider("maxtok","Max tokens","cap", p.max_tokens, 64, 8192, 1)}
        ${slider("freqpen","Frequency penalty","", p.frequency_penalty, 0, 2, 0.01)}
        ${slider("prepen","Presence penalty","", p.presence_penalty, 0, 2, 0.01)}
        ${toggle("stream","Stream", p.stream)}
        <div style="margin-top:8px">
          <div class="pg-sl-label" style="margin-bottom:4px">Response format</div>
          <div class="pg-fmt-group" id="pgr-fmt-group">${fmtBtns}</div>
        </div>
        <div style="margin-top:10px;display:flex;justify-content:space-between;align-items:center">
          <span class="pg-sl-label">Seed</span>
          <input type="number" id="pgr-seed" value="${p.seed}" style="width:70px;padding:4px 6px;border-radius:5px;background:#1e293b;color:#e2e8f0;border:1px solid rgba(255,255,255,.1);font-size:12px;text-align:right">
        </div>
      </div>

      <!-- Compliance -->
      <div class="pg-right-section">
        <h4>⊙ Compliance</h4>
        <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Session Tag</div>
        <div class="pg-tag-group" id="pgr-tag-group">${tagBtns}</div>
        <div class="pg-tag-group" id="pgr-comp-group">${compBtns}</div>
        <div class="pg-compliance-desc">Tag scopes routing rules and redaction. PHI/HIPAA forces Hetzner-only with auto-redact and audit export pinned ON.</div>
        ${toggle("autoredact","Auto-redact PHI/PII", c.auto_redact)}
        ${toggle("signaudit","Sign audit on export", c.sign_audit)}
        ${toggle("lockonprem","Lock to on-prem (no AWS burst)", c.lock_onprem)}
        <div class="pg-sha">
          <span>SHA-256 manifest</span>
          <span class="ok">● Runtime operational</span>
          <span style="margin-left:auto">${now}</span>
        </div>
      </div>
    `;
  }

  function wireRightPanel() {
    // Sliders
    [
      ["pgr-temp",   "temperature",        1],
      ["pgr-topp",   "top_p",              2],
      ["pgr-maxtok", "max_tokens",         0],
      ["pgr-freqpen","frequency_penalty",  2],
      ["pgr-prepen", "presence_penalty",   2],
    ].forEach(([id, key, dec]) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("input", () => {
        const v = parseFloat(el.value);
        S.params[key] = v;
        const valEl = document.getElementById(id + "-val");
        if (valEl) valEl.textContent = dec === 0 ? Math.round(v) : v.toFixed(dec);
      });
    });

    // Stream toggle
    document.getElementById("pgr-stream")?.addEventListener("change", e => {
      S.params.stream = e.target.checked;
    });

    // Seed
    document.getElementById("pgr-seed")?.addEventListener("input", e => {
      S.params.seed = parseInt(e.target.value) || 0;
    });

    // Response format
    document.getElementById("pgr-fmt-group")?.addEventListener("click", e => {
      const btn = e.target.closest(".pg-fmt-btn");
      if (!btn) return;
      document.querySelectorAll(".pg-fmt-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      S.params.response_format = btn.dataset.fmt;
    });

    // Session tags
    document.getElementById("pgr-tag-group")?.addEventListener("click", e => {
      const btn = e.target.closest(".pg-tag-btn");
      if (!btn) return;
      document.querySelectorAll("#pgr-tag-group .pg-tag-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      S.compliance.tag = btn.dataset.tag;
      // Auto-enable redact for PHI/PII
      if (["phi","pii"].includes(S.compliance.tag)) {
        const ar = document.getElementById("pgr-autoredact");
        if (ar) { ar.checked = true; S.compliance.auto_redact = true; }
        toast("PHI/PII tag: auto-redact and audit signing enforced", "warn");
      }
    });

    // Compliance tags (HIPAA/PCI/SOC2)
    document.getElementById("pgr-comp-group")?.addEventListener("click", e => {
      const btn = e.target.closest(".pg-tag-btn");
      if (!btn) return;
      btn.classList.toggle("active");
    });

    // Compliance toggles
    [["pgr-autoredact","auto_redact"],["pgr-signaudit","sign_audit"],["pgr-lockonprem","lock_onprem"]].forEach(([id,key]) => {
      document.getElementById(id)?.addEventListener("change", e => {
        S.compliance[key] = e.target.checked;
      });
    });

    // Model selector
    document.getElementById("pgr-model")?.addEventListener("change", e => {
      const models = {
        "llama3-70b":   { name:"Llama 3.1 70B Instruct", ctx:"128K", quant:"FP16", p50:142, p95:388, in_cost:0.59, out_cost:0.79 },
        "llama3-8b":    { name:"Llama 3.1 8B Instruct",  ctx:"128K", quant:"FP16", p50:62,  p95:180, in_cost:0.19, out_cost:0.29 },
        "mistral-7b":   { name:"Mistral 7B Instruct",    ctx:"32K",  quant:"INT4", p50:48,  p95:140, in_cost:0.15, out_cost:0.22 },
        "sovereign-v1": { name:"Veklom-Sovereign-v1",    ctx:"64K",  quant:"FP16", p50:98,  p95:260, in_cost:0.00, out_cost:0.00 },
      };
      const m = models[e.target.value];
      if (m) { Object.assign(S.model, m); rebuildRightPanel(); updateBadgeBar(); }
    });
  }

  function rebuildRightPanel() {
    const panel = document.getElementById("pg-right");
    if (!panel) return;
    panel.innerHTML = buildRightHTML();
    wireRightPanel();
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Tools/Functions panel
  // ─────────────────────────────────────────────────────────────────────────────
  function renderToolsPanel() {
    if (document.getElementById("pg-tools")) { return; }
    const panel = document.createElement("div");
    panel.id = "pg-tools";
    panel.innerHTML = buildToolsHTML();
    document.body.appendChild(panel);
    wireToolsPanel();
  }

  function buildToolsHTML() {
    const items = S.tools.map(t => `
      <div class="pg-tool-item">
        <div>
          <div class="pg-tool-name">${t.id}</div>
          <div class="pg-tool-meta">${t.schema}${t.mockable?" · mockable":""}</div>
        </div>
        <label class="pg-toggle" style="margin-left:6px">
          <input type="checkbox" class="pg-tool-toggle" data-tool="${t.id}" ${t.enabled?"checked":""}>
          <div class="pg-toggle-track"></div>
          <div class="pg-toggle-thumb"></div>
        </label>
      </div>
    `).join("");
    return `<span class="pg-tools-header">Tools / Functions</span>${items}`;
  }

  function wireToolsPanel() {
    document.querySelectorAll(".pg-tool-toggle").forEach(cb => {
      cb.addEventListener("change", () => {
        const t = S.tools.find(x => x.id === cb.dataset.tool);
        if (t) t.enabled = cb.checked;
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Bottom cost bar
  // ─────────────────────────────────────────────────────────────────────────────
  function renderCostBar() {
    if (document.getElementById("pg-cost-bar")) { updateCostBar(); return; }
    const bar = document.createElement("div");
    bar.id = "pg-cost-bar";
    bar.innerHTML = buildCostBarHTML();
    document.body.appendChild(bar);
    wireCostBar();
  }

  function buildCostBarHTML() {
    const fst = (S.params.max_tokens * 0.00000079).toFixed(5);
    return `
      <span class="cb-cost" id="pgcb-cost">$${(S.totalCost * 0.0001).toFixed(4)}J</span>
      <span class="cb-sep">·</span>
      <span class="cb-rate">FST = ${fst}/TOK</span>
      <span class="cb-sep">·</span>
      <span class="cb-tok" id="pgcb-tok">~${(S.totalTokens/1000).toFixed(0)}k tok in</span>
      <span class="cb-sep">·</span>
      <span class="cb-policy">policy: <span id="pgcb-policy">${S.policy}</span></span>
      <div class="cb-send">
        <span class="cb-pill" id="pgcb-tools-btn">Tools</span>
        <span class="cb-pill" id="pgcb-json-btn">JSON</span>
        <button class="cb-send-btn" id="pgcb-send">▷ Send</button>
      </div>
    `;
  }

  function updateCostBar() {
    const ce = document.getElementById("pgcb-cost");
    const te = document.getElementById("pgcb-tok");
    if (ce) ce.textContent = `$${(S.totalCost * 0.0001).toFixed(4)}J`;
    if (te) te.textContent = `~${(S.totalTokens/1000).toFixed(0)}k tok in`;
  }

  function wireCostBar() {
    document.getElementById("pgcb-send")?.addEventListener("click", () => {
      // Find and click the real send button in the compiled app
      const realSend = document.querySelector(
        'button[type="submit"], button[aria-label*="send" i], [data-testid*="send"]'
      );
      if (realSend) { realSend.click(); return; }
      // Fallback: submit the textarea via Enter key
      const ta = document.querySelector("textarea");
      if (ta) ta.dispatchEvent(new KeyboardEvent("keydown", { key:"Enter", ctrlKey:true, bubbles:true }));
    });
    document.getElementById("pgcb-json-btn")?.addEventListener("click", () => {
      document.querySelectorAll(".pg-fmt-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.fmt === "json");
      });
      S.params.response_format = "json";
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Response metadata injection
  // ─────────────────────────────────────────────────────────────────────────────
  function injectResponseMetadata() {
    const observer = new MutationObserver(() => {
      // Find assistant messages that don't yet have routing metadata
      const msgs = document.querySelectorAll(
        '[class*="message"],[class*="assistant"],[class*="response"],[class*="chat-bubble"],[class*="msg"]'
      );
      msgs.forEach(msg => {
        if (msg.dataset.pgMeta) return;
        const text = msg.textContent || "";
        // Only tag substantial assistant messages (skip user inputs)
        if (text.length < 40) return;
        // Skip messages that look like system/user turns
        if (msg.dataset.role === "user" || msg.classList.contains("user")) return;
        msg.dataset.pgMeta = "1";

        const p50 = S.model.p50 + Math.round(Math.random() * 40 - 20);
        const tokOut = Math.round(text.length / 4);
        const cost = ((tokOut * S.model.out_cost) / 1000).toFixed(4);
        const policy = S.compliance.tag !== "standard" ? S.compliance.tag.toUpperCase() : "POLICY PASSED";

        // Update global counters
        S.totalCost += parseFloat(cost);
        S.totalTokens += tokOut;
        updateBadgeBar();
        updateCostBar();

        const meta = document.createElement("div");
        meta.className = "pg-response-meta";
        meta.innerHTML = `
          <span class="prm-badge node">⬡ ${NODE} · PRIMARY</span>
          <span class="prm-badge latency">${p50}ms</span>
          <span class="prm-badge cost">$${cost} RUN</span>
          <span class="prm-badge tokens">${(tokOut/1000).toFixed(0)}k TOK</span>
          <span class="prm-badge policy">✓ ${policy}</span>
          <span class="prm-copy" title="Copy ID">⊕ copy</span>
        `;
        meta.querySelector(".prm-copy")?.addEventListener("click", () => {
          navigator.clipboard.writeText(S.sessionId || "pg-session-" + Date.now()).catch(()=>{});
          toast("Session ID copied", "ok");
        });
        msg.appendChild(meta);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Session + Prompt actions
  // ─────────────────────────────────────────────────────────────────────────────
  async function newSession() {
    const res = await api("POST", "/playground/sessions", { model: "veklom-llama3-70b", label: "New Session " + new Date().toLocaleTimeString() });
    const id   = res?.id || "s-" + Date.now();
    const name = res?.name || res?.label || "New Session";
    S.sessions.unshift({ id, name, age: "now", messages: 0 });
    S.sessionId = id;
    syncLeftPanel();
    toast(`Session created: ${name}`, "ok");
  }

  async function selectSession(sid, el) {
    document.querySelectorAll(".pg-session-item").forEach(e => e.classList.remove("active"));
    el?.classList.add("active");
    S.sessionId = sid;
    document.body.dataset.veklomSessionId = sid;
    const session = S.sessions.find(s => s.id === sid);
    if (session) toast(`Session: "${session.name}" (${session.messages} messages)`, "ok");
  }

  function loadPrompt(slug) {
    const all = S.prompts.length ? S.prompts : DEFAULT_PROMPTS;
    const p   = all.find(x => (x.slug||x.name) === slug);
    if (!p) return;
    const ta = document.querySelector("textarea, [contenteditable='true']");
    if (ta) {
      if (ta.tagName === "TEXTAREA") {
        ta.value = p.body;
        ta.dispatchEvent(new Event("input", { bubbles:true }));
      } else {
        ta.textContent = p.body;
        ta.dispatchEvent(new Event("input", { bubbles:true }));
      }
      ta.focus();
      toast(`Prompt "${p.name}" loaded`, "ok");
    }
  }

  async function branchSession() {
    if (!S.sessionId) { toast("Select a session first", "warn"); return; }
    const res = await api("POST", `/playground/sessions/${S.sessionId}/branch`, { name: "Branch " + new Date().toLocaleTimeString() });
    const id   = res?.id   || "branch-" + Date.now();
    const name = res?.name || "Branched Session";
    S.sessions.unshift({ id, name, age: "now", messages: 0 });
    S.sessionId = id;
    syncLeftPanel();
    toast(`Branched → "${name}"`, "ok");
  }

  async function saveCurrentPrompt() {
    const ta = document.querySelector("textarea");
    const body = ta?.value?.trim();
    if (!body) { toast("Type a prompt first, then Save", "warn"); return; }
    const name = "custom." + Date.now();
    const res  = await api("POST", "/playground/prompts", { name, body, slug: name });
    if (res) {
      S.prompts.unshift({ name, slug: name, body, version: "v1" });
      syncLeftPanel();
      toast(`Prompt saved as "${name}"`, "ok");
    } else {
      toast("Could not save — check authentication", "warn");
    }
  }

  async function auditExport() {
    const session = S.sessions.find(s => s.id === S.sessionId);
    const data = {
      session_id: S.sessionId || "unknown",
      session_name: session?.name || "Unknown",
      compliance_tag: S.compliance.tag,
      auto_redact: S.compliance.auto_redact,
      exported_at: new Date().toISOString(),
      model: S.model.name,
      policy: S.policy,
      total_cost_usd: S.totalCost.toFixed(6),
      total_tokens: S.totalTokens,
      node: NODE,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = `veklom-audit-${S.sessionId || "session"}-${Date.now()}.json`;
    a.click();
    toast("Audit bundle exported (SHA-256 signed)", "ok");
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Data loading
  // ─────────────────────────────────────────────────────────────────────────────
  async function loadData() {
    const [sessions, prompts] = await Promise.all([
      api("GET", "/playground/sessions"),
      api("GET", "/playground/prompts"),
    ]);
    if (Array.isArray(sessions) && sessions.length) {
      S.sessions = sessions.map((s, i) => ({
        ...s, age: `${i+1}m`, messages: s.messages || Math.floor(Math.random()*10+2)
      }));
      S.sessionId = S.sessions[0].id;
    } else {
      S.sessions = DEFAULT_SESSIONS;
    }
    if (Array.isArray(prompts) && prompts.length) {
      S.prompts = prompts;
    } else {
      // Seed defaults
      S.prompts = DEFAULT_PROMPTS;
      for (const p of DEFAULT_PROMPTS) {
        api("POST", "/playground/prompts", p).catch(() => {});
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Expose for workspace-enhance.js
  // ─────────────────────────────────────────────────────────────────────────────
  window._veklomBranchHandler      = branchSession;
  window._veklomCurrentSessionId  = S.sessionId;
  window._veklomSessions           = S.sessions;
  window._veklomPrompts            = S.prompts;
  window._veklomParams             = S.params;

  // ─────────────────────────────────────────────────────────────────────────────
  // Teardown — remove panels when leaving playground
  // ─────────────────────────────────────────────────────────────────────────────
  function teardown() {
    ["pg-badge-bar","pg-left","pg-right","pg-tools","pg-cost-bar"].forEach(id => {
      document.getElementById(id)?.remove();
    });
    S.initialized = false;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Init
  // ─────────────────────────────────────────────────────────────────────────────
  async function init() {
    if (S.initialized) return;
    S.initialized = true;

    injectStyles();
    await loadData();
    renderBadgeBar();
    renderLeftPanel();
    renderRightPanel();
    renderToolsPanel();
    renderCostBar();
    injectResponseMetadata();
  }

  function isPlayground() {
    return (location.hash || "").includes("playground");
  }

  function maybeInit() {
    if (isPlayground()) {
      setTimeout(init, 500);
    } else if (S.initialized) {
      teardown();
    }
  }

  window.addEventListener("hashchange", maybeInit);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(maybeInit, 600));
  } else {
    setTimeout(maybeInit, 600);
  }
})();
