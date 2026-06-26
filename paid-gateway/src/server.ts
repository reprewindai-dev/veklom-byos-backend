/**
 * Veklom x402 Paid Gateway
 *
 * Architecture:
 *   Agent wallet → this gateway → CDP facilitator → USDC settles to PAY_TO wallet
 *   → this gateway proxies the request to internal Veklom FastAPI backend
 *   → agent gets governed response + evidence receipt
 *
 * Agents never see the upstream API key or internal URL.
 * Unpaid requests receive HTTP 402 with payment requirements.
 * The upstream FastAPI backend is protected by UPSTREAM_GATEWAY_SECRET.
 *
 * From prompt to plan to proof — and now to payment.
 */

import "dotenv/config";
import express, { type Request, type Response, type NextFunction } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";

import { paymentMiddleware, x402ResourceServer } from "@x402/express";
import { CoinbaseFacilitatorClient } from "@x402/coinbase";
import { ExactEvmScheme } from "@x402/evm/exact/server";

import { paidRoutes, SOLD_ROUTE_PATTERNS } from "./routes.js";

// ---------------------------------------------------------------------------
// Environment validation
// ---------------------------------------------------------------------------
const REQUIRED_ENV = ["CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "PAY_TO", "UPSTREAM_BASE_URL", "UPSTREAM_GATEWAY_SECRET"];
const missing = REQUIRED_ENV.filter((k) => !process.env[k]);
if (missing.length > 0) {
  console.error(`[gateway] FATAL: Missing required env vars: ${missing.join(", ")}`);
  console.error("[gateway] Copy .env.example to .env and fill in all values.");
  process.exit(1);
}

const PAY_TO = process.env.PAY_TO!;
const UPSTREAM = process.env.UPSTREAM_BASE_URL!;
const GATEWAY_SECRET = process.env.UPSTREAM_GATEWAY_SECRET!;
const CDP_KEY_ID = process.env.CDP_API_KEY_ID!;
const CDP_KEY_SECRET = process.env.CDP_API_KEY_SECRET!;
const PORT = Number(process.env.PORT || 3001);
const NETWORK = process.env.NETWORK || "eip155:8453";

// ---------------------------------------------------------------------------
// x402 facilitator using @x402/coinbase — accepts Ed25519 base64 keys
// ---------------------------------------------------------------------------
const facilitatorClient = new CoinbaseFacilitatorClient({
  apiKeyId: CDP_KEY_ID,
  apiKeySecret: CDP_KEY_SECRET,
});

const resourceServer = new x402ResourceServer(facilitatorClient).register(
  NETWORK as `${string}:${string}`,
  new ExactEvmScheme(),
);

// ---------------------------------------------------------------------------
// Express app
// ---------------------------------------------------------------------------
const app = express();

// ---------------------------------------------------------------------------
// Health / discovery endpoints (free — no payment required)
// ---------------------------------------------------------------------------
app.get("/health", (_req, res) =>
  res.json({ ok: true, gateway: "veklom-x402", network: NETWORK, payTo: PAY_TO }),
);
app.get("/healthz", (_req, res) => res.json({ ok: true }));

app.get("/.well-known/x402.json", (_req, res) => {
  res.set("Access-Control-Allow-Origin", "*");
  res.json({
    x402_version: 2,
    provider: "Veklom Sovereign AI Hub",
    network: NETWORK,
    payTo: PAY_TO,
    currency: "USDC",
    routes: Object.entries(paidRoutes).map(([route, config]) => ({
      route,
      price: (config.accepts as any).price ?? (Array.isArray(config.accepts) ? config.accepts[0]?.price : undefined),
      description: config.description,
      tags: (config.extensions as any)?.bazaar?.tags ?? [],
      category: (config.extensions as any)?.bazaar?.category ?? "api",
    })),
    discovery: {
      bazaar: "https://bazaar.cdp.coinbase.com",
      mcp_sse: "https://api.veklom.com/mcp/sse",
      llms_txt: "https://api.veklom.com/llms.txt",
      openapi: "https://api.veklom.com/openapi.json",
    },
  });
});

// CORS preflight — always free
app.options("*", (_req, res) => {
  res.set({
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Payment-Proof, X-Payment-Signature, PAYMENT-SIGNATURE, PAYMENT-REQUIRED, PAYMENT-RESPONSE",
  });
  res.sendStatus(204);
});

// ---------------------------------------------------------------------------
// x402 payment middleware — gates every paid route
// ---------------------------------------------------------------------------
// Initialize facilitator to fetch supported payment kinds.
// With placeholder CDP keys this will fail — health + discovery still work.
// Paid routes return 500 until real CDP_API_KEY_ID / CDP_API_KEY_SECRET are set.
try {
  await resourceServer.initialize();
  console.log("[gateway] Facilitator initialized — payment settlement enabled");
} catch (err: any) {
  console.warn("[gateway] Facilitator init failed:", err.message?.split("\n")[0] || err);
  console.warn("[gateway] Health + discovery endpoints work. Paid routes need real CDP keys.");
}
app.use(paymentMiddleware(paidRoutes, resourceServer, undefined, undefined, false));

// ---------------------------------------------------------------------------
// Deny-by-default: every unlisted route returns 404 — nothing is free by accident
// ---------------------------------------------------------------------------
app.use((req: Request, res: Response, next: NextFunction) => {
  const allowed = SOLD_ROUTE_PATTERNS.some(([method, pattern]) =>
    req.method === method && pattern.test(req.path)
  );
  if (!allowed) {
    res.status(404).json({
      error: "endpoint_not_sold",
      message: "This endpoint is not listed as a paid x402 resource. Only priced routes are accessible through this gateway.",
      discovery: "https://api.veklom.com/.well-known/x402.json",
    });
    return;
  }
  next();
});

// ---------------------------------------------------------------------------
// Request logging
// ---------------------------------------------------------------------------
app.use((req: Request, _res: Response, next: NextFunction) => {
  const payer = req.headers["x-payer-address"] || req.headers["x-payment-signature"]?.toString().slice(0, 20) || "unknown";
  console.log(`[gateway] ${new Date().toISOString()} ${req.method} ${req.path} payer=${payer}`);
  next();
});

// ---------------------------------------------------------------------------
// Proxy to Veklom FastAPI backend
// The gateway authenticates to the upstream with UPSTREAM_GATEWAY_SECRET.
// The upstream should reject requests without this header.
// ---------------------------------------------------------------------------
app.use(
  createProxyMiddleware({
    target: UPSTREAM,
    changeOrigin: true,
    xfwd: true,
    on: {
      proxyReq: (proxyReq, _req) => {
        // Inject gateway auth secret — upstream validates this
        proxyReq.setHeader("X-Gateway-Secret", GATEWAY_SECRET);
        proxyReq.setHeader("X-Paid-Gateway", "veklom-x402");
        proxyReq.setHeader("X-Gateway-Network", NETWORK);

        // Strip x402 payment headers — upstream doesn't need them
        for (const h of ["PAYMENT-SIGNATURE", "PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "X-Payment-Proof"]) {
          proxyReq.removeHeader(h);
        }
      },
      proxyRes: (proxyRes, _req, _res) => {
        // Add gateway receipt headers to every response
        proxyRes.headers["x-veklom-gateway"] = "x402";
        proxyRes.headers["x-veklom-network"] = NETWORK;
        proxyRes.headers["access-control-allow-origin"] = "*";
        proxyRes.headers["access-control-expose-headers"] = [
          "X-Veklom-Request-ID",
          "X-Veklom-Evidence-ID",
          "X-Veklom-Cost-USDC",
          "X-Veklom-Policy-Result",
          "X-Veklom-Receipt-URL",
          "X-Veklom-Gateway",
          "X-Veklom-Network",
        ].join(", ");
      },
      error: (err, _req, res: any) => {
        console.error(`[gateway] Proxy error: ${err.message}`);
        if (!res.headersSent) {
          res.status(502).json({ error: "upstream_error", message: "Veklom backend unreachable" });
        }
      },
    },
  })
);

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`[gateway] Veklom x402 paid gateway running on port ${PORT}`);
  console.log(`[gateway] Network:  ${NETWORK}`);
  console.log(`[gateway] PayTo:    ${PAY_TO}`);
  console.log(`[gateway] Upstream: ${UPSTREAM}`);
  console.log(`[gateway] Routes:   ${Object.keys(paidRoutes).length} paid endpoints`);
  console.log(`[gateway] Discovery: GET /.well-known/x402.json`);
});
