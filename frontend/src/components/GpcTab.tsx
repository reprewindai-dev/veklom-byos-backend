import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Cpu, 
  Activity, 
  CheckCircle2, 
  Play, 
  Plus, 
  Terminal,
  TrendingUp,
  RefreshCw
} from "lucide-react";
import { api } from "../services/api";
import { GpcPlan, GpcRun } from "../types";

interface GpcTabProps {
  isDarkMode: boolean;
}

export default function GpcTab({ isDarkMode }: GpcTabProps) {
  const [plans, setPlans] = useState<GpcPlan[]>([]);
  const [runs, setRuns] = useState<GpcRun[]>([]);
  const [signals, setSignals] = useState({ cpu: 32.4, memory: 1408, concurrency: 12 });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Forms
  const [newPlanName, setNewPlanName] = useState("");
  const [maxRuns, setMaxRuns] = useState("1000");
  const [showPlanForm, setShowPlanForm] = useState(false);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const gpcPlans = await api.getGpcPlans();
      const gpcRuns = await api.getGpcRuns();
      setPlans(gpcPlans);
      setRuns(gpcRuns);
    } catch (err) {
      console.error(err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();

    // setup dynamic telemetry signals polling
    const timer = setInterval(async () => {
      try {
        const live = await api.getLivePulse();
        setSignals({
          cpu: live.signals.cpuPercent,
          memory: live.signals.memoryMb,
          concurrency: live.signals.concurrencyGauge
        });
      } catch {
        // silent
      }
    }, 4500);

    return () => clearInterval(timer);
  }, []);

  const handleStartRun = async (planId: string) => {
    try {
      await api.startGpcRun(planId);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreatePlanSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlanName.trim()) return;
    try {
      await api.createGpcPlan(newPlanName, Number(maxRuns));
      setNewPlanName("");
      setShowPlanForm(false);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="gpc-view">
      
      {/* LEFT SECTION: GPC Plans (7 Cols) */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        
        <section className={`p-8 rounded-3xl border ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold tracking-tight">GPC Airgap Subgrid Planners</h3>
              <p className="text-[11px] text-zinc-550 mt-0.5">Initialize flight checklist plans over isolated secure network targets</p>
            </div>
            <button 
              onClick={() => setShowPlanForm(!showPlanForm)}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] rounded-xl transition-all cursor-pointer flex items-center gap-1 uppercase tracking-wider font-sans"
            >
              <Plus className="w-3.5 h-3.5" /> Create Plan
            </button>
          </div>

          <AnimatePresence>
            {showPlanForm && (
              <motion.form 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleCreatePlanSubmit}
                className={`p-4 rounded-xl border text-xs flex flex-col gap-2.5 mb-5 overflow-hidden ${
                  isDarkMode ? "bg-zinc-950/60 border-zinc-850" : "bg-zinc-50 border-zinc-150"
                }`}
              >
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Grid Area Name Plan Label</label>
                  <input 
                    type="text" 
                    value={newPlanName}
                    onChange={(e) => setNewPlanName(e.target.value)}
                    placeholder="e.g. Tallinn Old Town Old Sector Grid Cycle"
                    className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded text-[10px] outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Max Quota Flight Executions</label>
                  <input 
                    type="number"
                    value={maxRuns}
                    onChange={(e) => setMaxRuns(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded text-[10px]"
                  />
                </div>
                <button type="submit" className="w-full py-1.5 bg-indigo-600 text-white rounded font-bold text-[9px] uppercase tracking-wider cursor-pointer mt-1">
                  Enact planner
                </button>
              </motion.form>
            )}
          </AnimatePresence>

          <div className="flex flex-col gap-3">
            {plans.map((p) => (
              <div 
                key={p.id}
                className={`p-4 rounded-2xl border flex items-center justify-between transition-all ${
                  isDarkMode ? "bg-zinc-950/40 border-zinc-850 hover:border-zinc-800" : "bg-zinc-50 border-zinc-200"
                }`}
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <p className="font-bold text-xs text-zinc-250 leading-none">{p.name}</p>
                  </div>
                  <p className="text-[9px] text-zinc-500 font-mono font-medium mt-1.5">ID: {p.id} • Created: {new Date(p.created_at).toLocaleDateString()} • Scale Cap: {p.maxRuns} runs</p>
                </div>
                <button 
                  onClick={() => handleStartRun(p.id)}
                  className="p-2 bg-indigo-700/10 hover:bg-indigo-700 text-indigo-400 hover:text-white rounded-xl border border-indigo-550/20 transition-all cursor-pointer shrink-0"
                  title="Initialize flight run instantly"
                >
                  <Play className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>

      </div>

      {/* RIGHT SECTION: Flight Telemetry monitors (5 Cols) */}
      <div className="lg:col-span-5 flex flex-col gap-6" id="gpc-telemetry-panel">
        
        {/* Live telemetry monitors */}
        <section className={`p-8 rounded-3xl border flex flex-col gap-4 ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <h3 className="text-xs font-bold uppercase text-indigo-400 tracking-wider flex items-center gap-1.5 font-mono">
            <Activity className="w-4 h-4 animate-pulse" /> Sub-grid Flight Logs
          </h3>
          
          <div className="flex flex-col gap-3">
            {runs.map((r) => (
              <div 
                key={r.id} 
                className={`p-4 rounded-2xl border flex flex-col gap-2 font-mono text-[10px] leading-relaxed ${
                  r.status === "running"
                    ? "bg-amber-950/10 border-amber-900/40 text-amber-200 animate-pulse"
                    : "bg-zinc-950/40 border-zinc-850 text-zinc-444"
                }`}
              >
                <div className="flex items-center justify-between border-b border-zinc-805/30 pb-1.5 font-sans font-bold">
                  <span className="text-zinc-200 uppercase tracking-wider text-[9px]">Run: {r.id}</span>
                  <span className={`text-[8px] px-1 py-0.5 rounded font-black uppercase ${
                    r.status === "running" ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
                  }`}>{r.status}</span>
                </div>
                
                <p className="text-zinc-350">{r.eventSummary}</p>
                
                <div className="flex items-center justify-between text-[9px] text-zinc-550 mt-1">
                  <span>Tokens: {r.tokensConsumed}</span>
                  <span>Progress: {r.progressPercentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>

    </div>
  );
}
