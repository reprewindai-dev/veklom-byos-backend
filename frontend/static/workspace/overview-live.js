(function () {
  const ROOT_HASHES = new Set(["", "#", "#/", "#/overview"]);
  const REFRESH_MS = 15000;

  function apiBase() {
    const filePreviewBase =
      window.location.protocol === "file:" ? "http://5.78.135.11:8000/api/v1" : "/api/v1";
    const configured = window.__VEKLOM_API_BASE__ || filePreviewBase;
    return String(configured).replace(/\/+$/, "");
  }

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
      } catch (_) {
        // Ignore non-JSON storage entries.
      }
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

  async function fetchJson(path, allowAuthFallback) {
    const response = await fetch(`${apiBase()}${path}`, {
      headers: {
        Accept: "application/json",
        ...authHeaders(),
      },
      credentials: "same-origin",
    });

    if (allowAuthFallback && (response.status === 401 || response.status === 403)) {
      return fetchJson("/workspace/overview/live", false);
    }
    if (!response.ok) throw new Error(`Overview API ${response.status}`);
    return response.json();
  }

  function formatInt(value) {
    return new Intl.NumberFormat("en-US").format(Number(value || 0));
  }

  function formatCompact(value) {
    const n = Number(value || 0);
    if (n >= 1000) return `${Math.round(n / 1000)}k`;
    return formatInt(n);
  }

  function formatUsd(value, decimals) {
    return `$${Number(value || 0).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}`;
  }

  function textNodes(root) {
    const nodes = [];
    const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      if (node.nodeValue && node.nodeValue.trim()) nodes.push(node);
      node = walker.nextNode();
    }
    return nodes;
  }

  function findText(pattern, root) {
    return textNodes(root).find((node) => pattern.test(node.nodeValue.trim()));
  }

  function closestPanel(node) {
    let current = node && node.parentElement;
    for (let i = 0; current && i < 8; i += 1) {
      const className = String(current.className || "");
      if (
        className.includes("frame") ||
        className.includes("rounded") ||
        className.includes("border")
      ) {
        return current;
      }
      current = current.parentElement;
    }
    return node && node.parentElement;
  }

  function setMetric(labelPattern, valueText, secondaryText) {
    const labelNode = findText(labelPattern);
    const panel = closestPanel(labelNode);
    if (!panel) return;
    const nodes = textNodes(panel);
    const valueNode = nodes.find((node) =>
      /^(\$)?[\d,.]+(?:k| ms)?$/i.test(node.nodeValue.trim()),
    );
    if (valueNode) valueNode.nodeValue = valueText;
    if (secondaryText) {
      const secondaryNode = nodes.find((node) =>
        /(?:\+|-)?\d+(?:\.\d+)?%|verified|quantized|cap|ms/i.test(node.nodeValue.trim()),
      );
      if (secondaryNode && secondaryNode !== valueNode) secondaryNode.nodeValue = secondaryText;
    }
  }

  function setExact(oldPattern, valueText) {
    const node = findText(oldPattern);
    if (node) node.nodeValue = valueText;
  }

  function wireButtons() {
    for (const button of document.querySelectorAll("button, a")) {
      const label = button.textContent.replace(/\s+/g, " ").trim();
      if (label === "New deployment") {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          window.location.hash = "#/deployments";
        });
      }
      if (label === "Open Playground" || label === "Playground") {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          window.location.hash = "#/playground";
        });
      }
      if (label === "Reserve" || label === "Fund") {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          window.location.hash = "#/billing";
        });
      }
    }
  }

  function setRecentRuns(runs) {
    if (!Array.isArray(runs) || runs.length === 0) return;
    const panel = closestPanel(findText(/RECENT RUNS/i));
    if (!panel) return;
    const rows = Array.from(panel.querySelectorAll("tbody tr"));
    rows.slice(0, runs.length).forEach((row, index) => {
      const run = runs[index];
      const cells = Array.from(row.querySelectorAll("td"));
      if (cells[0]) cells[0].textContent = run.model || "model";
      if (cells[1]) cells[1].textContent = String(run.route || "hetzner").replace("-", " ");
      if (cells[2]) cells[2].textContent = `${Number(run.latency || 0)} ms`;
      if (cells[3]) cells[3].textContent = formatInt(run.tokens || 0);
      if (cells[4]) cells[4].textContent = formatUsd(run.cost || 0, 5);
      if (cells[5]) cells[5].textContent = String(run.policy || "passed").toUpperCase();
      if (cells[6]) cells[6].textContent = run.ts || "";
    });
  }

  function setSpend(data) {
    setExact(/^\$1,284\.80 of \$1,900 cap$/, `${formatUsd(data.spend_today_usd, 2)} of ${formatUsd(data.spend_cap_usd, 0)} cap`);
    setExact(/^\$0\.0184 \/ min$/, `${formatUsd(data.burn_rate_usd_per_min, 4)} / min`);
    setExact(/^\$1,802 \(94% cap\)$/, `${formatUsd(data.forecast_eod_usd, 0)} (${Number(data.spend_percent || 0)}% cap)`);
  }

  function applyOverview(data) {
    if (!ROOT_HASHES.has(window.location.hash)) return;

    setMetric(/REQUESTS\s*\/\s*MIN/i, formatInt(data.requests_per_min), "+ live");
    setMetric(/P50 LATENCY/i, `${Number(data.p50_latency_ms || 0)} ms`, "live");
    setMetric(/TOKENS\s*\/\s*SEC/i, formatCompact(data.tokens_per_sec), "+ live");
    setMetric(/SPEND TODAY/i, formatUsd(data.spend_today_usd, 0), `${Number(data.spend_percent || 0)}% cap`);
    setMetric(/ACTIVE MODELS/i, formatInt(data.active_models), `${formatInt(data.models_enabled)} enabled`);
    setMetric(/AUDIT ENTRIES/i, formatInt(data.audit_entries), "verified");

    if (data.routing) {
      setExact(/HETZNER\s+88%/i, `HETZNER ${Number(data.routing.hetzner_percent || 0)}%`);
      setExact(/AWS\s+12%/i, `AWS ${Number(data.routing.aws_percent || 0)}%`);
    }

    setSpend(data);
    setRecentRuns(data.recent_runs);

    const alertsOpen = Array.isArray(data.alerts) ? data.alerts.length : 0;
    setExact(/^3 open$/i, `${alertsOpen} open`);
    setExact(/^12$/i, formatInt(data.active_models));

    document.body.dataset.veklomOverviewLive = "connected";
    document.body.dataset.veklomOverviewUpdatedAt = data.updated_at || new Date().toISOString();
    window.dispatchEvent(new CustomEvent("veklom:overview-live", { detail: data }));
  }

  async function refreshOverview() {
    try {
      const data = await fetchJson("/workspace/overview", true);
      applyOverview(data);
    } catch (error) {
      document.body.dataset.veklomOverviewLive = "error";
      document.body.dataset.veklomOverviewError = error.message || String(error);
    }
  }

  function start() {
    wireButtons();
    refreshOverview();
    window.addEventListener("hashchange", () => {
      wireButtons();
      refreshOverview();
    });
    window.setInterval(refreshOverview, REFRESH_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
