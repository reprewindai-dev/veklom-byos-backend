import React, { useState } from 'react';
import { 
  Terminal, 
  ShieldCheck, 
  Activity, 
  Coins, 
  UserCheck, 
  Lock, 
  Layers 
} from 'lucide-react';

export const CommandCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'stats' | 'quantum' | 'veklom'>('stats');

  return (
    <div className="space-y-6 h-[calc(100vh-140px)] flex flex-col justify-between">
      
      {/* Title Header / Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4 gap-4 flex-shrink-0">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <Terminal size={18} className="text-[var(--orange)]" /> Sovereign Twin Terminals & Command
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Admin cockpit monitoring MRR funnels, system regulations, and twin terminal console access.</p>
        </div>

        {/* Tab Selectors */}
        <div className="flex p-0.5 rounded-lg bg-[rgba(0,0,0,0.3)] border border-white/5 font-mono text-[11px]">
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all ${
              activeTab === 'stats'
                ? 'bg-[var(--orange)] text-black'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            ADMIN STATUS
          </button>
          <button
            onClick={() => setActiveTab('quantum')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all flex items-center gap-1.5 ${
              activeTab === 'quantum'
                ? 'bg-purple-600 text-white shadow-[0_0_10px_rgba(147,51,234,0.3)]'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            QUANTUM TERMINAL
          </button>
          <button
            onClick={() => setActiveTab('veklom')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all flex items-center gap-1.5 ${
              activeTab === 'veklom'
                ? 'bg-emerald-600 text-white shadow-[0_0_10px_rgba(16,185,129,0.3)]'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            VEKLOM TERMINAL
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        
        {/* Tab 1: Administrative Console Stats */}
        {activeTab === 'stats' && (
          <div className="h-full overflow-y-auto space-y-6 pr-1 pb-4">
            
            {/* Top widgets row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* MRR Conversion */}
              <div className="glow-card p-4 flex justify-between items-center">
                <div>
                  <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">aggregate revenue mrr</span>
                  <span className="text-xl font-bold font-mono text-white block mt-1.5">$48,250.00</span>
                  <span className="text-[9px] font-mono text-emerald-400 block mt-1">+14.2% today</span>
                </div>
                <div className="w-10 h-10 rounded bg-[rgba(255,184,0,0.04)] border border-[rgba(255,184,0,0.15)] flex items-center justify-center">
                  <Coins className="text-[var(--orange)]" size={16} />
                </div>
              </div>

              {/* Active users */}
              <div className="glow-card p-4 flex justify-between items-center">
                <div>
                  <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">ACTIVE SYSTEM OPERATORS</span>
                  <span className="text-xl font-bold font-mono text-white block mt-1.5">342 ONLINE</span>
                  <span className="text-[9px] font-mono text-emerald-400 block mt-1">14 active sessions</span>
                </div>
                <div className="w-10 h-10 rounded bg-blue-500/5 border border-blue-500/15 flex items-center justify-center">
                  <UserCheck className="text-blue-400" size={16} />
                </div>
              </div>

              {/* Security regulations score */}
              <div className="glow-card p-4 flex justify-between items-center">
                <div>
                  <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">COMPLIANCE COMPILATION SCORE</span>
                  <span className="text-xl font-bold font-mono text-emerald-400 block mt-1.5">94% RATING</span>
                  <span className="text-[9px] font-mono text-[var(--text-muted)] block mt-1">HIPAA / GDPR verified</span>
                </div>
                <div className="w-10 h-10 rounded bg-emerald-500/5 border border-emerald-500/15 flex items-center justify-center">
                  <ShieldCheck className="text-emerald-400" size={16} />
                </div>
              </div>

              {/* Locker status */}
              <div className="glow-card p-4 flex justify-between items-center">
                <div>
                  <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">PERIMETER CRYPTO VAULT</span>
                  <span className="text-xl font-bold font-mono text-white block mt-1.5">LOCKED</span>
                  <span className="text-[9px] font-mono text-emerald-400 block mt-1">AES-256 integrity intact</span>
                </div>
                <div className="w-10 h-10 rounded bg-purple-500/5 border border-purple-500/15 flex items-center justify-center">
                  <Lock className="text-purple-400" size={16} />
                </div>
              </div>
            </div>

            {/* Split row: System Funnels & Bare-metal load */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Funnel Conversions */}
              <div className="glow-card">
                <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono mb-4 flex items-center gap-2">
                  <Activity size={13} className="text-[var(--orange)]" /> RUNTIME CONVERSION FUNNEL
                </h3>
                <div className="space-y-4">
                  {[
                    { label: 'Intake Prompts Gated', count: '1,254,302', pct: 100 },
                    { label: 'Policy Interceptions Passed', count: '1,250,918', pct: 99.7 },
                    { label: 'Sovereign Redactions Completed', count: '342,109', pct: 27.2 },
                    { label: 'Ledger Audit Sign Verifications', count: '342,109', pct: 27.2 }
                  ].map((step, idx) => (
                    <div key={idx} className="space-y-1 font-mono text-xs">
                      <div className="flex justify-between">
                        <span className="text-[var(--text-secondary)]">{step.label}</span>
                        <span className="text-white font-bold">{step.count} ({step.pct}%)</span>
                      </div>
                      <div className="w-full bg-[rgba(255,255,255,0.04)] rounded-full h-2">
                        <div className="bg-[var(--orange)] h-2 rounded-full" style={{ width: `${step.pct}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Vault & Sovereignty Audit */}
              <div className="glow-card flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono mb-4 flex items-center gap-2">
                    <Layers size={13} className="text-[var(--orange)]" /> PERIMETER SOVEREIGN STATUS
                  </h3>
                  <div className="space-y-3 font-mono text-xs">
                    <div className="p-3 bg-[rgba(255,184,0,0.02)] border border-[rgba(255,184,0,0.08)] rounded space-y-2">
                      <div className="text-white font-bold">SOVEREIGN MODE ACTIVE</div>
                      <div className="text-[10.5px] text-[var(--text-secondary)] leading-relaxed">
                        The Veklom control plane is running fully isolated inside your Bare-Metal region (Hetzner FSN1). All public model connections are gated by your local perimeter security policies. PII leaks are physically impossible.
                      </div>
                    </div>

                    <div className="p-3 bg-[rgba(255,255,255,0.01)] border border-white/5 rounded space-y-1.5 text-[10.5px]">
                      <div className="flex justify-between">
                        <span>Bare-metal region:</span>
                        <span className="text-white">Hetzner Private Germany</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Vault Locker State:</span>
                        <span className="text-emerald-400">CIPHER KEY SECURED</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Auditor connection:</span>
                        <span className="text-emerald-400">100% LEDGER VERIFIED</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-[9px] font-mono text-[var(--text-muted)] text-center mt-4">
                  AUDITOR VERIFIED ENFORCER RULESETS ENGAGED
                </div>
              </div>

            </div>

            {/* Static embed preview indicator */}
            <div className="glow-card p-6 text-center space-y-3 max-w-xl mx-auto border border-dashed border-[rgba(255,184,0,0.2)] bg-[rgba(255,184,0,0.01)]">
              <Terminal className="mx-auto text-[var(--orange)] animate-pulse" size={24} />
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Twin Terminal Sandboxes Available</h4>
                <p className="text-[11px] text-[var(--text-secondary)] mt-1">
                  Access bare-metal command structures via retro terminals. Click the header buttons above to establish secure sub-application connections.
                </p>
              </div>
            </div>

          </div>
        )}

        {/* Tab 2: Quantum Terminal IFrame */}
        {activeTab === 'quantum' && (
          <div className="w-full h-full rounded-xl overflow-hidden border border-purple-500/20 bg-black relative flex flex-col justify-between shadow-[0_0_20px_rgba(147,51,234,0.1)]">
            <div className="h-6 bg-neutral-900 border-b border-purple-500/10 px-3 flex items-center justify-between font-mono text-[9px] text-purple-400 uppercase tracking-wider">
              <span>ESTABLISHING SECURE SSH TUNNEL...</span>
              <span>HOST: LOCAL-QUANTUM-TERMINAL</span>
            </div>
            <iframe
              src="/command-center/quantum-terminal/"
              className="flex-1 w-full border-none bg-black"
              title="Quantum Terminal"
            />
          </div>
        )}

        {/* Tab 3: Veklom Terminal IFrame */}
        {activeTab === 'veklom' && (
          <div className="w-full h-full rounded-xl overflow-hidden border border-emerald-500/20 bg-black relative flex flex-col justify-between shadow-[0_0_20px_rgba(16,185,129,0.1)]">
            <div className="h-6 bg-neutral-900 border-b border-emerald-500/10 px-3 flex items-center justify-between font-mono text-[9px] text-emerald-400 uppercase tracking-wider">
              <span>ESTABLISHING SECURE SSH TUNNEL...</span>
              <span>HOST: LOCAL-VEKLOM-TERMINAL</span>
            </div>
            <iframe
              src="/command-center/veklom-terminal/"
              className="flex-1 w-full border-none bg-black"
              title="Veklom Terminal"
            />
          </div>
        )}

      </div>

    </div>
  );
};