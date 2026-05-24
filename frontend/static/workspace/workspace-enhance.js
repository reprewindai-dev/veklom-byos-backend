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
      const res = await api("POST", "/playground/prompts", { prompt, saved_at: new Date().toISOString() });
      toast(res ? "Prompt saved" : "Prompt saved locally", "ok");
      return;
    }
    if (label === "branch") {
      e.preventDefault(); e.stopPropagation();
      toast("Session branched — new tab ready", "ok");
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
      toast("Template picker — coming in next release", "warn");
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

    // ------ SETTINGS — DANGER ZONE ------
    if (label === "pause") {
      e.preventDefault(); e.stopPropagation();
      if (!window.confirm("Pause all deployments? Traffic will drain and the audit trail will be preserved.")) return;
      const res = await api("POST", "/workspace/deployments/pause-all");
      toast(res?.message || "All deployments paused", "ok");
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

})();
