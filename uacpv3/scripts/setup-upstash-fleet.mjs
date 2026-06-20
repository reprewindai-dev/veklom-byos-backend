import { Box } from "@upstash/box";
import crypto from "node:crypto";
import { execSync } from "node:child_process";
import {
  BOX_WORKSPACE,
  DEFAULT_BOX_PORT,
  DEFAULT_BOX_SIZE,
  boxFleetSpecs,
  buildBootstrapCommand,
  buildManualLaunchCommand,
  parseFleetSelection,
} from "./upstash-box-fleet.config.mjs";

const apiKey = process.env.UPSTASH_BOX_API_KEY || "";
const port = Number(process.env.UACP_BOX_PORT || process.env.PORT || DEFAULT_BOX_PORT);
const size = process.env.UPSTASH_BOX_SIZE || DEFAULT_BOX_SIZE;
const fleetSelection = parseFleetSelection(process.env.UACP_BOX_FLEET || "");
const waitAttempts = Number(process.env.UPSTASH_BOX_WAIT_ATTEMPTS || 24);
const waitMs = Number(process.env.UPSTASH_BOX_WAIT_MS || 5000);
const envFilePath = process.env.UPSTASH_BOX_ENV_FILE || `${BOX_WORKSPACE}/.env`;
const repoUrl = process.env.UPSTASH_BOX_GIT_URL || readGit("git remote get-url origin");
const repoRef = process.env.UPSTASH_BOX_GIT_REF || readGit("git branch --show-current") || "main";
const setInitCommand = toBool(process.env.UPSTASH_BOX_SET_INIT_COMMAND, true);
const resumeIfPaused = toBool(process.env.UPSTASH_BOX_RESUME_IF_PAUSED, true);
const restartIfInitChanged = toBool(process.env.UPSTASH_BOX_RESTART_IF_INIT_CHANGED, true);
const writeDotEnv = toBool(process.env.UPSTASH_BOX_WRITE_DOTENV, true);

if (!apiKey) {
  throw new Error("Missing UPSTASH_BOX_API_KEY.");
}

if (!repoUrl) {
  throw new Error("Missing repo URL. Set UPSTASH_BOX_GIT_URL or configure git origin in the local repo.");
}

const selectedSpecs = boxFleetSpecs.filter((spec) => fleetSelection.has(spec.id) || fleetSelection.has(spec.boxName));
if (!selectedSpecs.length) {
  throw new Error(`No box specs matched UACP_BOX_FLEET=${process.env.UACP_BOX_FLEET || ""}`);
}

const existingBoxes = await Box.list({ apiKey });
const existingByName = new Map(existingBoxes.map((entry) => [entry.name || "", entry]));

const sharedSecrets = {
  internalApiKey: process.env.UACP_INTERNAL_API_KEY || "",
  adminKey: process.env.UACP_ADMIN_KEY || "",
};

const seedSpec = selectedSpecs.find((spec) => existingByName.has(spec.boxName)) || null;
if (seedSpec) {
  const seedRecord = existingByName.get(seedSpec.boxName);
  const seedBox = await Box.get(seedRecord.id, { apiKey });
  await hydrateSharedSecrets(seedBox);
}

if (!sharedSecrets.internalApiKey) {
  sharedSecrets.internalApiKey = crypto.randomBytes(24).toString("hex");
}

if (!sharedSecrets.adminKey) {
  sharedSecrets.adminKey = sharedSecrets.internalApiKey;
}

const results = [];

for (const spec of selectedSpecs) {
  const result = await reconcileBox(spec);
  results.push(result);
}

console.log(
  JSON.stringify(
    {
      ok: true,
      repo: {
        url: repoUrl,
        ref: repoRef,
      },
      fleet: results,
    },
    null,
    2,
  ),
);

