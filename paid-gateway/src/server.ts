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

// x402 imports — try @coinbase/x402 first, fall back to @x402/* packages
let paymentMiddleware: any;
let resourceServerFactory: any;
let facilitatorFactory: any;

try {
  // Modern Coinbase SDK (preferred)
  const coinbaseX402 = await import("@coinbase/x402/express");
  paymentMiddleware = coinbaseX402.paymentMiddleware;
  const cdpModule = await import("@coinbase/x402");
  facilitatorFactory = cdpModule.coinbase;
  console.log("[gateway] Using @coinbase/x402 (CDP facilitator)");
} catch {
  try {
    // Fallback: open-source @x402/* packages
    const x402Express = await import("@x402/express");
    paymentMiddleware = x402Express.paymentMiddleware;
    resourceServerFactory = x402Express.x402ResourceServer;
    const x402Core = await import("@x402/core/server");
    const x402Evm = await import("@x402/evm/exact/server");
    facilitatorFactory = null; // will use HTTPFacilitatorClient
    console.log("[gateway] Using @x402/express (open-source)");
  } catch (e) {
    console.error("[gateway] FATAL: No x402 package found. Install @coinbase/x402 or @x402/express");
    process.exit(1);
  }
}

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

const PAY_TO             = process.env.PAY_TO!;
const UPSTREAM           = process.env.UPSTREAM_BASE_URL!;
const GATEWAY_SECRET     = process.env.UPSTREAM_GATEWAY_SECRET!;
const CDP_KEY_ID         = process.env.CDP_API_KEY_ID!;
const CDP_KEY_SECRET     = process.env.CDP_API_KEY_SECRET!;
const PORT               = Number(process.env.PORT || 3001);
const NETWORK            = process.env.NETWORK || "eip155:8453";

// ---------------------------------------------------------------------------
// Express app
// ---------------------------------------------------------------------------
const app = express();

// ---------------------------------------------------------------------------
// Health / discovery endpoints (free — no payment required)
// ---------------------------------------------------------------------------
app.get("/health",  (_req, res) => res.json({ ok: true, gateway: "veklom-x402", network: NETWORK, payTo: PAY_TO }));
app.get("/healthz", (_req, res) => res.json({ ok: true }));

app.get("/.well-known/x402.json", (_req, res) => {
  res.set("Access-Control-Allow-Origin", "*");
  res.json({
    x402_version: 1,
    provider: "Veklom Sovereign AI Hub",
    network: NETWORK,
    payTo: PAY_TO,
    currency: "USDC",
    routes: Object.entries(paidRoutes).map(([route, config]) => ({
      route,
      price: config.accepts[0]?.price,
      description: config.description,
      tags: config.extensions?.bazaar?.tags ?? [],
      category: config.extensions?.bazaar?.category ?? "api",
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
if (facilitatorFactory) {
  // @coinbase/x402 path
  const facilitator = facilitatorFactory({ cdpKeyId: CDP_KEY_ID, cdpKeySecret: CDP_KEY_SECRET });
  app.use(
    paymentMiddleware(paidRoutes, { payTo: PAY_TO, network: NETWORK, facilitator })
  );
} else {
  // @x402/* open-source path
  const { HTTPFacilitatorClient } = await import("@x402/core/server");
  const { ExactEvmScheme } = await import("@x402/evm/exact/server");
  const { facilitator } = await import("@coinbase/x402");
  const facilitatorClient = new HTTPFacilitatorClient(
    facilitator({ cdpKeyId: CDP_KEY_ID, cdpKeySecret: CDP_KEY_SECRET })
  );
  const resourceServer = new resourceServerFactory(facilitatorClient).register(
    NETWORK,
    new ExactEvmScheme()
  );
  app.use(paymentMiddleware(paidRoutes, resourceServer));
}

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
      proxyReq: (proxyReq, req) => {
        // Inject gateway auth secret — upstream validates this
        proxyReq.setHeader("X-Gateway-Secret", GATEWAY_SECRET);
        proxyReq.setHeader("X-Paid-Gateway", "veklom-x402");
        proxyReq.setHeader("X-Gateway-Network", NETWORK);

        // Strip x402 payment headers — upstream doesn't need them
        for (const h of ["PAYMENT-SIGNATURE", "PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "X-Payment-Proof"]) {
          proxyReq.removeHeader(h);
        }
      },
      proxyRes: (proxyRes, req, res: any) => {
        // Add gateway receipt headers to every response
        proxyRes.headers["X-Veklom-Gateway"] = "x402";
        proxyRes.headers["X-Veklom-Network"] = NETWORK;
        proxyRes.headers["Access-Control-Allow-Origin"] = "*";
        proxyRes.headers["Access-Control-Expose-Headers"] = [
          "X-Veklom-Request-ID",
          "X-Veklom-Evidence-ID",
          "X-Veklom-Cost-USDC",
          "X-Veklom-Policy-Result",
          "X-Veklom-Receipt-URL",
          "X-Veklom-Gateway",
          "X-Veklom-Network",
        ].join(", ");
      },
      error: (err, req, res: any) => {
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
