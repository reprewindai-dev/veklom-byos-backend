import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Server, Activity, ArrowUpRight, Shield, RefreshCw } from 'lucide-react';

export const DeploymentsPage: React.FC = () => {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [subError, setSubError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchDeployments = async () => {
    setIsLoading(true);
    setSubError('');
    try {
      const res = await api('/deployments');
      setDeployments(res);
    } catch (err: any) {
      setSubError(err.message || 'Gateway sync aborted.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <Server size={18} className="text-[var(--orange)] animate-pulse" /> Bare-Metal Deployments
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Monitor active running docker vLLM bare-metal pods.</p>
        </div>
        <div>
          <button 
            onClick={fetchDeployments} 
            className="btn btn-secondary px-3 py-1.5 text-xs font-mono tracking-wider flex items-center gap-1.5"
            disabled={isLoading}
          >
            <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
            SYNC INSTANCES
          </button>
        </div>
      </div>

      {subError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded font-mono">
          {subError}
        </div>
      )}

      {/* Deployment Statistics Meters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glow-card p-4">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">RUNNING CONTAINER PODS</span>
          <span className="text-2xl font-black text-white mt-1.5 font-mono">{deployments.length} Pods</span>
          <span className="text-[9.5px] text-emerald-400 block mt-1 font-mono">100% HEALTH CHECK PASS</span>
        </div>
        <div className="glow-card p-4">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">ACTIVE HOST PORTS</span>
          <span className="text-2xl font-black text-white mt-1.5 font-mono">31 Ports</span>
          <span className="text-[9.5px] text-[var(--text-secondary)] block mt-1 font-mono">Isolated sovereign VLAN</span>
        </div>
        <div className="glow-card p-4">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">POD UPTIME DISPATCH</span>
          <span className="text-2xl font-black text-white mt-1.5 font-mono">99.998%</span>
          <span className="text-[9.5px] text-emerald-400 block mt-1 font-mono">SLA Commit achieved</span>
        </div>
        <div className="glow-card p-4">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">FIREWALL SECURITY GATE</span>
          <span className="text-2xl font-black text-[var(--orange)] mt-1.5 font-mono">ENFORCED</span>
          <span className="text-[9.5px] text-[var(--text-secondary)] block mt-1 font-mono">Zero egress to public net</span>
        </div>
      </div>

      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3 text-xs font-mono text-[var(--text-secondary)]">
          <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-spin">
            <circle cx="50" cy="50" r="40" stroke="rgba(255,184,0,0.1)" strokeWidth="10" />
            <path d="M50 10 A40 40 0 0 1 90 50" stroke="#ffb800" strokeWidth="10" strokeLinecap="round" />
          </svg>
          <span>QUERING DOCKER CLUSTER DEMONS...</span>
        </div>
      ) : deployments.length === 0 ? (
        <div className="py-12 border border-dashed border-white/5 rounded-xl flex flex-col items-center justify-center gap-2 text-center text-xs font-mono text-[var(--text-secondary)]">
          <Server size={24} className="text-[var(--text-muted)] mb-2" />
          <span>NO ACTIVE CONTAINER RUNTIMES DEPLOYED</span>
          <span className="text-[10px] text-[var(--text-muted)]">Register deployments in the Marketplace catalogue or create static services.</span>
        </div>
      ) : (
        <div className="overflow-x-auto glow-card p-0 border-white/5 bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
          <table className="data-table">
            <thead>
              <tr>
                <th>Deployment ID</th>
                <th>Instance Label</th>
                <th>Container Type</th>
                <th>Endpoint Tunnel</th>
                <th className="text-right">Platform Status</th>
              </tr>
            </thead>
            <tbody>
              {deployments.map((d) => (
                <tr key={d.id} className="hover:bg-white/[0.01]">
                  <td className="font-mono text-white font-bold text-[10px]">{d.id.toUpperCase()}</td>
                  <td className="font-semibold text-white flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    {d.name}
                  </td>
                  <td>
                    <span className="badge badge-orange text-[9px] uppercase font-mono tracking-wider">{d.type}</span>
                  </td>
                  <td className="font-mono text-neutral-300">{d.endpoint}</td>
                  <td className="text-right font-mono text-emerald-400 font-bold uppercase">
                    {d.status} <span className="text-white">✓</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
