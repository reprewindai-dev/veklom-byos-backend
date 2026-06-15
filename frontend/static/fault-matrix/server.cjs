var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express = __toESM(require("express"), 1);
var import_path = __toESM(require("path"), 1);
var import_vite = require("vite");
var import_dns = __toESM(require("dns"), 1);
var import_genai = require("@google/genai");
import_dns.default.setDefaultResultOrder("ipv4first");
var webhookLogs = [];
async function startServer() {
  const app = (0, import_express.default)();
  const PORT = 3e3;
  app.use(import_express.default.json());
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });
  app.post("/api/mock-webhook", (req, res) => {
    const log = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      payload: req.body,
      headers: req.headers
    };
    webhookLogs.push(log);
    if (webhookLogs.length > 50) {
      webhookLogs.shift();
    }
    return res.status(200).json({ status: "delivered", id: log.id });
  });
  app.get("/api/webhook-logs", (req, res) => {
    res.json(webhookLogs);
  });
  app.post("/api/trigger-alert", async (req, res) => {
    const { url, payload } = req.body;
    try {
      if (!url) {
        return res.status(400).json({ status: "error", error: "Missing webhook target url" });
      }
      const response = await globalThis.fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const responseText = await response.text();
      let responseJson = null;
      try {
        responseJson = JSON.parse(responseText);
      } catch (err) {
        responseJson = responseText;
      }
      return res.json({
        status: "success",
        statusCode: response.status,
        response: responseJson
      });
    } catch (error) {
      console.error("Outbound webhook alert failed:", error);
      return res.status(200).json({
        status: "failed",
        error: error?.message || "Connection refused"
      });
    }
  });
  app.post("/api/analyze-ledger", async (req, res) => {
    const { prompt, items } = req.body;
    try {
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
        return res.json({
          status: "simulated",
          text: "### [API Key Config Message]\nGemini API key is not configured in Settings > Secrets. Here is a simulated system check:\n\n**Verdict**: Veklom Agent Authority ledger is structurally integral. F-distribution mapping successfully detected variance offsets in the L4 semantic gateway tool queues. The 120-agent concurrency queue is currently safe, with no lock collision anomalies."
        });
      }
      const ai = new import_genai.GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build"
          }
        }
      });
      const fullPrompt = `You are the chief auditor for the Veklom Agent Authority Runtime.
Here is the operational ledger and system status context for diagnostic review:
${JSON.stringify(items, null, 2)}

User request/diagnostic task:
${prompt}

Provide a highly technical, precise, system-level operational review. Highlight whether there is any violation of agent auth limits, vector smuggling attempts, or F-distribution deviations. Keep it formatted in raw markdown.`;
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: fullPrompt
      });
      return res.json({
        status: "success",
        text: response.text
      });
    } catch (error) {
      console.error("Gemini API call failed:", error);
      return res.status(500).json({
        status: "error",
        error: error?.message || "Internal server error"
      });
    }
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(import_path.default.join(distPath, "index.html"));
    });
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Veklom Server running on http://localhost:${PORT}`);
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
