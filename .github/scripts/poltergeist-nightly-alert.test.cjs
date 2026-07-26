"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  evaluateAudit,
  parseDiskPercent,
  reconcileNightlyAlert,
} = require("./poltergeist-nightly-alert.cjs");

function createGithub(openIssues = []) {
  const calls = {
    comments: [],
    creates: [],
    updates: [],
  };
  const github = {
    rest: {
      issues: {
        listForRepo: async () => ({ data: openIssues }),
        create: async (input) => {
          calls.creates.push(input);
          return { data: { number: 200, ...input } };
        },
        createComment: async (input) => {
          calls.comments.push(input);
          return { data: input };
        },
        update: async (input) => {
          calls.updates.push(input);
          return { data: input };
        },
      },
    },
  };
  return { calls, github };
}

const context = { repo: { owner: "owner", repo: "repo" } };
const healthyChecks = {
  "API Health": "ok",
  "Agent Discovery": "ok",
};

test("parseDiskPercent accepts valid percentages and rejects invalid probes", () => {
  assert.equal(parseDiskPercent("91%"), 91);
  assert.equal(parseDiskPercent("7"), 7);
  assert.equal(parseDiskPercent("101%"), null);
  assert.equal(parseDiskPercent("ssh failed"), null);
  assert.equal(parseDiskPercent(""), null);
});

test("evaluateAudit treats missing endpoint output and invalid disk probes as failures", () => {
  const status = evaluateAudit({
    checks: { "API Health": "", "Status Page": "ok" },
    diskUsed: "",
    diskProbeStatus: "failed",
    diskProbeMessage: "SSH probe failed",
  });

  assert.deepEqual(status.unknownEndpoints, ["API Health"]);
  assert.equal(status.diskProbeFailed, true);
  assert.equal(status.unhealthy, true);
});

test("evaluateAudit uses the post-cleanup measurement and preserves cleanup failures", () => {
  const recovered = evaluateAudit({
    checks: healthyChecks,
    diskUsed: "65",
    diskProbeStatus: "ok",
    pruneStatus: "succeeded",
  });
  const cleanupFailed = evaluateAudit({
    checks: healthyChecks,
    diskUsed: "65",
    diskProbeStatus: "ok",
    pruneStatus: "failed",
  });

  assert.equal(recovered.unhealthy, false);
  assert.equal(cleanupFailed.unhealthy, true);
  assert.equal(cleanupFailed.pruneFailed, true);
});

test("reconcileNightlyAlert creates one canonical alert", async () => {
  const { calls, github } = createGithub();

  const result = await reconcileNightlyAlert({
    github,
    context,
    checks: { ...healthyChecks, "Status Page": "fail" },
    diskUsed: "42",
    diskProbeStatus: "ok",
    pruneStatus: "not-needed",
    now: new Date("2026-07-20T06:00:00Z"),
  });

  assert.equal(result.action, "created");
  assert.equal(calls.creates.length, 1);
  assert.equal(calls.creates[0].title, "👻 Poltergeist Nightly Alert (active)");
  assert.match(calls.creates[0].body, /Status Page/);
});

test("reconcileNightlyAlert updates the newest alert and closes duplicates", async () => {
  const { calls, github } = createGithub([
    { number: 101, title: "👻 Poltergeist Nightly Alert — 2026-07-15" },
    { number: 102, title: "👻 Poltergeist Nightly Alert — 2026-07-16" },
  ]);

  const result = await reconcileNightlyAlert({
    github,
    context,
    checks: healthyChecks,
    diskUsed: "91%",
    diskProbeStatus: "ok",
    pruneStatus: "disabled",
    now: new Date("2026-07-20T06:00:00Z"),
  });

  assert.equal(result.action, "updated");
  assert.equal(result.canonicalIssue, 102);
  assert.deepEqual(
    calls.updates.map((call) => [call.issue_number, call.state]),
    [
      [102, undefined],
      [101, "closed"],
    ],
  );
  assert.equal(calls.comments[0].issue_number, 101);
  assert.match(calls.comments[0].body, /#102/);
});

test("reconcileNightlyAlert closes every managed alert after recovery", async () => {
  const { calls, github } = createGithub([
    { number: 102, title: "👻 Poltergeist Nightly Alert (active)" },
  ]);

  const result = await reconcileNightlyAlert({
    github,
    context,
    checks: healthyChecks,
    diskUsed: "47",
    diskProbeStatus: "ok",
    pruneStatus: "not-needed",
    now: new Date("2026-07-20T06:00:00Z"),
  });

  assert.equal(result.action, "closed");
  assert.equal(calls.creates.length, 0);
  assert.equal(calls.comments[0].issue_number, 102);
  assert.deepEqual(calls.updates[0], {
    owner: "owner",
    repo: "repo",
    issue_number: 102,
    state: "closed",
  });
});
