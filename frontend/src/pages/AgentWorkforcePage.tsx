import React, { useState, useEffect } from 'react';
import { Bot, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

export const AgentWorkforcePage: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAgents = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api('/internal/operators');
      setAgents(Array.isArray(res) ? res : res.operators || []);
    } catch {
      setError('Backend route not wired or requires configuration.');
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAgents(); }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <Bot size={18} className="text-[var(--orange)] animate-pulse" /> Agent Workforce
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Agent registry, identity, runs, and policy enforcement.</p>
        </div>
        <button onClick={fetchAgents} disabled={loading} className="btn btn-secondary px-3 py-1.5 text-xs font-mono flex items-center gap-1.5">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
        </button>
      </div>

      {error && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-3">
          <AlertCircle size={16} className="text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="font-mono text-xs text-amber-300">
            <p className="font-bold mb-1">Backend route missing</p>
            <p className="text-amber-400/70">{error}</p>
            <p className="text-amber-400/50 mt-1">Route: GET /api/v1/internal/operators</p>
          </div>
        </div>
      )}

      {!loading && agents.length === 0 && !error && (
        <div className="py-16 border border-dashed border-white/5 rounded-xl flex flex-col items-center gap-3 text-center font-mono text-xs text-[var(--text-secondary)]">
          <Bot size={24} className="text-[var(--text-muted)]" />
          <p>No agents registered in the operator registry.</p>
        </div>
      )}

      {agents.length > 0 && (
        <div className="space-y-3">
          {agents.map((agent: any, i: number) => (
            <div key={i} className="glow-card p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-white font-mono">{agent.name || agent.id || `Agent ${i + 1}`}</p>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">{agent.role || agent.type || 'No role defined'}</p>
              </div>
              <span className={`text-[9px] font-mono font-bold uppercase border rounded px-2 py-0.5 ${
                agent.status === 'active'
                  ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                  : 'text-[var(--text-muted)] border-white/10 bg-white/[0.02]'
              }`}>{agent.status || 'unknown'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
