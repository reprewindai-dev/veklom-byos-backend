import "dotenv/config";
import crypto from "node:crypto";
import { promises as fs } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";
import { gzipSync, gunzipSync } from "node:zlib";
import cors from "cors";
import express from "express";
import { GoogleGenAI } from "@google/genai";
import pg from "pg";
import { Client as QStashClient, Receiver as QStashReceiver } from "@upstash/qstash";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { Search } from "@upstash/search";
import { XMLParser } from "fast-xml-parser";
import { createServer as createViteServer } from "vite";
import { WebSocket, WebSocketServer } from "ws";
import type {
  ArchiveEntry,
  ArchiveRecord,
  BackendProductEvent,
  BackendTruthSummary,
  BootstrapPayload,
  CanonicalPlanTemplate,
  Committee,
  CommitteeAuthorityLevel,
  CommitteeVote,
  CompiledArtifact,
  CompiledArtifactPhaseOutput,
  CompiledArtifactReference,
  ControlTelemetry,
  EscalationRule,
  EventItem,
  GovernanceProposal,
  GovernanceRegistry,
  GovernedRun,
  EnterpriseCheckView,
  EnterpriseCouncilView,
  PlanRegistryProof,
  OperatorCommittee,
  OperatorCommitteeRuntimeView,
  ModelProviderId,
  ModelProviderSnapshot,
  ModelProviderStatus,
  OutboundContact,
  OutboundMessage,
  OutboundRuntimeSnapshot,
  OperatorRun,
  OperatorWorker,
  Pillar,
  ResearchSignal,
  ResearchSourceStatus,
  RiskTier,
  RunStageRecord,
  SkillArtifact,
  StatusPageSnapshot,
  SunnyvaleInternalSnapshot,
  SunnyvaleOverview,
  SurfaceId,
  WorkerRuntimeState,
  WorkflowArtifact,
  InstitutionalPlan,
  CommandCenterSnapshot,
  CommercialArtifact,
  CommercialScorecard,
  OperatingSignal,
  ReplayRequest,
  ReplayResult,
  RoutedIntentResult,
  WorkerLastRunResult,
  WorkerRegistryRecord,
  WorkerRegistryStatus,
  WorkerRegistryValidation,
} from "./src/types";
import type {
  FounderReviewStatus,
  RegistryRouteStage,
  SkillBinding,
  V3Committee,
  V3DecisionStatus,
  V3Event,
  V3Plan,
  V3Run,
  VeklomPillar,
  VeklomPillarId,
  WorkerArchetype,
  WorkerRegistryEntry,
} from "./src/types";

const PORT = Number(process.env.PORT || 3000);
const TOOL_NAME = "uacpv3-control-plane";
const CONTACT_EMAIL = process.env.CONTACT_EMAIL || process.env.USER_EMAIL || "founder@uacp.local";
const DATA_DIR = process.env.DATA_DIR || path.join(process.cwd(), "data");
const COLD_STORAGE_DIR = process.env.UACP_COLD_STORAGE_DIR || path.join(DATA_DIR, "cold-store");
const STATE_FILE = path.join(DATA_DIR, "control-plane-state.json");
const REGISTRY_FILE = path.join(DATA_DIR, "governance-registry.json");
const STATE_SNAPSHOT_FILE = path.join(COLD_STORAGE_DIR, "runtime-state.snapshot.json.gz");
const REGISTRY_SNAPSHOT_FILE = path.join(COLD_STORAGE_DIR, "governance-registry.snapshot.json.gz");
const CONTROL_PLANE_BOOTED_AT = Date.now();
const ADMIN_API_KEY = process.env.UACP_ADMIN_KEY || "";
const INTERNAL_API_KEY = process.env.UACP_INTERNAL_API_KEY || ADMIN_API_KEY;
const BOX_NAME = process.env.UACP_BOX_NAME || TOOL_NAME;
const RUNTIME_MODE = process.env.UACP_RUNTIME_MODE || "control_plane";
const WORKER_GROUP = process.env.UACP_WORKER_GROUP || "control_plane";
const ARCHIVE_WRITE_REQUIRED = /^(1|true|yes|on)$/i.test(process.env.UACP_ARCHIVE_WRITE_REQUIRED || "");
const UACP_BACKEND_BASE_URL = String(process.env.UACP_BACKEND_BASE_URL || process.env.UACP_BACKEND_URL || "").trim().replace(/\/+$/, "");
const UACP_BACKEND_TIMEOUT_MS = Math.max(2000, Number(process.env.UACP_BACKEND_TIMEOUT_MS || 8000) || 8000);
const UACP_SCHEDULER_MAX_RELEASE_PER_TICK = Math.max(1, Number(process.env.UACP_SCHEDULER_MAX_RELEASE_PER_TICK || 3) || 3);
const UACP_SCHEDULER_MIN_STAGGER_MINUTES = Math.max(1, Number(process.env.UACP_SCHEDULER_MIN_STAGGER_MINUTES || 2) || 2);
const RESEND_API_KEY = process.env.RESEND_API_KEY || "";
const RESEND_FROM_EMAIL = process.env.RESEND_FROM_EMAIL || "";
const UACP_OUTBOUND_REPLY_TO = process.env.UACP_OUTBOUND_REPLY_TO || "";
const UACP_OUTBOUND_MAX_SENDS_PER_RUN = Math.max(1, Number(process.env.UACP_OUTBOUND_MAX_SENDS_PER_RUN || 2) || 2);
const DATABASE_URL = process.env.DATABASE_URL || "";
const DATABASE_SSL_MODE = (process.env.DATABASE_SSL_MODE || "require").trim().toLowerCase();
const UPSTASH_REDIS_REST_URL = process.env.UPSTASH_REDIS_REST_URL || "";
const UPSTASH_REDIS_REST_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || "";
const QSTASH_URL = (process.env.QSTASH_URL || "https://qstash.upstash.io").replace(/\/+$/, "");
const QSTASH_TOKEN = process.env.QSTASH_TOKEN || "";
const QSTASH_CURRENT_SIGNING_KEY = process.env.QSTASH_CURRENT_SIGNING_KEY || "";
const QSTASH_NEXT_SIGNING_KEY = process.env.QSTASH_NEXT_SIGNING_KEY || "";
const UACP_PUBLIC_BASE_URL = (process.env.UACP_PUBLIC_BASE_URL || "").replace(/\/+$/, "");
const UACP_QSTASH_CONVEYOR_CRON = process.env.UACP_QSTASH_CONVEYOR_CRON || "*/5 * * * *";
const UACP_QSTASH_CONVEYOR_SCHEDULE_ID = process.env.UACP_QSTASH_CONVEYOR_SCHEDULE_ID || "uacp-v3-worker-conveyor";
const UACP_QSTASH_QUEUE_NAME = process.env.UACP_QSTASH_QUEUE_NAME || "uacp-worker-conveyor";
const UPSTASH_SEARCH_REST_URL = process.env.UPSTASH_SEARCH_REST_URL || "";
const UPSTASH_SEARCH_REST_TOKEN = process.env.UPSTASH_SEARCH_REST_TOKEN || "";
const UACP_SEARCH_INDEX = process.env.UACP_SEARCH_INDEX || "default";
const RATE_LIMIT_TRUST_ACCESS_TIER_HEADER = /^(1|true|yes|on)$/i.test(
  process.env.UACP_RATE_LIMIT_TRUST_ACCESS_TIER_HEADER || "",
);
const GROQ_BASE_URL = (process.env.GROQ_BASE_URL || "https://api.groq.com/openai/v1").replace(/\/+$/, "");
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
const HF_BASE_URL = (process.env.HF_BASE_URL || "https://router.huggingface.co/v1").replace(/\/+$/, "");
const HF_TOKEN = process.env.HF_TOKEN || process.env.HUGGING_FACE_HUB_TOKEN || process.env.HUGGINGFACE_API_KEY || "";
const HF_MODEL = process.env.HF_MODEL || "openai/gpt-oss-120b";
const OLLAMA_BASE_URL = (process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434").replace(/\/+$/, "");
const OLLAMA_API_KEY = process.env.OLLAMA_API_KEY || "";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "";
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";
const { Pool } = pg;
const workerGroupBlueprints: WorkerGroupBlueprint[] = [
  {
    id: "pillar_council",
    label: "Pillar Council",
    runtimeMode: "pillar_council",
    boxRole: "hot",
    workerIds: ["gauge", "ledger", "sentinel", "mirror", "pulse", "sheriff", "polish", "oracle", "glide"],
    wakeTriggers: ["minimum-live cadence", "governance pressure", "truth drift", "freshness decay"],
    handoffTargets: ["growth_sales", "operations_intake", "builder_systems", "vendor_network"],
  },
  {
    id: "growth_sales",
    label: "Growth & Sales",
    runtimeMode: "growth_sales",
    boxRole: "warm",
    workerIds: ["signal", "mint", "scout", "spyglass", "raider", "welcome"],
    wakeTriggers: ["qualified pipeline pressure", "campaign backlog", "outbound queue", "competitor movement"],
    handoffTargets: ["pillar_council", "operations_intake", "vendor_network"],
  },
  {
    id: "operations_intake",
    label: "Operations & Intake",
    runtimeMode: "operations_intake",
    boxRole: "warm",
    workerIds: ["herald", "harvest", "bouncer", "arbiter"],
    wakeTriggers: ["intake backlog", "backend events", "admission queue pressure", "routing exceptions"],
    handoffTargets: ["pillar_council", "growth_sales", "builder_systems"],
  },
  {
    id: "builder_systems",
    label: "Builder Systems",
    runtimeMode: "builder_systems",
    boxRole: "warm",
    workerIds: ["builder-scout", "builder-forge", "builder-arbiter"],
    wakeTriggers: ["build backlog", "tool gap accepted", "automation expansion", "delivery blockers"],
    handoffTargets: ["pillar_council", "operations_intake"],
  },
  {
    id: "vendor_network",
    label: "Vendor Network",
    runtimeMode: "vendor_network",
    boxRole: "warm",
    workerIds: ["vendor-scout", "vendor-recruiter", "vendor-auditor"],
    wakeTriggers: ["partner queue", "vendor qualification demand", "channel expansion", "affiliate routing"],
    handoffTargets: ["pillar_council", "growth_sales", "operations_intake"],
  },
];
const REQUESTED_MODEL_PROVIDER = String(process.env.UACP_MODEL_PROVIDER || "").toLowerCase();
const GEMINI_PRIMARY_ENABLED = process.env.UACP_ENABLE_GEMINI_PRIMARY === "true";
const ALLOW_GEMINI_FALLBACK = process.env.ALLOW_GEMINI_FALLBACK === "true";
const MODEL_PROVIDER_ORDER = parseProviderOrder(
  process.env.UACP_MODEL_PROVIDER_ORDER ||
    (GEMINI_PRIMARY_ENABLED ? "groq,ollama,huggingface,gemini" : "groq,ollama,huggingface"),
);
const MAX_EVENTS = 120;
const MAX_ARCHIVES = 80;
const MAX_SIGNALS = 40;
const MAX_BACKEND_EVENTS = 200;
const MAX_OPERATOR_RUNS = 240;
const HISTORY_WINDOW = 25;
const RESEARCH_REFRESH_INTERVAL_MS = 1000 * 60 * 15;
const OPERATOR_TICK_INTERVAL_MS = 1000 * 60;
const DEFAULT_RESEARCH_QUERY =
  process.env.DEFAULT_RESEARCH_QUERY ||
  "ai governance orchestration workflow observability api mcp deployment compliance";
const CORE_RESEARCH_ANCHORS = [
  "ai",
  "agent",
  "agents",
  "llm",
  "model",
  "orchestration",
  "workflow",
  "governance",
  "observability",
  "automation",
  "api",
  "sdk",
  "cli",
  "mcp",
  "deployment",
  "compliance",
  "privacy",
  "security",
  "audit",
];
const GENERAL_AI_RESEARCH_ANCHORS = [
  "ai",
  "agent",
  "agents",
  "llm",
  "model",
  "automation",
];
const CONTROL_PLANE_RESEARCH_ANCHORS = [
  "orchestration",
  "workflow",
  "governance",
  "observability",
  "automation",
  "api",
  "sdk",
  "cli",
  "mcp",
  "deployment",
  "compliance",
  "privacy",
  "security",
  "audit",
];
const CORE_RESEARCH_PHRASES = [
  "control plane",
  "ai agent",
  "agentic workflow",
  "multi agent",
  "workflow orchestration",
  "policy enforcement",
  "model context protocol",
  "api integration",
  "software deployment",
  "enterprise ai",
  "evaluation workflow",
];
const HEALTH_RESEARCH_TERMS = [
  "medical",
  "clinical",
  "patient",
  "therapy",
  "drug",
  "diagnosis",
  "hospital",
  "biomedical",
  "hipaa",
  "pubmed",
  "medrxiv",
  "health",
];

const ai = process.env.GEMINI_API_KEY ? new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY }) : null;
const parser = new XMLParser({ ignoreAttributes: false });

type RateLimitTier = "free" | "paid";
type RateLimitProfile = "public_mutation" | "heavy_mutation" | "refresh";
type RateLimitWindow = Parameters<typeof Ratelimit.slidingWindow>[1];
type RateLimitStatus = {
  enabled: boolean;
  provider: "upstash-redis" | "disabled";
  trustTierHeader: boolean;
  initError: string | null;
  profiles: Record<RateLimitProfile, { free: { limit: number; window: RateLimitWindow }; paid: { limit: number; window: RateLimitWindow } }>;
};

type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type RemoteSunnyvaleSummaryEnvelope = Record<string, unknown> & {
  sunnyvale?: Record<string, unknown>;
};

type ProviderTextResponse = {
  provider: ModelProviderId;
  model: string;
  text: string;
};

type ProviderPromptOptions = {
  jsonMode?: boolean;
  maxTokens?: number;
  temperature?: number;
};

let providerSnapshotCache:
  | {
      snapshot: ModelProviderSnapshot;
      fetchedAt: number;
    }
  | undefined;

const rateLimitProfiles = {
  public_mutation: {
    free: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_PUBLIC_FREE_LIMIT, 10),
      window: (process.env.UACP_RATE_LIMIT_PUBLIC_FREE_WINDOW || "10 s") as RateLimitWindow,
      prefix: "ratelimit:public:free",
    },
    paid: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_PUBLIC_PAID_LIMIT, 60),
      window: (process.env.UACP_RATE_LIMIT_PUBLIC_PAID_WINDOW || "10 s") as RateLimitWindow,
      prefix: "ratelimit:public:paid",
    },
  },
  heavy_mutation: {
    free: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_HEAVY_FREE_LIMIT, 3),
      window: (process.env.UACP_RATE_LIMIT_HEAVY_FREE_WINDOW || "1 m") as RateLimitWindow,
      prefix: "ratelimit:heavy:free",
    },
    paid: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_HEAVY_PAID_LIMIT, 20),
      window: (process.env.UACP_RATE_LIMIT_HEAVY_PAID_WINDOW || "1 m") as RateLimitWindow,
      prefix: "ratelimit:heavy:paid",
    },
  },
  refresh: {
    free: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_REFRESH_FREE_LIMIT, 2),
      window: (process.env.UACP_RATE_LIMIT_REFRESH_FREE_WINDOW || "1 m") as RateLimitWindow,
      prefix: "ratelimit:refresh:free",
    },
    paid: {
      limit: parsePositiveIntegerEnv(process.env.UACP_RATE_LIMIT_REFRESH_PAID_LIMIT, 12),
      window: (process.env.UACP_RATE_LIMIT_REFRESH_PAID_WINDOW || "1 m") as RateLimitWindow,
      prefix: "ratelimit:refresh:paid",
    },
  },
} satisfies Record<RateLimitProfile, Record<RateLimitTier, { limit: number; window: string; prefix: string }>>;

const rateLimitRuntime = initializeRateLimitRuntime();
const qstashClient = QSTASH_TOKEN ? new QStashClient({ token: QSTASH_TOKEN, baseUrl: QSTASH_URL }) : null;
const qstashReceiver = QSTASH_CURRENT_SIGNING_KEY && QSTASH_NEXT_SIGNING_KEY
  ? new QStashReceiver({ currentSigningKey: QSTASH_CURRENT_SIGNING_KEY, nextSigningKey: QSTASH_NEXT_SIGNING_KEY })
  : null;
const searchClient = UPSTASH_SEARCH_REST_URL && UPSTASH_SEARCH_REST_TOKEN
  ? new Search({ url: UPSTASH_SEARCH_REST_URL, token: UPSTASH_SEARCH_REST_TOKEN })
  : null;

function getSearchIndex(indexName = UACP_SEARCH_INDEX) {
  return searchClient?.index<Record<string, unknown>, Record<string, unknown>>(indexName) || null;
}

const surfaces: BootstrapPayload["surfaces"] = [
  { id: "deterministic-engine", name: "Deterministic Engine", purpose: "Live signal intake, graph compilation, and run telemetry." },
  { id: "sunnyvale", name: "Sunnyvale", purpose: "Execution floor for approvals, runs, workers, and workflows." },
  { id: "silicon-valley", name: "Silicon Valley", purpose: "Founder control console for governance, risk, and source health." },
  { id: "archives", name: "Archives", purpose: "Replayable evidence, compiled artifacts, and ordered event memory." },
  { id: "status", name: "Status", purpose: "Observed uptime, incident history, and proof-backed operational metrics." },
];

const defaultGovernanceRegistry: GovernanceRegistry = {
  version: "1.1.0",
  updatedAt: "2026-05-09T00:00:00.000Z",
  updatedBy: "control-plane-ops",
  pillars: [
    { id: "governance", name: "Governance", mandate: "Keep the institution constitutional and replayable.", kpi: "Policy SLA" },
    { id: "product", name: "Product", mandate: "Translate institutional objectives into offers and UX.", kpi: "Activation rate" },
    { id: "engineering", name: "Engineering", mandate: "Ship reliable execution systems and control-plane primitives.", kpi: "Deployment quality" },
    { id: "growth", name: "Growth", mandate: "Acquire demand and compound distribution.", kpi: "Qualified pipeline" },
    { id: "sales", name: "Sales", mandate: "Convert pipeline into retained revenue.", kpi: "Closed ARR" },
    { id: "operations", name: "Operations", mandate: "Run queues, approvals, service delivery, and worker throughput.", kpi: "Cycle time" },
    { id: "finance", name: "Finance", mandate: "Protect margin, billing, and capital allocation.", kpi: "Gross margin" },
    { id: "compliance-risk", name: "Compliance / Risk", mandate: "Constrain execution by law, policy, and exposure.", kpi: "Risk incidents" },
    { id: "knowledge-research", name: "Knowledge / Research", mandate: "Turn public signals into institutional edge.", kpi: "Signal-to-shipment ratio" },
  ],
  committees: [
    {
      id: "founder-council",
      name: "Founder Council",
      purpose: "Final approval, veto, and escalation authority.",
      authority: "constitutional",
      chair: "UACP V3",
      members: ["UACP V3", "Policy Steward", "Revenue Operator"],
      escalation: "Direct founder override",
      allowedActions: ["approve_plans", "veto_runs", "reassign_committees"],
      vetoConditions: ["regulatory breach", "margin-negative execution", "missing research evidence"],
      pillarIds: ["governance", "finance", "compliance-risk"],
    },
    {
      id: "signal-council",
      name: "Signal Council",
      purpose: "Convert live research and market signals into opportunities and operating pressure.",
      authority: "advisory",
      chair: "Research Director",
      members: ["Research Scout", "Competitor Analyst", "Model Council Chair"],
      escalation: "Founder Council",
      allowedActions: ["publish_briefs", "recommend_targets", "open_investigations"],
      vetoConditions: ["no live sources", "low-evidence thesis"],
      pillarIds: ["knowledge-research", "growth", "product"],
    },
    {
      id: "execution-board",
      name: "Execution Board",
      purpose: "Route approved work into governed runs and service delivery.",
      authority: "operational",
      chair: "Operations Marshal",
      members: ["Workflow Captain", "Engineering Lead", "Revenue Operator"],
      escalation: "Founder Council",
      allowedActions: ["queue_runs", "assign_skills", "open_approvals"],
      vetoConditions: ["unapproved skill usage", "missing archive evidence"],
      pillarIds: ["operations", "engineering", "sales"],
    },
  ],
  skills: [
    {
      id: "marketing-competitive-analysis",
      name: "marketing-competitive-analysis",
      category: "skill",
      description: "Research competitors and expose positioning, workflow, and execution gaps using public evidence.",
      allowedTools: ["read", "browser"],
      source: "internal-registry/market-systems",
      ref: "v1.4.0",
      treeSha: "sha-9d8c1f1",
      status: "approved",
      pillarIds: ["growth", "knowledge-research"],
    },
    {
      id: "sales-call-prep",
      name: "sales-call-prep",
      category: "skill",
      description: "Prepare operator-grade account context, call strategy, and objection handling.",
      allowedTools: ["read", "browser", "write"],
      source: "internal-registry/revenue-systems",
      ref: "v2.0.1",
      treeSha: "sha-4ac77aa",
      status: "approved",
      pillarIds: ["sales", "growth"],
    },
    {
      id: "legal-compliance",
      name: "legal-compliance",
      category: "skill",
      description: "Constrain privacy, regulatory, and data subject workflows before execution.",
      allowedTools: ["read", "write"],
      source: "internal-registry/risk-systems",
      ref: "v1.9.3",
      treeSha: "sha-c13f9b2",
      status: "approved",
      pillarIds: ["compliance-risk", "governance"],
    },
    {
      id: "finance-audit-support",
      name: "finance-audit-support",
      category: "skill",
      description: "Support audit evidence, revenue control checks, and operating reviews.",
      allowedTools: ["read", "write"],
      source: "internal-registry/finance-systems",
      ref: "v1.1.8",
      treeSha: "sha-f82a11d",
      status: "review",
      pillarIds: ["finance", "governance"],
    },
  ],
  workflows: [
    {
      id: "competitive-intelligence",
      name: "Competitive intelligence",
      category: "workflow",
      description: "Monitor launches, pricing shifts, and partnership signals with live public-source evidence.",
      outcome: "Competitor weakness map",
      pillarIds: ["growth", "knowledge-research"],
    },
    {
      id: "model-council",
      name: "Model council",
      category: "workflow",
      description: "Run multi-model or deterministic council deliberation and capture convergence or dissent.",
      outcome: "Committee vote packet",
      pillarIds: ["governance", "knowledge-research"],
    },
    {
      id: "product-teardown",
      name: "Product teardown",
      category: "workflow",
      description: "Capture pricing, onboarding, feature gaps, and UX weaknesses from public artifacts.",
      outcome: "Actionable disruption brief",
      pillarIds: ["product", "growth", "sales"],
    },
    {
      id: "competitor-raid",
      name: "Competitor raid",
      category: "workflow",
      description: "Turn competitor launches, pricing gaps, and workflow failures into attack plans and counter-positioning packets.",
      outcome: "Competitive attack brief",
      pillarIds: ["growth", "sales", "knowledge-research", "product"],
    },
    {
      id: "vendor-recruitment",
      name: "Vendor recruitment",
      category: "workflow",
      description: "Source, qualify, and activate vendors, affiliates, and integration partners under governed outreach and screening rules.",
      outcome: "Vendor pipeline packet",
      pillarIds: ["growth", "sales", "operations", "compliance-risk"],
    },
  ],
  escalationRules: [
    {
      id: "missing-live-evidence",
      name: "Missing live evidence",
      description: "Escalate when a plan or run reaches governance without attributable live research.",
      trigger: "No live research references are attached to the plan or run.",
      route: ["signal-council", "founder-council"],
      severity: "high",
      ownerCommitteeId: "founder-council",
      pillarIds: ["governance", "knowledge-research", "compliance-risk"],
    },
    {
      id: "unapproved-skill-attempt",
      name: "Unapproved skill attempt",
      description: "Escalate when execution requires a skill that is not approved in the registry.",
      trigger: "A governed run requests a skill outside the approved registry set.",
      route: ["execution-board", "founder-council"],
      severity: "critical",
      ownerCommitteeId: "execution-board",
      pillarIds: ["operations", "engineering", "governance"],
    },
    {
      id: "regulated-objective-review",
      name: "Regulated objective review",
      description: "Escalate regulated, privacy, or compliance-heavy objectives through explicit founder review.",
      trigger: "The intent or evidence indicates regulated, privacy, legal, or compliance-sensitive work.",
      route: ["founder-council"],
      severity: "high",
      ownerCommitteeId: "founder-council",
      pillarIds: ["compliance-risk", "governance", "sales"],
    },
  ],
  operatorCommittees: [
    {
      id: "marketplace-operations",
      name: "Marketplace Operations",
      purpose: "Run marketplace health, intake, routing, and operational arbitration.",
      pillarIds: ["operations", "sales", "finance"],
      workerIds: ["herald", "harvest", "bouncer", "gauge", "arbiter"],
      chair: "Operations Marshal",
      sponsor: "Founder Council",
      decisionFramework: "RAPID",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Cycle time", "Qualified pipeline", "Gross margin"],
    },
    {
      id: "governance-evidence",
      name: "Governance & Evidence",
      purpose: "Protect evidence integrity, policy judgment, and escalation discipline.",
      pillarIds: ["governance", "finance", "compliance-risk", "knowledge-research"],
      workerIds: ["ledger", "oracle", "builder-arbiter", "sheriff"],
      chair: "Policy Steward",
      sponsor: "Founder Council",
      decisionFramework: "RAPID",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Policy SLA", "Risk incidents", "Signal-to-shipment ratio"],
    },
    {
      id: "growth-intelligence",
      name: "Growth & Intelligence",
      purpose: "Convert public signals and buyer motion into governed growth actions.",
      pillarIds: ["growth", "sales", "knowledge-research"],
      workerIds: ["signal", "scout", "spyglass", "raider", "mint", "welcome"],
      chair: "Revenue Operator",
      sponsor: "Founder Council",
      decisionFramework: "RAPID",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Qualified pipeline", "Closed ARR", "Signal-to-shipment ratio"],
    },
    {
      id: "builder-systems",
      name: "Builder Systems",
      purpose: "Discover, shape, and forge builder opportunities without bypassing governance.",
      pillarIds: ["engineering", "product", "knowledge-research"],
      workerIds: ["builder-scout", "builder-forge", "builder-arbiter"],
      chair: "Engineering Lead",
      sponsor: "Execution Board",
      decisionFramework: "DACI",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Deployment quality", "Activation rate", "Signal-to-shipment ratio"],
    },
    {
      id: "experience-assurance",
      name: "Experience Assurance",
      purpose: "Keep the product experience truthful, fresh, and regression-resistant.",
      pillarIds: ["product", "operations", "compliance-risk"],
      workerIds: ["sentinel", "mirror", "polish", "glide", "pulse", "sheriff", "welcome"],
      chair: "Experience Lead",
      sponsor: "Execution Board",
      decisionFramework: "RACI",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Activation rate", "Cycle time", "Risk incidents"],
    },
    {
      id: "vendor-network",
      name: "Vendor Network",
      purpose: "Source, recruit, qualify, and activate external vendors, affiliates, and distribution partners.",
      pillarIds: ["growth", "sales", "operations", "compliance-risk", "finance"],
      workerIds: ["vendor-scout", "vendor-recruiter", "vendor-auditor"],
      chair: "Channel Lead",
      sponsor: "Founder Council",
      decisionFramework: "DACI",
      cadencePerDay: 3,
      regroupIntervalMinutes: 480,
      successMetrics: ["Qualified pipeline", "Closed ARR", "Gross margin"],
    },
  ],
  workers: [
    {
      id: "herald",
      displayName: "Herald",
      committeeId: "marketplace-operations",
      primaryPillar: "operations",
      secondaryPillars: ["sales"],
      purpose: "Announce, route, and log incoming marketplace actions and operator-facing triggers.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["events", "archives", "research-signals"],
      allowedActions: ["route_notifications", "write_run_digest", "open_escalation"],
      forbiddenActions: ["modify_registry", "approve_payouts"],
      outputArtifact: "marketplace-intake-digest",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "next_run", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "harvest",
      displayName: "Harvest",
      committeeId: "marketplace-operations",
      primaryPillar: "operations",
      secondaryPillars: ["growth"],
      purpose: "Collect live demand, inventory, and signal opportunities into governed execution queues.",
      schedule: "Every 30 minutes",
      intervalMinutes: 30,
      inputSources: ["research-signals", "telemetry", "events"],
      allowedActions: ["collect_signals", "score_queue_pressure", "write_ops_digest"],
      forbiddenActions: ["bypass_committee_review"],
      outputArtifact: "harvest-queue-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "queue_pressure"],
      requiredSecrets: []
    },
    {
      id: "bouncer",
      displayName: "Bouncer",
      committeeId: "marketplace-operations",
      primaryPillar: "compliance-risk",
      secondaryPillars: ["operations"],
      purpose: "Gate unsafe or out-of-policy actions before they enter the live execution floor.",
      schedule: "Every 10 minutes",
      intervalMinutes: 10,
      inputSources: ["events", "runs", "telemetry"],
      allowedActions: ["deny_unsafe_admission", "flag_policy_mismatch", "write_gate_report"],
      forbiddenActions: ["override_founder_veto"],
      outputArtifact: "admission-gate-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "blocked_actions"],
      requiredSecrets: []
    },
    {
      id: "gauge",
      displayName: "Gauge",
      committeeId: "marketplace-operations",
      primaryPillar: "operations",
      secondaryPillars: ["finance", "growth"],
      purpose: "Track operating telemetry, route health, conversion, and usage drift.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["telemetry", "observability", "runs"],
      allowedActions: ["write_telemetry_snapshot", "flag_metric_anomaly", "recommend_followup"],
      forbiddenActions: ["change_metrics_history"],
      outputArtifact: "telemetry-digest",
      archiveEventType: "telemetry_snapshot_written",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "last_snapshot", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "ledger",
      displayName: "Ledger",
      committeeId: "governance-evidence",
      primaryPillar: "governance",
      secondaryPillars: ["finance", "compliance-risk"],
      purpose: "Protect evidence truth, archive integrity, and traceability across runs.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["archives", "runs", "events"],
      allowedActions: ["verify_archive_lineage", "write_evidence_report", "flag_missing_evidence"],
      forbiddenActions: ["delete_archive_records"],
      outputArtifact: "evidence-integrity-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "archive_coverage"],
      requiredSecrets: []
    },
    {
      id: "signal",
      displayName: "Signal",
      committeeId: "growth-intelligence",
      primaryPillar: "growth",
      secondaryPillars: ["knowledge-research"],
      purpose: "Turn live public-source evidence into actionable market pressure summaries.",
      schedule: "Every 30 minutes",
      intervalMinutes: 30,
      inputSources: ["research-signals", "research-status"],
      allowedActions: ["summarize_signal_pressure", "rank_opportunities", "write_growth_brief"],
      forbiddenActions: ["invent_sources"],
      outputArtifact: "signal-pressure-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "signal_count"],
      requiredSecrets: []
    },
    {
      id: "oracle",
      displayName: "Oracle",
      committeeId: "governance-evidence",
      primaryPillar: "knowledge-research",
      secondaryPillars: ["governance"],
      purpose: "Interpret live evidence into governance-ready judgment packets.",
      schedule: "Hourly",
      intervalMinutes: 60,
      inputSources: ["research-signals", "plans", "archives"],
      allowedActions: ["write_council_brief", "surface_uncertainty", "recommend_escalation"],
      forbiddenActions: ["self-approve_governance"],
      outputArtifact: "council-judgment-packet",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "brief_count"],
      requiredSecrets: []
    },
    {
      id: "mint",
      displayName: "Mint",
      committeeId: "growth-intelligence",
      primaryPillar: "finance",
      secondaryPillars: ["growth", "sales"],
      purpose: "Translate demand and workflow pressure into monetization and pricing recommendations.",
      schedule: "Hourly",
      intervalMinutes: 60,
      inputSources: ["telemetry", "plans", "research-signals"],
      allowedActions: ["write_pricing_digest", "flag_margin_risk", "recommend_offer_changes"],
      forbiddenActions: ["execute_billing_changes"],
      outputArtifact: "monetization-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "pricing_pressure"],
      requiredSecrets: []
    },
    {
      id: "scout",
      displayName: "Scout",
      committeeId: "growth-intelligence",
      primaryPillar: "knowledge-research",
      secondaryPillars: ["growth"],
      purpose: "Search for competitor weakness, broken workflows, and opportunity gaps.",
      schedule: "Every 45 minutes",
      intervalMinutes: 45,
      inputSources: ["research-signals", "events", "archives"],
      allowedActions: ["scan_opportunities", "write_gap_map", "recommend_builder_targets"],
      forbiddenActions: ["copy_external_products"],
      outputArtifact: "gap-map",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "gap_count"],
      requiredSecrets: []
    },
    {
      id: "spyglass",
      displayName: "Spyglass",
      committeeId: "growth-intelligence",
      primaryPillar: "knowledge-research",
      secondaryPillars: ["growth", "sales"],
      purpose: "Track competitor launches, pricing moves, distribution changes, and weak surfaces that can be attacked.",
      schedule: "Every 30 minutes",
      intervalMinutes: 30,
      inputSources: ["research-signals", "archives", "events"],
      allowedActions: ["monitor_competitors", "write_competitor_dossier", "flag_attack_surface"],
      forbiddenActions: ["invent_competitor_claims"],
      outputArtifact: "competitor-dossier",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "competitor_count"],
      requiredSecrets: []
    },
    {
      id: "raider",
      displayName: "Raider",
      committeeId: "growth-intelligence",
      primaryPillar: "growth",
      secondaryPillars: ["sales", "product"],
      purpose: "Convert competitor weaknesses into campaigns, offer attacks, and counter-positioning packets.",
      schedule: "Hourly",
      intervalMinutes: 60,
      inputSources: ["research-signals", "plans", "archives"],
      allowedActions: ["write_attack_brief", "rank_counter_moves", "route_counter_positioning"],
      forbiddenActions: ["launch_unapproved_campaigns"],
      outputArtifact: "competitive-attack-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "attack_vectors"],
      requiredSecrets: []
    },
    {
      id: "arbiter",
      displayName: "Arbiter",
      committeeId: "marketplace-operations",
      primaryPillar: "governance",
      secondaryPillars: ["operations"],
      purpose: "Resolve conflicts in marketplace routing and adjudicate queue priorities.",
      schedule: "Every 30 minutes",
      intervalMinutes: 30,
      inputSources: ["plans", "runs", "events"],
      allowedActions: ["rank_queue_priority", "write_adjudication_note", "open_escalation"],
      forbiddenActions: ["edit_registry_without_admin"],
      outputArtifact: "queue-adjudication-note",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "pending_conflicts"],
      requiredSecrets: []
    },
    {
      id: "builder-scout",
      displayName: "Builder Scout",
      committeeId: "builder-systems",
      primaryPillar: "knowledge-research",
      secondaryPillars: ["engineering", "product"],
      purpose: "Locate builder opportunities that can become original tools or repair kits.",
      schedule: "Every 90 minutes",
      intervalMinutes: 90,
      inputSources: ["research-signals", "archives", "plans"],
      allowedActions: ["open_builder_opportunity", "write_clean_room_brief", "recommend_scope"],
      forbiddenActions: ["clone_external_repos"],
      outputArtifact: "builder-opportunity-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "opportunity_count"],
      requiredSecrets: []
    },
    {
      id: "builder-forge",
      displayName: "Builder Forge",
      committeeId: "builder-systems",
      primaryPillar: "engineering",
      secondaryPillars: ["product"],
      purpose: "Turn approved builder opportunities into governed implementation packets.",
      schedule: "Every 120 minutes",
      intervalMinutes: 120,
      inputSources: ["plans", "archives", "events"],
      allowedActions: ["prepare_build_spec", "write_acceptance_packet", "flag_missing_dependencies"],
      forbiddenActions: ["ship_without_approval"],
      outputArtifact: "builder-implementation-packet",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "unapproved-skill-attempt",
      statusFields: ["status", "last_run", "active_specs"],
      requiredSecrets: []
    },
    {
      id: "builder-arbiter",
      displayName: "Builder Arbiter",
      committeeId: "governance-evidence",
      primaryPillar: "governance",
      secondaryPillars: ["engineering", "knowledge-research"],
      purpose: "Judge builder proposals for legal, policy, and operational admissibility.",
      schedule: "Every 90 minutes",
      intervalMinutes: 90,
      inputSources: ["plans", "archives", "research-signals"],
      allowedActions: ["approve_builder_route", "deny_builder_route", "write_builder_decision"],
      forbiddenActions: ["implement_code_changes"],
      outputArtifact: "builder-decision-record",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "builder_decisions"],
      requiredSecrets: []
    },
    {
      id: "sentinel",
      displayName: "Sentinel",
      committeeId: "experience-assurance",
      primaryPillar: "product",
      secondaryPillars: ["operations"],
      purpose: "Watch end-to-end product uptime and execution path health.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["telemetry", "events", "runs"],
      allowedActions: ["verify_route_health", "write_uptime_report", "escalate_outage"],
      forbiddenActions: ["mask_failures"],
      outputArtifact: "uptime-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "route_health", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "mirror",
      displayName: "Mirror",
      committeeId: "experience-assurance",
      primaryPillar: "product",
      secondaryPillars: ["engineering"],
      purpose: "Compare UI truth against backend truth and expose drift.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["telemetry", "observability", "archives"],
      allowedActions: ["compare_surface_truth", "write_drift_report", "flag_mismatch"],
      forbiddenActions: ["rewrite_archives"],
      outputArtifact: "truth-drift-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "drift_count", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "polish",
      displayName: "Polish",
      committeeId: "experience-assurance",
      primaryPillar: "product",
      secondaryPillars: ["sales"],
      purpose: "Guard product quality, clarity, and finish in customer-facing flows.",
      schedule: "Hourly",
      intervalMinutes: 60,
      inputSources: ["plans", "archives", "events"],
      allowedActions: ["write_quality_report", "flag_clutter", "recommend_copy_fix"],
      forbiddenActions: ["deploy_unreviewed_ui"],
      outputArtifact: "quality-pass-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "quality_findings", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "glide",
      displayName: "Glide",
      committeeId: "experience-assurance",
      primaryPillar: "product",
      secondaryPillars: ["sales"],
      purpose: "Inspect onboarding and user motion for friction and conversion drag.",
      schedule: "Every 45 minutes",
      intervalMinutes: 45,
      inputSources: ["telemetry", "plans", "research-signals"],
      allowedActions: ["write_onboarding_report", "flag_friction", "recommend_flow_change"],
      forbiddenActions: ["alter_conversion_data"],
      outputArtifact: "flow-friction-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "friction_count"],
      requiredSecrets: []
    },
    {
      id: "pulse",
      displayName: "Pulse",
      committeeId: "experience-assurance",
      primaryPillar: "operations",
      secondaryPillars: ["product"],
      purpose: "Keep live command panels, telemetry cards, and freshness indicators honest.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["telemetry", "events", "observability"],
      allowedActions: ["measure_panel_freshness", "write_staleness_report", "flag_stale_surface"],
      forbiddenActions: ["fabricate_refreshes"],
      outputArtifact: "panel-freshness-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "freshness_state", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "sheriff",
      displayName: "Sheriff",
      committeeId: "governance-evidence",
      primaryPillar: "compliance-risk",
      secondaryPillars: ["product", "governance"],
      purpose: "Catch regressions, unsafe drift, and policy violations before they compound.",
      schedule: "Every 15 minutes",
      intervalMinutes: 15,
      inputSources: ["runs", "events", "telemetry", "archives"],
      allowedActions: ["flag_regression", "write_incident_report", "open_escalation"],
      forbiddenActions: ["suppress_policy_findings"],
      outputArtifact: "regression-watch-report",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "regression_count", "heartbeat"],
      requiredSecrets: []
    },
    {
      id: "welcome",
      displayName: "Welcome",
      committeeId: "growth-intelligence",
      primaryPillar: "sales",
      secondaryPillars: ["growth", "product"],
      purpose: "Own first-contact clarity, evaluator entry paths, and guided next actions.",
      schedule: "Every 30 minutes",
      intervalMinutes: 30,
      inputSources: ["plans", "telemetry", "research-signals"],
      allowedActions: ["write_entrypoint_brief", "recommend_next_action", "flag_missing_guidance"],
      forbiddenActions: ["change_pricing_unilaterally"],
      outputArtifact: "welcome-journey-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "journey_health"],
      requiredSecrets: []
    },
    {
      id: "vendor-scout",
      displayName: "Vendor Scout",
      committeeId: "vendor-network",
      primaryPillar: "growth",
      secondaryPillars: ["sales", "operations"],
      purpose: "Find vendors, affiliates, and integration partners that expand distribution or service capacity.",
      schedule: "Hourly",
      intervalMinutes: 60,
      inputSources: ["research-signals", "events", "archives"],
      allowedActions: ["source_vendor_leads", "write_vendor_map", "score_partner_fit"],
      forbiddenActions: ["approve_vendor_contracts"],
      outputArtifact: "vendor-lead-map",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "vendor_count"],
      requiredSecrets: []
    },
    {
      id: "vendor-recruiter",
      displayName: "Vendor Recruiter",
      committeeId: "vendor-network",
      primaryPillar: "sales",
      secondaryPillars: ["growth", "operations"],
      purpose: "Run governed outreach, qualification, and follow-up for vendors and channel partners.",
      schedule: "Every 90 minutes",
      intervalMinutes: 90,
      inputSources: ["plans", "research-signals", "events"],
      allowedActions: ["prepare_vendor_outreach", "qualify_vendor_interest", "write_recruitment_brief"],
      forbiddenActions: ["sign_binding_agreements"],
      outputArtifact: "vendor-recruitment-brief",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "missing-live-evidence",
      statusFields: ["status", "last_run", "qualified_vendors"],
      requiredSecrets: []
    },
    {
      id: "vendor-auditor",
      displayName: "Vendor Auditor",
      committeeId: "vendor-network",
      primaryPillar: "compliance-risk",
      secondaryPillars: ["finance", "operations"],
      purpose: "Vet vendor economics, policy exposure, reliability, and onboarding readiness before activation.",
      schedule: "Every 120 minutes",
      intervalMinutes: 120,
      inputSources: ["plans", "archives", "events", "telemetry"],
      allowedActions: ["screen_vendor_risk", "write_vendor_decision", "flag_margin_exposure"],
      forbiddenActions: ["override_compliance_review"],
      outputArtifact: "vendor-activation-decision",
      archiveEventType: "worker_run_completed",
      escalationRuleId: "regulated-objective-review",
      statusFields: ["status", "last_run", "vendor_decisions"],
      requiredSecrets: []
    }
  ],
  minimumLiveWorkerIds: [
    "gauge",
    "ledger",
    "sentinel",
    "mirror",
    "pulse",
    "sheriff",
    "polish"
  ]
};

type RuntimeStats = {
  planCompileDurationsMs: number[];
  runDurationsMs: number[];
  researchRefreshDurationsMs: number[];
  determinismHistory: number[];
  runCompletionHistory: number[];
  policyAlignmentHistory: number[];
  archiveCoverageHistory: number[];
  sourceHealthHistory: number[];
  pressureHistory: number[];
  lastResearchSyncAt?: string;
  lastGovernanceRegistryHash?: string;
  lastGovernanceRegistrySyncAt?: string;
};

type RuntimeState = {
  plans: InstitutionalPlan[];
  runs: GovernedRun[];
  operatorRuns: OperatorRun[];
  workerRuntime: WorkerRuntimeState[];
  outboundContacts: OutboundContact[];
  outboundMessages: OutboundMessage[];
  backendEvents: BackendProductEvent[];
  backendSummary: BackendTruthSummary;
  events: EventItem[];
  archives: ArchiveEntry[];
  v3Plans: V3Plan[];
  v3Runs: V3Run[];
  v3Events: V3Event[];
  v3Archives: ArchiveRecord[];
  v3ReplayRequests: ReplayRequest[];
  v3ReplayResults: ReplayResult[];
  v3CommercialArtifacts: CommercialArtifact[];
  v3CommercialScorecard: CommercialScorecard;
  researchSignals: ResearchSignal[];
  researchStatus: ResearchSourceStatus[];
  stats: RuntimeStats;
};

type StorageRuntimeStatus = {
  configured: boolean;
  provider: "postgres" | "file";
  connected: boolean;
  mode: "postgres+file-fallback" | "file-only";
  lastError: string | null;
};

type WorkerGroupBlueprint = {
  id: string;
  label: string;
  runtimeMode: string;
  boxRole: "hot" | "warm";
  workerIds: string[];
  wakeTriggers: string[];
  handoffTargets: string[];
};

type ResearchFetchResult = {
  signals: ResearchSignal[];
  statuses: ResearchSourceStatus[];
  durationMs: number;
};

type GovernanceEvaluation = {
  passed: boolean;
  approvals: number;
  issues: string[];
  summary: string;
  skillIds: string[];
  workflowIds: string[];
};

type TelemetrySnapshot = {
  latencyMs: number;
  determinismScore: number;
  committeeHealth: number;
  policyAlignment: number;
  archiveCoverage: number;
  sourceHealth: number;
  activeRunCount: number;
  totalSignals: number;
  runSuccessRate: number;
  runFailureRate: number;
  researchFreshness: number;
  workerPriming: number;
  planReadiness: number;
  latestRunIntegrity: number;
  executionPressure: number;
  lastResearchSyncAt?: string;
};

function emptyBackendTruthSummary(): BackendTruthSummary {
  return {
    liveUsers: 0,
    signups: 0,
    evaluationsStarted: 0,
    runsCompleted: 0,
    pipelineTests: 0,
    endpointCalls: 0,
    failedRoutes: 0,
    reserveBalance: 0,
    revenue: 0,
    evidenceExports: 0,
    mfaEvents: 0,
    marketplaceInstalls: 0,
    lastEventAt: undefined,
  };
}

function emptyCommercialScorecard(): CommercialScorecard {
  return {
    qualifiedEvaluationConversations: 0,
    privateBackendAccessRequests: 0,
    vendorToolConversations: 0,
    approvedPackageConcepts: 0,
    founderApprovedCommunityInteractions: 0,
    blockedUnsafeClaims: 0,
    archiveRecordsWritten: 0,
    directReplayChecksCompleted: 0,
    replayLinkedArtifacts: 0,
    lastUpdatedAt: now(),
  };
}

function cloneRegistry(registry: GovernanceRegistry): GovernanceRegistry {
  return JSON.parse(JSON.stringify(registry)) as GovernanceRegistry;
}

function activePillars() {
  return governanceRegistry.pillars;
}

function activeCommittees() {
  return governanceRegistry.committees;
}

function activeSkills() {
  return governanceRegistry.skills;
}

function buildEnterpriseSkills(): SkillArtifact[] {
  return [
    {
      id: "competitive-intelligence",
      name: "competitive-intelligence",
      category: "skill",
      description: "Scans market signals and competitor surfaces for revenue-relevant weakness.",
      allowedTools: ["read", "browser", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-competitive-intelligence",
      status: "approved",
      pillarIds: ["growth", "knowledge-research"],
      governingCommitteeId: "signal-council",
      usableByCommitteeIds: ["growth-intelligence", "builder-systems", "vendor-network"],
      requiredEvidence: ["public-source references", "signal digest"],
      publishRisk: "medium",
      inputType: "market signals + public artifacts",
      outputType: "competitor weakness brief",
      sla: "4h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "growth-navigator",
      name: "growth-navigator",
      category: "skill",
      description: "Optimizes outreach routes, segment targeting, and buyer motion under governed constraints.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-growth-navigator",
      status: "approved",
      pillarIds: ["growth", "sales"],
      governingCommitteeId: "execution-board",
      usableByCommitteeIds: ["growth-intelligence", "marketplace-operations"],
      requiredEvidence: ["approved offer", "reply-rate baseline"],
      publishRisk: "medium",
      inputType: "segment + pipeline data",
      outputType: "outreach route plan",
      sla: "4h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "evaluation-surgeon",
      name: "evaluation-surgeon",
      category: "skill",
      description: "Audits performance data, delivery quality, and client-health friction for intervention points.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-evaluation-surgeon",
      status: "approved",
      pillarIds: ["product", "operations", "sales"],
      governingCommitteeId: "execution-board",
      usableByCommitteeIds: ["experience-assurance", "builder-systems"],
      requiredEvidence: ["delivery metrics", "client-health snapshot"],
      publishRisk: "medium",
      inputType: "delivery + customer telemetry",
      outputType: "performance correction brief",
      sla: "8h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "mirror-truth-check",
      name: "mirror-truth-check",
      category: "skill",
      description: "Compares backend truth against live data and surfaces drift before it compounds.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-mirror-truth-check",
      status: "approved",
      pillarIds: ["product", "governance"],
      governingCommitteeId: "execution-board",
      usableByCommitteeIds: ["experience-assurance", "governance-evidence"],
      requiredEvidence: ["backend summary", "surface telemetry"],
      publishRisk: "high",
      inputType: "backend truth + live surface state",
      outputType: "truth drift report",
      sla: "2h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "sentinel-uptime",
      name: "sentinel-uptime",
      category: "skill",
      description: "Monitors system reliability, route health, and governed execution uptime.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-sentinel-uptime",
      status: "approved",
      pillarIds: ["operations", "product"],
      governingCommitteeId: "execution-board",
      usableByCommitteeIds: ["experience-assurance", "marketplace-operations"],
      requiredEvidence: ["worker runtime", "route health"],
      publishRisk: "low",
      inputType: "runtime health",
      outputType: "uptime assurance report",
      sla: "1h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "policy-evaluation",
      name: "policy-evaluation",
      category: "skill",
      description: "Validates plan compliance, claim safety, and execution admissibility before worker runs proceed.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-policy-evaluation",
      status: "approved",
      pillarIds: ["governance", "compliance-risk"],
      governingCommitteeId: "founder-council",
      usableByCommitteeIds: ["governance-evidence", "marketplace-operations", "vendor-network"],
      requiredEvidence: ["plan payload", "risk rationale"],
      publishRisk: "high",
      inputType: "plan + policy context",
      outputType: "admission or veto decision",
      sla: "2h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "asset-convergence",
      name: "asset-convergence",
      category: "skill",
      description: "Measures execution and research alignment so the machine does not drift into disconnected activity.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-asset-convergence",
      status: "approved",
      pillarIds: ["operations", "knowledge-research"],
      governingCommitteeId: "execution-board",
      usableByCommitteeIds: ["marketplace-operations", "governance-evidence"],
      requiredEvidence: ["signal set", "run outputs"],
      publishRisk: "medium",
      inputType: "research + run artifacts",
      outputType: "convergence scorecard",
      sla: "8h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "probability-matrix",
      name: "probability-matrix",
      category: "skill",
      description: "Forecasts deterministic outcomes and commercial path quality from current telemetry and archive signals.",
      allowedTools: ["read", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-probability-matrix",
      status: "approved",
      pillarIds: ["finance", "sales", "knowledge-research"],
      governingCommitteeId: "founder-council",
      usableByCommitteeIds: ["growth-intelligence", "governance-evidence", "experience-assurance"],
      requiredEvidence: ["telemetry", "archive history"],
      publishRisk: "medium",
      inputType: "historical performance + pipeline state",
      outputType: "forecast matrix",
      sla: "8h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "signal-feed",
      name: "signal-feed",
      category: "skill",
      description: "Ingests external research and public evidence into the governed signal layer.",
      allowedTools: ["read", "browser", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-signal-feed",
      status: "approved",
      pillarIds: ["knowledge-research"],
      governingCommitteeId: "signal-council",
      usableByCommitteeIds: ["growth-intelligence", "governance-evidence"],
      requiredEvidence: ["research source health", "signal lineage"],
      publishRisk: "low",
      inputType: "research sources",
      outputType: "fresh signal inventory",
      sla: "1h",
      revisionHistory: ["v3.0.0"],
    },
    {
      id: "field-intelligence",
      name: "field-intelligence",
      category: "skill",
      description: "Tracks launches, pricing shifts, partnerships, and competitive movement in the field.",
      allowedTools: ["read", "browser", "write"],
      source: "overlay/enterprise-skill-catalog",
      ref: "v3.0.0",
      treeSha: "overlay-field-intelligence",
      status: "approved",
      pillarIds: ["growth", "knowledge-research", "sales"],
      governingCommitteeId: "signal-council",
      usableByCommitteeIds: ["growth-intelligence", "vendor-network"],
      requiredEvidence: ["public activity trace", "competitor artifact snapshot"],
      publishRisk: "medium",
      inputType: "field activity",
      outputType: "market movement brief",
      sla: "4h",
      revisionHistory: ["v3.0.0"],
    },
  ];
}

function activeWorkflows() {
  return governanceRegistry.workflows;
}

function activeEscalationRules() {
  return governanceRegistry.escalationRules;
}

function currentWorkerGroupBlueprint() {
  return workerGroupBlueprints.find((group) => group.id === WORKER_GROUP || group.runtimeMode === RUNTIME_MODE);
}

function currentWorkerIds() {
  const blueprint = currentWorkerGroupBlueprint();
  return blueprint ? new Set(blueprint.workerIds) : null;
}

function activeOperatorCommittees() {
  const workerIds = currentWorkerIds();
  if (!workerIds) {
    return governanceRegistry.operatorCommittees;
  }
  return governanceRegistry.operatorCommittees
    .map((committee) => ({
      ...committee,
      workerIds: committee.workerIds.filter((workerId) => workerIds.has(workerId)),
    }))
    .filter((committee) => committee.workerIds.length > 0);
}

function activeWorkers() {
  const workerIds = currentWorkerIds();
  if (!workerIds) {
    return governanceRegistry.workers;
  }
  return governanceRegistry.workers.filter((worker) => workerIds.has(worker.id));
}

function minimumLiveWorkerIds() {
  const workerIds = currentWorkerIds();
  if (!workerIds) {
    return governanceRegistry.minimumLiveWorkerIds;
  }
  return governanceRegistry.minimumLiveWorkerIds.filter((workerId) => workerIds.has(workerId));
}

function logStartupContext(providerSnapshot: ModelProviderSnapshot) {
  const providerStatuses = providerSnapshot.statuses
    .map((status) => `${status.id}:${status.health}${status.active ? "*" : ""}`)
    .join(", ");
  const blueprint = currentWorkerGroupBlueprint();

  console.log("[uacp] UACP V3 control plane starting");
  console.log(`[uacp] box name: ${BOX_NAME}`);
  console.log(`[uacp] runtime mode: ${RUNTIME_MODE}`);
  console.log(
    `[uacp] registry loaded: version=${governanceRegistry.version} pillars=${governanceRegistry.pillars.length} committees=${governanceRegistry.committees.length} operatorCommittees=${governanceRegistry.operatorCommittees.length} workers=${governanceRegistry.workers.length}`,
  );
  console.log(
    `[uacp] minimum live workers loaded: count=${minimumLiveWorkerIds().length} ids=${minimumLiveWorkerIds().join(",") || "none"}`,
  );
  console.log("[uacp] operator scheduler enabled: true");
  console.log(`[uacp] archive/data dir: ${DATA_DIR}`);
  console.log(
    `[uacp] storage: provider=${storageRuntime.provider} configured=${storageRuntime.configured} connected=${storageRuntime.connected} mode=${storageRuntime.mode} coldStore=${COLD_STORAGE_DIR}`,
  );
  console.log(
    `[uacp] provider readiness: default=${providerSnapshot.defaultProvider} active=${providerSnapshot.activeProvider} statuses=${providerStatuses} internalApi=${INTERNAL_API_KEY ? "ready" : "disabled"} adminApi=${ADMIN_API_KEY ? "ready" : "disabled"} archiveWrite=${ARCHIVE_WRITE_REQUIRED ? "required" : "optional"} workerGroup=${WORKER_GROUP}`,
  );
  if (blueprint) {
    console.log(
      `[uacp] topology: role=${blueprint.boxRole} label=${blueprint.label} workers=${blueprint.workerIds.join(",")} wakeTriggers=${blueprint.wakeTriggers.join(" | ")}`,
    );
  }
}

function workerById(workerId: string) {
  return activeWorkers().find((worker) => worker.id === workerId);
}

function operatorCommitteeById(committeeId: string) {
  return activeOperatorCommittees().find((committee) => committee.id === committeeId);
}

function isoAfterMinutes(minutes: number, base = Date.now()) {
  return new Date(base + minutes * 60 * 1000).toISOString();
}

type ExecutionWindow = {
  id: string;
  label: string;
  objective: string;
  dayFrom: number;
  dayTo: number;
  backlogByCommittee: Record<string, string[]>;
};

const executionWindows: ExecutionWindow[] = [
  {
    id: "foundation",
    label: "Week 1 - Foundation",
    objective: "Lock ICP, offer, pricing, onboarding, and product workflow foundations.",
    dayFrom: 0,
    dayTo: 6,
    backlogByCommittee: {
      "growth-intelligence": ["Define ICP", "Write outreach scripts", "Draft case-study angle"],
      "marketplace-operations": ["Configure CRM flow", "Map onboarding flow", "Route offer packaging"],
      "governance-evidence": ["Approve pricing guardrails", "Validate guarantee language", "Protect evidence path"],
      "builder-systems": ["Map workflow automation targets", "Prepare build specs", "Flag missing dependencies"],
      "experience-assurance": ["Review landing-page clarity", "Test demo path", "Check onboarding friction"],
      "vendor-network": ["List partner channels", "Score vendor candidates", "Open affiliate map"],
    },
  },
  {
    id: "acquisition",
    label: "Week 2 - Acquisition",
    objective: "Drive outbound, demos, pipeline scoring, and paid pilot motion.",
    dayFrom: 7,
    dayTo: 13,
    backlogByCommittee: {
      "growth-intelligence": ["Send outbound bursts", "Rank warm conversations", "Write competitor pressure brief"],
      "marketplace-operations": ["Track lead routing", "Monitor follow-up cadence", "Escalate blocked conversions"],
      "governance-evidence": ["Review claims on active outreach", "Audit pricing proof", "Escalate unsupported positioning"],
      "builder-systems": ["Support demo automation", "Patch delivery blockers", "Prepare paid-pilot tooling"],
      "experience-assurance": ["Tighten demo flow", "Reduce CTA friction", "Watch product truth drift"],
      "vendor-network": ["Open vendor conversations", "Qualify partner fit", "Route channel opportunities"],
    },
  },
  {
    id: "delivery",
    label: "Week 3 - Delivery",
    objective: "Deliver pilots, automate reporting, and convert wins into repeatable proof.",
    dayFrom: 14,
    dayTo: 20,
    backlogByCommittee: {
      "growth-intelligence": ["Capture testimonial prompts", "Find upsell openings", "Refresh opportunity map"],
      "marketplace-operations": ["Track SLA delivery", "Route customer updates", "Surface delivery blockers"],
      "governance-evidence": ["Verify archive truth", "Lock pilot evidence bundle", "Protect referral claims"],
      "builder-systems": ["Automate reporting", "Package SOP outputs", "Extend delivery workflows"],
      "experience-assurance": ["Watch onboarding success", "Review milestone clarity", "Flag churn risk"],
      "vendor-network": ["Line up delivery support vendors", "Screen partner reliability", "Open referral paths"],
    },
  },
  {
    id: "scale",
    label: "Weeks 4-6 - Scale, Optimize, Grow",
    objective: "Expand ICP, optimize conversion, improve retention, and compound referrals.",
    dayFrom: 21,
    dayTo: 60,
    backlogByCommittee: {
      "growth-intelligence": ["Expand ICP targets", "Tune messaging", "Score retention and upsell signals"],
      "marketplace-operations": ["Optimize funnel flow", "Track renewal ops", "Route growth-loop actions"],
      "governance-evidence": ["Audit scaling claims", "Review margin-safe approvals", "Keep archive coverage honest"],
      "builder-systems": ["Refine automations", "Harden dashboards", "Support new offer tiers"],
      "experience-assurance": ["Protect UX quality", "Measure activation rate", "Reduce friction regressions"],
      "vendor-network": ["Grow partner pipeline", "Activate referrals", "Vet distribution expansion"],
    },
  },
];

const enterpriseCouncilBlueprints: Array<{
  id: string;
  name: string;
  purpose: string;
  powers: string[];
  escalationRule: string;
  mappedOperatorCommitteeIds: string[];
  skillIds: string[];
}> = [
  {
    id: "growth-council",
    name: "Growth Council",
    purpose: "Oversees lead generation, outreach, content, and partnerships.",
    powers: ["Approve marketing plans", "Allocate outreach volume", "Veto low-ROI campaigns"],
    escalationRule: "Escalates to Founder Council if outreach efficiency < 80%.",
    mappedOperatorCommitteeIds: ["growth-intelligence", "vendor-network"],
    skillIds: ["competitive-intelligence", "growth-navigator", "signal-feed", "field-intelligence"],
  },
  {
    id: "sales-council",
    name: "Sales Council",
    purpose: "Owns pipeline, pricing, and conversion.",
    powers: ["Approve offer structures", "Adjust pricing", "Authorize pilots"],
    escalationRule: "Escalates if close rate < 20%.",
    mappedOperatorCommitteeIds: ["marketplace-operations"],
    skillIds: ["outreach-sequencing", "sales-call-prep", "probability-matrix", "policy-evaluation"],
  },
  {
    id: "delivery-council",
    name: "Delivery Council",
    purpose: "Ensures fulfillment quality and client satisfaction.",
    powers: ["Approve workflow templates", "Validate SLAs", "Manage onboarding"],
    escalationRule: "Escalates if SLA breach > 5%.",
    mappedOperatorCommitteeIds: ["builder-systems", "experience-assurance"],
    skillIds: ["governed-offer-packaging", "evaluation-surgeon", "demo-proof-check"],
  },
  {
    id: "retention-council",
    name: "Retention Council",
    purpose: "Manages renewals, upsells, and referrals.",
    powers: ["Approve retention workflows", "Review churn data"],
    escalationRule: "Escalates if churn risk > 10%.",
    mappedOperatorCommitteeIds: ["experience-assurance"],
    skillIds: ["evaluation-surgeon", "mirror-truth-check", "probability-matrix"],
  },
  {
    id: "operations-council",
    name: "Operations Council",
    purpose: "Maintains automation, finance, and reporting.",
    powers: ["Approve system updates", "Monitor uptime", "Manage reserves"],
    escalationRule: "Escalates if uptime < 95%.",
    mappedOperatorCommitteeIds: ["marketplace-operations", "builder-systems"],
    skillIds: ["sentinel-uptime", "asset-convergence", "policy-evaluation"],
  },
  {
    id: "intelligence-council",
    name: "Intelligence Council",
    purpose: "Handles research, data, and optimization.",
    powers: ["Approve new models", "Validate insights", "Monitor drift"],
    escalationRule: "Escalates if determinism ratio < 0.95.",
    mappedOperatorCommitteeIds: ["growth-intelligence", "governance-evidence"],
    skillIds: ["competitive-intelligence", "signal-feed", "field-intelligence", "mirror-truth-check"],
  },
];

const canonicalPlanTemplates: CanonicalPlanTemplate[] = [
  {
    id: "paid-customer-sprint-14d",
    name: "14-Day Paid Customer Sprint",
    objective: "Acquire the first paid client via AI-governed outreach and founder-approved offer framing.",
    ownerCouncil: "Growth Council + Sales Council",
    payingUser: "Founder-led B2B buyer",
    pricingModel: "Paid pilot with governed fast-start package",
    executionWindow: "14 days",
    committeeRoute: ["growth-council", "sales-council", "delivery-council", "operations-council"],
    requiredSkillIds: ["competitive-intelligence", "growth-navigator", "outreach-sequencing", "policy-evaluation"],
    workflowIds: ["competitive-intelligence", "product-teardown"],
    admissionRules: ["At least 3 approved skills are attached.", "At least 1 council sponsor is attached.", "Evidence-backed offer framing is present."],
    vetoRules: ["Regulatory breach", "Margin-negative execution", "Missing evidence"],
    successMetrics: ["Qualified conversations", "Booked calls", "Paid pilot conversion"],
  },
  {
    id: "retention-optimization-30d",
    name: "30-Day Retention Optimization",
    objective: "Reduce churn risk by tightening onboarding, reporting, renewal timing, and upsell sequencing.",
    ownerCouncil: "Retention Council",
    payingUser: "Active customer base",
    pricingModel: "Expansion and renewal preservation",
    executionWindow: "30 days",
    committeeRoute: ["retention-council", "delivery-council", "operations-council"],
    requiredSkillIds: ["evaluation-surgeon", "mirror-truth-check", "probability-matrix"],
    workflowIds: ["model-council"],
    admissionRules: ["At least 3 approved skills are attached.", "Client health data is present.", "Renewal or churn pressure is measurable."],
    vetoRules: ["Missing customer evidence", "Unsupported retention claim"],
    successMetrics: ["Churn risk reduction", "Upsell opportunities", "Renewal rate"],
  },
  {
    id: "automation-expansion-6w",
    name: "6-Week Automation Expansion",
    objective: "Deploy 10 new governed workflows without breaking determinism, uptime, or archive coverage.",
    ownerCouncil: "Operations Council",
    payingUser: "Internal operating reserve",
    pricingModel: "Efficiency and margin expansion",
    executionWindow: "6 weeks",
    committeeRoute: ["operations-council", "delivery-council", "intelligence-council"],
    requiredSkillIds: ["sentinel-uptime", "asset-convergence", "policy-evaluation"],
    workflowIds: ["model-council", "vendor-recruitment"],
    admissionRules: ["At least 3 approved skills are attached.", "Archive path is writable.", "Rollback strategy is defined."],
    vetoRules: ["Uptime degradation risk", "Missing archive coverage", "Unapproved skill usage"],
    successMetrics: ["Workflow count shipped", "Uptime", "Time saved"],
  },
  {
    id: "research-sync-quarterly",
    name: "Quarterly Research Sync",
    objective: "Update deterministic models and governed market truth with fresh external evidence.",
    ownerCouncil: "Intelligence Council",
    payingUser: "Institutional strategy layer",
    pricingModel: "Research leverage and model quality",
    executionWindow: "90 days",
    committeeRoute: ["intelligence-council", "growth-council", "operations-council"],
    requiredSkillIds: ["signal-feed", "field-intelligence", "competitive-intelligence", "mirror-truth-check"],
    workflowIds: ["competitive-intelligence", "competitor-raid"],
    admissionRules: ["At least 3 approved skills are attached.", "Fresh research sources are online.", "Determinism baseline is recorded."],
    vetoRules: ["No live sources", "Low-evidence thesis", "Determinism drift without explanation"],
    successMetrics: ["Signal freshness", "Determinism ratio", "Updated opportunity map"],
  },
  {
    id: "governance-review-annual",
    name: "Annual Governance Review",
    objective: "Audit all councils, workers, skills, and replay integrity for institutional trustworthiness.",
    ownerCouncil: "Founder Council",
    payingUser: "Founding governance body",
    pricingModel: "Risk reduction and institutional control",
    executionWindow: "12 months",
    committeeRoute: ["operations-council", "intelligence-council", "delivery-council"],
    requiredSkillIds: ["policy-evaluation", "archive-integrity-check", "sentinel-uptime", "mirror-truth-check"],
    workflowIds: ["model-council"],
    admissionRules: ["At least 3 approved skills are attached.", "Full archive coverage is available.", "Replay chain verification is enabled."],
    vetoRules: ["Broken replay chain", "Archive mutation", "Missing policy evidence"],
    successMetrics: ["Replay integrity", "Archive coverage", "Committee compliance"],
  },
];

function daysSinceControlPlaneBoot() {
  return Math.floor((Date.now() - CONTROL_PLANE_BOOTED_AT) / (1000 * 60 * 60 * 24));
}

function activeExecutionWindow() {
  const day = daysSinceControlPlaneBoot();
  return executionWindows.find((window) => day >= window.dayFrom && day <= window.dayTo) || executionWindows[executionWindows.length - 1];
}

function committeeRegroupIntervalMinutes(committee: OperatorCommittee) {
  return committee.regroupIntervalMinutes || Math.max(1, Math.floor((24 * 60) / Math.max(1, committee.cadencePerDay || 3)));
}

function workerConveyorOffsetMinutes(worker: OperatorWorker) {
  const committee = operatorCommitteeById(worker.committeeId);
  if (!committee) {
    return 0;
  }

  const index = Math.max(0, committee.workerIds.indexOf(worker.id));
  const spacing = clamp(
    Math.floor(Math.max(1, Math.min(worker.intervalMinutes, committeeRegroupIntervalMinutes(committee))) / Math.max(1, committee.workerIds.length)),
    UACP_SCHEDULER_MIN_STAGGER_MINUTES,
    15,
  );

  return index * spacing;
}

function initialWorkerNextRunAt(worker: OperatorWorker) {
  const offsetMinutes = workerConveyorOffsetMinutes(worker);
  return minimumLiveWorkerIds().includes(worker.id)
    ? isoAfterMinutes(offsetMinutes)
    : isoAfterMinutes(worker.intervalMinutes + offsetMinutes);
}

function committeeBacklog(committeeId: string) {
  const window = activeExecutionWindow();
  return window.backlogByCommittee[committeeId] || [];
}

function lastCommitteeRegroupAt(committeeId: string) {
  const regroupEvent = state.events
    .filter((event) => event.type === "COMMITTEE_REGROUP" && event.metadata?.committeeId === committeeId)
    .sort((left, right) => Date.parse(right.timestamp) - Date.parse(left.timestamp))[0];
  return regroupEvent?.timestamp;
}

function committeeRegroupsToday(committeeId: string) {
  const nowDate = new Date();
  return state.events.filter((event) => {
    if (event.type !== "COMMITTEE_REGROUP" || event.metadata?.committeeId !== committeeId) {
      return false;
    }
    const eventDate = new Date(event.timestamp);
    return eventDate.getUTCFullYear() === nowDate.getUTCFullYear()
      && eventDate.getUTCMonth() === nowDate.getUTCMonth()
      && eventDate.getUTCDate() === nowDate.getUTCDate();
  }).length;
}

function nextCommitteeRegroupAt(committee: OperatorCommittee) {
  const lastRegroup = lastCommitteeRegroupAt(committee.id);
  if (!lastRegroup) {
    return now();
  }
  return isoAfterMinutes(committeeRegroupIntervalMinutes(committee), Date.parse(lastRegroup));
}

function committeeBenefitSummary(committee: OperatorCommittee) {
  switch (committee.id) {
    case "growth-intelligence":
      return "Finds buyer pain, competitor weakness, and live pipeline opportunities so revenue motion never goes stale.";
    case "marketplace-operations":
      return "Keeps intake, routing, pricing flow, and commercial execution moving instead of stalling in ops debt.";
    case "governance-evidence":
      return "Prevents bad claims, weak proof, and archive drift from damaging trust or causing policy mistakes.";
    case "builder-systems":
      return "Turns approved opportunities into build packets and automation paths so the company compounds instead of improvising.";
    case "experience-assurance":
      return "Protects demo quality, onboarding clarity, and product truth so prospects and customers do not bounce.";
    case "vendor-network":
      return "Sources partners, channels, and delivery support that expand capacity and distribution without founder-only effort.";
    default:
      return committee.purpose;
  }
}

function buildOperatorCommitteeRuntimeView(committee: OperatorCommittee): OperatorCommitteeRuntimeView {
  const workerIds = committee.workerIds;
  const activeWorkerCount = state.operatorRuns.filter((run) => run.committeeId === committee.id && (run.status === "queued" || run.status === "running")).length;
  const queuedWorkerCount = state.operatorRuns.filter((run) => run.committeeId === committee.id && run.status === "queued").length;
  const window = activeExecutionWindow();

  return {
    id: committee.id,
    name: committee.name,
    purpose: committee.purpose,
    chair: committee.chair,
    sponsor: committee.sponsor,
    decisionFramework: committee.decisionFramework,
    cadencePerDay: committee.cadencePerDay || 3,
    regroupIntervalMinutes: committeeRegroupIntervalMinutes(committee),
    lastRegroupAt: lastCommitteeRegroupAt(committee.id),
    nextRegroupAt: nextCommitteeRegroupAt(committee),
    regroupsToday: committeeRegroupsToday(committee.id),
    workerCount: workerIds.length,
    activeWorkerCount,
    queuedWorkerCount,
    backlog: committeeBacklog(committee.id),
    activeExecutionWindow: {
      id: window.id,
      label: window.label,
      objective: window.objective,
    },
    benefitSummary: committeeBenefitSummary(committee),
    successMetrics: committee.successMetrics || [],
  };
}

function buildEnterpriseCouncils(): EnterpriseCouncilView[] {
  const skills = buildEnterpriseSkills();
  return enterpriseCouncilBlueprints.map((council) => {
    const workerCount = council.mappedOperatorCommitteeIds.reduce((total, committeeId) => {
      const committee = operatorCommitteeById(committeeId);
      return total + (committee?.workerIds.length || 0);
    }, 0);
    const skillCount = skills.filter((skill) => council.skillIds.includes(skill.id)).length;
    return {
      id: council.id,
      name: council.name,
      purpose: council.purpose,
      powers: council.powers,
      escalationRule: council.escalationRule,
      mappedOperatorCommitteeIds: council.mappedOperatorCommitteeIds,
      workerCount,
      skillCount,
    } satisfies EnterpriseCouncilView;
  });
}

function buildEnterpriseChecks(): EnterpriseCheckView[] {
  const nowAt = now();
  const liveWorkers = state.workerRuntime.filter((worker) => !worker.paused);
  const liveWorkerHeartbeats = liveWorkers
    .map((worker) => worker.lastHeartbeatAt ? (Date.now() - Date.parse(worker.lastHeartbeatAt)) / 60000 : Number.POSITIVE_INFINITY);
  const freshHeartbeatRatio = liveWorkerHeartbeats.length
    ? liveWorkerHeartbeats.filter((minutes) => Number.isFinite(minutes) && minutes <= 30).length / liveWorkerHeartbeats.length
    : 0;
  const pulseStatus: EnterpriseCheckView["status"] = freshHeartbeatRatio >= 0.95 ? "pass" : freshHeartbeatRatio >= 0.8 ? "watch" : "fail";

  const truthDriftScore = clamp(
    state.backendSummary.failedRoutes > 0
      ? state.backendSummary.failedRoutes / Math.max(1, state.backendSummary.endpointCalls || 1)
      : 0,
    0,
    1,
  );
  const mirrorStatus: EnterpriseCheckView["status"] = truthDriftScore <= 0.05 ? "pass" : truthDriftScore <= 0.15 ? "watch" : "fail";

  const erroredWorkers = state.workerRuntime.filter((worker) => worker.status === "error").length;
  const schedulerBase = liveWorkers.length > 0 ? (liveWorkers.length - erroredWorkers) / liveWorkers.length : 0;
  const uptimeMetric = clamp(
    (schedulerBase * 0.6) + ((1 - clamp(state.backendSummary.failedRoutes / Math.max(1, state.backendSummary.endpointCalls || 1), 0, 1)) * 0.4),
    0,
    1,
  );
  const sentinelStatus: EnterpriseCheckView["status"] = uptimeMetric >= 0.95 ? "pass" : uptimeMetric >= 0.8 ? "watch" : "fail";

  return [
    {
      id: "pulse",
      name: "Pulse",
      ownerWorkerId: "pulse",
      ownerCommitteeId: "experience-assurance",
      status: pulseStatus,
      summary: `${Math.round(freshHeartbeatRatio * 100)}% of live workers have a fresh heartbeat and regroup cadence remains within target.`,
      purpose: "Checks freshness of agents and feeds.",
      passCondition: "Fresh worker heartbeat ratio >= 95% and regroup cadence is intact.",
      failCondition: "Fresh worker heartbeat ratio < 80% or regroup cadence is stale.",
      metric: Number((freshHeartbeatRatio * 100).toFixed(2)),
      lastCheckedAt: nowAt,
    },
    {
      id: "mirror",
      name: "Mirror",
      ownerWorkerId: "mirror",
      ownerCommitteeId: "experience-assurance",
      status: mirrorStatus,
      summary: `${Math.round(truthDriftScore * 100)}% backend/live drift based on failed routes and truth mismatch pressure.`,
      purpose: "Detects truth drift between backend and live data.",
      passCondition: "Truth drift <= 5%.",
      failCondition: "Truth drift > 15%.",
      metric: Number((truthDriftScore * 100).toFixed(2)),
      lastCheckedAt: nowAt,
    },
    {
      id: "sentinel",
      name: "Sentinel",
      ownerWorkerId: "sentinel",
      ownerCommitteeId: "experience-assurance",
      status: sentinelStatus,
      summary: `${Math.round(uptimeMetric * 100)}% reliability score based on worker health and route failure pressure.`,
      purpose: "Monitors uptime and reliability.",
      passCondition: "Reliability score >= 95% and scheduler is advancing runs.",
      failCondition: "Reliability score < 80% or worker errors begin to dominate.",
      metric: Number((uptimeMetric * 100).toFixed(2)),
      lastCheckedAt: nowAt,
    },
  ];
}

function buildGovernanceBackbone() {
  return {
    councils: buildEnterpriseCouncils(),
    skills: buildEnterpriseSkills(),
    canonicalPlans: canonicalPlanTemplates,
    enterpriseChecks: buildEnterpriseChecks(),
    governanceRules: {
      admission: "Plan must have at least 3 approved skills and at least 1 committee sponsor.",
      execution: "Only admitted plans can trigger worker runs.",
      veto: "Founder Council may veto for regulatory breach, margin-negative execution, or missing evidence.",
      escalation: "Any breach of SLA or determinism ratio triggers review.",
      archival: "Completed runs are stored as replayable evidence in Archives.",
    },
  };
}

function makeWorkerRuntime(worker: OperatorWorker): WorkerRuntimeState {
  return {
    workerId: worker.id,
    status: "idle",
    paused: false,
    lastHeartbeatAt: undefined,
    lastRunAt: undefined,
    lastRunId: undefined,
    nextRunAt: initialWorkerNextRunAt(worker),
    lastError: undefined,
  };
}

function syncWorkerRuntimeState() {
  const current = new Map(state.workerRuntime.map((runtime) => [runtime.workerId, runtime]));
  state.workerRuntime = activeWorkers().map((worker) => {
    const existing = current.get(worker.id);
    return existing
      ? {
          ...existing,
          workerId: worker.id,
          nextRunAt: existing.nextRunAt || initialWorkerNextRunAt(worker),
        }
      : makeWorkerRuntime(worker);
  });
}

function normalizeWorkerRuntimeForStartup() {
  const minimumLive = new Set(minimumLiveWorkerIds());

  state.workerRuntime = state.workerRuntime.map((runtime) => {
    const worker = workerById(runtime.workerId);
    if (!worker) return runtime;

    const nextRunAt = runtime.nextRunAt || initialWorkerNextRunAt(worker);

    if (runtime.paused) {
      return {
        ...runtime,
        nextRunAt,
      };
    }

    if (runtime.status !== "error" && runtime.status !== "running") {
      return {
        ...runtime,
        nextRunAt,
      };
    }

    return {
      ...runtime,
      status: "idle",
      nextRunAt: minimumLive.has(runtime.workerId) ? initialWorkerNextRunAt(worker) : nextRunAt,
      lastError: undefined,
    };
  });
}

const clients = new Set<WebSocket>();
const eventStreamClients = new Set<express.Response>();
let state: RuntimeState = emptyState();
let persistQueue = Promise.resolve();
let governanceRegistry: GovernanceRegistry = cloneRegistry(defaultGovernanceRegistry);
let dbPool: pg.Pool | null = null;
let dbReadyPromise: Promise<boolean> | null = null;
const storageRuntime: StorageRuntimeStatus = {
  configured: Boolean(DATABASE_URL),
  provider: DATABASE_URL ? "postgres" : "file",
  connected: false,
  mode: DATABASE_URL ? "postgres+file-fallback" : "file-only",
  lastError: null,
};

function databaseSslConfig() {
  if (!DATABASE_URL) return undefined;
  if (DATABASE_SSL_MODE === "disable" || DATABASE_SSL_MODE === "off" || DATABASE_SSL_MODE === "false") {
    return false;
  }
  return { rejectUnauthorized: false };
}

function hashPayload(payload: Record<string, unknown>) {
  return crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

function latestEventHash() {
  return state.events[0]?.recordHash;
}

function latestArchiveHash() {
  return state.archives[0]?.recordHash;
}

function buildEventRecordHash(entry: Omit<EventItem, "recordHash">) {
  return hashPayload({
    id: entry.id,
    type: entry.type,
    timestamp: entry.timestamp,
    message: entry.message,
    surface: entry.surface,
    metadata: entry.metadata || null,
    previousHash: entry.previousHash || null,
  });
}

function buildArchiveRecordHash(entry: Omit<ArchiveEntry, "recordHash">) {
  return hashPayload({
    id: entry.id,
    title: entry.title,
    category: entry.category,
    summary: entry.summary,
    createdAt: entry.createdAt,
    lineage: entry.lineage,
    metadata: entry.metadata || null,
    previousHash: entry.previousHash || null,
  });
}

function normalizeEventHashChain() {
  let previousHash: string | undefined;
  const normalized = [...state.events]
    .reverse()
    .map((event) => {
      const next: EventItem = {
        ...event,
        previousHash,
      };
      next.recordHash = buildEventRecordHash({
        id: next.id,
        type: next.type,
        timestamp: next.timestamp,
        message: next.message,
        surface: next.surface,
        metadata: next.metadata,
        previousHash: next.previousHash,
      });
      previousHash = next.recordHash;
      return next;
    })
    .reverse();
  state.events = normalized;
}

function normalizeArchiveHashChain() {
  let previousHash: string | undefined;
  const normalized = [...state.archives]
    .reverse()
    .map((archive) => {
      const next: ArchiveEntry = {
        ...archive,
        previousHash,
      };
      next.recordHash = buildArchiveRecordHash({
        id: next.id,
        title: next.title,
        category: next.category,
        summary: next.summary,
        createdAt: next.createdAt,
        lineage: next.lineage,
        metadata: next.metadata,
        previousHash: next.previousHash,
      });
      previousHash = next.recordHash;
      return next;
    })
    .reverse();
  state.archives = normalized;
}

async function ensureDataDir() {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function ensureColdStorageDir() {
  await fs.mkdir(COLD_STORAGE_DIR, { recursive: true });
}

async function ensureDatabase() {
  if (!DATABASE_URL) {
    storageRuntime.connected = false;
    return false;
  }

  if (dbReadyPromise) {
    return dbReadyPromise;
  }

  dbReadyPromise = (async () => {
    try {
      if (!dbPool) {
        dbPool = new Pool({
          connectionString: DATABASE_URL,
          ssl: databaseSslConfig(),
          max: 4,
        });
      }

      await dbPool.query(`
        create table if not exists uacp_state_store (
          store_key text primary key,
          payload jsonb not null,
          updated_at timestamptz not null default now()
        )
      `);

      storageRuntime.connected = true;
      storageRuntime.lastError = null;
      return true;
    } catch (error) {
      storageRuntime.connected = false;
      storageRuntime.lastError = error instanceof Error ? error.message : "Unknown Postgres initialization error.";
      console.error("Postgres initialization error:", error);
      return false;
    } finally {
      dbReadyPromise = null;
    }
  })();

  return dbReadyPromise;
}

async function readDatabaseStore<T>(storeKey: string): Promise<T | null> {
  if (!(await ensureDatabase()) || !dbPool) {
    return null;
  }

  try {
    const result = await dbPool.query<{ payload: T }>("select payload from uacp_state_store where store_key = $1 limit 1", [storeKey]);
    return result.rows[0]?.payload ?? null;
  } catch (error) {
    storageRuntime.connected = false;
    storageRuntime.lastError = error instanceof Error ? error.message : "Unknown Postgres read error.";
    console.error(`Postgres read error for ${storeKey}:`, error);
    return null;
  }
}

async function writeDatabaseStore(storeKey: string, payload: unknown) {
  if (!(await ensureDatabase()) || !dbPool) {
    return false;
  }

  try {
    await dbPool.query(
      `
        insert into uacp_state_store (store_key, payload, updated_at)
        values ($1, $2::jsonb, now())
        on conflict (store_key)
        do update set payload = excluded.payload, updated_at = excluded.updated_at
      `,
      [storeKey, JSON.stringify(payload)],
    );
    storageRuntime.connected = true;
    storageRuntime.lastError = null;
    return true;
  } catch (error) {
    storageRuntime.connected = false;
    storageRuntime.lastError = error instanceof Error ? error.message : "Unknown Postgres write error.";
    console.error(`Postgres write error for ${storeKey}:`, error);
    return false;
  }
}

async function writeCompressedSnapshot(targetFile: string, payload: unknown) {
  await ensureColdStorageDir();
  const buffer = gzipSync(Buffer.from(JSON.stringify(payload), "utf8"), { level: 9 });
  await fs.writeFile(targetFile, buffer);
}

async function readCompressedSnapshot<T>(targetFile: string): Promise<T | null> {
  try {
    const buffer = await fs.readFile(targetFile);
    return JSON.parse(gunzipSync(buffer).toString("utf8")) as T;
  } catch {
    return null;
  }
}

const veklomPillars: VeklomPillar[] = [
  {
    id: "governance-policy",
    name: "Governance & Policy",
    purpose: "Define institutional rules, approval thresholds, and the conditions under which execution is allowed.",
    successMetric: "Policy-backed execution approval rate",
  },
  {
    id: "sovereignty-infrastructure",
    name: "Sovereignty & Infrastructure",
    purpose: "Protect trust boundaries, data residency, and infrastructure ownership for private AI execution.",
    successMetric: "Sovereign runtime coverage",
  },
  {
    id: "model-tool-governance",
    name: "Model & Tool Governance",
    purpose: "Govern models, tools, connectors, and marketplace capabilities through approved bindings.",
    successMetric: "Approved tool readiness",
  },
  {
    id: "execution-runtime-safety",
    name: "Execution & Runtime Safety",
    purpose: "Enforce runtime policies, admission control, circuit breakers, and safe execution constraints.",
    successMetric: "Safe run completion rate",
  },
  {
    id: "evidence-audit-archives",
    name: "Evidence, Audit & Archives",
    purpose: "Preserve replayable judgment through signed artifacts, event lineage, and archive bundles.",
    successMetric: "Replayable archive coverage",
  },
  {
    id: "tenant-experience-integration",
    name: "Tenant Experience & Integration",
    purpose: "Make governed execution legible to tenants and safe to integrate into real operating flows.",
    successMetric: "Tenant-ready governed flows",
  },
  {
    id: "economics-operating-reserve",
    name: "Economics & Operating Reserve",
    purpose: "Tie every run to cost, pricing, reserve logic, and monetizable operating leverage.",
    successMetric: "Margin-backed execution quality",
  },
  {
    id: "compliance-risk-legal",
    name: "Compliance, Risk & Legal Posture",
    purpose: "Constrain execution by legal, regulatory, privacy, and risk obligations.",
    successMetric: "Policy and risk review coverage",
  },
  {
    id: "research-knowledge-learning",
    name: "Research, Knowledge & Institutional Learning",
    purpose: "Turn market intelligence and competitor weakness into governed opportunities and institutional learning.",
    successMetric: "Signal-to-opportunity conversion",
  },
];

const veklomCommittees: V3Committee[] = [
  {
    id: "research-command",
    name: "Research Command",
    purpose: "Convert competitor weakness and buyer pain into governed opportunity inputs.",
    pillarIds: ["research-knowledge-learning"],
    authorityLevel: "operational",
    workerIds: ["scout-revenue", "curator-market"],
    allowedActions: ["surface_competitor_weakness", "open_opportunity_brief", "route_market_signal"],
    escalationTarget: "governance-council",
  },
  {
    id: "marketplace-council",
    name: "Marketplace Council",
    purpose: "Curate sellable tools and package governed offers from approved capabilities.",
    pillarIds: ["model-tool-governance", "tenant-experience-integration"],
    authorityLevel: "approval",
    workerIds: ["curator-market", "builder-package", "steward-tenant"],
    allowedActions: ["approve_capability_binding", "package_offer", "define_tool_scope"],
    escalationTarget: "governance-council",
  },
  {
    id: "governance-council",
    name: "Governance Council",
    purpose: "Apply policy, approval paths, and execution constraints before a governed run is allowed.",
    pillarIds: ["governance-policy", "execution-runtime-safety"],
    authorityLevel: "constitutional",
    workerIds: ["arbiter-policy", "switchman-runtime"],
    allowedActions: ["approve_plan", "deny_plan", "set_runtime_policy", "assign_execution_path"],
  },
  {
    id: "risk-office",
    name: "Risk Office",
    purpose: "Review legal, compliance, and policy exposure before an opportunity is promoted.",
    pillarIds: ["compliance-risk-legal"],
    authorityLevel: "veto",
    workerIds: ["sheriff-risk"],
    allowedActions: ["review_risk", "block_claim", "require_evidence"],
    escalationTarget: "governance-council",
  },
  {
    id: "reserve-board",
    name: "Reserve Board",
    purpose: "Attach pricing, cost, and operating reserve logic to every governed opportunity.",
    pillarIds: ["economics-operating-reserve"],
    authorityLevel: "approval",
    workerIds: ["gauge-economics", "treasurer-reserve"],
    allowedActions: ["set_pricing_hypothesis", "review_margin", "set_spend_cap"],
    escalationTarget: "governance-council",
  },
  {
    id: "archives-board",
    name: "Archives Board",
    purpose: "Capture archive bundles, replay metadata, and final evidence records.",
    pillarIds: ["evidence-audit-archives"],
    authorityLevel: "approval",
    workerIds: ["steward-archive"],
    allowedActions: ["write_archive_record", "sign_bundle", "prepare_replay"],
  },
];

const veklomSkills: SkillBinding[] = [
  {
    id: "skill-competitive-intel",
    name: "competitive-intel",
    state: "pinned",
    governingCommitteeId: "research-command",
    pillarIds: ["research-knowledge-learning"],
    purpose: "Extract competitor weakness and market pain from governed public research.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-competitive-intel-v1",
    allowedTools: ["read", "browser"],
  },
  {
    id: "skill-marketplace-curation",
    name: "marketplace-curation",
    state: "pinned",
    governingCommitteeId: "marketplace-council",
    pillarIds: ["model-tool-governance", "tenant-experience-integration"],
    purpose: "Package approved capability bundles into sellable marketplace offers.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-marketplace-curation-v1",
    allowedTools: ["read", "write"],
  },
  {
    id: "skill-policy-review",
    name: "policy-review",
    state: "pinned",
    governingCommitteeId: "governance-council",
    pillarIds: ["governance-policy", "execution-runtime-safety"],
    purpose: "Apply runtime policies, approval paths, and evidence requirements to a plan.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-policy-review-v1",
    allowedTools: ["read", "write"],
  },
  {
    id: "skill-risk-audit",
    name: "risk-audit",
    state: "pinned",
    governingCommitteeId: "risk-office",
    pillarIds: ["compliance-risk-legal", "evidence-audit-archives"],
    purpose: "Review legal exposure, policy claims, and required evidence for governed output.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-risk-audit-v1",
    allowedTools: ["read", "write"],
  },
  {
    id: "skill-reserve-pricing",
    name: "reserve-pricing",
    state: "pinned",
    governingCommitteeId: "reserve-board",
    pillarIds: ["economics-operating-reserve"],
    purpose: "Attach pricing hypothesis, reserve cost logic, and monetization framing.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-reserve-pricing-v1",
    allowedTools: ["read", "write"],
  },
  {
    id: "skill-archive-bundler",
    name: "archive-bundler",
    state: "pinned",
    governingCommitteeId: "archives-board",
    pillarIds: ["evidence-audit-archives"],
    purpose: "Write replayable archive bundles for completed or failed governed runs.",
    pinned: true,
    sourceRepo: "github.com/veklom/skills",
    sourceRef: "v1.0.0",
    sourceTreeSha: "tree-archive-bundler-v1",
    allowedTools: ["read", "write"],
  },
];

const veklomWorkers: WorkerRegistryEntry[] = [
  {
    id: "arbiter-policy",
    name: "Arbiter Policy",
    archetype: "arbiter",
    pillarId: "governance-policy",
    committeeId: "governance-council",
    authorityLevel: "constitutional",
    allowedSkillIds: ["skill-policy-review"],
    forbiddenActions: ["execute_without_approval", "publish_without_archive"],
    requiredOutput: "governance decision memo",
    reviewer: "Founder Council",
    archivePath: "archives/core/governance/arbiter-policy",
    requiredEnvKeys: ["UACP_ADMIN_KEY", "UACP_INTERNAL_API_KEY"],
    status: "ready",
    promotionMetric: "High-quality approval accuracy",
    demotionTrigger: "Approving runs without evidence path",
    currentJob: "Approve or block governed revenue plans",
  },
  {
    id: "sheriff-risk",
    name: "Sheriff Risk",
    archetype: "sheriff",
    pillarId: "compliance-risk-legal",
    committeeId: "risk-office",
    authorityLevel: "veto",
    allowedSkillIds: ["skill-risk-audit"],
    forbiddenActions: ["ignore_policy_gaps", "suppress_risk_findings"],
    requiredOutput: "policy and risk review",
    reviewer: "Governance Council",
    archivePath: "archives/core/risk/sheriff-risk",
    requiredEnvKeys: ["UACP_INTERNAL_API_KEY"],
    status: "ready",
    promotionMetric: "Risk findings caught before release",
    demotionTrigger: "Unjustified approval under compliance uncertainty",
    currentJob: "Block unsupported claims and require evidence",
  },
  {
    id: "gauge-economics",
    name: "Gauge Economics",
    archetype: "gauge",
    pillarId: "economics-operating-reserve",
    committeeId: "reserve-board",
    authorityLevel: "approval",
    allowedSkillIds: ["skill-reserve-pricing"],
    forbiddenActions: ["set_unbounded_spend", "omit_cost_view"],
    requiredOutput: "pricing and reserve pressure snapshot",
    reviewer: "Reserve Board",
    archivePath: "archives/core/economics/gauge-economics",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Margin-aware pricing quality",
    demotionTrigger: "Missing spend cap or cost trace",
    currentJob: "Quantify opportunity economics and pricing pressure",
  },
  {
    id: "switchman-runtime",
    name: "Switchman Runtime",
    archetype: "switchman",
    pillarId: "execution-runtime-safety",
    committeeId: "governance-council",
    authorityLevel: "approval",
    allowedSkillIds: ["skill-policy-review"],
    forbiddenActions: ["route_without_policy", "skip_runtime_controls"],
    requiredOutput: "runtime execution path",
    reviewer: "Governance Council",
    archivePath: "archives/core/runtime/switchman-runtime",
    requiredEnvKeys: ["UACP_INTERNAL_API_KEY"],
    status: "ready",
    promotionMetric: "Safe routing adherence",
    demotionTrigger: "Runtime policy bypass",
    currentJob: "Attach runtime policies and approval path",
  },
  {
    id: "curator-market",
    name: "Curator Market",
    archetype: "curator",
    pillarId: "model-tool-governance",
    committeeId: "marketplace-council",
    authorityLevel: "approval",
    allowedSkillIds: ["skill-competitive-intel", "skill-marketplace-curation"],
    forbiddenActions: ["approve_unpinned_tooling", "package_unreviewed_capability"],
    requiredOutput: "governed package brief",
    reviewer: "Marketplace Council",
    archivePath: "archives/core/marketplace/curator-market",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Sellable package acceptance rate",
    demotionTrigger: "Packaging ungoverned tools",
    currentJob: "Translate signals into approved marketplace packages",
  },
  {
    id: "builder-package",
    name: "Builder Package",
    archetype: "builder",
    pillarId: "model-tool-governance",
    committeeId: "marketplace-council",
    authorityLevel: "operational",
    allowedSkillIds: ["skill-marketplace-curation"],
    forbiddenActions: ["ship_without_committee_review", "clone_external_repos"],
    requiredOutput: "proposed package/tool",
    reviewer: "Marketplace Council",
    archivePath: "archives/core/builders/builder-package",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Original package readiness",
    demotionTrigger: "Unreviewed or derivative package generation",
    currentJob: "Shape an approved sellable offer from vetted capability inputs",
  },
  {
    id: "scout-revenue",
    name: "Scout Revenue",
    archetype: "scout",
    pillarId: "research-knowledge-learning",
    committeeId: "research-command",
    authorityLevel: "operational",
    allowedSkillIds: ["skill-competitive-intel"],
    forbiddenActions: ["invent_sources", "publish_without_review"],
    requiredOutput: "competitor weakness and buyer pain brief",
    reviewer: "Research Command",
    archivePath: "archives/core/research/scout-revenue",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Revenue-relevant opportunity quality",
    demotionTrigger: "Unsupported signal generation",
    currentJob: "Identify competitor weakness that can become revenue",
  },
  {
    id: "steward-tenant",
    name: "Steward Tenant",
    archetype: "steward",
    pillarId: "tenant-experience-integration",
    committeeId: "marketplace-council",
    authorityLevel: "operational",
    allowedSkillIds: ["skill-marketplace-curation", "skill-archive-bundler"],
    forbiddenActions: ["hide_governance_state", "omit_next_action"],
    requiredOutput: "tenant-facing next action and package framing",
    reviewer: "Marketplace Council",
    archivePath: "archives/core/tenant/steward-tenant",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Clarity of buyer-facing execution framing",
    demotionTrigger: "Missing buyer next action",
    currentJob: "Make the governed package legible to the buyer and tenant",
  },
  {
    id: "steward-archive",
    name: "Steward Archive",
    archetype: "steward",
    pillarId: "evidence-audit-archives",
    committeeId: "archives-board",
    authorityLevel: "approval",
    allowedSkillIds: ["skill-archive-bundler"],
    forbiddenActions: ["overwrite_source_run", "drop_event_lineage"],
    requiredOutput: "archive record",
    reviewer: "Archives Board",
    archivePath: "archives/core/evidence/steward-archive",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Replayable archive completeness",
    demotionTrigger: "Archive written without event lineage",
    currentJob: "Write replayable archive bundles and preserve source run integrity",
  },
  {
    id: "treasurer-reserve",
    name: "Treasurer Reserve",
    archetype: "treasurer",
    pillarId: "economics-operating-reserve",
    committeeId: "reserve-board",
    authorityLevel: "approval",
    allowedSkillIds: ["skill-reserve-pricing", "skill-archive-bundler"],
    forbiddenActions: ["omit_margin_logic", "approve_unpriced_offer"],
    requiredOutput: "pricing hypothesis and reserve view",
    reviewer: "Reserve Board",
    archivePath: "archives/core/finance/treasurer-reserve",
    requiredEnvKeys: [],
    status: "ready",
    promotionMetric: "Margin-backed offer quality",
    demotionTrigger: "Offer approved without economics trace",
    currentJob: "Attach pricing, margin, and reserve logic to governed opportunities",
  },
];

function emptyState(): RuntimeState {
  return {
    plans: [],
    runs: [],
    operatorRuns: [],
    workerRuntime: [],
    outboundContacts: [],
    outboundMessages: [],
    backendEvents: [],
    backendSummary: emptyBackendTruthSummary(),
    events: [],
    archives: [],
    v3Plans: [],
    v3Runs: [],
    v3Events: [],
    v3Archives: [],
    v3ReplayRequests: [],
    v3ReplayResults: [],
    v3CommercialArtifacts: [],
    v3CommercialScorecard: emptyCommercialScorecard(),
    researchSignals: [],
    researchStatus: [],
    stats: {
      planCompileDurationsMs: [],
      runDurationsMs: [],
      researchRefreshDurationsMs: [],
      determinismHistory: [],
      runCompletionHistory: [],
      policyAlignmentHistory: [],
      archiveCoverageHistory: [],
      sourceHealthHistory: [],
      pressureHistory: [],
      lastGovernanceRegistryHash: undefined,
      lastGovernanceRegistrySyncAt: undefined,
    },
  };
}

function createId(prefix: string) {
  return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
}

function now() {
  return new Date().toISOString();
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function average(values: number[]) {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function pushWindow(values: number[], value: number) {
  values.push(value);
  if (values.length > HISTORY_WINDOW) {
    values.splice(0, values.length - HISTORY_WINDOW);
  }
}

function uniqueStrings(values: string[]) {
  return [...new Set(values)];
}

function operationalEvidenceCount(inputs: string[]) {
  return inputs.filter((input) => /^(backend|event|archive|signal|source|plan|run):/.test(input)).length;
}

function systemHasOperationalEvidenceInventory() {
  return (
    state.backendEvents.length > 0 ||
    state.events.length > 0 ||
    state.archives.length > 0 ||
    state.researchSignals.length > 0 ||
    state.researchStatus.length > 0 ||
    state.plans.length > 0 ||
    state.runs.length > 0
  );
}

function parseProviderOrder(value: string): ModelProviderId[] {
  const allowed = new Set<ModelProviderId>(["groq", "huggingface", "ollama", "gemini"]);
  return uniqueStrings(
    value
      .split(/[,\s]+/)
      .map((provider) => provider.trim().toLowerCase())
      .filter((provider): provider is ModelProviderId => allowed.has(provider as ModelProviderId)),
  ) as ModelProviderId[];
}

function providerLabel(provider: ModelProviderId) {
  switch (provider) {
    case "groq":
      return "Groq";
    case "huggingface":
      return "Hugging Face";
    case "ollama":
      return "Ollama";
    case "gemini":
      return "Gemini";
    default:
      return "Deterministic";
  }
}

function requestedProvider(): ModelProviderId | undefined {
  if (!REQUESTED_MODEL_PROVIDER) return undefined;
  return ["groq", "huggingface", "ollama", "gemini", "deterministic"].includes(REQUESTED_MODEL_PROVIDER)
    ? REQUESTED_MODEL_PROVIDER as ModelProviderId
    : undefined;
}

function providerConfigured(provider: Exclude<ModelProviderId, "deterministic">) {
  switch (provider) {
    case "groq":
      return GROQ_API_KEY.length > 0;
    case "huggingface":
      return HF_TOKEN.length > 0;
    case "ollama":
      return OLLAMA_MODEL.length > 0;
    case "gemini":
      return Boolean(ai);
  }
}

function providerModelName(provider: Exclude<ModelProviderId, "deterministic">) {
  switch (provider) {
    case "groq":
      return GROQ_MODEL;
    case "huggingface":
      return HF_MODEL;
    case "ollama":
      return OLLAMA_MODEL;
    case "gemini":
      return GEMINI_MODEL;
  }
}

function providerBaseUrl(provider: Exclude<ModelProviderId, "deterministic">) {
  switch (provider) {
    case "groq":
      return GROQ_BASE_URL;
    case "huggingface":
      return HF_BASE_URL;
    case "ollama":
      return OLLAMA_BASE_URL;
    case "gemini":
      return undefined;
  }
}

function providerPreferenceOrder(): Exclude<ModelProviderId, "deterministic">[] {
  const order = [...MODEL_PROVIDER_ORDER];
  const explicit = requestedProvider();
  const normalized = order.filter((provider): provider is Exclude<ModelProviderId, "deterministic"> => provider !== "deterministic");
  const baseOrder = explicit && explicit !== "deterministic"
    ? [explicit, ...normalized.filter((provider) => provider !== explicit)]
    : normalized;

  if (explicit === "gemini" || GEMINI_PRIMARY_ENABLED || ALLOW_GEMINI_FALLBACK) {
    return uniqueStrings([...baseOrder, "gemini"]) as Exclude<ModelProviderId, "deterministic">[];
  }

  return baseOrder.filter((provider) => provider !== "gemini");
}

function modelProviderCacheTtlMs() {
  return 30_000;
}

async function checkOllamaReady() {
  if (!OLLAMA_MODEL) {
    return {
      health: "missing" as const,
      detail: "OLLAMA_MODEL is not configured.",
    };
  }

  try {
    const response = await fetch(`${OLLAMA_BASE_URL}/api/tags`, {
      headers: OLLAMA_API_KEY ? { Authorization: `Bearer ${OLLAMA_API_KEY}` } : undefined,
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      return {
        health: "degraded" as const,
        detail: `Ollama responded ${response.status} ${response.statusText}.`,
      };
    }

    const parsed = await response.json() as { models?: Array<{ name?: string; model?: string }> };
    const knownModels = parsed.models ?? [];
    const hasModel = knownModels.some((entry) => entry.name === OLLAMA_MODEL || entry.model === OLLAMA_MODEL);
    return {
      health: hasModel ? "ready" as const : "degraded" as const,
      detail: hasModel
        ? `Ollama is reachable and model ${OLLAMA_MODEL} is available.`
        : `Ollama is reachable but model ${OLLAMA_MODEL} is not listed.`,
    };
  } catch (error) {
    return {
      health: "degraded" as const,
      detail: error instanceof Error ? `Ollama unreachable: ${error.message}` : "Ollama unreachable.",
    };
  }
}

async function getProviderSnapshot(force = false): Promise<ModelProviderSnapshot> {
  if (!force && providerSnapshotCache && Date.now() - providerSnapshotCache.fetchedAt < modelProviderCacheTtlMs()) {
    return providerSnapshotCache.snapshot;
  }

  const explicit = requestedProvider();
  const order = providerPreferenceOrder();
  const geminiEnabled = explicit === "gemini" || GEMINI_PRIMARY_ENABLED || ALLOW_GEMINI_FALLBACK;
  const ollamaState = await checkOllamaReady();

  const statuses: ModelProviderStatus[] = [
    {
      id: "groq",
      label: providerLabel("groq"),
      health: GROQ_API_KEY ? "ready" : "missing",
      configured: providerConfigured("groq"),
      active: false,
      model: providerModelName("groq"),
      baseUrl: providerBaseUrl("groq"),
      detail: GROQ_API_KEY
        ? `Configured for OpenAI-compatible chat completions at ${GROQ_BASE_URL}.`
        : "GROQ_API_KEY is missing.",
    },
    {
      id: "huggingface",
      label: providerLabel("huggingface"),
      health: HF_TOKEN ? "ready" : "missing",
      configured: providerConfigured("huggingface"),
      active: false,
      model: providerModelName("huggingface"),
      baseUrl: providerBaseUrl("huggingface"),
      detail: HF_TOKEN
        ? `Configured for OpenAI-compatible inference routing at ${HF_BASE_URL}.`
        : "HF_TOKEN is missing.",
    },
    {
      id: "ollama",
      label: providerLabel("ollama"),
      health: ollamaState.health,
      configured: providerConfigured("ollama"),
      active: false,
      model: providerModelName("ollama"),
      baseUrl: providerBaseUrl("ollama"),
      detail: ollamaState.detail,
    },
    {
      id: "gemini",
      label: providerLabel("gemini"),
      health: ai ? (geminiEnabled ? "ready" : "disabled") : "missing",
      configured: providerConfigured("gemini"),
      active: false,
      model: providerModelName("gemini"),
      detail: ai
        ? geminiEnabled
          ? "Configured and eligible as a fallback model council provider."
          : "Configured but held in reserve; Gemini is not primary in this runtime."
        : "GEMINI_API_KEY is missing.",
    },
  ];

  const readyLookup = new Map(statuses.map((status) => [status.id, status.health === "ready"]));
  const activeProvider = explicit === "deterministic"
    ? "deterministic"
    : order.find((provider) => readyLookup.get(provider)) || "deterministic";
  const defaultProvider = explicit || order[0] || "deterministic";

  const snapshot: ModelProviderSnapshot = {
    defaultProvider,
    activeProvider,
    allowGeminiFallback: ALLOW_GEMINI_FALLBACK || GEMINI_PRIMARY_ENABLED || explicit === "gemini",
    updatedAt: now(),
    statuses: statuses.map((status) => ({
      ...status,
      active: status.id === activeProvider,
    })),
  };

  providerSnapshotCache = {
    snapshot,
    fetchedAt: Date.now(),
  };

  return snapshot;
}

function trimText(value: string, length: number) {
  const compact = value.replace(/\s+/g, " ").trim();
  return compact.length <= length ? compact : `${compact.slice(0, length - 3)}...`;
}

function normalizeTitle(value: unknown) {
  return String(value || "Untitled").replace(/\s+/g, " ").trim();
}

function parseDate(value: unknown) {
  if (!value) return now();
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? now() : parsed.toISOString();
}

function daysSince(isoDate: string) {
  const millis = new Date(isoDate).getTime();
  if (Number.isNaN(millis)) return 365;
  return Math.max(0, (Date.now() - millis) / (1000 * 60 * 60 * 24));
}

function tokenize(text: string) {
  const stopwords = new Set([
    "the", "and", "for", "with", "that", "this", "into", "from", "your", "about", "using",
    "build", "create", "make", "want", "need", "plan", "system", "teams", "team", "serious",
    "then", "they", "them", "their", "there", "have", "will", "what", "when", "where",
  ]);
  const shortTokens = new Set(["ai", "ml", "ui", "ux"]);

  return uniqueStrings(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter((token) => (token.length > 2 || shortTokens.has(token)) && !stopwords.has(token)),
  );
}

function normalizeSearchText(text: string) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function countTokenMatches(tokens: string[], haystack: string) {
  const haystackTokens = new Set(tokenize(haystack));
  return tokens.filter((token) => haystackTokens.has(token)).length;
}

function countPhraseMatches(phrases: string[], haystack: string) {
  const normalized = normalizeSearchText(haystack);
  return phrases.filter((phrase) => normalized.includes(phrase)).length;
}

function shouldUsePubMed(query: string) {
  const normalized = normalizeSearchText(query);
  return HEALTH_RESEARCH_TERMS.some((term) => normalized.includes(term));
}

function buildResearchTokens(text: string) {
  const tokens = tokenize(text);
  return uniqueStrings([...tokens, ...CORE_RESEARCH_ANCHORS]).slice(0, 12);
}

function buildResearchQuery(text: string) {
  const tokens = buildResearchTokens(text);
  return tokens.length > 0 ? tokens.join(" ") : DEFAULT_RESEARCH_QUERY;
}

function textRelevance(tokens: string[], haystack: string) {
  if (tokens.length === 0) return 0.15;
  const matches = countTokenMatches(tokens, haystack);
  return matches / tokens.length;
}

function computeSignalStrength(sourceBias: number, query: string, signalText: string, publishedAt: string) {
  const queryTokens = tokenize(query).slice(0, 10);
  const queryCoverage = textRelevance(queryTokens, signalText);
  const generalCoverage = clamp(countTokenMatches(GENERAL_AI_RESEARCH_ANCHORS, signalText) / 3, 0, 1);
  const controlCoverage = clamp(countTokenMatches(CONTROL_PLANE_RESEARCH_ANCHORS, signalText) / 2, 0, 1);
  const phraseCoverage = clamp(countPhraseMatches(CORE_RESEARCH_PHRASES, signalText) / 2, 0, 1);
  const domainFit = clamp(
    (queryCoverage * 0.2) + (generalCoverage * 0.15) + (controlCoverage * 0.45) + (phraseCoverage * 0.2),
    0,
    1,
  );
  const recency = clamp(1 - daysSince(publishedAt) / 365, 0, 1);
  return Math.round(clamp(25 + (domainFit * 50) + (recency * 10) + (sourceBias * 0.75), 10, 99));
}

function isRelevantResearchSignal(query: string, signal: ResearchSignal) {
  const headlineText = `${signal.title} ${signal.category}`;
  const searchText = `${signal.title} ${signal.abstract || ""} ${signal.category} ${(signal.authors || []).join(" ")}`;
  const queryTokens = tokenize(query).slice(0, 10);
  const queryCoverage = textRelevance(queryTokens, searchText);
  const generalMatchCount = countTokenMatches(GENERAL_AI_RESEARCH_ANCHORS, searchText);
  const controlMatchCount = countTokenMatches(CONTROL_PLANE_RESEARCH_ANCHORS, searchText);
  const headlineGeneralMatches = countTokenMatches(GENERAL_AI_RESEARCH_ANCHORS, headlineText);
  const headlineControlMatches = countTokenMatches(CONTROL_PLANE_RESEARCH_ANCHORS, headlineText);
  const generalCoverage = clamp(generalMatchCount / 3, 0, 1);
  const controlCoverage = clamp(controlMatchCount / 2, 0, 1);
  const phraseCoverage = clamp(countPhraseMatches(CORE_RESEARCH_PHRASES, searchText) / 2, 0, 1);
  const headlinePhraseMatches = countPhraseMatches(CORE_RESEARCH_PHRASES, headlineText);
  const domainFit = clamp(
    (queryCoverage * 0.2) + (generalCoverage * 0.15) + (controlCoverage * 0.45) + (phraseCoverage * 0.2),
    0,
    1,
  );
  const hasInstitutionalSignal = headlineControlMatches >= 1 || headlinePhraseMatches > 0;
  const hasEnoughCoverage = (headlineGeneralMatches >= 1 && headlineControlMatches >= 1) || headlinePhraseMatches > 0;

  return hasInstitutionalSignal && hasEnoughCoverage && domainFit >= 0.18 && signal.strength >= 48;
}

function toReference(signal: ResearchSignal): CompiledArtifactReference {
  return {
    title: signal.title,
    source: signal.source,
    url: signal.url,
    publishedAt: signal.publishedAt,
  };
}

function makeStatus(
  id: string,
  name: string,
  startedAt: number,
  itemCount: number,
  error?: string,
): ResearchSourceStatus {
  const latency = Date.now() - startedAt;
  return {
    id,
    name,
    status: error ? (itemCount > 0 ? "degraded" : "offline") : "online",
    lastSyncAt: now(),
    lastLatencyMs: latency,
    itemCount,
    error,
  };
}

function byRecencyAndStrength(a: ResearchSignal, b: ResearchSignal) {
  if (b.strength !== a.strength) return b.strength - a.strength;
  return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
}

async function fetchText(url: string) {
  const response = await fetch(url, {
    headers: { "User-Agent": `${TOOL_NAME} (${CONTACT_EMAIL})` },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.text();
}

async function fetchJson<T>(url: string) {
  const response = await fetch(url, {
    headers: { "User-Agent": `${TOOL_NAME} (${CONTACT_EMAIL})` },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function fetchInternalBackendJson<T>(pathname: string) {
  if (!UACP_BACKEND_BASE_URL) {
    throw new Error("UACP_BACKEND_BASE_URL is not configured.");
  }
  if (!INTERNAL_API_KEY) {
    throw new Error("UACP_INTERNAL_API_KEY is not configured.");
  }

  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  const response = await fetch(`${UACP_BACKEND_BASE_URL}${normalizedPath}`, {
    headers: {
      "User-Agent": `${TOOL_NAME} (${CONTACT_EMAIL})`,
      "x-uacp-internal-key": INTERNAL_API_KEY,
    },
    signal: AbortSignal.timeout(UACP_BACKEND_TIMEOUT_MS),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}${body ? ` :: ${trimText(body, 220)}` : ""}`);
  }

  return response.json() as Promise<T>;
}

async function fetchProviderJson<T>(url: string, init: RequestInit, timeoutMs = 20000) {
  const response = await fetch(url, {
    ...init,
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}${body ? ` :: ${trimText(body, 220)}` : ""}`);
  }
  return response.json() as Promise<T>;
}

function stripMarkdownFences(text: string) {
  return text
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();
}

function extractJsonObject(text: string) {
  const stripped = stripMarkdownFences(text);
  if (stripped.startsWith("{") && stripped.endsWith("}")) {
    return stripped;
  }

  const firstBrace = stripped.indexOf("{");
  const lastBrace = stripped.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    return stripped.slice(firstBrace, lastBrace + 1);
  }

  return stripped;
}

function parseJsonObject<T>(text: string) {
  return JSON.parse(extractJsonObject(text)) as T;
}

async function callGroq(messages: ChatMessage[], options: ProviderPromptOptions): Promise<ProviderTextResponse> {
  const response = await fetchProviderJson<{
    choices?: Array<{ message?: { content?: string } }>;
  }>(`${GROQ_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GROQ_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      messages,
      temperature: options.temperature ?? 0.2,
      max_tokens: options.maxTokens ?? 2000,
    }),
  });

  const text = response.choices?.[0]?.message?.content?.trim();
  if (!text) {
    throw new Error("Groq returned no message content.");
  }

  return {
    provider: "groq",
    model: GROQ_MODEL,
    text,
  };
}

async function callHuggingFace(messages: ChatMessage[], options: ProviderPromptOptions): Promise<ProviderTextResponse> {
  const response = await fetchProviderJson<{
    choices?: Array<{ message?: { content?: string } }>;
  }>(`${HF_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${HF_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: HF_MODEL,
      messages,
      temperature: options.temperature ?? 0.2,
      max_tokens: options.maxTokens ?? 2000,
    }),
  });

  const text = response.choices?.[0]?.message?.content?.trim();
  if (!text) {
    throw new Error("Hugging Face returned no message content.");
  }

  return {
    provider: "huggingface",
    model: HF_MODEL,
    text,
  };
}

async function callOllama(messages: ChatMessage[], options: ProviderPromptOptions): Promise<ProviderTextResponse> {
  const response = await fetchProviderJson<{
    message?: { content?: string };
  }>(`${OLLAMA_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(OLLAMA_API_KEY ? { Authorization: `Bearer ${OLLAMA_API_KEY}` } : {}),
    },
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      messages,
      stream: false,
      format: options.jsonMode ? "json" : undefined,
      options: {
        temperature: options.temperature ?? 0.2,
      },
      keep_alive: "10m",
    }),
  });

  const text = response.message?.content?.trim();
  if (!text) {
    throw new Error("Ollama returned no message content.");
  }

  return {
    provider: "ollama",
    model: OLLAMA_MODEL,
    text,
  };
}

async function callGemini(messages: ChatMessage[]): Promise<ProviderTextResponse> {
  if (!ai) {
    throw new Error("Gemini is not configured.");
  }

  const prompt = messages
    .map((message) => `${message.role.toUpperCase()}:\n${message.content}`)
    .join("\n\n");

  const result = await ai.models.generateContent({
    model: GEMINI_MODEL,
    contents: [
      {
        role: "user",
        parts: [{ text: prompt }],
      },
    ],
  });

  const text = result.text?.trim();
  if (!text) {
    throw new Error("Gemini returned no message content.");
  }

  return {
    provider: "gemini",
    model: GEMINI_MODEL,
    text,
  };
}

async function completeWithProviderChain(messages: ChatMessage[], options: ProviderPromptOptions = {}) {
  const snapshot = await getProviderSnapshot();
  const explicit = requestedProvider();
  const orderedProviders =
    explicit && explicit !== "deterministic"
      ? [explicit, ...providerPreferenceOrder().filter((provider) => provider !== explicit)]
      : providerPreferenceOrder();

  const errors: string[] = [];

  for (const provider of orderedProviders) {
    const status = snapshot.statuses.find((entry) => entry.id === provider);
    if (!status || status.health !== "ready") {
      continue;
    }

    try {
      if (provider === "groq") return await callGroq(messages, options);
      if (provider === "huggingface") return await callHuggingFace(messages, options);
      if (provider === "ollama") return await callOllama(messages, options);
      if (provider === "gemini") return await callGemini(messages);
    } catch (error) {
      errors.push(`${provider}: ${error instanceof Error ? error.message : "unknown error"}`);
    }
  }

  if (errors.length > 0) {
    console.warn("Model provider chain failed:", errors.join(" | "));
  }

  return null;
}

async function fetchArxivSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const tokens = buildResearchTokens(query).slice(0, 8);
    const searchQuery = tokens.length > 0
      ? `all:(${tokens.map((token) => `"${token}"`).join(" OR ")})`
      : `all:(${buildResearchTokens(DEFAULT_RESEARCH_QUERY).slice(0, 6).map((token) => `"${token}"`).join(" OR ")})`;
    const xml = await fetchText(
      `https://export.arxiv.org/api/query?search_query=${encodeURIComponent(searchQuery)}&start=0&max_results=${limit}&sortBy=lastUpdatedDate&sortOrder=descending`,
    );
    const parsed = parser.parse(xml);
    const entries = Array.isArray(parsed.feed?.entry)
      ? parsed.feed.entry
      : parsed.feed?.entry
        ? [parsed.feed.entry]
        : [];

    const signals = entries.map((entry: any) => {
      const publishedAt = parseDate(entry.updated || entry.published);
      const title = normalizeTitle(entry.title);
      const summary = trimText(String(entry.summary || ""), 400);
      const authors = Array.isArray(entry.author)
        ? entry.author.map((author: any) => normalizeTitle(author.name))
        : entry.author
          ? [normalizeTitle(entry.author.name)]
          : [];

      return {
        id: `arxiv-${String(entry.id || title).split("/").pop()}`,
        source: "arXiv",
        title,
        category: "Research",
        strength: computeSignalStrength(18, query, `${title} ${summary}`, publishedAt),
        publishedAt,
        url: entry.id,
        abstract: summary,
        authors,
      } satisfies ResearchSignal;
    });

    return {
      signals,
      status: makeStatus("arxiv", "arXiv", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("arxiv", "arXiv", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchPubMedSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const esearch = await fetchJson<{
      esearchresult?: { idlist?: string[] };
    }>(
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=${limit}&sort=pub+date&tool=${encodeURIComponent(TOOL_NAME)}&email=${encodeURIComponent(CONTACT_EMAIL)}&term=${encodeURIComponent(query)}`,
    );

    const ids = esearch.esearchresult?.idlist ?? [];
    if (ids.length === 0) {
      return {
        signals: [],
        status: makeStatus("pubmed", "PubMed", startedAt, 0),
      };
    }

    const esummary = await fetchJson<{
      result?: Record<string, any> & { uids?: string[] };
    }>(
      `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&tool=${encodeURIComponent(TOOL_NAME)}&email=${encodeURIComponent(CONTACT_EMAIL)}&id=${ids.join(",")}`,
    );

    const summary = esummary.result ?? {};
    const signals = ids
      .map((id) => summary[id])
      .filter(Boolean)
      .map((entry) => {
        const publishedAt = parseDate(entry.pubdate || entry.sortpubdate);
        const title = normalizeTitle(entry.title);
        const authors = Array.isArray(entry.authors)
          ? entry.authors.map((author: any) => normalizeTitle(author.name))
          : [];

        return {
          id: `pubmed-${entry.uid}`,
          source: "PubMed",
          title,
          category: "Biomedical",
          strength: computeSignalStrength(20, query, `${title} ${entry.fulljournalname || ""}`, publishedAt),
          publishedAt,
          url: `https://pubmed.ncbi.nlm.nih.gov/${entry.uid}/`,
          authors,
        } satisfies ResearchSignal;
      });

    return {
      signals,
      status: makeStatus("pubmed", "PubMed", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("pubmed", "PubMed", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchCrossrefSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const response = await fetchJson<{
      message?: { items?: Array<Record<string, any>> };
    }>(
      `https://api.crossref.org/works?query.bibliographic=${encodeURIComponent(query)}&rows=${limit}&sort=published&order=desc&select=DOI,title,URL,published,created,subject,author,type&mailto=${encodeURIComponent(CONTACT_EMAIL)}`,
    );

    const items = response.message?.items ?? [];
    const signals = items.map((item) => {
      const dateParts = item.published?.["date-parts"]?.[0] || item.created?.["date-parts"]?.[0];
      const publishedAt = Array.isArray(dateParts)
        ? parseDate(new Date(dateParts[0], (dateParts[1] || 1) - 1, dateParts[2] || 1).toISOString())
        : now();
      const title = normalizeTitle(Array.isArray(item.title) ? item.title[0] : item.title);
      const authors = Array.isArray(item.author)
        ? item.author.map((author: any) => normalizeTitle([author.given, author.family].filter(Boolean).join(" ")))
        : [];
      const subject = Array.isArray(item.subject) ? item.subject.join(", ") : item.type || "Crossref";

      return {
        id: `crossref-${item.DOI || createId("doi")}`,
        source: "Crossref",
        title,
        category: subject || "Crossref",
        strength: computeSignalStrength(14, query, `${title} ${subject}`, publishedAt),
        publishedAt,
        url: item.URL,
        authors,
        doi: item.DOI,
      } satisfies ResearchSignal;
    });

    return {
      signals,
      status: makeStatus("crossref", "Crossref", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("crossref", "Crossref", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchSsrnSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const response = await fetch(
      `https://papers.ssrn.com/searchresults.cfm?txtKey_Words=${encodeURIComponent(query)}`,
      {
        headers: {
          "user-agent": `${TOOL_NAME}/1.0 (${CONTACT_EMAIL})`,
          "accept": "text/html,application/xhtml+xml",
        },
      },
    );

    const html = await response.text();
    if (!response.ok || /just a moment/i.test(html) || /challenges.cloudflare.com/i.test(html)) {
      throw new Error("SSRN blocked automated fetch with an anti-bot challenge.");
    }

    const linkMatches = [...html.matchAll(/href="([^"]*abstract_id=\d+[^"]*)"[^>]*>(.*?)<\/a>/gi)];
    const seen = new Set<string>();
    const signals: ResearchSignal[] = [];

    for (const match of linkMatches) {
      const rawHref = match[1] || "";
      const rawTitle = match[2] || "";
      const abstractId = rawHref.match(/abstract_id=(\d+)/i)?.[1];
      const title = normalizeTitle(rawTitle.replace(/<[^>]+>/g, " "));

      if (!abstractId || !title || seen.has(abstractId)) {
        continue;
      }

      seen.add(abstractId);
      signals.push({
        id: `ssrn-${abstractId}`,
        source: "SSRN",
        title,
        category: "Business & Governance",
        strength: computeSignalStrength(19, query, `${title} ssrn governance business policy`, now()),
        publishedAt: now(),
        url: rawHref.startsWith("http") ? rawHref : `https://papers.ssrn.com${rawHref}`,
      });

      if (signals.length >= limit) {
        break;
      }
    }

    return {
      signals,
      status: makeStatus("ssrn", "SSRN", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("ssrn", "SSRN", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchOpenAlexSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const response = await fetchJson<{
      results?: Array<Record<string, any>>;
    }>(
      `https://api.openalex.org/works?search=${encodeURIComponent(query)}&per-page=${limit}&mailto=${encodeURIComponent(CONTACT_EMAIL)}`,
    );

    const items = response.results ?? [];
    const signals = items.map((item) => {
      const title = normalizeTitle(item.display_name || item.title);
      const publishedAt = parseDate(item.publication_date || item.publication_year || now());
      const sourceName =
        item.primary_topic?.display_name ||
        item.primary_location?.source?.display_name ||
        item.type ||
        "OpenAlex";
      const authors = Array.isArray(item.authorships)
        ? item.authorships
            .map((authorship: any) => normalizeTitle(authorship?.author?.display_name || ""))
            .filter(Boolean)
        : [];
      const businessBoost = /(market|pricing|revenue|buyer|enterprise|policy|governance|regulat|risk|compliance)/i.test(
        `${title} ${sourceName}`,
      )
        ? 5
        : 0;

      return {
        id: `openalex-${String(item.id || createId("oa")).split("/").pop()}`,
        source: "OpenAlex",
        title,
        category: sourceName,
        strength: computeSignalStrength(16 + businessBoost, query, `${title} ${sourceName}`, publishedAt),
        publishedAt,
        url: item.primary_location?.landing_page_url || item.id || item.doi,
        abstract: undefined,
        authors,
        doi: typeof item.doi === "string" ? item.doi.replace(/^https?:\/\/doi.org\//i, "") : undefined,
      } satisfies ResearchSignal;
    });

    return {
      signals,
      status: makeStatus("openalex", "OpenAlex", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("openalex", "OpenAlex", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchZenodoSignals(query: string, limit: number) {
  const startedAt = Date.now();
  try {
    const response = await fetchJson<{
      hits?: { hits?: Array<Record<string, any>> };
    }>(
      `https://zenodo.org/api/records?q=${encodeURIComponent(query)}&sort=mostrecent&page=1&size=${limit}`,
    );

    const hits = response.hits?.hits ?? [];
    const signals = hits.map((hit) => {
      const metadata = hit.metadata ?? {};
      const title = normalizeTitle(metadata.title || hit.title);
      const publishedAt = parseDate(metadata.publication_date || hit.created || hit.updated);
      const creators = Array.isArray(metadata.creators)
        ? metadata.creators.map((creator: any) => normalizeTitle(creator.name))
        : [];

      return {
        id: `zenodo-${hit.id || createId("zen")}`,
        source: "Zenodo",
        title,
        category: metadata.resource_type?.title || metadata.upload_type || "Repository",
        strength: computeSignalStrength(12, query, `${title} ${metadata.description || ""}`, publishedAt),
        publishedAt,
        url: hit.links?.html || hit.links?.self_html || hit.links?.self,
        abstract: metadata.description ? trimText(String(metadata.description), 400) : undefined,
        authors: creators,
        doi: metadata.doi,
      } satisfies ResearchSignal;
    });

    return {
      signals,
      status: makeStatus("zenodo", "Zenodo", startedAt, signals.length),
    };
  } catch (error) {
    return {
      signals: [],
      status: makeStatus("zenodo", "Zenodo", startedAt, 0, error instanceof Error ? error.message : "Unknown error"),
    };
  }
}

async function fetchLiveResearch(query: string, limitPerSource = 4): Promise<ResearchFetchResult> {
  const startedAt = Date.now();
  const rawLimit = Math.max(limitPerSource, 4) * 3;
  const sourceFetches = [
    fetchArxivSignals(query, rawLimit),
    fetchSsrnSignals(query, rawLimit),
    fetchOpenAlexSignals(query, rawLimit),
    fetchCrossrefSignals(query, rawLimit),
    fetchZenodoSignals(query, rawLimit),
  ];

  if (shouldUsePubMed(query)) {
    sourceFetches.push(fetchPubMedSignals(query, rawLimit));
  }

  const results = await Promise.all(sourceFetches);

  const deduped = new Map<string, ResearchSignal>();
  for (const result of results) {
    for (const signal of result.signals) {
      if (!isRelevantResearchSignal(query, signal)) {
        continue;
      }
      const key = signal.doi || signal.url || `${signal.source}:${signal.title.toLowerCase()}`;
      const existing = deduped.get(key);
      if (!existing || byRecencyAndStrength(signal, existing) < 0) {
        deduped.set(key, signal);
      }
    }
  }

  const signals = [...deduped.values()].sort(byRecencyAndStrength).slice(0, MAX_SIGNALS);
  const statuses = results.map((result) => result.status);

  return {
    signals,
    statuses,
    durationMs: Date.now() - startedAt,
  };
}

function keywordMatch(intent: string, keywords: string[]) {
  const normalized = intent.toLowerCase();
  return keywords.some((keyword) => normalized.includes(keyword));
}

function selectPillars(intent: string, signals: ResearchSignal[]) {
  const selected = new Set<string>(["governance", "engineering", "operations"]);
  const signalText = signals.map((signal) => `${signal.title} ${signal.category}`).join(" ").toLowerCase();
  const combined = `${intent.toLowerCase()} ${signalText}`;

  if (keywordMatch(combined, ["product", "feature", "onboarding", "ux", "workflow"])) selected.add("product");
  if (keywordMatch(combined, ["growth", "traffic", "distribution", "pipeline", "competitor", "market"])) selected.add("growth");
  if (keywordMatch(combined, ["sales", "buyer", "account", "deal", "revenue"])) selected.add("sales");
  if (keywordMatch(combined, ["finance", "pricing", "margin", "billing", "roi"])) selected.add("finance");
  if (keywordMatch(combined, ["compliance", "risk", "legal", "regulated", "privacy", "security"])) selected.add("compliance-risk");
  if (signals.length > 0) selected.add("knowledge-research");

  return activePillars().filter((pillar) => selected.has(pillar.id)).map((pillar) => pillar.id);
}

function selectCommittees(pillarIds: string[]) {
  const selected = new Set<string>(["founder-council", "execution-board"]);
  if (pillarIds.includes("knowledge-research") || pillarIds.includes("growth") || pillarIds.includes("product")) {
    selected.add("signal-council");
  }
  return activeCommittees().filter((committee) => committee.id && [...selected].includes(committee.id)).map((committee) => committee.id);
}

function selectRiskTier(intent: string, signals: ResearchSignal[]): RiskTier {
  const normalized = `${intent.toLowerCase()} ${signals.map((signal) => signal.category).join(" ").toLowerCase()}`;
  if (keywordMatch(normalized, ["regulated", "medical", "health", "privacy", "compliance", "legal"])) return "high";
  if (keywordMatch(normalized, ["finance", "security", "billing", "customer data"])) return "medium";
  return "low";
}

function selectWorkflowIds(pillarIds: string[]) {
  return activeWorkflows()
    .filter((workflow) => workflow.pillarIds.some((pillarId) => pillarIds.includes(pillarId)))
    .map((workflow) => workflow.id);
}

function selectSkillIds(pillarIds: string[]) {
  return activeSkills()
    .filter((skill) => skill.status === "approved" && skill.pillarIds.some((pillarId) => pillarIds.includes(pillarId)))
    .map((skill) => skill.id);
}

function selectEscalationRuleIds(intent: string, pillarIds: string[], riskTier: RiskTier, signals: ResearchSignal[], skillIds: string[]) {
  const normalized = intent.toLowerCase();
  const matches = new Set<string>();

  for (const rule of activeEscalationRules()) {
    if (!rule.pillarIds.some((pillarId) => pillarIds.includes(pillarId))) continue;
    if (rule.id === "missing-live-evidence" && signals.length === 0) matches.add(rule.id);
    if (rule.id === "unapproved-skill-attempt" && skillIds.length === 0) matches.add(rule.id);
    if (rule.id === "regulated-objective-review" && (riskTier === "high" || keywordMatch(normalized, ["regulated", "privacy", "legal", "compliance"]))) {
      matches.add(rule.id);
    }
  }

  return activeEscalationRules().filter((rule) => matches.has(rule.id)).map((rule) => rule.id);
}

function mergeProposals(proposals: GovernanceProposal[]) {
  const seen = new Set<string>();
  return proposals.filter((proposal) => {
    const key = `${proposal.type}:${proposal.name.toLowerCase()}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function makeProposal(type: GovernanceProposal["type"], name: string, rationale: string): GovernanceProposal {
  return {
    id: createId("proposal"),
    type,
    name: trimText(name, 120),
    rationale: trimText(rationale, 260),
    status: "proposed",
  };
}

function buildCoverageProposals(intent: string, workflowIds: string[], skillIds: string[]): GovernanceProposal[] {
  const proposals: GovernanceProposal[] = [];
  const compactIntent = trimText(intent.split(/\s+/).slice(0, 6).join(" ") || "operating mission", 80);

  if (workflowIds.length === 0) {
    proposals.push(
      makeProposal(
        "workflow",
        `${compactIntent.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-workflow`,
        "No approved workflow matched the selected pillar set. Review whether a new governed workflow should be added to the registry.",
      ),
    );
  }

  if (skillIds.length === 0) {
    proposals.push(
      makeProposal(
        "skill",
        `${compactIntent.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-skill`,
        "No approved skill matched the selected pillar set. Review whether a new governed skill should be proposed for approval.",
      ),
    );
  }

  return proposals;
}

function collectUnknownIdProposals(candidate: unknown, allowed: string[], type: GovernanceProposal["type"]) {
  if (!Array.isArray(candidate)) return [] as GovernanceProposal[];
  const allowedSet = new Set(allowed);
  return candidate
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0 && !allowedSet.has(value))
    .map((value) =>
      makeProposal(type, value, `Model requested an unregistered ${type}. It remains proposed until founder approval adds it to the governance registry.`),
    );
}

function buildDeterministicPlan(intent: string, researchQuery: string, signals: ResearchSignal[]): Omit<InstitutionalPlan, "id" | "createdAt"> {
  const pillarIds = selectPillars(intent, signals);
  const committeeIds = selectCommittees(pillarIds);
  const workflowIds = selectWorkflowIds(pillarIds);
  const skillIds = selectSkillIds(pillarIds);
  const researchReferences = signals.slice(0, 6).map(toReference);
  const title = trimText(intent.split(/\s+/).slice(0, 8).join(" ") || "Institutional Plan", 72);
  const riskTier = selectRiskTier(intent, signals);
  const escalationRuleIds = selectEscalationRuleIds(intent, pillarIds, riskTier, signals, skillIds);
  const proposals = buildCoverageProposals(intent, workflowIds, skillIds);
  const sourceList = uniqueStrings(signals.map((signal) => signal.source));
  const sourceSummary = sourceList.length > 0 ? `${signals.length} live sources from ${sourceList.join(", ")}` : "no live research sources";

  const votes: CommitteeVote[] = [
    {
      member: "Signal Council",
      model: "deterministic-council",
      vote: signals.length > 0 ? "approve" : "challenge",
      rationale: signals.length > 0
        ? `Live research context is present through ${sourceSummary}.`
        : "No live research evidence was available at plan compile time.",
    },
    {
      member: "Policy Steward",
      model: "deterministic-governance",
      vote: riskTier === "high" ? "challenge" : "approve",
      rationale: riskTier === "high"
        ? "High-risk language detected; compliance guardrails must be enforced before execution."
        : "The objective can proceed under standard governance constraints.",
    },
    {
      member: "Execution Board",
      model: "deterministic-execution",
      vote: "approve",
      rationale: `Workflow routing selected ${workflowIds.length} execution workflows and ${skillIds.length} approved skills.`,
    },
  ];

  const graphNodes = [
    {
      id: "intent-intake",
      label: "Intent Intake",
      stage: "intent" as const,
      ownerCommitteeId: "founder-council",
      pillarIds: ["governance"],
      summary: "Normalize founder intent into a monetizable operating objective.",
      latencyMs: 30 + intent.length,
    },
    {
      id: "research-council",
      label: "Model Council",
      stage: "reasoning" as const,
      ownerCommitteeId: committeeIds.includes("signal-council") ? "signal-council" : "founder-council",
      pillarIds: ["knowledge-research", "growth"].filter((pillarId) => pillarIds.includes(pillarId)),
      summary: `Review ${sourceSummary} and connect them to the operating thesis.`,
      latencyMs: 60 + (signals.length * 12),
    },
    {
      id: "governance-gate",
      label: "Governance Gate",
      stage: "governance" as const,
      ownerCommitteeId: "founder-council",
      pillarIds: ["governance", "compliance-risk"].filter((pillarId) => pillarIds.includes(pillarId)),
      summary: "Evaluate payment-bearing objective, risk tier, and skill eligibility before execution.",
      latencyMs: 50 + (riskTier === "high" ? 40 : 10),
    },
    {
      id: "execution-assembly",
      label: "Sunnyvale Run",
      stage: "execution" as const,
      ownerCommitteeId: "execution-board",
      pillarIds: pillarIds.filter((pillarId) => ["engineering", "operations", "sales", "growth"].includes(pillarId)),
      summary: `Assign ${workflowIds.length} workflows and ${skillIds.length} approved skills to the run contract.`,
      latencyMs: 75 + (workflowIds.length * 15),
    },
    {
      id: "archive-commit",
      label: "Archive Writeback",
      stage: "evidence" as const,
      ownerCommitteeId: "execution-board",
      pillarIds: ["operations", "governance"],
      summary: "Write compiled artifact, evidence references, and next actions into replayable memory.",
      latencyMs: 35 + (signals.length * 5),
    },
  ];

  return {
    title,
    intent,
    objective: trimText(intent, 240),
    pricingModel: pillarIds.includes("sales") || pillarIds.includes("growth") ? "Subscription + operator usage tiers" : "Platform license + advisory retainer",
    payingUser: pillarIds.includes("compliance-risk") ? "Regulated operating teams needing governed execution" : "Operator teams buying governed execution and live evidence",
    status: "review",
    revision: 1,
    riskTier,
    pillars: pillarIds,
    committeeIds,
    workflowIds,
    skillIds,
    escalationRuleIds,
    graph: {
      nodes: graphNodes,
      edges: graphNodes.slice(1).map((node, index) => ({
        from: graphNodes[index].id,
        to: node.id,
      })),
    },
    votes,
    guardrails: [
      "Runs must use only approved skills mapped to the active pillars.",
      "No plan is admitted without committee ownership and live evidence references.",
      "Archive writeback is mandatory before a run is considered complete.",
      "Plans may only activate governance objects that already exist in the registry.",
      "New committees, skills, or workflows must remain proposed until founder approval updates the registry.",
      signals.length > 0 ? `Maintain traceability to ${signals.length} live research signals.` : "Block high-risk runs when no live research signals are available.",
    ],
    successMetrics: [
      "Plan review is readable before execution.",
      "Approved run emits compiled artifact and archive record.",
      "Research references remain live and attributable.",
      "Governance proposals are explicit and never auto-activated.",
      pillarIds.includes("sales") ? "Buyer-facing next action is explicit." : "Institutional next action is explicit.",
    ],
    researchQuery,
    researchReferences,
    proposals,
  };
}

async function generatePlan(intent: string): Promise<Omit<InstitutionalPlan, "id" | "createdAt">> {
  const researchQuery = buildResearchQuery(intent);
  const researchContext = await fetchLiveResearch(researchQuery, 3);

  if (researchContext.signals.length > 0) {
    state.researchSignals = researchContext.signals;
    state.researchStatus = researchContext.statuses;
    pushWindow(state.stats.researchRefreshDurationsMs, researchContext.durationMs);
    state.stats.lastResearchSyncAt = now();
    captureMetricHistory();
    void persistState();
  }

  const deterministicPlan = buildDeterministicPlan(intent, researchQuery, researchContext.signals);
  try {
    const referenceBlock = deterministicPlan.researchReferences
      ?.map((reference, index) => `${index + 1}. ${reference.source}: ${reference.title}`)
      .join("\n") || "No live references were available.";

    const providerResult = await completeWithProviderChain([
      {
        role: "system",
        content: [
          "You are the model council inside UACP V3.",
          "Return strictly valid JSON only. No markdown fences. No prose outside the JSON object.",
          "Only activate governance objects from the provided registry lists.",
          "If a new committee, skill, or workflow is needed, put it under proposals instead of the active selections.",
        ].join("\n"),
      },
      {
        role: "user",
        content: [
          "Convert the founder intent into a UACP V3 institutional plan.",
          `Intent: ${intent}`,
          `Research query: ${researchQuery}`,
          `Live references:\n${referenceBlock}`,
          `Available pillars: ${activePillars().map((pillar) => pillar.id).join(", ")}`,
          `Available committees: ${activeCommittees().map((committee) => committee.id).join(", ")}`,
          `Available workflows: ${activeWorkflows().map((workflow) => workflow.id).join(", ")}`,
          `Available approved skills: ${activeSkills().filter((skill) => skill.status === "approved").map((skill) => skill.id).join(", ")}`,
          `Available escalation rules: ${activeEscalationRules().map((rule) => rule.id).join(", ")}`,
          [
            "Return a JSON object with these keys:",
            "title, objective, pricingModel, payingUser, riskTier, pillars, committeeIds, workflowIds, skillIds, escalationRuleIds, graph, votes, guardrails, successMetrics, proposals",
            "graph must contain nodes and edges.",
            "Each graph node must include id, label, stage, ownerCommitteeId, pillarIds, summary, latencyMs.",
            "Each vote must include member, model, vote, rationale.",
            "Each proposal must include type, name, rationale.",
          ].join("\n"),
        ].join("\n\n"),
      },
    ], {
      jsonMode: true,
      maxTokens: 2200,
      temperature: 0.2,
    });

    if (!providerResult) {
      return deterministicPlan;
    }

    const parsed = parseJsonObject<Record<string, unknown>>(providerResult.text);
    const modelProposals = sanitizeProposals(parsed.proposals);
    const inferredProposals = [
      ...collectUnknownIdProposals(parsed.committeeIds, activeCommittees().map((committee) => committee.id), "committee"),
      ...collectUnknownIdProposals(parsed.workflowIds, activeWorkflows().map((workflow) => workflow.id), "workflow"),
      ...collectUnknownIdProposals(parsed.skillIds, activeSkills().map((skill) => skill.id), "skill"),
    ];
    return {
      ...deterministicPlan,
      ...parsed,
      status: "review",
      revision: 1,
      pillars: sanitizeIds(parsed.pillars, activePillars().map((pillar) => pillar.id), deterministicPlan.pillars),
      committeeIds: sanitizeIds(parsed.committeeIds, activeCommittees().map((committee) => committee.id), deterministicPlan.committeeIds),
      workflowIds: sanitizeIds(parsed.workflowIds, activeWorkflows().map((workflow) => workflow.id), deterministicPlan.workflowIds),
      skillIds: sanitizeIds(parsed.skillIds, activeSkills().filter((skill) => skill.status === "approved").map((skill) => skill.id), deterministicPlan.skillIds),
      escalationRuleIds: sanitizeIds(parsed.escalationRuleIds, activeEscalationRules().map((rule) => rule.id), deterministicPlan.escalationRuleIds),
      graph: sanitizeGraph(parsed.graph, deterministicPlan.graph),
      votes: sanitizeVotes(parsed.votes, deterministicPlan.votes, providerResult.model),
      guardrails: sanitizeStrings(parsed.guardrails, deterministicPlan.guardrails),
      successMetrics: sanitizeStrings(parsed.successMetrics, deterministicPlan.successMetrics),
      researchQuery,
      researchReferences: deterministicPlan.researchReferences,
      proposals: mergeProposals([...(deterministicPlan.proposals || []), ...modelProposals, ...inferredProposals]),
    };
  } catch {
    return deterministicPlan;
  }
}

function sanitizeIds(candidate: unknown, allowed: string[], baseline: string[]) {
  if (!Array.isArray(candidate)) return baseline;
  const set = new Set(allowed);
  const values = candidate.filter((value): value is string => typeof value === "string" && set.has(value));
  return values.length > 0 ? uniqueStrings(values) : baseline;
}

function sanitizeStrings(candidate: unknown, baseline: string[]) {
  if (!Array.isArray(candidate)) return baseline;
  const values = candidate.filter((value): value is string => typeof value === "string" && value.trim().length > 0).map((value) => trimText(value, 180));
  return values.length > 0 ? values : baseline;
}

function sanitizeVotes(candidate: unknown, baseline: CommitteeVote[], fallbackModel = "deterministic-council") {
  if (!Array.isArray(candidate)) return baseline;
  const votes: CommitteeVote[] = candidate
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      member: trimText(String(item.member || "Committee"), 80),
      model: trimText(String(item.model || fallbackModel), 80),
      vote: item.vote === "approve" || item.vote === "challenge" || item.vote === "veto"
        ? item.vote as CommitteeVote["vote"]
        : "challenge",
      rationale: trimText(String(item.rationale || "No rationale provided."), 240),
    }));
  return votes.length > 0 ? votes : baseline;
}

function sanitizeProposals(candidate: unknown): GovernanceProposal[] {
  if (!Array.isArray(candidate)) return [];
  return candidate
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => {
      const type = item.type === "committee" || item.type === "skill" || item.type === "workflow" ? item.type : "workflow";
      return makeProposal(type, String(item.name || type), String(item.rationale || "Registry proposal requires founder review."));
    });
}

function sanitizeGraph(candidate: any, baseline: InstitutionalPlan["graph"]): InstitutionalPlan["graph"] {
  if (!candidate || typeof candidate !== "object" || !Array.isArray(candidate.nodes) || !Array.isArray(candidate.edges)) {
    return baseline;
  }

  const validCommitteeIds = new Set(activeCommittees().map((committee) => committee.id));
  const validPillarIds = new Set(activePillars().map((pillar) => pillar.id));
  const nodes = candidate.nodes
    .filter((node: any) => node && typeof node === "object")
    .map((node: any, index: number) => ({
      id: trimText(String(node.id || `node-${index + 1}`), 32),
      label: trimText(String(node.label || `Node ${index + 1}`), 80),
      stage: ["intent", "reasoning", "governance", "execution", "evidence", "continuity"].includes(node.stage)
        ? node.stage
        : baseline.nodes[Math.min(index, baseline.nodes.length - 1)]?.stage || "execution",
      ownerCommitteeId: validCommitteeIds.has(node.ownerCommitteeId) ? node.ownerCommitteeId : baseline.nodes[Math.min(index, baseline.nodes.length - 1)]?.ownerCommitteeId || "execution-board",
      pillarIds: Array.isArray(node.pillarIds)
        ? node.pillarIds.filter((pillarId: string) => validPillarIds.has(pillarId))
        : baseline.nodes[Math.min(index, baseline.nodes.length - 1)]?.pillarIds || ["operations"],
      summary: trimText(String(node.summary || baseline.nodes[Math.min(index, baseline.nodes.length - 1)]?.summary || "Institutional execution stage."), 220),
      latencyMs: Number.isFinite(node.latencyMs) ? Math.max(0, Number(node.latencyMs)) : baseline.nodes[Math.min(index, baseline.nodes.length - 1)]?.latencyMs || 60,
    }));

  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = candidate.edges
    .filter((edge: any) => edge && typeof edge.from === "string" && typeof edge.to === "string" && nodeIds.has(edge.from) && nodeIds.has(edge.to))
    .map((edge: any) => ({ from: edge.from, to: edge.to }));

  return nodes.length > 0 ? { nodes, edges: edges.length > 0 ? edges : baseline.edges } : baseline;
}

function addEvent(type: string, message: string, surface: SurfaceId, metadata?: Record<string, unknown>) {
  const eventBase: Omit<EventItem, "recordHash"> = {
    id: createId("evt"),
    type,
    message,
    timestamp: now(),
    surface,
    metadata,
  };
  const event: EventItem = {
    ...eventBase,
    previousHash: latestEventHash(),
    recordHash: buildEventRecordHash({
      ...eventBase,
      previousHash: latestEventHash(),
    }),
  };
  state.events = [event, ...state.events].slice(0, MAX_EVENTS);
  broadcast({ type: "event", data: event });
  void persistState();
  return event;
}

function addArchive(entry: Omit<ArchiveEntry, "id" | "createdAt">) {
  const archiveBase: Omit<ArchiveEntry, "recordHash"> = {
    id: createId("arc"),
    createdAt: now(),
    ...entry,
  };
  const archive: ArchiveEntry = {
    ...archiveBase,
    previousHash: latestArchiveHash(),
    recordHash: buildArchiveRecordHash({
      ...archiveBase,
      previousHash: latestArchiveHash(),
    }),
  };
  state.archives = [archive, ...state.archives].slice(0, MAX_ARCHIVES);
  broadcast({ type: "archive", data: archive });
  void persistState();
  return archive;
}

function eventStreamRedisBacked() {
  return Boolean(rateLimitRuntime.redis);
}

function buildEventStreamEnvelope(payload: unknown) {
  return {
    id: createId("stream"),
    emittedAt: now(),
    redis_backed: eventStreamRedisBacked(),
    channel: "uacp:event-stream",
    payload,
  };
}

function sendEventStreamFrame(res: express.Response, envelope: ReturnType<typeof buildEventStreamEnvelope>) {
  res.write(`id: ${envelope.id}\n`);
  res.write(`event: uacp_frame\n`);
  res.write(`data: ${JSON.stringify(envelope)}\n\n`);
}

async function persistEventStreamFrame(envelope: ReturnType<typeof buildEventStreamEnvelope>) {
  if (!rateLimitRuntime.redis) return;
  try {
    await rateLimitRuntime.redis.lpush("uacp:v5:event-stream", JSON.stringify(envelope));
    await rateLimitRuntime.redis.ltrim("uacp:v5:event-stream", 0, 499);
  } catch (error) {
    console.error("[uacp] event stream redis write failed:", error instanceof Error ? error.message : error);
  }
}

function broadcast(payload: unknown) {
  const serialized = JSON.stringify(payload);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(serialized);
    }
  }

  const envelope = buildEventStreamEnvelope(payload);
  for (const client of eventStreamClients) {
    sendEventStreamFrame(client, envelope);
  }
  void persistEventStreamFrame(envelope);
}

function upsertWorkerRuntime(nextRuntime: WorkerRuntimeState) {
  state.workerRuntime = [
    nextRuntime,
    ...state.workerRuntime.filter((runtime) => runtime.workerId !== nextRuntime.workerId),
  ];
}

function setWorkerRuntime(workerId: string, patch: Partial<WorkerRuntimeState>) {
  const worker = workerById(workerId);
  if (!worker) return;
  const current = state.workerRuntime.find((runtime) => runtime.workerId === workerId) || makeWorkerRuntime(worker);
  upsertWorkerRuntime({
    ...current,
    ...patch,
    workerId,
  });
}

function normalizeBackendSeverity(value: unknown): BackendProductEvent["severity"] {
  if (value === "critical" || value === "warning" || value === "info") return value;
  return "info";
}

function getPayloadNumber(payload: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const parsed = Number(payload[key]);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  return value as Record<string, unknown>;
}

function getRecordString(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim().length > 0) return value.trim();
  }
  return undefined;
}

function getRecordNumber(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const parsed = Number(record[key]);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function getRecordStringArray(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (Array.isArray(value)) {
      return value.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0).map((entry) => entry.trim());
    }
    if (typeof value === "string" && value.trim().length > 0) {
      return value.split(/[,\n]+/).map((entry) => entry.trim()).filter(Boolean);
    }
  }
  return [];
}

function extractQueueRecords(value: unknown, preferredKey?: string) {
  if (Array.isArray(value)) {
    return value.map(asRecord).filter((entry): entry is Record<string, unknown> => Boolean(entry));
  }

  const record = asRecord(value);
  if (!record) return [] as Record<string, unknown>[];

  const candidateKeys = preferredKey ? [preferredKey, "queue", "items", "results", "data"] : ["queue", "items", "results", "data"];
  for (const key of candidateKeys) {
    const nested = record[key];
    if (Array.isArray(nested)) {
      return nested.map(asRecord).filter((entry): entry is Record<string, unknown> => Boolean(entry));
    }
  }

  return [];
}

function classifyBackendEvent(input: {
  eventType: string;
  entityType: string;
  severity: BackendProductEvent["severity"];
  status: string;
  payload: Record<string, unknown>;
}) {
  const text = `${input.eventType} ${input.entityType} ${input.status} ${JSON.stringify(input.payload)}`.toLowerCase();
  const pillars = new Set<string>();
  const committees = new Set<string>();
  const workers = new Set<string>();

  const assign = (pillarIds: string[], committeeIds: string[], workerIds: string[]) => {
    pillarIds.forEach((id) => pillars.add(id));
    committeeIds.forEach((id) => committees.add(id));
    workerIds.forEach((id) => workers.add(id));
  };

  if (/(endpoint|route|pipeline|deploy|deployment|latency|outage|health|regression|auth|ui|experience)/.test(text)) {
    assign(
      ["engineering", "product", "operations"],
      ["experience-assurance"],
      ["sentinel", "mirror", "pulse", "sheriff"],
    );
  }

  if (/(billing|reserve|revenue|subscription|payment|invoice|wallet|margin)/.test(text)) {
    assign(
      ["finance", "sales", "operations"],
      ["marketplace-operations", "governance-evidence"],
      ["gauge", "ledger", "mint"],
    );
  }

  if (/(security|mfa|vault|credential|compliance|privacy|access|permission)/.test(text)) {
    assign(
      ["compliance-risk", "governance"],
      ["governance-evidence", "marketplace-operations"],
      ["bouncer", "ledger", "oracle", "sheriff"],
    );
  }

  if (/(marketplace|install|listing|vendor|partner|queue)/.test(text)) {
    assign(
      ["operations", "sales", "growth"],
      ["marketplace-operations"],
      ["herald", "harvest", "arbiter", "welcome"],
    );
  }

  if (/(workspace|tenant|user|signup|evaluation|onboarding|customer|lead)/.test(text)) {
    assign(
      ["growth", "sales", "product"],
      ["growth-intelligence", "experience-assurance"],
      ["welcome", "signal", "glide", "scout"],
    );
  }

  if (input.severity === "critical") {
    assign(
      ["governance", "compliance-risk"],
      ["governance-evidence"],
      ["ledger", "sheriff"],
    );
  }

  if (pillars.size === 0) {
    assign(["operations", "governance"], ["marketplace-operations"], ["gauge", "ledger"]);
  }

  return {
    pillarIds: [...pillars],
    committeeIds: [...committees],
    workerIds: [...workers],
  };
}

function updateBackendSummaryFromEvent(event: BackendProductEvent) {
  const text = `${event.eventType} ${event.entityType}`.toLowerCase();
  const payload = event.payload;

  if (/(signup|user_created|user_signed_up)/.test(text)) {
    state.backendSummary.signups += 1;
    state.backendSummary.liveUsers += Math.max(1, getPayloadNumber(payload, ["delta_users", "live_users_delta"]) ?? 1);
  }
  if (/(evaluation_started|evaluation|trial_started)/.test(text)) {
    state.backendSummary.evaluationsStarted += 1;
  }
  if (/(run_completed|execution_completed|pipeline_run_completed)/.test(text)) {
    state.backendSummary.runsCompleted += 1;
  }
  if (/(pipeline_test|pipeline)/.test(text)) {
    state.backendSummary.pipelineTests += 1;
  }
  if (/(endpoint_call|endpoint|route)/.test(text)) {
    state.backendSummary.endpointCalls += Math.max(1, getPayloadNumber(payload, ["endpoint_calls", "count"]) ?? 1);
    if (event.status === "failed" || event.severity === "critical") {
      state.backendSummary.failedRoutes += 1;
    }
  }
  if (/(billing|payment|invoice|revenue|subscription)/.test(text)) {
    const revenue = getPayloadNumber(payload, ["revenue", "amount", "amount_usd"]);
    if (typeof revenue === "number") {
      state.backendSummary.revenue = Math.max(0, state.backendSummary.revenue + revenue);
    }
  }
  if (/(reserve|wallet)/.test(text)) {
    const reserve = getPayloadNumber(payload, ["reserve_balance", "reserveBalance", "wallet_balance"]);
    if (typeof reserve === "number") {
      state.backendSummary.reserveBalance = reserve;
    }
  }
  if (/(evidence_export|evidence_bundle|export)/.test(text)) {
    state.backendSummary.evidenceExports += 1;
  }
  if (/(mfa|security|auth)/.test(text)) {
    state.backendSummary.mfaEvents += 1;
  }
  if (/(marketplace_install|install)/.test(text)) {
    state.backendSummary.marketplaceInstalls += 1;
  }

  const liveUsers = getPayloadNumber(payload, ["live_users", "active_users"]);
  if (typeof liveUsers === "number") {
    state.backendSummary.liveUsers = liveUsers;
  }

  state.backendSummary.lastEventAt = event.timestamp;
}

function buildCommandCenterSnapshot(): CommandCenterSnapshot {
  const activeWorkerCount = state.workerRuntime.filter((runtime) => runtime.status === "running").length;
  const pausedWorkerCount = state.workerRuntime.filter((runtime) => runtime.paused).length;
  const openEscalations = state.operatorRuns.filter((run) => run.status === "escalated" || run.escalations.length > 0).length;
  const enterpriseChecks = buildEnterpriseChecks();

  return {
    backend: state.backendSummary,
    institution: {
      workerCount: activeWorkers().length,
      activeWorkerCount,
      pausedWorkerCount,
      operatorRunCount: state.operatorRuns.length,
      openEscalations,
      archiveCount: state.archives.length,
      planCount: state.plans.length,
      governedRunCount: state.runs.length,
    },
    governance: {
      councilCount: enterpriseCouncilBlueprints.length,
      canonicalPlanCount: canonicalPlanTemplates.length,
      enterpriseCheckCount: enterpriseChecks.length,
      passingEnterpriseChecks: enterpriseChecks.filter((check) => check.status === "pass").length,
    },
  };
}

function buildBoxTopologySnapshot() {
  return {
    current: currentWorkerGroupBlueprint()
      ? {
          ...currentWorkerGroupBlueprint(),
          activeWorkerCount: activeWorkers().length,
          minimumLiveWorkerIds: minimumLiveWorkerIds(),
          committeeIds: activeOperatorCommittees().map((committee) => committee.id),
        }
      : {
          id: WORKER_GROUP,
          label: "Control Plane",
          runtimeMode: RUNTIME_MODE,
          boxRole: "hot",
          activeWorkerCount: activeWorkers().length,
          minimumLiveWorkerIds: minimumLiveWorkerIds(),
          committeeIds: activeOperatorCommittees().map((committee) => committee.id),
        },
    groups: workerGroupBlueprints.map((group) => ({
      ...group,
      committeeIds: governanceRegistry.operatorCommittees
        .filter((committee) => committee.workerIds.some((workerId) => group.workerIds.includes(workerId)))
        .map((committee) => committee.id),
    })),
  };
}

type WorkspaceOperatingAccumulator = {
  key: string;
  workspaceId?: string;
  accountLabel: string;
  tier?: string;
  lastActivityAt?: string;
  runsUsed: number;
  runsLimit?: number;
  endpointCreated: boolean;
  endpointTested: boolean;
  endpointFailed: boolean;
  evidenceViewed: boolean;
  evidenceExported: boolean;
  billingViewed: boolean;
  reserveAdded: boolean;
  reserveBalance?: number;
  mfaEnabled: boolean;
  mfaIncomplete: boolean;
  errorsCount: number;
  archiveRefs: Set<string>;
  eventIds: Set<string>;
  evidence: Set<string>;
  workerIds: Set<string>;
  committeeIds: Set<string>;
  pillarIds: Set<string>;
};

function getPayloadString(payload: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }
  return undefined;
}

function sanitizeEmail(email: string) {
  return email.trim().toLowerCase();
}

function extractOutboundEmail(payload: Record<string, unknown>) {
  const email = getPayloadString(payload, [
    "email",
    "contact_email",
    "contactEmail",
    "owner_email",
    "ownerEmail",
    "user_email",
    "userEmail",
    "billing_email",
    "billingEmail",
  ]);
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return undefined;
  }
  return sanitizeEmail(email);
}

function isVendorOrPartnerEvent(event: BackendProductEvent) {
  const text = `${event.eventType} ${event.entityType} ${event.status} ${JSON.stringify(event.payload)}`.toLowerCase();
  return /(vendor|partner|affiliate|channel|integration|reseller|supplier)/.test(text);
}

function outboundContactId(kind: OutboundContact["kind"], email: string) {
  const token = Buffer.from(`${kind}:${sanitizeEmail(email)}`).toString("base64url").slice(0, 16);
  return `outc-${token}`;
}

function normalizeOutboundKind(value: unknown): OutboundContact["kind"] {
  const text = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (["vendor", "partner", "affiliate", "channel"].includes(text)) return "vendor";
  return "customer";
}

function normalizeOutboundWorker(kind: OutboundContact["kind"], value: unknown) {
  const requestedWorkerId = typeof value === "string" ? value.trim() : "";
  if (requestedWorkerId) {
    const worker = workerById(requestedWorkerId);
    if (!worker) throw new Error(`Unknown outbound worker ${requestedWorkerId}.`);
    if (!["welcome", "vendor-recruiter"].includes(worker.id)) {
      throw new Error(`Worker ${requestedWorkerId} is not allowed to execute Resend outbound.`);
    }
    if (kind === "customer" && worker.id !== "welcome") {
      throw new Error("Customer outbound must be assigned to welcome.");
    }
    if (kind === "vendor" && worker.id !== "vendor-recruiter") {
      throw new Error("Vendor outbound must be assigned to vendor-recruiter.");
    }
    return worker.id;
  }
  return kind === "vendor" ? "vendor-recruiter" : "welcome";
}

function enqueueOutboundContactFromPayload(candidate: unknown, source: "internal-api" | "backend-event") {
  const record = ensureRecord(candidate, "outboundContact");
  const email = extractOutboundEmail(record);
  if (!email) throw new Error("outboundContact.email must be a valid email address.");

  const kind = normalizeOutboundKind(record.kind ?? record.type ?? record.contact_type ?? record.contactType);
  const assignedWorkerId = normalizeOutboundWorker(kind, record.assigned_worker_id ?? record.assignedWorkerId ?? record.worker_id ?? record.workerId);
  const accountLabel =
    getPayloadString(record, ["account_label", "accountLabel", "name", "contact_name", "contactName", "company", "organization", "org"]) ||
    email.split("@")[0] ||
    email;
  const company = getPayloadString(record, ["company", "organization", "org", "vendor_name", "vendorName"]);
  const workspaceId = getPayloadString(record, ["workspace_id", "workspaceId"]);
  const sourceEventIds = Array.isArray(record.source_event_ids)
    ? record.source_event_ids.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0).map((entry) => entry.trim())
    : Array.isArray(record.sourceEventIds)
      ? record.sourceEventIds.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0).map((entry) => entry.trim())
      : [];

  const contact = upsertOutboundContact({
    kind,
    email,
    accountLabel,
    company,
    workspaceId,
    sourceEventIds,
    assignedWorkerId,
    status: "queued",
    lastActivityAt: now(),
    metadata: {
      source,
      sourceUrl: getPayloadString(record, ["source_url", "sourceUrl", "url"]),
      consentBasis: getPayloadString(record, ["consent_basis", "consentBasis", "basis"]),
      reason: getPayloadString(record, ["reason", "fit_reason", "fitReason", "notes"]),
      tags: Array.isArray(record.tags) ? record.tags.filter((entry) => typeof entry === "string") : [],
    },
  });

  const archive = addArchive({
    title: `${kind === "vendor" ? "Vendor" : "Customer"} outbound contact queued`,
    category: "run",
    summary: `${contact.email} queued for ${assignedWorkerId} via ${source}.`,
    lineage: [contact.id, assignedWorkerId, ...sourceEventIds],
    metadata: {
      contactId: contact.id,
      email: contact.email,
      kind: contact.kind,
      assignedWorkerId,
      source,
    },
  });

  return { contact, archiveId: archive.id };
}

function upsertOutboundContact(input: Omit<OutboundContact, "id" | "createdAt" | "updatedAt" | "attemptCount"> & { attemptCount?: number }) {
  const email = sanitizeEmail(input.email);
  const id = outboundContactId(input.kind, email);
  const current = state.outboundContacts.find((contact) => contact.id === id);
  const timestamp = now();
  const next: OutboundContact = current
    ? {
        ...current,
        ...input,
        email,
        sourceEventIds: uniqueStrings([...(current.sourceEventIds || []), ...(input.sourceEventIds || [])]),
        updatedAt: timestamp,
      }
    : {
        id,
        createdAt: timestamp,
        updatedAt: timestamp,
        attemptCount: input.attemptCount ?? 0,
        ...input,
        email,
      };

  state.outboundContacts = [next, ...state.outboundContacts.filter((contact) => contact.id !== id)];
  return next;
}

function queueOutboundContactFromBackendEvent(event: BackendProductEvent) {
  const email = extractOutboundEmail(event.payload);
  if (!email) return;

  const vendor = isVendorOrPartnerEvent(event);
  const accountLabel =
    getPayloadString(event.payload, ["workspace_name", "workspaceName", "organization", "org", "account_name", "vendor_name", "company"]) ||
    event.workspaceId ||
    event.entityId;
  const company = getPayloadString(event.payload, ["company", "vendor_name", "organization", "org"]);

  upsertOutboundContact({
    kind: vendor ? "vendor" : "customer",
    email,
    accountLabel,
    company,
    workspaceId: event.workspaceId,
    sourceEventIds: [event.eventId],
    assignedWorkerId: vendor ? "vendor-recruiter" : "welcome",
    status: "queued",
    lastActivityAt: event.timestamp,
    metadata: {
      entityType: event.entityType,
      entityId: event.entityId,
      eventType: event.eventType,
      severity: event.severity,
    },
  });
}

function latestApprovedOutreachArtifact() {
  return state.v3CommercialArtifacts.find((artifact) => artifact.type === "outreach_asset" && artifact.founderReview.status === "approved");
}

function latestApprovedOfferArtifact() {
  return state.v3CommercialArtifacts.find((artifact) => artifact.type === "buyer_facing_offer" && artifact.founderReview.status === "approved");
}

function buildOutboundMessageDraft(contact: OutboundContact) {
  if (contact.kind === "customer") {
    const outreach = latestApprovedOutreachArtifact();
    const subject = outreach?.copy?.headline || "A governed AI workflow gap we can fix fast";
    const bodyLines = outreach?.copy
      ? [
          `Hi ${contact.accountLabel},`,
          "",
          outreach.copy.headline,
          outreach.copy.subheadline,
          "",
          ...(outreach.copy.body || []),
          "",
          outreach.copy.cta || "Reply if you want a walkthrough.",
        ]
      : [
          `Hi ${contact.accountLabel},`,
          "",
          "We help private AI teams turn model testing into governed execution with replayable proof, policy alignment, and cost-attached evidence.",
          "If your team is evaluating endpoints or evidence flows right now, we can show you where activation gets stuck and how to fix it fast.",
          "",
          "Reply if you want a short walkthrough.",
        ];
    return { subject: trimText(subject, 120), body: bodyLines.join("\n") };
  }

  const offer = latestApprovedOfferArtifact();
  const subject = offer?.copy?.headline ? `Partnership: ${offer.copy.headline}` : "Partnership opportunity with Veklom";
  const body = [
    `Hi ${contact.accountLabel},`,
    "",
    "We are building a governed AI operating system and are looking for vendors, affiliates, and integration partners that can expand distribution or service capacity.",
    "If there is fit, we want a fast qualification conversation around reliability, delivery shape, and economics.",
    "",
    offer?.copy?.cta || "Reply if you want to explore a partner path.",
  ].join("\n");
  return { subject: trimText(subject, 120), body };
}

function resendConfigured() {
  return Boolean(RESEND_API_KEY && RESEND_FROM_EMAIL);
}

async function sendResendEmail(to: string, subject: string, body: string) {
  if (!resendConfigured()) {
    throw new Error("Resend outbound is not configured.");
  }

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: RESEND_FROM_EMAIL,
      to: [to],
      subject,
      text: body,
      ...(UACP_OUTBOUND_REPLY_TO ? { reply_to: UACP_OUTBOUND_REPLY_TO } : {}),
    }),
    signal: AbortSignal.timeout(20000),
  });

  const payload = await response.json().catch(() => ({} as Record<string, unknown>));
  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText}${payload && typeof payload === "object" && typeof (payload as Record<string, unknown>).message === "string" ? ` :: ${(payload as Record<string, unknown>).message}` : ""}`,
    );
  }

  return {
    id: typeof payload.id === "string" ? payload.id : undefined,
  };
}

function queuedContactsForWorker(workerId: string) {
  const cooldownCutoff = Date.now() - (72 * 60 * 60 * 1000);
  return state.outboundContacts
    .filter((contact) => contact.assignedWorkerId === workerId && contact.status === "queued")
    .filter((contact) => !contact.lastSentAt || Date.parse(contact.lastSentAt) < cooldownCutoff)
    .sort((left, right) => new Date(left.updatedAt).getTime() - new Date(right.updatedAt).getTime());
}

function buildOutboundRuntimeSnapshot(): OutboundRuntimeSnapshot {
  return {
    enabled: resendConfigured(),
    provider: resendConfigured() ? "resend" : "disabled",
    fromConfigured: Boolean(RESEND_FROM_EMAIL),
    queuedContacts: state.outboundContacts.filter((contact) => contact.status === "queued").length,
    sentMessages: state.outboundMessages.filter((message) => message.status === "sent").length,
    failedMessages: state.outboundMessages.filter((message) => message.status === "failed").length,
    customerQueue: state.outboundContacts.filter((contact) => contact.status === "queued" && contact.kind === "customer").length,
    vendorQueue: state.outboundContacts.filter((contact) => contact.status === "queued" && contact.kind === "vendor").length,
  };
}

async function executeWorkerOutboundTasks(worker: OperatorWorker, run: OperatorRun) {
  if (worker.id !== "welcome" && worker.id !== "vendor-recruiter") {
    return { actions: [] as string[], evidenceCreated: [] as string[], outboundMessageIds: [] as string[] };
  }

  const contacts = queuedContactsForWorker(worker.id).slice(0, UACP_OUTBOUND_MAX_SENDS_PER_RUN);
  if (contacts.length === 0) {
    return { actions: ["no_outbound_contacts_ready"], evidenceCreated: [] as string[], outboundMessageIds: [] as string[] };
  }

  if (!resendConfigured()) {
    return {
      actions: ["outbound_blocked_resend_unconfigured"],
      evidenceCreated: [] as string[],
      outboundMessageIds: [] as string[],
    };
  }

  const evidenceCreated: string[] = [];
  const outboundMessageIds: string[] = [];
  const actions: string[] = [];

  for (const contact of contacts) {
    const draft = buildOutboundMessageDraft(contact);
    const messageRecord: OutboundMessage = {
      id: createId("outmsg"),
      contactId: contact.id,
      workerId: worker.id,
      provider: "resend",
      subject: draft.subject,
      body: draft.body,
      status: "queued",
      createdAt: now(),
    };
    state.outboundMessages = [messageRecord, ...state.outboundMessages];
    contact.lastAttemptAt = now();
    contact.attemptCount += 1;
    contact.updatedAt = now();

    try {
      const providerResult = await sendResendEmail(contact.email, draft.subject, draft.body);
      messageRecord.status = "sent";
      messageRecord.sentAt = now();
      messageRecord.providerMessageId = providerResult.id;
      contact.status = "sent";
      contact.lastSentAt = messageRecord.sentAt;
      contact.lastMessageId = messageRecord.id;
      contact.updatedAt = now();

      const archive = addArchive({
        title: `${worker.displayName} outbound send`,
        category: "run",
        summary: `${worker.displayName} sent a governed ${contact.kind} outreach email to ${contact.email}.`,
        lineage: [run.id, worker.id, contact.id, ...(contact.sourceEventIds || [])],
        metadata: {
          workerId: worker.id,
          contactId: contact.id,
          outboundKind: contact.kind,
          email: contact.email,
          subject: draft.subject,
          provider: "resend",
          providerMessageId: providerResult.id,
        },
      });
      messageRecord.archiveRef = archive.id;
      evidenceCreated.push(archive.id);
      outboundMessageIds.push(messageRecord.id);
      actions.push(contact.kind === "vendor" ? "sent_vendor_outreach" : "sent_customer_outreach");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown Resend outbound failure.";
      messageRecord.status = "failed";
      messageRecord.error = message;
      contact.status = "failed";
      contact.updatedAt = now();
      actions.push(contact.kind === "vendor" ? "failed_vendor_outreach" : "failed_customer_outreach");
      throw new Error(message);
    }
  }

  return { actions, evidenceCreated, outboundMessageIds };
}

function getLatestArchiveForEventIds(eventIds: string[]) {
  return state.archives.find((archive) => {
    const lineage = Array.isArray(archive.lineage) ? archive.lineage : [];
    return eventIds.some((eventId) => lineage.includes(eventId));
  });
}

function chooseOperatorCommittee(workerIds: string[]) {
  let bestCommitteeId: string | undefined;
  let bestScore = -1;

  for (const committee of activeOperatorCommittees()) {
    const overlap = workerIds.filter((workerId) => committee.workerIds.includes(workerId)).length;
    if (overlap > bestScore) {
      bestScore = overlap;
      bestCommitteeId = committee.id;
    }
  }

  return bestCommitteeId;
}

function buildWorkspaceOperatingAccumulators() {
  const accumulators = new Map<string, WorkspaceOperatingAccumulator>();

  for (const event of state.backendEvents) {
    const key = event.workspaceId || event.tenantId || event.userId || event.entityId;
    const text = `${event.eventType} ${event.entityType} ${event.status} ${JSON.stringify(event.payload)}`.toLowerCase();
    const existing = accumulators.get(key);
    const accountLabel =
      getPayloadString(event.payload, ["workspace_name", "workspaceName", "organization", "org", "email", "account_name"]) ||
      event.workspaceId ||
      event.tenantId ||
      event.userId ||
      event.entityId;

    const next = existing || {
      key,
      workspaceId: event.workspaceId,
      accountLabel,
      tier: getPayloadString(event.payload, ["tier", "plan", "subscription_tier"]),
      lastActivityAt: event.timestamp,
      runsUsed: 0,
      runsLimit: getPayloadNumber(event.payload, ["runs_limit", "run_limit", "evaluation_limit", "trial_limit"]),
      endpointCreated: false,
      endpointTested: false,
      endpointFailed: false,
      evidenceViewed: false,
      evidenceExported: false,
      billingViewed: false,
      reserveAdded: false,
      reserveBalance: getPayloadNumber(event.payload, ["reserve_balance", "reserveBalance", "wallet_balance"]),
      mfaEnabled: false,
      mfaIncomplete: false,
      errorsCount: 0,
      archiveRefs: new Set<string>(),
      eventIds: new Set<string>(),
      evidence: new Set<string>(),
      workerIds: new Set<string>(),
      committeeIds: new Set<string>(),
      pillarIds: new Set<string>(),
    } satisfies WorkspaceOperatingAccumulator;

    next.accountLabel = next.accountLabel || accountLabel;
    next.workspaceId = next.workspaceId || event.workspaceId;
    next.lastActivityAt = !next.lastActivityAt || new Date(event.timestamp) > new Date(next.lastActivityAt) ? event.timestamp : next.lastActivityAt;
    next.tier = next.tier || getPayloadString(event.payload, ["tier", "plan", "subscription_tier"]);
    next.runsLimit = next.runsLimit ?? getPayloadNumber(event.payload, ["runs_limit", "run_limit", "evaluation_limit", "trial_limit"]);
    next.reserveBalance = next.reserveBalance ?? getPayloadNumber(event.payload, ["reserve_balance", "reserveBalance", "wallet_balance"]);

    const runsUsed = getPayloadNumber(event.payload, ["runs_used", "run_count", "count", "usage_count"]);
    if (typeof runsUsed === "number" && runsUsed > next.runsUsed) {
      next.runsUsed = runsUsed;
    }
    if (/(playground|run_completed|run_used|evaluation_started|evaluation_limit_reached)/.test(text) && next.runsUsed === 0) {
      next.runsUsed += 1;
    }

    if (/(endpoint_created|deployment_created|route_created|endpoint)/.test(text)) {
      next.endpointCreated = true;
    }
    if (/(endpoint_tested|test_succeeded|pipeline_test_succeeded|endpoint_verified)/.test(text) || (/(endpoint|pipeline|route)/.test(text) && event.status === "succeeded")) {
      next.endpointTested = true;
    }
    if (/(endpoint_test_failed|pipeline_test_failed|route_failed|endpoint_failed|deployment_failed)/.test(text) || event.status === "failed") {
      next.endpointFailed = true;
      next.errorsCount += 1;
    }
    if (/(evidence_viewed|evidence_opened|evidence_bundle_viewed|gdpr_viewed|hipaa_viewed)/.test(text)) {
      next.evidenceViewed = true;
    }
    if (/(evidence_export|evidence_bundle|export)/.test(text)) {
      next.evidenceExported = true;
    }
    if (/(billing_page_opened|billing_viewed|pricing_viewed|subscription_viewed)/.test(text)) {
      next.billingViewed = true;
    }
    if (/(reserve_added|reserve_funded|wallet_funded|payment_succeeded|subscription_activated)/.test(text)) {
      next.reserveAdded = true;
    }
    if (/(mfa_enabled|mfa_completed|2fa_enabled)/.test(text)) {
      next.mfaEnabled = true;
    }
    if (/(mfa_incomplete|mfa_required|2fa_required|security_incomplete)/.test(text)) {
      next.mfaIncomplete = true;
    }

    if (event.archiveId) {
      next.archiveRefs.add(event.archiveId);
    }
    next.eventIds.add(event.eventId);
    next.workerIds = new Set([...next.workerIds, ...event.workerIds]);
    next.committeeIds = new Set([...next.committeeIds, ...event.committeeIds]);
    next.pillarIds = new Set([...next.pillarIds, ...event.pillarIds]);

    if (next.runsLimit && next.runsUsed >= next.runsLimit) {
      next.evidence.add(`Evaluation limit reached at ${next.runsUsed}/${next.runsLimit} runs.`);
    }
    if (next.endpointTested) {
      next.evidence.add("Endpoint created and tested successfully.");
    } else if (next.endpointCreated) {
      next.evidence.add("Endpoint has been created but not fully validated.");
    }
    if (next.evidenceViewed) {
      next.evidence.add("Evidence surface was viewed by the account.");
    }
    if (next.evidenceExported) {
      next.evidence.add("Evidence bundle was exported.");
    }
    if (next.billingViewed) {
      next.evidence.add("Billing or pricing surface was opened.");
    }
    if (next.reserveAdded || (typeof next.reserveBalance === "number" && next.reserveBalance > 0)) {
      next.evidence.add("Reserve funding or activation payment behavior is present.");
    }
    if (next.endpointFailed || next.errorsCount > 0) {
      next.evidence.add("Technical failure or route error is blocking activation.");
    }
    if (next.mfaIncomplete) {
      next.evidence.add("Security readiness is incomplete because MFA is not finished.");
    } else if (next.mfaEnabled) {
      next.evidence.add("Security readiness improved with MFA enabled.");
    }

    accumulators.set(key, next);
  }

  return [...accumulators.values()];
}

function buildEvaluationSignals(): OperatingSignal[] {
  const accumulators = buildWorkspaceOperatingAccumulators();

  return accumulators
    .map((entry) => {
      const reserveState =
        entry.reserveAdded || (typeof entry.reserveBalance === "number" && entry.reserveBalance > 0)
          ? `reserve live${typeof entry.reserveBalance === "number" ? ` ($${entry.reserveBalance.toFixed(2)})` : ""}`
          : entry.billingViewed
            ? "billing viewed / no reserve"
            : "no reserve";
      const endpointStatus = entry.endpointFailed
        ? "failed"
        : entry.endpointTested
          ? "created + tested"
          : entry.endpointCreated
            ? "created"
            : "not started";
      const evidenceActivity = entry.evidenceExported ? "exported" : entry.evidenceViewed ? "viewed" : "none";
      const mfaState = entry.mfaEnabled ? "enabled" : entry.mfaIncomplete ? "incomplete" : "not started";
      const evaluationStage =
        entry.reserveAdded || (typeof entry.reserveBalance === "number" && entry.reserveBalance > 0)
          ? "Activation ready"
          : entry.endpointTested && (entry.evidenceViewed || entry.billingViewed)
            ? "Serious evaluation"
            : entry.endpointCreated || entry.runsUsed > 0 || entry.billingViewed
              ? "Active evaluation"
              : "Free evaluation";

      let activationScore = 18;
      activationScore += Math.min(24, entry.runsUsed * 6);
      activationScore += entry.endpointCreated ? 12 : 0;
      activationScore += entry.endpointTested ? 18 : 0;
      activationScore += entry.evidenceViewed ? 10 : 0;
      activationScore += entry.evidenceExported ? 6 : 0;
      activationScore += entry.billingViewed ? 8 : 0;
      activationScore += entry.reserveAdded ? 18 : 0;
      activationScore += entry.mfaEnabled ? 8 : 0;
      activationScore -= entry.endpointFailed ? 12 : 0;
      activationScore -= Math.min(12, entry.errorsCount * 4);
      activationScore = clamp(Math.round(activationScore), 0, 99);

      let riskScore = 12;
      riskScore += entry.endpointFailed ? 28 : 0;
      riskScore += Math.min(18, entry.errorsCount * 6);
      riskScore += entry.billingViewed && !entry.reserveAdded ? 16 : 0;
      riskScore += entry.runsLimit && entry.runsUsed >= entry.runsLimit && !entry.reserveAdded ? 22 : 0;
      riskScore += entry.mfaIncomplete ? 14 : 0;
      riskScore += entry.endpointCreated && !entry.endpointTested ? 8 : 0;
      riskScore -= entry.endpointTested ? 10 : 0;
      riskScore -= entry.reserveAdded ? 14 : 0;
      riskScore = clamp(Math.round(riskScore), 0, 100);

      const confidence = clamp(
        ((entry.eventIds.size * 0.12) + (entry.evidence.size * 0.08) + (entry.workerIds.size * 0.03)),
        0.35,
        0.98,
      );

      let recommendedAction = "Drive the next successful endpoint test and attach the correct evidence path.";
      if (entry.endpointFailed || entry.errorsCount > 0) {
        recommendedAction = "Route this account through Sentinel and Mirror, clear the technical blocker, and retest the endpoint.";
      } else if (entry.runsLimit && entry.runsUsed >= entry.runsLimit && !entry.reserveAdded) {
        recommendedAction = "Explain activation, the reserve model, and the regulated access path before evaluation stalls.";
      } else if ((entry.evidenceViewed || entry.evidenceExported) && !entry.reserveAdded) {
        recommendedAction = "Attach the evidence summary, explain activation, and move the account toward reserve-funded access.";
      } else if (entry.billingViewed && !entry.reserveAdded) {
        recommendedAction = "Clarify pricing and reserve economics before the account drifts.";
      } else if (entry.mfaIncomplete && (entry.endpointCreated || entry.endpointTested)) {
        recommendedAction = "Complete MFA and security readiness before deeper regulated evaluation.";
      } else if (entry.endpointTested) {
        recommendedAction = "Offer a technical walkthrough and present the strongest evidence bundle now that the endpoint is proven.";
      }

      const assignedWorkerIds = uniqueStrings([
        "gauge",
        "welcome",
        ...(entry.evidenceViewed || entry.evidenceExported ? ["ledger"] : []),
        ...(entry.billingViewed || entry.reserveAdded ? ["mint"] : []),
        ...(entry.endpointFailed || entry.errorsCount > 0 ? ["sentinel", "mirror", "sheriff"] : []),
        ...(entry.endpointCreated || entry.endpointTested ? ["pulse"] : []),
      ]);

      const archive = entry.archiveRefs.size > 0 ? [...entry.archiveRefs][0] : getLatestArchiveForEventIds([...entry.eventIds])?.id;

      return {
        id: `sig-${entry.key}`,
        kind: "evaluation",
        title: `${entry.accountLabel} evaluation signal`,
        summary: `${evaluationStage} with ${entry.runsUsed}${entry.runsLimit ? `/${entry.runsLimit}` : ""} runs, endpoint ${endpointStatus}, evidence ${evidenceActivity}, and ${reserveState}.`,
        category: "evaluation",
        accountLabel: entry.accountLabel,
        workspaceId: entry.workspaceId,
        tier: entry.tier || "free evaluation",
        evaluationStage,
        lastActivityAt: entry.lastActivityAt,
        runsUsed: entry.runsUsed,
        runsLimit: entry.runsLimit,
        endpointStatus,
        evidenceActivity,
        billingState: entry.billingViewed ? "viewed" : "not viewed",
        reserveState,
        mfaState,
        errorsCount: entry.errorsCount,
        score: activationScore,
        riskScore,
        confidence,
        evidence: [...entry.evidence].slice(0, 8),
        recommendedAction,
        assignedWorkerIds,
        committeeId: chooseOperatorCommittee(assignedWorkerIds),
        pillarIds: uniqueStrings([
          ...entry.pillarIds,
          "growth",
          "sales",
          "product",
          ...(entry.billingViewed || entry.reserveAdded ? ["finance"] : []),
          ...(entry.mfaEnabled || entry.mfaIncomplete ? ["compliance-risk"] : []),
        ]),
        archiveRef: archive,
        status: riskScore >= 70 ? "escalated" : activationScore >= 75 ? "ready" : riskScore >= 45 ? "watch" : "open",
        sourceEventIds: [...entry.eventIds],
      } satisfies OperatingSignal;
    })
    .sort((left, right) => {
      const rightWeight = (right.riskScore * 1.1) + right.score;
      const leftWeight = (left.riskScore * 1.1) + left.score;
      return rightWeight - leftWeight;
    });
}

function buildGrowthOpportunities(): OperatingSignal[] {
  const opportunities: OperatingSignal[] = [];
  const builderArchive = state.archives.find((archive) => archive.title.toLowerCase().includes("builder") || archive.summary.toLowerCase().includes("builder"));

  for (const event of state.backendEvents) {
    const text = `${event.eventType} ${event.entityType} ${event.status} ${JSON.stringify(event.payload)}`.toLowerCase();
    if (!/(marketplace|install|vendor|partner|integration|tool|registry|github)/.test(text)) {
      continue;
    }

    const title =
      getPayloadString(event.payload, ["opportunity_title", "integration_name", "tool_name", "vendor_name"]) ||
      `${event.entityType} opportunity`;
    const accountLabel =
      getPayloadString(event.payload, ["workspace_name", "organization", "org", "account_name"]) ||
      event.workspaceId ||
      event.entityId;
    const score = clamp(
      Math.round(
        (event.severity === "critical" ? 82 : event.severity === "warning" ? 68 : 56) +
        (/(broken|missing|failed|gap|abandoned)/.test(text) ? 12 : 0),
      ),
      0,
      99,
    );
    const workers = /(tool|integration|github|registry)/.test(text)
      ? ["builder-scout", "builder-forge", "builder-arbiter"]
      : ["harvest", "scout", "signal"];

    opportunities.push({
      id: `growth-${event.eventId}`,
      kind: "growth",
      title,
      summary: `UACP detected a ${event.entityType} opportunity from backend truth and mapped it into a governed worker route.`,
      category: /(tool|integration|github|registry)/.test(text) ? "tool" : "buyer",
      accountLabel,
      score,
      riskScore: clamp(Math.round(score * 0.45), 10, 75),
      confidence: clamp(0.45 + (event.workerIds.length * 0.07), 0.45, 0.92),
      evidence: [
        `Backend event ${event.eventType} arrived with ${event.severity} severity.`,
        `Entity: ${event.entityType}/${event.entityId}.`,
        ...(event.workspaceId ? [`Workspace context: ${event.workspaceId}.`] : []),
      ],
      recommendedAction: /(tool|integration|github|registry)/.test(text)
        ? "Validate the pain with Builder Scout, open a clean-room spec, and gate the route through Builder Arbiter."
        : "Qualify the account or vendor path, then route the best next move through Harvest and Scout.",
      assignedWorkerIds: workers,
      committeeId: chooseOperatorCommittee(workers),
      pillarIds: /(tool|integration|github|registry)/.test(text)
        ? ["engineering", "product", "knowledge-research"]
        : ["growth", "sales", "operations"],
      archiveRef: event.archiveId || builderArchive?.id,
      status: score >= 72 ? "ready" : "open",
      sourceEventIds: [event.eventId],
    });
  }

  return opportunities
    .sort((left, right) => (right.score + right.confidence * 10) - (left.score + left.confidence * 10))
    .slice(0, 12);
}

function buildFieldIntelligenceSignals(evaluationSignals: OperatingSignal[]): OperatingSignal[] {
  const intelligence: OperatingSignal[] = [];
  const evaluationCliff = evaluationSignals.filter((signal) => (signal.runsLimit || 0) > 0 && (signal.runsUsed || 0) >= (signal.runsLimit || 0) && !/reserve live/.test(signal.reserveState || ""));
  const evidenceMoment = evaluationSignals.filter((signal) => signal.evidenceActivity && signal.evidenceActivity !== "none");
  const endpointMoment = evaluationSignals.filter((signal) => signal.endpointStatus === "created + tested");
  const mfaGate = evaluationSignals.filter((signal) => signal.mfaState === "incomplete");

  if (evaluationCliff.length > 0) {
    intelligence.push({
      id: "intel-evaluation-cliff",
      kind: "field-intelligence",
      title: "The Evaluation Cliff",
      summary: "Accounts that consume the full evaluation allowance without reserve activation are the clearest stall pattern in the product truth.",
      category: "activation-pattern",
      accountLabel: `${evaluationCliff.length} accounts`,
      score: clamp(58 + evaluationCliff.length * 6, 58, 96),
      riskScore: clamp(45 + evaluationCliff.length * 7, 45, 92),
      confidence: clamp(0.42 + evaluationCliff.length * 0.08, 0.42, 0.94),
      evidence: evaluationCliff.slice(0, 4).map((signal) => `${signal.accountLabel} hit ${signal.runsUsed}/${signal.runsLimit} without reserve activation.`),
      recommendedAction: "Welcome, Mint, and Ledger should convert this pattern into a direct activation explanation sequence with evidence attached.",
      assignedWorkerIds: ["welcome", "mint", "ledger", "gauge"],
      committeeId: chooseOperatorCommittee(["welcome", "mint", "ledger", "gauge"]),
      pillarIds: ["growth", "sales", "finance", "product"],
      archiveRef: evaluationCliff.find((signal) => signal.archiveRef)?.archiveRef,
      status: "watch",
      sourceEventIds: evaluationCliff.flatMap((signal) => signal.sourceEventIds).slice(0, 10),
    });
  }

  if (evidenceMoment.length > 0) {
    intelligence.push({
      id: "intel-evidence-signal",
      kind: "field-intelligence",
      title: "The Evidence Signal",
      summary: "Evidence interaction is a stronger operator-intent signal than casual prompt activity, especially once an endpoint has been tested.",
      category: "buyer-intent",
      accountLabel: `${evidenceMoment.length} accounts`,
      score: clamp(52 + evidenceMoment.length * 5, 52, 92),
      riskScore: 28,
      confidence: clamp(0.4 + evidenceMoment.length * 0.08, 0.4, 0.93),
      evidence: evidenceMoment.slice(0, 4).map((signal) => `${signal.accountLabel} touched evidence before activation.`),
      recommendedAction: "Ledger should package the strongest proof assets while Welcome sequences the correct activation message.",
      assignedWorkerIds: ["ledger", "welcome", "signal"],
      committeeId: chooseOperatorCommittee(["ledger", "welcome", "signal"]),
      pillarIds: ["growth", "sales", "knowledge-research"],
      archiveRef: evidenceMoment.find((signal) => signal.archiveRef)?.archiveRef,
      status: "open",
      sourceEventIds: evidenceMoment.flatMap((signal) => signal.sourceEventIds).slice(0, 10),
    });
  }

  if (endpointMoment.length > 0) {
    intelligence.push({
      id: "intel-endpoint-moment",
      kind: "field-intelligence",
      title: "The Endpoint Moment",
      summary: "A successful endpoint test is the cleanest threshold from casual evaluation into serious deployment intent.",
      category: "technical-success",
      accountLabel: `${endpointMoment.length} accounts`,
      score: clamp(60 + endpointMoment.length * 4, 60, 90),
      riskScore: 22,
      confidence: clamp(0.45 + endpointMoment.length * 0.07, 0.45, 0.91),
      evidence: endpointMoment.slice(0, 4).map((signal) => `${signal.accountLabel} created and tested an endpoint successfully.`),
      recommendedAction: "Sentinel and Pulse should protect the path while Welcome and Harvest convert the account into a guided deployment conversation.",
      assignedWorkerIds: ["sentinel", "pulse", "welcome", "harvest"],
      committeeId: chooseOperatorCommittee(["sentinel", "pulse", "welcome", "harvest"]),
      pillarIds: ["product", "engineering", "growth", "sales"],
      archiveRef: endpointMoment.find((signal) => signal.archiveRef)?.archiveRef,
      status: "ready",
      sourceEventIds: endpointMoment.flatMap((signal) => signal.sourceEventIds).slice(0, 10),
    });
  }

  if (mfaGate.length > 0) {
    intelligence.push({
      id: "intel-mfa-trust-gate",
      kind: "field-intelligence",
      title: "The MFA Trust Gate",
      summary: "Security completion is a gating signal for regulated or serious accounts; partial setup creates avoidable drag.",
      category: "security-readiness",
      accountLabel: `${mfaGate.length} accounts`,
      score: clamp(54 + mfaGate.length * 5, 54, 88),
      riskScore: clamp(48 + mfaGate.length * 6, 48, 90),
      confidence: clamp(0.4 + mfaGate.length * 0.08, 0.4, 0.92),
      evidence: mfaGate.slice(0, 4).map((signal) => `${signal.accountLabel} is still blocked on MFA or security completion.`),
      recommendedAction: "Ledger, Sheriff, and Welcome should convert security friction into a clear readiness checklist before deeper access is granted.",
      assignedWorkerIds: ["ledger", "sheriff", "welcome"],
      committeeId: chooseOperatorCommittee(["ledger", "sheriff", "welcome"]),
      pillarIds: ["compliance-risk", "governance", "growth"],
      archiveRef: mfaGate.find((signal) => signal.archiveRef)?.archiveRef,
      status: "watch",
      sourceEventIds: mfaGate.flatMap((signal) => signal.sourceEventIds).slice(0, 10),
    });
  }

  return intelligence.sort((left, right) => (right.score + right.riskScore) - (left.score + left.riskScore));
}

function defaultWorkerIdsForSignal(kind: OperatingSignal["kind"]) {
  switch (kind) {
    case "evaluation":
      return ["gauge", "welcome", "ledger"];
    case "growth":
      return ["harvest", "scout", "signal"];
    case "field-intelligence":
      return ["signal", "ledger", "gauge"];
    default:
      return ["gauge"];
  }
}

function normalizeSignalStatus(
  value: unknown,
  score: number,
  riskScore: number,
): OperatingSignal["status"] {
  if (value === "ready" || value === "watch" || value === "open" || value === "escalated") {
    return value;
  }

  if (riskScore >= 70) return "escalated";
  if (score >= 75) return "ready";
  if (riskScore >= 45 || score >= 55) return "watch";
  return "open";
}

function normalizeConfidence(value: unknown, fallback = 0.65) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return clamp(fallback, 0.2, 0.99);
  const normalized = parsed > 1 ? parsed / 100 : parsed;
  return clamp(normalized, 0.2, 0.99);
}

function signalSlug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function normalizeRemoteSunnyvaleSignal(
  record: Record<string, unknown>,
  kind: OperatingSignal["kind"],
  index: number,
): OperatingSignal {
  const accountLabel =
    getRecordString(record, ["account_label", "workspace_name", "account_name", "customer_name", "org", "organization", "workspace_id"]) ||
    `${kind}-${index + 1}`;
  const title =
    getRecordString(record, ["title", "name", "opportunity_title", "headline"]) ||
    (kind === "evaluation" ? `${accountLabel} evaluation signal` : `${accountLabel} ${kind} signal`);
  const workspaceId = getRecordString(record, ["workspace_id", "workspaceId", "tenant_id", "tenantId", "account_id"]);
  const score = clamp(
    Math.round(
      getRecordNumber(record, ["score", "activation_score", "opportunity_score", "priority", "rank_score", "priority_score"]) ??
      (normalizeConfidence(record.confidence ?? record.confidence_score, 0.65) * 100),
    ),
    0,
    99,
  );
  const riskScore = clamp(
    Math.round(
      getRecordNumber(record, ["risk_score", "risk", "riskScore", "severity_score", "severity"]) ??
      (kind === "evaluation" ? score * 0.55 : score * 0.4),
    ),
    0,
    100,
  );
  const assignedWorkerIds = uniqueStrings(
    getRecordStringArray(record, ["assigned_worker_ids", "worker_ids", "workers", "assignedWorkers"]).concat(defaultWorkerIdsForSignal(kind)),
  );
  const evidence = uniqueStrings(
    getRecordStringArray(record, ["evidence", "evidence_refs", "evidence_items", "proof", "signals"]),
  );
  const sourceEventIds = uniqueStrings(
    getRecordStringArray(record, ["source_event_ids", "event_ids", "backend_event_ids", "source_ids"]),
  );
  const confidence = normalizeConfidence(
    record.confidence ?? record.confidence_score ?? record.worker_confidence ?? record.certainty,
    score / 100,
  );
  const recommendedAction =
    getRecordString(record, ["recommended_action", "top_action", "next_action", "action", "proposed_action"]) ||
    (kind === "growth"
      ? "Qualify the opportunity and route the next governed build or commercial action."
      : kind === "field-intelligence"
        ? "Convert the repeated pattern into a governed institutional response."
        : "Advance the workspace through the next governed evaluation action.");
  const summary =
    getRecordString(record, ["summary", "description", "reason", "rationale", "detail", "details"]) ||
    recommendedAction;
  const signalId =
    getRecordString(record, ["id", "signal_id", "workspace_id", "run_id", "deployment_id", "archive_id"]) ||
    `${kind}-${signalSlug(accountLabel)}-${index + 1}`;
  const pillarIds = uniqueStrings(
    getRecordStringArray(record, ["pillar_ids", "pillars"]).concat(
      kind === "growth"
        ? ["growth", "sales"]
        : kind === "field-intelligence"
          ? ["knowledge-research", "governance"]
          : ["growth", "product", "sales"],
    ),
  );

  return {
    id: signalId,
    kind,
    title,
    summary: trimText(summary, 280),
    category: getRecordString(record, ["category", "signal_type", "opportunity_type", "entity_type", "queue", "kind"]) || kind,
    accountLabel,
    workspaceId,
    tier: getRecordString(record, ["tier", "plan_tier", "workspace_tier", "account_tier"]),
    evaluationStage: getRecordString(record, ["evaluation_stage", "stage", "lifecycle_stage"]),
    lastActivityAt: getRecordString(record, ["last_activity_at", "updated_at", "as_of", "created_at"]),
    runsUsed: getRecordNumber(record, ["runs_used", "run_count", "count", "usage_count"]),
    runsLimit: getRecordNumber(record, ["runs_limit", "run_limit", "evaluation_limit", "trial_limit"]),
    endpointStatus: getRecordString(record, ["endpoint_status", "endpoint", "route_status", "deployment_status"]),
    evidenceActivity: getRecordString(record, ["evidence_activity", "evidence_status", "evidence_state"]),
    billingState: getRecordString(record, ["billing_state", "billing_status", "pricing_state"]),
    reserveState: getRecordString(record, ["reserve_state", "reserve_status", "reserve_balance_state"]),
    mfaState: getRecordString(record, ["mfa_state", "security_state", "auth_state"]),
    errorsCount: getRecordNumber(record, ["errors_count", "error_count", "failed_routes", "failures"]),
    score,
    riskScore,
    confidence,
    evidence: evidence.length > 0 ? evidence : [trimText(summary, 120)],
    recommendedAction,
    assignedWorkerIds,
    committeeId: getRecordString(record, ["committee_id", "owner_committee_id", "committee"]) || chooseOperatorCommittee(assignedWorkerIds),
    pillarIds,
    archiveRef: getRecordString(record, ["archive_ref", "archive_id", "archive"]),
    status: normalizeSignalStatus(record.status ?? record.queue_status, score, riskScore),
    sourceEventIds,
  };
}

function mergeSunnyvaleOverview(
  fallback: SunnyvaleOverview,
  remoteSummary: RemoteSunnyvaleSummaryEnvelope | null,
  evaluationSignals: OperatingSignal[],
  growthOpportunities: OperatingSignal[],
  fieldIntelligence: OperatingSignal[],
): SunnyvaleOverview {
  const sunnyvale = asRecord(remoteSummary?.sunnyvale) || remoteSummary || {};
  const totalSignals = evaluationSignals.length + growthOpportunities.length + fieldIntelligence.length;
  const seriousSignals =
    evaluationSignals.filter((signal) => signal.riskScore >= 65 || signal.score >= 70).length +
    growthOpportunities.filter((signal) => signal.score >= 75).length;

  return {
    totalSignals: Math.round(getRecordNumber(sunnyvale, ["total_signals", "signal_count"]) ?? totalSignals),
    activeEvaluations: Math.round(
      getRecordNumber(sunnyvale, ["active_evaluations", "evaluation_count", "evaluation_surgeon_queue_count"]) ?? evaluationSignals.length,
    ),
    seriousSignals: Math.round(getRecordNumber(sunnyvale, ["serious_signals", "serious_signal_count"]) ?? seriousSignals),
    reserveBalance: getRecordNumber(sunnyvale, ["reserve_balance", "reserve", "reserve_live"]) ?? fallback.reserveBalance,
    workerConfidence: Math.round(
      getRecordNumber(sunnyvale, ["worker_confidence", "worker_confidence_pct", "confidence_percent"]) ?? fallback.workerConfidence,
    ),
    liveWorkers: Math.round(getRecordNumber(sunnyvale, ["live_workers", "running_workers", "workers_live"]) ?? fallback.liveWorkers),
    failedRoutes: Math.round(getRecordNumber(sunnyvale, ["failed_routes", "route_failures", "failed_route_count"]) ?? fallback.failedRoutes),
    evidenceExports: Math.round(getRecordNumber(sunnyvale, ["evidence_exports", "evidence_export_count"]) ?? fallback.evidenceExports),
    lastBackendEventAt:
      getRecordString(sunnyvale, ["last_backend_event_at", "last_event_at", "as_of", "updated_at"]) || fallback.lastBackendEventAt,
  };
}

function buildLocalSunnyvaleInternalSnapshot(): SunnyvaleInternalSnapshot {
  const telemetry = buildTelemetry();
  const evaluationSignals = buildEvaluationSignals();
  const growthOpportunities = buildGrowthOpportunities();
  const fieldIntelligence = buildFieldIntelligenceSignals(evaluationSignals);
  const liveWorkers = state.workerRuntime.filter((runtime) => runtime.status === "running" || minutesSince(runtime.lastHeartbeatAt) <= 20).length;
  const seriousSignals =
    evaluationSignals.filter((signal) => signal.riskScore >= 65 || signal.score >= 70).length +
    growthOpportunities.filter((signal) => signal.score >= 75).length;

  return {
    mode: state.backendEvents.length > 0 ? "live" : state.researchSignals.length > 0 ? "research-only" : "waiting",
    asOf: now(),
    source: "local-fallback",
    bridgeStatus: {
      enabled: false,
      baseUrlConfigured: Boolean(UACP_BACKEND_BASE_URL),
      internalKeyConfigured: Boolean(INTERNAL_API_KEY),
    },
    overview: {
      totalSignals: evaluationSignals.length + growthOpportunities.length + fieldIntelligence.length,
      activeEvaluations: evaluationSignals.length,
      seriousSignals,
      reserveBalance: state.backendSummary.reserveBalance,
      workerConfidence: Math.round(telemetry.determinismScore * 100),
      liveWorkers,
      failedRoutes: state.backendSummary.failedRoutes,
      evidenceExports: state.backendSummary.evidenceExports,
      lastBackendEventAt: state.backendSummary.lastEventAt,
    },
    evaluationSignals,
    growthOpportunities,
    fieldIntelligence,
  };
}

async function buildSunnyvaleInternalSnapshot(): Promise<SunnyvaleInternalSnapshot> {
  const fallback = buildLocalSunnyvaleInternalSnapshot();

  if (!UACP_BACKEND_BASE_URL || !INTERNAL_API_KEY) {
    fallback.bridgeStatus = {
      enabled: false,
      baseUrlConfigured: Boolean(UACP_BACKEND_BASE_URL),
      internalKeyConfigured: Boolean(INTERNAL_API_KEY),
    };
    return fallback;
  }

  try {
    const [summaryEnvelope, evaluationPayload, growthPayload] = await Promise.all([
      fetchInternalBackendJson<RemoteSunnyvaleSummaryEnvelope>("/api/v1/internal/uacp/summary"),
      fetchInternalBackendJson<unknown>("/api/v1/internal/uacp/evaluation-surgeon"),
      fetchInternalBackendJson<unknown>("/api/v1/internal/uacp/growth-opportunities"),
    ]);

    const summarySunnyvale = asRecord(summaryEnvelope?.sunnyvale);
    const evaluationRecords = extractQueueRecords(
      evaluationPayload,
      "evaluation_surgeon_queue",
    ).length > 0
      ? extractQueueRecords(evaluationPayload, "evaluation_surgeon_queue")
      : extractQueueRecords(summarySunnyvale?.evaluation_surgeon_queue, "evaluation_surgeon_queue");
    const growthRecords = extractQueueRecords(
      growthPayload,
      "hub_growth_opportunities",
    ).length > 0
      ? extractQueueRecords(growthPayload, "hub_growth_opportunities")
      : extractQueueRecords(summarySunnyvale?.hub_growth_opportunities, "hub_growth_opportunities");

    if (evaluationRecords.length === 0 && growthRecords.length === 0) {
      return fallback;
    }

    const evaluationSignals = evaluationRecords.length > 0
      ? evaluationRecords.map((record, index) => normalizeRemoteSunnyvaleSignal(record, "evaluation", index))
      : fallback.evaluationSignals;
    const growthOpportunities = growthRecords.length > 0
      ? growthRecords.map((record, index) => normalizeRemoteSunnyvaleSignal(record, "growth", index))
      : fallback.growthOpportunities;
    const fieldIntelligence = buildFieldIntelligenceSignals(evaluationSignals);

    return {
      mode: "live",
      asOf: now(),
      source: "backend-truth",
      bridgeStatus: {
        enabled: true,
        baseUrlConfigured: true,
        internalKeyConfigured: true,
      },
      overview: mergeSunnyvaleOverview(fallback.overview, summaryEnvelope, evaluationSignals, growthOpportunities, fieldIntelligence),
      evaluationSignals,
      growthOpportunities,
      fieldIntelligence,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.warn(`[uacp] sunnyvale backend bridge failed: ${message}`);
    fallback.bridgeStatus = {
      enabled: false,
      baseUrlConfigured: Boolean(UACP_BACKEND_BASE_URL),
      internalKeyConfigured: Boolean(INTERNAL_API_KEY),
      lastError: message,
    };
    return fallback;
  }
}

function workerInputSnapshot(worker: OperatorWorker) {
  const observability = buildEngineObservability();
  const telemetry = buildTelemetry();
  const inputs: string[] = [];

  for (const source of worker.inputSources) {
    if (source === "events") {
      inputs.push(...state.events.slice(0, 5).map((event) => `event:${event.type}:${event.id}`));
    } else if (source === "archives") {
      inputs.push(...state.archives.slice(0, 5).map((archive) => `archive:${archive.id}:${archive.category}`));
    } else if (source === "research-signals") {
      inputs.push(...state.researchSignals.slice(0, 5).map((signal) => `signal:${signal.source}:${signal.id}`));
    } else if (source === "research-status") {
      inputs.push(...state.researchStatus.map((status) => `source:${status.id}:${status.status}`));
    } else if (source === "plans") {
      inputs.push(...state.plans.slice(0, 4).map((plan) => `plan:${plan.id}:${plan.status}`));
    } else if (source === "runs") {
      inputs.push(...state.runs.slice(0, 4).map((run) => `run:${run.id}:${run.status}`));
    } else if (source === "telemetry") {
      inputs.push(`telemetry:determinism:${telemetry.determinismScore.toFixed(3)}`);
      inputs.push(`telemetry:policy:${telemetry.policyAlignment.toFixed(3)}`);
      inputs.push(`telemetry:archive:${telemetry.archiveCoverage.toFixed(3)}`);
    } else if (source === "observability") {
      inputs.push(`observability:pressure:${observability.uacp_pressure.toFixed(3)}`);
      inputs.push(`observability:latency:${observability.classical_latency}`);
    } else if (source === "backend-events") {
      inputs.push(...state.backendEvents.slice(0, 5).map((event) => `backend:${event.eventType}:${event.eventId}`));
    } else if (source === "backend-summary") {
      inputs.push(`backend:liveUsers:${state.backendSummary.liveUsers}`);
      inputs.push(`backend:reserve:${state.backendSummary.reserveBalance}`);
    }
  }

  return uniqueStrings(inputs).slice(0, 12);
}

function determineWorkerEscalations(worker: OperatorWorker, inputs: string[]) {
  const escalations: string[] = [];

  if (worker.escalationRuleId === "missing-live-evidence") {
    const evidenceInputs = operationalEvidenceCount(inputs);
    const researchSourceAvailability = average(
      state.researchStatus.map((status) => (
        status.status === "online" ? 1 : status.status === "degraded" ? 0.5 : 0
      )),
    ) || (state.researchStatus.length === 0 ? 1 : 0);

    const shouldEscalateMissingEvidence =
      !inStartupPrimingWindow() &&
      evidenceInputs === 0 &&
      (systemHasOperationalEvidenceInventory() || researchSourceAvailability < 0.4);

    if (shouldEscalateMissingEvidence) {
      escalations.push("missing-live-evidence");
    }
  }
  if (
    worker.escalationRuleId === "regulated-objective-review" &&
    (state.plans.some((plan) => plan.riskTier === "high" || plan.riskTier === "critical") ||
      state.backendEvents.some((event) => event.severity === "critical"))
  ) {
    escalations.push("regulated-objective-review");
  }
  if (
    worker.escalationRuleId === "unapproved-skill-attempt" &&
    state.plans.some((plan) => (plan.proposals || []).some((proposal) => proposal.type === "skill"))
  ) {
    escalations.push("unapproved-skill-attempt");
  }

  if (state.runs.some((run) => run.status === "failed" || run.status === "blocked")) {
    escalations.push("execution-floor-attention");
  }

  return uniqueStrings(escalations);
}

function determineWorkerActions(worker: OperatorWorker, escalations: string[]) {
  if (escalations.length > 0) {
    return worker.allowedActions
      .filter((action) => /(flag|escalat|deny|verify|write|open)/.test(action))
      .slice(0, 3);
  }

  if (state.backendEvents.some((event) => event.workerIds.includes(worker.id))) {
    return worker.allowedActions
      .filter((action) => /(write|recommend|route|compare|measure|scan|summarize|verify)/.test(action))
      .slice(0, 3);
  }

  return worker.allowedActions.slice(0, Math.min(3, worker.allowedActions.length));
}

function determineWorkerRecommendation(worker: OperatorWorker, escalations: string[]) {
  if (escalations.length > 0) {
    return `${worker.displayName} raised ${escalations.join(", ")}. Founder review or committee intervention is required before the next scheduled run.`;
  }

  const committee = operatorCommitteeById(worker.committeeId);
  const backlog = committee ? committeeBacklog(committee.id) : [];
  if (backlog.length > 0) {
    return `${worker.displayName} should rejoin ${committee?.name || worker.committeeId} and take the next backlog item: ${backlog[0]}.`;
  }

  if (state.backendEvents.some((event) => event.workerIds.includes(worker.id))) {
    return `${worker.displayName} should continue monitoring assigned backend truth and write the next governed update on schedule.`;
  }

  return `${worker.displayName} should maintain heartbeat discipline and wait for the next scheduled operating window.`;
}

function resolveWorkerNextRunMinutes(worker: OperatorWorker) {
  const committee = operatorCommitteeById(worker.committeeId);
  const backlog = committee ? committeeBacklog(committee.id) : [];
  if (backlog.length > 0) {
    return Math.min(worker.intervalMinutes, 45);
  }
  return worker.intervalMinutes;
}

function queueCommitteeRegroup(committee: OperatorCommittee) {
  const backlog = committeeBacklog(committee.id);
  addEvent("COMMITTEE_REGROUP", `${committee.name} regrouped to review backlog, assignments, and current execution window.`, "silicon-valley", {
    committeeId: committee.id,
    cadencePerDay: committee.cadencePerDay || 3,
    regroupIntervalMinutes: committeeRegroupIntervalMinutes(committee),
    activeExecutionWindow: activeExecutionWindow().id,
    backlog,
  });

  const regroupBase = Date.now();
  for (const workerId of committee.workerIds) {
    const worker = workerById(workerId);
    if (!worker) continue;

    const hasActiveRun = state.operatorRuns.some((run) => run.workerId === workerId && (run.status === "queued" || run.status === "running"));
    if (hasActiveRun) continue;

    const runtime = state.workerRuntime.find((entry) => entry.workerId === workerId) || makeWorkerRuntime(worker);
    if (runtime.paused) continue;

    const offsetMinutes = workerConveyorOffsetMinutes(worker);
    setWorkerRuntime(workerId, {
      status: runtime.status === "error" ? "error" : "idle",
      nextRunAt: isoAfterMinutes(offsetMinutes, regroupBase),
    });
  }
}

function queueOperatorRun(workerId: string, trigger: "manual" | "scheduled" | "backend-event", inputHint?: string) {
  const worker = workerById(workerId);
  if (!worker) {
    throw new Error(`Unknown worker ${workerId}.`);
  }

  const runtime = state.workerRuntime.find((entry) => entry.workerId === workerId) || makeWorkerRuntime(worker);
  if (runtime.paused) {
    throw new Error(`${worker.displayName} is paused and cannot be scheduled.`);
  }
  if (state.operatorRuns.some((run) => run.workerId === workerId && (run.status === "queued" || run.status === "running"))) {
    throw new Error(`${worker.displayName} already has an active operator run.`);
  }

  const committee = operatorCommitteeById(worker.committeeId);
  const run: OperatorRun = {
    id: createId("oprun"),
    workerId: worker.id,
    committeeId: worker.committeeId,
    pillarId: worker.primaryPillar,
    startedAt: now(),
    status: "queued",
    inputs: inputHint ? [inputHint] : [],
    actionsTaken: [],
    evidenceCreated: [],
    archiveRef: undefined,
    escalations: [],
    errors: [],
    nextRecommendation: `${worker.displayName} is queued for ${trigger} execution.`,
  };

  state.operatorRuns = [run, ...state.operatorRuns].slice(0, MAX_OPERATOR_RUNS);
  setWorkerRuntime(worker.id, {
    status: "running",
      paused: false,
      lastHeartbeatAt: now(),
      lastRunId: run.id,
      nextRunAt: undefined,
    });
  addEvent("WORKER_RUN_QUEUED", `${worker.displayName} queued for ${trigger} execution.`, "silicon-valley", {
    workerId: worker.id,
    committeeId: committee?.id,
    runId: run.id,
    trigger,
  });
  broadcast({ type: "operator_run_update", data: run });
  void persistState();
  void executeOperatorRun(run.id);
  return run;
}

function releasePlanSearchWorkers(plan: InstitutionalPlan) {
  const workerIds = uniqueStrings([
    "signal",
    "scout",
    "builder-scout",
    "welcome",
    ...(plan.pillars.includes("growth") ? ["vendor-scout"] : []),
    ...(plan.pillars.includes("sales") ? ["mint"] : []),
  ]);
  const releasedRunIds: string[] = [];
  const skipped: Array<{ workerId: string; reason: string }> = [];

  for (const workerId of workerIds) {
    try {
      const run = queueOperatorRun(workerId, "manual", `plan-search:${plan.id}:${plan.researchQuery || plan.intent}`);
      releasedRunIds.push(run.id);
    } catch (error) {
      skipped.push({
        workerId,
        reason: error instanceof Error ? error.message : "Unknown worker release failure.",
      });
    }
  }

  addEvent("PLAN_SEARCH_WORKERS_RELEASED", `Plan ${plan.id} released ${releasedRunIds.length} search-pressure worker run(s).`, "deterministic-engine", {
    planId: plan.id,
    workerIds,
    releasedRunIds,
    skipped,
  });

  return { releasedRunIds, skipped };
}

async function executeOperatorRun(runId: string) {
  const run = state.operatorRuns.find((entry) => entry.id === runId);
  if (!run) return;
  const worker = workerById(run.workerId);
  if (!worker) return;

  try {
    const inputs = uniqueStrings([...run.inputs, ...workerInputSnapshot(worker)]);
    const escalations = determineWorkerEscalations(worker, inputs);
    let actionsTaken = determineWorkerActions(worker, escalations);
    const nextRecommendation = determineWorkerRecommendation(worker, escalations);
    const committee = operatorCommitteeById(worker.committeeId);

    run.status = escalations.length > 0 ? "escalated" : "running";
    run.inputs = inputs;
    run.actionsTaken = actionsTaken;
    run.escalations = escalations;
    run.nextRecommendation = nextRecommendation;
    setWorkerRuntime(worker.id, {
      status: escalations.length > 0 ? "error" : "running",
      paused: false,
      lastHeartbeatAt: now(),
      lastRunAt: now(),
      lastRunId: run.id,
      lastError: escalations.length > 0 ? escalations.join(", ") : undefined,
    });
    broadcast({ type: "operator_run_update", data: run });

    const outboundExecution = await executeWorkerOutboundTasks(worker, run);
    actionsTaken = uniqueStrings([...actionsTaken, ...outboundExecution.actions]);
    run.actionsTaken = actionsTaken;

    const archive = addArchive({
      title: `${worker.displayName} ${worker.outputArtifact}`,
      category: "run",
      summary: `${worker.displayName} executed under ${committee?.name || worker.committeeId} using ${inputs.length} live inputs and ${actionsTaken.length} governed actions.`,
      lineage: [run.id, worker.id, worker.committeeId, worker.primaryPillar],
      metadata: {
        workerId: worker.id,
        committeeId: worker.committeeId,
        trigger: run.inputs[0] || "scheduled",
        inputs,
        actionsTaken,
        escalations,
        nextRecommendation,
        outboundMessageIds: outboundExecution.outboundMessageIds,
      },
    });

    run.archiveRef = archive.id;
    run.evidenceCreated = uniqueStrings([archive.id, ...outboundExecution.evidenceCreated]);
    run.completedAt = now();
    run.status = escalations.length > 0 ? "escalated" : "completed";
    run.nextRecommendation = nextRecommendation;
    setWorkerRuntime(worker.id, {
      status: escalations.length > 0 ? "error" : "idle",
      paused: false,
      lastHeartbeatAt: now(),
      lastRunAt: run.completedAt,
      lastRunId: run.id,
      nextRunAt: isoAfterMinutes(resolveWorkerNextRunMinutes(worker)),
      lastError: escalations.length > 0 ? escalations.join(", ") : undefined,
    });

    addEvent(worker.archiveEventType.toUpperCase(), `${worker.displayName} completed a governed operator run.`, "silicon-valley", {
      workerId: worker.id,
      runId: run.id,
      archiveId: archive.id,
      escalations,
    });
    broadcast({ type: "operator_run_update", data: run });
    captureMetricHistory();
    await persistState();
  } catch (error) {
    run.status = "failed";
    run.completedAt = now();
    run.errors = [error instanceof Error ? error.message : "Unknown worker runtime failure."];
    run.nextRecommendation = `${worker.displayName} failed and requires operator review before the next heartbeat.`;
    setWorkerRuntime(worker.id, {
      status: "error",
      paused: false,
      lastHeartbeatAt: now(),
      lastRunAt: run.completedAt,
      lastRunId: run.id,
      nextRunAt: isoAfterMinutes(resolveWorkerNextRunMinutes(worker)),
      lastError: run.errors.join(", "),
    });
    addEvent("WORKER_RUN_FAILED", `${worker.displayName} failed during operator execution.`, "silicon-valley", {
      workerId: worker.id,
      runId: run.id,
      errors: run.errors,
    });
    broadcast({ type: "operator_run_update", data: run });
    await persistState();
  }
}

async function operatorSchedulerTick() {
  for (const committee of activeOperatorCommittees()) {
    const nextRegroupAt = Date.parse(nextCommitteeRegroupAt(committee));
    if (Number.isFinite(nextRegroupAt) && nextRegroupAt <= Date.now()) {
      queueCommitteeRegroup(committee);
    }
  }

  const dueWorkers = state.workerRuntime
    .filter((runtime) => !runtime.paused && runtime.nextRunAt && new Date(runtime.nextRunAt).getTime() <= Date.now())
    .sort((left, right) => new Date(left.nextRunAt || 0).getTime() - new Date(right.nextRunAt || 0).getTime())
    .map((runtime) => runtime.workerId);

  for (const workerId of dueWorkers.slice(0, UACP_SCHEDULER_MAX_RELEASE_PER_TICK)) {
    try {
      queueOperatorRun(workerId, "scheduled", "scheduled-heartbeat");
    } catch {
      continue;
    }
  }
}

function ingestBackendEvent(candidate: unknown) {
  const record = ensureRecord(candidate, "backendEvent");
  const eventType = ensureString(record.event_type ?? record.eventType, "backendEvent.event_type");
  const entityType = ensureString(record.entity_type ?? record.entityType, "backendEvent.entity_type");
  const entityId = ensureString(record.entity_id ?? record.entityId, "backendEvent.entity_id");
  const status = ensureString(record.status, "backendEvent.status");
  const timestamp = parseDate(record.timestamp ?? now());
  const payload = record.payload && typeof record.payload === "object" && !Array.isArray(record.payload)
    ? record.payload as Record<string, unknown>
    : {};
  const severity = normalizeBackendSeverity(record.severity);
  const assignment = classifyBackendEvent({ eventType, entityType, severity, status, payload });

  const event: BackendProductEvent = {
    eventId: ensureString(record.event_id ?? record.eventId ?? createId("bevt"), "backendEvent.event_id"),
    eventType,
    source: "backend",
    workspaceId: typeof record.workspace_id === "string" ? record.workspace_id : typeof record.workspaceId === "string" ? record.workspaceId : undefined,
    tenantId: typeof record.tenant_id === "string" ? record.tenant_id : typeof record.tenantId === "string" ? record.tenantId : undefined,
    userId: typeof record.user_id === "string" ? record.user_id : typeof record.userId === "string" ? record.userId : undefined,
    entityType,
    entityId,
    severity,
    status,
    timestamp,
    payload,
    pillarIds: assignment.pillarIds,
    committeeIds: assignment.committeeIds,
    workerIds: assignment.workerIds.filter((workerId) => Boolean(workerById(workerId))),
    archiveId: undefined,
  };

  updateBackendSummaryFromEvent(event);
  queueOutboundContactFromBackendEvent(event);
  const archive = addArchive({
    title: `Backend event ${event.eventType}`,
    category: "research",
    summary: `Backend truth reported ${event.eventType} on ${event.entityType}/${event.entityId} with severity ${event.severity}.`,
    lineage: [event.eventId, event.entityId, ...(event.workspaceId ? [event.workspaceId] : [])],
    metadata: { backendEvent: event as unknown },
  });
  event.archiveId = archive.id;
  state.backendEvents = [event, ...state.backendEvents.filter((entry) => entry.eventId !== event.eventId)].slice(0, MAX_BACKEND_EVENTS);
  addEvent("BACKEND_EVENT_INGESTED", `${event.eventType} mapped to ${event.workerIds.length} workers.`, "silicon-valley", {
    eventId: event.eventId,
    entityType: event.entityType,
    workerIds: event.workerIds,
  });
  broadcast({ type: "backend_event", data: event });
  for (const workerId of event.workerIds.slice(0, 3)) {
    try {
      queueOperatorRun(workerId, "backend-event", `backend-event:${event.eventType}:${event.eventId}`);
    } catch {
      continue;
    }
  }
  void persistState();
  return event;
}

function hydrateRuntimeState(parsed?: Partial<RuntimeState> | null) {
  state = {
    plans: Array.isArray(parsed?.plans) ? parsed.plans : [],
    runs: Array.isArray(parsed?.runs) ? parsed.runs : [],
    operatorRuns: Array.isArray(parsed?.operatorRuns) ? parsed.operatorRuns : [],
    workerRuntime: Array.isArray(parsed?.workerRuntime) ? parsed.workerRuntime : [],
    backendEvents: Array.isArray(parsed?.backendEvents) ? parsed.backendEvents : [],
    backendSummary: parsed?.backendSummary && typeof parsed.backendSummary === "object"
      ? {
          ...emptyBackendTruthSummary(),
          ...parsed.backendSummary,
        }
      : emptyBackendTruthSummary(),
    events: Array.isArray(parsed?.events) ? parsed.events : [],
    archives: Array.isArray(parsed?.archives) ? parsed.archives : [],
    v3Plans: Array.isArray(parsed?.v3Plans) ? parsed.v3Plans : [],
    v3Runs: Array.isArray(parsed?.v3Runs) ? parsed.v3Runs : [],
    v3Events: Array.isArray(parsed?.v3Events) ? parsed.v3Events : [],
    v3Archives: Array.isArray(parsed?.v3Archives) ? parsed.v3Archives : [],
    v3ReplayRequests: Array.isArray(parsed?.v3ReplayRequests) ? parsed.v3ReplayRequests : [],
    v3ReplayResults: Array.isArray(parsed?.v3ReplayResults) ? parsed.v3ReplayResults : [],
    v3CommercialArtifacts: Array.isArray(parsed?.v3CommercialArtifacts) ? parsed.v3CommercialArtifacts : [],
    v3CommercialScorecard: parsed?.v3CommercialScorecard && typeof parsed.v3CommercialScorecard === "object"
      ? {
          ...emptyCommercialScorecard(),
          ...parsed.v3CommercialScorecard,
          lastUpdatedAt: typeof parsed.v3CommercialScorecard.lastUpdatedAt === "string"
            ? parsed.v3CommercialScorecard.lastUpdatedAt
            : now(),
        }
      : emptyCommercialScorecard(),
    researchSignals: Array.isArray(parsed?.researchSignals) ? parsed.researchSignals : [],
    researchStatus: Array.isArray(parsed?.researchStatus) ? parsed.researchStatus : [],
    outboundContacts: Array.isArray(parsed?.outboundContacts) ? parsed.outboundContacts : [],
    outboundMessages: Array.isArray(parsed?.outboundMessages) ? parsed.outboundMessages : [],
    stats: {
      planCompileDurationsMs: Array.isArray(parsed?.stats?.planCompileDurationsMs) ? parsed.stats?.planCompileDurationsMs : [],
      runDurationsMs: Array.isArray(parsed?.stats?.runDurationsMs) ? parsed.stats?.runDurationsMs : [],
      researchRefreshDurationsMs: Array.isArray(parsed?.stats?.researchRefreshDurationsMs) ? parsed.stats?.researchRefreshDurationsMs : [],
      determinismHistory: Array.isArray(parsed?.stats?.determinismHistory) ? parsed.stats?.determinismHistory : [],
      runCompletionHistory: Array.isArray(parsed?.stats?.runCompletionHistory) ? parsed.stats?.runCompletionHistory : [],
      policyAlignmentHistory: Array.isArray(parsed?.stats?.policyAlignmentHistory) ? parsed.stats?.policyAlignmentHistory : [],
      archiveCoverageHistory: Array.isArray(parsed?.stats?.archiveCoverageHistory) ? parsed.stats?.archiveCoverageHistory : [],
      sourceHealthHistory: Array.isArray(parsed?.stats?.sourceHealthHistory) ? parsed.stats?.sourceHealthHistory : [],
      pressureHistory: Array.isArray(parsed?.stats?.pressureHistory) ? parsed.stats?.pressureHistory : [],
      lastResearchSyncAt: parsed?.stats?.lastResearchSyncAt,
      lastGovernanceRegistryHash: parsed?.stats?.lastGovernanceRegistryHash,
      lastGovernanceRegistrySyncAt: parsed?.stats?.lastGovernanceRegistrySyncAt,
    },
  };
  normalizeEventHashChain();
  normalizeArchiveHashChain();
  normalizeV3AuditState();
  syncWorkerRuntimeState();
  normalizeWorkerRuntimeForStartup();
}

async function loadState() {
  try {
    const databaseState = await readDatabaseStore<Partial<RuntimeState>>("runtime_state");
    if (databaseState) {
      hydrateRuntimeState(databaseState);
      return;
    }
  } catch {
    // file fallback remains available below
  }

  try {
    const raw = await fs.readFile(STATE_FILE, "utf8");
    hydrateRuntimeState(JSON.parse(raw) as Partial<RuntimeState>);
    return;
  } catch {
    const snapshotState = await readCompressedSnapshot<Partial<RuntimeState>>(STATE_SNAPSHOT_FILE);
    hydrateRuntimeState(snapshotState || emptyState());
  }
}

function persistState() {
  persistQueue = persistQueue
    .then(async () => {
      await ensureDataDir();
      const writes = [
        fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2), "utf8"),
        writeCompressedSnapshot(STATE_SNAPSHOT_FILE, state),
      ];
      if (DATABASE_URL) {
        writes.unshift(writeDatabaseStore("runtime_state", state).then(() => undefined));
      }
      await Promise.allSettled(writes);
    })
    .catch((error) => {
      console.error("State persistence error:", error);
    });
  return persistQueue;
}

function ensureRecord(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function ensureString(value: unknown, label: string) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string.`);
  }
  return value.trim();
}

function ensureStringArray(value: unknown, label: string) {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string" || entry.trim().length === 0)) {
    throw new Error(`${label} must be an array of non-empty strings.`);
  }
  return uniqueStrings(value.map((entry) => entry.trim()));
}

function ensureNumber(value: unknown, label: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${label} must be a finite number.`);
  }
  return parsed;
}

function ensureUniqueIds<T extends { id: string }>(items: T[], label: string) {
  const ids = items.map((item) => item.id);
  if (new Set(ids).size !== ids.length) {
    throw new Error(`${label} contains duplicate ids.`);
  }
}

const V3_EVENT_HASH_ALGORITHM = "sha256" as const;
const V3_EVENT_SCHEMA_VERSION = "v3-event/1";
const V3_ARCHIVE_HASH_ALGORITHM = "sha256" as const;

function toStableValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => toStableValue(entry));
  }
  if (value && typeof value === "object") {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((accumulator, key) => {
        const nextValue = (value as Record<string, unknown>)[key];
        if (typeof nextValue !== "undefined") {
          accumulator[key] = toStableValue(nextValue);
        }
        return accumulator;
      }, {});
  }
  return value;
}

function canonicalizeForHash(value: unknown) {
  return JSON.stringify(toStableValue(value));
}

function sha256Hex(value: unknown) {
  return crypto.createHash("sha256").update(canonicalizeForHash(value)).digest("hex");
}

function computeV3PlanRevisionHash(plan: Pick<
  V3Plan,
  | "id"
  | "title"
  | "intent"
  | "revision"
  | "createdAt"
  | "pillars"
  | "committeeIds"
  | "workerIds"
  | "skillIds"
  | "route"
  | "requiredOutputs"
  | "approvalPath"
  | "runtimePolicies"
  | "evidenceCapture"
  | "archivePath"
>) {
  return sha256Hex({
    id: plan.id,
    title: plan.title,
    intent: plan.intent,
    revision: plan.revision,
    createdAt: plan.createdAt,
    pillars: plan.pillars,
    committeeIds: plan.committeeIds,
    workerIds: plan.workerIds,
    skillIds: plan.skillIds,
    route: plan.route,
    requiredOutputs: plan.requiredOutputs,
    approvalPath: plan.approvalPath,
    runtimePolicies: plan.runtimePolicies,
    evidenceCapture: plan.evidenceCapture,
    archivePath: plan.archivePath,
  });
}

function normalizeV3Plan(candidate: V3Plan): V3Plan {
  const revision = Number.isFinite(candidate.revision) && candidate.revision > 0 ? candidate.revision : 1;
  const normalized: V3Plan = {
    ...candidate,
    revision,
    frozenAt: candidate.frozenAt || candidate.createdAt || candidate.updatedAt || now(),
    revisionHash: candidate.revisionHash || "",
  };
  normalized.revisionHash = computeV3PlanRevisionHash(normalized);
  return normalized;
}

function normalizeV3Run(candidate: V3Run, plan?: V3Plan): V3Run {
  const normalized: V3Run = {
    ...candidate,
    planRevision: Number.isFinite(candidate.planRevision) && candidate.planRevision > 0 ? candidate.planRevision : (plan?.revision ?? 0),
    planRevisionHash: candidate.planRevisionHash || plan?.revisionHash || "",
    integrityStatus: candidate.integrityStatus || "ok",
  };
  if ((normalized.status === "completed" || normalized.status === "failed") && !normalized.archiveRecordId) {
    normalized.integrityStatus = "integrity_failed";
  }
  return normalized;
}

function buildV3EventHashInput(event: Omit<V3Event, "eventHash">) {
  return {
    prevEventHash: event.prevEventHash,
    runId: event.runId,
    planId: event.planId,
    planRevision: event.planRevision,
    seq: event.seq,
    type: event.type,
    at: event.at,
    actorType: event.actorType,
    actorId: event.actorId,
    committeeId: event.committeeId,
    workerId: event.workerId,
    skillId: event.skillId,
    surface: event.surface,
    pillarIds: event.pillarIds,
    message: event.message,
    payload: event.payload,
    policyRefs: event.policyRefs,
    evidenceRefs: event.evidenceRefs,
    replayable: event.replayable,
    schemaVersion: event.schemaVersion,
    hashAlgorithm: event.hashAlgorithm,
  };
}

function computeV3EventHash(event: Omit<V3Event, "eventHash">) {
  return sha256Hex(buildV3EventHashInput(event));
}

function validateReplayRequestRecord(request: ReplayRequest) {
  if (!request.id || !request.runId || !request.requestedBy || !request.requestedAt || !request.reason) {
    throw new Error("ReplayRequest is missing required fields.");
  }
}

function validateReplayResultRecord(result: ReplayResult) {
  if (!result.id || !result.sourceRunId || !result.mode || !result.status || !result.summary) {
    throw new Error("ReplayResult is missing required fields.");
  }
}

function validateArchiveRecordRecord(archive: ArchiveRecord) {
  if (!archive.id || !archive.runId || !archive.planId || !archive.planRevision || !archive.archivePath) {
    throw new Error("ArchiveRecord is missing required identifiers.");
  }
  if (!archive.bundleHash || !archive.signer || !archive.signedAt) {
    throw new Error("ArchiveRecord integrity fields are missing.");
  }
}

function validateV3EventRecord(event: V3Event) {
  if (!event.id || !event.runId || !event.planId || !event.planRevision) {
    throw new Error("V3Event is missing required identifiers.");
  }
  if (event.actorType === "worker" && (!event.workerId || !event.committeeId)) {
    throw new Error("Worker events require workerId and committeeId.");
  }
  if (!event.eventHash || !event.hashAlgorithm || !event.schemaVersion) {
    throw new Error("V3Event integrity fields are missing.");
  }
}

function buildArchiveBundleHashPayload(archive: Omit<ArchiveRecord, "bundleHash">) {
  return {
    id: archive.id,
    runId: archive.runId,
    planId: archive.planId,
    planRevision: archive.planRevision,
    archivePath: archive.archivePath,
    type: archive.type,
    summary: archive.summary,
    decisionStatus: archive.decisionStatus,
    eventIds: archive.eventIds,
    sourceEventRange: archive.sourceEventRange,
    lineage: archive.lineage,
    metadata: archive.metadata,
    artifact: archive.artifact,
    replayable: archive.replayable,
  };
}

function computeArchiveBundleHash(archive: Omit<ArchiveRecord, "bundleHash">) {
  return sha256Hex(buildArchiveBundleHashPayload(archive));
}

function buildEventChainIntegrity(runId: string) {
  const run = state.v3Runs.find((entry) => entry.id === runId);
  const events = state.v3Events
    .filter((event) => event.runId === runId)
    .sort((left, right) => left.seq - right.seq);

  if (!run) {
    return {
      chainValid: false,
      checkedEventCount: events.length,
      firstBrokenSeq: undefined as number | undefined,
      reason: "Run not found.",
    };
  }

  let expectedSeq = 1;
  let previousHash: string | undefined;

  for (const event of events) {
    if (event.seq !== expectedSeq) {
      return {
        chainValid: false,
        checkedEventCount: events.length,
        firstBrokenSeq: event.seq,
        reason: `Expected seq ${expectedSeq} but found ${event.seq}.`,
      };
    }
    if (event.planRevision !== run.planRevision) {
      return {
        chainValid: false,
        checkedEventCount: events.length,
        firstBrokenSeq: event.seq,
        reason: `Event plan revision ${event.planRevision} does not match run plan revision ${run.planRevision}.`,
      };
    }
    if (event.prevEventHash !== previousHash) {
      return {
        chainValid: false,
        checkedEventCount: events.length,
        firstBrokenSeq: event.seq,
        reason: `prevEventHash mismatch at seq ${event.seq}.`,
      };
    }
    const { eventHash: _eventHash, ...eventForHash } = event;
    const expectedHash = computeV3EventHash(eventForHash);
    if (event.eventHash !== expectedHash) {
      return {
        chainValid: false,
        checkedEventCount: events.length,
        firstBrokenSeq: event.seq,
        reason: `eventHash mismatch at seq ${event.seq}.`,
      };
    }
    previousHash = event.eventHash;
    expectedSeq += 1;
  }

  return {
    chainValid: true,
    checkedEventCount: events.length,
    firstBrokenSeq: undefined as number | undefined,
    reason: undefined as string | undefined,
  };
}

function buildArchiveIntegrity(run: V3Run, archive: ArchiveRecord | undefined) {
  if ((run.status === "completed" || run.status === "failed") && !archive) {
    return {
      valid: false,
      reason: "Governed run finalized without an archive bundle.",
    };
  }
  if (!archive) {
    return {
      valid: true,
      reason: "No archive required for this run state.",
    };
  }
  const { bundleHash: _bundleHash, ...archiveForHash } = archive;
  const expectedHash = computeArchiveBundleHash(archiveForHash);
  if (archive.bundleHash !== expectedHash) {
    return {
      valid: false,
      reason: "Archive bundle hash mismatch.",
    };
  }
  if (archive.sourceEventRange) {
    const archivedEvents = state.v3Events
      .filter((event) => archive.eventIds.includes(event.id))
      .sort((left, right) => left.seq - right.seq);
    const minSeq = archivedEvents.length > 0 ? archivedEvents[0].seq : undefined;
    const maxSeq = archivedEvents.length > 0 ? archivedEvents[archivedEvents.length - 1].seq : undefined;
    if (minSeq !== archive.sourceEventRange.startSeq || maxSeq !== archive.sourceEventRange.endSeq) {
      return {
        valid: false,
        reason: "Archive source event range does not match current event lineage.",
      };
    }
  }
  return {
    valid: true,
    reason: "Archive bundle hash and event range verified.",
  };
}

function buildReplayIntegrity(run: V3Run, replayResults: ReplayResult[], replayArchives: ArchiveRecord[]) {
  if (replayResults.length === 0) {
    return {
      valid: true,
      sourceUnchanged: true,
      reason: "No replay created for this run.",
    };
  }
  const mismatchedResult = replayResults.find((result) => result.sourceRunId !== run.id || !result.replayArchiveId);
  if (mismatchedResult) {
    return {
      valid: false,
      sourceUnchanged: false,
      reason: "Replay result is missing sourceRunId or replayArchiveId linkage.",
    };
  }
  const nonReplayArchive = replayArchives.find((archive) => archive.type !== "replay_bundle" || archive.runId !== run.id);
  if (nonReplayArchive) {
    return {
      valid: false,
      sourceUnchanged: false,
      reason: "Replay archive integrity failed.",
    };
  }
  return {
    valid: true,
    sourceUnchanged: true,
    reason: "Replay records remain separate and preserve the source run/archive.",
  };
}

function normalizeV3AuditState() {
  state.v3Plans = state.v3Plans.map((plan) => normalizeV3Plan(plan));
  state.v3Runs = state.v3Runs.map((run) => normalizeV3Run(run, state.v3Plans.find((plan) => plan.id === run.planId)));

  const normalizedEvents: V3Event[] = [];
  for (const run of state.v3Runs) {
    const runEvents = state.v3Events
      .filter((event) => event.runId === run.id)
      .sort((left, right) => left.seq - right.seq || Date.parse(left.at || run.submittedAt) - Date.parse(right.at || run.submittedAt));
    let previousHash: string | undefined;
    let seq = 1;
    for (const rawEvent of runEvents) {
      const actorType = rawEvent.actorType
        || (rawEvent.workerId ? "worker" : rawEvent.skillId ? "skill" : rawEvent.committeeId ? "committee" : "system");
      const actorId = rawEvent.actorId
        || rawEvent.workerId
        || rawEvent.skillId
        || rawEvent.committeeId
        || "uacp-v3";
      const normalizedEventBase: Omit<V3Event, "eventHash"> = {
        ...rawEvent,
        at: rawEvent.at || run.submittedAt || now(),
        planRevision: Number.isFinite(rawEvent.planRevision) && rawEvent.planRevision > 0 ? rawEvent.planRevision : run.planRevision,
        seq,
        actorType,
        actorId,
        replayable: typeof rawEvent.replayable === "boolean" ? rawEvent.replayable : true,
        hashAlgorithm: rawEvent.hashAlgorithm || V3_EVENT_HASH_ALGORITHM,
        schemaVersion: rawEvent.schemaVersion || V3_EVENT_SCHEMA_VERSION,
        prevEventHash: previousHash,
      };
      const normalizedEvent: V3Event = {
        ...normalizedEventBase,
        eventHash: computeV3EventHash(normalizedEventBase),
      };
      validateV3EventRecord(normalizedEvent);
      normalizedEvents.push(normalizedEvent);
      previousHash = normalizedEvent.eventHash;
      seq += 1;
    }
  }
  state.v3Events = normalizedEvents;

  state.v3Archives = state.v3Archives.map((archive) => {
    const run = state.v3Runs.find((entry) => entry.id === archive.runId);
    const plan = state.v3Plans.find((entry) => entry.id === archive.planId);
    const runEvents = state.v3Events.filter((event) => event.runId === archive.runId).sort((left, right) => left.seq - right.seq);
    const sourceEventRange = archive.sourceEventRange || (runEvents.length > 0
      ? { startSeq: runEvents[0].seq, endSeq: runEvents[runEvents.length - 1].seq }
      : undefined);
    const normalizedArchiveBase: Omit<ArchiveRecord, "bundleHash"> = {
      ...archive,
      planRevision: Number.isFinite(archive.planRevision) && archive.planRevision > 0
        ? archive.planRevision
        : (run?.planRevision || plan?.revision || 0),
      hashAlgorithm: archive.hashAlgorithm || V3_ARCHIVE_HASH_ALGORITHM,
      signer: archive.signer || archive.createdBy || "UACP V3",
      signedAt: archive.signedAt || archive.createdAt || now(),
      sourceEventRange,
      lineage: archive.lineage || {
        sourceRunId: archive.runId,
        sourcePlanId: archive.planId,
      },
      metadata: archive.metadata || {},
    };
    const normalizedArchive: ArchiveRecord = {
      ...normalizedArchiveBase,
      bundleHash: computeArchiveBundleHash(normalizedArchiveBase),
    };
    validateArchiveRecordRecord(normalizedArchive);
    return normalizedArchive;
  });

  state.v3ReplayRequests.forEach(validateReplayRequestRecord);
  state.v3ReplayResults = state.v3ReplayResults.map((result) => {
    const normalizedResult: ReplayResult = {
      ...result,
      replayArchiveId: result.replayArchiveId || result.archiveRecordId,
      sourceUnchanged: typeof result.sourceUnchanged === "boolean" ? result.sourceUnchanged : true,
      eventChainIntegrity: result.eventChainIntegrity || buildEventChainIntegrity(result.sourceRunId),
    };
    validateReplayResultRecord(normalizedResult);
    return normalizedResult;
  });
}

const veklomPillarIdSet = new Set<VeklomPillarId>(veklomPillars.map((pillar) => pillar.id));
const committeeAuthoritySet = new Set<CommitteeAuthorityLevel>(["advisory", "operational", "approval", "veto", "constitutional"]);
const workerArchetypeSet = new Set<WorkerArchetype>(["arbiter", "sheriff", "gauge", "switchman", "curator", "builder", "scout", "steward", "treasurer"]);

function getV3Pillar(pillarId: string) {
  return veklomPillars.find((pillar) => pillar.id === pillarId);
}

function getV3Committee(committeeId: string) {
  return veklomCommittees.find((committee) => committee.id === committeeId);
}

function getV3Worker(workerId: string) {
  return veklomWorkers.find((worker) => worker.id === workerId);
}

function getV3Skill(skillId: string) {
  return veklomSkills.find((skill) => skill.id === skillId);
}

function ensureV3PillarId(value: unknown, label: string) {
  const pillarId = ensureString(value, label) as VeklomPillarId;
  if (!veklomPillarIdSet.has(pillarId)) {
    throw new Error(`${label} must resolve to one of the Veklom 9 pillars.`);
  }
  return pillarId;
}

function ensureV3PillarIdArray(value: unknown, label: string) {
  return ensureStringArray(value, label).map((entry, index) => ensureV3PillarId(entry, `${label}[${index}]`));
}

function ensureCommitteeAuthority(value: unknown, label: string) {
  const authority = ensureString(value, label) as CommitteeAuthorityLevel;
  if (!committeeAuthoritySet.has(authority)) {
    throw new Error(`${label} must be a valid committee authority level.`);
  }
  return authority;
}

function ensureWorkerArchetype(value: unknown, label: string) {
  const archetype = ensureString(value, label) as WorkerArchetype;
  if (!workerArchetypeSet.has(archetype)) {
    throw new Error(`${label} must be a valid worker archetype.`);
  }
  return archetype;
}

function validateSkillBinding(skill: SkillBinding) {
  if (!getV3Committee(skill.governingCommitteeId)) {
    throw new Error(`Skill ${skill.id} must resolve to a governing committee.`);
  }
  skill.pillarIds.forEach((pillarId) => ensureV3PillarId(pillarId, `skill ${skill.id} pillarId`));
  if (skill.pinned && (!skill.sourceRepo || !skill.sourceRef || !skill.sourceTreeSha)) {
    throw new Error(`Pinned skill ${skill.id} requires sourceRepo, sourceRef, and sourceTreeSha.`);
  }
}

function validateWorkerRegistryEntry(worker: WorkerRegistryEntry) {
  ensureWorkerArchetype(worker.archetype, `worker ${worker.id}.archetype`);
  ensureV3PillarId(worker.pillarId, `worker ${worker.id}.pillarId`);
  ensureCommitteeAuthority(worker.authorityLevel, `worker ${worker.id}.authorityLevel`);
  if (!worker.requiredOutput || !worker.reviewer || !worker.archivePath) {
    throw new Error(`Worker ${worker.id} must define required output, reviewer, and archive path.`);
  }
  if (!getV3Committee(worker.committeeId)) {
    throw new Error(`Worker ${worker.id} committeeId must resolve to a real committee.`);
  }
  worker.allowedSkillIds.forEach((skillId) => {
    const skill = getV3Skill(skillId);
    if (!skill) {
      throw new Error(`Worker ${worker.id} references unknown skill ${skillId}.`);
    }
  });
}

function getLatestPlanForWorker(workerId: string) {
  const plans = state.v3Plans
    .filter((plan) => plan.workerIds.includes(workerId))
    .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));
  return plans[0];
}

function getLatestRunForWorker(workerId: string) {
  const runs = state.v3Runs
    .filter((run) => run.workerIds.includes(workerId))
    .sort((left, right) => {
      const leftTime = Date.parse(left.completedAt ?? left.startedAt ?? left.submittedAt);
      const rightTime = Date.parse(right.completedAt ?? right.startedAt ?? right.submittedAt);
      return rightTime - leftTime;
    });
  return runs[0];
}

function mapRunToWorkerLastResult(run?: V3Run): WorkerLastRunResult {
  if (!run) {
    return "none";
  }
  if (run.status === "blocked" || run.decisionStatus === "blocked") {
    return "blocked";
  }
  if (run.status === "failed") {
    return "failure";
  }
  if (run.status === "completed" && run.decisionStatus === "approved") {
    return "success";
  }
  if (run.status === "completed" || run.decisionStatus === "needs_founder_review") {
    return "partial_success";
  }
  return "none";
}

function buildWorkerRegistryValidation(worker: WorkerRegistryEntry, plan?: V3Plan): WorkerRegistryValidation {
  const resolved = {
    pillar: Boolean(worker.pillarId && getV3Pillar(worker.pillarId)),
    committee: Boolean(worker.committeeId && getV3Committee(worker.committeeId)),
    plan: Boolean(plan),
    archive_path: Boolean(worker.archivePath),
    reviewer: Boolean(worker.reviewer),
    required_output: Boolean(worker.requiredOutput),
    authority_level: Boolean(worker.authorityLevel),
  };
  const missing_fields = Object.entries(resolved)
    .filter(([, value]) => !value)
    .map(([key]) => key);
  return {
    worker_id: worker.id,
    valid: missing_fields.length === 0,
    current_status: missing_fields.length === 0 ? "ready" : "blocked_invalid_registry",
    missing_fields,
    resolved,
  };
}

function mapWorkerRegistryStatus(
  worker: WorkerRegistryEntry,
  validation: WorkerRegistryValidation,
  run?: V3Run,
): WorkerRegistryStatus {
  if (!validation.valid) {
    return "blocked_invalid_registry";
  }
  if (run?.status === "executing" || run?.status === "queued" || run?.status === "approved") {
    return "active";
  }
  if (run?.decisionStatus === "needs_founder_review") {
    return "review";
  }
  if (worker.status === "paused") {
    return "paused";
  }
  if (worker.status === "blocked") {
    return "blocked";
  }
  return "ready";
}

function buildWorkerRegistryRecord(worker: WorkerRegistryEntry): WorkerRegistryRecord {
  const pillar = getV3Pillar(worker.pillarId);
  const committee = getV3Committee(worker.committeeId);
  const plan = getLatestPlanForWorker(worker.id);
  const run = getLatestRunForWorker(worker.id);
  const validation = buildWorkerRegistryValidation(worker, plan);

  return {
    worker_id: worker.id,
    worker_name: worker.name,
    pillar_id: worker.pillarId,
    pillar_name: pillar?.name ?? "Unknown pillar",
    committee_id: worker.committeeId,
    committee_name: committee?.name ?? "Unknown committee",
    job: worker.currentJob,
    authority_level: worker.authorityLevel,
    allowed_skills: worker.allowedSkillIds.map((skillId) => getV3Skill(skillId)?.name ?? skillId),
    forbidden_actions: worker.forbiddenActions,
    keys_envs_required: worker.requiredEnvKeys,
    current_status: mapWorkerRegistryStatus(worker, validation, run),
    required_output: worker.requiredOutput,
    reviewer: worker.reviewer,
    promotion_metric: worker.promotionMetric,
    demotion_trigger: worker.demotionTrigger,
    archive_path: worker.archivePath,
    plan_id: plan?.id ?? "",
    last_run_id: run?.id,
    last_run_result: mapRunToWorkerLastResult(run),
    last_run_summary: run?.summary ?? (typeof run?.artifact?.artifactSummary === "string" ? run.artifact.artifactSummary : undefined),
    last_run_at: run?.completedAt ?? run?.startedAt ?? run?.submittedAt,
  };
}

function buildPlanRegistryProof(planId: string): PlanRegistryProof | undefined {
  const plan = state.v3Plans.find((entry) => entry.id === planId);
  if (!plan) {
    return undefined;
  }

  const run = state.v3Runs
    .filter((entry) => entry.planId === planId)
    .sort((left, right) => {
      const leftTime = Date.parse(left.completedAt ?? left.startedAt ?? left.submittedAt);
      const rightTime = Date.parse(right.completedAt ?? right.startedAt ?? right.submittedAt);
      return rightTime - leftTime;
    })[0];

  const workerRecords = plan.workerIds
    .map((workerId) => getV3Worker(workerId))
    .filter((worker): worker is WorkerRegistryEntry => Boolean(worker))
    .map((worker) => buildWorkerRegistryRecord(worker));

  const validations = plan.workerIds.map((workerId) => {
    const worker = getV3Worker(workerId);
    if (!worker) {
      return {
        worker_id: workerId,
        valid: false,
        current_status: "blocked_invalid_registry" as const,
        missing_fields: ["worker_registry_record"],
        resolved: {
          pillar: false,
          committee: false,
          plan: true,
          archive_path: false,
          reviewer: false,
          required_output: false,
          authority_level: false,
        },
      };
    }
    return buildWorkerRegistryValidation(worker, plan);
  });

  return {
    plan_id: plan.id,
    run_id: run?.id,
    archive_record_id: run?.archiveRecordId,
    valid: validations.every((validation) => validation.valid),
    worker_records: workerRecords,
    validations,
    issues: validations.flatMap((validation) =>
      validation.missing_fields.map((field) => `${validation.worker_id}: missing ${field}`),
    ),
  };
}

function buildRoutedIntentResult(plan: V3Plan, run: V3Run): RoutedIntentResult {
  const artifact = (run.artifact || {}) as Record<string, unknown>;
  const route: RegistryRouteStage[] = ["Research", "Product", "Governance", "Marketplace/Growth", "Finance", "Archive"];
  const stageWorkerMap: Record<RegistryRouteStage, string> = {
    Research: "scout-revenue",
    Product: "builder-package",
    Governance: "arbiter-policy",
    "Marketplace/Growth": "steward-tenant",
    Finance: "treasurer-reserve",
    Archive: "steward-archive",
  };
  const stageOutputMap: Record<RegistryRouteStage, string> = {
    Research: `Opportunity brief: ${String(artifact.opportunitySummary || artifact.competitorWeakness || "Opportunity signal captured.")}`,
    Product: `Package spec: ${String(artifact.proposedPackageTool || "Governed package specification prepared.")}`,
    Governance: `Approved with policy review: ${String(artifact.policyRiskReview || "Policy-safe route enforced.")}`,
    "Marketplace/Growth": `Marketplace listing draft: ${String(artifact.nextAction || "Buyer-facing rollout prepared.")}`,
    Finance: `Pricing memo: ${String(artifact.pricingHypothesis || "Reserve-backed pricing attached.")}`,
    Archive: `Signed archive bundle written: ${run.archiveRecordId || "archive pending"}`,
  };

  const steps = route.map((stage) => {
    const worker = getV3Worker(stageWorkerMap[stage]);
    if (!worker) {
      return {
        stage,
        worker_name: stageWorkerMap[stage],
        status: "blocked" as const,
        reason: "No valid worker is registered for this route stage.",
      };
    }

    const validation = buildWorkerRegistryValidation(worker, plan);
    if (!validation.valid) {
      return {
        stage,
        worker_name: worker.name,
        status: "blocked" as const,
        reviewer: worker.reviewer,
        archive_path: worker.archivePath,
        reason: validation.missing_fields.join("; "),
      };
    }

    return {
      stage,
      worker_name: worker.name,
      status: "completed" as const,
      output: stageOutputMap[stage],
      reviewer: worker.reviewer,
      archive_path: worker.archivePath,
    };
  });

  const blockedStep = steps.find((step) => step.status === "blocked");

  return {
    intent: plan.intent,
    route,
    status: blockedStep ? "blocked" : "completed",
    blocked_reason: blockedStep?.reason,
    plan_id: plan.id,
    steps,
  };
}

function validateV3ReferenceData() {
  veklomSkills.forEach(validateSkillBinding);
  veklomWorkers.forEach(validateWorkerRegistryEntry);
}

function nextV3EventSeq(runId: string) {
  return state.v3Events
    .filter((event) => event.runId === runId)
    .reduce((maxSeq, event) => Math.max(maxSeq, event.seq), 0) + 1;
}

function appendV3Event(
  input: Omit<V3Event, "id" | "at" | "seq" | "planRevision" | "actorType" | "actorId" | "prevEventHash" | "eventHash" | "hashAlgorithm" | "schemaVersion" | "replayable">
    & Partial<Pick<V3Event, "actorType" | "actorId" | "surface" | "policyRefs" | "evidenceRefs" | "replayable">>,
) {
  const run = state.v3Runs.find((entry) => entry.id === input.runId);
  if (!run) {
    throw new Error(`Cannot append event for unknown run ${input.runId}.`);
  }
  if (!run.planRevision || !run.planRevisionHash) {
    throw new Error(`Run ${run.id} is missing a frozen plan revision.`);
  }
  if (input.planId !== run.planId) {
    throw new Error(`Event planId ${input.planId} does not match run planId ${run.planId}.`);
  }
  if (input.workerId && !input.committeeId) {
    throw new Error("Every worker event must include workerId and committeeId.");
  }
  if (input.workerId) {
    const worker = getV3Worker(input.workerId);
    if (!worker) {
      throw new Error(`Worker event references unknown worker ${input.workerId}.`);
    }
  }
  if (input.committeeId && !getV3Committee(input.committeeId)) {
    throw new Error(`Worker event references unknown committee ${input.committeeId}.`);
  }
  const actorType = input.actorType
    || (input.workerId ? "worker" : input.skillId ? "skill" : input.committeeId ? "committee" : "system");
  const actorId = input.actorId
    || input.workerId
    || input.skillId
    || input.committeeId
    || "uacp-v3";
  const priorEvents = state.v3Events
    .filter((event) => event.runId === input.runId)
    .sort((left, right) => left.seq - right.seq);
  const prevEventHash = priorEvents.length > 0 ? priorEvents[priorEvents.length - 1].eventHash : undefined;
  const eventBase: Omit<V3Event, "eventHash"> = {
    id: createId("v3evt"),
    seq: nextV3EventSeq(input.runId),
    at: now(),
    planRevision: run.planRevision,
    actorType,
    actorId,
    prevEventHash,
    hashAlgorithm: V3_EVENT_HASH_ALGORITHM,
    schemaVersion: V3_EVENT_SCHEMA_VERSION,
    replayable: typeof input.replayable === "boolean" ? input.replayable : true,
    ...input,
  };
  const event: V3Event = {
    ...eventBase,
    eventHash: computeV3EventHash(eventBase),
  };
  validateV3EventRecord(event);
  state.v3Events = [...state.v3Events, event];
  return event;
}

function writeV3ArchiveRecord(run: V3Run, artifact: Record<string, unknown>, createdBy = "UACP V3") {
  const plan = state.v3Plans.find((entry) => entry.id === run.planId);
  if (!plan) {
    throw new Error(`Cannot archive unknown V3 plan ${run.planId}.`);
  }
  const runEvents = state.v3Events.filter((event) => event.runId === run.id).sort((left, right) => left.seq - right.seq);
  const eventIds = runEvents.map((event) => event.id);
  const archiveBase: Omit<ArchiveRecord, "bundleHash"> = {
    id: createId("v3arc"),
    runId: run.id,
    planId: plan.id,
    planRevision: run.planRevision,
    archivePath: plan.archivePath,
    type: "run_bundle",
    summary: `Replayable archive bundle for ${plan.title}`,
    createdAt: now(),
    createdBy,
    decisionStatus: (run.decisionStatus || "blocked"),
    artifact,
    eventIds,
    hashAlgorithm: V3_ARCHIVE_HASH_ALGORITHM,
    signer: createdBy,
    signedAt: now(),
    sourceEventRange: runEvents.length > 0 ? { startSeq: runEvents[0].seq, endSeq: runEvents[runEvents.length - 1].seq } : undefined,
    lineage: {
      sourceRunId: run.id,
      sourcePlanId: plan.id,
      sourcePlanRevision: run.planRevision,
    },
    metadata: {
      planRevisionHash: run.planRevisionHash,
      runStatus: run.status,
    },
    replayable: true,
  };
  const archive: ArchiveRecord = {
    ...archiveBase,
    bundleHash: computeArchiveBundleHash(archiveBase),
  };
  validateArchiveRecordRecord(archive);
  state.v3Archives = [archive, ...state.v3Archives].slice(0, MAX_ARCHIVES);
  run.archiveRecordId = archive.id;
  run.integrityStatus = "ok";
  appendV3Event({
    runId: run.id,
    planId: run.planId,
    type: "archive_written",
    committeeId: "archives-board",
    workerId: "steward-archive",
    skillId: "skill-archive-bundler",
    actorType: "archive_service",
    actorId: "archive_service",
    surface: "archives",
    pillarIds: ["evidence-audit-archives"],
    message: `Archive record ${archive.id} written for ${run.id}.`,
    payload: { archiveRecordId: archive.id, bundleHash: archive.bundleHash },
    evidenceRefs: [archive.id],
  });
  return archive;
}

function writeV3ReplayArchiveRecord(sourceRun: V3Run, replayRequest: ReplayRequest, replayResultId: string) {
  const plan = state.v3Plans.find((entry) => entry.id === sourceRun.planId);
  if (!plan) {
    throw new Error(`Cannot archive replay for unknown V3 plan ${sourceRun.planId}.`);
  }
  const sourceArchive = sourceRun.archiveRecordId
    ? state.v3Archives.find((entry) => entry.id === sourceRun.archiveRecordId)
    : undefined;
  const replayArtifact = {
    sourceRunId: sourceRun.id,
    sourceArchiveRecordId: sourceRun.archiveRecordId || null,
    replayMode: replayRequest.mode,
    replayReason: replayRequest.reason,
    preservedDecisionStatus: sourceRun.decisionStatus || "blocked",
    preservedArtifactSummary: sourceRun.artifact?.artifactSummary || sourceRun.summary || "No source artifact summary available.",
    sourceEventCount: state.v3Events.filter((event) => event.runId === sourceRun.id).length,
    replayGuarantees: [
      "source run not overwritten",
      "source archive unchanged",
      "ordered event lineage preserved",
    ],
  };
  const runEvents = state.v3Events.filter((event) => event.runId === sourceRun.id).sort((left, right) => left.seq - right.seq);
  const archiveBase: Omit<ArchiveRecord, "bundleHash"> = {
    id: createId("v3arc"),
    runId: sourceRun.id,
    planId: plan.id,
    planRevision: sourceRun.planRevision,
    archivePath: `${plan.archivePath}/replay`,
    type: "replay_bundle",
    summary: `Replay bundle for ${sourceRun.id}`,
    createdAt: now(),
    createdBy: replayRequest.requestedBy,
    decisionStatus: sourceRun.decisionStatus || "blocked",
    artifact: replayArtifact,
    eventIds: runEvents.map((event) => event.id),
    hashAlgorithm: V3_ARCHIVE_HASH_ALGORITHM,
    signer: replayRequest.requestedBy,
    signedAt: now(),
    sourceEventRange: runEvents.length > 0 ? { startSeq: runEvents[0].seq, endSeq: runEvents[runEvents.length - 1].seq } : undefined,
    lineage: {
      sourceRunId: sourceRun.id,
      sourceArchiveRecordId: sourceRun.archiveRecordId || null,
      replayRequestId: replayRequest.id,
      replayResultId,
    },
    metadata: {
      replayMode: replayRequest.mode,
      replayReason: replayRequest.reason,
      preservedSourceArchiveRecordId: sourceArchive?.id || null,
    },
    replayable: true,
  };
  const archive: ArchiveRecord = {
    ...archiveBase,
    bundleHash: computeArchiveBundleHash(archiveBase),
  };
  validateArchiveRecordRecord(archive);
  state.v3Archives = [archive, ...state.v3Archives].slice(0, MAX_ARCHIVES);
  return archive;
}

function validateV3Plan(plan: V3Plan) {
  if (plan.pillars.length === 0 || plan.committeeIds.length === 0 || plan.workerIds.length === 0 || plan.skillIds.length === 0) {
    throw new Error("Plan must define pillars, committees, workers, and skills.");
  }
  if (!plan.revision || !plan.revisionHash || !plan.frozenAt) {
    throw new Error("Plan must carry a frozen revision, revision hash, and frozenAt timestamp.");
  }
  if (!plan.requiredOutputs.length) {
    throw new Error("Plan must define required outputs.");
  }
  if (!plan.archivePath) {
    throw new Error("Plan must define an archive path.");
  }
  plan.pillars.forEach((pillarId) => ensureV3PillarId(pillarId, `plan ${plan.id}.pillars`));
  plan.route.forEach((pillarId) => ensureV3PillarId(pillarId, `plan ${plan.id}.route`));
  plan.committeeIds.forEach((committeeId) => {
    if (!getV3Committee(committeeId)) {
      throw new Error(`Plan ${plan.id} references unknown committee ${committeeId}.`);
    }
  });
  plan.workerIds.forEach((workerId) => {
    const worker = getV3Worker(workerId);
    if (!worker) {
      throw new Error(`Plan ${plan.id} references unknown worker ${workerId}.`);
    }
    validateWorkerRegistryEntry(worker);
  });
  plan.skillIds.forEach((skillId) => {
    const skill = getV3Skill(skillId);
    if (!skill) {
      throw new Error(`Plan ${plan.id} references unknown skill ${skillId}.`);
    }
    validateSkillBinding(skill);
  });
}

function validateGovernedLiveRun(plan: V3Plan) {
  if (plan.runtimePolicies.length === 0 || plan.approvalPath.length === 0 || plan.evidenceCapture.length === 0) {
    throw new Error("governed_live runs require runtime policies, approval path, and evidence capture.");
  }
  if (!plan.revision || !plan.revisionHash || !plan.frozenAt) {
    throw new Error("Every governed run must reference a frozen plan revision.");
  }
}

function buildV3ValidationChecks(plan: V3Plan, run?: V3Run) {
  const checks = [
    {
      id: "pillars",
      label: "All plan pillars resolve to the Veklom 9 pillars",
      passed: plan.pillars.every((pillarId) => Boolean(getV3Pillar(pillarId))),
      reason: "Every route step and worker pillar must resolve to a locked Veklom pillar.",
    },
    {
      id: "committees",
      label: "All committee references resolve",
      passed: plan.committeeIds.every((committeeId) => Boolean(getV3Committee(committeeId))),
      reason: "No plan or worker can execute with a missing committee.",
    },
    {
      id: "workers",
      label: "All workers have governance-required fields",
      passed: plan.workerIds.every((workerId) => {
        const worker = getV3Worker(workerId);
        return Boolean(worker?.requiredOutput && worker?.reviewer && worker?.archivePath && worker?.allowedSkillIds.length);
      }),
      reason: "Workers require pillar, committee, allowlisted skills, output, reviewer, and archive path.",
    },
    {
      id: "skills",
      label: "All skills resolve to a governing committee",
      passed: plan.skillIds.every((skillId) => Boolean(getV3Skill(skillId)?.governingCommitteeId && getV3Committee(getV3Skill(skillId)!.governingCommitteeId))),
      reason: "Every skill must be owned by a real committee.",
    },
    {
      id: "pinned-skills",
      label: "Pinned skills include provenance",
      passed: plan.skillIds.every((skillId) => {
        const skill = getV3Skill(skillId);
        return !skill?.pinned || Boolean(skill.sourceRepo && skill.sourceRef && skill.sourceTreeSha);
      }),
      reason: "Pinned skills require sourceRepo, sourceRef, and sourceTreeSha.",
    },
    {
      id: "governed-live",
      label: "Governed live execution has runtime policies, approval path, and evidence capture",
      passed: plan.runtimePolicies.length > 0 && plan.approvalPath.length > 0 && plan.evidenceCapture.length > 0,
      reason: "governed_live runs require policy, approval, and evidence capture before execution.",
    },
    {
      id: "archive",
      label: "Archive path is declared",
      passed: Boolean(plan.archivePath),
      reason: "Every governed run must terminate in an archive path.",
    },
  ];

  if (run) {
    const orderedEvents = state.v3Events.filter((event) => event.runId === run.id).sort((left, right) => left.seq - right.seq);
    checks.push({
      id: "ordered-events",
      label: "Run events are append-only and ordered by seq",
      passed: orderedEvents.every((event, index) => event.seq === index + 1),
      reason: "Every V3 event must preserve ordered replay semantics.",
    });
    checks.push({
      id: "archive-record",
      label: "Completed or failed governed run wrote an archive record",
      passed: run.status !== "completed" && run.status !== "failed" ? false : Boolean(run.archiveRecordId),
      reason: "Every completed or failed governed run must emit an ArchiveRecord.",
    });
  }

  return checks;
}

function deriveRevenueIntentDecision(intent: string) {
  const normalized = intent.toLowerCase();
  if (normalized.includes("regulated-industry buyer pain")) {
    return {
      decisionStatus: "needs_founder_review" as const,
      decisionReason: "The opportunity is commercially promising, but the buyer segment is regulated and requires founder-level positioning approval before packaging claims are promoted.",
      opportunitySummary: "Governed buyer-pain diagnostic for regulated operators who need proof-safe AI admission, archive lineage, and reserve visibility.",
      competitorWeakness: "Competing vendors talk about compliance posture, but they do not expose replayable proof chains or cost-attached evidence bundles.",
      buyerPain: "Regulated teams cannot safely evaluate AI workflows because they lack defensible logs, approval traces, and scoped runtime controls.",
      proposedPackageTool: "Veklom Regulated Workflow Proof Diagnostic with governed runtime review, archive package, and buyer-readiness memo.",
      pricingHypothesis: { model: "operating_reserve", diagnosticUsd: 3500, reserveKickoffUsd: 1200, evidenceBundleUsd: 950 },
      nextAction: "Founder review the regulated-segment claim set, then approve the first buyer-facing diagnostic package.",
    };
  }
  if (normalized.includes("competitor weakness")) {
    return {
      decisionStatus: "approved" as const,
      decisionReason: "The opportunity can be exploited safely because the package is framed around evidence-backed governance gaps instead of unsupported feature claims.",
      opportunitySummary: "Competitive takedown package for teams burned by weak AI gateway proof, built around safe evidence-first differentiation.",
      competitorWeakness: "Competitors expose weak audit lineage, loose model/tool governance, and generic subscription pricing disconnected from actual governed execution.",
      buyerPain: "Buyers cannot tell whether a competitor’s platform can prove what happened during a sensitive AI workflow.",
      proposedPackageTool: "Veklom Competitor Weakness Conversion Kit with governed package brief, reserve pricing, and archive-backed proof narrative.",
      pricingHypothesis: { model: "operating_reserve", kickoffUsd: 4000, governedEvaluationUsd: 1500, archiveBundleUsd: 850 },
      nextAction: "Ship the competitor-proof positioning bundle into a founder-approved outreach and demo sequence.",
    };
  }
  if (normalized.includes("sellable marketplace opportunity")) {
    return {
      decisionStatus: "approved" as const,
      decisionReason: "The opportunity is monetizable, governed, and supported by the required approval, pricing, and archive path.",
      opportunitySummary: "Private AI gateway evidence-packaging lane for regulated teams that need governed marketplace execution without exposing internal data.",
      competitorWeakness: "Competing AI gateways expose weak audit lineage, vague proof packages, and generic pricing that does not align to regulated execution risk.",
      buyerPain: "Operators in regulated teams cannot prove what the model did, what it cost, or whether the workflow stayed inside policy.",
      proposedPackageTool: "Veklom Governed Evidence Gateway: governed execution bundle with policy checks, signed archive package, and reserve-priced run controls.",
      pricingHypothesis: { model: "operating_reserve", setupFeeUsd: 4500, governedRunReserveUsd: 1500, evidenceBundleUsd: 750 },
      nextAction: "Prepare the founder-reviewed package page and run one tenant-facing governed evaluation demo.",
    };
  }

  return {
    decisionStatus: "blocked" as const,
    decisionReason: "The founder intent did not resolve to a sufficiently specific, evidence-backed revenue path.",
    opportunitySummary: "No governed revenue opportunity qualified.",
    competitorWeakness: "Insufficient competitor signal specificity.",
    buyerPain: "Insufficient buyer pain specificity.",
    proposedPackageTool: "Blocked pending clearer governed opportunity definition.",
    pricingHypothesis: { model: "operating_reserve", status: "blocked" },
    nextAction: "Refine the founder intent so it points to a concrete buyer, pain, and governed package boundary.",
  };
}

function buildRevenueOpportunityArtifact(plan: V3Plan) {
  const decision = deriveRevenueIntentDecision(plan.intent);
  return {
    artifactSummary: `${decision.opportunitySummary} Decision: ${decision.decisionStatus}. ${decision.decisionReason}`,
    opportunitySummary: decision.opportunitySummary,
    competitorWeakness: decision.competitorWeakness,
    buyerPain: decision.buyerPain,
    proposedPackageTool: decision.proposedPackageTool,
    pricingHypothesis: decision.pricingHypothesis,
    policyRiskReview: "Only archive-backed, policy-safe claims are allowed. No deployment-level implementation claim may exceed captured evidence.",
    requiredEvidence: [
      "competitor weakness brief",
      "policy decision log",
      "runtime policy path",
      "pricing reserve trace",
      "archive bundle hash",
    ],
    nextAction: decision.nextAction,
    decisionReason: decision.decisionReason,
    finalStatus: decision.decisionStatus,
    route: plan.route,
  };
}

function buildV3InspectionView(runId: string) {
  const run = state.v3Runs.find((entry) => entry.id === runId);
  if (!run) {
    throw new Error(`V3 run ${runId} not found.`);
  }
  const plan = state.v3Plans.find((entry) => entry.id === run.planId);
  if (!plan) {
    throw new Error(`V3 plan ${run.planId} not found.`);
  }
  const events = state.v3Events.filter((event) => event.runId === runId).sort((left, right) => left.seq - right.seq);
  const archive = state.v3Archives.find((entry) => entry.id === run.archiveRecordId);
  const replayResults = state.v3ReplayResults.filter((entry) => entry.sourceRunId === runId);
  const replayArchives = state.v3Archives.filter((entry) => entry.runId === runId && entry.type === "replay_bundle");
  const commercialArtifacts = state.v3CommercialArtifacts.filter((entry) => entry.sourceRunId === runId);
  const eventChainIntegrity = buildEventChainIntegrity(runId);
  const archiveIntegrity = buildArchiveIntegrity(run, archive);
  const replayIntegrity = buildReplayIntegrity(run, replayResults, replayArchives);
  return {
    planSummary: {
      id: plan.id,
      title: plan.title,
      intent: plan.intent,
      status: plan.status,
      revision: plan.revision,
      revisionHash: plan.revisionHash,
      frozenAt: plan.frozenAt,
      requiredOutputs: plan.requiredOutputs,
    },
    pillarRoute: plan.route.map((pillarId) => ({
      id: pillarId,
      name: getV3Pillar(pillarId)?.name,
    })),
    committeeRoute: plan.committeeIds.map((committeeId) => getV3Committee(committeeId)),
    workerAssignments: plan.workerIds.map((workerId) => getV3Worker(workerId)),
    skillBindings: plan.skillIds.map((skillId) => getV3Skill(skillId)),
    validationChecks: buildV3ValidationChecks(plan, run),
    orderedEventTimeline: events,
    eventChainIntegrity,
    archiveRecord: archive || null,
    archiveIntegrity,
    replayArchives,
    replayStatus: replayResults.length > 0 ? replayResults : [{ status: "not_created", summary: "No replay has been created for this run." }],
    replayIntegrity,
    commercialArtifacts,
    finalBusinessArtifact: run.artifact || null,
  };
}

function mapFounderReviewStatusToDecisionStatus(status: FounderReviewStatus): V3DecisionStatus {
  if (status === "approved") return "approved";
  if (status === "pending_founder_review" || status === "needs_revision") return "needs_founder_review";
  return "blocked";
}

function archiveCommercialDecision(artifact: CommercialArtifact, createdBy: string) {
  const sourceRun = state.v3Runs.find((entry) => entry.id === artifact.sourceRunId);
  const runEvents = state.v3Events.filter((event) => event.runId === artifact.sourceRunId).sort((left, right) => left.seq - right.seq);
  const archiveBase: Omit<ArchiveRecord, "bundleHash"> = {
    id: createId("v3arc"),
    runId: artifact.sourceRunId,
    planId: artifact.sourcePlanId,
    planRevision: sourceRun?.planRevision || 0,
    archivePath: `${artifact.archiveReference}/decision`,
    type: "commercial_decision",
    summary: `Commercial decision archive for ${artifact.title}`,
    createdAt: now(),
    createdBy,
    decisionStatus: mapFounderReviewStatusToDecisionStatus(artifact.founderReview.status),
    artifact: {
      commercialArtifactId: artifact.id,
      type: artifact.type,
      founderReview: artifact.founderReview,
      headline: artifact.copy.headline,
      summary: artifact.summary,
    },
    eventIds: runEvents.map((event) => event.id),
    hashAlgorithm: V3_ARCHIVE_HASH_ALGORITHM,
    signer: createdBy,
    signedAt: now(),
    sourceEventRange: runEvents.length > 0 ? { startSeq: runEvents[0].seq, endSeq: runEvents[runEvents.length - 1].seq } : undefined,
    lineage: {
      sourceCommercialArtifactId: artifact.id,
      sourceRunId: artifact.sourceRunId,
      sourcePlanId: artifact.sourcePlanId,
    },
    metadata: {
      artifactType: artifact.type,
      buyerFacing: artifact.buyerFacing,
      evidenceBacked: artifact.evidenceBacked,
    },
    replayable: false,
  };
  const archive: ArchiveRecord = {
    ...archiveBase,
    bundleHash: computeArchiveBundleHash(archiveBase),
  };
  validateArchiveRecordRecord(archive);
  state.v3Archives = [archive, ...state.v3Archives].slice(0, MAX_ARCHIVES);
  artifact.founderReview.archiveReference = archive.id;
  artifact.updatedAt = now();
  return archive;
}

function refreshCommercialScorecard() {
  const approvedArtifacts = state.v3CommercialArtifacts.filter((artifact) => artifact.founderReview.status === "approved");
  const blockedArtifacts = state.v3CommercialArtifacts.filter((artifact) => artifact.founderReview.status === "rejected");
  const commercialArchives = state.v3Archives.filter((archive) => archive.type === "commercial_decision");
  const directReplayChecksCompleted = state.v3CommercialArtifacts.filter(
    (artifact) => Boolean(artifact.replayArchiveRecordId && !artifact.sourceCommercialArtifactId),
  ).length;
  const replayLinkedArtifacts = state.v3CommercialArtifacts.filter((artifact) => Boolean(artifact.replayArchiveRecordId)).length;
  state.v3CommercialScorecard = {
    qualifiedEvaluationConversations: state.v3CommercialScorecard.qualifiedEvaluationConversations || 0,
    privateBackendAccessRequests: state.v3CommercialScorecard.privateBackendAccessRequests || 0,
    vendorToolConversations: state.v3CommercialScorecard.vendorToolConversations || 0,
    approvedPackageConcepts: approvedArtifacts.filter((artifact) => artifact.type === "buyer_facing_offer" || artifact.type === "tool_package_candidate").length,
    founderApprovedCommunityInteractions: approvedArtifacts.filter((artifact) => artifact.type === "outreach_asset" || artifact.type === "competitor_positioning").length,
    blockedUnsafeClaims: blockedArtifacts.length,
    archiveRecordsWritten: commercialArchives.length,
    directReplayChecksCompleted,
    replayLinkedArtifacts,
    lastUpdatedAt: now(),
  };
}

function createCommercialArtifact(
  input: Omit<CommercialArtifact, "id" | "createdAt" | "updatedAt" | "founderReview"> & { founderReview: Omit<CommercialArtifact["founderReview"], "archiveReference"> },
) {
  const artifact: CommercialArtifact = {
    id: createId("v3commercial"),
    createdAt: now(),
    updatedAt: now(),
    ...input,
    founderReview: {
      ...input.founderReview,
      archiveReference: undefined,
    },
  };
  const archive = archiveCommercialDecision(artifact, "UACP V3");
  artifact.archiveReference = archive.id;
  state.v3CommercialArtifacts = [artifact, ...state.v3CommercialArtifacts.filter((entry) => entry.id !== artifact.id)];
  refreshCommercialScorecard();
  return artifact;
}

function createCommercialArtifactsForRun(plan: V3Plan, run: V3Run, sourceArchive: ArchiveRecord) {
  if (!run.artifact) return [];
  const summary = ensureString(run.artifact.opportunitySummary || run.artifact.artifactSummary, "commercialArtifact.summary");
  const artifacts: CommercialArtifact[] = [];
  const intent = plan.intent.toLowerCase();

  if (intent.includes("sellable marketplace opportunity")) {
    artifacts.push(
      createCommercialArtifact({
        type: "buyer_facing_offer",
        title: "Veklom Sovereign AI Hub / Governed Evidence Gateway",
        summary,
        sourcePlanId: plan.id,
        sourceRunId: run.id,
        sourceArchiveRecordId: sourceArchive.id,
        buyerFacing: true,
        positioningUse: true,
        highRisk: false,
        evidenceBacked: true,
        copy: {
          headline: "Veklom Sovereign AI Hub",
          subheadline: "Governed Evidence Gateway for private AI operations.",
          body: [
            "Every private AI run passes through policy, cost controls, routing rules, and archive capture before it becomes part of your operation.",
            "Veklom gives teams a tenant-scoped way to test models, run pipelines, control fallback, monitor usage, and produce replayable evidence for every AI action.",
          ],
          cta: "Book a governed evaluation demo",
        },
        archiveReference: `${plan.archivePath}/commercial/buyer-facing-offer`,
        founderReview: {
          status: "approved",
          reason: "Approved from an archive-backed commercial artifact with pricing and governance framing.",
          riskNotes: ["Do not overclaim deployment verification beyond evidence."],
          approvedCopy: "Veklom Sovereign AI Hub / Governed Evidence Gateway",
          rejectedClaims: [],
          reviewedAt: now(),
          reviewedBy: "UACP V3",
        },
      }),
      createCommercialArtifact({
        type: "tool_package_candidate",
        title: "Governed Evidence Gateway Package",
        summary,
        sourcePlanId: plan.id,
        sourceRunId: run.id,
        sourceArchiveRecordId: sourceArchive.id,
        buyerFacing: false,
        positioningUse: false,
        highRisk: false,
        evidenceBacked: true,
        copy: {
          headline: "Governed Evidence Gateway",
          subheadline: "Archive-backed package candidate for regulated AI operations.",
          body: [
            "Includes policy checking, reserve-priced execution, ordered events, source archive, and replayable proof.",
          ],
        },
        archiveReference: `${plan.archivePath}/commercial/tool-package`,
        founderReview: {
          status: "approved",
          reason: "Approved as an internal package concept backed by governance, pricing, and archive evidence.",
          riskNotes: [],
          approvedCopy: "Governed Evidence Gateway package candidate approved.",
          rejectedClaims: [],
          reviewedAt: now(),
          reviewedBy: "UACP V3",
        },
      }),
    );
  } else if (intent.includes("regulated-industry buyer pain")) {
    artifacts.push(
      createCommercialArtifact({
        type: "founder_review_claim",
        title: "Regulated Workflow Proof Diagnostic",
        summary,
        sourcePlanId: plan.id,
        sourceRunId: run.id,
        sourceArchiveRecordId: sourceArchive.id,
        buyerFacing: true,
        positioningUse: false,
        highRisk: true,
        evidenceBacked: true,
        copy: {
          headline: "Regulated Workflow Proof Diagnostic",
          subheadline: "Private evaluation artifact pending founder approval.",
          body: [
            "This diagnostic frames regulated buyer pain around archive-backed workflow proof, admission control, and scoped runtime policy.",
            "Public publication is blocked until founder approves the specific regulated-industry claim set.",
          ],
          cta: "Internal founder review required",
        },
        archiveReference: `${plan.archivePath}/commercial/founder-review-claim`,
        founderReview: {
          status: "pending_founder_review",
          reason: "Regulated-industry claims require founder approval before public use.",
          riskNotes: [
            "No broad compliance promise can publish yet.",
            "Keep the asset limited to private evaluation or sales-call use until approved.",
          ],
          approvedCopy: "",
          rejectedClaims: [
            "Do not imply sector-wide compliance certification.",
          ],
        },
      }),
    );
  } else if (intent.includes("competitor weakness")) {
    artifacts.push(
      createCommercialArtifact({
        type: "competitor_positioning",
        title: "Competitor Proof-Gap Positioning",
        summary,
        sourcePlanId: plan.id,
        sourceRunId: run.id,
        sourceArchiveRecordId: sourceArchive.id,
        buyerFacing: true,
        positioningUse: true,
        highRisk: true,
        evidenceBacked: true,
        copy: {
          headline: "The problem is not AI access. It is proof.",
          subheadline: "Veklom positions against weak audit lineage and generic pricing.",
          body: [
            "Competing AI gateways still leave teams with logs nobody trusts and pricing disconnected from governed execution.",
            "Veklom packages policy, reserve economics, source archives, and replayable proof into one tenant-scoped operating hub.",
          ],
          cta: "See the proof chain",
        },
        archiveReference: `${plan.archivePath}/commercial/competitor-positioning`,
        founderReview: {
          status: "approved",
          reason: "Competitor claim is framed around evidence-backed governance gaps and avoids unsupported feature assertions.",
          riskNotes: ["Keep all competitor language comparative and evidence-backed."],
          approvedCopy: "Competitor proof-gap positioning approved for outreach and website framing.",
          rejectedClaims: [],
          reviewedAt: now(),
          reviewedBy: "UACP V3",
        },
      }),
      createCommercialArtifact({
        type: "outreach_asset",
        title: "Competitor Gap Outreach Asset",
        summary,
        sourcePlanId: plan.id,
        sourceRunId: run.id,
        sourceArchiveRecordId: sourceArchive.id,
        buyerFacing: true,
        positioningUse: true,
        highRisk: false,
        evidenceBacked: true,
        copy: {
          headline: "If your AI gateway cannot prove what happened, your team is carrying the risk.",
          subheadline: "Outreach copy derived from V3 competitor-gap analysis.",
          body: [
            "We found a recurring market weakness: teams can test models, but they still cannot prove the decision trail, cost path, or replay outcome.",
            "Veklom gives private AI teams governed execution with source archive and replayable proof.",
          ],
          cta: "Request a private backend access walkthrough",
        },
        archiveReference: `${plan.archivePath}/commercial/outreach-asset`,
        founderReview: {
          status: "approved",
          reason: "Outreach asset is evidence-backed and commercially usable.",
          riskNotes: ["Keep the proof claim tied to replay and archive features only."],
          approvedCopy: "Outreach asset approved for founder-supervised use.",
          rejectedClaims: [],
          reviewedAt: now(),
          reviewedBy: "UACP V3",
        },
      }),
    );
  }

  refreshCommercialScorecard();
  return artifacts;
}

function attachReplayToCommercialArtifacts(runId: string, replayResultId: string, replayArchiveId: string) {
  let updated = false;
  state.v3CommercialArtifacts = state.v3CommercialArtifacts.map((artifact) => {
    if (artifact.sourceRunId !== runId) return artifact;
    updated = true;
    return {
      ...artifact,
      sourceReplayResultId: replayResultId,
      replayArchiveRecordId: replayArchiveId,
      updatedAt: now(),
    };
  });
  if (updated) {
    refreshCommercialScorecard();
  }
}

function buildCommercialArtifactView(artifactId: string) {
  const artifact = state.v3CommercialArtifacts.find((entry) => entry.id === artifactId);
  if (!artifact) {
    throw new Error(`Commercial artifact ${artifactId} not found.`);
  }
  const sourcePlan = state.v3Plans.find((entry) => entry.id === artifact.sourcePlanId) || null;
  const sourceRun = state.v3Runs.find((entry) => entry.id === artifact.sourceRunId) || null;
  const sourceArchive = state.v3Archives.find((entry) => entry.id === artifact.sourceArchiveRecordId) || null;
  const replayArchive = artifact.replayArchiveRecordId
    ? state.v3Archives.find((entry) => entry.id === artifact.replayArchiveRecordId) || null
    : null;
  const replayResult = artifact.sourceReplayResultId
    ? state.v3ReplayResults.find((entry) => entry.id === artifact.sourceReplayResultId) || null
    : null;
  const sourceCommercialArtifact = artifact.sourceCommercialArtifactId
    ? state.v3CommercialArtifacts.find((entry) => entry.id === artifact.sourceCommercialArtifactId) || null
    : null;
  return {
    artifact,
    sourcePlan,
    sourceRun,
    sourceArchive,
    replayArchive,
    replayResult,
    sourceCommercialArtifact,
  };
}

function applyFounderReviewDecision(
  artifactId: string,
  status: FounderReviewStatus,
  reason: string,
  riskNotes: string[],
  approvedCopy: string | undefined,
  rejectedClaims: string[],
  reviewedBy: string,
) {
  const artifact = state.v3CommercialArtifacts.find((entry) => entry.id === artifactId);
  if (!artifact) {
    throw new Error(`Commercial artifact ${artifactId} not found.`);
  }
  if (artifact.type === "founder_review_claim" && status === "approved" && (!approvedCopy || approvedCopy.trim().length === 0)) {
    throw new Error("Regulated founder-review claims require approved copy before publication.");
  }
  if (artifact.type === "competitor_positioning" && status === "approved" && !artifact.evidenceBacked) {
    throw new Error("Competitor positioning cannot publish without evidence-backed framing.");
  }
  if ((artifact.type === "vendor_lead" || artifact.type === "tool_package_candidate") && status === "approved") {
    const hasRiskOrLicenseReview = riskNotes.some((note) => /risk|license/i.test(note));
    if (!hasRiskOrLicenseReview) {
      throw new Error("Vendor/tool artifacts cannot be approved without risk/license review notes.");
    }
  }

  artifact.founderReview = {
    status,
    reason,
    riskNotes,
    approvedCopy,
    rejectedClaims,
    archiveReference: artifact.founderReview.archiveReference,
    reviewedAt: now(),
    reviewedBy,
  };
  artifact.updatedAt = now();
  const archive = archiveCommercialDecision(artifact, reviewedBy);
  artifact.archiveReference = archive.id;
  refreshCommercialScorecard();
  return { artifact, archive };
}

function attachReplayToCommercialArtifact(artifactId: string, replayResultId: string, replayArchiveId: string) {
  const artifact = state.v3CommercialArtifacts.find((entry) => entry.id === artifactId);
  if (!artifact) {
    throw new Error(`Commercial artifact ${artifactId} not found.`);
  }
  artifact.sourceReplayResultId = replayResultId;
  artifact.replayArchiveRecordId = replayArchiveId;
  artifact.updatedAt = now();
  refreshCommercialScorecard();
}

function createReplayForCommercialArtifact(artifactId: string, requestedBy: string, mode: ReplayRequest["mode"], reason: string) {
  const artifact = state.v3CommercialArtifacts.find((entry) => entry.id === artifactId);
  if (!artifact) {
    throw new Error(`Commercial artifact ${artifactId} not found.`);
  }
  if (!artifact.buyerFacing && !artifact.positioningUse && !artifact.highRisk) {
    throw new Error("Replay is reserved for buyer-facing, positioning, founder-reviewed, or high-risk artifacts.");
  }
  const sourceRun = state.v3Runs.find((entry) => entry.id === artifact.sourceRunId);
  if (!sourceRun) {
    throw new Error(`Source run ${artifact.sourceRunId} not found for commercial artifact ${artifactId}.`);
  }
  const replayRequest: ReplayRequest = {
    id: createId("v3replayreq"),
    runId: sourceRun.id,
    requestedBy,
    requestedAt: now(),
    mode,
    reason,
  };
  state.v3ReplayRequests = [replayRequest, ...state.v3ReplayRequests];
  const replayResultId = createId("v3replay");
  const runEvents = state.v3Events.filter((event) => event.runId === sourceRun.id).sort((left, right) => left.seq - right.seq);
  const replayArchiveBase: Omit<ArchiveRecord, "bundleHash"> = {
    id: createId("v3arc"),
    runId: sourceRun.id,
    planId: sourceRun.planId,
    planRevision: sourceRun.planRevision,
    archivePath: `${artifact.archiveReference}/replay`,
    type: "replay_bundle",
    summary: `Commercial replay bundle for ${artifact.title}`,
    createdAt: now(),
    createdBy: requestedBy,
    decisionStatus: mapFounderReviewStatusToDecisionStatus(artifact.founderReview.status),
    artifact: {
      sourceArtifactId: artifact.id,
      sourceRunId: sourceRun.id,
      sourceArchiveRecordId: artifact.sourceArchiveRecordId,
      replayMode: mode,
      replayReason: reason,
      sourceHeadline: artifact.copy.headline,
      sourceSummary: artifact.summary,
      replayGuarantees: [
        "source artifact unchanged",
        "source archive unchanged",
        "source run unchanged",
        "separate replay archive written",
      ],
    },
    eventIds: runEvents.map((event) => event.id),
    hashAlgorithm: V3_ARCHIVE_HASH_ALGORITHM,
    signer: requestedBy,
    signedAt: now(),
    sourceEventRange: runEvents.length > 0 ? { startSeq: runEvents[0].seq, endSeq: runEvents[runEvents.length - 1].seq } : undefined,
    lineage: {
      sourceCommercialArtifactId: artifact.id,
      sourceRunId: sourceRun.id,
      sourceArchiveRecordId: artifact.sourceArchiveRecordId,
    },
    metadata: {
      replayMode: mode,
      replayReason: reason,
      sourceArtifactId: artifact.id,
    },
    replayable: true,
  };
  const replayArchive: ArchiveRecord = {
    ...replayArchiveBase,
    bundleHash: computeArchiveBundleHash(replayArchiveBase),
  };
  validateArchiveRecordRecord(replayArchive);
  state.v3Archives = [replayArchive, ...state.v3Archives].slice(0, MAX_ARCHIVES);
  const replayResult: ReplayResult = {
    id: replayResultId,
    sourceRunId: sourceRun.id,
    mode,
    status: "completed",
    summary: `Commercial replay completed for artifact ${artifact.id} without overwriting the source record.`,
    archiveRecordId: replayArchive.id,
    replayArchiveId: replayArchive.id,
    sourceUnchanged: true,
    eventChainIntegrity: buildEventChainIntegrity(sourceRun.id),
    divergenceNotes: [
      "Replay targeted the commercial artifact only.",
      "Source archive and source artifact remained unchanged.",
    ],
  };
  validateReplayRequestRecord(replayRequest);
  validateReplayResultRecord(replayResult);
  state.v3ReplayResults = [replayResult, ...state.v3ReplayResults];
  attachReplayToCommercialArtifact(artifact.id, replayResult.id, replayArchive.id);
  return { replayRequest, replayResult, replayArchive, artifact: buildCommercialArtifactView(artifact.id) };
}

function generateHomepageCopyArtifact(sourceArtifactId: string) {
  const source = state.v3CommercialArtifacts.find((entry) => entry.id === sourceArtifactId);
  if (!source || source.type !== "buyer_facing_offer") {
    throw new Error("Homepage copy source must be a buyer-facing offer artifact.");
  }
  if (source.founderReview.status !== "approved") {
    throw new Error("Homepage copy can only be generated from an approved buyer-facing offer.");
  }
  return createCommercialArtifact({
    type: "buyer_facing_offer",
    title: "Homepage Copy Block: Veklom Sovereign AI Hub",
    summary: "Buyer-facing homepage block derived from the approved Governed Evidence Gateway offer.",
    sourceCommercialArtifactId: source.id,
    sourcePlanId: source.sourcePlanId,
    sourceRunId: source.sourceRunId,
    sourceArchiveRecordId: source.sourceArchiveRecordId,
    replayArchiveRecordId: source.replayArchiveRecordId,
    sourceReplayResultId: source.sourceReplayResultId,
    buyerFacing: true,
    positioningUse: true,
    highRisk: false,
    evidenceBacked: true,
    copy: {
      headline: "Veklom Sovereign AI Hub",
      subheadline: "Test, run, deploy, govern, and monitor private AI from one tenant-scoped workspace.",
      body: [
        "Every private AI run passes through policy, cost controls, routing rules, and archive capture before it becomes part of your operation.",
        "Veklom gives teams a tenant-scoped way to test models, run pipelines, control fallback, monitor usage, and produce replayable evidence for every AI action.",
      ],
      cta: "Book a governed evaluation demo",
    },
    archiveReference: `${source.archiveReference}/homepage-copy`,
    founderReview: {
      status: "approved",
      reason: "Derived from an approved buyer-facing offer with evidence-backed framing.",
      riskNotes: ["Do not expand beyond governed evidence and private AI operating claims."],
      approvedCopy: "Homepage copy block approved.",
      rejectedClaims: [],
      reviewedAt: now(),
      reviewedBy: "UACP V3",
    },
  });
}

function generateOutreachCopyArtifact(sourceArtifactId: string) {
  const source = state.v3CommercialArtifacts.find((entry) => entry.id === sourceArtifactId);
  if (!source || source.type !== "competitor_positioning") {
    throw new Error("Outreach copy source must be a competitor-positioning artifact.");
  }
  if (!source.evidenceBacked) {
    throw new Error("Competitor outreach requires evidence-backed framing.");
  }
  return createCommercialArtifact({
    type: "outreach_asset",
    title: "Outreach Copy Block: Competitor Proof Gap",
    summary: "Buyer-facing outreach block derived from the approved competitor-positioning artifact.",
    sourceCommercialArtifactId: source.id,
    sourcePlanId: source.sourcePlanId,
    sourceRunId: source.sourceRunId,
    sourceArchiveRecordId: source.sourceArchiveRecordId,
    replayArchiveRecordId: source.replayArchiveRecordId,
    sourceReplayResultId: source.sourceReplayResultId,
    buyerFacing: true,
    positioningUse: true,
    highRisk: false,
    evidenceBacked: true,
    copy: {
      headline: "If your AI gateway cannot prove what happened, your team is carrying the risk.",
      subheadline: "Veklom turns governed execution into replayable evidence instead of trust-me logs.",
      body: [
        "We found a recurring market gap: teams can test models, but they still cannot prove the decision trail, cost path, or replay outcome.",
        "Veklom gives private AI teams policy-backed execution, source archive, and replayable proof without rewriting history.",
      ],
      cta: "Request a private backend access walkthrough",
    },
    archiveReference: `${source.archiveReference}/outreach-copy`,
    founderReview: {
      status: "approved",
      reason: "Derived from an approved competitor-positioning artifact with evidence-backed framing.",
      riskNotes: ["Keep competitor comparisons grounded in proof and governance language only."],
      approvedCopy: "Outreach copy block approved.",
      rejectedClaims: [],
      reviewedAt: now(),
      reviewedBy: "UACP V3",
    },
  });
}

function createRevenueOpportunityPlan(intent: string) {
  const createdAt = now();
  const route: VeklomPillarId[] = [
    "research-knowledge-learning",
    "model-tool-governance",
    "governance-policy",
    "compliance-risk-legal",
    "economics-operating-reserve",
    "evidence-audit-archives",
  ];
  const plan = normalizeV3Plan({
    id: createId("v3plan"),
    title: "Run Veklom Revenue Opportunity Test",
    intent,
    status: "approved",
    revision: 1,
    revisionHash: "",
    frozenAt: createdAt,
    createdAt,
    updatedAt: createdAt,
    pillars: uniqueStrings([...route, "tenant-experience-integration"]) as VeklomPillarId[],
    committeeIds: ["research-command", "marketplace-council", "governance-council", "risk-office", "reserve-board", "archives-board"],
    workerIds: ["scout-revenue", "curator-market", "builder-package", "arbiter-policy", "switchman-runtime", "sheriff-risk", "gauge-economics", "treasurer-reserve", "steward-tenant"],
    skillIds: ["skill-competitive-intel", "skill-marketplace-curation", "skill-policy-review", "skill-risk-audit", "skill-reserve-pricing", "skill-archive-bundler"],
    route,
    requiredOutputs: [
      "opportunity summary",
      "competitor weakness",
      "buyer pain",
      "proposed package/tool",
      "pricing hypothesis",
      "policy/risk review",
      "required evidence",
      "next action",
      "archive record",
      "final status",
    ],
    approvalPath: ["research-command", "marketplace-council", "governance-council", "risk-office", "reserve-board", "archives-board"],
    runtimePolicies: ["governed-output-only", "archive-required", "no-unsupported-implementation-claims", "reserve-pricing-attached"],
    evidenceCapture: ["plan_snapshot", "ordered_events", "policy_decision_log", "pricing_trace", "archive_bundle"],
    archivePath: "archives/core/revenue-opportunity-test",
  });
  validateV3Plan(plan);
  validateGovernedLiveRun(plan);
  return plan;
}

function executeRevenueOpportunityRun(plan: V3Plan) {
  validateGovernedLiveRun(plan);
  const submittedAt = now();
  const run: V3Run = {
    id: createId("v3run"),
    planId: plan.id,
    planRevision: plan.revision,
    planRevisionHash: plan.revisionHash,
    status: "executing",
    submittedAt,
    startedAt: submittedAt,
    workerIds: plan.workerIds,
    committeeIds: plan.committeeIds,
    skillIds: plan.skillIds,
    approvalPath: plan.approvalPath,
    runtimePolicies: plan.runtimePolicies,
    evidenceCapture: plan.evidenceCapture,
    currentStep: "research-knowledge-learning",
    integrityStatus: "ok",
    errors: [],
  };
  state.v3Runs = [run, ...state.v3Runs];
  appendV3Event({
    runId: run.id,
    planId: plan.id,
    type: "run_submitted",
    pillarIds: ["research-knowledge-learning"],
    message: `Run ${run.id} submitted for ${plan.title}.`,
    payload: { intent: plan.intent },
  });

  for (const committeeId of plan.approvalPath) {
    const committee = getV3Committee(committeeId)!;
    appendV3Event({
      runId: run.id,
      planId: plan.id,
      type: "approval_requested",
      committeeId,
      pillarIds: committee.pillarIds,
      message: `${committee.name} received approval request.`,
    });
    const assignedWorkers = veklomWorkers.filter((worker) => worker.committeeId === committeeId);
    assignedWorkers.forEach((worker) => {
      appendV3Event({
        runId: run.id,
        planId: plan.id,
        type: "worker_assigned",
        committeeId,
        workerId: worker.id,
        pillarIds: [worker.pillarId],
        message: `${worker.name} assigned: ${worker.currentJob}.`,
      });
      worker.allowedSkillIds.forEach((skillId) => {
        appendV3Event({
          runId: run.id,
          planId: plan.id,
          type: "skill_invoked",
          committeeId,
          workerId: worker.id,
          skillId,
          pillarIds: [worker.pillarId],
          message: `${worker.name} invoked ${getV3Skill(skillId)?.name}.`,
        });
      });
    });
    appendV3Event({
      runId: run.id,
      planId: plan.id,
      type: "approval_granted",
      committeeId,
      pillarIds: committee.pillarIds,
      message: `${committee.name} approved its stage.`,
    });
  }

  const artifact = buildRevenueOpportunityArtifact(plan);
  run.status = "completed";
  run.decisionStatus = artifact.finalStatus as V3Run["decisionStatus"];
  run.currentStep = "completed";
  run.completedAt = now();
  run.artifact = artifact;
  run.summary = "Revenue opportunity test completed with governed plan, ordered events, pricing, risk review, and archive bundle.";
  appendV3Event({
    runId: run.id,
    planId: plan.id,
    type: "artifact_created",
    committeeId: "archives-board",
    workerId: "steward-tenant",
    skillId: "skill-archive-bundler",
    pillarIds: ["evidence-audit-archives"],
    message: `Governed revenue artifact created for ${run.id}.`,
    payload: artifact,
  });
  const archive = writeV3ArchiveRecord(run, artifact);
  if (!archive?.id) {
    run.integrityStatus = "integrity_failed";
    throw new Error(`Governed run ${run.id} completed without an archive bundle.`);
  }
  createCommercialArtifactsForRun(plan, run, archive);
  appendV3Event({
    runId: run.id,
    planId: plan.id,
    type: "run_completed",
    committeeId: "archives-board",
    pillarIds: ["evidence-audit-archives"],
    message: `Run ${run.id} completed with archive ${archive.id}.`,
    payload: { archiveRecordId: archive.id, decisionStatus: run.decisionStatus },
  });
  return { run, archive, artifact };
}

function createReplayForRun(runId: string, requestedBy: string, mode: ReplayRequest["mode"], reason: string) {
  const sourceRun = state.v3Runs.find((entry) => entry.id === runId);
  if (!sourceRun) {
    throw new Error(`Unknown V3 run ${runId}.`);
  }
  const replayRequest: ReplayRequest = {
    id: createId("v3replayreq"),
    runId,
    requestedBy,
    requestedAt: now(),
    mode,
    reason,
  };
  state.v3ReplayRequests = [replayRequest, ...state.v3ReplayRequests];
  const replayResultId = createId("v3replay");
  const replayArchive = writeV3ReplayArchiveRecord(sourceRun, replayRequest, replayResultId);
  const sourceArchiveIdBefore = sourceRun.archiveRecordId;
  const sourceArtifactSnapshot = canonicalizeForHash(sourceRun.artifact || {});
  const sourceEventChainIntegrity = buildEventChainIntegrity(sourceRun.id);
  const replayResult: ReplayResult = {
    id: replayResultId,
    sourceRunId: runId,
    mode,
    status: "completed",
    summary: `Replay prepared for ${runId} without overwriting the source run.`,
    archiveRecordId: replayArchive.id,
    replayArchiveId: replayArchive.id,
    sourceUnchanged: sourceRun.archiveRecordId === sourceArchiveIdBefore
      && canonicalizeForHash(sourceRun.artifact || {}) === sourceArtifactSnapshot,
    eventChainIntegrity: sourceEventChainIntegrity,
    divergenceNotes: [
      "Replay reconstructed event order and source artifact without mutating the source run.",
      "Replay archive bundle written separately from the source archive record.",
    ],
  };
  validateReplayRequestRecord(replayRequest);
  validateReplayResultRecord(replayResult);
  state.v3ReplayResults = [replayResult, ...state.v3ReplayResults];
  attachReplayToCommercialArtifacts(runId, replayResult.id, replayArchive.id);
  return { replayRequest, replayResult, replayArchive };
}

function parsePillars(value: unknown): Pillar[] {
  if (!Array.isArray(value)) throw new Error("Governance registry pillars must be an array.");
  const pillars = value.map((entry, index) => {
    const record = ensureRecord(entry, `pillar[${index}]`);
    return {
      id: ensureString(record.id, `pillar[${index}].id`),
      name: ensureString(record.name, `pillar[${index}].name`),
      mandate: ensureString(record.mandate, `pillar[${index}].mandate`),
      kpi: ensureString(record.kpi, `pillar[${index}].kpi`),
    } satisfies Pillar;
  });
  ensureUniqueIds(pillars, "Governance registry pillars");
  return pillars;
}

function parseCommittees(value: unknown, pillarIds: Set<string>): Committee[] {
  if (!Array.isArray(value)) throw new Error("Governance registry committees must be an array.");
  const committees = value.map((entry, index) => {
    const record = ensureRecord(entry, `committee[${index}]`);
    const linkedPillars = ensureStringArray(record.pillarIds, `committee[${index}].pillarIds`);
    if (linkedPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`committee[${index}] references unknown pillar ids.`);
    }
    return {
      id: ensureString(record.id, `committee[${index}].id`),
      name: ensureString(record.name, `committee[${index}].name`),
      purpose: ensureString(record.purpose, `committee[${index}].purpose`),
      authority: ensureString(record.authority, `committee[${index}].authority`),
      chair: ensureString(record.chair, `committee[${index}].chair`),
      members: ensureStringArray(record.members, `committee[${index}].members`),
      escalation: ensureString(record.escalation, `committee[${index}].escalation`),
      allowedActions: ensureStringArray(record.allowedActions, `committee[${index}].allowedActions`),
      vetoConditions: ensureStringArray(record.vetoConditions, `committee[${index}].vetoConditions`),
      pillarIds: linkedPillars,
    } satisfies Committee;
  });
  ensureUniqueIds(committees, "Governance registry committees");
  return committees;
}

function parseSkills(
  value: unknown,
  pillarIds: Set<string>,
  governingCommitteeIds: Set<string>,
  usableCommitteeIds: Set<string>,
): SkillArtifact[] {
  if (!Array.isArray(value)) throw new Error("Governance registry skills must be an array.");
  const skills = value.map((entry, index) => {
    const record = ensureRecord(entry, `skill[${index}]`);
    const linkedPillars = ensureStringArray(record.pillarIds, `skill[${index}].pillarIds`);
    if (linkedPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`skill[${index}] references unknown pillar ids.`);
    }
    const status = ensureString(record.status, `skill[${index}].status`);
    if (!["approved", "review", "quarantined"].includes(status)) {
      throw new Error(`skill[${index}].status is invalid.`);
    }
    const governingCommitteeId = typeof record.governingCommitteeId === "string" ? record.governingCommitteeId.trim() : undefined;
    if (governingCommitteeId && !governingCommitteeIds.has(governingCommitteeId)) {
      throw new Error(`skill[${index}] references unknown governing committee.`);
    }
    const usableByCommitteeIds = Array.isArray(record.usableByCommitteeIds)
      ? ensureStringArray(record.usableByCommitteeIds, `skill[${index}].usableByCommitteeIds`)
      : undefined;
    if (usableByCommitteeIds?.some((committeeId) => !usableCommitteeIds.has(committeeId))) {
      throw new Error(`skill[${index}] references unknown usable-by committees.`);
    }
    const publishRisk = typeof record.publishRisk === "string" ? record.publishRisk.trim() : undefined;
    if (publishRisk && !["low", "medium", "high", "critical"].includes(publishRisk)) {
      throw new Error(`skill[${index}].publishRisk is invalid.`);
    }
    return {
      id: ensureString(record.id, `skill[${index}].id`),
      name: ensureString(record.name, `skill[${index}].name`),
      category: ensureString(record.category, `skill[${index}].category`),
      description: ensureString(record.description, `skill[${index}].description`),
      allowedTools: ensureStringArray(record.allowedTools, `skill[${index}].allowedTools`),
      source: ensureString(record.source, `skill[${index}].source`),
      ref: ensureString(record.ref, `skill[${index}].ref`),
      treeSha: ensureString(record.treeSha, `skill[${index}].treeSha`),
      status: status as SkillArtifact["status"],
      pillarIds: linkedPillars,
      governingCommitteeId,
      usableByCommitteeIds,
      requiredEvidence: Array.isArray(record.requiredEvidence)
        ? ensureStringArray(record.requiredEvidence, `skill[${index}].requiredEvidence`)
        : [],
      publishRisk: (publishRisk || "medium") as SkillArtifact["publishRisk"],
      inputType: typeof record.inputType === "string" ? record.inputType.trim() : "governed_input",
      outputType: typeof record.outputType === "string" ? record.outputType.trim() : "governed_output",
      sla: typeof record.sla === "string" ? record.sla.trim() : "24h",
      revisionHistory: Array.isArray(record.revisionHistory)
        ? ensureStringArray(record.revisionHistory, `skill[${index}].revisionHistory`)
        : [ensureString(record.ref, `skill[${index}].ref`)],
    } satisfies SkillArtifact;
  });
  ensureUniqueIds(skills, "Governance registry skills");
  return skills;
}

function parseWorkflows(value: unknown, pillarIds: Set<string>): WorkflowArtifact[] {
  if (!Array.isArray(value)) throw new Error("Governance registry workflows must be an array.");
  const workflows = value.map((entry, index) => {
    const record = ensureRecord(entry, `workflow[${index}]`);
    const linkedPillars = ensureStringArray(record.pillarIds, `workflow[${index}].pillarIds`);
    if (linkedPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`workflow[${index}] references unknown pillar ids.`);
    }
    return {
      id: ensureString(record.id, `workflow[${index}].id`),
      name: ensureString(record.name, `workflow[${index}].name`),
      category: ensureString(record.category, `workflow[${index}].category`),
      description: ensureString(record.description, `workflow[${index}].description`),
      outcome: ensureString(record.outcome, `workflow[${index}].outcome`),
      pillarIds: linkedPillars,
    } satisfies WorkflowArtifact;
  });
  ensureUniqueIds(workflows, "Governance registry workflows");
  return workflows;
}

function parseEscalationRules(value: unknown, pillarIds: Set<string>, committeeIds: Set<string>): EscalationRule[] {
  if (!Array.isArray(value)) throw new Error("Governance registry escalationRules must be an array.");
  const rules = value.map((entry, index) => {
    const record = ensureRecord(entry, `escalationRule[${index}]`);
    const route = ensureStringArray(record.route, `escalationRule[${index}].route`);
    const linkedPillars = ensureStringArray(record.pillarIds, `escalationRule[${index}].pillarIds`);
    if (route.some((committeeId) => !committeeIds.has(committeeId))) {
      throw new Error(`escalationRule[${index}] references unknown route committees.`);
    }
    if (linkedPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`escalationRule[${index}] references unknown pillar ids.`);
    }
    const severity = ensureString(record.severity, `escalationRule[${index}].severity`);
    if (!["low", "medium", "high", "critical"].includes(severity)) {
      throw new Error(`escalationRule[${index}].severity is invalid.`);
    }
    const ownerCommitteeId = ensureString(record.ownerCommitteeId, `escalationRule[${index}].ownerCommitteeId`);
    if (!committeeIds.has(ownerCommitteeId)) {
      throw new Error(`escalationRule[${index}] references unknown owner committee.`);
    }
    return {
      id: ensureString(record.id, `escalationRule[${index}].id`),
      name: ensureString(record.name, `escalationRule[${index}].name`),
      description: ensureString(record.description, `escalationRule[${index}].description`),
      trigger: ensureString(record.trigger, `escalationRule[${index}].trigger`),
      route,
      severity: severity as RiskTier,
      ownerCommitteeId,
      pillarIds: linkedPillars,
    } satisfies EscalationRule;
  });
  ensureUniqueIds(rules, "Governance registry escalation rules");
  return rules;
}

function parseOperatorCommittees(value: unknown, pillarIds: Set<string>): OperatorCommittee[] {
  if (!Array.isArray(value)) throw new Error("Governance registry operatorCommittees must be an array.");
  const operatorCommittees = value.map((entry, index) => {
    const record = ensureRecord(entry, `operatorCommittee[${index}]`);
    const linkedPillars = ensureStringArray(record.pillarIds, `operatorCommittee[${index}].pillarIds`);
    if (linkedPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`operatorCommittee[${index}] references unknown pillar ids.`);
    }
    return {
      id: ensureString(record.id, `operatorCommittee[${index}].id`),
      name: ensureString(record.name, `operatorCommittee[${index}].name`),
      purpose: ensureString(record.purpose, `operatorCommittee[${index}].purpose`),
      pillarIds: linkedPillars,
      workerIds: ensureStringArray(record.workerIds, `operatorCommittee[${index}].workerIds`),
      chair: typeof record.chair === "string" ? record.chair.trim() : undefined,
      sponsor: typeof record.sponsor === "string" ? record.sponsor.trim() : undefined,
      decisionFramework:
        record.decisionFramework === "RACI" || record.decisionFramework === "DACI" || record.decisionFramework === "RAPID"
          ? record.decisionFramework
          : "RAPID",
      cadencePerDay: typeof record.cadencePerDay === "number" && Number.isFinite(record.cadencePerDay)
        ? Math.max(1, Math.round(record.cadencePerDay))
        : 3,
      regroupIntervalMinutes: typeof record.regroupIntervalMinutes === "number" && Number.isFinite(record.regroupIntervalMinutes)
        ? Math.max(1, Math.round(record.regroupIntervalMinutes))
        : 480,
      successMetrics: Array.isArray(record.successMetrics)
        ? ensureStringArray(record.successMetrics, `operatorCommittee[${index}].successMetrics`)
        : [],
    } satisfies OperatorCommittee;
  });
  ensureUniqueIds(operatorCommittees, "Governance registry operator committees");
  return operatorCommittees;
}

function parseWorkers(
  value: unknown,
  pillarIds: Set<string>,
  operatorCommitteeIds: Set<string>,
  escalationRuleIds: Set<string>,
): OperatorWorker[] {
  if (!Array.isArray(value)) throw new Error("Governance registry workers must be an array.");
  const workers = value.map((entry, index) => {
    const record = ensureRecord(entry, `worker[${index}]`);
    const committeeId = ensureString(record.committeeId, `worker[${index}].committeeId`);
    if (!operatorCommitteeIds.has(committeeId)) {
      throw new Error(`worker[${index}] references unknown operator committee.`);
    }
    const primaryPillar = ensureString(record.primaryPillar, `worker[${index}].primaryPillar`);
    if (!pillarIds.has(primaryPillar)) {
      throw new Error(`worker[${index}] references unknown primary pillar.`);
    }
    const secondaryPillars = ensureStringArray(record.secondaryPillars, `worker[${index}].secondaryPillars`);
    if (secondaryPillars.some((pillarId) => !pillarIds.has(pillarId))) {
      throw new Error(`worker[${index}] references unknown secondary pillar ids.`);
    }
    const escalationRuleId = ensureString(record.escalationRuleId, `worker[${index}].escalationRuleId`);
    if (!escalationRuleIds.has(escalationRuleId)) {
      throw new Error(`worker[${index}] references unknown escalation rule.`);
    }
    const intervalMinutes = Math.max(1, Math.round(ensureNumber(record.intervalMinutes, `worker[${index}].intervalMinutes`)));

    return {
      id: ensureString(record.id, `worker[${index}].id`),
      displayName: ensureString(record.displayName, `worker[${index}].displayName`),
      committeeId,
      primaryPillar,
      secondaryPillars,
      purpose: ensureString(record.purpose, `worker[${index}].purpose`),
      schedule: ensureString(record.schedule, `worker[${index}].schedule`),
      intervalMinutes,
      inputSources: ensureStringArray(record.inputSources, `worker[${index}].inputSources`),
      allowedActions: ensureStringArray(record.allowedActions, `worker[${index}].allowedActions`),
      forbiddenActions: ensureStringArray(record.forbiddenActions, `worker[${index}].forbiddenActions`),
      outputArtifact: ensureString(record.outputArtifact, `worker[${index}].outputArtifact`),
      archiveEventType: ensureString(record.archiveEventType, `worker[${index}].archiveEventType`),
      escalationRuleId,
      statusFields: ensureStringArray(record.statusFields, `worker[${index}].statusFields`),
      requiredSecrets: Array.isArray(record.requiredSecrets)
        ? ensureStringArray(record.requiredSecrets, `worker[${index}].requiredSecrets`)
        : [],
    } satisfies OperatorWorker;
  });
  ensureUniqueIds(workers, "Governance registry workers");
  return workers;
}

function validateGovernanceRegistry(candidate: unknown): GovernanceRegistry {
  const record = ensureRecord(candidate, "governanceRegistry");
  const version = ensureString(record.version, "governanceRegistry.version");
  const updatedAt = parseDate(ensureString(record.updatedAt, "governanceRegistry.updatedAt"));
  const updatedBy = ensureString(record.updatedBy, "governanceRegistry.updatedBy");
  const pillars = parsePillars(record.pillars);
  const pillarIds = new Set(pillars.map((pillar) => pillar.id));
  const committees = parseCommittees(record.committees, pillarIds);
  const committeeIds = new Set(committees.map((committee) => committee.id));
  const operatorCommittees = parseOperatorCommittees(record.operatorCommittees, pillarIds);
  const operatorCommitteeIds = new Set(operatorCommittees.map((committee) => committee.id));
  const skills = parseSkills(
    record.skills,
    pillarIds,
    committeeIds,
    new Set([...committeeIds, ...operatorCommitteeIds]),
  );
  const workflows = parseWorkflows(record.workflows, pillarIds);
  const escalationRules = parseEscalationRules(record.escalationRules, pillarIds, committeeIds);
  const escalationRuleIds = new Set(escalationRules.map((rule) => rule.id));
  const workers = parseWorkers(record.workers, pillarIds, operatorCommitteeIds, escalationRuleIds);
  const workerIds = new Set(workers.map((worker) => worker.id));
  const minimumLiveWorkerIds = ensureStringArray(record.minimumLiveWorkerIds, "governanceRegistry.minimumLiveWorkerIds");

  if (minimumLiveWorkerIds.some((workerId) => !workerIds.has(workerId))) {
    throw new Error("minimumLiveWorkerIds references unknown workers.");
  }

  for (const operatorCommittee of operatorCommittees) {
    if (operatorCommittee.workerIds.some((workerId) => !workerIds.has(workerId))) {
      throw new Error(`operatorCommittee ${operatorCommittee.id} references unknown workers.`);
    }
  }

  return {
    version,
    updatedAt,
    updatedBy,
    pillars,
    committees,
    skills,
    workflows,
    escalationRules,
    operatorCommittees,
    workers,
    minimumLiveWorkerIds,
  };
}

function governanceRegistryHash(registry: GovernanceRegistry) {
  return crypto.createHash("sha256").update(JSON.stringify(registry)).digest("hex");
}

async function persistGovernanceRegistry() {
  await ensureDataDir();
  const writes = [
    fs.writeFile(REGISTRY_FILE, JSON.stringify(governanceRegistry, null, 2), "utf8"),
    writeCompressedSnapshot(REGISTRY_SNAPSHOT_FILE, governanceRegistry),
  ];
  if (DATABASE_URL) {
    writes.unshift(writeDatabaseStore("governance_registry", governanceRegistry).then(() => undefined));
  }
  await Promise.allSettled(writes);
}

async function recordGovernanceRegistrySync(reason: string) {
  const hash = governanceRegistryHash(governanceRegistry);
  const previousHash = state.stats.lastGovernanceRegistryHash;
  const changed = previousHash !== hash;
  state.stats.lastGovernanceRegistryHash = hash;
  state.stats.lastGovernanceRegistrySyncAt = now();
  await persistState();

  if (!changed) return;

  const summary = `Governance registry ${governanceRegistry.version} synced with ${governanceRegistry.pillars.length} pillars, ${governanceRegistry.committees.length} governance committees, ${governanceRegistry.operatorCommittees.length} operator committees, ${governanceRegistry.workers.length} named workers, ${governanceRegistry.skills.length} skills, ${governanceRegistry.workflows.length} workflows, and ${governanceRegistry.escalationRules.length} escalation rules.`;
  addArchive({
    title: `Governance registry ${governanceRegistry.version}`,
    category: "policy",
    summary,
    lineage: [`registry:${hash}`],
    metadata: {
      reason,
      hash,
      previousHash,
      updatedAt: governanceRegistry.updatedAt,
      updatedBy: governanceRegistry.updatedBy,
      registry: governanceRegistry,
    },
  });
  addEvent("GOVERNANCE_REGISTRY_SYNCED", summary, "silicon-valley", {
    reason,
    hash,
    previousHash,
    version: governanceRegistry.version,
    updatedBy: governanceRegistry.updatedBy,
  });
}

async function loadGovernanceRegistry() {
  await ensureDataDir();

  try {
    const storedRegistry = await readDatabaseStore<GovernanceRegistry>("governance_registry");
    if (storedRegistry) {
      governanceRegistry = validateGovernanceRegistry(storedRegistry);
      return;
    }
  } catch {
    // file and cold-storage fallbacks remain available below
  }

  try {
    const raw = await fs.readFile(REGISTRY_FILE, "utf8");
    governanceRegistry = validateGovernanceRegistry(JSON.parse(raw));
  } catch (error) {
    const snapshotRegistry = await readCompressedSnapshot<GovernanceRegistry>(REGISTRY_SNAPSHOT_FILE);
    if (snapshotRegistry) {
      governanceRegistry = validateGovernanceRegistry(snapshotRegistry);
      return;
    }
    if ((error as NodeJS.ErrnoException)?.code === "ENOENT") {
      governanceRegistry = cloneRegistry(defaultGovernanceRegistry);
      await persistGovernanceRegistry();
      return;
    }
    throw new Error(
      `Governance registry failed validation or could not be read: ${
        error instanceof Error ? error.message : "Unknown registry error"
      }`,
    );
  }
}

function requireAdmin(req: express.Request, res: express.Response, next: express.NextFunction) {
  if (!ADMIN_API_KEY) {
    res.status(503).json({ error: "Admin registry editing is disabled until UACP_ADMIN_KEY is configured." });
    return;
  }

  const provided = req.header("x-uacp-admin-key");
  if (provided !== ADMIN_API_KEY) {
    res.status(403).json({ error: "Admin authorization failed." });
    return;
  }

  next();
}

function requireInternal(req: express.Request, res: express.Response, next: express.NextFunction) {
  if (!INTERNAL_API_KEY) {
    res.status(503).json({ error: "Internal runtime APIs are disabled until UACP_INTERNAL_API_KEY or UACP_ADMIN_KEY is configured." });
    return;
  }

  const provided = req.header("x-uacp-internal-key");
  if (provided !== INTERNAL_API_KEY) {
    res.status(403).json({ error: "Internal authorization failed." });
    return;
  }

  next();
}

function parsePositiveIntegerEnv(value: string | undefined, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function initializeRateLimitRuntime() {
  if (!UPSTASH_REDIS_REST_URL || !UPSTASH_REDIS_REST_TOKEN) {
    return {
      redis: null,
      limiters: null,
      status: buildRateLimitStatus(null),
    };
  }

  try {
    const redis = new Redis({
      url: UPSTASH_REDIS_REST_URL,
      token: UPSTASH_REDIS_REST_TOKEN,
    });

    const limiters = {
      public_mutation: {
        free: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.public_mutation.free.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.public_mutation.free.limit,
            rateLimitProfiles.public_mutation.free.window,
          ),
        }),
        paid: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.public_mutation.paid.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.public_mutation.paid.limit,
            rateLimitProfiles.public_mutation.paid.window,
          ),
        }),
      },
      heavy_mutation: {
        free: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.heavy_mutation.free.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.heavy_mutation.free.limit,
            rateLimitProfiles.heavy_mutation.free.window,
          ),
        }),
        paid: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.heavy_mutation.paid.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.heavy_mutation.paid.limit,
            rateLimitProfiles.heavy_mutation.paid.window,
          ),
        }),
      },
      refresh: {
        free: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.refresh.free.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.refresh.free.limit,
            rateLimitProfiles.refresh.free.window,
          ),
        }),
        paid: new Ratelimit({
          redis,
          analytics: true,
          prefix: rateLimitProfiles.refresh.paid.prefix,
          limiter: Ratelimit.slidingWindow(
            rateLimitProfiles.refresh.paid.limit,
            rateLimitProfiles.refresh.paid.window,
          ),
        }),
      },
    } satisfies Record<RateLimitProfile, Record<RateLimitTier, Ratelimit>>;

    return {
      redis,
      limiters,
      status: buildRateLimitStatus(null),
    };
  } catch (error) {
    return {
      redis: null,
      limiters: null,
      status: buildRateLimitStatus(error instanceof Error ? error.message : "Unknown Upstash Redis bootstrap error."),
    };
  }
}

function buildRateLimitStatus(initError: string | null): RateLimitStatus {
  return {
    enabled: Boolean(UPSTASH_REDIS_REST_URL && UPSTASH_REDIS_REST_TOKEN && !initError),
    provider: UPSTASH_REDIS_REST_URL && UPSTASH_REDIS_REST_TOKEN && !initError ? "upstash-redis" : "disabled",
    trustTierHeader: RATE_LIMIT_TRUST_ACCESS_TIER_HEADER,
    initError,
    profiles: {
      public_mutation: {
        free: { limit: rateLimitProfiles.public_mutation.free.limit, window: rateLimitProfiles.public_mutation.free.window },
        paid: { limit: rateLimitProfiles.public_mutation.paid.limit, window: rateLimitProfiles.public_mutation.paid.window },
      },
      heavy_mutation: {
        free: { limit: rateLimitProfiles.heavy_mutation.free.limit, window: rateLimitProfiles.heavy_mutation.free.window },
        paid: { limit: rateLimitProfiles.heavy_mutation.paid.limit, window: rateLimitProfiles.heavy_mutation.paid.window },
      },
      refresh: {
        free: { limit: rateLimitProfiles.refresh.free.limit, window: rateLimitProfiles.refresh.free.window },
        paid: { limit: rateLimitProfiles.refresh.paid.limit, window: rateLimitProfiles.refresh.paid.window },
      },
    },
  };
}

function requestBypassesRateLimit(req: express.Request) {
  const internalKey = req.header("x-uacp-internal-key");
  if (INTERNAL_API_KEY && internalKey === INTERNAL_API_KEY) {
    return true;
  }
  const adminKey = req.header("x-uacp-admin-key");
  return Boolean(ADMIN_API_KEY && adminKey === ADMIN_API_KEY);
}

function normalizeClientIp(req: express.Request) {
  const forwarded = String(req.header("x-forwarded-for") || "")
    .split(",")
    .map((entry) => entry.trim())
    .find(Boolean);
  const raw = forwarded || req.ip || req.socket.remoteAddress || "127.0.0.1";
  return raw.replace(/^::ffff:/, "");
}

function resolveRateLimitTier(req: express.Request): RateLimitTier {
  if (!RATE_LIMIT_TRUST_ACCESS_TIER_HEADER) {
    return "free";
  }
  const provided = String(req.header("x-uacp-access-tier") || "").trim().toLowerCase();
  return provided === "paid" ? "paid" : "free";
}

function resolveRateLimitIdentifier(req: express.Request, profile: RateLimitProfile, tier: RateLimitTier) {
  const trustedUserId = RATE_LIMIT_TRUST_ACCESS_TIER_HEADER
    ? String(req.header("x-uacp-user-id") || "").trim()
    : "";
  const identifier = trustedUserId || normalizeClientIp(req);
  return `${profile}:${tier}:${identifier}`;
}

function resolveRateLimitRate(req: express.Request) {
  const body = req.body;
  if (!body || typeof body !== "object") {
    return 1;
  }

  const candidate =
    typeof (body as Record<string, unknown>).rate === "number"
      ? Number((body as Record<string, unknown>).rate)
      : typeof (body as Record<string, unknown>).batchSize === "number"
        ? Number((body as Record<string, unknown>).batchSize)
        : Array.isArray((body as Record<string, unknown>).items)
          ? (body as { items: unknown[] }).items.length
          : 1;

  return Number.isFinite(candidate) && candidate > 0 ? Math.min(Math.floor(candidate), 1000) : 1;
}

function buildRetryAfterSeconds(reset?: number) {
  if (!Number.isFinite(reset)) return undefined;
  const retryMs = Math.max(0, Number(reset) - Date.now());
  return Math.max(1, Math.ceil(retryMs / 1000));
}

function withPublicRateLimit(profile: RateLimitProfile): express.RequestHandler {
  return async (req, res, next) => {
    if (!rateLimitRuntime.limiters || requestBypassesRateLimit(req)) {
      next();
      return;
    }

    try {
      const tier = resolveRateLimitTier(req);
      const limiter = rateLimitRuntime.limiters[profile][tier];
      const rate = resolveRateLimitRate(req);
      const identifier = resolveRateLimitIdentifier(req, profile, tier);
      const result = await limiter.limit(identifier, { rate });
      const retryAfterSeconds = buildRetryAfterSeconds(result.reset);

      if (typeof result.limit === "number") {
        res.setHeader("x-ratelimit-limit", String(result.limit));
      }
      if (typeof result.remaining === "number") {
        res.setHeader("x-ratelimit-remaining", String(result.remaining));
      }
      if (typeof result.reset === "number") {
        res.setHeader("x-ratelimit-reset", String(result.reset));
      }
      if (retryAfterSeconds !== undefined) {
        res.setHeader("retry-after", String(retryAfterSeconds));
      }
      res.setHeader("x-uacp-rate-limit-profile", profile);
      res.setHeader("x-uacp-rate-limit-tier", tier);

      if (!result.success) {
        res.status(429).json({
          error: "Rate limit exceeded.",
          message: `V5 governed runtime limit reached for ${profile}. This protects shared public infrastructure; authenticated owner/internal requests bypass this limiter.`,
          profile,
          tier,
          limit: result.limit,
          remaining: result.remaining,
          reset: result.reset,
          identifierType: RATE_LIMIT_TRUST_ACCESS_TIER_HEADER && req.header("x-uacp-user-id") ? "user" : "ip",
          retryAfterSeconds: retryAfterSeconds ?? null,
        });
        return;
      }

      next();
    } catch (error) {
      res.status(503).json({
        error: "Rate limiter unavailable.",
        detail: error instanceof Error ? error.message : "Unknown rate limiter failure.",
      });
    }
  };
}

function qstashRuntimeSnapshot() {
  return {
    enabled: Boolean(qstashClient),
    provider: qstashClient ? "upstash-qstash" : "disabled",
    baseUrlConfigured: Boolean(QSTASH_URL),
    tokenConfigured: Boolean(QSTASH_TOKEN),
    receiverVerification: Boolean(qstashReceiver),
    publicBaseUrlConfigured: Boolean(UACP_PUBLIC_BASE_URL),
    queueName: UACP_QSTASH_QUEUE_NAME,
    scheduleId: UACP_QSTASH_CONVEYOR_SCHEDULE_ID,
    scheduleCron: UACP_QSTASH_CONVEYOR_CRON,
    webhookPath: "/api/v1/qstash/worker-conveyor",
  };
}

function searchRuntimeSnapshot() {
  return {
    enabled: Boolean(searchClient),
    provider: searchClient ? "upstash-search" : "disabled",
    urlConfigured: Boolean(UPSTASH_SEARCH_REST_URL),
    tokenConfigured: Boolean(UPSTASH_SEARCH_REST_TOKEN),
    index: UACP_SEARCH_INDEX,
  };
}

function normalizeSearchDocument(candidate: unknown) {
  const record = ensureRecord(candidate, "searchDocument");
  const id = ensureString(record.id ?? record.document_id ?? record.documentId ?? createId("doc"), "searchDocument.id");
  const type = typeof record.type === "string" ? record.type.trim() : "document";
  const title = typeof record.title === "string" && record.title.trim()
    ? record.title.trim()
    : typeof record.name === "string" && record.name.trim()
      ? record.name.trim()
      : id;
  const text = typeof record.text === "string" && record.text.trim()
    ? record.text.trim()
    : typeof record.body === "string" && record.body.trim()
      ? record.body.trim()
      : typeof record.description === "string" && record.description.trim()
        ? record.description.trim()
        : title;
  const url = getPayloadString(record, ["url", "source_url", "sourceUrl"]);
  const source = getPayloadString(record, ["source", "provider"]) || "uacp";
  const tags = Array.isArray(record.tags) ? record.tags.filter((entry): entry is string => typeof entry === "string") : [];
  const metadata = record.metadata && typeof record.metadata === "object" && !Array.isArray(record.metadata)
    ? record.metadata as Record<string, unknown>
    : {};

  return {
    id,
    content: {
      title,
      text,
      type,
      source,
      url: url || "",
      tags,
    },
    metadata: {
      ...metadata,
      type,
      source,
      url: url || "",
      indexedAt: now(),
    },
  };
}

async function upsertSearchDocuments(documents: unknown[], indexName = UACP_SEARCH_INDEX) {
  const index = getSearchIndex(indexName);
  if (!index) throw new Error("Upstash Search is not configured.");
  const normalized = documents.map(normalizeSearchDocument);
  await index.upsert(normalized);
  const archive = addArchive({
    title: "Search documents indexed",
    category: "research",
    summary: `${normalized.length} document(s) indexed into Upstash Search index ${indexName}.`,
    lineage: normalized.map((document) => document.id),
    metadata: {
      index: indexName,
      documentIds: normalized.map((document) => document.id),
    },
  });
  await persistState();
  return { documents: normalized, archiveId: archive.id };
}

async function searchDocuments(query: string, limit: number, filter?: string, indexName = UACP_SEARCH_INDEX) {
  const index = getSearchIndex(indexName);
  if (!index) throw new Error("Upstash Search is not configured.");
  const results = await index.search({
    query,
    limit: Math.min(Math.max(limit, 1), 25),
    ...(filter ? { filter } : {}),
    semanticWeight: 0.5,
    inputEnrichment: true,
  });
  addEvent("UPSTASH_SEARCH_QUERY", `Upstash Search returned ${results.length} result(s).`, "deterministic-engine", {
    query,
    limit,
    filter,
    index: indexName,
  });
  await persistState();
  return results;
}

function buildQStashDestination(pathname = "/api/v1/qstash/worker-conveyor") {
  if (!UACP_PUBLIC_BASE_URL) {
    throw new Error("UACP_PUBLIC_BASE_URL is required before publishing QStash worker conveyor messages.");
  }
  return `${UACP_PUBLIC_BASE_URL}${pathname.startsWith("/") ? pathname : `/${pathname}`}`;
}

function normalizeQStashWorkerIds(value: unknown) {
  const requested = Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0).map((entry) => entry.trim())
    : [];
  const workerIds = requested.length > 0
    ? requested
    : state.workerRuntime
        .filter((runtime) => !runtime.paused && runtime.nextRunAt && new Date(runtime.nextRunAt).getTime() <= Date.now())
        .sort((left, right) => new Date(left.nextRunAt || 0).getTime() - new Date(right.nextRunAt || 0).getTime())
        .slice(0, UACP_SCHEDULER_MAX_RELEASE_PER_TICK)
        .map((runtime) => runtime.workerId);

  return uniqueStrings(workerIds).filter((workerId) => Boolean(workerById(workerId)));
}

async function verifyQStashRequest(req: express.Request) {
  if (!qstashReceiver) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("QStash receiver signing keys are not configured.");
    }
    return { verified: false, skipped: true };
  }
  const signature = req.header("upstash-signature");
  if (!signature) throw new Error("Missing upstash-signature header.");
  const rawBody = typeof (req as express.Request & { rawBody?: string }).rawBody === "string"
    ? (req as express.Request & { rawBody?: string }).rawBody || JSON.stringify(req.body ?? {})
    : JSON.stringify(req.body ?? {});
  const protocol = req.header("x-forwarded-proto") || req.protocol || "https";
  const host = req.header("x-forwarded-host") || req.header("host");
  const url = host ? `${protocol}://${host}${req.originalUrl}` : undefined;
  await qstashReceiver.verify({
    signature,
    body: rawBody,
    url,
    upstashRegion: req.header("upstash-region") || undefined,
    clockTolerance: 60,
  });
  return { verified: true, skipped: false };
}

async function publishQStashWorkerConveyor(workerIds: string[], options: { delaySeconds?: number; reason?: string } = {}) {
  if (!qstashClient) throw new Error("QStash is not configured.");
  const destination = buildQStashDestination();
  const delay = Math.max(0, Math.floor(options.delaySeconds || 0));
  const response = await qstashClient.publishJSON({
    url: destination,
    body: {
      workerIds,
      reason: options.reason || "qstash-worker-conveyor",
      publishedAt: now(),
    },
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
    retries: 3,
    delay,
    flowControl: {
      key: UACP_QSTASH_QUEUE_NAME,
      parallelism: 1,
      rate: 1,
      period: "10s",
    },
    label: "uacp-worker-conveyor",
  });
  addEvent("QSTASH_WORKER_CONVEYOR_PUBLISHED", `Published ${workerIds.length} worker release(s) to QStash.`, "silicon-valley", {
    workerIds,
    delaySeconds: delay,
    messageId: typeof response.messageId === "string" ? response.messageId : undefined,
  });
  await persistState();
  return response;
}

async function createQStashConveyorSchedule() {
  if (!qstashClient) throw new Error("QStash is not configured.");
  const destination = buildQStashDestination();
  const response = await qstashClient.schedules.create({
    scheduleId: UACP_QSTASH_CONVEYOR_SCHEDULE_ID,
    destination,
    cron: UACP_QSTASH_CONVEYOR_CRON,
    method: "POST",
    body: JSON.stringify({
      workerIds: [],
      reason: "scheduled-qstash-worker-conveyor",
    }),
    headers: {
      "Content-Type": "application/json",
    },
    retries: 3,
    flowControl: {
      key: UACP_QSTASH_QUEUE_NAME,
      parallelism: 1,
      rate: 1,
      period: "10s",
    },
    label: "uacp-worker-conveyor-schedule",
  });
  addEvent("QSTASH_WORKER_CONVEYOR_SCHEDULED", "QStash worker conveyor schedule created or updated.", "silicon-valley", {
    scheduleId: response.scheduleId,
    cron: UACP_QSTASH_CONVEYOR_CRON,
  });
  await persistState();
  return response;
}

async function refreshBackgroundResearch(reason: "startup" | "scheduled" | "manual") {
  const result = await fetchLiveResearch(DEFAULT_RESEARCH_QUERY, 3);
  state.researchSignals = result.signals;
  state.researchStatus = result.statuses;
  pushWindow(state.stats.researchRefreshDurationsMs, result.durationMs);
  state.stats.lastResearchSyncAt = now();
  captureMetricHistory();
  await persistState();

  const metadata = {
    reason,
    signalCount: result.signals.length,
    onlineSources: result.statuses.filter((status) => status.status === "online").length,
  };

  if (result.signals.length > 0) {
    addEvent("RESEARCH_REFRESHED", `Live research refresh completed with ${result.signals.length} signals.`, "deterministic-engine", metadata);
  } else {
    addEvent("RESEARCH_UNAVAILABLE", "Research refresh completed without any live signals.", "silicon-valley", metadata);
  }
}

function minutesSince(timestamp?: string) {
  if (!timestamp) return Number.POSITIVE_INFINITY;
  const parsed = new Date(timestamp).getTime();
  if (Number.isNaN(parsed)) return Number.POSITIVE_INFINITY;
  return Math.max(0, (Date.now() - parsed) / (1000 * 60));
}

function controlPlaneBootAgeMinutes() {
  return Math.max(0, (Date.now() - CONTROL_PLANE_BOOTED_AT) / (1000 * 60));
}

function inStartupPrimingWindow() {
  return controlPlaneBootAgeMinutes() <= 15;
}

function computeResearchFreshness() {
  const ageMinutes = minutesSince(state.stats.lastResearchSyncAt);
  if (!Number.isFinite(ageMinutes)) return 0.35;
  if (ageMinutes <= 15) return 1;
  if (ageMinutes <= 30) return 0.93;
  if (ageMinutes <= 60) return 0.82;
  if (ageMinutes <= 120) return 0.65;
  return 0.45;
}

function computeWorkerPriming() {
  const minimumLive = minimumLiveWorkerIds();
  if (minimumLive.length === 0) return 0.6;

  const scores = minimumLive.map((workerId) => {
    const worker = workerById(workerId);
    const runtime = state.workerRuntime.find((entry) => entry.workerId === workerId);
    if (!worker || !runtime) return 0.35;

    const freshnessWindow = Math.max(worker.intervalMinutes * 2, 45);
    const heartbeatAge = minutesSince(runtime.lastHeartbeatAt);
    const heartbeatScore = !Number.isFinite(heartbeatAge)
      ? runtime.paused
        ? 0.2
        : runtime.status === "error"
          ? 0.15
          : inStartupPrimingWindow()
            ? 0.96
            : 0.82
      : heartbeatAge <= freshnessWindow
        ? 1
        : heartbeatAge <= freshnessWindow * 2
          ? 0.7
          : 0.4;
    const statusScore =
      runtime.paused
        ? 0.2
        : runtime.status === "error"
          ? 0.15
          : runtime.status === "running"
            ? 1
            : inStartupPrimingWindow()
              ? 0.96
              : 0.9;

    return clamp((heartbeatScore * 0.55) + (statusScore * 0.45), 0, 1);
  });

  return average(scores) || 0.35;
}

function computeLatestPlanReadiness(researchReadiness: number, workerPriming: number) {
  const latestPlan = state.plans[0];
  const registryReadiness = activePillars().length > 0 && activeCommittees().length > 0 && activeWorkflows().length > 0 ? 1 : 0.4;

  if (!latestPlan) {
    return clamp(
      (registryReadiness * 0.4) + (researchReadiness * 0.35) + (workerPriming * 0.25),
      inStartupPrimingWindow() ? 0.9 : 0.82,
      0.97,
    );
  }

  const referencesScore = Math.min(1, (latestPlan.researchReferences?.length || 0) / 4);
  const governanceScore = average([
    latestPlan.guardrails.length > 0 ? 1 : 0.35,
    latestPlan.votes.length > 0 ? 1 : 0.35,
    latestPlan.committeeIds.length > 0 ? 1 : 0.35,
    latestPlan.graph.nodes.length > 0 ? 1 : 0.35,
    latestPlan.pillars.length > 0 ? 1 : 0.35,
  ]);
  const executionScore = average([
    latestPlan.workflowIds.length > 0 ? 1 : 0.4,
    latestPlan.skillIds.length > 0 ? 1 : 0.4,
    latestPlan.escalationRuleIds.length > 0 || latestPlan.riskTier === "low" ? 1 : 0.55,
  ]);
  const proposalPenalty = Math.min(0.3, (latestPlan.proposals?.length || 0) * 0.08);

  return clamp(
    (referencesScore * 0.28) + (governanceScore * 0.34) + (executionScore * 0.28) + (researchReadiness * 0.1) - proposalPenalty,
    0,
    1,
  );
}

function computeLatestRunIntegrity(planReadiness: number, sourceHealth: number, workerPriming: number) {
  const latestRun = state.runs[0];
  if (!latestRun) {
    return clamp(
      (planReadiness * 0.45) + (sourceHealth * 0.3) + (workerPriming * 0.25),
      inStartupPrimingWindow() ? 0.9 : 0.84,
      0.98,
    );
  }

  if (latestRun.status === "completed") {
    const artifactScore = latestRun.artifact ? 1 : 0.75;
    const evidenceScore = clamp((latestRun.evidenceCount || 0) / 4, 0.6, 1);
    const stageScore = clamp((latestRun.stages?.length || 0) / 5, 0.6, 1);
    return clamp((artifactScore * 0.45) + (evidenceScore * 0.3) + (stageScore * 0.25), 0, 1);
  }

  if (latestRun.status === "executing" || latestRun.status === "queued") {
    const progressScore = clamp((latestRun.progress || 0) / 100, 0.6, 0.95);
    return clamp((progressScore * 0.65) + (planReadiness * 0.35), 0, 0.96);
  }

  if (latestRun.status === "blocked") return 0.3;
  if (latestRun.status === "failed") return 0.15;
  return clamp(planReadiness * 0.75, 0.25, 0.85);
}

function computeCurrentArchiveCoverage(latestRunIntegrity: number, workerPriming: number) {
  const latestRun = state.runs[0];
  if (latestRun?.artifact) {
    const archiveLinkScore = latestRun.artifact.archiveRecordIds.length > 0 ? 1 : 0.7;
    return clamp((archiveLinkScore * 0.6) + (latestRunIntegrity * 0.4), 0, 1);
  }

  if (state.archives.length > 0) {
    return clamp(0.8 + Math.min(0.15, state.archives.length * 0.01), 0, 0.95);
  }

  if (state.plans.length > 0 || state.runs.length > 0) {
    return 0.72;
  }

  return clamp(
    (latestRunIntegrity * 0.55) + (workerPriming * 0.45),
    inStartupPrimingWindow() ? 0.9 : 0.82,
    0.95,
  );
}

function computeCurrentCommitteeHealth() {
  const latestPlan = state.plans[0];
  if (!latestPlan) {
    return activeCommittees().length > 0 ? 0.95 : 0.4;
  }

  const validAssignments = latestPlan.committeeIds.filter((committeeId) => activeCommittees().some((committee) => committee.id === committeeId)).length;
  const committeeAssignmentScore = validAssignments / Math.max(1, latestPlan.committeeIds.length);
  const voteCoverage = latestPlan.votes.length > 0 ? 1 : 0.45;
  const governanceNodeCoverage = latestPlan.graph.nodes.some((node) => node.stage === "governance") ? 1 : 0.55;
  return clamp(average([committeeAssignmentScore, voteCoverage, governanceNodeCoverage]), 0, 1);
}

function computeCurrentEscalationPenalty() {
  const latestByWorker = new Map<string, OperatorRun>();

  for (const run of state.operatorRuns) {
    const current = latestByWorker.get(run.workerId);
    const currentTime = current ? new Date(current.completedAt || current.startedAt).getTime() : 0;
    const nextTime = new Date(run.completedAt || run.startedAt).getTime();
    if (!current || nextTime > currentTime) {
      latestByWorker.set(run.workerId, run);
    }
  }

  const degradedWorkers = [...latestByWorker.values()].filter((run) => {
    if (run.status !== "escalated" && run.status !== "failed") {
      return false;
    }
    const worker = workerById(run.workerId);
    const runTime = new Date(run.completedAt || run.startedAt).getTime();
    if (Number.isFinite(runTime) && runTime < CONTROL_PLANE_BOOTED_AT) {
      return false;
    }
    const freshnessWindow = Math.max((worker?.intervalMinutes || 30) * 2, 90);
    return minutesSince(run.completedAt || run.startedAt) <= freshnessWindow;
  }).length;

  return clamp(degradedWorkers / Math.max(1, activeWorkers().length), 0, 0.35);
}

function computeTelemetrySnapshot(): TelemetrySnapshot {
  const activeRunCount = state.runs.filter((run) => run.status === "queued" || run.status === "executing").length;
  const sourceAvailability = average(
    state.researchStatus.map((status) => (
      status.status === "online" ? 1 : status.status === "degraded" ? 0.5 : 0
    )),
  ) || 0;
  const researchFreshness = computeResearchFreshness();
  const sourceHealth = clamp((sourceAvailability * 0.55) + (researchFreshness * 0.45), 0, 1);
  const workerPriming = computeWorkerPriming();
  const planReadiness = computeLatestPlanReadiness(sourceHealth, workerPriming);
  const latestRunIntegrity = computeLatestRunIntegrity(planReadiness, sourceHealth, workerPriming);
  const committeeHealth = computeCurrentCommitteeHealth();
  const archiveCoverage = computeCurrentArchiveCoverage(latestRunIntegrity, workerPriming);
  const executionPressure = clamp(
    (workerPriming * 0.35) + (planReadiness * 0.25) + (latestRunIntegrity * 0.2) + (sourceHealth * 0.2),
    0,
    1,
  );
  const latestPlan = state.plans[0];
  const complianceScore = latestPlan?.riskTier === "high"
    ? (latestPlan.pillars.includes("compliance-risk") ? 1 : 0.25)
    : 1;
  const proposalScore = latestPlan ? Math.max(0.45, 1 - ((latestPlan.proposals?.length || 0) * 0.12)) : 0.95;
  const policyAlignment = clamp(
    (planReadiness * 0.35) +
      (committeeHealth * 0.2) +
      (sourceHealth * 0.15) +
      (complianceScore * 0.15) +
      (proposalScore * 0.15),
    0,
    1,
  );
  const primeLock =
    sourceHealth >= 0.95 &&
    workerPriming >= 0.95 &&
    planReadiness >= 0.9 &&
    latestRunIntegrity >= 0.95 &&
    archiveCoverage >= 0.95 &&
    policyAlignment >= 0.95;
  const determinismScore = primeLock
    ? 0.99999
    : clamp(
      (workerPriming * 0.22) +
        (sourceHealth * 0.18) +
        (planReadiness * 0.2) +
        (latestRunIntegrity * 0.22) +
        (archiveCoverage * 0.1) +
        (committeeHealth * 0.08),
      0,
      0.99999,
    );
  const runSuccessRate = latestRunIntegrity;
  const runFailureRate = 1 - latestRunIntegrity;
  const latencyMs = Math.round(
    average([...state.stats.planCompileDurationsMs, ...state.stats.runDurationsMs, ...state.stats.researchRefreshDurationsMs].slice(-10)) || 0,
  );

  return {
    latencyMs,
    determinismScore,
    committeeHealth,
    policyAlignment,
    archiveCoverage,
    sourceHealth,
    activeRunCount,
    totalSignals: state.researchSignals.length,
    runSuccessRate,
    runFailureRate,
    researchFreshness,
    workerPriming,
    planReadiness,
    latestRunIntegrity,
    executionPressure,
    lastResearchSyncAt: state.stats.lastResearchSyncAt,
  };
}

function computeUacpPressure(telemetry: TelemetrySnapshot) {
  const archivePressure = clamp(state.archives.length / Math.max(25, activeWorkers().length * 2), 0, 1);
  const operatorThroughputPressure = clamp(state.operatorRuns.length / Math.max(50, activeWorkers().length * 4), 0, 1);
  const backendSignalPressure = clamp(state.backendEvents.length / MAX_BACKEND_EVENTS, 0, 1);
  const escalationPressure = clamp(
    state.operatorRuns.filter((run) => run.status === "escalated" || run.escalations.length > 0).length / Math.max(6, activeWorkers().length / 2),
    0,
    1,
  );
  const liveProviderPressure = providerSnapshotCache
    ? clamp(providerSnapshotCache.snapshot.statuses.filter((status) => status.health === "ready").length / 3, 0, 1)
    : 0;
  const evidencePressure = clamp(
    (archivePressure * 0.28) +
      (operatorThroughputPressure * 0.28) +
      (telemetry.workerPriming * 0.18) +
      (escalationPressure * 0.12) +
      (telemetry.sourceHealth * 0.07) +
      (liveProviderPressure * 0.09) +
      (backendSignalPressure * 0.02),
    0,
    1,
  );

  return clamp(Math.max(telemetry.executionPressure, evidencePressure), 0, 1);
}

function captureMetricHistory() {
  const telemetry = computeTelemetrySnapshot();
  const pressure = computeUacpPressure(telemetry);
  pushWindow(state.stats.determinismHistory, telemetry.determinismScore);
  pushWindow(state.stats.runCompletionHistory, telemetry.latestRunIntegrity);
  pushWindow(state.stats.policyAlignmentHistory, telemetry.policyAlignment);
  pushWindow(state.stats.archiveCoverageHistory, telemetry.archiveCoverage);
  pushWindow(state.stats.sourceHealthHistory, telemetry.sourceHealth);
  pushWindow(state.stats.pressureHistory, pressure);
}

function buildTelemetry(): ControlTelemetry {
  const telemetry = computeTelemetrySnapshot();

  return {
    latencyMs: telemetry.latencyMs,
    determinismScore: telemetry.determinismScore,
    committeeHealth: telemetry.committeeHealth,
    policyAlignment: telemetry.policyAlignment,
    archiveCoverage: telemetry.archiveCoverage,
    sourceHealth: telemetry.sourceHealth,
    activeRunCount: telemetry.activeRunCount,
    totalSignals: telemetry.totalSignals,
    lastResearchSyncAt: telemetry.lastResearchSyncAt,
    metrics: [
      { label: "Latency", value: telemetry.latencyMs, unit: "ms", trend: telemetry.latencyMs > 3000 ? "down" : "stable" },
      { label: "Certainty", value: Math.round(telemetry.determinismScore * 1000) / 10, unit: "%", trend: telemetry.determinismScore >= 0.95 ? "up" : telemetry.determinismScore >= 0.85 ? "stable" : "down" },
      { label: "Policy Alignment", value: Math.round(telemetry.policyAlignment * 1000) / 10, unit: "%", trend: telemetry.policyAlignment >= 0.95 ? "up" : telemetry.policyAlignment >= 0.85 ? "stable" : "down" },
      { label: "Run Completion", value: Math.round(telemetry.latestRunIntegrity * 1000) / 10, unit: "%", trend: telemetry.latestRunIntegrity >= 0.95 ? "up" : telemetry.latestRunIntegrity >= 0.8 ? "stable" : "down" },
      { label: "Worker Priming", value: Math.round(telemetry.workerPriming * 1000) / 10, unit: "%", trend: telemetry.workerPriming >= 0.95 ? "up" : telemetry.workerPriming >= 0.8 ? "stable" : "down" },
      { label: "Source Health", value: Math.round(telemetry.sourceHealth * 1000) / 10, unit: "%", trend: telemetry.sourceHealth >= 0.95 ? "up" : telemetry.sourceHealth >= 0.8 ? "stable" : "down" },
    ],
  };
}

function buildEngineObservability() {
  const snapshot = computeTelemetrySnapshot();
  const telemetry = buildTelemetry();
  const pressure = computeUacpPressure(snapshot);

  return {
    quantum_coherence: telemetry.determinismScore * 100,
    classical_latency: telemetry.latencyMs,
    uacp_pressure: pressure,
    gopher_policy_alignment: telemetry.policyAlignment,
    market_convergence: [
      {
        label: "Execution Priming",
        value: `${(snapshot.executionPressure * 100).toFixed(1)}%`,
        description: "Readiness across live workers, fresh research, and current plan/run state.",
        progress: clamp(snapshot.executionPressure, 0, 1),
      },
      {
        label: "Research Coverage",
        value: `${(telemetry.sourceHealth * 100).toFixed(1)}%`,
        description: "Availability and freshness of live public-source evidence.",
        progress: clamp(telemetry.sourceHealth, 0, 1),
      },
      {
        label: "Worker Priming",
        value: `${(snapshot.workerPriming * 100).toFixed(1)}%`,
        description: "Heartbeat freshness and runtime health across the minimum-live worker crew.",
        progress: clamp(snapshot.workerPriming, 0, 1),
      },
    ],
    horowitz_signals: [
      {
        id: "UACP_PRESSURE",
        value: clamp(pressure, 0, 1),
        trend: pressure >= 0.95 ? "rising" : pressure >= 0.85 ? "stable" : "falling",
        history: state.stats.pressureHistory.slice(-HISTORY_WINDOW).map((value) => clamp(value, 0, 1)),
      },
      {
        id: "COHERENCE_TRANSITION",
        value: clamp(telemetry.determinismScore, 0, 1),
        trend: telemetry.determinismScore >= 0.95 ? "rising" : telemetry.determinismScore >= 0.85 ? "stable" : "falling",
        history: state.stats.determinismHistory.slice(-HISTORY_WINDOW).map((value) => clamp(value, 0, 1)),
      },
      {
        id: "SIGNAL_NOISE",
        value: clamp(1 - telemetry.sourceHealth, 0, 1),
        trend: telemetry.sourceHealth >= 0.9 ? "falling" : telemetry.sourceHealth >= 0.75 ? "stable" : "rising",
        history: state.stats.sourceHealthHistory.slice(-HISTORY_WINDOW).map((value) => clamp(1 - value, 0, 1)),
      },
      {
        id: "RUN_COMPLETION",
        value: clamp(snapshot.latestRunIntegrity, 0, 1),
        trend: snapshot.latestRunIntegrity >= 0.95 ? "up" : snapshot.latestRunIntegrity >= 0.8 ? "stable" : "down",
        history: state.stats.runCompletionHistory.slice(-HISTORY_WINDOW).map((value) => clamp(value, 0, 1)),
      },
      {
        id: "POLICY_ALIGNMENT",
        value: clamp(telemetry.policyAlignment, 0, 1),
        trend: telemetry.policyAlignment >= 0.95 ? "up" : telemetry.policyAlignment >= 0.85 ? "stable" : "down",
        history: state.stats.policyAlignmentHistory.slice(-HISTORY_WINDOW).map((value) => clamp(value, 0, 1)),
      },
      {
        id: "EXECUTION_PRESSURE",
        value: clamp(pressure, 0, 1),
        trend: pressure >= 0.95 ? "up" : pressure >= 0.8 ? "stable" : "down",
        history: state.stats.pressureHistory.slice(-HISTORY_WINDOW).map((value) => clamp(value, 0, 1)),
      },
    ],
  };
}

function toEngineSignals(signals: ResearchSignal[]) {
  return signals.map((signal) => ({
    id: signal.id,
    title: signal.title,
    strength: signal.strength,
    timestamp: signal.publishedAt,
    category: signal.category,
  }));
}

async function synthesizeCouncilSummary(plan: InstitutionalPlan, signals: ResearchSignal[]) {
  const references = signals.slice(0, 5).map((signal, index) => `${index + 1}. ${signal.source}: ${signal.title}`).join("\n");
  try {
    const providerResult = await completeWithProviderChain([
      {
        role: "system",
        content: "You are the UACP V3 model council. Respond with concise institutional prose only.",
      },
      {
        role: "user",
        content: [
          `Plan title: ${plan.title}`,
          `Plan objective: ${plan.objective}`,
          `References:\n${references || "No live references available."}`,
          "Write a concise institutional council summary grounded in the references.",
        ].join("\n\n"),
      },
    ], {
      maxTokens: 500,
      temperature: 0.2,
    });

    if (!providerResult) {
      return signals.length > 0
        ? `Council reviewed ${signals.length} live sources and found the strongest evidence in ${uniqueStrings(signals.map((signal) => signal.source)).join(", ")}. Primary signals: ${signals.slice(0, 3).map((signal) => signal.title).join(" | ")}.`
        : "Council proceeded without live research references and elevated the plan's uncertainty.";
    }

    return trimText(providerResult.text || "", 700) || "Council summary unavailable.";
  } catch {
    return signals.length > 0
      ? `Council reviewed ${signals.length} live sources and found the strongest evidence in ${uniqueStrings(signals.map((signal) => signal.source)).join(", ")}.`
      : "Council summary unavailable because no live references were collected.";
  }
}

function evaluateGovernance(plan: InstitutionalPlan, signals: ResearchSignal[]): GovernanceEvaluation {
  const approvedSkillIds = new Set(
    activeSkills()
      .filter((skill) => skill.status === "approved")
      .map((skill) => skill.id),
  );
  const validWorkflowIds = new Set(activeWorkflows().map((workflow) => workflow.id));
  const validEscalationRuleIds = new Set(activeEscalationRules().map((rule) => rule.id));
  const skillIds = plan.skillIds.filter((skillId) => approvedSkillIds.has(skillId));
  const workflowIds = plan.workflowIds.filter((workflowId) => validWorkflowIds.has(workflowId));
  const escalationRuleIds = plan.escalationRuleIds.filter((ruleId) => validEscalationRuleIds.has(ruleId));
  const issues: string[] = [];

  if (signals.length === 0) {
    issues.push("No live research signals were available for this run.");
  }
  if (plan.proposals && plan.proposals.length > 0) {
    issues.push(`Plan carries ${plan.proposals.length} governance proposals that require founder approval before activation.`);
  }
  if (skillIds.length === 0) {
    issues.push("No approved skills matched the plan's pillar set.");
  }
  if (workflowIds.length === 0) {
    issues.push("No workflows matched the plan's pillar set.");
  }
  if (plan.escalationRuleIds.length > 0 && escalationRuleIds.length === 0) {
    issues.push("Selected escalation rules are not present in the active governance registry.");
  }
  if (plan.riskTier === "high" && !plan.pillars.includes("compliance-risk")) {
    issues.push("High-risk plan is missing the compliance / risk pillar.");
  }

  const approvals =
    plan.votes.filter((vote) => vote.vote === "approve").length +
    (signals.length > 0 ? 1 : 0) +
    (skillIds.length > 0 ? 1 : 0);

  const passed = issues.length === 0;
  const summary = passed
    ? `Governance approved the run with ${approvals} approval signals, ${skillIds.length} approved skills, and ${workflowIds.length} execution workflows.`
    : `Governance blocked the run: ${issues.join(" ")}`;

  return {
    passed,
    approvals,
    issues,
    summary: passed && escalationRuleIds.length > 0 ? `${summary} Escalation coverage includes ${escalationRuleIds.length} registry rules.` : summary,
    skillIds,
    workflowIds,
  };
}

function createArtifact(
  plan: InstitutionalPlan,
  signals: ResearchSignal[],
  governance: GovernanceEvaluation,
  phaseOutputs: CompiledArtifactPhaseOutput[],
  archiveRecordIds: string[],
): CompiledArtifact {
  const references = signals.slice(0, 8).map(toReference);
  const signalSources = uniqueStrings(signals.map((signal) => signal.source));
  const workflowIds = governance.workflowIds;
  const skillIds = governance.skillIds;

  return {
    id: createId("artifact"),
    title: plan.title,
    objective: plan.objective,
    summary: `Compiled artifact generated from ${references.length} live references across ${signalSources.join(", ") || "no online sources"}, with ${workflowIds.length} workflows and ${skillIds.length} approved skills ready for Sunnyvale execution.`,
    sourceCount: references.length,
    signalSources,
    workflowIds,
    skillIds,
    governanceSummary: governance.summary,
    nextAction: governance.passed
      ? "Open the compiled artifact in Sunnyvale, assign worker execution, and verify archive completion."
      : "Resolve governance issues before attempting another run.",
    archiveRecordIds,
    phaseOutputs,
    references,
    createdAt: now(),
  };
}

function buildRunProof(runId: string) {
  const run = state.runs.find((entry) => entry.id === runId);
  if (!run) return null;

  const plan = state.plans.find((entry) => entry.id === run.planId) || null;
  const runEvents = state.events.filter((event) => event.metadata?.runId === run.id || event.metadata?.planId === run.planId);
  const runArchives = state.archives.filter((archive) => archive.lineage.includes(run.id) || archive.lineage.includes(run.planId));
  const artifact = run.artifact || null;
  const archiveRecordIds = artifact?.archiveRecordIds || runArchives.map((archive) => archive.id);

  const inputFrame = {
    planId: run.planId,
    planIntent: plan?.intent || null,
    planTitle: plan?.title || null,
    graph: plan?.graph || null,
    committeeIds: plan?.committeeIds || [],
    workflowIds: plan?.workflowIds || [],
    skillIds: plan?.skillIds || [],
  };
  const outputFrame = {
    runOutput: run.output || null,
    artifact,
    archiveRecordIds,
  };
  const genomeFrame = {
    pillarIds: plan?.pillars || [],
    committeeIds: plan?.committeeIds || [],
    workflowIds: plan?.workflowIds || [],
    skillIds: plan?.skillIds || [],
    escalationRuleIds: plan?.escalationRuleIds || [],
    graph: plan?.graph || null,
  };
  const decisionFrame = {
    runId: run.id,
    status: run.status,
    currentStage: run.currentStage,
    approvals: run.approvals,
    evidenceCount: run.evidenceCount,
    stages: run.stages || [],
    eventHashes: runEvents.map((event) => event.recordHash).filter(Boolean),
    archiveHashes: runArchives.map((archive) => archive.recordHash).filter(Boolean),
  };

  return {
    proofId: createId("proof"),
    generatedAt: now(),
    runtime: {
      system: TOOL_NAME,
      version: "v5-proof",
      stream: {
        route: "/api/v1/internal/uacp/event-stream",
        redis_backed: eventStreamRedisBacked(),
      },
    },
    run,
    plan,
    artifact,
    archives: runArchives,
    events: runEvents,
    hashes: {
      inputHash: sha256Hex(inputFrame),
      outputHash: sha256Hex(outputFrame),
      genomeHash: sha256Hex(genomeFrame),
      decisionFrameHash: sha256Hex(decisionFrame),
      artifactHash: artifact ? sha256Hex(artifact) : null,
      runHash: sha256Hex(run),
      planHash: plan ? sha256Hex(plan) : null,
    },
  };
}

function buildStatusPageSnapshot(providerSnapshot: ModelProviderSnapshot): StatusPageSnapshot {
  const telemetry = buildTelemetry();
  const terminalRuns = state.runs.filter((run) => ["completed", "blocked", "failed"].includes(run.status));
  const completedRuns = state.runs.filter((run) => run.status === "completed");
  const failedOrBlockedRuns = state.runs.filter((run) => run.status === "failed" || run.status === "blocked");
  const archiveProofCoverage = state.runs.length === 0
    ? 1
    : completedRuns.filter((run) => run.artifact && run.artifact.archiveRecordIds.length > 0).length / Math.max(1, completedRuns.length || state.runs.length);
  const runSuccessRate = terminalRuns.length === 0 ? 1 : completedRuns.length / terminalRuns.length;
  const criticalEvents = state.events.filter((event) => /FAILED|BLOCKED|CRITICAL|ERROR|UNAVAILABLE|ESCALATED/.test(event.type));
  const recentCriticalEvents = criticalEvents.filter((event) => Date.now() - new Date(event.timestamp).getTime() <= 14 * 24 * 60 * 60 * 1000);
  const providerReadyCount = providerSnapshot.statuses.filter((status) => status.health === "ready").length;
  const providerConfiguredCount = providerSnapshot.statuses.filter((status) => status.configured).length;
  const serviceStatus: StatusPageSnapshot["service"]["status"] = failedOrBlockedRuns.some((run) => !run.completedAt || Date.now() - new Date(run.completedAt).getTime() < 60 * 60 * 1000)
    ? "incident"
    : recentCriticalEvents.length > 0 || providerReadyCount === 0 || storageRuntime.connected === false
      ? "degraded"
      : "operational";

  const history = Array.from({ length: 14 }, (_, index) => {
    const day = new Date(Date.now() - (13 - index) * 24 * 60 * 60 * 1000);
    const date = day.toISOString().slice(0, 10);
    const dayEvents = criticalEvents.filter((event) => event.timestamp.slice(0, 10) === date);
    const dayRuns = state.runs.filter((run) => run.startedAt.slice(0, 10) === date);
    const dayArchives = state.archives.filter((archive) => archive.createdAt.slice(0, 10) === date);
    const status: "operational" | "degraded" | "incident" = dayEvents.some((event) => /FAILED|CRITICAL|ERROR/.test(event.type))
      ? "incident"
      : dayEvents.length > 0
        ? "degraded"
        : "operational";
    return {
      date,
      status,
      incidentCount: dayEvents.length,
      runCount: dayRuns.length,
      archiveCount: dayArchives.length,
    };
  });

  const incidents = recentCriticalEvents.slice(0, 20).map((event) => ({
    id: event.id,
    type: event.type,
    status: event.type.includes("FAILED") || event.type.includes("BLOCKED") ? "resolved" as const : "monitoring" as const,
    severity: /FAILED|CRITICAL|ERROR/.test(event.type) ? "critical" as const : "warning" as const,
    title: event.type.replace(/_/g, " "),
    summary: event.message,
    startedAt: event.timestamp,
    resolvedAt: event.type.includes("FAILED") || event.type.includes("BLOCKED") ? event.timestamp : undefined,
    evidenceRefs: [
      ...(typeof event.metadata?.runId === "string" ? [event.metadata.runId] : []),
      ...(typeof event.metadata?.planId === "string" ? [event.metadata.planId] : []),
    ],
  }));

  return {
    generatedAt: now(),
    service: {
      name: "Veklom UACP Control Plane",
      status: serviceStatus,
      uptimeObservedSeconds: Math.floor((Date.now() - CONTROL_PLANE_BOOTED_AT) / 1000),
      publicUrl: UACP_PUBLIC_BASE_URL || undefined,
    },
    stats: {
      observedUptimePercent: history.length === 0 ? 100 : Number(((history.filter((day) => day.status !== "incident").length / history.length) * 100).toFixed(2)),
      runSuccessRate: Number((runSuccessRate * 100).toFixed(2)),
      archiveProofCoverage: Number((archiveProofCoverage * 100).toFixed(2)),
      policyAlignment: Number((telemetry.policyAlignment * 100).toFixed(2)),
      determinismScore: Number((telemetry.determinismScore * 100).toFixed(2)),
      activeRunCount: state.runs.filter((run) => run.status === "queued" || run.status === "executing").length,
      totalRuns: state.runs.length,
      completedRuns: completedRuns.length,
      incidentCount14d: recentCriticalEvents.length,
      evidenceExports: state.backendSummary.evidenceExports,
      providerReadyCount,
      providerConfiguredCount,
      redisBackedEventStream: eventStreamRedisBacked(),
    },
    components: [
      {
        id: "control-plane",
        name: "Control Plane API",
        status: serviceStatus === "incident" ? "incident" : "operational",
        detail: `HTTP server bound to 0.0.0.0:${PORT}.`,
      },
      {
        id: "event-stream",
        name: "Realtime Event Stream",
        status: eventStreamRedisBacked() ? "operational" : "degraded",
        detail: eventStreamRedisBacked() ? "Redis-backed stream frames are enabled." : "SSE is live; Redis stream persistence is waiting for Upstash Redis env.",
      },
      {
        id: "proof-archive",
        name: "Proof Archive",
        status: archiveProofCoverage >= 0.95 ? "operational" : archiveProofCoverage > 0 ? "degraded" : "incident",
        detail: `${Math.round(archiveProofCoverage * 100)}% of completed runs have archive-backed artifacts.`,
      },
      {
        id: "model-routing",
        name: "Model Routing",
        status: providerReadyCount > 0 ? "operational" : "degraded",
        detail: `${providerReadyCount}/${providerSnapshot.statuses.length} providers ready.`,
      },
      {
        id: "storage",
        name: "State Storage",
        status: storageRuntime.connected || storageRuntime.provider === "file" ? "operational" : "degraded",
        detail: `${storageRuntime.provider} mode: ${storageRuntime.mode}.`,
      },
      {
        id: "research-ingest",
        name: "Research Ingest",
        status: state.researchStatus.some((source) => source.status === "online") ? "operational" : "degraded",
        detail: `${state.researchSignals.length} research signals currently retained.`,
      },
    ],
    history,
    incidents,
  };
}

async function advanceRunStage(
  run: GovernedRun,
  plan: InstitutionalPlan,
  index: number,
  totalStages: number,
  stage: string,
  summary: string,
  sourceCount?: number,
) {
  const startedAt = now();
  run.status = "executing";
  run.currentStage = stage;
  run.progress = Math.round(((index + 1) / totalStages) * 100);
  const record: RunStageRecord = {
    stage,
    status: "completed",
    startedAt,
    completedAt: now(),
    summary: trimText(summary, 280),
    sourceCount,
  };
  run.stages = [...(run.stages || []), record];
  addEvent("RUN_STAGE", `${run.id} advanced to ${stage}.`, "sunnyvale", { runId: run.id, planId: plan.id, summary: record.summary });
  broadcast({ type: "run_update", data: run });
  captureMetricHistory();
  await persistState();
}

async function executeRun(runId: string) {
  const run = state.runs.find((item) => item.id === runId);
  if (!run) return;
  const plan = state.plans.find((item) => item.id === run.planId);
  if (!plan) return;

  const runStartedAt = Date.now();
  const phaseOutputs: CompiledArtifactPhaseOutput[] = [];
  const archiveRecordIds: string[] = [];

  try {
    await advanceRunStage(run, plan, 0, 5, "Intent Intake", "Founder objective normalized into a governed execution contract.");
    phaseOutputs.push({ stage: "Intent Intake", summary: "Founder objective normalized into a governed execution contract." });

    const researchContext = await fetchLiveResearch(plan.researchQuery || buildResearchQuery(plan.intent), 4);
    if (researchContext.signals.length > 0) {
      state.researchSignals = researchContext.signals;
      state.researchStatus = researchContext.statuses;
      pushWindow(state.stats.researchRefreshDurationsMs, researchContext.durationMs);
      state.stats.lastResearchSyncAt = now();
    }
    const councilSummary = await synthesizeCouncilSummary(plan, researchContext.signals);
    await advanceRunStage(run, plan, 1, 5, "Model Council", councilSummary, researchContext.signals.length);
    phaseOutputs.push({ stage: "Model Council", summary: councilSummary });

    const governance = evaluateGovernance(plan, researchContext.signals);
    run.approvals = governance.approvals;
    await advanceRunStage(run, plan, 2, 5, "Governance Gate", governance.summary, researchContext.signals.length);
    phaseOutputs.push({ stage: "Governance Gate", summary: governance.summary });

    if (!governance.passed) {
      run.status = "blocked";
      run.currentStage = "Governance Blocked";
      run.errors = governance.issues;
      run.output = governance.summary;
      plan.status = "review";
      addArchive({
        title: `${plan.title} blocked governance packet`,
        category: "policy",
        summary: governance.summary,
        lineage: [plan.id, run.id],
        metadata: { issues: governance.issues },
      });
      addEvent("RUN_BLOCKED", `${run.id} blocked by governance.`, "silicon-valley", { runId: run.id, planId: plan.id, issues: governance.issues });
      broadcast({ type: "run_update", data: run });
      captureMetricHistory();
      await persistState();
      return;
    }

    const executionSummary = `Execution assembled ${governance.workflowIds.length} workflows and ${governance.skillIds.length} approved skills for the plan.`;
    await advanceRunStage(run, plan, 3, 5, "Sunnyvale Run", executionSummary, researchContext.signals.length);
    phaseOutputs.push({ stage: "Sunnyvale Run", summary: executionSummary });

    const artifact = createArtifact(plan, researchContext.signals, governance, phaseOutputs, archiveRecordIds);
    const archive = addArchive({
      title: `${plan.title} compiled artifact`,
      category: "run",
      summary: artifact.summary,
      lineage: [plan.id, run.id, artifact.id],
      metadata: { artifact },
    });
    archiveRecordIds.push(archive.id);

    const archiveSummary = `Archive committed ${archive.id} with ${artifact.references.length} live references and ${artifact.phaseOutputs.length} phase outputs.`;
    await advanceRunStage(run, plan, 4, 5, "Archive Commit", archiveSummary, artifact.references.length);
    phaseOutputs.push({ stage: "Archive Commit", summary: archiveSummary });

    artifact.archiveRecordIds = archiveRecordIds;
    artifact.phaseOutputs = phaseOutputs;
    run.status = "completed";
    run.currentStage = "Autonomous Continuity";
    run.completedAt = now();
    run.evidenceCount = artifact.references.length + archiveRecordIds.length;
    run.artifact = artifact;
    run.output = artifact.summary;
    plan.status = "completed";

    pushWindow(state.stats.runDurationsMs, Date.now() - runStartedAt);
    addEvent("RUN_COMPLETED", `${run.id} completed with compiled artifact ${artifact.id}.`, "archives", {
      runId: run.id,
      planId: plan.id,
      artifactId: artifact.id,
    });
    broadcast({ type: "run_update", data: run });
    captureMetricHistory();
    await persistState();
  } catch (error) {
    run.status = "failed";
    run.currentStage = "Execution Failed";
    run.completedAt = now();
    run.errors = [error instanceof Error ? error.message : "Unknown execution failure"];
    run.output = "Run failed before a compiled artifact could be committed.";
    plan.status = "review";
    addEvent("RUN_FAILED", `${run.id} failed during execution.`, "archives", {
      runId: run.id,
      planId: plan.id,
      errors: run.errors,
    });
    broadcast({ type: "run_update", data: run });
    captureMetricHistory();
    await persistState();
  }
}

async function startServer() {
  validateV3ReferenceData();
  await loadGovernanceRegistry();
  await loadState();
  await recordGovernanceRegistrySync("startup");
  const providerSnapshot = await getProviderSnapshot(true);
  logStartupContext(providerSnapshot);
  if (state.stats.determinismHistory.length === 0) {
    captureMetricHistory();
    await persistState();
  }
  await refreshBackgroundResearch("startup");
  await operatorSchedulerTick();
  setInterval(() => {
    void refreshBackgroundResearch("scheduled");
  }, RESEARCH_REFRESH_INTERVAL_MS);
  setInterval(() => {
    void operatorSchedulerTick();
  }, OPERATOR_TICK_INTERVAL_MS);

  const app = express();
  const httpServer = createServer(app);
  const wss = new WebSocketServer({ server: httpServer });

  app.set("trust proxy", true);
  app.use(cors());
  app.use(express.json({
    limit: "1mb",
    verify: (req, _res, buf) => {
      (req as express.Request & { rawBody?: string }).rawBody = buf.toString("utf8");
    },
  }));

  wss.on("connection", (ws) => {
    clients.add(ws);
    ws.send(JSON.stringify({ type: "init", message: "UACP V3 control plane online" }));
    ws.on("close", () => clients.delete(ws));
  });

  app.get("/api/bootstrap", (_req, res) => {
    const payload: BootstrapPayload = {
      system: "UACP V3",
      version: "3.1.0",
      thesis: "Institutional control plane for governed AI-native operations with live public-source evidence.",
      surfaces,
      doctrines: [
        "Plans are promises, not prompts.",
        "Governance is distinct from execution.",
        "Skills are governed execution artifacts.",
        "Archives preserve replayable judgment.",
      ],
      status: "operational",
      identity: "UACP-V3",
      userEmail: process.env.USER_EMAIL || "FOUNDER",
    };
    res.json(payload);
  });

  app.get("/api/health", async (_req, res) => {
    res.json({
      ok: true,
      system: "UACP V3",
      runtime: {
        boxName: BOX_NAME,
        mode: RUNTIME_MODE,
        workerGroup: WORKER_GROUP,
        archiveWriteRequired: ARCHIVE_WRITE_REQUIRED,
        schedulerEnabled: true,
        dataDir: DATA_DIR,
        storage: {
          ...storageRuntime,
          coldStorageDir: COLD_STORAGE_DIR,
        },
        topology: buildBoxTopologySnapshot().current,
        auditChain: {
          eventHeadHash: latestEventHash() || null,
          archiveHeadHash: latestArchiveHash() || null,
        },
        backendBridge: {
          enabled: Boolean(UACP_BACKEND_BASE_URL && INTERNAL_API_KEY),
          baseUrlConfigured: Boolean(UACP_BACKEND_BASE_URL),
          internalKeyConfigured: Boolean(INTERNAL_API_KEY),
        },
        rateLimit: rateLimitRuntime.status,
        qstash: qstashRuntimeSnapshot(),
        search: searchRuntimeSnapshot(),
        outbound: buildOutboundRuntimeSnapshot(),
      },
      registry: {
        version: governanceRegistry.version,
        updatedAt: governanceRegistry.updatedAt,
        workerCount: activeWorkers().length,
        minimumLiveWorkerCount: minimumLiveWorkerIds().length,
      },
      providers: await getProviderSnapshot(),
      verification: {
        bootstrap: "/api/bootstrap",
        operators: "/api/v1/internal/operators",
        operatorRuns: "/api/v1/internal/operators/runs",
        internalAuthRequired: Boolean(INTERNAL_API_KEY),
      },
    });
  });

  app.get("/api/governance-registry", (_req, res) => res.json(governanceRegistry));
  app.get("/api/pillars", (_req, res) => res.json(activePillars()));
  app.get("/api/committees", (_req, res) => res.json(activeCommittees()));
  app.get("/api/operator-committees", (_req, res) => res.json(activeOperatorCommittees()));
  app.get("/api/operator-committees/runtime", (_req, res) => {
    res.json({
      activeExecutionWindow: activeExecutionWindow(),
      committees: activeOperatorCommittees().map((committee) => buildOperatorCommitteeRuntimeView(committee)),
    });
  });
  app.get("/api/operators", (_req, res) => res.json(activeWorkers()));
  app.get("/api/operator-runtime", (_req, res) => res.json(state.workerRuntime));
  app.get("/api/operator-runs", (_req, res) => res.json(state.operatorRuns));
  app.get("/api/skills", (_req, res) => res.json(activeSkills()));
  app.get("/api/enterprise-councils", (_req, res) => res.json(buildEnterpriseCouncils()));
  app.get("/api/enterprise-skills", (_req, res) => res.json(buildEnterpriseSkills()));
  app.get("/api/canonical-plans", (_req, res) => res.json(canonicalPlanTemplates));
  app.get("/api/v3/enterprise-checks", (_req, res) => res.json(buildEnterpriseChecks()));
  app.get("/api/v3/governance-backbone", (_req, res) => res.json(buildGovernanceBackbone()));
  app.get("/api/workflows", (_req, res) => res.json(activeWorkflows()));
  app.get("/api/escalation-rules", (_req, res) => res.json(activeEscalationRules()));
  app.get("/api/backend-summary", (_req, res) => res.json(state.backendSummary));
  app.get("/api/backend-events", (_req, res) => res.json(state.backendEvents));
  app.get("/api/command-center", (_req, res) => res.json(buildCommandCenterSnapshot()));
  app.get("/api/box-topology", (_req, res) => res.json(buildBoxTopologySnapshot()));
  app.get("/api/sunnyvale-internal", async (_req, res) => res.json(await buildSunnyvaleInternalSnapshot()));
  app.get("/api/research-signals", (_req, res) => res.json(state.researchSignals));
  app.get("/api/research-status", (_req, res) => res.json(state.researchStatus));
  app.get("/api/provider-readiness", async (_req, res) => res.json(await getProviderSnapshot()));
  app.get("/api/outbound/runtime", (_req, res) => res.json(buildOutboundRuntimeSnapshot()));
  app.get("/api/qstash/runtime", (_req, res) => res.json(qstashRuntimeSnapshot()));
  app.get("/api/search/runtime", (_req, res) => res.json(searchRuntimeSnapshot()));
  app.post("/api/v1/internal/search/documents", requireInternal, async (req, res) => {
    try {
      const body = ensureRecord(req.body, "searchIndexRequest");
      const rawDocuments = Array.isArray(body.documents) ? body.documents : [body.document ?? body];
      if (rawDocuments.length === 0) {
        res.status(400).json({ error: "At least one search document is required." });
        return;
      }
      const indexName = typeof body.index === "string" && body.index.trim() ? body.index.trim() : UACP_SEARCH_INDEX;
      const result = await upsertSearchDocuments(rawDocuments, indexName);
      res.status(201).json({
        index: indexName,
        indexed: result.documents.length,
        documentIds: result.documents.map((document) => document.id),
        archiveId: result.archiveId,
        runtime: searchRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to index search documents." });
    }
  });
  app.post("/api/v1/internal/search/query", requireInternal, async (req, res) => {
    try {
      const body = ensureRecord(req.body, "searchQueryRequest");
      const query = ensureString(body.query, "searchQueryRequest.query");
      const limit = typeof body.limit === "number" ? body.limit : 10;
      const filter = typeof body.filter === "string" && body.filter.trim() ? body.filter.trim() : undefined;
      const indexName = typeof body.index === "string" && body.index.trim() ? body.index.trim() : UACP_SEARCH_INDEX;
      const results = await searchDocuments(query, limit, filter, indexName);
      res.json({
        index: indexName,
        query,
        count: results.length,
        results,
        runtime: searchRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to query search documents." });
    }
  });
  app.get("/api/v1/internal/outbound/contacts", requireInternal, (_req, res) => res.json(state.outboundContacts));
  app.get("/api/v1/internal/outbound/messages", requireInternal, (_req, res) => res.json(state.outboundMessages));
  app.post("/api/v1/internal/outbound/contacts", requireInternal, async (req, res) => {
    try {
      const body = ensureRecord(req.body, "outboundContactRequest");
      const rawContacts = Array.isArray(body.contacts) ? body.contacts : [body.contact ?? body];
      if (rawContacts.length === 0) {
        res.status(400).json({ error: "At least one outbound contact is required." });
        return;
      }

      const results = rawContacts.map((contact) => enqueueOutboundContactFromPayload(contact, "internal-api"));
      const release = body.release === true || body.send_now === true || body.sendNow === true;
      const assignedWorkers = uniqueStrings(results.map((result) => result.contact.assignedWorkerId));
      const releasedRuns = [];
      if (release) {
        for (const workerId of assignedWorkers) {
          try {
            releasedRuns.push(queueOperatorRun(workerId, "manual", "outbound-contact-release"));
          } catch (error) {
            addEvent("OUTBOUND_RELEASE_SKIPPED", `Outbound release skipped for ${workerId}.`, "silicon-valley", {
              workerId,
              reason: error instanceof Error ? error.message : "Unknown release failure.",
            });
          }
        }
      }

      await persistState();
      res.status(201).json({
        contacts: results.map((result) => result.contact),
        archiveIds: results.map((result) => result.archiveId),
        releasedRunIds: releasedRuns.map((run) => run.id),
        outbound: buildOutboundRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to queue outbound contact." });
    }
  });
  app.post("/api/v1/internal/outbound/release", requireInternal, async (req, res) => {
    try {
      const body = req.body && typeof req.body === "object" && !Array.isArray(req.body) ? req.body as Record<string, unknown> : {};
      const requestedWorkers = Array.isArray(body.workerIds)
        ? body.workerIds.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0)
        : [];
      const workerIds = requestedWorkers.length > 0 ? requestedWorkers : ["welcome", "vendor-recruiter"];
      const releasedRuns = [];
      for (const workerId of uniqueStrings(workerIds)) {
        const worker = workerById(workerId);
        if (!worker || !["welcome", "vendor-recruiter"].includes(worker.id)) {
          throw new Error(`Worker ${workerId} is not allowed to execute outbound release.`);
        }
        if (queuedContactsForWorker(worker.id).length === 0) continue;
        try {
          releasedRuns.push(queueOperatorRun(worker.id, "manual", "outbound-release"));
        } catch (error) {
          addEvent("OUTBOUND_RELEASE_SKIPPED", `Outbound release skipped for ${worker.id}.`, "silicon-valley", {
            workerId: worker.id,
            reason: error instanceof Error ? error.message : "Unknown release failure.",
          });
        }
      }
      await persistState();
      res.json({
        releasedRunIds: releasedRuns.map((run) => run.id),
        outbound: buildOutboundRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to release outbound queue." });
    }
  });
  app.post("/api/v1/internal/qstash/worker-conveyor/publish", requireInternal, async (req, res) => {
    try {
      const body = req.body && typeof req.body === "object" && !Array.isArray(req.body) ? req.body as Record<string, unknown> : {};
      const workerIds = normalizeQStashWorkerIds(body.workerIds);
      if (workerIds.length === 0) {
        res.status(400).json({ error: "No due or requested workers are available for QStash release." });
        return;
      }
      const delaySeconds = typeof body.delaySeconds === "number" ? body.delaySeconds : typeof body.delay_seconds === "number" ? body.delay_seconds : 0;
      const response = await publishQStashWorkerConveyor(workerIds, {
        delaySeconds,
        reason: typeof body.reason === "string" ? body.reason : "manual-qstash-worker-conveyor",
      });
      res.status(202).json({
        workerIds,
        qstash: response,
        runtime: qstashRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to publish QStash worker conveyor message." });
    }
  });
  app.post("/api/v1/internal/qstash/worker-conveyor/schedule", requireInternal, async (_req, res) => {
    try {
      const response = await createQStashConveyorSchedule();
      res.status(201).json({
        schedule: response,
        runtime: qstashRuntimeSnapshot(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to create QStash worker conveyor schedule." });
    }
  });
  app.post("/api/v1/qstash/worker-conveyor", async (req, res) => {
    try {
      const verification = await verifyQStashRequest(req);
      const body = req.body && typeof req.body === "object" && !Array.isArray(req.body) ? req.body as Record<string, unknown> : {};
      const workerIds = normalizeQStashWorkerIds(body.workerIds);
      const releasedRuns = [];
      for (const workerId of workerIds) {
        try {
          releasedRuns.push(queueOperatorRun(workerId, "scheduled", typeof body.reason === "string" ? body.reason : "qstash-worker-conveyor"));
        } catch (error) {
          addEvent("QSTASH_WORKER_RELEASE_SKIPPED", `QStash worker release skipped for ${workerId}.`, "silicon-valley", {
            workerId,
            reason: error instanceof Error ? error.message : "Unknown QStash release failure.",
          });
        }
      }
      await persistState();
      res.json({
        ok: true,
        verification,
        workerIds,
        releasedRunIds: releasedRuns.map((run) => run.id),
      });
    } catch (error) {
      res.status(401).json({ error: error instanceof Error ? error.message : "Invalid QStash worker conveyor request." });
    }
  });
  app.get("/api/ssrn-signals", (_req, res) => res.json(toEngineSignals(state.researchSignals)));
  app.get("/api/v1/internal/uacp/event-stream", (req, res) => {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });

    const initEnvelope = buildEventStreamEnvelope({
      type: "stream_init",
      data: {
        redis_backed: eventStreamRedisBacked(),
        recentEvents: state.events.slice(0, 20),
        recentRuns: state.runs.slice(0, 10),
        recentArchives: state.archives.slice(0, 10),
      },
    });
    sendEventStreamFrame(res, initEnvelope);
    eventStreamClients.add(res);

    const heartbeat = setInterval(() => {
      sendEventStreamFrame(res, buildEventStreamEnvelope({ type: "heartbeat", data: { at: now() } }));
    }, 25000);

    req.on("close", () => {
      clearInterval(heartbeat);
      eventStreamClients.delete(res);
      res.end();
    });
  });
  app.get("/api/plans", (_req, res) => res.json(state.plans));
  app.get("/api/runs", (_req, res) => res.json(state.runs));
  app.get("/api/events", (_req, res) => res.json(state.events));
  app.get("/api/archives", (_req, res) => res.json(state.archives));
  app.get("/api/v3/pillars", (_req, res) => res.json(veklomPillars));
  app.get("/api/v3/committees", (_req, res) => res.json(veklomCommittees));
  app.get("/api/v3/workers", (_req, res) => res.json(veklomWorkers));
  app.get("/api/registry/workers", (_req, res) => {
    res.json(veklomWorkers.map((worker) => buildWorkerRegistryRecord(worker)));
  });
  app.get("/api/registry/workers/:worker_id", (req, res) => {
    const workerId = String(req.params.worker_id || "");
    const worker = getV3Worker(workerId);
    if (!worker) {
      res.status(404).json({ error: "Worker registry record not found." });
      return;
    }
    const plan = getLatestPlanForWorker(worker.id);
    res.json({
      record: buildWorkerRegistryRecord(worker),
      validation: buildWorkerRegistryValidation(worker, plan),
    });
  });
  app.get("/api/v3/skills", (_req, res) => res.json(veklomSkills));
  app.get("/api/v3/archives", (_req, res) => res.json(state.v3Archives));
  app.get("/api/v3/commercial-artifacts", (_req, res) => {
    res.json(state.v3CommercialArtifacts.map((artifact) => buildCommercialArtifactView(artifact.id)));
  });
  app.get("/api/v3/commercial-artifacts/:id", (req, res) => {
    try {
      res.json(buildCommercialArtifactView(String(req.params.id || "")));
    } catch (error) {
      res.status(404).json({ error: error instanceof Error ? error.message : "Commercial artifact not found." });
    }
  });
  app.get("/api/v3/commercial-scorecard", (_req, res) => {
    refreshCommercialScorecard();
    res.json(state.v3CommercialScorecard);
  });
  app.post("/api/v3/commercial-artifacts/:id/replay", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body || {}, "commercialReplayRequest");
      const requestedBy = typeof body.requestedBy === "string" && body.requestedBy.trim().length > 0
        ? body.requestedBy.trim()
        : (process.env.USER_EMAIL || "founder");
      const mode = (typeof body.mode === "string" ? body.mode : "audit_only") as ReplayRequest["mode"];
      const reason = ensureString(body.reason || "Commercial replay proof check requested.", "commercialReplayRequest.reason");
      const result = createReplayForCommercialArtifact(String(req.params.id || ""), requestedBy, mode, reason);
      await persistState();
      res.status(201).json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to replay commercial artifact." });
    }
  });
  app.post("/api/v3/commercial-copy/homepage", withPublicRateLimit("public_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "homepageCopyRequest");
      const sourceArtifactId = ensureString(body.sourceArtifactId, "homepageCopyRequest.sourceArtifactId");
      const artifact = generateHomepageCopyArtifact(sourceArtifactId);
      await persistState();
      res.status(201).json(buildCommercialArtifactView(artifact.id));
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to generate homepage copy artifact." });
    }
  });
  app.post("/api/v3/commercial-copy/outreach", withPublicRateLimit("public_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "outreachCopyRequest");
      const sourceArtifactId = ensureString(body.sourceArtifactId, "outreachCopyRequest.sourceArtifactId");
      const artifact = generateOutreachCopyArtifact(sourceArtifactId);
      await persistState();
      res.status(201).json(buildCommercialArtifactView(artifact.id));
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to generate outreach copy artifact." });
    }
  });
  app.get("/api/v3/runs/:id/events", (req, res) => {
    const runId = String(req.params.id || "");
    const run = state.v3Runs.find((entry) => entry.id === runId);
    if (!run) {
      res.status(404).json({ error: "V3 run not found." });
      return;
    }
    res.json(state.v3Events.filter((event) => event.runId === runId));
  });
  app.get("/api/v3/inspection/:runId", (req, res) => {
    try {
      res.json(buildV3InspectionView(String(req.params.runId || "")));
    } catch (error) {
      res.status(404).json({ error: error instanceof Error ? error.message : "Inspection view unavailable." });
    }
  });
  app.get("/api/runs/:runId/proof", (req, res) => {
    const proof = buildRunProof(String(req.params.runId || ""));
    if (!proof) {
      res.status(404).json({ error: "Run proof not found." });
      return;
    }
    res.json(proof);
  });
  app.get("/api/runs/:runId/proof/export", (req, res) => {
    const proof = buildRunProof(String(req.params.runId || ""));
    if (!proof) {
      res.status(404).json({ error: "Run proof not found." });
      return;
    }
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Content-Disposition", `attachment; filename="${proof.run.id}-veklom-run-proof.json"`);
    res.send(JSON.stringify(proof, null, 2));
  });
  app.get("/api/status-page", async (_req, res) => {
    res.json(buildStatusPageSnapshot(await getProviderSnapshot(false)));
  });
  app.get("/api/telemetry", (_req, res) => res.json(buildTelemetry()));
  app.get("/api/observability/signals", (_req, res) => res.json(buildEngineObservability()));

  app.post("/api/research-refresh", withPublicRateLimit("refresh"), async (_req, res) => {
    await refreshBackgroundResearch("manual");
    res.json({ ok: true, signalCount: state.researchSignals.length });
  });

  app.put("/api/governance-registry", requireAdmin, async (req, res) => {
    try {
      const candidate = ensureRecord(req.body, "governanceRegistryUpdate");
      const nextRegistry = validateGovernanceRegistry({
        ...candidate,
        updatedAt: now(),
        updatedBy: req.header("x-uacp-admin-actor") || process.env.USER_EMAIL || "admin-api",
      });
      governanceRegistry = nextRegistry;
      syncWorkerRuntimeState();
      await persistGovernanceRegistry();
      await recordGovernanceRegistrySync("admin-update");
      await persistState();
      res.json(governanceRegistry);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid governance registry." });
    }
  });

  app.get("/api/v1/internal/operators", requireInternal, (_req, res) => {
    const response = activeWorkers().map((worker) => ({
      ...worker,
      runtime: state.workerRuntime.find((runtime) => runtime.workerId === worker.id) || makeWorkerRuntime(worker),
    }));
    res.json(response);
  });

  app.get("/api/v1/internal/operators/runs", requireInternal, (_req, res) => res.json(state.operatorRuns));

  app.post("/api/v1/internal/operators/:workerId/run", requireInternal, async (req, res) => {
    try {
      const run = queueOperatorRun(String(req.params.workerId || ""), "manual", "manual-trigger");
      await persistState();
      res.status(202).json(run);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to queue operator run." });
    }
  });

  app.get("/api/v1/internal/operators/:workerId/runs", requireInternal, (req, res) => {
    const workerId = String(req.params.workerId || "");
    res.json(state.operatorRuns.filter((run) => run.workerId === workerId));
  });

  app.get("/api/v1/internal/operators/:workerId/evidence", requireInternal, (req, res) => {
    const workerId = String(req.params.workerId || "");
    const archives = state.archives.filter((archive) => archive.metadata && (archive.metadata as Record<string, unknown>).workerId === workerId);
    res.json(archives);
  });

  app.post("/api/v1/internal/operators/:workerId/pause", requireInternal, async (req, res) => {
    const workerId = String(req.params.workerId || "");
    const worker = workerById(workerId);
    if (!worker) {
      res.status(404).json({ error: "Worker not found." });
      return;
    }
    setWorkerRuntime(workerId, { status: "paused", paused: true, lastHeartbeatAt: now(), nextRunAt: undefined });
    addEvent("WORKER_PAUSED", `${worker.displayName} was paused.`, "silicon-valley", { workerId });
    await persistState();
    res.json(state.workerRuntime.find((runtime) => runtime.workerId === workerId));
  });

  app.post("/api/v1/internal/operators/:workerId/resume", requireInternal, async (req, res) => {
    const workerId = String(req.params.workerId || "");
    const worker = workerById(workerId);
    if (!worker) {
      res.status(404).json({ error: "Worker not found." });
      return;
    }
    setWorkerRuntime(workerId, { status: "idle", paused: false, lastHeartbeatAt: now(), nextRunAt: now() });
    addEvent("WORKER_RESUMED", `${worker.displayName} was resumed.`, "silicon-valley", { workerId });
    await persistState();
    res.json(state.workerRuntime.find((runtime) => runtime.workerId === workerId));
  });

  app.post("/api/v1/internal/operators/:workerId/escalate", requireInternal, async (req, res) => {
    const workerId = String(req.params.workerId || "");
    const worker = workerById(workerId);
    if (!worker) {
      res.status(404).json({ error: "Worker not found." });
      return;
    }

    const run: OperatorRun = {
      id: createId("oprun"),
      workerId,
      committeeId: worker.committeeId,
      pillarId: worker.primaryPillar,
      startedAt: now(),
      completedAt: now(),
      status: "escalated",
      inputs: ["manual-escalation"],
      actionsTaken: ["open_escalation"],
      evidenceCreated: [],
      archiveRef: undefined,
      escalations: [worker.escalationRuleId],
      errors: [],
      nextRecommendation: `${worker.displayName} requires immediate founder review.`,
    };
    state.operatorRuns = [run, ...state.operatorRuns].slice(0, MAX_OPERATOR_RUNS);
    setWorkerRuntime(workerId, {
      status: "error",
      paused: false,
      lastHeartbeatAt: now(),
      lastRunAt: run.completedAt,
      lastRunId: run.id,
      nextRunAt: isoAfterMinutes(worker.intervalMinutes),
      lastError: worker.escalationRuleId,
    });
    addEvent("WORKER_ESCALATED", `${worker.displayName} was manually escalated.`, "silicon-valley", {
      workerId,
      escalationRuleId: worker.escalationRuleId,
      runId: run.id,
    });
    await persistState();
    res.json(run);
  });

  app.post("/api/v1/internal/backend/events", requireInternal, async (req, res) => {
    try {
      const backendEvent = ingestBackendEvent(req.body);
      await persistState();
      res.status(202).json(backendEvent);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid backend event payload." });
    }
  });

  app.post("/api/v3/plans", withPublicRateLimit("public_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "v3PlanRequest");
      const intent = ensureString(body.intent, "v3PlanRequest.intent");
      const plan = createRevenueOpportunityPlan(intent);
      const title = typeof body.title === "string" && body.title.trim().length > 0 ? body.title.trim() : plan.title;
      const nextPlan = normalizeV3Plan({
        ...plan,
        title,
        updatedAt: now(),
      });
      validateV3Plan(nextPlan);
      state.v3Plans = [nextPlan, ...state.v3Plans.filter((entry) => entry.id !== nextPlan.id)];
      await persistState();
      res.status(201).json(nextPlan);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid V3 plan payload." });
    }
  });

  app.post("/api/v3/runs", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "v3RunRequest");
      const planId = ensureString(body.planId, "v3RunRequest.planId");
      const plan = state.v3Plans.find((entry) => entry.id === planId);
      if (!plan) {
        res.status(404).json({ error: "V3 plan not found." });
        return;
      }
      validateV3Plan(plan);
      validateGovernedLiveRun(plan);
      const { run, archive, artifact } = executeRevenueOpportunityRun(plan);
      await persistState();
      res.status(201).json({
        run,
        archive,
        artifact,
        workersUsed: run.workerIds.map((workerId) => getV3Worker(workerId)),
        committeesInvolved: run.committeeIds.map((committeeId) => getV3Committee(committeeId)),
        skillsInvoked: run.skillIds.map((skillId) => getV3Skill(skillId)),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to execute V3 run." });
    }
  });

  app.post("/api/v3/replay", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "v3ReplayRequest");
      const runId = ensureString(body.runId, "v3ReplayRequest.runId");
      const requestedBy = typeof body.requestedBy === "string" && body.requestedBy.trim().length > 0
        ? body.requestedBy.trim()
        : (process.env.USER_EMAIL || "founder");
      const mode = (typeof body.mode === "string" ? body.mode : "audit_only") as ReplayRequest["mode"];
      const reason = ensureString(body.reason || "Replay requested for governed audit.", "v3ReplayRequest.reason");
      const result = createReplayForRun(runId, requestedBy, mode, reason);
      await persistState();
      res.status(201).json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to create replay." });
    }
  });

  app.post("/api/v3/commercial-artifacts/:id/founder-review", withPublicRateLimit("public_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body, "founderReviewRequest");
      const status = ensureString(body.status, "founderReviewRequest.status") as FounderReviewStatus;
      if (!["pending_founder_review", "approved", "rejected", "needs_revision"].includes(status)) {
        throw new Error("Founder review status is invalid.");
      }
      const reason = ensureString(body.reason, "founderReviewRequest.reason");
      const riskNotes = Array.isArray(body.riskNotes)
        ? body.riskNotes.map((entry) => ensureString(entry, "founderReviewRequest.riskNotes[]"))
        : [];
      const approvedCopy = typeof body.approvedCopy === "string" ? body.approvedCopy.trim() : undefined;
      const rejectedClaims = Array.isArray(body.rejectedClaims)
        ? body.rejectedClaims.map((entry) => ensureString(entry, "founderReviewRequest.rejectedClaims[]"))
        : [];
      const reviewedBy = typeof body.reviewedBy === "string" && body.reviewedBy.trim().length > 0
        ? body.reviewedBy.trim()
        : (process.env.USER_EMAIL || "founder");
      const result = applyFounderReviewDecision(String(req.params.id || ""), status, reason, riskNotes, approvedCopy, rejectedClaims, reviewedBy);
      await persistState();
      res.status(201).json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to apply founder review." });
    }
  });

  app.post("/api/v3/demo/revenue-opportunity-test", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body || {}, "v3RevenueDemoRequest");
      const intent = typeof body.intent === "string" && body.intent.trim().length > 0
        ? body.intent.trim()
        : "Find one sellable Veklom marketplace opportunity from competitor weakness, package it, govern it, attach pricing, and archive the result.";
      const title = typeof body.title === "string" && body.title.trim().length > 0
        ? body.title.trim()
        : "Run Veklom Revenue Opportunity Test";
      const plan = normalizeV3Plan({
        ...createRevenueOpportunityPlan(intent),
        title,
      });
      state.v3Plans = [plan, ...state.v3Plans.filter((entry) => entry.id !== plan.id)];
      const { run, archive, artifact } = executeRevenueOpportunityRun(plan);
      await persistState();
      res.status(201).json({
        plan,
        run,
        archive,
        artifact,
        workersUsed: run.workerIds.map((workerId) => getV3Worker(workerId)),
        committeesInvolved: run.committeeIds.map((committeeId) => getV3Committee(committeeId)),
        skillsInvoked: run.skillIds.map((skillId) => getV3Skill(skillId)),
        inspection: buildV3InspectionView(run.id),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to run Veklom revenue opportunity test." });
    }
  });
  app.post("/api/intents/route-test", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    try {
      const body = ensureRecord(req.body || {}, "routeTestRequest");
      const intent = typeof body.intent === "string" && body.intent.trim().length > 0
        ? body.intent.trim()
        : "Find one revenue opportunity for Veklom, package it, govern it, and archive the result.";
      const plan = normalizeV3Plan({
        ...createRevenueOpportunityPlan(intent),
        title: "Registry Route Test",
      });
      state.v3Plans = [plan, ...state.v3Plans.filter((entry) => entry.id !== plan.id)];
      const { run, archive, artifact } = executeRevenueOpportunityRun(plan);
      const routedIntentResult = buildRoutedIntentResult(plan, run);
      const registryProof = buildPlanRegistryProof(plan.id);
      await persistState();
      res.status(201).json({
        routedIntentResult,
        registryProof,
        plan,
        run,
        archive,
        artifact,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Unable to execute route test." });
    }
  });
  app.get("/api/plans/:plan_id/registry-proof", (req, res) => {
    const planId = String(req.params.plan_id || "");
    const proof = buildPlanRegistryProof(planId);
    if (!proof) {
      res.status(404).json({ error: "Registry proof not found for the requested plan." });
      return;
    }
    res.json(proof);
  });

  app.post("/api/plans", withPublicRateLimit("public_mutation"), async (req, res) => {
    const intent = String(req.body?.intent || "").trim();
    if (!intent) {
      res.status(400).json({ error: "Intent is required." });
      return;
    }

    const startedAt = Date.now();
    const draft = await generatePlan(intent);
    const plan: InstitutionalPlan = {
      id: createId("plan"),
      createdAt: now(),
      ...draft,
    };
    state.plans = [plan, ...state.plans.filter((entry) => entry.id !== plan.id)];
    pushWindow(state.stats.planCompileDurationsMs, Date.now() - startedAt);

    addEvent("PLAN_CREATED", `Plan ${plan.title} created from institutional intent.`, "deterministic-engine", { planId: plan.id });
    addArchive({
      title: `${plan.title} doctrine snapshot`,
      category: "plan",
      summary: `Plan created with ${plan.pillars.length} pillars, ${plan.committeeIds.length} committees, ${plan.workflowIds.length} workflows, ${plan.skillIds.length} skills, ${plan.proposals?.length || 0} proposals, and ${plan.researchReferences?.length || 0} live references.`,
      lineage: [plan.id],
      metadata: {
        planId: plan.id,
        researchQuery: plan.researchQuery,
        references: plan.researchReferences,
        workflowIds: plan.workflowIds,
        skillIds: plan.skillIds,
        escalationRuleIds: plan.escalationRuleIds,
        proposals: plan.proposals,
      },
    });
    const workerRelease = releasePlanSearchWorkers(plan);
    captureMetricHistory();
    await persistState();
    res.json({
      ...plan,
      searchPressure: workerRelease,
    });
  });

  app.post("/api/runs", withPublicRateLimit("heavy_mutation"), async (req, res) => {
    const planId = String(req.body?.planId || "");
    const plan = state.plans.find((item) => item.id === planId);
    if (!plan) {
      res.status(404).json({ error: "Plan not found." });
      return;
    }

    const run: GovernedRun = {
      id: createId("run"),
      planId,
      status: "queued",
      currentStage: "Admission control",
      progress: 0,
      approvals: 0,
      evidenceCount: 0,
      startedAt: now(),
      stages: [],
      errors: [],
    };
    state.runs = [run, ...state.runs.filter((entry) => entry.id !== run.id)];
    plan.status = "active";
    addEvent("RUN_QUEUED", `Run queued for plan ${plan.title}.`, "sunnyvale", { runId: run.id, planId });
    captureMetricHistory();
    await persistState();
    void executeRun(run.id);
    res.json(run);
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => res.sendFile(path.join(distPath, "index.html")));
  }

  httpServer.listen(PORT, "0.0.0.0", () => {
    addEvent("SYSTEM_ONLINE", "UACP V3 constitutional control plane initialized with live research ingestion.", "silicon-valley");
    console.log(
      `Model providers: primary=${providerSnapshot.defaultProvider} active=${providerSnapshot.activeProvider} statuses=${providerSnapshot.statuses.map((status) => `${status.id}:${status.health}`).join(", ")}`,
    );
    console.log(`UACP V3 running on http://localhost:${PORT}`);
  });
}

void startServer().catch((error) => {
  console.error("UACP V3 failed to start:", error);
  process.exit(1);
});
