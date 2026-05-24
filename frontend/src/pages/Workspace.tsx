import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { setToken } from '../api/client';
import {
  LayoutDashboard,
  Terminal,
  ShieldCheck,
  ShoppingBag,
  Bot,
  GitBranch,
  FileSearch,
  MonitorDot,
  Users,
  CreditCard,
  Server,
  Settings as SettingsIcon,
  LogOut,
  ChevronLeft,
  Search,
  Flame,
  Activity,
  User,
} from 'lucide-react';

interface WorkspaceProps {
  onLogout: () => void;
  user: any;
}

const NAV_ITEMS = [
  { to: '/command-center',  icon: LayoutDashboard, label: 'Command Center' },
  { to: '/playground',      icon: Terminal,        label: 'Playground',        badge: 'LIVE' },
  { to: '/gpc',             icon: ShieldCheck,     label: 'GPC' },
  { to: '/marketplace',     icon: ShoppingBag,     label: 'Marketplace' },
  { to: '/agent-workforce', icon: Bot,             label: 'Agent Workforce' },
  { to: '/chainops',        icon: GitBranch,       label: 'ChainOps' },
  { to: '/evidence',        icon: FileSearch,      label: 'Evidence & Audit' },
  { to: '/terminals',       icon: MonitorDot,      label: 'Terminals' },
  { to: '/users',           icon: Users,           label: 'Users & Identity' },
  { to: '/billing',         icon: CreditCard,      label: 'Billing & Usage' },
  { to: '/deployments',     icon: Server,          label: 'Deployments / BYOS' },
  { to: '/settings',        icon: SettingsIcon,    label: 'Settings' },
];

