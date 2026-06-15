import React, { useState } from 'react';
import { ShieldCheck, Lock, AlertTriangle, EyeOff, Scale, Server } from 'lucide-react';

export const Governance: React.FC = () => {
  const [piiEnabled, setPiiEnabled] = useState(true);
  const [csamEnabled] = useState(true); // Hardcoded true per manual

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-neutral-200">
      <header className="p-6 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-10 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" /> Sovereignty Guardrails
          </h1>
          <p className="text-xs text-neutral-500 font-mono mt-1 uppercase tracking-widest">Zero-Trust Boundaries & Content Safety</p>
        </div>
      </header>

      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-y-auto">
        <div className="border border-neutral-850 rounded-xl p-5 bg-black/40 shadow-[0_0_15px_rgba(16,185,129,0.02)]">
          <h2 className="text-sm font-bold font-mono text-emerald-400 flex items-center gap-2 mb-4 uppercase tracking-wider">
            <Lock className="w-4 h-4" /> Inline Interceptors
          </h2>
          <div className="space-y-4">
            
            {/* PII Masking */}
            <div className={`p-4 border rounded-lg transition-colors ${piiEnabled ? 'bg-emerald-950/10 border-emerald-900/30' : 'bg-neutral-900/40 border-neutral-800'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <EyeOff className={`w-4 h-4 ${piiEnabled ? 'text-emerald-400' : 'text-neutral-500'}`} />
                  <span className="text-xs font-bold text-white font-mono">GDPR PII Auto-Masking</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={piiEnabled} onChange={() => setPiiEnabled(!piiEnabled)} />
                  <div className="w-9 h-5 bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
                </label>
              </div>
              <p className="text-[10px] text-neutral-400 font-mono leading-relaxed">
                Automatically redact SSN, Email, Phone, and Credit Cards from prompts before routing to the LLM. 
                Re-hydrates the response transparently.
              </p>
            </div>

            {/* CSAM Scanner */}
            <div className="p-4 border border-emerald-900/30 bg-emerald-950/10 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white font-mono">Zero-Tolerance Content Safety</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  Enforced
                </span>
              </div>
              <p className="text-[10px] text-neutral-400 font-mono leading-relaxed">
                Hardware-enforced zero-tolerance pipeline for illicit content detection. Hard-blocks execution instantly. Cannot be disabled.
              </p>
            </div>

          </div>
        </div>

        <div className="space-y-6">
          <div className="border border-neutral-850 rounded-xl p-5 bg-black/40 shadow-inner">
            <h2 className="text-sm font-bold font-mono text-neutral-300 flex items-center gap-2 mb-4 uppercase tracking-wider">
              <Scale className="w-4 h-4 text-blue-400" /> Automated Compliance
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-neutral-900/40 border border-neutral-800 rounded-lg">
                <div className="text-xs font-bold text-white font-mono">SOC2 / HIPAA Audit Anchoring</div>
                <button className="text-[10px] text-blue-400 hover:text-blue-300 font-bold uppercase tracking-widest font-mono">Configure</button>
              </div>
              <p className="text-[10px] text-neutral-500 font-mono leading-relaxed px-1">
                Every API call is cryptographically signed using HMAC-SHA256 and appended to the immutable local ledger.
              </p>
            </div>
          </div>

          <div className="border border-red-900/20 rounded-xl p-5 bg-red-950/10 shadow-inner">
            <h2 className="text-sm font-bold font-mono text-red-500 flex items-center gap-2 mb-4 uppercase tracking-wider">
              <AlertTriangle className="w-4 h-4" /> Workspace Kill Switch
            </h2>
            <p className="text-xs text-neutral-400 mb-4 font-mono leading-relaxed">
              Instantly revoke all access tokens, halt all running autonomous agents, and sever network access.
            </p>
            <button className="w-full py-3 bg-red-900/20 hover:bg-red-900/40 border border-red-900/50 text-red-500 rounded-md text-xs font-bold uppercase tracking-widest font-mono transition-colors">
              ENGAGE KILL SWITCH
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
