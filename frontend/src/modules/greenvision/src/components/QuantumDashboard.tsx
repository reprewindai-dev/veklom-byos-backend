// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { SignalIngestionFeed } from './SignalIngestionFeed';
import { AgentFleetView } from './AgentFleetView';
import { ResearchInsights } from './ResearchInsights';
import { AutopilotCopilot } from './AutopilotCopilot';

export function QuantumDashboard() {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'fleet' | 'research'>('topology');
  const [statusState, setStatusState] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [securityData, setSecurityData] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [layers, setLayers] = useState<any>([]);
  const [infra, setInfra] = useState<any>(null);
  const [gpuData, setGpuData] = useState<any>(null);
  const [nodes, setNodes] = useState<{x: number, y: number, r: number, glow: boolean}[]>([]);
  const [edges, setEdges] = useState<{n1: number, n2: number}[]>([]);

  // Collapse / Expand layout states
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);

  useEffect(() => {
    // Generate static deterministic topology nodes based on grid. 
    // Data-driven rendering based on actual Layer count will make it somewhat dynamic
    const buildGraph = (layerCount: number) => {
      const n = [];
      const nodeCount = Math.max(15, layerCount * 4);
      const gridSize = Math.ceil(Math.sqrt(nodeCount));
      for(let i=0; i<nodeCount; i++) {
         n.push({
           x: 10 + (i % gridSize) * ((80)/Math.max(1, gridSize-1)) + Math.sin(i)*5,
           y: 10 + Math.floor(i / gridSize) * ((80)/Math.max(1, gridSize-1)) + Math.cos(i)*5,
           r: i === 0 ? 8 : (i < layerCount ? 4 : 2),
           glow: i % 3 === 0
         });
      }
      setNodes(n);
      
      const e = [];
      for(let i=0; i<nodeCount*1.5; i++) {
         e.push({
           n1: i % n.length,
           n2: (i + 3) % n.length
         });
      }
      setEdges(e);
    };

    buildGraph(layers?.length || 4);
  }, [layers?.length]);

  const fetchData = async () => {
    const endpoints = [
      { url: '/api/uacp/hub/metrics', setter: setTelemetry },
      { url: '/api/status', setter: setStatusState },
      { url: '/api/v1/sys/health', setter: setHealth },
      { url: '/api/uacp/security', setter: setSecurityData },
      { url: '/api/uacp/layers', setter: setLayers },
      { url: '/api/uacp/infrastructure', setter: setInfra },
      { url: '/api/v1/sys/gpu', setter: setGpuData },
      { url: '/api/v1/agents/monthly-report', setter: setReport }
    ];

    await Promise.all(endpoints.map(async (e) => {
      try {
        const res = await fetch(e.url);
        if (res.ok) {
          const contentType = res.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const data = await res.json().catch(() => null);
            if (data) {
              e.setter(data);
            }
          } else {
            console.warn(`Skipped non-JSON response from ${e.url}`);
          }
        } else {
          console.error(`Fetch failed for ${e.url}: ${res.status}`);
        }
      } catch (err) {
        console.error(`Error fetching ${e.url}`, err);
      }
    }));
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  const coherence = telemetry ? parseFloat(telemetry.fidelity || 99.8) : 99.8;
  const errorRate = telemetry ? parseFloat(telemetry.leakage_rate || 0.0) : 0.00;
  
  const systemOperational = statusState?.status === "healthy";
  const circuitState = statusState?.circuit_breaker?.state || "UNKNOWN";
  const llmModel = statusState?.llm_model || "Connecting...";
  const uptime = statusState?.uptime_seconds || 0;
  
  const zenoCycles = telemetry?.zeno_cycles || 0;
  const sysScore = health?.score || 0;

  const threatCount = securityData?.surfaces?.filter((s:any) => s.threat_level === "critical").length || 0;
  const warnCount = securityData?.surfaces?.filter((s:any) => s.threat_level === "high").length || 0;

  const engineState = telemetry?.status || "PHASE_LOCKED";
  const activeStatus = "ACTIVE";

  // Simple formatting helpers
  const fmtTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="quantum-dashboard font-mono text-[10px]" style={{ height: '100%', overflowY: 'auto', backgroundColor: '#050a0f', color: '#88aebf', padding: '16px' }}>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
         <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full border border-cyan-500/50 flex items-center justify-center p-1 text-cyan-400">
               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
               </svg>
            </div>
            <div>
               <div className="text-white font-sans font-medium text-sm tracking-widest">QUANTUM SERIES UACP</div>
               <div className="text-[8px] tracking-widest uppercase text-cyan-500/80">Universal Autonomous Control Plane</div>
            </div>
         </div>
         <div className="flex gap-4">
             {/* Dynamic Sidebar Control Console */}
             <div className="flex gap-1 bg-cyan-950/45 border border-cyan-800/40 p-0.5 rounded-lg mr-2 font-black">
                 <button
                   onClick={() => setIsLeftCollapsed(!isLeftCollapsed)}
                   className={`px-2 py-1 rounded text-[8px] tracking-widest uppercase transition-all flex items-center gap-1 ${isLeftCollapsed ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'text-white/40 hover:text-white/70'}`}
                   title="Toggle Left Side Panel"
                 >
                   {isLeftCollapsed ? '◀ SHOW EVENT LOG' : '▶ HIDE EVENT LOG'}
                 </button>
                 <button
                   onClick={() => setIsRightCollapsed(!isRightCollapsed)}
                   className={`px-2 py-1 rounded text-[8px] tracking-widest uppercase transition-all flex items-center gap-1 ${isRightCollapsed ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'text-white/40 hover:text-white/70'}`}
                   title="Toggle Right Side Panel"
                 >
                   {isRightCollapsed ? 'SHOW METRIC ENV ▶' : 'HIDE METRIC ENV ◀'}
                 </button>
             </div>

             <div className="flex gap-2 text-cyan-500/50">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
             </div>
             <div className="text-right">
                <div className="text-cyan-400 font-sans text-xs tracking-widest">{llmModel}</div>
                <div className="text-[8px] uppercase tracking-widest text-cyan-500/50">Uptime: {fmtTime(uptime)}</div>
             </div>
         </div>
      <div className={`grid grid-cols-1 gap-4 transition-all duration-300 ${isLeftCollapsed && isRightCollapsed ? 'md:grid-cols-1' : isLeftCollapsed ? 'md:grid-cols-[1fr_1.3fr]' : isRightCollapsed ? 'md:grid-cols-[1.3fr_1fr]' : 'md:grid-cols-[1fr_2fr_1fr]'}`}>
         {/* Left Column */}
         {!isLeftCollapsed && (
            <div className="flex flex-col gap-4">
               {/* SYSTEM LOGS */}
               <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm shadow-[0_0_15px_rgba(0,255,255,0.03)]">
                  <div className="text-[10px] tracking-widest text-white/90 font-sans mb-4 flex items-center justify-between">
                     SYSTEM EVENTS <span className="text-cyan-500/40 tracking-[0.2em] font-mono">...</span>
                  </div>
                  
                  <div className="space-y-4">
                     {[
                        { t: 'Circuit Breaker', s: circuitState },
                        { t: 'LLM Engine', s: statusState?.llm_ok ? "ONLINE" : "OFFLINE" },
                        { t: 'Privacy Shield', s: statusState?.privacy?.pii_protection || "Loading..." }
                     ].map((x, i) => (
                        <div key={i} className="flex gap-2 items-start">
                           <div className="w-[4px] h-[4px] rounded-full bg-cyan-400 mt-[5px] shadow-[0_0_6px_#0ff]"></div>
                           <div>
                              <div className="text-white/80">{x.t}</div>
                              <div className="text-[8px] text-cyan-500/50 uppercase">{x.s}</div>
                           </div>
                        </div>
                     ))}
                  </div>

                  <div className="mt-6 h-16 w-full border-t border-cyan-900/30 pt-2 relative">
                     {/* Waveform graphic */}
                     <svg className="w-full h-full text-cyan-500/70" viewBox="0 0 100 40" preserveAspectRatio="none">
                        <path d="M0,20 Q10,35 20,20 T40,20 T60,20 T80,20 T100,20" fill="none" stroke="currentColor" strokeWidth="1" />
                        <path d="M0,20 Q15,5 25,20 T50,20 T75,20 T100,20" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan-400 drop-shadow-[0_0_3px_#0ff]" />
                     </svg>
                     <div className="flex justify-between text-[8px] text-cyan-500/40 absolute bottom-0 w-full">
                        <span>T-120s</span><span>T-60s</span><span>T-30s</span><span>Now</span>
                     </div>
                  </div>
               </div>

               {/* AGENT WORKFORCE REPORT */}
               <div className="bg-[#0b1219]/60 border border-white/5 rounded-2xl p-5 relative backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.4)]">
                  <div className="text-[10px] tracking-[0.3em] text-white/90 font-black mb-6 flex items-center justify-between uppercase">
                     AGENT PERFORMANCE AUD <span className="text-cyan-500/20 font-mono">:: {new Date().toLocaleDateString(undefined, {month:'short', year:'numeric'})}</span>
                  </div>
                  {report ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                          <div className="text-[8px] text-white/30 uppercase tracking-tighter mb-1">Total Fleet</div>
                          <div className="text-lg text-white/90 font-black tracking-tight">{report.workforce_summary.total_agents}</div>
                          <div className="text-[7px] text-white/20 mt-1 uppercase leading-none">114 OP + 16 GOV</div>
                        </div>
                        <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                          <div className="text-[8px] text-white/30 uppercase tracking-tighter mb-1">Operational</div>
                          <div className="text-lg text-green-400 font-black tracking-tight">{report.workforce_summary.agents_active_during_period}</div>
                          <div className="text-[7px] text-white/20 mt-1 uppercase leading-none">Active / Running</div>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between items-end px-1">
                           <span className="text-[9px] uppercase tracking-widest text-white/40">Runtime Success</span>
                           <span className="text-xs text-white/90 font-bold">{((report.runtime_proof.successful_runs / report.runtime_proof.total_agent_runs) * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                           <div 
                             className="h-full bg-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)] transition-all duration-1000" 
                             style={{width: `${(report.runtime_proof.successful_runs / report.runtime_proof.total_agent_runs) * 100}%`}}
                           ></div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-2">
                         <div>
                           <div className="text-[7px] text-white/20 uppercase tracking-widest mb-1">Total Runs</div>
                           <div className="text-xs text-white/70 font-mono">{report.runtime_proof.total_agent_runs.toLocaleString()}</div>
                         </div>
                         <div>
                           <div className="text-[7px] text-white/20 uppercase tracking-widest mb-1">Compute Cost</div>
                           <div className="text-xs text-white/70 font-mono">${(report.runtime_proof.total_cost_cents / 100).toFixed(2)}</div>
                         </div>
                      </div>

                      <div className="pt-4 border-t border-white/5 flex gap-4 text-[7px] text-white/20 uppercase tracking-widest">
                        <span>FROZEN: {report.workforce_summary.agents_frozen_during_period}</span>
                        <span>TOKENS: {(report.runtime_proof.total_tokens_used / 1000).toFixed(0)}K</span>
                        <span className="ml-auto text-cyan-500/30 font-bold">VERIFIED_PROOF</span>
                      </div>
                    </div>
                  ) : (
                    <div className="py-12 flex flex-col items-center justify-center gap-4 text-cyan-500/20">
                      <div className="w-8 h-8 rounded-full border-2 border-current border-t-transparent animate-spin"></div>
                      <div className="text-[8px] tracking-[0.4em] uppercase font-bold">Validating workforce proof...</div>
                    </div>
                  )}
               </div>

               {/* SIGNAL INGESTION FEED */}
               <div className="flex-1 min-h-[400px]">
                  <SignalIngestionFeed />
               </div>
            </div>
         )}  </div>

         {/* Center Column */}
         <div className="bg-[#0b1219]/80 border border-cyan-800/40 rounded-xl p-5 relative flex flex-col justify-between backdrop-blur-md shadow-[inset_0_0_40px_rgba(0,180,255,0.03)]">
            <div className="flex gap-4 mb-4">
                {(['topology', 'fleet', 'research'] as const).map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)} className={`text-[10px] uppercase tracking-widest ${activeTab === tab ? 'text-white' : 'text-white/40'}`}>
                        {tab}
                    </button>
                ))}
            </div>
            
            {activeTab === 'topology' ? (
                <>
                <div className="flex justify-between items-start z-10">
                   <div>
                      <div className="text-[12px] tracking-widest text-white font-sans mb-1">QUANTUM NETWORK TOPOLOGY</div>
                      <div className="flex items-center gap-3">
                         <div className="flex items-center gap-1 text-[8px] tracking-widest text-green-400/90 border border-green-500/30 bg-green-500/10 px-2 py-0.5 rounded-full">
                            <div className="w-[4px] h-[4px] bg-green-400 rounded-full shadow-[0_0_5px_#4ade80]"></div>
                            {engineState}
                         </div>
                         <span className="text-[10px] text-white/50 tracking-widest">ERRORS {errorRate}%</span>
                      </div>
                   </div>
                   <div className="flex items-center gap-3">
                      <div className="text-[8px] tracking-widest text-cyan-500/40 text-right pr-2">SCORE: {sysScore}/100</div>
                      <div className="flex items-center gap-2">
                         <div className="text-center w-12 h-12 rounded-full border border-cyan-500/30 flex flex-col justify-center items-center shadow-[inset_0_0_10px_rgba(0,255,255,0.1)] relative">
                            <svg className="absolute w-full h-full rotate-[-90deg]">
                               <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(0,255,255,0.1)" strokeWidth="2" />
                               <circle cx="24" cy="24" r="22" fill="none" stroke="var(--accent)" strokeWidth="2" strokeDasharray="138" strokeDashoffset={138 - (138 * Math.min(errorRate, 10)) / 100} />
                            </svg>
                            <span className="text-white/80 text-[10px]">{errorRate}%</span>
                            <span className="text-[6px] text-cyan-500/50 uppercase">Error</span>
                         </div>
                         <div className="text-center w-12 h-12 rounded-full border border-cyan-500/30 flex flex-col justify-center items-center shadow-[inset_0_0_10px_rgba(0,255,255,0.1)] relative">
                            <svg className="absolute w-full h-full rotate-[-90deg]">
                               <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(0,255,255,0.1)" strokeWidth="2" />
                               <circle cx="24" cy="24" r="22" fill="none" stroke="var(--accent)" strokeWidth="2" strokeDasharray="138" strokeDashoffset={138 - (138 * coherence) / 100} />
                            </svg>
                            <span className="text-white/80 text-[10px]">{coherence.toFixed(1)}%</span>
                            <span className="text-[6px] text-cyan-500/50 uppercase">Coherence</span>
                         </div>
                      </div>
                   </div>
                </div>

                {/* Network Topology Visualization */}
                <div className="absolute inset-0 flex justify-center items-center pointer-events-none">
                   <svg className="w-[80%] h-[70%] text-cyan-400">
                       {edges.map((e, i) => {
                          const n1 = nodes[e.n1];
                          const n2 = nodes[e.n2];
                          if(!n1 || !n2) return null;
                          return <line key={i} x1={`${n1.x}%`} y1={`${n1.y}%`} x2={`${n2.x}%`} y2={`${n2.y}%`} stroke="rgba(0, 255, 255, 0.2)" strokeWidth="1" strokeDasharray={i % 2 === 0 ? "2,2" : ""} />
                       })}
                       {nodes.map((n, i) => (
                          <g key={i}>
                            {n.glow && <circle cx={`${n.x}%`} cy={`${n.y}%`} r={n.r * 3} fill="rgba(0,255,255,0.1)" filter="blur(4px)" />}
                            {n.glow && <circle cx={`${n.x}%`} cy={`${n.y}%`} r={n.r * 1.5} fill="rgba(0,255,255,0.3)" />}
                            <circle cx={`${n.x}%`} cy={`${n.y}%`} r={n.r} fill="currentColor" className="drop-shadow-[0_0_8px_#0ff]" />
                          </g>
                       ))}
                       {/* Main core */}
                       <circle cx="50%" cy="50%" r="20" fill="rgba(0,255,255,0.1)" className="drop-shadow-[0_0_20px_#0ff]" />
                       <circle cx="50%" cy="50%" r="8" fill="#fff" className="drop-shadow-[0_0_10px_#fff]" />
                       <circle cx="50%" cy="50%" r="25" fill="none" stroke="rgba(0,255,255,0.3)" strokeDasharray="4 4" strokeWidth="2" />
                   </svg>
                </div>

                <div className="z-10 mt-auto">
                   <div className="text-cyan-200/80 mb-6">
                      <div>Qubit Stability: <span className="text-cyan-400">{coherence}%</span></div>
                      <div>Network Integrity: <span className="text-cyan-400">{errorRate < 1 ? 'High' : 'Degraded'}</span></div>
                      <div>Status: <span className="text-white/60">{engineState}</span></div>
                   </div>

                   <div className="w-full h-[1px] bg-cyan-900/40 mb-3 relative flex justify-end">
                      <div className="absolute top-[-8px] bg-[#0b1219] px-2 text-[8px] text-cyan-400 tracking-widest mr-2 uppercase border border-cyan-800/40 rounded">ENTANGLEMENT {engineState}</div>
                   </div>

                   <div className="grid grid-cols-5 gap-2 text-center items-end pb-2">
                      <div className="flex flex-col border-r border-cyan-900/30 pr-2 overflow-hidden text-ellipsis whitespace-nowrap">
                         <span className="text-[8px] text-cyan-500/50 uppercase tracking-widest mb-1 truncate">SYSTEM STATUS</span>
                         <span className="text-cyan-300 tracking-wider truncate">{systemOperational ? 'OPERATIONAL' : 'DEGRADED'}</span>
                      </div>
                      <div className="flex flex-col border-r border-cyan-900/30 px-2 overflow-hidden text-ellipsis whitespace-nowrap">
                         <span className="text-[8px] text-cyan-500/50 uppercase tracking-widest mb-1 truncate">CIRCUIT</span>
                         <span className="text-cyan-300 tracking-wider truncate">{circuitState}</span>
                      </div>
                      <div className="flex flex-col border-r border-cyan-900/30 px-2 overflow-hidden text-ellipsis whitespace-nowrap">
                         <span className="text-[8px] text-cyan-500/50 uppercase tracking-widest mb-1 truncate">QUBIT ARRAY</span>
                         <span className="text-cyan-300 tracking-wider truncate">ACTIVE <span className="text-[8px] text-cyan-500/50">({zenoCycles}C)</span></span>
                      </div>
                      <div className="flex flex-col border-r border-cyan-900/30 px-2 overflow-hidden text-ellipsis whitespace-nowrap">
                         <span className="text-[8px] text-cyan-500/50 uppercase tracking-widest mb-1 truncate">COHERENCE</span>
                         <span className="text-cyan-300 text-[12px] truncate">{coherence.toFixed(1)}%</span>
                      </div>
                      <div className="flex flex-col pl-2 overflow-hidden text-ellipsis whitespace-nowrap">
                         <span className="text-[8px] text-cyan-500/50 uppercase tracking-widest mb-1 truncate">SYS SCORE</span>
                         <span className="text-cyan-300 text-[12px] truncate">{sysScore}</span>
                      </div>
                   </div>
                </div>
                </>
            ) : activeTab === 'fleet' ? <AgentFleetView /> : <ResearchInsights />}
            {activeTab === 'topology' && <AutopilotCopilot />}
                  {/* Right Column */}
         {!isRightCollapsed && (
            <div className="flex flex-col gap-4">
               {/* RESOURCES */}
               <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm">
                  <div className="text-[10px] tracking-widest text-white/90 font-sans mb-4 flex items-center justify-between">
                     HEALTH COMPONENTS <span className="text-cyan-500/40 tracking-[0.2em] font-mono">...</span>
                  </div>
                  <div className="space-y-3">
                     {health?.components ? Object.keys(health.components).map((k) => (
                        <div key={k}>
                           <div className="flex justify-between text-[10px] text-cyan-100/80 mb-1">
                              <span className="capitalize">{k}</span>
                              <span>{health.components[k].status} ({health.components[k].latency})</span>
                           </div>
                           <div className="h-1 bg-cyan-950 rounded-full overflow-hidden">
                              <div className="h-full bg-cyan-400 shadow-[0_0_8px_#0ff]" style={{width: health.components[k].status === 'healthy' ? '100%' : '50%'}}></div>
                           </div>
                        </div>
                     )) : (
                        <div className="text-cyan-500/50">Loading metrics...</div>
                     )}
                  </div>
               </div>

                {/* GPU ACCELERATION MONITOR */}
                <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm mb-4">
                   <div className="text-[10px] tracking-widest text-white/90 font-sans mb-3 flex items-center justify-between">
                      GPU COGNITIVE ACCELERATION <span className="text-cyan-500/40 tracking-[0.2em] font-mono">LIVE_CORRELATION</span>
                   </div>

                   {gpuData ? (
                     <div className="space-y-4">
                       {/* Hardware Header Block */}
                       <div className="border border-cyan-950 bg-cyan-955/10 rounded-lg p-2.5 flex flex-col gap-1.5">
                         <div className="flex justify-between items-center">
                           <span className="text-white/85 text-[9px] font-sans font-bold flex items-center gap-1.5">
                             <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                             {gpuData.hardware}
                           </span>
                           <span className="text-[7.5px] px-1.5 py-0.5 bg-cyan-900/40 border border-cyan-800/50 text-cyan-300 rounded font-mono uppercase">
                             CUDA {gpuData.cuda_version}
                           </span>
                         </div>
                         <div className="flex justify-between text-[7.5px] text-white/40 font-mono">
                           <span>DRIVER: v{gpuData.driver_version}</span>
                           <span>VRAM: {gpuData.allocated_vram_gb}GB / {gpuData.total_vram_gb}GB</span>
                         </div>
                       </div>

                       {/* Global Load meter and Temperature status metrics bar */}
                       <div className="grid grid-cols-2 gap-3">
                         <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-lg flex flex-col justify-between">
                           <span className="text-[7.5px] uppercase tracking-wider text-white/40 block mb-1">Compute Core Load</span>
                           <div className="flex justify-between items-baseline mb-1">
                             <span className="text-lg text-cyan-400 font-sans font-black tracking-tight">{gpuData.system_gpu_load_percent}%</span>
                             <span className="text-[7px] text-cyan-500/50 font-mono uppercase">Duty Ratio</span>
                           </div>
                           <div className="h-1 bg-cyan-950 rounded-full overflow-hidden">
                             <div className="h-full bg-cyan-400 shadow-[0_0_8px_#0ff] transition-all duration-500" style={{ width: `${gpuData.system_gpu_load_percent}%` }}></div>
                           </div>
                         </div>
                         
                         <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-lg flex flex-col justify-between">
                           <span className="text-[7.5px] uppercase tracking-wider text-white/40 block mb-1">Core Thermal</span>
                           <div className="flex justify-between items-baseline mb-1">
                             <span className="text-lg text-emerald-400 font-sans font-black tracking-tight">{gpuData.temperature_c}°C</span>
                             <span className="text-[7px] text-emerald-400/50 font-mono">SAFE</span>
                           </div>
                           <div className="h-1 bg-emerald-950 rounded-full overflow-hidden">
                             <div className="h-full bg-emerald-400 shadow-[0_0_8px_#10b981] transition-all duration-500" style={{ width: `${(gpuData.temperature_c / 85) * 100}%` }}></div>
                           </div>
                         </div>
                       </div>

                       {/* Active Model Utilization List */}
                       <div className="space-y-1.5">
                         <span className="text-[7.5px] uppercase tracking-widest text-white/30 font-black block font-mono">Active Model Pipeline GPU Distribution:</span>
                         <div className="space-y-1.5 max-h-[170px] overflow-y-auto pr-1">
                           {gpuData.active_models?.map((model: any, index: number) => (
                             <div key={index} className="bg-white/5 border border-white/[0.03] rounded p-2 flex flex-col gap-1 hover:border-cyan-500/10 transition-all">
                               <div className="flex justify-between items-center text-[8px] font-mono">
                                 <span className="text-white/80 font-bold">{model.model_name}</span>
                                 <span className={`px-1 rounded text-[7px] font-bold ${model.status === 'active' ? 'bg-cyan-950/40 text-cyan-400 animate-pulse' : 'bg-white/5 text-white/40'}`}>
                                   {model.status.toUpperCase()}
                                 </span>
                               </div>
                               <div className="flex justify-between items-center text-[8px] text-white/40 font-mono">
                                 <span>VRAM: <strong className="text-white/60">{model.vram_allocated_gb} GB</strong></span>
                                 <span>Tasks Done: <strong className="text-white/60">{model.tasks_processed.toLocaleString()}</strong></span>
                               </div>
                               <div className="flex items-center gap-2 mt-0.5">
                                 <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                                   <div 
                                     className={`h-full transition-all duration-500 ${model.status === 'active' ? 'bg-cyan-500 shadow-[0_0_5px_rgba(6,182,212,0.5)]' : 'bg-white/30'}`} 
                                     style={{ width: `${model.gpu_load_percent}%` }}
                                   ></div>
                                 </div>
                                 <span className="text-[7.5px] font-bold text-white/65 font-mono inline-block w-8 text-right">{model.gpu_load_percent}%</span>
                               </div>
                             </div>
                           ))}
                         </div>
                       </div>
                     </div>
                   ) : (
                     <div className="py-6 flex flex-col items-center justify-center gap-3 text-cyan-500/20">
                       <div className="w-5 h-5 rounded-full border-2 border-current border-t-transparent animate-spin"></div>
                       <span className="text-[7.5px] uppercase font-bold tracking-[0.2em]">Interrogating NVIDIA System Management Interface...</span>
                     </div>
                   )}
                </div>

               {/* ALERT MONITOR */}
               <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm">
                  <div className="text-[10px] tracking-widest text-white/90 font-sans mb-4 flex items-center justify-between">
                     SECURITY SURFACES <span className="text-cyan-500/40 tracking-[0.2em] font-mono">...</span>
                  </div>
                  <div className="flex gap-6 relative h-[25px]">
                     <div>
                        <div className="text-2xl text-red-500 font-sans tracking-tight mb-1 items-baseline flex gap-1">{threatCount} <span className="text-[10px] font-mono tracking-widest text-red-300/80">Critical</span></div>
                        <div className="h-[2px] w-full bg-red-950 absolute bottom-0 left-0"><div className="h-full bg-red-500 transition-all duration-500" style={{width: threatCount > 0 ? '100%' : '0%'}}></div></div>
                     </div>
                     <div>
                        <div className="text-2xl text-yellow-500 font-sans tracking-tight mb-1 items-baseline flex gap-1">{warnCount} <span className="text-[10px] font-mono tracking-widest text-yellow-300/80">High</span></div>
                        <div className="h-[2px] w-full bg-yellow-950 absolute bottom-0 right-0 w-[50%]"><div className="h-full bg-yellow-500 transition-all duration-500" style={{width: warnCount > 0 ? '100%' : '0%'}}></div></div>
                     </div>
                  </div>
               </div>

               {/* TIMELINE */}
               <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm flex-1 overflow-hidden">
                  <div className="text-[10px] tracking-widest text-white/90 font-sans mb-4 flex items-center justify-between">
                     TIMELINE <span className="text-cyan-500/40 tracking-[0.2em] font-mono">...</span>
                  </div>
                  <div className="space-y-4 border-l border-cyan-900/50 pl-3 ml-1 h-[150px] overflow-y-auto pr-2 scrollbar-hide">
                     {telemetry?.timestamp ? (
                        <div className="relative">
                           <div className="absolute left-[-16.5px] top-[4px] w-2 h-2 rounded-full border border-cyan-400 bg-[#0b1219] z-10 box-content shadow-[0_0_8px_#0ff] flex items-center justify-center">
                              <div className="w-[2px] h-[2px] bg-cyan-400 rounded-full"></div>
                           </div>
                           <div className="text-white/80">Event: Qubit Sync [{new Date(telemetry.timestamp).toLocaleTimeString()}]</div>
                           <div className="text-[8px] text-cyan-500/50 uppercase">Data ingested from MCP</div>
                        </div>
                     ) : null}
                     {health?.status ? (
                        <div className="relative">
                           <div className="absolute left-[-16.5px] top-[4px] w-2 h-2 rounded-full border border-cyan-400 bg-[#0b1219] z-10 box-content shadow-[0_0_8px_#0ff] flex items-center justify-center">
                              <div className="w-[2px] h-[2px] bg-cyan-400 rounded-full"></div>
                           </div>
                           <div className="text-white/80">Event: Health Check [{new Date().toLocaleTimeString()}]</div>
                           <div className="text-[8px] text-cyan-500/50 uppercase">Substems: {Object.keys(health.components || {}).join(', ')}</div>
                        </div>
                     ) : null}
                     {securityData?.surfaces ? securityData.surfaces.slice(0, 3).map((s:any, i:number) => (
                        <div key={`sec-${i}`} className="relative">
                           <div className="absolute left-[-16.5px] top-[4px] w-2 h-2 rounded-full border border-red-500 bg-[#0b1219] z-10 box-content shadow-[0_0_8px_#f00] flex items-center justify-center">
                              <div className="w-[2px] h-[2px] bg-red-500 rounded-full"></div>
                           </div>
                           <div className="text-red-300/90">Alert: {s.name}</div>
                           <div className="text-[8px] text-red-500/50 uppercase">Threat: {s.threat_level}</div>
                        </div>
                     )) : null}
                     {!telemetry && !health && !securityData && (
                        <div className="text-[10px] text-cyan-500/50">Awaiting telemetry datastream...</div>
                     )}
                  </div>
               </div>
            </div>
         )}  </div>
      </div>
    </div>
  );
}
