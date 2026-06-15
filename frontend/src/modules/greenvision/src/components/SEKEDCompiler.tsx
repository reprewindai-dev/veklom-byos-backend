// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Cpu, Zap, Shield, Target, Layers, Anchor } from 'lucide-react';
import { SEKEDState } from '../types';

interface SEKEDCompilerProps {
  state: SEKEDState;
}

export const SEKEDCompiler: React.FC<SEKEDCompilerProps> = ({ state }) => {
  const params = [
    { label: 'Energy (E)', value: state.energy, icon: <Zap size={10} />, color: 'text-amber-400' },
    { label: 'Resilience (R)', value: state.resilience, icon: <Shield size={10} />, color: 'text-cyan-400' },
    { label: 'Confidence (C)', value: state.confidence, icon: <Target size={10} />, color: 'text-purple-400' },
    { label: 'Diversity (D)', value: state.diversity, icon: <Layers size={10} />, color: 'text-emerald-400' },
    { label: 'Stability (S)', value: state.stability, icon: <Anchor size={10} />, color: 'text-blue-400' },
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu size={18} className="text-amber-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">SEKED Compiler</h2>
        </div>
        <div className="px-3 py-1 bg-amber-400/10 border border-amber-400/20 rounded flex items-center gap-2">
          <span className="text-[10px] font-mono text-amber-400 font-bold uppercase tracking-tighter">Directive:</span>
          <span className="text-xs font-mono font-black text-white group-hover:animate-pulse uppercase">{state.directive}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {params.map((p) => (
          <div key={p.label} className="p-3 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-2 relative overflow-hidden">
             <div className="flex items-center gap-2 mb-1">
                <span className={p.color}>{p.icon}</span>
                <span className="text-[9px] font-mono uppercase text-white/40">{p.label}</span>
             </div>
             <div className="flex items-end justify-between">
                <span className="text-xs font-mono font-bold text-white/80">{(p.value * 100).toFixed(1)}%</span>
                <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${p.value * 100}%` }}
                        className={`h-full ${p.color.replace('text-', 'bg-')}`}
                    />
                </div>
             </div>
          </div>
        ))}
      </div>

      <div className="mt-2 p-3 rounded-xl bg-white/5 border border-dashed border-white/10">
        <p className="text-[9px] font-mono text-white/30 leading-relaxed uppercase">
          Mapping 100,000 potential system states to exactly nine deterministic directives. Current state-space mapping verified via Bounded Rationality heuristics.
        </p>
      </div>
    </div>
  );
};
