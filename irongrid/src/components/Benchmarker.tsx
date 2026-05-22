import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Play, PlayCircle, Zap, Cpu, Gauge, Layers, Users, RefreshCw, AlertTriangle, 
  CheckCircle, Search, ArrowUpDown, Hourglass
} from 'lucide-react';
import { QueueAgent, BenchmarkMetrics } from '../types';

export default function Benchmarker() {
  const [workforceSize, setWorkforceSize] = useState<number>(60);
  const [engineType, setEngineType] = useState<'pure_python' | 'rust_ffi'>('rust_ffi');
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [testProgress, setTestProgress] = useState(0);
  
  // Real-time states to watch
  const [agents, setAgents] = useState<QueueAgent[]>([]);
  const [averageLatency, setAverageLatency] = useState<number>(0);
  const [throughput, setThroughput] = useState<number>(0);
  const [cpuUtilization, setCpuUtilization] = useState<number>(0);
  const [activeWorkers, setActiveWorkers] = useState<number[]>([0, 0, 0, 0]);

  // Premium agent metrics explorer filters & views
  const [viewMode, setViewMode] = useState<'grid' | 'metrics'>('metrics'); // Default to metrics as requested!
  const [agentSearch, setAgentSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'queued' | 'processing' | 'completed' | 'blocked' | 'error'>('all');
  const [sortBy, setSortBy] = useState<'id' | 'progress' | 'time' | 'size'>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Polling contract simulator states
  const [selectedScenario, setSelectedScenario] = useState<'expired_pending' | 'active_lock' | 'completed'>('active_lock');
  const [pollTxId, setPollTxId] = useState<string>('3b49ee7c-ad81-42cb-bdf7-e7d69d71c828');
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [pollResult, setPollResult] = useState<any | null>(null);

  // Comparative benchmarks static database (matching prompt exactly)
  const officialBenchmarks = [
    { size: '10×10', python: 1200, rust: 15, speedup: 80 },
    { size: '50×50', python: 5800, rust: 35, speedup: 165 },
    { size: '100×100', python: 14500, rust: 95, speedup: 152 },
  ];

  // Simulated queue background runner
  const testIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startLoadTest = () => {
    if (isRunningTest) return;

    setIsRunningTest(true);
    setTestProgress(0);
    setAverageLatency(0);
    setThroughput(0);

    // Bootstrap agent array with initial coordinates + names
    const generated: QueueAgent[] = Array.from({ length: workforceSize }).map((_, idx) => ({
      id: `agent-${idx + 1}`,
      name: `Navigator Unit #${String(idx + 1).padStart(3, '0')}`,
      status: 'queued',
      progress: 0,
      routeSize: Math.floor(Math.random() * 80) + 20, // 20 - 100 sized grid route lookup
      processedBy: null,
      timeTakenUs: 0,
      cpuPercent: 0,
      cpuHistory: Array.from({ length: 5 }, () => Math.floor(Math.random() * 4) + 1),
      errorMessage: undefined,
    }));

    setAgents(generated);

    // Speeds of solver based on technology selection
    const isRust = engineType === 'rust_ffi';
    let completedCount = 0;

    if (testIntervalRef.current) clearInterval(testIntervalRef.current);

    // We cycle through queue steps
    const tickRate = isRust ? 30 : 150; // Rust chews queue way faster!

    testIntervalRef.current = setInterval(() => {
      setAgents((prevAgents) => {
        const updated = [...prevAgents];

        if (isRust) {
          // Rust processes 4 items simultaneously on the 4 process worker threads
          const openWorkers = [0, 1, 2, 3];
          const busyWorkers = [0, 0, 0, 0];
          
          let modified = false;

          for (let i = 0; i < updated.length; i++) {
            const agent = updated[i];
            
            if (agent.status === 'processing') {
              agent.progress += 25;
              const wName = agent.processedBy || 'Worker 1';
              const wIdx = wName.includes('Worker 1') ? 0 : wName.includes('Worker 2') ? 1 : wName.includes('Worker 3') ? 2 : 3;
              busyWorkers[wIdx] = 45;
              
              // Low compiled CPU overhead per agent, e.g. 12-18%
              agent.cpuPercent = Math.floor(Math.random() * 6) + 12;
              const history = [...(agent.cpuHistory || [])];
              history.push(agent.cpuPercent);
              if (history.length > 8) history.shift();
              agent.cpuHistory = history;

              if (agent.progress >= 100) {
                agent.status = 'completed';
                agent.timeTakenUs = Math.floor(agent.routeSize * 0.95); // Compiled microsecond math
                agent.cpuPercent = 0;
                completedCount++;
              }
              modified = true;
            } else if (agent.status === 'queued') {
              // Assign to first available worker thread slot
              const assignedWorkerIdx = openWorkers.find(idx => busyWorkers[idx] === 0);
              if (assignedWorkerIdx !== undefined) {
                agent.status = 'processing';
                agent.processedBy = `Worker ${assignedWorkerIdx + 1}`;
                agent.progress = 0;
                busyWorkers[assignedWorkerIdx] = 45;

                agent.cpuPercent = Math.floor(Math.random() * 6) + 12;
                const history = [...(agent.cpuHistory || [])];
                history.push(agent.cpuPercent);
                if (history.length > 8) history.shift();
                agent.cpuHistory = history;
              }
              modified = true;
            }
          }

          setActiveWorkers(busyWorkers.map(w => w > 0 ? Math.floor(Math.random() * 15) + 80 : 0));
          setCpuUtilization(Math.floor(Math.random() * 10) + (completedCount < workforceSize ? 60 : 2));

          // Reset wait CPU for unassigned agents
          for (let i = 0; i < updated.length; i++) {
            if (updated[i].status === 'queued') {
              updated[i].cpuPercent = 0;
            } else if (updated[i].status === 'completed') {
              updated[i].cpuPercent = 0;
            }
          }

          if (!modified && completedCount >= workforceSize) {
            finishTest();
          }

          return updated;

        } else {
          // Pure Python: due to CPU-bound event-loop GIL, ONLY ONE item can process at an absolute time.
          // All other items remain 'queued' or 'blocked'.
          let currentProcessingIdx = updated.findIndex((a) => a.status === 'processing');
          
          if (currentProcessingIdx !== -1) {
            const agent = updated[currentProcessingIdx];
            agent.progress += 20; // slow progress core
            setActiveWorkers([85, 0, 0, 0]); // ONLY WORKER 1 is locked up! (GIL single-loop)
            setCpuUtilization(100); // Thread spike locks single process completely

            // Simulate high Python CPU intensity per agent
            agent.cpuPercent = Math.floor(Math.random() * 8) + 92;
            const history = [...(agent.cpuHistory || [])];
            history.push(agent.cpuPercent);
            if (history.length > 8) history.shift();
            agent.cpuHistory = history;

            const idx = parseInt(agent.id.replace('agent-', '')) - 1;
            // Inject periodic GIL deadlock failures on index 5, 17, 29, 41... to mimic production CPU ceiling errors
            if (idx > 0 && idx % 12 === 5 && agent.progress >= 60 && agent.progress < 100) {
              agent.status = 'error';
              agent.errorMessage = 'GIL deadlock: CPU saturation (100%) during 8-neighbor steepness propagation.';
              agent.cpuPercent = 0;
              completedCount++;

              // Move next item from queue to processing
              const nextQueuedIdx = updated.findIndex((a) => a.status === 'queued' || a.status === 'blocked');
              if (nextQueuedIdx !== -1) {
                updated[nextQueuedIdx].status = 'processing';
                updated[nextQueuedIdx].processedBy = 'Worker 1 (GIL Locked)';
              }
            } else if (agent.progress >= 100) {
              agent.status = 'completed';
              agent.timeTakenUs = Math.floor(agent.routeSize * 145); // Pure python translation loops
              agent.cpuPercent = 0;
              completedCount++;
              
              // Move next item from queue to processing
              const nextQueuedIdx = updated.findIndex((a) => a.status === 'queued' || a.status === 'blocked');
              if (nextQueuedIdx !== -1) {
                updated[nextQueuedIdx].status = 'processing';
                updated[nextQueuedIdx].processedBy = 'Worker 1 (GIL Locked)';
              }
            }
          } else {
            // Pick first queued
            const nextQueuedIdx = updated.findIndex((a) => a.status === 'queued' || a.status === 'blocked');
            if (nextQueuedIdx !== -1) {
              updated[nextQueuedIdx].status = 'processing';
              updated[nextQueuedIdx].processedBy = 'Worker 1 (GIL Locked)';
            } else if (completedCount >= workforceSize) {
              finishTest();
            }
          }

          // Mark other queued items as 'blocked' visually to prove event loop starvation
          for (let i = 0; i < updated.length; i++) {
            if (updated[i].status === 'queued' || updated[i].status === 'blocked') {
              updated[i].status = 'blocked';
              updated[i].cpuPercent = Math.floor(Math.random() * 3) + 1; // background wait CPU noise
              const history = [...(updated[i].cpuHistory || [])];
              history.push(updated[i].cpuPercent || 0);
              if (history.length > 8) history.shift();
              updated[i].cpuHistory = history;
            } else if (updated[i].status === 'completed') {
              updated[i].cpuPercent = 0;
            }
          }

          return updated;
        }
      });

      // Compute statistics mid-test
      setAgents((current) => {
        const completed = current.filter((a) => a.status === 'completed');
        const totalCompleted = completed.length;

        if (totalCompleted > 0) {
          const avg = completed.reduce((sum, a) => sum + a.timeTakenUs, 0) / totalCompleted;
          setAverageLatency(Math.round(avg));
          // Throughput = completed agents per virtualized second
          setThroughput(Number((totalCompleted * (isRust ? 1205 : 12)).toFixed(0)));
        }

        const pct = Math.round((totalCompleted / workforceSize) * 100);
        setTestProgress(pct);

        if (totalCompleted >= workforceSize) {
          finishTest();
        }

        return current;
      });

    }, tickRate);
  };

  const finishTest = () => {
    setIsRunningTest(false);
    setActiveWorkers([0, 0, 0, 0]);
    setCpuUtilization(0);
    if (testIntervalRef.current) clearInterval(testIntervalRef.current);
    
    // Set absolute final benchmark metrics safely preserving errors
    setAgents((prev) => {
      return prev.map((a) => {
        if (a.status === 'error') {
          return {
            ...a,
            cpuPercent: 0
          };
        }
        return {
          ...a,
          status: 'completed',
          timeTakenUs: a.timeTakenUs || Math.floor(a.routeSize * (engineType === 'rust_ffi' ? 0.95 : 145)),
          cpuPercent: 0
        };
      });
    });

    setAverageLatency(engineType === 'rust_ffi' ? 62 : 11520);
    setThroughput(engineType === 'rust_ffi' ? 45000 : 85);
  };

  const handlePollSimulation = () => {
    setIsPolling(true);
    setPollResult(null);
    setTimeout(() => {
      setIsPolling(false);
      if (selectedScenario === 'expired_pending') {
        setPollResult({
          transaction_id: pollTxId,
          status: "PENDING",
          destination_node: null,
          detail: "Transaction unallocated or state window expired. Safe to re-submit payload."
        });
      } else if (selectedScenario === 'active_lock') {
        setPollResult({
          transaction_id: pollTxId,
          status: "PROCESSING",
          destination_node: null,
          detail: "Mathematical gradient calculation actively computing on an isolated worker."
        });
      } else {
        setPollResult({
          transaction_id: pollTxId,
          status: "COMPLETED",
          destination_node: "Node(24, 48)",
          detail: "Routing complete. Cache entry active for the remainder of the TTL window."
        });
      }
    }, 850);
  };

  const generateNewUUID = () => {
    const chars = '0123456789abcdef';
    let uuid = '';
    for (let i = 0; i < 36; i++) {
      if (i === 8 || i === 13 || i === 18 || i === 23) {
        uuid += '-';
      } else if (i === 14) {
        uuid += '4';
      } else {
        uuid += chars[Math.floor(Math.random() * 16)];
      }
    }
    setPollTxId(uuid);
    setPollResult(null);
  };

  // Sparkline generator helper
  const renderSparkline = (history: number[] | undefined, status: string) => {
    if (!history || history.length < 2) return null;
    const width = 44;
    const height = 12;
    const max = 100;
    const min = 0;
    
    // Calculate coordinates
    const points = history.map((val, i) => {
      const x = (i / (history.length - 1)) * width;
      const y = height - ((val - min) / (max - min)) * height;
      return `${x},${y}`;
    }).join(' ');

    let strokeColor = '#22d3ee'; // cyan-400
    if (status === 'error') {
      strokeColor = '#f43f5e'; // rose-500/red
    } else if (status === 'processing') {
      strokeColor = '#f59e0b'; // amber-500
    } else if (status === 'blocked') {
      strokeColor = '#fda4af'; // rose-300
    } else if (status === 'completed') {
      strokeColor = '#10b981'; // emerald-500
    } else {
      strokeColor = '#475569'; // slate-600
    }

    return (
      <div className="flex items-center opacity-70" title={`CPU History: ${history.join(', ')}%`}>
        <svg width={width} height={height} className="overflow-visible">
          <polyline
            fill="none"
            stroke={strokeColor}
            strokeWidth="1.25"
            points={points}
          />
        </svg>
      </div>
    );
  };

  useEffect(() => {
    return () => {
      if (testIntervalRef.current) clearInterval(testIntervalRef.current);
    };
  }, []);

  return (
    <div className="flex flex-col gap-5 border border-slate-800 bg-[#070b15] rounded-xl p-5 shadow-lg relative overflow-hidden h-full">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-rose-500 to-cyan-500" />
      
      <div>
        <div className="flex items-center gap-2">
          <span className="p-1 px-1.5 bg-rose-500/10 border border-rose-500/30 text-rose-405 text-rose-450 rounded text-xs font-mono font-semibold uppercase tracking-wider">
            Engine Benchmarking
          </span>
          <h2 className="text-xl font-sans font-medium text-slate-150 leading-tight">
            Workforce Load Concurrency Simulator
          </h2>
        </div>
        <p className="text-slate-400 text-xs mt-1 font-sans font-light">
          Simulate concurrency limits. Spawning math route loops across 120 asynchronous agents triggers either lock contention or parallel Rust core execution.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-stretch">
        
        {/* Core parameters */}
        <div className="xl:col-span-4 flex flex-col gap-4 bg-slate-950/40 border border-slate-800 p-4 rounded-lg">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Gauge className="w-4 h-4 text-rose-500" /> Stress Configuration
          </span>

          {/* Toggle engine type */}
          <div className="flex flex-col gap-1.5 mt-1">
            <label id="engine-select-label" className="text-xs text-slate-500 font-mono">Select Core Processor Environment</label>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setEngineType('rust_ffi')}
                className={`py-2.5 px-3 flex items-center justify-between rounded-lg border transition text-left ${
                  engineType === 'rust_ffi'
                    ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400'
                    : 'bg-transparent border-slate-800 text-slate-400 hover:bg-slate-900/40 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Zap className={`w-4 h-4 ${engineType === 'rust_ffi' ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <div className="flex flex-col">
                    <span className="text-xs font-sans font-semibold">Rust Core: PyO3 FFI</span>
                    <span className="text-[10px] text-slate-505 font-mono">Process Isolation / Alloc-less</span>
                  </div>
                </div>
                {engineType === 'rust_ffi' && <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" />}
              </button>

              <button
                onClick={() => setEngineType('pure_python')}
                className={`py-2.5 px-3 flex items-center justify-between rounded-lg border transition text-left ${
                  engineType === 'pure_python'
                    ? 'bg-rose-500/10 border-rose-500/40 text-rose-400'
                    : 'bg-transparent border-slate-800 text-slate-400 hover:bg-slate-900/40 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle className={`w-4 h-4 ${engineType === 'pure_python' ? 'text-rose-450' : 'text-slate-500'}`} />
                  <div className="flex flex-col">
                    <span className="text-xs font-sans font-semibold">Pure Python: Single-Thread</span>
                    <span className="text-[10px] text-slate-505 font-mono">Blocked by Event-Loop GIL</span>
                  </div>
                </div>
                {engineType === 'pure_python' && <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-pulse" />}
              </button>
            </div>
          </div>

          {/* Slider for agents */}
          <div className="flex flex-col gap-1.5 mt-2">
            <div className="flex justify-between items-center text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Concurrent Agents</span>
              <span className="text-cyan-400 font-bold">{workforceSize} / 120</span>
            </div>
            <input 
              type="range" 
              min={10} 
              max={120} 
              step={10}
              value={workforceSize} 
              disabled={isRunningTest}
              onChange={(e) => setWorkforceSize(Number(e.target.value))}
              className="w-full accent-cyan-400 bg-slate-900 h-2 rounded-lg cursor-pointer disabled:opacity-40"
            />
            <span className="text-[10px] text-slate-500 leading-normal font-sans">
              Each concurrent agent fires structural 8-neighbor gradient descent path calculation loops.
            </span>
          </div>

          <button
            onClick={startLoadTest}
            disabled={isRunningTest}
            className={`w-full py-2.5 px-4 font-sans text-xs font-bold rounded-lg border transition flex items-center justify-center gap-2 ${
              isRunningTest 
                ? 'bg-slate-900 border-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-rose-500 hover:bg-rose-600 text-slate-950 border-rose-400 shadow-sm active:scale-95'
            }`}
          >
            {isRunningTest ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-slate-500" /> Computing Thread Load ({testProgress}%)
              </>
            ) : (
              <>
                <PlayCircle className="w-4 h-4 fill-current" /> Spawn Concurrent Agent Requests
              </>
            )}
          </button>
        </div>

        {/* Live processing dashboard */}
        <div className="xl:col-span-8 flex flex-col gap-4 bg-slate-950/20 border border-slate-850 p-4 rounded-lg flex-1">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" /> Multi-Core Thread Activity logs
            </span>
            
            {/* Display Toggles */}
            <div className="flex bg-[#040812] border border-slate-800 p-0.5 rounded-lg text-[10px] font-mono select-none">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-2.5 py-1 rounded-md transition font-medium cursor-pointer ${
                  viewMode === 'grid'
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                GRID OVERVIEW
              </button>
              <button
                onClick={() => setViewMode('metrics')}
                className={`px-2.5 py-1 rounded-md transition font-medium cursor-pointer ${
                  viewMode === 'metrics'
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                METRICS EXPLORER
              </button>
            </div>
          </div>

          {/* Core loads */}
          <div className="grid grid-cols-4 gap-2 mb-1">
            {activeWorkers.map((load, idx) => (
              <div key={idx} className="bg-slate-900/50 border border-slate-800 p-2.5 rounded flex flex-col items-center gap-1">
                <span className="text-[10px] text-slate-500 font-mono">Core #{idx + 1}</span>
                <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden">
                  <motion.div 
                    className={`h-full ${engineType === 'rust_ffi' ? 'bg-cyan-400 shadow-[0_0_8px_#22d3ee]' : 'bg-rose-500'}`}
                    animate={{ width: `${load}%` }}
                    transition={{ duration: 0.1 }}
                  />
                </div>
                <span className={`text-[10px] font-mono ${load > 0 ? 'text-slate-300 font-bold' : 'text-slate-600'}`}>
                  {load > 0 ? `${load.toFixed(0)}%` : '0% (IDLE)'}
                </span>
               </div>
            ))}
          </div>

          {/* Dynamic Content Views */}
          {viewMode === 'grid' ? (
            /* Traditional Matrix Overview */
            <div className="flex-1 bg-slate-950/80 border border-slate-900 rounded-lg p-2 overflow-y-auto max-h-[220px] grid grid-cols-5 sm:grid-cols-8 md:grid-cols-12 gap-1.5 relative min-h-[160px]">
              {agents.length === 0 ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
                  <span className="text-xs font-mono text-slate-500">Queue is idle. Trigger load test configurations above.</span>
                </div>
              ) : (
                agents.map((agent) => {
                  let statusColor = 'bg-slate-800 text-slate-500';
                  if (agent.status === 'processing') statusColor = 'bg-amber-500/20 text-amber-300 border border-amber-600/40 animate-pulse';
                  if (agent.status === 'completed') statusColor = 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30';
                  if (agent.status === 'blocked') statusColor = 'bg-rose-500/20 text-rose-350 border border-rose-500/30 animate-pulse';
                  if (agent.status === 'error') statusColor = 'bg-rose-950 border border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)] text-red-200';

                  return (
                    <div
                      key={agent.id}
                      className={`font-mono text-[9px] rounded py-1 px-1.5 flex flex-col justify-between items-center text-center select-none ${statusColor}`}
                      title={`${agent.name} is ${agent.status.toUpperCase()} (${agent.routeSize} nodes) ${agent.errorMessage ? `: ${agent.errorMessage}` : ''}`}
                    >
                      <span>#{agent.id.replace('agent-', '')}</span>
                      {agent.status === 'completed' ? (
                        <span className="text-[8px] text-emerald-400 font-semibold">{agent.timeTakenUs < 1000 ? `${agent.timeTakenUs}μs` : `${(agent.timeTakenUs/1000).toFixed(1)}ms`}</span>
                      ) : agent.status === 'processing' ? (
                        <span className="text-[8px] text-amber-300 animate-pulse">{agent.progress}%</span>
                      ) : agent.status === 'blocked' ? (
                        <span className="text-[8px] text-rose-355 text-rose-400">Locked</span>
                      ) : agent.status === 'error' ? (
                        <span className="text-[8px] text-red-400 font-bold animate-pulse">FAIL</span>
                      ) : (
                        <span className="text-[8px] text-slate-600">Wait</span>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            /* Premium Searchable List Inspector */
            <div className="flex flex-col gap-3 bg-slate-950/80 border border-slate-900 rounded-lg p-3 relative min-h-[160px] max-h-[320px] overflow-hidden">
              
              {/* Controls Overlay header */}
              <div className="flex flex-col gap-2 border-b border-slate-900 pb-2.5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 items-center">
                  
                  {/* Search box with inline absolute icon */}
                  <div className="relative">
                    <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search unit name, active worker ID ..."
                      value={agentSearch}
                      onChange={(e) => setAgentSearch(e.target.value)}
                      className="pl-7 bg-slate-900/60 border border-slate-800 rounded-md py-1.5 px-3 block text-[11px] text-slate-300 w-full focus:outline-none focus:border-cyan-500/30 font-mono"
                    />
                  </div>

                  {/* Filter chips bar */}
                  <div className="flex flex-wrap gap-1 md:justify-end">
                    {[
                      { id: 'all', label: 'All', color: 'bg-slate-400' },
                      { id: 'queued', label: 'Queued', color: 'bg-slate-500' },
                      { id: 'processing', label: 'Processing', color: 'bg-amber-400' },
                      { id: 'blocked', label: 'Blocked', color: 'bg-rose-500' },
                      { id: 'error', label: 'Error', color: 'bg-rose-600' },
                      { id: 'completed', label: 'Completed', color: 'bg-emerald-400' }
                    ].map((chip) => {
                      const count = chip.id === 'all' 
                        ? agents.length 
                        : agents.filter(a => a.status === chip.id).length;
                      return (
                        <button
                          key={chip.id}
                          onClick={() => setStatusFilter(chip.id as any)}
                          className={`py-1 px-1.5 text-[9px] font-mono rounded border transition flex items-center gap-1 cursor-pointer ${
                            statusFilter === chip.id
                              ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                              : 'bg-transparent border-slate-900 text-slate-550 text-slate-500 hover:text-slate-300'
                          }`}
                        >
                          <span className={`w-1 h-1 rounded-full ${chip.color} ${chip.id === 'processing' && count > 0 ? 'animate-ping' : ''}`} />
                          <span>{chip.label}</span>
                          <span className="opacity-60">({count})</span>
                        </button>
                      );
                    })}
                  </div>

                </div>

                {/* Sub-filtering options & Sort criteria selection */}
                <div className="flex items-center gap-2 justify-between mt-1 text-[10px] font-mono text-slate-500">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span>Sort by:</span>
                    {[
                      { id: 'id', label: 'ID Sequence' },
                      { id: 'progress', label: 'Progress (%)' },
                      { id: 'time', label: 'Compute Time' },
                      { id: 'size', label: 'Nodes size' }
                    ].map((btn) => (
                      <button
                        key={btn.id}
                        onClick={() => {
                          if (sortBy === btn.id) {
                            setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
                          } else {
                            setSortBy(btn.id as any);
                            setSortOrder('desc'); // High speeds/progresses first
                          }
                        }}
                        className={`px-1 rounded border transition flex items-center gap-1 cursor-pointer ${
                          sortBy === btn.id
                            ? 'border-cyan-500/20 text-cyan-400 bg-cyan-500/5'
                            : 'border-transparent text-slate-500 hover:text-slate-300'
                        }`}
                      >
                        <span>{btn.label}</span>
                        {sortBy === btn.id && (
                          <ArrowUpDown className="w-2.5 h-2.5" />
                        )}
                      </button>
                    ))}
                  </div>
                  <div className="text-[9px] text-slate-600">
                    Displaying{' '}
                    {agents.length === 0 ? 0 : 
                      agents.filter((a) => {
                        const q = agentSearch.toLowerCase();
                        const isMatch = statusFilter === 'all' || a.status === statusFilter;
                        const matchText = a.name.toLowerCase().includes(q) || a.id.toLowerCase().includes(q) || (a.processedBy && a.processedBy.toLowerCase().includes(q));
                        return isMatch && matchText;
                      }).length} of {agents.length} units
                  </div>
                </div>

              </div>

              {/* Live list scroll zone */}
              <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-1.5 max-h-[175px]">
                {agents.length === 0 ? (
                  <div className="flex flex-col items-center justify-center text-center p-5 py-8">
                    <span className="text-xs font-mono text-slate-505 text-slate-500">
                      Workforce pipeline is currently unallocated. Click the stress button to spawn math requests.
                    </span>
                  </div>
                ) : (
                  agents
                    .filter((a) => {
                      const q = agentSearch.toLowerCase();
                      const isMatch = statusFilter === 'all' || a.status === statusFilter;
                      const matchText = a.name.toLowerCase().includes(q) || a.id.toLowerCase().includes(q) || (a.processedBy && a.processedBy.toLowerCase().includes(q));
                      return isMatch && matchText;
                    })
                    .sort((a, b) => {
                      const orderMod = sortOrder === 'asc' ? 1 : -1;
                      if (sortBy === 'id') {
                        const idA = parseInt(a.id.replace('agent-', '')) || 0;
                        const idB = parseInt(b.id.replace('agent-', '')) || 0;
                        return (idA - idB) * orderMod;
                      }
                      if (sortBy === 'progress') return (a.progress - b.progress) * orderMod;
                      if (sortBy === 'time') return (a.timeTakenUs - b.timeTakenUs) * orderMod;
                      if (sortBy === 'size') return (a.routeSize - b.routeSize) * orderMod;
                      return 0;
                    })
                    .map((agent) => {
                      // Status color styles mapping
                      let badgeStyle = 'bg-slate-900 border-slate-800 text-slate-400';
                      let barStyle = 'bg-slate-700';
                      let showAnimation = false;

                      if (agent.status === 'processing') {
                        badgeStyle = 'bg-amber-500/10 border-amber-500/20 text-amber-400';
                        barStyle = 'bg-amber-400';
                        showAnimation = true;
                      } else if (agent.status === 'completed') {
                        badgeStyle = 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
                        barStyle = 'bg-emerald-400';
                      } else if (agent.status === 'blocked') {
                        badgeStyle = 'bg-rose-500/15 border-rose-500/25 text-rose-450 text-rose-400';
                        barStyle = 'bg-rose-500';
                      } else if (agent.status === 'error') {
                        badgeStyle = 'bg-red-500/10 border-red-500/20 text-red-400';
                        barStyle = 'bg-red-500';
                      }

                      const cardStyle = agent.status === 'error'
                        ? 'bg-rose-950/10 hover:bg-[#180a0f] border-red-500/30'
                        : 'bg-slate-950/40 hover:bg-[#070c17] border-slate-900';

                      return (
                        <div 
                          key={agent.id}
                          className={`rounded-md border p-2 flex flex-col gap-1.5 transition ${cardStyle}`}
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-[11px] font-mono leading-none">
                            {/* Unit Title */}
                            <div className="flex items-center gap-2 sm:w-[18%]">
                              <span className="text-slate-500 text-[10px] font-bold">#{agent.id.replace('agent-', '').padStart(3, '0')}</span>
                              <span className="text-slate-300 font-sans truncate font-medium">{agent.name}</span>
                            </div>

                            {/* Dynamic Progress indicator with bar */}
                            <div className="flex items-center gap-2 flex-grow min-w-[80px] sm:w-[20%]">
                              <span className="text-slate-500 text-[9px] w-6 text-right select-none">{agent.progress}%</span>
                              <div className="h-1.5 flex-1 bg-slate-900 border border-slate-900 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full rounded-full transition-all duration-150 ${barStyle} ${showAnimation ? 'animate-pulse' : ''}`}
                                  style={{ width: `${agent.progress}%` }}
                                />
                              </div>
                            </div>

                            {/* Status Badge */}
                            <div className="flex items-center gap-1 sm:w-[13%]">
                              <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border flex items-center gap-1 ${badgeStyle}`}>
                                {agent.status === 'queued' ? (
                                  <>
                                    <Hourglass className="w-2.5 h-2.5 text-slate-500" />
                                    <span>QUEUED</span>
                                  </>
                                ) : agent.status === 'processing' ? (
                                  <>
                                    <RefreshCw className="w-2.5 h-2.5 text-amber-400 animate-spin" />
                                    <span className="animate-pulse">RUNNING</span>
                                  </>
                                ) : agent.status === 'blocked' ? (
                                  <>
                                    <AlertTriangle className="w-2.5 h-2.5 text-rose-450 text-rose-400" />
                                    <span>BLOCKED</span>
                                  </>
                                ) : agent.status === 'error' ? (
                                  <>
                                    <AlertTriangle className="w-2.5 h-2.5 text-red-400 animate-pulse" />
                                    <span>CRASHED</span>
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle className="w-2.5 h-2.5 text-emerald-400" />
                                    <span>RESOLVED</span>
                                  </>
                                )}
                              </span>
                            </div>

                            {/* Real-time CPU usage column */}
                            <div className="flex items-center gap-2 sm:w-[18%] justify-between select-none">
                              <div className="flex items-center gap-1.5 min-w-[38px]">
                                <Cpu className="w-3 h-3 text-slate-500" />
                                <span className={`text-[10px] font-bold ${
                                  agent.cpuPercent && agent.cpuPercent > 80
                                    ? 'text-rose-400 animate-pulse font-extrabold'
                                    : agent.cpuPercent && agent.cpuPercent > 40
                                      ? 'text-amber-400'
                                      : agent.cpuPercent && agent.cpuPercent > 0
                                        ? 'text-cyan-400'
                                        : 'text-slate-600'
                                }`}>
                                  {agent.cpuPercent !== undefined ? `${agent.cpuPercent}%` : '0%'}
                                </span>
                              </div>
                              {renderSparkline(agent.cpuHistory, agent.status)}
                            </div>

                            {/* Compute Speed */}
                            <div className="flex items-center gap-1 text-slate-400 sm:w-[14%]">
                              <span className="text-slate-500 text-[9px] uppercase">Speed:</span>
                              {agent.status === 'completed' ? (
                                <span className="font-semibold text-emerald-400 select-all">
                                  {agent.timeTakenUs < 1000 ? `${agent.timeTakenUs}μs` : `${(agent.timeTakenUs/1000).toFixed(1)}ms`}
                                </span>
                              ) : agent.status === 'processing' ? (
                                <span className="text-amber-300 font-light animate-pulse text-[10px]">Active</span>
                              ) : agent.status === 'blocked' ? (
                                <span className="text-rose-450 text-rose-450 text-rose-400/80 font-mono">GIL Locked</span>
                              ) : agent.status === 'error' ? (
                                <span className="text-red-400 font-semibold text-[9px] uppercase">FATAL</span>
                              ) : (
                                <span className="text-slate-600">Pending</span>
                              )}
                            </div>

                            {/* Thread Core Processor / Route Nodes */}
                            <div className="text-[10px] text-slate-500 flex items-center justify-between sm:justify-end gap-1.5 sm:w-[17%] select-none">
                              <span className="text-slate-450 text-slate-400">{agent.routeSize}n</span>
                              <span className="opacity-10 border-l border-slate-705 border-slate-700 h-3 hidden sm:inline" />
                              <span className="text-slate-600 truncate max-w-[85px]">
                                {agent.processedBy || 'Pool Wait'}
                              </span>
                            </div>
                          </div>

                          {/* Crash details tray if error */}
                          {agent.status === 'error' && agent.errorMessage && (
                            <div className="mt-1 pt-1 border-t border-red-500/10 flex items-center gap-1.5 text-[10px] text-red-400 bg-red-950/20 px-2 py-1 rounded font-sans leading-normal">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                              <span>{agent.errorMessage}</span>
                            </div>
                          )}

                        </div>
                      );
                    })
                )}
              </div>

            </div>
          )}

          {/* Test statistics result cards */}
          <div className="grid grid-cols-3 gap-3 bg-[#0a0f1d]/60 border border-slate-900 p-3 rounded-lg font-mono">
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500">Average response Latency</span>
              <span className={`text-base font-bold ${engineType === 'rust_ffi' ? 'text-cyan-400' : 'text-rose-450 text-rose-400'}`}>
                {averageLatency > 0 ? (
                  averageLatency < 1000 ? `${averageLatency} μs` : `${(averageLatency/1000).toFixed(1)} ms`
                ) : '---'}
              </span>
            </div>
            
            <div className="flex flex-col font-bold">
              <span className="text-[10px] text-slate-505 font-light normal-case">Throughput Capacity</span>
              <span className="text-base text-slate-205 text-slate-200">
                {throughput > 0 ? `${throughput.toLocaleString()} req/s` : '---'}
              </span>
            </div>

            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500">CPU Lockup contention</span>
              <span className={`text-base font-bold ${cpuUtilization > 80 ? 'text-rose-450 text-rose-400 animate-pulse' : 'text-emerald-400'}`}>
                {cpuUtilization > 0 ? `${cpuUtilization}%` : '0%'}
              </span>
            </div>
          </div>

        </div>
      </div>

      {/* 202 Accepted Status Polling Sandbox */}
      <div className="bg-[#050915] border border-slate-800/80 rounded-lg p-5 mt-2 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-900 pb-3">
          <div className="flex items-center gap-2">
            <span className="p-1 px-1.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded text-[10px] font-mono font-semibold uppercase tracking-wider">
              API Contract Simulation
            </span>
            <h3 className="text-md font-sans font-medium text-slate-200">
              `/status/{'{transaction_id}'}` Polling Sandbox
            </h3>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            Guarantees idempotent client tracking down to microsecond math loops
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          
          {/* Simulation Controls (Left pane) */}
          <div className="lg:col-span-5 flex flex-col gap-3.5 bg-slate-950/20 border border-slate-900 p-4 rounded-lg">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
              Test Scenario Selector
            </span>

            {/* Simulated Redis Key Status */}
            <div className="flex flex-col gap-2">
              <label className="text-[11px] font-mono text-slate-550 text-slate-500">Pick Redis Idempotency Lock Condition</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => { setSelectedScenario('expired_pending'); setPollResult(null); }}
                  className={`py-2 px-2.5 rounded border text-center transition flex flex-col gap-1 cursor-pointer ${
                    selectedScenario === 'expired_pending'
                      ? 'bg-zinc-500/20 border-zinc-500/50 text-zinc-300'
                      : 'bg-transparent border-slate-900 text-slate-500 hover:text-slate-300 hover:bg-slate-900/10'
                  }`}
                >
                  <span className="text-[11px] font-bold">Case A</span>
                  <span className="text-[9px] font-mono leading-none font-light">EXPIRED key</span>
                </button>

                <button
                  onClick={() => { setSelectedScenario('active_lock'); setPollResult(null); }}
                  className={`py-2 px-2.5 rounded border text-center transition flex flex-col gap-1 cursor-pointer ${
                    selectedScenario === 'active_lock'
                      ? 'bg-amber-500/20 border-amber-500/50 text-amber-350 text-amber-300'
                      : 'bg-transparent border-slate-900 text-slate-500 hover:text-slate-300 hover:bg-slate-900/10'
                  }`}
                >
                  <span className="text-[11px] font-bold">Case B</span>
                  <span className="text-[9px] font-mono leading-none font-light">ACTIVE LOCK</span>
                </button>

                <button
                  onClick={() => { setSelectedScenario('completed'); setPollResult(null); }}
                  className={`py-2 px-2.5 rounded border text-center transition flex flex-col gap-1 cursor-pointer ${
                    selectedScenario === 'completed'
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-350 text-emerald-300'
                      : 'bg-transparent border-slate-900 text-slate-500 hover:text-slate-300 hover:bg-slate-900/10'
                  }`}
                >
                  <span className="text-[11px] font-bold">Case C</span>
                  <span className="text-[9px] font-mono leading-none font-light">COMPLETED</span>
                </button>
              </div>
            </div>

            {/* Config details */}
            <div className="bg-[#050917] p-2.5 rounded border border-slate-900 text-[11px] font-mono text-slate-400 leading-normal">
              {selectedScenario === 'expired_pending' && (
                <div>
                  <span className="text-zinc-400 font-bold">Redis Key state:</span> <code className="text-zinc-500">None</code> (expired or unallocated). FastAPI returns <code className="text-zinc-450 font-semibold">PENDING</code>, indicating it is completely safe to submit or re-try payload blocks.
                </div>
              )}
              {selectedScenario === 'active_lock' && (
                <div>
                  <span className="text-amber-400 font-bold">Redis Key state:</span> <code className="text-amber-450">"lock:8a892f..."</code> (prefix matches active lock token). FastAPI returns <code className="text-amber-355 font-semibold">PROCESSING</code> back to upstream pollers.
                </div>
              )}
              {selectedScenario === 'completed' && (
                <div>
                  <span className="text-emerald-400 font-bold">Redis Key state:</span> <code className="text-emerald-450 font-semibold">"Node(24, 48)"</code> (holds the final computed path element string). FastAPI returns <code className="text-emerald-400">COMPLETED</code> with complete coordinates.
                </div>
              )}
            </div>

            {/* Input fields */}
            <div className="flex flex-col gap-1.5 text-left">
              <span className="text-[10px] font-mono text-slate-500 flex justify-between items-center select-none">
                <span>Transaction ID (UUID)</span>
                <button onClick={generateNewUUID} className="text-cyan-400 hover:underline cursor-pointer">Regenerate ID</button>
              </span>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={pollTxId}
                  onChange={(e) => { setPollTxId(e.target.value); setPollResult(null); }}
                  className="bg-[#040812] border border-slate-900 px-3 py-1.5 rounded text-xs text-slate-300 font-mono w-full focus:outline-none focus:border-cyan-500/40 select-all"
                />
              </div>
            </div>

            <button
              onClick={handlePollSimulation}
              disabled={isPolling}
              className={`py-2 px-3 font-mono text-xs font-semibold rounded border transition flex items-center justify-center gap-2 cursor-pointer ${
                isPolling
                  ? 'bg-slate-900 border-slate-900 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 active:scale-95'
              }`}
            >
              {isPolling ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Querying state cache...
                </>
              ) : (
                <>
                  <span>GET /status/{pollTxId.slice(0, 8)}...</span>
                </>
              )}
            </button>
          </div>

          {/* Interactive JSON representation (Right pane) */}
          <div className="lg:col-span-7 flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-500 border-b border-slate-900/60 pb-1.5 select-none">
              <span>FastAPI Mock Console</span>
              <span>REST Response Payload</span>
            </div>

            <div className="flex-1 bg-slate-950 border border-slate-900/80 rounded-lg p-4 font-mono text-xs flex flex-col justify-between min-h-[190px] relative">
              
              {isPolling ? (
                <div className="absolute inset-0 bg-[#040812]/90 flex flex-col items-center justify-center gap-2 rounded-lg">
                  <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
                  <span className="text-[11px] text-cyan-400 animate-pulse font-mono font-light">Acquiring Token State Space...</span>
                </div>
              ) : null}

              {pollResult ? (
                <div className="flex flex-col gap-3 text-left">
                  <div className="flex items-center justify-between border-b border-slate-90a border-slate-900/40 pb-2">
                    <span className="text-emerald-400 font-mono font-bold text-[11px] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" /> HTTP 200 OK
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono font-light">StatusResponse model verified</span>
                  </div>

                  <pre className="text-cyan-300 text-[11px] leading-relaxed select-all overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(pollResult, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
                  <span className="text-slate-600 font-mono text-xs leading-normal font-light">
                    Simulation ready. Select an active lock scenario to mock the Redis state context, then dispatch the status poll.
                  </span>
                </div>
              )}

              <div className="border-t border-slate-900/60 pt-2.5 mt-2 flex flex-col gap-1 text-[10px] text-slate-500 leading-normal text-left">
                <div className="flex items-center gap-1">
                  <span className="text-cyan-405 text-cyan-500 font-bold">URI Path:</span>
                  <code className="text-slate-450 text-slate-400 font-mono text-[9px]">GET /v1/route/gradient-field/status/{pollTxId}</code>
                </div>
                <div>Ensures active thread compute pools yield predictable, non-blocking idempotency constraints.</div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Comparative Official Benchmark Matrix */}
      <div className="bg-[#040811] border border-slate-800/80 rounded-lg p-4 mt-1 flex flex-col gap-3">
        <div className="flex items-center gap-1.5 justify-between">
          <span className="text-xs font-mono font-medium text-slate-200 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" /> Compiled PyO3 FFI vs Pure Python Core
          </span>
          <span className="text-[10px] text-slate-500 font-mono">Benchmarked Grid Resolution Calculations</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full font-mono text-xs text-left">
            <thead>
              <tr className="border-b border-slate-800 text-slate-550 text-slate-500 font-medium">
                <th className="py-2.5 font-normal">Grid Dimensions</th>
                <th className="py-2.5 font-normal text-rose-400">Pure Python Process (GIL)</th>
                <th className="py-2.5 font-normal text-cyan-400">Rust PyO3 FFI Core</th>
                <th className="py-2.5 font-normal text-emerald-400 text-right">Rust Speed multiplier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900 text-slate-300">
              {officialBenchmarks.map((bench, idx) => (
                <tr key={idx} className="hover:bg-slate-900/30">
                  <td className="py-2.5 font-semibold font-sans">{bench.size} Grid</td>
                  <td className="py-2.5 text-rose-400/80">~ {bench.python.toLocaleString()} μs</td>
                  <td className="py-2.5 text-cyan-451 text-cyan-400 font-semibold select-all">~ {bench.rust} μs</td>
                  <td className="py-2.5 text-emerald-452 text-emerald-400 font-bold text-right py-2">{bench.speedup}x Faster</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