async function reconcileBox(spec) {
  let boxRecord = existingByName.get(spec.boxName) || null;
  let box = null;

  if (boxRecord) {
    box = await Box.get(boxRecord.id, { apiKey });
  } else {
    box = await Box.create({
      apiKey,
      runtime: "node",
      size,
      keepAlive: true,
      name: spec.boxName,
      initCommand: buildBootstrapCommand(spec, { repoUrl, repoRef }),
      env: buildRuntimeEnv(spec),
    });

    boxRecord = { id: box.id, name: spec.boxName, keep_alive: true, runtime: "node" };
    existingByName.set(spec.boxName, boxRecord);
  }

  const statusBefore = await box.getStatus();
  const keepAlive = true;

  let currentInitCommand = "";
  try {
    currentInitCommand = await box.getInitCommand();
  } catch {
    currentInitCommand = "";
  }

  const initCommand = buildBootstrapCommand(spec, { repoUrl, repoRef });
  const initCommandUpdated = setInitCommand && normalize(currentInitCommand) !== normalize(initCommand);

  if (initCommandUpdated) {
    await box.setInitCommand(initCommand);
  }

  await hydrateSharedSecrets(box);

  if (writeDotEnv) {
    await writeRuntimeDotEnv(box, spec);
  }

  if (resumeIfPaused && statusBefore.status === "paused") {
    await box.resume();
  }

  const healthBeforeLaunch = await tryFetchJson(box, "/api/health");
  let manualLaunch = false;

  if (!healthBeforeLaunch && (initCommandUpdated ? restartIfInitChanged : true)) {
    await startKeepAliveProcess(box, spec);
    manualLaunch = true;
  }

  const health = await waitForJson(box, "/api/health");
  const bootstrap = await waitForJson(box, "/api/bootstrap");
  const topology = await waitForJson(box, "/api/box-topology");
  const operators = await waitForJson(box, "/api/v1/internal/operators", {
    "x-uacp-internal-key": sharedSecrets.internalApiKey,
  });
  const operatorRuns = await waitForJson(box, "/api/v1/internal/operators/runs", {
    "x-uacp-internal-key": sharedSecrets.internalApiKey,
  });
  const statusAfter = await box.getStatus();

  return {
    box: {
      id: box.id,
      name: spec.boxName,
      role: spec.role,
      runtimeMode: spec.runtimeMode,
      workerGroup: spec.workerGroup,
      statusBefore: statusBefore.status,
      statusAfter: statusAfter.status,
      keepAlive,
    },
    initCommand: {
      updated: initCommandUpdated,
      target: initCommand,
      manualLaunch,
    },
    runtime: {
      healthOk: Boolean(health?.ok),
      boxName: health?.runtime?.boxName,
      mode: health?.runtime?.mode,
      workerGroup: health?.runtime?.workerGroup,
      storage: health?.runtime?.storage || null,
    },
    topology: topology?.current || null,
    operators: {
      count: Array.isArray(operators) ? operators.length : null,
      runCount: Array.isArray(operatorRuns) ? operatorRuns.length : null,
    },
    bootstrap: {
      system: bootstrap?.system,
      status: bootstrap?.status,
    },
  };
}

async function hydrateSharedSecrets(box) {
  if (!sharedSecrets.internalApiKey) {
    sharedSecrets.internalApiKey = await readBoxEnv(box, "UACP_INTERNAL_API_KEY");
  }

  if (!sharedSecrets.internalApiKey) {
    sharedSecrets.internalApiKey = await readDotEnvValue(box, "UACP_INTERNAL_API_KEY");
  }

  if (!sharedSecrets.internalApiKey) {
    sharedSecrets.internalApiKey = crypto.randomBytes(24).toString("hex");
  }

  if (!sharedSecrets.adminKey) {
    sharedSecrets.adminKey = await readBoxEnv(box, "UACP_ADMIN_KEY");
  }

  if (!sharedSecrets.adminKey) {
    sharedSecrets.adminKey = await readDotEnvValue(box, "UACP_ADMIN_KEY");
  }

  if (!sharedSecrets.adminKey) {
    sharedSecrets.adminKey = sharedSecrets.internalApiKey;
  }
}

