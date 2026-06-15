import React, { useState, useEffect } from "react";
import { 
  Sparkles, 
  Shield, 
  Zap, 
  Brain, 
  Hammer, 
  Palette, 
  UserPlus, 
  UserCheck, 
  FileText, 
  RotateCcw, 
  Dices,
  Lock,
  Compass,
  AlertOctagon,
  Award
} from "lucide-react";
import { Agent } from "../types";

interface CharacterCreatorProps {
  onAgentCreated: (newAgent: Agent) => void;
}

// Structs for options
interface AvatarBase {
  id: string;
  name: string;
  avatar: string;
  description: string;
  icon: any;
}

interface PaletteOption {
  id: string;
  name: string;
  glowColor: string;
  borderColor: string;
  textColor: string;
  bgColor: string;
  badgeBg: string;
}

const AVATAR_BASES: AvatarBase[] = [
  { id: "sentinel", name: "Sentinel", avatar: "🛡️", description: "Defensive & security orchestration layer.", icon: Shield },
  { id: "oracle", name: "Oracle", avatar: "🧠", description: "Deep analysis & cognitive intelligence node.", icon: Brain },
  { id: "forge", name: "Forge", avatar: "🛠️", description: "Synthesizer of structures and software code.", icon: Hammer },
  { id: "muse", name: "Muse", avatar: "🎨", description: "Creative copy sculpting & brand narrative strategist.", icon: Palette },
  { id: "swift", name: "Swift", avatar: "⚡", description: "High-frequency automation & tactical stream handler.", icon: Zap },
];

const PALETTES: PaletteOption[] = [
  { id: "teal", name: "Teal / Black (Governed)", glowColor: "shadow-[0_0_25px_rgba(6,182,212,0.15)]", borderColor: "border-cyan-500/40", textColor: "text-cyan-400", bgColor: "bg-[#080c0d]/80", badgeBg: "bg-cyan-500/10" },
  { id: "red", name: "Red / Graphite (Rogue)", glowColor: "shadow-[0_0_25px_rgba(239,68,68,0.15)]", borderColor: "border-rose-500/40", textColor: "text-rose-400", bgColor: "bg-[#0f0a0a]/80", badgeBg: "bg-rose-500/10" },
  { id: "violet", name: "Violet / Navy (Research)", glowColor: "shadow-[0_0_25px_rgba(139,92,246,0.15)]", borderColor: "border-violet-500/40", textColor: "text-violet-400", bgColor: "bg-[#0a0912]/80", badgeBg: "bg-violet-500/10" },
  { id: "gold", name: "Gold / Charcoal (Premium)", glowColor: "shadow-[0_0_25px_rgba(245,158,11,0.15)]", borderColor: "border-amber-500/40", textColor: "text-amber-400", bgColor: "bg-[#110e08]/80", badgeBg: "bg-amber-500/10" },
  { id: "green", name: "Green / Slate (Eco-Route)", glowColor: "shadow-[0_0_25px_rgba(16,185,129,0.15)]", borderColor: "border-emerald-500/40", textColor: "text-emerald-400", bgColor: "bg-[#080d0a]/80", badgeBg: "bg-emerald-500/10" },
];

const AVAILABLE_SCOPES = [
  { id: "repo:read", label: "repo:read", desc: "Allows scanning and reading codespace files/metadata." },
  { id: "repo:write", label: "repo:write", desc: "Allows modifying repository files and committing code structures." },
  { id: "db:read", label: "db:read", desc: "Allows querying database tables." },
  { id: "db:write", label: "db:write", desc: "Allows mutating, inserting, or dropping database layers." },
  { id: "network:outbound", label: "network:outbound", desc: "Allows raw socket outbounds & external Webhook postings." },
  { id: "budget:consume", label: "budget:consume", desc: "Allows looping API queries with premium credentials." },
];

