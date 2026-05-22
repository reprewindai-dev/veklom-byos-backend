// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';

interface SpectralAnalysisProps {
  data: {
    v1x?: number;
    v2x?: number;
    carpet?: number;
  };
}

export const SpectralAnalysis: React.FC<SpectralAnalysisProps> = ({ data }) => {
  const v1 = data.v1x || 20;
  const v2 = data.v2x || 15;
  const carpet = data.carpet || 40;

  return (
    <div className="w-full h-32 bg-black/40 rounded-xl border border-white/5 p-4 flex flex-col gap-3 relative overflow-hidden group">
      <div className="flex justify-between items-center text-[9px] font-mono text-white/30 uppercase tracking-[0.2em]">
        <span>FFT Spectral Analysis (ISO 10816)</span>
        <span className="text-amber-400 group-hover:text-amber-300 transition-colors">Vibration Triggered</span>
      </div>

      <div className="flex-1 flex items-end gap-1 px-1">
        {[...Array(30)].map((_, i) => {
          let height = 10 + Math.random() * carpet;
          let color = 'bg-white/10';
          
          // 1x RPM harmonic
          if (i === 5) {
            height = v1;
            color = 'bg-cyan-400';
          }
          // 2x RPM harmonic
          if (i === 10) {
            height = v2;
            color = 'bg-amber-400/50';
          }
          // Sub-harmonics or carpet noise spikes
          if (i > 20 && Math.random() > 0.8) {
            height = 15;
            color = 'bg-red-400/30';
          }

          return (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              animate={{ height: `${height}%` }}
              transition={{ duration: 0.5, delay: i * 0.02 }}
              className={`flex-1 rounded-t-sm transition-colors ${color}`}
            />
          );
        })}
      </div>

      <div className="flex justify-between items-center">
        <div className="flex gap-4">
           <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span className="text-[8px] font-mono text-white/40 uppercase">1x RPM (Unbalance)</span>
           </div>
           <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-400/50" />
              <span className="text-[8px] font-mono text-white/40 uppercase">2x RPM (Misalign)</span>
           </div>
        </div>
        <div className="text-[8px] font-mono text-cyan-400/50">Carpet Level: Stable</div>
      </div>

      <div className="mt-2 pt-2 border-t border-white/5 flex justify-between items-center bg-black/20 -mx-4 px-4 py-1">
        <div className="flex gap-2 items-center">
           <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter">Imputation Mode:</span>
           <span className="text-[7px] font-mono text-cyan-400/80">GAN-Latent-Recon</span>
        </div>
        <div className="flex gap-2">
           {['MCAR', 'MAR', 'MNAR'].map(type => (
             <div key={type} className="flex items-center gap-1">
                <div className={`w-1 h-1 rounded-full ${type === 'MNAR' ? 'bg-amber-400' : 'bg-green-400'}`} />
                <span className="text-[7px] font-mono text-white/30">{type}</span>
             </div>
           ))}
        </div>
      </div>
    </div>
  );
};
