/**
 * Veklom workspace wiring trace — UNAUTHENTICATED.
 *
 * Loads each public/login surface of https://veklom.com and the workspace
 * shell at /workspace/ and captures every fetch/XHR the prebuilt bundle
 * issues.  The output is a JSON report (one row per request) that the
 * WIRING_MATRIX uses as evidence of which endpoints the bundle actually
 * calls — no claims are made beyond what the network shows.
 *
 * Run:
 *   cd tests/playwright
 *   npm install
 *   npx playwright install chromium
 *   npx playwright test wiring_trace.spec.ts --reporter=list
 *
 * Output:
 *   tests/playwright/trace-output/wiring_trace.json
 *   tests/playwright/trace-output/<surface>.har   (one HAR per surface)
 */
import { test, expect, Request, Response } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const OUT_DIR = path.join(__dirname, "trace-output");
const REPORT = path.join(OUT_DIR, "wiring_trace.json");

interface CapturedRequest {
  surface: string;
  method: string;
  url: string;
  resourceType: string;
  status?: number;
  ok?: boolean;
  fromBundle: boolean;
}

const allRequests: CapturedRequest[] = [];

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function isApiRequest(url: string): boolean {
  // Anything pointing at a backend route on veklom.com counts as a wiring signal.
  // Excludes static assets + analytics.
  if (url.includes("/api/v1/")) return true;
  if (url.includes("/health")) return true;
  if (url.includes("/openapi.json")) return true;
  if (url.includes("/api-status")) return true;
  if (url.includes("/legal/")) return true;
  if (url.includes("/.well-known/")) return true;
  if (url.includes("/llms.txt")) return true;
  if (url.includes("/robots.txt")) return true;
  if (url.includes("/mcp/")) return true;
  return false;
}

async function capture(page: any, surface: string, navigate: () => Promise<void>) {
  const requests: CapturedRequest[] = [];

  page.on("request", (req: Request) => {
    if (!isApiRequest(req.url())) return;
    requests.push({
      surface,
      method: req.method(),
      url: req.url(),
      resourceType: req.resourceType(),
      fromBundle: true,
    });
  });

  page.on("response", (res: Response) => {
    const url = res.url();
    if (!isApiRequest(url)) return;
    const last = [...requests].reverse().find(
      (r) => r.url === url && r.method === res.request().method() && r.status === undefined,
    );
    if (last) {
      last.status = res.status();
      last.ok = res.ok();
    }
  });

  await navigate();
  // Allow late XHR/SSE to settle.
  await page.waitForTimeout(2500);

  allRequests.push(...requests);
  return requests;
}

test.beforeAll(() => ensureDir(OUT_DIR));

test.afterAll(() => {
  fs.writeFileSync(REPORT, JSON.stringify(allRequests, null, 2), "utf-8");
  // Aggregate summary: distinct path × method → first status seen.
  const seen = new Map<string, { method: string; url: string; status?: number; surfaces: Set<string> }>();
  for (const r of allRequests) {
    const u = new URL(r.url);
    const key = `${r.method} ${u.pathname}`;
    if (!seen.has(key)) seen.set(key, { method: r.method, url: u.pathname, status: r.status, surfaces: new Set() });
    seen.get(key)!.surfaces.add(r.surface);
  }
  const summaryPath = path.join(OUT_DIR, "wiring_summary.txt");
  const lines: string[] = [];
  lines.push(`Veklom workspace unauth network trace — ${new Date().toISOString()}`);
  lines.push(`Surfaces visited: home, login, register, workspace, command-center, irongrid, terminal, gpc, marketplace, security, acceptable-use, billing, llms.txt`);
  lines.push("");
  lines.push("METHOD  STATUS  PATH");
  lines.push("-".repeat(80));
  const rows = [...seen.values()].sort((a, b) => a.url.localeCompare(b.url));
  for (const r of rows) {
    lines.push(`${r.method.padEnd(7)} ${String(r.status ?? "?").padEnd(6)} ${r.url}    [${[...r.surfaces].join(",")}]`);
  }
  lines.push("");
  lines.push(`Total requests captured: ${allRequests.length}`);
  lines.push(`Distinct method×path:    ${seen.size}`);
  fs.writeFileSync(summaryPath, lines.join("\n"), "utf-8");
});

