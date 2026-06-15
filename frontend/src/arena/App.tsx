import React, { useState, useEffect, useRef } from "react";
import { 
  Layers, 
  Users, 
  Play, 
  SkipForward, 
  RotateCcw, 
  Plus, 
  Trash2, 
  Edit3, 
  Save, 
  Check, 
  Code, 
  Megaphone, 
  Gamepad2, 
  Settings2, 
  Sparkles, 
  Send, 
  Copy, 
  HelpCircle,
  FileText,
  UserCheck,
  CheckCircle,
  Clock,
  Coins,
  Cpu,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  PlusCircle,
  X,
  Database,
  Mail,
  GitBranch,
  Flame,
  ShieldAlert
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Agent, PipelineStep, WorkflowType, StepLog, PresetTemplate } from "./types";
import { PRESET_TEMPLATES } from "./templates";
import CharacterCreator from "./components/CharacterCreator";
import AuthorityScenarios from "./components/AuthorityScenarios";
import { TelemetryPanel } from "../components/TelemetryPanel";

// Default Agents list if no template is loaded
const DEFAULT_AGENTS: Agent[] = [
  {
    id: "writer",
    name: "Genevieve (Writer)",
    role: "Content Creator",
    systemInstruction: "You are a witty, eloquent, and creative creative writer. Your job is to draft engaging stories, marketing drafts, or narrative pitches. Focus on descriptive metaphors, emotional depth, and elegant structure.",
    temperature: 0.8,
    model: "gemini-3.5-flash",
    avatar: "✍️",
    color: "violet"
  },
  {
    id: "critic",
    name: "Marcus (Critic)",
    role: "Editorial Director",
    systemInstruction: "You are an analytical, direct, and slightly cynical content critic. Your job is to analyze literary contributions, find logic holes, point out overly-flowery vocabulary, refine pacing, and suggest actual optimizations. Keep your reviews incredibly constructive but razor-sharp.",
    temperature: 0.4,
    model: "gemini-3.5-flash",
    avatar: "🧐",
    color: "amber"
  }
];

const DEFAULT_STEPS: PipelineStep[] = [
  {
    id: "step-1",
    agentId: "writer",
    instruction: "Compose a beautiful, short introductory paragraph describing a high-tech plant shop in Neo-Tokyo."
  },
  {
    id: "step-2",
    agentId: "critic",
    instruction: "Review the paragraph, highlight structural improvements, point out cliché keywords, and edit the paragraph to be extremely sharp."
  }
];

