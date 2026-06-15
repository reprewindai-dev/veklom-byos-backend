// @ts-nocheck
import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Leaf, Zap, Cloud, Focus, Layers, Activity } from 'lucide-react';

export const MitigationPathwaysPanel: React.FC = () => {
  const pathways = [
    { 
      id: 'IMP-Ren', 
      label: 'Renewables', 
      icon: <Zap size={14} />, 
      color: 'bg-yellow-400', 
      textColor: 'text-yellow-400',
      description: 'Massive shift to solar/wind, eliminating unabated coal by 2050.' 
    },
    { 
      id: 'IMP-LD', 
      label: 'Low Demand', 
      icon: <Layers size={14} />, 
      color: 'bg-emerald-400', 
      textColor: 'text-emerald-400',
      description: 'Efficiency and lifestyle changes reduce reliance on carbon removal.' 
    },
    { 
      id: 'IMP-Neg', 
      label: 'Net Negative', 
      icon: <Cloud size={14} />, 
      color: 'bg-blue-400', 
      textColor: 'text-blue-400',
      description: 'Extensive use of CDR (BECCS/DACCS) to compensate for residual emissions.' 
    },
    { 
      id: 'IMP-SP', 
      label: 'Shifting Pathways', 
      icon: <Focus size={14} />, 
      color: 'bg-purple-400', 
      textColor: 'text-purple-400',
      description: 'Integrated mitigation with broader sustainable development goals.' 
    }
  ];

  const [activeTab, setActiveTab] = React.useState(pathways[0].id);

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-5">
      <div className="flex items-center gap-2 mb-1">
        <Leaf size={18} className="text-emerald-400" />
        <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Illustrative Mitigation Pathways (IMP)</h2>
      </div>

      <div className="flex flex-wrap gap-2">
        {pathways.map((p) => (
          <button
            key={p.id}
            onClick={() => setActiveTab(p.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-[10px] font-mono uppercase tracking-widest ${
              activeTab === p.id 
                ? `${p.color}/20 border-${p.color.replace('bg-', '')}/40 ${p.textColor}` 
                : 'bg-white/5 border-white/5 text-white/40 hover:bg-white/10'
            }`}
          >
            {p.icon}
            {p.id}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-black/20 rounded-xl border border-white/5 p-4 relative min-h-[120px]">
        <AnimatePresence mode="wait">
          {pathways.map((p) => activeTab === p.id && (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col gap-3"
            >
              <div className="flex justify-between items-center">
                <span className={`text-xs font-bold ${p.textColor}`}>{p.label} Archetype</span>
                <span className="text-[9px] font-mono text-white/20">C1: 1.5°C Compatible</span>
              </div>
              <p className="text-[11px] text-white/60 leading-relaxed font-mono italic">
                "{p.description}"
              </p>
              <div className="grid grid-cols-2 gap-4 mt-2 pt-3 border-t border-white/5">
                <div className="flex flex-col gap-1">
                  <span className="text-[8px] font-mono text-white/30 uppercase">Feasibility Frontier</span>
                  <span className="text-[10px] text-white/80">Institutional/Economic</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[8px] font-mono text-white/30 uppercase">Primary Constraint</span>
                  <span className="text-[10px] text-white/80">Capex Allocation</span>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
         <div className="p-2 rounded bg-emerald-500/10 text-emerald-400">
            <Activity size={14} />
         </div>
         <p className="text-[9px] font-mono text-white/40 leading-tight">
            Research indicates the AFOLU sector could reach net zero CO2 as early as the 2030s in multi-pathway ensembles.
         </p>
      </div>
    </div>
  );
};
