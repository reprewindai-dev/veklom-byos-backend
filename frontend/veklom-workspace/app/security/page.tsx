"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, StatCard, Table } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function SecurityPage() {
  const dash = useApi<any>("/api/v1/security/dashboard");
  const alerts = useApi<any>("/api/v1/security/alerts");
  const vault = useApi<any>("/api/v1/security/vault");
  const stats = useApi<any>("/api/v1/security/stats");

  return (
    <Shell>
      <TierGate required="sovereign" feature="Security Center">
        <PageHeader title="Security Center" subtitle="Alerts, secret vault, threat statistics." />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <StatCard label="Open alerts" value={stats.data?.open_alerts ?? unwrapList(alerts.data).length} accent="text-accent-amber" />
          <StatCard label="Threats (7d)" value={stats.data?.threats_7d ?? "—"} accent="text-accent-red" />
          <StatCard label="Vault secrets" value={unwrapList(vault.data).length} />
          <StatCard label="Posture score" value={dash.data?.score ?? "—"} accent="text-accent-green" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Alerts</div>
            {alerts.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(alerts.data)} rowKey={(r) => r.id || r.alert_id} empty="No alerts" columns={[
                { key: "ts", header: "Time", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
                { key: "title", header: "Alert", render: (r) => r.title || r.message },
                { key: "sev", header: "Severity", render: (r) => <span className={r.severity === "high" ? "text-accent-red" : "text-accent-amber"}>{r.severity}</span> },
                { key: "status", header: "Status", render: (r) => r.status || "open" },
              ]} />
            }
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Vault</div>
            {vault.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(vault.data)} rowKey={(r) => r.id || r.secret_id} empty="No secrets in vault" columns={[
                { key: "name", header: "Secret", render: (r) => r.name || r.key },
                { key: "rotated", header: "Last rotated", render: (r) => <span className="text-ink-400 text-xs">{r.last_rotated_at || "—"}</span> },
              ]} />
            }
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
