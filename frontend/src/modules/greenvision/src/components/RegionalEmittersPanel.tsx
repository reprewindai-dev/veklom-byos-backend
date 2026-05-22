// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Globe, User } from 'lucide-react';
import { RegionalEmitter } from '../types';

interface RegionalEmittersPanelProps {
  emitters: RegionalEmitter[];
}

export const RegionalEmittersPanel: React.FC<RegionalEmittersPanelProps> = ({ emitters }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Globe size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Regional Emitter Density</h2>
        </div>
        <span className="text-[9px] font-mono text-cyan-400/50 uppercase">Territorial Basis (Excl. LULUCF)</span>
      </div>

      <div className="space-y-3">
        {emitters.map((emitter, i) => (
          <div key={emitter.name} className="flex flex-col gap-2 p-3 rounded-xl bg-black/20 border border-white/5 group hover:border-white/20 transition-all">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold text-white/80">{emitter.name}</span>
                <span className="text-[9px] font-mono text-white/20">{emitter.percentage}% Of Global</span>
              </div>
              <span className="text-xs font-mono font-bold text-white/80">{emitter.volume.toLocaleString()} MtCO2e</span>
            </div>
            
            <div className="relative h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${emitter.percentage}%` }}
                 transition={{ duration: 1, delay: i * 0.1 }}
                 className="h-full bg-cyan-400/50 group-hover:bg-cyan-400 transition-colors"
               />
            </div>

            {emitter.perCapita && (
               <div className="flex items-center gap-1.5 mt-1">
                  <User size={10} className="text-white/20" />
                  <span className="text-[8px] font-mono text-white/30 uppercase tracking-tighter">
                    Per Capita Intensity: <span className="text-white/60 font-bold">{emitter.perCapita}t</span>
                  </span>
               </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-2 pt-4 border-t border-white/5">
        <p className="text-[9px] leading-relaxed text-white/20 font-mono italic">
          * Note: USA remains the largest cumulative emitter historically, while current annual totals are skewed by high-intensity industrial clusters.
        </p>
      </div>
    </div>
  );
};
