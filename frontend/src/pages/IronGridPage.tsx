import React, { useEffect, useState } from 'react';
import { Activity, Cpu, GitFork, ShieldCheck, ShoppingBag } from 'lucide-react';
import { api } from '../api/client';

type RouteClass = {
  description: string;
  providers: string[];
  required_controls: string[];
};

type Topology = {
  policy_version: string;
  substrate: string;
  route_classes: Record<string, RouteClass>;
  decision_inputs: string[];
};

const fallbackTopology: Topology = {
  policy_version: '2026-05-22.det-ai-infra.v1',
  substrate: 'py03-irongrid',
  route_classes: {
    sovereign_private: {
      description: 'Private runtime path for regulated or data-sovereign workloads.',
      providers: ['vllm', 'ollama', 'openai-compatible-private'],
      required_controls: ['workspace_isolation', 'audit_hash', 'evidence_capture'],
    },
    cost_optimized: {
      description: 'Low-cost execution path for non-regulated workloads with flexible latency.',
      providers: ['groq', 'huggingface', 'gemini', 'openai'],
      required_controls: ['wallet_debit', 'usage_metering', 'audit_hash'],
    },
    latency_critical: {
      description: 'Fast path for interactive workloads with strict latency limits.',
      providers: ['groq', 'openai', 'private-edge'],
      required_controls: ['rate_limit', 'wallet_debit', 'audit_hash'],
    },
    verification_heavy: {
      description: 'Multi-step path for high-risk output requiring policy checks and replay.',
      providers: ['private-primary', 'openai-fallback', 'anthropic-fallback'],
      required_controls: ['policy_gate', 'evidence_capture', 'human_review_if_high_risk'],
    },
  },
  decision_inputs: [
    'workspace_entitlement',
    'estimated_tokens',
    'compliance_tags',
    'sovereignty_region',
    'max_latency_ms',
    'budget_remaining_usd',
    'route_pressure',
    'provider_health',
  ],
};

export const IronGridPage: React.FC = () => {
  const [topology, setTopology] = useState<Topology>(fallbackTopology);
  const [status, setStatus] = useState<'synced' | 'fallback'>('fallback');

  useEffect(() => {
    let mounted = true;
    api('/routing/topology')
      .then((data) => {
        if (!mounted) return;
        setTopology(data);
        setStatus('synced');
      })
      .catch(() => {
        if (!mounted) return;
        setTopology(fallbackTopology);
        setStatus('fallback');
      });

    return () => {
      mounted = false;
    };
  }, []);

  const routeClasses = Object.entries(topology.route_classes);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-white/5 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
            <span>Marketplace</span>
            <span>/</span>
            <span className="text-[var(--orange)]">PY03 IronGrid</span>
          </div>
          <h2 className="flex items-center gap-3 text-lg font-bold tracking-tight text-white">
            <Cpu size={18} className="text-[var(--orange)]" /> PY03 IronGrid
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Deterministic routing mesh for GPC-compiled workloads, provider pressure, and data movement economics.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase">
          <span className={`rounded border px-2 py-1 ${status === 'synced' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-amber-500/30 bg-amber-500/10 text-amber-400'}`}>
            {status === 'synced' ? 'API synced' : 'local contract'}
          </span>
          <span className="rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-white/50">
            {topology.policy_version}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="glow-card p-4">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Substrate</span>
          <span className="mt-2 block font-mono text-xl font-bold text-white">{topology.substrate}</span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-emerald-400">GPC child runtime</span>
        </div>
        <div className="glow-card p-4">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Route Classes</span>
          <span className="mt-2 block font-mono text-xl font-bold text-white">{routeClasses.length}</span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--text-muted)]">Replayable policy paths</span>
        </div>
        <div className="glow-card p-4">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Marketplace SKU</span>
          <span className="mt-2 block font-mono text-xl font-bold text-white">PY03-IRONGRID</span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--orange)]">Listed runtime add-on</span>
        </div>
        <div className="glow-card p-4">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Billing Gate</span>
          <span className="mt-2 block font-mono text-xl font-bold text-emerald-400">Sovereign+</span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--text-muted)]">Entitlement required</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="glow-card">
          <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
            <GitFork size={13} className="text-[var(--orange)]" /> Routing classes
          </h3>
          <div className="space-y-3">
            {routeClasses.map(([key, route]) => (
              <div key={key} className="rounded border border-white/5 bg-white/[0.02] p-3">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="font-mono text-[11px] font-bold uppercase text-white">{key.replace(/_/g, ' ')}</div>
                    <p className="mt-1 text-[11px] leading-relaxed text-[var(--text-secondary)]">{route.description}</p>
                  </div>
                  <div className="font-mono text-[9px] uppercase text-[var(--text-muted)] md:text-right">
                    {route.providers.join(' / ')}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {route.required_controls.map((control) => (
                    <span key={control} className="rounded border border-white/10 bg-black/20 px-2 py-1 font-mono text-[9px] uppercase text-white/50">
                      {control.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="glow-card">
            <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
              <Activity size={13} className="text-[var(--orange)]" /> Decision inputs
            </h3>
            <div className="grid grid-cols-1 gap-2">
              {topology.decision_inputs.map((input) => (
                <div key={input} className="flex items-center justify-between border-b border-white/5 py-2 font-mono text-[10px]">
                  <span className="uppercase text-[var(--text-secondary)]">{input.replace(/_/g, ' ')}</span>
                  <span className="text-emerald-400">tracked</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glow-card">
            <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
              <ShoppingBag size={13} className="text-[var(--orange)]" /> Marketplace packaging
            </h3>
            <div className="space-y-3 font-mono text-[10.5px] text-[var(--text-secondary)]">
              <div className="flex justify-between border-b border-white/5 pb-2">
                <span>Package</span>
                <span className="text-white">PY03 IronGrid Route Optimizer</span>
              </div>
              <div className="flex justify-between border-b border-white/5 pb-2">
                <span>Attach point</span>
                <span className="text-white">GPC add-on</span>
              </div>
              <div className="flex justify-between border-b border-white/5 pb-2">
                <span>Buyer outcome</span>
                <span className="text-white">Lower routing waste</span>
              </div>
              <div className="flex justify-between">
                <span>Control</span>
                <span className="text-emerald-400">Entitlement + audit gated</span>
              </div>
            </div>
          </div>

          <div className="glow-card border-emerald-500/10 bg-emerald-500/[0.02]">
            <h3 className="mb-3 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
              <ShieldCheck size={13} className="text-emerald-400" /> Placement rule
            </h3>
            <p className="text-[11px] leading-relaxed text-[var(--text-secondary)]">
              IronGrid sits under GPC because it routes compiled execution graphs. Command Center watches UACP
              and Veklom Runtime; GPC owns the path where IronGrid is operated and sold.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
