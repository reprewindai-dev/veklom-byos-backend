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
    let fallback = null;
    for (let i = 0; current && i < 8; i += 1) {
      const className = String(current.className || "");
      if (className.includes("frame")) {
        return current;
      }
      if (!fallback && (className.includes("rounded") || className.includes("border"))) {
        fallback = current;
      }
      current = current.parentElement;
    }
    return fallback || (node && node.parentElement);
  }

  function panelByHeading(pattern) {
    return closestPanel(findText(pattern));
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
    }
  }

  function setRecentRuns(runs) {
    const panel = panelByHeading(/RECENT RUNS/i);
    if (!panel) return;
    const tbody = panel.querySelector("tbody");
    if (!tbody) return;
    const liveRuns = Array.isArray(runs) ? runs : [];
    tbody.innerHTML = "";
    if (liveRuns.length === 0) {
      const row = document.createElement("tr");
      row.className = "border-b border-border/40 last:border-0";
      row.innerHTML =
        '<td colspan="7" class="px-4 py-5 text-center text-muted-foreground">No live inference runs yet.</td>';
      tbody.appendChild(row);
      return;
    }
    liveRuns.slice(0, 5).forEach((run) => {
      const row = document.createElement("tr");
      row.className = "border-b border-border/40 last:border-0 hover-elevate";
      row.innerHTML =
        `<td class="px-4 py-2">${run.model || "model"}</td>` +
        `<td class="px-4 py-2">${String(run.route || "hetzner").replace("-", " ")}</td>` +
        `<td class="px-4 py-2 text-right font-mono">${Number(run.latency || 0)} ms</td>` +
        `<td class="px-4 py-2 text-right font-mono">${formatInt(run.tokens || 0)}</td>` +
        `<td class="px-4 py-2 text-right font-mono">${formatUsd(run.cost || 0, 5)}</td>` +
        `<td class="px-4 py-2">${String(run.policy || "passed").toUpperCase()}</td>` +
        `<td class="px-4 py-2 text-right text-muted-foreground font-mono">${run.ts || ""}</td>`;
      tbody.appendChild(row);
    });
  }

  function setSpend(data) {
    setExact(/^\$1,284\.80 of \$1,900 cap$/, `${formatUsd(data.spend_today_usd, 2)} of ${formatUsd(data.spend_cap_usd, 0)} cap`);
    setExact(/^\$0\.0184 \/ min$/, `${formatUsd(data.burn_rate_usd_per_min, 4)} / min`);
    setExact(/^\$1,802 \(94% cap\)$/, `${formatUsd(data.forecast_eod_usd, 0)} (${Number(data.spend_percent || 0)}% cap)`);
    setSpendBreakdown(data.spend_breakdown);
  }

  function setSpendBreakdown(breakdown) {
    const items = Array.isArray(breakdown) ? breakdown : [];
    items.forEach((item) => {
      const labelNode = findText(new RegExp(`^${item.label}$`, "i"));
      const panel = closestPanel(labelNode);
      if (!panel) return;
      const nodes = textNodes(panel);
      const valueNode = nodes.find((node) => /^\$[\d,.]+/.test(node.nodeValue.trim()));
      const percentNode = nodes.find((node) => /^\d+%$/.test(node.nodeValue.trim()));
      if (valueNode) valueNode.nodeValue = formatUsd(item.amount_usd, 2);
      if (percentNode) percentNode.nodeValue = `${Number(item.percent || 0)}%`;
    });
  }

  function setSimpleList(panelPattern, rows, emptyText, renderRow) {
    const panel = panelByHeading(panelPattern);
    if (!panel) return;
    const body = Array.from(panel.children).find((child) =>
      String(child.className || "").includes("divide-y"),
    );
    if (!body) return;
    body.innerHTML = "";
    const liveRows = Array.isArray(rows) ? rows : [];
    if (liveRows.length === 0) {
      body.innerHTML = `<div class="px-4 py-5 text-[12px] text-muted-foreground">${emptyText}</div>`;
      return;
    }
    liveRows.slice(0, 5).forEach((row) => body.appendChild(renderRow(row)));
  }

  function setAlerts(alerts) {
    setSimpleList(/^ALERTS$/i, alerts, "No live alerts.", (alert) => {
      const row = document.createElement("div");
      row.className = "flex items-start gap-3 px-4 py-3";
      row.innerHTML =
        '<span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-info"></span>' +
        '<div class="flex-1">' +
        `<div class="text-[12.5px]">${alert.title || "Alert"}</div>` +
        `<div class="mt-0.5 flex items-center gap-2 text-eyebrow"><span>${alert.source || "monitoring"}</span><span>·</span><span>${alert.time || ""}</span></div>` +
        "</div>";
      return row;
    });
  }

  function setAuditLogs(logs) {
    setSimpleList(/AUDIT TRAIL/i, logs, "No live audit records yet.", (log) => {
      const row = document.createElement("div");
      row.className = "px-4 py-2.5 text-[12px]";
      row.innerHTML =
        `<div class="flex items-center justify-between"><span class="font-mono">${log.action || "audit.event"}</span><span class="font-mono text-[10.5px] text-muted-foreground">${log.ts || ""}</span></div>` +
        `<div class="flex items-center justify-between text-[11px] text-muted-foreground"><span class="truncate">${log.target || "workspace"} · ${log.actor || "system"}</span><span class="font-mono">${log.hash || ""}</span></div>`;
      return row;
    });
  }

  function setPolicyEvents(events) {
    const panel = panelByHeading(/POLICY INTERCEPTION/i);
    const list = panel && panel.querySelector("ol");
    if (!list) return;
    const liveEvents = Array.isArray(events) ? events : [];
    list.innerHTML = "";
    if (liveEvents.length === 0) {
      const item = document.createElement("li");
      item.className = "px-1 py-3 text-[12px] text-muted-foreground";
      item.textContent = "No live policy decisions yet.";
      list.appendChild(item);
      return;
    }
    liveEvents.slice(0, 5).forEach((event) => {
      const item = document.createElement("li");
      item.className = "relative flex gap-3 pl-2";
      item.innerHTML =
        '<div class="z-10 mt-0.5 grid h-5 w-5 place-items-center rounded-full border border-info/40 bg-background text-info">•</div>' +
        '<div class="flex-1">' +
        `<div class="flex items-center justify-between"><span class="text-[12.5px] text-foreground">${event.title || "Policy event"}</span><span class="font-mono text-[10.5px] text-muted-foreground">${event.t || ""}</span></div>` +
        `<div class="text-[11.5px] text-muted-foreground">${event.body || ""}</div>` +
        "</div>";
      list.appendChild(item);
    });
  }

  function setFleet(fleet) {
    const panel = panelByHeading(/^FLEET$/i);
    const body = panel && panel.querySelector(".space-y-2");
    if (!body) return;
    const liveFleet = Array.isArray(fleet) ? fleet : [];
    body.innerHTML = "";
    if (liveFleet.length === 0) {
      body.innerHTML = '<div class="px-1 py-3 text-[12px] text-muted-foreground">No live models enabled.</div>';
      return;
    }
    liveFleet.slice(0, 4).forEach((model) => {
      const row = document.createElement("div");
      row.className = "flex items-center justify-between rounded-md border bg-background/40 px-3 py-2";
      row.innerHTML =
        `<div><div class="text-[12.5px]">${model.name || "Model"}</div><div class="text-[10.5px] text-muted-foreground font-mono">${model.quant || ""} · ${model.replicas || 0} replicas</div></div>` +
        `<div class="flex items-center gap-1.5"><span class="rounded border px-2 py-1 font-mono text-[10px]">${String(model.route || "hetzner").replace("-", " ")}</span><span class="rounded border px-2 py-1 font-mono text-[10px]">P50 ${Number(model.p50 || 0)} MS</span></div>`;
      body.appendChild(row);
    });
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
    setPolicyEvents(data.policy_events);
    setAlerts(data.alerts);
    setAuditLogs(data.audit_logs);
    setFleet(data.fleet);

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
