// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Compass, CheckCircle2, Clock, Map, Target } from 'lucide-react';
import { RoadmapPhase } from '../types';

interface GovernanceRoadmapProps {
  phases: RoadmapPhase[];
}

export const GovernanceRoadmap: React.FC<GovernanceRoadmapProps> = ({ phases }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Compass size={18} className="text-purple-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Agent Governance Roadmap</h2>
        </div>
        <div className="flex items-center gap-2">
            <span className="text-[9px] font-mono text-purple-400/50 uppercase">Closing the Agent Security Gap</span>
        </div>
      </div>

      <div className="relative">
        {/* Connection Line */}
        <div className="absolute left-4 top-0 bottom-0 w-[1px] bg-white/10" />

        <div className="space-y-6">
          {phases.map((phase, i) => (
            <motion.div 
              key={phase.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="relative pl-12 group"
            >
              {/* Dot */}
              <div className={`absolute left-[13px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-black z-10 transition-colors ${
                phase.status === 'completed' ? 'bg-emerald-400' :
                phase.status === 'in-progress' ? 'bg-amber-400 animate-pulse' : 'bg-white/20'
              }`} />

              <div className="p-4 rounded-xl bg-black/40 border border-white/5 group-hover:border-purple-400/30 transition-all flex flex-col gap-2">
                 <div className="flex justify-between items-start">
                    <div className="flex flex-col">
                        <span className="text-[9px] font-mono text-purple-400 uppercase tracking-tighter">Phase 0{phase.id}</span>
                        <h3 className="text-xs font-bold text-white uppercase">{phase.label}</h3>
                    </div>
                    <div className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded ${
                        phase.status === 'completed' ? 'bg-emerald-400/10 text-emerald-400' :
                        phase.status === 'in-progress' ? 'bg-amber-400/10 text-amber-400' : 'bg-white/5 text-white/30'
                    }`}>
                        {phase.status.replace('-', ' ')}
                    </div>
                 </div>

                 <p className="text-[10px] text-white/40 leading-relaxed font-medium">
                    {phase.description}
                 </p>

                 <div className="mt-1 pt-2 border-t border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Target size={10} className="text-red-400/60" />
                        <span className="text-[8px] font-mono text-white/30 uppercase">Target: {phase.target_threat}</span>
                    </div>
                    {phase.status === 'completed' && <CheckCircle2 size={12} className="text-emerald-400/40" />}
                 </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="p-3 bg-purple-400/5 border border-purple-400/10 rounded-xl flex items-center gap-3">
         <Map size={14} className="text-purple-400 shrink-0" />
         <span className="text-[9px] font-mono text-purple-400/70 uppercase leading-snug">
            Strategic Alignment: EU AI Act (Article 9, 11, 14) // NIST AI RMF Integration.
         </span>
      </div>
    </div>
  );
};
