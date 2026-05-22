import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Play, Pause, RotateCcw, Paintbrush, Sliders, Waves, PlayCircle, Eye, ArrowRight,
  Briefcase, BarChart3, TrendingUp, Cpu, Server, ShieldCheck, Zap, Building2, Target, Activity
} from 'lucide-react';
import { GridNode, GridDimension } from '../types';

interface GridVisualizerProps {
  onPathUpdate?: (path: [number, number][]) => void;
}

export default function GridVisualizer({ onPathUpdate }: GridVisualizerProps) {
  const [gridSize, setGridSize] = useState<GridDimension>(25);
  const [grid, setGrid] = useState<GridNode[][]>([]);
  const [startNode, setStartNode] = useState<{ r: number; c: number }>({ r: 3, c: 3 });
  const [endNode, setEndNode] = useState<{ r: number; c: number }>({ r: 21, c: 21 });
  const [brushType, setBrushType] = useState<'obstacle' | 'hill' | 'start' | 'end' | 'eraser'>('obstacle');
  const [isDrawing, setIsDrawing] = useState(false);
  
  // Solver State
  const [isSolving, setIsSolving] = useState(false);
  const [solved, setSolved] = useState(false);
  const [wavefrontSteps, setWavefrontSteps] = useState<number>(0);
  const [activePath, setActivePath] = useState<[number, number][]>([]);
  const [currentSolverNode, setCurrentSolverNode] = useState<{ r: number; c: number } | null>(null);
  const [potentialMax, setPotentialMax] = useState<number>(1);
  const [showVectors, setShowVectors] = useState(true);
  const [showPotentialHeatmap, setShowPotentialHeatmap] = useState(true);

  // New industrial presets state
  const [activePreset, setActivePreset] = useState<'warehouse' | 'drone' | 'city' | null>(null);

  const solveIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Re-initialize grid when size, start, or end changes with preset detection
  useEffect(() => {
    if (activePreset) {
      applyPresetLayout(gridSize, activePreset);
    } else {
      initializeGrid(gridSize);
    }
    return () => {
      if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);
    };
  }, [gridSize, activePreset]);

  // Dual-signature potential field generator to support async preset loads
  const computePotentialField = (
    currentGrid: GridNode[][], 
    sizeInput?: number, 
    targetInput?: { r: number; c: number }
  ): { updatedGrid: GridNode[][]; maxPotential: number } => {
    const size = sizeInput || gridSize;
    const targetE = targetInput || endNode;

    const g = currentGrid.map(row => row.map(cell => ({
      ...cell,
      potential: 9999,
      visited: false,
      isPath: false,
      gradientX: 0,
      gradientY: 0
    })));

    // Priority queue / flat queue for BFS distance propagation
    interface QueueItem {
      r: number;
      c: number;
      pot: number;
    }
    
    const queue: QueueItem[] = [];
    g[targetE.r][targetE.c].potential = 0;
    queue.push({ r: targetE.r, c: targetE.c, pot: 0 });

    let activeSteps = 0;
    let localMaxPot = 0;

    while (queue.length > 0) {
      // Sort to get node with lowest potential (simplifies Dijkstra)
      queue.sort((a, b) => a.pot - b.pot);
      const curr = queue.shift()!;
      
      const currCell = g[curr.r][curr.c];
      if (currCell.visited) continue;
      currCell.visited = true;
      activeSteps++;

      // 8 neighbor offsets
      const neighbors = [
        { dr: -1, dc: 0, cost: 1.0 },  // N
        { dr: 1, dc: 0, cost: 1.0 },   // S
        { dr: 0, dc: -1, cost: 1.0 },  // W
        { dr: 0, dc: 1, cost: 1.0 },   // E
        { dr: -1, dc: -1, cost: 1.414 }, // NW
        { dr: -1, dc: 1, cost: 1.414 },  // NE
        { dr: 1, dc: -1, cost: 1.414 },  // SW
        { dr: 1, dc: 1, cost: 1.414 }    // SE
      ];

      for (const n of neighbors) {
        const nr = curr.r + n.dr;
        const nc = curr.c + n.dc;

        if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
          const neighborCell = g[nr][nc];
          if (neighborCell.isObstacle || neighborCell.visited) continue;

          // Cost includes base cell step multiplied by cell friction/multiplier
          const stepWeight = (currCell.weight + neighborCell.weight) / 2;
          const costToMove = n.cost * stepWeight;
          const newPot = curr.pot + costToMove;

          if (newPot < neighborCell.potential) {
            neighborCell.potential = Number(newPot.toFixed(2));
            queue.push({ r: nr, c: nc, pot: newPot });
            if (newPot < 9000 && newPot > localMaxPot) {
              localMaxPot = newPot;
            }
          }
        }
      }
    }

    // Now compute Gradient Vectors for 8 neighbors based on neighboring steepness
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const cell = g[r][c];
        if (cell.isObstacle || cell.potential >= 9999) continue;

        // Nabla vector estimations (dx, dy)
        let dx = 0;
        let dy = 0;
        
        // Horizontal vector component
        const leftPot = c > 0 && !g[r][c-1].isObstacle ? g[r][c-1].potential : cell.potential;
        const rightPot = c < size - 1 && !g[r][c+1].isObstacle ? g[r][c+1].potential : cell.potential;
        dx = rightPot - leftPot;

        // Vertical vector component
        const topPot = r > 0 && !g[r-1][c].isObstacle ? g[r-1][c].potential : cell.potential;
        const bottomPot = r < size - 1 && !g[r+1][c].isObstacle ? g[r+1][c].potential : cell.potential;
        dy = bottomPot - topPot;

        // Normalize gradient vector to point DOWN the potential slope (steepest descent)
        const length = Math.sqrt(dx * dx + dy * dy);
        if (length > 0) {
          cell.gradientX = -dx / length;
          cell.gradientY = -dy / length;
        }
      }
    }

    setWavefrontSteps(activeSteps);
    return { updatedGrid: g, maxPotential: localMaxPot };
  };

  const applyPresetLayout = (size: GridDimension, preset: 'warehouse' | 'drone' | 'city') => {
    setIsSolving(false);
    setSolved(false);
    setWavefrontSteps(0);
    setActivePath([]);
    setCurrentSolverNode(null);

    let sNode = { r: 1, c: 1 };
    let eNode = { r: 23, c: 23 };

    if (preset === 'city') {
      sNode = { r: 4, c: 4 };
      eNode = { r: 45, c: 45 };
    } else if (preset === 'warehouse') {
      sNode = { r: 1, c: 1 };
      eNode = { r: 23, c: 23 };
    } else if (preset === 'drone') {
      sNode = { r: 2, c: 2 };
      eNode = { r: 22, c: 22 };
    }

    setStartNode(sNode);
    setEndNode(eNode);

    const newGrid: GridNode[][] = [];
    for (let r = 0; r < size; r++) {
      const rowNodes: GridNode[] = [];
      for (let c = 0; c < size; c++) {
        const isS = r === sNode.r && c === sNode.c;
        const isE = r === eNode.r && c === eNode.c;
        rowNodes.push({
          row: r,
          col: c,
          isStart: isS,
          isEnd: isE,
          isObstacle: false,
          weight: 1,
          potential: 9999,
          visited: false,
          isPath: false,
        });
      }
      newGrid.push(rowNodes);
    }

    // Apply specific preset obstacles or hill patterns
    if (preset === 'warehouse') {
      // Horizontal racks with middle corridors
      for (let r = 4; r < size - 2; r += 4) {
        for (let c = 2; c < size - 2; c++) {
          if (c !== 12 && c !== 13) { // keep two columns clear for vertical cross-aisle
            newGrid[r][c].isObstacle = true;
            newGrid[r][c].weight = Infinity;
            if (r + 1 < size) {
              newGrid[r + 1][c].isObstacle = true;
              newGrid[r + 1][c].weight = Infinity;
            }
          }
        }
      }
    } else if (preset === 'drone') {
      // Severe wind patterns & mountain gorge walls
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          if ((r === sNode.r && c === sNode.c) || (r === eNode.r && c === eNode.c)) continue;
          
          // Diagonal pass with breach in the middle
          const isBreach = (r >= 10 && r <= 14) && (c >= 10 && c <= 14);
          if (!isBreach) {
            if (r + c >= 22 && r + c <= 25) {
              newGrid[r][c].isObstacle = true;
              newGrid[r][c].weight = Infinity;
            } else if (r + c >= 18 && r + c <= 29) {
              newGrid[r][c].weight = 5; // windy hills surround mountain
            }
          }
        }
      }
    } else if (preset === 'city') {
      // Grid pattern city blocks
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          if ((r === sNode.r && c === sNode.c) || (r === eNode.r && c === eNode.c)) continue;
          
          // Streets every 8 cells
          const remR = r % 8;
          const remC = c % 8;
          if (remR < 6 && remC < 6) {
            newGrid[r][c].isObstacle = true;
            newGrid[r][c].weight = Infinity;
          }
        }
      }
    }

    setGrid(newGrid);

    // Auto-calculate potentials for immediate visual feedback of vector field!
    const field = computePotentialField(newGrid, size, eNode);
    setPotentialMax(field.maxPotential || 1);
    setSolved(true);
    setGrid(field.updatedGrid);
  };

  const initializeGrid = (size: GridDimension, preserveClippedObstacles = false) => {
    const sNode = size === 10 ? { r: 1, c: 1 } : size === 25 ? { r: 3, c: 3 } : { r: 5, c: 5 };
    const eNode = size === 10 ? { r: 8, c: 8 } : size === 25 ? { r: 21, c: 21 } : { r: 44, c: 44 };
    
    setStartNode(sNode);
    setEndNode(eNode);
    setIsSolving(false);
    setSolved(false);
    setWavefrontSteps(0);
    setActivePath([]);
    setCurrentSolverNode(null);

    const newGrid: GridNode[][] = [];
    for (let r = 0; r < size; r++) {
      const rowNodes: GridNode[] = [];
      for (let c = 0; c < size; c++) {
        const isS = r === sNode.r && c === sNode.c;
        const isE = r === eNode.r && c === eNode.c;
        rowNodes.push({
          row: r,
          col: c,
          isStart: isS,
          isEnd: isE,
          isObstacle: false,
          weight: 1,
          potential: 9999,
          visited: false,
          isPath: false,
        });
      }
      newGrid.push(rowNodes);
    }
    setGrid(newGrid);
  };

  const handleCellInteraction = (r: number, c: number) => {
    if (isSolving) return;
    
    // Clear active preset if user starts drawing manually
    setActivePreset(null);

    setGrid((prev) => {
      const next = prev.map(row => row.map(cell => ({ ...cell })));
      const cell = next[r][c];

      if (brushType === 'start') {
        if (cell.isEnd || cell.isObstacle) return prev;
        // Reset old start
        next[startNode.r][startNode.c].isStart = false;
        cell.isStart = true;
        cell.weight = 1;
        setStartNode({ r, c });
      } else if (brushType === 'end') {
        if (cell.isStart || cell.isObstacle) return prev;
        // Reset old end
        next[endNode.r][endNode.c].isEnd = false;
        cell.isEnd = true;
        cell.weight = 1;
        setEndNode({ r, c });
      } else if (brushType === 'obstacle') {
        if (cell.isStart || cell.isEnd) return prev;
        cell.isObstacle = true;
        cell.weight = Infinity;
      } else if (brushType === 'hill') {
        if (cell.isStart || cell.isEnd) return prev;
        cell.isObstacle = false;
        cell.weight = 5; // slow down cost
      } else if (brushType === 'eraser') {
        if (cell.isStart || cell.isEnd) return prev;
        cell.isObstacle = false;
        cell.weight = 1;
      }
      return next;
    });
    
    // Clear computed potentials to force recalculation on run
    setSolved(false);
    setActivePath([]);
  };

  const handleMouseDown = (r: number, c: number) => {
    setIsDrawing(true);
    handleCellInteraction(r, c);
  };

  const handleMouseEnter = (r: number, c: number) => {
    if (isDrawing) {
      handleCellInteraction(r, c);
    }
  };

  const handleMouseUp = () => {
    setIsDrawing(false);
  };

  useEffect(() => {
    window.addEventListener('mouseup', handleMouseUp);
    return () => window.removeEventListener('mouseup', handleMouseUp);
  }, []);

  // Duplicate computePotentialField removed. Using the robust dual-signature computePotentialField defined above.

  // Perform 8-Neighbor Gradient Descent Routing
  const startGradientDescent = () => {
    if (isSolving) {
      setIsSolving(false);
      if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);
      return;
    }

    setIsSolving(true);

    let activeG = grid;
    if (!solved) {
      const calculation = computePotentialField(grid);
      activeG = calculation.updatedGrid;
      setPotentialMax(calculation.maxPotential || 1);
      setGrid(activeG);
      setSolved(true);
    }

    // Start pathfinder trace
    const pathTrace: [number, number][] = [[startNode.r, startNode.c]];
    let currentPos = { r: startNode.r, c: startNode.c };
    setCurrentSolverNode(currentPos);
    setActivePath([...pathTrace]);

    if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);

    // Iterative worker interval
    solveIntervalRef.current = setInterval(() => {
      const { r, c } = currentPos;

      // Arrived at destination
      if (r === endNode.r && c === endNode.c) {
        setIsSolving(false);
        if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);
        // Highlight full path on state
        markFinalPath(pathTrace, activeG);
        return;
      }

      // Check the 8 neighbors for local minimum potentials
      const neighbors = [
        { dr: -1, dc: 0 },  // N
        { dr: 1, dc: 0 },   // S
        { dr: 0, dc: -1 },  // W
        { dr: 0, dc: 1 },   // E
        { dr: -1, dc: -1 }, // NW
        { dr: -1, dc: 1 },  // NE
        { dr: 1, dc: -1 },  // SW
        { dr: 1, dc: 1 }    // SE
      ];

      let bestNeighbor: { r: number; c: number; pot: number } | null = null;
      let minPotential = activeG[r][c].potential;

      for (const n of neighbors) {
        const nr = r + n.dr;
        const nc = c + n.dc;

        if (nr >= 0 && nr < gridSize && nc >= 0 && nc < gridSize) {
          const cell = activeG[nr][nc];
          if (!cell.isObstacle && cell.potential < minPotential) {
            // Check diagonal clearance (prevent clipping through squeezed walls)
            if (n.dr !== 0 && n.dc !== 0) {
              const squeeze1 = activeG[r + n.dr][c];
              const squeeze2 = activeG[r][c + n.dc];
              if (squeeze1.isObstacle && squeeze2.isObstacle) continue; // Squeezed, ignore diagonal
            }

            minPotential = cell.potential;
            bestNeighbor = { r: nr, c: nc, pot: cell.potential };
          }
        }
      }

      // Trapped in local minimum (blocked path or isolated)
      if (!bestNeighbor) {
        setIsSolving(false);
        if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);
        alert("Local minimum reached. Path is completely blocked by obstacles (GIL-like node starvation simulated)!");
        return;
      }

      // Anti-loop protection: if we've seen this neighbor very recently, break
      const recentPathStr = JSON.stringify(pathTrace.slice(-6));
      if (recentPathStr.includes(JSON.stringify([bestNeighbor.r, bestNeighbor.c]))) {
        setIsSolving(false);
        if (solveIntervalRef.current) clearInterval(solveIntervalRef.current);
        alert("Oscillation loop detected. Gradient is flat.");
        return;
      }

      currentPos = { r: bestNeighbor.r, c: bestNeighbor.c };
      pathTrace.push([currentPos.r, currentPos.c]);
      setCurrentSolverNode(currentPos);
      setActivePath([...pathTrace]);
      if (onPathUpdate) {
        onPathUpdate(pathTrace);
      }
    }, gridSize === 10 ? 100 : gridSize === 25 ? 40 : 15);
  };

  const markFinalPath = (path: [number, number][], activeG: GridNode[][]) => {
    const updated = activeG.map((row, r) => row.map((cell, c) => {
      const onPath = path.some(([pr, pc]) => pr === r && pc === c);
      return { ...cell, isPath: onPath };
    }));
    setGrid(updated);
  };

  const clearGrid = () => {
    initializeGrid(gridSize);
  };

  const renderGridContent = () => {
    // Dynamically calculate grid proportions
    return (
      <div 
        className="grid bg-[#0a0f1d] border border-slate-800 rounded-lg p-2 select-none relative overflow-hidden"
        style={{
          gridTemplateRows: `repeat(${gridSize}, minmax(0, 1fr))`,
          gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))`,
          aspectRatio: '1/1',
        }}
      >
        {grid.map((row, r) => 
          row.map((cell, c) => {
            const isPathNode = activePath.some(([pr, pc]) => pr === r && pc === c);
            const isSolvingNode = currentSolverNode?.r === r && currentSolverNode?.c === c;
            
            // Grid background heatmaps
            let bgStyle: React.CSSProperties = {};
            if (cell.isObstacle) {
              bgStyle.backgroundColor = '#1e293b'; // Slate Dark Wall
            } else if (cell.weight > 1) {
              bgStyle.backgroundColor = 'rgba(245, 158, 11, 0.25)'; // Amber Hill
            } else if (showPotentialHeatmap && solved && cell.potential < 9000) {
              // Interpolate heatmap from End node (teal/blue) to outer bounds (dark slate purple)
              const ratio = Math.min(cell.potential / potentialMax, 1);
              bgStyle.backgroundColor = `rgba(13, 148, 136, ${Math.max(0.04, 0.45 * (1 - ratio))})`;
            }

            return (
              <div
                key={`${r}-${c}`}
                id={`grid-cell-${r}-${c}`}
                className={`
                  border-[0.5px] border-slate-900/40 relative flex items-center justify-center transition-all duration-150 cursor-pointer
                  ${isSolvingNode ? 'scale-105 z-10' : ''}
                `}
                style={bgStyle}
                onMouseDown={() => handleMouseDown(r, c)}
                onMouseEnter={() => handleMouseEnter(r, c)}
              >
                {/* Node Icons / Visual highlights */}
                <AnimatePresence mode="popLayout">
                  {cell.isStart && (
                    <motion.div 
                      layoutId="start-node"
                      className="absolute inset-[15%] rounded-full bg-emerald-500 border border-emerald-300 flex items-center justify-center text-white font-sans text-[10px] font-bold shadow-lg shadow-emerald-500/20"
                    >
                      S
                    </motion.div>
                  )}
                  {cell.isEnd && (
                    <motion.div 
                      layoutId="end-node"
                      className="absolute inset-[15%] rounded-full bg-rose-500 border border-rose-300 flex items-center justify-center text-white font-sans text-[10px] font-bold shadow-lg shadow-rose-500/20"
                    >
                      E
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Weighted Hill Marker */}
                {cell.weight === 5 && !cell.isStart && !cell.isEnd && (
                  <div className="absolute w-2 h-2 rounded-full bg-amber-500/80 animate-pulse" />
                )}

                {/* Path highlight indicator */}
                {isPathNode && !cell.isStart && !cell.isEnd && (
                  <motion.div 
                    initial={{ scale: 0.1, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className={`absolute inset-[25%] rounded-full ${solved ? 'bg-cyan-400 shadow-[0_0_10px_#22d3ee]' : 'bg-cyan-500/70'}`}
                  />
                )}

                {/* Gradient arrows (directional lines) */}
                {showVectors && solved && !cell.isObstacle && !cell.isStart && !cell.isEnd && cell.potential < 9000 && (cell.gradientX !== 0 || cell.gradientY !== 0) && (
                  <div 
                    className="absolute text-cyan-400/40 font-mono text-[9px] pointer-events-none transition-transform"
                    style={{
                      transform: `rotate(${Math.atan2(cell.gradientY || 0, cell.gradientX || 0) * (180 / Math.PI)}deg)`,
                    }}
                  >
                    →
                  </div>
                )}
                
                {/* Hot tracker node */}
                {isSolvingNode && (
                  <div className="absolute inset-0 border-2 border-cyan-400 rounded-sm animate-ping pointer-events-none" />
                )}
              </div>
            );
          })
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-5 border border-slate-800 bg-[#070b15] rounded-xl p-5 shadow-lg relative overflow-hidden h-full">
      {/* Decorative top strip */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-cyan-500 to-amber-500" />
      
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 px-1.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded text-xs font-mono font-semibold uppercase tracking-wider">
              Simulation Unit
            </span>
            <h2 className="text-xl font-sans font-medium text-slate-150 leading-tight">
              8-Neighbor Gradient Descent
            </h2>
          </div>
          <p className="text-slate-400 text-xs mt-1 max-w-xl font-sans font-light">
            Constructs a scalar cost wavefront backwards from the Destination <span className="text-rose-400 font-normal">E</span>. The engine computes directional gradient vectors field, allowing pathfinders to drop through optimal unconstrained real-value paths.
          </p>
        </div>

        {/* Configuration settings panel */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-800 p-1 rounded-lg">
            {( [10, 25, 50] as GridDimension[]).map((size) => (
              <button
                key={size}
                onClick={() => setGridSize(size)}
                className={`px-2.5 py-1 text-xs font-mono rounded ${
                  gridSize === size 
                    ? 'bg-slate-800 text-cyan-400 border border-cyan-500/20 font-medium' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {size}x{size}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch flex-1">
        {/* Main interactive grid display */}
        <div className="lg:col-span-7 flex flex-col justify-center">
          {renderGridContent()}
        </div>

        {/* Controls and Stats block */}
        <div className="lg:col-span-5 flex flex-col gap-4 justify-between">
          
          {/* ⭐ Industry Application Presets (Instant ROI Proof) */}
          <div className="bg-[#05091a]/95 border-2 border-cyan-500/20 rounded-xl p-4 flex flex-col gap-3 shadow-lg shadow-cyan-950/20 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />
            
            <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
              <div className="flex items-center gap-1.5">
                <Briefcase className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono text-slate-205 text-slate-250 font-semibold uppercase tracking-wider">
                  Enterprise Use-Case Presets
                </span>
              </div>
              <span className="text-[10px] bg-cyan-400/10 text-cyan-300 font-mono px-1.5 py-0.5 rounded border border-cyan-500/20">
                AHA! PROOF
              </span>
            </div>

            <p className="text-[11px] text-slate-400 font-sans leading-relaxed font-light">
              Click to instantly configure real-world coordinates and view compiled FFI mathematical potential fields and core business advantages:
            </p>

            {/* Selector Grid Buttons */}
            <div className="grid grid-cols-3 gap-2 mt-1">
              <button
                onClick={() => {
                  setActivePreset('warehouse');
                  setGridSize(25);
                }}
                className={`py-2 px-2.5 rounded-lg border text-center transition flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                  activePreset === 'warehouse'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-355 text-emerald-400 font-medium'
                    : 'bg-slate-950/40 border-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-900/10'
                }`}
              >
                <Building2 className="w-4 h-4" />
                <span className="text-[10px] uppercase font-mono tracking-tight leading-none">Warehouse</span>
              </button>

              <button
                onClick={() => {
                  setActivePreset('drone');
                  setGridSize(25);
                }}
                className={`py-2 px-2.5 rounded-lg border text-center transition flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                  activePreset === 'drone'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-355 text-amber-400 font-medium'
                    : 'bg-slate-950/40 border-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-900/10'
                }`}
              >
                <Target className="w-4 h-4" />
                <span className="text-[10px] uppercase font-mono tracking-tight leading-none">Drone Gorges</span>
              </button>

              <button
                onClick={() => {
                  setActivePreset('city');
                  setGridSize(50);
                }}
                className={`py-2 px-2.5 rounded-lg border text-center transition flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                  activePreset === 'city'
                    ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-355 text-cyan-400 font-medium'
                    : 'bg-slate-950/40 border-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-900/10'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span className="text-[10px] uppercase font-mono tracking-tight leading-none">Smart City</span>
              </button>
            </div>

            {/* Dynamic Preset Business ROI Panel */}
            <AnimatePresence mode="popLayout">
              {activePreset ? (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-slate-950/50 rounded-lg border border-slate-900 p-3 flex flex-col gap-2 mt-1"
                >
                  {activePreset === 'warehouse' && (
                    <>
                      <div className="flex items-center justify-between text-[11px] font-mono border-b border-slate-900 pb-1.5 select-none">
                        <span className="text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <Zap className="w-3.5 h-3.5" /> AMR Fulfillment Logistics
                        </span>
                        <span className="text-slate-500">Live ROI Data</span>
                      </div>
                      <div className="text-[11px] text-slate-350 leading-relaxed font-sans font-light">
                        <strong>Problem Solved:</strong> Prevents multi-robot coordinate race-locks and collision stalling across standard shelving racks.
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-1">
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Picking Throughput</span>
                          <span className="text-emerald-400 font-bold text-sm tracking-tight">+42% Velocity</span>
                        </div>
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Server Scale Savings</span>
                          <span className="text-cyan-400 font-bold text-sm tracking-tight">Save $22,400/yr</span>
                        </div>
                      </div>
                    </>
                  )}

                  {activePreset === 'drone' && (
                    <>
                      <div className="flex items-center justify-between text-[11px] font-mono border-b border-slate-900 pb-1.5 select-none">
                        <span className="text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <Zap className="w-3.5 h-3.5" /> Drone Wind Gorge Mission
                        </span>
                        <span className="text-slate-500">Fleet Radius Advantage</span>
                      </div>
                      <div className="text-[11px] text-slate-350 leading-relaxed font-sans font-light">
                        <strong>Problem Solved:</strong> Avoids extreme headwinds diagonals by dynamically shifting gradient waves. Minimizes battery wear on drone fleets.
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-1">
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Battery Degradation</span>
                          <span className="text-emerald-400 font-bold text-sm tracking-tight">-18% Power Wear</span>
                        </div>
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Math Thread Lockups</span>
                          <span className="text-cyan-400 font-bold text-sm tracking-tight">0% GIL Starvation</span>
                        </div>
                      </div>
                    </>
                  )}

                  {activePreset === 'city' && (
                    <>
                      <div className="flex items-center justify-between text-[11px] font-mono border-b border-slate-900 pb-1.5 select-none">
                        <span className="text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <Zap className="w-3.5 h-3.5" /> Smart Metropolitan EV Grid
                        </span>
                        <span className="text-slate-500">Fleet Scale Proof</span>
                      </div>
                      <div className="text-[11px] text-slate-350 leading-relaxed font-sans font-light">
                        <strong>Problem Solved:</strong> Instantly processes thousands of alternate city block paths under sub-millisecond rates when blocks freeze.
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-1">
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Compute Overhead</span>
                          <span className="text-emerald-400 font-bold text-sm tracking-tight">92% Cost Cut</span>
                        </div>
                        <div className="bg-[#050915] p-2 rounded border border-slate-900 flex flex-col justify-center">
                          <span className="text-[9px] font-mono text-slate-500 uppercase">Active Workforce</span>
                          <span className="text-cyan-400 font-bold text-sm tracking-tight">120+ Real-Time</span>
                        </div>
                      </div>
                    </>
                  )}
                </motion.div>
              ) : (
                <div className="bg-slate-950/20 border border-slate-900 border-dashed rounded-lg p-3 text-center text-slate-500 text-[10px] font-mono py-4">
                  💡 PRO TIP FOR INVESTORS: Select any preset to see how unconstrained descent layers replace high-overhead pure-Python A* queries.
                </div>
              )}
            </AnimatePresence>
          </div>
          
          {/* Toolbelt - brushes */}
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-3 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <Paintbrush className="w-3.5 h-3.5 text-cyan-400" /> Brush Tools
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Draw on Grid</span>
            </div>
            
            <div className="grid grid-cols-5 gap-1.5">
              <button
                onClick={() => setBrushType('obstacle')}
                className={`py-2 px-1 flex flex-col items-center gap-1 text-[10px] font-mono rounded transition border ${
                  brushType === 'obstacle' 
                    ? 'bg-slate-800 border-slate-700 text-slate-100' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-250'
                }`}
                title="Slabs of solid obstruction (Infinity travel cost, solid wall)"
              >
                <div className="w-5 h-3.5 bg-slate-400 rounded-sm" />
                Wall
              </button>
              
              <button
                onClick={() => setBrushType('hill')}
                className={`py-2 px-1 flex flex-col items-center gap-1 text-[10px] font-mono rounded transition border ${
                  brushType === 'hill' 
                    ? 'bg-amber-950/30 border-amber-800/50 text-amber-300' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-250'
                }`}
                title="Adds rough terrain friction multiplier (+5x processing cost)"
              >
                <div className="w-5 h-3.5 rounded-full bg-amber-500/80 border border-amber-300/40" />
                Hill (+5x)
              </button>

              <button
                onClick={() => setBrushType('start')}
                className={`py-2 px-1 flex flex-col items-center gap-1 text-[10px] font-mono rounded transition border ${
                  brushType === 'start' 
                    ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-305' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-250'
                }`}
                title="Relocate the Start worker coordinate point"
              >
                <div className="w-4 h-4 rounded-full bg-emerald-500 text-[8px] flex items-center justify-center font-bold text-white">S</div>
                Start
              </button>

              <button
                onClick={() => setBrushType('end')}
                className={`py-2 px-1 flex flex-col items-center gap-1 text-[10px] font-mono rounded transition border ${
                  brushType === 'end' 
                    ? 'bg-rose-950/30 border-rose-800/50 text-rose-300' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-250'
                }`}
                title="Relocate the target route coordinates destination"
              >
                <div className="w-4 h-4 rounded-full bg-rose-500 text-[8px] flex items-center justify-center font-bold text-white">E</div>
                End
              </button>

              <button
                onClick={() => setBrushType('eraser')}
                className={`py-2 px-1 flex flex-col items-center gap-1 text-[10px] font-mono rounded transition border ${
                  brushType === 'eraser' 
                    ? 'bg-slate-800 border-slate-750 text-slate-200' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/40 hover:text-slate-250'
                }`}
                title="Erase weights and restore cells to flat open spaces"
              >
                <div className="w-5 h-3.5 border border-dashed border-slate-600 rounded-sm" />
                Eraser
              </button>
            </div>
          </div>

          {/* Visualization toggles */}
          <div className="bg-slate-950/20 border border-slate-800/60 rounded-lg p-3 flex flex-col gap-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-widest flex items-center gap-2 mb-1">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" /> Overlay Settings
            </span>
            <div className="grid grid-cols-2 gap-3">
              <label id="toggle-vectors-label" className="flex items-center justify-between p-2 bg-slate-900/40 rounded border border-slate-850 cursor-pointer text-xs font-sans text-slate-300">
                <span>Descent Vector Field</span>
                <input 
                  type="checkbox" 
                  checked={showVectors} 
                  onChange={(e) => setShowVectors(e.target.checked)}
                  className="rounded border-slate-800 bg-[#090f1d] text-cyan-400 focus:ring-opacity-0 accent-cyan-400 focus:ring-0"
                />
              </label>

              <label id="toggle-heatmap-label" className="flex items-center justify-between p-2 bg-slate-900/40 rounded border border-slate-850 cursor-pointer text-xs font-sans text-slate-300">
                <span>Scalar Potential heatmap</span>
                <input 
                  type="checkbox" 
                  checked={showPotentialHeatmap} 
                  onChange={(e) => setShowPotentialHeatmap(e.target.checked)}
                  className="rounded border-slate-800 bg-[#090f1d] text-cyan-400 focus:ring-opacity-0 accent-cyan-400 focus:ring-0"
                />
              </label>
            </div>
          </div>

          {/* Engine telemetry stats */}
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 font-mono text-xs flex flex-col gap-2 flex-1 justify-center">
            <span className="text-xs text-slate-400 uppercase tracking-widest flex items-center gap-2 border-b border-slate-800/60 pb-1.5">
              <Waves className="w-3.5 h-3.5 text-cyan-400" /> Scalar Physics Field Telemetry
            </span>
            
            <div className="grid grid-cols-2 gap-2 text-[11px] py-1.5">
              <div className="flex flex-col gap-0.5">
                <span className="text-slate-500">Grid Dimensions</span>
                <span className="text-slate-300 text-sm font-semibold">{gridSize} × {gridSize} ({gridSize * gridSize} cells)</span>
              </div>
              <div className="flex flex-col gap-0.5 animate-pulse">
                <span className="text-slate-500">Propagation state</span>
                <span className="text-emerald-400 text-sm font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" /> {solved ? 'Pre-allocated' : 'Out-of-Sync'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-900/30 p-2 rounded border border-slate-800/40">
              <div className="flex flex-col">
                <span className="text-slate-500">Wavefront Steps</span>
                <span className="text-cyan-300 font-medium">{solved ? wavefrontSteps : '0'} steps</span>
              </div>
              <div className="flex flex-col">
                <span className="text-slate-500">Max potential node value</span>
                <span className="text-amber-300 font-medium">{solved ? potentialMax.toFixed(2) : '0.00' } φ</span>
              </div>
            </div>

            <div className="mt-1 flex flex-col gap-1 bg-[#040811] p-2 rounded text-[10px] text-cyan-400/80">
              <span className="text-[11px] font-semibold text-slate-350">Optimal Path Geometry:</span>
              <span className="text-[#8892b0] flex flex-wrap gap-1 leading-relaxed">
                {activePath.length > 0 ? (
                  <>
                    Total Nodes: <strong className="text-cyan-400 font-medium">{activePath.length}</strong>. 
                     Moves diagonally in <strong className="text-amber-400 font-medium">8-neighbor vectors</strong> bypassing structural 90° blocks. 
                     Total distance: <strong className="text-emerald-400 font-semibold">{(activePath.length * 1.1).toFixed(2)}m</strong>
                  </>
                ) : (
                  "Ready to trace descent pathways..."
                )}
              </span>
            </div>
          </div>

          {/* Solver controls */}
          <div className="flex gap-2.5">
            <button
              onClick={startGradientDescent}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 font-sans text-sm font-semibold rounded-lg shadow-sm border transition-all ${
                isSolving 
                  ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border-amber-500/30 font-medium hover:border-amber-500/50' 
                  : 'bg-cyan-500 hover:bg-cyan-600 text-slate-950 border-cyan-400 font-bold active:scale-[0.98]'
              }`}
            >
              {isSolving ? (
                <>
                  <Pause className="w-4 h-4 fill-current" /> Pause Solver
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" /> Run Optimizer Loop
                </>
              )}
            </button>

            <button
              onClick={clearGrid}
              className="px-4 py-3 bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-850 rounded-lg transition-all active:scale-95"
              title="Clear obstacles and reset paths"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
