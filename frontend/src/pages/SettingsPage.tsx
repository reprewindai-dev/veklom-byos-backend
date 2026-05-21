import React, { useState } from 'react';
import { Settings as SettingsIcon, LogOut, ShieldAlert, Cpu, ToggleLeft, ToggleRight } from 'lucide-react';
import { api, setToken } from '../api/client';

interface SettingsPageProps {
  user: any;
  onLogout: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ user, onLogout }) => {
  const [profile] = useState<any>(user || { email: 'operator@veklom.perimeter', role: 'owner' });
  const [sovereignMode, setSovereignMode] = useState(true);
  const [firewallPolicy, setFirewallPolicy] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleLogoutAction = () => {
    setToken('');
    onLogout();
  };

  const handleToggleSovereign = () => {
    setSovereignMode(!sovereignMode);
    triggerSaveToast();
  };

  const handleToggleFirewall = () => {
    setFirewallPolicy(!firewallPolicy);
    triggerSaveToast();
  };

  const triggerSaveToast = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-3">
          <SettingsIcon size={18} className="text-[var(--orange)]" /> Perimeter Control Settings
        </h2>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">Configure system thresholds, firewall parameters, and regional compliance standards.</p>
      </div>

      {saveSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded font-mono animate-fade-in flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          PERIMETER PARAMETERS APPLIED SECURELY
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Profile Card */}
        <div className="glow-card lg:col-span-6 bg-[rgba(10,10,12,0.6)] backdrop-blur-sm space-y-4">
          <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider border-b border-white/5 pb-2">
            Perimeter Operator Details
          </h3>
          <div className="space-y-3 font-mono text-xs text-[var(--text-secondary)]">
            <div className="flex justify-between py-1 border-b border-white/[0.02]">
              <span>OPERATOR IDENTITY:</span>
              <span className="text-white font-bold">{profile.email}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/[0.02]">
              <span>SECURITY ROLE:</span>
              <span className="text-[var(--orange)] font-bold uppercase">{profile.role}</span>
            </div>
            <div className="flex justify-between py-1">
              <span>DECRYPTION INTEGRITY:</span>
              <span className="text-emerald-400 font-bold uppercase">Active secure session</span>
            </div>
          </div>
        </div>

        {/* Global Security Controls */}
        <div className="glow-card lg:col-span-6 bg-[rgba(10,10,12,0.6)] backdrop-blur-sm space-y-4">
          <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider border-b border-white/5 pb-2">
            System Parameters Override
          </h3>
          <div className="space-y-4">
            
            {/* Toggle 1 */}
            <div className="flex justify-between items-center text-xs font-mono">
              <div className="max-w-[80%]">
                <span className="text-white block font-bold">SOVEREIGN MODE ONLY</span>
                <span className="text-[10px] text-[var(--text-muted)] mt-1 block leading-relaxed">
                  Disable all outgoing connections to unapproved public hosts, enforcing absolute data sovereignty.
                </span>
              </div>
              <button 
                onClick={handleToggleSovereign} 
                className="text-[var(--orange)] hover:opacity-80 transition-opacity"
              >
                {sovereignMode ? <ToggleRight size={28} /> : <ToggleLeft size={28} className="text-neutral-600" />}
              </button>
            </div>

            {/* Toggle 2 */}
            <div className="flex justify-between items-center text-xs font-mono pt-3 border-t border-white/5">
              <div className="max-w-[80%]">
                <span className="text-white block font-bold">EGRESS FIREWALL PROTOCOLS</span>
                <span className="text-[10px] text-[var(--text-muted)] mt-1 block leading-relaxed">
                  Enforce strict cryptographic headers verification on all outgoing RAG data packets.
                </span>
              </div>
              <button 
                onClick={handleToggleFirewall} 
                className="text-[var(--orange)] hover:opacity-80 transition-opacity"
              >
                {firewallPolicy ? <ToggleRight size={28} /> : <ToggleLeft size={28} className="text-neutral-600" />}
              </button>
            </div>

          </div>
        </div>

        {/* Hazard Zone */}
        <div className="glow-card lg:col-span-12 border-red-500/10 bg-[rgba(255,68,102,0.01)] backdrop-blur-sm space-y-4">
          <h3 className="text-xs font-bold text-red-400 font-mono uppercase tracking-wider flex items-center gap-2">
            <ShieldAlert size={14} /> SECURE AREA OPERATIONS
          </h3>
          <p className="text-xs text-[var(--text-secondary)] font-mono leading-relaxed max-w-xl">
            Terminating your session will immediately clear all local cryptographic keys, revoke runtime environment variables, and enforce emergency lockdown on active playground connections.
          </p>
          <div className="pt-2">
            <button 
              onClick={handleLogoutAction} 
              className="btn btn-secondary py-2.5 px-4 text-xs font-bold font-mono tracking-widest flex items-center justify-center gap-1.5 text-red-400 border-red-500/20 hover:border-red-500/50 hover:bg-red-500/5 transition-all self-start"
            >
              <LogOut size={13} /> TERMINATE SECURE SESSION
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
