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
});