export const Workspace: React.FC<WorkspaceProps> = ({ onLogout, user }) => {
  const [collapsed, setCollapsed] = useState(false);
  const profile = user || { email: 'workspace@veklom.com', role: 'USER', workspace_id: '' };
  const workspaceLabel = profile.workspace_id
    ? `WS-${String(profile.workspace_id).slice(0, 8).toUpperCase()}`
    : 'ACME-PROD';

  const handleLogoutAction = () => {
    setToken('');
    onLogout();
  };

  const getNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    `w-full text-left px-3 py-2 text-xs font-mono rounded flex items-center gap-2.5 transition-all ${
      isActive
        ? 'bg-[rgba(255,184,0,0.08)] border-l-2 border-[var(--orange)] text-white font-bold pl-[10px]'
        : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.03]'
    }`;

  return (
    <div className="grid-bg min-h-screen flex flex-col">

      {/* Top Header Bar */}
      <header className="h-11 bg-[rgba(10,10,12,0.95)] border-b border-[rgba(255,255,255,0.05)] backdrop-blur-md px-4 flex items-center justify-between relative z-20 flex-shrink-0 gap-4">

        {/* Left: collapse + env selector */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => setCollapsed(c => !c)}
            className="p-1 text-[var(--text-muted)] hover:text-white transition-colors"
            title="Toggle sidebar"
          >
            <ChevronLeft size={14} className={`transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </button>
          <div className="flex items-center gap-1.5 font-mono text-[10px]">
            <span className="bg-neutral-800 border border-white/10 rounded px-2 py-0.5 text-white/80 cursor-pointer hover:border-white/20 transition-colors flex items-center gap-1">
              <span className="pulse-dot"></span>{workspaceLabel}
            </span>
            <span className="text-white/20">·</span>
            <span className="text-white/40">US-EAST</span>
            <span className="text-white/20">·</span>
            <span className="text-white/30">V1.0</span>
          </div>
        </div>

        {/* Center: search */}
        <div className="flex-1 max-w-md relative hidden sm:block">
          <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Jump to page, model, or doc..."
            className="w-full bg-white/[0.03] border border-white/[0.06] rounded text-[11px] font-mono text-white/50 placeholder-white/20 py-1 pl-7 pr-3 focus:outline-none focus:border-[var(--orange)]/30 transition-colors"
          />
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] font-mono text-white/20 border border-white/10 rounded px-1">Cmd+K</span>
        </div>

        {/* Right: status + user + logout */}
        <div className="flex items-center gap-3 flex-shrink-0 font-mono text-[9px]">
          <span className="flex items-center gap-1 text-[var(--text-muted)]">
            <Flame size={10} className="text-[var(--orange)]" />
            Burn <span className="text-white/70 ml-0.5">$0.0184/min</span>
          </span>
          <span className="text-white/30 hidden md:block">68% budget</span>
          <span className="hidden md:flex items-center gap-1 text-emerald-400">
            <Activity size={9} /> HEALTHY
          </span>
          <span className="bg-[rgba(255,184,0,0.1)] border border-[rgba(255,184,0,0.2)] text-[var(--orange)] rounded px-1.5 py-0.5 hidden lg:block">
            EU-SOVEREIGN
          </span>
          <div className="flex items-center gap-2 pl-2 border-l border-white/10">
            <span className="text-[var(--text-secondary)] hidden sm:block">{profile.email.split('@')[0]}</span>
            <div className="w-6 h-6 rounded-full border border-white/10 flex items-center justify-center bg-white/[0.02] text-[var(--orange)]">
              <User size={11} />
            </div>
            <button onClick={handleLogoutAction} className="p-1 text-[var(--text-muted)] hover:text-red-400 transition-colors" title="Sign out">
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden relative z-10">

        {/* Sidebar */}
        <aside className={`${collapsed ? 'w-0 overflow-hidden' : 'w-56'} bg-[rgba(10,10,12,0.9)] border-r border-[rgba(255,255,255,0.05)] flex flex-col backdrop-blur-md shrink-0 select-none transition-all duration-200`}>

          {/* Logo */}
          <div className="px-4 py-4 border-b border-[rgba(255,255,255,0.05)] flex-shrink-0">
            <NavLink to="/command-center" className="flex items-center gap-2">
              <img src="/static/branding/veklom-wordmark.png" alt="Veklom" className="veklom-wordmark h-7" />
            </NavLink>
            <p className="text-[8px] font-mono tracking-widest text-[var(--text-muted)] uppercase mt-1">Sovereign Control Node</p>
          </div>

          {/* Nav spine - 12 items, flat, ordered */}
          <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
            {NAV_ITEMS.map(({ to, icon: Icon, label, badge }) => (
              <NavLink key={to} to={to} className={getNavLinkClass}>
                <Icon size={13} className="flex-shrink-0" />
                <span className="flex-1 truncate">{label}</span>
                {badge && (
                  <span className="text-[8px] font-bold tracking-wider text-emerald-400 border border-emerald-500/30 rounded px-1 py-0.5 bg-emerald-500/10">
                    {badge}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Sovereign Mode footer */}
          <div className="px-3 py-3 border-t border-[rgba(255,255,255,0.05)] flex-shrink-0">
            <div className="flex items-center gap-1.5 font-mono text-[9px] text-[var(--text-muted)] mb-1.5 uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0"></span>
              Sovereign Mode · On-Prem
            </div>
            <p className="text-[9px] text-[var(--text-muted)] leading-relaxed mb-2">
              All requests evaluated by policy on Hetzner. AWS burst gated by tenant rule.
            </p>
            <div className="flex gap-1.5">
              <span className="text-[8px] font-mono font-bold bg-[rgba(255,184,0,0.08)] border border-[rgba(255,184,0,0.2)] text-[var(--orange)] rounded px-1.5 py-0.5">HETZNER</span>
              <span className="text-[8px] font-mono font-bold bg-[rgba(0,200,255,0.06)] border border-[rgba(0,200,255,0.15)] text-[#00c8ff] rounded px-1.5 py-0.5">AWS</span>
            </div>
          </div>
        </aside>

        {/* Page content */}
        <main className="flex-1 p-6 overflow-y-auto relative bg-[rgba(10,10,12,0.4)] backdrop-blur-sm">
          <Outlet />
        </main>

      </div>
    </div>
  );
};