function buildRuntimeEnv(spec) {
  const runtimeEnv = {
    PORT: String(port),
    USER_EMAIL: process.env.USER_EMAIL || "founder@uacp.local",
    CONTACT_EMAIL: process.env.CONTACT_EMAIL || process.env.USER_EMAIL || "founder@uacp.local",
    UACP_INTERNAL_API_KEY: sharedSecrets.internalApiKey,
    UACP_ADMIN_KEY: sharedSecrets.adminKey,
    UACP_BOX_NAME: spec.boxName,
    UACP_RUNTIME_MODE: spec.runtimeMode,
    UACP_WORKER_GROUP: spec.workerGroup,
    UACP_ARCHIVE_WRITE_REQUIRED: process.env.UACP_ARCHIVE_WRITE_REQUIRED || "true",
  };

  const boxDatabaseUrl = process.env.UACP_BOX_DATABASE_URL || process.env.DATABASE_URL || "";
  const boxDatabaseSslMode = process.env.UACP_BOX_DATABASE_SSL_MODE || process.env.DATABASE_SSL_MODE || "";

  if (boxDatabaseUrl) {
    runtimeEnv.DATABASE_URL = boxDatabaseUrl;
  }

  if (boxDatabaseSslMode) {
    runtimeEnv.DATABASE_SSL_MODE = boxDatabaseSslMode;
  }

  for (const key of [
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GROQ_API_KEY",
    "GROQ_BASE_URL",
    "GROQ_MODEL",
    "HF_TOKEN",
    "HF_MODEL",
    "HF_BASE_URL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "UACP_MODEL_PROVIDER",
    "UACP_MODEL_PROVIDER_ORDER",
    "UACP_ENABLE_GEMINI_PRIMARY",
    "ALLOW_GEMINI_FALLBACK",
    "DEFAULT_RESEARCH_QUERY",
    "DATA_DIR",
    "UACP_COLD_STORAGE_DIR",
    "UACP_BACKEND_BASE_URL",
    "UACP_BACKEND_TIMEOUT_MS",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "UACP_RATE_LIMIT_TRUST_ACCESS_TIER_HEADER",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "UACP_OUTBOUND_REPLY_TO",
    "UACP_OUTBOUND_MAX_SENDS_PER_RUN",
    "GIT_TOKEN",
    "GITHUB_TOKEN",
  ]) {
    if (process.env[key]) {
      runtimeEnv[key] = process.env[key];
    }
  }

  return runtimeEnv;
}

async function writeRuntimeDotEnv(box, spec) {
  const content = Object.entries(buildRuntimeEnv(spec))
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join("\n")
    .concat("\n");

  await box.files.write({ path: envFilePath, content });
}

async function startKeepAliveProcess(box, spec) {
  const script = buildManualLaunchCommand(spec);
  await box.exec.command(`sh -lc ${shellQuote(shellLine(script))}`);
}

async function waitForJson(box, path, headers = {}) {
  let lastError = "";

  for (let attempt = 1; attempt <= waitAttempts; attempt += 1) {
    try {
      return await fetchJson(box, path, headers);
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
      if (attempt < waitAttempts) {
        await sleep(waitMs);
      }
    }
  }

  throw new Error(`Failed to fetch ${path} after ${waitAttempts} attempts. ${lastError}`);
}

async function fetchJson(box, path, headers = {}) {
  const source = `
const url = ${JSON.stringify(`http://127.0.0.1:${port}${path}`)};
const headers = ${JSON.stringify(headers)};
const response = await fetch(url, { headers });
const text = await response.text();
if (!response.ok) {
  console.error(text);
  process.exit(response.status || 1);
}
process.stdout.write(text);
`;

  const run = await box.exec.command(`node --input-type=module -e ${shellQuote(source)}`);
  return JSON.parse(String(run.result || "").trim());
}

async function tryFetchJson(box, path, headers = {}) {
  try {
    return await fetchJson(box, path, headers);
  } catch {
    return null;
  }
}

async function readBoxEnv(box, name) {
  const source = `
import os, sys
sys.stdout.write(os.environ.get(${JSON.stringify(name)}, ""))
`;
  const run = await box.exec.command(`python -c ${shellQuote(source)}`);
  return String(run.result || "").trim();
}

async function readDotEnvValue(box, name) {
  const source = `
import fs from "node:fs";
const file = ${JSON.stringify(envFilePath)};
const key = ${JSON.stringify(name)};
if (!fs.existsSync(file)) process.exit(0);
const line = fs.readFileSync(file, "utf8").split(/\\r?\\n/).find((entry) => entry.startsWith(key + "="));
if (!line) process.exit(0);
const raw = line.slice(key.length + 1);
try {
  process.stdout.write(JSON.parse(raw));
} catch {
  process.stdout.write(raw.replace(/^"|"$/g, ""));
}
`;
  const run = await box.exec.command(`node --input-type=module -e ${shellQuote(source)}`);
  return String(run.result || "").trim();
}

function normalize(value) {
  return String(value || "").trim().replace(/\r\n/g, "\n");
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}

function shellLine(value) {
  return String(value || "").replace(/\r/g, "").replace(/\n/g, "");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toBool(value, fallback) {
  if (value == null || value === "") return fallback;
  return /^(1|true|yes|on)$/i.test(String(value));
}

function readGit(command) {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}
