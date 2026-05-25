/**
 * playground-live.js
 * Wires the Playground page against the real backend:
 *  - Sessions: track current, new → create in DB
 *  - Prompt Library: seed defaults, click → load into textarea
 *  - Branch: use current session ID, surface result banner
 *  - Parameters: sliders update live cost / token estimate
 */
(function () {
  "use strict";

  const base = (window.__VEKLOM_API_BASE__ || "/api/v1").replace(/\/+$/, "");

  function getToken() {
    const keys = ["access_token","accessToken","token","authToken","veklom_token","veklom-auth-token","auth_token","veklom.access_token"];
    for (const k of keys) {
      const v = localStorage.getItem(k) || sessionStorage.getItem(k);
      if (v) return v;
    }
    return "";
  }

  function authHdrs() {
    const t = getToken();
    return {
      "Content-Type": "application/json",
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
    };
  }

  async function apiCall(method, path, body) {
    try {
      const res = await fetch(`${base}${path}`, {
        method,
        headers: authHdrs(),
        credentials: "include",
        ...(body != null ? { body: JSON.stringify(body) } : {}),
      });
      return res.ok ? await res.json().catch(() => null) : null;
    } catch (_) {
      return null;
    }
  }

  function toast(msg, type) {
    const existing = document.getElementById("pg-toast");
    if (existing) existing.remove();
    const el = document.createElement("div");
    el.id = "pg-toast";
    el.textContent = msg;
    el.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:99999;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:500;color:#fff;background:${type === "error" ? "#dc2626" : type === "warn" ? "#d97706" : "#16a34a"};box-shadow:0 4px 14px rgba(0,0,0,.35);pointer-events:none;opacity:1;transition:opacity .4s;`;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 500); }, 3500);
  }

  // ── State ──────────────────────────────────────────────────────────────────
  window._veklomCurrentSessionId = window._veklomCurrentSessionId || null;
  window._veklomSessions          = window._veklomSessions         || [];
  window._veklomPrompts           = window._veklomPrompts          || [];
  window._veklomParams            = window._veklomParams           || { temperature: 0.7, top_p: 0.95, top_k: 40, max_tokens: 1024, frequency_penalty: 0, presence_penalty: 0 };

  // ── Default Prompts ────────────────────────────────────────────────────────
  const DEFAULT_PROMPTS = [
    {
      name: "ssci.evidence_collect",
      slug: "ssci_evidence_collect",
      body: "Collect and summarize peer-reviewed scientific evidence on the following topic:\n\n{{topic}}\n\nProvide citations and confidence levels for each claim. Use APA format.",
      tags: ["science", "research", "evidence"],
    },
    {
      name: "phi_summarize.json",
      slug: "phi_summarize_json",
      body: "Summarize the following clinical note while removing all PHI/PII:\n\n{{note}}\n\nReturn structured JSON with keys: diagnosis, medications, follow_up, redacted_fields.",
      tags: ["healthcare", "phi", "json"],
    },
    {
      name: "outbound_public_policy",
      slug: "outbound_public_policy",
      body: "Draft a public policy statement for the following topic:\n\n{{topic}}\n\nTone: professional. Length: ~300 words. Include: objectives, stakeholders, implementation steps.",
      tags: ["policy", "governance"],
    },
    {
      name: "code_repair.flm",
      slug: "code_repair_flm",
      body: "Review the following code and return a corrected version with explanations:\n\n```\n{{code}}\n```\n\nIdentify: bugs, security vulnerabilities, performance issues, style violations.",
      tags: ["code", "review", "repair"],
    },
    {
      name: "legal_redactor_v3",
      slug: "legal_redactor_v3",
      body: "Redact and summarize the following legal document:\n\n{{document}}\n\nRemove: names, dates, case numbers, addresses. Preserve: legal arguments, obligations, terms.",
      tags: ["legal", "redaction", "privacy"],
    },
    {
      name: "risk_classifier_eval",
      slug: "risk_classifier_eval",
      body: "Classify the risk level of the following input and justify your classification:\n\n{{input}}\n\nOutput JSON: { risk_level: 'low|medium|high|critical', justification: string, recommended_action: string }",
      tags: ["risk", "classification", "compliance"],
    },
  ];

  // ── Sessions ───────────────────────────────────────────────────────────────
  async function loadSessions() {
    const sessions = await apiCall("GET", "/playground/sessions");
    if (Array.isArray(sessions)) {
      window._veklomSessions = sessions;
      if (sessions.length > 0 && !window._veklomCurrentSessionId) {
        window._veklomCurrentSessionId = sessions[0].id;
      }
    }
    return window._veklomSessions;
  }

  // ── Prompts ────────────────────────────────────────────────────────────────
  async function loadAndSeedPrompts() {
    const prompts = await apiCall("GET", "/playground/prompts");
    if (Array.isArray(prompts) && prompts.length > 0) {
      window._veklomPrompts = prompts;
      return;
    }
    // Empty — seed defaults
    const seeded = [];
    for (const p of DEFAULT_PROMPTS) {
      const created = await apiCall("POST", "/playground/prompts", p);
      if (created) seeded.push(created);
    }
    window._veklomPrompts = seeded;
    if (seeded.length > 0) toast(`Prompt library seeded with ${seeded.length} defaults`, "ok");
  }

  function loadPromptIntoTextarea(promptBody) {
    const selectors = [
      'textarea',
      '[contenteditable="true"]',
      '[placeholder*="send" i]',
      '[placeholder*="message" i]',
      '[data-lexical-editor]',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (!el) continue;
      if (el.tagName === "TEXTAREA") {
        el.value = promptBody;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        el.focus();
        return true;
      } else {
        el.textContent = promptBody;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.focus();
        return true;
      }
    }
    return false;
  }

  // ── Branch ─────────────────────────────────────────────────────────────────
  async function branchCurrentSession() {
    const sessionId = window._veklomCurrentSessionId;
    if (!sessionId) {
      toast("No active session — click a session in the list first, then branch", "warn");
      return null;
    }
    const session = window._veklomSessions.find(s => s.id === sessionId);
    const branchName = `${(session?.name || "Session").replace(/ \(branch.*\)$/, "")} (branch ${new Date().toLocaleTimeString()})`;
    const branch = await apiCall("POST", `/playground/sessions/${sessionId}/branch`, { name: branchName });
    if (!branch) {
      toast("Branch failed — session not found in database", "error");
      return null;
    }
    window._veklomSessions.unshift(branch);
    window._veklomCurrentSessionId = branch.id;
    document.body.dataset.veklomSessionId = branch.id;

    // Persistent banner showing the new branch
    document.getElementById("veklom-branch-banner")?.remove();
    const banner = document.createElement("div");
    banner.id = "veklom-branch-banner";
    banner.style.cssText = "position:fixed;top:72px;right:24px;z-index:99998;background:#111;border:1px solid rgba(249,115,22,.5);border-radius:10px;padding:16px 18px;min-width:320px;font-size:13px;color:#e2e8f0;box-shadow:0 4px 24px rgba(0,0,0,.6);";
    banner.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-weight:700;color:#f97316;font-size:14px;">Branch Created</span>
        <button id="vbb-close" style="background:none;border:none;color:#666;cursor:pointer;font-size:18px;line-height:1;">×</button>
      </div>
      <div style="font-size:12px;color:#aaa;margin-bottom:4px;">Name: <span style="color:#e2e8f0;font-weight:600;">${branch.name}</span></div>
      <div style="font-family:monospace;font-size:11px;color:#555;margin-bottom:10px;">ID: ${branch.id}</div>
      <div style="font-size:11px;color:#f97316;line-height:1.5;">
        ↩ Branch is now the active session.<br>
        New messages will run in this branch.<br>
        The original session is preserved.
      </div>
    `;
    document.body.appendChild(banner);
    banner.querySelector("#vbb-close").onclick = () => banner.remove();
    setTimeout(() => banner.remove(), 15000);
    return branch;
  }

  // Expose so workspace-enhance.js branch handler can delegate here
  window._veklomBranchHandler = branchCurrentSession;

  // ── Parameters → Live Cost ─────────────────────────────────────────────────
  const COST_PER_TOKEN = { input: 0.0000006, output: 0.0000008 }; // Llama 3 70B approx

  function estimateCost(maxTokens) {
    const avgInput = 512;
    const output = Math.min(maxTokens, 4096);
    return (avgInput * COST_PER_TOKEN.input + output * COST_PER_TOKEN.output).toFixed(5);
  }

  function wireParameterSliders() {
    document.addEventListener("input", function (e) {
      if (!location.hash.includes("playground")) return;
      const target = e.target;
      if (target.tagName !== "INPUT" || target.type !== "range") return;

      const val = parseFloat(target.value);

      // Identify the slider from its nearby label
      const container = target.closest(
        "[class*='param'], [class*='field'], [class*='row'], tr, li, [class*='slider']"
      );
      const labelEl = container?.querySelector("span, label, [class*='label'], [class*='name']");
      const labelText = (labelEl?.textContent || "").toLowerCase();

      // Store value
      if (labelText.includes("max") || labelText.includes("token")) {
        window._veklomParams.max_tokens = val;
      } else if (labelText.includes("temp")) {
        window._veklomParams.temperature = val;
      } else if (labelText.includes("top-p") || labelText.includes("top p")) {
        window._veklomParams.top_p = val;
      } else if (labelText.includes("top-k") || labelText.includes("top k")) {
        window._veklomParams.top_k = val;
      } else if (labelText.includes("freq")) {
        window._veklomParams.frequency_penalty = val;
      } else if (labelText.includes("pres")) {
        window._veklomParams.presence_penalty = val;
      }

      // Update any cost / token display in the bottom status bar
      const costStr = `$${estimateCost(window._veklomParams.max_tokens)}`;
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      let updated = 0;
      while (node && updated < 2) {
        const v = node.nodeValue.trim();
        if (/^\$\d+\.\d{4}/.test(v)) {
          node.nodeValue = costStr;
          updated++;
        }
        node = walker.nextNode();
      }

      // Update the tokens display (e.g. "1024" shown near max tokens)
      if (labelText.includes("max") || labelText.includes("token")) {
        const valueDisplays = document.querySelectorAll(
          "[class*='value'], [class*='param-value'], [class*='token-count']"
        );
        valueDisplays.forEach(el => {
          const n = parseInt(el.textContent, 10);
          if (n >= 64 && n <= 8192 && el !== target) {
            el.textContent = Math.round(val).toString();
          }
        });
      }
    });
  }

  // ── Click Detection: Sessions & Prompts ────────────────────────────────────
  function watchLeftPanelClicks() {
    document.addEventListener("click", async function (e) {
      if (!location.hash.includes("playground")) return;

      const el = e.target.closest(
        "li, [class*='item'], [class*='row'], [class*='session'], [class*='prompt'], [class*='entry'], button"
      );
      if (!el) return;

      const text = (el.textContent || "").trim().slice(0, 100).toLowerCase();

      // ---- Prompt library clicks ----
      if (window._veklomPrompts.length > 0) {
        const matchedPrompt = window._veklomPrompts.find(p => {
          const slug = (p.slug || p.name || "").toLowerCase();
          const name = (p.name || "").toLowerCase();
          return (slug.length > 4 && text.includes(slug.slice(0, 20))) ||
                 (name.length > 4 && text.includes(name.toLowerCase().slice(0, 20)));
        });
        if (matchedPrompt && matchedPrompt.body) {
          const loaded = loadPromptIntoTextarea(matchedPrompt.body);
          if (loaded) {
            toast(`Prompt "${matchedPrompt.name}" loaded`, "ok");
            return;
          }
        }
      }

      // ---- Session clicks ----
      if (window._veklomSessions.length > 0) {
        const matchedSession = window._veklomSessions.find(s => {
          const name = (s.name || "").toLowerCase();
          return name.length > 4 && text.includes(name.slice(0, 25));
        });
        if (matchedSession) {
          window._veklomCurrentSessionId = matchedSession.id;
          document.body.dataset.veklomSessionId = matchedSession.id;
          document.body.dataset.veklomSessionName = matchedSession.name;
          toast(
            `Session: "${matchedSession.name}" (${matchedSession.messages?.length || 0} messages)`,
            "ok"
          );
        }
      }
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  async function init() {
    const hash = location.hash || "";
    if (!hash.includes("playground")) return;

    await loadSessions();
    await loadAndSeedPrompts();
    wireParameterSliders();
    watchLeftPanelClicks();
    window._pgLiveInit = true;
  }

  function maybeInit() {
    if (window._pgLiveInit) return;
    if ((location.hash || "").includes("playground")) init();
  }

  window.addEventListener("hashchange", () => {
    window._pgLiveInit = false;
    setTimeout(maybeInit, 400);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(maybeInit, 600));
  } else {
    setTimeout(maybeInit, 600);
  }
})();
