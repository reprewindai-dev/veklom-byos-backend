// @ts-nocheck
import React, { useState, useEffect, useRef } from 'react';
import './index.css';
import { motion, AnimatePresence } from 'motion/react';
import { SpectralAnalysis } from './components/SpectralAnalysis';
import { GovernanceMonitor } from './components/GovernanceMonitor';
import { ComplianceHorizon } from './components/ComplianceHorizon';
import { GenomeDNA } from './components/GenomeDNA';
import { LineageLedger } from './components/LineageLedger';
import { StatePropagationAtlas } from './components/StatePropagationAtlas';
import { ROIPanel } from './components/ROIPanel';
import { AgentTrustScore } from './components/AgentTrustScore';

// New imports
import { BoundedScaling } from './components/BoundedScaling';
import { UACPLayers } from './components/UACPLayers';
import { SEKEDCompiler } from './components/SEKEDCompiler';
import { AgentConsensusMatrix } from './components/AgentConsensusMatrix';
import { ArchivesOfOrder } from './components/ArchivesOfOrder';
import { DeterminismRatio } from './components/DeterminismRatio';
import { EmissionsTrajectory } from './components/EmissionsTrajectory';
import { GovernanceRoadmap } from './components/GovernanceRoadmap';
import { IdentityGovernancePanel } from './components/IdentityGovernancePanel';
import { IntentConsole } from './components/IntentConsole';
import { MCPGateway } from './components/MCPGateway';
import { MemoryVault } from './components/MemoryVault';
import { MitigationPathwaysPanel } from './components/MitigationPathwaysPanel';
import { ObservabilitySignals } from './components/ObservabilitySignals';
import { PolicyEvaluationPanel } from './components/PolicyEvaluationPanel';
import { ProbabilityMatrix } from './components/ProbabilityMatrix';
import { RegionalEmittersPanel } from './components/RegionalEmittersPanel';
import { SignalIngestionFeed } from './components/SignalIngestionFeed';
import { AgentLatencyVisualizer } from './components/AgentLatencyVisualizer';
import { ThreatLandscape } from './components/ThreatLandscape';
import { QuantumDashboard } from './components/QuantumDashboard';
import { ToolExecutor } from './components/ToolExecutor';
import { ModelRouterConsole } from './components/ModelRouterConsole';

// Type definitions to help manage the state
type ViewType = 'terminal' | 'mesh' | 'tele' | 'paths' | 'engine' | 'hub' | 'climate' | 'security' | 'trust' | 'dashboard' | 'tools' | 'router';
type LogType = 'sys' | 'pmt' | 'out' | 'ok' | 'warn' | 'err' | 'error' | 'dim' | 'pur' | 'hdr' | 'sep' | 'custom';

interface ProviderConfig {
  id: string;
  name: string;
  enabled: boolean;
  apiKey?: string;
  baseUrl?: string;
}

type LLMProvider = 'google' | 'openai' | 'anthropic' | 'groq' | 'ollama' | 'huggingface' | 'deepseek' | 'serp';

interface SpecPath {
  l: string;
  v: number;
  locked?: boolean;
  pruned?: boolean;
  ok?: boolean; // custom logical state for color
}

interface LogEntry {
  id: string;
  text: string;
  type: LogType;
  delay?: number;
  isSpec?: boolean;
  specPaths?: SpecPath[];
  isMesh?: boolean;
  meshLbl?: string;
  isRaw?: boolean;
}

interface TelemetryState {
  zenoCycles: number;
  pathsPruned: number;
  eventLogs: { id: string; cls: string; text: string; time: string }[];
}