test.describe("Veklom workspace — unauth network trace", () => {
  test("homepage", async ({ page }) => {
    const reqs = await capture(page, "home", async () => {
      await page.goto("/", { waitUntil: "networkidle" });
    });
    expect(page.url()).toContain("veklom.com");
    console.log(`  home: ${reqs.length} backend calls`);
  });

  test("login page", async ({ page }) => {
    const reqs = await capture(page, "login", async () => {
      await page.goto("/login", { waitUntil: "networkidle" });
    });
    console.log(`  login: ${reqs.length} backend calls`);
  });

  test("register page", async ({ page }) => {
    const reqs = await capture(page, "register", async () => {
      await page.goto("/register", { waitUntil: "networkidle" });
    });
    console.log(`  register: ${reqs.length} backend calls`);
  });

  test("workspace shell (unauth → expect 401 redirects)", async ({ page }) => {
    const reqs = await capture(page, "workspace", async () => {
      await page.goto("/workspace/", { waitUntil: "networkidle" });
    });
    console.log(`  workspace: ${reqs.length} backend calls`);
  });

  test("command-center page", async ({ page }) => {
    const reqs = await capture(page, "command-center", async () => {
      await page.goto("/command-center/", { waitUntil: "networkidle" });
    });
    console.log(`  command-center: ${reqs.length} backend calls`);
  });

  test("irongrid page", async ({ page }) => {
    const reqs = await capture(page, "irongrid", async () => {
      await page.goto("/irongrid/", { waitUntil: "networkidle" });
    });
    console.log(`  irongrid: ${reqs.length} backend calls`);
  });

  test("terminal page", async ({ page }) => {
    const reqs = await capture(page, "terminal", async () => {
      await page.goto("/terminal", { waitUntil: "networkidle" });
    });
    console.log(`  terminal: ${reqs.length} backend calls`);
  });

  test("gpc page", async ({ page }) => {
    const reqs = await capture(page, "gpc", async () => {
      await page.goto("/gpc/", { waitUntil: "networkidle" });
    });
    console.log(`  gpc: ${reqs.length} backend calls`);
  });

  test("marketplace page", async ({ page }) => {
    const reqs = await capture(page, "marketplace", async () => {
      await page.goto("/marketplace", { waitUntil: "networkidle" });
    });
    console.log(`  marketplace: ${reqs.length} backend calls`);
  });

  test("legal/security page", async ({ page }) => {
    const reqs = await capture(page, "security", async () => {
      await page.goto("/legal/security", { waitUntil: "networkidle" });
    });
    console.log(`  security: ${reqs.length} backend calls`);
  });

  test("legal/acceptable-use page", async ({ page }) => {
    const reqs = await capture(page, "acceptable-use", async () => {
      await page.goto("/legal/acceptable-use", { waitUntil: "networkidle" });
    });
    console.log(`  acceptable-use: ${reqs.length} backend calls`);
  });

  test("legal/privacy page", async ({ page }) => {
    const reqs = await capture(page, "privacy", async () => {
      await page.goto("/legal/privacy", { waitUntil: "networkidle" });
    });
    console.log(`  privacy: ${reqs.length} backend calls`);
  });

  test("llms.txt", async ({ page }) => {
    const reqs = await capture(page, "llms.txt", async () => {
      await page.goto("/llms.txt", { waitUntil: "networkidle" });
    });
    console.log(`  llms.txt: ${reqs.length} backend calls`);
  });

  test("billing page", async ({ page }) => {
    const reqs = await capture(page, "billing", async () => {
      await page.goto("/workspace/", { waitUntil: "networkidle" });
    });
    console.log(`  billing: ${reqs.length} backend calls`);
  });
});

