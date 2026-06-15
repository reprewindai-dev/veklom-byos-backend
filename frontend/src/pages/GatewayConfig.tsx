import React from 'react';
import { Server, Activity, ArrowRightLeft, Database, Zap, Cpu } from 'lucide-react';

export const GatewayConfig: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-neutral-200">
      <header className="p-6 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-10 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans tracking-tight flex items-center gap-2">
            <Server className="w-5 h-5 text-purple-400" /> Intelligent Routing Gateway
          </h1>
          <p className="text-xs text-neutral-500 font-mono mt-1 uppercase tracking-widest">Self-Healing Circuit Breaker & Cost Intelligence</p>
        </div>
        <div className="px-3 py-1 bg-purple-500/10 border border-purple-500/20 text-purple-400 font-mono text-[10px] rounded uppercase font-bold tracking-widest">
          Sovereign Mode: Active
        </div>
      </header>

      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-y-auto">
        <div className="border border-neutral-850 rounded-xl p-5 bg-black/40 shadow-[0_0_15px_rgba(168,85,247,0.02)]">
          <h2 className="text-sm font-bold font-mono text-purple-400 flex items-center gap-2 mb-4 uppercase tracking-wider">
            <ArrowRightLeft className="w-4 h-4" /> Active Routing Strategies
          </h2>
          <div className="space-y-4">
            
            {/* Primary Strategy */}
            <div className="p-4 bg-purple-950/10 border border-purple-900/30 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-bold text-white font-mono flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.8)]"></span> Cost-Optimized Sovereign Fallback
                </div>
                <span className="text-[9px] uppercase font-bold text-purple-400 tracking-widest">Enforced</span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-neutral-400 bg-black/40 p-2 rounded border border-neutral-800/50 mb-2">
                <Cpu size={14} className="text-emerald-400" />
                <span>GPC Base Node (Local)</span>
                <ArrowRightLeft size={12} className="text-neutral-600" />
                <Zap size={14} className="text-blue-400" />
                <span>Repolgate Burst (Cloud)</span>
              </div>
              <p className="text-[10px] text-neutral-500 font-mono leading-relaxed mt-2">
                Routes locally to GPC to maintain $0.00 compute cost. Automatically bursts to Repolgate if concurrency exceeds threshold or circuit breaker triggers.
              </p>
            </div>
            
            {/* Experimental Strategy */}
            <div className="p-4 bg-neutral-900/40 border border-neutral-800 rounded-lg opacity-80">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-bold text-white font-mono flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neutral-600"></span> Speed-Optimized Routing
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-9 h-5 bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-500"></div>
                </label>
              </div>
              <p className="text-[10px] text-neutral-500 font-mono leading-relaxed">
                Prioritizes latency over cost. Dynamically routes to fastest responding node globally. Disables full sovereignty guarantees.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="border border-neutral-850 rounded-xl p-5 bg-black/40 shadow-inner">
            <h2 className="text-sm font-bold font-mono text-cyan-400 flex items-center gap-2 mb-4 uppercase tracking-wider">
              <Database className="w-4 h-4" /> Zero-Trust Vault
            </h2>
            <p className="text-[10px] text-neutral-400 mb-4 font-mono leading-relaxed">
              Cryptographically hashes API keys and provider tokens at rest (AES-256-GCM). Client never sees internal routing keys.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded p-3 mb-4 flex justify-between items-center text-xs font-mono">
              <span className="text-neutral-500">Provider: Repolgate</span>
              <span className="text-cyan-400">Secured ✓</span>
            </div>
            <button className="w-full py-2.5 bg-neutral-800 hover:bg-neutral-700 transition-colors border border-neutral-700 rounded-md text-xs font-bold uppercase tracking-widest font-mono text-white">
              Manage Secrets
            </button>
          </div>
          
          <div className="border border-emerald-900/20 rounded-xl p-5 bg-emerald-950/10 shadow-inner">
            <h2 className="text-sm font-bold font-mono text-emerald-500 flex items-center gap-2 mb-2 uppercase tracking-wider">
              <Activity className="w-4 h-4" /> Circuit Breaker Status
            </h2>
            <div className="text-2xl font-bold text-white font-mono mb-1">CLOSED (Healthy)</div>
            <p className="text-[10px] text-emerald-400/80 font-mono leading-relaxed">
              Primary sovereign nodes operating optimally. 0 failures in last 24h.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};
