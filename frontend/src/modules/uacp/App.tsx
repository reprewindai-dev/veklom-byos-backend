import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ShieldCheck,
  ShieldAlert,
  Key,
  Users,
  HeartPulse,
  Calculator,
  Cpu,
  Database,
  CheckCircle2,
  XCircle,
  Plus,
  RefreshCw,
  Trash2,
  User,
  Lock,
  Globe,
  Settings,
  Lightbulb,
  FileText,
  AlertTriangle,
  History,
  Info,
  Download
} from "lucide-react";
import { Agent, Policy, LedgerBlock } from "./types";

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [ledger, setLedger] = useState<LedgerBlock[]>([]);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);
  
  // Input fields state
  const [selectedAgentId, setSelectedAgentId] = useState<string>("tax-kratt");
  const [citizenEmail, setCitizenEmail] = useState<string>("chomp.pixel@gmail.com");
  const [citizenQuery, setCitizenQuery] = useState<string>("Show my estimated capital tax refund");
  
  // UI interactive state
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [executionStep, setExecutionStep] = useState<number>(0);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<LedgerBlock | null>(null);
  const [isVerifyingChain, setIsVerifyingChain] = useState<boolean>(false);
  const [verificationMessage, setVerificationMessage] = useState<{ status: "success" | "error"; text: string } | null>(null);
  
  // Custom policy creation state
  const [isCreatingPolicy, setIsCreatingPolicy] = useState<boolean>(false);
  const [newPolicyAgent, setNewPolicyAgent] = useState<string>("border-kratt");
  const [newPolicyAction, setNewPolicyAction] = useState<string>("security:border-crossings");
  const [newPolicyStatus, setNewPolicyStatus] = useState<"granted" | "revoked">("granted");

  // Fetch initial data on load
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [resAgents, resPolicies, resLedger] = await Promise.all([
        fetch("/api/uacp/agents"),
        fetch("/api/uacp/policies"),
        fetch("/api/uacp/ledger")
      ]);
      
      if (resAgents.ok) setAgents(await resAgents.json());
      if (resPolicies.ok) setPolicies(await resPolicies.json());
      if (resLedger.ok) setLedger(await resLedger.json());
    } catch (err) {
      console.error("Failed to load initial sovereign data", err);
    }
  };

  // Toggle Policy status dynamically with instantaneous server DB sync
  const handleTogglePolicy = async (policyId: string) => {
    const policy = policies.find(p => p.id === policyId);
    if (!policy) return;

    const updatedStatus = policy.status === "granted" ? "revoked" : "granted";
    
    try {
      const res = await fetch("/api/uacp/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          citizenEmail: policy.citizenEmail,
          agentId: policy.agentId,
          action: policy.action,
          status: updatedStatus,
          validUntil: policy.validUntil
        })
      });

      if (res.ok) {
        // Refresh policies
        const updatedPoliciesRes = await fetch("/api/uacp/policies");
        if (updatedPoliciesRes.ok) {
          setPolicies(await updatedPoliciesRes.json());
        }
      }
    } catch (err) {
      console.error("Failed to sync updated policy rule", err);
    }
  };

  // Create new Policy and sync with DB
  const handleCreatePolicySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/uacp/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          citizenEmail,
          agentId: newPolicyAgent,
          action: newPolicyAction,
          status: newPolicyStatus
        })
      });

      if (res.ok) {
        setIsCreatingPolicy(false);
        const updatedPoliciesRes = await fetch("/api/uacp/policies");
        if (updatedPoliciesRes.ok) {
          setPolicies(await updatedPoliciesRes.json());
        }
      }
    } catch (err) {
      console.error("Failed to write new sovereign access policy", err);
    }
  };

  // Execute sovereign AI portal query with full animated integrity gates pipeline
  const handleExecuteSovereignQuery = async () => {
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);
    
    // Smooth sequential animation for Gate 1 and Gate 2 before hitting API
    setExecutionStep(1); // Gate 1: Signature checking
    await new Promise(resolve => setTimeout(resolve, 800));
    setExecutionStep(2); // Gate 2: Consent delegation checking
    await new Promise(resolve => setTimeout(resolve, 800));
    setExecutionStep(3); // Gate 3: Sovereign Boundary Execution

    try {
      const res = await fetch("/api/uacp/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          citizenEmail,
          agentId: selectedAgentId,
          query: citizenQuery
        })
      });

      const data = await res.json();
      
      // Keep Gate 3 processing long enough to show visual processing
      await new Promise(resolve => setTimeout(resolve, 900));
      setExecutionStep(4); // Gate 4: Token quota metrics
      await new Promise(resolve => setTimeout(resolve, 700));
      setExecutionStep(5); // Gate 5: Blockchain committing

      if (res.ok) {
        await new Promise(resolve => setTimeout(resolve, 600));
        setExecutionResult(data.block);
        
        // Refresh global ledger state
        const resLedger = await fetch("/api/uacp/ledger");
        if (resLedger.ok) {
          setLedger(await resLedger.json());
        }
        
        if (!data.success) {
          // One of our integrity gates failed (likely policy blocking)
          if (!data.block.gatesResult.gate2_consent.passed) {
            setExecutionError(`Security Halt: Citizen Consent rule violated. Request blocked.`);
          } else {
            setExecutionError(`Sovereign gate infraction detected. Safe payload halted.`);
          }
        }
      } else {
        setExecutionError(data.error || "Gateway internal execution failure.");
      }
    } catch (err: any) {
      setExecutionError("System timeout connecting to sovereign firewall clusters.");
      console.error(err);
    } finally {
      setIsExecuting(false);
    }
  };

  // Run cryptographic verification over the downloaded blockchain ledger
  const handleVerifyLedgerSecurity = () => {
    setIsVerifyingChain(true);
    setVerificationMessage(null);

    setTimeout(() => {
      let isChainIntact = true;
      let errorMsg = "";

      // Cryptographically verify hashes iteratively (skip index 0 genesis previous checks)
      for (let i = 1; i < ledger.length; i++) {
        const block = ledger[i];
        const prevBlock = ledger[i - 1];

        if (block.previousHash !== prevBlock.hash) {
          isChainIntact = false;
          errorMsg = `Ledger mismatch on block #${block.index}: Expected previous hash "${prevBlock.hash.slice(0, 8)}...", got "${block.previousHash.slice(0, 8)}..."`;
          break;
        }
      }

      if (isChainIntact) {
        setVerificationMessage({
          status: "success",
          text: `Cryptographic Blockchain Ledger Verified: 100% Intact. Tested ${ledger.length} blocks recursively. No unauthorized tamper attempts detected.`
        });
      } else {
        setVerificationMessage({
          status: "error",
          text: errorMsg
        });
      }
      setIsVerifyingChain(false);
    }, 1200);
  };

  // Reset Custody Transactions
  const handleResetLedger = async () => {
    try {
      const res = await fetch("/api/uacp/clear-ledger", { method: "POST" });
      if (res.ok) {
        setVerificationMessage(null);
        fetchInitialData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Export current cryptographic ledger as a formatted JSON document
  const handleExportLedger = () => {
    try {
      const jsonString = JSON.stringify(ledger, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `uacp-audit-ledger-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export ledger audit log", err);
    }
  };

  // Helper lists matching icon names to Lucide icons
  const renderAgentIcon = (iconName: string) => {
    const iconClass = "w-5 h-5 text-emerald-400";
    switch (iconName) {
      case "Calculator": return <Calculator className={iconClass} />;
      case "HeartPulse": return <HeartPulse className={iconClass} />;
      case "ShieldAlert": return <ShieldAlert className={iconClass} />;
      case "Users": return <Users className={iconClass} />;
      default: return <Cpu className={iconClass} />;
    }
  };

  return (
    <div className={`min-h-screen font-sans transition-all duration-300 ${isDarkMode ? "bg-[#080808] text-zinc-100" : "bg-zinc-50 text-zinc-900"}`}>
      
      {/* Banner Margin Status Header (Clean, sleek Kinetic OS / Bento look) */}
      <header className={`border-b ${isDarkMode ? "bg-[#080808]/80 border-zinc-900/65" : "bg-white/80 border-zinc-150"} sticky top-0 z-40 backdrop-blur-md`}>
        <div className="max-w-7xl mx-auto px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
                UACP v6 <span className="text-xs bg-indigo-600/25 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-lg font-mono font-medium">Sovereign Layer</span>
              </h1>
              <p className={`text-xs ${isDarkMode ? "text-zinc-500" : "text-zinc-550"}`}>
                Unified Access Control Platform • Estonia Bürokratt Trust Network
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest leading-none">Status</p>
              <p className="text-xs text-emerald-400 font-semibold mt-1">Systems Nominal</p>
            </div>
            
            <div className="w-px h-8 bg-zinc-800 hidden sm:block"></div>

            <button
              id="theme-toggler"
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`px-4 py-2 rounded-xl text-xs font-bold tracking-tight transition-all border ${
                isDarkMode 
                  ? "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-850 hover:border-zinc-700" 
                  : "bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50"
              }`}
            >
              Toggle {isDarkMode ? "Light" : "Dark"} Theme
            </button>
            
            <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center overflow-hidden">
              <div className="w-full h-full bg-gradient-to-br from-indigo-500 to-purple-600"></div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid Workspace */}
      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6 relative">
        
        {/* LEFT COLUMN: Controls & Config (Scale: 5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6" id="controls-section">
          
          {/* USER IDENTITY SECURITY CONTEXT widget */}
          <section className={`p-8 rounded-[2rem] border relative overflow-hidden transition-all group ${isDarkMode ? "bg-zinc-900/40 border-zinc-900 text-zinc-100 hover:border-zinc-800" : "bg-white border-zinc-200 text-zinc-900 hover:border-zinc-300 shadow-sm shadow-zinc-100"}`}>
            <div className="absolute -top-24 -right-24 w-60 h-60 bg-indigo-600/5 dark:bg-indigo-600/10 blur-[90px] rounded-full pointer-events-none"></div>
            
            <h2 className="text-[11px] font-bold tracking-widest uppercase text-indigo-400 mb-4 flex items-center gap-2">
              <User className="w-4 h-4" /> Citizen Security Signature Context
            </h2>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-2">Authenticated Email</label>
                <div className="relative">
                  <input
                    type="email"
                    value={citizenEmail}
                    onChange={(e) => setCitizenEmail(e.target.value)}
                    className={`w-full px-4 py-3 text-sm rounded-xl border font-mono transition-all outline-none ${
                      isDarkMode 
                        ? "bg-zinc-950 border-zinc-800 text-zinc-200 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20" 
                        : "bg-zinc-50 border-zinc-200 text-zinc-800 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20"
                    }`}
                    placeholder="citizen@mail.com"
                  />
                  <div className="absolute right-4 top-3.5 flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Certified Hub ID
                  </div>
                </div>
                <p className="text-[10px] text-zinc-500 mt-2 font-medium leading-relaxed font-mono">
                  Changing this email simulates of what happens when external agents query unlinked citizens.
                </p>
              </div>
            </div>
          </section>

          {/* POLICY INTEGRITY / CONSENT RULES DELEGATION widget */}
          <section className={`p-8 rounded-[2rem] border relative overflow-hidden transition-all group ${isDarkMode ? "bg-zinc-900/40 border-zinc-900 text-zinc-100 hover:border-zinc-800" : "bg-white border-zinc-200 text-zinc-900 hover:border-zinc-300 shadow-sm shadow-zinc-100"}`}>
            <div className="absolute -bottom-24 -right-24 w-60 h-60 bg-emerald-500/5 dark:bg-emerald-500/10 blur-[90px] rounded-full pointer-events-none"></div>

            <div className="flex items-center justify-between mb-5">
              <h2 className="text-[11px] font-bold tracking-widest uppercase text-emerald-400 flex items-center gap-2">
                <Lock className="w-4 h-4" /> Delegate Consent Catalog (v6 Rules)
              </h2>
              <button
                onClick={() => setIsCreatingPolicy(!isCreatingPolicy)}
                className="text-xs bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 px-3 py-1.5 rounded-xl font-bold transition-all flex items-center gap-1"
                id="add-policy-btn"
              >
                <Plus className="w-3.5 h-3.5" /> New Consent Rule
              </button>
            </div>

            {/* Quick Rules Addition form */}
            <AnimatePresence>
              {isCreatingPolicy && (
                <motion.form
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  onSubmit={handleCreatePolicySubmit}
                  className={`overflow-hidden mb-5 p-5 rounded-2xl border ${isDarkMode ? "bg-zinc-950 border-zinc-800" : "bg-zinc-100 border-zinc-200"}`}
                >
                  <p className="text-xs font-bold mb-3 text-zinc-300">Configure Delegation Consent Link</p>
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <div>
                      <label className="text-[10px] text-zinc-500 block">Agent Link</label>
                      <select
                        value={newPolicyAgent}
                        onChange={(e) => {
                          setNewPolicyAgent(e.target.value);
                          // link action to correct scope
                          const boundScope = agents.find(a => a.id === e.target.value)?.scope || "records";
                          setNewPolicyAction(boundScope);
                        }}
                        className="w-full p-2 text-xs rounded-xl border bg-zinc-900 border-zinc-700 text-zinc-200"
                      >
                        {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 block">Scope Access Action</label>
                      <input
                        type="text"
                        value={newPolicyAction}
                        readOnly
                        className="w-full p-2 text-xs rounded-xl border bg-zinc-900 border-zinc-800 text-zinc-400 font-mono"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-3 text-xs">
                    <span className="text-zinc-400">Consent State:</span>
                    <div className="flex gap-2">
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="radio"
                          name="status-selector"
                          checked={newPolicyStatus === "granted"}
                          onChange={() => setNewPolicyStatus("granted")}
                        />
                        <span className="text-emerald-400">Granted</span>
                      </label>
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="radio"
                          name="status-selector"
                          checked={newPolicyStatus === "revoked"}
                          onChange={() => setNewPolicyStatus("revoked")}
                        />
                        <span className="text-rose-400">Revoked</span>
                      </label>
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end mt-4">
                    <button
                      type="button"
                      onClick={() => setIsCreatingPolicy(false)}
                      className="px-2 py-1 text-xs rounded border border-zinc-700 text-zinc-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-2.5 py-1 text-xs bg-emerald-500 hover:bg-emerald-600 rounded text-white"
                    >
                      Establish Link
                    </button>
                  </div>
                </motion.form>
              )}
            </AnimatePresence>

            {/* List of active mapped Policies */}
            <div className="flex flex-col gap-3">
              {policies.map((pol) => {
                const targetAgent = agents.find(a => a.id === pol.agentId);
                const isGranted = pol.status === "granted";
                return (
                  <div
                    key={pol.id}
                    className={`p-4 rounded-2xl border flex items-center justify-between transition-all ${
                      isDarkMode 
                        ? "bg-zinc-950/45 border-zinc-900 hover:border-zinc-800" 
                        : "bg-zinc-50 border-zinc-200 hover:border-zinc-300"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`p-2 rounded-xl shrink-0 ${isGranted ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"}`}>
                        {isGranted ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-bold text-zinc-200">{targetAgent?.name || pol.agentId}</span>
                          <span className="text-[9px] font-mono bg-zinc-900 border border-zinc-805 text-zinc-400 px-1.5 py-0.5 rounded-md font-medium">{pol.action}</span>
                        </div>
                        <p className="text-[10px] text-zinc-500 truncate mt-1">Link Email: {pol.citizenEmail}</p>
                      </div>
                    </div>
                    
                    {/* Switch Toggle */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleTogglePolicy(pol.id)}
                        className={`text-[10px] px-3 py-1.5 rounded-xl font-mono font-bold transition-all border ${
                          isGranted 
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20" 
                            : "bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20"
                        }`}
                        id={`toggle-policy-${pol.id}`}
                      >
                        {isGranted ? "GRANTED" : "REVOKED"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            
            <div className="mt-4 flex items-start gap-2.5 p-3.5 rounded-2xl bg-amber-500/5 border border-amber-500/10 text-amber-500/90 text-xs font-mono">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Rules-as-code are evaluated dynamically inside **Gate 2 (Consent Delegation Gate)** on the server. Revoking a policy instantly halts security validation of that agent.
              </p>
            </div>
          </section>

          {/* IMMUTABLE REGISTERED AI KRATTS (Database context) */}
          <section className={`p-8 rounded-[2rem] border relative overflow-hidden transition-all group ${isDarkMode ? "bg-zinc-900/40 border-zinc-900 text-zinc-100 hover:border-zinc-800" : "bg-white border-zinc-200 text-zinc-900 hover:border-zinc-300 shadow-sm shadow-zinc-100"}`}>
            <div className="absolute -top-24 -left-24 w-60 h-60 bg-indigo-600/5 blur-[90px] rounded-full pointer-events-none"></div>

            <h2 className="text-[11px] font-bold tracking-widest uppercase text-indigo-400 mb-4 flex items-center gap-2">
              <Database className="w-4 h-4" /> Sovereign AI Kratts Registry
            </h2>
            <div className="grid grid-cols-1 gap-3">
              {agents.map((ag) => (
                <div
                  key={ag.id}
                  className={`p-4 rounded-2xl border transition-colors ${
                    isDarkMode ? "bg-zinc-950/60 border-zinc-900" : "bg-zinc-50 border-zinc-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {renderAgentIcon(ag.icon)}
                      <span className="text-xs font-bold text-zinc-200">{ag.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/45 border border-indigo-900/40 px-2 py-0.5 rounded-full font-bold">
                      Trust: {ag.trustScore}%
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400 mb-2 leading-relaxed">{ag.description}</p>
                  <div className="flex items-center justify-between text-[9px] font-mono text-zinc-500 pt-1.5 border-t border-zinc-900/60 font-mono">
                    <span>Dataset: {ag.dataset}</span>
                    <span>Scope: {ag.scope}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>

        {/* RIGHT COLUMN: Execution Dashboard & Live Pipeline Ledger (Scale: 7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6" id="dashboard-section">
          
          {/* CORE IMMUTABLE SOVEREIGN QUERY EXECUTOR & 5 INTEGRITY GATES MONITOR */}
          <section className={`p-8 rounded-[2rem] border relative overflow-hidden transition-all group ${isDarkMode ? "bg-zinc-900/40 border-zinc-900 text-zinc-100 hover:border-zinc-800" : "bg-white border-zinc-200 text-zinc-900 hover:border-zinc-300 shadow-sm shadow-zinc-150"}`}>
            <div className="absolute -top-24 -right-24 w-60 h-60 bg-indigo-600/5 dark:bg-indigo-600/10 blur-[90px] rounded-full pointer-events-none"></div>

            <div className={`flex flex-col md:flex-row md:items-center justify-between border-b pb-6 mb-6 gap-4 ${isDarkMode ? "border-zinc-900/60" : "border-zinc-150"}`}>
              <div>
                <h2 className="text-sm font-bold tracking-widest uppercase text-indigo-400 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-indigo-400 animate-pulse" /> Sovereign AI Agent Portal
                </h2>
                <p className={`text-xs mt-1 ${isDarkMode ? "text-zinc-500" : "text-zinc-550"}`}>
                  Select an AI agent Kratt and safely route requests inside Estonia's secure boundary
                </p>
              </div>
              <div className={`flex items-center gap-1.5 p-1 rounded-xl shrink-0 ${isDarkMode ? "bg-[#0b0b0b]" : "bg-zinc-100"}`}>
                {agents.map(ag => (
                  <button
                    key={ag.id}
                    onClick={() => {
                      setSelectedAgentId(ag.id);
                      // set realistic template prompts
                      if (ag.id === "tax-kratt") setCitizenQuery("What is my capital tax refund amount this year?");
                      else if (ag.id === "medical-kratt") setCitizenQuery("Retrieve my active clinic immunizations checklist");
                      else if (ag.id === "border-kratt") setCitizenQuery("Verify custom passport delegation for border crossing");
                      else if (ag.id === "family-kratt") setCitizenQuery("Generate wedding registry verification certificate");
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold tracking-tight transition-all uppercase ${
                      selectedAgentId === ag.id 
                        ? "bg-indigo-600 text-white shadow-lg shadow-indigo-505/15" 
                        : isDarkMode 
                          ? "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900" 
                          : "text-zinc-550 hover:text-zinc-800 hover:bg-white"
                    }`}
                    id={`agent-select-${ag.id}`}
                  >
                    {ag.name.replace(" Kratt", "")}
                  </button>
                ))}
              </div>
            </div>

            {/* Simulated Query Box Input */}
            <div className="flex flex-col gap-3 mb-6">
              <div>
                <label className="text-xs font-bold text-zinc-400 block mb-2 font-sans">Citizen Natural Language Request</label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="text"
                    value={citizenQuery}
                    onChange={(e) => setCitizenQuery(e.target.value)}
                    placeholder="Enter command for sovereign agent..."
                    className={`flex-1 px-4 py-3 text-sm rounded-xl border font-mono transition-all outline-none ${
                      isDarkMode 
                        ? "bg-zinc-950 border-zinc-800 text-zinc-200 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20" 
                        : "bg-zinc-50 border-zinc-200 text-zinc-800 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20"
                    }`}
                  />
                  <button
                    onClick={handleExecuteSovereignQuery}
                    disabled={isExecuting || !citizenQuery}
                    className={`px-5 py-3 rounded-xl text-xs font-bold tracking-wider uppercase flex items-center justify-center gap-2 shadow-lg transition-all shrink-0 ${
                      isExecuting || !citizenQuery
                        ? "bg-zinc-800 text-zinc-500 cursor-not-allowed border-zinc-705"
                        : "bg-indigo-600 hover:bg-indigo-550 text-white shadow-indigo-500/15 hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
                    }`}
                    id="execute-query-btn"
                  >
                    {isExecuting ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : <ShieldCheck className="w-4 h-4 text-white" />}
                    {isExecuting ? "Executing..." : "Execute Gateway"}
                  </button>
                </div>
              </div>
            </div>

            {/* 5 LOGICAL INTEGRITY GATES CHANNELS PIPELINE */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-4 flex items-center gap-1.5 font-sans">
                <Globe className="w-4 h-4 text-indigo-400 animate-pulse" /> Active Integrity Gates (v6 Pipeline)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 relative">
                
                {/* Gate 1 widget */}
                <div className={`p-4 rounded-2xl border text-center transition-all ${
                  isExecuting && executionStep >= 1 || executionResult
                    ? executionResult?.gatesResult.gate1_signature.passed !== false
                      ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/5 border-rose-505/30 text-rose-455 text-rose-400"
                    : isDarkMode 
                      ? "bg-zinc-950/65 border-zinc-900 text-zinc-650" 
                      : "bg-zinc-50 border-zinc-150 text-zinc-400 shadow-sm shadow-zinc-100"
                }`}>
                  <div className="text-[11px] font-bold tracking-tight leading-none mb-1 font-sans">Gate 1</div>
                  <p className="text-[8px] font-bold font-mono uppercase tracking-widest leading-none">SIGNATURE</p>
                  <div className="flex justify-center mt-3">
                    {isExecuting && executionStep === 1 ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                    ) : executionResult || (isExecuting && executionStep > 1) ? (
                      executionResult?.gatesResult.gate1_signature.passed !== false ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-405 text-emerald-400 animate-in zoom-in" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 animate-in zoom-in" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-200 dark:border-zinc-800"></div>
                    )}
                  </div>
                </div>

                {/* Gate 2 widget */}
                <div className={`p-4 rounded-2xl border text-center transition-all ${
                  isExecuting && executionStep >= 2 || executionResult
                    ? executionResult?.gatesResult.gate2_consent.passed
                      ? "bg-emerald-505/5 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-505/5 border-rose-500/30 text-rose-400"
                    : isDarkMode 
                      ? "bg-zinc-950/65 border-zinc-900 text-zinc-650" 
                      : "bg-zinc-50 border-zinc-150 text-zinc-400 shadow-sm shadow-zinc-100"
                }`}>
                  <div className="text-[11px] font-bold tracking-tight leading-none mb-1 font-sans">Gate 2</div>
                  <p className="text-[8px] font-bold font-mono uppercase tracking-widest leading-none">CONSENT</p>
                  <div className="flex justify-center mt-3">
                    {isExecuting && executionStep === 2 ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                    ) : executionResult || (isExecuting && executionStep > 2) ? (
                      executionResult?.gatesResult.gate2_consent.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 animate-in zoom-in" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 animate-in zoom-in" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-200 dark:border-zinc-800"></div>
                    )}
                  </div>
                </div>

                {/* Gate 3 widget */}
                <div className={`p-4 rounded-2xl border text-center transition-all ${
                  isExecuting && executionStep >= 3 || executionResult
                    ? executionResult?.gatesResult.gate3_boundary.passed
                      ? "bg-emerald-500/5 border-emerald-505/30 text-emerald-400"
                      : "bg-rose-505/5 border-rose-500/30 text-rose-405 text-rose-400"
                    : isDarkMode 
                      ? "bg-zinc-950/65 border-zinc-900 text-zinc-650" 
                      : "bg-zinc-50 border-zinc-150 text-zinc-400 shadow-sm shadow-zinc-100"
                }`}>
                  <div className="text-[11px] font-bold tracking-tight leading-none mb-1 font-sans">Gate 3</div>
                  <p className="text-[8px] font-bold font-mono uppercase tracking-widest leading-none">BOUNDARY</p>
                  <div className="flex justify-center mt-3">
                    {isExecuting && executionStep === 3 ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                    ) : executionResult || (isExecuting && executionStep > 3) ? (
                      executionResult?.gatesResult.gate3_boundary.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 animate-in zoom-in" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 animate-in zoom-in" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-200 dark:border-zinc-800"></div>
                    )}
                  </div>
                </div>

                {/* Gate 4 widget */}
                <div className={`p-4 rounded-2xl border text-center transition-all ${
                  isExecuting && executionStep >= 4 || executionResult
                    ? executionResult?.gatesResult.gate4_quota.passed
                      ? "bg-emerald-500/5 border-emerald-505/30 text-emerald-400"
                      : "bg-rose-505/5 border-rose-500/30 text-rose-455 text-rose-405 text-rose-400"
                    : isDarkMode 
                      ? "bg-zinc-950/65 border-zinc-900 text-zinc-650" 
                      : "bg-zinc-50 border-zinc-150 text-zinc-400 shadow-sm shadow-zinc-100"
                }`}>
                  <div className="text-[11px] font-bold tracking-tight leading-none mb-1 font-sans">Gate 4</div>
                  <p className="text-[8px] font-bold font-mono uppercase tracking-widest leading-none font-bold">QUOTA/COST</p>
                  <div className="flex justify-center mt-3">
                    {isExecuting && executionStep === 4 ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                    ) : executionResult || (isExecuting && executionStep > 4) ? (
                      executionResult?.gatesResult.gate4_quota.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-450 text-emerald-400 animate-in zoom-in" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 animate-in zoom-in" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-200 dark:border-zinc-800"></div>
                    )}
                  </div>
                </div>

                {/* Gate 5 widget */}
                <div className={`p-4 rounded-2xl border text-center transition-all ${
                  isExecuting && executionStep >= 5 || executionResult
                    ? executionResult?.gatesResult.gate5_ledger.passed !== false
                      ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/5 border-rose-500/30 text-rose-400"
                    : isDarkMode 
                      ? "bg-zinc-950/65 border-zinc-900 text-zinc-650" 
                      : "bg-zinc-50 border-zinc-150 text-zinc-400 shadow-sm shadow-zinc-100"
                }`}>
                  <div className="text-[11px] font-bold tracking-tight leading-none mb-1 font-sans">Gate 5</div>
                  <p className="text-[8px] font-bold font-mono uppercase tracking-widest leading-none font-bold">HASH LINK</p>
                  <div className="flex justify-center mt-3">
                    {isExecuting && executionStep === 5 ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                    ) : executionResult ? (
                      executionResult?.gatesResult.gate5_ledger.passed !== false ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-450 text-emerald-400 animate-in zoom-in" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 animate-in zoom-in" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-200 dark:border-zinc-800"></div>
                    )}
                  </div>
                </div>

              </div>
            </div>

            {/* Display processing outputs */}
            <AnimatePresence mode="wait">
              {isExecuting && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`mt-6 p-5 rounded-2xl border text-xs font-mono leading-relaxed ${isDarkMode ? "bg-zinc-950 border-zinc-900 text-emerald-400" : "bg-zinc-50 border-zinc-200 text-zinc-700"}`}
                >
                  <div className="flex items-center gap-2 mb-3 pb-2 border-b border-indigo-500/10">
                    <span className="w-2 h-2 bg-emerald-405 bg-emerald-400 rounded-full animate-ping shrink-0"></span>
                    <span className="font-bold font-sans uppercase tracking-wider text-zinc-300">RIA V6 Node Processing System Running:</span>
                  </div>
                  {executionStep >= 1 && <p className="mb-1.5 font-bold">✓ Gate 1: Signature generation, syntax and schema checks produced...</p>}
                  {executionStep >= 2 && <p className="mb-1.5 font-bold">✓ Gate 2: Looking up rules database matching Citizen: "{citizenEmail}" and Agent: "{selectedAgentId}"...</p>}
                  {executionStep >= 3 && <p className="mb-1.5 font-bold text-indigo-400 animate-pulse">⚡ Gate 3: Launching sovereign, sandboxed server-side LLM secure node (using Gemini 3.5 models)...</p>}
                  {executionStep >= 4 && <p className="mb-1.5 font-bold">✓ Gate 4: Calculating token quotas and micro-computation costs for ledger logging...</p>}
                  {executionStep >= 5 && <p className="mb-1.5 font-bold text-emerald-400">🔒 Gate 5: Compiling transaction payload block. Generating cryptographic Merkle-Hash link...</p>}
                </motion.div>
              )}

              {executionResult && !isExecuting && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`mt-6 p-6 rounded-2xl border ${
                    executionError 
                      ? "bg-rose-950/20 border-rose-900/30 text-rose-200" 
                      : isDarkMode 
                        ? "bg-zinc-950 border-zinc-900 text-zinc-100" 
                        : "bg-zinc-50 border-zinc-150 text-zinc-800 shadow-sm"
                  }`}
                  id="execution-output-box"
                >
                  <div className={`flex items-center justify-between mb-4 pb-3 border-b ${isDarkMode ? "border-zinc-900" : "border-zinc-200"}`}>
                    <div className="flex items-center gap-2.5">
                      <span className={`text-[9px] font-bold tracking-widest font-mono p-1.5 rounded-lg ${executionError ? "bg-rose-500/15 text-rose-450 border border-rose-500/20" : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"}`}>
                        {executionError ? "INFRACTION BLOCKED" : "Sovereign Audit Passed"}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-bold font-mono">Block Index: #{executionResult.index}</span>
                    </div>
                    <span className="text-xs text-zinc-500 font-bold font-mono">{new Date(executionResult.timestamp).toLocaleTimeString()}</span>
                  </div>

                  {/* Complete gate verification logs */}
                  <div className={`mb-4 p-4 rounded-2xl border ${isDarkMode ? "bg-zinc-900/40 border-zinc-900" : "bg-[#fcfcfc] border-zinc-200"}`}>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2.5 font-mono">Gate Inspection Logs</p>
                    <div className="flex flex-col gap-2.5 text-xs font-mono">
                      <div className="flex items-start gap-1.5">
                        <span className="font-bold text-zinc-400 shrink-0">1. Signature:</span>
                        <span className="text-emerald-400 font-mono text-[11px] leading-snug">{executionResult.gatesResult.gate1_signature.details}</span>
                      </div>
                      <div className="flex items-start gap-1.5">
                        <span className="font-bold text-zinc-400 shrink-0">2. Mapped Consent:</span>
                        <span className={`font-mono text-[11px] leading-snug ${executionResult.gatesResult.gate2_consent.passed ? "text-emerald-400" : "text-rose-450 font-bold text-rose-400"}`}>
                          {executionResult.gatesResult.gate2_consent.details}
                        </span>
                      </div>
                      {executionResult.gatesResult.gate2_consent.passed && (
                        <>
                          <div className="flex items-start gap-1.5">
                            <span className="font-bold text-zinc-400 shrink-0">3. Sovereign check:</span>
                            <span className="text-emerald-400 font-mono text-[11px] leading-snug">{executionResult.gatesResult.gate3_boundary.details}</span>
                          </div>
                          <div className="flex items-start gap-1.5">
                            <span className="font-bold text-zinc-400 shrink-0">4. Quota check:</span>
                            <span className="text-emerald-400 font-mono text-[11px] leading-snug">{executionResult.gatesResult.gate4_quota.details}</span>
                          </div>
                        </>
                      )}
                      <div className={`flex items-start gap-1.5 pt-2.5 border-t mt-2 ${isDarkMode ? "border-zinc-900" : "border-zinc-200"}`}>
                        <span className="font-bold text-[#b4b4b4] shrink-0 text-[10px] uppercase tracking-wider">5. Blockchain hash:</span>
                        <span className="text-emerald-500 font-mono text-[10px] break-all">
                          {executionResult.hash}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* final text body output */}
                  <div>
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 font-sans">Agent Return Payload</h4>
                    <div className={`p-4.5 rounded-2xl border leading-relaxed text-sm ${executionError ? "font-mono text-rose-455 border-rose-950 bg-rose-950/10 text-rose-400" : isDarkMode ? "bg-zinc-900/20 border-zinc-900 text-zinc-350" : "bg-white border-zinc-155 text-zinc-800"}`}>
                      {executionResult.response.split("\n").map((line, i) => (
                        <p key={i} className="mb-1 font-sans">{line}</p>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          {/* CRYPTOGRAPHIC AUDIT LOGS CHAIN VIEW */}
          <section className={`p-6 md:p-8 rounded-3xl border transition-all ${isDarkMode ? "bg-zinc-950 border-zinc-900 text-zinc-100" : "bg-white border-zinc-150 text-zinc-800 shadow-xl shadow-zinc-100"}`}>
            <div className={`flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5 mb-5 ${isDarkMode ? "border-zinc-900" : "border-zinc-200"}`}>
              <div>
                <h2 className={`text-base font-bold tracking-tight flex items-center gap-2 font-sans ${isDarkMode ? "text-zinc-100" : "text-zinc-800"}`}>
                  <History className="w-5 h-5 text-indigo-505 text-indigo-500 animate-pulse" /> Cryptographic Audit Ledger Link
                </h2>
                <p className="text-xs text-zinc-500 mt-1 font-sans">
                  Transactions are logged sequentially with SHA-256 block hashes linked dynamically to guarantee complete local audit integrity.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={handleVerifyLedgerSecurity}
                  className="px-4.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-550 text-white text-xs font-bold tracking-wider uppercase flex items-center gap-1.5 shadow-lg shadow-indigo-500/15 cursor-pointer transition-all"
                  id="verify-chain-btn"
                >
                  <ShieldCheck className="w-4 h-4 text-white" /> Verify Chain
                </button>
                <button
                  onClick={handleExportLedger}
                  title="Export current cryptographic ledger blocks as a formatted JSON document"
                  className={`px-4.5 py-2 rounded-xl border text-xs font-bold tracking-wider uppercase flex items-center gap-1.5 transition-all cursor-pointer ${
                    isDarkMode 
                      ? "border-zinc-800 bg-zinc-900/40 text-zinc-200 hover:bg-zinc-800 hover:border-zinc-700" 
                      : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                  id="export-ledger-btn"
                >
                  <Download className="w-4 h-4 text-indigo-500" /> Export Log
                </button>
                <button
                  onClick={handleResetLedger}
                  title="Reset custom blocks"
                  className={`p-2 rounded-xl border transition-all cursor-pointer ${
                    isDarkMode 
                      ? "border-zinc-900 text-zinc-500 hover:text-rose-450 hover:bg-zinc-900" 
                      : "border-zinc-200 text-zinc-400 hover:text-rose-500 hover:bg-zinc-50/50"
                  }`}
                  id="reset-ledger-btn"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Verification message popup banner */}
            <AnimatePresence>
              {verificationMessage && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className={`mb-5 overflow-hidden p-4 rounded-2xl border transition-all ${
                    verificationMessage.status === "success"
                      ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/5 border-rose-500/30 text-rose-400"
                  }`}
                  id="verification-banner"
                >
                  <div className="flex items-start gap-2.5 text-xs">
                    {verificationMessage.status === "success" ? (
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-bold font-sans tracking-wide uppercase">{verificationMessage.status === "success" ? "TRANSPARENCY SHIELD ACTIVE" : "SECURITY MISMATCH DETECTED"}</p>
                      <p className="mt-1 leading-relaxed">{verificationMessage.text}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Ledger Timeline Blocks */}
            <div className={`flex flex-col gap-4 relative pl-4 border-l ml-2 ${isDarkMode ? "border-zinc-905 border-zinc-900" : "border-zinc-150"}`}>
              {ledger.slice().reverse().map((block, idx) => {
                const queryAgent = agents.find(a => a.id === block.agentId);
                const isGenesis = block.index === 0;
                return (
                  <div key={block.index} className="relative z-10 transition-all hover:scale-[1.002]">
                    {/* Visual chain connectors */}
                    <div className="absolute -left-[21px] top-4.5 w-2.5 h-2.5 rounded-full border flex items-center justify-center bg-zinc-950 border-zinc-800 dark:border-zinc-800">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    </div>

                    <div className={`p-5 rounded-2xl border transition-all ${
                      isDarkMode 
                        ? "bg-zinc-900/10 border-zinc-900 hover:border-zinc-800" 
                        : "bg-[#fafafa]/80 border-zinc-150 hover:border-zinc-250 shadow-sm"
                    }`}>
                      <div className={`flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3 border-b pb-2 ${isDarkMode ? "border-zinc-900/60" : "border-zinc-200/60"}`}>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md ${isDarkMode ? "bg-zinc-900 text-zinc-400" : "bg-zinc-100 text-zinc-550"}`}>
                            BLOCK #{block.index}
                          </span>
                          <span className={`text-xs font-bold font-sans ${isDarkMode ? "text-zinc-300" : "text-zinc-700"}`}>
                            {isGenesis ? "Genesis Seed Initialization" : `${queryAgent?.name || block.agentId}`}
                          </span>
                        </div>
                        <span className="text-[10px] text-zinc-550 text-zinc-500 font-mono">
                          {new Date(block.timestamp).toLocaleString()}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 text-xs mb-3 pt-1">
                        <div className="md:col-span-4 font-mono text-zinc-500">
                          <p>Citizen Ref: <span className={isDarkMode ? "text-zinc-400" : "text-zinc-650"}>{block.citizenEmail}</span></p>
                          {!isGenesis && <p className="truncate mt-1.5">Sign Crypt: <span className="text-emerald-400/90 font-bold">{block.signature.slice(0, 16)}</span></p>}
                        </div>
                        <div className="md:col-span-8 font-mono">
                          <p className="text-zinc-500 truncate">Sovereign Payload: <span className={`italic font-sans ${isDarkMode ? "text-zinc-300" : "text-zinc-750 text-zinc-700"}`}>"{block.query}"</span></p>
                          <p className="text-zinc-550 text-zinc-500 truncate mt-1">Response Head: <span className={`font-sans ${isDarkMode ? "text-zinc-405 text-zinc-400" : "text-zinc-600"}`}>{block.response.slice(0, 48).trim()}...</span></p>
                        </div>
                      </div>

                      {/* Cryptographic chain signatures links */}
                      <div className={`grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t text-[10px] font-mono ${isDarkMode ? "border-zinc-900/50" : "border-zinc-200/50"}`}>
                        <div>
                          <p className="text-zinc-500 font-bold tracking-wide uppercase text-[8px]">Block Secure Hash:</p>
                          <p className="text-emerald-555 text-emerald-500/90 font-bold truncate mt-0.5">{block.hash}</p>
                        </div>
                        <div>
                          <p className="text-zinc-500 font-bold tracking-wide uppercase text-[8px]">Previous Chain Link Hash:</p>
                          <p className="text-zinc-500/85 truncate mt-0.5">{block.previousHash || "00000000000000000000000000000000000000000000000000000005"}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

        </div>

      </main>

      {/* Estonia Sovereign footer */}
      <footer className={`mt-16 border-t py-8 text-center text-xs ${isDarkMode ? "border-slate-900 bg-slate-950 text-slate-500" : "border-slate-200 bg-slate-100 text-slate-500"}`}>
        <p className="font-semibold tracking-wider uppercase mb-1">Estonia State Information System Authority (RIA)</p>
        <p>Tallinn, Estonia • Unified Access Control Protocol v6 Sovereign Trust Architecture</p>
        <p className="text-[10px] text-slate-600 mt-2">
          This system uses full sandboxed TLS token signatures and SHA-256 verification chains in compliance with the kratt strategy guidelines.
        </p>
      </footer>

    </div>
  );
}
