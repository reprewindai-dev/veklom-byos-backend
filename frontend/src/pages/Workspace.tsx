import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { setToken } from '../api/client';
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
  User,
  UserCheck,
  ShoppingBag
} from 'lucide-react';

interface WorkspaceProps {
  onLogout: () => void;
  user: any;
}

export const Workspace: React.FC<WorkspaceProps> = ({ onLogout, user }) => {
  const [profile] = useState<any>(user || { email: 'operator@veklom.perimeter', role: 'owner' });

  const handleLogoutAction = () => {
    setToken('');
    onLogout();
  };

  const getNavLinkClass = ({ isActive }: { isActive: boolean }) => 
    `w-full text-left px-3 py-2 text-xs font-mono font-semibold rounded flex items-center gap-2.5 transition-all ${
      isActive
        ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white font-bold'
        : 'text-[var(--text-secondary)] hover:text-white'
    }`;

  return (
    <div className="grid-bg min-h-screen flex flex-col justify-between">
      
      {/* Dynamic Header console bar */}
      <header className="h-14 bg-[rgba(10,10,12,0.9)] border-b border-[rgba(255,255,255,0.05)] backdrop-blur-md px-6 flex items-center justify-between relative z-20 flex-shrink-0">
        <div className="flex items-center gap-3">
          <NavLink to="/overview" className="flex items-center gap-3">
            <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-[0_0_4px_rgba(255,184,0,0.4)] cursor-pointer">
              <path d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15" stroke="#ffb800" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="50" cy="48" r="8" fill="#ffffff" />
            </svg>
            <span className="text-sm font-black tracking-[0.1em] text-white">VEKLOM</span>
          </NavLink>
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
                <NavLink to="/overview" className={getNavLinkClass}>
                  <Activity size={13} /> Overview
                </NavLink>
                <NavLink to="/playground" className={getNavLinkClass}>
                  <Terminal size={13} /> Playground
                </NavLink>
                <NavLink to="/command-center" className={getNavLinkClass}>
                  <Layers size={13} /> Command Center
                </NavLink>
                <NavLink to="/marketplace" className={getNavLinkClass}>
                  <ShoppingBag size={13} /> Marketplace
                </NavLink>
              </nav>
            </div>

            {/* Sec: GPC */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">GPC Spine</span>
              <nav className="space-y-1">
                <NavLink to="/gpc" className={getNavLinkClass}>
                  <Sliders size={13} /> GPC Compiler
                </NavLink>
                <NavLink to="/gpc/py03-irongrid" className={getNavLinkClass}>
                  <Cpu size={13} /> PY03 IronGrid
                </NavLink>
              </nav>
            </div>

            {/* Sec: Infrastructure */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Veklom Runtime</span>
              <nav className="space-y-1">
                <NavLink to="/models" className={getNavLinkClass}>
                  <Cpu size={13} /> Models
                </NavLink>
                <NavLink to="/pipelines" className={getNavLinkClass}>
                  <GitFork size={13} /> Pipelines
                </NavLink>
                <NavLink to="/deployments" className={getNavLinkClass}>
                  <Server size={13} /> Deployments
                </NavLink>
                <NavLink to="/routing" className={getNavLinkClass}>
                  <Sliders size={13} /> Sovereign Routing
                </NavLink>
              </nav>
            </div>

            {/* Sec: Governance */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Governance Guard</span>
              <nav className="space-y-1">
                <NavLink to="/vault" className={getNavLinkClass}>
                  <Key size={13} /> Crypto Vault
                </NavLink>
                <NavLink to="/compliance" className={getNavLinkClass}>
                  <ShieldCheck size={13} /> Compliance Audits
                </NavLink>
              </nav>
            </div>

            {/* Sec: Operations */}
            <div>
              <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase block px-3 mb-2">Expense & Monitors</span>
              <nav className="space-y-1">
                <NavLink to="/monitoring" className={getNavLinkClass}>
                  <ActivitySquare size={13} /> Observability
                </NavLink>
                <NavLink to="/billing" className={getNavLinkClass}>
                  <CreditCard size={13} /> Ledger Wallet
                </NavLink>
                <NavLink to="/team" className={getNavLinkClass}>
                  <UserCheck size={13} /> Team Cockpit
                </NavLink>
                <NavLink to="/settings" className={getNavLinkClass}>
                  <SettingsIcon size={13} /> Perimeter Settings
                </NavLink>
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
          <Outlet />
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
          <span>© 2026 VEKLOM INC</span>
        </div>
      </footer>

    </div>
  );
};
