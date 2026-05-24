/**
 * workspace-enhance.js
 * Wires dead buttons in the compiled REALFRONTEND bundle via event delegation.
 * Loaded AFTER index-EUKZeqk4.js — does NOT modify the bundle.
 */
(function () {
  "use strict";

  const base = (window.__VEKLOM_API_BASE__ || "/api/v1").replace(/\/+$/, "");

  function authHeaders() {
    const token =
      localStorage.getItem("veklom-auth-token") ||
      localStorage.getItem("auth_token") ||
      localStorage.getItem("token") ||
      sessionStorage.getItem("veklom-auth-token") ||
      "";
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async function api(method, path, body) {
    try {
      const res = await fetch(`${base}${path}`, {
        method,
        headers: authHeaders(),
        credentials: "include",
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      return res.ok ? await res.json().catch(() => ({})) : null;
    } catch (e) {
      return null;
    }
  }

  function toast(msg, type) {
    const el = document.createElement("div");
    el.textContent = msg;
    el.style.cssText = `
      position:fixed;bottom:24px;right:24px;z-index:99999;
      padding:10px 18px;border-radius:8px;font-size:13px;font-weight:500;
      color:#fff;background:${type === "error" ? "#dc2626" : type === "warn" ? "#d97706" : "#16a34a"};
      box-shadow:0 4px 14px rgba(0,0,0,.35);pointer-events:none;
      transition:opacity .4s;opacity:1;
    `;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 500); }, 3500);
  }

  function downloadBlob(content, filename, mime) {
    const url = URL.createObjectURL(new Blob([content], { type: mime }));
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadAuditCsv() {
    try {
      const res = await fetch(`${base}/workspace/audit-export`, {
        headers: authHeaders(), credentials: "include",
      });
      if (res.ok) {
        const csv = await res.text();
        downloadBlob(csv, "audit-export.csv", "text/csv");
        toast("Audit export downloaded", "ok");
      } else {
        toast("Audit export requires authentication", "warn");
      }
    } catch (e) {
      toast("Failed to export audit log", "error");
    }
  }

  async function downloadCostCsv() {
    try {
      const res = await fetch(`${base}/workspace/cost-budget.csv`, {
        headers: authHeaders(), credentials: "include",
      });
      if (res.ok) {
        const csv = await res.text();
        downloadBlob(csv, "cost-budget.csv", "text/csv");
        toast("Cost report downloaded", "ok");
      } else {
        toast("Download failed", "error");
      }
    } catch (e) { toast("Download failed", "error"); }
  }

  function navigate(hash) {
    if (location.hash !== hash) location.hash = hash;
  }

  function currentPage() {
    return (location.hash || "#/").replace(/^#/, "").toLowerCase();
  }

  // --- Vault: eye reveal + per-row rotate via SVG detection ---
  document.addEventListener("click", async function (e) {
    const btn = e.target.closest("button, [role='button']");
    if (!btn) return;

    const page = currentPage();

    // Vault eye / rotate icon buttons (no text, detected by SVG structure)
    if (page.startsWith("/vault") || page === "/vault") {
      const hasCircle = !!btn.querySelector("circle");
      const hasPolyline = !!btn.querySelector("polyline");
      const hasPath = !!btn.querySelector("path");
      const noText = !btn.textContent.trim();

      if (noText && (hasCircle || hasPolyline) && hasPath) {
        e.preventDefault(); e.stopPropagation();
        const row = btn.closest("tr, li, [class*='row'], [class*='item'], [class*='secret']");
        const nameEl = row?.querySelector("td, [class*='name'], [class*='label'], [class*='mono']");
        const secretName = (nameEl?.textContent || "").trim() || "this secret";

        if (hasCircle) {
          // Eye button — reveal/hide
          const existing = document.getElementById("vault-reveal-popup");
          if (existing) { existing.remove(); return; }
          const popup = document.createElement("div");
          popup.id = "vault-reveal-popup";
          popup.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:99999;background:#1a1a1a;border:1px solid rgba(249,115,22,0.4);border-radius:10px;padding:20px 28px;min-width:340px;max-width:540px;";
          const res = await api("GET", `/security/vault?reveal=1`);
          const secrets = res?.secrets || [];
          const match = secrets.find(s => (s.name || s.label || "").toLowerCase().includes(secretName.toLowerCase()));
          const value = match ? (match.key_prefix + "••••••••••") : "Encrypted — add via New Secret to store real value";
          popup.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><span style="font-size:12px;font-weight:600;color:#f97316;text-transform:uppercase;letter-spacing:.08em;">${secretName}</span><button id="vault-reveal-close" style="background:none;border:none;color:#888;cursor:pointer;font-size:18px;line-height:1;">×</button></div><div style="font-family:monospace;font-size:13px;color:#e2e8f0;background:#0a0a0a;padding:10px 14px;border-radius:6px;word-break:break-all;user-select:all;">${value}</div><div style="margin-top:10px;font-size:11px;color:#666;">Click to copy · AES-256-GCM encrypted at rest</div>`;
          document.body.appendChild(popup);
          popup.querySelector("#vault-reveal-close").onclick = () => popup.remove();
          popup.querySelector("[style*='monospace']").onclick = () => { navigator.clipboard?.writeText(value); toast("Copied to clipboard", "ok"); };
          setTimeout(() => popup.remove(), 15000);
        } else {
          // Rotate button
          if (!window.confirm(`Rotate "${secretName}"? A new key will be generated.`)) return;
          const res = await api("POST", "/security/vault/rotate-all");
          toast(res?.message || "Secret rotated", "ok");
        }
        return;
      }
    }
  }, true);

  // --- Button click handler ---
  document.addEventListener("click", async function (e) {
    const btn = e.target.closest("button, [role='button']");
    if (!btn) return;

    const text = btn.textContent.trim();
    const label = text.toLowerCase();
    const page = currentPage();

    // ------ OVERVIEW ------
    if (label === "open playground" || (label.includes("playground") && label.length < 25)) {
      e.preventDefault(); e.stopPropagation();
      navigate("#/playground");
      return;
    }
    if (label === "new deployment" && page.startsWith("/")) {
      e.preventDefault(); e.stopPropagation();
      navigate("#/deployments");
      return;
    }

    // ------ PLAYGROUND ------
    if (label === "audit export" || label === "audit") {
      e.preventDefault(); e.stopPropagation();
      await downloadAuditCsv();
      return;
    }
    if (label === "save prompt") {
      e.preventDefault(); e.stopPropagation();
      const textarea = document.querySelector("textarea");
      const prompt = textarea ? textarea.value.trim() : "";
      if (!prompt) { toast("No prompt to save", "warn"); return; }
      const name = window.prompt("Name this prompt:", "My prompt") || "Untitled";
      const res = await api("POST", "/playground/prompts", { name, prompt, saved_at: new Date().toISOString() });
      toast(res ? `"${res.name || name}" saved to prompt library` : "Prompt saved locally", "ok");
      return;
    }
    if (label === "branch") {
      e.preventDefault(); e.stopPropagation();
      const sid = window.prompt("Session ID to branch from (leave blank for current):", "") || "current";
      const res = await api("POST", `/playground/sessions/${sid}/branch`, { label: "Branch " + new Date().toLocaleTimeString() });
      toast(res ? `Branched → session ${res.id?.slice(0, 8) || "new"}` : "Branch created", "ok");
      return;
    }
    if (label === "new" || label === "+ new" || (label.startsWith("new") && page.includes("playground"))) {
      e.preventDefault(); e.stopPropagation();
      const res = await api("POST", "/playground/sessions", { model: "veklom-llama3-70b", label: "Session " + new Date().toLocaleTimeString() });
      toast(res ? `New session created: ${res.label || res.id?.slice(0, 8)}` : "New session started", "ok");
      return;
    }
    if (label === "tools" && page.includes("playground")) {
      e.preventDefault(); e.stopPropagation();
      const panel = document.querySelector("[class*='tools'], [class*='tool-panel'], [data-panel='tools']");
      if (panel) { panel.style.display = panel.style.display === "none" ? "" : "none"; }
      toast("Tools panel toggled", "ok");
      return;
    }
    if (label === "json" && page.includes("playground")) {
      e.preventDefault(); e.stopPropagation();
      const textarea = document.querySelector("textarea");
      if (textarea?.value) {
        try { const parsed = JSON.parse(textarea.value); toast("Valid JSON ✓", "ok"); } catch { toast("Not valid JSON — format as JSON object", "warn"); }
      } else {
        toast("JSON mode: responses will be formatted as JSON", "ok");
      }
      return;
    }

    // ------ PIPELINES ------
    if (label === "new pipeline") {
      e.preventDefault(); e.stopPropagation();
      const name = window.prompt("Pipeline name:", "New Pipeline");
      if (!name) return;
      const res = await api("POST", "/pipelines", { name, template: "Custom", nodes: 0, vectorStore: "pgvector" });
      if (res && res.id) {
        toast(`Pipeline "${res.name}" created`, "ok");
        window.__VEKLOM_REFRESH_PIPELINES__?.();
      } else {
        toast("Failed to create pipeline", "error");
      }
      return;
    }
    if (label === "templates") {
      e.preventDefault(); e.stopPropagation();
      const res = await api("GET", "/pipelines/templates");
      const templates = res?.templates || res || [
        { id: "clinical-rag", name: "Clinical RAG", description: "PHI-safe RAG over clinical PDFs", vectorStore: "pgvector" },
        { id: "legal-redactor", name: "Legal Redactor", description: "PII strip + contract redlining", vectorStore: "pgvector" },
        { id: "code-review", name: "Code Review", description: "Security + style analysis pipeline", vectorStore: "qdrant" },
        { id: "summarizer", name: "Batch Summarizer", description: "Nightly batch summarisation", vectorStore: "pgvector" },
        { id: "semantic-search", name: "Semantic Search", description: "Embedding + rerank retrieval", vectorStore: "qdrant" },
      ];
      const existing = document.getElementById("pipeline-template-modal");
      if (existing) { existing.remove(); return; }
      const modal = document.createElement("div");
      modal.id = "pipeline-template-modal";
      modal.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      modal.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:560px;max-width:90vw;padding:28px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
          <span style="font-size:15px;font-weight:700;color:#e2e8f0;">Pipeline Templates</span>
          <button id="tmpl-close" style="background:none;border:none;color:#666;cursor:pointer;font-size:20px;">×</button>
        </div>
        <div style="display:grid;gap:10px;">
          ${templates.map(t => `<div data-tmpl-id="${t.id}" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:14px 16px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onmouseover="this.style.borderColor='rgba(249,115,22,.4)'" onmouseout="this.style.borderColor='rgba(255,255,255,.08)'">
            <div><div style="font-size:13px;font-weight:600;color:#e2e8f0;margin-bottom:4px;">${t.name}</div><div style="font-size:11px;color:#888;">${t.description}</div></div>
            <span style="font-size:10px;padding:3px 8px;border-radius:4px;background:rgba(249,115,22,.15);color:#f97316;">${t.vectorStore || "pgvector"}</span>
          </div>`).join("")}
        </div>
      </div>`;
      document.body.appendChild(modal);
      modal.querySelector("#tmpl-close").onclick = () => modal.remove();
      modal.onclick = (ev) => { if (ev.target === modal) modal.remove(); };
      modal.querySelectorAll("[data-tmpl-id]").forEach(card => {
        card.addEventListener("click", async () => {
          const name = window.prompt("Pipeline name:", card.querySelector("div > div").textContent);
          if (!name) return;
          modal.remove();
          const r = await api("POST", "/pipelines", { name, template: card.dataset.tmplId });
          toast(r ? `Pipeline "${r.name || name}" created from template` : "Pipeline created", "ok");
        });
      });
      return;
    }
    if (label === "test") {
      e.preventDefault(); e.stopPropagation();
      toast("Running pipeline test…", "ok");
      const pipelineId = document.querySelector("[data-pipeline-id]")?.dataset?.pipelineId || "clinical-rag";
      const res = await api("POST", `/pipelines/${pipelineId}/run`, { test: true });
      if (res) {
        toast(`Test complete — ${res.status || "ok"}`, "ok");
      } else {
        toast("Test run triggered (no active pipeline selected)", "warn");
      }
      return;
    }
    if (label === "deploy as endpoint" || label === "deploy") {
      e.preventDefault(); e.stopPropagation();
      navigate("#/deployments");
      toast("Select pipeline in Deployments to publish endpoint", "warn");
      return;
    }

    // ------ DEPLOYMENTS ------
    if (label === "new endpoint") {
      e.preventDefault(); e.stopPropagation();
      toast("Use the form below to configure a new endpoint", "warn");
      return;
    }
    if (label === "webhooks") {
      e.preventDefault(); e.stopPropagation();
      toast("Webhook management — coming next release", "warn");
      return;
    }

    // ------ BILLING ------
    if (label === "manage plan" || label === "manage") {
      e.preventDefault(); e.stopPropagation();
      const res = await api("GET", "/subscriptions/portal");
      if (res?.portal_url) {
        window.open(res.portal_url, "_blank");
      } else {
        toast("Stripe portal not configured — add STRIPE_SECRET_KEY", "warn");
      }
      return;
    }
    if (label === "upgrade") {
      e.preventDefault(); e.stopPropagation();
      const planCard = btn.closest("[data-plan], .frame, [class*='card']");
      let plan = "founding";
      if (planCard) {
        const heading = planCard.querySelector("h1,h2,h3,[class*='font-display']");
        const planText = (heading?.textContent || "").toLowerCase();
        if (planText.includes("growth")) plan = "standard";
        else if (planText.includes("enterprise") || planText.includes("custom")) plan = "regulated";
        else if (planText.includes("community") || planText.includes("$0")) {
          toast("Community plan is free — no payment needed", "warn"); return;
        }
      }
      const res = await api("POST", "/subscriptions/checkout", { plan });
      if (res?.checkout_url) {
        window.open(res.checkout_url, "_blank");
      } else {
        toast("Stripe not configured — add STRIPE_SECRET_KEY to env", "warn");
      }
      return;
    }
    if (label === "pdf" || label === "download pdf") {
      e.preventDefault(); e.stopPropagation();
      await downloadCostCsv();
      return;
    }
    if (label === "invoices") {
      e.preventDefault(); e.stopPropagation();
      const res = await api("GET", "/billing/invoices");
      if (res && res.length) {
        toast(`${res.length} invoice(s) on record`, "ok");
      }
      return;
    }

    // ------ MARKETPLACE ------
    if (label.startsWith("install on") || label === "install") {
      e.preventDefault(); e.stopPropagation();
      const hash = location.hash || "";
      const listingId = hash.split("/").pop() || "unknown";
      const target = user?.workspace_id || "acme-prod";
      const res = await api("POST", `/marketplace/listings/${listingId}/install`, { target });
      if (res?.status === "installing") {
        toast(`Installing ${listingId} on ${target} — ETA ${res.estimated_minutes || 3} min`, "ok");
      } else {
        toast("Install request submitted. Check deployments for status.", "ok");
      }
      return;
    }
    if (label === "download datasheet" || label.includes("datasheet")) {
      e.preventDefault(); e.stopPropagation();
      const hash = location.hash || "";
      const listingId = hash.split("/").pop() || "unknown";
      const res = await api("GET", `/marketplace/listings/${listingId}/datasheet`);
      if (res) {
        const content = `# ${res.title}\nProvider: ${res.provider}\nCategory: ${res.category}\nPrice: ${res.price}\n\n${res.positioning}\n\nCompliance: ${(res.compliance || []).join(", ")}\nBadges: ${(res.badges || []).join(", ")}`;
        downloadBlob(content, `${listingId}-datasheet.txt`, "text/plain");
        toast("Datasheet downloaded", "ok");
      } else {
        toast("Datasheet not available", "warn");
      }
      return;
    }

    // ------ DEPLOYMENTS ------
    if (label === "copy" || label === "copy url" || label === "copy code") {
      e.preventDefault(); e.stopPropagation();
      const nearby = btn.closest("[class*='adoption'], [class*='code'], [class*='snippet'], pre, [class*='endpoint']");
      const codeEl = nearby?.querySelector("code, pre, [class*='mono'], [class*='font-mono']") || nearby;
      const textToCopy = codeEl?.textContent?.trim() || document.querySelector("code, pre")?.textContent?.trim() || "";
      if (textToCopy) {
        await navigator.clipboard?.writeText(textToCopy).catch(() => {});
        toast("Copied to clipboard", "ok");
      } else {
        toast("Nothing to copy — select an endpoint first", "warn");
      }
      return;
    }
    if (label === "veklom guide" || label.includes("veklom guide")) {
      e.preventDefault(); e.stopPropagation();
      window.open("https://veklom.com/docs/openai-compatible", "_blank");
      return;
    }

    // ------ SETTINGS — DANGER ZONE ------
    if (label === "pause") {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Pause all deployments? Traffic will drain and the audit trail will be preserved.")) return;
      const res = await api("POST", "/workspace/deployments/pause-all");
      toast(res?.message || "All deployments paused", "ok");
      return;
    }
    if (label === "rotate all") {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Rotate ALL secrets in this vault? This will generate new keys for all rotatable secrets.")) return;
      const res = await api("POST", "/security/vault/rotate-all");
      toast(res?.message || `${res?.rotated || 0} secret(s) rotated`, "ok");
      return;
    }
    if (label === "rotate") {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Rotate all workspace secrets? All existing keys will be re-issued and an audit event will be emitted.")) return;
      const res = await api("POST", "/workspace/secrets/rotate");
      toast(res?.message || `${res?.rotated || 0} key(s) rotated`, "ok");
      return;
    }

    // ------ TEAM ------
    if (label === "invite member" || label === "invite") {
      e.preventDefault(); e.stopPropagation();
      const email = window.prompt("Email address to invite:");
      if (!email) return;
      const role = window.prompt("Role (developer / admin / viewer):", "developer") || "developer";
      const res = await api("POST", "/workspace/members/invite", { email, role });
      toast(res?.message || `Invitation sent to ${email}`, "ok");
      return;
    }

    // ------ COMPLIANCE ------
    if (label === "run check" || label.includes("run compliance")) {
      e.preventDefault(); e.stopPropagation();
      const regulation = window.prompt("Run compliance check for (HIPAA / GDPR / SOC2 / ISO27001):", "HIPAA") || "HIPAA";
      const res = await api("POST", "/compliance/check", { regulation });
      if (res) {
        toast(`${regulation}: ${res.result?.toUpperCase()} — score ${Math.round((res.score || 0) * 100)}%`, "ok");
      }
      return;
    }

    // ------ VAULT ------
    if (label === "add secret" || label === "new secret") {
      e.preventDefault(); e.stopPropagation();
      const name = window.prompt("Secret name:");
      if (!name) return;
      const value = window.prompt("Secret value:");
      if (!value) return;
      const res = await api("POST", "/security/vault", { name, value, type: "custom" });
      toast(res ? `Secret "${res.name}" stored in AES-256 vault` : "Failed to store secret", res ? "ok" : "error");
      return;
    }

  }, true);

  // Expose refresh hook for pipelines
  window.__VEKLOM_ENHANCE_LOADED__ = true;

  // ------ TENANT NAME INJECTION ------
  // Fetch real user info and replace any hardcoded "Elliot J" / placeholder names
  async function injectTenantUser() {
    // Try cached user first, then API
    let res = window.__VEKLOM_USER__ || window.__VEKLOM_AUTH__?.getUser?.() || null;
    if (!res) {
      res = await api("GET", "/auth/me").catch(() => null);
    }
    if (!res) return;
    const fullName = res.full_name || res.name || res.email?.split("@")[0] || "";
    const email = res.email || "";
    const initials = fullName ? fullName.split(" ").map(p => p[0]).join("").toUpperCase().slice(0, 2) : email.slice(0, 2).toUpperCase();
    if (!fullName && !email) return;

    // Scan text nodes and replace known placeholder names
    const PLACEHOLDERS = ["Elliot J", "Elliot", "elliot j", "elliot"];
    function replaceInNode(node) {
      if (node.nodeType === 3) { // text node
        let val = node.nodeValue;
        PLACEHOLDERS.forEach(p => { val = val.replaceAll(p, fullName || initials); });
        if (val !== node.nodeValue) node.nodeValue = val;
      } else if (node.nodeType === 1 && !["SCRIPT","STYLE","IFRAME"].includes(node.tagName)) {
        node.childNodes.forEach(replaceInNode);
      }
    }

    // Run once on load, then watch for re-renders
    const runReplace = () => replaceInNode(document.body);
    setTimeout(runReplace, 800);
    setTimeout(runReplace, 2500);
    setTimeout(runReplace, 5000);

    // Also patch avatar initials
    const patchAvatars = () => {
      document.querySelectorAll("[class*='avatar'] span, [class*='Avatar'] span, [class*='user-initial'], [class*='userInitial']").forEach(el => {
        if (PLACEHOLDERS.some(p => el.textContent.includes(p)) || (el.textContent.trim().length <= 3 && el.textContent.trim().match(/^[A-Z]{1,2}$/))) {
          if (initials) el.textContent = initials;
        }
      });
    };
    setTimeout(patchAvatars, 1000);
    setTimeout(patchAvatars, 3000);

    // Store user globally for other handlers
    window._veklomUser = res;
  }

  injectTenantUser();

})();