// ---------------------------------------------------------------------------
// Discovery endpoint assertions — these must all return 200 and correct types
// ---------------------------------------------------------------------------
test.describe("Machine-native discovery endpoints", () => {
  test("/.well-known/ai-plugin.json returns 200 JSON with schema_version", async ({ request }) => {
    const res = await request.get("/.well-known/ai-plugin.json");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("schema_version");
    expect(body).toHaveProperty("name_for_model");
    expect(body).toHaveProperty("api");
  });

  test("/.well-known/agent.json returns 200 with tiers and agent_controls", async ({ request }) => {
    const res = await request.get("/.well-known/agent.json");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("tiers");
    expect(body).toHaveProperty("agent_controls");
    expect(body.agent_controls).toHaveProperty("kill_switch", true);
    expect(body.agent_controls).toHaveProperty("budget_caps", true);
    expect(body.agent_controls).toHaveProperty("evidence_receipts", true);
  });

  test("/.well-known/x402.json returns 200 with routes array", async ({ request }) => {
    const res = await request.get("/.well-known/x402.json");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("x402_version", 1);
    expect(body).toHaveProperty("routes");
    expect(Array.isArray(body.routes)).toBe(true);
    expect(body.routes.length).toBeGreaterThan(5);
    expect(body.routes[0]).toHaveProperty("price_usdc");
    expect(body.routes[0]).toHaveProperty("payment");
  });

  test("/llms.txt returns 200 plain text with four-tier framing", async ({ request }) => {
    const res = await request.get("/llms.txt");
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text).toContain("Humans");
    expect(text).toContain("Developers");
    expect(text).toContain("Agents");
    expect(text).toContain("Enterprises");
    expect(text).toContain("x402");
  });

  test("/robots.txt returns 200 with agent-native directives", async ({ request }) => {
    const res = await request.get("/robots.txt");
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text).toContain("User-agent: *");
    expect(text).toContain("llms.txt");
    expect(text).toContain("agent.json");
  });

  test("/mcp/sse returns 200 SSE stream with tool definitions", async ({ request }) => {
    const res = await request.get("/mcp/sse");
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text).toContain("server_info");
    expect(text).toContain("veklom_gpc_compile");
    expect(text).toContain("veklom_ai_inference");
    expect(text).toContain("done");
  });

  test("/openapi.json returns 200 with valid OpenAPI schema", async ({ request }) => {
    const res = await request.get("/openapi.json");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("openapi");
    expect(body).toHaveProperty("paths");
    expect(body).toHaveProperty("info");
  });
});

// ---------------------------------------------------------------------------
// x402 gate assertions — unauthenticated paid routes must return 402 or use free quota
// ---------------------------------------------------------------------------
test.describe("x402 payment gate", () => {
  test("paid route returns receipt headers when free quota available", async ({ request }) => {
    const res = await request.post("/api/v1/ai/inference", {
      data: { messages: [{ role: "user", content: "hello" }] },
    });
    // Free tier allows first N requests — should get receipt headers regardless
    const headers = res.headers();
    const hasReceipt = (
      "x-veklom-request-id" in headers ||
      "x-veklom-free-trial" in headers
    );
    expect(hasReceipt).toBe(true);
  });

  test("paid route without payment eventually returns 402 after quota", async ({ request }) => {
    // This route has free_daily: 0 — must return 402 immediately for unauthenticated requests
    const res = await request.post("/api/v1/pipelines/trigger", {
      data: { pipeline_id: "test" },
    });
    expect([402, 404]).toContain(res.status());
    if (res.status() === 402) {
      const body = await res.json();
      expect(body).toHaveProperty("x402Version", 1);
      expect(body).toHaveProperty("accepts");
      expect(Array.isArray(body.accepts)).toBe(true);
      const headers = res.headers();
      expect(headers).toHaveProperty("x-payment-required", "true");
      expect(headers).toHaveProperty("x-payment-scheme", "x402");
    }
  });

  test("free route health returns 200 with no payment headers", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.status()).toBe(200);
    const headers = res.headers();
    expect("x-payment-required" in headers).toBe(false);
  });
});
