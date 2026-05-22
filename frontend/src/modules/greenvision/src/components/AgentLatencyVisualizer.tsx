// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { Activity } from 'lucide-react';

export const AgentLatencyVisualizer: React.FC = () => {
  const [data, setData] = useState<{ time: number; latency: number }[]>([]);
  
  useEffect(() => {
    // Generate initial flat-ish data
    const initialData = Array.from({ length: 40 }, (_, i) => ({
      time: i,
      latency: 120 + Math.random() * 20
    }));
    setData(initialData);

    let timeCounter = 40;
    const interval = setInterval(() => {
      setData(prevData => {
        const newData = [...prevData.slice(1)];
        timeCounter++;
        // Create an occasional latency spike
        const isSpike = Math.random() > 0.85;
        const baseLatency = 120 + Math.random() * 20;
        const spikeAmount = isSpike ? Math.random() * 180 : 0;
        
        newData.push({
          time: timeCounter,
          latency: baseLatency + spikeAmount
        });
        return newData;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const currentLatency = data.length > 0 ? Math.round(data[data.length - 1].latency) : 0;
  const isHighLatency = currentLatency > 250;

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4 relative overflow-hidden">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-emerald-400" />
          <h3 className="text-xs font-mono uppercase tracking-widest text-white/80">Real-Time Latency Metrics</h3>
        </div>
        <div className="text-right flex items-center gap-3">
          {isHighLatency && (
             <span className="text-[10px] bg-red-500/20 text-red-500 border border-red-500/30 px-2 py-0.5 rounded font-mono animate-pulse uppercase">Spike Detected</span>
          )}
          <div className="text-2xl font-bold font-mono tracking-tighter w-24 text-right">
             <span className={isHighLatency ? "text-red-400" : "text-emerald-400"}>{currentLatency}</span><span className="text-sm text-white/40 ml-1">ms</span>
          </div>
        </div>
      </div>

      <div className="h-24 w-full -mx-2">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={isHighLatency ? "#ef4444" : "#34d399"} stopOpacity={0.4}/>
                <stop offset="95%" stopColor={isHighLatency ? "#ef4444" : "#34d399"} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <Area 
              type="monotone" 
              dataKey="latency" 
              stroke={isHighLatency ? "#ef4444" : "#34d399"} 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorLatency)" 
              isAnimationActive={false}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0b1219', borderColor: '#083344', color: '#fff', fontSize: '10px' }}
              itemStyle={{ color: isHighLatency ? "#ef4444" : "#34d399" }}
              labelStyle={{ display: 'none' }}
              cursor={{ stroke: '#083344', strokeWidth: 1 }}
              formatter={(value: number) => [`${Math.round(value)}ms`, 'Latency']}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      <div className="flex justify-between items-center pt-2 border-t border-white/10">
         <span className="text-[9px] font-mono text-white/40 uppercase">Rolling Window: 40s</span>
         <div className="flex gap-4">
            <span className="text-[9px] font-mono text-white/40 uppercase">Min: <span className="text-white/80">{Math.round(Math.min(...(data.map(d => d.latency) || [0])))}ms</span></span>
            <span className="text-[9px] font-mono text-white/40 uppercase">Max: <span className="text-white/80">{Math.round(Math.max(...(data.map(d => d.latency) || [0])))}ms</span></span>
         </div>
      </div>
    </div>
  );
};
