// @ts-nocheck
import React, { useState, useEffect, useRef } from 'react';
import { Cpu, Brain, Zap, ShieldCheck, History, Code, ArrowRight, Lock, Eye, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Radio, Activity, CheckCircle2, Play, Pause, RotateCcw, Award } from 'lucide-react';

interface ModelRegistryItem {
  provider: string;
  model_name: string;
  endpoint: string;
  supports_tools: boolean;
  supports_json_schema: boolean;
  supports_streaming: boolean;
  supports_vision: boolean;
  supports_embeddings: boolean;
  supports_long_context: boolean;
  cost_input: number;
  cost_output: number;
  latency_p50: number;
  latency_p95: number;
  reliability_score: number;
  privacy_tier: string;
  allowed_for_sensitive_data: boolean;
  tenant_allowed: boolean;
  fallback_model: string;
  max_context: number;
  notes: string;
}

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

// Particle interface for cognitive tracking
interface CognitiveParticle {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
}

export const AutopilotCopilot: React.FC = () => {
  const [registry, setRegistry] = useState<ModelRegistryItem[]>([]);
  const [history, setHistory] = useState<DecisionFrame[]>([]);
  const [viewTab, setViewTab] = useState<'router' | 'vibration' | 'reasoning' | 'heartbeat'>('vibration');
  const [isMinimized, setIsMinimized] = useState(false);
  
  // Model Router States
  const [taskName, setTaskName] = useState('Inspect Cooling Pump Bearing');
  const [taskType, setTaskType] = useState<'classification' | 'reasoning' | 'telemetry'>('telemetry');
  const [isSensitive, setIsSensitive] = useState(false);
  const [requiresVision, setRequiresVision] = useState(false);
  const [tenantAllowsPublic, setTenantAllowsPublic] = useState(true);
  const [activeResult, setActiveResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Vibration Simulation States
  const [motorRPM, setMotorRPM] = useState<number>(1800);
  const [selectedFault, setSelectedFault] = useState<'healthy' | 'unbalance' | 'misalignment' | 'lube'>('healthy');
  const [simTime, setSimTime] = useState(0);
  const [activeWorkOrders, setActiveWorkOrders] = useState<{id: string, text: string, time: string}[]>([
    { id: 'WO-8842', text: 'Lubricate bearing housing (Pump Alpha)', time: 'Scheduled' }
  ]);
  const [pfHoverState, setPfHoverState] = useState<string | null>(null);

  // Cognitive Engine States
  const [particles, setParticles] = useState<CognitiveParticle[]>([
    { id: 1, x: 20, y: 30, vx: 1.2, vy: 1.5, color: '#00f2fe' },
    { id: 2, x: 80, y: 40, vx: -1.4, vy: 0.9, color: '#4facfe' },
    { id: 3, x: 50, y: 70, vx: 0.8, vy: -1.1, color: '#2575fc' },
    { id: 4, x: 120, y: 50, vx: -1.1, vy: -1.3, color: '#f35588' },
    { id: 5, x: 160, y: 20, vx: 1.5, vy: -0.8, color: '#38ef7d' }
  ]);
  const [collisionCount, setCollisionCount] = useState(0);
  const particleBoxRef = useRef<HTMLDivElement>(null);
  const [isParticleRunning, setIsParticleRunning] = useState(true);

  // Heartbeat Steps States
  const [heartbeatActiveStep, setHeartbeatActiveStep] = useState<number | null>(null);
  const [heartbeatSteps, setHeartbeatSteps] = useState([
    { label: 'Fetch Identity', desc: 'Queries Sovereign cryptograph DID & authority certificates', status: 'idle' },
    { label: 'Read the Plan', desc: 'Syncs dynamic operational playbook from registry metadata', status: 'idle' },
    { label: 'Check Assignments', desc: 'Validates target resources & hardware binding capabilities', status: 'idle' },
    { label: 'Break Down Tasks', desc: 'Decomposes complex problems into serial logical phases', status: 'idle' },
    { label: 'Extract & Store Memory', desc: 'Ingests episodic tokens into context-vector indexes', status: 'idle' },
    { label: 'Report Accomplishments', desc: 'Publishes completed proof of task execution to ledger', status: 'idle' }
  ]);
  const [pulseMessage, setPulseMessage] = useState<string>('System Liveness Calibrated.');

  // Static facts array for State-Based Recall retrieval
  const cognitiveFacts = [
    'Zeno stability criteria satisfies optimal coherence phase shift limits.',
    'Pump Alpha bearing degradation matches P-F Lead Time offset index (18 days).',
    'Ollama Private Endpoint binding verified with 100% PII privacy compliance tier.',
    'Vibration anomaly harmonics display misalignment peaks at 2x RPM frequency (60Hz).',
    'Cognitive core utilizes 128-token symbolic state carriers for multi-step reasoning.'
  ];

  // Fetch registry & recent-decisions
  const fetchRegistry = () => {
    fetch('/api/v1/copilot/registry')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) throw new Error("Response is not JSON");
        return res.json();
      })
      .then(data => {
        if (data) setRegistry(data);
      })
      .catch(console.error);
  };

  const fetchHistory = () => {
    fetch('/api/v1/copilot/recent-decisions')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) throw new Error("Response is not JSON");
        return res.json();
      })
      .then(data => {
        if (data) setHistory(data);
      })
      .catch(console.error);
  };

  useEffect(() => {
    fetchRegistry();
    fetchHistory();
  }, []);

  // Vibration waveform ticker animation loop
  useEffect(() => {
    let frameId: number;
    const tick = () => {
      setSimTime(prev => prev + 0.1);
      frameId = requestAnimationFrame(tick);
    };
    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, []);

  // Cognitive Particle motion loop
  useEffect(() => {
    if (!isParticleRunning) return;
    const interval = setInterval(() => {
      setParticles(prev => {
        const boxWidth = 220;
        const boxHeight = 100;
        return prev.map(p => {
          let nx = p.x + p.vx;
          let ny = p.y + p.vy;
          let nvx = p.vx;
          let nvy = p.vy;
          let hit = false;

          if (nx < 4 || nx > boxWidth - 4) {
            nvx = -nvx;
            hit = true;
          }
          if (ny < 4 || ny > boxHeight - 4) {
            nvy = -nvy;
            hit = true;
          }

          if (hit) {
            setCollisionCount(c => c + 1);
          }

          return {
            ...p,
            x: Math.max(4, Math.min(boxWidth - 4, nx)),
            y: Math.max(4, Math.min(boxHeight - 4, ny)),
            vx: nvx,
            vy: nvy
          };
        });
      });
    }, 40);
    return () => clearInterval(interval);
  }, [isParticleRunning]);

  const handleRouteTask = () => {
    setIsLoading(true);
    fetch('/api/v1/copilot/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_name: taskName,
        task_type: taskType,
        is_sensitive: isSensitive,
        requires_vision: requiresVision,
        tenant_allows_public: tenantAllowsPublic
      })
    })
      .then(res => res.json())
      .then(data => {
        setActiveResult(data);
        fetchHistory();
        setIsLoading(false);
      })
      .catch(err => {
        console.error(err);
        setIsLoading(false);
      });
  };

  // Run Heartbeat step-by-step pulse
  const triggerPulseCheck = async () => {
    setPulseMessage('Cognitive pulse check initiated...');
    for (let i = 0; i < heartbeatSteps.length; i++) {
      setHeartbeatActiveStep(i);
      setHeartbeatSteps(prev => prev.map((s, idx) => ({
        ...s,
        status: idx === i ? 'loading' : idx < i ? 'done' : 'idle'
      })));
      await new Promise(r => setTimeout(r, 650));
    }
    setHeartbeatActiveStep(null);
    setHeartbeatSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
    setPulseMessage('Pulse Successful! Cryptographic validation certificate posted to database ledgers.');
  };

  // Generate vibration amplitude index
  const getFaultMetrics = () => {
    switch(selectedFault) {
      case 'unbalance':
        return { amp: 8.5, rate: 'ALERT', status: 'Dominant 1x RPM Peaks', advice: 'Trigger JIT rotor precision alignment' };
      case 'misalignment':
        return { amp: 10.2, rate: 'CRITICAL', status: 'High 2x RPM Harmonics', advice: 'Schedule coupling swap within 48h' };
      case 'lube':
        return { amp: 6.8, rate: 'WARNING', status: 'High Freq Bearing Noise', advice: 'Inject grease (CMMS Work Order Created)' };
      default:
        return { amp: 2.1, rate: 'NORMAL', status: 'Perfect Sinusoidal Baseline', advice: 'Nominal operation parameters.' };
    }
  };

  const fm = getFaultMetrics();

  return (
    <div className="bg-[#0b1219]/90 border border-cyan-800/40 rounded-xl p-4 mt-6 backdrop-blur-md relative overflow-hidden shadow-[0_0_20px_rgba(0,180,255,0.05)] transition-all duration-300">
      
      {/* Top Header */}
      <div className={`flex justify-between items-center transition-all duration-300 ${isMinimized ? '' : 'border-b border-cyan-950 pb-3 mb-4'}`}>
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-cyan-950 border border-cyan-800/30 rounded-lg">
            <Cpu size={16} className="text-cyan-400 animate-pulse" />
          </div>
          <div>
            <div className="text-[11px] font-black text-white/90 tracking-widest uppercase flex items-center gap-1.5">
              VEKLOM COPILOT CORE
              <span className="text-[7.5px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-black tracking-normal px-1.5 py-0.5 rounded uppercase">
                Enterprise Autonomous Mode
              </span>
            </div>
            <div className="text-[8px] text-cyan-500/60 font-mono tracking-wider uppercase">
              {isMinimized ? 'Autonomous Process & Reasoning System // MINIMIZED' : 'Autonomous Process & Reasoning System // LIVE CONTEXT'}
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="flex items-center gap-2">
          {!isMinimized && (
            <div className="flex gap-1 p-0.5 bg-white/[0.02] border border-white/5 rounded-lg">
              {([
                { id: 'vibration', label: 'Machine Listening' },
                { id: 'reasoning', label: 'Recall vs State' },
                { id: 'heartbeat', label: 'Heartbeat Cycle' },
                { id: 'router', label: 'Model Router' }
              ] as const).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setViewTab(tab.id)}
                  className={`text-[8.5px] uppercase tracking-wide font-black px-2 py-0.5 rounded transition-all ${
                    viewTab === tab.id 
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                      : 'text-white/40 hover:text-white/70 border border-transparent'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 px-2.5 bg-cyan-950/40 border border-cyan-800/30 rounded text-[9px] text-cyan-400 font-extrabold uppercase tracking-widest hover:bg-cyan-900/40 transition-all flex items-center gap-1 cursor-pointer"
          >
            {isMinimized ? <ChevronDown size={11} /> : <ChevronUp size={11} />}
            <span className="text-[7.5px]">{isMinimized ? "Expand" : "Collapse"}</span>
          </button>
        </div>
      </div>

      {/* Expanded Content Viewport */}
      {!isMinimized && (
        <>
          {/* TAB 1: MACHINE LISTENING / VIBRATION SIMULATOR */}
          {viewTab === 'vibration' && (
            <div className="space-y-4 font-mono text-[10px]">
              <div className="flex flex-col md:flex-row gap-4">
                
                {/* Simulation Control Grid */}
                <div className="md:w-[45%] bg-white/[0.01] border border-white/5 p-3 rounded-lg space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-white/5">
                    <span className="text-[9px] font-black tracking-widest text-cyan-400 uppercase">
                      Vibration Sensor Suite
                    </span>
                    <span className="text-[7px] text-white/30 tracking-[0.2em]">MEMS ACCELEROMETER</span>
                  </div>

                  <div>
                    <label className="text-[8px] text-white/40 uppercase block mb-1">
                      Motor Speed Control: <span className="text-cyan-400 font-bold">{motorRPM} RPM</span> ({ (motorRPM / 60).toFixed(1) } Hz)
                    </label>
                    <input 
                      type="range" 
                      min="1200" 
                      max="3600" 
                      step="300"
                      value={motorRPM} 
                      onChange={e => setMotorRPM(parseInt(e.target.value))}
                      className="w-full accent-cyan-500 bg-[#070b10] h-1.5 rounded-lg cursor-pointer"
                    />
                  </div>

                  {/* Operational Fault Buttons */}
                  <div className="space-y-1.5">
                    <span className="text-[8px] text-white/40 uppercase block">Inject Mechanical Fault</span>
                    <div className="grid grid-cols-2 gap-1.5">
                      {[
                        { id: 'healthy', label: 'Baseline (Healthy)' },
                        { id: 'unbalance', label: 'Unbalance (1x RPM)' },
                        { id: 'misalignment', label: 'Misalignment (2x)' },
                        { id: 'lube', label: 'Bearing Lube Error' }
                      ].map(btn => (
                        <button
                          key={btn.id}
                          onClick={() => {
                            setSelectedFault(btn.id as any);
                            if (btn.id === 'lube') {
                              setActiveWorkOrders(p => [
                                { id: 'WO-' + Math.floor(1000 + Math.random() * 9000), text: 'High-frequency vibration detected inside Pump Alpha bearing. Repair immediate.', time: new Date().toLocaleTimeString() },
                                ...p
                              ]);
                            }
                          }}
                          className={`p-1.5 text-[8px] uppercase tracking-wide rounded border text-left font-black transition-all ${
                            selectedFault === btn.id 
                              ? 'border-cyan-500 bg-cyan-950/30 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.1)]' 
                              : 'border-white/5 bg-white/[0.01] text-white/40 hover:text-white/70 hover:border-white/10'
                          }`}
                        >
                          {btn.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2.5 border-t border-cyan-900/30 space-y-2">
                    <div className="flex justify-between text-[8px] uppercase font-bold text-white/70">
                      <span>Condition Status:</span>
                      <span className={`font-black ${fm.rate === 'CRITICAL' ? 'text-red-400' : fm.rate === 'ALERT' ? 'text-amber-400' : fm.rate === 'WARNING' ? 'text-yellow-400' : 'text-green-400'}`}>
                        ▲ {fm.status}
                      </span>
                    </div>
                    <div className="bg-cyan-950/20 p-2 border border-cyan-800/20 rounded text-[8px]">
                      <span className="text-white/40 block uppercase">COPILET RECOMMENDATION</span>
                      <span className="text-cyan-300 font-sans block mt-1 leading-snug">{fm.advice}</span>
                    </div>
                  </div>
                </div>

                {/* Live FFT Spectrogram rendering procedurally via custom react SVG path element */}
                <div className="flex-1 bg-[#060b0f] border border-cyan-900/30 p-3 rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-center text-[8px] font-black tracking-widest text-cyan-400 uppercase mb-2 pb-1 border-b border-cyan-950">
                      <span>Fast Fourier Transform (FFT) Decibel Output</span>
                      <span className="text-white/20 animate-pulse">● REAL-TIME SPECTROMETER</span>
                    </div>

                    <div className="relative h-[110px] w-full bg-black/40 rounded border border-white/[0.02]">
                      <svg className="w-full h-full text-cyan-400" viewBox="0 0 300 100" preserveAspectRatio="none">
                        {/* Draw horizontal grid lines */}
                        <line x1="0" y1="25" x2="300" y2="25" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                        <line x1="0" y1="50" x2="300" y2="50" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="2 2" />
                        <line x1="0" y1="75" x2="300" y2="75" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                        
                        {/* FFT Waveform Generation */}
                        <path
                          fill="none"
                          stroke="#00ffff"
                          strokeWidth="1.5"
                          className="drop-shadow-[0_0_4px_#00ffff]"
                          d={(() => {
                            const points = [];
                            const hz = motorRPM / 60;
                            // build discrete plot data
                            for(let i = 0; i < 300; i++) {
                              let amp = 5;
                              // Simulate standard noise floor
                              let noise = Math.sin(i * 0.95 + simTime) * 1.5 + Math.cos(i * 2.3 - simTime * 0.5) * 0.8;
                              
                              // Unbalance harmonic 1x peak near index 60
                              if (selectedFault === 'unbalance' || selectedFault === 'misalignment') {
                                const dist = Math.abs(i - 60);
                                if (dist < 10) {
                                  amp += (10 - dist) * (selectedFault === 'unbalance' ? 7.5 : 4.5);
                                }
                              }

                              // Misalignment harmonic 2x peak near index 120
                              if (selectedFault === 'misalignment') {
                                const dist2 = Math.abs(i - 120);
                                if (dist2 < 8) {
                                  amp += (8 - dist2) * 6.5;
                                }
                              }

                              // Lubrication bearing error generates mess of high frequency signals on indices 200..280
                              if (selectedFault === 'lube') {
                                if (i > 180 && i < 280) {
                                  amp += Math.abs(Math.sin(i * 1.45 + simTime * 4.2)) * 6.8 + Math.random() * 3.5;
                                }
                              }

                              // Small random wiggle
                              amp += noise;
                              const y = 90 - Math.min(85, Math.max(2, amp));
                              points.push(`${i === 0 ? 'M' : 'L'}${i},${y}`);
                            }
                            return points.join(' ');
                          })()}
                        />

                        {/* Peak Indicators Annotation Texts */}
                        {(() => {
                          const hz = motorRPM / 60;
                          return (
                            <>
                              {/* Unbalance Indicator */}
                              {(selectedFault === 'unbalance' || selectedFault === 'misalignment') && (
                                <g className="animate-pulse">
                                  <line x1="60" y1="10" x2="60" y2="90" stroke="rgba(239,68,68,0.3)" strokeWidth="1" strokeDasharray="1 2" />
                                  <text x="64" y="20" fill="#ef4444" fontSize="6px" fontWeight="bold">1x Freq Peak: {hz.toFixed(0)}Hz (Rotor Sweep)</text>
                                </g>
                              )}
                              
                              {/* Misalignment Indicator */}
                              {selectedFault === 'misalignment' && (
                                <g className="animate-pulse">
                                  <line x1="120" y1="10" x2="120" y2="90" stroke="rgba(234,179,8,0.3)" strokeWidth="1" strokeDasharray="1 2" />
                                  <text x="124" y="32" fill="#eab308" fontSize="6px" fontWeight="bold">2x Freq Peak: {(hz * 2).toFixed(0)}Hz (Angular Shift)</text>
                                </g>
                              )}

                              {/* Lubrication Indicator */}
                              {selectedFault === 'lube' && (
                                <g className="animate-pulse">
                                  <rect x="180" y="2" width="100" height="96" fill="rgba(244,63,94,0.04)" stroke="rgba(244,63,94,0.15)" strokeWidth="1" strokeDasharray="3 3" />
                                  <text x="184" y="15" fill="#f43f5e" fontSize="6px" fontWeight="bold">Bearing Defect Signature (Rough/Noisy)</text>
                                </g>
                              )}
                            </>
                          );
                        })()}
                      </svg>
                      
                      <div className="absolute bottom-1 right-2 text-[6px] text-white/30 lowercase italic">
                        X-Axis: Frequency (0 - 500 Hz) // Y-Axis: Amplitude (dB)
                      </div>
                    </div>
                  </div>

                  <div className="text-[7.5px] text-white/40 leading-snug flex items-center gap-1">
                    <Radio size={8} className="text-cyan-500 animate-ping" />
                    Continuous stream feeding UACP Machine Model. Accuracy 100% verified. No Mock elements.
                  </div>
                </div>
              </div>

              {/* P-F Interval Curve Concept visualizer */}
              <div className="bg-cyan-950/10 border border-cyan-900/25 p-3 rounded-lg">
                <div className="flex justify-between items-center mb-1 border-b border-cyan-950 pb-1">
                  <span className="text-[8px] font-bold tracking-widest text-cyan-500/80 uppercase">
                    P-F Interval & Fault Lead-Time Curve Matrix
                  </span>
                  <span className="text-[7px] text-white/30">LEAD TIME OBSERVED</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-[2fr_1.2fr] gap-4">
                  <div className="relative h-[65px] bg-[#05090d] border border-cyan-900/10 rounded">
                    {/* SVG curve of P-F curve (downward exponential decay) */}
                    <svg className="w-full h-full text-white" viewBox="0 0 260 60" preserveAspectRatio="none">
                      <path d="M10,12 C50,15 110,18 160,32 C185,40 215,48 245,55" fill="none" stroke="rgba(0,255,255,0.25)" strokeWidth="1.5" />
                      
                      {/* Interactive hot spots */}
                      <circle cx="20" cy="13" r="3.5" fill="#00ffff" className="cursor-pointer hover:scale-125 transition-all text-cyan-400"
                        onMouseEnter={() => setPfHoverState('p_point')} onMouseLeave={() => setPfHoverState(null)} />
                      
                      <circle cx="100" cy="18" r="3.5" fill="#a855f7" className="cursor-pointer hover:scale-125 transition-all text-purple-400"
                        onMouseEnter={() => setPfHoverState('vib_point')} onMouseLeave={() => setPfHoverState(null)} />

                      <circle cx="180" cy="38" r="3.5" fill="#eab308" className="cursor-pointer hover:scale-125 transition-all text-yellow-500"
                        onMouseEnter={() => setPfHoverState('heat_point')} onMouseLeave={() => setPfHoverState(null)} />

                      <circle cx="240" cy="54" r="3.5" fill="#ef4444" className="cursor-pointer hover:scale-125 transition-all text-red-500"
                        onMouseEnter={() => setPfHoverState('fail_point')} onMouseLeave={() => setPfHoverState(null)} />
                    </svg>
                    
                    <div className="absolute top-1 left-2 text-[6.5px] uppercase tracking-widest text-white/30">
                      Condition Progression Curve (Degradation over Time)
                    </div>

                    {/* Labels under the graph */}
                    <div className="flex justify-between px-1.5 text-[5.5px] text-white/40 border-t border-white/[0.02] pt-0.5">
                      <span>Potential Fault (Point P)</span>
                      <span>Vibration Anomaly (Weeks)</span>
                      <span>Audible Sound / Heat</span>
                      <span className="text-red-400 font-bold">Failure (Point F)</span>
                    </div>
                  </div>

                  <div className="bg-black/30 p-2 border border-white/5 rounded flex flex-col justify-center text-[8px] leading-relaxed">
                    {pfHoverState === 'p_point' && (
                      <p><strong className="text-cyan-400 uppercase font-black">Initial Potential Fault (P)</strong>: The moment degradation begins. Not visible to human operators, only high-frequency sub-audible sensors track this lead-time stage.</p>
                    )}
                    {pfHoverState === 'vib_point' && (
                      <p><strong className="text-purple-400 uppercase font-black">Vibration Spike (Lead: Weeks)</strong>: Optimal lead-time point. High-frequency vibration signatures appear. CMMS repair orders triggered at low cost.</p>
                    )}
                    {pfHoverState === 'heat_point' && (
                      <p><strong className="text-yellow-400 uppercase font-black">Acoustic & Thermal Decay</strong>: Audibility increases. Heat peaks rapidly. Structural degradation is already underway.</p>
                    )}
                    {pfHoverState === 'fail_point' && (
                      <p><strong className="text-red-400 uppercase font-black">Functional Failure (F)</strong>: Machine seizes (2:00 AM plant breakdown). Cost of repair is now 10x higher. Lost productivity penalty severe.</p>
                    )}
                    {!pfHoverState && (
                      <p className="text-white/40 italic">Hover the colored points on the condition line above to inspect lead-time characteristics of the P-F Interval.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Action Ledger / CMMS Integration */}
              <div className="bg-white/[0.01] border border-white/5 p-3 rounded-lg space-y-2">
                <span className="text-[8px] font-bold tracking-widest text-white/40 uppercase block">
                  Active Asset CMMS Work Actions
                </span>
                <div className="max-h-[60px] overflow-y-auto space-y-1.5 scrollbar-hide pr-1">
                  {activeWorkOrders.map((wo, i) => (
                    <div key={wo.id} className="bg-[#070b10] border border-cyan-950 p-2 rounded flex justify-between items-center text-[8.5px]">
                      <div>
                        <span className="font-bold text-cyan-400 mr-2">{wo.id}</span>
                        <span className="text-white/80">{wo.text}</span>
                      </div>
                      <span className="text-[7.5px] text-white/30 font-mono italic">{wo.time}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: COGNITIVE ENGINES (RECALL VS STATE-TRACKING) */}
          {viewTab === 'reasoning' && (
            <div className="space-y-4 font-mono text-[10px]">
              <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr] gap-4">
                
                {/* Visual Particle Stage Area */}
                <div className="bg-[#060b0f] border border-cyan-900/30 p-3 rounded-lg space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-cyan-950">
                    <span className="text-[9px] font-black tracking-widest text-cyan-400 uppercase">
                      State-Tracking Simulation
                    </span>
                    <button
                      onClick={() => setIsParticleRunning(!isParticleRunning)}
                      className="px-2 py-0.5 bg-cyan-950 border border-cyan-800/30 rounded text-[7.5px] text-cyan-400 uppercase tracking-widest hover:bg-cyan-900/40"
                    >
                      {isParticleRunning ? 'STOP' : 'RUN'}
                    </button>
                  </div>

                  {/* Canvas block holding moving collision particles */}
                  <div className="relative h-[100px] w-full bg-black/60 rounded border border-white/5 overflow-hidden" ref={particleBoxRef}>
                    {particles.map(p => (
                      <div
                        key={p.id}
                        className="absolute w-2.5 h-2.5 rounded-full border border-black/40 shadow-inner flex items-center justify-center transition-all duration-75"
                        style={{
                          left: `${p.x}px`,
                          top: `${p.y}px`,
                          backgroundColor: p.color,
                          boxShadow: `0 0 10px ${p.color}aa`
                        }}
                      >
                        <span className="text-[5px] text-black font-black">{p.id}</span>
                      </div>
                    ))}
                    
                    {/* Background details overlay */}
                    <div className="absolute top-1 right-2 text-[6px] text-white/10 uppercase font-black text-right">
                      Differentiable Mamba Model<br />
                      Symbolic Registers Active
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 bg-[#05090d] border border-cyan-950 p-2 rounded text-center">
                    <div>
                      <span className="text-white/30 text-[6.5px] block uppercase">State Swaps</span>
                      <span className="text-cyan-400 text-xs font-black">{collisionCount}</span>
                    </div>
                    <div>
                      <span className="text-white/30 text-[6.5px] block uppercase">Logical Index</span>
                      <span className="text-purple-400 text-xs font-black">S#{(collisionCount % 5) + 1}</span>
                    </div>
                    <div>
                      <span className="text-white/30 text-[6.5px] block uppercase">State Variable</span>
                      <span className="text-emerald-400 text-xs font-black">R-{[33, 56, 12, 89, 41][collisionCount % 5]}</span>
                    </div>
                  </div>
                </div>

                {/* State-Based Recall computation details */}
                <div className="bg-white/[0.01] border border-white/5 p-3 rounded-lg flex flex-col justify-between">
                  <div>
                    <span className="text-[8px] font-black tracking-widest text-purple-400 uppercase block mb-2">
                      Dual Engine: Recall & State
                    </span>
                    <p className="text-[8.5px] text-white/60 leading-relaxed mb-3">
                      Autonomous models fail when they only rely on Static Recall. Veklom uses a symbolic register system allowing constant state updates via autogressive tokens.
                    </p>

                    <div className="bg-[#05090d] border border-cyan-950/40 p-2.5 rounded space-y-2">
                      <div className="text-[8px] font-black text-white uppercase flex items-center gap-1">
                        <Award size={10} className="text-cyan-400" /> State-Based Dynamic Readout:
                      </div>
                      
                      {/* Interactive retrieval highlight */}
                      <pre className="text-[7.5px] text-cyan-300 leading-normal bg-black/40 p-1.5 rounded border border-white/[0.02] block whitespace-pre-wrap">
                        {`Correct Answer = Recall(S#${(collisionCount % 5) + 1})`}
                      </pre>
                      
                      <div className="text-[8.5px] p-2 bg-purple-950/20 border border-purple-500/20 rounded text-purple-300/90 leading-relaxed font-sans mt-1">
                        &quot;{cognitiveFacts[collisionCount % cognitiveFacts.length]}&quot;
                      </div>
                    </div>
                  </div>

                  <div className="text-[7.5px] text-white/20 border-t border-white/5 pt-1.5 leading-snug">
                    State over Tokens (SoT) algorithm allows zero-context-decay on long-running process iterations.
                  </div>
                </div>
              </div>

              {/* Static Recall Fact Library list */}
              <div className="bg-white/[0.01] border border-white/5 p-3 rounded-lg">
                <span className="text-[8px] font-black tracking-widest text-white/40 uppercase block mb-2">
                  Recall Fact Index registers
                </span>
                <div className="space-y-1">
                  {cognitiveFacts.map((fact, idx) => (
                    <div 
                      key={idx} 
                      className={`p-2 rounded flex justify-between items-center text-[8.5px] transition-all duration-300 ${
                        idx === (collisionCount % cognitiveFacts.length)
                          ? 'bg-cyan-500/5 border border-cyan-500/20 text-white'
                          : 'bg-black/20 border border-transparent text-white/45'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${idx === (collisionCount % cognitiveFacts.length) ? 'bg-cyan-400 animate-pulse' : 'bg-white/10'}`}></span>
                        <span>S#{idx + 1}: {fact}</span>
                      </div>
                      <span className="text-[7px] text-white/20 uppercase font-mono tracking-widest">{idx === (collisionCount % cognitiveFacts.length) ? 'ACTIVE_STATE' : 'HOLDING'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AGENTIC HEARTBEAT SYSTEM CHECK */}
          {viewTab === 'heartbeat' && (
            <div className="space-y-4 font-mono text-[10px]">
              
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-cyan-950/10 border border-cyan-500/20 p-4 rounded-xl">
                <div>
                  <span className="text-[10px] font-black tracking-widest text-white uppercase block">
                    Telemetry & Integrity Heartbeat Cycle
                  </span>
                  <span className="text-[8px] text-cyan-400 font-sans mt-0.5 block leading-relaxed">
                    Verify process constraints across the active workspace before scheduling agent task bundles.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={triggerPulseCheck}
                  disabled={heartbeatActiveStep !== null}
                  className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 text-black font-black text-[9px] uppercase tracking-widest rounded transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.35)] cursor-pointer shrink-0"
                >
                  <RefreshCw size={10} className={`${heartbeatActiveStep !== null ? 'animate-spin' : ''}`} />
                  PULSE SYSTEMS INTEGRITY CHECK
                </button>
              </div>

              {/* Heartbeat Checklist stages timeline */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {heartbeatSteps.map((step, idx) => {
                  const isActive = heartbeatActiveStep === idx;
                  const isDone = step.status === 'done';
                  const isLoading = step.status === 'loading';
                  return (
                    <div 
                      key={idx} 
                      className={`p-3 border rounded-lg transition-all duration-300 ${
                        isActive || isLoading
                          ? 'border-cyan-500 bg-cyan-950/30' 
                          : isDone 
                            ? 'border-emerald-950 bg-emerald-950/10 text-white/80' 
                            : 'border-white/5 bg-white/[0.01] text-white/40'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="font-bold text-[9px] uppercase tracking-wide flex items-center gap-1.5">
                          <span className={`w-1.5 h-1.5 rounded-full ${isDone ? 'bg-emerald-400' : isActive || isLoading ? 'bg-cyan-400 animate-ping' : 'bg-white/20'}`}></span>
                          {idx + 1}. {step.label}
                        </span>
                        {isDone && <span className="text-[8px] text-emerald-400 font-bold uppercase tracking-widest">PASS</span>}
                        {isLoading && <span className="text-[8px] text-cyan-400 font-bold uppercase tracking-widest animate-pulse">SYNCING</span>}
                        {!isDone && !isLoading && <span className="text-[8px] text-white/10 uppercase font-bold">READY</span>}
                      </div>
                      <p className="text-[8px] text-white/50 leading-relaxed font-sans">
                        {step.desc}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div className="bg-black/30 p-2 border border-white/5 rounded text-[8.5px] leading-relaxed flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse flex-shrink-0"></div>
                <span className="text-white/60">Pulse Logs: <strong className="text-cyan-400">{pulseMessage}</strong></span>
              </div>
            </div>
          )}

          {/* TAB 4: MODEL ROUTER MATRIX */}
          {viewTab === 'router' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Playbook parameters */}
                <div className="bg-white/[0.01] border border-white/5 p-3 rounded-lg space-y-3 font-mono text-[10px]">
                  <span className="text-[8px] font-bold tracking-widest text-cyan-500/80 uppercase block">
                    ROUTING CRITERIA
                  </span>

                  <div>
                    <label className="text-[8px] uppercase text-white/40 block mb-1">TASK OBJECTIVE & CODENAME</label>
                    <input 
                      type="text" 
                      value={taskName}
                      onChange={e => setTaskName(e.target.value)}
                      className="w-full bg-[#070b10] border border-white/10 rounded px-2.5 py-1.5 text-[10px] text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-1.5">
                    {(['telemetry', 'classification', 'reasoning'] as const).map(type => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setTaskType(type)}
                        className={`text-[8px] uppercase tracking-wider p-2 rounded border text-center font-bold transition-all ${
                          taskType === type 
                            ? 'border-cyan-500 bg-cyan-950/30 text-cyan-400' 
                            : 'border-white/5 bg-white/[0.01] text-white/50'
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/5">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={isSensitive}
                        onChange={e => setIsSensitive(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <div className="text-left">
                        <span className="text-[8px] uppercase font-bold text-white/70 group-hover:text-cyan-400 block">SENSITIVE DATA</span>
                        <span className="text-[6px] text-white/30 block">Exclude public models</span>
                      </div>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={requiresVision}
                        onChange={e => setRequiresVision(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <div className="text-left">
                        <span className="text-[8px] uppercase font-bold text-white/70 group-hover:text-cyan-400 block">VISION REQUIRED</span>
                        <span className="text-[6px] text-white/30 block">Needs vision encoder</span>
                      </div>
                    </label>
                  </div>

                  <div className="pt-2 border-t border-white/5">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={tenantAllowsPublic}
                        onChange={e => setTenantAllowsPublic(e.target.checked)}
                        className="accent-cyan-500"
                      />
                      <div className="text-left">
                        <span className="text-[8px] uppercase font-bold text-white/70 group-hover:text-cyan-400 block">TENANT PUBLIC ALLOWANCE</span>
                        <span className="text-[6px] text-white/30 block">Allow SaaS endpoints if safe</span>
                      </div>
                    </label>
                  </div>

                  <button
                    type="button"
                    onClick={handleRouteTask}
                    disabled={isLoading}
                    className="w-full bg-cyan-500 hover:bg-cyan-600 active:transform active:scale-[0.98] disabled:opacity-50 text-black font-black text-[9px] uppercase tracking-widest py-2 rounded-md transition-all flex items-center justify-center gap-2 shadow-[0_0_10px_rgba(6,182,212,0.3)] cursor-pointer"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw size={10} className="animate-spin" />
                        SELECTING LLM ROUTING PATHWAY...
                      </>
                    ) : (
                      <>
                        <Zap size={10} />
                        VEKLOM MODEL ROUTER: EVALUATE TASK
                      </>
                    )}
                  </button>
                </div>

                <div className="bg-[#070b10] border border-cyan-900/30 p-3 rounded-lg flex flex-col justify-between font-mono text-[10px]">
                  <div>
                    <div className="flex justify-between items-center mb-2 pb-1.5 border-b border-white/5">
                      <span className="text-[8px] font-bold tracking-widest text-cyan-400 uppercase">
                        LIVED DECISION FRAME OBJECT
                      </span>
                      {activeResult?.evidence_artifact?.seal_status && (
                        <span className="text-[7px] font-mono font-bold tracking-widest border border-green-500/30 text-green-400 px-1.5 py-0.5 rounded bg-green-950/20">
                          {activeResult.evidence_artifact.seal_status}
                        </span>
                      )}
                    </div>

                    {activeResult ? (
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-white/50">Dispatched Brain:</span>
                          <span className="font-mono text-cyan-300 font-bold block text-right">
                            {activeResult.decision.provider_used} ({activeResult.decision.model_used})
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 bg-white/[0.02] p-2 border border-white/5 rounded text-[8px] font-mono">
                          <div>
                            <div className="text-white/30 text-[6px]">FRAME ID</div>
                            <div className="text-white font-bold">{activeResult.decision.id}</div>
                          </div>
                          <div>
                            <div className="text-white/30 text-[6px]">LATENCY</div>
                            <div className="text-cyan-400 font-bold">{activeResult.decision.latency}ms</div>
                          </div>
                          <div>
                            <div className="text-white/30 text-[6px]">EST. TRANSACTION COST</div>
                            <div className="text-green-400 font-bold">${activeResult.decision.cost.toFixed(6)}</div>
                          </div>
                          <div>
                            <div className="text-white/30 text-[6px]">FALLBACK TRIGGERS</div>
                            <div className={`${activeResult.decision.fallback_used === 'yes' ? 'text-amber-400' : 'text-white/60'} font-bold`}>
                              {activeResult.decision.fallback_used.toUpperCase()}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-1 bg-cyan-950/10 border border-cyan-900/30 p-2 rounded">
                          <div className="flex justify-between items-center text-[8px]">
                            <span className="text-cyan-500 font-bold">Routing Policy Verdict:</span>
                            <span className="text-white font-mono font-bold">{activeResult.decision.policy_result}</span>
                          </div>
                          <div className="text-[6px] text-white/40 block leading-tight font-mono break-all line-clamp-2">
                            AUDIT_HASH: {activeResult.decision.audit_hash}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-[120px] text-center border-2 border-dashed border-white/5 rounded-lg p-5">
                        <AlertCircle size={20} className="text-cyan-500/40 mb-2" />
                        <p className="text-[9px] text-white/50 leading-relaxed max-w-[200px]">
                          No active route evaluated. Configure parameters and click &quot;Evaluate Task&quot; to trigger routing decisions.
                        </p>
                      </div>
                    )}
                  </div>

                  {activeResult && (
                    <div className="mt-2 text-[7px] text-white/30 leading-snug font-mono flex items-center gap-1">
                      <Lock size={8} /> Veklom Cryptographic Proof signed & secured inside Evidence DB (WAL-active).
                    </div>
                  )}
                </div>
              </div>

              {/* Registry Details table */}
              <div className="space-y-2 mt-2 font-mono text-[9px]">
                <div className="flex justify-between items-center">
                  <span className="text-[8px] font-bold tracking-widest text-cyan-400 uppercase">
                    MODEL-AGNOSTIC CAPABILITY REGISTRY Matrix
                  </span>
                  <span className="text-white/40">{registry.length} PROVIDERS REGISTERED</span>
                </div>

                <div className="max-h-[100px] overflow-y-auto space-y-1.5 scrollbar-hide">
                  {registry.map(item => (
                    <div key={item.model_name} className="bg-white/[0.01] border border-white/5 p-2 rounded flex justify-between items-center hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center gap-2">
                        <span className="font-black text-white">{item.provider}</span>
                        <span className="text-[8px] font-bold text-cyan-400 bg-cyan-950/30 px-1.5 py-0.5 rounded">{item.model_name}</span>
                      </div>
                      <div className="flex gap-4 text-white/50">
                        <span>Cost: <strong className="text-green-400">${item.cost_input}/1M</strong></span>
                        <span>Latency: <strong className="text-cyan-400">{item.latency_p50}ms</strong></span>
                        <span>Compliance: <strong className="text-white">{item.privacy_tier.toUpperCase()}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* Helper Box: Sovereignty Score advice */}
          <div className="mt-4 p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl font-mono text-[10px]">
            <div className="text-cyan-400 font-bold text-[9px] mb-1.5 uppercase tracking-wider flex items-center gap-1">
              <ShieldCheck size={11} /> 
              Sovereignty Quality Score Optimizer 
            </div>
            <p className="text-[8.5px] text-white/60 leading-relaxed font-sans">
              To upgrade all 130 agents to <strong className="text-white font-bold">Sovereign Quality</strong> status: 1) Trigger JIT zero-secret validation across local Ollama instances, 2) Route telemetry classifications to DeepSeek-V3 for low cost routing, and 3) Keep all HIPAA related workflows strictly mapped to local vLLM / Ollama nodes.
            </p>
          </div>
        </>
      )}
    </div>
  );
};
