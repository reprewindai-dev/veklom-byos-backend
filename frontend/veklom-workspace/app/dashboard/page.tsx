"use client";

import Shell from "@/components/Shell";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, StatCard, Table, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function DashboardPage() {
  const balance = useApi<any>("/api/v1/wallet/balance");
  const overview = useApi<any>("/api/v1/workspace/overview");
  const activity = useApi<any>("/api/v1/command-center/activity-feed");
  const audit = useApi<any>("/api/v1/audit?limit=10");

  return (
    <Shell>
      <PageHeader
        title="Overview"
        subtitle="Live state of your sovereign control plane — wallet, health, and recent activity."
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Token Balance"
          value={balance.isLoading ? <Skeleton className="h-8 w-24" /> : (balance.data?.balance ?? balance.data?.tokens ?? "—")}
          hint={balance.data?.currency || "tokens"}
          accent="text-brand-400"
        />
        <StatCard
          label="Health"
          value={overview.data?.health || overview.data?.status || (overview.isLoading ? <Skeleton className="h-8 w-16" /> : "—")}
          accent="text-accent-green"
        />
        <StatCard
          label="Active Deployments"
          value={overview.data?.active_deployments ?? overview.data?.deployments ?? "—"}
        />
        <StatCard
          label="Open Alerts"
          value={overview.data?.open_alerts ?? overview.data?.alerts ?? "—"}
          accent="text-accent-amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="text-sm font-medium mb-3">Recent audit events</div>
          {audit.error ? <ErrorBox message={audit.error.message} /> :
            audit.isLoading ? <Skeleton className="h-40 w-full" /> :
            <Table
              rows={unwrapList<any>(audit.data).slice(0, 10)}
              rowKey={(r) => r.id || r.log_id || JSON.stringify(r).slice(0, 24)}
              empty="No audit entries yet"
              columns={[
                { key: "ts", header: "Time", render: (r) => <span className="text-ink-400">{r.ts || r.timestamp || r.created_at || "—"}</span> },
                { key: "actor", header: "Actor", render: (r) => r.actor || r.user || r.user_id || "—" },
                { key: "action", header: "Action", render: (r) => r.action || r.event || "—" },
                { key: "resource", header: "Resource", render: (r) => r.resource || r.target || "—" },
              ]}
            />
          }
        </Card>
        <Card>
          <div className="text-sm font-medium mb-3">Activity feed</div>
          {activity.error ? <ErrorBox message={activity.error.message} /> :
            activity.isLoading ? <Skeleton className="h-40 w-full" /> :
            <ul className="space-y-2 text-sm">
              {unwrapList<any>(activity.data).slice(0, 8).map((a, i) => (
                <li key={i} className="border-b border-border/60 pb-2 last:border-0">
                  <div className="text-ink-50">{a.title || a.message || a.event || "Event"}</div>
                  <div className="text-xs text-ink-400">{a.ts || a.timestamp || a.created_at || ""}</div>
                </li>
              ))}
              {unwrapList(activity.data).length === 0 && <li className="text-ink-400 text-sm">No recent activity</li>}
            </ul>
          }
        </Card>
      </div>
    </Shell>
  );
}
