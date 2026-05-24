/* Veklom Sovereign AI Hub — Frontend JS */
(function () {
  "use strict";

  const API = "/api/v1";

  // --- Platform Pulse (refresh every 60s) ---
  async function fetchPulse() {
    try {
      const res = await fetch(`${API}/platform/pulse`);
      const d = await res.json();
      setText("pulse-users", d.total_users);
      setText("pulse-listings", d.active_listings);
      setText("pulse-installs", d.tool_installs);
      setText("pulse-gpc", d.gpc_compiles_total);
      setText("pulse-users-delta", d.user_growth_pct_30d >= 0 ? `+${d.user_growth_pct_30d}% (30d)` : `${d.user_growth_pct_30d}% (30d)`);
      setText("pulse-listings-delta", `+${d.new_listings_7d} (7d)`);
      setText("pulse-tools-delta", `${d.active_tools} active tools`);
    } catch (e) {
      console.warn("Pulse fetch failed:", e);
    }
  }

  // --- Uptime Monitor ---
  async function fetchUptime() {
    try {
      const res = await fetch(`${API}/platform/uptime`);
      const d = await res.json();
      renderUptimePreview(d);
      renderStatusPage(d);
    } catch (e) {
      console.warn("Uptime fetch failed:", e);
    }
  }

  function renderUptimePreview(data) {
    const container = document.getElementById("uptime-dashboard");
    if (!container) return;

    setText("uptime-overall-title", data.headline || "All governed runtime systems operational");
    setText("uptime-overall-copy", `${data.services?.length || 0} runtime boundaries reporting. Last sync ${formatTime(data.updated_at)}.`);
    setText("uptime-percent", `${formatPercent(data.uptime_percent)}%`);
    setText("uptime-latency", `${data.avg_response_time_ms || 0}ms`);
    setText("uptime-incidents", data.active_incidents ?? 0);

    container.innerHTML = (data.services || [])
      .slice(0, 6)
      .map((service) => serviceSymbol(service, "compact"))
      .join("");

    renderLedger("uptime-ledger", data.history || []);
  }

  function renderStatusPage(data) {
    const services = document.getElementById("status-page-services");
    if (!services) return;

    setText("status-page-headline", data.headline || "All governed runtime systems operational");
    setText("status-page-uptime", `${formatPercent(data.uptime_percent)}%`);
    setText("status-page-latency", `${data.avg_response_time_ms || 0}ms`);
    setText("status-page-checks", Number(data.checks_passed_24h || 0).toLocaleString());
    setText("status-page-incidents", data.active_incidents ?? 0);
    setText("status-page-updated", `Last verified ${formatTime(data.updated_at)} · ${data.window_days || 90}-day evidence window`);

    services.innerHTML = (data.services || [])
      .map((service) => serviceSymbol(service, "full"))
      .join("");

    renderLedger("status-page-ledger", data.history || []);
    renderIncidents(data.incidents || []);
  }

  function serviceSymbol(service, mode) {
    const status = normalizeStatus(service.status);
    const label = status === "up" ? "Operational" : status === "degraded" ? "Degraded" : "Incident";
    const icon = statusIcon(service.symbol || "vmark");

    if (mode === "compact") {
      return `
        <a class="status-symbol-tile status-${status}" href="/uptime" aria-label="${escapeHtml(service.service)} ${label}">
          <span class="status-icon-wrap">${icon}</span>
          <span>${escapeHtml(shortServiceName(service.service))}</span>
        </a>
      `;
    }

    return `
      <article class="status-service-card status-${status}">
        <div class="status-service-icon">${icon}</div>
        <div class="status-service-body">
          <div class="status-service-topline">
            <span>${escapeHtml(service.region || "Runtime")}</span>
            <strong>${label}</strong>
          </div>
          <h3>${escapeHtml(service.service)}</h3>
          <p>${escapeHtml(service.description || "Operational boundary is reporting normally.")}</p>
          <div class="status-service-meta">
            <span>${service.response_time_ms || 0}ms response</span>
            <span>${formatPercent(service.uptime_90d)}% 90d</span>
          </div>
        </div>
      </article>
    `;
  }

  function renderLedger(id, history) {
    const container = document.getElementById(id);
    if (!container) return;
    container.innerHTML = history
      .map((entry) => {
        const status = normalizeStatus(entry.status);
        return `<span class="status-ledger-mark status-${status}" title="${escapeHtml(entry.day)} · ${statusLabel(status)}" aria-label="${escapeHtml(entry.day)} ${statusLabel(status)}"></span>`;
      })
      .join("");
  }

  function renderIncidents(incidents) {
    const container = document.getElementById("status-page-incidents-list");
    if (!container) return;
    container.innerHTML = incidents
      .map((incident) => `
        <article class="status-incident">
          <div>
            <span class="status-incident-date">${escapeHtml(incident.date)}</span>
            <h3>${escapeHtml(incident.title)}</h3>
            <p>${escapeHtml(incident.impact)}</p>
          </div>
          <span class="status-incident-pill status-${normalizeStatus(incident.status === "resolved" || incident.status === "informational" ? "up" : incident.status)}">${escapeHtml(incident.status)}</span>
        </article>
      `)
      .join("");
  }

  function statusIcon(symbol) {
    const common = 'viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"';
    const stroke = 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
    const icons = {
      shield: `<svg ${common}><path ${stroke} d="M16 4 26 8v7c0 6.2-3.8 10.4-10 13-6.2-2.6-10-6.8-10-13V8l10-4Z"/><path ${stroke} d="m12 16 3 3 6-7"/></svg>`,
      lock: `<svg ${common}><rect ${stroke} x="7" y="14" width="18" height="12" rx="2"/><path ${stroke} d="M11 14v-3a5 5 0 0 1 10 0v3"/><path ${stroke} d="M16 19v3"/></svg>`,
      lens: `<svg ${common}><circle ${stroke} cx="14" cy="14" r="8"/><path ${stroke} d="m20 20 6 6"/><path ${stroke} d="M14 10v8M10 14h8"/></svg>`,
      stack: `<svg ${common}><path ${stroke} d="m16 5 11 6-11 6-11-6 11-6Z"/><path ${stroke} d="m5 16 11 6 11-6"/><path ${stroke} d="m5 21 11 6 11-6"/></svg>`,
      globe: `<svg ${common}><circle ${stroke} cx="16" cy="16" r="11"/><path ${stroke} d="M5 16h22M16 5c3 3 4.5 6.7 4.5 11S19 24 16 27c-3-3-4.5-6.7-4.5-11S13 8 16 5Z"/></svg>`,
      vmark: `<svg ${common}><path ${stroke} d="m7 7 9 19L25 7"/><circle fill="currentColor" cx="16" cy="16" r="2.2"/></svg>`,
    };
    return icons[symbol] || icons.vmark;
  }

  function normalizeStatus(status) {
    const value = String(status || "").toLowerCase();
    if (value === "up" || value === "operational" || value === "resolved" || value === "informational") return "up";
    if (value === "degraded" || value === "warning") return "degraded";
    return "down";
  }

  function statusLabel(status) {
    return status === "up" ? "operational" : status === "degraded" ? "degraded" : "incident";
  }

  function shortServiceName(name) {
    return String(name || "")
      .replace("Governed Compiler (GPC)", "GPC")
      .replace("API Gateway", "API")
      .replace("Compliance Auditor", "Auditor")
      .replace("Autonomous Router", "Router")
      .replace("Playground Engine", "Playground");
  }

  function formatPercent(value) {
    const n = Number(value || 0);
    return n % 1 === 0 ? n.toFixed(0) : n.toFixed(2);
  }

  function formatTime(value) {
    if (!value) return "just now";
    try {
      return new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return "just now";
    }
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]));
  }

  // --- Premium Toast Notification ---
  function showToast(message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 12px;
        pointer-events: none;
      `;
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.style.cssText = `
      background: #0A0A0A;
      color: #FFFFFF;
      border: 1px solid ${type === "success" ? "#FFB800" : "#EF4444"};
      padding: 14px 18px;
      border-radius: 8px;
      font-family: 'Inter', sans-serif;
      font-size: 0.85rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.8), 0 0 10px rgba(255, 184, 0, 0.1);
      min-width: 300px;
      max-width: 420px;
      display: flex;
      align-items: center;
      gap: 10px;
      pointer-events: auto;
      transform: translateY(20px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    const icon = document.createElement("span");
    icon.innerHTML = type === "success" ? "⚡" : "⚠";
    icon.style.color = type === "success" ? "#FFB800" : "#EF4444";
    icon.style.fontSize = "1rem";

    const text = document.createElement("span");
    text.textContent = message;

    toast.appendChild(icon);
    toast.appendChild(text);
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transform = "translateY(0)";
      toast.style.opacity = "1";
    }, 10);

    setTimeout(() => {
      toast.style.transform = "translateY(-20px)";
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // --- Feedback Form ---
  function initFeedbackForm() {
    const form = document.getElementById("feedback-form");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const cat = document.getElementById("fb-category").value;
      const subj = document.getElementById("fb-subject").value;
      const body = document.getElementById("fb-body").value;
      if (!subj || !body) {
        showToast("Please fill in both subject and description", "error");
        return;
      }
      try {
        const res = await fetch(
          `${API}/feedback/?category=${encodeURIComponent(cat)}&subject=${encodeURIComponent(subj)}&body=${encodeURIComponent(body)}`,
          { method: "POST" }
        );
        const d = await res.json();
        showToast(d.message || "Feedback submitted successfully!");
        form.reset();
      } catch (err) {
        console.error("Feedback submit failed:", err);
        showToast("Failed to submit feedback. Please try again.", "error");
      }
    });
  }

  // --- Helpers ---
  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  // --- Init ---
  document.addEventListener("DOMContentLoaded", () => {
    fetchPulse();
    fetchUptime();
    initFeedbackForm();
    setInterval(fetchPulse, 60000);
    setInterval(fetchUptime, 60000);
  });
})();
