// @ts-nocheck
import React from 'react';
import { Shield, Eye, Lock as LockIcon, ShieldCheck } from 'lucide-react';
import { motion } from 'motion/react';

export const GovernanceMonitor: React.FC = () => {
  const securityControls = [
    { label: 'PII Redaction', status: 'Active', icon: <LockIcon size={12} />, color: 'text-cyan-400' },
    { label: 'Audit Traceability', status: 'Propagating', icon: <Eye size={12} />, color: 'text-amber-400' },
    { label: 'Access Constraints', status: 'Verified', icon: <ShieldCheck size={12} />, color: 'text-green-400' },
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-2">
        <Shield size={18} className="text-cyan-400" />
        <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Governance Layer</h2>
      </div>

      <div className="space-y-3">
        {securityControls.map((control, i) => (
          <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-black/20 border border-white/5 group hover:border-white/20 transition-all">
            <div className="flex items-center gap-3">
              <div className={`${control.color} opacity-50 group-hover:opacity-100 transition-opacity`}>
                {control.icon}
              </div>
              <span className="text-[11px] font-medium text-white/70">{control.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono uppercase ${control.color}`}>{control.status}</span>
              <motion.div 
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className={`w-1 h-3 rounded-full bg-current ${control.color.replace('text-', 'bg-')}`}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 pt-4 border-t border-white/5">
        <div className="flex justify-between items-center text-[9px] font-mono text-white/20 uppercase mb-2">
           <span>Behavioral Compliance Score</span>
           <span className="text-cyan-400">98.4%</span>
        </div>
        <div className="h-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: '98.4%' }}
            className="h-full bg-cyan-400"
          />
        </div>
      </div>
    </div>
  );
};
