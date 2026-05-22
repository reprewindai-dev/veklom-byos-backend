// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Radio, ArrowUpRight, ArrowDownLeft, Minus } from 'lucide-react';
import { ObservabilitySignal } from '../types';

interface ObservabilitySignalsProps {
  signals: ObservabilitySignal[];
}

export const ObservabilitySignals: React.FC<ObservabilitySignalsProps> = ({ signals }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio size={18} className="text-cyan-400 animate-pulse" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Value Traces (Pillar VII)</h2>
        </div>
        <span className="text-[9px] font-mono text-white/30 uppercase">UACP Rest-State Monitor</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {signals.map((s) => (
          <div key={s.name} className="p-3 rounded-xl bg-black/40 border border-white/5 group hover:border-cyan-400/30 transition-all flex flex-col gap-2">
            <div className="flex justify-between items-center">
                <span className="text-[9px] font-mono text-white/40 uppercase truncate mr-2">{s.name}</span>
                <div className={`p-0.5 rounded ${
                    s.state === 'RISING' ? 'text-emerald-400' :
                    s.state === 'FALLING' ? 'text-red-400' : 'text-white/40'
                }`}>
                    {s.state === 'RISING' ? <ArrowUpRight size={10} /> : s.state === 'FALLING' ? <ArrowDownLeft size={10} /> : <Minus size={10} />}
                </div>
            </div>
            <div className="flex items-baseline justify-between">
                <span className={`text-[10px] font-mono font-bold ${
                    s.state === 'RISING' ? 'text-emerald-400' :
                    s.state === 'FALLING' ? 'text-red-400' : 'text-white/40'
                }`}>{s.state}</span>
                <span className="text-[8px] font-mono text-white/20 uppercase tracking-tighter leading-none mt-1">Operational Definition</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 text-[9px] font-mono text-white/20 uppercase leading-snug">
        System pressure rising // Coherence stable // Noise actively falling.
      </div>
    </div>
  );
};
