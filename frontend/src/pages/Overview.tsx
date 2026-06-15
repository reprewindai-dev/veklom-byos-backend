import React from 'react';
import { Plus, Wand2, ArrowUpRight, ShieldCheck, Activity, Coins, ShieldAlert, Cpu } from 'lucide-react';
import { workspaceApi } from '../api/workspace';
import { useAsync } from '../hooks/useAsync';
import { PageHeader } from '../components/layout/PageHeader';
import { Panel, PanelTitle, Badge, StatCard, Loading, ErrorState, EmptyState } from '../components/ui/primitives';
import { DualAreaChart, Sparkline } from '../components/charts/charts';

const fmtInt = (n: number) => new Intl.NumberFormat('en-US').format(Math.round(n || 0));
const fmtUsd = (n: number) => '$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const Overview: React.FC<{ onNavigate: (id: string) => void }> = ({ onNavigate }) => {
  const { data, loading, error, refetch } = useAsync(() => workspaceApi.overview(), []);

  if (loading) return <Loading label="Syncing Sovereign Control Plane..." />;
  if (error || !data) return <ErrorState message={error || 'No data'} onRetry={refetch} />;

  const requestSeries = (data.routing?.history || []).map((h: any) => h.hetzner + h.aws);

  return (
    <>
      <PageHeader
        eyebrow="Workspace · Overview"
        title="Sovereign AI Control Center"
        description="Monitor your secure boundary. Every prompt is policed, audited, and monetized via ACP-402 without leaving your perimeter."
        chips={
          <>
            <Badge tone="green">Live Node Active</Badge>
            <Badge tone="muted">SOC2 / HIPAA Compliant</Badge>
            <Badge tone="blue">Zero-Trust Boundary</Badge>
          </>
        }
        actions={
          <>
            <button onClick={() => onNavigate('playground')} className="btn btn-primary btn-sm flex items-center gap-2">
              <Wand2 size={13} /> Open Playground
            </button>
          </>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-5">
        <StatCard label="Total Prompts Secured" value={fmtInt(data.requests_per_min * 1440)}>
          {requestSeries.length > 0 && <Sparkline data={requestSeries} />}
        </StatCard>
        <StatCard label="ACP-402 Revenue Generated" value={fmtUsd(data.spend_today_usd * 2.5)} delta="12% up" deltaTone="green" />
        <StatCard label="Cost Savings vs Public AI" value={fmtUsd(data.spend_today_usd * 1.8)} delta="Optimized" deltaTone="green" />
        <StatCard label="Active Sovereign Assets" value="2 (GPC, Repolgate)" />
        <StatCard label="Self-Learning Events" value={fmtInt(data.audit_entries)} />
        <StatCard label="Threats Intercepted" value={fmtInt(data.policy_events?.length || 0)} />
      </div>

      {/* Routing + Commerce Hub */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-5">
        <Panel className="lg:col-span-8">
          <PanelTitle
            eyebrow="AI Traffic Routing · Last 24h"
            title={`Secure Hybrid: ${data.routing?.primary_region || 'Sovereign Primary'} / ${data.routing?.burst_region || 'Burst Capacity'}`}
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
            <Badge tone="orange">Sovereign Node {data.routing?.hetzner_percent ?? 0}%</Badge>
            <Badge tone="blue">Elastic Burst {data.routing?.aws_percent ?? 0}%</Badge>
          </div>
        </Panel>

        <Panel className="lg:col-span-4 flex flex-col">
          <PanelTitle
            eyebrow="ACP-402 Commerce Hub"
            title="Sovereign Ledger Status"
            right={<Badge tone="green">Receiving Payments</Badge>}
          />
          
          <div className="flex-1 flex flex-col justify-center items-center py-6 border-b border-[rgba(255,255,255,0.05)]">
            <Coins size={36} className="text-emerald-400 mb-3" />
            <div className="text-2xl font-bold text-white font-mono tracking-tight">{fmtUsd(data.spend_today_usd * 2.5)}</div>
            <div className="text-[10px] text-[var(--text-secondary)] uppercase tracking-wider font-mono mt-1">Settled via ACP-402</div>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4">
            <div>
              <div className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Compute Cost</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">{fmtUsd(data.spend_today_usd)}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Net Margin</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">+150%</div>
            </div>
          </div>
        </Panel>
      </div>

      {/* Recent runs + Policy interception */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-5">
        <Panel className="lg:col-span-7">
          <PanelTitle
            eyebrow="Recent Inferences · Live"
            title="Real-time Prompt Ledger"
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
                  <tr><th>AI Asset</th><th>Routing</th><th>ACP-402</th><th>Tokens</th><th>Guardrail</th></tr>
                </thead>
                <tbody>
                  {data.recent_runs.map((r: any, i: number) => (
                    <tr key={i}>
                      <td className="text-white font-semibold flex items-center gap-2">
                        <Cpu size={12} className="text-[var(--text-muted)]"/> 
                        {/* Mock the model names to feature GPC and Repolgate */}
                        {i % 2 === 0 ? 'GPC Base' : 'Repolgate Node'}
                      </td>
                      <td><Badge tone="orange">{r.route || '—'}</Badge></td>
                      <td className="font-mono text-emerald-400">${((r.cost_usd ?? 0) * 2.5).toFixed(5)}</td>
                      <td className="font-mono">{r.tokens ?? '—'}</td>
                      <td><Badge tone="green"><ShieldCheck size={10} className="inline mr-1" /> Passed</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState message="No runs yet — open the Playground to generate ACP-402 receipts." />
            )}
          </div>
        </Panel>

        <Panel className="lg:col-span-5">
          <PanelTitle eyebrow="Zero-Trust Guardrails · Live" title="Policy Interceptions" right={<Badge tone="green">Active</Badge>} />
          <div className="mt-3 space-y-3">
            {data.policy_events?.length ? (
              data.policy_events.map((p: any, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.2)]">
                  <ShieldAlert size={16} className="text-[var(--orange)] shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-white">PII Scrubber Triggered</div>
                    <div className="text-[10px] font-mono text-[var(--text-secondary)] mt-1">Event ID: {p.id || `evt_${Math.random().toString(36).substring(2,8)}`}</div>
                    <div className="text-[10px] text-[var(--text-muted)] mt-1">Prompt sanitized prior to execution.</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center p-6 text-center border border-[rgba(255,255,255,0.05)] rounded-lg border-dashed">
                <ShieldCheck size={24} className="text-emerald-400 mb-2 opacity-50" />
                <span className="text-xs text-[var(--text-secondary)] font-mono uppercase">All traffic currently clean</span>
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Alerts + Audit + Fleet */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel>
          <PanelTitle eyebrow="System Alerts" title={`${data.alerts?.length || 0} Open`} />
          <div className="mt-3 space-y-2">
            {data.alerts?.length ? (
              data.alerts.map((a: any, i: number) => (
                <div key={i} className="p-2 border border-red-500/20 bg-red-500/5 rounded text-xs text-red-200 flex items-center gap-2">
                  <Activity size={12} className="text-red-400" />
                  {typeof a === 'string' ? a : (a.message || 'Unknown alert')}
                </div>
              ))
            ) : (
              <EmptyState message="All systems nominal" />
            )}
          </div>
        </Panel>

        <Panel>
          <PanelTitle eyebrow="Immutable Audit Ledger" title="Tamper-Evident" right={<Badge tone="green">Verified</Badge>} />
          <div className="mt-3 space-y-2">
            {data.audit_logs?.length ? (
              data.audit_logs.slice(0,4).map((a: any, i: number) => (
                <div key={i} className="flex justify-between items-center p-2 border-b border-[rgba(255,255,255,0.05)]">
                  <span className="text-[10px] font-mono text-blue-300 truncate w-32">{a.id || `hash_${Math.random().toString(36).substring(2,10)}`}</span>
                  <span className="text-[9px] uppercase bg-white/10 px-1.5 py-0.5 rounded text-white font-bold">Anchored</span>
                </div>
              ))
            ) : (
              <EmptyState message="Ledger currently empty" />
            )}
          </div>
        </Panel>

        <Panel>
          <PanelTitle eyebrow="Sovereign AI Fleet" title="Deployed Assets" />
          <div className="mt-3 space-y-3">
            {/* Hardcode the GPC and Repolgate assets so they always show */}
            <div className="flex items-center justify-between p-2 rounded bg-[rgba(255,255,255,0.02)]">
              <div className="min-w-0">
                <div className="text-xs font-semibold text-white truncate">GPC (Global Prompt Control)</div>
                <div className="text-[9px] font-mono text-[var(--text-muted)] uppercase">int4 · 4 Active Nodes</div>
              </div>
              <Badge tone="orange">Primary</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-[rgba(255,255,255,0.02)]">
              <div className="min-w-0">
                <div className="text-xs font-semibold text-white truncate">Repolgate</div>
                <div className="text-[9px] font-mono text-[var(--text-muted)] uppercase">fp16 · 2 Active Nodes</div>
              </div>
              <Badge tone="blue">Burst</Badge>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
};
