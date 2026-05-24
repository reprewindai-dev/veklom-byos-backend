import React, { useState, useEffect } from "react";
import { 
  Heart, 
  ShieldAlert, 
  CheckCircle2, 
  Lock, 
  Coins, 
  Cpu, 
  Volume2, 
  RefreshCw,
  TrendingDown,
  Play,
  ArrowRight,
  Brain,
  Zap,
  Sparkles,
  Activity,
  Gauge,
  Database,
  ShieldCheck
} from "lucide-react";
import { api } from "../services/api";
import { WorkspaceModel, SecurityEvent, ThreatStats } from "../types";

interface DashboardTabProps {
  isDarkMode: boolean;
  onNavigateToPlayground: () => void;
}

export default function DashboardTab({ isDarkMode, onNavigateToPlayground }: DashboardTabProps) {
  const [platformStatus, setPlatformStatus] = useState<any>(null);
  const [hardware, setHardware] = useState({ cpu: 32.4, memory: 1408, concurrency: 12 });
  const [models, setModels] = useState<WorkspaceModel[]>([]);
  const [alerts, setAlerts] = useState<SecurityEvent[]>([]);
  const [threats, setThreats] = useState<ThreatStats>({ totalScanned: 5410, blockedIncidents: 142, piiMaskedCount: 890, sandboxViolationsResolved: 15 });
  const [wallet, setWallet] = useState({ balanceUsd: 1845.50 });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // --- NABAOS CONFIG & SIMULATOR STATES ---
  const [viewMode, setViewMode] = useState<"mainframe" | "nabaos">("mainframe");
  const [cacheStats, setCacheStats] = useState<any>(null);

  // Slider controls for 130-agent cost variables
  const [agentCount, setAgentCount] = useState(130);
  const [reflectionLoops, setReflectionLoops] = useState(10);
  const [unreliabilityRate, setUnreliabilityRate] = useState(20);
  const [trafficVolume, setTrafficVolume] = useState(25000);

  // Load execution simulation states
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulatedTiers, setSimulatedTiers] = useState<number[]>([0, 0, 0, 0, 0]);
  const [simSavingPennies, setSimSavingPennies] = useState(0);
  const [simOriginalCost, setSimOriginalCost] = useState(0);
  const [simOptimizedCost, setSimOptimizedCost] = useState(0);

  // Prompt canonicalization text arena states
  const [sandboxPrompt, setSandboxPrompt] = useState("Draft an EMTA declared income tax credit statement audit for Tallinn household GDPR records");
  const [sandboxAnalysis, setSandboxAnalysis] = useState<any>(null);

  const fetchCacheStats = async () => {
    try {
      const res = await fetch("/api/v1/byos/config");
      const data = await res.json();
      if (data && data.cacheStats) {
        setCacheStats(data.cacheStats);
      }
    } catch (err) {
      console.error("Failed to fetch cache stats", err);
    }
  };

  const fetchDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const [statusRes, modelsRes, securityRes, balanceRes] = await Promise.all([
        api.getStatus(),
        api.getWorkspaceModels(),
        api.getSecurityDashboard(),
        api.getWalletBalance()
      ]);

      setPlatformStatus(statusRes);
      setModels(modelsRes);
      setAlerts(securityRes.events.slice(0, 4));
      setThreats(securityRes.threatStats);
      setWallet(balanceRes);
    } catch (err) {
      console.error("Failed to load dashboard statistics", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Analyze quick text changes and decompose into W5H2 keys
  const analyzeSandboxPrompt = (promptText: string) => {
    const textLower = promptText.toLowerCase();
    let whatValue = "process_general_query";
    let whereValue = "sovereign_hub_cache";
    let whoValue = "citizen_admin";
    let whyValue = "resolve citizen administrative intent";
    let howValue = "general_parameters";
    let howMuchValue = "none";
    let matchedTier = 5;
    let fallbackText = "No direct matching patterns. Assigned to Tier 5 Frontier LLM.";

    if (textLower.includes("refund") || textLower.includes("tax") || textLower.includes("declared") || textLower.includes("income")) {
      whatValue = "check_refund_estimate";
      whereValue = "emta_portal";
      whoValue = "citizen_admin";
      whyValue = "calculate overpaid income tax credits";
      howValue = "income_declaration";
      howMuchValue = "€412.50";
      matchedTier = 2;
      fallbackText = "Tier 2 BERT Classifier: Template signature matched EMTA financial check.";
    } else if (textLower.includes("vaccine") || textLower.includes("tetanus") || textLower.includes("lisinopril") || textLower.includes("health") || textLower.includes("med") || textLower.includes("immunize")) {
      whatValue = "retrieve_immunizations_scripts";
      whereValue = "health_registry";
      whoValue = "citizen_admin";
      whyValue = "verify national immunization certificates and scripts";
      howValue = "Lisinopril active check, Tetanus vaccine status";
      howMuchValue = "dosage: 10mg once daily";
      matchedTier = 2;
      fallbackText = "Tier 2 BERT Classifier: Template matched patient medical records.";
    } else if (textLower.includes("gdpr") || textLower.includes("regulation") || textLower.includes("civil") || textLower.includes("household") || textLower.includes("residence") || textLower.includes("citizen")) {
      whatValue = "verify_residence_household";
      whereValue = "civil_registry";
      whoValue = "citizen_admin";
      whyValue = "validate household residents under compliance rules";
      howValue = "Harju region audit";
      howMuchValue = "GDPR-101";
      matchedTier = 3;
      fallbackText = "Tier 3 SetFit Classifier: Classified as long-tail regulatory query.";
    } else if (promptText.length < 40) {
      whatValue = "execute_simple_action";
      whereValue = "local_system";
      matchedTier = 4;
      fallbackText = "Tier 4 Cheap LLM: Small parameter slot-filling template applied.";
    }

    setSandboxAnalysis({
      what: whatValue,
      where: whereValue,
      who: whoValue,
      when: new Date().toISOString().split("T")[0],
      why: whyValue,
      how: howValue,
      howMuch: howMuchValue,
      tier: matchedTier,
      tierReason: fallbackText
    });
  };

  const runLoadSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setSimulatedTiers([0, 0, 0, 0, 0]);
    setSimSavingPennies(0);
    setSimOriginalCost(0);
    setSimOptimizedCost(0);

    const duration = 2500;
    const intervalMs = 50;
    const steps = duration / intervalMs;
    let stepCount = 0;

    const finalOriginalCost = 100.00;
    const finalOptimizedCost = 2.16;
    const finalSavingPennies = (finalOriginalCost - finalOptimizedCost) * 100;

    const timer = setInterval(() => {
      stepCount++;
      const ratio = stepCount / steps;

      setSimulatedTiers([
        Math.floor(ratio * 60),
        Math.floor(ratio * 640),
        Math.floor(ratio * 180),
        Math.floor(ratio * 100),
        Math.floor(ratio * 20),
      ]);

      setSimOriginalCost(+(ratio * finalOriginalCost).toFixed(2));
      setSimOptimizedCost(+(ratio * finalOptimizedCost).toFixed(2));
      setSimSavingPennies(Math.floor(ratio * finalSavingPennies));

      if (stepCount >= steps) {
        clearInterval(timer);
        setIsSimulating(false);
        fetchCacheStats();
      }
    }, intervalMs);
  };

  useEffect(() => {
    fetchDashboardData();
    fetchCacheStats();
    analyzeSandboxPrompt(sandboxPrompt);

    // Setup periodic polling for live hardware pulse telemetry
    const interval = setInterval(async () => {
      try {
        const live = await api.getLivePulse();
        setHardware({
          cpu: live.signals.cpuPercent,
          memory: live.signals.memoryMb,
          concurrency: live.signals.concurrencyGauge
        });
        fetchCacheStats();
      } catch {
        // Silent fallback
      }
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  // Recalculate quick prompt analytics on edit
  useEffect(() => {
    analyzeSandboxPrompt(sandboxPrompt);
  }, [sandboxPrompt]);

  return (
    <div className="flex flex-col gap-6" id="dashboard-tab">
      
      {/* Top Banner Core Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        
        {/* Metric 1: Platform Status */}
        <div className={`p-5 rounded-3xl border transition-all ${
          isDarkMode 
            ? "bg-zinc-900/30 border-zinc-900/60 text-zinc-150 hover:border-zinc-800" 
            : "bg-white border-zinc-200 text-zinc-800 shadow-sm shadow-zinc-100"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Platform Status</span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          </div>
          <p className="text-xl font-black mt-2 tracking-tight">Active</p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">
            {platformStatus ? platformStatus.firewall + " firewall active" : "e-Estonia Network"}
          </p>
        </div>

        {/* Metric 2: Sovereign Wallet */}
        <div className={`p-5 rounded-3xl border transition-all ${
          isDarkMode 
            ? "bg-zinc-900/30 border-zinc-900/60 text-zinc-150 hover:border-zinc-800" 
            : "bg-white border-zinc-200 text-zinc-800 shadow-sm shadow-zinc-100"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Sovereign Wallet</span>
            <Coins className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-xl font-black mt-2 tracking-tight">
            ${wallet.balanceUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">Simulated USD Deposits</p>
        </div>

        {/* Metric 3: NabaOS Cache Savings (NEW - Dynamically populated from backend) */}
        <div className={`p-5 rounded-3xl border transition-all ${
          isDarkMode 
            ? "bg-[#090b10]/80 border-indigo-900/40 text-zinc-150 hover:border-indigo-800/60 shadow-lg shadow-indigo-950/20" 
            : "bg-indigo-50/10 border-indigo-150 text-indigo-955 shadow-sm shadow-indigo-100"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider">NabaOS™ Savings</span>
            <TrendingDown className="w-4 h-4 text-emerald-450 animate-pulse" />
          </div>
          <p className="text-xl font-black mt-2 tracking-tight text-emerald-400">
            ${(((cacheStats ? cacheStats.estimatedComputeSavedPennies : 94132.89) / 100)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">
            {cacheStats ? cacheStats.hits : 452} computed cache hits
          </p>
        </div>

        {/* Metric 4: Audit Blockchain */}
        <div className={`p-5 rounded-3xl border transition-all ${
          isDarkMode 
            ? "bg-zinc-900/30 border-zinc-900/60 text-zinc-150 hover:border-zinc-800" 
            : "bg-white border-zinc-200 text-zinc-800 shadow-sm shadow-zinc-100"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Audit Blockchain</span>
            <Lock className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-xl font-black mt-2 tracking-tight">
            {platformStatus ? platformStatus.blockchainHeight : 0} Blocks
          </p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">Cryptographic chained logs</p>
        </div>

        {/* Metric 5: Threat Shields */}
        <div className={`p-5 rounded-3xl border transition-all ${
          isDarkMode 
            ? "bg-zinc-900/30 border-zinc-900/60 text-zinc-150 hover:border-zinc-800" 
            : "bg-white border-zinc-200 text-zinc-800 shadow-sm shadow-zinc-100"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Threat Shields</span>
            <ShieldAlert className="w-4 h-4 text-rose-500 animate-bounce" />
          </div>
          <p className="text-xl font-black mt-2 tracking-tight text-rose-500">
            {threats.blockedIncidents} Blocked
          </p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">{threats.totalScanned} prompts checked</p>
        </div>

      </div>

      {/* Main split grid: Diagnostics and Models */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COMPONENT: Live Observable Signal (8 Cols) */}
        <div className={`lg:col-span-7 p-8 rounded-3xl border ${
          isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200"
        }`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold tracking-tight">Mainframe Live Observability Signals</h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Real-time hardware resource telemetry</p>
            </div>
            <button 
              onClick={fetchDashboardData}
              disabled={isRefreshing}
              className={`p-2 rounded-xl border transition-all ${
                isRefreshing ? "animate-spin cursor-not-allowed text-zinc-650" : "hover:bg-zinc-800 cursor-pointer text-indigo-400"
              }`}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-col gap-5">
            {/* CPU Signal */}
            <div>
              <div className="flex items-center justify-between text-xs font-bold mb-2">
                <span className="flex items-center gap-1.5 text-zinc-400">
                  <Cpu className="w-4 h-4 text-blue-500" /> Administrative CPU Nodes
                </span>
                <span className="font-mono text-zinc-200">{hardware.cpu}%</span>
              </div>
              <div className="h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-1000"
                  style={{ width: `${hardware.cpu}%` }}
                ></div>
              </div>
            </div>

            {/* Memory Signal */}
            <div>
              <div className="flex items-center justify-between text-xs font-bold mb-2">
                <span className="flex items-center gap-1.5 text-zinc-400">
                  <Volume2 className="w-4 h-4 text-purple-500" /> Allocated Private RAM
                </span>
                <span className="font-mono text-zinc-200">{hardware.memory} MB / 8192 MB</span>
              </div>
              <div className="h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-purple-500 transition-all duration-1000"
                  style={{ width: `${(hardware.memory / 8192) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Simulated Live telemetry points */}
            <div className="grid grid-cols-3 gap-2 mt-2">
              <div className={`p-4 rounded-xl border text-center ${isDarkMode ? "bg-zinc-950/40 border-zinc-900" : "bg-zinc-50 border-zinc-150"}`}>
                <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">Average Latency</p>
                <p className="text-base font-black text-indigo-400 mt-1 font-mono">142ms</p>
              </div>
              <div className={`p-4 rounded-xl border text-center ${isDarkMode ? "bg-zinc-950/40 border-zinc-900" : "bg-zinc-50 border-zinc-150"}`}>
                <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">PII Mask Shield</p>
                <p className="text-base font-black text-emerald-400 mt-1 font-mono">{threats.piiMaskedCount}</p>
              </div>
              <div className={`p-4 rounded-xl border text-center ${isDarkMode ? "bg-zinc-950/40 border-zinc-900" : "bg-zinc-50 border-zinc-150"}`}>
                <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">Concurrences</p>
                <p className="text-base font-black text-pink-400 mt-1 font-mono">{hardware.concurrency}</p>
              </div>
            </div>
            
            <div className="pt-4 border-t border-zinc-800/40 flex items-center justify-between">
              <p className="text-xs text-zinc-500">Need to execute prompt queries through Bürokratt security gates?</p>
              <button 
                onClick={onNavigateToPlayground}
                className="px-4.5 py-2 hover:bg-indigo-600 bg-indigo-700 font-bold text-xs rounded-xl text-white transition-all cursor-pointer"
              >
                Go to AI Playground
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COMPONENT: Sovereign Models Catalog (5 Cols) */}
        <div className={`lg:col-span-5 p-8 rounded-3xl border ${
          isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200"
        }`}>
          <h3 className="text-sm font-bold tracking-tight mb-4">Sovereign Models Access Registry</h3>
          <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
            {models.map((model) => (
              <div 
                key={model.id}
                className={`p-3.5 rounded-2xl border flex items-center justify-between text-xs transition-all ${
                  model.active 
                    ? isDarkMode 
                      ? "bg-zinc-950/30 border-indigo-900/40 text-zinc-250" 
                      : "bg-indigo-50/20 border-indigo-100 text-zinc-800"
                    : isDarkMode 
                      ? "bg-zinc-950/10 border-zinc-900/40 text-zinc-500" 
                      : "bg-zinc-50/50 border-zinc-200 text-zinc-500"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="font-bold truncate text-zinc-200">{model.name}</p>
                  <p className="text-[10px] text-zinc-500 mt-0.5 truncate font-medium">Provider: {model.provider} • Context: {model.contextLength.toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest font-bold shrink-0">
                  {model.active ? (
                    <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 block"></span> Active
                    </span>
                  ) : (
                    <span className="text-zinc-550 flex items-center gap-1 font-semibold">
                      Offline
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Incident alerts panel */}
      <div className={`p-8 rounded-3xl border ${
        isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200"
      }`}>
        <h3 className="text-sm font-bold tracking-tight mb-1">Recent Security & Sandbox Gate Warnings</h3>
        <p className="text-[11px] text-zinc-500 mb-5">Continuous logging matching system firewall regulations</p>
        
        <div className="flex flex-col gap-3">
          {alerts.map((al) => (
            <div 
              key={al.id}
              className={`p-4 rounded-2xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                al.severity === "critical"
                  ? isDarkMode ? "bg-rose-950/10 border-rose-900/45 text-rose-200" : "bg-rose-50 border-rose-200 text-rose-800"
                  : al.severity === "warning"
                    ? isDarkMode ? "bg-amber-950/15 border-amber-900/40 text-amber-200" : "bg-amber-50 border-amber-200 text-amber-800"
                    : isDarkMode ? "bg-zinc-950/40 border-zinc-900 text-zinc-455" : "bg-zinc-50 border-zinc-200 text-zinc-750"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 mt-0.5 font-mono ${
                  al.severity === "critical" 
                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/40" 
                    : al.severity === "warning"
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-zinc-800/60 text-zinc-400"
                }`}>
                  {al.severity}
                </span>
                <div>
                  <p className="font-semibold text-zinc-250 leading-relaxed font-sans">{al.message}</p>
                  <p className="text-[10px] text-zinc-500 font-medium font-mono mt-0.5">
                    Triggered: {new Date(al.timestamp).toLocaleString()} • Module: {al.category}
                  </p>
                </div>
              </div>
              <div className="text-right shrink-0">
                {al.blocked ? (
                  <span className="text-red-400 font-bold font-mono tracking-wider text-[10px] uppercase">
                    HARDBLOCKED
                  </span>
                ) : (
                  <span className="text-emerald-400 font-bold font-mono tracking-wider text-[10px] uppercase">
                    PERMITTED & LOGGED
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
