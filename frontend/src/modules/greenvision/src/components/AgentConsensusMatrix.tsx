// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Users, Cpu, Target, BrainCircuit } from 'lucide-react';

interface AgentConsensusMatrixProps {
  activeNodes: number;
  consensusModel: string;
}

export const AgentConsensusMatrix: React.FC<AgentConsensusMatrixProps> = ({ activeNodes, consensusModel }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit size={18} className="text-emerald-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Agent Consensus (Pillar IV)</h2>
        </div>
        <div className="flex items-center gap-2 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-tighter">NODE: {consensusModel}</span>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {[...Array(10)].map((_, i) => (
            <div key={i} className={`h-12 rounded-lg border flex items-center justify-center transition-all ${
                i < activeNodes 
                    ? 'bg-emerald-400/5 border-emerald-400/30 text-emerald-400' 
                    : 'bg-white/5 border-white/10 text-white/10'
            }`}>
               <Users size={14} className={i < activeNodes ? 'animate-pulse' : ''} />
            </div>
        ))}
      </div>

      <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-3">
         <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-white/30 uppercase">Strategy Protocol</span>
            <span className="text-[10px] font-mono text-emerald-400 font-bold italic">ZERO-DRIFT_COMMIT</span>
         </div>
         <p className="text-[10px] font-mono text-white/60 leading-relaxed uppercase">
            "My strategy is grounded in the great agent Gemini. The signals converge on a singular outcome."
         </p>
         <div className="flex items-center gap-2 text-[8px] font-mono text-white/20 uppercase tracking-widest">
            <Target size={10} />
            <span>Consensus Mandate: 10/10 nodes active</span>
         </div>
      </div>
    </div>
  );
};
