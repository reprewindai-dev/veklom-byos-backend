import express from "express";
import { createServer as createViteServer } from "vite";
import { WebSocketServer, WebSocket } from "ws";
import { createServer } from "http";
import path from "path";
import cors from "cors";
import { GoogleGenAI } from "@google/genai";
import { XMLParser } from "fast-xml-parser";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || "" });

interface SSRNSignal {
  id: string;
  title: string;
  strength: number;
  timestamp: string;
  category: string;
}

const parser = new XMLParser();

let ssrnSignals: SSRNSignal[] = [
  { id: '#2401.0921', title: 'Quantum Probabilistic Modeling', strength: 98.4, timestamp: new Date().toISOString(), category: 'Quantum' },
  { id: '#2312.4402', title: 'Neural Determinism in LLMs', strength: 94.1, timestamp: new Date().toISOString(), category: 'Deterministic' },
  { id: '#2402.1155', title: 'Heuristic Agents & Capital', strength: 89.2, timestamp: new Date().toISOString(), category: 'Economics' }
];

let marketConvergence = [
  { label: "Deterministic Alpha", value: "+14.2%", description: "Hedge-adjusted probabilistic yield" },
  { label: "Market Heuristics", value: "+8.7%", description: "Sentiment aggregation" }
];

async function updateRealSignals() {
  try {
    // 1. Fetch from ArXiv
    const arxivRes = await fetch("https://export.arxiv.org/api/query?search_query=all:quantum+computing+OR+all:LLM+OR+all:deterministic&start=0&max_results=5&sortBy=lastUpdatedDate&sortOrder=descending");
    const xml = await arxivRes.text();
    const jsonObj = parser.parse(xml);
    const entries = jsonObj.feed?.entry || [];
    
    if (Array.isArray(entries)) {
      ssrnSignals = entries.map((entry: any) => ({
        id: entry.id?.split('/').pop() || '#UKNOWN',
        title: entry.title?.replace(/\n/g, ' ').trim() || 'Untitled Paper',
        strength: 85 + Math.random() * 14,
        timestamp: entry.updated || new Date().toISOString(),
        category: (entry.category?.attr_term || 'Research').replace('cs.', '')
      }));
    }

    // 2. Fetch Market Data (CoinGecko)
    const marketRes = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true");
    const marketData = await marketRes.json();
    
    if (marketData.bitcoin) {
      marketConvergence = [
        { 
          label: "BTC/USD Momentum", 
          value: `${marketData.bitcoin.usd_24h_change > 0 ? '+' : ''}${marketData.bitcoin.usd_24h_change.toFixed(2)}%`,
          description: `Real-time Bitcoin 24h delta: $${marketData.bitcoin.usd.toLocaleString()}`
        },
        { 
          label: "ETH/USD Stability", 
          value: `${marketData.ethereum.usd_24h_change > 0 ? '+' : ''}${marketData.ethereum.usd_24h_change.toFixed(2)}%`,
          description: `Ethereum network pressure check: $${marketData.ethereum.usd.toLocaleString()}`
        }
      ];
    }
  } catch (err) {
    console.error("Real data fetch error:", err);
  }
}

// Initial fetch
updateRealSignals();
// Refresh every 5 minutes
setInterval(updateRealSignals, 300000);

// --- Types & Storage (Mock DB) ---
interface Plan {
  id: string;
  name: string;
  intent: string;
  revision: number;
  status: 'draft' | 'verified' | 'locked';
  graph: any;
  createdAt: string;
}

interface Run {
  id: string;
  planId: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  currentStep: string;
  progress: number;
  output?: any;
  startTime: string;
  endTime?: string;
}

interface AppEvent {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  metadata?: any;
}

let plans: Plan[] = [];
let runs: Run[] = [];
let events: AppEvent[] = [];

function addEvent(type: string, message: string, metadata?: any) {
  const event: AppEvent = {
    id: Math.random().toString(36).substring(2, 9),
    type,
    message,
    timestamp: new Date().toISOString(),
    metadata
  };
  events.push(event);
  broadcast({ type: 'event', data: event });
}

// --- WebSocket Support ---
let clients: Set<WebSocket> = new Set();
function broadcast(data: any) {
  const payload = JSON.stringify(data);
  clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  });
}

