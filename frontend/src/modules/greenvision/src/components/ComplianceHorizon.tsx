// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Scale, CheckCircle2, AlertTriangle, Info } from 'lucide-react';

export const ComplianceHorizon: React.FC = () => {
  const regulations = [
    { 
      name: 'EU AI Act (Art. 9)', 
      requirement: 'Risk Management', 
      status: 'Active', 
      detail: 'Continuous assessment of agent-specific context manipulation risks.',
      icon: <CheckCircle2 size={12} className="text-green-400" />
    },
    { 
      name: 'EU AI Act (Art. 11)', 
      requirement: 'Technical Documentation', 
      status: 'Compliant', 
      detail: 'Full logging of connection topologies and security policies via UACP.',
      icon: <CheckCircle2 size={12} className="text-green-400" />
    },
    { 
      name: 'EU AI Act (Art. 12)', 
      requirement: 'Automated Logging', 
      status: 'Compliant', 
      detail: 'PGL Merkle Ledger providing irreversible audit trails for all inferences.',
      icon: <CheckCircle2 size={12} className="text-green-400" />
    },
    { 
      name: 'EU AI Act (Art. 14)', 
      requirement: 'Human Oversight', 
      status: 'Enforced', 
      detail: 'Mandatory HITL confirmation gates for Tier 1 high-risk write operations.',
      icon: <CheckCircle2 size={12} className="text-green-400" />
    },
    { 
      name: 'NIST AI RMF', 
      requirement: 'Governance', 
      status: 'Configuring', 
      detail: 'Watchtower Layer monitoring real-time I/O violations and bias drifts.',
      icon: <AlertTriangle size={12} className="text-amber-400" />
    }
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Scale size={18} className="text-amber-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Compliance Horizon (2026)</h2>
        </div>
        <span className="text-[9px] font-mono text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">MANDATORY TRACK</span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {regulations.map((reg, i) => (
          <div key={i} className="p-3 rounded-xl bg-black/20 border border-white/5 group hover:border-white/10 transition-all">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                {reg.icon}
                <span className="text-[11px] font-bold text-white/80">{reg.name}</span>
              </div>
              <span className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded ${
                reg.status === 'Compliant' ? 'text-green-400 bg-green-400/10' :
                reg.status === 'Active' ? 'text-cyan-400 bg-cyan-400/10' : 'text-amber-400 bg-amber-400/10'
              }`}>
                {reg.status}
              </span>
            </div>
            <div className="flex flex-col ml-5">
               <span className="text-[9px] font-mono text-white/40 uppercase mb-1">{reg.requirement}</span>
               <p className="text-[9px] text-white/20 italic leading-tight">{reg.detail}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 pt-4 border-t border-white/5 flex flex-col gap-2">
         <div className="flex justify-between items-center text-[9px] font-mono text-white/10 uppercase italic">
            <span>Aug 2, 2026 Penalty Threshold</span>
            <span>Est. Risk Reduction: 92%</span>
         </div>
         <div className="h-1 bg-white/5 rounded-full overflow-hidden">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: '85%' }}
              className="h-full bg-gradient-to-r from-cyan-400 to-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.3)]"
            />
         </div>
      </div>
    </div>
  );
};
