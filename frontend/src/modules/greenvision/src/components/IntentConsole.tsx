// @ts-nocheck
import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Terminal, Send, Shield, Zap, Cpu } from 'lucide-react';
import { LLMProvider, ProviderConfig } from '../types';

interface IntentConsoleProps {
  onExecute: (intent: string) => void;
  isLocked: boolean;
  selectedProvider: LLMProvider;
  onProviderChange: (provider: LLMProvider) => void;
  providers: ProviderConfig[];
}

export const IntentConsole: React.FC<IntentConsoleProps> = ({ 
  onExecute, 
  isLocked, 
  selectedProvider, 
  onProviderChange,
  providers 
}) => {
  const [latencyTarget, setLatencyTarget] = useState('< 450ms');
  const [intentValue, setIntentValue] = useState('');

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4 relative overflow-hidden">
      <div className="absolute top-0 right-0 p-1">
         <div className="flex items-center gap-1">
            <div className="w-1 h-1 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[7px] font-mono text-cyan-400/30 uppercase tracking-tighter">Multi-Agent Gateway Ready</span>
         </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={18} className="text-cyan-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Strategic Intent Console</h2>
        </div>
        <div className="flex gap-2">
           <select 
             value={selectedProvider}
             onChange={(e) => onProviderChange(e.target.value as LLMProvider)}
             className="bg-black/60 border border-white/10 rounded-lg px-2 py-1 text-[10px] font-mono text-cyan-400 focus:outline-none focus:border-cyan-400/50"
           >
             {providers.map(p => (
               <option key={p.id} value={p.id}>{p.name}</option>
             ))}
           </select>
        </div>
      </div>

      <div className="relative group">
        <textarea 
          value={intentValue}
          onChange={(e) => setIntentValue(e.target.value)}
          placeholder="State your orchestration intent (e.g., 'Verify satellite coverage for Amazon basin')..."
          className="w-full h-32 bg-black/40 border border-white/10 rounded-xl p-4 text-sm font-mono text-white/90 placeholder:text-white/10 focus:outline-none focus:border-cyan-400/50 transition-all resize-none"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
              if (intentValue) {
                 onExecute(intentValue);
                 setIntentValue('');
              }
            }
          }}
        />
        <div className="absolute bottom-4 right-4 flex gap-3">
             <div className="flex flex-col items-end justify-center mr-2">
                <span className="text-[8px] font-mono text-white/20 uppercase">Model Routing</span>
                <span className="text-[9px] font-mono text-cyan-400/50 font-bold uppercase tracking-widest">
                  {providers.find(p => p.id === selectedProvider)?.name || selectedProvider}
                </span>
             </div>
            <button 
                disabled={isLocked}
                onClick={() => {
                   if (intentValue) {
                      onExecute(intentValue);
                      setIntentValue('');
                   }
                }}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs uppercase font-bold transition-all ${
                    isLocked ? 'bg-white/5 text-white/20 cursor-not-allowed' : 'bg-cyan-400 text-black hover:bg-cyan-300'
                }`}
            >
                <Zap size={14} fill="currentColor" />
                Dispatch
            </button>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 p-3 bg-white/5 border border-white/5 rounded-xl">
         <div className="flex items-center gap-3">
            <Shield size={16} className={isLocked ? "text-red-400/60" : "text-emerald-400/60"} />
            <p className="text-[9px] font-mono text-white/40 uppercase leading-snug">
               {isLocked ? 'Execution Locked: Deterministic Plan Initialization Pending.' : 'Execution Ready: Multi-provider safety gateway verified.'}
            </p>
         </div>
         <div className="flex items-center gap-3 pr-2">
            <div className="h-4 w-px bg-white/10" />
            <div className="flex flex-col">
               <span className="text-[8px] font-mono text-white/20 uppercase">Latency Target</span>
               <select 
                 value={latencyTarget}
                 onChange={(e) => setLatencyTarget(e.target.value)}
                 className="bg-transparent border border-emerald-400/30 rounded px-1 text-[9px] font-mono text-emerald-400 focus:outline-none cursor-pointer min-w-[70px]"
               >
                 <option className="bg-black text-emerald-400" value="< 150ms">{'< 150ms'}</option>
                 <option className="bg-black text-emerald-400" value="< 250ms">{'< 250ms'}</option>
                 <option className="bg-black text-emerald-400" value="< 450ms">{'< 450ms'}</option>
                 <option className="bg-black text-emerald-400" value="< 800ms">{'< 800ms'}</option>
                 <option className="bg-black text-emerald-400" value="relax">{'Relaxed'}</option>
               </select>
            </div>
         </div>
      </div>
    </div>
  );
};
