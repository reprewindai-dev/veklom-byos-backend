// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Fingerprint, Shield, FileText, Activity } from 'lucide-react';
import { PGLGenome } from '../types';

interface GenomeDNAProps {
  genome?: PGLGenome;
}

export const GenomeDNA: React.FC<GenomeDNAProps> = ({ genome }) => {
  if (!genome) return null;

  const DNA_LAYERS = [
    { key: 'model', label: 'Model Layer', icon: <Activity size={12} /> },
    { key: 'prompt', label: 'Prompt Layer', icon: <FileText size={12} /> },
    { key: 'policy', label: 'Policy Layer', icon: <Shield size={12} /> },
    { key: 'watchtower', label: 'Watchtower', icon: <Fingerprint size={12} /> },
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Fingerprint size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Sovereign AI Genome</h2>
        </div>
        <div className="flex flex-col items-end">
            <span className="text-[9px] font-mono text-cyan-400/50 uppercase">Hash Identifier</span>
            <span className="text-xs font-mono font-bold text-cyan-400">0x{genome.hash}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {DNA_LAYERS.map((layer) => (
          <div key={layer.key} className="p-3 rounded-xl bg-black/20 border border-white/5 flex flex-col gap-1">
            <div className="flex items-center gap-2 text-white/40 mb-1">
              {layer.icon}
              <span className="text-[9px] font-mono uppercase tracking-wider">{layer.label}</span>
            </div>
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-white/80">{(genome.layers as any)[layer.key]}</span>
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 pt-4 border-t border-white/5">
        <div className="flex justify-between items-center text-[9px] font-mono text-white/20 uppercase mb-2">
           <span>Constitutional Integrity</span>
           <span className="text-cyan-400">Verified (SHA-256)</span>
        </div>
        <div className="flex gap-1">
          {[...Array(24)].map((_, i) => (
            <motion.div 
              key={i}
              initial={{ scaleY: 0.2 }}
              animate={{ scaleY: [0.2, Math.random() + 0.2, 0.2] }}
              transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.05 }}
              className="h-3 flex-1 bg-cyan-400/20 rounded-full"
            />
          ))}
        </div>
      </div>
    </div>
  );
};
