import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  CreditCard, 
  Settings, 
  Users, 
  Download, 
  Check, 
  Plus, 
  RefreshCw,
  Cpu,
  ToggleLeft,
  ToggleRight
} from "lucide-react";
import { api } from "../services/api";
import { WorkspaceOverview, WorkspaceModel, WorkspaceMember, BudgetRule, ByosConfig } from "../types";

interface WorkspaceTabProps {
  isDarkMode: boolean;
}

export default function WorkspaceTab({ isDarkMode }: WorkspaceTabProps) {
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [models, setModels] = useState<WorkspaceModel[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [budgetRules, setBudgetRules] = useState<BudgetRule[]>([]);
  const [isUpdating, setIsUpdating] = useState(false);

  // BYOS Handshake configuration state
  const [byosConfig, setByosConfig] = useState<ByosConfig | null>(null);
  const [byosUrl, setByosUrl] = useState("");
  const [byosToken, setByosToken] = useState("");
  const [isHandshaking, setIsHandshaking] = useState(false);
  const [handshakeError, setHandshakeError] = useState<string | null>(null);
  const [handshakeSuccess, setHandshakeSuccess] = useState<string | null>(null);

  // Forms
  const [wsName, setWsName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "operator" | "viewer">("viewer");
  const [showInviteForm, setShowInviteForm] = useState(false);

  const loadData = async () => {
    try {
      const summary = await api.getWorkspaceOverview();
      const mods = await api.getWorkspaceModels();
      const mems = await api.getMembers();
      const rules = await api.getWorkspaceBudget();
      const byos = await api.getByosConfig();

      setWorkspace(summary.workspace);
      setModels(mods);
      setMembers(mems);
      setBudgetRules(rules);
      setWsName(summary.workspace.name);
      setByosConfig(byos);
      if (byos.byosBackendUrl) {
        setByosUrl(byos.byosBackendUrl);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleByosHandshake = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!byosUrl.trim()) return;
    setIsHandshaking(true);
    setHandshakeError(null);
    setHandshakeSuccess(null);
    try {
      const res = await api.performByosHandshake(byosUrl, byosToken);
      if (res.success) {
        setByosConfig(res.config);
        setHandshakeSuccess(res.message || "Crypto socket handshake successfully established with the source of truth!");
        setTimeout(() => {
          loadData();
        }, 1200);
      } else {
        setHandshakeError(res.error || "Handshake handshake rejected.");
      }
    } catch (err: any) {
      setHandshakeError(err.message || "Network handshake error. Confirm the destination allows CORS and is online.");
    } finally {
      setIsHandshaking(false);
    }
  };

  const handleDisconnectByos = async () => {
    setIsHandshaking(true);
    setHandshakeError(null);
    setHandshakeSuccess(null);
    try {
      const res = await api.disconnectByos();
      if (res.success) {
        setHandshakeSuccess("Handshake dissolved cleanly. Returning to offline test sandbox.");
        setByosToken("");
        setTimeout(() => {
          loadData();
        }, 1200);
      }
    } catch (err: any) {
      setHandshakeError(err.message);
    } finally {
      setIsHandshaking(false);
    }
  };

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wsName.trim()) return;
    setIsUpdating(true);
    try {
      const updated = await api.updateWorkspaceName(wsName);
      setWorkspace(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleToggleModel = async (id: string) => {
    try {
      const updated = await api.toggleWorkspaceModel(id);
      setModels(updated);
    } catch (err) {
      console.error(err);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    try {
      await api.inviteMember(inviteEmail, inviteRole);
      setInviteEmail("");
      setShowInviteForm(false);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownloadCsv = () => {
    // Download the cost-budget.csv endpoint directly
    window.open("/api/v1/workspace/cost-budget.csv", "_blank");
  };

  if (!workspace) return <div className="text-center p-8 font-mono text-zinc-500 animate-pulse">Loading Workspace details...</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="workspace-view">
      
      {/* SOVEREIGN BYOS HANDSHAKE CONTROLLER CARD */}
      <section className={`col-span-1 lg:col-span-12 p-8 rounded-3xl border transition-all ${
        isDarkMode ? "bg-indigo-950/10 border-indigo-500/20" : "bg-indigo-50/20 border-indigo-200 shadow-sm"
      }`} id="byos-handshake-panel">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></span>
              <h3 className="text-sm font-bold tracking-tight text-indigo-400 font-mono uppercase">
                Veklom BYOS Handshake & Truth Alignment Gateway
              </h3>
            </div>
            <p className="text-[11px] text-zinc-500 mt-1 font-medium">
              Connect and align this Hub with your live custom <strong>Veklom Bring-Your-Own-Server (BYOS)</strong> backend. Establishes cryptographic proxy tunnels directly to the source of truth.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-[10px]">
            {byosConfig?.byosConnected ? (
              <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-black rounded-lg uppercase tracking-wider flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                Sovereign Aligned
              </span>
            ) : (
              <span className="px-3 py-1 bg-amber-500/10 border border-amber-500/25 text-amber-405 font-black rounded-lg uppercase tracking-wider">
                Local Sandbox Mode
              </span>
            )}
          </div>
        </div>

        {byosConfig?.byosConnected ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className={`p-4 rounded-2xl border md:col-span-2 ${
              isDarkMode ? "bg-zinc-950/60 border-zinc-900" : "bg-white border-zinc-200"
            }`}>
              <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">Active Truth Tunnel URL</span>
              <p className="text-xs font-mono font-bold text-indigo-400 mt-1 break-all bg-indigo-500/5 px-3 py-2 rounded-xl border border-indigo-500/10">
                {byosConfig.byosBackendUrl}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 font-mono text-[10px]">
                <div>
                  <span className="text-zinc-505 block uppercase font-bold text-[8px] tracking-wider">Handshake Timestamp</span>
                  <span className="text-zinc-300 block mt-0.5 font-bold">
                    {byosConfig.byosHandshakeDetails?.timestamp ? new Date(byosConfig.byosHandshakeDetails.timestamp).toLocaleString() : "N/A"}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-505 block uppercase font-bold text-[8px] tracking-wider">Tested Endpoint</span>
                  <span className="text-zinc-300 block mt-0.5 text-emerald-400 font-bold">
                    GET {byosConfig.byosHandshakeDetails?.details?.endpointTested || "/health"} ({byosConfig.byosHandshakeDetails?.details?.responseStatus || "200"})
                  </span>
                </div>
              </div>

              {/* Quantum Probabilistic Caching Telemetry */}
              {byosConfig.cacheStats && (
                <div className="mt-5 pt-4 border-t border-zinc-800/20 dark:border-zinc-800/40">
                  <span className="text-[8px] block uppercase font-black text-indigo-400 tracking-widest font-mono mb-2">
                    Einstein Probabilistic Cache telemetry (Zero-Compute Optimization)
                  </span>
                  <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
                    <div className="p-2 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                      <span className="text-zinc-500 block text-[7.5px] font-bold uppercase text-[7px]">CACHE HITS (0ms)</span>
                      <span className="text-emerald-400 font-bold block mt-0.5 text-[11px] font-black">{byosConfig.cacheStats.hits} hits</span>
                    </div>
                    <div className="p-2 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                      <span className="text-zinc-500 block text-[7.5px] font-bold uppercase text-[7px]">LATENCY SAVED</span>
                      <span className="text-indigo-400 font-bold block mt-0.5 text-[11px] font-black">{byosConfig.cacheStats.latencySavedMs} ms</span>
                    </div>
                    <div className="p-2 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                      <span className="text-zinc-500 block text-[7.5px] font-bold uppercase text-[7px]">COMPUTE SAVED</span>
                      <span className="text-amber-400 font-bold block mt-0.5 text-[11px] font-black">¢{byosConfig.cacheStats.estimatedComputeSavedPennies.toFixed(3)} cx</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className={`p-5 rounded-2xl border flex flex-col justify-between ${
              isDarkMode ? "bg-zinc-950/20 border-zinc-900" : "bg-zinc-50/50 border-zinc-205"
            }`}>
              <div>
                <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider block">Operational Security</span>
                <p className="text-[11px] text-zinc-400 leading-relaxed mt-2 font-sans">
                  The client state machine is bound to the external server database. Local mock caches are dissolved. API keys and data operations are authenticated live.
                </p>
              </div>

              <button
                type="button"
                onClick={handleDisconnectByos}
                disabled={isHandshaking}
                className="mt-4 w-full py-2 cursor-pointer bg-rose-500/15 border border-rose-500/25 hover:bg-rose-500/25 text-rose-400 font-bold text-xs rounded-xl transition-all uppercase tracking-wider font-mono text-[9px]"
              >
                {isHandshaking ? "Disconnecting..." : "Dissolve Handshake"}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleByosHandshake} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="md:col-span-2">
              <label className="text-[10px] text-zinc-500 font-bold uppercase block mb-1 font-mono">
                Sovereign Backend URL (e.g., http://localhost:4000)
              </label>
              <input
                type="url"
                required
                value={byosUrl}
                onChange={(e) => setByosUrl(e.target.value)}
                placeholder="https://your-veklom-byos-endpoint.gpc"
                className={`w-full px-3.5 py-2.5 text-xs rounded-xl border outline-none font-mono ${
                  isDarkMode 
                    ? "bg-zinc-950 border-zinc-800 text-indigo-305 focus:border-indigo-500/50" 
                    : "bg-white border-zinc-250 text-indigo-600 focus:border-indigo-400"
                }`}
              />
            </div>

            <div>
              <label className="text-[10px] text-zinc-500 font-bold uppercase block mb-1 font-mono">
                Admin Authorization Key (Optional)
              </label>
              <input
                type="password"
                value={byosToken}
                onChange={(e) => setByosToken(e.target.value)}
                placeholder="vklm_byos_secret_token..."
                className={`w-full px-3.5 py-2.5 text-xs rounded-xl border outline-none font-mono ${
                  isDarkMode 
                    ? "bg-zinc-950 border-zinc-800 text-zinc-300 focus:border-indigo-500/50" 
                    : "bg-white border-zinc-250 text-zinc-700 focus:border-indigo-400"
                }`}
              />
            </div>

            <button
              type="submit"
              disabled={isHandshaking}
              className="py-2.5 px-4.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-zinc-805 text-white font-bold text-xs rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1.5 font-mono uppercase tracking-wider text-[10px] shrink-0"
            >
              {isHandshaking ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Plus className="w-3.5 h-3.5" />
              )}
              {isHandshaking ? "Aligning..." : "Connect BYOS"}
            </button>
          </form>
        )}

        {/* Dynamic Diagnostics Error or Success Logs */}
        {handshakeError && (
          <div className="mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 font-mono text-[10px] leading-relaxed">
            <span className="font-bold block uppercase mb-1">ALIGNMENT EXCEPTION TRIGGERED</span>
            {handshakeError}
          </div>
        )}
        {handshakeSuccess && (
          <div className="mt-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] leading-relaxed animate-pulse">
            <span className="font-bold block uppercase mb-1">SOVEREIGN NETWORK CONVERGENCE</span>
            {handshakeSuccess}
          </div>
        )}
      </section>

      {/* LEFT SECTION: Settings, Team, Model matrix (7 Cols) */}
      <div className="lg:col-span-7 flex flex-col gap-6">

        {/* Workspace core Settings */}
        <section className={`p-6 rounded-3xl border ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <h3 className="text-sm font-bold tracking-tight mb-4 flex items-center gap-2">
            <Settings className="w-4.5 h-4.5 text-indigo-400" /> Workspace Settings
          </h3>
          <form onSubmit={handleUpdateName} className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="flex-1">
              <label className="text-[10px] text-zinc-500 font-bold uppercase block mb-1">Workspace Mainframe Label</label>
              <input 
                type="text"
                value={wsName}
                onChange={(e) => setWsName(e.target.value)}
                className={`w-full px-3.5 py-2 text-xs rounded-xl border outline-none font-semibold ${
                  isDarkMode 
                    ? "bg-zinc-950 border-zinc-800 text-zinc-100" 
                    : "bg-zinc-50 border-zinc-200 text-zinc-800"
                }`}
              />
            </div>
            <button 
              type="submit"
              disabled={isUpdating}
              className="px-4.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl transition-all cursor-pointer inline-flex items-center gap-1 shrink-0"
            >
              {isUpdating ? "Syncing..." : "Update Details"}
            </button>
          </form>
        </section>

        {/* Model Activation Matrix */}
        <section className={`p-6 rounded-3xl border ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <h3 className="text-sm font-bold tracking-tight mb-1 flex items-center gap-2">
            <Cpu className="w-4.5 h-4.5 text-indigo-400" /> Cognitive Layer Model Matrix
          </h3>
          <p className="text-[11px] text-zinc-550 mb-4">Toggle AI and Agent nodes availability within this sovereign workspace</p>
          
          <div className="flex flex-col gap-2.5">
            {models.map((mod) => (
              <div 
                key={mod.id}
                className={`p-3 rounded-2xl border flex items-center justify-between transition-all ${
                  mod.active 
                    ? isDarkMode ? "bg-zinc-950/40 border-indigo-900/30" : "bg-indigo-50/10 border-indigo-100"
                    : "opacity-60 bg-transparent border-zinc-900/10"
                }`}
              >
                <div>
                  <p className="text-xs font-bold text-zinc-200">{mod.name}</p>
                  <p className="text-[9px] text-zinc-500 font-medium font-mono mt-0.5">ID: {mod.id} • Cost rate: ${(mod.costPer1kInput * 1000).toFixed(4)}/1k tkn</p>
                </div>
                <button 
                  onClick={() => handleToggleModel(mod.id)}
                  className="p-1 px-2 group shrink-0 transition-all cursor-pointer"
                >
                  {mod.active ? (
                    <span className="text-indigo-400 flex items-center gap-0.5 font-bold text-[10px]">
                      <ToggleRight className="w-8 h-8 text-indigo-500" />
                    </span>
                  ) : (
                    <span className="text-zinc-550 flex items-center gap-0.5 font-bold text-[10px]">
                      <ToggleLeft className="w-8 h-8 text-zinc-800" />
                    </span>
                  )}
                </button>
              </div>
            ))}
          </div>
        </section>

      </div>

      {/* RIGHT SECTION: Budget Rules & Team coordinations (5 Cols) */}
      <div className="lg:col-span-5 flex flex-col gap-6">

        {/* Budget ledger rules & CSV exports */}
        <section className={`p-6 rounded-3xl border text-xs ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase text-indigo-400 tracking-wider flex items-center gap-1.5 font-mono">
              <CreditCard className="w-4 h-4" /> Quota Budget Regulations
            </h3>
            <button 
              onClick={handleDownloadCsv}
              className="px-2.5 py-1 text-[10px] bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-500/15 rounded-lg font-bold transition-all flex items-center gap-1 cursor-pointer font-sans"
              id="export-budget-csv-btn"
            >
              <Download className="w-3.5 h-3.5" /> CSV Report
            </button>
          </div>

          <div className="flex flex-col gap-3">
            {budgetRules.map((br) => (
              <div key={br.id} className={`p-3.5 rounded-2xl border ${isDarkMode ? "bg-zinc-950/50 border-zinc-850" : "bg-zinc-50 border-zinc-200"}`}>
                <div className="flex items-center justify-between text-xs font-bold">
                  <span className="text-zinc-200">{br.name}</span>
                  <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono font-medium">{br.interval}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-zinc-500 mt-2 font-mono">
                  <span>Usage: ${br.spentUsd.toFixed(2)}</span>
                  <span>Limit: ${br.limitUsd.toLocaleString()}</span>
                </div>
                <div className="h-1.5 bg-zinc-800/60 rounded-full mt-2.5 overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${br.spentUsd / br.limitUsd > 0.85 ? "bg-rose-500" : "bg-indigo-500"}`}
                    style={{ width: `${Math.min(100, (br.spentUsd / br.limitUsd) * 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Team Coordination Members List */}
        <section className={`p-6 rounded-3xl border flex flex-col gap-3 ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-indigo-400 tracking-wider flex items-center gap-1.5 font-mono">
              <Users className="w-4 h-4" /> Workspace Members
            </h3>
            <button 
              onClick={() => setShowInviteForm(!showInviteForm)}
              className="text-[10px] bg-indigo-600/15 border border-indigo-500/25 text-indigo-400 px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer"
            >
              Invite
            </button>
          </div>

          <AnimatePresence>
            {showInviteForm && (
              <motion.form 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleInviteMember}
                className={`p-3 rounded-xl border text-xs flex flex-col gap-2 overflow-hidden ${
                  isDarkMode ? "bg-zinc-950/60 border-zinc-800" : "bg-zinc-50 border-zinc-150"
                }`}
              >
                <input 
                  type="email" 
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="Invite colleague email..."
                  className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 text-[10px] rounded"
                />
                <button type="submit" className="w-full py-1 bg-indigo-600 rounded font-black text-white text-[9px] uppercase cursor-pointer">
                  Send Invite
                </button>
              </motion.form>
            )}
          </AnimatePresence>

          <div className="flex flex-col gap-2">
            {members.map((m) => (
              <div 
                key={m.id}
                className={`p-3 rounded-2xl border text-xs flex items-center justify-between font-mono ${
                  isDarkMode ? "bg-zinc-950/30 border-zinc-900" : "bg-zinc-50 border-zinc-200"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="font-semibold text-zinc-300 font-sans truncate">{m.email}</p>
                  <p className="text-[9px] text-zinc-500 capitalize">{m.role}</p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                  m.status === "active" 
                    ? "bg-emerald-500/10 text-emerald-400" 
                    : "bg-amber-500/10 text-amber-400"
                }`}>
                  {m.status}
                </span>
              </div>
            ))}
          </div>
        </section>

      </div>

    </div>
  );
}
