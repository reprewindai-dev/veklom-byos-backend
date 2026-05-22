import React, { useState } from 'react';
import { 
  Activity,
  GitFork,
  Terminal, 
  ShieldCheck, 
  Server
} from 'lucide-react';

export const CommandCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'uacp' | 'runtime'>('uacp');

  return (
    <div className="space-y-6 h-[calc(100vh-140px)] flex flex-col justify-between">
      
      {/* Title Header / Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4 gap-4 flex-shrink-0">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <Terminal size={18} className="text-[var(--orange)]" /> Command Center
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Operator surface for UACP constitutional coordination and Veklom runtime infrastructure.</p>
        </div>

        {/* Tab Selectors */}
        <div className="flex p-0.5 rounded-lg bg-[rgba(0,0,0,0.3)] border border-white/5 font-mono text-[11px]">
          <button
            onClick={() => setActiveTab('uacp')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all ${
              activeTab === 'uacp'
                ? 'bg-[var(--orange)] text-black'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            UACP
          </button>
          <button
            onClick={() => setActiveTab('runtime')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all flex items-center gap-1.5 ${
              activeTab === 'runtime'
                ? 'bg-emerald-600 text-white shadow-[0_0_10px_rgba(16,185,129,0.3)]'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            VEKLOM RUNTIME
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">

        {/* UACP Constitutional Coordination */}
        {activeTab === 'uacp' && (
          <div className="h-full overflow-y-auto space-y-6 pr-1 pb-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'constitutional lock', value: 'ENFORCED', sub: 'Founder veto active', tone: 'text-emerald-400' },
                { label: 'operator workers', value: '24', sub: 'committee mapped', tone: 'text-white' },
                { label: 'evidence gates', value: '5', sub: 'regulated review paths', tone: 'text-[var(--orange)]' },
                { label: 'coordination mode', value: 'UACP', sub: 'constitutional layer', tone: 'text-purple-300' },
              ].map((metric) => (
                <div key={metric.label} className="glow-card p-4">
                  <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">{metric.label}</span>
                  <span className={`mt-2 block font-mono text-xl font-bold ${metric.tone}`}>{metric.value}</span>
                  <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--text-muted)]">{metric.sub}</span>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="glow-card">
                <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
                  <ShieldCheck size={13} className="text-[var(--orange)]" /> UACP Coordination Layer
                </h3>
                <div className="space-y-3">
                  {[
                    ['Founder Council', 'Final approval, veto, and regulated escalation authority'],
                    ['Signal Council', 'Research-backed opportunity and operating pressure briefs'],
                    ['Execution Board', 'Approved work routing into governed runs and service delivery'],
                    ['Operator Committees', 'Marketplace, evidence, growth, assurance, and vendor workers'],
                  ].map(([name, detail]) => (
                    <div key={name} className="rounded border border-white/5 bg-white/[0.02] p-3">
                      <div className="font-mono text-[11px] font-bold uppercase text-white">{name}</div>
                      <p className="mt-1 text-[11px] leading-relaxed text-[var(--text-secondary)]">{detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glow-card">
                <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
                  <GitFork size={13} className="text-[var(--orange)]" /> Escalation Spine
                </h3>
                <div className="space-y-3 font-mono text-[10.5px] text-[var(--text-secondary)]">
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Oracle evidence</span>
                    <span className="text-emerald-400">required</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Ledger hash chain</span>
                    <span className="text-emerald-400">verified</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Regulated objectives</span>
                    <span className="text-[var(--orange)]">review gated</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Runtime authority</span>
                    <span className="text-white">Veklom only</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Veklom Runtime Infrastructure */}
        {activeTab === 'runtime' && (
          <div className="grid h-full grid-cols-1 gap-4 xl:grid-cols-[0.35fr_0.65fr]">
            <div className="space-y-4 overflow-y-auto pr-1">
              <div className="glow-card">
                <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
                  <Server size={13} className="text-emerald-400" /> Veklom Runtime
                </h3>
                <div className="space-y-3 font-mono text-[10.5px] text-[var(--text-secondary)]">
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Runtime role</span>
                    <span className="text-white">Sovereign infrastructure</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Billing gate</span>
                    <span className="text-emerald-400">wallet enforced</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span>Tenant boundary</span>
                    <span className="text-emerald-400">isolated</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Audit state</span>
                    <span className="text-[var(--orange)]">hash chained</span>
                  </div>
                </div>
              </div>

              <div className="glow-card">
                <h3 className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
                  <Activity size={13} className="text-[var(--orange)]" /> Runtime owns
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {['auth', 'billing', 'execution', 'provider routing', 'audit evidence', 'buyer deploy'].map((item) => (
                    <span key={item} className="rounded border border-white/10 bg-black/20 px-2 py-1 font-mono text-[9px] uppercase text-white/50">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="h-full overflow-hidden rounded-xl border border-emerald-500/20 bg-black shadow-[0_0_20px_rgba(16,185,129,0.1)]">
              <div className="h-6 bg-neutral-900 border-b border-emerald-500/10 px-3 flex items-center justify-between font-mono text-[9px] text-emerald-400 uppercase tracking-wider">
                <span className="flex items-center gap-1.5"><Terminal size={10} /> VEKLOM RUNTIME TERMINAL</span>
                <span>HOST: VEKLOM-RUNTIME-INFRASTRUCTURE</span>
              </div>
              <iframe
                src="/command-center/veklom-terminal/"
                className="h-[calc(100%-24px)] w-full border-none bg-black"
                title="Veklom Runtime"
              />
            </div>
          </div>
        )}

      </div>

    </div>
  );
};
