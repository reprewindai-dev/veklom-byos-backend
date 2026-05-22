// @ts-nocheck
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { motion } from 'motion/react';
import { TrendingUp, Activity } from 'lucide-react';
import { EmissionPoint } from '../types';

interface EmissionsTrajectoryProps {
  data: EmissionPoint[];
}

export const EmissionsTrajectory: React.FC<EmissionsTrajectoryProps> = ({ data }) => {
  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4 min-h-[300px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp size={18} className="text-red-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Global CO2 Trajectory</h2>
        </div>
        <div className="flex gap-2">
          <span className="text-[9px] font-mono text-red-400 bg-red-400/10 px-2 py-0.5 rounded border border-red-400/20 uppercase tracking-tighter">Gap Widening</span>
          <span className="text-[9px] font-mono text-white/30 uppercase tracking-tighter">Unit: GtCO2</span>
        </div>
      </div>

      <div className="flex-1 w-full h-[200px]">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="emissionsColor" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#f87171" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis 
              dataKey="year" 
              stroke="#ffffff30" 
              fontSize={10} 
              tickLine={false} 
              axisLine={false}
              tick={{ fill: 'rgba(255,255,255,0.4)' }}
            />
            <YAxis 
              stroke="#ffffff30" 
              fontSize={10} 
              tickLine={false} 
              axisLine={false}
              tick={{ fill: 'rgba(255,255,255,0.4)' }}
              domain={[0, 'auto']}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#000', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
              itemStyle={{ color: '#f87171', fontSize: '10px', fontFamily: 'monospace' }}
              labelStyle={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginBottom: '4px' }}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#f87171" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#emissionsColor)" 
              animationDuration={2000}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-2">
         <div className="flex flex-col p-3 rounded-xl bg-black/20 border border-white/5">
            <span className="text-[9px] font-mono text-white/30 uppercase mb-1">2024 Inventory</span>
            <div className="flex items-end gap-2">
               <span className="text-xl font-bold text-white">37.8</span>
               <span className="text-[10px] text-red-400 font-mono mb-1">±2.0 GtCO2</span>
            </div>
         </div>
         <div className="flex flex-col p-3 rounded-xl bg-black/20 border border-white/5">
            <span className="text-[9px] font-mono text-white/30 uppercase mb-1">2025 Projection</span>
            <div className="flex items-end gap-2">
               <span className="text-xl font-bold text-white">38.1</span>
               <span className="text-[10px] text-amber-400 font-mono mb-1">+1.1% Trend</span>
            </div>
         </div>
      </div>
    </div>
  );
};
