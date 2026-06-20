import { useState, useEffect, useRef, ReactNode } from "react";
import { 
  Zap, 
  Terminal, 
  Activity, 
  LayoutGrid, 
  Disc, 
  Play, 
  Box, 
  ChevronRight, 
  ShieldCheck, 
  Cpu, 
  Database,
  ArrowUpRight,
  Info,
  Layers,
  Lock,
  Search,
  BrainCircuit
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { GoogleGenAI } from "@google/genai";
import { 
  AreaChart, 
  Area, 
  ResponsiveContainer,
} from "recharts";

// --- Types ---
interface SSRNSignal {
  id: string;
  title: string;
  strength: number;
  timestamp: string;
  category: string;
}

interface Plan {
  id: string;
  name: string;
  intent: string;
  graph: {
    nodes: Array<{
      id: string;
      type: 'quantum' | 'classical';
      description: string;
      policy_tag?: string;
      entropy?: number;
    }>;
    edges: Array<{ from: string; to: string }>;
  };
  status: string;
  createdAt: string;
}

interface Run {
  id: string;
  planId: string;
  status: string;
  progress: number;
  currentStep: string;
  startTime: string;
  output?: string;
}

// --- SDK Initialization ---
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || "" });

export default function App() {
  const [activeTab, setActiveTab] = useState<'intent' | 'execution' | 'ops'>('intent');
  const [intent, setIntent] = useState("");
  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [signals, setSignals] = useState<any>(null);
  const [ssrnData, setSsrnData] = useState<SSRNSignal[]>([]);
  const [identity, setIdentity] = useState<string>("ANON_AGENT");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initial Bootstrap
    const fetchData = async () => {
      try {
        const [p, r, e, s, b] = await Promise.all([
          fetch("/api/plans").then(res => res.json()),
          fetch("/api/runs").then(res => res.json()),
          fetch("/api/events").then(res => res.json()),
          fetch("/api/ssrn-signals").then(res => res.json()),
          fetch("/api/bootstrap").then(res => res.json())
        ]);
        setPlans(p);
        setRuns(r);
        setEvents(e);
        setSsrnData(s);
        setIdentity(b.userEmail);
      } catch (err) {
        console.error("Bootstrap error:", err);
      }
    };
    
    fetchData();

    // Signal Polling
    const interval = setInterval(() => {
      fetch("/api/observability/signals")
        .then(res => res.json())
        .then(setSignals)
        .catch(() => {});
    }, 4000);

    // WebSocket for real-time updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}`;
    const connectWs = () => {
      socketRef.current = new WebSocket(wsUrl);
      socketRef.current.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'run_update') {
          setRuns(prev => {
            const idx = prev.findIndex(r => r.id === msg.data.id);
            if (idx === -1) return [msg.data, ...prev];
            const next = [...prev];
            next[idx] = msg.data;
            return next;
          });
        } else if (msg.type === 'event') {
          setEvents(prev => {
            const exists = prev.some(e => e.id === msg.data.id);
            if (exists) return prev;
            return [msg.data, ...prev].slice(0, 50);
          });
        }
      };
      socketRef.current.onclose = () => setTimeout(connectWs, 3000);
    };

    connectWs();
    return () => {
      clearInterval(interval);
      socketRef.current?.close();
    };
  }, []);

  const handleCreatePlan = async () => {
    if (!intent.trim() || loading) return;
    setLoading(true);
    
    try {
      const response = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: `
          You are the Quantum UACP Deterministic Orchestrator. 
          Translate natural language intent into a hybrid quantum-classical orchestration plan.
          
          Intent: "${intent}"
          
          Return ONLY a JSON object:
          {
            "name": "Concise identifier",
            "graph": {
              "nodes": [
                { "id": "NODE_ID", "type": "quantum|classical", "description": "Specific action", "policy_tag": "AC-10", "entropy": 0.4 }
              ],
              "edges": [{ "from": "NODE_ID", "to": "NODE_ID" }]
            }
          }
        `,
        config: {
          responseMimeType: "application/json"
        }
      });

      const planData = JSON.parse(response.text || "{}");
      
      const res = await fetch("/api/plans", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...planData, intent })
      });
      if (!res.ok) throw new Error("Failed to save plan");
      const savedPlan = await res.json();
      setPlans(prev => [savedPlan, ...prev]);
      setIntent("");
      setActiveTab('execution');
    } catch (error) {
      console.error("Compilation error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRun = async (planId: string) => {
    try {
      const res = await fetch("/api/runs", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ planId })
      });
      const newRun = await res.json();
      setRuns(prev => [newRun, ...prev]);
      setActiveTab('ops');
    } catch (error) {
      console.error("Run error:", error);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#050505] text-[#e0e0e0] font-sans selection:bg-blue-500/30 overflow-hidden relative">
      <div className="absolute inset-0 scanner pointer-events-none z-0 opacity-50" />
      
      {/* Header Navigation */}
      <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-[#0a0a0a] z-50 shadow-2xl relative">
        <div className="flex items-center gap-6">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 via-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-500/20 group cursor-pointer overflow-hidden relative">
            <motion.div 
              className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            />
            <Zap size={16} className="text-white fill-current relative z-10" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif italic text-xl tracking-tight leading-none text-white/90">The Deterministic Engine</span>
            <span className="text-[8px] font-mono tracking-[0.4em] uppercase text-blue-400/60 mt-1">UACP Control Plane v0.2.0</span>
          </div>
        </div>
        
        <nav className="flex items-center gap-12 text-[10px] uppercase tracking-[0.25em] font-bold text-white/40">
          <TabButton active={activeTab === 'intent'} onClick={() => setActiveTab('intent')} label="Signal Feed" />
          <TabButton active={activeTab === 'execution'} onClick={() => setActiveTab('execution')} label="Probability Matrix" />
          <TabButton active={activeTab === 'ops'} onClick={() => setActiveTab('ops')} label="Deterministic Ops" />
          
          <div className="h-8 w-px bg-white/5 mx-2" />
          
          <div className="flex items-center gap-3 px-4 py-1.5 border border-white/10 rounded-full bg-white/5 backdrop-blur-sm group cursor-help">
            <ShieldCheck size={12} className="text-blue-400" />
            <span className="text-[9px] font-mono lowercase tracking-normal text-white/60">Node: Gemini Pro Integrated</span>
            <ArrowUpRight size={10} className="text-white/20 group-hover:text-blue-400 transition-colors" />
          </div>
        </nav>
      </header>

      {/* Main Content Workspace */}
      <main className="flex-1 grid grid-cols-12 gap-1 p-1 bg-white/5 overflow-hidden">
        
        {/* Left Column: Research Signals & Event Log */}
        <section className="col-span-3 bg-[#0a0a0a] flex flex-col border border-white/5 overflow-hidden glass-panel">
          <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
            <h2 className="text-[10px] uppercase tracking-[0.2em] text-blue-400 font-bold mb-1 flex items-center gap-2">
              <Search size={10} />
              Signal Ingestion Feed
            </h2>
            <p className="text-[10px] text-white/30 italic">Continuous scanning of SSRN research nodes</p>
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar p-1 pb-24">
            <div className="space-y-px">
              {ssrnData.map((sig) => (
                <div key={sig.id} className="p-4 bg-white/[0.01] hover:bg-white/[0.03] transition-colors border-b border-white/[0.03] last:border-0 group cursor-default">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[9px] font-mono text-blue-400/80 tracking-tighter uppercase">{sig.id}</span>
                    <span className="text-[9px] text-white/20 font-mono">{sig.category}</span>
                  </div>
                  <h3 className="text-xs text-white/80 font-light leading-snug group-hover:text-white transition-colors">{sig.title}</h3>
                  <div className="mt-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-blue-500 animate-pulse" />
                      <span className="text-[8px] font-mono text-white/30 tracking-widest uppercase">Match Strength</span>
                    </div>
                    <span className="text-[10px] font-mono text-green-500/80">{sig.strength}%</span>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="p-6 border-t border-white/5 mt-4">
              <h3 className="text-[9px] uppercase tracking-widest text-white/20 font-bold mb-4">Event Sequence Log</h3>
              <div className="space-y-3">
                {events.slice(0, 8).map((ev) => (
                  <div key={ev.id} className="flex gap-3 items-start group">
                    <div className="mt-1 w-1.5 h-1.5 rounded-full border border-white/20 group-hover:border-blue-400 transition-colors shrink-0" />
                    <div className="flex flex-col gap-0.5" title={ev.message}>
                      <span className="text-[9px] text-white/80 font-mono tracking-tighter leading-none">{ev.type}</span>
                      <span className="text-[9px] text-white/30 italic truncate max-w-[180px]">{ev.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="p-6 border-t border-white/5 bg-black/40">
            <div className="flex justify-between items-center text-[10px] mb-3 text-white/40 uppercase font-mono tracking-tighter">
              <span>Policy Evaluation</span>
              <span className="text-blue-400">Gopher v4.1</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden relative">
              <motion.div 
                className="h-full bg-gradient-to-r from-blue-600 to-purple-600"
                animate={{ width: `${(signals?.gopher_policy_alignment || 0.95) * 100}%` }}
              />
            </div>
            <p className="mt-3 text-[9px] text-white/20 italic leading-relaxed">
              "Deterministic constraints verified against policy family AC-10."
            </p>
          </div>
        </section>

        {/* Center Panel: Hero Interaction Surface */}
        <section className="col-span-6 flex flex-col bg-[#080808] border border-white/5 overflow-hidden technical-grid relative">
          <AnimatePresence mode="wait">
            {activeTab === 'intent' && (
              <motion.div 
                key="intent"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-12 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-12">
                  <div className="space-y-4">
                    <span className="text-[10px] uppercase tracking-[0.4em] text-white/20 font-mono">Input Deterministic Strategy</span>
                    <h1 className="font-serif italic text-5xl text-white/90 leading-tight">
                      "Probability is merely the shadow of a hidden order."
                    </h1>
                  </div>

                  <div className="w-full relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-indigo-500/10 rounded-xl blur-xl opacity-0 group-focus-within:opacity-100 transition duration-1000" />
                    <div className="relative glass-panel rounded-xl overflow-hidden border border-white/10 shadow-2xl">
                      <textarea 
                        className="w-full h-48 bg-black/80 p-8 text-xl font-light italic text-white/90 placeholder:text-white/10 focus:outline-none resize-none transition-all focus:bg-black relative z-20"
                        placeholder="State your orchestration intent..."
                        value={intent}
                        onChange={(e) => setIntent(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleCreatePlan();
                          }
                        }}
                        autoFocus
                      />
                      
                      {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/90 backdrop-blur-md z-50">
                          <div className="flex flex-col items-center gap-6">
                            <div className="relative">
                              <motion.div 
                                className="w-16 h-16 rounded-full border-2 border-t-blue-500 border-r-transparent border-b-purple-500 border-l-transparent" 
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                              />
                            </div>
                            <div className="space-y-2 text-center">
                              <span className="text-[11px] font-mono tracking-[0.3em] text-blue-400 block uppercase">Analyzing Complexity</span>
                              <span className="text-[9px] font-mono text-white/30 uppercase">Negotiating with Gemini Core Matrix...</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <button 
                    disabled={loading || !intent.trim()}
                    onClick={handleCreatePlan}
                    className="w-full max-w-sm py-5 bg-white text-black text-[12px] uppercase tracking-[0.5em] font-black hover:bg-blue-600 hover:text-white transition-all disabled:opacity-10 group active:scale-[0.98] shadow-[0_20px_50px_rgba(255,255,255,0.1)] hover:shadow-blue-500/40"
                  >
                    <span className="flex items-center justify-center gap-4">
                      SEND SIGNAL / EXECUTE
                      <ChevronRight size={16} className="group-hover:translate-x-2 transition-transform" />
                    </span>
                  </button>
                  <p className="text-[9px] uppercase tracking-[0.4em] text-white/10 font-mono">Press [Enter] to transmit</p>
                </div>

                <div className="mt-auto flex justify-between items-end border-t border-white/5 pt-6 text-[9px] uppercase tracking-[0.2em] font-mono text-white/20">
                  <div className="space-y-1">
                    <div>Station: CONTROL_PLANE_ALPHA</div>
                    <div>Identity: {identity}</div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="text-3xl font-serif italic text-white/70">0.0000001%</div>
                    <div>Acceptable Non-Deterministic Entropy</div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'execution' && (
              <motion.div 
                key="execution"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-8 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                   <div className="space-y-1">
                    <h2 className="font-serif italic text-3xl text-white/90">Probability Matrix</h2>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold">Plan Hierarchy Revision 1.0.4</p>
                   </div>
                   <div className="flex gap-4">
                     {plans.length > 0 && (
                       <div className="px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-md flex items-center gap-3">
                         <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                         <span className="text-[9px] font-mono text-blue-200 uppercase tracking-widest">Directive: {plans[0].name}</span>
                       </div>
                     )}
                     <button className="text-[10px] font-mono text-white/50 hover:text-blue-400 transition-colors px-4 py-2 border border-white/10 rounded uppercase tracking-widest">
                      Export Schema
                     </button>
                   </div>
                </div>

                {plans.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8 p-4 bg-white/[0.02] border border-white/5 rounded-lg backdrop-blur-sm"
                  >
                    <div className="flex items-start gap-4">
                      <div className="mt-1 p-1.5 bg-blue-500/10 rounded text-blue-400">
                        <Info size={14} />
                      </div>
                      <div className="flex-1">
                        <span className="text-[9px] font-mono text-white/20 uppercase tracking-widest block mb-1">Strategic Briefing</span>
                        <p className="text-xs text-white/60 leading-relaxed italic">
                          "{plans[0].intent}" — Sequence initialized with {plans[0].graph?.nodes?.length || 0} nodes. 
                          Anticipated deterministic yield is 99.9%. Policy markers AC-10 and AC-GLOBAL applied to all transition states.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div className="flex-1 flex items-center justify-center overflow-auto custom-scrollbar p-12">
                   {plans.length > 0 ? (
                     <div className="flex items-center gap-12 relative animate-in fade-in duration-700">
                        {plans[0].graph?.nodes?.map((node: any, idx: number) => (
                          <div key={`${node.id}-${idx}`} className="relative group shrink-0">
                            <motion.div 
                              initial={{ y: 20, opacity: 0 }}
                              animate={{ y: 0, opacity: 1 }}
                              transition={{ delay: idx * 0.1 }}
                              whileHover={{ scale: 1.05 }}
                              className="w-64 p-8 glass-panel rounded-lg shadow-2xl relative z-10 hover:border-blue-500/50 transition-all border-white/10 group-hover:shadow-blue-500/20 backdrop-blur-xl group cursor-crosshair"
                            >
                               {/* Quantum Shimmer Effect */}
                               <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                               
                               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white/5 to-transparent" />
                               <div className="flex justify-between items-start mb-6">
                                  <div className="p-2.5 bg-white/5 rounded-lg border border-white/10 group-hover:bg-blue-500/20 transition-colors">
                                    {node.type === 'quantum' ? <Cpu size={16} className="text-purple-400" /> : <Database size={16} className="text-blue-400" />}
                                  </div>
                                  <div className="text-right">
                                    <span className="text-[8px] font-mono text-white/20 block uppercase tracking-tighter">Policy_Tag</span>
                                    <span className="text-[9px] font-mono text-blue-400 flex items-center gap-1">
                                      <Lock size={8} />
                                      {node.policy_tag || 'AC-GLOBAL'}
                                    </span>
                                  </div>
                               </div>
                               
                               <div className="text-sm font-mono font-black text-white/95 uppercase tracking-tight mb-3 flex items-center gap-2">
                                 {node.id}
                                 <motion.div 
                                   animate={{ opacity: [0.2, 1, 0.2] }} 
                                   transition={{ repeat: Infinity, duration: 2 }}
                                   className="w-1 h-1 rounded-full bg-blue-400" 
                                 />
                               </div>
                               
                               <div className="text-xs text-white/50 leading-relaxed font-light italic h-16 overflow-hidden mb-6 group-hover:text-white/80 transition-colors">
                                 {node.description}
                                </div>
                               
                               <div className="flex items-center justify-between pt-5 border-t border-white/5">
                                  <div className="flex items-center gap-2">
                                     <div className="w-1.5 h-1.5 rounded-sm bg-blue-500 group-hover:animate-spin" />
                                     <span className="text-[9px] font-mono text-white/30 uppercase tracking-[0.2em]">Entropy: {node.entropy || '0.22'}</span>
                                  </div>
                                  <ArrowUpRight size={12} className="text-white/10 group-hover:text-white transition-all transform group-hover:translate-x-1 group-hover:-translate-y-1" />
                               </div>

                               {/* Position Indicators */}
                               <div className="absolute -bottom-2 -left-2 text-[7px] font-mono text-white/10 opacity-0 group-hover:opacity-100 transition-opacity">
                                 X: {idx.toFixed(2)} Y: 0.00
                               </div>
                            </motion.div>
                            
                            {/* Connector Lines with Flow Effect */}
                            {idx < plans[0].graph.nodes.length - 1 && (
                              <div className="absolute top-1/2 -right-12 w-12 h-px z-0">
                                <div className="absolute inset-0 bg-white/10" />
                                <motion.div 
                                  animate={{ x: [-12, 48], opacity: [0, 1, 0] }}
                                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                  className="w-4 h-full bg-blue-400 blur-sm"
                                />
                              </div>
                            )}
                          </div>
                        ))}
                     </div>
                   ) : (
                     <div className="flex flex-col items-center gap-6 opacity-30">
                        <Layers size={48} className="animate-pulse" />
                        <span className="font-serif italic text-lg">No deterministic plans compiled.</span>
                     </div>
                   )}
                </div>

                <div className="mt-auto pt-12 flex justify-center">
                  {plans.length > 0 && (
                    <button 
                      onClick={() => handleStartRun(plans[0].id)}
                      className="px-12 py-3 border border-white/10 text-[10px] uppercase font-bold tracking-[0.4em] hover:bg-white hover:text-black transition-all shadow-xl active:scale-95"
                    >
                      Commit Sequence to Control Plane
                    </button>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === 'ops' && (
              <motion.div 
                key="ops"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-12 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex justify-between items-end mb-12 border-b border-white/5 pb-6">
                   <div className="space-y-1">
                    <h2 className="font-serif italic text-3xl text-white/90">Archives of Order</h2>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold">Live Execution Telemetry</p>
                   </div>
                   <div className="flex items-center gap-4 text-right">
                    <div className="flex flex-col">
                      <span className="text-[8px] font-mono text-white/30">Latency</span>
                      <span className="text-xs font-mono text-blue-400">{signals?.classical_latency?.toFixed(1) || '0'}ms</span>
                    </div>
                    <div className="h-8 w-px bg-white/5" />
                    <div className="flex flex-col">
                      <span className="text-[8px] font-mono text-white/30">Coherence</span>
                      <span className="text-xs font-mono text-purple-400">{signals?.quantum_coherence?.toFixed(1) || '0'}%</span>
                    </div>
                   </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-8 pr-6">
                   {runs.map((run) => (
                     <div key={run.id} className="glass-panel p-8 relative overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-20 group-hover:opacity-100 transition-opacity" />
                        
                        <div className="flex justify-between items-start mb-8">
                          <div className="space-y-2">
                             <div className="flex items-center gap-4">
                                <span className="font-mono text-xs font-bold text-white tracking-widest">{run.id}</span>
                                <span className={`text-[9px] px-2 py-0.5 border rounded-full uppercase tracking-widest font-bold ${run.status === 'completed' ? 'border-green-500/20 text-green-500 bg-green-500/5' : 'border-blue-500/20 text-blue-400 bg-blue-500/5'}`}>
                                  {run.status.toUpperCase()}
                                </span>
                             </div>
                             <p className="text-[10px] text-white/40 font-mono italic">Compiled Reference: {run.planId}</p>
                          </div>
                          <div className="text-right">
                             <div className="text-4xl font-serif italic text-white/90 tabular-nums">{run.progress}%</div>
                          </div>
                        </div>

                         <div className="space-y-4">
                           <div className="flex justify-between text-[10px] font-mono uppercase tracking-[0.2em] text-white/40">
                              <span className="flex items-center gap-2">
                                <Disc size={10} className={run.status === 'completed' ? '' : 'animate-spin'} />
                                Active Phase: {run.currentStep}
                              </span>
                              <span>TS INITIATION: {new Date(run.startTime).toLocaleTimeString()}</span>
                           </div>
                           <div className="w-full h-2 bg-white/5 overflow-hidden relative rounded-full">
                              <motion.div 
                                className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 shadow-[0_0_15px_rgba(59,130,246,0.6)]"
                                animate={{ width: `${run.progress}%` }}
                              />
                              <motion.div 
                                animate={{ x: ['0%', '100%'], opacity: [0, 1, 0] }}
                                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                                className="absolute top-0 bottom-0 w-20 bg-white/20 skew-x-12"
                              />
                           </div>
                           
                           {/* Step Micro-Labels */}
                           <div className="flex justify-between mt-2 overflow-hidden">
                              {plans.find(p => p.id === run.planId)?.graph.nodes.map((node, nIdx) => (
                                <div key={`${node.id}-${nIdx}`} className="flex flex-col items-center gap-1 opacity-20 hover:opacity-100 transition-opacity cursor-default">
                                  <div className={`w-1 h-1 rounded-full ${nIdx / (plans.find(p => p.id === run.planId)?.graph.nodes.length || 1) * 100 <= run.progress ? 'bg-blue-400' : 'bg-white/40'}`} />
                                  <span className="text-[7px] font-mono uppercase tracking-tighter">{node.id}</span>
                                </div>
                              ))}
                           </div>
                        </div>

                        {run.status === 'completed' && run.output && (
                           <motion.div 
                             initial={{ opacity: 0, y: 10 }}
                             animate={{ opacity: 1, y: 0 }}
                             className="mt-8 p-6 bg-blue-500/5 border border-blue-500/10 rounded-lg relative overflow-hidden"
                           >
                              <div className="absolute top-0 right-0 p-2 text-blue-500/20">
                                <Activity size={40} className="opacity-10" />
                              </div>
                              <div className="flex gap-4 relative z-10">
                                 <div className="shrink-0 p-2 bg-blue-500/10 rounded text-blue-400 h-fit">
                                   <BrainCircuit size={16} />
                                 </div>
                                 <div className="space-y-1">
                                   <span className="text-[9px] font-mono text-blue-300 uppercase tracking-widest block">Deterministic Outcome Report</span>
                                   <p className="text-xs text-white/70 leading-relaxed font-light italic">
                                     {run.output}
                                   </p>
                                 </div>
                              </div>
                           </motion.div>
                        )}
                     </div>
                   ))}
                   
                   {runs.length === 0 && (
                     <div className="h-full flex flex-col items-center justify-center opacity-20 space-y-6">
                        <Lock size={48} />
                        <span className="font-serif italic text-xl">Operational plane locked. Initialize plan to unlock.</span>
                     </div>
                   )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Right Column: Convergence Telemetry */}
        <section className="col-span-3 bg-[#0a0a0a] flex flex-col border border-white/5 overflow-hidden glass-panel">
           <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
              <h2 className="text-[10px] uppercase tracking-[0.2em] text-purple-400 font-bold mb-1 flex items-center gap-2">
                <Activity size={10} />
                Asset Convergence
              </h2>
              <p className="text-[10px] text-white/30 italic">Real-time heuristics & deterministic alpha</p>
           </div>
           
           <div className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-24 space-y-10">
              {signals?.market_convergence?.map((m: any, idx: number) => (
                <ConvergenceBar 
                  key={`${m.label}-${idx}`}
                  label={m.label} 
                  value={m.value} 
                  progress={Math.abs(parseFloat(m.value)) / 10} 
                  color={idx % 2 === 0 ? "blue" : "purple"} 
                />
              ))}
              
              {!signals?.market_convergence && (
                <>
                  <ConvergenceBar 
                    label="Deterministic Alpha" 
                    value={"+14.2%"} 
                    progress={0.72} 
                    color="blue" 
                  />
                  <ConvergenceBar 
                    label="Market Heuristics" 
                    value={"+8.7%"} 
                    progress={0.58} 
                    color="purple" 
                  />
                </>
              )}
              
              <div className="pt-8 border-t border-white/5 space-y-6">
                <h3 className="text-[9px] uppercase tracking-widest text-white/20 font-bold">Observability Signals</h3>
                {signals?.horowitz_signals?.map((sig: any, sIdx: number) => (
                  <div key={`${sig.id}-${sIdx}`} className="space-y-4">
                    <div className="flex justify-between items-end">
                      <div className="flex flex-col">
                        <span className="text-[9px] font-mono text-white/40 uppercase tracking-tighter">{sig.id}</span>
                        <span className="text-xs font-serif italic text-white/80">Value Trace</span>
                      </div>
                      <span className={`text-[9px] font-mono uppercase font-bold ${sig.trend === 'rising' ? 'text-green-500' : 'text-blue-400'}`}>{sig.trend}</span>
                    </div>
                    
                    <div className="h-16 w-full opacity-50 overflow-hidden grayscale hover:grayscale-0 transition-all duration-700">
                       <ResponsiveContainer width="100%" height="100%" minHeight={60} minWidth={100}>
                          <AreaChart data={Array.from({length: 20}, () => ({ val: Math.random() }))}>
                            <defs>
                              <linearGradient id={`grad-${sig.id}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={sig.trend === 'rising' ? "#10b981" : "#3b82f6"} stopOpacity={0.3}/>
                                <stop offset="95%" stopColor={sig.trend === 'rising' ? "#10b981" : "#3b82f6"} stopOpacity={0}/>
                              </linearGradient>
                            </defs>
                            <Area type="monotone" dataKey="val" stroke={sig.trend === 'rising' ? "#10b981" : "#3b82f6"} fillOpacity={1} fill={`url(#grad-${sig.id})`} />
                          </AreaChart>
                       </ResponsiveContainer>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-5 glass-panel rounded border-white/5 bg-white/[0.01] mt-8">
                 <h3 className="text-[9px] uppercase tracking-widest text-white/30 font-bold mb-4 flex items-center gap-2">
                   <Info size={10} className="text-blue-400" />
                   Agent Consensus
                 </h3>
                 <div className="text-xs text-white/60 italic leading-relaxed font-light">
                  "My strategy is grounded in the great agent Gemini. The signals converge on a singular outcome."
                 </div>
                 <div className="mt-4 flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-blue-500/10 flex items-center justify-center text-[8px] text-blue-400 italic">g</div>
                    <span className="text-[8px] font-mono text-white/20 uppercase tracking-widest">— GEMINI CORE MATRIX</span>
                 </div>
              </div>
           </div>

           <div className="p-8 border-t border-white/5 bg-black/40">
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center text-[9px] font-mono text-white/20 uppercase tracking-widest">
                  <span>Certainty Index</span>
                  <span className="text-white text-sm font-serif italic">0.9999</span>
                </div>
                <div className="h-[2px] w-full bg-white/5 relative overflow-hidden">
                  <motion.div 
                    className="absolute inset-0 bg-blue-500/40"
                    animate={{ x: [-100, 400] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                  />
                  <div className="absolute right-0 top-0 h-full bg-blue-400 shadow-[0_0_10px_rgba(59,130,246,1)]" style={{ width: '0.1%' }} />
                </div>
              </div>
           </div>
        </section>
      </main>

      {/* Footer Status Bar */}
      <footer className="h-8 bg-[#050505] border-t border-white/10 flex items-center justify-between px-8 text-[9px] uppercase tracking-[0.3em] text-white/30 font-mono z-50">
        <div className="flex gap-10">
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]"></span> 
            Uplink Established
          </span>
          <span className="flex items-center gap-2">
            <Activity size={10} className="text-blue-500/50" />
            Control Plane: Stable
          </span>
          <span className="flex items-center gap-2">
            <Cpu size={10} className="text-purple-500/50" />
            Determinism Ratio: 1.0
          </span>
        </div>
        <div className="flex gap-6 items-center">
          <span>AI Studio Build 2026.05.06</span>
          <div className="h-3 w-px bg-white/10" />
          <span>© DETERMINISTIC RESEARCH • UNIVERSAL CONTROL PROTOTYPE</span>
        </div>
      </footer>
    </div>
  );
}

function TabButton({ active, onClick, label }: { active: boolean, onClick: () => void, label: string }) {
  return (
    <button 
      onClick={onClick}
      className={`relative py-1 transition-all group outline-none ${active ? 'text-white' : 'text-white/40 hover:text-white/70'}`}
    >
      {label}
      {active && (
        <motion.div 
          layoutId="tab"
          className="absolute -bottom-1 left-0 right-0 h-[2px] bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]"
        />
      )}
    </button>
  );
}

function ConvergenceBar({ label, value, progress, color }: { label: string, value: string, progress: number, color: 'blue' | 'purple' }) {
  return (
    <div className="group cursor-default">
      <div className="flex justify-between items-end mb-3">
        <span className="text-[10px] text-white/40 italic font-light tracking-wide group-hover:text-white/60 transition-colors">{label}</span>
        <span className="text-green-400 font-mono font-bold tracking-tighter text-xs">{value}</span>
      </div>
      <div className="h-10 w-full glass-panel overflow-hidden relative group-hover:border-white/10 transition-colors bg-white/[0.01]">
         <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${progress * 100}%` }}
            className={`absolute bottom-0 left-0 h-full ${color === 'blue' ? 'bg-blue-500/10' : 'bg-purple-500/10'}`}
         />
         <div className="absolute inset-0 flex items-center px-4 overflow-hidden">
            <div className="w-full flex gap-0.5 opacity-10">
               {[...Array(40)].map((_, i) => (
                 <div key={i} className="flex-1 h-3 border-r border-white/20 last:border-0" />
               ))}
            </div>
         </div>
         <motion.div 
            initial={{ x: -200 }}
            animate={{ x: 400 }}
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            className={`absolute top-0 w-32 h-[1px] ${color === 'blue' ? 'bg-blue-400/50' : 'bg-purple-400/50'} blur-sm`}
         />
      </div>
    </div>
  );
}
