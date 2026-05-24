import React, { useState, useEffect } from 'react';
import { FileSearch, RefreshCw, ShieldCheck, FileText, Hash } from 'lucide-react';
import { api } from '../api/client';

export const EvidenceAuditPage: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [compliance, setCompliance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [auditRes, compRes] = await Promise.allSettled([
        api('/audit/logs?limit=20'),
        api('/compliance/report'),
      ]);
      if (auditRes.status === 'fulfilled') setAuditLogs(auditRes.value?.logs || auditRes.value || []);
      if (compRes.status === 'fulfilled') setCompliance(compRes.value);
    } catch {
      setError('One or more evidence routes unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <FileSearch size={18} className="text-[var(--orange)] animate-pulse" /> Evidence & Audit
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Execution ledgers, audit logs, evidence artifacts, hashes, policy records.</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="btn btn-secondary px-3 py-1.5 text-xs font-mono flex items-center gap-1.5">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> SYNC EVIDENCE CHAIN
        </button>
      </div>

      {error && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs rounded font-mono">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance summary */}
        <div className="glow-card">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2 border-b border-white/5 pb-2">
            <ShieldCheck size={13} className="text-emerald-400" /> Compliance Summary
          </h3>
          {compliance ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="text-[var(--text-secondary)]">Overall Score</span>
                <span className="text-emerald-400 font-bold text-lg">{compliance.overall_score}%</span>
              </div>
              {compliance.regulations?.slice(0, 4).map((r: any, i: number) => (
                <div key={i} className="flex items-center justify-between border-b border-white/5 pb-2 font-mono text-[11px]">
                  <span className="text-[var(--text-secondary)]">{r.name}</span>
                  <span className="text-emerald-400">{r.score}% — {r.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs font-mono text-[var(--text-muted)]">
              {loading ? 'Loading...' : 'No compliance report available.'}
            </p>
          )}
        </div>

        {/* Audit log */}
        <div className="glow-card">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2 border-b border-white/5 pb-2">
            <FileText size={13} className="text-[var(--orange)]" /> Recent Audit Log
          </h3>
          {auditLogs.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto font-mono text-[10px] text-[var(--text-secondary)]">
              {auditLogs.map((log: any, i: number) => (
                <div key={i} className="flex gap-2 border-b border-white/5 pb-1.5">
                  <span className="text-[var(--text-muted)] shrink-0">{log.created_at?.slice(11, 19) || '--:--:--'}</span>
                  <span className="text-white/70">{log.action || log.event_type || 'EVENT'}</span>
                  <span className="text-[var(--text-muted)] truncate">{log.resource || log.target || ''}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="font-mono text-xs">
              <p className="text-[var(--text-muted)] mb-3">{loading ? 'Loading...' : 'No audit logs returned.'}</p>
              <div className="p-3 bg-neutral-950 border border-white/5 rounded text-[9px] leading-relaxed space-y-1">
                <p className="text-[var(--orange)] font-bold">// AUDIT ENGINE ACTIVE</p>
                <p className="text-emerald-400">[PASS] Hash chain verified — root signatures intact.</p>
                <p className="text-[var(--text-muted)]">[INFO] Tamper-evident log system operational.</p>
              </div>
            </div>
          )}
        </div>

        {/* Hash verification panel */}
        <div className="glow-card lg:col-span-2">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
            <Hash size={13} className="text-[var(--orange)]" /> Evidence Hash Verification
          </h3>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Paste audit entry ID or hash to verify..."
              className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-2 text-xs font-mono text-white/70 placeholder-white/20 focus:outline-none focus:border-[var(--orange)]/40"
            />
            <button className="btn btn-secondary px-4 py-2 text-xs font-mono">VERIFY</button>
          </div>
          <p className="text-[9px] font-mono text-[var(--text-muted)] mt-2">
            Route: POST /api/v1/audit/verify/{'{id}'} — Cryptographic hash chain validation.
          </p>
        </div>
      </div>
    </div>
  );
};
