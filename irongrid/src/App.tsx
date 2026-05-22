import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Zap, Cpu, ShieldAlert, Award, Grid, Compass, Gauge, CpuIcon, Layers, HardDrive, Info, ArrowUpRight 
} from 'lucide-react';
import GridVisualizer from './components/GridVisualizer';
import Benchmarker from './components/Benchmarker';
import MemoryInspector from './components/MemoryInspector';

type ActiveTab = 'optimizer' | 'concurrency' | 'memory';

export default function App() {
  const [activeTab, setActiveTab ] = useState<ActiveTab>('optimizer');
  const [sharedCoords, setSharedCoords] = useState<[number, number][]>([]);

  const handleCoordsChange = (coords: [number, number][]) => {
    setSharedCoords(coords);
  };

  const explainers = [
    {
      title: "1. PyO3 Rust FFI Bridge",
      desc: "FastAPI is merely an async traffic cop. The math drops out of the virtual machine entirely, executing inside bare-metal compiled Rust extensions over unmanaged preallocated memories."
    },
    {
      title: "2. Async Concurrency Safeguards",
      desc: "By storing isolated router engine instances inside an asyncio Queue, Uvicorn's horizontal worker processes (scale of 4) segregate the event loops to bypass CPU GIL bottlenecks."
    },
    {
      title: "3. Zero Allocation Memory Defense",
      desc: "Pre-allocated heap pools bypass continuous malloc overhead during live request streams. Floating-point coords pack straight to 8-byte structures to drop GC pauses to absolute zero."
    }
  ];

  return (
    <div className="min-h-screen bg-[#03060f] text-[#ccd6f6] font-sans antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
      
      {/* Structural Master Grid Header */}
      <header className="border-b border-slate-900 bg-[#060a16]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row items-center justify-between gap-4">
          
          {/* Logo & Platform Name */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-cyan-505/20 from-cyan-500/10 to-emerald-500/20 border border-cyan-500/30 rounded-lg shadow-inner">
              <Cpu className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold font-sans tracking-tight text-white leading-none">
                  PyO3 Gradient Route Optimizer Engine
                </h1>
                <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-[9px] font-bold px-1.5 py-0.5 rounded leading-none">
                  V2.4 COMPILED
                </span>
              </div>
              <p className="text-[11.5px] text-slate-450 text-slate-400 mt-0.5 font-mono">
                High-Performance FFI Bridge & Concurrency Sandbox
              </p>
            </div>
          </div>

          {/* Core System Telemetry */}
          <div className="flex flex-wrap items-center gap-3 font-mono text-[10px]">
            <div className="flex items-center gap-1.5 bg-slate-950/60 border border-slate-900/80 px-2.5 py-1.5 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              <span className="text-slate-500">WORKFORCE AGENTS:</span>
              <span className="text-cyan-400 font-semibold">120 CONCURRENT</span>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-950/60 border border-slate-900/80 px-2.5 py-1.5 rounded">
              <span className="text-slate-500">UVICORN WORKERS:</span>
              <span className="text-slate-350 font-semibold uppercase">4 CORES ISOLATED</span>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-950/60 border border-slate-900/80 px-2.5 py-1.5 rounded">
              <span className="text-slate-505 text-slate-500">GARBAGE COLLECTION:</span>
              <span className="text-emerald-400 font-bold uppercase">0% PAUSE (RUST ENVELOPE)</span>
            </div>
          </div>

        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6">
        
        {/* Architectural Insight Callout banner */}
        <section className="bg-gradient-to-r from-[#030919] via-[#051126] to-[#030919] border border-slate-800/60 rounded-xl p-4 sm:p-5 relative overflow-hidden shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3 max-w-3xl">
            <div className="p-1.5 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 rounded-lg mt-0.5">
              <Info className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">
                Architectural Insight: Circumventing the Python Global Interpreter Lock (GIL)
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mt-1 font-sans font-light">
                This dashboard visualizes how enterprise routers sustain 120-agent workforce calculations in a single-threaded Python layer. By offloading gradient arithmetic to raw unmanaged machine code and utilising a process queue with multiple OS workers, performance constraints disappear.
              </p>
            </div>
          </div>
          <div className="text-[11px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 p-2.5 rounded shrink-0 flex items-center gap-1">
            Core latency: <strong className="text-white">~ 95 microseconds</strong>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </div>
        </section>

        {/* Dynamic Tab Switchers */}
        <div className="flex border-b border-slate-900/80 gap-3">
          <button
            onClick={() => setActiveTab('optimizer')}
            className={`pb-3 text-xs sm:text-sm font-sans font-medium relative transition-colors flex items-center gap-2 px-1 ${
              activeTab === 'optimizer' ? 'text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-205 hover:text-slate-200'
            }`}
          >
            <Compass className="w-4 h-4" />
            1. 8-Neighbor Solver Stage
            {activeTab === 'optimizer' && (
              <motion.div layoutId="active-tab-line" className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('concurrency')}
            className={`pb-3 text-xs sm:text-sm font-sans font-medium relative transition-colors flex items-center gap-2 px-1 ${
              activeTab === 'concurrency' ? 'text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-250 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            2. Workforce Concurrency Benchmark
            {activeTab === 'concurrency' && (
              <motion.div layoutId="active-tab-line" className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('memory')}
            className={`pb-3 text-xs sm:text-sm font-sans font-medium relative transition-colors flex items-center gap-2 px-1 ${
              activeTab === 'memory' ? 'text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-250 hover:text-slate-200'
            }`}
          >
            <HardDrive className="w-4 h-4" />
            3. Binary Struct Packers
            {activeTab === 'memory' && (
              <motion.div layoutId="active-tab-line" className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400" />
            )}
          </button>
        </div>

        {/* Tab Layout Render Section */}
        <div className="min-h-[500px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              {activeTab === 'optimizer' ? (
                <GridVisualizer onPathUpdate={handleCoordsChange} />
              ) : activeTab === 'concurrency' ? (
                <Benchmarker />
              ) : (
                <MemoryInspector coordSource={sharedCoords} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer Concept Cards (No slop, clean architectural details) */}
        <section className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {explainers.map((exp, idx) => (
            <div key={idx} className="bg-slate-950/30 border border-slate-900 p-4 rounded-lg flex flex-col gap-1.5 hover:border-slate-800 transition">
              <span className="text-xs font-semibold text-slate-100">{exp.title}</span>
              <p className="text-[11.5px] text-slate-450 text-slate-400 leading-relaxed font-sans font-light">
                {exp.desc}
              </p>
            </div>
          ))}
        </section>

      </main>

      {/* Humble Footer */}
      <footer className="border-t border-slate-900 py-6 mt-12 bg-slate-950/20">
        <div className="max-w-7xl mx-auto px-4 text-center font-mono text-[10px] text-slate-550 text-slate-500">
          FFI route solver compiled natively using Rust PyO3 bindings & FastAPI. Crafted with Desktop-First typography.
        </div>
      </footer>

    </div>
  );
}
