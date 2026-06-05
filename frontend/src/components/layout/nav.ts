// Navigation model for the workspace shell. Each item maps to a hash route.
// `embed` items render an external app in an iframe pane (GPC / Terminal /
// IronGrid / Command Center are SEPARATE apps, not React pages).
import {
  Activity,
  Terminal,
  Store,
  Cpu,
  GitFork,
  Server,
  KeyRound,
  ShieldCheck,
  LineChart,
  CreditCard,
  Users,
  Settings as SettingsIcon,
  Sliders,
  Grid3x3,
  LayoutGrid,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  embed?: string; // iframe src for separate apps
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const NAV: NavSection[] = [
  {
    title: 'Workspace',
    items: [
      { id: 'overview', label: 'Overview', icon: Activity },
      { id: 'playground', label: 'Playground', icon: Terminal, badge: 'LIVE' },
      { id: 'marketplace', label: 'Marketplace', icon: Store },
    ],
  },
  {
    title: 'Infrastructure',
    items: [
      { id: 'models', label: 'Models', icon: Cpu },
      { id: 'pipelines', label: 'Pipelines', icon: GitFork },
      { id: 'deployments', label: 'Deployments', icon: Server },
    ],
  },
  {
    title: 'Governance',
    items: [
      { id: 'vault', label: 'Vault', icon: KeyRound },
      { id: 'compliance', label: 'Compliance', icon: ShieldCheck },
    ],
  },
  {
    title: 'Operations',
    items: [
      { id: 'monitoring', label: 'Monitoring', icon: LineChart },
      { id: 'billing', label: 'Billing', icon: CreditCard },
      { id: 'team', label: 'Team', icon: Users },
    ],
  },
  {
    title: 'Control Plane',
    items: [
      { id: 'command-center', label: 'Command Center', icon: LayoutGrid, embed: '/command-center/' },
      { id: 'gpc', label: 'GPC Compiler', icon: Sliders, embed: '/gpc-engine' },
      { id: 'terminal', label: 'Quantum Terminal', icon: Terminal, embed: '/terminal' },
      { id: 'irongrid', label: 'PYO3 IronGrid', icon: Grid3x3, embed: '/irongrid/' },
    ],
  },
];

export const SETTINGS_ITEM: NavItem = { id: 'settings', label: 'Settings', icon: SettingsIcon };

export function findNavItem(id: string): NavItem | undefined {
  for (const section of NAV) {
    const hit = section.items.find((i) => i.id === id);
    if (hit) return hit;
  }
  if (id === SETTINGS_ITEM.id) return SETTINGS_ITEM;
  return undefined;
}
