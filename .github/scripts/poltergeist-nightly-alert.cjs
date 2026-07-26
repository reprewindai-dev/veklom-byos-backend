"use strict";

const ALERT_TITLE = "👻 Poltergeist Nightly Alert";
const ALERT_LABEL = "poltergeist-alert";

function parseDiskPercent(value) {
  const normalized = String(value ?? "").trim();
  const match = normalized.match(/^(\d{1,3})(?:\.\d+)?%?$/);
  if (!match) {
    return null;
  }

  const percent = Number.parseInt(match[1], 10);
  return percent >= 0 && percent <= 100 ? percent : null;
}

function evaluateAudit({
  checks = {},
  diskUsed,
  diskProbeStatus,
  diskProbeMessage = "",
  pruneStatus = "not-needed",
  diskAlertThreshold = 88,
}) {
  const failedEndpoints = [];
  const unknownEndpoints = [];

  for (const [name, status] of Object.entries(checks)) {
    if (status === "fail") {
      failedEndpoints.push(name);
    } else if (status !== "ok") {
      unknownEndpoints.push(name);
    }
  }

  const diskPercent = parseDiskPercent(diskUsed);
  const diskProbeFailed = diskProbeStatus !== "ok" || diskPercent === null;
  const diskHigh = !diskProbeFailed && diskPercent >= diskAlertThreshold;
  const pruneFailed = pruneStatus === "failed";

  return {
    failedEndpoints,
    unknownEndpoints,
    diskPercent,
    diskProbeFailed,
    diskProbeMessage,
    diskHigh,
    diskAlertThreshold,
    pruneStatus,
    pruneFailed,
    unhealthy:
      failedEndpoints.length > 0 ||
      unknownEndpoints.length > 0 ||
      diskProbeFailed ||
      diskHigh ||
      pruneFailed,
  };
}

function renderAlertBody(status, now = new Date()) {
  const sections = ["## Poltergeist Nightly Audit Alert"];

  if (status.failedEndpoints.length > 0) {
    sections.push(
      `### Down endpoints\n${status.failedEndpoints
        .map((name) => `- **${name}**`)
        .join("\n")}`,
    );
  }

  if (status.unknownEndpoints.length > 0) {
    sections.push(
      `### Inconclusive endpoint checks\n${status.unknownEndpoints
        .map((name) => `- **${name}** did not return a valid audit result`)
        .join("\n")}`,
    );
  }

  if (status.diskProbeFailed) {
    const detail = status.diskProbeMessage || "The SSH disk probe did not return a valid percentage.";
    sections.push(`### Disk probe failed\n${detail}`);
  } else if (status.diskHigh) {
    sections.push(
      `### Disk usage high\nServer disk is at **${status.diskPercent}%** ` +
        `(alert threshold: ${status.diskAlertThreshold}%).`,
    );
  }

  if (status.pruneFailed) {
    sections.push(
      "### Automatic cleanup failed\n" +
        "The guarded host cleanup command failed. Manual review is required.",
    );
  } else if (status.pruneStatus === "succeeded") {
    sections.push("Automatic host cleanup completed before the final disk measurement.");
  } else if (status.pruneStatus === "disabled" && status.diskHigh) {
    sections.push(
      "Automatic host cleanup is disabled through `POLTERGEIST_AUTO_PRUNE=false`.",
    );
  }

  sections.push(`> Poltergeist last evaluated this alert at ${now.toUTCString()}.`);
  return sections.join("\n\n");
}

function isManagedAlert(issue) {
  return !issue.pull_request && issue.title.startsWith(ALERT_TITLE);
}

async function reconcileNightlyAlert({
  github,
  context,
  checks,
  diskUsed,
  diskProbeStatus,
  diskProbeMessage,
  pruneStatus,
  diskAlertThreshold = 88,
  now = new Date(),
}) {
  const status = evaluateAudit({
    checks,
    diskUsed,
    diskProbeStatus,
    diskProbeMessage,
    pruneStatus,
    diskAlertThreshold,
  });
  const repo = {
    owner: context.repo.owner,
    repo: context.repo.repo,
  };

  const { data: issues } = await github.rest.issues.listForRepo({
    ...repo,
    state: "open",
    labels: ALERT_LABEL,
    per_page: 100,
  });
  const openAlerts = issues
    .filter(isManagedAlert)
    .sort((left, right) => right.number - left.number);

  if (!status.unhealthy) {
    for (const issue of openAlerts) {
      await github.rest.issues.createComment({
        ...repo,
        issue_number: issue.number,
        body:
          `Resolved automatically: all nightly checks passed at ${now.toUTCString()}.`,
      });
      await github.rest.issues.update({
        ...repo,
        issue_number: issue.number,
        state: "closed",
      });
    }
    return { action: openAlerts.length > 0 ? "closed" : "none", status };
  }

  const body = renderAlertBody(status, now);
  let canonical = openAlerts[0];

  if (canonical) {
    await github.rest.issues.update({
      ...repo,
      issue_number: canonical.number,
      title: `${ALERT_TITLE} (active)`,
      body,
    });
  } else {
    const { data: created } = await github.rest.issues.create({
      ...repo,
      title: `${ALERT_TITLE} (active)`,
      body,
      labels: [ALERT_LABEL, "ops"],
    });
    canonical = created;
  }

  for (const duplicate of openAlerts.slice(1)) {
    await github.rest.issues.createComment({
      ...repo,
      issue_number: duplicate.number,
      body: `Superseded by the canonical active alert #${canonical.number}.`,
    });
    await github.rest.issues.update({
      ...repo,
      issue_number: duplicate.number,
      state: "closed",
    });
  }

  return {
    action: openAlerts.length > 0 ? "updated" : "created",
    canonicalIssue: canonical.number,
    status,
  };
}

module.exports = {
  ALERT_TITLE,
  evaluateAudit,
  parseDiskPercent,
  reconcileNightlyAlert,
  renderAlertBody,
};
