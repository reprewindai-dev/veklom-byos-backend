// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { Brain, Database, Box, UserCheck } from 'lucide-react';
import { UACPLayerStatus } from '../types';

interface UACPLayersProps {
  layers: UACPLayerStatus[];
}

export const UACPLayers: React.FC<UACPLayersProps> = ({ layers }) => {
  const layerIcons = {
    cognitive: <Brain size={14} />,
    context: <Database size={14} />,
    execution: <Box size={14} />,
    hitl: <UserCheck size={14} />,
  };

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Box size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">UACP Orchestration</h2>
        </div>
        <span className="text-[9px] font-mono text-cyan-400/50 uppercase">Federated Control Plane</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {layers.map((l) => (
          <div key={l.layer} className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-3 group hover:border-cyan-400/30 transition-all relative overflow-hidden">
             <div className="flex items-center justify-between">
                <div className="p-1.5 rounded bg-cyan-400/10 text-cyan-400">
                    {layerIcons[l.layer]}
                </div>
                <div className={`px-2 py-0.5 rounded text-[8px] font-mono uppercase ${
                    l.status === 'active' ? 'bg-green-400/10 text-green-400' : 
                    l.status === 'isolated' ? 'bg-amber-400/10 text-amber-400' : 'bg-white/10 text-white/40'
                }`}>
                    {l.status}
                </div>
             </div>
             
             <div>
                <div className="text-[10px] font-mono uppercase text-white/30 tracking-tight">{l.layer} Layer</div>
                <div className="text-lg font-bold text-white/90 capitalize">{l.layer}</div>
             </div>

             <div className="flex justify-between items-center mt-1">
                <span className="text-[9px] font-mono text-white/20 uppercase">Latency</span>
                <span className="text-[10px] font-mono text-cyan-400/70">{l.latency}ms</span>
             </div>

             {l.status === 'active' && (
                 <motion.div 
                    animate={{ x: [-100, 200] }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                    className="absolute bottom-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent"
                 />
             )}
          </div>
        ))}
      </div>
    </div>
  );
};
