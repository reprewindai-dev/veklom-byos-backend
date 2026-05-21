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
      const container = document.getElementById("uptime-dashboard");
      if (!container) return;
      container.innerHTML = d.services
        .map(
          (s) => `
        <div class="card" style="text-align:center">
          <div style="font-size:1.5rem;margin-bottom:8px;color:${s.status === "up" ? "var(--green)" : "var(--red)"}">${s.status === "up" ? "●" : "○"}</div>
          <h3 style="font-size:1rem;text-transform:capitalize">${s.service}</h3>
          <div style="color:var(--text-muted);font-size:0.8rem;margin-top:4px">${s.response_time_ms || 0}ms</div>
          <div style="color:${s.status === "up" ? "var(--green)" : "var(--red)"};font-size:0.8rem;margin-top:4px">${s.status === "up" ? "Operational" : "Down"}</div>
        </div>
      `
        )
        .join("");
    } catch (e) {
      console.warn("Uptime fetch failed:", e);
    }
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
