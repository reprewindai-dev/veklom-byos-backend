import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dns from "dns";
import { GoogleGenAI } from "@google/genai";
import fetch from "node-fetch"; // Node 18+ has native fetch, but node-fetch fits CJS/ESM nicely, or we can use globalThis.fetch!

dns.setDefaultResultOrder("ipv4first");

interface WebhookLog {
  id: string;
  timestamp: string;
  payload: any;
  headers: any;
}

const webhookLogs: WebhookLog[] = [];

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Memory store for simulation
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });

  // Mock Webhook Target Endpoint - can be triggered by the client-initiated server-side fetch
  app.post("/api/mock-webhook", (req, res) => {
    const log: WebhookLog = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      payload: req.body,
      headers: req.headers
    };
    webhookLogs.push(log);
    // Keep max 50 logs
    if (webhookLogs.length > 50) {
      webhookLogs.shift();
    }
    return res.status(200).json({ status: "delivered", id: log.id });
  });

  // Endpoint to fetch simulated webhook logs
  app.get("/api/webhook-logs", (req, res) => {
    res.json(webhookLogs);
  });

  // Trigger outbound webhook call from the server to bypass any sandbox constraints and prove real HTTP communication
  app.post("/api/trigger-alert", async (req, res) => {
    const { url, payload } = req.body;
    try {
      if (!url) {
        return res.status(400).json({ status: "error", error: "Missing webhook target url" });
      }

      // Perform a real server-side fetch request
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
    } catch (error: any) {
      console.error("Outbound webhook alert failed:", error);
      return res.status(200).json({
        status: "failed",
        error: error?.message || "Connection refused"
      });
    }
  });

  // AI Audit and Anomaly Analyzer powered by Gemini
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

      const ai = new GoogleGenAI({
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

    } catch (error: any) {
      console.error("Gemini API call failed:", error);
      return res.status(500).json({
        status: "error",
        error: error?.message || "Internal server error"
      });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Veklom Server running on http://localhost:${PORT}`);
  });
}

startServer();
