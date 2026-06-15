// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { ExternalLink, Share2, BrainCircuit } from 'lucide-react';

interface SSRNSignal {
  id: string;
  category: string;
  title: string;
  source: string;
  matchStrength: number;
}

export const SignalIngestionFeed: React.FC = () => {
  const [signals, setSignals] = useState<SSRNSignal[]>([]);

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const res = await fetch('/api/uacp/hub/ssrn');
        if (res.ok) {
          const contentType = res.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const data = await res.json().catch(() => null);
            if (data) {
              setSignals(data);
            }
          }
        }
      } catch (e) {
        console.error("Signal fetch failed", e);
      }
    };

    fetchSignals();
    const interval = setInterval(fetchSignals, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#0b1219]/60 border border-cyan-900/40 rounded-xl p-4 relative backdrop-blur-sm h-full flex flex-col">
      <div className="text-[10px] tracking-widest text-white/90 font-sans mb-4 flex items-center justify-between uppercase">
        <div className="flex items-center gap-2">
            <BrainCircuit size={14} className="text-cyan-500" />
            <span>Academic Research Ingestion</span>
        </div>
        <span className="text-cyan-500/40 tracking-[0.2em] font-mono">LIVE_SCAN</span>
      </div>
      
      <div className="space-y-3 overflow-y-auto pr-2 scrollbar-hide flex-1">
        {signals.map((signal) => (
          <div key={signal.id} className="bg-cyan-950/20 border border-cyan-900/40 p-3 rounded-xl hover:border-cyan-700/50 transition-colors">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[9px] font-bold text-cyan-400/70 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-900/50">
                {signal.source}
              </span>
              <div className="flex gap-2 text-white/30">
                <Share2 size={12} className="cursor-pointer hover:text-white" />
                <a href={`https://doi.org/${signal.id.replace('crossref-', '').replace('openalex-', '')}`} target="_blank" rel="noopener noreferrer">
                  <ExternalLink size={12} className="cursor-pointer hover:text-white" />
                </a>
              </div>
            </div>
            <h3 className="text-[11px] text-white/90 leading-snug font-medium mb-1 font-sans">{signal.title}</h3>
            <p className="text-[9px] text-white/40 mb-3">{signal.category}</p>
            
            <div className="flex items-center justify-between text-[9px]">
               <span className="text-white/30 truncate">Strength</span>
               <div className="flex items-center gap-2">
                 <div className="w-16 h-1 bg-cyan-950 rounded-full overflow-hidden">
                    <div className="h-full bg-cyan-500/50" style={{ width: `${signal.matchStrength}%` }}></div>
                 </div>
                 <span className="font-mono text-cyan-400 font-bold">{signal.matchStrength}%</span>
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