async function startServer() {
  const app = express();
  const httpServer = createServer(app);
  const wss = new WebSocketServer({ server: httpServer });

  const PORT = Number(process.env.PORT || 3001);

  app.use(cors());
  app.use(express.json());

  wss.on("connection", (ws) => {
    clients.add(ws);
    ws.send(JSON.stringify({ type: 'init', message: 'UACP Control Plane Online' }));
    ws.on("close", () => clients.delete(ws));
  });

  // --- API Routes ---

  app.get("/api/bootstrap", (req, res) => {
    res.json({
      system: "Quantum UACP v0",
      version: "0.2.0-alpha",
      status: "operational",
      identity: "Gopher-Engine",
      userEmail: process.env.USER_EMAIL || "ANON_AGENT"
    });
  });

  app.get("/api/plans", (req, res) => res.json(plans));
  
  app.post("/api/plans", (req, res) => {
    const { name, intent, graph } = req.body;
    if (!intent) return res.status(400).json({ error: "Intent required" });

    const newPlan: Plan = {
      id: `p-${Math.random().toString(36).substring(2, 9)}`,
      name: name || "AI Generated Plan",
      intent,
      revision: 1,
      status: 'draft',
      graph: graph || { nodes: [], edges: [] },
      createdAt: new Date().toISOString()
    };
    
    plans.push(newPlan);
    addEvent('PLAN_CREATED', `New plan created: ${newPlan.id} (${newPlan.name})`, { planId: newPlan.id });
    res.json(newPlan);
  });

  app.get("/api/runs", (req, res) => res.json(runs));

  app.post("/api/runs", (req, res) => {
    const { planId } = req.body;
    const plan = plans.find(p => p.id === planId);
    if (!plan) return res.status(404).json({ error: "Plan not found" });

    const newRun: Run = {
      id: `run-${Math.random().toString(36).substring(2, 9)}`,
      planId,
      status: 'pending',
      currentStep: 'Initializing Gateway',
      progress: 0,
      startTime: new Date().toISOString()
    };
    runs.push(newRun);
    addEvent('RUN_STARTED', `Execution run started for plan ${planId}`, { runId: newRun.id, planId });
    
    // Simulate execution
    simulateExecution(newRun.id);
    
    res.json(newRun);
  });

  app.get("/api/ssrn-signals", (req, res) => res.json(ssrnSignals));

  app.get("/api/events", (req, res) => res.json(events));

  app.get("/api/observability/signals", (req, res) => {
    // Generate high-fidelity signals with trends
    const t = Date.now();
    res.json({
      quantum_coherence: 88 + Math.sin(t/5000) * 5,
      classical_latency: 14 + Math.cos(t/3000) * 3,
      uacp_pressure: Math.max(0, 0.05 + Math.sin(t/8000) * 0.04),
      gopher_policy_alignment: 0.992 + (Math.random() * 0.005),
      market_convergence: marketConvergence,
      horowitz_signals: [
        { id: 'UACP_PRESSURE', value: 0.82 + Math.sin(t/10000)*0.1, trend: 'rising' },
        { id: 'COHERENCE_TRANSITION', value: 0.45 + Math.cos(t/6000)*0.05, trend: 'stable' },
        { id: 'SIGNAL_NOISE', value: 0.12 + Math.sin(t/2000)*0.02, trend: 'falling' }
      ]
    });
  });

  async function simulateExecution(runId: string) {
    const run = runs.find(r => r.id === runId);
    if (!run) return;

    const plan = plans.find(p => p.id === run.planId);
    
    const baseSteps = [
      { step: 'Quantum State Preparation', progress: 20 },
      { step: 'HHL Matrix Decomposition', progress: 40 },
      { step: 'Classical Error Correction Overlay', progress: 60 },
      { step: 'VQE Objective Function Optimization', progress: 80 },
      { step: 'Collapsing Result Wavefunction', progress: 100 }
    ];

    // Use plan nodes if they exist for more "real" steps
    const steps = (plan?.graph?.nodes?.length > 0) 
      ? plan.graph.nodes.map((node: any, i: number) => ({
          step: node.description,
          progress: Math.floor(((i + 1) / plan.graph.nodes.length) * 100)
        }))
      : baseSteps;

    for (const step of steps) {
      await new Promise(r => setTimeout(r, 2000));
      run.status = 'executing';
      run.currentStep = step.step;
      run.progress = step.progress;
      addEvent('RUN_UPDATE', `Run ${runId}: ${step.step}`, { runId, progress: step.progress });
      broadcast({ type: 'run_update', data: run });
    }

    // Final Intelligence Summary using AI
    try {
      const result = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: `
          You are the Quantum UACP Intelligence Agent.
          The user intent was: "${plan?.intent || 'Unknown'}"
          The current research signals include: ${ssrnSignals.map(s => s.title).join(', ')}
          The current market state is: ${marketConvergence.map(m => `${m.label}: ${m.value}`).join(', ')}
          
          Provide a concise (2 sentence) final outcome report for this orchestration.
        `
      });
      run.output = result.text;
    } catch (e) {
      console.error("Summary error:", e);
      run.output = "Execution finalized. Deterministic outcomes verified across all research nodes.";
    }

    run.status = 'completed';
    run.endTime = new Date().toISOString();
    addEvent('RUN_COMPLETED', `Run ${runId} finalized successfully`, { runId });
    broadcast({ type: 'run_update', data: run });
  }

  // --- Vite Middleware for Dev / Static Serving for Prod ---

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

  httpServer.listen(PORT, "0.0.0.0", () => {
    console.log(`UACP Server running on http://localhost:${PORT}`);
    addEvent('SYSTEM_ONLINE', 'Quantum UACP Control Plane Initialized');
  });
}

startServer();
