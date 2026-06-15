// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Database, History, TrendingUp, Anchor } from 'lucide-react';

export const MemoryVault: React.FC = () => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={18} className="text-amber-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">The Vault (Pillar V)</h2>
        </div>
        <span className="text-[9px] font-mono text-amber-400/50 uppercase">Asset Convergence</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase">
                <History size={12} className="text-amber-400" />
                <span>Memory Dynamics</span>
            </div>
            <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-white">92.4%</span>
                <span className="text-[9px] font-mono text-emerald-400 uppercase">Match</span>
            </div>
            <span className="text-[8px] font-mono text-white/20 uppercase leading-none">Historical Heuristics</span>
        </div>

        <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase">
                <TrendingUp size={12} className="text-cyan-400" />
                <span>Deterministic Alpha</span>
            </div>
            <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-white">Σ Active</span>
            </div>
            <span className="text-[8px] font-mono text-white/20 uppercase leading-none">Real-time heuristics</span>
        </div>
      </div>

      <div className="p-3 bg-amber-400/5 border border-amber-400/10 rounded-xl flex items-center gap-3">
         <Anchor size={14} className="text-amber-400 shrink-0" />
         <p className="text-[10px] font-mono text-white/40 uppercase leading-snug">
            Memory is not a static asset but a live signal projected onto the current operational state.
         </p>
      </div>
    </div>
  );
};