function ZenoCanvas({ zenoOn, zenoLabel }: { zenoOn: boolean; zenoLabel: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    let animationId: number;
    let zenoPhase = 0;

    const resizeZ = () => {
      const d = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * d;
      canvas.height = 26 * d;
      ctx.scale(d, d);
    };
    resizeZ();
    window.addEventListener('resize', resizeZ);

    const drawZ = () => {
      const w = canvas.offsetWidth;
      const h = 26;
      ctx.clearRect(0, 0, w * 2, h * 2);
      ctx.beginPath();
      for (let x = 0; x < w; x++) {
        const amp = zenoOn ? 7 : 2.5;
        const fr = zenoOn ? 0.07 : 0.035;
        const y = h / 2 + Math.sin(x * fr + zenoPhase) * amp + Math.sin(x * fr * 2.1 + zenoPhase * 1.6) * (amp * 0.35);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = zenoOn ? 'rgba(227,179,65,.75)' : 'rgba(99,179,237,.5)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      
      if (zenoOn) {
        for (let i = 0; i < 5; i++) {
          const sx = (canvas.offsetWidth / 6) * (i + 1) + Math.sin(zenoPhase + i) * 4;
          const sh = 6 + Math.abs(Math.sin(zenoPhase * 2 + i)) * 9;
          ctx.beginPath();
          ctx.moveTo(sx, h / 2);
          ctx.lineTo(sx, h / 2 - sh);
          ctx.strokeStyle = `rgba(188,140,255,${0.3 + Math.abs(Math.sin(zenoPhase + i)) * 0.5})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
      zenoPhase += zenoOn ? 0.055 : 0.016;
      animationId = requestAnimationFrame(drawZ);
    };
    drawZ();

    return () => {
      window.removeEventListener('resize', resizeZ);
      cancelAnimationFrame(animationId);
    };
  }, [zenoOn]);

  return (
    <div className="zeno-strip">
      <div className="z-lbl">Zeno</div>
      <div className="z-wrap"><canvas ref={canvasRef} id="zeno"></canvas></div>
      <div className={`z-state ${zenoOn ? 'on' : ''}`}>{zenoLabel}</div>
    </div>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewType>('dashboard');
  const [inputVal, setInputVal] = useState('');
  const [isEmergencyHalt, setIsEmergencyHalt] = useState(false);
  const [isInputMinimized, setIsInputMinimized] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [zenoState, setZenoState] = useState({ on: false, lbl: 'PHASE_LOCKED' });
  const [providers, setProviders] = useState<ProviderConfig[]>([
    { id: 'google', name: 'Google (Gemini Pro)', enabled: true },
    { id: 'openai', name: 'OpenAI (GPT-4o)', enabled: true },
    { id: 'anthropic', name: 'Anthropic (Claude 3)', enabled: true },
    { id: 'groq', name: 'Groq (Llama-3.1)', enabled: true },
    { id: 'ollama', name: 'Ollama (Local)', enabled: true, baseUrl: 'http://localhost:11434' },
    { id: 'huggingface', name: 'HuggingFace', enabled: true },
    { id: 'deepseek', name: 'DeepSeek', enabled: true }
  ]);

  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('openai');
  const [agentTaskForce, setAgentTaskForce] = useState(() => 
    Array.from({ length: 120 }).map((_, i) => ({
      id: i + 1,
      role: `Agent-${i + 1}`,
      status: 'idle' as 'idle' | 'assigned' | 'executing' | 'blocked'
    }))
  );
  
  const [hubMetrics, setHubMetrics] = useState<any>(null);
  const [genome, setGenome] = useState<any>(null);
  const [lineage, setLineage] = useState<any>(null);
  
  const [tele, setTele] = useState<TelemetryState>({
    zenoCycles: 0,
    pathsPruned: 0,
    eventLogs: [
      { id: '1', cls: 'g', text: '<b>BOOT</b> — 120 Sovereign agents initialised', time: '00:00' },
      { id: '2', cls: 'p', text: '<b>Zeno</b> — Interrogator subsystem ONLINE', time: '00:01' },
      { id: '3', cls: 'a', text: '<b>co2router_srv</b> — Capability negotiation pending', time: '00:01' }
    ]
  });

  const [evTimeOffset, setEvTimeOffset] = useState(2);
  const outRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (outRef.current) {
      outRef.current.scrollTop = outRef.current.scrollHeight;
    }
  }, [logs, isTyping]);

  useEffect(() => {
    const bootSequence = async () => {
      await sleep(100);
      pushLog('—'.repeat(44), 'sep');
      pushLog('  VEKLOM TERMINAL  //  UACP v4.0', 'hdr');
      pushLog('  Neural Orchestration Engine · Antigravity v4.0', 'dim');
      pushLog('—'.repeat(44), 'sep');
      await sleep(200); pushLog('[BOOT]  Quantum context surface…', 'sys');
      await sleep(200); pushLog('[BOOT]  MCP host adapter loaded', 'sys');
      await sleep(200); pushLog('        ✓  filesystem_srv  (stdio)', 'ok');
      await sleep(200); pushLog('        ✓  quantum_srv     (SSE, 1024 qubits)', 'ok');
      await sleep(200); pushLog('        ⚠  co2router_srv   (capability pending)', 'warn');
      await sleep(200); pushLog('[BOOT]  Zeno Interrogator: ONLINE', 'sys');
      await sleep(200); pushLog('[BOOT]  Gladiator Engine: 8 paths ready', 'sys');
      await sleep(200); pushLog('[BOOT]  Cognitive Engine: CONNECTED', 'ok');
      await sleep(150); pushLog('', 'out');
      await sleep(150); pushLog('Tap a chip or type a command. Explore all 5 tabs below.', 'dim');
      await sleep(150); pushLog('—'.repeat(44), 'sep');
    };
    bootSequence();
  }, []);

  const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

  const pushLog = (text: string, type: LogType, extra: Partial<LogEntry> = {}) => {
    setLogs(p => [...p, { id: crypto.randomUUID(), text, type, ...extra }]);
  };

  const updateTele = (z: number, p: number) => {
    setTele(prev => ({
      ...prev,
      zenoCycles: prev.zenoCycles + z,
      pathsPruned: prev.pathsPruned + p
    }));
  };

  useEffect(() => {
    const fetchAgentsAndMetrics = async () => {
      try {
        const [agentsRes, metricsRes, genRes, linRes] = await Promise.all([
            fetch("/api/agents/task-force"),
            fetch("/api/uacp/hub/metrics"),
            fetch("/api/pgl/genome"),
            fetch("/api/pgl/ledger")
        ]);

        const getJSON = async (res: Response) => {
          if (res.ok && res.headers.get("content-type")?.includes("application/json")) {
            return res.json().catch(() => null);
          }
          return null;
        };

        const agentsData = await getJSON(agentsRes);
        if (agentsData) setAgentTaskForce(agentsData);

        const metricsData = await getJSON(metricsRes);
        if (metricsData) setHubMetrics(metricsData);

        const genData = await getJSON(genRes);
        if (genData) setGenome(genData);

        const linData = await getJSON(linRes);
        if (linData) setLineage(linData);
      } catch (e) {
        // graceful degrade
      }
    };
    
    // Initial fetch
    fetchAgentsAndMetrics();
    
    const interval = setInterval(() => {
      fetchAgentsAndMetrics();
      setTele(prev => ({
        ...prev,
        zenoCycles: prev.zenoCycles + Math.floor(Math.random() * 3)
      }));
    }, 12000);
    return () => clearInterval(interval);
  }, []);

  const addEvent = (cls: string, text: string) => {
    setTele(prev => {
      const newTime = evTimeOffset + Math.floor(Math.random() * 4) + 1;
      setEvTimeOffset(newTime);
      const m = String(Math.floor(newTime / 60)).padStart(2, '0');
      const s = String(newTime % 60).padStart(2, '0');
      const t = `${m}:${s}`;
      return {
        ...prev,
        eventLogs: [{ id: crypto.randomUUID(), cls, text, time: t }, ...prev.eventLogs]
      };
    });
  };

  const cmdMap = [
    { match: 'health check', route: '/health', method: 'GET' },
    { match: 'status', route: '/status', method: 'GET' },
    { match: 'telemetry', route: '/api/quantum-metrics', method: 'GET' },
    { match: 'monitoring health', route: '/api/v1/sys/health', method: 'GET' },
    { match: 'uacp security', route: '/api/uacp/security', method: 'GET' },
    { match: 'uacp layers', route: '/api/uacp/layers', method: 'GET' },
    { match: 'uacp execute', route: '/internal/uacp/execute', method: 'POST' },
    { match: 'workspace members', route: '/api/v1/workspace/members', method: 'GET' },
    { match: 'api keys list', route: '/api/v1/auth/api-keys', method: 'GET' },
    { match: 'api key create', route: '/api/v1/auth/api-keys', method: 'POST' },
    { match: 'workspace models', route: '/api/v1/workspace/models', method: 'GET' },
    { match: 'generic models', route: '/api/v1/models', method: 'GET' },
    { match: 'providers', route: '/api/v1/providers', method: 'GET' },
    { match: 'exec v1', route: '/api/v1/exec', method: 'POST' },
    { match: 'exec', route: '/v1/exec', method: 'POST' },
    { match: 'ai complete', route: '/api/v1/ai/complete', method: 'POST' },
    { match: 'listings', route: '/api/v1/listings', method: 'GET' },
    { match: 'marketplace', route: '/api/v1/marketplace', method: 'GET' },
    { match: 'pipelines list', route: '/api/v1/pipelines', method: 'GET' },
    { match: 'pipeline create', route: '/api/v1/pipelines', method: 'POST' },
    { match: 'pipeline save', route: '/api/v1/pipelines', method: 'POST' },
    { match: 'deployments list', route: '/api/v1/deployments', method: 'GET' },
    { match: 'deployment create', route: '/api/v1/deployments', method: 'POST' },
    { match: 'audit logs', route: '/api/v1/audit/logs', method: 'GET' },
    { match: 'wallet', route: '/api/v1/wallet', method: 'GET' },
    { match: 'add reserve', route: '/api/v1/billing/add-reserve', method: 'POST' },
    { match: 'reserve action', route: '/api/v1/wallet/reserve', method: 'POST' },
    { match: 'compliance', route: '/api/v1/compliance', method: 'GET' },
    { match: 'export evidence', route: '/api/v1/compliance/export', method: 'POST' },
    { match: 'schedule evidence', route: '/api/v1/compliance/schedule-export', method: 'POST' }
  ];

  const doRealCommand = async (cmdInfo: typeof cmdMap[0], rawArgs: string) => {
    pushLog(`[EXEC]    Triggering ${cmdInfo.match}...`, 'sys');
    pushLog(`[ROUTER]  ${cmdInfo.method} ${cmdInfo.route}`, 'sys');
    
    await sleep(300);
    
    try {
        const opts: RequestInit = { method: cmdInfo.method };
        if (cmdInfo.method === 'POST') {
             opts.headers = { 'Content-Type': 'application/json' };
             opts.body = JSON.stringify({ action: "terminal_invoke", payload: rawArgs });
        }

        const t = performance.now();
        const res = await fetch(cmdInfo.route, opts);
        const elapsed = performance.now() - t;
        
        if (!res.ok) {
            pushLog(`[ERROR]   HTTP ${res.status} ${res.statusText}`, 'warn');
            if (res.status === 404) {
               pushLog('          Route is not currently implemented on the backend.', 'warn');
            } else {
               let bod = await res.text().catch(()=>null);
               if (bod) pushLog(`          ${bod.substring(0, 100)}`, 'dim');
            }
        } else {
             const data = await res.json().catch(()=>null);
             if (data) {
                  const str = JSON.stringify(data, null, 2);
                  const lines = str.split('\n').filter(l => l.trim() !== '' && l.trim() !== '{' && l.trim() !== '}').map(l => l.substring(0, 60));
                  pushLog(`[SUCCESS] Transmit time: ${elapsed.toFixed(1)}ms. Response:`, 'ok');
                  lines.slice(0, 8).forEach(l => pushLog(`          ${l}`, 'out'));
                  if (lines.length > 8) pushLog(`          ... (${lines.length - 8} more lines)`, 'out');
             } else {
                  pushLog(`[SUCCESS] Transmit time: ${elapsed.toFixed(1)}ms. (Empty body)`, 'ok');
             }
        }
    } catch (err: any) {
         pushLog(`[FAULT]   Network failure: ${err.message}`, 'error');
    }
    
    updateTele(0, 1);
  };

  const submitCmd = async () => {
    const raw = inputVal.trim();
    if (!raw) return;
    setInputVal('');
    
    pushLog('', 'out');
    pushLog(`$ ${raw}`, 'pmt');
    
    setIsTyping(true);
    setZenoState({ on: true, lbl: 'INTERROGATING' });
    
    const aInterval = setInterval(() => {
      setAgentTaskForce(p => p.map(a => Math.random() > 0.82 ? { ...a, status: ['assigned', 'executing', 'blocked', 'idle'][Math.floor(Math.random() * 4)] as any } : a));
    }, 150);

    try {
      const lo = raw.toLowerCase();
      const mapped = cmdMap.find(c => lo === c.match || lo.startsWith(c.match));
      
      if (mapped) {
         await doRealCommand(mapped, raw);
      } else {
         // USE REAL BACKEND ENGINE
         const response = await fetch('/api/terminal/shell', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ command: raw })
         });
         
         if (response.ok) {
           const backendLogs = await response.json();
           for (const log of backendLogs) {
             pushLog(log.text, log.type, log);
             if (log.type === 'pur' || log.text.includes('Zeno')) updateTele(64, 0);
             if (log.type === 'ok') updateTele(0, 1);
             await sleep(50); // Small rhythmic delay
           }
         } else {
           try {
             const errData = await response.json();
             const errMsg = Array.isArray(errData) ? errData[0].text : (errData.error || errData.details || 'Unknown Error');
             pushLog(`[FAULT] Engine Error: ${errMsg}`, 'err');
           } catch {
             pushLog('[FAULT] Engine communication failure (500).', 'err');
           }
         }
      }
    } catch (err: any) {
      pushLog(`[FAULT] Neural link severed: ${err.message}`, 'error');
    }
    
    setIsTyping(false);
    clearInterval(aInterval);
    setAgentTaskForce(p => p.map(a => ({ ...a, status: 'idle' })));
    setZenoState({ on: false, lbl: 'PHASE_LOCKED' });
  };

  const handleEmergencyKill = async () => {
    if (confirm("INITIATE IMMEDIATE SYSTEM-WIDE HALT? This will block all agent operations.")) {
      const res = await fetch("/api/v1/emergency/kill", { method: "POST" });
      if (res.ok) {
        setIsEmergencyHalt(true);
        pushLog("[CRITICAL] EMERGENCY HALT INITIATED BY OPERATOR.", "err");
      }
    }
  };

  const handleReset = async () => {
    const confirmation = prompt("To reset, type: RESET SYSTEM");
    if (confirmation === "RESET SYSTEM") {
      const res = await fetch("/api/v1/emergency/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation })
      });
      if (res.ok) {
        setIsEmergencyHalt(false);
        pushLog("[STATUS] EMERGENCY HALT LIFTED. System recovered.", "ok");
      }
    }
  };

  const fillPrompt = (t: string) => {
    setInputVal(t);
    setActiveView('terminal');
    // We let the user press run
  };

  const pct = Math.min((tele.zenoCycles/512)*100, 100).toFixed(0);
  const coh = (99.8 - tele.pathsPruned*0.3).toFixed(1);

  const viewVariants = {
    initial: { opacity: 0, scale: 0.98 },
    animate: { opacity: 1, scale: 1, transition: { duration: 0.2, ease: "easeOut" } },
    exit: { opacity: 0, scale: 0.98, transition: { duration: 0.15, ease: "easeIn" } },
  };

  return (
    <div className="flex flex-col h-screen bg-[#050a0f] text-[#88aebf] font-mono selection:bg-cyan-500/30 overflow-hidden">
      {/* GLOBAL HEADER */}
      <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-[#0a0f14] z-50 shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${isEmergencyHalt ? 'bg-red-500 shadow-[0_0_10px_#f00] animate-pulse' : 'bg-green-500 shadow-[0_0_10px_#22c55e]'}`}></div>
            <div className="text-[10px] tracking-[0.4em] font-black text-white/90">UACP SOVEREIGN CORE</div>
          </div>
          
          <div className="h-4 w-[1px] bg-white/10"></div>
          
          <nav className="flex gap-4">
            {(['dashboard', 'terminal', 'router', 'tools', 'security'] as ViewType[]).map((v) => (
              <button
                key={v}
                onClick={() => setActiveView(v)}
                className={`text-[9.5px] tracking-[0.2em] uppercase font-bold transition-all px-2.5 py-1 rounded ${activeView === v ? 'text-cyan-400 bg-cyan-950/30' : 'text-white/30 hover:text-white/60'}`}
              >
                {v}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <div className="text-[9px] text-cyan-400">LLM Engine: {selectedProvider.toUpperCase()}</div>
            <div className="text-[7px] text-white/20 tracking-widest uppercase">Latency: {(9 + Math.random()*5).toFixed(1)}ms</div>
          </div>

          <div className="h-4 w-[1px] bg-white/10"></div>

          {isEmergencyHalt ? (
            <button 
              onClick={handleReset}
              className="px-4 py-1.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg text-[9px] font-bold tracking-widest hover:bg-green-500/30 transition-all shadow-[0_0_20px_rgba(34,197,94,0.1)]"
            >
              RESET_SYSTEM
            </button>
          ) : (
            <button 
              onClick={handleEmergencyKill}
              className="px-4 py-1.5 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg text-[9px] font-bold tracking-widest hover:bg-red-500/30 transition-all shadow-[0_0_20px_rgba(239,68,68,0.1)]"
            >
              EMERGENCY_HALT
            </button>
          )}
        </div>
      </div>

      {/* VIEWPORT CONTROLLER */}
      <div className="flex-1 relative overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto pb-32 scrollbar-hide perspective-[1000px]">
          <AnimatePresence mode="wait">
            {activeView === 'dashboard' && (
              <motion.div key="dashboard" {...viewVariants} className="h-full">
                <QuantumDashboard />
              </motion.div>
            )}
            {activeView === 'terminal' && (
              <motion.div key="terminal" {...viewVariants} className="h-full p-12 max-w-5xl mx-auto flex flex-col">
                <div className="flex-1 overflow-auto space-y-3 font-mono text-[11px] pr-4 scrollbar-hide">
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl mb-6">
                     <div className="text-[10px] text-white/40 mb-2 uppercase tracking-widest">Active Chips</div>
                     <div className="flex flex-wrap gap-2">
                        {['📡 Optimize Transmission', '⚛️ Heron QE', '🌿 CO2 Router', '🔬 Zeno Scan'].map(chip => (
                          <button key={chip} onClick={() => fillPrompt(chip)} className="px-3 py-1 bg-white/5 border border-white/10 rounded-md text-[9px] text-white/60 hover:bg-white/10 transition-all">
                            {chip}
                          </button>
                        ))}
                     </div>
                  </div>
                  {logs.map((L) => (
                    <div key={L.id} className={`flex gap-4 group`}>
                      <span className="shrink-0 text-white/10 select-none font-sans group-hover:text-white/20 transition-colors">[{new Date().toLocaleTimeString(undefined, {hour12:false})}]</span>
                      <span className={`leading-relaxed whitespace-pre-wrap ${L.type === 'err' ? 'text-red-400' : L.type === 'ok' ? 'text-green-400' : 'text-white/70'}`}>
                        {L.text}
                      </span>
                    </div>
                  ))}
                  <div ref={outRef} className="h-40" />
                </div>
              </motion.div>
            )}
            {activeView === 'router' && (
              <motion.div key="router" {...viewVariants} className="h-full">
                <ModelRouterConsole />
              </motion.div>
            )}
            {activeView === 'tools' && (
              <motion.div key="tools" {...viewVariants} className="h-full">
                <ToolExecutor />
              </motion.div>
            )}
            {activeView === 'security' && (
              <motion.div key="security" {...viewVariants} className="h-full p-8 max-w-5xl mx-auto">
                 <ThreatLandscape surfaces={[]} />
                 <div className="mt-6">
                   <IdentityGovernancePanel data={{xaaStatus: 'active', activeAgents: 130, shadowAiDetections: 0, complianceLevel: 100}} />
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* PERSISTENT FLOATING COMMAND INPUT */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-6 z-[60] flex flex-col items-center">
          {isInputMinimized ? (
            <button 
              onClick={() => setIsInputMinimized(false)}
              className="p-2 sm:p-2.5 px-6 bg-[#0b1219]/95 text-cyan-400 border border-cyan-500/30 rounded-full hover:bg-cyan-950/40 hover:border-cyan-400 hover:text-white hover:shadow-[0_0_20px_rgba(0,255,255,0.15)] shadow-[0_4px_15px_rgba(0,0,0,0.6)] transition-all font-mono text-[8px] font-bold tracking-widest uppercase flex items-center gap-2 cursor-pointer"
            >
              <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping"></span>
              CORE COGNITIVE SWARM INPUT // EXPAND
            </button>
          ) : (
            <div className="w-full">
               <div className={`p-1.5 bg-[#0b1219]/90 border ${isEmergencyHalt ? 'border-red-500/50 shadow-[0_0_50px_rgba(239,68,68,0.2)] animate-pulse' : 'border-white/10 shadow-[0_40px_100px_rgba(0,0,0,0.8)]'} rounded-2xl backdrop-blur-3xl flex gap-2 items-center ring-1 ring-white/5`}>
                  <div className="pl-4 text-white/20 font-bold select-none cursor-default">§</div>
                  <input 
                     className={`flex-1 bg-transparent border-none outline-none text-[12px] font-mono py-2 text-white placeholder:text-white/10 ${isEmergencyHalt ? 'cursor-not-allowed text-red-500/50' : ''}`}
                     placeholder={isEmergencyHalt ? "SYSTEM_HALTED :: UNAUTHORIZED" : "Direct the cognitive swarm..."}
                     value={inputVal}
                     onChange={(e) => !isEmergencyHalt && setInputVal(e.target.value)}
                     onKeyDown={(e) => !isEmergencyHalt && e.key === 'Enter' && submitCmd()}
                     autoFocus
                     disabled={isEmergencyHalt}
                  />
                  <button 
                    onClick={() => setIsInputMinimized(true)}
                    className="px-2 py-1.5 text-[8px] font-bold tracking-widest text-white/30 hover:text-cyan-400 hover:bg-white/5 rounded-md transition-all uppercase"
                    title="Collapse input panel"
                  >
                    Minimize
                  </button>
                  <button 
                    onClick={submitCmd}
                    disabled={isEmergencyHalt || !inputVal.trim()}
                    className={`px-5 py-2.5 rounded-xl text-[10px] font-black tracking-[0.2em] transition-all ${isEmergencyHalt ? 'bg-white/5 text-white/5' : 'bg-white/5 hover:bg-white text-white/40 hover:text-black group'}`}
                  >
                    COMMIT
                  </button>
               </div>
               
               <div className="flex justify-center mt-4">
                  <div className="flex gap-6 text-[8px] tracking-[0.3em] font-bold text-white/10 uppercase">
                     <span>Zeno Subsystem: {coh}% stability</span>
                     <span className="w-[1px] h-2.5 bg-white/5"></span>
                     <span>Active Qubits: 1024</span>
                     <span className="w-[1px] h-2.5 bg-white/5"></span>
                     <span>Nodes: Persistent</span>
                  </div>
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
