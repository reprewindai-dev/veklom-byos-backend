// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Activity, Leaf, Wind, Droplets } from 'lucide-react';
import { BoundedMetrics } from '../types';

interface BoundedScalingProps {
  metrics: BoundedMetrics;
}

export const BoundedScaling: React.FC<BoundedScalingProps> = ({ metrics }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-emerald-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Optimal Bounded Design</h2>
        </div>
        <div className="px-2 py-0.5 bg-emerald-400/10 border border-emerald-400/20 rounded">
            <span className="text-[9px] font-mono text-emerald-400 uppercase font-bold">Scaling Ratio: {metrics.phi_ratio}φ</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white/40">
                    <Leaf size={12} />
                    <span className="text-[10px] font-mono uppercase">Carbon Intensity</span>
                </div>
                <span className="text-xs font-mono font-bold text-emerald-400">{(metrics.carbon_intensity * 100).toFixed(0)}% Opt</span>
            </div>
            <div className="h-12 flex items-end gap-1 px-1">
                {[...Array(12)].map((_, i) => (
                    <motion.div 
                        key={i}
                        animate={{ height: [`${Math.random() * 60}%`, `${Math.random() * 100}%`, `${Math.random() * 40}%`] }}
                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.1 }}
                        className="flex-1 bg-emerald-400/20 rounded-t-sm"
                    />
                ))}
            </div>
        </div>

        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white/40">
                    <Wind size={12} />
                    <span className="text-[10px] font-mono uppercase">Grid-Aware Load</span>
                </div>
                <span className="text-xs font-mono font-bold text-cyan-400">{(metrics.utilization * 100).toFixed(0)}% Load</span>
            </div>
            <div className="flex-1 flex flex-col justify-center gap-2">
                 <div className="flex justify-between text-[9px] font-mono text-white/20 uppercase">
                    <span>Floor</span>
                    <span>Ceiling</span>
                 </div>
                 <div className="h-1 bg-white/5 rounded-full overflow-hidden relative">
                    <motion.div 
                        initial={{ left: '-100%' }}
                        animate={{ left: '0%' }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"
                    />
                 </div>
            </div>
        </div>

        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white/40">
                    <Droplets size={12} />
                    <span className="text-[10px] font-mono uppercase">Water Risk Profile</span>
                </div>
                <span className={`text-[10px] font-mono uppercase px-1.5 rounded ${
                    metrics.water_risk === 'low' ? 'bg-green-400/10 text-green-400' : 'bg-amber-400/10 text-amber-400'
                }`}>
                    {metrics.water_risk}
                </span>
            </div>
            <div className="flex-1 flex items-center justify-center">
                <p className="text-[9px] text-white/30 font-mono text-center leading-tight">
                    Tuning carbon/compute ratio to φ-equivalent efficiency point. Workloads scheduled for peak renewable cycles.
                </p>
            </div>
        </div>
      </div>
    </div>
  );
};
