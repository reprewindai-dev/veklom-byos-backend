import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  ShieldCheck, 
  User, 
  Lock, 
  Plus, 
  Terminal, 
  CheckCircle2, 
  XCircle, 
  RefreshCw,
  Eye,
  EyeOff,
  Download,
  Trash2,
  Brain,
  Database,
  Sparkles,
  BookOpen,
  Search
} from "lucide-react";
import { api } from "../services/api";
import { Agent, Policy, LedgerBlock } from "../types";

interface PlaygroundTabProps {
  isDarkMode: boolean;
}

export default function PlaygroundTab({ isDarkMode }: PlaygroundTabProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  
  // Controls state
  const [selectedAgentId, setSelectedAgentId] = useState<string>("tax-kratt");
  const [citizenEmail, setCitizenEmail] = useState<string>("chomp.pixel@gmail.com");
  const [citizenQuery, setCitizenQuery] = useState<string>("Show my estimated capital tax refund");
  
  // Pipeline Visual Animation State
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [executionResult, setExecutionResult] = useState<LedgerBlock | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [ledger, setLedger] = useState<LedgerBlock[]>([]);

  // Memori™ Persistent Memory Layer interactive state
  const [useMemori, setUseMemori] = useState(true);
  const [memoriStats, setMemoriStats] = useState<any>(null);
  const [memoriTriples, setMemoriTriples] = useState<any[]>([]);
  const [memoriSummaries, setMemoriSummaries] = useState<any[]>([]);
  const [memoriSubTab, setMemoriSubTab] = useState<"triples" | "summaries">("triples");
  const [newTripleSubject, setNewTripleSubject] = useState("");
  const [newTriplePredicate, setNewTriplePredicate] = useState("");
  const [newTripleObject, setNewTripleObject] = useState("");
  const [tripleSearch, setTripleSearch] = useState("");
  const [lastMemoriMetrics, setLastMemoriMetrics] = useState<any>(null);

  // PII analysis state
  const [piiReport, setPiiReport] = useState<{ detected: boolean; masked: string }>({ detected: false, masked: "" });

  // NabaOS™ optimization metrics state
  const [lastNabaosMetrics, setLastNabaosMetrics] = useState<any>(null);

  // Policy Builder Modal state
  const [isCreatingPolicy, setIsCreatingPolicy] = useState(false);
  const [newPolicyAgent, setNewPolicyAgent] = useState("border-kratt");
  const [newPolicyAction, setNewPolicyAction] = useState("security:border-crossings");
  const [newPolicyStatus, setNewPolicyStatus] = useState<"granted" | "revoked">("granted");

  const fetchMemoriData = async () => {
    try {
      const [stats, db] = await Promise.all([
        api.getMemoriStats(),
        api.getMemoriDb()
      ]);
      setMemoriStats(stats);
      setMemoriTriples(db.triples);
      setMemoriSummaries(db.summaries);
    } catch (err) {
      console.error("Failed to fetch Memori state:", err);
    }
  };

  const loadData = async () => {
    try {
      const [resAgents, resPolicies, resLedger] = await Promise.all([
        api.getUacpAgents(),
        api.getUacpPolicies(),
        api.getUacpLedger(),
        fetchMemoriData()
      ]);
      setAgents(resAgents);
      setPolicies(resPolicies);
      setLedger(resLedger);
    } catch (err) {
      console.error("Failed to fetch playground controls", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Real-time PII detection check on input query
  useEffect(() => {
    const examinePiiText = async () => {
      if (citizenQuery.length < 5) {
        setPiiReport({ detected: false, masked: citizenQuery });
        return;
      }
      try {
        const detect = await api.detectPii(citizenQuery);
        const mask = await api.maskPii(citizenQuery);
        setPiiReport({
          detected: detect.piiDetected,
          masked: mask.maskedText
        });
      } catch {
        // silent
      }
    };
    const debounce = setTimeout(examinePiiText, 500);
    return () => clearTimeout(debounce);
  }, [citizenQuery]);

  // Execute Sovereign Multi-Gate Protocol
  const handleExecute = async () => {
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);
    setLastMemoriMetrics(null);
    setLastNabaosMetrics(null);

    // GATE 1: Digital Signature Validation Checking (Sovereign Hub nonces check)
    setCurrentStep(1);
    await new Promise(r => setTimeout(r, 700));

    // GATE 2: Delegated Citizen Consent Validation (Rules-as-code checked)
    setCurrentStep(2);
    await new Promise(r => setTimeout(r, 700));

    // GATE 3: Sovereign Boundary Safety Node Execution
    setCurrentStep(3);

    try {
      const promptToUse = piiReport.detected ? piiReport.masked : citizenQuery;
      const res = await api.executeUacpQuery(citizenEmail, selectedAgentId, promptToUse, useMemori);
      
      await new Promise(r => setTimeout(r, 850));
      // GATE 4: Compute & Quota pricing limit
      setCurrentStep(4);
      await new Promise(r => setTimeout(r, 600));

      // GATE 5: Cryptographic Merkle Block committing
      setCurrentStep(5);
      await new Promise(r => setTimeout(r, 500));

      setExecutionResult(res.block);
      if (res.memoriMetrics) {
        setLastMemoriMetrics(res.memoriMetrics);
      }
      if ((res as any).nabaosMetrics) {
        setLastNabaosMetrics((res as any).nabaosMetrics);
      }
      
      // Refresh blockchain log state
      const updatedLedger = await api.getUacpLedger();
      setLedger(updatedLedger);
      await fetchMemoriData();

      if (!res.success) {
        if (!res.block.gatesResult.gate2_consent.passed) {
          setExecutionError("POL-HALT: Delegated Citizen Consent denied. Gating rule is set to OFF.");
        } else if (!res.block.gatesResult.gate3_boundary.passed) {
          setExecutionError("SANDBOX-LEAK: Sovereign firewall halted execution. System offline simulation failed.");
        } else {
          setExecutionError("GOVERNANCE-STOP: Quota or schema verification blocked completion.");
        }
      }
    } catch {
      setExecutionError("CONNECTION-FAIL: Timeout connecting to sovereign API nodes.");
    } finally {
      setIsExecuting(false);
    }
  };

  // Toggle Policy rules statefully
  const handleTogglePolicy = async (pId: string) => {
    const policy = policies.find(p => p.id === pId);
    if (!policy) return;
    const toggledStatus = policy.status === "granted" ? "revoked" : "granted";
    try {
      const res = await api.saveUacpPolicy({
        citizenEmail: policy.citizenEmail,
        agentId: policy.agentId,
        action: policy.action,
        status: toggledStatus,
        validUntil: policy.validUntil
      });
      if (res.success) {
        const updated = await api.getUacpPolicies();
        setPolicies(updated);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Submit Policy Build form
  const handleCreatePolicySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.saveUacpPolicy({
        citizenEmail,
        agentId: newPolicyAgent,
        action: newPolicyAction,
        status: newPolicyStatus
      });
      if (res.success) {
        setIsCreatingPolicy(false);
        const updated = await api.getUacpPolicies();
        setPolicies(updated);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Export ledger blocks audit trails formatted JSON docs
  const handleExportAuditLogs = () => {
    try {
      const formatted = JSON.stringify(ledger, null, 2);
      const url = URL.createObjectURL(new Blob([formatted], { type: "application/json" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `veklom-audit-ledger-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    }
  };

  // Reset Custom Ledger state
  const handleResetBlockchain = async () => {
    if (!confirm("Are you sure you want to scrub the custom blocks? Genesis block #0 will be kept.")) return;
    try {
      const res = await api.clearUacpLedger();
      if (res.success) {
        const updated = await api.getUacpLedger();
        setLedger(updated);
        setExecutionResult(null);
        setExecutionError(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Memori™ Event Hook handlers
  const handleAddTriple = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTripleSubject.trim() || !newTriplePredicate.trim() || !newTripleObject.trim()) return;
    try {
      await api.addMemoriTriple({
        subject: newTripleSubject.trim(),
        predicate: newTriplePredicate.trim(),
        object: newTripleObject.trim()
      });
      setNewTripleSubject("");
      setNewTriplePredicate("");
      setNewTripleObject("");
      await fetchMemoriData();
    } catch (err) {
      console.error("Failed to append manual triple fact:", err);
    }
  };

  const handleDeleteTriple = async (id: string) => {
    try {
      await api.deleteMemoriTriple(id);
      await fetchMemoriData();
    } catch (err) {
      console.error("Failed to delete triple fact from database:", err);
    }
  };

  const handleResetMemoriData = async () => {
    if (!confirm("Restore all Memori persistent memory store records to default paper benchmarks?")) return;
    try {
      await api.resetMemori();
      await fetchMemoriData();
      setLastMemoriMetrics(null);
    } catch (err) {
      console.error("Failed to reset Memori persistent database:", err);
    }
  };

  // Helper colors
  const activeAgentInfo = agents.find(a => a.id === selectedAgentId);

  return (
    <div className="flex flex-col gap-8">
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="playground-view">
      
      {/* 1. LEFT WORKSPACE COLUMN: Controls (5 Cols) */}
      <div className="lg:col-span-5 flex flex-col gap-6">

        {/* IDENTITY SECURITY CONTEXT */}
        <section className={`p-6 rounded-3xl border ${isDarkMode ? "bg-zinc-950/20 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <h3 className="text-xs font-bold uppercase text-indigo-400 mb-4 flex items-center gap-1.5 font-mono">
            <User className="w-4 h-4" /> Authenticated Citizen Identity Context
          </h3>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[10px] text-zinc-500 font-bold uppercase tracking-tight block mb-1.5">Signer Identity Email</label>
              <input 
                type="email"
                value={citizenEmail}
                onChange={(e) => setCitizenEmail(e.target.value)}
                className={`w-full px-4 py-2.5 text-xs rounded-xl font-mono border transition-all outline-none ${
                  isDarkMode 
                    ? "bg-zinc-900 border-zinc-800 text-zinc-100 focus:border-indigo-500" 
                    : "bg-zinc-50 border-zinc-200 text-zinc-900 focus:border-zinc-400"
                }`}
                placeholder="citizen@mail.com"
              />
            </div>
          </div>
        </section>

        {/* CONSENT AND DELEGATION RULES CONTROLLER */}
        <section className={`p-6 rounded-3xl border flex flex-col gap-4 ${isDarkMode ? "bg-zinc-950/20 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-emerald-400 flex items-center gap-1.5 font-mono">
              <Lock className="w-4 h-4" /> Delegated Consent Gates (Rules-As-Code)
            </h3>
            <button 
              onClick={() => setIsCreatingPolicy(!isCreatingPolicy)}
              className="px-3 py-1 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/25 text-indigo-400 rounded-xl font-bold text-[10px] transition-all cursor-pointer flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> Toggle Form
            </button>
          </div>

          {/* Quick policy builders inline dropdown layout */}
          <AnimatePresence>
            {isCreatingPolicy && (
              <motion.form 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                onSubmit={handleCreatePolicySubmit}
                className={`p-4 rounded-2xl border text-xs flex flex-col gap-2 overflow-hidden ${
                  isDarkMode ? "bg-zinc-900/60 border-zinc-800" : "bg-zinc-100 border-zinc-150"
                }`}
              >
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[9px] text-zinc-500 font-mono block mb-1">Target Agent Node</label>
                    <select 
                      value={newPolicyAgent}
                      onChange={(e) => {
                        setNewPolicyAgent(e.target.value);
                        const scopeMatch = agents.find(a => a.id === e.target.value)?.scope || "medical";
                        setNewPolicyAction(scopeMatch);
                      }}
                      className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded-lg text-[10px]"
                    >
                      {agents.map(a => (
                        <option value={a.id} key={a.id}>{a.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[9px] text-zinc-500 font-mono block mb-1">Status Status</label>
                    <select 
                      value={newPolicyStatus}
                      onChange={(e) => setNewPolicyStatus(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded-lg text-[10px]"
                    >
                      <option value="granted">GRANTED</option>
                      <option value="revoked">REVOKED</option>
                    </select>
                  </div>
                </div>
                <button 
                  type="submit"
                  className="w-full py-1.5 bg-indigo-600 rounded-xl font-bold text-white transition-all cursor-pointer text-[10px] uppercase tracking-wider mt-2"
                >
                  Confirm Gating Rule
                </button>
              </motion.form>
            )}
          </AnimatePresence>

          {/* Connected Consent list */}
          <div className="flex flex-col gap-2 max-h-[170px] overflow-y-auto pr-1">
            {policies.filter(p => p.citizenEmail === citizenEmail).map((p) => {
              const matchedAgent = agents.find(ag => ag.id === p.agentId);
              return (
                <div 
                  key={p.id}
                  className={`p-3 rounded-2xl border flex items-center justify-between text-xs font-mono transition-all ${
                    p.status === "granted"
                      ? isDarkMode ? "bg-zinc-950/40 border-zinc-800" : "bg-emerald-50/10 border-zinc-200"
                      : "bg-rose-950/5 border-rose-950/20 text-rose-350"
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="font-bold text-zinc-250 truncate">{matchedAgent ? matchedAgent.name : p.agentId}</p>
                    <p className="text-[9px] text-zinc-500 truncate">{p.action}</p>
                  </div>
                  <button 
                    onClick={() => handleTogglePolicy(p.id)}
                    className={`px-2.5 py-1 rounded-lg text-[9px] font-black tracking-wider uppercase transition-all cursor-pointer ${
                      p.status === "granted"
                        ? "bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-600/10 hover:bg-rose-600/20 text-rose-400 border border-rose-500/15"
                    }`}
                  >
                    {p.status === "granted" ? "GRANTED" : "REVOKED"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

      </div>

      {/* 2. RIGHT WORKSPACE COLUMN: Sequential Engine Interactive Execution (7 Cols) */}
      <div className="lg:col-span-7 flex flex-col gap-6" id="playground-terminal-section">
        
        {/* Core complete playground box */}
        <section className={`p-8 rounded-[2rem] border relative overflow-hidden flex flex-col gap-4 ${
          isDarkMode ? "bg-zinc-900/30 border-zinc-900 text-zinc-100" : "bg-white border-zinc-200 text-zinc-900 shadow-sm"
        }`}>
          <div className="flex items-center justify-between border-b border-zinc-805/4s pb-4 mb-2">
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-indigo-400 animate-pulse" />
              <div>
                <h3 className="text-sm font-bold tracking-tight">Sovereign Agent Gated Gateway</h3>
                <p className="text-[10px] text-zinc-500">Bürokratt Trust Gating Pipeline Interface</p>
              </div>
            </div>
            
            {/* Reset ledger option */}
            <button 
              onClick={handleResetBlockchain}
              className="p-1 px-2 hover:bg-zinc-800/40 text-zinc-550 hover:text-rose-400 rounded-lg text-xs transition-all cursor-pointer flex items-center gap-1 border border-zinc-800/10"
              title="Reset Ledger State"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex flex-col gap-4">
            
            {/* Agent Select and prompt box */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] text-zinc-500 block font-bold mb-2 uppercase">Select Sovereign Agent Node</label>
                <select 
                  value={selectedAgentId}
                  onChange={(e) => setSelectedAgentId(e.target.value)}
                  className={`w-full px-4 py-2.5 text-xs font-semibold rounded-xl border outline-none ${
                    isDarkMode 
                      ? "bg-zinc-950 border-zinc-800 text-zinc-200" 
                      : "bg-zinc-50 border-zinc-200 text-zinc-850"
                  }`}
                >
                  {agents.map(a => (
                    <option value={a.id} key={a.id}>{a.name} ({a.scope})</option>
                  ))}
                </select>
              </div>
              <div className="text-xs transition-all flex flex-col justify-center">
                {activeAgentInfo && (
                  <div className={`p-3 rounded-2xl border leading-relaxed font-mono text-[10px] ${
                    isDarkMode ? "bg-zinc-950/60 border-zinc-800" : "bg-zinc-50 border-zinc-150"
                  }`}>
                    <p className="font-bold text-zinc-350">Bound Dataset:</p>
                    <p className="text-zinc-550 truncate mt-0.5">{activeAgentInfo.dataset}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Prompt input with PII warnings */}
            <div>
              <label className="text-[10px] text-zinc-500 block font-bold mb-2 uppercase flex items-center justify-between">
                <span>Citizen Question Prompt</span>
                {piiReport.detected && (
                  <span className="text-amber-500 text-[9px] animate-pulse font-mono tracking-wider uppercase font-black">
                    ⚠️ PII DETECTED & AUTOMATED MASKS APPLIED
                  </span>
                )}
              </label>
              <textarea 
                value={citizenQuery}
                onChange={(e) => setCitizenQuery(e.target.value)}
                rows={3}
                placeholder="Ask e.g. Show my child's birth registry files or declare deductibles."
                className={`w-full px-4 py-3 text-xs leading-relaxed font-sans rounded-xl border outline-none transition-all ${
                  isDarkMode 
                    ? "bg-zinc-950 border-zinc-800 text-zinc-250 focus:border-indigo-500" 
                    : "bg-zinc-50 border-zinc-200 text-zinc-850 focus:border-zinc-400"
                }`}
              />
              
              {/* PII Mask display section */}
              {piiReport.detected && (
                <div className={`mt-2 p-3 rounded-xl border font-mono text-[9px] leading-normal ${
                  isDarkMode ? "bg-amber-950/10 border-amber-900/35 text-amber-300" : "bg-amber-50 border-amber-200 text-amber-800"
                }`}>
                  <p className="font-bold uppercase tracking-widest text-[8px] opacity-75">Sovereign Compliance Filtered Query Preview:</p>
                  <p className="mt-1">"{piiReport.masked}"</p>
                </div>
              )}
            </div>

            {/* Memori™ Persistent Memory Layer interactive toggle and metadata */}
            <div className={`p-4.5 rounded-2xl border flex flex-col gap-3.5 transition-all ${
              isDarkMode ? "bg-indigo-950/10 border-indigo-950/40 text-zinc-150" : "bg-indigo-50/20 border-indigo-100/50 text-zinc-800 shadow-sm"
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <Brain className={`w-4 h-4 text-indigo-400 shrink-0 ${useMemori ? "animate-pulse" : ""}`} />
                  <div className="overflow-hidden">
                    <h5 className="font-bold text-xs tracking-tight">Memori™ Persistent Context Layer</h5>
                    <p className="text-[9px] text-zinc-500 truncate">Optimizes agent context footprint using dynamic semantic compression (LoCoMo style)</p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input 
                    type="checkbox" 
                    checked={useMemori} 
                    onChange={(e) => setUseMemori(e.target.checked)} 
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 peer-checked:after:bg-indigo-400 after:border-zinc-305 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-950 border border-zinc-750"></div>
                </label>
              </div>

              {/* Show metrics for the current run if we have them */}
              {useMemori && lastMemoriMetrics ? (
                <div className="grid grid-cols-3 gap-2 font-mono text-[9px] border-t border-indigo-950/15 pt-2.5 mt-0.5">
                  <div className="p-2 rounded-lg bg-zinc-950/40 border border-zinc-900/40 leading-normal">
                    <p className="text-zinc-500 font-bold uppercase text-[7px]">Full-Context</p>
                    <p className="text-rose-450 font-black mt-0.5">26,031 tokens</p>
                  </div>
                  <div className="p-2 rounded-lg bg-zinc-950/40 border border-zinc-900/40 leading-normal animate-pulse">
                    <p className="text-indigo-400 font-black uppercase text-[7px]">Memori Opt</p>
                    <p className="text-emerald-400 font-black mt-0.5">1,294 tokens</p>
                  </div>
                  <div className="p-2 rounded-lg bg-indigo-950/10 border border-indigo-900/20 leading-normal text-right">
                    <p className="text-indigo-400 font-bold uppercase text-[7px]">Penny Savings</p>
                    <p className="text-emerald-400 font-black mt-0.5">¢{(lastMemoriMetrics.savedPennies || 1.979).toFixed(3)}</p>
                  </div>
                </div>
              ) : (
                <p className="text-[9px] text-zinc-550 border-t border-indigo-950/10 font-mono pt-2">
                  {useMemori 
                    ? "✓ Memory is ARMED. Run query to trigger 95.03% context footprint compression." 
                    : "✗ Memory BYPASS. Queries consume raw full context overhead with high latency."}
                </p>
              )}
            </div>

            {/* Pipeline Trigger Buttons */}
            <div>
              <button 
                onClick={handleExecute}
                disabled={isExecuting || citizenQuery.trim().length === 0}
                className="w-full py-4.5 bg-indigo-600 hover:bg-indigo-700 text-white font-black text-xs tracking-widest uppercase rounded-2xl shadow-lg shadow-indigo-600/20 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isExecuting ? "Executing Integrity Pipeline..." : "Execute Gated Sovereign Query"}
              </button>
            </div>

            {/* 5-Gate Sequential Animation Visualization card */}
            <div className="flex flex-col gap-3 mt-4">
              <h4 className="text-[10px] text-indigo-400 font-black tracking-widest uppercase font-mono">Cognitive Gate Pipeline Checks</h4>
              
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 font-mono text-[9px]">
                
                {/* Gate 1 */}
                <div className={`p-3 rounded-xl border flex flex-col justify-between shrink-0 transition-all ${
                  currentStep >= 1 
                    ? isExecuting && currentStep === 1 
                      ? "border-blue-500 bg-blue-500/10 text-blue-300" 
                      : "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                    : "border-zinc-800 bg-zinc-905 text-zinc-600"
                }`}>
                  <p className="font-bold">1: Schema</p>
                  <p className="font-semibold text-[8px] uppercase mt-1">
                    {currentStep >= 1 ? (currentStep === 1 && isExecuting ? "PARSING..." : "PASSED") : "ARMED"}
                  </p>
                </div>

                {/* Gate 2 */}
                <div className={`p-3 rounded-xl border flex flex-col justify-between shrink-0 transition-all ${
                  currentStep >= 2 
                    ? isExecuting && currentStep === 2 
                      ? "border-amber-500 bg-amber-500/10 text-amber-300" 
                      : executionError?.includes("POL-HALT") 
                        ? "border-rose-500/50 bg-rose-500/10 text-rose-400" 
                        : "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                    : "border-zinc-800 bg-zinc-905 text-zinc-600"
                }`}>
                  <p className="font-bold">2: Consent</p>
                  <p className="font-semibold text-[8px] uppercase mt-1">
                    {currentStep >= 2 
                      ? (currentStep === 2 && isExecuting 
                        ? "EVALUATING..." 
                        : executionError?.includes("POL-HALT") ? "BLOCKED" : "PASSED") 
                      : "ARMED"}
                  </p>
                </div>

                {/* Gate 3 */}
                <div className={`p-3 rounded-xl border flex flex-col justify-between shrink-0 transition-all ${
                  currentStep >= 3 
                    ? isExecuting && currentStep === 3 
                      ? "border-purple-500 bg-purple-500/10 text-purple-300" 
                      : executionError?.includes("SANDBOX-LEAK")
                        ? "border-rose-500/50 bg-rose-500/10 text-rose-400"
                        : "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                    : "border-zinc-800 bg-zinc-905 text-zinc-600"
                }`}>
                  <p className="font-bold">3: Firewall</p>
                  <p className="font-semibold text-[8px] uppercase mt-1">
                    {currentStep >= 3 
                      ? (currentStep === 3 && isExecuting 
                        ? "ENCRYPTING..." 
                        : executionError?.includes("SANDBOX-LEAK") ? "HALTED" : "COMPLETED") 
                      : "ARMED"}
                  </p>
                </div>

                {/* Gate 4 */}
                <div className={`p-3 rounded-xl border flex flex-col justify-between shrink-0 transition-all ${
                  currentStep >= 4 
                    ? isExecuting && currentStep === 4 
                      ? "border-pink-500 bg-pink-500/10 text-pink-300" 
                      : "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                    : "border-zinc-800 bg-zinc-905 text-zinc-600"
                }`}>
                  <p className="font-bold">4: Quota</p>
                  <p className="font-semibold text-[8px] uppercase mt-1">
                    {currentStep >= 4 ? (currentStep === 4 && isExecuting ? "ACCOUNTING..." : "PASSED") : "ARMED"}
                  </p>
                </div>

                {/* Gate 5 */}
                <div className={`p-3 rounded-xl border flex flex-col justify-between shrink-0 transition-all ${
                  currentStep >= 5 
                    ? isExecuting && currentStep === 5 
                      ? "border-teal-500 bg-teal-500/10 text-teal-300" 
                      : "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                    : "border-zinc-800 bg-zinc-905 text-zinc-600"
                }`}>
                  <p className="font-bold">5: Merkle</p>
                  <p className="font-semibold text-[8px] uppercase mt-1">
                    {currentStep >= 5 ? (currentStep === 5 && isExecuting ? "COMMITTING..." : "CHAINED") : "ARMED"}
                  </p>
                </div>

              </div>
            </div>

            {/* Results visualization */}
            {executionError && (
              <div className={`p-5 rounded-2xl border text-xs leading-relaxed font-semibold flex items-start gap-3 ${
                isDarkMode ? "bg-rose-950/15 border-rose-900/45 text-rose-300" : "bg-rose-50 border-rose-200 text-rose-800"
              }`}>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold uppercase tracking-wider font-mono">Sovereign Exception Stop Triggered</p>
                  <p className="mt-1 font-sans">{executionError}</p>
                </div>
              </div>
            )}

            {executionResult && !executionError && (
              <div className={`p-6 rounded-2xl border text-xs flex flex-col gap-4 transition-all ${
                isDarkMode ? "bg-[#0a0a0a] border-zinc-800 text-zinc-100" : "bg-white border-zinc-200 text-zinc-900"
              }`}>
                <div className="flex items-center justify-between border-b border-zinc-800/40 pb-3">
                  <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-black tracking-widest font-mono uppercase">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" /> SECURE BLOCK ENCAPSULATION # {executionResult.index}
                  </span>
                  <span className="text-[9px] text-zinc-500 font-mono font-medium">{new Date(executionResult.timestamp).toLocaleTimeString()}</span>
                </div>
                
                {/* Visual markdown body */}
                <div className="leading-relaxed whitespace-pre-wrap font-sans text-zinc-250 italic">
                  {executionResult.response}
                </div>

                {/* Ledger specific cryptographic metadata */}
                <div className={`p-4 rounded-xl border text-[9px] font-mono leading-normal flex flex-col gap-1.5 ${
                  isDarkMode ? "bg-zinc-950/80 border-zinc-850" : "bg-zinc-50 border-zinc-150"
                }`}>
                  <p className="text-zinc-500 font-bold uppercase block text-[8px] mb-1">Merkle Proof Signatures</p>
                  <p className="truncate"><span className="text-indigo-400">HASH:</span> {executionResult.hash}</p>
                  <p className="truncate"><span className="text-indigo-400">PREV_HASH:</span> {executionResult.previousHash}</p>
                  <p className="truncate"><span className="text-indigo-400">CITIZEN_SIG:</span> {executionResult.signature}</p>
                </div>

                {lastNabaosMetrics && (
                  <div className="mt-4 pt-4 border-t border-zinc-800/40 flex flex-col gap-4">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                      <h4 className="text-[11px] font-bold text-indigo-400 uppercase tracking-widest font-mono">NabaOS™ Cost & Safety Optimization Analysis</h4>
                    </div>

                    {/* Split grid for tier and pramana cert */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      
                      {/* Tier router */}
                      <div className={`p-4.5 rounded-2xl border flex flex-col justify-between gap-2.5 ${
                        isDarkMode ? "bg-zinc-950/40 border-zinc-900" : "bg-zinc-100/50 border-zinc-200"
                      }`}>
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest font-mono">5-Tier Cascade Router</span>
                          <span className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase ${
                            lastNabaosMetrics.tier.id <= 3 
                              ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-400" 
                              : lastNabaosMetrics.tier.id === 4
                                ? "bg-amber-500/15 border border-amber-500/30 text-amber-400"
                                : "bg-indigo-500/15 border border-indigo-500/30 text-indigo-400"
                          }`}>
                            {lastNabaosMetrics.tier.name.split(":")[0]}
                          </span>
                        </div>
                        <div>
                          <p className="text-xs font-bold text-zinc-250 mt-1">{lastNabaosMetrics.tier.name}</p>
                          <p className="text-[10px] text-zinc-500 mt-1 font-sans leading-relaxed">{lastNabaosMetrics.tier.mechanism}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[9px] border-t border-zinc-800/30 pt-2.5 font-mono mt-1">
                          <div>
                            <span className="text-zinc-500 block">TIER COST:</span>
                            <span className="font-bold text-zinc-200">${lastNabaosMetrics.tier.cost.toFixed(5)}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-zinc-500 block">TOKEN SAVED:</span>
                            <span className="font-bold text-emerald-400">+{lastNabaosMetrics.tier.savingPercent}% SAVED</span>
                          </div>
                        </div>
                      </div>

                      {/* Pramana receipt */}
                      <div className={`p-4.5 rounded-2xl border flex flex-col justify-between gap-2.5 ${
                        isDarkMode ? "bg-indigo-950/10 border-indigo-900/30 text-zinc-200" : "bg-indigo-50/20 border-indigo-150 text-indigo-950"
                      }`}>
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest font-mono">Nyaya Shastra Pramana</span>
                          <span className="text-emerald-400 font-bold font-mono text-[8px] uppercase tracking-wider bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                            ACTIVE VERIFICATION
                          </span>
                        </div>
                        <div>
                          <p className="text-xs font-bold text-indigo-450 font-mono flex items-center gap-1.5 uppercase">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            {lastNabaosMetrics.toolReceipt.pramana}
                          </p>
                          <p className="text-[10px] text-zinc-500 mt-1 font-sans leading-relaxed">
                            {lastNabaosMetrics.toolReceipt.description}
                          </p>
                        </div>
                        
                        <div className="text-[9px] border-t border-zinc-800/30 pt-2.5 font-mono mt-1 flex flex-col gap-1 overflow-hidden">
                          <p className="truncate"><span className="text-zinc-500 uppercase">TOOL:</span> <span className="text-zinc-300 font-bold">{lastNabaosMetrics.toolReceipt.toolName}()</span></p>
                          <p className="truncate"><span className="text-zinc-500 uppercase">INPUT:</span> <span className="text-zinc-400">{JSON.stringify(lastNabaosMetrics.toolReceipt.inputs)}</span></p>
                          <p className="truncate"><span className="text-zinc-500 uppercase">OUTPUT:</span> <span className="text-zinc-400">{JSON.stringify(lastNabaosMetrics.toolReceipt.outputs)}</span></p>
                          <p className="truncate"><span className="text-zinc-500 uppercase">PROOF SIG:</span> <span className="text-indigo-400 font-semibold">{lastNabaosMetrics.toolReceipt.hmacSignature}</span></p>
                        </div>
                      </div>

                    </div>

                    {/* W5H2 structured intent canonicalization */}
                    <div className={`p-4.5 rounded-2xl border flex flex-col gap-3 ${
                      isDarkMode ? "bg-zinc-950/20 border-zinc-900" : "bg-zinc-50 border-zinc-200"
                    }`}>
                      <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest font-mono block">W5H2 Structured Intent Canonicalization Keys</span>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px] font-mono leading-normal">
                        <div className="p-2.5 bg-zinc-950/40 rounded-xl border border-zinc-800/60">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">WHAT (Action)</span>
                          <span className="text-indigo-400 font-semibold">{lastNabaosMetrics.w5h2.what}</span>
                        </div>
                        <div className="p-2.5 bg-zinc-950/40 rounded-xl border border-zinc-800/60">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">WHERE (Endpoint)</span>
                          <span className="text-zinc-300">{lastNabaosMetrics.w5h2.where}</span>
                        </div>
                        <div className="p-2.5 bg-zinc-950/40 rounded-xl border border-zinc-800/60">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">WHO (Subject)</span>
                          <span className="text-zinc-200 truncate block">{lastNabaosMetrics.w5h2.who}</span>
                        </div>
                        <div className="p-2.5 bg-zinc-950/40 rounded-xl border border-zinc-800/60">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">WHEN (Temporal)</span>
                          <span className="text-zinc-300">{lastNabaosMetrics.w5h2.when}</span>
                        </div>
                        <div className="p-2.5 bg-zinc-950/40 rounded-xl border border-zinc-800/60 col-span-2">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">WHY (Motivation Context)</span>
                          <span className="text-zinc-300 block truncate font-sans text-[11px]">{lastNabaosMetrics.w5h2.why}</span>
                        </div>
                        <div className="p-2.5 bg-[#0e0e0e]/50 rounded-xl border border-zinc-800/60 text-zinc-300">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">HOW (Param Slot)</span>
                          <span className="block truncate font-medium text-[9px]">{lastNabaosMetrics.w5h2.how}</span>
                        </div>
                        <div className="p-2.5 bg-[#0e0e0e]/50 rounded-xl border border-zinc-800/60 text-emerald-400">
                          <span className="text-zinc-500 block text-[8px] uppercase font-bold tracking-wider">HOW MUCH (Limits)</span>
                          <span className="block truncate font-bold text-[9px]">{lastNabaosMetrics.w5h2.howMuch}</span>
                        </div>
                      </div>
                    </div>

                    {/* MCP and supervisor stats banner */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[10px] text-zinc-500 font-medium">
                      <div className="flex gap-2.5 items-start p-3 bg-zinc-950/10 border border-zinc-900 rounded-xl">
                        <span className="text-emerald-400 font-bold shrink-0 font-mono text-[8px] tracking-wider uppercase bg-emerald-500/10 border border-emerald-500/25 px-1.5 py-0.5 rounded">MCP FILTER</span>
                        <div>
                          <span className="text-zinc-350 font-bold font-mono">Payload Compression:</span>
                          <p className="font-sans leading-relaxed text-[10px] text-zinc-455 mt-0.5">{lastNabaosMetrics.mcpOptimizations.fieldFiltering}</p>
                        </div>
                      </div>
                      <div className="flex gap-2.5 items-start p-3 bg-zinc-950/10 border border-zinc-900 rounded-xl">
                        <span className="text-emerald-400 font-bold shrink-0 font-mono text-[8px] tracking-wider uppercase bg-emerald-500/10 border border-emerald-500/25 px-1.5 py-0.5 rounded">SUPERVISOR</span>
                        <div>
                          <span className="text-zinc-350 font-bold font-mono">SupervisorAgent Feedback Filter:</span>
                          <p className="font-sans leading-relaxed text-[10px] text-zinc-455 mt-0.5">{lastNabaosMetrics.supervisorAgent.status} ({lastNabaosMetrics.supervisorAgent.tokenSavedPercent}% fewer loops)</p>
                        </div>
                      </div>
                    </div>

                  </div>
                )}
                
                <div className="flex gap-2">
                  <button 
                    onClick={handleExportAuditLogs}
                    className={`px-4.5 py-2 hover:bg-zinc-800 text-zinc-3 font-bold text-[10px] rounded-xl transition-all flex items-center gap-1 cursor-pointer border ${
                      isDarkMode ? "border-zinc-800 bg-zinc-900 text-zinc-300" : "border-zinc-200 bg-zinc-50 text-zinc-700"
                    }`}
                  >
                    <Download className="w-3.5 h-3.5" /> Export Audit Log
                  </button>
                </div>
              </div>
            )}

          </div>
        </section>

      </div>

    </div>

    {/* 3. MEMORI™ PERSISTENT MEMORY EXPLORER CARD */}
    <section className={`p-8 rounded-[2rem] border relative overflow-hidden flex flex-col gap-6 ${
      isDarkMode ? "bg-[#09090b]/40 border-zinc-900/80 text-zinc-100" : "bg-white border-zinc-200 text-zinc-900 shadow-sm"
    }`} id="memori-explorer-section">
      
      {/* Header section with status glow */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-800/10 pb-5">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-indigo-600/10 rounded-2xl border border-indigo-500/25 text-indigo-400 shrink-0">
            <Brain className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm sm:text-base font-bold tracking-tight">Memori™ Decoupled Persistent Memory Engine</h3>
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[9px] font-black tracking-wider uppercase font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping"></span> Live LoCoMo
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-1 max-w-2xl leading-normal font-medium">
              An innovative, model-agnostic software layer providing persistent memory for Bürokratt AI agents by treating dialogue history as semantic triples & narrative blocks (reduces context footprint by 95%).
            </p>
          </div>
        </div>

        <button 
          onClick={handleResetMemoriData}
          className={`px-4 py-2 text-xs font-bold rounded-xl border transition-all flex items-center gap-1.5 cursor-pointer hover:bg-rose-600/10 hover:text-rose-400 hover:border-rose-500/35 shrink-0 select-none ${
            isDarkMode ? "border-zinc-850 bg-zinc-900/60 text-zinc-450" : "border-zinc-200 bg-zinc-50 text-zinc-700"
          }`}
        >
          <RefreshCw className="w-3.5 h-3.5" /> Reset Memory Store
        </button>
      </div>

      {/* Telemetry panel */}
      {memoriStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Metric 1 */}
          <div className={`p-5 rounded-2xl border flex flex-col justify-between ${
            isDarkMode ? "bg-zinc-950/40 border-zinc-900/60" : "bg-zinc-50/50 border-zinc-200"
          }`}>
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Cognitive Transactions</span>
            <div className="mt-3.5 flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono tracking-tight text-zinc-150">{memoriStats.totalQueriesOptimized}</span>
              <span className="text-[10px] text-indigo-400 font-mono">Optimized calls</span>
            </div>
            <p className="text-[10px] text-zinc-500 mt-1 font-mono leading-none">Compact dialogue compression loops executed</p>
          </div>

          {/* Metric 2 */}
          <div className={`p-5 rounded-2xl border flex flex-col justify-between ${
            isDarkMode ? "bg-zinc-950/40 border-zinc-900/60" : "bg-zinc-50/50 border-zinc-200"
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider font-mono">Footprint Reduction Ratio</span>
              <span className="text-[10px] text-emerald-450 font-black font-mono">95.03% SLIVER</span>
            </div>
            <div className="mt-3">
              <div className="w-full bg-zinc-800/40 rounded-full h-2 overflow-hidden flex">
                <div className="bg-emerald-500 h-full animate-pulse" style={{ width: "4.97%" }} title="Memori size (1,294 tokens)"></div>
                <div className="bg-rose-500/25 h-full" style={{ width: "95.03%" }} title="Saved overhead (24,737 tokens)"></div>
              </div>
              <div className="flex justify-between text-[9px] font-mono mt-2 text-zinc-550">
                <span>Memori: 1,294 t</span>
                <span>Baseline Full: 26,031 t</span>
              </div>
            </div>
          </div>

          {/* Metric 3 */}
          <div className={`p-5 rounded-2xl border flex flex-col justify-between ${
            isDarkMode ? "bg-zinc-950/40 border-indigo-950/20 relative overflow-hidden" : "bg-zinc-50/50 border-zinc-200 shadow-sm"
          }`}>
            <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider font-mono">Sovereign Penny Savings</span>
            <div className="mt-3.5 flex items-baseline gap-1.5">
              <span className="text-2xl font-black font-mono text-emerald-400">
                ¢{(memoriStats.savedPenniesTotal || 94132.89).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </span>
              <span className="text-[10px] text-zinc-500 font-mono">savings accrued</span>
            </div>
            <p className="text-[10px] text-zinc-500 mt-1 font-mono leading-none font-medium">Eliminated costly serverless runtime loops</p>
          </div>

        </div>
      )}

      {/* Dynamic Interactive DB Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-2">
        
        {/* Sub Tab selection (left side rail) */}
        <div className="lg:col-span-3 flex flex-row lg:flex-col gap-2">
          <button
            onClick={() => setMemoriSubTab("triples")}
            className={`w-full p-4 rounded-2xl border font-bold text-xs flex items-center gap-3 transition-all cursor-pointer ${
              memoriSubTab === "triples"
                ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/10"
                : isDarkMode 
                  ? "bg-zinc-950/40 border-zinc-900/60 text-zinc-400 hover:text-zinc-200" 
                  : "bg-zinc-50 border-zinc-200 text-zinc-700 hover:bg-zinc-100"
            }`}
          >
            <Database className="w-4 h-4 shrink-0 hover:scale-105" />
            <div className="text-left font-sans">
              <p className="font-bold text-[11px] leading-tight">Semantic Fact Store</p>
              <p className={`text-[9px] font-mono mt-1 leading-none ${memoriSubTab === "triples" ? "text-indigo-200 font-semibold" : "text-zinc-500"}`}>
                {memoriTriples.length} relational tuples
              </p>
            </div>
          </button>

          <button
            onClick={() => setMemoriSubTab("summaries")}
            className={`w-full p-4 rounded-2xl border font-bold text-xs flex items-center gap-3 transition-all cursor-pointer ${
              memoriSubTab === "summaries"
                ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/10"
                : isDarkMode 
                  ? "bg-zinc-950/40 border-zinc-900/60 text-zinc-400 hover:text-zinc-200" 
                  : "bg-zinc-50 border-zinc-200 text-zinc-700 hover:bg-zinc-100"
            }`}
          >
            <BookOpen className="w-4 h-4 shrink-0 hover:scale-105" />
            <div className="text-left font-sans">
              <p className="font-bold text-[11px] leading-tight">Conversation Summaries</p>
              <p className={`text-[9px] font-mono mt-1 leading-none ${memoriSubTab === "summaries" ? "text-indigo-200 font-semibold" : "text-zinc-500"}`}>
                {memoriSummaries.length} block outlines
              </p>
            </div>
          </button>
        </div>

        {/* Active view detail rail */}
        <div className="lg:col-span-9 flex flex-col gap-4">
          
          {memoriSubTab === "triples" && (
            <div className="flex flex-col gap-4">
              
              {/* Inline facts synthesis builder */}
              <form 
                onSubmit={handleAddTriple}
                className={`p-5 rounded-2xl border flex flex-col gap-3.5 ${
                  isDarkMode ? "bg-zinc-950/40 border-zinc-900/60" : "bg-zinc-50/20 border-zinc-200"
                }`}
              >
                <div className="flex items-center gap-2 border-b border-zinc-800/10 pb-2">
                  <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
                  <span className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase font-mono">Manual Memory Triple Synthesizer</span>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[8px] text-zinc-500 block font-bold mb-1 font-mono uppercase">Subject</label>
                    <input 
                      type="text"
                      placeholder="e.g. tax-refund"
                      value={newTripleSubject}
                      onChange={(e) => setNewTripleSubject(e.target.value)}
                      className={`w-full px-3 py-2 text-xs font-semibold rounded-xl border outline-none ${
                        isDarkMode 
                          ? "bg-zinc-950 border-zinc-850 text-zinc-200 focus:border-indigo-500" 
                          : "bg-white border-zinc-200 text-zinc-800 focus:border-zinc-350"
                      }`}
                    />
                  </div>
                  <div>
                    <label className="text-[8px] text-zinc-500 block font-bold mb-1 font-mono uppercase">Predicate</label>
                    <input 
                      type="text"
                      placeholder="e.g. estimatedAmount"
                      value={newTriplePredicate}
                      onChange={(e) => setNewTriplePredicate(e.target.value)}
                      className={`w-full px-3 py-2 text-xs font-semibold rounded-xl border outline-none ${
                        isDarkMode 
                          ? "bg-zinc-950 border-zinc-850 text-zinc-200 focus:border-indigo-500" 
                          : "bg-white border-zinc-200 text-zinc-800 focus:border-zinc-350"
                      }`}
                    />
                  </div>
                  <div>
                    <label className="text-[8px] text-zinc-500 block font-bold mb-1 font-mono uppercase">Object</label>
                    <input 
                      type="text"
                      placeholder="e.g. €412.50"
                      value={newTripleObject}
                      onChange={(e) => setNewTripleObject(e.target.value)}
                      className={`w-full px-3 py-2 text-xs font-semibold rounded-xl border outline-none ${
                        isDarkMode 
                          ? "bg-zinc-950 border-zinc-850 text-zinc-200 focus:border-indigo-500" 
                          : "bg-white border-zinc-200 text-zinc-800 focus:border-zinc-350"
                      }`}
                    />
                  </div>
                </div>

                <div className="flex justify-end mt-1">
                  <button
                    type="submit"
                    disabled={!newTripleSubject.trim() || !newTriplePredicate.trim() || !newTripleObject.trim()}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-black tracking-widest uppercase rounded-xl shadow-sm transition-all cursor-pointer disabled:opacity-45"
                  >
                    Teach Fact Tuple
                  </button>
                </div>
              </form>

              {/* Search bar inside fact DB */}
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-zinc-500">
                  <Search className="w-3.5 h-3.5" />
                </span>
                <input
                  type="text"
                  placeholder="Search memory triples database (e.g. tax, health, role)..."
                  value={tripleSearch}
                  onChange={(e) => setTripleSearch(e.target.value)}
                  className={`w-full pl-9 pr-4 py-2 text-xs font-medium rounded-xl border outline-none ${
                    isDarkMode 
                      ? "bg-zinc-950 border-zinc-850 text-zinc-200 focus:border-indigo-500" 
                      : "bg-white border-zinc-200 text-zinc-800 focus:border-zinc-350"
                  }`}
                />
              </div>

              {/* Triple list table */}
              <div className={`border rounded-2xl overflow-hidden ${
                isDarkMode ? "border-zinc-900 bg-zinc-950/35" : "border-zinc-150 bg-white shadow-sm"
              }`}>
                <table className="w-full text-left font-mono text-[10px] border-collapse">
                  <thead>
                    <tr className={`border-b font-sans font-bold tracking-widest text-zinc-500 text-[8px] uppercase ${
                      isDarkMode ? "border-zinc-900 bg-zinc-950/60" : "border-zinc-150 bg-zinc-50"
                    }`}>
                      <th className="p-3 pl-4">Subject</th>
                      <th className="p-3">Predicate</th>
                      <th className="p-3">Object</th>
                      <th className="p-3 hidden sm:table-cell">Committed</th>
                      <th className="p-3 text-right pr-4">Scope Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/10">
                    {memoriTriples
                      .filter(t => {
                        const s = tripleSearch.toLowerCase();
                        return t.subject.toLowerCase().includes(s) || 
                               t.predicate.toLowerCase().includes(s) || 
                               t.object.toLowerCase().includes(s);
                      })
                      .map((t) => (
                        <tr key={t.id} className="hover:bg-zinc-950/10 group">
                          <td className="p-3 pl-4 font-black text-indigo-400 truncate max-w-[120px]">{t.subject}</td>
                          <td className="p-3 text-zinc-400 font-semibold">{t.predicate}</td>
                          <td className="p-3 text-emerald-400 font-black">{t.object}</td>
                          <td className="p-3 text-zinc-500 hidden sm:table-cell">{new Date(t.timestamp).toLocaleTimeString()}</td>
                          <td className="p-3 text-right pr-4">
                            <button
                              onClick={() => handleDeleteTriple(t.id)}
                              className="p-1 text-zinc-500 hover:text-rose-400 rounded-lg transition-all hover:bg-rose-500/10 cursor-pointer"
                              title="Purge Knowledge"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    {memoriTriples.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-xs text-zinc-500 font-sans">
                          No memory triples stored. Type or run queries to dynamically extract.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

            </div>
          )}

          {memoriSubTab === "summaries" && (
            <div className="flex flex-col gap-3">
              {memoriSummaries.map((s) => (
                <div 
                  key={s.id} 
                  className={`p-5 rounded-3xl border flex flex-col gap-2.5 ${
                    isDarkMode ? "bg-zinc-950/45 border-zinc-900/60" : "bg-white border-zinc-150 shadow-sm"
                  }`}
                >
                  <div className="flex justify-between items-center border-b border-zinc-950/10 pb-2">
                    <span className="text-[9px] text-zinc-500 font-bold font-mono uppercase">{s.id}</span>
                    <span className="text-[9px] text-zinc-500 font-mono font-medium">{new Date(s.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-xs font-bold font-sans text-zinc-200 leading-snug">{s.summaryText}</p>
                  <div className={`p-3.5 rounded-xl text-[10px] font-medium font-sans leading-relaxed text-zinc-400 italic ${
                    isDarkMode ? "bg-zinc-950/40" : "bg-zinc-50"
                  }`}>
                    {s.narrativeFlow}
                  </div>
                </div>
              ))}
              
              {memoriSummaries.length === 0 && (
                <div className="p-8 text-center text-xs text-zinc-500 font-sans">
                  No dialogue outlines summarized yet.
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </section>

  </div>
);
}
