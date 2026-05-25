/**
 * Veklom paid route definitions.
 *
 * This is the single source of truth for:
 *   - what is sold
 *   - what it costs (USDC on Base mainnet)
 *   - what description agents/Bazaar see
 *
 * Every route listed here requires a valid x402 payment.
 * Every route NOT listed here returns 404 — nothing passes for free.
 */

export const PAY_TO = process.env.PAY_TO!;
export const NETWORK = process.env.NETWORK || "eip155:8453"; // Base mainnet

/**
 * Route definitions for paymentMiddleware.
 * Price is in USDC. scheme: "exact" = fixed per-call pricing.
 */
export const paidRoutes = {
  // ---------------------------------------------------------------------------
  // AI Inference
  // ---------------------------------------------------------------------------
  "POST /api/v1/ai/inference": {
    accepts: [{ scheme: "exact" as const, price: "$0.008", network: NETWORK, payTo: PAY_TO }],
    description: "Policy-gated AI inference. Ollama-first, auto-escalates to Groq/Gemini/OpenAI. Returns result + evidence receipt.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "ai-inference",
        tags: ["ai", "inference", "governed", "policy", "veklom"],
      },
    },
  },

  "POST /api/v1/ai/chat": {
    accepts: [{ scheme: "exact" as const, price: "$0.005", network: NETWORK, payTo: PAY_TO }],
    description: "AI chat with 20-message persistent memory (24h Redis TTL). Hot/warm response cache.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "ai-inference",
        tags: ["ai", "chat", "memory", "persistent", "veklom"],
      },
    },
  },

  // ---------------------------------------------------------------------------
  // GPC — Governed Plan Compiler
  // ---------------------------------------------------------------------------
  "POST /api/v1/gpc/compile": {
    accepts: [{ scheme: "exact" as const, price: "$0.015", network: NETWORK, payTo: PAY_TO }],
    description: "Compile agent intent into a deterministic, policy-checked governed plan. Returns Decision Frame with proof_hash.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "governance",
        tags: ["gpc", "compile", "plan", "governance", "policy", "veklom"],
      },
    },
  },

  "POST /api/v1/gpc/intent-to-plan": {
    accepts: [{ scheme: "exact" as const, price: "$0.010", network: NETWORK, payTo: PAY_TO }],
    description: "Convert high-level intent string into a structured governed execution plan.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "governance",
        tags: ["gpc", "intent", "plan", "veklom"],
      },
    },
  },

  "POST /api/v1/gpc/runs": {
    accepts: [{ scheme: "exact" as const, price: "$0.020", network: NETWORK, payTo: PAY_TO }],
    description: "Execute a compiled governed plan. All steps are policy-checked and evidence-sealed.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "governance",
        tags: ["gpc", "run", "execute", "governed", "veklom"],
      },
    },
  },

  // ---------------------------------------------------------------------------
  // Pipelines
  // ---------------------------------------------------------------------------
  "POST /api/v1/pipelines/trigger": {
    accepts: [{ scheme: "exact" as const, price: "$0.025", network: NETWORK, payTo: PAY_TO }],
    description: "Trigger a governed pipeline. Budget caps and kill switches enforced at every node.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "orchestration",
        tags: ["pipeline", "trigger", "orchestration", "veklom"],
      },
    },
  },

  // ---------------------------------------------------------------------------
  // Runtime Jobs
  // ---------------------------------------------------------------------------
  "POST /api/v1/runtime/jobs": {
    accepts: [{ scheme: "exact" as const, price: "$0.020", network: NETWORK, payTo: PAY_TO }],
    description: "Submit a runtime job to the governed execution layer.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "compute",
        tags: ["runtime", "job", "compute", "veklom"],
      },
    },
  },

  // ---------------------------------------------------------------------------
  // Evidence & Compliance
  // ---------------------------------------------------------------------------
  "GET /api/v1/evidence/export": {
    accepts: [{ scheme: "exact" as const, price: "$0.005", network: NETWORK, payTo: PAY_TO }],
    description: "Export SHA-256 sealed audit evidence for a governed execution. Replayable proof object.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "compliance",
        tags: ["evidence", "audit", "sha256", "proof", "veklom"],
      },
    },
  },

  "GET /api/v1/compliance/report": {
    accepts: [{ scheme: "exact" as const, price: "$0.010", network: NETWORK, payTo: PAY_TO }],
    description: "Generate a compliance report. Frameworks: SOC2, HIPAA, GDPR, ISO 27001, EU AI Act, FedRAMP.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "compliance",
        tags: ["compliance", "soc2", "hipaa", "gdpr", "report", "veklom"],
      },
    },
  },

  // ---------------------------------------------------------------------------
  // Marketplace
  // ---------------------------------------------------------------------------
  "POST /api/v1/marketplace/acquire": {
    accepts: [{ scheme: "exact" as const, price: "$0.050", network: NETWORK, payTo: PAY_TO }],
    description: "Acquire a sovereign AI model or governance pack from the Veklom marketplace.",
    mimeType: "application/json",
    extensions: {
      bazaar: {
        discoverable: true,
        category: "marketplace",
        tags: ["marketplace", "model", "acquire", "sovereign", "veklom"],
      },
    },
  },
};

/**
 * Regex patterns for deny-by-default protection.
 * Only routes matching these patterns are allowed through.
 * Everything else returns 404 before hitting the upstream.
 */
export const SOLD_ROUTE_PATTERNS: Array<[string, RegExp]> = [
  ["POST",  /^\/api\/v1\/ai\/inference\/?$/],
  ["POST",  /^\/api\/v1\/ai\/chat\/?$/],
  ["POST",  /^\/api\/v1\/gpc\/compile\/?$/],
  ["POST",  /^\/api\/v1\/gpc\/intent-to-plan\/?$/],
  ["POST",  /^\/api\/v1\/gpc\/runs\/?$/],
  ["POST",  /^\/api\/v1\/pipelines\/trigger\/?$/],
  ["POST",  /^\/api\/v1\/runtime\/jobs\/?$/],
  ["GET",   /^\/api\/v1\/evidence\/export\/?/],
  ["GET",   /^\/api\/v1\/compliance\/report\/?/],
  ["POST",  /^\/api\/v1\/marketplace\/acquire\/?$/],
];