export default function App() {
  // Application State
  const [agents, setAgents] = useState<Agent[]>(PRESET_TEMPLATES[0].agents);
  const [workflowType, setWorkflowType] = useState<WorkflowType>(PRESET_TEMPLATES[0].workflowType);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(PRESET_TEMPLATES[0].steps);
  const [discussionTurns, setDiscussionTurns] = useState<number>(3);
  const [inputPrompt, setInputPrompt] = useState<string>(PRESET_TEMPLATES[0].defaultInput);
  
  // Simulation Simulation Runtime States
  const [simulationLogs, setSimulationLogs] = useState<StepLog[]>([]);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [simulationStatus, setSimulationStatus] = useState<"idle" | "ready" | "running" | "completed" | "error">("idle");
  const [apiError, setApiError] = useState<string | null>(null);
  
  // Custom Agent Form / Drawer State
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [showAgentModal, setShowAgentModal] = useState<boolean>(false);
  const [newAgentName, setNewAgentName] = useState<string>("");
  const [newAgentRole, setNewAgentRole] = useState<string>("");
  const [newAgentInstruction, setNewAgentInstruction] = useState<string>("");
  const [newAgentModel, setNewAgentModel] = useState<string>("gemini-3.5-flash");
  const [newAgentTemp, setNewAgentTemperature] = useState<number>(0.7);
  const [newAgentAvatar, setNewAgentAvatar] = useState<string>("🤖");
  const [newAgentColor, setNewAgentColor] = useState<string>("blue");

  // Selection Template state
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>(PRESET_TEMPLATES[0].id);

  // Edit Log state (allows manually tweaking output of intermediate steps!)
  const [editingLogId, setEditingLogId] = useState<string | null>(null);
  const [editingLogText, setEditingLogText] = useState<string>("");

  // Copy success indicator
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Tabs states
  const [leftTab, setLeftTab] = useState<"workspace" | "creator">("workspace");
  const [rightTab, setRightTab] = useState<"pipeline" | "authority">("pipeline");

  // Callback for custom character creator
  const handleCustomAgentCreated = (newAgent: Agent) => {
    setAgents(prev => [...prev, newAgent]);
    if (workflowType === "sequential") {
      setPipelineSteps(prev => [...prev, {
        id: `step-${Date.now()}`,
        agentId: newAgent.id,
        instruction: `Analyze and contribute based on specialized skill set for role: ${newAgent.role}`
      }]);
    }
    setLeftTab("workspace");
  };

  // Auto-ref for scrolling simulation console to bottom
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [simulationLogs, activeStepIndex, isSimulating]);

  // Load Preset Template
  const handleSelectTemplate = (template: PresetTemplate) => {
    setSelectedTemplateId(template.id);
    setAgents(JSON.parse(JSON.stringify(template.agents)));
    setWorkflowType(template.workflowType);
    setPipelineSteps(JSON.parse(JSON.stringify(template.steps || [])));
    if (template.discussionTurns) {
      setDiscussionTurns(template.discussionTurns);
    }
    setInputPrompt(template.defaultInput);
    
    // Reset simulation
    setSimulationLogs([]);
    setActiveStepIndex(-1);
    setSimulationStatus("idle");
    setApiError(null);
  };

  // Reset current workspace simulation state
  const handleResetSimulation = () => {
    setSimulationLogs([]);
    setActiveStepIndex(-1);
    setSimulationStatus("idle");
    setApiError(null);
  };

  // Run the ENTIRE Simulation automatically on the backend
  const handleRunFullSimulation = async () => {
    if (!inputPrompt.trim()) {
      setApiError("Please provide an initial start prompt first.");
      return;
    }
    setApiError(null);
    setIsSimulating(true);
    setSimulationStatus("running");
    setSimulationLogs([]);
    setActiveStepIndex(0);

    try {
      const response = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: inputPrompt,
          workflowType,
          agents,
          steps: pipelineSteps,
          discussionTurns,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to execute workflow simulation.");
      }

      setSimulationLogs(data.logs);
      setSimulationStatus("completed");
      setActiveStepIndex(data.logs.length);
    } catch (err: any) {
      console.error(err);
      setApiError(err.message || "An unexpected error occurred during execution.");
      setSimulationStatus("error");
    } finally {
      setIsSimulating(false);
    }
  };

  // Initialize Step-by-Step Manual Arena Run
  const handleInitializeManualArena = () => {
    if (!inputPrompt.trim()) {
      setApiError("Please provide an initial prompt brief first.");
      return;
    }
    setSimulationLogs([]);
    setApiError(null);
    setActiveStepIndex(0);
    setSimulationStatus("ready");
  };

  // Run single manual step/turn in character
  const handleExecuteSingleTurn = async () => {
    if (workflowType === "sequential" && activeStepIndex >= pipelineSteps.length) {
      setSimulationStatus("completed");
      return;
    }
    if (workflowType === "collaboration" && activeStepIndex >= discussionTurns) {
      setSimulationStatus("completed");
      return;
    }

    setApiError(null);
    setIsSimulating(true);

    const prevStatus = simulationStatus;
    setSimulationStatus("running");

    try {
      let currentAgent: Agent;
      let stepInstruction = "";

      if (workflowType === "sequential") {
        const step = pipelineSteps[activeStepIndex];
        currentAgent = agents.find(a => a.id === step.agentId) || agents[0];
        stepInstruction = step.instruction;
      } else {
        // Collaboration round robin turn selection
        currentAgent = agents[activeStepIndex % agents.length];
        stepInstruction = "Collaborative response & brainstorming feedback loop.";
      }

      const response = await fetch("/api/simulate/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: inputPrompt,
          workflowType,
          currentAgent,
          historyLog: simulationLogs,
          stepInstruction,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Turn execution failed.");
      }

      setSimulationLogs(prev => [...prev, data.log]);
      const nextIndex = activeStepIndex + 1;
      setActiveStepIndex(nextIndex);

      // Check if finished
      const maxSteps = workflowType === "sequential" ? pipelineSteps.length : discussionTurns;
      if (nextIndex >= maxSteps) {
        setSimulationStatus("completed");
      } else {
        setSimulationStatus("ready");
      }
    } catch (err: any) {
      console.error(err);
      setApiError(err.message || "An unexpected error occurred during turn execution.");
      setSimulationStatus("error");
    } finally {
      setIsSimulating(false);
    }
  };

  // Editing Agent Profile
  const handleOpenAddAgent = () => {
    setEditingAgent(null);
    setNewAgentName("");
    setNewAgentRole("");
    setNewAgentInstruction("");
    setNewAgentModel("gemini-3.5-flash");
    setNewAgentTemperature(0.7);
    setNewAgentAvatar("🤖");
    setNewAgentColor("blue");
    setShowAgentModal(true);
  };

  const handleOpenEditAgent = (agent: Agent) => {
    setEditingAgent(agent);
    setNewAgentName(agent.name);
    setNewAgentRole(agent.role);
    setNewAgentInstruction(agent.systemInstruction);
    setNewAgentModel(agent.model);
    setNewAgentTemperature(agent.temperature);
    setNewAgentAvatar(agent.avatar);
    setNewAgentColor(agent.color);
    setShowAgentModal(true);
  };

  const handleSaveAgent = () => {
    if (!newAgentName.trim() || !newAgentRole.trim() || !newAgentInstruction.trim()) {
      alert("Please fill in Name, Role, and system instructions.");
      return;
    }

    if (editingAgent) {
      // Edit mode
      setAgents(prev => prev.map(a => a.id === editingAgent.id ? {
        ...a,
        name: newAgentName,
        role: newAgentRole,
        systemInstruction: newAgentInstruction,
        model: newAgentModel,
        temperature: newAgentTemp,
        avatar: newAgentAvatar,
        color: newAgentColor
      } : a));
    } else {
      // Create Mode
      const newId = `agent-${Date.now()}`;
      const newAgent: Agent = {
        id: newId,
        name: newAgentName,
        role: newAgentRole,
        systemInstruction: newAgentInstruction,
        temperature: newAgentTemp,
        model: newAgentModel,
        avatar: newAgentAvatar,
        color: newAgentColor
      };
      setAgents(prev => [...prev, newAgent]);

      // If sequential, automatically add an initial dummy step for this new agent
      if (workflowType === "sequential") {
        setPipelineSteps(prev => [...prev, {
          id: `step-${Date.now()}`,
          agentId: newId,
          instruction: `Collaborate to review and draft content for: "${newAgentRole}"`
        }]);
      }
    }

    // Reset modals
    setShowAgentModal(false);
    setEditingAgent(null);
  };

  const handleDeleteAgent = (agentId: string) => {
    if (agents.length <= 1) {
      alert("A workspace must contain at least 1 design agent.");
      return;
    }
    setAgents(prev => prev.filter(a => a.id !== agentId));
    setPipelineSteps(prev => prev.filter(s => s.agentId !== agentId));
    handleResetSimulation();
  };

  // Pipeline Step CRUD helpers
  const handleUpdateStepInstruction = (stepId: string, newInstruction: string) => {
    setPipelineSteps(prev => prev.map(s => s.id === stepId ? { ...s, instruction: newInstruction } : s));
  };

  const handleUpdateStepAgent = (stepId: string, agentId: string) => {
    setPipelineSteps(prev => prev.map(s => s.id === stepId ? { ...s, agentId } : s));
  };

  const handleMoveStepUp = (index: number) => {
    if (index === 0) return;
    setPipelineSteps(prev => {
      const nextSteps = [...prev];
      const temp = nextSteps[index];
      nextSteps[index] = nextSteps[index - 1];
      nextSteps[index - 1] = temp;
      return nextSteps;
    });
    handleResetSimulation();
  };

  const handleMoveStepDown = (index: number) => {
    if (index === pipelineSteps.length - 1) return;
    setPipelineSteps(prev => {
      const nextSteps = [...prev];
      const temp = nextSteps[index];
      nextSteps[index] = nextSteps[index + 1];
      nextSteps[index + 1] = temp;
      return nextSteps;
    });
    handleResetSimulation();
  };

  const handleAddPipelineStep = (agentId: string) => {
    setPipelineSteps(prev => [...prev, {
      id: `step-${Date.now()}`,
      agentId,
      instruction: "Draft or review progress based on your specialized domain instruction."
    }]);
    handleResetSimulation();
  };

  const handleDeletePipelineStep = (stepId: string) => {
    if (pipelineSteps.length <= 1) {
      alert("A sequential pipeline must contain at least one step node.");
      return;
    }
    setPipelineSteps(prev => prev.filter(s => s.id !== stepId));
    handleResetSimulation();
  };

  // Save manually edited agent output to allow mid-simulation adjustments
  const handleSaveEditedOutput = (logId: string) => {
    setSimulationLogs(prev => prev.map(log => log.id === logId ? { ...log, output: editingLogText } : log));
    setEditingLogId(null);
  };

  // Copy result utility
  const handleCopyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  // Custom styled markdown block tokenizer to capture lists and code blocks beautifully
  const renderTextContent = (text: string) => {
    if (!text) return null;

    // Simple code block parser & general text formatter
    const blocks = text.split(/(```[\s\S]*?```)/g);

    return blocks.map((block, idx) => {
      if (block.startsWith("```")) {
        const lines = block.split("\n");
        const language = lines[0].replace("```", "").trim() || "code";
        const code = lines.slice(1, -1).join("\n");
        return (
          <div key={idx} className="my-4 rounded-lg overflow-hidden border border-slate-700 bg-slate-950 font-mono text-[13px] md:text-sm shadow-inner">
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900/80 text-[11px] text-slate-400 select-none">
              <span className="flex items-center gap-1.5 font-sans font-medium uppercase tracking-wider text-slate-400">
                <Code className="w-3.5 h-3.5 text-indigo-400" /> {language}
              </span>
              <button 
                onClick={() => handleCopyToClipboard(code, `code-${idx}`)}
                className="hover:text-white transition-colors duration-150 py-0.5 px-2 rounded hover:bg-slate-800 flex items-center gap-1 text-[10px]"
              >
                {copiedId === `code-${idx}` ? "Copied!" : "Copy Raw"}
              </button>
            </div>
            <pre className="p-4 overflow-x-auto text-emerald-400 font-medium leading-relaxed font-mono">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // Convert inline markdown ticks format
      const parts = block.split(/(`[^`]+`)/g);

      return (
        <p key={idx} className="leading-relaxed text-[14px] md:text-[15px] space-y-2 whitespace-pre-wrap">
          {parts.map((part, pIdx) => {
            if (part.startsWith("`") && part.endsWith("`")) {
              return (
                <code key={pIdx} className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono border border-slate-800 text-sm">
                  {part.slice(1, -1)}
                </code>
              );
            }
            return part;
          })}
        </p>
      );
    });
  };

  const getAccentClass = (color: string) => {
    switch(color) {
      case "emerald": return { border: "border-emerald-500/30", text: "text-emerald-400", bg: "bg-emerald-500/10", ribbon: "bg-emerald-500" };
      case "blue": return { border: "border-cyan-500/30", text: "text-cyan-400", bg: "bg-cyan-500/10", ribbon: "bg-cyan-500" };
      case "amber": return { border: "border-amber-500/30", text: "text-amber-400", bg: "bg-amber-500/10", ribbon: "bg-amber-500" };
      case "purple": return { border: "border-purple-500/30", text: "text-purple-400", bg: "bg-purple-500/10", ribbon: "bg-purple-500" };
      case "rose": return { border: "border-rose-500/30", text: "text-rose-400", bg: "bg-rose-500/10", ribbon: "bg-rose-500" };
      case "cyan": return { border: "border-cyan-500/30", text: "text-cyan-400", bg: "bg-cyan-500/10", ribbon: "bg-cyan-500" };
      case "violet": return { border: "border-violet-500/30", text: "text-violet-400", bg: "bg-violet-500/10", ribbon: "bg-violet-500" };
      case "fuchsia": return { border: "border-fuchsia-500/30", text: "text-fuchsia-400", bg: "bg-fuchsia-500/10", ribbon: "bg-fuchsia-500" };
      case "pink": return { border: "border-pink-500/30", text: "text-pink-400", bg: "bg-pink-500/10", ribbon: "bg-pink-500" };
      default: return { border: "border-neutral-700", text: "text-neutral-300", bg: "bg-neutral-800/10", ribbon: "bg-neutral-550" };
    }
  };

  return (
    <div className="min-h-screen bg-[#080808] text-[#e0e0e0] flex flex-col font-mono overflow-x-hidden antialiased relative">
      
      {/* Mesh dot background overlay */}
      <div className="fixed inset-0 opacity-[0.035] pointer-events-none select-none bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px] z-0"></div>

      {/* HEADER SECTION */}
      <header className="border-b border-neutral-800 bg-neutral-900/20 backdrop-blur sticky top-0 z-30 px-6 py-4 flex flex-col md:flex-row items-stretch justify-between gap-6 z-10">
        <div className="flex flex-col">
          <span className="text-[9px] text-cyan-500 tracking-widest uppercase mb-1 font-bold">SYSTEM HEADER // INITIALIZATION & ORCHESTRATION</span>
          <h1 className="text-2xl md:text-3xl font-black tracking-tighter text-white font-sans flex items-center gap-2">
            VEKLOM AUTHORITY ARENA
            <span className="text-[9px] tracking-widest font-mono uppercase bg-neutral-800 text-cyan-400 border border-neutral-700 px-2 py-0.5 rounded font-bold">
              LAB-V2.1
            </span>
          </h1>
          <p className="text-[11px] text-neutral-500 mt-1 uppercase tracking-wide">Runtime Enforcement Simulation Lab</p>
        </div>

        {/* Dynamic Telemetry Stats */}
        <div className="flex flex-wrap items-center gap-6 text-[10px] text-neutral-400 font-mono">
          <div className="flex flex-col items-end">
            <span className="text-orange-500 font-bold uppercase tracking-widest">ACTIVE ENGINES</span>
            <span>V2.1.0 // {agents.length} AGENT CHANNELS</span>
          </div>
          <div className="flex flex-col items-end border-l border-neutral-800 pl-6">
            <span className="text-cyan-400 font-bold uppercase tracking-widest">EST. TOKENS</span>
            <span>{simulationLogs.reduce((sum, item) => sum + (item.tokensUsed || 0), 0).toLocaleString()} UNITS</span>
          </div>
          <div className="flex flex-col items-end border-l border-neutral-800 pl-6">
            <span className="text-violet-400 font-bold uppercase tracking-widest">LAPSE TIME</span>
            <span>{(simulationLogs.reduce((sum, item) => sum + item.durationMs, 0) / 1000).toFixed(1)}S TOTAL</span>
          </div>
        </div>
      </header>

      {/* CORE BENTO GRID WORKSPACE */}
      <main className="flex-1 w-full max-w-[1700px] mx-auto p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch z-10 relative">
        
        {/* COLUMN 1: CONFIGURATION & MANAGEMENT (5/12 width) */}
        <section className="lg:col-span-12 xl:col-span-5 flex flex-col gap-5 bg-transparent" id="workspace-sidebar">
          
          {/* Sub-Tabs Selector inside Column 1 */}
          <div className="flex bg-neutral-950 p-1 rounded-lg border border-neutral-850">
            <button 
              onClick={() => setLeftTab("workspace")}
              className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all cursor-pointer ${
                leftTab === "workspace" 
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" 
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              1. Scenario Registry
            </button>
            <button 
              onClick={() => setLeftTab("creator")}
              className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all cursor-pointer ${
                leftTab === "creator" 
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" 
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              2. Authority Profile Builder
            </button>
          </div>

          {leftTab === "workspace" ? (
            <>
              {/* Preset Core Scenarios Selection */}
              <div className="bg-neutral-900/30 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4 backdrop-blur-sm relative overflow-hidden group">
                <div className="flex justify-between items-center pb-2 border-b border-neutral-800">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[#a0a0a0] flex items-center gap-1.5 font-mono">
                    [01] SELECT RUNTIME SCENARIO
                  </h2>
                  <span className="text-[9px] bg-neutral-950 px-2 py-0.5 rounded text-neutral-500 font-mono">READY</span>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {PRESET_TEMPLATES.map((tmpl) => {
                    const isSelected = selectedTemplateId === tmpl.id;
                    return (
                      <button
                        key={tmpl.id}
                        onClick={() => handleSelectTemplate(tmpl)}
                        className={`text-left p-4 rounded border transition-all duration-250 cursor-pointer flex items-start gap-4 ${
                          isSelected 
                            ? "bg-cyan-500/5 border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.05)]" 
                            : "bg-neutral-900/20 border-neutral-850 hover:bg-neutral-800/20 hover:border-neutral-700"
                        }`}
                      >
                        <div className={`p-2 rounded border ${
                          isSelected 
                            ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/35" 
                            : "bg-neutral-950 text-neutral-600 border-neutral-850"
                        } transition-colors`}>
                          {tmpl.icon === "Code" && <Code className="w-4 h-4" />}
                          {tmpl.icon === "Megaphone" && <Megaphone className="w-4 h-4" />}
                          {tmpl.icon === "Gamepad2" && <Gamepad2 className="w-4 h-4" />}
                          {tmpl.icon === "Database" && <Database className="w-4 h-4" />}
                          {tmpl.icon === "Mail" && <Mail className="w-4 h-4" />}
                          {tmpl.icon === "GitBranch" && <GitBranch className="w-4 h-4" />}
                          {tmpl.icon === "Coins" && <Coins className="w-4 h-4" />}
                          {tmpl.icon === "Flame" && <Flame className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0 font-mono">
                          <div className="flex items-center justify-between gap-2">
                            <span className={`text-[12px] font-bold uppercase tracking-wide truncate ${isSelected ? "text-cyan-400" : "text-neutral-200"}`}>
                              {tmpl.title}
                            </span>
                            <span className="text-[8px] tracking-widest px-1.5 py-0.5 rounded font-bold bg-neutral-950 text-neutral-500 border border-neutral-850 flex-shrink-0">
                              {tmpl.customTypeLabel || tmpl.workflowType.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-[11px] text-neutral-500 mt-1 lines-clamp-2 leading-relaxed lowercase">{tmpl.description}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Active Agents CONFIGURATION & LIST */}
              <div className="bg-neutral-900/30 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4 backdrop-blur-sm relative overflow-hidden flex-1 select-none">
                <div className="flex justify-between items-center pb-2 border-b border-neutral-800">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[#a0a0a0] flex items-center gap-1.5 font-mono">
                    [02] AGENT REGISTRY
                  </h2>
                  <span className="text-[9px] bg-neutral-950 px-2 py-0.5 rounded text-cyan-400 border border-neutral-800 font-bold uppercase font-mono tracking-wider">
                    0{agents.length} ACTIVE
                  </span>
                </div>

                {/* List of current Agents */}
                <div className="grid grid-cols-1 gap-3 overflow-y-auto max-h-[460px] pr-1 scrollbar-thin">
                  {agents.map((agent) => {
                    const stepCount = pipelineSteps.filter(s => s.agentId === agent.id).length;
                    const accent = getAccentClass(agent.color);
                    
                    return (
                      <div 
                        key={agent.id} 
                        className={`p-4 bg-neutral-950/40 hover:bg-neutral-950/80 border ${accent.border} rounded-md transition-all duration-200 flex items-start justify-between gap-3 group relative overflow-hidden`}
                      >
                        <div className="absolute top-0 left-0 w-[3px] h-full bg-cyan-700/70"></div>
                        
                        <div className="flex items-start gap-3.5 pl-1.5">
                          <div className="w-10 h-10 rounded bg-neutral-950 border border-neutral-800 flex items-center justify-center text-lg relative self-start flex-shrink-0 shadow-inner">
                            {agent.avatar}
                            <span className={`absolute bottom-0 right-0 w-2 h-2 rounded-full ring-1 ring-neutral-950 ${accent.ribbon}`}></span>
                          </div>
                          
                          <div className="flex-1 min-w-0 font-mono">
                            <div className="flex items-center gap-2">
                              <span className="text-[12px] font-bold uppercase text-white truncate">{agent.name}</span>
                              {workflowType === "sequential" && (
                                <span className="text-[8px] font-bold bg-neutral-900 border border-neutral-800 text-neutral-500 px-1.5 py-0.2 rounded font-semibold">
                                  {stepCount} NODE{stepCount === 1 ? "" : "S"}
                                </span>
                              )}
                            </div>
                            
                            <div className="text-[10px] text-cyan-400 font-semibold tracking-wider font-mono mt-0.5 uppercase">
                              ROLE: {agent.role}
                            </div>
                            
                            <p className="text-[10px] text-neutral-450 mt-1.5 line-clamp-2 leading-relaxed lowercase italic">
                              "{agent.systemInstruction}"
                            </p>
                            
                            <div className="flex items-center gap-2 mt-2.5 text-[9px] text-neutral-500 font-bold">
                              <span className="bg-neutral-900 px-2 py-0.5 rounded border border-neutral-850">
                                {agent.model.toUpperCase()}
                              </span>
                              <span className="bg-neutral-900 px-2 py-0.5 rounded border border-neutral-850">
                                TEMP={agent.temperature}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 self-start opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                          <button
                            onClick={() => handleOpenEditAgent(agent)}
                            className="p-1 px-1.5 bg-neutral-900 text-neutral-500 hover:text-cyan-400 border border-neutral-800 rounded transition-colors cursor-pointer text-[10px]"
                            title="Edit Agent Profile"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteAgent(agent.id)}
                            className="p-1 px-1.5 bg-neutral-900 text-neutral-500 hover:text-orange-500 border border-neutral-800 rounded transition-colors cursor-pointer text-[10px]"
                            title="Remove Agent"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <button 
                  onClick={handleOpenAddAgent}
                  className="mt-2 w-full py-2.5 bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 text-[10px] font-bold uppercase tracking-widest text-neutral-300 font-mono transition-all hover:text-white cursor-pointer active:scale-[0.99] flex items-center justify-center gap-2 rounded"
                >
                  <Plus className="w-3.5 h-3.5" /> Deploy New Entity
                </button>
              </div>
            </>
          ) : (
            <div className="bg-neutral-900/30 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4 backdrop-blur-sm relative overflow-hidden">
              <CharacterCreator onAgentCreated={handleCustomAgentCreated} />
            </div>
          )}
          
        </section>

        {/* COLUMN 2: SIMULATION SYSTEM & LOG TIMELINE (7/12 width) */}
        <section className="lg:col-span-12 xl:col-span-7 flex flex-col gap-5 animate-fadeIn" id="workspace-main">
          
          {/* Sub-Tabs Selector inside Column 2 */}
          <div className="flex bg-neutral-950 p-1 rounded-lg border border-neutral-850">
            <button 
              onClick={() => setRightTab("pipeline")}
              className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all cursor-pointer ${
                rightTab === "pipeline" 
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" 
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              Interactive Action Sandbox
            </button>
            <button 
              onClick={() => setRightTab("authority")}
              className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all cursor-pointer ${
                rightTab === "authority" 
                  ? "bg-violet-500/10 text-violet-400 border border-violet-500/20" 
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              Security Spine Enforcement Lab
            </button>
          </div>

          {rightTab === "pipeline" ? (
            <>
              {/* Main User Prompt / Goal Context Input */}
              <div className="bg-neutral-900/30 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4 backdrop-blur-sm relative overflow-hidden">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-widest font-mono text-[#a0a0a0]">
                [03] CHANNELS ORCHESTRATION INSTRUCTIONS
              </label>
              <textarea
                value={inputPrompt}
                onChange={(e) => {
                  setInputPrompt(e.target.value);
                  handleResetSimulation();
                }}
                placeholder="Declare what tasks, software elements, or slogan briefs you want the agent team to iterate on..."
                rows={3}
                className="w-full bg-black/60 p-4 border border-neutral-850 rounded text-neutral-200 placeholder-neutral-600 font-mono focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/10 text-xs md:text-sm resize-y leading-relaxed shadow-inner"
              />
            </div>

            {/* Workflow Mode Select & Variables */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-neutral-850/80">
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-neutral-500 font-mono uppercase font-bold">WORKFLOW ENGINE:</span>
                <div className="flex items-center gap-1.5 p-1 bg-black/40 rounded border border-neutral-850">
                  <button
                    onClick={() => {
                      setWorkflowType("sequential");
                      if (pipelineSteps.length === 0 && agents.length > 0) {
                        setPipelineSteps(agents.map(a => ({
                          id: `step-${Math.random()}`,
                          agentId: a.id,
                          instruction: "Analyze and build on the draft context."
                        })));
                      }
                      handleResetSimulation();
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1 text-[10px] uppercase font-bold tracking-wider transition-all cursor-pointer ${
                      workflowType === "sequential"
                        ? "bg-cyan-900/20 text-cyan-400 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.1)] rounded"
                        : "text-neutral-500 hover:text-neutral-300"
                    }`}
                  >
                    <Layers className="w-3 h-3" /> Sequential Pipeline
                  </button>
                  <button
                    onClick={() => {
                      setWorkflowType("collaboration");
                      handleResetSimulation();
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1 text-[10px] uppercase font-bold tracking-wider transition-all cursor-pointer ${
                      workflowType === "collaboration"
                        ? "bg-cyan-900/20 text-cyan-400 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.1)] rounded"
                        : "text-neutral-500 hover:text-neutral-300"
                    }`}
                  >
                    <Users className="w-3 h-3" /> Group Meeting
                  </button>
                </div>
              </div>

              {/* Turns config or pipeline count */}
              <div className="flex items-center gap-2">
                {workflowType === "collaboration" ? (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-neutral-500 font-mono uppercase">TURNS LIMIT:</span>
                    <select
                      value={discussionTurns}
                      onChange={(e) => {
                        setDiscussionTurns(Number(e.target.value));
                        handleResetSimulation();
                      }}
                      className="bg-neutral-950 border border-neutral-850 text-neutral-300 text-[10px] px-2.5 py-1 rounded font-mono focus:outline-none focus:border-cyan-500 cursor-pointer uppercase"
                    >
                      <option value={2}>02 TURNS</option>
                      <option value={3}>03 TURNS</option>
                      <option value={4}>04 TURNS</option>
                      <option value={5}>05 TURNS</option>
                      <option value={6}>06 TURNS</option>
                    </select>
                  </div>
                ) : (
                  <span className="text-[9px] uppercase tracking-wider font-mono bg-neutral-950 px-3 py-1.5 rounded border border-neutral-850 text-neutral-400">
                    <b className="font-bold text-neutral-200">{pipelineSteps.length}</b> CONNECTED PIPELINE NODES
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Sequential Pipeline Steps Node Editor (Sequential ONLY) */}
          {workflowType === "sequential" && (
            <div className="bg-neutral-900/30 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4 backdrop-blur-sm relative overflow-hidden">
              <h3 className="text-xs font-bold uppercase tracking-widest font-mono text-[#a0a0a0]">
                [04] PIPELINE STEP-BY-STEP SEQUENCING
              </h3>
              
              <div className="flex flex-col gap-3.5 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
                {pipelineSteps.map((step, idx) => {
                  const agent = agents.find(a => a.id === step.agentId) || agents[0];
                  return (
                    <div key={step.id} className="relative pl-6 border-l border-neutral-800 last:border-b-0 space-y-3 pb-3 last:pb-0">
                      {/* Interactive timing dots */}
                      <div className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 bg-neutral-700 rounded-full"></div>
                      
                      <div className="flex flex-wrap gap-3 items-center bg-[#0e0e0e]/60 p-3 rounded border border-neutral-850">
                        {/* Interactive Agent Select box */}
                        <div className="flex items-center gap-1.5 bg-neutral-950 px-2.5 py-1.5 rounded border border-neutral-850">
                          <span className="text-[12px]">{agent?.avatar}</span>
                          <select
                            value={step.agentId}
                            onChange={(e) => handleUpdateStepAgent(step.id, e.target.value)}
                            className="bg-transparent text-[10px] font-bold text-neutral-300 uppercase focus:outline-none cursor-pointer max-w-[110px] font-mono select-none"
                          >
                            {agents.map((ag) => (
                              <option key={ag.id} value={ag.id} className="bg-neutral-900 text-white font-mono lowercase">
                                {ag.name.split(" ")[0]} ({ag.role.includes("Node") ? ag.role : ag.role.slice(0, 15)})
                              </option>
                            ))}
                          </select>
                        </div>

                        <ChevronRight className="w-3 h-3 text-neutral-700 flex-shrink-0" />

                        {/* Inline instruction edit field */}
                        <div className="flex-1 min-w-[200px]">
                          <input
                            type="text"
                            value={step.instruction}
                            onChange={(e) => handleUpdateStepInstruction(step.id, e.target.value)}
                            placeholder="What specific tasks should this agent execute?"
                            className="w-full bg-neutral-950/60 border border-neutral-850 px-3 py-1.5 rounded text-xs focus:outline-none focus:border-cyan-500 focus:bg-neutral-950 text-neutral-200 font-mono"
                          />
                        </div>

                        {/* Custom Reordering Controls + Add next / Delete */}
                        <div className="flex items-center gap-1.5 bg-neutral-950/40 p-1 rounded border border-neutral-850/60 font-mono">
                          <button
                            onClick={() => handleMoveStepUp(idx)}
                            disabled={idx === 0}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              idx === 0 ? "text-neutral-800 cursor-not-allowed" : "text-neutral-400 hover:text-cyan-400 hover:bg-neutral-900"
                            }`}
                            title="Move Step Up"
                          >
                            <ChevronUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleMoveStepDown(idx)}
                            disabled={idx === pipelineSteps.length - 1}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              idx === pipelineSteps.length - 1 ? "text-neutral-800 cursor-not-allowed" : "text-neutral-400 hover:text-cyan-400 hover:bg-neutral-900"
                            }`}
                            title="Move Step Down"
                          >
                            <ChevronDown className="w-3.5 h-3.5" />
                          </button>
                          
                          <span className="w-px h-3.5 bg-neutral-800 mx-1"></span>

                          <button
                            onClick={() => handleAddPipelineStep(step.agentId)}
                            className="p-1 hover:bg-neutral-900 text-cyan-400 hover:text-cyan-300 rounded transition-colors cursor-pointer"
                            title="Split step node"
                          >
                            <PlusCircle className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeletePipelineStep(step.id)}
                            className="p-1 hover:bg-neutral-900 text-orange-500 hover:text-orange-400 rounded transition-colors cursor-pointer"
                            title="Remove Node"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Append Step Dynamic Control */}
              <div className="pt-3 border-t border-neutral-850 flex items-center justify-between gap-3 font-mono text-[10px] bg-neutral-950/20 p-2.5 rounded border border-neutral-850/60 mt-1">
                <span className="text-neutral-500 uppercase tracking-wider">Interactive Lab Assembly // SEKED_CHAIN:</span>
                <div className="flex items-center gap-2">
                  <select
                    id="append-agent-select"
                    className="bg-neutral-950 px-2.5 py-1 rounded border border-neutral-850 text-neutral-300 text-[10px] focus:outline-none cursor-pointer font-mono"
                  >
                    {agents.map(ag => (
                      <option key={ag.id} value={ag.id} className="bg-neutral-900">
                        {ag.avatar} {ag.name.split(" ")[0]} ({ag.role})
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => {
                      const selectEl = document.getElementById("append-agent-select") as HTMLSelectElement | null;
                      if (selectEl?.value) {
                        handleAddPipelineStep(selectEl.value);
                      }
                    }}
                    className="px-3 py-1 bg-cyan-650 hover:bg-cyan-500 text-neutral-950 font-bold uppercase tracking-wider rounded transition active:scale-95 cursor-pointer"
                  >
                    + Add Node
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* SIMULATION CONSOLE / ARENA STAGE PANEL */}
          <div className="bg-neutral-900 border border-neutral-800 rounded-lg overflow-hidden flex flex-col flex-1 shadow-[0_4px_24px_rgba(0,0,0,0.55)] bg-gradient-to-b from-neutral-900 to-[#0c0c0c] min-h-[460px]">
            
            {/* Arena Header Status + Telemetry */}
            <div className="p-4 border-b border-neutral-800 flex flex-col sm:flex-row justify-between items-start sm:items-center bg-black/40 gap-4 z-10 relative">
              <div className="flex items-center gap-3">
                <span className="flex h-2 w-2 relative">
                  {simulationStatus === "running" ? (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  ) : null}
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${
                    simulationStatus === "completed" ? "bg-cyan-500" :
                    simulationStatus === "running" ? "bg-cyan-400" :
                    simulationStatus === "ready" ? "bg-amber-500" :
                    simulationStatus === "error" ? "bg-orange-600" : "bg-neutral-700"
                  }`}></span>
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xs font-bold text-[#e0e0e0] uppercase tracking-widest font-mono">
                      Live Simulation View
                    </h2>
                    <span className="text-[7px] px-1.5 py-0.3 bg-cyan-950/40 text-cyan-400 border border-cyan-850/60 rounded uppercase font-bold tracking-wider">
                      Simulation Mode
                    </span>
                    <span className="text-[7px] px-1.5 py-0.3 bg-neutral-950 text-neutral-400 border border-neutral-850 rounded uppercase font-bold tracking-wider">
                      Backend Connected
                    </span>
                    <span className="text-[7px] px-1.5 py-0.3 bg-emerald-950/20 text-emerald-400 border border-emerald-900/30 rounded uppercase font-bold tracking-wider">
                      Evidence Verified
                    </span>
                  </div>
                  <span className="text-[9px] font-mono text-neutral-500 tracking-tighter block mt-0.5 font-semibold">
                    UPLINK STATUS: STABLE // PROCESSOR ENGINE ISOLATION ACTIVE · {logsTimelineTitle(simulationStatus).toUpperCase()}
                  </span>
                </div>
              </div>
              
              <div className="flex gap-4 text-[10px] font-mono text-neutral-500">
                <span>TOKENS/SEC: {simulationStatus === "running" ? "124.5" : "0.0"}</span>
                <span className="border-l border-neutral-800 pl-3 uppercase">Cluster: US-COGNITIVE-0</span>
              </div>
            </div>

            {/* Live Arena Timeline Flow Area */}
            <div className="flex-1 bg-black/95 p-5 min-h-[350px] max-h-[580px] overflow-y-auto flex flex-col gap-5 scrollbar-thin font-mono relative z-10">
              
              {/* Radial pattern within console */}
              <div className="absolute inset-0 opacity-[0.05] pointer-events-none" style={{ backgroundImage: "radial-gradient(circle, #222 1px, transparent 1px)", backgroundSize: "20px 20px" }}></div>

              {/* Welcoming instructions if no entries */}
              {simulationLogs.length === 0 && !isSimulating && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto self-center z-10 font-mono">
                  <div className="w-16 h-16 border border-dashed border-neutral-700 rounded-full flex items-center justify-center mb-5 relative">
                    <div className="w-10 h-10 border border-cyan-500/30 rounded-full flex items-center justify-center text-cyan-400 text-xs">
                      CORE
                    </div>
                  </div>
                  <h4 className="text-[12px] font-bold text-neutral-300 uppercase tracking-widest">The Arena is Silent // TTY:00</h4>
                  <p className="text-[11px] text-neutral-500 mt-2.5 leading-relaxed lowercase">
                    Launch the automated production script to witness Gemini orchestrating step-by-step sequential feedback chains, or start the **Interactive Arena** to drive node-by-node executions manually.
                  </p>
                  
                  {/* Preset Quick Actions summary display */}
                  <div className="mt-6 flex flex-wrap gap-2.5 justify-center">
                    <span className="text-[9px] font-mono bg-neutral-900 py-1 px-2.5 rounded border border-neutral-800 text-neutral-400 font-semibold uppercase">
                      UPLINK: STABLE
                    </span>
                    <span className="text-[9px] font-mono bg-neutral-900 py-1 px-2.5 rounded border border-neutral-800 text-neutral-400 font-semibold uppercase">
                      SECURE SANDBOX
                    </span>
                  </div>
                </div>
              )}

              {/* TIMELINE LOGGING LINES */}
              <AnimatePresence initial={false}>
                {simulationLogs.map((log, idx) => {
                  const isEditing = editingLogId === log.id;
                  
                  return (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="p-4 bg-neutral-900/40 border border-neutral-850 hover:border-neutral-800 rounded flex flex-col gap-3.5 relative transition-all duration-150 group z-10"
                    >
                      {/* Top Agent Identity Tag & Header Block */}
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800/60 pb-2 text-[10px] text-neutral-500">
                        <div className="flex items-center gap-2">
                          <span className="text-cyan-500 font-bold">[{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]</span>
                          <span className="text-[#f5f5f5] font-bold uppercase tracking-wider">{log.agentName}</span>
                          <span className="text-neutral-700">//</span>
                          <span className="text-[9px] uppercase bg-neutral-950 px-2 py-0.2 rounded border border-neutral-850 tracking-wide text-neutral-400">{log.role}</span>
                        </div>
                        <div className="flex items-center gap-3 text-[9px] font-mono">
                          <span className="text-orange-500 uppercase tracking-widest">DUR: {(log.durationMs / 1000).toFixed(2)}s</span>
                          <span className="text-neutral-700">|</span>
                          <span className="text-[#a0a0a0]">{log.tokensUsed ? log.tokensUsed.toLocaleString() : "..."} TOK</span>
                        </div>
                      </div>

                      {/* Log Body Output Workspace */}
                      <div className="text-neutral-300 font-mono tracking-wide leading-relaxed break-words text-xs italic-none">
                        {isEditing ? (
                          <div className="flex flex-col gap-2 pt-1">
                            <textarea
                              value={editingLogText}
                              onChange={(e) => setEditingLogText(e.target.value)}
                              rows={8}
                              className="w-full bg-black font-mono text-xs p-4 border border-cyan-500/40 rounded text-neutral-200 leading-relaxed focus:outline-none"
                            />
                            <div className="flex items-center justify-end gap-2 pt-1 font-mono">
                              <button
                                onClick={() => setEditingLogId(null)}
                                className="px-3 py-1.5 bg-neutral-800 text-[10px] uppercase font-bold text-neutral-400 rounded hover:bg-neutral-700 transition cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleSaveEditedOutput(log.id)}
                                className="flex items-center gap-1 px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 text-[10px] uppercase font-bold text-black rounded transition cursor-pointer"
                              >
                                <Save className="w-3 h-3" /> Save tweaks
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="prose prose-invert bg-[#0d0d0d] p-4 rounded border border-neutral-855 text-[12px] md:text-[13px] leading-relaxed text-neutral-350 shadow-inner">
                            {renderTextContent(log.output)}
                          </div>
                        )}
                        {/* Display Telemetry Receipt below output */}
                        {!isEditing && (log.log_id || log.tenant_id) && (
                          <TelemetryPanel 
                            data={{
                              tenant_id: log.tenant_id || "workspace-default",
                              log_id: log.log_id || "N/A",
                              prompt_tokens: log.prompt_tokens || 0,
                              completion_tokens: log.completion_tokens || 0,
                              total_tokens: log.tokensUsed || 0,
                              latency_ms: log.durationMs,
                              provider: "veklom-authority",
                              model: log.modelUsed,
                              cost: log.cost || 0,
                              acp402_receipt: `tx_${Math.random().toString(36).substring(2, 10)}`,
                              self_learning: true
                            }} 
                            className="mt-3" 
                          />
                        )}
                      </div>

                      {/* Bottom utility controls */}
                      {!isEditing && (
                        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-neutral-850/60 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                          <button
                            onClick={() => {
                              setEditingLogId(log.id);
                              setEditingLogText(log.output);
                            }}
                            className="p-1 px-2 bg-neutral-950 font-semibold text-cyan-400 hover:text-cyan-300 rounded border border-cyan-800/20 hover:border-cyan-500/35 transition cursor-pointer text-[10px] flex items-center gap-1"
                          >
                            <Edit3 className="w-3 h-3" /> Tweak output
                          </button>

                          <button
                            onClick={() => handleCopyToClipboard(log.output, log.id)}
                            className="p-1 px-2.5 bg-neutral-950 text-neutral-400 hover:text-white rounded border border-neutral-800 transition cursor-pointer text-[10px] flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> {copiedId === log.id ? "Copied" : "Copy raw"}
                          </button>
                        </div>
                      )}
                    </motion.div>
                  );
                })}

                {/* Live step rendering loading block indicator */}
                {isSimulating && (
                  <motion.div
                    key="simulating-loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-4 bg-neutral-950 border border-neutral-850 rounded p-4 font-mono z-10"
                  >
                    <div className="flex flex-col items-center justify-center p-1 relative flex-shrink-0">
                      <div className="w-6 h-6 rounded-full border border-neutral-800 border-t-cyan-500 animate-spin"></div>
                    </div>
                    <div>
                      <h4 className="text-[11px] font-bold uppercase tracking-widest text-cyan-400 animate-pulse">
                        Downstream calculations in progress...
                      </h4>
                      <p className="text-[9px] text-neutral-500 mt-0.5 leading-relaxed">
                        {workflowType === "sequential" 
                          ? `EXEC_SEQUENTIAL // STEP NODE #${activeStepIndex + 1}: ${agents.find(a => a.id === pipelineSteps[activeStepIndex]?.agentId)?.name || "Agent"}`
                          : `EXEC_MEETING // SPEAK ROUND TURN #${activeStepIndex + 1}`
                        }
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* API Failure display bar */}
              {apiError && (
                <div className="p-4 bg-[#140404] border border-[#ff3333]/20 text-[#ffa0a0] text-xs rounded shadow z-10 leading-relaxed font-mono">
                  <p className="font-bold uppercase tracking-widest text-[#ff3333]">Simulation halted // Error occurred</p>
                  <p className="mt-1 text-neutral-400 lowercase">{apiError}</p>
                  <button
                    onClick={handleExecuteSingleTurn}
                    className="mt-3 text-[10px] uppercase font-bold bg-[#ff3333]/20 border border-[#ff3333]/40 hover:bg-[#ff3333]/30 px-3 py-1 rounded text-white transition cursor-pointer"
                  >
                    Retry calculation turn
                  </button>
                </div>
              )}

              {/* Anchor block for scrolling bottom */}
              <div ref={logsEndRef} />
              
            </div>

            {/* LIVE FINAL CONSOLIDATED LEDGER */}
            {simulationStatus === "completed" && simulationLogs.length > 0 && (
              <div className="bg-neutral-950 border-t border-neutral-850 p-5 flex flex-col gap-3 z-10 relative">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-neutral-850 gap-3">
                  <div className="flex items-center gap-2 font-mono">
                    <CheckCircle className="w-4 h-4 text-cyan-400" />
                    <div>
                      <h3 className="text-[12px] font-bold uppercase tracking-widest text-white">
                        Ledger Consolidated Asset
                      </h3>
                      <p className="text-[9px] text-neutral-500 uppercase">Signed sequential chain completed</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleCopyToClipboard(simulationLogs[simulationLogs.length - 1].output, "final-log")}
                    className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-[10px] font-bold uppercase tracking-wider text-black transition cursor-pointer"
                  >
                    <Copy className="w-3 h-3" /> 
                    {copiedId === "final-log" ? "Asset Copied!" : "Copy Consolidated Asset"}
                  </button>
                </div>
                
                {/* Visual rendering panel */}
                <div className="bg-[#0b0b0b] p-4 rounded border border-neutral-850 text-neutral-300 font-mono text-xs md:text-sm leading-relaxed whitespace-pre-wrap overflow-y-auto max-h-[300px] shadow-inner">
                  {renderTextContent(simulationLogs[simulationLogs.length - 1].output)}
                </div>
              </div>
            )}

            {/* Terminal Actions Footer Controls */}
            <div className="p-4 bg-black/60 border-t border-neutral-800 flex flex-wrap gap-3 items-center z-10 relative font-mono text-[10px]">
              
              {/* Reset button if logs exist */}
              {simulationLogs.length > 0 && (
                <button
                  onClick={handleResetSimulation}
                  className="px-3 py-2 border border-neutral-800 hover:border-neutral-600 rounded bg-[#101010] text-orange-500 hover:text-orange-400 font-bold uppercase transition duration-150 cursor-pointer flex items-center gap-1 active:scale-[0.98]"
                  title="Initialize state"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Initialize
                </button>
              )}

              {/* Automation: Full Run */}
              <button
                onClick={handleRunFullSimulation}
                disabled={isSimulating || !inputPrompt.trim()}
                className={`px-4 py-2 uppercase font-bold tracking-wider transition rounded cursor-pointer active:scale-[0.98] flex items-center gap-1.5 ${
                  simulationStatus === "running" || !inputPrompt.trim()
                    ? "bg-neutral-900 text-neutral-600 border border-neutral-800/60 pointer-events-none"
                    : "bg-cyan-650 hover:bg-cyan-500 text-black font-bold"
                }`}
              >
                <Play className="w-3 h-3 fill-current" /> Deploy full workflow
              </button>

              {/* Step By Step interactive arena trigger */}
              {simulationStatus === "idle" ? (
                <button
                  onClick={handleInitializeManualArena}
                  disabled={isSimulating || !inputPrompt.trim()}
                  className={`px-4 py-2 uppercase font-bold tracking-wider border border-neutral-700 bg-[#121212] hover:bg-neutral-850 hover:border-neutral-500 text-white transition rounded cursor-pointer active:scale-[0.98] flex items-center gap-1.5 ${
                    !inputPrompt.trim() ? "opacity-30 pointer-events-none" : ""
                  }`}
                >
                  <Send className="w-3.5 h-3.5 text-cyan-400" /> Start interactive arena
                </button>
              ) : simulationStatus === "ready" || simulationStatus === "running" ? (
                <button
                  onClick={handleExecuteSingleTurn}
                  disabled={isSimulating}
                  className={`px-4 py-2 uppercase font-bold tracking-wider bg-amber-500 hover:bg-amber-400 text-black transition rounded cursor-pointer active:scale-[0.98] flex items-center gap-1.5 ${
                    isSimulating ? "bg-neutral-850 text-neutral-550 pointer-events-none" : ""
                  }`}
                >
                  <SkipForward className="w-3.5 h-3.5" /> 
                  {workflowType === "sequential" 
                    ? `Execute step node #${activeStepIndex + 1}`
                    : `Execute talk round #${activeStepIndex + 1}`
                  }
                </button>
              ) : null}

            </div>
            
          </div>
            </>
          ) : (
            <div className="bg-neutral-900/40 border border-neutral-800/80 rounded-lg p-5 backdrop-blur-sm relative overflow-hidden flex-1 flex flex-col">
              <AuthorityScenarios />
            </div>
          )}
        </section>

      </main>

      {/* MODAL SYSTEM FOR ADDING/EDITING AGENT */}
      <AnimatePresence>
        {showAgentModal && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-lg bg-[#0e0e0e] border border-neutral-800 rounded shadow-2xl p-6 relative flex flex-col gap-4 text-neutral-300 font-mono"
            >
              <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
                <h3 className="text-sm font-bold uppercase tracking-widest text-white flex items-center gap-1.5">
                  [MNT-PROT] {editingAgent ? "Edit Agent Profile" : "Deploy Custom Agent"}
                </h3>
                <button
                  onClick={() => setShowAgentModal(false)}
                  className="text-neutral-500 hover:text-white rounded p-1 hover:bg-neutral-900 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Custom Edit Inputs */}
              <div className="grid grid-cols-2 gap-4">
                
                <div className="col-span-2 flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Agent Entity Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Athena (Architect)"
                    value={newAgentName}
                    onChange={(e) => setNewAgentName(e.target.value)}
                    className="bg-black border border-neutral-800 p-2.5 rounded focus:outline-none focus:border-cyan-500/60 text-xs text-neutral-250 font-mono"
                  />
                </div>

                <div className="col-span-2 flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Specialized Domain Role</label>
                  <input
                    type="text"
                    placeholder="e.g. Principal Lead Architect"
                    value={newAgentRole}
                    onChange={(e) => setNewAgentRole(e.target.value)}
                    className="bg-black border border-neutral-800 p-2.5 rounded focus:outline-none focus:border-cyan-500/60 text-xs text-neutral-250 font-mono"
                  />
                </div>

                {/* Avatar select */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Character Avatar</label>
                  <select
                    value={newAgentAvatar}
                    onChange={(e) => setNewAgentAvatar(e.target.value)}
                    className="bg-black border border-neutral-800 p-2.5 rounded focus:outline-none focus:border-cyan-500/60 text-xs cursor-pointer text-neutral-300 font-mono"
                  >
                    <option value="🤖">🤖 Bot</option>
                    <option value="🧠">🧠 Neural</option>
                    <option value="💻">💻 Code</option>
                    <option value="🎨">🎨 Artist</option>
                    <option value="🧐">🧐 Critic</option>
                    <option value="📋">📋 PM</option>
                    <option value="✍️">✍️ Writer</option>
                    <option value="📈">📈 Charts</option>
                    <option value="🚀">🚀 Rocket</option>
                    <option value="🕵️">🕵️ Analyst</option>
                    <option value="🛡️">🛡️ Shield</option>
                    <option value="📣">📣 Speaker</option>
                    <option value="🦖">🦖 Dino</option>
                    <option value="👾">👾 Gamer</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Theme Accent Color</label>
                  <select
                    value={newAgentColor}
                    onChange={(e) => setNewAgentColor(e.target.value)}
                    className="bg-black border border-neutral-800 p-2.5 rounded focus:outline-none focus:border-cyan-500/60 text-xs cursor-pointer text-neutral-300 font-mono"
                  >
                    <option value="blue">Cyan Blue</option>
                    <option value="emerald">Emerald Green</option>
                    <option value="amber">Amber Orange</option>
                    <option value="purple">Purple Magenta</option>
                    <option value="rose">Rose Red</option>
                    <option value="cyan">Neon Cyan</option>
                    <option value="violet">Violet Indigo</option>
                    <option value="fuchsia">Fuchsia Violet</option>
                    <option value="pink">Pink Accent</option>
                  </select>
                </div>

                {/* Model Choice & Temperature Settings */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Orchestrator Model</label>
                  <select
                    value={newAgentModel}
                    onChange={(e) => setNewAgentModel(e.target.value)}
                    className="bg-black border border-neutral-800 p-2.5 rounded focus:outline-none focus:border-cyan-500/60 text-xs cursor-pointer text-neutral-300 font-mono"
                  >
                    <option value="gemini-3.5-flash">GEMINI-3.5-FLASH</option>
                    <option value="gemini-3.1-flash-lite">GEMINI-3.1-FLASH-LITE</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Creativity (Temp: {newAgentTemp})</label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.1"
                    value={newAgentTemp}
                    onChange={(e) => setNewAgentTemperature(parseFloat(e.target.value))}
                    className="w-full h-8 accent-cyan-500 cursor-pointer bg-neutral-900 border-neutral-850 rounded"
                  />
                </div>

                <div className="col-span-2 flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">System Directive Instructions (Identity & Context Guidelines)</label>
                  <textarea
                    placeholder="Tell this agent who they are, their tone, constraints, and strict output requirements..."
                    value={newAgentInstruction}
                    onChange={(e) => setNewAgentInstruction(e.target.value)}
                    rows={4}
                    className="bg-black border border-neutral-800 p-3 rounded focus:outline-none focus:border-cyan-500/60 text-xs leading-relaxed text-neutral-200 resize-y"
                  />
                </div>

              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-neutral-800 font-mono text-[10px]">
                <button
                  onClick={() => setShowAgentModal(false)}
                  className="px-4 py-2 hover:bg-neutral-900 hover:text-white rounded font-bold uppercase transition duration-150 cursor-pointer"
                >
                  Discard
                </button>
                <button
                  onClick={handleSaveAgent}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-black rounded font-bold uppercase shadow transition duration-150 cursor-pointer flex items-center gap-1"
                >
                  <Check className="w-4 h-4" /> Save entity signature
                </button>
              </div>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* FOOTER AUDIT SECTION */}
      <footer className="border-t border-neutral-800 bg-black py-4 px-6 flex flex-col md:flex-row justify-between items-center text-[10px] text-neutral-500 uppercase tracking-[0.2em] gap-4 z-10 relative">
        <div>CLUSTER: US-CENTRAL-ALPHA</div>
        <div>SESSION UID: {Math.floor(1000 + Math.random() * 9000)}-AA{Math.floor(10 + Math.random() * 89)}-{Math.floor(1000 + Math.random() * 9000)}XB // UNRESTRICTED COGNITION DIRECTIVE</div>
        <div className="flex gap-4">
          <span className="text-cyan-900">SECURE PROCESSOR ISOLATION: ACTIVE</span>
        </div>
      </footer>

    </div>
  );
}

// Inline helper for dynamic titles
function logsTimelineTitle(status: string): string {
  switch (status) {
    case "idle": return "Ready to compile intent";
    case "ready": return "Interactive loop initialized";
    case "running": return "Executing live cognitive cycles...";
    case "completed": return "Concluded. Consolidated audit ledger signed.";
    case "error": return "Failure state halted.";
    default: return "Awaiting input";
  }
}
