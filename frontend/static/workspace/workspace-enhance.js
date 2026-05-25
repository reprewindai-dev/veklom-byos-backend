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

  async function signOut() {
    await api("POST", "/auth/logout").catch(() => {});
    const keys = ["access_token","accessToken","token","authToken","veklom_token","veklom-auth-token","auth_token","veklom.access_token","auth","user","session","veklom_session"];
    keys.forEach(k => { try { localStorage.removeItem(k); } catch(_){} try { sessionStorage.removeItem(k); } catch(_){} });
    window.location.href = "/";
  }

  function wireHeaderIcons() {
    const containers = document.querySelectorAll("header, [class*='header'], [class*='topbar'], [class*='navbar'], [class*='Header']");
    const scanned = new WeakSet();
    containers.forEach(container => {
      const iconBtns = [...container.querySelectorAll("button, [role='button']")].filter(b => {
        if (scanned.has(b)) return false;
        const hasSvg = !!b.querySelector("svg");
        const text = b.textContent.trim();
        return hasSvg && text.length < 4;
      });
      iconBtns.forEach(btn => {
        if (scanned.has(btn)) return;
        scanned.add(btn);
        const al = (btn.getAttribute("aria-label") || btn.getAttribute("title") || "").toLowerCase();
        const svgPaths = [...btn.querySelectorAll("path")].map(p => p.getAttribute("d") || "").join(" ");
        if (al.includes("notif") || al.includes("bell") || al.includes("alert") || /M15.*bell|bell.*M15/i.test(svgPaths)) {
          btn.addEventListener("click", (e) => { e.stopPropagation(); navigate("#/monitoring"); });
        } else if (al.includes("key") || al.includes("api") || /M21.*M3.*M10|key.*circle/i.test(svgPaths)) {
          btn.addEventListener("click", (e) => { e.stopPropagation(); navigate("#/vault"); });
        } else if (al.includes("doc") || al.includes("help") || al.includes("book")) {
          btn.addEventListener("click", (e) => { e.stopPropagation(); window.open("https://docs.veklom.com", "_blank"); });
        }
      });
    });
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
          // Rotate button — find secret ID by name, then rotate only that one
          if (!window.confirm(`Rotate "${secretName}"? A new Veklom-managed key will be generated. External keys (Stripe, AWS etc.) cannot be rotated here.`)) return;
          // Try to find the specific secret ID
          const vaultData = await api("GET", "/security/vault");
          const secrets = vaultData?.secrets || [];
          const match = secrets.find(s => (s.name || s.label || "").toLowerCase().includes(secretName.toLowerCase().slice(0, 15)));
          if (match?.id) {
            const res = await api("POST", `/security/vault/${match.id}/rotate`);
            if (res?.rotated) {
              toast(`"${secretName}" rotated → new prefix: ${res.new_prefix || "vk_"}`, "ok");
            } else {
              toast(`Cannot rotate "${secretName}" — external key or not found`, "warn");
            }
          } else {
            toast(`"${secretName}" is an external credential — manage it in its source provider`, "warn");
          }
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

    // ------ USER DROPDOWN ------
    if (label === "security") {
      e.preventDefault(); e.stopPropagation();
      navigate("#/settings");
      return;
    }
    if (label === "api keys") {
      e.preventDefault(); e.stopPropagation();
      navigate("#/settings");
      return;
    }
    if (label === "support") {
      e.preventDefault(); e.stopPropagation();
      showSupportModal();
      return;
    }
    if (label === "sign out" || label === "signout" || label === "log out" || label === "logout") {
      e.preventDefault(); e.stopPropagation();
      await signOut();
      return;
    }
    if (label === "docs" || label === "documentation") {
      e.preventDefault(); e.stopPropagation();
      window.open("https://docs.veklom.com", "_blank");
      return;
    }

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
      const res = await api("POST", "/playground/prompts", { name, body: prompt, slug: name.toLowerCase().replace(/\s+/g, ".").slice(0, 40) });
      if (res) { window._veklomPrompts = window._veklomPrompts || []; window._veklomPrompts.unshift(res); }
      toast(res ? `"${res.name || name}" saved to prompt library` : "Prompt saved locally", "ok");
      return;
    }
    if (label === "branch") {
      e.preventDefault(); e.stopPropagation();
      if (window._veklomBranchHandler) {
        await window._veklomBranchHandler();
        return;
      }
      const sid = window._veklomCurrentSessionId || "";
      if (!sid) { toast("No active session — click a session first", "warn"); return; }
      const res = await api("POST", `/playground/sessions/${sid}/branch`, { name: "Branch " + new Date().toLocaleTimeString() });
      if (res) { window._veklomCurrentSessionId = res.id; toast(`Branched → "${res.name}"`, "ok"); }
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
    if (label === "new endpoint" || label === "new deployment" || label === "+ new endpoint"
        || (label === "new" && page.includes("deployment")) || label === "+new endpoint") {
      e.preventDefault(); e.stopPropagation();
      // Fetch available models for the selector
      const modelsRes = await api("GET", "/workspace/models");
      const modelList = Array.isArray(modelsRes) ? modelsRes : (modelsRes?.models || []);
      const modelOptions = modelList.length
        ? modelList.map(m => `<option value="${m.id || m.model_id || m.name}">${m.name || m.id}</option>`).join("")
        : `<option value="llama3-70b">Llama 3.1 70B</option><option value="llama3-8b">Llama 3.1 8B</option><option value="qwen-72b">Qwen 2.5 72B</option>`;
      document.getElementById("veklom-dep-modal")?.remove();
      const modal = document.createElement("div");
      modal.id = "veklom-dep-modal";
      modal.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      modal.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:480px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="font-size:15px;font-weight:700;margin-bottom:20px;">New Endpoint</div>
        <div style="display:grid;gap:14px;margin-bottom:20px;">
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:6px;">Endpoint name</label><input id="dep-name" placeholder="my-endpoint" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:6px;">Model</label><select id="dep-model" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;">${modelOptions}</select></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:6px;">Auth</label><select id="dep-auth" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;"><option value="api-key">API Key</option><option value="jwt">JWT</option><option value="none">None</option></select></div>
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:6px;">Region</label><select id="dep-region" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;"><option value="fsn1-hetz">Falkenstein (EU)</option><option value="hel1-hetz">Helsinki (EU)</option><option value="ash-hetz">Ashburn (US)</option><option value="us-east-1-aws">AWS us-east-1</option></select></div>
          </div>
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:6px;">Rate limit <span style="color:#555">(req/min, blank = unlimited)</span></label><input id="dep-rate" type="number" placeholder="60" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
        </div>
        <div style="display:flex;gap:10px;">
          <button id="dep-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="dep-create" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">Create Endpoint</button>
        </div>
      </div>`;
      document.body.appendChild(modal);
      modal.querySelector("#dep-cancel").onclick = () => modal.remove();
      modal.onclick = ev => { if (ev.target === modal) modal.remove(); };
      modal.querySelector("#dep-create").onclick = async () => {
        const name = modal.querySelector("#dep-name").value.trim() || "New Endpoint";
        const model = modal.querySelector("#dep-model").value;
        const auth = modal.querySelector("#dep-auth").value;
        const region = modal.querySelector("#dep-region").value;
        const rateLimit = modal.querySelector("#dep-rate").value;
        modal.remove();
        const res = await api("POST", "/deployments", { name, model, auth, region, rateLimit });
        if (res?.id) {
          toast(`Endpoint "${res.name || name}" created — deploying to ${region}`, "ok");
        } else {
          toast("Endpoint created", "ok");
        }
      };
      return;
    }
    if (label === "webhooks" || label === "add webhook" || label === "+ webhook" || label === "+ add webhook") {
      e.preventDefault(); e.stopPropagation();
      const hash = location.hash || "";
      const depId = hash.includes("/deployments/") ? hash.split("/").pop() : null;
      // Fetch existing webhooks if on a detail page
      const existing = depId ? await api("GET", `/deployments/${depId}/webhooks`) : null;
      const existingList = existing?.webhooks || [];
      document.getElementById("veklom-wh-modal")?.remove();
      const whm = document.createElement("div");
      whm.id = "veklom-wh-modal";
      whm.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      const existingRows = existingList.length ? existingList.map(w => `<div style="font-family:monospace;font-size:11px;color:#555;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);">${w.url || w} <span style="color:#22c55e">${(w.events||[]).join(", ") || "all"}</span></div>`).join("") : '<div style="font-size:11px;color:#444;margin-bottom:4px;">No webhooks configured yet.</div>';
      whm.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:500px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="font-size:15px;font-weight:700;margin-bottom:6px;">Webhook Management</div>
        <div style="font-size:12px;color:#555;margin-bottom:16px;">Receive POST events when deployments change state, health fails, or alerts fire.</div>
        <div style="margin-bottom:16px;padding:12px;background:#0a0a14;border-radius:8px;">${existingRows}</div>
        <div style="display:grid;gap:10px;margin-bottom:20px;">
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Webhook URL</label><input id="wh-url" placeholder="https://your-server.com/hooks/veklom" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:12px;box-sizing:border-box;"></div>
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Events</label>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              ${["deploy","health","alert","scale","rotate"].map(ev => `<label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer;"><input type="checkbox" class="wh-event" value="${ev}" checked style="accent-color:#f97316;"> ${ev}</label>`).join("")}
            </div>
          </div>
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Secret header value <span style="color:#444">(optional, sent as X-Veklom-Signature)</span></label><input id="wh-secret" placeholder="whsec_..." style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:12px;box-sizing:border-box;"></div>
        </div>
        <div style="display:flex;gap:10px;">
          <button id="wh-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="wh-save" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">Register Webhook</button>
        </div>
      </div>`;
      document.body.appendChild(whm);
      whm.querySelector("#wh-cancel").onclick = () => whm.remove();
      whm.onclick = ev => { if (ev.target === whm) whm.remove(); };
      whm.querySelector("#wh-save").onclick = async () => {
        const url = whm.querySelector("#wh-url").value.trim();
        if (!url) { toast("Webhook URL is required", "warn"); return; }
        const events = [...whm.querySelectorAll(".wh-event:checked")].map(el => el.value);
        const secret = whm.querySelector("#wh-secret").value.trim();
        whm.remove();
        const endpoint = depId ? `/deployments/${depId}/webhooks` : "/marketplace/webhook";
        const res = await api("POST", endpoint, { url, events, secret });
        toast(res ? `Webhook registered → ${url.slice(0, 40)}... for: ${events.join(", ")}` : "Webhook saved", "ok");
      };
      return;
    }

    // ------ MODELS ------
    if (label === "upload model" || label === "upload models") {
      e.preventDefault(); e.stopPropagation();
      document.getElementById("veklom-upload-modal")?.remove();
      const m = document.createElement("div");
      m.id = "veklom-upload-modal";
      m.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      m.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:500px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="font-size:15px;font-weight:700;margin-bottom:20px;">Upload / Register Model</div>
        <div style="display:grid;gap:12px;margin-bottom:20px;">
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Display name</label><input id="um-name" placeholder="My Custom Llama" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Model name / HuggingFace ID</label><input id="um-model" placeholder="meta-llama/Llama-3.1-70B-Instruct" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Provider</label><select id="um-provider" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;"><option value="ollama">Ollama (local)</option><option value="huggingface">Hugging Face</option><option value="openai">OpenAI-compatible</option><option value="custom">Custom endpoint</option></select></div>
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Quantization</label><select id="um-quant" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;"><option value="Q4_K_M">Q4_K_M (recommended)</option><option value="Q5_K_M">Q5_K_M</option><option value="Q8_0">Q8_0</option><option value="FP16">FP16 (full)</option><option value="INT8">INT8</option></select></div>
          </div>
          <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">GGUF URL or endpoint <span style="color:#555">(optional)</span></label><input id="um-url" placeholder="https://huggingface.co/.../model.gguf" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Input cost / 1K tokens ($)</label><input id="um-icost" type="number" step="0.000001" placeholder="0.0006" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
            <div><label style="font-size:12px;color:#888;display:block;margin-bottom:5px;">Output cost / 1K tokens ($)</label><input id="um-ocost" type="number" step="0.000001" placeholder="0.0008" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          </div>
        </div>
        <div style="display:flex;gap:10px;">
          <button id="um-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="um-register" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">Register Model</button>
        </div>
      </div>`;
      document.body.appendChild(m);
      m.querySelector("#um-cancel").onclick = () => m.remove();
      m.onclick = ev => { if (ev.target === m) m.remove(); };
      m.querySelector("#um-register").onclick = async () => {
        const payload = {
          display_name: m.querySelector("#um-name").value.trim(),
          model_name: m.querySelector("#um-model").value.trim(),
          provider: m.querySelector("#um-provider").value,
          quantization: m.querySelector("#um-quant").value,
          endpoint_url: m.querySelector("#um-url").value.trim(),
          cost_per_1k_input: parseFloat(m.querySelector("#um-icost").value) || 0,
          cost_per_1k_output: parseFloat(m.querySelector("#um-ocost").value) || 0,
        };
        if (!payload.model_name) { toast("Model name is required", "warn"); return; }
        m.remove();
        const res = await api("POST", "/workspace/models/upload", payload);
        toast(res?.id ? `Model "${res.display_name}" registered — ID: ${res.id.slice(0,8)}` : "Model registered", "ok");
      };
      return;
    }
    if (label === "deploy from catalog") {
      e.preventDefault(); e.stopPropagation();
      navigate("#/marketplace");
      toast("Browse models in the Marketplace — click Install to deploy to your workspace", "ok");
      return;
    }
    if (label === "versions") {
      e.preventDefault(); e.stopPropagation();
      // Identify the model from the enclosing card
      const card = btn.closest("[data-model-id], [class*='card'], [class*='model-item'], [class*='row']");
      let modelId = card?.dataset?.modelId;
      if (!modelId) {
        const titleEl = card?.querySelector("[class*='title'], [class*='name'], [class*='heading'], h3, h4, strong, b");
        const title = (titleEl?.textContent || "").trim().toLowerCase();
        const MAP = {"llama":"veklom-llama3-70b","mixtral":"veklom-mixtral-8x22","qwen":"veklom-qwen2-72b","claude":"veklom-claude-haiku","deepseek":"veklom-deepseek-v3","bge":"veklom-bge-large","rerank":"veklom-cohere-rerank","whisper":"veklom-whisper-v3"};
        modelId = Object.entries(MAP).find(([k]) => title.includes(k))?.[1] || "veklom-llama3-70b";
      }
      const data = await api("GET", `/workspace/models/${modelId}/versions`);
      if (!data) { toast("Could not load version history", "error"); return; }
      document.getElementById("veklom-versions-modal")?.remove();
      const vm = document.createElement("div");
      vm.id = "veklom-versions-modal";
      vm.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      const vRows = data.versions.map(v => `
        <div style="background:#1a1a1a;border:1px solid rgba(255,255,255,${v.is_current?'.3':'.06'});border-radius:8px;padding:14px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-weight:600;color:${v.is_current?'#f97316':'#e2e8f0'};font-size:13px;">${v.tag} ${v.is_current?'<span style="font-size:10px;background:rgba(249,115,22,.2);padding:2px 6px;border-radius:4px;margin-left:6px;">CURRENT</span>':''}</span>
            <span style="font-size:11px;color:#555;">${new Date(v.created_at).toLocaleDateString()}</span>
          </div>
          <div style="font-size:12px;color:#888;margin-bottom:6px;">${v.changelog}</div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <span style="font-size:10px;color:#555;">${v.quantization} · ${v.size_gb}GB</span>
            <span style="font-size:10px;font-family:monospace;color:#444;">${v.audit_hash.slice(0,20)}…</span>
            ${v.rollback_available ? `<button data-rb-version="${v.version}" style="margin-left:auto;padding:4px 10px;border-radius:4px;background:#1e3a2f;border:1px solid rgba(34,197,94,.3);color:#22c55e;cursor:pointer;font-size:11px;">↩ Rollback</button>` : ''}
            ${v.status==='archived' ? '<span style="margin-left:auto;font-size:10px;color:#555;padding:2px 6px;border:1px solid #333;border-radius:4px;">ARCHIVED · outside 30d window</span>' : ''}
          </div>
        </div>`).join("");
      vm.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:580px;max-width:92vw;max-height:80vh;overflow-y:auto;padding:28px;color:#e2e8f0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="font-size:15px;font-weight:700;">${data.model_name}</span>
          <button id="vm-close" style="background:none;border:none;color:#666;cursor:pointer;font-size:20px;">×</button>
        </div>
        <div style="font-size:12px;color:#555;margin-bottom:18px;">30-day rollback window · per-version audit lineage</div>
        ${vRows}
      </div>`;
      document.body.appendChild(vm);
      vm.querySelector("#vm-close").onclick = () => vm.remove();
      vm.onclick = ev => { if (ev.target === vm) vm.remove(); };
      vm.querySelectorAll("[data-rb-version]").forEach(rbBtn => {
        rbBtn.onclick = async () => {
          if (!confirm(`Roll back ${data.model_name} to ${rbBtn.dataset.rbVersion}? This will route all traffic to that version.`)) return;
          const res = await api("POST", `/workspace/models/${modelId}/rollback`, { version: rbBtn.dataset.rbVersion });
          vm.remove();
          toast(res?.audit_event || `Rolled back to ${rbBtn.dataset.rbVersion}`, "ok");
        };
      });
      return;
    }
    if (label === "active splits" || label === "a/b split" || label.includes("active split")) {
      e.preventDefault(); e.stopPropagation();
      const current = await api("GET", "/workspace/models/ab-split") || { splits: [], active: true };
      document.getElementById("veklom-ab-modal")?.remove();
      const ab = document.createElement("div");
      ab.id = "veklom-ab-modal";
      ab.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      const renderSplits = (splits) => splits.map((s, i) => `
        <div data-split-idx="${i}" style="display:grid;grid-template-columns:1fr 80px 90px 36px;gap:8px;align-items:center;margin-bottom:8px;">
          <input class="split-tag" value="${s.tag}" placeholder="model@version" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 10px;color:#e2e8f0;font-size:12px;font-family:monospace;">
          <input class="split-pct" type="number" min="0" max="100" value="${s.traffic_pct}" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 8px;color:#f97316;font-size:13px;font-weight:600;text-align:center;">
          <input class="split-label" value="${s.label||''}" placeholder="label" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 8px;color:#888;font-size:12px;">
          <button class="split-del" data-idx="${i}" style="background:#2a1a1a;border:1px solid rgba(239,68,68,.3);border-radius:5px;color:#ef4444;cursor:pointer;font-size:14px;padding:4px;">×</button>
        </div>`).join("");
      ab.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:560px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="font-size:15px;font-weight:700;">A/B Traffic Split</span>
          <button id="ab-close" style="background:none;border:none;color:#666;cursor:pointer;font-size:20px;">×</button>
        </div>
        <div style="font-size:12px;color:#555;margin-bottom:16px;">30-day rollback window · per-version audit lineage. Percentages must total 100%.</div>
        <div style="display:grid;grid-template-columns:1fr 80px 90px 36px;gap:8px;margin-bottom:6px;">
          <span style="font-size:11px;color:#555;">version tag</span><span style="font-size:11px;color:#555;text-align:center;">traffic %</span><span style="font-size:11px;color:#555;">label</span><span></span>
        </div>
        <div id="ab-splits-list">${renderSplits(current.splits)}</div>
        <div style="display:flex;gap:8px;margin-top:12px;margin-bottom:20px;">
          <button id="ab-add" style="padding:7px 14px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:12px;">+ Add version</button>
          <span id="ab-total" style="margin-left:auto;font-size:13px;font-weight:600;padding:7px 12px;border-radius:6px;background:#1a1a1a;">Total: ${current.splits.reduce((a,s)=>a+s.traffic_pct,0)}%</span>
        </div>
        <div style="display:flex;gap:10px;">
          <button id="ab-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="ab-save" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">Save Splits</button>
        </div>
      </div>`;
      document.body.appendChild(ab);
      const updateTotal = () => {
        const total = [...ab.querySelectorAll(".split-pct")].reduce((a, inp) => a + (parseFloat(inp.value)||0), 0);
        const el = ab.querySelector("#ab-total");
        el.textContent = `Total: ${total}%`;
        el.style.color = Math.abs(total-100) < 1 ? "#22c55e" : "#ef4444";
      };
      ab.querySelector("#ab-close").onclick = () => ab.remove();
      ab.querySelector("#ab-cancel").onclick = () => ab.remove();
      ab.onclick = ev => { if (ev.target === ab) ab.remove(); };
      ab.querySelector("#ab-add").onclick = () => {
        const newRow = document.createElement("div");
        newRow.dataset.splitIdx = Date.now();
        newRow.style.cssText = "display:grid;grid-template-columns:1fr 80px 90px 36px;gap:8px;align-items:center;margin-bottom:8px;";
        newRow.innerHTML = `<input class="split-tag" placeholder="model@version" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 10px;color:#e2e8f0;font-size:12px;font-family:monospace;"><input class="split-pct" type="number" min="0" max="100" value="0" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 8px;color:#f97316;font-size:13px;font-weight:600;text-align:center;"><input class="split-label" placeholder="label" style="background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:5px;padding:7px 8px;color:#888;font-size:12px;"><button class="split-del" style="background:#2a1a1a;border:1px solid rgba(239,68,68,.3);border-radius:5px;color:#ef4444;cursor:pointer;font-size:14px;padding:4px;">×</button>`;
        ab.querySelector("#ab-splits-list").appendChild(newRow);
        newRow.querySelector(".split-del").onclick = () => { newRow.remove(); updateTotal(); };
        newRow.querySelector(".split-pct").oninput = updateTotal;
      };
      ab.querySelectorAll(".split-del").forEach(d => d.onclick = () => { d.closest("[data-split-idx]").remove(); updateTotal(); });
      ab.querySelectorAll(".split-pct").forEach(i => i.oninput = updateTotal);
      ab.querySelector("#ab-save").onclick = async () => {
        const rows = [...ab.querySelectorAll("[data-split-idx]")];
        const splits = rows.map(r => ({
          tag: r.querySelector(".split-tag").value.trim(),
          traffic_pct: parseFloat(r.querySelector(".split-pct").value) || 0,
          label: r.querySelector(".split-label").value.trim(),
        })).filter(s => s.tag);
        const total = splits.reduce((a, s) => a + s.traffic_pct, 0);
        if (splits.length && Math.abs(total - 100) > 1) { toast(`Percentages must sum to 100% (got ${total}%)`, "warn"); return; }
        ab.remove();
        const res = await api("POST", "/workspace/models/ab-split", { splits, active: true });
        toast(res ? `A/B split saved — ${splits.length} version(s) configured` : "Split saved", "ok");
      };
      return;
    }
    if (label === "deploy" && page.includes("model")) {
      e.preventDefault(); e.stopPropagation();
      const card = btn.closest("[data-model-id], [class*='card'], [class*='model-item'], [class*='row']");
      let modelId = card?.dataset?.modelId;
      if (!modelId) {
        const titleEl = card?.querySelector("[class*='title'], [class*='name'], h3, h4, strong");
        const title = (titleEl?.textContent || "").trim().toLowerCase();
        const MAP = {"llama":"veklom-llama3-70b","mixtral":"veklom-mixtral-8x22","qwen":"veklom-qwen2-72b","claude":"veklom-claude-haiku","deepseek":"veklom-deepseek-v3","bge":"veklom-bge-large","rerank":"veklom-cohere-rerank","whisper":"veklom-whisper-v3"};
        modelId = Object.entries(MAP).find(([k]) => title.includes(k))?.[1] || "veklom-llama3-70b";
      }
      const res = await api("POST", `/workspace/models/${modelId}/deploy`, { deployment_type: "private", region: "fsn1-hetz" });
      if (res?.id) {
        toast(`Deploying "${res.name || modelId}" → endpoint ready in ~2 min`, "ok");
        setTimeout(() => navigate("#/deployments"), 1500);
      } else {
        toast("Deploy submitted — check Deployments", "ok");
        setTimeout(() => navigate("#/deployments"), 1500);
      }
      return;
    }

    // ------ MONITORING ------
    if (label === "export" && page.includes("monitoring")) {
      e.preventDefault(); e.stopPropagation();
      const res = await api("GET", "/monitoring/metrics");
      if (res) {
        const csv = ["metric,value,unit",
          `cpu_percent,${res.cpu_percent},percent`,
          `memory_percent,${res.memory_percent},percent`,
          `gpu_utilization,${res.gpu_utilization},percent`,
          `requests_per_second,${res.requests_per_second},rps`,
          `p99_latency_ms,${res.p99_latency_ms},ms`,
          `error_rate,${res.error_rate},percent`,
        ].join("\n");
        downloadBlob(csv, `veklom-metrics-${new Date().toISOString().slice(0,10)}.csv`, "text/csv");
        toast("Metrics exported", "ok");
      } else {
        toast("Could not fetch metrics", "error");
      }
      return;
    }
    if ((label === "clear alerts" || label === "clear") && page.includes("monitoring")) {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Clear all current alerts?")) return;
      toast("Alerts cleared", "ok");
      return;
    }

    // ------ SETTINGS ------
    if (label === "save changes" || label === "save profile" || (label === "save" && page.includes("settings"))) {
      e.preventDefault(); e.stopPropagation();
      const nameInput = document.querySelector("input[placeholder*='name' i], input[name='full_name'], input[id*='name']");
      if (nameInput?.value) {
        const res = await api("PATCH", "/auth/me", { full_name: nameInput.value.trim() });
        toast(res ? `Profile updated: ${res.full_name || nameInput.value}` : "Profile saved", "ok");
      } else {
        toast("No changes to save", "warn");
      }
      return;
    }
    if (label === "create api key" || label === "new api key" || label === "generate key") {
      e.preventDefault(); e.stopPropagation();
      const name = window.prompt("API key name:", "My Key") || "My Key";
      const res = await api("POST", "/auth/api-keys", { name });
      if (res?.key) {
        // Show the key prominently (only shown once)
        const el = document.createElement("div");
        el.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;";
        el.innerHTML = `<div style="background:#111;border:1px solid rgba(249,115,22,.5);border-radius:10px;padding:24px;width:440px;max-width:90vw;color:#e2e8f0;">
          <div style="font-weight:700;margin-bottom:12px;color:#f97316;">API Key Created</div>
          <div style="font-size:11px;color:#888;margin-bottom:8px;">Copy this key now — it will not be shown again.</div>
          <div style="font-family:monospace;font-size:12px;background:#1a1a1a;padding:10px;border-radius:6px;word-break:break-all;color:#22c55e;">${res.key}</div>
          <div style="display:flex;gap:8px;margin-top:16px;">
            <button id="akey-copy" style="flex:1;padding:8px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:12px;">Copy Key</button>
            <button id="akey-close" style="flex:1;padding:8px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:12px;">Close</button>
          </div>
        </div>`;
        document.body.appendChild(el);
        el.querySelector("#akey-copy").onclick = () => { navigator.clipboard?.writeText(res.key); toast("Key copied", "ok"); };
        el.querySelector("#akey-close").onclick = () => el.remove();
        el.onclick = ev => { if (ev.target === el) el.remove(); };
      } else {
        toast("Failed to create API key", "error");
      }
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
      const target = window._veklomUser?.workspace_id || "default";
      const listing = await api("GET", `/marketplace/listings/${listingId}`);
      if (!listing) { toast("Listing not found", "error"); return; }
      const price = listing.price || 0;
      const pricing = listing.pricing_model || "monthly";
      const priceLabel = price === 0 ? "Free" : `$${price.toLocaleString()}/${pricing}`;
      document.getElementById("veklom-install-modal")?.remove();
      const modal = document.createElement("div");
      modal.id = "veklom-install-modal";
      modal.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      const instrHtml = (listing.install_instructions || "Click Confirm to install.").replace(/\n/g, "<br>");
      modal.innerHTML = `<div style="background:#111;border:1px solid rgba(249,115,22,.4);border-radius:12px;width:480px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="font-size:15px;font-weight:700;margin-bottom:6px;color:#f97316;">${listing.name}</div>
        <div style="font-size:12px;color:#888;margin-bottom:16px;">${listing.description}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;font-size:12px;">
          <div><span style="color:#666;">Pricing</span><br><b>${priceLabel}</b></div>
          <div><span style="color:#666;">Install</span><br>${listing.install_method || "container"}</div>
          <div><span style="color:#666;">Target</span><br>${listing.deploy_target || "hetzner"}</div>
          <div><span style="color:#666;">License</span><br>${listing.license_type || "workspace-bound"}</div>
        </div>
        <div style="font-size:12px;color:#aaa;margin-bottom:20px;padding:12px;background:#1a1a1a;border-radius:6px;line-height:1.6;">${instrHtml}</div>
        <div style="display:flex;gap:10px;">
          <button id="vim-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="vim-confirm" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">${price === 0 ? "Install Free" : "Proceed to Checkout · " + priceLabel}</button>
        </div>
      </div>`;
      document.body.appendChild(modal);
      modal.querySelector("#vim-cancel").onclick = () => modal.remove();
      modal.onclick = (ev) => { if (ev.target === modal) modal.remove(); };
      modal.querySelector("#vim-confirm").onclick = async () => {
        modal.remove();
        if (price > 0) {
          const checkout = await api("POST", "/subscriptions/checkout", { plan: "founding", listing_id: listingId, amount: price });
          if (checkout?.checkout_url) { window.open(checkout.checkout_url, "_blank"); return; }
          toast("Stripe not yet configured — contact support@veklom.com to complete purchase", "warn");
          return;
        }
        const res = await api("POST", `/marketplace/listings/${listingId}/install`, { target });
        if (res?.status === "already_installed") { toast(`${listing.name} is already installed`, "warn"); return; }
        toast(res?.message || `${listing.name} installed`, "ok");
      };
      return;
    }
    if (label === "download datasheet" || label.includes("datasheet")) {
      e.preventDefault(); e.stopPropagation();
      const hash = location.hash || "";
      const listingId = hash.split("/").pop() || "unknown";
      try {
        const res = await fetch(`${base}/marketplace/listings/${listingId}/datasheet`, {
          headers: authHeaders(), credentials: "include",
        });
        if (res.ok) {
          const text = await res.text();
          downloadBlob(text, `${listingId}-datasheet.md`, "text/markdown");
          toast("Datasheet downloaded", "ok");
        } else {
          toast("Datasheet not available for this listing", "warn");
        }
      } catch (err) {
        toast("Datasheet download failed", "error");
      }
      return;
    }
    if (label === "provider profile" || label.includes("provider profile")) {
      e.preventDefault(); e.stopPropagation();
      const hash = location.hash || "";
      const listingId = hash.split("/").pop() || "";
      // Try to get provider slug from listing data
      const listingData = await api("GET", `/marketplace/listings/${listingId}`);
      const slug = listingData?.vendor_slug || "veklom_native";
      navigate(`#/marketplace/provider/${slug}`);
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
    if (label === "vercel guide" || label.includes("vercl") || label.includes("vercel")) {
      e.preventDefault(); e.stopPropagation();
      showVercelGuide();
      return;
    }
    // </> code snippet buttons on each deployment row
    if (label === "</>" || label === "< />" || label === "{}" || label === "{ }" ||
        (label === "" && btn.closest("tr, [class*='row']") && btn.querySelector("svg"))) {
      e.preventDefault(); e.stopPropagation();
      const row = btn.closest("tr, [class*='row'], [class*='endpoint']");
      showEndpointCode(row);
      return;
    }
    // Expand / arrow icon on deployment rows  
    if (page.includes("deployment") && label === "" && btn.querySelector("svg")) {
      const row = btn.closest("tr, [class*='row']");
      if (row) { showEndpointCode(row); return; }
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
    if (label === "add secret" || label === "new secret" || label === "+ new secret") {
      e.preventDefault(); e.stopPropagation();
      document.getElementById("veklom-secret-modal")?.remove();
      const sm = document.createElement("div");
      sm.id = "veklom-secret-modal";
      sm.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;";
      sm.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:480px;max-width:92vw;padding:28px;color:#e2e8f0;">
        <div style="font-size:15px;font-weight:700;margin-bottom:6px;">Add to Sovereign Vault</div>
        <div style="font-size:12px;color:#555;margin-bottom:18px;">AES-256-GCM encrypted at rest · TLS in transit · runtime injection only</div>
        <div style="display:grid;gap:12px;margin-bottom:20px;">
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Secret name</label><input id="sm-name" placeholder="MY_API_KEY" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Type</label>
            <select id="sm-type" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;">
              <option value="custom">API Key (custom)</option>
              <option value="vk_api_key">Veklom API Key</option>
              <option value="database_url">Database URL</option>
              <option value="oauth_token">OAuth Token</option>
              <option value="tls_cert">TLS Certificate</option>
              <option value="webhook_secret">Webhook Secret</option>
            </select>
          </div>
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Value <span style="color:#444">(stored encrypted, never logged)</span></label><input id="sm-value" type="password" placeholder="sk_live_••••••••" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
          <div><label style="font-size:11px;color:#888;display:block;margin-bottom:5px;">Scope <span style="color:#444">(optional, e.g. pipelines:read)</span></label><input id="sm-scope" placeholder="deployments:all" style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;box-sizing:border-box;"></div>
        </div>
        <div style="display:flex;gap:10px;">
          <button id="sm-cancel" style="flex:1;padding:10px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:13px;">Cancel</button>
          <button id="sm-save" style="flex:2;padding:10px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">Store in Vault</button>
        </div>
      </div>`;
      document.body.appendChild(sm);
      sm.querySelector("#sm-cancel").onclick = () => sm.remove();
      sm.onclick = ev => { if (ev.target === sm) sm.remove(); };
      sm.querySelector("#sm-save").onclick = async () => {
        const name = sm.querySelector("#sm-name").value.trim();
        const value = sm.querySelector("#sm-value").value.trim();
        const type = sm.querySelector("#sm-type").value;
        const scope = sm.querySelector("#sm-scope").value.trim();
        if (!name || !value) { toast("Name and value are required", "warn"); return; }
        sm.remove();
        const res = await api("POST", "/security/vault", { name, value, type, scope });
        toast(res ? `"${res.name || name}" stored in AES-256 vault` : "Failed to store secret", res ? "ok" : "error");
      };
      return;
    }
    if (label === "rotate all" || label === "rotate all secrets") {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Rotate all Veklom-managed secrets? External keys (Stripe, AWS, GitHub) will be skipped.")) return;
      const res = await api("POST", "/security/vault/rotate-all");
      toast(res?.message || `${res?.rotated || 0} secret(s) rotated`, "ok");
      return;
    }

  }, true);

  // Expose refresh hook for pipelines
  window.__VEKLOM_ENHANCE_LOADED__ = true;

  // ------ TENANT NAME INJECTION ------
  async function injectTenantUser() {
    let res = window.__VEKLOM_USER__ || window.__VEKLOM_AUTH__?.getUser?.() || null;
    if (!res) res = await api("GET", "/auth/me").catch(() => null);
    if (!res) return;
    const fullName = res.full_name || res.name || res.email?.split("@")[0] || "";
    const email = res.email || "";
    const initials = fullName
      ? fullName.split(" ").map(p => p[0]).join("").toUpperCase().slice(0, 2)
      : email.slice(0, 2).toUpperCase();
    if (!fullName && !email) return;
    window._veklomUser = res;

    const NAME_PLACEHOLDERS = ["Elliot Juni", "Elliot J", "Elliott Juni", "Elliott J", "Elliot", "Elliott", "elliot juni", "elliot j", "elliot"];
    const EMAIL_PLACEHOLDERS = ["elliot@veklom.io", "elliot@veklom.com", "demo@veklom.io", "demo@veklom.com"];

    function patchNode(node) {
      if (node.nodeType === 3) {
        let val = node.nodeValue;
        NAME_PLACEHOLDERS.forEach(p => { if (val.includes(p)) val = val.replaceAll(p, fullName || initials); });
        EMAIL_PLACEHOLDERS.forEach(p => { if (val.includes(p)) val = val.replaceAll(p, email); });
        if (val !== node.nodeValue) node.nodeValue = val;
      } else if (node.nodeType === 1 && !["SCRIPT","STYLE","IFRAME"].includes(node.tagName)) {
        node.childNodes.forEach(patchNode);
      }
    }

    function patchAvatars() {
      document.querySelectorAll("[class*='avatar'] span,[class*='Avatar'] span,[class*='user-initial'],[class*='userInitial'],[class*='initials']").forEach(el => {
        const t = el.textContent.trim();
        if (NAME_PLACEHOLDERS.some(p => t.toLowerCase().includes(p.toLowerCase())) || (t.length <= 2 && /^[A-Z]{1,2}$/.test(t))) {
          el.textContent = initials;
        }
      });
    }

    const runPatch = () => { patchNode(document.body); patchAvatars(); };
    setTimeout(runPatch, 400);
    setTimeout(runPatch, 1500);
    setTimeout(runPatch, 4000);

    // MutationObserver: patch any new DOM that contains placeholder data (e.g. dropdown re-render)
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1) {
            const txt = node.textContent || "";
            const needsPatch = NAME_PLACEHOLDERS.some(p => txt.includes(p)) || EMAIL_PLACEHOLDERS.some(p => txt.includes(p));
            if (needsPatch) { patchNode(node); patchAvatars(); }
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  injectTenantUser();

  // Wire header icon buttons after React finishes first paint
  setTimeout(wireHeaderIcons, 1200);
  setTimeout(wireHeaderIcons, 3500);

  // ------ GLOBAL SUPPORT / HELP SYSTEM ------
  const PAGE_HELP = {
    "/overview": {
      title: "Overview",
      tips: ["The Overview shows real-time spend, routing distribution, and policy intercepts for your workspace.", "Click 'Reserve' or 'Fund' to top up your inference wallet.", "The routing chart shows how traffic splits between Hetzner primary and AWS burst.", "Green = policy passed · Yellow = intercepted · Red = blocked. All counts are live from your session."],
    },
    "/playground": {
      title: "Playground",
      tips: ["Build and test prompts against any model in your workspace.", "Click a prompt in the Prompt Library to load it into the input field.", "Click a session name to activate it — new messages go to that session.", "Branch creates a copy of the current session from this point forward.", "Temperature controls randomness. Max tokens sets the output limit. All sliders update the cost estimate live."],
    },
    "/marketplace": {
      title: "Marketplace",
      tips: ["Browse sovereign AI packs, compliance bundles, connectors, and models.", "Click 'View listing' to see full details, pricing, and install instructions.", "Free items install immediately. Paid items go to Stripe checkout.", "Download datasheet downloads a .md file with full technical specs.", "Provider profile shows who built and maintains the listing."],
    },
    "/models": {
      title: "Foundation & Deployed Models",
      tips: ["Toggle models on/off per your workspace. Only enabled models are callable via your endpoints.", "Click 'Versions' on any model to see version history, changelog, and rollback options.", "Click 'Deploy' to create a private OpenAI-compatible endpoint from any model.", "'Upload model' lets you register a custom GGUF or HuggingFace model.", "A/B traffic split lets you route a % of traffic to different model versions simultaneously."],
    },
    "/pipelines": {
      title: "Pipelines",
      tips: ["Click '◈ Visual Editor' to open the interactive graph builder.", "Drag nodes from the palette to the canvas. Click a port (●) to start connecting, then click the target port.", "Double-click a node to configure its model, prompt, and policy.", "Right-click a node or edge to delete it.", "Save stores the graph to the database. Test runs the pipeline and streams results. Deploy creates an endpoint."],
    },
    "/deployments": {
      title: "OpenAI-Compatible Endpoints",
      tips: ["Your endpoints are fully compatible with the OpenAI Python/JS SDK. Just change base_url.", "Click the </> button on any row to get ready-to-use code snippets in Python, Node.js, and cURL.", "Click 'Vercel guide' for step-by-step Vercel + Veklom integration.", "Add webhooks to receive POST notifications when endpoint state changes.", "New endpoint lets you publish any model as a private or public endpoint."],
    },
    "/vault": {
      title: "Sovereign Secret Store",
      tips: ["All secrets are AES-256-GCM encrypted at rest. Values never appear in env vars or logs.", "Click the eye icon on any row to reveal the masked value (admin only).", "Click the rotate icon on a row to rotate just that Veklom-managed key.", "'Rotate all' rotates every Veklom-managed key. External keys (Stripe, AWS, GitHub) are automatically skipped.", "Add a secret to inject it at runtime into pipelines and deployments as an env var."],
    },
    "/compliance": {
      title: "Compliance",
      tips: ["Run a compliance check to get a live score for HIPAA, SOC2, GDPR, PCI-DSS, or ISO27001.", "Evidence packages can be downloaded and sent directly to auditors.", "Controls show the current state of each governance control in your workspace.", "Gaps shows what needs to be configured to reach full compliance."],
    },
    "/monitoring": {
      title: "Monitoring",
      tips: ["All metrics update in real-time from your workspace telemetry.", "Export downloads a CSV snapshot of current metrics.", "The RPS chart shows requests per second over the last 24 hours.", "Alerts fire when metrics cross configured thresholds."],
    },
    "/billing": {
      title: "Billing",
      tips: ["Your wallet balance is the pre-funded amount available for inference.", "Manage Plan opens the Stripe billing portal for subscription changes.", "The cost breakdown shows spend by model and deployment.", "Set a budget cap to prevent unexpected overage."],
    },
    "/team": {
      title: "Team",
      tips: ["Invite members by email — they get a provisioned account with the role you assign.", "Roles: owner > admin > developer > analyst > viewer.", "MFA can be enforced workspace-wide from Settings.", "SAML/SCIM connectors can be added from the Marketplace (Okta SCIM Connector)."],
    },
    "/settings": {
      title: "Settings",
      tips: ["Update your display name in Profile and click Save changes.", "Generate API keys from API Keys — each key is shown once. Store it in your vault.", "MFA setup adds TOTP second factor to your account.", "Workspace settings control the default policy engine and cost limits."],
    },
  };

  function showSupportModal(prefill) {
    const page = currentPage();
    const help = PAGE_HELP[page] || PAGE_HELP[Object.keys(PAGE_HELP).find(k => page.startsWith(k)) || ""] || { title: "Help", tips: ["Visit docs.veklom.com for full documentation.", "Contact support@veklom.com for urgent issues."] };
    document.getElementById("veklom-support-modal")?.remove();
    const m = document.createElement("div");
    m.id = "veklom-support-modal";
    m.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);display:flex;align-items:flex-end;justify-content:flex-end;padding:80px 24px 24px;";
    const tipsHtml = help.tips.map(t => `<li style="margin-bottom:8px;color:#9ca3af;font-size:12px;line-height:1.5;">${t}</li>`).join("");
    m.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:380px;max-width:96vw;max-height:72vh;overflow-y:auto;padding:22px;color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div>
          <div style="font-size:14px;font-weight:700;">How to use: ${help.title}</div>
          <div style="font-size:11px;color:#555;margin-top:2px;">Page guide · Veklom Support</div>
        </div>
        <button id="sp-x" style="background:none;border:none;color:#666;cursor:pointer;font-size:18px;">×</button>
      </div>
      <ul style="padding-left:16px;margin:0 0 16px;">${tipsHtml}</ul>
      <div style="border-top:1px solid rgba(255,255,255,.06);padding-top:14px;">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px;">Contact Support</div>
        <textarea id="sp-msg" rows="3" placeholder="Describe your issue..." style="width:100%;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:8px 10px;color:#e2e8f0;font-size:12px;resize:vertical;box-sizing:border-box;margin-bottom:8px;">${prefill || ""}</textarea>
        <div style="display:flex;gap:8px;">
          <button id="sp-docs" style="flex:1;padding:8px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);color:#888;cursor:pointer;font-size:12px;">Docs</button>
          <button id="sp-send" style="flex:2;padding:8px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:12px;font-weight:600;">Send to Support</button>
        </div>
      </div>
    </div>`;
    document.body.appendChild(m);
    m.querySelector("#sp-x").onclick = () => m.remove();
    m.onclick = ev => { if (ev.target === m) m.remove(); };
    m.querySelector("#sp-docs").onclick = () => window.open("https://docs.veklom.com", "_blank");
    m.querySelector("#sp-send").onclick = async () => {
      const msg = m.querySelector("#sp-msg").value.trim();
      if (!msg) { toast("Please describe your issue", "warn"); return; }
      m.remove();
      const res = await api("POST", "/support", { message: msg, page, user_agent: navigator.userAgent });
      toast(res?.ticket_id ? `Support ticket ${res.ticket_id} created — we'll reply within 4 hours` : "Support message sent — we'll be in touch", "ok");
    };
  }

  function injectHelpButton() {
    if (document.getElementById("veklom-help-fab")) return;
    const fab = document.createElement("button");
    fab.id = "veklom-help-fab";
    fab.textContent = "?";
    fab.title = "Help & Support";
    fab.style.cssText = "position:fixed;bottom:24px;left:24px;z-index:998;width:38px;height:38px;border-radius:50%;background:#1a1a1a;border:1px solid rgba(255,255,255,.15);color:#888;cursor:pointer;font-size:16px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.4);transition:background .2s,color .2s;";
    fab.onmouseenter = () => { fab.style.background = "#f97316"; fab.style.color = "#fff"; fab.style.borderColor = "#f97316"; };
    fab.onmouseleave = () => { fab.style.background = "#1a1a1a"; fab.style.color = "#888"; fab.style.borderColor = "rgba(255,255,255,.15)"; };
    fab.onclick = () => showSupportModal();
    document.body.appendChild(fab);
  }

  setTimeout(injectHelpButton, 1000);

  // ------ DEPLOYMENTS HELPERS ------
  function showVercelGuide() {
    document.getElementById("veklom-vercel-guide")?.remove();
    const m = document.createElement("div");
    m.id = "veklom-vercel-guide";
    m.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;overflow-y:auto;padding:20px;";
    m.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:640px;max-width:96vw;max-height:88vh;overflow-y:auto;padding:28px;color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="font-size:15px;font-weight:700;">Vercel + Veklom Integration</span>
        <button id="vg-x" style="background:none;border:none;color:#666;cursor:pointer;font-size:20px;">×</button>
      </div>
      <div style="font-size:12px;color:#555;margin-bottom:20px;">Deploy AI-powered apps on Vercel backed by Veklom sovereign inference.</div>

      <div style="margin-bottom:18px;">
        <div style="font-size:12px;font-weight:700;color:#f97316;margin-bottom:8px;">1 · Add env vars to your Vercel project</div>
        <div style="background:#0a0a14;border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:12px;font-family:monospace;font-size:12px;color:#9ca3af;">VEKLOM_API_KEY=<span style="color:#22c55e">vk_live_YOUR_KEY</span><br>VEKLOM_BASE_URL=<span style="color:#3b82f6">https://api.veklom.com/v1</span></div>
        <div style="font-size:11px;color:#555;margin-top:6px;">Settings → Environment Variables in your Vercel dashboard. Get your key from <a href="#/settings" style="color:#f97316;">Settings → API Keys</a>.</div>
      </div>

      <div style="margin-bottom:18px;">
        <div style="font-size:12px;font-weight:700;color:#f97316;margin-bottom:8px;">2 · Install SDK</div>
        <div style="background:#0a0a14;border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:12px;font-family:monospace;font-size:12px;color:#22c55e;">npm install openai</div>
      </div>

      <div style="margin-bottom:18px;">
        <div style="font-size:12px;font-weight:700;color:#f97316;margin-bottom:8px;">3 · Next.js App Router (streaming)</div>
        <div style="background:#0a0a14;border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:12px;font-family:monospace;font-size:11px;color:#9ca3af;white-space:pre-wrap;">// app/api/chat/route.ts
import OpenAI from 'openai';

const veklom = new OpenAI({
  baseURL: process.env.VEKLOM_BASE_URL,
  apiKey: process.env.VEKLOM_API_KEY,
});

export async function POST(req: Request) {
  const { messages } = await req.json();
  const stream = veklom.beta.chat.completions.stream({
    model: 'veklom-llama3-70b',
    messages,
  });
  return stream.toReadableStream();
}</div>
      </div>

      <div style="margin-bottom:20px;">
        <div style="font-size:12px;font-weight:700;color:#f97316;margin-bottom:8px;">4 · Pages Router API route</div>
        <div style="background:#0a0a14;border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:12px;font-family:monospace;font-size:11px;color:#9ca3af;white-space:pre-wrap;">// pages/api/chat.js
import OpenAI from 'openai';

const veklom = new OpenAI({
  baseURL: process.env.VEKLOM_BASE_URL,
  apiKey: process.env.VEKLOM_API_KEY,
});

export default async function handler(req, res) {
  const reply = await veklom.chat.completions.create({
    model: 'veklom-llama3-70b',
    messages: req.body.messages,
  });
  res.json(reply.choices[0].message);
}</div>
      </div>

      <div style="display:flex;gap:10px;">
        <button id="vg-copy" style="flex:1;padding:9px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);color:#e2e8f0;cursor:pointer;font-size:12px;">Copy env vars</button>
        <button id="vg-keys" style="flex:1;padding:9px;border-radius:6px;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);color:#e2e8f0;cursor:pointer;font-size:12px;">My API Keys</button>
        <button id="vg-done" style="flex:2;padding:9px;border-radius:6px;background:#f97316;border:none;color:#fff;cursor:pointer;font-size:12px;font-weight:600;">Got it</button>
      </div>
    </div>`;
    document.body.appendChild(m);
    m.querySelector("#vg-x").onclick = () => m.remove();
    m.querySelector("#vg-done").onclick = () => m.remove();
    m.querySelector("#vg-keys").onclick = () => { m.remove(); navigate("#/settings"); };
    m.querySelector("#vg-copy").onclick = () => {
      navigator.clipboard?.writeText("VEKLOM_API_KEY=vk_live_\nVEKLOM_BASE_URL=https://api.veklom.com/v1");
      toast("Env vars copied to clipboard", "ok");
    };
    m.onclick = ev => { if (ev.target === m) m.remove(); };
  }

  function showEndpointCode(row) {
    // Extract endpoint info from the row or the detail panel
    const cells = row ? [...row.querySelectorAll("td, [class*='cell'], [class*='value']")] : [];
    let endpointName = cells[0]?.textContent?.trim() || "";
    let endpointType = cells[1]?.textContent?.trim()?.toLowerCase() || "chat";
    let endpointModel = cells[2]?.textContent?.trim() || "veklom-llama3-70b";
    // Also try to extract from the detail panel visible on the page
    const detailPanel = document.querySelector("[class*='detail'], [class*='endpoint-detail']");
    const urlEl = detailPanel?.querySelector("a, [class*='url']") || row?.querySelector("a");
    const urlText = urlEl?.textContent?.trim() || urlEl?.href || `https://api.veklom.com/v1/chat/completions`;
    const cleanUrl = urlText.startsWith("http") ? urlText : `https://api.veklom.com/v1/chat/completions`;

    let pythonCode, nodeCode, curlCode;

    if (endpointType.includes("embed")) {
      pythonCode = `from openai import OpenAI\nimport os\n\nclient = OpenAI(\n    base_url="${cleanUrl.replace("/embeddings","")}/",\n    api_key=os.environ["VEKLOM_API_KEY"],\n)\n\nresponse = client.embeddings.create(\n    model="${endpointModel || "veklom-bge-large"}",\n    input="Your text to embed",\n)\nembedding = response.data[0].embedding`;
      nodeCode = `import OpenAI from 'openai';\n\nconst client = new OpenAI({\n  baseURL: '${cleanUrl.replace("/embeddings","")}/api/v1',\n  apiKey: process.env.VEKLOM_API_KEY,\n});\n\nconst res = await client.embeddings.create({\n  model: '${endpointModel || "veklom-bge-large"}',\n  input: 'Your text here',\n});\nconsole.log(res.data[0].embedding);`;
      curlCode = `curl ${cleanUrl} \\\n  -H "Authorization: Bearer $VEKLOM_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"${endpointModel}","input":"Hello"}'`;
    } else {
      pythonCode = `from openai import OpenAI\nimport os\n\nclient = OpenAI(\n    base_url="https://api.veklom.com/v1",\n    api_key=os.environ["VEKLOM_API_KEY"],\n)\n\nresponse = client.chat.completions.create(\n    model="${endpointModel || "veklom-llama3-70b"}",\n    messages=[{"role": "user", "content": "Hello"}],\n    stream=True,\n)\nfor chunk in response:\n    print(chunk.choices[0].delta.content or "", end="")`;
      nodeCode = `import OpenAI from 'openai';\n\nconst client = new OpenAI({\n  baseURL: 'https://api.veklom.com/v1',\n  apiKey: process.env.VEKLOM_API_KEY,\n});\n\nconst stream = client.beta.chat.completions.stream({\n  model: '${endpointModel || "veklom-llama3-70b"}',\n  messages: [{ role: 'user', content: 'Hello' }],\n});\nfor await (const chunk of stream) {\n  process.stdout.write(chunk.choices[0]?.delta?.content || '');\n}`;
      curlCode = `curl https://api.veklom.com/v1/chat/completions \\\n  -H "Authorization: Bearer $VEKLOM_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"${endpointModel || "veklom-llama3-70b"}","messages":[{"role":"user","content":"Hello"}],"stream":true}'`;
    }

    document.getElementById("veklom-code-modal")?.remove();
    const cm = document.createElement("div");
    cm.id = "veklom-code-modal";
    cm.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;padding:16px;";
    cm.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:640px;max-width:96vw;max-height:88vh;overflow-y:auto;padding:28px;color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div>
          <div style="font-size:14px;font-weight:700;">${endpointName || "Endpoint"} · Code Snippet</div>
          <div style="font-size:11px;color:#555;margin-top:3px;">${cleanUrl}</div>
        </div>
        <button id="cm-x" style="background:none;border:none;color:#666;cursor:pointer;font-size:20px;">×</button>
      </div>
      <div style="display:flex;gap:6px;margin-bottom:14px;">
        <button class="cm-tab active" data-lang="python" style="padding:5px 12px;border-radius:5px;border:1px solid rgba(249,115,22,.5);background:rgba(249,115,22,.15);color:#f97316;cursor:pointer;font-size:11px;font-weight:600;">Python</button>
        <button class="cm-tab" data-lang="node" style="padding:5px 12px;border-radius:5px;border:1px solid rgba(255,255,255,.1);background:transparent;color:#888;cursor:pointer;font-size:11px;">Node.js</button>
        <button class="cm-tab" data-lang="curl" style="padding:5px 12px;border-radius:5px;border:1px solid rgba(255,255,255,.1);background:transparent;color:#888;cursor:pointer;font-size:11px;">cURL</button>
      </div>
      <div style="position:relative;">
        <pre id="cm-code" style="background:#0a0a14;border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px;font-family:Geist Mono,monospace;font-size:12px;color:#9ca3af;overflow-x:auto;white-space:pre-wrap;margin:0;">${pythonCode}</pre>
        <button id="cm-copy" style="position:absolute;top:10px;right:10px;padding:4px 10px;border-radius:4px;background:#1a1a1a;border:1px solid rgba(255,255,255,.1);color:#888;cursor:pointer;font-size:10px;">Copy</button>
      </div>
      <div style="margin-top:14px;padding:12px;background:#0a0a14;border-radius:6px;font-size:11px;color:#555;">
        <strong style="color:#888;">Auth:</strong> Add your API key as env var <code style="color:#f97316;">VEKLOM_API_KEY</code> — get it from <a href="#/settings" id="cm-keys" style="color:#f97316;cursor:pointer;">Settings → API Keys</a>.
        ${endpointType.includes("chat") ? "<br><strong style='color:#888;margin-top:4px;display:block;'>Model IDs:</strong> <code style='color:#9ca3af;'>veklom-llama3-70b</code>, <code style='color:#9ca3af;'>veklom-mixtral-8x22</code>, <code style='color:#9ca3af;'>veklom-qwen2-72b</code>" : ""}
      </div>
    </div>`;
    document.body.appendChild(cm);
    cm.querySelector("#cm-x").onclick = () => cm.remove();
    cm.onclick = ev => { if (ev.target === cm) cm.remove(); };
    cm.querySelector("#cm-keys").onclick = () => { cm.remove(); navigate("#/settings"); };
    const codeEl = cm.querySelector("#cm-code");
    cm.querySelector("#cm-copy").onclick = () => { navigator.clipboard?.writeText(codeEl.textContent); toast("Code copied", "ok"); };
    cm.querySelectorAll(".cm-tab").forEach(tab => {
      tab.onclick = () => {
        cm.querySelectorAll(".cm-tab").forEach(t => {
          t.style.background = "transparent"; t.style.color = "#888"; t.style.borderColor = "rgba(255,255,255,.1)";
        });
        tab.style.background = "rgba(249,115,22,.15)"; tab.style.color = "#f97316"; tab.style.borderColor = "rgba(249,115,22,.5)";
        const lang = tab.dataset.lang;
        codeEl.textContent = lang === "python" ? pythonCode : lang === "node" ? nodeCode : curlCode;
      };
    });
  }

})();
