// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Percent, Zap, Wallet, Gauge } from 'lucide-react';

interface DeterminismRatioProps {
  ratio: number;
  certainty: number;
  noise: number;
  entropy: number;
}

export const DeterminismRatio: React.FC<DeterminismRatioProps> = ({ ratio, certainty, noise, entropy }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gauge size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Determinism Ratio (Pillar VIII)</h2>
        </div>
        <div className="flex items-center gap-2 bg-cyan-400/10 px-2 py-0.5 rounded border border-cyan-400/20">
            <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-tighter">TARGET: {ratio.toFixed(1)}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-4">
            <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-[10px] font-mono text-white/40 uppercase">
                    <span>Certainty Index</span>
                    <span className="text-white font-bold">{certainty.toFixed(4)}</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${certainty * 100}%` }}
                        transition={{ duration: 1.5 }}
                        className="h-full bg-cyan-400"
                    />
                </div>
            </div>

            <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-[10px] font-mono text-white/40 uppercase">
                    <span>Acceptable Noise</span>
                    <span className="text-white font-bold">{noise.toFixed(3)}</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${noise * 100}%` }}
                        transition={{ duration: 1.5 }}
                        className="h-full bg-amber-400"
                    />
                </div>
            </div>
        </div>

        <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-black/40 border border-white/5 text-center gap-1">
            <span className="text-[9px] font-mono text-white/30 uppercase">Deterministic Entropy</span>
            <span className="text-2xl font-bold text-white font-mono">{entropy.toFixed(3)}</span>
            <span className="text-[8px] font-mono text-cyan-400/60 uppercase tracking-widest mt-1">Resource Optimizing</span>
        </div>
      </div>

      <div className="p-3 bg-cyan-400/5 border border-cyan-400/10 rounded-xl flex items-center justify-between">
         <div className="flex items-center gap-3">
            <Wallet size={14} className="text-cyan-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase font-bold tracking-tight">Optimization Billing Mode</span>
         </div>
         <span className="text-[10px] font-mono text-cyan-400/60 uppercase font-bold">SOLO_SCALE: ✅</span>
      </div>
    </div>
  );
};
