// @ts-nocheck
import React, { useState } from 'react';
import { 
  GitMerge, Clock, Coins, ShieldAlert, CheckCircle2, AlertCircle, ArrowRight,
  TrendingUp, Terminal, Filter, HelpCircle, Server, Activity, Users, Layers, ShieldCheck
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface DecisionFrame {
  id: string;
  task_name: string;
  model_used: string;
  provider_used: string;
  latency: number;
  cost: number;
  fallback_used: string;
  policy_result: string;
  audit_hash: string;
}

interface RoutingPathFlowProps {
  history: DecisionFrame[];
}

export const RoutingPathFlow: React.FC<RoutingPathFlowProps> = ({ history }) => {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredLink, setHoveredLink] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sankey' | 'timeline'>('sankey');

  // Helper classification for dynamic calculations
  const classifyTask = (taskName: string): string => {
    const name = taskName.toLowerCase();
    if (name.includes('telemetry') || name.includes('sensor') || name.includes('hydraulic') || name.includes('pump') || name.includes('grid')) {
      return 'Telemetry Ingestion';
    }
    if (name.includes('audit') || name.includes('compliance') || name.includes('patient') || name.includes('secure') || name.includes('privacy')) {
      return 'Compliance Audit';
    }
    if (name.includes('vision') || name.includes('image') || name.includes('camera') || name.includes('scan')) {
      return 'Visual Sensory Feed';
    }
    if (name.includes('optimize') || name.includes('deep') || name.includes('synthesize') || name.includes('reason') || name.includes('heavy')) {
      return 'Cognitive Reasoning';
    }
    return 'Ad-Hoc Workload';
  };

  // Define Nodes for Sankey diagram
  // Columns:
  // Col 0: Workload Types
  // Col 1: Broker Policy Layers
  // Col 2: Allocated Engines
  // Col 3: Safe Outcome Pillars
  const nodes = [
    // Column 0
    { id: 'src_telemetry', label: 'Telemetry Ingestion', col: 0, color: 'text-cyan-400', border: 'border-cyan-500/30', bg: 'bg-cyan-500/10' },
    { id: 'src_compliance', label: 'Compliance Audit', col: 0, color: 'text-purple-400', border: 'border-purple-500/30', bg: 'bg-purple-500/10' },
    { id: 'src_vision', label: 'Visual Sensory Feed', col: 0, color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
    { id: 'src_reasoning', label: 'Cognitive Reasoning', col: 0, color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
    { id: 'src_adhoc', label: 'Ad-Hoc Workload', col: 0, color: 'text-slate-400', border: 'border-slate-500/20', bg: 'bg-slate-500/10' },

    // Column 1
    { id: 'gate_policy', label: 'Privacy & Policy Guard', col: 1, color: 'text-indigo-400', border: 'border-indigo-500/30', bg: 'bg-indigo-500/10' },
    { id: 'gate_fallback', label: 'Tenant Override Handler', col: 1, color: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/10' },
    { id: 'gate_load', label: 'Cognitive Router', col: 1, color: 'text-cyan-400', border: 'border-cyan-500/30', bg: 'bg-cyan-500/10' },

    // Column 2
    { id: 'core_google', label: 'Google Gemini', col: 2, color: 'text-sky-400', border: 'border-sky-500/30', bg: 'bg-sky-500/10' },
    { id: 'core_anthropic', label: 'Anthropic Claude', col: 2, color: 'text-rose-400', border: 'border-rose-500/30', bg: 'bg-rose-500/10' },
    { id: 'core_openai', label: 'OpenAI GPT-Core', col: 2, color: 'text-green-400', border: 'border-green-500/30', bg: 'bg-green-500/10' },
    { id: 'core_groq', label: 'Groq (Inference-Low)', col: 2, color: 'text-orange-400', border: 'border-orange-500/30', bg: 'bg-orange-500/10' },
    { id: 'core_ollama', label: 'Ollama (Local Private)', col: 2, color: 'text-zinc-400', border: 'border-zinc-500/30', bg: 'bg-zinc-500/10' },

    // Column 3
    { id: 'out_direct', label: 'Direct Standard Output', col: 3, color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
    { id: 'out_fallback', label: 'Bypassed Fallback Path', col: 3, color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  ];

  // Dynamic layout calculations
  const colX = [40, 275, 520, 760]; // horizontal positions of columns
  const svgWidth = 800;
  const svgHeight = 440;

  // Node placements heights/offsets
  const nodeYOffsets: { [key: string]: number } = {
    // Column 0
    src_telemetry: 30,
    src_compliance: 110,
    src_vision: 190,
    src_reasoning: 270,
    src_adhoc: 350,

    // Column 1
    gate_policy: 60,
    gate_fallback: 190,
    gate_load: 320,

    // Column 2
    core_google: 30,
    core_anthropic: 110,
    core_openai: 190,
    core_groq: 270,
    core_ollama: 350,

    // Column 3
    out_direct: 110,
    out_fallback: 270,
  };

  // Node dimensions
  const nodeWidth = 140;
  const nodeHeight = 42;

  // Compile Links based on active historical transactions
  interface SankeyLink {
    id: string;
    source: string;
    target: string;
    color: string;
    label: string;
    transactions: DecisionFrame[];
    totalCost: number;
    avgLatency: number;
  }

  const compileSankeyFlows = (): SankeyLink[] => {
    const linksMap: { [key: string]: SankeyLink } = {};

    // Initial links configuration
    const addLinkMetric = (linkKey: string, sourceId: string, targetId: string, color: string, label: string, tx: DecisionFrame) => {
      if (!linksMap[linkKey]) {
        linksMap[linkKey] = {
          id: linkKey,
          source: sourceId,
          target: targetId,
          color,
          label,
          transactions: [],
          totalCost: 0,
          avgLatency: 0,
        };
      }
      linksMap[linkKey].transactions.push(tx);
      linksMap[linkKey].totalCost += tx.cost;
      linksMap[linkKey].avgLatency += tx.latency;
    };

    history.forEach(tx => {
      // 1. Map Task Category -> Gate
      const taskCategory = classifyTask(tx.task_name);
      let col0Node = 'src_adhoc';
      let link0Color = 'stroke-slate-500/20';

      if (taskCategory === 'Telemetry Ingestion') { col0Node = 'src_telemetry'; link0Color = 'stroke-cyan-500/20'; }
      else if (taskCategory === 'Compliance Audit') { col0Node = 'src_compliance'; link0Color = 'stroke-purple-500/20'; }
      else if (taskCategory === 'Visual Sensory Feed') { col0Node = 'src_vision'; link0Color = 'stroke-amber-500/20'; }
      else if (taskCategory === 'Cognitive Reasoning') { col0Node = 'src_reasoning'; link0Color = 'stroke-emerald-500/20'; }

      // Router state routing to gates
      let col1Node = 'gate_load';
      if (tx.fallback_used === 'yes') {
        col1Node = 'gate_fallback';
      } else if (tx.policy_result.toLowerCase().includes('override') || tx.policy_result.toLowerCase().includes('sensitive')) {
        col1Node = 'gate_policy';
      }

      const key01 = `${col0Node}->${col1Node}`;
      addLinkMetric(key01, col0Node, col1Node, link0Color, taskCategory, tx);

      // 2. Map Gate -> Dedicated Core Node
      let col2Node = 'core_google';
      let link1Color = 'stroke-sky-500/20';

      const prov = (tx.provider_used || '').toLowerCase();
      const model = (tx.model_used || '').toLowerCase();

      if (prov.includes('google')) { col2Node = 'core_google'; link1Color = 'stroke-sky-500/20'; }
      else if (prov.includes('anthropic') || model.includes('claude')) { col2Node = 'core_anthropic'; link1Color = 'stroke-rose-500/20'; }
      else if (prov.includes('openai') || model.includes('gpt')) { col2Node = 'core_openai'; link1Color = 'stroke-green-500/20'; }
      else if (prov.includes('groq')) { col2Node = 'core_groq'; link1Color = 'stroke-orange-500/20'; }
      else if (prov.includes('ollama') || model.includes('llama3.2')) { col2Node = 'core_ollama'; link1Color = 'stroke-slate-400/20'; }

      const key12 = `${col1Node}->${col2Node}`;
      addLinkMetric(key12, col1Node, col2Node, link1Color, `Routing through ${nodes.find(n => n.id === col1Node)?.label}`, tx);

      // 3. Map Core Node -> Final Outcome
      const col3Node = tx.fallback_used === 'yes' ? 'out_fallback' : 'out_direct';
      const link2Color = col3Node === 'out_fallback' ? 'stroke-amber-500/20' : 'stroke-emerald-500/20';
      const key23 = `${col2Node}->${col3Node}`;
      addLinkMetric(key23, col2Node, col3Node, link2Color, `Outcome: ${nodes.find(n => n.id === col3Node)?.label}`, tx);
    });

    // Finalize averages and parameters
    return Object.values(linksMap).map(link => ({
      ...link,
      avgLatency: Math.round(link.avgLatency / link.transactions.length),
    }));
  };

  const activeLinks = compileSankeyFlows();

  // Draw smooth Bezier curve for Sankey paths
  const calculateBezierPath = (sourceId: string, targetId: string) => {
    const sNode = nodes.find(n => n.id === sourceId);
    const tNode = nodes.find(n => n.id === targetId);
    if (!sNode || !tNode) return '';

    const x1 = colX[sNode.col] + nodeWidth;
    const y1 = nodeYOffsets[sourceId] + nodeHeight / 2;
    const x2 = colX[tNode.col];
    const y2 = nodeYOffsets[targetId] + nodeHeight / 2;

    const dx = Math.abs(x2 - x1) / 2;
    return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
  };

  // Determine if a link or node is highlighted
  const isLinkActive = (link: SankeyLink) => {
    if (hoveredLink && hoveredLink === link.id) return true;
    if (hoveredNode) {
      return link.source === hoveredNode || link.target === hoveredNode;
    }
    return false;
  };

  // Compute stats
  const totalVolume = history.length;
  const avgLatency = totalVolume > 0 ? Math.round(history.reduce((a, b) => a + b.latency, 0) / totalVolume) : 0;
  const totalCost = history.reduce((a, b) => a + b.cost, 0);
  const fallbackCount = history.filter(h => h.fallback_used === 'yes').length;
  const fallbackPercent = totalVolume > 0 ? Math.round((fallbackCount / totalVolume) * 100) : 0;

  return (
    <div className="flex flex-col gap-6 h-full bg-[#0b1219]/70 border border-cyan-800/15 rounded-2xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] select-none">
      
      {/* HEADER SECTION WITH TOGGLE BUTTONS */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/5 pb-4 shrink-0">
        <div>
          <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-cyan-400 block">
            Multi-Model Workload Telemetry Flow
          </span>
          <h2 className="text-sm font-semibold text-white tracking-wider mt-0.5 uppercase">
            Model Routing Decision Visualizer
          </h2>
        </div>
        
        <div className="flex bg-[#050a0f] p-1 rounded-xl border border-white/5 font-mono">
          <button
            onClick={() => setActiveTab('sankey')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all ${
              activeTab === 'sankey'
                ? 'bg-cyan-500/10 border border-cyan-500/25 text-cyan-400'
                : 'text-white/40 hover:text-white/70 border border-transparent'
            }`}
          >
            <GitMerge size={11} />
            Sankey Node Network
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all ${
              activeTab === 'timeline'
                ? 'bg-cyan-500/10 border border-cyan-500/25 text-cyan-400'
                : 'text-white/40 hover:text-white/70 border border-transparent'
            }`}
          >
            <Clock size={11} />
            Timeline Cascade (FIFO)
          </button>
        </div>
      </div>

      {/* COMPREHENSIVE RUNTIME SUMMARY METRICS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#050a0f] border border-white/[0.03] p-3 rounded-xl">
          <div className="text-[7px] text-white/30 uppercase tracking-widest block font-mono font-bold">TOTAL DISPATCHED WORKLOADS</div>
          <div className="text-xl font-bold font-mono text-white mt-1 flex items-baseline gap-1.5">
            {totalVolume}
            <span className="text-[8px] font-normal text-slate-500">jobs</span>
          </div>
        </div>

        <div className="bg-[#050a0f] border border-white/[0.03] p-3 rounded-xl">
          <div className="text-[7px] text-white/30 uppercase tracking-widest block font-mono font-bold">AVERAGE COGNITIVE LATENCY</div>
          <div className="text-xl font-bold font-mono text-cyan-400 mt-1 flex items-baseline gap-1.5 animate-pulse">
            {avgLatency}
            <span className="text-[8.5px] font-normal text-cyan-500/70">ms</span>
          </div>
        </div>

        <div className="bg-[#050a0f] border border-white/[0.03] p-3 rounded-xl">
          <div className="text-[7px] text-white/30 uppercase tracking-widest block font-mono font-bold">ACCUMULATED CORES COST</div>
          <div className="text-xl font-bold font-mono text-green-400 mt-1 flex items-baseline gap-0.5">
            ${totalCost.toFixed(5)}
            <span className="text-[8px] font-normal text-emerald-600/70">USD</span>
          </div>
        </div>

        <div className="bg-[#050a0f] border border-white/[0.03] p-3 rounded-xl">
          <div className="text-[7px] text-white/30 uppercase tracking-widest block font-mono font-bold">FALLBACK ESCALATION RATE</div>
          <div className="text-xl font-bold font-mono text-yellow-500 mt-1 flex items-baseline gap-1">
            {fallbackPercent}%
            <span className="text-[8px] font-normal text-amber-600/70">
              ({fallbackCount} overrides)
            </span>
          </div>
        </div>
      </div>

      {/* CORE GRAPH INTERACTIVE CANVAS */}
      <div className="flex-1 bg-black/40 rounded-2xl border border-white/5 relative min-h-[380px] overflow-auto scrollbar-hide">
        
        <AnimatePresence mode="wait">
          {activeTab === 'sankey' ? (
            <motion.div
              key="sankey-tab"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              className="absolute inset-0 p-4 min-w-[800px] flex items-center justify-center"
            >
              <div className="relative w-[800px] h-[400px]">
                
                {/* SVG Connecting Links */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
                  <defs>
                    {/* Glowing Filters */}
                    <filter id="hyperglow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="3" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                  </defs>

                  {/* Draw Background Links */}
                  {activeLinks.map(link => {
                    const active = isLinkActive(link);
                    const widthFactor = Math.max(2, Math.min(18, link.transactions.length * 3.5));
                    const baseOpacity = 'opacity-30';
                    return (
                      <path
                        key={link.id}
                        d={calculateBezierPath(link.source, link.target)}
                        fill="none"
                        className={`transition-all duration-300 ${link.color} ${active ? 'opacity-90 stroke-cyan-400' : baseOpacity}`}
                        strokeWidth={widthFactor}
                        filter={active ? 'url(#hyperglow)' : undefined}
                      />
                    );
                  })}

                  {/* Flow Particles for active routes */}
                  {activeLinks.map((link, idx) => {
                    const widthFactor = Math.max(2, Math.min(18, link.transactions.length * 3.5));
                    return (
                      <path
                        key={`particle-${link.id}-${idx}`}
                        d={calculateBezierPath(link.source, link.target)}
                        fill="none"
                        stroke="rgba(34, 211, 238, 0.4)"
                        strokeWidth={Math.max(1, widthFactor / 4)}
                        strokeDasharray="6 20"
                        className="animate-[dash_6s_linear_infinite]"
                        style={{
                          animationDuration: `${Math.max(2, 6 - link.transactions.length)}s`
                        }}
                      />
                    );
                  })}
                </svg>

                {/* Nodes Layout */}
                {nodes.map(node => {
                  const nodeX = colX[node.col];
                  const nodeY = nodeYOffsets[node.id];
                  
                  // Filter transactions for this node which determines highlights
                  const nodeTransactions = history.filter(tx => {
                    const taskCategory = classifyTask(tx.task_name);
                    const prov = (tx.provider_used || '').toLowerCase();
                    const model = (tx.model_used || '').toLowerCase();

                    if (node.col === 0) {
                      if (node.id === 'src_telemetry' && taskCategory === 'Telemetry Ingestion') return true;
                      if (node.id === 'src_compliance' && taskCategory === 'Compliance Audit') return true;
                      if (node.id === 'src_vision' && taskCategory === 'Visual Sensory Feed') return true;
                      if (node.id === 'src_reasoning' && taskCategory === 'Cognitive Reasoning') return true;
                      if (node.id === 'src_adhoc' && taskCategory === 'Ad-Hoc Workload') return true;
                    } else if (node.col === 1) {
                      if (node.id === 'gate_fallback' && tx.fallback_used === 'yes') return true;
                      if (node.id === 'gate_policy' && tx.fallback_used !== 'yes' && (tx.policy_result.toLowerCase().includes('override') || tx.policy_result.toLowerCase().includes('sensitive'))) return true;
                      if (node.id === 'gate_load' && tx.fallback_used !== 'yes' && !(tx.policy_result.toLowerCase().includes('override') || tx.policy_result.toLowerCase().includes('sensitive'))) return true;
                    } else if (node.col === 2) {
                      if (node.id === 'core_google' && prov.includes('google')) return true;
                      if (node.id === 'core_anthropic' && (prov.includes('anthropic') || model.includes('claude'))) return true;
                      if (node.id === 'core_openai' && (prov.includes('openai') || model.includes('gpt'))) return true;
                      if (node.id === 'core_groq' && prov.includes('groq')) return true;
                      if (node.id === 'core_ollama' && (prov.includes('ollama') || model.includes('llama3.2'))) return true;
                    } else if (node.col === 3) {
                      if (node.id === 'out_fallback' && tx.fallback_used === 'yes') return true;
                      if (node.id === 'out_direct' && tx.fallback_used !== 'yes') return true;
                    }
                    return false;
                  });

                  const count = nodeTransactions.length;
                  const isHighlighted = hoveredNode === node.id || (hoveredLink && activeLinks.find(l => l.id === hoveredLink)?.source === node.id) || (hoveredLink && activeLinks.find(l => l.id === hoveredLink)?.target === node.id);

                  if (count === 0 && history.length > 0) {
                    // Invisible if no workloads traversed this node
                    return null;
                  }

                  return (
                    <div
                      key={node.id}
                      style={{
                        position: 'absolute',
                        left: `${nodeX}px`,
                        top: `${nodeY}px`,
                        width: `${nodeWidth}px`,
                        height: `${nodeHeight}px`,
                      }}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                      className={`z-10 rounded-xl border p-2 flex flex-col justify-between cursor-pointer transition-all duration-300 backdrop-blur-md ${node.border} ${node.bg} ${
                        isHighlighted 
                          ? 'border-cyan-400 shadow-[0_0_12px_rgba(34,197,94,0.15)] scale-[1.03] bg-cyan-950/20' 
                          : 'hover:scale-[1.02]'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className={`text-[8.5px] font-bold truncate tracking-wide block uppercase font-mono ${node.color}`}>
                          {node.label}
                        </span>
                        {node.col === 1 && <Filter size={9} className="text-white/30" />}
                        {node.col === 2 && <Server size={9} className="text-white/30" />}
                      </div>

                      <div className="flex justify-between items-center text-[7.5px] font-mono text-white/50 pt-1 border-t border-white/5 mt-0.5">
                        <span>Traffics:</span>
                        <span className="font-bold text-white">{count} ({totalVolume > 0 ? Math.round((count / totalVolume)*100) : 0}%)</span>
                      </div>
                    </div>
                  );
                })}

                {/* Draw Overlay details for hovered link */}
                <AnimatePresence>
                  {hoveredLink && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute bottom-2 left-1/2 transform -translate-x-1/2 bg-[#050a0f] border border-cyan-800/30 p-3 rounded-xl z-20 w-[420px] font-mono shadow-2xl backdrop-blur-lg grid grid-cols-2 gap-2 text-[9px]"
                    >
                      <div className="col-span-2 border-b border-white/5 pb-1 flex justify-between">
                        <span className="text-cyan-400 font-bold uppercase tracking-wider">
                          {activeLinks.find(l => l.id === hoveredLink)?.label} Overlay
                        </span>
                        <span className="text-white/40">{activeLinks.find(l => l.id === hoveredLink)?.transactions.length} Active Swarms</span>
                      </div>
                      <div>
                        <span className="text-white/30 block uppercase text-[7.5px]">Avg Latency:</span>
                        <span className="text-cyan-400 font-black">{activeLinks.find(l => l.id === hoveredLink)?.avgLatency}ms</span>
                      </div>
                      <div>
                        <span className="text-white/30 block uppercase text-[7.5px]">Incurred Expenses:</span>
                        <span className="text-green-400 font-black">${activeLinks.find(l => l.id === hoveredLink)?.totalCost.toFixed(6)}</span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Instructions overlays inside Sankey diagram columns */}
                <div className="absolute top-0 right-0 p-2 opacity-50 flex items-center gap-1 text-[7.5px] font-mono text-white/40 select-none">
                  <HelpCircle size={10} /> Hover on active nodes to inspect routing overlays
                </div>
                
                {/* Column Headers */}
                <div className="absolute -top-1 left-[40px] text-[7.5px] font-bold text-white/20 uppercase tracking-[0.2em]">01. Workload Ingestion</div>
                <div className="absolute -top-1 left-[275px] text-[7.5px] font-bold text-white/20 uppercase tracking-[0.2em]">02. Policy Broker Guard</div>
                <div className="absolute -top-1 left-[520px] text-[7.5px] font-bold text-white/20 uppercase tracking-[0.2em]">03. Allocated Engine</div>
                <div className="absolute -top-1 left-[760px] text-[7.5px] font-bold text-white/20 uppercase tracking-[0.2em]">04. Endpoint State</div>

              </div>
            </motion.div>
          ) : (
            <motion.div
              key="timeline-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute inset-0 p-5 overflow-auto scrollbar-hide flex flex-col gap-4"
            >
              {history.length > 0 ? (
                <div className="space-y-4">
                  {history.map((tx, idx) => {
                    const taskCat = classifyTask(tx.task_name);
                    const isFallback = tx.fallback_used === 'yes';
                    
                    return (
                      <div 
                        key={tx.id} 
                        className="bg-[#050a0f]/80 p-4 rounded-xl border border-white/[0.03] hover:border-cyan-700/20 transition-all font-mono text-[9px] relative overflow-hidden flex flex-col gap-3"
                      >
                        {/* Transaction ID & Flow Line Header */}
                        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 border-b border-white/5 pb-2 shrink-0">
                          <div className="flex items-center gap-2">
                            <span className="px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 rounded font-black text-[8px] tracking-wide font-mono">
                              {tx.id}
                            </span>
                            <span className="text-white font-bold text-[9.5px] max-w-[280px] break-all truncate block">
                              {tx.task_name}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-4 text-[8px]">
                            <span className="text-white/30">AUDIT_HASH: <strong className="text-white/65">{tx.audit_hash.substring(0, 16)}...</strong></span>
                            <span className="text-white/30">COMPLIANCE: 
                              <strong className={`ml-1 ${tx.policy_result.includes('SUCCESS') ? 'text-green-400' : 'text-amber-400'}`}>
                                {tx.policy_result}
                              </strong>
                            </span>
                          </div>
                        </div>

                        {/* STEP-BY-STEP FLOW VISUALIZER TIMELINE CHART */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 py-1 items-center relative">
                          
                          {/* Step 1: Workload Ingest */}
                          <div className="bg-white/[0.01] p-2.5 rounded-lg border border-white/5 flex flex-col gap-1 relative">
                            <span className="text-white/30 text-[7px] block uppercase font-mono">STEP 1: WORKLOAD</span>
                            <div className="text-cyan-400 font-bold uppercase">{taskCat}</div>
                            <span className="text-white/40 text-[7.5px] leading-tight mt-0.5">Scanned context and payload indices matching core types.</span>
                          </div>

                          {/* Step 2: Policy Routing evaluation */}
                          <div className="bg-white/[0.01] p-2.5 rounded-lg border border-white/5 flex flex-col gap-1 relative">
                            <span className="text-white/30 text-[7px] block uppercase font-mono">STEP 2: POLICY EVAL</span>
                            <div className="flex items-center gap-1.5">
                              {isFallback ? (
                                <>
                                  <ShieldAlert size={12} className="text-amber-400 animate-pulse" />
                                  <span className="text-amber-400 font-black uppercase">Fallback Route Active</span>
                                </>
                              ) : (
                                <>
                                  <ShieldCheck size={12} className="text-indigo-400" />
                                  <span className="text-indigo-400 font-bold uppercase">Compliance Sealed</span>
                                </>
                              )}
                            </div>
                            <span className="text-white/40 text-[7.5px] leading-tight mt-0.5">
                              {isFallback 
                                ? 'Tenant security checks triggered. Standard nodes restricted.' 
                                : 'Privacy scan completed. Standard load balanced route cleared.'
                              }
                            </span>
                          </div>

                          {/* Step 3: Server Selection */}
                          <div className="bg-white/[0.01] p-2.5 rounded-lg border border-white/5 flex flex-col gap-1 relative">
                            <span className="text-white/30 text-[7px] block uppercase font-mono">STEP 3: ENGINE DISPATCH</span>
                            <div className="text-green-400 font-black uppercase tracking-wider truncate" title={`${tx.provider_used} - ${tx.model_used}`}>
                              {tx.provider_used}
                            </div>
                            <span className="text-white/40 text-[7.5px] truncate font-bold select-all block mt-0.5 text-zinc-300">
                              {tx.model_used}
                            </span>
                          </div>

                          {/* Step 4: Metric Outcomes */}
                          <div className="bg-white/[0.01] p-2.5 rounded-lg border border-white/5 flex flex-col gap-1 relative">
                            <span className="text-white/30 text-[7px] block uppercase font-mono">STEP 4: TELEMETRY LEDGER</span>
                            <div className="flex justify-between items-center">
                              <span className="text-white/40 block">LATENCY:</span>
                              <span className="text-cyan-400 font-bold">{tx.latency}ms</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-white/40 block">EXPENSES:</span>
                              <span className="text-green-400 font-bold">${tx.cost.toFixed(6)}</span>
                            </div>
                          </div>

                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="py-24 flex flex-col items-center justify-center h-full text-cyan-500/20">
                  <AlertCircle size={24} className="mb-3" />
                  <span className="text-sm tracking-widest uppercase font-bold">No routing transactions simulated.</span>
                  <p className="text-[10px] text-white/30 mt-1 uppercase max-w-sm text-center tracking-normal font-mono">
                    Go back to the Router Console tab and execute a task flow route to log real-time telemetry metrics.
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

      </div>

      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -100;
          }
        }
      `}</style>
    </div>
  );
};
