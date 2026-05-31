import { useState } from "react";
import { Link, useLocation } from "wouter";
import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { VeklomLogo } from "@/components/brand/Logo";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { GROUPS, NAV } from "./nav";
import { cn } from "@/lib/utils";
import { IS_DEMO_MODE } from "@/lib/env";

export function Sidebar() {
  const [location] = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "sticky top-0 z-30 flex h-screen shrink-0 flex-col border-r bg-sidebar/80 backdrop-blur transition-[width]",
        collapsed ? "w-[72px]" : "w-[260px]",
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-4">
        <Link href="/" className="hover-elevate -mx-2 rounded-md px-2 py-1">
          <VeklomLogo withWordmark={!collapsed} showTagline={!collapsed} />
        </Link>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="hover-elevate inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {GROUPS.map((g) => (
          <div key={g.id} className="mb-4">
            {!collapsed && <div className="px-3 pb-1.5 text-eyebrow">{g.label}</div>}
            <ul className="space-y-0.5">
              {NAV.filter((n) => n.group === g.id).map((n) => {
                const isActive = location === n.href || (n.href !== "/" && location.startsWith(n.href));
                const Icon = n.icon;
                return (
                  <li key={n.href}>
                    <Link
                      href={n.href}
                      className={cn(
                        "hover-elevate group flex items-center gap-3 rounded-md px-3 py-1.5 text-[13px]",
                        isActive
                          ? "bg-sidebar-accent text-foreground"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <Icon className={cn("h-4 w-4 shrink-0", isActive && "text-primary")} />
                      {!collapsed && (
                        <span className="flex flex-1 items-center justify-between">
                          <span>{n.label}</span>
                          {n.badge && (
                            <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-success">
                              {n.badge}
                            </span>
                          )}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-3 py-3">
        {!collapsed ? (
          <div className="frame-quiet space-y-2 p-3">
            <div className="flex items-center justify-between">
              <span className="text-eyebrow">{IS_DEMO_MODE ? "Demo mode" : "Sovereign mode"}</span>
              <LiveBadge label={IS_DEMO_MODE ? "UNCONFIGURED" : "ON-PREM"} />
            </div>
            <p className="text-[11px] leading-snug text-muted-foreground">
              {IS_DEMO_MODE
                ? "Set VITE_VEKLOM_API_BASE to your veklom-byos-backend URL to wire live data."
                : "Every request evaluated by policy on your perimeter. Bursts gated by tenant rule."}
            </p>
            <div className="flex items-center gap-2">
              <Chip tone="primary" dot>
                Hetzner
              </Chip>
              <Chip tone="info" dot>
                AWS
              </Chip>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <LiveBadge label="" />
          </div>
        )}
      </div>
    </aside>
  );
}
