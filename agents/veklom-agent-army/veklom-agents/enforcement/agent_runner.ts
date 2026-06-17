/**
 * Veklom Agent Runner — OpenRouter-powered
 * Runs any of the 120 agents using OpenRouter's SDK
 * Models are selected per agent role (not hardcoded)
 * 
 * Usage: OPENROUTER_API_KEY=sk-or-... npx tsx agent_runner.ts --agent agent-001
 */

import { OpenRouter, tool, stepCountIs } from "@openrouter/sdk";
import { EventEmitter } from "eventemitter3";
import { z } from "zod";
import * as fs from "fs";
import * as path from "path";

const AGENT_MODEL_MAP: Record<string, string> = {
  // Engineering agents use fast, precise coding models
  "agent-001": "anthropic/claude-sonnet-4-5",
  "agent-002": "anthropic/claude-sonnet-4-5",
  "agent-008": "anthropic/claude-opus-4-5",  // Security needs deeper reasoning
  // Growth agents use fast models
  "agent-040": "google/gemini-2.5-flash",
  "agent-041": "google/gemini-2.5-flash",
  // Commander uses the most powerful
  "agent-000": "anthropic/claude-opus-4-5",
  // Research gets multi-model via OpenRouter auto
  "agent-063": "openrouter/auto",
  // Default for all others
  "default": "anthropic/claude-sonnet-4-5"
};

// Veklom MCP tools (these call your actual backend)
const veklomTools = {
  read_progress: tool({
    name: "read_progress",
    description: "Read PROGRESS.md from the Veklom repo",
    inputSchema: z.object({}),
    execute: async () => {
      // In production: SSH to server and cat PROGRESS.md
      return { content: "PROGRESS.md content would be fetched here" };
    }
  }),

  write_progress: tool({
    name: "write_progress",
    description: "Append an update to PROGRESS.md",
    inputSchema: z.object({
      agent_id: z.string(),
      update: z.string(),
      status: z.enum(["COMPLETE", "IN_PROGRESS", "BLOCKED"])
    }),
    execute: async ({ agent_id, update, status }) => {
      const entry = `\n## ${agent_id} Update — ${new Date().toISOString()}\n- ${update}\n- Status: ${status}\n`;
      // In production: SSH and append to PROGRESS.md
      console.log("PROGRESS.md update:", entry);
      return { appended: true, entry };
    }
  }),

  call_veklom_api: tool({
    name: "call_veklom_api",
    description: "Call the live Veklom backend API at https://veklom.com",
    inputSchema: z.object({
      method: z.enum(["GET", "POST", "PATCH", "DELETE"]),
      endpoint: z.string().describe("e.g. /api/v1/health"),
      body: z.record(z.unknown()).optional(),
      auth_token: z.string().optional()
    }),
    execute: async ({ method, endpoint, body, auth_token }) => {
      const url = `https://veklom.com${endpoint}`;
      const headers: Record<string, string> = {
        "Content-Type": "application/json"
      };
      if (auth_token) headers["Authorization"] = `Bearer ${auth_token}`;

      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined
      });
      const data = await res.json();
      return { status: res.status, data };
    }
  }),

  store_memory: tool({
    name: "store_memory",
    description: "Store a learning or decision in agent memory",
    inputSchema: z.object({
      content: z.string(),
      category: z.enum(["learning", "decision", "blocker", "pattern", "handoff"])
    }),
    execute: async ({ content, category }) => {
      // In production: call /api/v1/agent-memory/{agent_id}/remember
      console.log(`Memory stored [${category}]:`, content);
      return { stored: true };
    }
  })
};

async function runAgent(agentId: string, task: string) {
  const client = new OpenRouter({
    apiKey: process.env.OPENROUTER_API_KEY!
  });

  // Load mission file
  const missionPath = findMissionFile(agentId);
  const mission = missionPath ? fs.readFileSync(missionPath, "utf-8") : "";

  // Load relevant memories
  console.log(`🧠 Loading memories for ${agentId}...`);
  // In production: fetch from memory backend

  const model = AGENT_MODEL_MAP[agentId] || AGENT_MODEL_MAP["default"];
  console.log(`🤖 Running ${agentId} on ${model}`);
  console.log(`📋 Task: ${task}\n`);

  const result = client.callModel({
    model,
    instructions: `${mission}\n\nYou are ${agentId}. Execute your mission. Use tools to interact with the Veklom backend.`,
    input: [{ role: "user", content: task }],
    tools: Object.values(veklomTools),
    stopWhen: [stepCountIs(10)]
  });

  for await (const item of result.getItemsStream()) {
    if (item.type === "message") {
      const text = item.content?.find((c: any) => c.type === "output_text");
      if (text && "text" in text) process.stdout.write(text.text);
    } else if (item.type === "function_call" && item.status === "completed") {
      console.log(`\n🔧 Tool: ${item.name}`);
    }
  }

  console.log("\n✅ Agent session complete");
}

function findMissionFile(agentId: string): string | null {
  const dirs = [
    "agents/phase0-scaffolding",
    "agents/phase1-engineering",
    "agents/phase2-vendor-acquisition",
    "agents/phase3-user-acquisition",
    "agents/phase4-retention-revenue",
    "agents/phase5-daily-operations",
    "agents/security-force",
    "agents/rag-knowledge",
    "agents/hrm-workforce"
  ];
  const num = agentId.replace("agent-", "");
  for (const dir of dirs) {
    const files = fs.existsSync(dir) ? fs.readdirSync(dir) : [];
    const match = files.find(f => f.startsWith(`agent-${num}-`));
    if (match) return path.join(dir, match);
  }
  return null;
}

// CLI entry
const args = process.argv.slice(2);
const agentFlag = args.indexOf("--agent");
const taskFlag = args.indexOf("--task");
const agentId = agentFlag >= 0 ? args[agentFlag + 1] : "agent-000";
const task = taskFlag >= 0 ? args[taskFlag + 1] : "Read PROGRESS.md and report current status";

runAgent(agentId, task).catch(console.error);
