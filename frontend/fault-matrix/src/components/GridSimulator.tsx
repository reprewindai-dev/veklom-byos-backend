import React, { useState, useEffect, useRef } from 'react';
import { GridCell, Agent, FaultMatrixEvent } from '../types';
import { Play, RotateCcw, AlertTriangle, Cpu, Layers, ShieldCheck, Zap } from 'lucide-react';

interface GridSimulatorProps {
  onAppendLedger: (eventType: string, action: string, memo: string, agentId?: string) => void;
  onStateUpdate: (resourceName: string, value: number, unit: string) => void;
}

export default function GridSimulator({ onAppendLedger, onStateUpdate }: GridSimulatorProps) {
  const GRID_SIZE = 10;
  const [grid, setGrid] = useState<GridCell[][]>([]);
  const [start, setStart] = useState<{ x: number; y: number }>({ x: 1, y: 1 });
  const [target, setTarget] = useState<{ x: number; y: number }>({ x: 8, y: 8 });
  const [isSimulating, setIsSimulating] = useState(false);
  const [pathSteps, setPathSteps] = useState<{ x: number; y: number }[]>([]);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [placementMode, setPlacementMode] = useState<'obstacle' | 'start' | 'target'>('obstacle');

  // 120-Agent Workforce Configuration
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activeAgentCount, setActiveAgentCount] = useState(0);

  // Fault Matrix State
  const [faults, setFaults] = useState<FaultMatrixEvent[]>([
    {
      event: "Worker Compute Lag",
      impact: "Thread loses lock mid-flight. Triggering LUA_COMPLETE_IF_MATCH boundary.",
      recovery: "Triggers 409 Conflict. Safe rejection prevents lock stomping.",
      active: false
    },
    {
      event: "Redis Node Outage",
      impact: "Proxy connection socket exception. Lost telemetry metrics.",
      recovery: "Fallback blocks trigger 500 error, returning Rust executor to asyncio queue.",
      active: false
    },
    {
      event: "Asynchronous Retries",
      impact: "Payload duplicate submitted under high-traffic bottleneck.",
      recovery: "Encounters cache.set(..., nx=True) boundary. Fires 202 Accepted tracking link.",
      active: false
    },
    {
      event: "Physical Node Crash",
      impact: "Active thread vanishes instantly. Active locks stay unreturned.",
      recovery: "Distributed lock falls back to natural 60s TTL before subsequent client resolution.",
      active: false
    },
    {
      event: "Heterogeneous Arch Drift",
      impact: "Disparate ARM64 / x86-64 server floats run across mixed farm.",
      recovery: "struct.pack('<...d') little-endian serialization prevents byte deviation.",
      active: false
    }
  ]);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize Grid
  const initializeGrid = () => {
    const newGrid: GridCell[][] = [];
    for (let y = 0; y < GRID_SIZE; y++) {
      const row: GridCell[] = [];
      for (let x = 0; x < GRID_SIZE; x++) {
        let type: GridCell['type'] = 'empty';
        if (x === start.x && y === start.y) type = 'start';
        else if (x === target.x && y === target.y) type = 'target';
        // Add some default obstacles
        else if (
          (x === 3 && y >= 2 && y <= 6) ||
          (x === 6 && y >= 3 && y <= 7)
        ) {
          type = 'obstacle';
        }

        row.push({
          x,
          y,
          type,
          potential: 0,
        });
      }
      newGrid.push(row);
    }
    recalculatePotentialField(newGrid, start, target);
  };

  // Run initial grid load
  useEffect(() => {
    initializeGrid();
    generateAgents();
  }, []);

  // Recalculate potential values of cell (attractive to target, repulsive to obstacles)
  const recalculatePotentialField = (
    currentGrid: GridCell[][],
    startPos: { x: number; y: number },
    targetPos: { x: number; y: number }
  ) => {
    const updated = currentGrid.map((row) =>
      row.map((cell) => {
        // Target distance (attractive field)
        const distToTarget = Math.sqrt((cell.x - targetPos.x) ** 2 + (cell.y - targetPos.y) ** 2);
        
        // Find nearest obstacle distance (repulsive field)
        let minObstacleDist = 99;
        currentGrid.forEach((r) => {
          r.forEach((c) => {
            if (c.type === 'obstacle') {
              const d = Math.sqrt((cell.x - c.x) ** 2 + (cell.y - c.y) ** 2);
              if (d < minObstacleDist) minObstacleDist = d;
            }
          });
        });

        // Compute potential scalar
        let potential = distToTarget * 10;
        if (minObstacleDist < 3) {
          potential += (3 - minObstacleDist) * 35; // Exponential scale for repulsive force
        }

        if (cell.type === 'obstacle') {
          potential = 999;
        }

        return {
          ...cell,
          potential: parseFloat(potential.toFixed(1)),
        };
      })
    );
    setGrid(updated);
  };

  // Update starting/target positions if changed
  useEffect(() => {
    if (grid.length > 0) {
      const updated = grid.map((row) =>
        row.map((cell) => {
          let type = cell.type;
          if (cell.x === start.x && cell.y === start.y) type = 'start';
          else if (cell.x === target.x && cell.y === target.y) type = 'target';
          else if (type === 'start' || type === 'target') type = 'empty';
          return { ...cell, type };
        })
      );
      recalculatePotentialField(updated, start, target);
    }
  }, [start, target]);

  // Generate 120 Agents
  const generateAgents = () => {
    const freshAgents: Agent[] = [];
    const names = [
      "Alpha-Plan", "Beta-Scribe", "Delta-Sync", "Sigma-Crypt", "Omega-Sec", 
      "Gamma-Route", "Tau-Audit", "Zeta-Filter", "Kappa-Guard", "Rho-Ledger"
    ];
    for (let i = 1; i <= 100; i++) {
      const type = i % 3 === 0 ? "Orchestrator" : i % 2 === 0 ? "Execution" : "Validator";
      freshAgents.push({
        id: `AGT-${i.toString().padStart(3, '0')}`,
        name: `${names[i % names.length]}-${i}`,
        type,
        status: 'Idle',
        energyUsed: 0,
        carbonIntensity: 215, // default
        currentTask: 'Awaiting workload allocation',
        progress: 0,
      });
    }
    setAgents(freshAgents);
  };

  const handleCellClick = (x: number, y: number) => {
    if (isSimulating) return;

    if (placementMode === 'start') {
      if (grid[y][x].type === 'obstacle') return;
      setStart({ x, y });
      setPlacementMode('obstacle');
      onAppendLedger('IDENTITY', `Redefined node start boundary coordinates`, `Assigned L3 context start to (${x}, ${y})`);
    } else if (placementMode === 'target') {
      if (grid[y][x].type === 'obstacle') return;
      setTarget({ x, y });
      setPlacementMode('obstacle');
      onAppendLedger('IDENTITY', `Redefined objective target coordinates`, `Assigned L3 path goal to (${x}, ${y})`);
    } else {
      // Toggle obstacle
      if ((x === start.x && y === start.y) || (x === target.x && y === target.y)) return;
      
      const newGrid = [...grid];
      const currentCell = newGrid[y][x];
      newGrid[y][x] = {
        ...currentCell,
        type: currentCell.type === 'obstacle' ? 'empty' : 'obstacle',
      };
      
      recalculatePotentialField(newGrid, start, target);
      onAppendLedger(
        'AUTHORITY', 
        `Toggled path obstacle state`, 
        `${currentCell.type === 'obstacle' ? 'De-allocated' : 'Provisioned'} L1 grid obstruction at coordinates (${x}, ${y})`
      );
    }
  };

  // Perform 8-neighbor gradient descent path calculation
  const runPathfinder = () => {
    if (isSimulating) return;
    setIsSimulating(true);

    // Standard 8-neighbor directions
    const dirX = [0, 0, 1, -1, 1, 1, -1, -1];
    const dirY = [1, -1, 0, 0, 1, -1, 1, -1];

    const visited = new Set<string>();
    const steps: { x: number; y: number }[] = [];
    let currentX = start.x;
    let currentY = start.y;

    steps.push({ x: currentX, y: currentY });
    visited.add(`${currentX},${currentY}`);

    let safetyCounter = 0;
    
    // Check if Worker Compute Lag fault is active (simulates premature abort / conflict)
    const computeLagActive = faults.find(f => f.event === "Worker Compute Lag")?.active;
    const redisOutageActive = faults.find(f => f.event === "Redis Node Outage")?.active;

    onAppendLedger(
      'EXECUTION', 
      'Initializing gradient pathfinding task', 
      `8-neighbor gradient descent routing initiated from (${start.x}, ${start.y}) targeting (${target.x}, ${target.y})`
    );

    while (safetyCounter < 150) {
      safetyCounter++;
      if (currentX === target.x && currentY === target.y) {
        break;
      }

      // Check all 8 neighbors to find local minimum potential
      let minPotential = 1000;
      let nextX = currentX;
      let nextY = currentY;

      for (let i = 0; i < 8; i++) {
        const nx = currentX + dirX[i];
        const ny = currentY + dirY[i];

        if (nx >= 0 && nx < GRID_SIZE && ny >= 0 && ny < GRID_SIZE) {
          const neighbor = grid[ny][nx];
          if (neighbor.type !== 'obstacle' && !visited.has(`${nx},${ny}`)) {
            if (neighbor.potential < minPotential) {
              minPotential = neighbor.potential;
              nextX = nx;
              nextY = ny;
            }
          }
        }
      }

      // If no valid step, backtrack or fail
      if (nextX === currentX && nextY === currentY) {
        // Pathfinder trapped (local minima issue or blocked)
        onAppendLedger('EXECUTION', 'Gradient pathfinder trapped', 'Deadlock reached due to localized target repulsion blocks');
        break;
      }

      currentX = nextX;
      currentY = nextY;
      steps.push({ x: currentX, y: currentY });
      visited.add(`${currentX},${currentY}`);
    }

    setPathSteps(steps);
    setActiveStepIndex(0);

    // Simulate Agent Queue
    triggerAgentBatchSimulation();

    // Trigger visual state update in outer telemetry system
    onStateUpdate("Pathfinding Compute Load", 78 + Math.floor(Math.random() * 15), "Hz");
    onStateUpdate("Active System Thread Locks", steps.length * 3, "Units");
  };

  const triggerAgentBatchSimulation = () => {
    // Pick 12 random agents and spin up simulation
    setActiveAgentCount(12);
    setAgents((prev) => 
      prev.map((agent, i) => {
        if (i < 12) {
          return {
            ...agent,
            status: 'Planning',
            currentTask: `Evaluating potential path state indices...`,
            progress: 10
          };
        }
        return agent;
      })
    );
  };

  // Handle path rendering interval ticks
  useEffect(() => {
    if (isSimulating && activeStepIndex >= 0 && activeStepIndex < pathSteps.length) {
      intervalRef.current = setTimeout(() => {
        // Anomaly updates
        const currentCoord = pathSteps[activeStepIndex];
        
        // Randomly simulate resource change
        onStateUpdate("Active Cell Compute Latency", 45 + Math.floor(Math.random() * 95), "ms");
        onStateUpdate("Gradient Deviation Magnitude", Math.floor(Math.random() * 4)? 12 : 55, "mRad");

        // Simulate agent task states moving along
        setAgents((prev) =>
          prev.map((agent, idx) => {
            if (idx < 12) {
              const progress = Math.min(100, (activeStepIndex / pathSteps.length) * 100);
              let status: Agent['status'] = 'Executing';
              if (progress >= 95) status = 'Done';
              else if (progress >= 70) status = 'Anchoring';
              
              return {
                ...agent,
                status,
                progress: Math.floor(progress),
                energyUsed: agent.energyUsed + 3.2,
                currentTask: status === 'Done' ? 'Completed proof sequence' : `Navigating segment lock index ${activeStepIndex}`
              };
            }
            return agent;
          })
        );

        if (activeStepIndex === pathSteps.length -1) {
          setIsSimulating(false);
          onAppendLedger(
            'PROOF', 
            'Gradient path resolved of execution blocks', 
            `Verification block resolved safely. Target reached in ${pathSteps.length} moves. Registered to Solana.`
          );
        } else {
          setActiveStepIndex((prev) => prev + 1);
        }
      }, 350);
    }

    return () => {
      if (intervalRef.current) clearTimeout(intervalRef.current);
    };
  }, [isSimulating, activeStepIndex]);

  const toggleFault = (index: number) => {
    const updated = [...faults];
    updated[index].active = !updated[index].active;
    setFaults(updated);

    const isActivated = updated[index].active;
    onAppendLedger(
      'AUTHORITY', 
      `${isActivated ? 'Injected' : 'Resolved'} routing system fault: ${updated[index].event}`, 
      `State shifted of fault matrix index. Impact trigger: "${updated[index].impact}"`
    );

    // If we activate a fault, we update the metrics beautifully
    if (isActivated) {
      if (updated[index].event === "Worker Compute Lag") {
        onStateUpdate("Active System Thread Locks", 120, "Units");
        onStateUpdate("Veklom Network Response Delay", 540, "ms");
      } else if (updated[index].event === "Redis Node Outage") {
        onStateUpdate("Telemetry Stream Accuracy", 0, "%");
      }
    } else {
      // Recovery values
      onStateUpdate("Veklom Network Response Delay", 48, "ms");
      onStateUpdate("Telemetry Stream Accuracy", 100, "%");
    }
  };

  const resetAll = () => {
    if (intervalRef.current) clearTimeout(intervalRef.current);
    setIsSimulating(false);
    setPathSteps([]);
    setActiveStepIndex(-1);
    setActiveAgentCount(0);
    generateAgents();
    initializeGrid();
    onAppendLedger('AUTHORITY', 'Reset grid simulation states', 'Restored OOBE substrate parameters to baseline.');
  };

  // Render grid to UI helper
  const renderCellClasses = (cell: GridCell) => {
    let classes = "w-full aspect-square border border-slate-900/65 flex flex-col justify-between p-1 transition-all duration-205 relative select-none ";
    
    // Check if currently traversed step
    const isTraversed = pathSteps.slice(0, activeStepIndex + 1).some(s => s.x === cell.x && s.y === cell.y);
    const isCurrent = activeStepIndex >= 0 && pathSteps[activeStepIndex]?.x === cell.x && pathSteps[activeStepIndex]?.y === cell.y;

    if (cell.type === 'start') {
      classes += "bg-cyan-950/65 text-cyan-400 font-bold border border-cyan-455 shadow-[0_0_12px_rgba(6,182,212,0.4)]";
    } else if (cell.type === 'target') {
      classes += "bg-amber-950/65 text-amber-400 font-bold border border-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.4)]";
    } else if (cell.type === 'obstacle') {
      classes += "bg-[#111622] border border-slate-800 shadow-inner";
    } else if (isCurrent) {
      classes += "bg-cyan-400 text-slate-950 font-black border border-cyan-205 animate-pulse shadow-[0_0_15px_rgba(34,211,238,0.6)]";
    } else if (isTraversed) {
      classes += "bg-cyan-950/25 border border-cyan-500/25 text-cyan-300/80";
    } else {
      classes += "bg-[#05070a]/40 text-slate-700 hover:bg-cyan-950/15 cursor-pointer";
    }

    return classes;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="VeklomGridSimulator">
      
      {/* Simulation Controls & Matrix */}
      <div className="lg:col-span-4 bg-[#0a0c14]/85 border border-cyan-500/20 p-4 rounded-xl flex flex-col justify-between shadow-xl">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Layers className="text-cyan-400 w-5 h-5 animate-pulse" />
            <h3 className="text-md uppercase font-mono font-semibold tracking-wide text-cyan-300">
              OOBE Substrate Simulator
            </h3>
          </div>
          <p className="text-xs text-slate-400 mb-4 font-mono leading-relaxed">
            8-neighbor gradient descent pathfinder. Toggle placement mode to reposition targets, then run the probabilistic model constraint resolver.
          </p>

          {/* Interactive Setters */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <button
              onClick={() => setPlacementMode('obstacle')}
              className={`p-2 rounded text-xs font-mono border transition-all cursor-pointer ${
                placementMode === 'obstacle'
                  ? 'bg-cyan-950/45 border-cyan-400 text-cyan-300 font-semibold shadow-[0_0_8px_rgba(6,182,212,0.25)]'
                  : 'bg-[#111622] border-slate-800/80 text-slate-500 hover:text-slate-400'
              }`}
            >
              🚧 Wall Brush
            </button>
            <button
              onClick={() => setPlacementMode('start')}
              className={`p-2 rounded text-xs font-mono border transition-all cursor-pointer ${
                placementMode === 'start'
                  ? 'bg-cyan-950/45 border-cyan-400 text-cyan-300 font-semibold shadow-[0_0_8px_rgba(6,182,212,0.35)]'
                  : 'bg-[#111622] border-slate-800/80 text-slate-500 hover:text-slate-400'
              }`}
            >
              🟢 Set Start
            </button>
            <button
              onClick={() => setPlacementMode('target')}
              className={`p-2 rounded text-xs font-mono border transition-all cursor-pointer ${
                placementMode === 'target'
                  ? 'bg-amber-950/40 border-amber-500 text-amber-300 font-semibold shadow-[0_0_8px_rgba(245,158,11,0.35)]'
                  : 'bg-[#111622] border-slate-800/80 text-slate-500 hover:text-slate-400'
              }`}
            >
              🎯 Set Target
            </button>
          </div>

          <div className="flex gap-2 mb-6">
            <button
              onClick={runPathfinder}
              disabled={isSimulating}
              className="flex-1 py-3 px-4 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-800/80 disabled:text-slate-650 text-[#05070a] font-mono font-bold rounded-lg text-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-[0_0_15px_rgba(6,182,212,0.35)]"
            >
              <Play className="w-3.5 h-3.5 fill-[#05070a]" /> RUN PATHFINDER
            </button>
            <button
              onClick={resetAll}
              className="py-3 px-3 bg-[#0d1117] hover:bg-slate-850 border border-slate-800 text-slate-350 font-mono rounded-lg text-xs flex items-center justify-center transition-all cursor-pointer"
              title="Reset Grid State"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Workforce Concurrency Panel */}
          <div className="border border-cyan-500/20 bg-cyan-950/5 p-3 rounded-lg shadow-inner">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-mono text-cyan-400 tracking-wider font-semibold">CONCURRENT OPERATIONS</span>
              <span className="text-xs font-mono bg-cyan-950/70 text-cyan-300 px-2 py-0.5 rounded border border-cyan-800/40">120 Workers</span>
            </div>
            
            {/* Visual Queue representation grid */}
            <div className="grid grid-cols-20 gap-[3px] mb-2">
              {Array.from({ length: 120 }).map((_, i) => {
                let colorClass = "bg-[#111622]";
                if (i < activeAgentCount) {
                  const stateColors = ["bg-cyan-400", "bg-sky-400", "bg-amber-400", "bg-blue-400"];
                  colorClass = stateColors[i % stateColors.length];
                }
                return (
                  <div 
                    key={i} 
                    className={`w-full aspect-square rounded-[1px] transition-all duration-350 ${colorClass}`}
                    title={`Worker #${i + 1} State Indicator`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-[9px] font-mono text-slate-500">
              <span>W_ID: AGT-001 - AGT-120</span>
              <span className="text-cyan-400/80 font-bold">Active Queue Concurrency: {activeAgentCount} Threads</span>
            </div>
          </div>
        </div>

        {/* Fault Engine Metrics */}
        <div className="mt-4 pt-4 border-t border-slate-900">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-2">
            System Lock Telemetry (L2)
          </span>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-[#0d1117] p-2 rounded border border-slate-800/80">
              <span className="text-slate-500 block text-[9px]">KV CACHE HITS</span>
              <span className="text-cyan-400 font-semibold">{isSimulating ? "98.4%" : "100.0%"}</span>
            </div>
            <div className="bg-[#0d1117] p-2 rounded border border-slate-800/80">
              <span className="text-slate-500 block text-[9px]">PAGEDATTENTION</span>
              <span className="text-cyan-400 font-semibold text-xs">Active (16kb block)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Pathfinder Grid */}
      <div className="lg:col-span-5 bg-[#0a0c14]/85 border border-cyan-500/20 p-4 rounded-xl flex flex-col items-center justify-between shadow-xl">
        <div className="w-full flex justify-between items-center mb-3">
          <span className="text-xs font-mono text-cyan-400 font-semibold tracking-wider">VECTOR SPACE DESCENT MATRIX</span>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            8-neighbor potential fields
          </span>
        </div>

        {/* Main 2D Grid */}
        <div className="w-full max-w-[420px] aspect-square grid grid-cols-10 gap-[2px] bg-slate-900 bg-opacity-20 p-2 rounded-lg border border-slate-800/80 shadow-2xl">
          {grid.map((row) =>
            row.map((cell) => {
              const isStart = cell.x === start.x && cell.y === start.y;
              const isTarget = cell.x === target.x && cell.y === target.y;
              const cellPotential = isTarget ? 0 : cell.potential;

              return (
                <div
                  key={`${cell.x}-${cell.y}`}
                  onClick={() => handleCellClick(cell.x, cell.y)}
                  className={renderCellClasses(cell)}
                >
                  <span className="text-[9px] font-mono opacity-25 absolute top-0.5 left-1">
                    {cell.x},{cell.y}
                  </span>
                  <span className="text-[10px] font-mono font-medium self-end w-full text-right leading-none pb-0.5 pr-0.5">
                    {cell.type === 'obstacle' ? '█' : cellPotential}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Grid Legends */}
        <div className="w-full grid grid-cols-3 gap-2 mt-4 text-[10px] font-mono text-slate-400 border-t border-slate-900 pt-3">
          <div className="flex items-center gap-1.5 justify-center">
            <span className="w-2.5 h-2.5 bg-cyan-955 border border-cyan-400 rounded-sm inline-block animate-pulse" />
            <span>🟢 Start</span>
          </div>
          <div className="flex items-center gap-1.5 justify-center">
            <span className="w-2.5 h-2.5 bg-amber-950 border border-amber-400 rounded-sm inline-block" />
            <span>🎯 Target</span>
          </div>
          <div className="flex items-center gap-1.5 justify-center">
            <span className="w-2.5 h-2.5 bg-slate-900 border border-slate-750 rounded-sm inline-block" />
            <span>█ Obstacles</span>
          </div>
        </div>
      </div>

      {/* Veklom Routing Fault Matrix (Runbook) */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <div className="bg-[#0a0c14]/85 border border-cyan-500/20 p-4 rounded-xl flex-1 shadow-xl">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="text-amber-500 w-5 h-5 animate-pulse" />
            <h3 className="text-md uppercase font-mono font-semibold tracking-wide text-cyan-300">
              Fault Injection Matrix
            </h3>
          </div>
          <p className="text-xs text-slate-400 mb-4 font-mono leading-relaxed">
            Inject deterministic routing degradation vectors on the probabilistic plane and monitor compensation protocols in real time.
          </p>

          <div className="flex flex-col gap-3">
            {faults.map((f, i) => (
              <div 
                key={f.event} 
                className={`p-3 rounded-lg border transition-all ${
                  f.active 
                    ? 'bg-amber-950/20 border-amber-500/80 shadow-[0_0_12px_rgba(245,158,11,0.2)]' 
                    : 'bg-[#0d1117] border-slate-900/60 hover:order-slate-800'
                }`}
              >
                <div className="flex justify-between items-center mb-1.5">
                  <span className={`text-xs font-mono font-bold ${f.active ? 'text-amber-400' : 'text-slate-300'}`}>
                    {f.event}
                  </span>
                  
                  {/* Slider Toggle */}
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={f.active} 
                      onChange={() => toggleFault(i)} 
                    />
                    <div className="w-7 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 peer-checked:after:bg-amber-400 after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-amber-900/60 transition-all"></div>
                  </label>
                </div>
                
                {f.active && (
                  <div className="text-[10px] font-mono text-slate-400 leading-relaxed border-t border-amber-900/40 mt-1.5 pt-1.5 animate-fade-in">
                    <span className="text-amber-500/80 uppercase font-extrabold mr-1">IMPACT:</span> {f.impact}
                    <div className="text-cyan-400/95 mt-1">
                      <span className="text-cyan-500 uppercase font-extrabold mr-1">RECOVERY:</span> {f.recovery}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      
    </div>
  );
}
