"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { MODULES, modulesByGroup } from "@/lib/modules";
import { meetsTier, TIER_LABEL } from "@/lib/tiers";
import * as Icons from "lucide-react";
import clsx from "clsx";

const GROUP_TITLES: Record<string, string> = {
  ops: "Operations",
  governance: "Governance",
  account: "Account",
  vendor: "Vendor",
  admin: "Admin",
};

function Icon({ name, className }: { name: string; className?: string }) {
  const C = (Icons as any)[name] || Icons.Circle;
  return <C className={className} size={16} />;
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const { me, sub, tier, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading) {
    return <div className="min-h-screen grid place-items-center text-ink-400">Loading…</div>;
  }
  if (!me) return null;

  const groups = modulesByGroup();
  const orderedGroups: Array<keyof typeof groups> = ["ops", "governance", "account", "vendor", "admin"];

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-border bg-bg-800 px-3 py-4 flex flex-col">
        <Link href="/dashboard" className="flex items-center gap-2 px-2 py-2 mb-2">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white font-bold">V</div>
          <div>
            <div className="text-sm font-semibold tracking-tight">Veklom</div>
            <div className="text-[10px] text-ink-400 uppercase tracking-widest">Control Plane</div>
          </div>
        </Link>
        <nav className="flex-1 overflow-y-auto scroll-thin space-y-4 mt-2">
          {orderedGroups.map((g) => {
            if (!groups[g]) return null;
            // Hide admin group entirely unless superuser.
            if (g === "admin" && !me.is_superuser) return null;
            return (
              <div key={g}>
                <div className="px-2 text-[10px] uppercase tracking-widest text-ink-600 mb-1">
                  {GROUP_TITLES[g]}
                </div>
                <ul className="space-y-0.5">
                  {groups[g].map((m) => {
                    const active = pathname?.startsWith(m.href);
                    const locked = !meetsTier(tier, m.minTier);
                    return (
                      <li key={m.slug}>
                        <Link
                          href={m.href}
                          className={clsx(
                            "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm",
                            active ? "bg-bg-700 text-ink-50" : "text-ink-200 hover:bg-bg-700/60",
                            locked && "opacity-60"
                          )}
                        >
                          <Icon name={m.icon} className="text-ink-400" />
                          <span className="flex-1 truncate">{m.label}</span>
                          {locked && <Icons.Lock size={12} className="text-ink-600" />}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-border bg-bg-800/70 backdrop-blur flex items-center px-5 gap-4">
          <div className="text-sm text-ink-400">
            {sub?.status === "active" ? "Active" : sub?.status ?? "Free"} · org{" "}
            <span className="text-ink-50">{me.org_name || me.org_id || me.email}</span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span
              className="tier-badge"
              style={{ color: tierColor(tier) }}
              title={`Plan: ${TIER_LABEL[tier]}`}
            >
              {TIER_LABEL[tier]}
            </span>
            <Link href="/subscriptions" className="text-xs text-ink-400 hover:text-ink-50">
              Manage plan
            </Link>
            <button onClick={logout} className="text-xs text-ink-400 hover:text-ink-50">
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 p-6 overflow-y-auto scroll-thin">{children}</main>
      </div>
    </div>
  );
}

function tierColor(t: string) {
  switch (t) {
    case "enterprise": return "#A78BFA";
    case "sovereign": return "#3EE7A2";
    case "pro": return "#3FB6FF";
    case "starter": return "#FFB547";
    default: return "#8892AB";
  }
}
