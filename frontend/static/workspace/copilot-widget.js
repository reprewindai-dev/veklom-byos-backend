(function () {
  const API_BASE = window.__VEKLOM_API_BASE__ || "/api/v1";

  function tokenFromStorage(storage) {
    if (!storage) return "";
    const directKeys = [
      "access_token",
      "accessToken",
      "token",
      "authToken",
      "veklom_token",
      "veklom.access_token",
    ];
    for (const key of directKeys) {
      const value = storage.getItem(key);
      if (value) return value;
    }
    for (const key of ["auth", "user", "session", "veklom_session"]) {
      const raw = storage.getItem(key);
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        const value =
          parsed.access_token ||
          parsed.accessToken ||
          parsed.token ||
          parsed.jwt ||
          parsed?.state?.accessToken ||
          parsed?.state?.token;
        if (value) return value;
      } catch (_) {}
    }
    return "";
  }

  function authHeaders() {
    const token = tokenFromStorage(window.localStorage) || tokenFromStorage(window.sessionStorage);
    if (!token) return {};
    return {
      Authorization: String(token).startsWith("Bearer ") ? String(token) : `Bearer ${token}`,
    };
  }

  async function fetchCopilotSuggestions(page) {
    try {
      const response = await fetch(`${API_BASE}/copilot/suggestions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({ page, context: {} }),
      });
      if (!response.ok) throw new Error("Failed to fetch suggestions");
      return await response.json();
    } catch (error) {
      console.error("Copilot suggestions error:", error);
      return null;
    }
  }

  async function fetchMoneySavingTips() {
    try {
      const response = await fetch(`${API_BASE}/copilot/money-saving-tips`, {
        headers: authHeaders(),
      });
      if (!response.ok) throw new Error("Failed to fetch money-saving tips");
      return await response.json();
    } catch (error) {
      console.error("Money-saving tips error:", error);
      return null;
    }
  }

  function getCurrentPage() {
    const hash = window.location.hash;
    if (hash.includes("#/overview")) return "overview";
    if (hash.includes("#/playground")) return "playground";
    if (hash.includes("#/marketplace")) return "marketplace";
    if (hash.includes("#/models")) return "models";
    if (hash.includes("#/pipelines")) return "pipelines";
    if (hash.includes("#/deployments")) return "deployments";
    if (hash.includes("#/vault")) return "vault";
    if (hash.includes("#/compliance")) return "compliance";
    if (hash.includes("#/monitoring")) return "monitoring";
    if (hash.includes("#/billing")) return "billing";
    if (hash.includes("#/team")) return "team";
    if (hash.includes("#/settings")) return "settings";
    return "overview";
  }

  function createCopilotWidget() {
    if (document.getElementById("veklom-copilot-widget")) return;

    const widget = document.createElement("div");
    widget.id = "veklom-copilot-widget";
    widget.style.cssText = `
      position: fixed;
      bottom: 80px;
      right: 16px;
      width: 320px;
      max-height: 480px;
      background: rgba(18, 18, 22, 0.98);
      border: 1px solid rgba(249, 115, 22, 0.4);
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
      z-index: 9999;
      font-family: Inter, system-ui, sans-serif;
      overflow: hidden;
      transition: transform 0.3s ease, opacity 0.3s ease;
    `;

    widget.innerHTML = `
      <div style="padding: 12px 16px; background: rgba(249, 115, 22, 0.1); border-bottom: 1px solid rgba(249, 115, 22, 0.3); display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: #22c55e; animation: pulse 2s infinite;"></span>
          <span style="color: #fff; font-size: 13px; font-weight: 600;">Veklom Copilot</span>
        </div>
        <button id="copilot-close" style="background: none; border: none; color: #a1a1a6; cursor: pointer; font-size: 16px; padding: 4px;">×</button>
      </div>
      <div id="copilot-content" style="padding: 16px; overflow-y: auto; max-height: 400px;">
        <div style="color: #a1a1a6; font-size: 12px; text-align: center; padding: 20px 0;">Loading suggestions...</div>
      </div>
    `;

    document.body.appendChild(widget);

    const style = document.createElement("style");
    style.textContent = `
      @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.9); }
      }
      #copilot-suggestion {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        transition: background 0.2s ease;
      }
      #copilot-suggestion:hover {
        background: rgba(255, 255, 255, 0.08);
      }
      .suggestion-action {
        color: #fff;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 4px;
      }
      .suggestion-benefit {
        color: #a1a1a6;
        font-size: 11px;
        margin-bottom: 4px;
      }
      .suggestion-priority {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 10px;
        font-weight: 600;
      }
      .priority-high {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
      }
      .priority-medium {
        background: rgba(249, 115, 22, 0.2);
        color: #f97316;
      }
      .priority-low {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
      }
      .money-tip {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
      }
      .money-tip-category {
        color: #22c55e;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 4px;
      }
      .money-tip-text {
        color: #fff;
        font-size: 12px;
        margin-bottom: 4px;
      }
      .money-tip-savings {
        color: #22c55e;
        font-size: 11px;
      }
    `;
    document.head.appendChild(style);

    document.getElementById("copilot-close").addEventListener("click", () => {
      widget.style.display = "none";
    });
  }

  function renderSuggestions(data) {
    const content = document.getElementById("copilot-content");
    if (!content) return;

    let html = "";

    if (data.suggestions) {
      if (typeof data.suggestions === "string") {
        try {
          const parsed = JSON.parse(data.suggestions);
          data.suggestions = parsed;
        } catch (e) {
          // Not JSON, display as text
        }
      }

      if (Array.isArray(data.suggestions)) {
        html += `<div style="color: #fff; font-size: 12px; font-weight: 600; margin-bottom: 12px;">Suggestions for ${data.page}</div>`;
        data.suggestions.forEach((s) => {
          const priorityClass = s.priority === "high" ? "priority-high" : s.priority === "medium" ? "priority-medium" : "priority-low";
          html += `
            <div id="copilot-suggestion">
              <div class="suggestion-action">${s.action || s.suggestion || "Optimize your workflow"}</div>
              <div class="suggestion-benefit">${s.benefit || s.description || "Improve efficiency"}</div>
              <span class="suggestion-priority ${priorityClass}">${s.priority || "medium"}</span>
            </div>
          `;
        });
      } else {
        html += `<div style="color: #fff; font-size: 12px; margin-bottom: 8px;">${data.suggestions}</div>`;
      }
    }

    content.innerHTML = html;
  }

  function renderMoneyTips(data) {
    const content = document.getElementById("copilot-content");
    if (!content || !data.tips) return;

    let html = `<div style="color: #fff; font-size: 12px; font-weight: 600; margin-bottom: 12px;">💰 Money-Saving Tips</div>`;

    data.tips.forEach((tip) => {
      html += `
        <div class="money-tip">
          <div class="money-tip-category">${tip.category}</div>
          <div class="money-tip-text">${tip.tip}</div>
          <div class="money-tip-savings">💵 ${tip.savings}</div>
        </div>
      `;
    });

    content.innerHTML = html;
  }

  async function loadCopilotContent() {
    const page = getCurrentPage();
    const content = document.getElementById("copilot-content");
    if (!content) return;

    content.innerHTML = `<div style="color: #a1a1a6; font-size: 12px; text-align: center; padding: 20px 0;">Loading suggestions...</div>`;

    // Try proactive suggestions first
    const suggestions = await fetchCopilotSuggestions(page);
    if (suggestions && suggestions.suggestions) {
      renderSuggestions(suggestions);
      return;
    }

    // Fallback to money-saving tips
    const tips = await fetchMoneySavingTips();
    if (tips && tips.tips) {
      renderMoneyTips(tips);
      return;
    }

    content.innerHTML = `<div style="color: #a1a1a6; font-size: 12px; text-align: center; padding: 20px 0;">No suggestions available</div>`;
  }

  function initCopilot() {
    createCopilotWidget();
    loadCopilotContent();

    // Reload suggestions when page changes
    window.addEventListener("hashchange", () => {
      setTimeout(loadCopilotContent, 500);
    });

    // Refresh suggestions every 60 seconds
    setInterval(loadCopilotContent, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCopilot);
  } else {
    initCopilot();
  }
})();
