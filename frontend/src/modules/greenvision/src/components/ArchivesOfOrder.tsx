// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Archive, Lock as LockIcon, Shield, Cpu, Activity } from 'lucide-react';

interface ArchivesOfOrderProps {
  isLocked: boolean;
  latency: number;
  coherence: number;
  progress: number;
}

export const ArchivesOfOrder: React.FC<ArchivesOfOrderProps> = ({ isLocked, latency, coherence, progress }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive size={18} className="text-purple-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Archives of Order (Pillar IX)</h2>
        </div>
        <div className="flex items-center gap-3">
             <div className="flex items-center gap-2 px-3 py-1 rounded bg-black/40 border border-white/5">
                <span className="text-[9px] font-mono text-white/30 uppercase">Latency:</span>
                <span className="text-[10px] font-mono text-purple-400 font-bold">{latency.toFixed(1)}ms</span>
             </div>
             <div className="flex items-center gap-2 px-3 py-1 rounded bg-black/40 border border-white/5">
                <span className="text-[9px] font-mono text-white/30 uppercase">Coherence:</span>
                <span className="text-[10px] font-mono text-emerald-400 font-bold">{coherence.toFixed(1)}%</span>
             </div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between p-4 rounded-xl bg-purple-400/5 border border-purple-400/20 group hover:border-purple-400/40 transition-all">
            <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${isLocked ? 'bg-red-400/10 text-red-400' : 'bg-emerald-400/10 text-emerald-400'}`}>
                    <LockIcon size={18} />
                </div>
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">Operational Plane Lock</span>
                    <span className="text-[10px] font-mono text-white/30 uppercase leading-none mt-1">Definitive Execution Telemetry</span>
                </div>
            </div>
            <div className="flex flex-col items-end">
                <span className={`text-[10px] font-mono font-bold uppercase ${isLocked ? 'text-red-400' : 'text-emerald-400'}`}>
                    {isLocked ? 'PLANE_LOCKED' : 'PLANE_ACTIVE'}
                </span>
                <span className="text-[8px] font-mono text-white/20 uppercase tracking-tighter">Status</span>
            </div>
        </div>

        <div className="space-y-3 p-4 rounded-xl bg-black/40 border border-white/5">
            <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                <span className="text-white/40">Gated System Progress</span>
                <span className="text-purple-400 font-bold">{progress.toExponential(7)}%</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(progress * 100000, 2)}%` }}
                    transition={{ duration: 1 }}
                    className="h-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,0.5)]"
                />
            </div>
            <p className="text-[9px] font-mono text-white/20 uppercase text-right leading-none">
                Awaiting Deterministic Plan Initialization
            </p>
        </div>
      </div>

      <div className="flex items-center gap-3 p-3 bg-white/5 border border-dashed border-white/10 rounded-xl">
         <Activity size={12} className="text-purple-400" />
         <p className="text-[9px] font-mono text-white/40 uppercase leading-snug truncate italic">
            Audit Log initialized: Solo-orchestrated environment authenticated for Station: ALPHA.
         </p>
      </div>
    </div>
  );
};
