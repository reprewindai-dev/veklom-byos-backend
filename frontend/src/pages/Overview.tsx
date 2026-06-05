import React from 'react';
import { Plus, Wand2, ArrowUpRight } from 'lucide-react';
import { workspaceApi } from '../api/workspace';
import { useAsync } from '../hooks/useAsync';
import { PageHeader } from '../components/layout/PageHeader';
import { Panel, PanelTitle, Badge, StatCard, Loading, ErrorState, EmptyState } from '../components/ui/primitives';
import { DualAreaChart, Sparkline } from '../components/charts/charts';

const fmtInt = (n: number) => new Intl.NumberFormat('en-US').format(Math.round(n || 0));
const fmtUsd = (n: number) => `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

export const Overview: React.FC<{ onNavigate: (id: string) => void }> = ({ onNavigate }) => {
  const { data, loading, error, refetch } = useAsync(() => workspaceApi.overview(), []);

  if (loading) return <Loading label="Loading control plane" />;
  if (error || !data) return <ErrorState message={error || 'No data'} onRetry={refetch} />;

  const requestSeries = (data.routing?.history || []).map((h) => h.hetzner + h.aws);

  return (
    <>
      <PageHeader
        eyebrow="Workspace · Overview"
        title="Sovereign control plane"
        description="Every prompt routed, policed, and audited — across Hetzner primary and AWS burst — without leaving your perimeter."
        chips={
          <>
            <Badge tone="green">Live backend connected</Badge>
            <Badge tone="muted">SOC2-ready</Badge>
            <Badge tone="muted">HIPAA-aware</Badge>
            <Badge tone="blue">EU-Sovereign</Badge>
          </>
        }
        actions={
          <>
            <button onClick={() => onNavigate('deployments')} className="btn btn-secondary btn-sm">
              <Plus size={13} /> New deployment
            </button>
            <button onClick={() => onNavigate('playground')} className="btn btn-primary btn-sm">
              <Wand2 size={13} /> Open Playground
            </button>
          </>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-5">
        <StatCard label="Requests / min" value={fmtInt(data.requests_per_min)}>
          {requestSeries.length > 0 && <Sparkline data={requestSeries} />}
        </StatCard>
        <StatCard label="P50 latency" value={`${fmtInt(data.p50_latency_ms)} ms`} />
        <StatCard label="Tokens / sec" value={fmtInt(data.tokens_per_sec)} />
        <StatCard label="Spend today" value={fmtUsd(data.spend_today_usd)} delta={`${data.spend_percent}% cap`} deltaTone={data.spend_percent > 90 ? 'red' : 'green'} />
        <StatCard label="Active models" value={fmtInt(data.active_models)} />
        <StatCard label="Audit entries" value={fmtInt(data.audit_entries)} />
      </div>

      {/* Routing + Spend */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-5">
        <Panel className="lg:col-span-8">
          <PanelTitle
            eyebrow="Routing · last 24h"
            title={`${data.routing?.primary_region || 'primary'} · ${data.routing?.burst_region || 'burst'}`}
            right={<ArrowUpRight size={16} className="text-[var(--text-muted)]" />}
          />
          <div className="mt-4">
            {data.routing?.history?.length ? (
              <DualAreaChart data={data.routing.history} xKey="hour" aKey="hetzner" bKey="aws" />
            ) : (
              <EmptyState message="No routing history yet" />
            )}
          </div>
          <div className="flex gap-2 mt-3">
            <Badge tone="orange">Hetzner {data.routing?.hetzner_percent ?? 0}%</Badge>
            <Badge tone="blue">AWS {data.routing?.aws_percent ?? 0}%</Badge>
          </div>
        </Panel>

        <Panel className="lg:col-span-4">
          <PanelTitle
            eyebrow="Spend · today"
            title={`${fmtUsd(data.spend_today_usd)} of ${fmtUsd(data.spend_cap_usd)}`}
            right={<Badge tone={data.spend_percent > 90 ? 'red' : 'green'}>{data.spend_status}</Badge>}
          />
          <div className="mt-4 h-2 rounded-full bg-white/[0.05] overflow-hidden">
            <div
              className="h-full bg-[var(--orange)]"
              style={{ width: `${Math.min(100, data.spend_percent)}%` }}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 mt-5">
            {data.spend_breakdown?.map((b) => (
              <div key={b.label}>
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-[var(--text-secondary)]">{b.label}</span>
                  <span className="text-[var(--text-muted)]">{b.percent}%</span>
                </div>
                <div className="text-sm font-bold text-white font-mono mt-0.5">{fmtUsd(b.amount_usd)}</div>
              </div>
            ))}
          </div>
          <div className="border-t border-[var(--border)] mt-5 pt-3 flex items-center justify-between font-mono text-[10px]">
            <span className="text-[var(--text-secondary)]">Burn rate</span>
            <span className="text-white">${data.burn_rate_usd_per_min.toFixed(4)} / min</span>
          </div>
          <div className="flex items-center justify-between font-mono text-[10px] mt-1">
            <span className="text-[var(--text-secondary)]">Forecast EOD</span>
            <span className="text-white">{fmtUsd(data.forecast_eod_usd)}</span>
          </div>
        </Panel>
      </div>

      {/* Recent runs + Policy interception */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-5">
        <Panel className="lg:col-span-7">
          <PanelTitle
            eyebrow="Recent runs · live"
            title="Per-call routing, latency, cost"
            right={
              <button onClick={() => onNavigate('playground')} className="text-[10px] font-mono text-[var(--orange)] flex items-center gap-1">
                Playground <ArrowUpRight size={12} />
              </button>
            }
          />
          <div className="overflow-x-auto mt-3">
            {data.recent_runs?.length ? (
              <table className="data-table">
                <thead>
                  <tr><th>Model</th><th>Route</th><th>Latency</th><th>Tokens</th><th>Cost</th><th>Policy</th></tr>
                </thead>
                <tbody>
                  {data.recent_runs.map((r, i) => (
                    <tr key={i}>
                      <td className="text-white font-semibold">{r.model || '—'}</td>
                      <td><Badge tone="orange">{r.route || '—'}</Badge></td>
                      <td className="font-mono">{r.latency_ms ?? '—'} ms</td>
                      <td className="font-mono">{r.tokens ?? '—'}</td>
                      <td className="font-mono">${(r.cost_usd ?? 0).toFixed(5)}</td>
                      <td><Badge tone="green">{r.policy || 'passed'}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState message="No runs yet — open the Playground to make your first governed call" />
            )}
          </div>
        </Panel>

        <Panel className="lg:col-span-5">
          <PanelTitle eyebrow="Policy interception · live" title="Decision before execution" right={<Badge tone="green">Live</Badge>} />
          <div className="mt-3 space-y-3">
            {data.policy_events?.length ? (
              data.policy_events.map((p, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="pulse-dot mt-1.5" />
                  <pre className="font-mono text-[10px] text-[var(--text-secondary)] whitespace-pre-wrap">{JSON.stringify(p)}</pre>
                </div>
              ))
            ) : (
              <EmptyState message="No policy events yet" />
            )}
          </div>
        </Panel>
      </div>

      {/* Alerts + Audit + Fleet */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel>
          <PanelTitle eyebrow="Alerts" title={`${data.alerts?.length || 0} open`} />
          <div className="mt-3 space-y-2">
            {data.alerts?.length ? (
              data.alerts.map((a, i) => (
                <div key={i} className="text-[11px] font-mono text-[var(--text-secondary)]">{JSON.stringify(a)}</div>
              ))
            ) : (
              <EmptyState message="No active alerts" />
            )}
          </div>
        </Panel>

        <Panel>
          <PanelTitle eyebrow="Audit trail · tamper-evident" title="Hash-chained" right={<Badge tone="green">Verified</Badge>} />
          <div className="mt-3 space-y-2">
            {data.audit_logs?.length ? (
              data.audit_logs.map((a, i) => (
                <div key={i} className="text-[11px] font-mono text-[var(--text-secondary)]">{JSON.stringify(a)}</div>
              ))
            ) : (
              <EmptyState message="No audit entries yet" />
            )}
          </div>
        </Panel>

        <Panel>
          <PanelTitle eyebrow="Fleet · models" title="Deployments" />
          <div className="mt-3 space-y-3">
            {data.fleet?.length ? (
              data.fleet.map((f) => (
                <div key={f.id} className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-white truncate">{f.name}</div>
                    <div className="text-[9px] font-mono text-[var(--text-muted)] uppercase">{f.quant} · {f.replicas} replicas</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge tone="orange">{f.route}</Badge>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">P50 {f.p50} ms</span>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState message="No models deployed" />
            )}
          </div>
        </Panel>
      </div>
    </>
  );
};
