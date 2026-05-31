"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, StatCard } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function LockerPage() {
  const dashboard = useApi<any>("/api/v1/locker/security/dashboard");
  const controls = useApi<any>("/api/v1/locker/security/controls");
  const alerts = useApi<any>("/api/v1/locker/monitoring/alerts");
  const threats = useApi<any>("/api/v1/locker/security/threats/stats");

  return (
    <Shell>
      <TierGate required="sovereign" feature="Locker Security">
        <PageHeader title="Locker Security" subtitle="Isolated credential vault, control surface, monitoring, and threat stats." />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Controls active" value={dashboard.data?.controls_active ?? "—"} accent="text-accent-green" />
          <StatCard label="Open alerts" value={dashboard.data?.open_alerts ?? unwrapList(alerts.data).length ?? "—"} accent="text-accent-amber" />
          <StatCard label="Threats (24h)" value={threats.data?.last_24h ?? threats.data?.count ?? "—"} accent="text-accent-red" />
          <StatCard label="Posture" value={dashboard.data?.posture || dashboard.data?.score || "—"} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Security controls</div>
            {controls.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table
                rows={unwrapList<any>(controls.data)}
                rowKey={(r) => r.id || r.control_id}
                empty="No controls configured"
                columns={[
                  { key: "name", header: "Control", render: (r) => r.name || r.title },
                  { key: "status", header: "Status", render: (r) => <span className={r.enabled || r.status === "enabled" ? "text-accent-green" : "text-ink-400"}>{r.enabled || r.status === "enabled" ? "enabled" : "disabled"}</span> },
                  { key: "severity", header: "Severity", render: (r) => r.severity || "—" },
                ]}
              />
            }
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Recent alerts</div>
            {alerts.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table
                rows={unwrapList<any>(alerts.data).slice(0, 20)}
                rowKey={(r) => r.id || r.alert_id || JSON.stringify(r).slice(0, 24)}
                empty="No alerts"
                columns={[
                  { key: "ts", header: "Time", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
                  { key: "title", header: "Alert", render: (r) => r.title || r.message },
                  { key: "sev", header: "Severity", render: (r) => <span className={r.severity === "high" || r.severity === "critical" ? "text-accent-red" : "text-accent-amber"}>{r.severity || "info"}</span> },
                ]}
              />
            }
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
