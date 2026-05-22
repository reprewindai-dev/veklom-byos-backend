// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { ShieldCheck, Gavel, BarChart3, Lock as LockIcon } from 'lucide-react';

interface PolicyEvaluationPanelProps {
  status: 'ACTIVE' | 'VIOLATION' | 'PENDING';
}

export const PolicyEvaluationPanel: React.FC<PolicyEvaluationPanelProps> = ({ status }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gavel size={18} className="text-red-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Compliance (Pillar VI)</h2>
        </div>
        <div className="flex items-center gap-2 bg-black/40 px-2 py-0.5 rounded border border-white/5">
            <span className="text-[9px] font-mono text-white/30 uppercase">Policy Family:</span>
            <span className="text-[10px] font-mono text-red-400 font-bold uppercase tracking-widest">AC-10</span>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between p-4 rounded-xl bg-black/40 border border-white/5">
            <div className="flex items-center gap-3">
                <ShieldCheck size={18} className={status === 'ACTIVE' ? 'text-emerald-400' : 'text-red-400'} />
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-white uppercase tracking-tight">GOPHER V4.1 Policy Evaluation</span>
                    <span className="text-[9px] font-mono text-white/30 uppercase leading-none mt-1">Live Automated Verification</span>
                </div>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-all ${
                status === 'ACTIVE' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-red-400/10 text-red-400'
            }`}>
                {status}
            </span>
        </div>

        <div className="space-y-2">
            <div className="flex justify-between items-center text-[9px] font-mono text-white/30 uppercase">
                <span>Deterministic Constraints</span>
                <span>Ready</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2, ease: "easeInOut" }}
                    className="h-full bg-red-400"
                />
            </div>
        </div>
      </div>

      <div className="flex items-center gap-3 p-3 bg-white/5 border border-dashed border-white/10 rounded-xl">
         <LockIcon size={12} className="text-white/20" />
         <p className="text-[9px] font-mono text-white/40 uppercase leading-tight italic">
            Compliance is a hard constraint on the execution engine, not an afterthought. Gated execution path verified.
         </p>
      </div>
    </div>
  );
};
