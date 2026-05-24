import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Network, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Users, 
  ArrowRight,
  TrendingUp,
  Plus,
  RefreshCw,
  Cpu
} from "lucide-react";
import { api } from "../services/api";
import { Pipeline, RoutingRule } from "../types";

interface PipelinesTabProps {
  isDarkMode: boolean;
}

export default function PipelinesTab({ isDarkMode }: PipelinesTabProps) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [routingRules, setRoutingRules] = useState<RoutingRule[]>([]);
  
  // Custom router form states
  const [newPath, setNewPath] = useState("");
  const [newModel, setNewModel] = useState("tax-kratt-v6");
  const [newFallback, setNewFallback] = useState("gemini-3.5-flash");
  const [newPolicy, setNewPolicy] = useState<"cost_optimized" | "latency_optimized" | "integrity_max">("cost_optimized");
  const [showRouterForm, setShowRouterForm] = useState(false);

  const loadData = async () => {
    try {
      const pipes = await api.getPipelines();
      const routes = await api.getRoutingRules();
      setPipelines(pipes);
      setRoutingRules(routes);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunPipeline = async (id: string) => {
    try {
      await api.triggerPipelineRun(id);
      loadData();
      // Simulates loading interval
      setTimeout(loadData, 4500);
    } catch (err) {
      console.error(err);
    }
  };

  const handlePromoteCanary = async (id: string) => {
    try {
      await api.promoteCanary(id);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateRouter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPath.trim()) return;
    try {
      await api.createRoutingRule({
        path: newPath,
        modelId: newModel,
        fallbackModelId: newFallback,
        policy: newPolicy
      });
      setNewPath("");
      setShowRouterForm(false);
      loadData();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="pipelines-view">
      
      {/* LEFT COMPONENT: Automated Continuous Pipelines (7 Cols) */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        
        <section className={`p-8 rounded-3xl border ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold tracking-tight">Active Automation Pipelines</h3>
              <p className="text-[11px] text-zinc-550 mt-0.5">Control schedules, manual triggers, and Edge Canary rates</p>
            </div>
            <button 
              onClick={loadData}
              className="p-2 rounded-xl bg-zinc-805 border border-zinc-800 text-zinc-350 cursor-pointer hover:bg-zinc-800"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-col gap-4">
            {pipelines.map((p) => (
              <div 
                key={p.id}
                className={`p-4.5 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${
                  isDarkMode ? "bg-zinc-950/40 border-zinc-850" : "bg-zinc-50 border-zinc-200"
                }`}
              >
                <div className="overflow-hidden">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      p.status === "completed" 
                        ? "bg-emerald-500" 
                        : p.status === "running"
                          ? "bg-amber-500 animate-pulse"
                          : "bg-rose-500"
                    }`}></span>
                    <p className="font-bold text-xs text-zinc-200">{p.name}</p>
                  </div>
                  
                  <div className="flex items-center gap-3.5 text-[10px] text-zinc-500 font-mono mt-2 font-medium">
                    <span>Trigger: {p.trigger}</span>
                    <span>Canary Target: {p.canaryTarget}%</span>
                    {p.lastRunAt && <span>Ran: {new Date(p.lastRunAt).toLocaleTimeString()}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 font-sans">
                  {/* Promote Canary button if not 100% */}
                  {p.canaryTarget < 100 && (
                    <button 
                      onClick={() => handlePromoteCanary(p.id)}
                      className="px-3 py-1 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-500/20 text-emerald-400 font-bold text-[9px] rounded-lg tracking-wider transition-all cursor-pointer uppercase"
                    >
                      Promote Canary
                    </button>
                  )}
                  
                  {/* Trigger Run */}
                  <button 
                    onClick={() => handleRunPipeline(p.id)}
                    disabled={p.status === "running"}
                    className="p-2 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/15 rounded-xl transition-all cursor-pointer shrink-0"
                    title="Trigger Run Manually"
                  >
                    <Play className="w-3.5 h-3.5" />
                  </button>
                </div>

              </div>
            ))}
          </div>
        </section>

      </div>

      {/* RIGHT COMPONENT: Gated Policy Routing rule config (5 Cols) */}
      <div className="lg:col-span-5 flex flex-col gap-6" id="routing-config-section">
        
        <section className={`p-8 rounded-3xl border flex flex-col gap-4 ${isDarkMode ? "bg-zinc-900/30 border-zinc-900" : "bg-white border-zinc-200 shadow-sm"}`}>
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-indigo-400 tracking-wider flex items-center gap-1.5 font-mono">
              <Network className="w-4 h-4" /> Cognitive Routing Rules
            </h3>
            <button 
              onClick={() => setShowRouterForm(!showRouterForm)}
              className="text-[10px] bg-indigo-600/15 border border-indigo-500/35 text-indigo-400 px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer font-sans"
            >
              Add Route
            </button>
          </div>

          {/* Router Form */}
          <AnimatePresence>
            {showRouterForm && (
              <motion.form 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleCreateRouter}
                className={`p-4 rounded-xl border text-xs flex flex-col gap-2.5 overflow-hidden ${
                  isDarkMode ? "bg-zinc-950/60 border-zinc-850" : "bg-zinc-50 border-zinc-150"
                }`}
              >
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Target Endpoint Path URI</label>
                  <input 
                    type="text" 
                    value={newPath}
                    onChange={(e) => setNewPath(e.target.value)}
                    placeholder="e.g. /api/v1/ai/custom-records"
                    className="w-full px-2.5 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded text-[10px] outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Main Model Node</label>
                  <select 
                    value={newModel}
                    onChange={(e) => setNewModel(e.target.value)}
                    className="w-full px-2 py-1.5 bg-zinc-905 border border-[rgb(120,40,240)] text-zinc-200 rounded text-[10px]"
                  >
                    <option value="tax-kratt-v6">Sovereign Tax Kratt Node</option>
                    <option value="medical-kratt-v6">Sovereign Tervise Patient files Node</option>
                    <option value="deepseek-r1">DeepSeek R1 Sovereign local node</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Fallback node (Gate override)</label>
                  <select 
                    value={newFallback}
                    onChange={(e) => setNewFallback(e.target.value)}
                    className="w-full px-2 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded text-[10px]"
                  >
                    <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                    <option value="gemini-3.5-pro">Gemini 3.5 Pro (Heavy model)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Routing optimization policy</label>
                  <select 
                    value={newPolicy}
                    onChange={(e) => setNewPolicy(e.target.value as any)}
                    className="w-full px-2 py-1.5 bg-zinc-905 border border-zinc-700 text-zinc-200 rounded text-[10px]"
                  >
                    <option value="cost_optimized">COST OPTIMIZED</option>
                    <option value="latency_optimized">LATENCY OPTIMIZED</option>
                    <option value="integrity_max">MAXIMUM PROTECTION CONSTRAINTS</option>
                  </select>
                </div>
                <button type="submit" className="w-full py-1.5 bg-indigo-600 text-white rounded font-bold text-[9px] uppercase tracking-wider cursor-pointer mt-1">
                  Enforce routing rule
                </button>
              </motion.form>
            )}
          </AnimatePresence>

          <div className="flex flex-col gap-3">
            {routingRules.map((rr) => (
              <div 
                key={rr.id}
                className={`p-4 rounded-2xl border text-xs leading-normal font-mono flex flex-col gap-1.5 ${
                  isDarkMode ? "bg-zinc-950/40 border-zinc-900" : "bg-zinc-50 border-zinc-200"
                }`}
              >
                <div className="flex items-center justify-between border-b border-zinc-800/20 pb-2">
                  <span className="font-bold text-zinc-250 font-sans tracking-tight text-[11px]">{rr.path}</span>
                  <span className="text-[8px] bg-indigo-500/10 text-indigo-400 px-1 py-0.5 rounded font-black uppercase font-mono border border-indigo-500/20">
                    {rr.policy.replace("_", " ")}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-[10px] text-zinc-500 mt-1 font-medium font-mono">
                  <span className="text-indigo-400 font-semibold uppercase text-[9px]">Root:</span> {rr.modelId} 
                  <ArrowRight className="w-3.5 h-3.5" /> 
                  <span className="text-zinc-500 uppercase text-[9px]">Fallback:</span> {rr.fallbackModelId}
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>

    </div>
  );
}
