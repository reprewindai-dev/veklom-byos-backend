// @ts-nocheck
import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { SpeculativePath } from '../types';
import { GitBranch, ShieldCheck, XCircle } from 'lucide-react';

interface SpeculativeGraphProps {
  paths: SpeculativePath[];
}

export const SpeculativeGraph: React.FC<SpeculativeGraphProps> = ({ paths }) => {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-mono uppercase tracking-[0.2em] text-white/50">Agent Reasoning Traces (State-over-Tokens)</h3>
        <div className="flex gap-2">
           <span className="text-[10px] font-mono text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded border border-cyan-400/20">Active: {paths.filter(p => p.status === 'active').length}</span>
           <span className="text-[10px] font-mono text-red-400 bg-red-400/10 px-2 py-0.5 rounded border border-red-400/20">Pruned: {paths.filter(p => p.status === 'pruned').length}</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <AnimatePresence mode="popLayout">
          {paths.map((path, idx) => (
            <motion.div
              layout
              key={path.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ delay: idx * 0.1 }}
              className={`relative p-4 rounded-xl border ${
                path.status === 'active' 
                ? 'bg-cyan-950/20 border-cyan-500/30' 
                : 'bg-red-950/20 border-red-500/10 text-white/40 grayscale'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-lg ${path.status === 'active' ? 'bg-cyan-500/20 text-cyan-400' : 'bg-red-500/10 text-red-400'}`}>
                    {path.status === 'active' ? <ShieldCheck size={14} /> : <XCircle size={14} />}
                  </div>
                  <span className="text-sm font-medium">{path.label}</span>
                </div>
                <span className="text-[10px] font-mono opacity-50">{(path.probability * 100).toFixed(0)}%</span>
              </div>
              
              <p className="text-[12px] leading-relaxed mb-3 opacity-80 italic">
                "{path.insight}"
              </p>

              <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${path.probability * 100}%` }}
                  className={`h-full ${path.status === 'active' ? 'bg-cyan-400' : 'bg-red-400'}`}
                />
              </div>

              {path.status === 'pruned' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px] rounded-xl">
                   <div className="bg-red-500 text-white text-[10px] font-mono px-2 py-1 rotate-[-10deg] uppercase tracking-widest font-bold">Pruned</div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
};