export default function CharacterCreator({ onAgentCreated }: CharacterCreatorProps) {
  // Input fields
  const [characterName, setCharacterName] = useState<string>("Vega Analyst One");
  const [selectedBase, setSelectedBase] = useState<string>("oracle");
  const [selectedPalette, setSelectedPalette] = useState<string>("teal");
  const [previewMode, setPreviewMode] = useState<"biometrics" | "pgl" | "execId">("execId");
  const [intendedAction, setIntendedAction] = useState<string>("Review code structures and run standard static analyses");
  const [requestedScopes, setRequestedScopes] = useState<string[]>(["repo:read"]);
  
  // Helper for realistic deterministic hex strings matching user settings
  const getPglHexStr = (seed: string, len: number) => {
    let h = 0x811c9dc5;
    for (let i = 0; i < seed.length; i++) {
      h ^= seed.charCodeAt(i);
      h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
    }
    const hex = Math.abs(h).toString(16).padEnd(8, "0");
    const fill = "ac8b742e912b7a9deaf821f04cca219ccf84de91b112cf3a";
    return (hex + fill).slice(0, len).toLowerCase();
  };

  // Attribute stats (Users get 20 starting points. Starting on default base values adding up to 10. Total limit is 20)
  const [attributes, setAttributes] = useState({
    intelligence: 4,
    creativity: 4,
    speed: 4,
    security: 4,
    reliability: 4
  });

  // Unique Agent ID generated on load and randomized
  const [agentId, setAgentId] = useState<string>("");

  useEffect(() => {
    generateRandomId();
  }, [selectedBase]);

  const generateRandomId = () => {
    const caps = selectedBase.slice(0, 3).toUpperCase();
    const randNum = Math.floor(100 + Math.random() * 900);
    setAgentId(`VK-${caps}-${randNum}`);
  };

  const totalPointsSpent = 
    attributes.intelligence + 
    attributes.creativity + 
    attributes.speed + 
    attributes.security + 
    attributes.reliability;

  const pointsRemaining = 20 - totalPointsSpent;

  // Set individual attribute score safely
  const handleSetStat = (stat: keyof typeof attributes, val: number) => {
    // Current sum of other attributes
    const sumOthers = Object.keys(attributes)
      .filter(k => k !== stat)
      // @ts-ignore
      .reduce((acc, current) => acc + attributes[current], 0);

    // Enforce bounds: min 1, max 10
    if (val < 1 || val > 10) return;
    
    // Check points sum limit <= 20
    if (sumOthers + val <= 20) {
      setAttributes(prev => ({
        ...prev,
        [stat]: val
      }));
    }
  };

  const handleRandomize = () => {
    // Select random base and palette
    const randBase = AVATAR_BASES[Math.floor(Math.random() * AVATAR_BASES.length)].id;
    const randPalette = PALETTES[Math.floor(Math.random() * PALETTES.length)].id;
    
    setSelectedBase(randBase);
    setSelectedPalette(randPalette);

    // Randomize name
    const prefixes = ["Vega", "Orion", "Apex", "Kore", "Synapse", "Quantum", "Nexus", "Helios", "Aegis"];
    const suffixes = ["Alpha", "Prime", "Sigma", "Ghost", "Zero", "MINT", "Sovereign"];
    const randName = `${prefixes[Math.floor(Math.random() * prefixes.length)]} ${suffixes[Math.floor(Math.random() * suffixes.length)]}`;
    setCharacterName(randName);

    // Distribute 20 points randomly (each stat minimum 1)
    let pointsToDistribute = 15; // as we assign 1 to each of the 5 stats first
    const newStats = { intelligence: 1, creativity: 1, speed: 1, security: 1, reliability: 1 };
    const statKeys = Object.keys(newStats) as (keyof typeof attributes)[];

    while (pointsToDistribute > 0) {
      const randomKey = statKeys[Math.floor(Math.random() * statKeys.length)];
      if (newStats[randomKey] < 10) {
        newStats[randomKey] += 1;
        pointsToDistribute -= 1;
      }
    }
    setAttributes(newStats);
  };

  const handleResetPoints = () => {
    setAttributes({
      intelligence: 1,
      creativity: 1,
      speed: 1,
      security: 1,
      reliability: 1
    });
  };

  const handleCreateAgent = () => {
    if (!characterName.trim()) {
      alert("Please designate a System Name for your agent profile.");
      return;
    }
    if (totalPointsSpent !== 20) {
      alert("You must assign exactly 20 skill points across attributes before proceeding.");
      return;
    }

    const baseObj = AVATAR_BASES.find(b => b.id === selectedBase) || AVATAR_BASES[0];
    const paletteObj = PALETTES.find(p => p.id === selectedPalette) || PALETTES[0];

    // Map starting palettes into tailwind color themes
    const colorMap: Record<string, string> = {
      teal: "cyan",
      red: "rose",
      violet: "violet",
      gold: "amber",
      green: "emerald",
    };

    // Construct system instructions dynamically from attributes, bases, declarations & scopes
    const attributesSummary = `Authority Profile: Autonomy Level ${attributes.intelligence}/10, Delegation Depth ${attributes.creativity}/10, Budget Limit ${attributes.speed}/10, Security Posture ${attributes.security}/10, Gov Compliance ${attributes.reliability}/10. Assigned Role: ${getBestRoleFit()}`;
    const policyPreCert = `PGL-Security-PreCert: Registered genome_hash: sha256:${getPglHexStr(selectedBase + "_" + attributes.intelligence + "_" + attributes.speed, 8)}... Scopes: [${requestedScopes.join(", ")}]. Declared Intended Action: "${intendedAction}". Verify all tool calls against this boundary.`;
    const systemInstruction = `You are an AI Agent with signature ID ${agentId}. Your designated role function is "${getBestRoleFit()}". You are powered by a ${selectedBase.toUpperCase()} intelligence core. Instructions: Adopt a highly focused, professional tone matching your specialization details. Focus on constraints, structure, and providing actionable contributions. ${attributesSummary}. ${policyPreCert}`;

    const newAgent: Agent = {
      id: agentId.toLowerCase(),
      name: characterName,
      role: getBestRoleFit(),
      systemInstruction: systemInstruction,
      temperature: 0.1 + (attributes.creativity * 0.08), // Scaling temperature with creativity attribute!
      model: "gemini-3.5-flash",
      avatar: baseObj.avatar,
      color: colorMap[selectedPalette] || "blue"
    };

    onAgentCreated(newAgent);
  };

  // Derived calculations: Best Role Fit
  const getBestRoleFit = (): string => {
    const { intelligence, creativity, speed, security, reliability } = attributes;
    if (security >= 7 && reliability >= 7) return "Sovereign Runtime Guardian";
    if (intelligence >= 7 && reliability >= 7) return "Meticulous Policy Analyst";
    if (creativity >= 7 && intelligence >= 7) return "Tactical Cognitive Architect";
    if (creativity >= 7 && speed >= 7) return "Narrative Sculpting Engineer";
    if (speed >= 7 && reliability >= 7) return "High-Frequency System Automation";
    if (intelligence >= 7) return "Chief Strategy Protocol Director";
    if (creativity >= 7) return "Generative Content Synthesizer";
    if (speed >= 7) return "Pipeline Execution Accelerator";
    
    // Fallback based on avatar base selection
    switch (selectedBase) {
      case "sentinel": return "Aegis Security Supervisor";
      case "oracle": return "Deep Cognitive Researcher";
      case "forge": return "High-Precision Code Craftsman";
      case "muse": return "Interactive Brand Strategist";
      case "swift": return "Automation Stream Dispatcher";
      default: return "Cognitive Synergy Unit";
    }
  };

  // Derived calculations: Risk Level
  const getRiskLevel = () => {
    const { security, speed } = attributes;
    if (selectedPalette === "red" || (security < 3 && speed >= 7)) {
      return { level: "CRITICAL ROGUE SECTOR", color: "text-rose-500 bg-rose-500/10 border-rose-500/30" };
    }
    if (security >= 7 && attributes.reliability >= 7) {
      return { level: "COMPLIANT SOVEREIGN SECURE", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" };
    }
    if (security >= 4) {
      return { level: "GOVERNED RUNTIME COUPLING", color: "text-amber-400 bg-amber-500/10 border-amber-500/30" };
    }
    return { level: "STANDARD ENTROPIC BUFFER", color: "text-neutral-400 bg-neutral-900 border-neutral-800" };
  };

  // Derived calculations: Execution Tier
  const getExecutionTier = (): string => {
    const { intelligence, speed } = attributes;
    if (intelligence + speed >= 16) return "OVERCLOCKED CLASS X5";
    if (intelligence + speed >= 12) return "INTERACTIVE BATCH TIER A";
    return "STANDARD DESKTOP LATENCY";
  };

  // Authority Runtime Compatibility checkers
  const getCompatibilityMatrix = () => {
    const { security, reliability, intelligence } = attributes;
    return {
      pglPass: security >= 3 && reliability >= 2,
      sekedPass: intelligence >= 3 && security >= 4,
      executionPass: reliability >= 4,
      mcpPass: security >= 3
    };
  };

  const baseObj = AVATAR_BASES.find(b => b.id === selectedBase) || AVATAR_BASES[0];
  const paletteObj = PALETTES.find(p => p.id === selectedPalette) || PALETTES[0];
  const risk = getRiskLevel();
  const balanceRemaining = pointsRemaining;
  const compatibility = getCompatibilityMatrix();

  return (
    <div className="flex flex-col gap-5 text-neutral-300 font-mono select-none" id="character-creator-container">
      
      {/* Dynamic Upper Header banner */}
      <div className="flex justify-between items-center pb-2 border-b border-neutral-800">
        <h3 className="text-xs font-bold uppercase tracking-widest text-[#a0a0a0] flex items-center gap-1.5">
          [🔮] GOVERNED AGENT IDENTITY BUILDER
        </h3>
        <button 
          onClick={handleRandomize}
          className="text-[10px] bg-neutral-900 border border-neutral-800 text-neutral-400 px-2.5 py-1 rounded flex items-center gap-1.5 hover:text-white hover:border-neutral-700 transition cursor-pointer"
        >
          <Dices className="w-3.5 h-3.5 text-cyan-400" /> Auto-Calibrate Profile
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        
        {/* Left Side: Avatar Interactive Preview Card (120x160ish responsive layout) */}
        <div className="md:col-span-5 flex flex-col gap-3">
          <div className="flex bg-neutral-950 p-1 rounded border border-neutral-850 gap-1">
            <button
              type="button"
              onClick={() => setPreviewMode("biometrics")}
              className={`flex-1 py-1 text-[8px] font-bold uppercase tracking-wider rounded transition cursor-pointer ${
                previewMode === "biometrics"
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              Identity Profile
            </button>
            <button
              type="button"
              onClick={() => setPreviewMode("pgl")}
              className={`flex-1 py-1 text-[8px] font-bold uppercase tracking-wider rounded transition cursor-pointer flex items-center justify-center gap-1 ${
                previewMode === "pgl"
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              🔐 PGL Pre-Cert
            </button>
            <button
              type="button"
              onClick={() => setPreviewMode("execId")}
              className={`flex-1 py-1 text-[8px] font-bold uppercase tracking-wider rounded transition cursor-pointer flex items-center justify-center gap-1 ${
                previewMode === "execId"
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              🔑 Exec ID v1
            </button>
          </div>
          
          <div className={`p-4 rounded-lg border ${paletteObj.borderColor} ${paletteObj.bgColor} ${paletteObj.glowColor} flex flex-col items-center text-center relative overflow-hidden transition-all duration-300 flex-1 min-h-[380px] justify-between`}>
            
            {previewMode === "biometrics" ? (
              <>
                {/* Top digital coordinates decor */}
                <div className="flex justify-between w-full text-[8px] text-neutral-600">
                  <span>CORE_CH: {selectedBase.toUpperCase()}-v2</span>
                  <span>ID: {agentId}</span>
                </div>

                {/* Glowing active avatar sphere */}
                <div className="my-6 relative flex items-center justify-center">
                  <div className={`absolute inset-0 rounded-full blur-xl opacity-30 ${selectedPalette === "teal" ? "bg-cyan-500" : selectedPalette === "red" ? "bg-rose-500" : selectedPalette === "violet" ? "bg-violet-500" : selectedPalette === "gold" ? "bg-amber-500" : "bg-emerald-500"}`}></div>
                  <div className="w-24 h-24 rounded-full border border-neutral-800 bg-neutral-950/90 flex items-center justify-center text-5xl cursor-default animate-bounce relative z-10 shadow-lg">
                    {baseObj.avatar}
                  </div>
                </div>

                {/* Details output summary inside card */}
                <div className="w-full space-y-2 mt-auto">
                  <div className="text-xs font-bold uppercase text-white truncate max-w-full">
                    {characterName || "SYSTEM UNIT"}
                  </div>
                  <div className={`text-[9px] uppercase tracking-wider font-bold py-0.5 px-2 rounded-full border ${paletteObj.textColor} ${paletteObj.badgeBg} inline-block font-mono`}>
                    {getBestRoleFit()}
                  </div>

                  {/* Mini properties listing inside index tag */}
                  <div className="grid grid-cols-2 gap-1.5 text-[8px] text-neutral-500 mt-3 pt-3 border-t border-neutral-800/80">
                    <div className="text-left">
                      <span>TIER:</span> <span className="text-neutral-300 font-bold block truncate">{getExecutionTier()}</span>
                    </div>
                    <div className="text-left">
                      <span>RISK SECTOR:</span> <span className={`${risk.level.includes("ROGUE") ? "text-rose-500" : "text-neutral-300"} font-bold block truncate`}>{risk.level.split(" ")[0]}</span>
                    </div>
                  </div>
                </div>
              </>
            ) : previewMode === "pgl" ? (
              <div className="w-full text-left font-mono text-[8.2px] leading-normal text-neutral-450 space-y-0.5 select-text">
                <div className="border-b border-neutral-800 pb-1 mb-1.5 flex justify-between items-center">
                  <span className="text-cyan-400 font-black tracking-widest text-[9px] uppercase">PGL PRE-EXECUTION CERTIFICATE</span>
                  <span className="text-[7px] text-neutral-600">v1.2</span>
                </div>
                <div><span className="text-neutral-500">status:</span> <span className="text-cyan-400 font-bold">committed</span></div>
                <div><span className="text-neutral-500">pre_execution_certificate_id:</span> <span className="text-neutral-200">pgl_cert_pre_{getPglHexStr(agentId, 12)}</span></div>
                <div><span className="text-neutral-500">actor_id:</span> <span className="text-neutral-200">agent_{(characterName || "unit").trim().toLowerCase().replace(/\s+/g, "_")}</span></div>
                <div><span className="text-neutral-500">workspace_id:</span> <span className="text-neutral-200">sandbox_demo</span></div>
                <div className="pt-0.5"><span className="text-neutral-500">genome_hash:</span> <span className="text-cyan-500 block break-all font-mono">sha256:{getPglHexStr(selectedBase + "_" + attributes.intelligence + "_" + attributes.speed, 32)}...</span></div>
                <div><span className="text-neutral-500">constitution_hash:</span> <span className="text-violet-500 block break-all font-mono">sha256:{getPglHexStr((characterName || "unit") + "_" + attributes.security + "_" + attributes.reliability + "_" + selectedPalette, 32)}...</span></div>
                <div><span className="text-neutral-500">plan_hash:</span> <span className="text-amber-500 block break-all font-mono">sha256:{getPglHexStr(getBestRoleFit() + "_" + intendedAction, 32)}...</span></div>
                <div><span className="text-neutral-500">tool_manifest_hash:</span> <span className="text-emerald-500 block break-all font-mono">sha256:{getPglHexStr(requestedScopes.concat().sort().join(","), 32)}...</span></div>
                <div><span className="text-neutral-500">delegation_chain_hash:</span> <span className="text-neutral-600 block break-all font-mono">sha256:{getPglHexStr(agentId + "_chain", 32)}...</span></div>
                <div><span className="text-neutral-500">input_hash:</span> <span className="text-neutral-600 block break-all font-mono">sha256:{getPglHexStr(intendedAction || "empty_input", 32)}...</span></div>
                <div><span className="text-neutral-500">persisted:</span> <span className="text-cyan-400 font-bold">true</span></div>
                <div><span className="text-neutral-500">event_hash:</span> <span className="text-[#999] block break-all font-mono">sha256:{getPglHexStr(agentId + "_event_commit", 32)}...</span></div>
                
                <div className="border-t border-neutral-800 pt-1.5 mt-1.5 text-neutral-500">
                  <span className="text-neutral-400 font-bold block mb-0.5 text-[7.5px] tracking-wider uppercase">REQUESTED RUNTIME BOUNDARIES:</span>
                  <div className="flex flex-wrap gap-1">
                    {requestedScopes.length === 0 ? (
                      <span className="text-[7px] px-1 py-0.5 bg-neutral-900 border border-neutral-850 rounded text-neutral-500 uppercase">no high-risk scopes</span>
                    ) : (
                      requestedScopes.map(sc => (
                        <span key={sc} className="text-[7px] px-1 py-0.5 bg-cyan-950/40 border border-cyan-850/60 rounded text-cyan-400 uppercase font-mono">{sc}</span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="w-full text-left font-mono text-[7.8px] leading-snug text-neutral-400 space-y-0.5 select-text overflow-y-auto max-h-[360px] scrollbar-thin">
                <div className="border-b border-neutral-800 pb-1 mb-1 bg-black/20 flex justify-between items-center">
                  <span className="text-violet-400 font-black tracking-widest text-[8.5px] uppercase">EXECUTION IDENTITY V1</span>
                  <span className="text-[6.5px] text-neutral-600">LAW 0 OBJECT</span>
                </div>
                <div><span className="text-neutral-550 mr-1">execution_id:</span><span className="text-violet-350">exec_vk_{getPglHexStr(agentId, 12)}</span></div>
                <div><span className="text-neutral-550 mr-1">pgl_pre_cert_id:</span><span className="text-neutral-300">pgl_cert_pre_{getPglHexStr(agentId, 12)}</span></div>
                <div><span className="text-neutral-550 mr-1">genome_hash:</span><span className="text-cyan-500/85 font-mono">sha256:{getPglHexStr(selectedBase + "_" + attributes.intelligence + "_" + attributes.speed, 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">constitution_hash:</span><span className="text-violet-500/85 font-mono">sha256:{getPglHexStr((characterName || "unit") + "_" + attributes.security + "_" + attributes.reliability + "_" + selectedPalette, 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">plan_hash:</span><span className="text-amber-500/85 font-mono">sha256:{getPglHexStr(getBestRoleFit() + "_" + intendedAction, 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">tool_manifest_hash:</span><span className="text-emerald-550 font-mono">sha256:{getPglHexStr(requestedScopes.concat().sort().join(","), 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">delegation_chain_hash:</span><span className="text-neutral-500 font-mono text-[7px]">{getPglHexStr(agentId + "_chain", 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">seked_attestation_hash:</span><span className="text-neutral-550 font-mono">{getPglHexStr(agentId + "_seked", 24)}...</span></div>
                <div><span className="text-neutral-550 mr-1">directive_summary:</span><span className="text-neutral-350 lowercase">"powered by {selectedBase} core w/ {attributes.intelligence}/10 autonomy"</span></div>
                <div><span className="text-neutral-550 mr-1">risk_tier:</span><span className="text-rose-400 font-bold">{risk.level}</span></div>
                <div><span className="text-neutral-550 mr-1">budget_approved_cents:</span><span className="text-amber-400 font-bold">{attributes.speed * 100}¢</span></div>
                <div><span className="text-neutral-550 mr-1">delegation_depth:</span><span className="text-violet-400 font-bold">{attributes.creativity}</span></div>
                <div><span className="text-neutral-550 mr-1">ttl_seconds:</span><span className="text-cyan-400 font-mono">{attributes.intelligence * 360}s</span></div>
                <div><span className="text-neutral-550 mr-1">scope:</span><span className="text-emerald-400">[{requestedScopes.join(", ") || "no_destructive"}]</span></div>
                <div><span className="text-neutral-550 mr-1">issuer:</span><span className="text-cyan-400">Veklom Authority v5</span></div>
                <div><span className="text-neutral-550 mr-1">status:</span><span className="text-emerald-400 font-bold">READY_TO_MINT</span></div>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Customization Controls Panel */}
        <div className="md:col-span-7 flex flex-col gap-4">
          
          {/* Identity Name Input */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">01. Designated System Name</span>
            <input 
              type="text" 
              placeholder="Inject Agent Name Signifier..." 
              value={characterName} 
              onChange={(e) => setCharacterName(e.target.value)}
              className="w-full bg-black/60 p-3 border border-neutral-850 rounded text-neutral-200 placeholder-neutral-600 text-xs focus:outline-none focus:border-cyan-500/60"
            />
          </div>

          {/* Avatar Base selector */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">02. Select Neural Core Base</span>
            <div className="grid grid-cols-5 gap-1.5">
              {AVATAR_BASES.map(b => (
                <button
                  key={b.id}
                  onClick={() => setSelectedBase(b.id)}
                  className={`p-2.5 rounded border flex flex-col items-center gap-1 transition ${
                    selectedBase === b.id 
                      ? "bg-cyan-500/[0.04] border-cyan-500/40 text-cyan-400" 
                      : "bg-neutral-900/30 border-neutral-850 text-neutral-400 hover:bg-neutral-850 hover:text-white"
                  }`}
                  title={`${b.name}: ${b.description}`}
                >
                  <span className="text-lg">{b.avatar}</span>
                  <span className="text-[8px] uppercase tracking-tighter font-bold">{b.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Color palette selector */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">03. Calibration Color Palette</span>
            <div className="grid grid-cols-5 gap-1.5">
              {PALETTES.map(p => {
                const isSelected = selectedPalette === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPalette(p.id)}
                    className={`p-2 rounded border text-center transition-all flex flex-col gap-1 items-center justify-center ${
                      isSelected 
                        ? `${p.borderColor} ${p.badgeBg} ${p.textColor}` 
                        : "bg-neutral-900/10 border-neutral-850 text-neutral-500 hover:text-neutral-300 hover:border-neutral-800"
                    }`}
                  >
                    {/* Tiny Color Sphere preview */}
                    <div className={`w-2 h-2 rounded-full ${
                      p.id === "teal" ? "bg-cyan-400" :
                      p.id === "red" ? "bg-rose-500" :
                      p.id === "violet" ? "bg-violet-400" :
                      p.id === "gold" ? "bg-amber-400" : "bg-emerald-400"
                    }`}></div>
                    <span className="text-[7.5px] uppercase font-bold tracking-tight">{p.name.split(" ")[0]}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Attributes Allocator section */}
          <div className="flex flex-col gap-2 p-4 bg-black/40 border border-neutral-850 rounded">
            <div className="flex justify-between items-center border-b border-neutral-850/80 pb-2">
              <span className="text-[10px] uppercase font-bold text-neutral-450 tracking-wider">04. Configure Governance Authority Posture</span>
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-bold text-neutral-450 font-mono uppercase tracking-wide">
                  BALANCE: <b className={`font-mono font-black ${pointsRemaining === 0 ? "text-cyan-400" : pointsRemaining < 0 ? "text-rose-500" : "text-amber-400"}`}>{pointsRemaining} NODES</b> REMAINING
                </span>
                <button 
                  onClick={handleResetPoints}
                  className="text-[8px] bg-neutral-950 px-2 py-0.5 border border-neutral-850 text-neutral-500 hover:text-white rounded uppercase"
                  title="Wipe allocated points"
                >
                  Clear Points
                </button>
              </div>
            </div>

            {/* Individual sliders/allocators */}
            <div className="space-y-2 pt-1 font-mono text-[10px]">
              {/* Autonomy Level */}
              <div className="flex items-center justify-between gap-4">
                <span className="w-24 text-neutral-400 font-medium whitespace-nowrap">AUTONOMY LEVEL</span>
                <div className="flex-1 flex items-center gap-1.5">
                  <button 
                    onClick={() => handleSetStat("intelligence", attributes.intelligence - 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95 animate-none"
                  >-</button>
                  <div className="flex-1 bg-neutral-950 h-2.5 rounded overflow-hidden p-0.5 border border-neutral-850 flex items-center justify-start gap-0.5 relative">
                    {Array.from({ length: attributes.intelligence }).map((_, i) => (
                      <div key={i} className="h-full bg-cyan-500/80 rounded-sm" style={{ width: `${100 / 10}%` }}></div>
                    ))}
                  </div>
                  <span className="w-4 font-bold text-right text-cyan-400">{attributes.intelligence}</span>
                  <button 
                    onClick={() => handleSetStat("intelligence", attributes.intelligence + 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >+</button>
                </div>
              </div>

              {/* Delegation Depth */}
              <div className="flex items-center justify-between gap-4">
                <span className="w-24 text-neutral-400 font-medium whitespace-nowrap">DELEGATION DEPTH</span>
                <div className="flex-1 flex items-center gap-1.5">
                  <button 
                    onClick={() => handleSetStat("creativity", attributes.creativity - 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >-</button>
                  <div className="flex-1 bg-neutral-950 h-2.5 rounded overflow-hidden p-0.5 border border-neutral-850 flex items-center justify-start gap-0.5 relative">
                    {Array.from({ length: attributes.creativity }).map((_, i) => (
                      <div key={i} className="h-full bg-violet-500/80 rounded-sm" style={{ width: `${100 / 10}%` }}></div>
                    ))}
                  </div>
                  <span className="w-4 font-bold text-right text-violet-400">{attributes.creativity}</span>
                  <button 
                    onClick={() => handleSetStat("creativity", attributes.creativity + 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >+</button>
                </div>
              </div>

              {/* Budget Limit */}
              <div className="flex items-center justify-between gap-4">
                <span className="w-24 text-neutral-400 font-medium whitespace-nowrap">BUDGET LIMIT</span>
                <div className="flex-1 flex items-center gap-1.5">
                  <button 
                    onClick={() => handleSetStat("speed", attributes.speed - 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >-</button>
                  <div className="flex-1 bg-neutral-950 h-2.5 rounded overflow-hidden p-0.5 border border-neutral-850 flex items-center justify-start gap-0.5 relative">
                    {Array.from({ length: attributes.speed }).map((_, i) => (
                      <div key={i} className="h-full bg-amber-500/80 rounded-sm" style={{ width: `${100 / 10}%` }}></div>
                    ))}
                  </div>
                  <span className="w-4 font-bold text-right text-amber-500">{attributes.speed}</span>
                  <button 
                    onClick={() => handleSetStat("speed", attributes.speed + 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >+</button>
                </div>
              </div>

              {/* Security Posture */}
              <div className="flex items-center justify-between gap-4">
                <span className="w-24 text-neutral-400 font-medium whitespace-nowrap">RESTR. POSTURE</span>
                <div className="flex-1 flex items-center gap-1.5">
                  <button 
                    onClick={() => handleSetStat("security", attributes.security - 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >-</button>
                  <div className="flex-1 bg-neutral-950 h-2.5 rounded overflow-hidden p-0.5 border border-neutral-850 flex items-center justify-start gap-0.5 relative">
                    {Array.from({ length: attributes.security }).map((_, i) => (
                      <div key={i} className="h-full bg-rose-500/80 rounded-sm" style={{ width: `${100 / 10}%` }}></div>
                    ))}
                  </div>
                  <span className="w-4 font-bold text-right text-rose-500">{attributes.security}</span>
                  <button 
                    onClick={() => handleSetStat("security", attributes.security + 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >+</button>
                </div>
              </div>

              {/* Governance Compliance */}
              <div className="flex items-center justify-between gap-4">
                <span className="w-24 text-neutral-400 font-medium whitespace-nowrap">GOV COMPLIANCE</span>
                <div className="flex-1 flex items-center gap-1.5">
                  <button 
                    onClick={() => handleSetStat("reliability", attributes.reliability - 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >-</button>
                  <div className="flex-1 bg-neutral-950 h-2.5 rounded overflow-hidden p-0.5 border border-neutral-850 flex items-center justify-start gap-0.5 relative">
                    {Array.from({ length: attributes.reliability }).map((_, i) => (
                      <div key={i} className="h-full bg-emerald-500/80 rounded-sm" style={{ width: `${100 / 10}%` }}></div>
                    ))}
                  </div>
                  <span className="w-4 font-bold text-right text-emerald-400">{attributes.reliability}</span>
                  <button 
                    onClick={() => handleSetStat("reliability", attributes.reliability + 1)}
                    className="w-5 h-5 bg-neutral-900 border border-neutral-800 text-center text-xs text-neutral-400 rounded hover:text-white hover:border-neutral-700 font-bold active:scale-95"
                  >+</button>
                </div>
              </div>

            </div>
          </div>

          {/* Step 05: Runtime Policy Scopes & Action Declaration */}
          <div className="flex flex-col gap-2.5 p-4 bg-black/40 border border-neutral-850 rounded">
            <span className="text-[10px] uppercase font-bold text-neutral-450 tracking-wider">05. Runtime Declarations & Policy Scopes</span>
            
            <div className="flex flex-col gap-1.5 pt-1">
              <label className="text-[8.5px] uppercase font-bold text-neutral-450 tracking-wide font-mono">Declared Intended Action</label>
              <input
                type="text"
                placeholder="Declare active task intention..."
                value={intendedAction}
                onChange={(e) => setIntendedAction(e.target.value)}
                className="w-full bg-neutral-950 p-2.5 border border-neutral-850 rounded text-neutral-200 placeholder-neutral-700 text-[10.5px] focus:outline-none focus:border-cyan-500/40 font-mono"
              />
              
              {/* Quick Template Suggestion Chips */}
              <div className="flex flex-wrap gap-1 mt-1">
                <span className="text-[7.5px] text-neutral-500 mr-1 self-center">DECLARATION TEMPLATES:</span>
                {[
                  "Scan files to audit system telemetry buffers",
                  "Verify billing records & check database tables",
                  "Mutate repo files & run write execution trials",
                  "Drop client bills & force outbound exfiltration"
                ].map((txt) => (
                  <button
                    key={txt}
                    type="button"
                    onClick={() => setIntendedAction(txt)}
                    className={`text-[7.5px] px-1.5 py-0.5 rounded border font-mono transition cursor-pointer ${
                      intendedAction === txt
                        ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-400 font-bold"
                        : "bg-neutral-950 border-neutral-850 text-neutral-400 hover:text-white"
                    }`}
                  >
                    {txt.split(" ").slice(0, 3).join(" ")}...
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5 pt-2 border-t border-neutral-850/60 mt-1">
              <label className="text-[8.5px] uppercase font-bold text-neutral-450 tracking-wide font-mono">Requested Governed Tool Scopes</label>
              <div className="grid grid-cols-2 gap-2 text-[9px] font-mono leading-tight">
                {AVAILABLE_SCOPES.map(sc => {
                  const isChecked = requestedScopes.includes(sc.id);
                  return (
                    <button
                      key={sc.id}
                      type="button"
                      onClick={() => {
                        if (isChecked) {
                          setRequestedScopes(prev => prev.filter(x => x !== sc.id));
                        } else {
                          setRequestedScopes(prev => [...prev, sc.id]);
                        }
                      }}
                      className={`p-2 rounded border text-left flex items-start gap-2 transition hover:bg-neutral-900/40 cursor-pointer ${
                        isChecked
                          ? "bg-cyan-500/[0.02] border-cyan-500/30 text-neutral-200 shadow-sm"
                          : "bg-neutral-950/20 border-neutral-850 text-neutral-500"
                      }`}
                    >
                      <div className={`w-3 h-3 rounded flex items-center justify-center border font-bold text-[8px] flex-shrink-0 mt-0.5 ${
                        isChecked ? "bg-cyan-500/15 border-cyan-400/50 text-cyan-400" : "bg-neutral-950 border-neutral-800 text-transparent"
                      }`}>
                        ✓
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <span className={`block font-bold truncate ${isChecked ? "text-cyan-400" : "text-neutral-450"}`}>{sc.label}</span>
                        <span className="block text-[7.5px] text-neutral-500 line-clamp-1">{sc.desc}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Authority Runtime Compatibility Section */}
      <div className="bg-[#0b0c10]/80 p-4 border border-neutral-850 rounded">
        <span className="text-[10px] uppercase font-bold text-[#b4b4b4] tracking-widest font-mono block pb-2 border-b border-neutral-850/85 mb-3 flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-cyan-500" /> Veklom Authority Boundary Compatibility Checklist
        </span>
        
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-[9px] font-mono leading-tight">
          
          <div className="flex items-center gap-2.5 bg-neutral-950/40 p-2.5 rounded border border-neutral-850/60">
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-bold text-[8px] border ${compatibility.pglPass ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" : "text-neutral-500 border-neutral-800"}`}>
              {compatibility.pglPass ? "✓" : "✗"}
            </div>
            <div>
              <span className="font-bold text-neutral-400 block">PGL IDENTITY</span>
              <span className="text-neutral-500">{compatibility.pglPass ? "Validated Signature" : "Insufficient Security"}</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-neutral-950/40 p-2.5 rounded border border-neutral-850/60">
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-bold text-[8px] border ${compatibility.sekedPass ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" : "text-neutral-500 border-neutral-800"}`}>
              {compatibility.sekedPass ? "✓" : "✗"}
            </div>
            <div>
              <span className="font-bold text-neutral-400 block">SEKED POLICY GATE</span>
              <span className="text-neutral-500">{compatibility.sekedPass ? "Policy Approved" : "Policy Rejected"}</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-neutral-950/40 p-2.5 rounded border border-neutral-850/60">
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-bold text-[8px] border ${compatibility.executionPass ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" : "text-neutral-500 border-neutral-800"}`}>
              {compatibility.executionPass ? "✓" : "✗"}
            </div>
            <div>
              <span className="font-bold text-neutral-400 block">EXECUTION IDENTITY</span>
              <span className="text-neutral-500">{compatibility.executionPass ? "Ready to Mint" : "Reliability Low"}</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-neutral-950/40 p-2.5 rounded border border-neutral-850/60">
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-bold text-[8px] border ${compatibility.mcpPass ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" : "text-neutral-500 border-neutral-800"}`}>
              {compatibility.mcpPass ? "✓" : "✗"}
            </div>
            <div>
              <span className="font-bold text-neutral-400 block">MCP TOOL BOUNDARY</span>
              <span className="text-neutral-500">{compatibility.mcpPass ? "Within Tool Scope" : "Scope Exceeds Capacity"}</span>
            </div>
          </div>

        </div>
      </div>

      {/* Button controls to finish up Character Generation */}
      <div className="pt-2 flex justify-between gap-3 text-[10px] font-mono">
        <div className="flex flex-col text-[11px] justify-center">
          <span className="text-neutral-450 uppercase uppercase">Arena Readiness Metric:</span>
          <span className={`font-black uppercase text-xs ${pointsRemaining === 0 ? "text-cyan-400" : "text-rose-500"}`}>
            {pointsRemaining === 0 
              ? `${attributes.reliability * 10}% COMPLIANT & READY`
              : `Awaiting Point Sync (${Math.abs(pointsRemaining)} PTS off)`
            }
          </span>
        </div>
        
        <button
          onClick={handleCreateAgent}
          disabled={totalPointsSpent !== 20}
          className={`px-5 py-3 rounded text-[10px] font-black uppercase tracking-wider flex items-center gap-2 transition duration-200 cursor-pointer ${
            totalPointsSpent === 20
              ? "bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_15px_rgba(6,182,212,0.15)] active:scale-95"
              : "bg-neutral-900 text-neutral-500 border border-neutral-850 cursor-not-allowed"
          }`}
        >
          <UserPlus className="w-4 h-4" /> Register Agent Identity
        </button>
      </div>

    </div>
  );
}
