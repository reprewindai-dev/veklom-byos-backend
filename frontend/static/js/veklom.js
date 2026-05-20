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

  // --- Feedback Form ---
  function initFeedbackForm() {
    const form = document.getElementById("feedback-form");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const cat = document.getElementById("fb-category").value;
      const subj = document.getElementById("fb-subject").value;
      const body = document.getElementById("fb-body").value;
      if (!subj || !body) return;
      try {
        const res = await fetch(
          `${API}/feedback/?category=${encodeURIComponent(cat)}&subject=${encodeURIComponent(subj)}&body=${encodeURIComponent(body)}`,
          { method: "POST" }
        );
        const d = await res.json();
        const result = document.getElementById("fb-result");
        result.textContent = d.message || "Submitted!";
        result.style.display = "block";
        form.reset();
        setTimeout(() => (result.style.display = "none"), 4000);
      } catch (err) {
        console.error("Feedback submit failed:", err);
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
