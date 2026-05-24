import React, { useState, useEffect } from 'react';
import { api, setToken } from '../api/client';
import { Overview } from '../components/Overview';
import { Playground } from '../components/Playground';
import { Pipelines } from '../components/Pipelines';
import { Routing } from '../components/Routing';
import { Billing } from '../components/Billing';
import { CommandCenter } from '../components/CommandCenter';
import { 
  Activity, 
  Terminal, 
  Cpu, 
  GitFork, 
  Key, 
  ShieldCheck, 
  ActivitySquare, 
  CreditCard, 
  Settings as SettingsIcon, 
  Sliders, 
  LogOut, 
  Server, 
  Layers, 
  Plus, 
  Trash,
  User
} from 'lucide-react';

interface WorkspaceProps {
  onLogout: () => void;
  user: any;
}

export const Workspace: React.FC<WorkspaceProps> = ({ onLogout, user }) => {
  const [currentView, setCurrentView] = useState<string>('overview');
  const [profile] = useState<any>(user || { email: 'operator@veklom.perimeter', role: 'owner' });

  // Secondary dynamic states (Models, Deployments, Vault, Compliance, Monitoring)
  const [modelsList, setModelsList] = useState<any[]>([]);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [complianceReport, setComplianceReport] = useState<any>(null);
  const [observability, setObservability] = useState<any>(null);
  const [subError, setSubError] = useState('');

  // Handle hash routing on mount/change
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace(/^#\/?/, '');
      if (hash) {
        setCurrentView(hash);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange(); // Run on mount

    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view: string) => {
    window.location.hash = `#/${view}`;
    setCurrentView(view);
  };

  // Sync background details when specific pages mount
  useEffect(() => {
    const syncSubData = async () => {
      setSubError('');
      try {
        if (currentView === 'models') {
          const res = await api('/workspace/models');
          setModelsList(res);
        } else if (currentView === 'deployments') {
          const res = await api('/deployments');
          setDeployments(res);
        } else if (currentView === 'vault') {
          const res = await api('/workspace/api-keys');
          setApiKeys(res);
        } else if (currentView === 'compliance') {
          const res = await api('/compliance/report');
          setComplianceReport(res);
        } else if (currentView === 'monitoring') {
          const res = await api('/workspace/observability');
          setObservability(res);
        }
      } catch (err: any) {
        setSubError(err.message || 'Gateway sync aborted.');
      }
    };

    syncSubData();
  }, [currentView]);

  // Handle API Key Creation
  const handleCreateAPIKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setSubError('');
    setGeneratedKey('');
    try {
      const res = await api('/workspace/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: newKeyName })
      });
      setGeneratedKey(res.key);
      setNewKeyName('');
      
      // refresh
      const updated = await api('/workspace/api-keys');
      setApiKeys(updated);
    } catch (err: any) {
      setSubError(err.message || 'Key compilation failed.');
    }
  };

  // Handle Toggling Model Status
  const handleToggleModel = async (id: string, currentlyEnabled: boolean) => {
    try {
      await api(`/workspace/models/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_enabled: !currentlyEnabled })
      });
      setModelsList(prev => prev.map(m => m.id === id ? { ...m, is_enabled: !currentlyEnabled } : m));
    } catch (err: any) {
      setSubError(err.message || 'Failed to update model fleet configurations.');
    }
  };

  // Handle Deleting API Key
  const handleDeleteKey = async (id: string) => {
    try {
      await api(`/workspace/api-keys/${id}`, { method: 'DELETE' });
      setApiKeys(prev => prev.filter(k => k.id !== id));
    } catch (err: any) {
      setSubError(err.message || 'Purging key failed.');
    }
  };

  const handleLogoutAction = () => {
    setToken('');
    onLogout();
  };

  const renderActiveView = () => {
    switch (currentView) {
      case 'overview':
        return <Overview />;
      case 'playground':
        return <Playground />;
      case 'gpc':
        return (
          <div className="w-full h-full relative rounded-xl border border-white/5 bg-black overflow-hidden flex flex-col justify-between shadow-[0_0_20px_rgba(255,184,0,0.05)]">
            <div className="h-6 bg-neutral-900 border-b border-white/5 px-3 flex items-center justify-between font-mono text-[9px] text-[var(--orange)] uppercase tracking-wider">
              <span>ESTABLISHING GPC BARE-METAL INSTANCE...</span>
              <span>HOST: LOCAL-GPC-COMPILER</span>
            </div>
            <iframe src="/gpc-engine" className="flex-1 w-full border-none bg-[#050505]" title="Governed Plan Compiler" />
          </div>
        );
      case 'pipelines':
        return <Pipelines />;
      case 'routing':
        return <Routing />;
      case 'billing':
        return <Billing />;
      case 'command-center':
        return <CommandCenter />;
      case 'irongrid':
        return (
          <div className="w-full h-full relative rounded-xl border border-white/5 bg-black overflow-hidden shadow-[0_0_20px_rgba(255,184,0,0.05)]" style={{minHeight: 'calc(100vh - 200px)'}}>
            <iframe src="/irongrid/" className="w-full h-full border-none bg-[#0a0a0a]" title="PYO3 IronGrid Simulator" style={{minHeight: 'calc(100vh - 200px)'}} />
          </div>
        );
      case 'terminal':
        return (
          <div className="w-full h-full relative rounded-xl border border-white/5 bg-black overflow-hidden shadow-[0_0_20px_rgba(255,184,0,0.05)]" style={{minHeight: 'calc(100vh - 200px)'}}>
            <iframe src="/uacp-quantum-terminal.html" className="w-full h-full border-none bg-[#0a0a0a]" title="UACP Quantum Terminal" style={{minHeight: 'calc(100vh - 200px)'}} />
          </div>
        );
      
      // Secondary inline compiled views
      case 'models':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <Cpu size={18} className="text-[var(--orange)]" /> Bare-Metal Model Fleet
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">Toggle active bare-metal LLM engines in your local bare-metal clusters.</p>
            </div>
            {subError && <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">{subError}</div>}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {modelsList.map((m) => (
                <div key={m.id} className="glow-card p-4 flex justify-between items-center">
                  <div>
                    <span className="text-xs font-bold text-white block">{m.display_name}</span>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block mt-0.5">{m.provider.toUpperCase()} ┬╖ {m.model_name}</span>
                    <span className="text-[9.5px] text-[var(--text-secondary)] font-mono block mt-1">RATE: ${m.cost_per_1k_input.toFixed(5)} / 1K tokens</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`badge ${m.is_enabled ? 'badge-green' : 'badge-orange'}`}>
                      {m.is_enabled ? 'online' : 'offline'}
                    </span>
                    <input
                      type="checkbox"
                      checked={m.is_enabled}
                      onChange={() => handleToggleModel(m.id, m.is_enabled)}
                      className="accent-[var(--orange)] h-4 w-4 bg-neutral-900 border-white/5 cursor-pointer rounded"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'deployments':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <Server size={18} className="text-[var(--orange)]" /> bare-metal Deployments
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">Monitor active running docker vLLM bare-metal pods.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Deployment ID</th>
                    <th>Instance Label</th>
                    <th>Type</th>
                    <th>Endpoint Tunnel</th>
                    <th className="text-right">Platform Status</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.map((d) => (
                    <tr key={d.id}>
                      <td className="font-mono text-white font-bold text-[10px]">{d.id.toUpperCase()}</td>
                      <td className="font-semibold text-white">{d.name}</td>
                      <td>
                        <span className="badge badge-orange text-[9px]">{d.type}</span>
                      </td>
                      <td className="font-mono">{d.endpoint}</td>
                      <td className="text-right font-mono text-emerald-400 font-bold uppercase">{d.status} Γ£ô</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );

      case 'vault':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <Key size={18} className="text-[var(--orange)]" /> Cryptographic Key Vault
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">Manage sovereign API keys for external application gateways.</p>
            </div>

            {subError && <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">{subError}</div>}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Creator */}
              <div className="glow-card lg:col-span-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-3">GENERATE SECURITY KEY</h3>
                <form onSubmit={handleCreateAPIKey} className="space-y-4">
                  <input
                    type="text"
                    placeholder="Key Identifier (e.g. acme-backend)"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="form-input text-xs font-mono"
                    required
                  />
                  <button type="submit" className="btn btn-primary w-full py-2.5 text-xs font-bold font-mono tracking-wider flex items-center justify-center gap-1.5">
                    <Plus size={13} /> GENERATE KEY
                  </button>
                </form>

                {generatedKey && (
                  <div className="mt-4 p-3 bg-emerald-500/5 border border-emerald-500/20 rounded font-mono text-[10px] space-y-2 text-white">
                    <div className="text-[var(--orange)] font-bold uppercase">COPY PRIVATE KEY ONCE:</div>
                    <div className="break-all p-2 rounded bg-black select-all border border-emerald-500/20 text-emerald-400 font-bold">{generatedKey}</div>
                    <p className="text-[9px] text-[var(--text-muted)] leading-relaxed uppercase">This token will be salted and salted hashes stored. It cannot be recovered later.</p>
                  </div>
                )}
              </div>

              {/* List */}
              <div className="glow-card lg:col-span-8">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4">ACTIVE SOVEREIGN KEYS</h3>
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Key Label</th>
                        <th>Token Prefix</th>
                        <th>Audit Status</th>
                        <th className="text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {apiKeys.map((k) => (
                        <tr key={k.id}>
                          <td className="font-semibold text-white">{k.name}</td>
                          <td className="font-mono text-white">{k.key_prefix}ΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇó</td>
                          <td>
                            <span className={`badge ${k.is_active ? 'badge-green' : 'badge-orange'}`}>
                              {k.is_active ? 'active' : 'revoked'}
                            </span>
                          </td>
                          <td className="text-right">
                            <button
                              onClick={() => handleDeleteKey(k.id)}
                              className="text-red-400 hover:text-red-300 p-1 transition-colors"
                              title="Revoke and delete key"
                            >
                              <Trash size={12} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          </div>
        );

      case 'compliance':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <ShieldCheck size={18} className="text-[var(--orange)]" /> Regulatory Compliance report
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5"> cryptographic verification audits and regulatory logs status.</p>
            </div>

            {complianceReport && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* overall */}
                <div className="glow-card lg:col-span-4 flex flex-col justify-between py-6 items-center text-center">
                  <div>
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">COMPLIANCE COMPILER SCORE</span>
                    <h3 className="text-5xl font-extrabold font-mono text-emerald-400 mt-4">{complianceReport.overall_score}%</h3>
                    <span className="badge badge-green mt-4 block">COMPLIANT PROFILE</span>
                  </div>
                  <p className="text-[9px] font-mono text-[var(--text-muted)] mt-6 uppercase leading-relaxed">
                    Sovereign Auditor verified. All regulatory hash chains signed and verified intact.
                  </p>
                </div>

                {/* regulations details */}
                <div className="glow-card lg:col-span-8">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4">COMPLIANCE RULES CHECKLISTS</h3>
                  <div className="space-y-4">
                    {complianceReport.regulations?.map((r: any, idx: number) => (
                      <div key={idx} className="p-3 bg-[rgba(255,255,255,0.01)] border border-white/5 rounded flex justify-between items-center font-mono">
                        <div>
                          <span className="text-xs font-bold text-white block">{r.name} REGULATION</span>
                          <span className="text-[9.5px] text-[var(--text-secondary)] block mt-0.5">Audit checklist threshold achieved</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-emerald-400 font-bold">{r.score}% achieved</span>
                          <span className="badge badge-green uppercase">{r.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case 'monitoring':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <ActivitySquare size={18} className="text-[var(--orange)]" /> Observability platform pulse
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5"> bare-metal latency health, error distributions, and system check gates.</p>
            </div>

            {observability && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glow-card p-4">
                  <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">bare-metal Region</span>
                  <span className="text-base font-bold text-white block mt-1.5 uppercase">{observability.region}</span>
                  <span className="text-[9px] font-mono text-emerald-400 block mt-0.5">operational bare-metal pod</span>
                </div>
                <div className="glow-card p-4">
                  <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">latency checker</span>
                  <span className="text-base font-bold text-white block mt-1.5">{observability.latency_ms} ms</span>
                  <span className="text-[9px] font-mono text-[var(--text-muted)] block mt-0.5">p50 system check</span>
                </div>
                <div className="glow-card p-4">
                  <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">error rate today</span>
                  <span className="text-base font-bold text-white block mt-1.5">{(observability.error_rate * 100).toFixed(3)}%</span>
                  <span className="text-[9px] font-mono text-emerald-400 block mt-0.5">100% dispatcher SLA intact</span>
                </div>
              </div>
            )}
          </div>
        );

      case 'settings':
        return (
          <div className="space-y-6">
            <div className="border-b border-white/5 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <SettingsIcon size={18} className="text-[var(--orange)]" /> Perimeter Control Settings
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">Configure system thresholds, firewall parameters, and regional compliance standards.</p>
            </div>
            
            <div className="glow-card max-w-xl space-y-6">
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider border-b border-white/5 pb-2">Perimeter Operator details</h3>
                <div className="space-y-1 font-mono text-xs text-[var(--text-secondary)]">
                  <div>OPERATOR IDENTITY: <span className="text-white font-bold">{profile.email}</span></div>
                  <div>SECURITY ROLE: <span className="text-[var(--orange)] font-bold uppercase">{profile.role}</span></div>
                  <div>bare-metal KEY: <span className="text-white">Active session decrypted</span></div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider border-b border-white/5 pb-2">System parameters override</h3>
                <div className="flex justify-between items-center py-2 text-xs font-mono">
                  <div>
                    <span className="text-white block font-bold">SOVEREIGN MODE ONLY</span>
                    <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block">Disable all outgoing connections to unapproved public hosts</span>
                  </div>
                  <input type="checkbox" defaultChecked className="accent-[var(--orange)] h-4 w-4 rounded" />
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <button onClick={handleLogoutAction} className="btn btn-secondary w-full py-2.5 text-xs font-bold font-mono tracking-widest flex items-center justify-center gap-1.5 text-red-400 border-red-500/10 hover:border-red-500/30 hover:bg-red-500/5">
                  <LogOut size={13} /> TERMINATE SECURE PERIMETER SESSION
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return <Overview />;
    }
  };

  return (
    <div className="grid-bg min-h-screen flex flex-col justify-between">
      
      {/* Dynamic Header console bar */}
      <header className="h-14 bg-[rgba(10,10,12,0.9)] border-b border-[rgba(255,255,255,0.05)] backdrop-blur-md px-6 flex items-center justify-between relative z-20 flex-shrink-0">
        <div className="flex items-center gap-3">
          <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-[0_0_4px_rgba(255,184,0,0.4)] cursor-pointer" onClick={() => navigateTo('overview')}>
            <path d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15" stroke="#ffb800" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="50" cy="48" r="8" fill="#ffffff" />
          </svg>
          <span className="text-sm font-black tracking-[0.1em] text-white">VEKLOM</span>
          <span className="h-4 w-0.5 bg-neutral-800"></span>
          
          {/* Project selector */}
          <div className="flex items-center gap-1.5 font-mono text-[10px] text-white/80 bg-neutral-900 border border-white/5 rounded px-2 py-0.5 cursor-pointer">
            <span className="pulse-dot"></span> ACME-PROD
          </div>
        </div>

        {/* User profile right controls */}
        <div className="flex items-center gap-4">
          <div className="flex flex-col text-right font-mono text-[9px] text-[var(--text-secondary)]">
            <span className="text-white font-semibold leading-tight">{profile.email.split('@')[0]}</span>
            <span>SECURE PERIMETER CLIENT</span>
          </div>
          <div className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center bg-[rgba(255,255,255,0.02)] text-[var(--orange)] font-bold text-xs">
            <User size={13} />
          </div>
        </div>
      </header>

      {/* Main sidebar & pages workspace */}
      <div className="flex-1 flex overflow-hidden relative z-10">
        
        {/* Command Sidebar */}
        <aside className="w-64 bg-[rgba(10,10,12,0.85)] border-r border-[rgba(255,255,255,0.05)] flex flex-col justify-between p-4 backdrop-blur-md overflow-y-auto shrink-0 select-none">
          
          <div className="space-y-6">
            
            {/* Sec: Workspace */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Workspace Dashboard</span>
              <nav className="space-y-1">
                <button
                  onClick={() => navigateTo('overview')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'overview'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Activity size={13} /> Overview
                </button>
                <button
                  onClick={() => navigateTo('playground')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'playground'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Terminal size={13} /> Playground
                </button>
                <button
                  onClick={() => navigateTo('gpc')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'gpc'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Sliders size={13} /> GPC Compiler
                </button>
                <button
                  onClick={() => navigateTo('command-center')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'command-center'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Layers size={13} /> Twin Terminals
                </button>
              </nav>
            </div>

            {/* Sec: Infrastructure */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Compute Fleet</span>
              <nav className="space-y-1">
                <button
                  onClick={() => navigateTo('models')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'models'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Cpu size={13} /> Models
                </button>
                <button
                  onClick={() => navigateTo('pipelines')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'pipelines'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <GitFork size={13} /> Pipelines
                </button>
                <button
                  onClick={() => navigateTo('deployments')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'deployments'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Server size={13} /> Deployments
                </button>
                <button
                  onClick={() => navigateTo('routing')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'routing'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Sliders size={13} /> Sovereign Routing
                </button>
                <button
                  onClick={() => navigateTo('irongrid')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'irongrid'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Layers size={13} /> PYO3 IronGrid
                </button>
                <button
                  onClick={() => navigateTo('terminal')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'terminal'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Terminal size={13} /> Quantum Terminal
                </button>
              </nav>
            </div>

            {/* Sec: Governance */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Governance Guard</span>
              <nav className="space-y-1">
                <button
                  onClick={() => navigateTo('vault')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'vault'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <Key size={13} /> Crypto Vault
                </button>
                <button
                  onClick={() => navigateTo('compliance')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'compliance'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <ShieldCheck size={13} /> Compliance Audits
                </button>
              </nav>
            </div>

            {/* Sec: Operations */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Expense & Monitors</span>
              <nav className="space-y-1">
                <button
                  onClick={() => navigateTo('monitoring')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'monitoring'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <ActivitySquare size={13} /> Observability
                </button>
                <button
                  onClick={() => navigateTo('billing')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'billing'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <CreditCard size={13} /> Ledger Wallet
                </button>
                <button
                  onClick={() => navigateTo('settings')}
                  className={`w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
                    currentView === 'settings'
                      ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white'
                      : 'text-[var(--text-secondary)] hover:text-white'
                  }`}
                >
                  <SettingsIcon size={13} /> Perimeter Settings
                </button>
              </nav>
            </div>

          </div>

          {/* Secure Logout Action */}
          <div className="pt-4 border-t border-[rgba(255,255,255,0.05)] mt-4">
            <button
              onClick={handleLogoutAction}
              className="w-full py-2.5 text-xs font-bold font-mono tracking-wider border border-[rgba(255,255,255,0.04)] bg-neutral-900 text-red-400/90 rounded flex items-center justify-center gap-1.5 hover:bg-red-500/5 hover:border-red-500/25 transition-all"
            >
              <LogOut size={13} /> TERMINATE CLIENT
            </button>
          </div>
        </aside>

        {/* Active Page Viewport Content */}
        <main className="flex-1 p-6 overflow-y-auto relative bg-[rgba(10,10,12,0.4)] backdrop-blur-sm">
          {renderActiveView()}
        </main>

      </div>

      {/* Bottom Status Spine Panel bar */}
      <footer className="h-6 bg-[rgba(10,10,12,0.95)] border-t border-[rgba(255,255,255,0.05)] px-6 flex items-center justify-between font-mono text-[9px] text-[var(--text-muted)] select-none z-20 flex-shrink-0">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> REGION DEPLOYMENT: HETZNER-DE</span>
          <span>SLA INTEGRITY: 100%</span>
        </div>
        <div className="flex items-center gap-4 text-white">
          <span className="text-[var(--orange)]">SOVEREIGN STATE COCKPIT ACTIVE</span>
          <span>┬⌐ 2026 VEKLOM INC</span>
        </div>
      </footer>

    </div>
  );
};