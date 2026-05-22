import React from 'react';
import '../modules/greenvision/src/index.css';
import { QuantumDashboard } from '../modules/greenvision/src/components/QuantumDashboard';

export const GreenVisionPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-white/5 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
            <span>Marketplace</span>
            <span>/</span>
            <span className="text-emerald-500">GreenVision</span>
          </div>
          <h2 className="flex items-center gap-3 text-lg font-bold tracking-tight text-white">
            <span className="text-emerald-500">🌿</span> GreenVision Carbon/Cost Routing
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Carbon and cost-aware routing vertical. Optimizes model selection based on regional emissions and workload priority.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase">
          <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-emerald-400">
            Active Vertical
          </span>
        </div>
      </div>

      <div className="h-[800px] rounded-xl overflow-hidden border border-white/10">
        <QuantumDashboard />
      </div>
    </div>
  );
};
