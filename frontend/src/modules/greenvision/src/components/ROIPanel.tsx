// @ts-nocheck
import React from 'react';
import { TrendingDown, Users, Zap, BarChart3 } from 'lucide-react';
import { motion } from 'motion/react';

export const ROIPanel: React.FC = () => {
  const metrics = [
    { label: 'Equipment Breakdowns', value: '75%', trend: 'Decrease', icon: <TrendingDown size={14} />, color: 'text-red-400' },
    { label: 'Maintenance Labour', value: '45%', trend: 'Reduction', icon: <Users size={14} />, color: 'text-cyan-400' },
    { label: 'P-F Interval Delay', value: '12.4h', trend: 'Optimization', icon: <Zap size={14} />, color: 'text-amber-400' },
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 size={18} className="text-amber-400" />
        <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Operational ROI</h2>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {metrics.map((m, i) => (
          <div key={i} className="flex flex-col gap-2 p-3 rounded-xl bg-black/20 border border-white/5">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2 text-white/40">
                {m.icon}
                <span className="text-[10px] font-mono uppercase tracking-wider">{m.label}</span>
              </div>
              <span className={`text-sm font-bold ${m.color}`}>{m.value}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[9px] font-mono text-white/20 italic">{m.trend} Strategy</span>
              <div className="flex gap-1">
                {[...Array(4)].map((_, j) => (
                  <motion.div 
                    key={j}
                    animate={{ scaleY: [1, 1.5, 1] }}
                    transition={{ repeat: Infinity, duration: 1.5, delay: j * 0.2 }}
                    className={`w-1 h-2 rounded-full bg-current ${m.color.replace('text-', 'bg-')}`}
                  />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <p className="text-[9px] leading-relaxed text-white/30 font-mono italic mt-2 border-l border-white/10 pl-3">
        * Estimates based on transitioning from reactive firefighting to precision, condition-based spectral analysis.
      </p>
    </div>
  );
};
