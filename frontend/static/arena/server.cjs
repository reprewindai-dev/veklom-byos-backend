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
var import_url = require("url");
var import_vite = require("vite");
var import_genai = require("@google/genai");
var import_dotenv = __toESM(require("dotenv"), 1);
var import_meta = {};
import_dotenv.default.config();
var __filename = (0, import_url.fileURLToPath)(import_meta.url);
var __dirname = import_path.default.dirname(__filename);
var app = (0, import_express.default)();
var PORT = 3e3;
app.use(import_express.default.json());
var ai = new import_genai.GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      "User-Agent": "aistudio-build"
    }
  }
});
function estimateTokens(text) {
  return Math.ceil(text.length / 4);
}
app.post("/api/simulate/turn", async (req, res) => {
  try {
    const { input, workflowType, currentAgent, historyLog, stepInstruction } = req.body;
    if (!currentAgent) {
      return res.status(400).json({ error: "Missing active agent configuration." });
    }
    const tStart = Date.now();
    let prompt = "";
    if (workflowType === "sequential") {
      const previousOutputContext = historyLog && historyLog.length > 0 ? historyLog.map((log) => `[Agent: ${log.agentName} (${log.role})]
${log.output}`).join("\n\n---\n\n") : "None (This is the primary workflow starting point).";
      prompt = `You are part of a coordinated multi-agent sequential pipeline to solve this task:

### CORE MISSION BRIEF
"${input}"

### CURRENT PIPELINE PROGRESS (PREVIOUS STEPS OUTPUT)
${previousOutputContext}

### YOUR CURRENT ASSIGNED STEP INSTRUCTION
Resource specification step: "${stepInstruction || "Analyze and contribute based on your role."}"

=======================================================
Your Profile:
- Name: ${currentAgent.name}
- Specialized Role: ${currentAgent.role}
- Guideline Instructions: ${currentAgent.systemInstruction}

GENERATE YOUR DETAILED CONTRIBUTION NOW. Enhance, refine, or build on top of any previous progress. Be concrete, technical, and complete (avoid generic or vague summaries). Provide code blocks, specifications, outlines, or copy where relevant. Speak as your character. Write in standard markdown. Do not repeat previous outputs unless explicitly modifying them.`;
    } else {
      const chatContext = historyLog && historyLog.length > 0 ? historyLog.map((log) => `[${log.agentName} | ${log.role}]: ${log.output}`).join("\n\n") : "The meeting has just begun. No comments have been shared yet.";
      prompt = `You are a key committee member in an active collaborative multi-agent brainstorming session.

### BRAND MISSION / OBJECTIVE BRIEF
"${input}"

### ACTIVE MEETING ROOM CHAT HISTORY
${chatContext}

=======================================================
Your Profile:
- Name: ${currentAgent.name}
- Specialized Role: ${currentAgent.role}
- Personality & Directives: ${currentAgent.systemInstruction}

IT IS NOW YOUR TURN TO CONTRIBUTE TO THE FEEDBACK LOOP. 
Add your character voice to the discussion. React dynamically, challenge potential bugs/flaws constructively, suggest creative shifts, or propose concrete slogans/copy based on the conversation history. Keep your response conversational, concise, and focused (usually 1-3 highly punchy paragraphs). Write in markdown. Address other panel members naturally if appropriate.`;
    }
    const modelToUse = currentAgent.model || "gemini-3.5-flash";
    const response = await ai.models.generateContent({
      model: modelToUse,
      contents: prompt,
      config: {
        temperature: currentAgent.temperature ?? 0.7
      }
    });
    const outputText = response.text || "No response received from agent.";
    const durationMs = Date.now() - tStart;
    const tokensUsed = estimateTokens(prompt) + estimateTokens(outputText);
    return res.json({
      success: true,
      log: {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        agentId: currentAgent.id,
        agentName: currentAgent.name,
        avatar: currentAgent.avatar,
        color: currentAgent.color,
        role: currentAgent.role,
        inputUsed: prompt,
        output: outputText,
        durationMs,
        tokensUsed,
        modelUsed: modelToUse,
        completedAt: (/* @__PURE__ */ new Date()).toISOString()
      }
    });
  } catch (error) {
    console.error("Gemini turn simulation failed:", error);
    return res.status(500).json({
      error: "Agent computation failed",
      details: error.message || error
    });
  }
});
app.post("/api/simulate", async (req, res) => {
  try {
    const { input, workflowType, agents, steps, discussionTurns } = req.body;
    if (!agents || agents.length === 0) {
      return res.status(400).json({ error: "No agents in workspace config." });
    }
    const tStartTotal = Date.now();
    const logs = [];
    if (workflowType === "sequential") {
      for (const step of steps) {
        const agent = agents.find((a) => a.id === step.agentId);
        if (!agent) continue;
        const previousOutputContext = logs.length > 0 ? logs.map((log) => `[Agent: ${log.agentName} (${log.role})]
${log.output}`).join("\n\n---\n\n") : "None (This is the primary workflow starting point).";
        const prompt = `You are part of a coordinated multi-agent sequential pipeline to solve this task:

### CORE MISSION BRIEF
"${input}"

### CURRENT PIPELINE PROGRESS (PREVIOUS STEPS OUTPUT)
${previousOutputContext}

### YOUR CURRENT ASSIGNED STEP INSTRUCTION
Resource specification step: "${step.instruction || "Analyze and contribute based on your role."}"

=======================================================
Your Profile:
- Name: ${agent.name}
- Specialized Role: ${agent.role}
- Guideline Instructions: ${agent.systemInstruction}

GENERATE YOUR DETAILED CONTRIBUTION NOW. Enhance, refine, or build on top of any previous progress. Be concrete, technical, and complete (avoid generic or vague summaries). Provide code blocks, specifications, outlines, or copy where relevant. Speak as your character. Write in standard markdown. Do not repeat previous outputs unless explicitly modifying them.`;
        const tStart = Date.now();
        const response = await ai.models.generateContent({
          model: agent.model || "gemini-3.5-flash",
          contents: prompt,
          config: {
            temperature: agent.temperature ?? 0.7
          }
        });
        const outputText = response.text || "No response received from agent.";
        const durationMs = Date.now() - tStart;
        const tokensUsed = estimateTokens(prompt) + estimateTokens(outputText);
        logs.push({
          id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
          agentId: agent.id,
          agentName: agent.name,
          avatar: agent.avatar,
          color: agent.color,
          role: agent.role,
          inputUsed: prompt,
          output: outputText,
          durationMs,
          tokensUsed,
          modelUsed: agent.model || "gemini-3.5-flash",
          completedAt: (/* @__PURE__ */ new Date()).toISOString()
        });
      }
    } else {
      const turns = discussionTurns || 3;
      for (let i = 0; i < turns; i++) {
        const agent = agents[i % agents.length];
        const chatContext = logs.length > 0 ? logs.map((log) => `[${log.agentName} | ${log.role}]: ${log.output}`).join("\n\n") : "The meeting has just begun. No comments have been shared yet.";
        const prompt = `You are a key committee member in an active collaborative multi-agent brainstorming session.

### BRAND MISSION / OBJECTIVE BRIEF
"${input}"

### ACTIVE MEETING ROOM CHAT HISTORY
${chatContext}

=======================================================
Your Profile:
- Name: ${agent.name}
- Specialized Role: ${agent.role}
- Personality & Directives: ${agent.systemInstruction}

IT IS NOW YOUR TURN TO CONTRIBUTE TO THE FEEDBACK LOOP. 
Add your character voice to the discussion. React dynamically, challenge potential bugs/flaws constructively, suggest creative shifts, or propose concrete slogans/copy based on the conversation history. Keep your response conversational, concise, and focused (usually 1-3 highly punchy paragraphs). Write in markdown. Address other panel members naturally if appropriate.`;
        const tStart = Date.now();
        const response = await ai.models.generateContent({
          model: agent.model || "gemini-3.5-flash",
          contents: prompt,
          config: {
            temperature: agent.temperature ?? 0.7
          }
        });
        const outputText = response.text || "No response received from agent.";
        const durationMs = Date.now() - tStart;
        const tokensUsed = estimateTokens(prompt) + estimateTokens(outputText);
        logs.push({
          id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
          agentId: agent.id,
          agentName: agent.name,
          avatar: agent.avatar,
          color: agent.color,
          role: agent.role,
          inputUsed: prompt,
          output: outputText,
          durationMs,
          tokensUsed,
          modelUsed: agent.model || "gemini-3.5-flash",
          completedAt: (/* @__PURE__ */ new Date()).toISOString()
        });
      }
    }
    const finalOutput = logs.length > 0 ? logs[logs.length - 1].output : "No output generated.";
    const totalDurationMs = Date.now() - tStartTotal;
    return res.json({
      success: true,
      logs,
      finalOutput,
      totalDurationMs
    });
  } catch (error) {
    console.error("Full simulation failed:", error);
    return res.status(500).json({
      error: "Simulation run failed",
      details: error.message || error
    });
  }
});
async function setupViteStaticServer() {
  if (process.env.NODE_ENV !== "production") {
    console.log("Starting server in DEVELOPMENT mode with Vite Middleware...");
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    console.log("Starting server in PRODUCTION mode...");
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(import_path.default.join(distPath, "index.html"));
    });
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server fully online, listening on http://localhost:${PORT}`);
  });
}
setupViteStaticServer();
//# sourceMappingURL=server.cjs.map
