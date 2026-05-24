import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Key, 
  ShieldAlert, 
  Trash2, 
  Plus, 
  Activity, 
  AlertTriangle,
  Lock,
  Unlock,
  CheckCircle2,
  Download,
  ShieldCheck,
  FileText,
  RefreshCw,
  Check,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { api } from "../services/api";
import { ApiKey, SecurityEvent, LedgerBlock } from "../types";

interface SecurityTabProps {
  isDarkMode: boolean;
}

export default function SecurityTab({ isDarkMode }: SecurityTabProps) {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isSystemLocked, setIsSystemLocked] = useState(false);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [ledger, setLedger] = useState<LedgerBlock[]>([]);
  const [verifiedBlocks, setVerifiedBlocks] = useState<Record<number, { verified: boolean; validatedAt: string }>>({});
  const [isVerifying, setIsVerifying] = useState<Record<number, boolean>>({});
  const [expandedBlocks, setExpandedBlocks] = useState<Record<number, boolean>>({});
  const [isAutoRefresh, setIsAutoRefresh] = useState(false);
  
  const toggleBlockExpanded = (index: number) => {
    setExpandedBlocks(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };
  
  // Create Key form state
  const [keyName, setKeyName] = useState("");
  const [keyScope, setKeyScope] = useState("all");
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [isActivating, setIsActivating] = useState(false);

  const loadData = async () => {
    try {
      const keys = await api.getApiKeys();
      const status = await api.getKillSwitchStatus();
      const dbInfo = await api.getSecurityDashboard();
      const auditLedger = await api.getAuditLogs();
      
      setApiKeys(keys);
      setIsSystemLocked(status.active);
      setEvents(dbInfo.events);
      setLedger(auditLedger);
    } catch (err) {
      console.error(err);
    }
  };

  const handleExportAuditLogs = () => {
    try {
      const formatted = JSON.stringify(ledger, null, 2);
      const url = URL.createObjectURL(new Blob([formatted], { type: "application/json" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `veklom-blockchain-ledger-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    }
  };

  const handleVerifyBlock = async (index: number) => {
    setIsVerifying(prev => ({ ...prev, [index]: true }));
    try {
      const res = await api.verifyAuditLog(index);
      if (res.success || res.Verified) {
        setVerifiedBlocks(prev => ({
          ...prev,
          [index]: {
            verified: res.Verified !== false,
            validatedAt: res.validatedAt || new Date().toISOString()
          }
        }));
      }
    } catch (err) {
      console.error("Failed to verify block alignment", err);
    } finally {
      setIsVerifying(prev => ({ ...prev, [index]: false }));
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (isAutoRefresh) {
      interval = setInterval(async () => {
        try {
          const auditLedger = await api.getAuditLogs();
          setLedger(auditLedger);
        } catch (err) {
          console.error("Auto-refresh ledger error:", err);
        }
      }, 10000);
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isAutoRefresh]);

  const handleCreateKey = typeof window !== 'undefined' ? async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    try {
      await api.createApiKey(keyName, keyScope);
      setKeyName("");
      setShowKeyForm(false);
      loadData();
    } catch (err) {
      console.error(err);
    }
  } : undefined;

  const handleRevokeKey = async (id: string) => {
    if (!confirm("Are you sure you want to instantly revoke this access credential?")) return;
    try {
      await api.revokeApiKey(id);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  // Toggle Global System Emergency Kill Switch
  const handleToggleKillSwitch = async () => {
    setIsActivating(true);
    try {
      if (isSystemLocked) {
        const res = await api.deactivateKillSwitch();
        setIsSystemLocked(res.active);
      } else {
        if (confirm("WARNING: STAGE 1 COGNITIVE FIREWALL DISABLING ACTIVATES HARD COLD-LOCK OVER ALL RUNNING MODELS. THIS TERMINATES OUTGOING API ENDPOINTS IMMEDIATELY. PROCEED?")) {
          const res = await api.activateKillSwitch();
          setIsSystemLocked(res.active);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsActivating(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="security-view">
      
      {/* LEFT SECTION: Key Vault & Key Builder (7 Cols) */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        
        {/* API credential vault */}
        <section className={`p-8 rounded-3xl border ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold tracking-tight">Access Token API Vault (Administrative Keys)</h3>
              <p className="text-[11px] text-zinc-550 mt-0.5">Manage administrative credentials for Sovereign API links</p>
            </div>
            <button 
              onClick={() => setShowKeyForm(!showKeyForm)}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] rounded-xl transition-all cursor-pointer flex items-center gap-1 uppercase tracking-wider font-sans"
            >
              <Plus className="w-3.5 h-3.5" /> Create Key
            </button>
          </div>

          <AnimatePresence>
            {showKeyForm && (
              <motion.form 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleCreateKey}
                className={`p-4 rounded-2xl border text-xs flex flex-col gap-3 mb-5 overflow-hidden ${
                  isDarkMode ? "bg-zinc-950/60 border-zinc-800" : "bg-zinc-50 border-zinc-150"
                }`}
              >
                <div>
                  <label className="text-[10px] text-zinc-500 font-bold block mb-1">Key Label Name</label>
                  <input 
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-905 border border-zinc-700 text-zinc-150 text-[11px] rounded-lg focus:border-indigo-500"
                    placeholder="e.g. Tallinn Analytics Integration webhook"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-bold block mb-1">Security Scope Permission</label>
                  <select 
                    value={keyScope}
                    onChange={(e) => setKeyScope(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-150 text-[11px] rounded-lg"
                  >
                    <option value="all">Superuser scope (All permissions)</option>
                    <option value="financial:tax-records">Tax credentials only</option>
                    <option value="medical:patient-files">medical files retrieval only</option>
                  </select>
                </div>
                <button 
                  type="submit" 
                  className="w-full py-2 bg-indigo-600 rounded-xl font-bold text-white text-[10px] tracking-wider uppercase mt-1 cursor-pointer hover:bg-indigo-700"
                >
                  Authorize and Generate Secret
                </button>
              </motion.form>
            )}
          </AnimatePresence>

          <div className="flex flex-col gap-3">
            {apiKeys.map((k) => (
              <div 
                key={k.id}
                className={`p-4 rounded-2xl border flex items-center justify-between text-xs font-mono transition-all ${
                  isDarkMode ? "bg-zinc-950/40 border-zinc-850" : "bg-zinc-50 border-zinc-200"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="font-bold text-zinc-200 font-sans">{k.name}</p>
                  <div className="flex items-center gap-3 text-[10px] text-zinc-500 mt-1">
                    <span className="bg-zinc-800/40 px-1.5 py-0.5 rounded text-indigo-400 font-semibold">{k.prefix}_••••••••</span>
                    <span>Scope: {k.scope}</span>
                  </div>
                </div>
                <button 
                  onClick={() => handleRevokeKey(k.id)}
                  className="p-2 bg-zinc-800 hover:bg-rose-950/20 text-zinc-500 hover:text-rose-400 rounded-xl transition-all border border-zinc-800/40 hover:border-rose-900/30 cursor-pointer"
                  title="Revoke Key instantly"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>

      </div>

      {/* RIGHT SECTION: Sovereign System Emergency Kill Switch (5 Cols) */}
      <div className="lg:col-span-5 flex flex-col gap-6" id="killswitch-section">
        
        {/* Red emergency component calling system api */}
        <section className={`p-8 rounded-3xl border flex flex-col gap-4 relative overflow-hidden transition-all ${
          isSystemLocked 
            ? "border-rose-900 bg-rose-950/10 text-rose-100 shadow-lg shadow-rose-950/10" 
            : isDarkMode 
              ? "bg-zinc-900/30 border-zinc-900 text-zinc-150" 
              : "bg-white border-zinc-200 text-zinc-900 shadow-sm"
        }`}>
          <div className="absolute top-0 right-0 w-36 h-36 bg-rose-600/10 dark:bg-rose-600/10 blur-[50px] rounded-full pointer-events-none"></div>
          
          <h3 className="text-xs font-bold uppercase text-rose-500 tracking-wider flex items-center gap-1.5 font-mono">
            <ShieldAlert className="w-4 h-4 animate-bounce" /> Sovereign Hub Emergency Lockdown
          </h3>
          <p className="text-xs leading-relaxed text-zinc-400">
            Authorized administrators can deploy a cognitive cyber-curtain. This locks the active model nodes statefully to prevent rogue leak attempts or compliance breaches.
          </p>

          <div className="flex items-center gap-3.5 my-3 p-4 rounded-2xl border bg-zinc-950/50 border-rose-950/30 font-mono">
            {isSystemLocked ? (
              <>
                <Lock className="w-8 h-8 text-rose-500 animate-pulse shrink-0" />
                <div>
                  <p className="text-xs font-black text-rose-400 tracking-wider">🔒 COGNITIVE COLD-LOCK ACTIVE</p>
                  <p className="text-[9px] text-rose-500 mt-0.5">All outgoing queries blocked recursively</p>
                </div>
              </>
            ) : (
              <>
                <Unlock className="w-8 h-8 text-emerald-400 shrink-0" />
                <div>
                  <p className="text-xs font-black text-emerald-400 tracking-wider">🛡️ FIREWALL STANDBY nominal</p>
                  <p className="text-[9px] text-zinc-550 mt-0.5">Agent gates operating in routing alignment</p>
                </div>
              </>
            )}
          </div>

          <button 
            onClick={handleToggleKillSwitch}
            disabled={isActivating}
            className={`w-full py-4.5 rounded-2xl font-black text-xs tracking-widest uppercase transition-all shadow-lg cursor-pointer ${
              isSystemLocked 
                ? "bg-indigo-700 hover:bg-indigo-600 text-white shadow-indigo-700/10" 
                : "bg-rose-700 hover:bg-rose-600 text-white shadow-rose-700/20"
            }`}
          >
            {isActivating ? "BROADCASTING ENCRYPTED SIGNAL..." : isSystemLocked ? "DISARM SYSTEM LOCKDOWN" : "ENGAGE SYSTEM COLD-LOCK"}
          </button>
        </section>

      </div>

      {/* FULL WIDTH SECTION: Blockchain Ledger Auditing System */}
      <section className={`col-span-1 lg:col-span-12 p-8 rounded-3xl border transition-all ${
        isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"
      }`} id="ledger-audit-section">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
          <div>
            <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Sovereign Blockchain Ledger Audit Log
            </h3>
            <p className="text-[11px] text-zinc-550 mt-1">
              Tamper-proof, cryptographically signed ledger blocks proving citizen query safety and execution compliance.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            {/* Elegant Auto-Refresh Toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input 
                type="checkbox" 
                checked={isAutoRefresh} 
                onChange={(e) => setIsAutoRefresh(e.target.checked)}
                className="sr-only peer"
              />
              <div className={`w-8 h-4.5 bg-zinc-700/65 dark:bg-zinc-800 rounded-full relative transition-colors duration-200 peer-focus:outline-none ${
                isAutoRefresh ? "bg-indigo-600 dark:bg-indigo-600" : ""
              }`}>
                <div className={`w-3 h-3 bg-white rounded-full absolute top-[3px] transition-all duration-200 ${
                  isAutoRefresh ? "left-[17px]" : "left-[3px]"
                }`} />
              </div>
              <span className={`text-[10px] font-mono uppercase tracking-wider font-bold transition-all ${
                isAutoRefresh 
                  ? "text-indigo-400" 
                  : isDarkMode ? "text-zinc-550 hover:text-zinc-400" : "text-zinc-650 hover:text-zinc-800"
              } flex items-center gap-1.5`}>
                Auto-Refresh (10s)
                {isAutoRefresh && <RefreshCw className="w-2.5 h-2.5 animate-spin text-indigo-400" />}
              </span>
            </label>

            <span className="hidden sm:block w-px h-5 bg-zinc-800/30"></span>

            <button 
              onClick={handleExportAuditLogs}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl transition-all cursor-pointer self-start uppercase tracking-wider text-[10px]"
            >
              <Download className="w-3.5 h-3.5" />
              Export Audit Log
            </button>
          </div>
        </div>

        {ledger.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-zinc-800 rounded-2xl">
            <p className="text-xs text-zinc-500 font-mono">No cryptographic blocks committed to the ledger yet.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4 max-h-[500px] overflow-y-auto pr-2">
            {[...ledger].reverse().map((block) => {
              const isGenesis = block.index === 0;
              const isVerified = verifiedBlocks[block.index]?.verified;
              const verificationTime = verifiedBlocks[block.index]?.validatedAt;
              const verifyingNow = isVerifying[block.index];
              const isExpanded = !!expandedBlocks[block.index];

              return (
                <div 
                  key={block.index}
                  onClick={() => toggleBlockExpanded(block.index)}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer select-none ${
                    isDarkMode 
                      ? "bg-zinc-950/40 border-zinc-900 hover:border-zinc-800/80 hover:bg-zinc-900/15" 
                      : "bg-zinc-50/55 border-zinc-200 hover:border-zinc-300 hover:bg-zinc-100/40 shadow-sm"
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-zinc-800/15 dark:border-zinc-850 mb-3">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className={`px-2.5 py-1 text-[9px] font-mono font-black tracking-wider uppercase rounded-lg ${
                        isGenesis 
                          ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                          : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/10"
                      }`}>
                        Block #{block.index}
                      </span>
                      {isGenesis && (
                        <span className="px-2 py-0.5 bg-purple-500/15 text-purple-400 border border-purple-500/20 text-[8px] font-mono font-bold rounded-md">
                          GENESIS ROOT
                        </span>
                      )}
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {new Date(block.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {isVerified ? (
                        <div className="flex items-center gap-1 text-[9px] text-emerald-400 font-mono uppercase bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Chain Verified</span>
                        </div>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleVerifyBlock(block.index);
                          }}
                          disabled={verifyingNow}
                          className={`flex items-center gap-1.5 px-3 py-1 text-[9px] font-bold rounded-lg border cursor-pointer transition-all ${
                            isDarkMode 
                              ? "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800 hover:text-white"
                              : "bg-white border-zinc-300 text-zinc-700 hover:bg-zinc-100"
                          }`}
                        >
                          {verifyingNow ? (
                            <RefreshCw className="w-3 h-3 animate-spin text-zinc-400" />
                          ) : (
                            <ShieldCheck className="w-3 h-3 text-indigo-400" />
                          )}
                          Verify Integration
                        </button>
                      )}

                      {/* Expand Chevron Icon */}
                      <div className={`p-1 rounded-lg transition-all ${
                        isDarkMode ? "hover:bg-zinc-905 text-zinc-500" : "hover:bg-zinc-200 text-zinc-500"
                      }`}>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-indigo-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-zinc-500 hover:text-zinc-650 dark:hover:text-zinc-300" />
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3 font-mono text-[10px]">
                    <div>
                      <span className="text-zinc-500 block uppercase font-bold text-[8px] tracking-wider">Citizen Signer</span>
                      <span className="text-zinc-300 truncate block mt-0.5 font-sans font-medium">{block.citizenEmail}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block uppercase font-bold text-[8px] tracking-wider">Target Node</span>
                      <span className="text-emerald-400 font-mono font-semibold uppercase block mt-0.5">{block.agentId}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block uppercase font-bold text-[8px] tracking-wider">Citizen Query</span>
                      <span className="text-indigo-400 font-sans block mt-0.5 truncate">{block.query}</span>
                    </div>
                  </div>

                  <div className={`p-3 rounded-xl mb-3 leading-relaxed text-xs ${
                    isDarkMode ? "bg-zinc-950/60 text-zinc-400" : "bg-white border border-zinc-150 text-zinc-700"
                  }`}>
                    <p className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider mb-1 font-mono">Response Payload Checkpoint</p>
                    <p className="font-sans line-clamp-2 hover:line-clamp-none transition-all duration-300 cursor-pointer">
                      {block.response}
                    </p>
                  </div>

                  {/* Cryptographic Gate Evaluation Result (Expandable code block) */}
                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22, ease: "easeInOut" }}
                        className="overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className={`p-4 rounded-xl border mb-3 font-mono text-[10.5px] leading-relaxed select-text ${
                          isDarkMode ? "bg-zinc-900/30 border-zinc-900 text-zinc-300" : "bg-zinc-100/60 border-zinc-250 text-zinc-805"
                        }`}>
                          <div className="flex items-center justify-between border-b border-zinc-800/10 dark:border-zinc-800/40 pb-2 mb-2">
                            <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-widest font-mono">Cryptographic Gates Evaluation Report</span>
                            <span className="text-[9px] bg-indigo-505/10 bg-indigo-600/10 text-indigo-405 text-indigo-400 px-2 py-0.5 rounded border border-indigo-500/20 font-sans font-black">gatesResult</span>
                          </div>
                          <pre className="overflow-x-auto whitespace-pre p-1 text-[10px] bg-zinc-950/20 dark:bg-zinc-950/60 p-2.5 rounded-lg max-h-[350px] scrollbar-thin scrollbar-thumb-zinc-800">
                            {JSON.stringify(block.gatesResult, null, 2)}
                          </pre>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className={`p-3.5 rounded-xl border font-mono text-[9px] flex flex-col gap-1.5 ${
                    isDarkMode ? "bg-zinc-950/80 border-zinc-900" : "bg-zinc-100/50 border-zinc-200"
                  }`}>
                    <div className="flex justify-between gap-4 overflow-hidden">
                      <span className="text-zinc-500 uppercase font-black text-[8px] shrink-0">BLOCK HASH</span>
                      <span className="text-zinc-400 truncate max-w-xl font-mono">{block.hash}</span>
                    </div>
                    <div className="flex justify-between gap-4 overflow-hidden border-t border-zinc-900/10 dark:border-zinc-900/40 pt-1.5">
                      <span className="text-zinc-500 uppercase font-black text-[8px] shrink-0">PREVIOUS BLOCK HASH</span>
                      <span className="text-zinc-400 truncate max-w-xl font-mono">{block.previousHash}</span>
                    </div>
                    {block.signature && (
                      <div className="flex justify-between gap-4 overflow-hidden border-t border-zinc-900/10 dark:border-zinc-900/40 pt-1.5">
                        <span className="text-zinc-500 uppercase font-black text-[8px] shrink-0">MUTUALLY SIGNED ROOT</span>
                        <span className="text-indigo-400/90 truncate max-w-xl font-mono">{block.signature}</span>
                      </div>
                    )}
                    {verificationTime && (
                      <div className="flex flex-col sm:flex-row justify-between gap-2 mt-2 pt-2 border-t border-emerald-500/20">
                        <span className="text-emerald-500 font-bold uppercase text-[8px] tracking-widest">VERIFIED ALIGNMENT SECURE</span>
                        <span className="text-emerald-400/90 font-sans">Active alignment confirmed at {new Date(verificationTime).toLocaleTimeString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

    </div>
  );
}
