import React from 'react';
import { GitBranch, Clock } from 'lucide-react';

export const ChainOpsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-3">
          <GitBranch size={18} className="text-[var(--orange)]" /> ChainOps
        </h2>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">Governed LangChain / chain workflow area — traces, tools, memory, cost.</p>
      </div>

      <div className="py-20 border border-dashed border-white/[0.07] rounded-xl flex flex-col items-center gap-4 text-center">
        <Clock size={32} className="text-[var(--text-muted)]" />
        <div className="space-y-1">
          <p className="text-sm font-bold text-white font-mono">Coming Soon</p>
          <p className="text-xs text-[var(--text-secondary)] max-w-sm">
            ChainOps will surface governed LangChain execution: chains, runs, traces, tools, memory, prompts, cost, errors, and policy gates.
          </p>
        </div>
        <div className="mt-2 px-3 py-1.5 border border-amber-500/20 bg-amber-500/10 rounded font-mono text-[10px] text-amber-400">
          NOT WIRED — Backend route required
        </div>
      </div>
    </div>
  );
};
