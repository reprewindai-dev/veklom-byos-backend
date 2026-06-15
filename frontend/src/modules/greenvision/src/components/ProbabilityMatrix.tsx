// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Grid3X3, Layers, FileJson, Lock as LockIcon } from 'lucide-react';

interface ProbabilityMatrixProps {
  revision: string;
  isCompiled: boolean;
}

export const ProbabilityMatrix: React.FC<ProbabilityMatrixProps> = ({ revision, isCompiled }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Grid3X3 size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Probability Matrix (Pillar III)</h2>
        </div>
        <div className="flex items-center gap-2 bg-black/40 px-2 py-0.5 rounded border border-white/5">
            <span className="text-[9px] font-mono text-white/30 uppercase">Rev:</span>
            <span className="text-[10px] font-mono text-cyan-400 font-bold">{revision}</span>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center p-8 rounded-2xl bg-black/40 border border-dashed border-white/10 relative overflow-hidden group">
        {!isCompiled ? (
            <div className="flex flex-col items-center gap-3 relative z-10">
                <div className="p-3 rounded-full bg-white/5 text-white/20">
                    <Layers size={24} />
                </div>
                <div className="flex flex-col items-center">
                    <span className="text-sm font-bold text-white/40 uppercase">No deterministic plans compiled</span>
                    <span className="text-[10px] font-mono text-white/20 uppercase">Waiting for Intent Ingestion...</span>
                </div>
            </div>
        ) : (
            <div className="text-emerald-400 font-mono text-xs uppercase">Plan Compiled: Alpha-Gated Execution Ready</div>
        )}

        <motion.div 
            animate={{ opacity: [0.1, 0.3, 0.1] }}
            transition={{ duration: 4, repeat: Infinity }}
            className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(34,211,238,0.1)_0%,transparent_70%)]"
        />
      </div>

      <div className="flex gap-4">
        <button className="flex-1 flex items-center justify-center gap-2 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all group">
            <Layers size={14} className="text-white/40 group-hover:text-cyan-400 transition-colors" />
            <span className="text-[10px] font-mono uppercase text-white/60">Compile Plan</span>
        </button>
        <button className="flex-1 flex items-center justify-center gap-2 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all group">
            <FileJson size={14} className="text-white/40 group-hover:text-purple-400 transition-colors" />
            <span className="text-[10px] font-mono uppercase text-white/60">Export Schema</span>
        </button>
      </div>
    </div>
  );
};
