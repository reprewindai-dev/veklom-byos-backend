// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { ShieldAlert, Zap, Lock as LockIcon, Eye, Terminal } from 'lucide-react';
import { SecuritySurface } from '../types';

interface ThreatLandscapeProps {
  surfaces: SecuritySurface[];
}

export const ThreatLandscape: React.FC<ThreatLandscapeProps> = ({ surfaces }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ShieldAlert size={18} className="text-red-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">MCP Threat Landscape</h2>
        </div>
        <span className="text-[9px] font-mono text-red-400/50 uppercase">Active Attack Surface Monitoring</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {surfaces.map((s, i) => (
          <div key={s.name} className="p-3 rounded-xl bg-black/20 border border-white/5 group hover:border-red-400/20 transition-all">
            <div className="flex justify-between items-start mb-2">
              <div className="flex flex-col">
                <span className="text-[11px] font-bold text-white/80">{s.name}</span>
                <span className="text-[8px] font-mono text-white/20 uppercase leading-none mt-1">{s.description}</span>
              </div>
              <span className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded ${
                s.threat_level === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                s.threat_level === 'high' ? 'bg-orange-500/10 text-orange-400' : 'bg-white/10 text-white/40'
              }`}>
                {s.threat_level}
              </span>
            </div>
            
            <div className="flex flex-col gap-1.5">
               <div className="flex justify-between items-center text-[8px] font-mono text-white/30 uppercase">
                  <span>Containment Profile</span>
                  <span>{(s.containment * 100).toFixed(0)}%</span>
               </div>
               <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${s.containment * 100}%` }}
                    transition={{ duration: 1, delay: i * 0.1 }}
                    className={`h-full ${
                      s.containment > 0.8 ? 'bg-green-400' : 
                      s.containment > 0.5 ? 'bg-amber-400' : 'bg-red-400'
                    }`}
                  />
               </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 p-3 rounded-xl bg-red-400/5 border border-red-400/10 flex items-start gap-3">
         <Terminal size={14} className="text-red-400 mt-0.5 shrink-0" />
         <p className="text-[9px] font-mono text-white/40 leading-tight">
            SYSTEM_DECREE: No communication trusted by default. Confused Deputy risks mitigated via description version pinning and real-time behavioral audit chains.
         </p>
      </div>
    </div>
  );
};
