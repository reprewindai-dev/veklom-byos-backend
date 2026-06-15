import React from 'react';
import { ScrollText, Filter, Search, ChevronRight, Activity, ShieldCheck, Coins } from 'lucide-react';

export const AuditTrace: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-neutral-200">
      <header className="p-6 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-10 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans tracking-tight flex items-center gap-2">
            <ScrollText className="w-5 h-5 text-emerald-400" /> Sovereign Transaction Ledger
          </h1>
          <p className="text-xs text-neutral-500 font-mono mt-1 uppercase tracking-widest">Immutable HMAC-SHA256 Audit Trail (PGL)</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input 
              type="text" 
              placeholder="Search by Hash or TxID..." 
              className="pl-9 pr-4 py-2 bg-black/40 border border-neutral-800 rounded-md text-xs font-mono text-neutral-200 focus:outline-none focus:border-emerald-500/50 w-64"
            />
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-md text-xs font-mono hover:bg-neutral-800 transition-colors">
            <Filter className="w-3.5 h-3.5" /> Filters
          </button>
        </div>
      </header>

      <main className="flex-1 p-6">
        <div className="border border-neutral-850 rounded-xl bg-black/40 overflow-hidden shadow-[0_0_15px_rgba(16,185,129,0.02)]">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-neutral-900/50 border-b border-neutral-850 text-neutral-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-medium">Cryptographic Hash</th>
                <th className="px-4 py-3 font-medium">Sovereign Node</th>
                <th className="px-4 py-3 font-medium">Tokens</th>
                <th className="px-4 py-3 font-medium">ACP-402 Status</th>
                <th className="px-4 py-3 font-medium">Value</th>
                <th className="px-4 py-3 font-medium">Guardrail</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-850">
              {/* Row 1 - GPC */}
              <tr className="hover:bg-neutral-900/30 transition-colors group cursor-pointer">
                <td className="px-4 py-3 font-medium text-blue-400">sha256:8f92b...</td>
                <td className="px-4 py-3 text-neutral-300">GPC Base</td>
                <td className="px-4 py-3 text-neutral-400">1,240</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 w-max">
                    <Coins size={10} /> Paid
                  </span>
                </td>
                <td className="px-4 py-3 text-emerald-400 font-bold">$0.0052</td>
                <td className="px-4 py-3">
                  <span className="text-neutral-500 flex items-center gap-1"><ShieldCheck size={12} className="text-emerald-400"/> Clean</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <ChevronRight className="w-4 h-4 text-neutral-600 group-hover:text-emerald-400 transition-colors ml-auto" />
                </td>
              </tr>
              {/* Row 2 - Repolgate */}
              <tr className="hover:bg-neutral-900/30 transition-colors group cursor-pointer">
                <td className="px-4 py-3 font-medium text-blue-400">sha256:3a19c...</td>
                <td className="px-4 py-3 text-neutral-300">Repolgate</td>
                <td className="px-4 py-3 text-neutral-400">850</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 w-max">
                    <Coins size={10} /> Paid
                  </span>
                </td>
                <td className="px-4 py-3 text-emerald-400 font-bold">$0.0034</td>
                <td className="px-4 py-3">
                  <span className="text-neutral-500 flex items-center gap-1"><ShieldCheck size={12} className="text-emerald-400"/> Clean</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <ChevronRight className="w-4 h-4 text-neutral-600 group-hover:text-emerald-400 transition-colors ml-auto" />
                </td>
              </tr>
              {/* Row 3 - Blocked */}
              <tr className="hover:bg-neutral-900/30 transition-colors group cursor-pointer">
                <td className="px-4 py-3 font-medium text-blue-400">sha256:7b21e...</td>
                <td className="px-4 py-3 text-neutral-300">GPC Base</td>
                <td className="px-4 py-3 text-neutral-400">0</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-neutral-500/10 text-neutral-400 border border-neutral-500/20 flex items-center gap-1 w-max">
                    Blocked
                  </span>
                </td>
                <td className="px-4 py-3 text-neutral-500 font-bold">$0.0000</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">PII Intercept</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <ChevronRight className="w-4 h-4 text-neutral-600 group-hover:text-emerald-400 transition-colors ml-auto" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};
