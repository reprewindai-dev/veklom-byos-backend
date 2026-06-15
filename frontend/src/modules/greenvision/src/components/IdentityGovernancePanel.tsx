// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { UserCheck, Zap, Lock as LockIcon, Eye, AlertCircle } from 'lucide-react';
import { IdentityGovernance } from '../types';

interface IdentityGovernancePanelProps {
  data: IdentityGovernance;
}

export const IdentityGovernancePanel: React.FC<IdentityGovernancePanelProps> = ({ data }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <UserCheck size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Identity Governance (XAA)</h2>
        </div>
        <span className="text-[9px] font-mono text-cyan-400/50 uppercase italic">Beyond the User-Extension Model</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
           <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-2">
              <div className="flex justify-between items-center text-[10px] font-mono text-white/40 uppercase">
                 <span>Cross App Access (XAA)</span>
                 <span className={`px-1.5 rounded ${data.xaa_status === 'enforced' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-amber-400/10 text-amber-400'}`}>
                    {data.xaa_status}
                 </span>
              </div>
              <p className="text-[9px] text-white/30 font-mono mt-1">
                 Validating intent, not just credentials. Authority derived from runtime attestation.
              </p>
           </div>

           <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-2">
              <div className="flex justify-between items-center text-[10px] font-mono text-white/40 uppercase">
                 <span>Just-In-Time (JIT) Access</span>
                 <span className={`px-1.5 rounded ${data.jit_access === 'active' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-white/10 text-white/20'}`}>
                    {data.jit_access}
                 </span>
              </div>
              <p className="text-[9px] text-white/30 font-mono mt-1">
                 No persistent authority. Scoped tokens generated for duration of validated task.
              </p>
           </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
           <div className="p-4 rounded-xl bg-white/5 border border-white/5 flex flex-col items-center justify-center text-center gap-2">
              <span className="text-2xl font-bold text-white">{data.active_agents}</span>
              <span className="text-[8px] font-mono uppercase text-white/40">Verified Agents</span>
           </div>
           <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center gap-2 ${
              data.shadow_ai_detected > 0 ? 'bg-red-400/5 border-red-400/20' : 'bg-emerald-400/5 border-emerald-400/20'
           }`}>
              <span className={`text-2xl font-bold ${data.shadow_ai_detected > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                 {data.shadow_ai_detected}
              </span>
              <span className="text-[8px] font-mono uppercase text-white/40">Shadow AI detected</span>
           </div>
           <div className="col-span-2 p-3 rounded-xl bg-cyan-400/5 border border-cyan-400/10 flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${data.secretless_mode ? 'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.5)]' : 'bg-white/20'}`} />
              <span className="text-[10px] font-mono uppercase text-cyan-400 font-bold">Secretless Auth (OIDC) Optimized</span>
           </div>
        </div>
      </div>

      <div className="mt-2 p-3 rounded-xl bg-white/5 border border-dashed border-white/10 flex items-start gap-3">
         <LockIcon size={12} className="text-white/40 mt-0.5" />
         <p className="text-[9px] font-mono text-white/30 uppercase leading-tight italic">
            Transitioning from passive session-based security to persistent behavioral intent validation. Addressing the "Confused Deputy" structural vulnerability.
         </p>
      </div>
    </div>
  );
};
