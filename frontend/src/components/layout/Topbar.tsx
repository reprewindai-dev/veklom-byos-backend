import React, { useState } from 'react';
import { Search, Bell, ChevronDown } from 'lucide-react';
import type { OverviewPayload } from '../../api/workspace';
import type { AuthUser } from '../../api/auth';

interface TopbarProps {
  user: AuthUser | null;
  overview: OverviewPayload | null;
  onSearch?: (q: string) => void;
}

export const Topbar: React.FC<TopbarProps> = ({ user, overview, onSearch }) => {
  const [q, setQ] = useState('');
  const burn = overview ? `$${overview.burn_rate_usd_per_min.toFixed(4)}/min` : null;
  const budgetPct = overview ? overview.spend_percent : null;
  const status = overview?.spend_status;
  const healthy = !status || status === 'on-pace';
  const region = overview?.routing?.primary_region || '';
  const sovereign = /fsn|fra|eu/i.test(region);
  const wsName = user?.workspace_name || user?.workspace_id || 'workspace';

  return (
    <header className="shell-header justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-1.5 font-mono text-[10px] text-white/80 bg-white/[0.03] border border-[var(--border)] rounded px-2 py-1 cursor-pointer shrink-0">
          <span className="pulse-dot" />
          <span className="uppercase font-semibold truncate max-w-[120px]">{wsName}</span>
          <ChevronDown size={11} className="text-[var(--text-muted)]" />
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSearch?.(q);
        }}
        className="flex-1 max-w-xl relative"
      >
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Jump to model, deployment, log, or doc…"
          className="form-input !py-1.5 !pl-8 !text-xs font-mono"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] font-mono text-[var(--text-faint)]">
          ⌘K
        </span>
      </form>

      <div className="flex items-center gap-2 shrink-0">
        {burn && (
          <div className="hidden md:flex items-center gap-2 font-mono text-[10px] bg-white/[0.03] border border-[var(--border)] rounded px-2 py-1">
            <span className="text-[var(--text-muted)]">Burn</span>
            <span className="text-white font-semibold">{burn}</span>
            {budgetPct !== null && (
              <span className={budgetPct > 90 ? 'text-[var(--red)]' : 'text-[var(--text-secondary)]'}>
                {budgetPct}% budget
              </span>
            )}
          </div>
        )}
        <span className={`badge ${healthy ? 'badge-green' : 'badge-orange'}`}>
          {healthy ? 'Healthy' : status}
        </span>
        {sovereign && <span className="badge badge-blue">EU-Sovereign</span>}
        <button className="text-[var(--text-muted)] hover:text-white transition-colors p-1">
          <Bell size={15} />
        </button>
        <div className="w-7 h-7 rounded-full border border-white/10 flex items-center justify-center bg-white/[0.02] text-[var(--orange)] font-bold text-[10px] font-mono uppercase">
          {(user?.email || 'u').slice(0, 2)}
        </div>
      </div>
    </header>
  );
};
