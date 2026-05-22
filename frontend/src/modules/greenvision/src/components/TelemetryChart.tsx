// @ts-nocheck
import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { QuantumTelemetry } from '../types';

interface TelemetryChartProps {
  data: QuantumTelemetry[];
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({ data }) => {
  return (
    <div className="w-full h-32 bg-black/20 rounded-lg p-2 border border-white/5">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorFidelity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="timestamp" 
            hide 
          />
          <YAxis 
            domain={[95, 100]} 
            hide 
          />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="bg-[#0a0a0b] border border-white/10 p-2 rounded shadow-xl">
                    <p className="text-[10px] font-mono text-white/50 mb-1">FIDELITY</p>
                    <p className="text-xs font-mono text-cyan-400 font-bold">{payload[0].value}%</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area 
            type="monotone" 
            dataKey="fidelity" 
            stroke="#22d3ee" 
            fillOpacity={1} 
            fill="url(#colorFidelity)" 
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
