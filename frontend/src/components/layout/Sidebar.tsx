import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { NAV, SETTINGS_ITEM } from './nav';
import { Logo } from '../brand/Logo';

interface SidebarProps {
  active: string;
  onNavigate: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ active, onNavigate }) => {
  const renderItem = (id: string, label: string, Icon: LucideIcon, badge?: string) => (
    <button
      key={id}
      onClick={() => onNavigate(id)}
      className={`sidebar-item w-full ${active === id ? 'active' : ''}`}
    >
      <Icon size={14} />
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className="text-[8px] font-bold font-mono tracking-wider text-[var(--green)] bg-[var(--green-dim)] px-1.5 py-0.5 rounded">
          {badge}
        </span>
      )}
    </button>
  );

  return (
    <aside className="shell-sidebar">
      <div className="sidebar-logo">
        <Logo size={22} />
        <div className="leading-none">
          <div className="text-[13px] font-black tracking-[0.08em] text-white">Veklom</div>
          <div className="text-[8px] font-mono tracking-[0.16em] text-[var(--text-muted)] uppercase mt-0.5">
            Sovereign Control Node
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map((section) => (
          <div key={section.title}>
            <div className="sidebar-section-title">{section.title}</div>
            {section.items.map((i) => renderItem(i.id, i.label, i.icon, i.badge))}
          </div>
        ))}
        <div className="mt-3">{renderItem(SETTINGS_ITEM.id, SETTINGS_ITEM.label, SETTINGS_ITEM.icon)}</div>
      </nav>

      {/* Sovereign mode footer card */}
      <div className="m-3 p-3 rounded-lg border border-[var(--border)] bg-white/[0.02]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] font-bold font-mono tracking-wider text-[var(--text-muted)] uppercase">
            Sovereign Mode
          </span>
          <span className="flex items-center gap-1 text-[9px] font-mono text-[var(--green)]">
            <span className="pulse-dot" /> ON-PREM
          </span>
        </div>
        <p className="text-[9px] text-[var(--text-secondary)] leading-relaxed mb-2">
          All requests evaluated by policy on Hetzner. AWS burst gated by tenant rule.
        </p>
        <div className="flex gap-1.5">
          <span className="badge badge-orange">Hetzner</span>
          <span className="badge badge-blue">AWS</span>
        </div>
      </div>
    </aside>
  );
};
