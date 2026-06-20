export const BOX_WORKSPACE = "/workspace/home/uacpv3";
export const DEFAULT_BOX_SIZE = "small";
export const DEFAULT_BOX_PORT = 3000;

export const boxFleetSpecs = [
  {
    id: "pillar_council",
    boxName: "uacp-pillar-council",
    runtimeMode: "pillar_council",
    workerGroup: "pillar_council",
    startScript: "worker:pillar-council",
    logFile: "pillar-council.log",
    role: "hot",
    wakeTriggers: ["minimum_live_heartbeat", "governance_escalation", "archive_required"],
    handoffTargets: ["growth_sales", "operations_intake", "builder_systems", "vendor_network"],
  },
  {
    id: "growth_sales",
    boxName: "uacp-growth-sales",
    runtimeMode: "growth_sales",
    workerGroup: "growth_sales",
    startScript: "worker:growth-sales",
    logFile: "growth-sales.log",
    role: "warm",
    wakeTriggers: ["outbound_queue_pressure", "qualified_lead_backlog", "sales_committee_release"],
    handoffTargets: ["operations_intake", "vendor_network"],
  },
  {
    id: "operations_intake",
    boxName: "uacp-operations-intake",
    runtimeMode: "operations_intake",
    workerGroup: "operations_intake",
    startScript: "worker:operations-intake",
    logFile: "operations-intake.log",
    role: "warm",
    wakeTriggers: ["inbound_request_queue", "activation_recovery", "ops_committee_release"],
    handoffTargets: ["builder_systems", "vendor_network", "pillar_council"],
  },
  {
    id: "builder_systems",
    boxName: "uacp-builder-systems",
    runtimeMode: "builder_systems",
    workerGroup: "builder_systems",
    startScript: "worker:builder-systems",
    logFile: "builder-systems.log",
    role: "warm",
    wakeTriggers: ["tool_build_queue", "repo_issue_backlog", "engineering_committee_release"],
    handoffTargets: ["operations_intake", "pillar_council"],
  },
  {
    id: "vendor_network",
    boxName: "uacp-vendor-network",
    runtimeMode: "vendor_network",
    workerGroup: "vendor_network",
    startScript: "worker:vendor-network",
    logFile: "vendor-network.log",
    role: "warm",
    wakeTriggers: ["vendor_candidate_queue", "partner_outreach_queue", "vendor_committee_release"],
    handoffTargets: ["growth_sales", "operations_intake", "pillar_council"],
  },
];

export function findBoxSpec({ boxName = "", runtimeMode = "", workerGroup = "" } = {}) {
  return (
    boxFleetSpecs.find(
      (spec) =>
        spec.boxName === boxName || spec.runtimeMode === runtimeMode || spec.workerGroup === workerGroup || spec.id === runtimeMode,
    ) || boxFleetSpecs[0]
  );
}

export function parseFleetSelection(raw) {
  if (!raw) {
    return new Set(boxFleetSpecs.map((spec) => spec.id));
  }

  const tokens = String(raw)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  if (!tokens.length) {
    return new Set(boxFleetSpecs.map((spec) => spec.id));
  }

  return new Set(tokens);
}

export function buildBootstrapCommand(spec, { repoUrl, repoRef }) {
  const ref = repoRef || "main";
  const gitCloneUrl = repoUrl || "";
  const branchFlags = ref ? `--branch ${shellToken(ref)} --single-branch` : "";

  return [
    "set -e",
    "mkdir -p /workspace/home",
    gitCloneUrl
      ? `if [ ! -d ${shellToken(BOX_WORKSPACE)}/.git ]; then git clone ${branchFlags} ${shellToken(gitCloneUrl)} ${shellToken(BOX_WORKSPACE)}; fi`
      : `if [ ! -d ${shellToken(BOX_WORKSPACE)}/.git ]; then echo 'Missing repo URL for box bootstrap' >&2; exit 1; fi`,
    `cd ${shellToken(BOX_WORKSPACE)}`,
    ref ? `git fetch origin ${shellToken(ref)}` : "git fetch origin",
    ref ? `git checkout ${shellToken(ref)}` : "true",
    ref ? `git reset --hard origin/${shellToken(ref)}` : "git reset --hard HEAD",
    "npm install",
    "npm run build",
    `npm run ${shellToken(spec.startScript)}`,
  ].join(" && ");
}

export function buildManualLaunchCommand(spec) {
  return [
    `cd ${shellToken(BOX_WORKSPACE)}`,
    `nohup npm run ${shellToken(spec.startScript)} >${shellToken(`${BOX_WORKSPACE}/${spec.logFile}`)} 2>&1 </dev/null &`,
    "echo started",
  ].join("; ");
}

function shellToken(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}
