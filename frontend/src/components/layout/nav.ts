import {
  Compass,
  Sparkles,
  Boxes,
  Workflow,
  PlugZap,
  Gauge,
  FileLock2,
  ShieldCheck,
  Store,
  CreditCard,
  Users,
  Settings2,
  Terminal,
  RadioTower,
  Bot,
  Network,
  GitBranch,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: typeof Compass;
  group: "core" | "infra" | "govern" | "ops" | "super";
  badge?: string;
  /** Only show for roles in this list (UI-only gate; backend enforces auth). */
  roles?: string[];
};

export const NAV: NavItem[] = [
  // Workspace
  { href: "/", label: "Overview", icon: Compass, group: "core" },
  { href: "/playground", label: "Playground", icon: Sparkles, group: "core", badge: "Live" },
  { href: "/marketplace", label: "Marketplace", icon: Store, group: "core" },

  // Infrastructure
  { href: "/models", label: "Models", icon: Boxes, group: "infra" },
  { href: "/pipelines", label: "Pipelines", icon: Workflow, group: "infra" },
  { href: "/deployments", label: "Deployments", icon: PlugZap, group: "infra" },
  { href: "/routing", label: "Routing", icon: Network, group: "infra" },

  // Governance
  { href: "/gpc", label: "GPC Plans", icon: GitBranch, group: "govern" },
  { href: "/agents", label: "Agent Workforce", icon: Bot, group: "govern" },
  { href: "/vault", label: "Vault", icon: FileLock2, group: "govern" },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck, group: "govern" },

  // Operations
  { href: "/monitoring", label: "Monitoring", icon: Gauge, group: "ops" },
  { href: "/billing", label: "Billing", icon: CreditCard, group: "ops" },
  { href: "/team", label: "Team", icon: Users, group: "ops" },
  { href: "/settings", label: "Settings", icon: Settings2, group: "ops" },

  // Super-user / admin-only surfaces
  { href: "/command-center", label: "Command Center", icon: RadioTower, group: "super", roles: ["admin", "owner", "superuser"] },
  { href: "/terminal", label: "GPC Terminal", icon: Terminal, group: "super", roles: ["admin", "owner", "superuser"] },
];

export const GROUPS: { id: NavItem["group"]; label: string }[] = [
  { id: "core", label: "Workspace" },
  { id: "infra", label: "Infrastructure" },
  { id: "govern", label: "Governance" },
  { id: "ops", label: "Operations" },
  { id: "super", label: "Super User" },
];
