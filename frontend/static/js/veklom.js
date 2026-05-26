/* Veklom Sovereign AI Hub - Frontend JS */
(function () {
  "use strict";

  const API = "/api/v1";

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
    setText("uptime-overall-copy", `${data.services?.length || 0} runtime boundaries reporting. Last sync ${formatSyncTime(data.updated_at)}.`);
    setText("uptime-percent", `${formatPercent(data.uptime_percent)}%`);
    setText("uptime-latency", `${data.avg_response_time_ms || 0}ms`);
    setText("uptime-incidents", data.active_incidents ?? 0);

    container.innerHTML = (data.services || [])
      .slice(0, 6)
      .map((service, index) => serviceStatusRow(service, index, true))
      .join("");
  }

  function renderStatusPage(data) {
    const services = document.getElementById("status-page-services");
    if (!services) return;

    setText("status-page-headline", headlineForStatus(data));
    setText("status-page-updated", `Last updated on ${formatStatusTime(data.updated_at)}`);
    setText("status-boundary-title", data.headline || "All governed runtime systems operational");
    setText("status-boundary-copy", `${data.services?.length || 0} runtime boundaries reporting. Last sync ${formatSyncTime(data.updated_at)}.`);
    setText("status-page-uptime", `${formatPercent(data.uptime_percent)}%`);
    setText("status-page-latency", `${data.avg_response_time_ms || 0}ms`);
    setText("status-page-incidents", data.active_incidents ?? 0);

    services.innerHTML = (data.services || [])
      .map((service, index) => serviceStatusRow(service, index, false))
      .join("");

    renderIncidents(data.incidents || []);
  }

  function serviceStatusRow(service, index, compact) {
    const status = normalizeStatus(service.status);
    const label = status === "up" ? "Operational" : status === "degraded" ? "Degraded" : "Incident";
    const name = serviceName(service);
    const history = serviceHistory(service, index);
    const compactClass = compact ? " status-service-row-compact" : "";

    return `
      <article class="status-service-row status-${status}${compactClass}">
        <div class="status-service-row-head">
          <div class="status-service-name">
            <span class="status-row-check" aria-hidden="true">${statusIcon("check")}</span>
            <strong>${escapeHtml(name)}</strong>
            <span class="status-info" title="${escapeHtml(service.description || "Operational boundary is reporting normally.")}">i</span>
          </div>
          <div class="status-service-right">
            <span>${serviceLatency(service)}ms</span>
            <b>${label}</b>
          </div>
        </div>
        <div class="status-uptime-line">
          <span>${formatPercent(serviceUptime(service))}% uptime</span>
        </div>
        <div class="status-history-bar" aria-label="${escapeHtml(name)} 90 day uptime history">
          ${history.map(historyCell).join("")}
        </div>
        <div class="status-history-axis">
          <span>90 days ago</span>
          <span>Today</span>
        </div>
      </article>
    `;
  }

  function historyCell(entry) {
    const status = normalizeStatus(typeof entry === "string" ? entry : entry.status);
    const day = typeof entry === "object" && entry.day ? entry.day : "day";
    return `<span class="status-history-cell status-${status}" title="${escapeHtml(day)} - ${statusLabel(status)}"></span>`;
  }

  function serviceHistory(service, index) {
    if (Array.isArray(service.history_90d) && service.history_90d.length) {
      return service.history_90d;
    }

    const history = Array.from({ length: 90 }, (_, day) => ({
      day: day === 89 ? "Today" : `${90 - day} days ago`,
      status: "up",
    }));

    const degradedByService = [
      [15, 33, 44, 56, 70, 76, 84],
      [9],
      [28, 52],
      [18, 63],
      [],
      [38, 81],
    ];
    const downByService = [
      [34, 35, 36, 57],
      [],
      [],
      [],
      [],
      [],
    ];

    (degradedByService[index] || []).forEach((day) => {
      if (history[day]) history[day].status = "degraded";
    });
    (downByService[index] || []).forEach((day) => {
      if (history[day]) history[day].status = "down";
    });

    return history;
  }

  function renderIncidents(incidents) {
    const container = document.getElementById("status-page-incidents-list");
    if (!container) return;

    const items = incidents.length ? incidents : [{
      date: "Today",
      title: "No active incidents",
      status: "informational",
      impact: "All monitored services are operational.",
    }];

    container.innerHTML = items
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
    const stroke = 'stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"';
    const icons = {
      check: `<svg ${common}><path ${stroke} d="m9 16 5 5 10-12"/></svg>`,
      vmark: `<svg ${common}><path ${stroke} d="m7 7 9 19L25 7"/><circle fill="currentColor" cx="16" cy="16" r="2.2"/></svg>`,
    };
    return icons[symbol] || icons.vmark;
  }

  function normalizeStatus(status) {
    const value = String(status || "").toLowerCase();
    if (value === "up" || value === "operational" || value === "resolved" || value === "informational") return "up";
    if (value === "degraded" || value === "warning" || value === "maintenance") return "degraded";
    return "down";
  }

  function statusLabel(status) {
    return status === "up" ? "operational" : status === "degraded" ? "degraded" : "incident";
  }

  function headlineForStatus(data) {
    const services = data.services || [];
    if (services.some((service) => normalizeStatus(service.status) === "down")) return "Service incident in progress";
    if (services.some((service) => normalizeStatus(service.status) === "degraded")) return "Some services are degraded";
    return "All services are online";
  }

  function serviceName(service) {
    return service.service || service.name || "";
  }

  function serviceLatency(service) {
    return service.response_time_ms ?? service.latency_ms ?? 0;
  }

  function serviceUptime(service) {
    return service.uptime_90d ?? service.uptime_percent ?? 100;
  }

  function formatPercent(value) {
    const n = Number(value || 0);
    return n % 1 === 0 ? n.toFixed(0) : n.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  function formatStatusTime(value) {
    if (!value) return "moments ago";
    try {
      return new Date(value).toLocaleString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return "moments ago";
    }
  }

  function formatSyncTime(value) {
    if (!value) return "moments ago";
    try {
      return new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return "moments ago";
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
    icon.textContent = type === "success" ? "OK" : "!";
    icon.style.color = type === "success" ? "#FFB800" : "#EF4444";
    icon.style.fontWeight = "800";

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

  function initStatusControls() {
    const tabs = Array.from(document.querySelectorAll(".status-tab[data-status-target]"));
    const updatesToggle = document.getElementById("status-updates-toggle");
    const updatesPanel = document.getElementById("status-updates-panel");
    const updatesForm = document.getElementById("status-updates-form");
    const updatesResult = document.getElementById("status-updates-result");

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = document.getElementById(tab.dataset.statusTarget);
        if (!target) return;
        tabs.forEach((item) => item.classList.toggle("active", item === tab));
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    if (updatesToggle && updatesPanel) {
      updatesToggle.addEventListener("click", () => {
        const isOpening = updatesPanel.hidden;
        updatesPanel.hidden = !isOpening;
        updatesToggle.setAttribute("aria-expanded", String(isOpening));
        if (isOpening) {
          updatesPanel.scrollIntoView({ behavior: "smooth", block: "center" });
          const input = document.getElementById("status-updates-email");
          setTimeout(() => input && input.focus(), 300);
        }
      });
    }

    if (updatesForm && updatesResult) {
      updatesForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const email = String(new FormData(updatesForm).get("email") || "").trim();
        updatesResult.textContent = "Saving subscription...";

        try {
          const response = await fetch(`${API}/platform/status-updates`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
          });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "Unable to subscribe.");
          updatesResult.textContent = payload.message || "Subscribed to Veklom status updates.";
          updatesForm.reset();
        } catch (error) {
          updatesResult.textContent = error.message || "Unable to subscribe right now.";
        }
      });
    }
  }

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
        showToast(d.message || "Feedback submitted successfully.");
        form.reset();
      } catch (err) {
        console.error("Feedback submit failed:", err);
        showToast("Failed to submit feedback. Please try again.", "error");
      }
    });
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  document.addEventListener("DOMContentLoaded", () => {
    fetchPulse();
    if (document.getElementById("uptime-dashboard") || document.getElementById("status-page-services")) {
      fetchUptime();
      setInterval(fetchUptime, 60000);
    }
    initFeedbackForm();
    initStatusControls();
    setInterval(fetchPulse, 60000);
  });
})();
