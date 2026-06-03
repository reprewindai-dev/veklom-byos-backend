import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Sliders, RefreshCw, AlertTriangle, Play, Check, Server, Cpu } from 'lucide-react';

interface RoutingRule {
  id: string;
  name: string;
  strategy: string;
  is_active: boolean;
}

interface RoutingPolicy {
  default_strategy: string;
  fallback_enabled: boolean;
  max_retries: number;
  timeout_seconds: number;
}

export const Routing: React.FC = () => {
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [policy, setPolicy] = useState<RoutingPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Target Distribution Sliders
  const [hetznerWeight, setHetznerWeight] = useState(78);
  const [fraWeight, setFraWeight] = useState(10);
  const [awsWeight, setAwsWeight] = useState(12);

  // Testing cockpit
  const [testPrompt, setTestPrompt] = useState('Categorize the user inquiry and redact PHI data before sending to LLM');
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const fetchRoutingData = async () => {
    setLoading(true);
    setError('');
    try {
      const [rulesData, policyData] = await Promise.all([
        api('/routing'),
        api('/routing/policy')
      ]);
      setRules(rulesData);
      setPolicy(policyData);
    } catch (err: any) {
      setError(err.message || 'Failed to sync routing protocols.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoutingData();
  }, []);

  const handleApplyOverride = async () => {
    setIsSaving(true);
    setError('');
    setSuccess('');
    try {
      // API call to override
      await api('/autonomous/override', {
        method: 'POST',
        body: JSON.stringify({
          model: 'custom_distribution',
          weights: {
            hetzner_fsn1: hetznerWeight,
            hetzner_fra1: fraWeight,
            aws_burst: awsWeight
          }
        })
      });
      setSuccess('Autonomous routing policy successfully redeployed across perimeter nodes.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError(err.message || 'Routing override rejected by sovereign gatekeeper.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPrompt.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api('/routing/model/test', {
        method: 'POST',
        body: JSON.stringify({ prompt: testPrompt })
      });
      setTestResult(result);
    } catch (err: any) {
      setError(err.message || 'Routing test evaluation failed.');
    } finally {
      setTesting(false);
    }
  };

  // Adjust sliders to guarantee 100% total
  const handleHetznerChange = (val: number) => {
    setHetznerWeight(val);
    const remaining = 100 - val;
    const ratio = remaining / (fraWeight + awsWeight || 1);
    setFraWeight(Math.round(fraWeight * ratio));
    setAwsWeight(100 - val - Math.round(fraWeight * ratio));
  };

  const handleFraChange = (val: number) => {
    setFraWeight(val);
    const remaining = 100 - val;
    const ratio = remaining / (hetznerWeight + awsWeight || 1);
    setHetznerWeight(Math.round(hetznerWeight * ratio));
    setAwsWeight(100 - val - Math.round(hetznerWeight * ratio));
  };

  const handleAwsChange = (val: number) => {
    setAwsWeight(val);
    const remaining = 100 - val;
    const ratio = remaining / (hetznerWeight + fraWeight || 1);
    setHetznerWeight(Math.round(hetznerWeight * ratio));
    setFraWeight(100 - val - Math.round(hetznerWeight * ratio));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Cpu className="animate-spin text-[var(--orange)]" size={32} />
        <div className="text-xs text-[var(--text-secondary)] font-mono tracking-widest uppercase">Aligning Autonomous Routes...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <Server size={18} className="text-[var(--orange)]" /> Sovereign Routing System
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Control traffic distribution across local bare-metal clusters and sandboxed public providers.</p>
        </div>
        <button className="btn btn-secondary btn-sm flex items-center gap-1.5" onClick={fetchRoutingData}>
          <RefreshCw size={12} /> Sync Protocols
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded bg-[rgba(255,68,102,0.06)] border border-red-500/20 text-red-400 text-xs flex items-center gap-3">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-3.5 rounded bg-[rgba(16,185,129,0.06)] border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-3">
          <Check size={16} className="shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Dynamic Weight Tuning Sliders */}
        <div className="glow-card lg:col-span-7 flex flex-col justify-between">
          <div>
            <div className="mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2"><Sliders size={15} className="text-[var(--orange)]" /> Manual Override Controls</h3>
              <p className="text-[10px] text-[var(--text-muted)] font-mono uppercase mt-0.5">TUNE PERIMETER LOAD TARGET PERCENTAGES (MUST TOTAL 100%)</p>
            </div>

            <div className="space-y-6 py-2">
              {/* Hetzner Bare Metal */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded bg-[var(--orange)]"></span>
                    <span className="text-white font-bold">Hetzner Private Bare-Metal (FSN1)</span>
                  </div>
                  <span className="text-white font-bold">{hetznerWeight}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={hetznerWeight}
                  onChange={(e) => handleHetznerChange(parseInt(e.target.value))}
                  className="w-full accent-[var(--orange)] bg-neutral-800"
                />
                <p className="text-[10px] text-[var(--text-secondary)] font-mono">Main perimeter region. Zero-leakage compliance pool.</p>
              </div>

              {/* Hetzner FRA1 */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded bg-purple-400"></span>
                    <span className="text-white font-bold">Hetzner FRA1 Sovereign Node Pool</span>
                  </div>
                  <span className="text-white font-bold">{fraWeight}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={fraWeight}
                  onChange={(e) => handleFraChange(parseInt(e.target.value))}
                  className="w-full accent-purple-400 bg-neutral-800"
                />
                <p className="text-[10px] text-[var(--text-secondary)] font-mono">Secondary Bare-Metal cluster in Frankfurt private sandbox.</p>
              </div>

              {/* AWS Burst */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded bg-[var(--blue)]"></span>
                    <span className="text-white font-bold">AWS Gated Burst (us-east-1)</span>
                  </div>
                  <span className="text-white font-bold">{awsWeight}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={awsWeight}
                  onChange={(e) => handleAwsChange(parseInt(e.target.value))}
                  className="w-full accent-[var(--blue)] bg-neutral-800"
                />
                <p className="text-[10px] text-[var(--text-secondary)] font-mono">Public fallback pool. Monitored and encrypted by sovereign gatekeeper.</p>
              </div>
            </div>

            {/* Weights Graph Bar Representation */}
            <div className="mt-6 p-3.5 bg-[rgba(255,255,255,0.01)] rounded border border-[rgba(255,255,255,0.05)]">
              <span className="form-label text-[10px] mb-2 uppercase">AGGREGATED PROMPT INJECTION GRAPH</span>
              <div className="h-5 rounded bg-neutral-800 flex overflow-hidden border border-white/5">
                <div className="bg-[var(--orange)] h-full transition-all duration-300" style={{ width: `${hetznerWeight}%` }} title={`Hetzner: ${hetznerWeight}%`}></div>
                <div className="bg-purple-500 h-full transition-all duration-300" style={{ width: `${fraWeight}%` }} title={`Hetzner FRA1: ${fraWeight}%`}></div>
                <div className="bg-[var(--blue)] h-full transition-all duration-300" style={{ width: `${awsWeight}%` }} title={`AWS Burst: ${awsWeight}%`}></div>
              </div>
              <div className="flex justify-between font-mono text-[9px] text-[var(--text-muted)] mt-2 uppercase">
                <span>bare metal: {hetznerWeight + fraWeight}%</span>
                <span>public gateway: {awsWeight}%</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-[rgba(255,255,255,0.05)] mt-4">
            <button
              onClick={handleApplyOverride}
              className="btn btn-primary w-full py-3 text-xs font-bold font-mono tracking-widest"
              disabled={isSaving}
            >
              {isSaving ? 'APPLYING PERIMETER REDEPLOYMENT...' : 'DEPLOY DYNAMIC ROUTING CONFIG'}
            </button>
          </div>
        </div>

        {/* Right Side: Active Rules and Interactive Simulator */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Active Rules Panel */}
          <div className="glow-card">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-3">ENABLED SCHEMAS</h3>
            <div className="space-y-3">
              {rules.map((rule) => (
                <div key={rule.id} className="flex justify-between items-center p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]">
                  <div>
                    <span className="text-xs font-bold text-white block">{rule.name}</span>
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block mt-0.5">strategy: {rule.strategy.replace('_', ' ')}</span>
                  </div>
                  <span className={`badge ${rule.is_active ? 'badge-green' : 'badge-orange'}`}>
                    {rule.is_active ? 'enforced' : 'inactive'}
                  </span>
                </div>
              ))}

              {policy && (
                <div className="p-3 bg-[rgba(255,184,0,0.02)] border border-[rgba(255,184,0,0.08)] rounded text-[10px] font-mono text-[var(--text-secondary)] space-y-1">
                  <div className="flex justify-between">
                    <span>FALLBACK TARGET:</span>
                    <span className="text-white">{policy.fallback_enabled ? 'ENABLED' : 'DISABLED'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>MAX DISPATCH RETRIES:</span>
                    <span className="text-white">{policy.max_retries} TIMES</span>
                  </div>
                  <div className="flex justify-between">
                    <span>NODE GATEWAY TIMEOUT:</span>
                    <span className="text-white">{policy.timeout_seconds}S</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Interactive Cockpit Simulator */}
          <div className="glow-card">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-1 flex items-center gap-1.5"><Play size={12} className="text-[var(--orange)]" /> ROUTE DISPATCH TESTER</h3>
            <p className="text-[10px] text-[var(--text-muted)] font-mono uppercase mb-3">COMPILE AND EVALUATE TRAFFIC DESTINATIONS</p>

            <form onSubmit={handleTestRoute} className="space-y-3">
              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="Type a sample prompt to simulate system routing..."
                className="form-input text-xs font-mono h-16 py-2.5"
                disabled={testing}
              />
              <button
                type="submit"
                className="btn btn-secondary w-full text-xs font-bold font-mono tracking-wider py-2"
                disabled={testing || !testPrompt.trim()}
              >
                {testing ? 'COMPILING ROUTE PROFILES...' : 'DISPATCH ROUTE SIMULATOR'}
              </button>
            </form>

            {testResult && (
              <div className="mt-4 p-3 rounded bg-[rgba(0,200,255,0.02)] border border-[rgba(0,200,255,0.12)] font-mono text-[10.5px] space-y-2">
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">SELECTED DISPATCH:</span>
                  <span className="text-[var(--blue)] font-bold uppercase">{testResult.selected_model}</span>
                </div>
                <div className="text-[var(--text-secondary)] leading-relaxed">
                  <span className="text-[var(--text-muted)]">JUSTIFICATION:</span> {testResult.reason}
                </div>
                {testResult.alternatives && (
                  <div className="text-[10px] text-[var(--text-muted)] border-t border-[rgba(255,255,255,0.04)] pt-1.5 mt-1">
                    ALT PATHWAYS: {testResult.alternatives.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
};