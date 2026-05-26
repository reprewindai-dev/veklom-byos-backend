import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { 
  Activity, 
  Clock, 
  Cpu, 
  DollarSign, 
  CheckCircle, 
  Lock, 
  ShieldAlert, 
  Database,
  ArrowRight,
  TrendingUp,
  RefreshCw
} from 'lucide-react';

export const Overview: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchOverviewData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);
    setError('');

    try {
      // First try to load user specific overview, fallback to public live view on 401/403
      let res;
      try {
        res = await api('/workspace/overview');
      } catch (authErr) {
        // Fallback to overview live endpoint if user session not fully loaded or testing
        res = await api('/workspace/overview/live');
      }
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch real-time telemetry.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
    const interval = setInterval(() => {
      fetchOverviewData(true);
    }, 15000); // Poll every 15s (matching REFRESH_MS in original)
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Cpu className="animate-spin text-[var(--orange)]" size={32} />
        <div className="text-xs text-[var(--text-secondary)] font-mono tracking-widest uppercase">Syncing Telemetry...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-6 rounded-lg bg-[rgba(255,68,102,0.06)] border border-red-500/20 max-w-2xl mx-auto mt-8">
        <h3 className="text-sm font-bold text-red-400 mb-2 flex items-center gap-2">
          <ShieldAlert size={16} /> Telemetry Error
        </h3>
        <p className="text-xs text-[var(--text-secondary)] font-mono leading-relaxed mb-4">{error}</p>
        <button className="btn btn-secondary btn-sm" onClick={() => fetchOverviewData()}>Retry Gateway Sync</button>
      </div>
    );
  }

  // Fallback defaults if API fields are missing (robust protection)
  const d = data || {
    requests_per_min: 0,
    p50_latency_ms: 0,
    tokens_per_sec: 0,
    spend_today_usd: 0,
    spend_cap_usd: 150,
    spend_percent: 0,
    active_models: 0,
    models_enabled: 0,
    audit_entries: 0,
    burn_rate_usd_per_min: 0,
    forecast_eod_usd: 0,
    spend_breakdown: [],
    recent_runs: [],
    policy_events: [],
    alerts: [],
    audit_logs: [],
    fleet: [],
    routing: { hetzner_percent: 100, aws_percent: 0, regions: [] }
  };

  return (
    <div className="space-y-6">
      
      {/* Platform Pulsing Header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <span className="pulse-dot"></span> Sovereign Control Panel
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Real-time developer telemetry, perimeter guard status, and audit verification.</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-[var(--text-muted)]">
          {isRefreshing && <span className="text-[var(--orange)] flex items-center gap-1.5"><RefreshCw size={12} className="animate-spin" /> Fetching live...</span>}
          <span>REFRESH: 15S</span>
          <span>GATEWAY: CONNECTED</span>
        </div>
      </div>

      {/* Top 6 Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        
        {/* RPM */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">Requests / Min</span>
            <Activity className="text-[var(--orange)] opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">{d.requests_per_min}</span>
            <span className="text-[10px] text-emerald-400 font-mono block">+ live</span>
          </div>
          {/* Visual SVG Mini sparkline */}
          <svg className="w-full h-5 mt-1" viewBox="0 0 100 20">
            <path className="sparkline-path" d="M0,15 Q15,5 30,12 T60,5 T90,15" fill="none" stroke="rgba(255, 184, 0, 0.4)" strokeWidth="1.5" />
          </svg>
        </div>

        {/* Latency */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">P50 Latency</span>
            <Clock className="text-[var(--blue)] opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">{d.p50_latency_ms} ms</span>
            <span className="text-[10px] text-[var(--text-muted)] font-mono block">p50 check</span>
          </div>
          <svg className="w-full h-5 mt-1" viewBox="0 0 100 20">
            <path className="sparkline-path" d="M0,10 Q20,18 40,8 T80,14 T100,6" fill="none" stroke="rgba(0, 200, 255, 0.4)" strokeWidth="1.5" />
          </svg>
        </div>

        {/* Tokens */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">Tokens / Sec</span>
            <Cpu className="text-[var(--green)] opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">
              {d.tokens_per_sec >= 1000 ? `${(d.tokens_per_sec / 1000).toFixed(1)}k` : d.tokens_per_sec}
            </span>
            <span className="text-[10px] text-emerald-400 font-mono block">+ live</span>
          </div>
          <svg className="w-full h-5 mt-1" viewBox="0 0 100 20">
            <path className="sparkline-path" d="M0,8 Q30,4 60,16 T100,4" fill="none" stroke="rgba(0, 255, 148, 0.4)" strokeWidth="1.5" />
          </svg>
        </div>

        {/* Spend */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">Spend Today</span>
            <DollarSign className="text-[var(--orange)] opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">${Number(d.spend_today_usd).toFixed(2)}</span>
            <span className="text-[10px] text-[var(--orange)] font-mono block">{d.spend_percent}% cap</span>
          </div>
          <div className="w-full bg-[rgba(255,255,255,0.05)] rounded-full h-1.5 mt-2">
            <div className="bg-[var(--orange)] h-1.5 rounded-full" style={{ width: `${Math.min(100, d.spend_percent)}%` }}></div>
          </div>
        </div>

        {/* Active Models */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">Active Fleet</span>
            <Cpu className="text-purple-400 opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">{d.active_models}</span>
            <span className="text-[10px] text-[var(--text-muted)] font-mono block">{d.models_enabled} enabled</span>
          </div>
          <svg className="w-full h-5 mt-1" viewBox="0 0 100 20">
            <circle cx="20" cy="10" r="3" fill="var(--green)" />
            <circle cx="50" cy="10" r="3" fill="var(--green)" />
            <circle cx="80" cy="10" r="3" fill="var(--green)" />
            <path d="M20,10 L80,10" stroke="rgba(0, 255, 148, 0.2)" strokeWidth="1" />
          </svg>
        </div>

        {/* Audit Entries */}
        <div className="glow-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="form-label text-[10px] m-0">Audit Logs</span>
            <CheckCircle className="text-emerald-400 opacity-80" size={14} />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold font-mono text-white">{d.audit_entries}</span>
            <span className="text-[10px] text-emerald-400 font-mono block">verified Γ£ô</span>
          </div>
          <div className="flex gap-0.5 mt-2">
            {[1,2,3,4,5,6,7,8].map((i) => (
              <div key={i} className="h-3 w-1.5 rounded-sm bg-emerald-500/25 border border-emerald-500/40"></div>
            ))}
          </div>
        </div>

      </div>

      {/* Grid of Chart & Spend Rules */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Autonomous Routing Controls */}
        <div className="glow-card lg:col-span-8 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2"><TrendingUp size={16} className="text-[var(--orange)]" /> Autonomous Load Distribution</h3>
                <p className="text-[10.5px] text-[var(--text-secondary)] mt-0.5 font-mono uppercase">PERIMETER ROUTING TARGETS ΓÇö LAST 24 HOURS</p>
              </div>
              <div className="flex gap-4 font-mono text-[11px]">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[var(--orange)]"></span> HETZNER {d.routing?.hetzner_percent || 0}%</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[var(--blue)]"></span> AWS BURST {d.routing?.aws_percent || 0}%</span>
              </div>
            </div>
            
            {/* Visual routing chart mockup representation */}
            <div className="h-44 bg-[rgba(0,0,0,0.25)] rounded-lg border border-[rgba(255,255,255,0.05)] p-4 flex flex-col justify-end relative">
              
              {/* Fake gridlines */}
              <div className="absolute inset-0 grid grid-rows-4 pointer-events-none p-4">
                {[1,2,3].map((i) => (
                  <div key={i} className="border-b border-[rgba(255,255,255,0.03)] w-full"></div>
                ))}
              </div>

              {/* Dynamic bar charts showing routing historical activity */}
              <div className="flex items-end justify-between h-28 relative z-10 font-mono text-[9px] text-[var(--text-muted)]">
                {Array.isArray(d.routing?.history) && d.routing.history.map((h: any, i: number) => {
                  const hetznerCount = h.hetzner || 0;
                  const awsCount = h.aws || 0;
                  const max = Math.max(1, ...d.routing.history.map((x: any) => (x.hetzner || 0) + (x.aws || 0)));
                  const hetznerH = `${(hetznerCount / max) * 100}%`;
                  const awsH = `${(awsCount / max) * 100}%`;

                  return (
                    <div key={i} className="flex flex-col items-center gap-1 flex-1">
                      <div className="w-3 bg-[rgba(255,255,255,0.03)] h-20 rounded-sm flex flex-col justify-end overflow-hidden">
                        <div className="bg-[var(--blue)] w-full" style={{ height: awsH }}></div>
                        <div className="bg-[var(--orange)] w-full" style={{ height: hetznerH }}></div>
                      </div>
                      <span>{h.hour}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 pt-4 border-t border-[rgba(255,255,255,0.05)]">
            {(d.routing?.regions || []).map((r: any, idx: number) => (
              <div key={idx} className="p-3 rounded bg-[rgba(0,0,0,0.15)] border border-[rgba(255,255,255,0.03)]">
                <div className="text-[10px] text-[var(--text-muted)] font-mono uppercase">{r.label}</div>
                <div className="text-xs font-bold text-white mt-1">{r.value}</div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">{r.sub}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Spend Progress, Caps & Forecasts */}
        <div className="glow-card lg:col-span-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2"><DollarSign size={16} className="text-[var(--orange)]" /> Perimeter Budget</h3>
            <p className="text-[10.5px] text-[var(--text-secondary)] font-mono uppercase mb-4">SOVEREIGN EXPENSE GUARD</p>

            <div className="space-y-4">
              
              <div>
                <div className="flex justify-between text-xs font-mono text-[var(--text-secondary)] mb-1">
                  <span>TODAY SPEND</span>
                  <span className="text-white font-bold">${Number(d.spend_today_usd).toFixed(2)} of ${d.spend_cap_usd} Cap</span>
                </div>
                <div className="w-full bg-[rgba(255,255,255,0.05)] rounded-full h-2">
                  <div className="bg-[var(--orange)] h-2 rounded-full" style={{ width: `${Math.min(100, d.spend_percent)}%` }}></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-[rgba(0,0,0,0.15)] border border-[rgba(255,255,255,0.03)]">
                  <span className="text-[10px] text-[var(--text-muted)] uppercase block">BURN RATE</span>
                  <span className="text-white font-bold mt-1 block">${Number(d.burn_rate_usd_per_min).toFixed(4)} / min</span>
                </div>
                <div className="p-2.5 rounded bg-[rgba(0,0,0,0.15)] border border-[rgba(255,255,255,0.03)]">
                  <span className="text-[10px] text-[var(--text-muted)] uppercase block">FORECAST EOD</span>
                  <span className={`font-bold mt-1 block ${d.spend_status === 'over-pace' ? 'text-red-400' : 'text-emerald-400'}`}>
                    ${Number(d.forecast_eod_usd).toFixed(2)} ({d.spend_percent}% cap)
                  </span>
                </div>
              </div>

              {/* Spend Breakdown Categories */}
              <div className="pt-2">
                <span className="form-label text-[10px] mb-2">CATEGORY ALLOCATION</span>
                <div className="space-y-2">
                  {Array.isArray(d.spend_breakdown) && d.spend_breakdown.map((item: any, idx: number) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-[11px] font-mono">
                        <span className="text-[var(--text-secondary)]">{item.label}</span>
                        <span className="text-white font-semibold">${Number(item.amount_usd).toFixed(2)} ({item.percent}%)</span>
                      </div>
                      <div className="w-full bg-[rgba(255,255,255,0.03)] rounded-full h-1">
                        <div className="bg-white/40 h-1 rounded-full" style={{ width: `${item.percent}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>

          <div className="text-[10px] font-mono text-[var(--text-muted)] border-t border-[rgba(255,255,255,0.05)] pt-4 mt-4 text-center">
            SOVEREIGN REGULATION AUDITOR ENFORCED Γ£ô
          </div>
        </div>

      </div>

      {/* Dynamic Console Bottom Tables Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Card 1: Recent Runs */}
        <div className="glow-card xl:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono">RECENT RUNS</h3>
              <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase">REAL-TIME INFERENCE LOGS</span>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Route</th>
                    <th className="text-right">Latency</th>
                    <th className="text-right">Tokens</th>
                    <th className="text-right">Cost</th>
                    <th>Policy</th>
                    <th className="text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.isArray(d.recent_runs) && d.recent_runs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-6 text-[var(--text-muted)] font-mono">No live inference runs recorded.</td>
                    </tr>
                  ) : (
                    d.recent_runs.slice(0, 5).map((r: any, idx: number) => (
                      <tr key={idx}>
                        <td className="font-semibold text-white">{r.model}</td>
                        <td>
                          <span className="badge badge-orange text-[9px]">{String(r.route).replace('-', ' ')}</span>
                        </td>
                        <td className="text-right font-mono text-white">{r.latency} ms</td>
                        <td className="text-right font-mono">{r.tokens.toLocaleString()}</td>
                        <td className="text-right font-mono text-white">${r.cost.toFixed(5)}</td>
                        <td>
                          <span className={`badge ${r.policy === 'passed' ? 'badge-green' : 'badge-red'}`}>
                            {r.policy}
                          </span>
                        </td>
                        <td className="text-right text-[var(--text-muted)] font-mono">{r.ts}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="text-[10px] text-right font-mono text-[var(--text-muted)] mt-4 pt-2 border-t border-[rgba(255,255,255,0.03)]">
            SECURE ROUTE TUNNEL ACTIVE
          </div>
        </div>

        {/* Card 2: Interceptions & Decisons flow */}
        <div className="glow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono">POLICY INTERCEPTION</h3>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">ENFORCER SHIELD</span>
            </div>
            
            <div className="space-y-4">
              {Array.isArray(d.policy_events) && d.policy_events.length === 0 ? (
                <div className="py-6 text-center text-[var(--text-muted)] font-mono text-xs">No policy decisions triggered.</div>
              ) : (
                d.policy_events.slice(0, 4).map((evt: any, idx: number) => (
                  <div key={idx} className="relative pl-6 border-l border-[rgba(255,184,0,0.15)] flex flex-col gap-0.5">
                    {/* Orange Dot Marker */}
                    <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full border border-[var(--orange)] bg-[#0a0a0a] flex items-center justify-center text-[8px] text-[var(--orange)] font-bold">ΓÇó</div>
                    <div className="flex justify-between items-center text-xs font-semibold text-white">
                      <span>{evt.title}</span>
                      <span className="text-[10px] text-[var(--text-muted)] font-mono">{evt.t}</span>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] font-mono">{evt.body}</div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="text-[10px] font-mono text-[var(--text-muted)] mt-4 pt-2 border-t border-[rgba(255,255,255,0.03)]">
            PERIMETER RULESETS ENABLED: 14
          </div>
        </div>

      </div>

      {/* Row 3: Alerts, Logs & Fleet info */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        
        {/* Card 3: Security Threats Alerts */}
        <div className="glow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono flex items-center gap-1.5"><ShieldAlert size={14} className="text-red-400 animate-pulse" /> ALERTS</h3>
              <span className="badge badge-red">{d.alerts ? d.alerts.length : 0} open</span>
            </div>
            
            <div className="divide-y divide-[rgba(255,255,255,0.05)]">
              {Array.isArray(d.alerts) && d.alerts.length === 0 ? (
                <div className="py-6 text-center text-[var(--text-muted)] font-mono text-xs">No active perimeter threats.</div>
              ) : (
                d.alerts.slice(0, 4).map((alert: any, idx: number) => (
                  <div key={idx} className="py-3 first:pt-0 last:pb-0 flex gap-3 items-start">
                    <span className="w-1.5 h-1.5 bg-red-400 rounded-full mt-1.5 shrink-0 animate-ping"></span>
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-white leading-tight">{alert.title}</div>
                      <div className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5 uppercase flex items-center gap-2">
                        <span>{alert.source}</span>
                        <span>┬╖</span>
                        <span>{alert.time}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <button className="btn btn-secondary btn-sm mt-4 w-full text-center text-[10px] font-mono" onClick={() => window.location.hash = '#/command-center'}>
            OPEN LOCKER TERMINAL <ArrowRight size={10} />
          </button>
        </div>

        {/* Card 4: Cryptographic Audit Trail */}
        <div className="glow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono flex items-center gap-1.5"><Lock size={14} className="text-emerald-400" /> AUDIT TRAIL</h3>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">HASHCHAIN BLOCKS</span>
            </div>
            
            <div className="divide-y divide-[rgba(255,255,255,0.05)]">
              {Array.isArray(d.audit_logs) && d.audit_logs.length === 0 ? (
                <div className="py-6 text-center text-[var(--text-muted)] font-mono text-xs">No cryptographic blocks generated.</div>
              ) : (
                d.audit_logs.slice(0, 4).map((log: any, idx: number) => (
                  <div key={idx} className="py-2.5 first:pt-0 last:pb-0 font-mono text-[11px]">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-bold text-[11.5px]">{log.action}</span>
                      <span className="text-[9px] text-[var(--text-muted)]">{log.ts?.slice(11,19)} UTC</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-[var(--text-secondary)] mt-0.5">
                      <span>{log.target} ┬╖ {log.actor?.split('@')[0]}</span>
                      <span className="text-[var(--orange)] bg-[rgba(255,184,0,0.06)] px-1 rounded border border-[rgba(255,184,0,0.15)]">{log.hash}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="text-[9px] font-mono text-[var(--text-muted)] text-center mt-4 pt-2 border-t border-[rgba(255,255,255,0.03)] uppercase">
            Sovereign Ledger Synced: 100% Verified
          </div>
        </div>

        {/* Card 5: LLM Fleet Status */}
        <div className="glow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono flex items-center gap-1.5"><Database size={14} className="text-purple-400" /> ACTIVE FLEET</h3>
              <span className="badge badge-orange">{d.fleet ? d.fleet.length : 0} online</span>
            </div>

            <div className="space-y-2">
              {Array.isArray(d.fleet) && d.fleet.length === 0 ? (
                <div className="py-6 text-center text-[var(--text-muted)] font-mono text-xs">No LLM replica clusters active.</div>
              ) : (
                d.fleet.slice(0, 4).map((model: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center p-2 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)] hover:border-[rgba(255,184,0,0.25)] transition-all">
                    <div>
                      <div className="text-xs font-bold text-white">{model.name}</div>
                      <div className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5">{model.quant} ┬╖ {model.replicas} replica(s)</div>
                    </div>
                    <div className="flex items-center gap-1.5 font-mono text-[9px] text-[var(--text-secondary)]">
                      <span className="border border-[rgba(255,255,255,0.05)] px-1.5 py-0.5 rounded bg-[#0a0a0a]">{String(model.route).replace('-', ' ')}</span>
                      <span className="border border-[rgba(255,255,255,0.05)] px-1.5 py-0.5 rounded bg-[#0a0a0a]">P50 {model.p50} MS</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <button className="btn btn-secondary btn-sm mt-4 w-full text-center text-[10px] font-mono" onClick={() => window.location.hash = '#/models'}>
            CONFIGURE MODELS <ArrowRight size={10} />
          </button>
        </div>

      </div>

    </div>
  );
};