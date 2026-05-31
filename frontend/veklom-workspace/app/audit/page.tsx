"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function AuditPage() {
  const audit = useApi<any>("/api/v1/audit");
  const [busy, setBusy] = useState(false);

  async function exportReport() {
    setBusy(true);
    try {
      const res = await api<any>("/api/v1/audit/compliance-report", { body: {} });
      if (res?.url) window.open(res.url, "_blank");
    } catch {} finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Audit Log">
        <PageHeader
          title="Audit Log"
          subtitle="Tamper-evident execution audit trail. Export for regulators."
          actions={<Button onClick={exportReport} disabled={busy}>{busy ? "Exporting…" : "Compliance export"}</Button>}
        />
        <Card className="p-0">
          {audit.isLoading ? <div className="p-6"><Skeleton className="h-64 w-full" /></div> :
            <Table
              rows={unwrapList<any>(audit.data)}
              rowKey={(r) => r.id || r.log_id || JSON.stringify(r).slice(0, 32)}
              empty="No audit entries"
              columns={[
                { key: "ts", header: "Time", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.timestamp || r.created_at}</span> },
                { key: "actor", header: "Actor", render: (r) => r.actor || r.user || r.user_id || "—" },
                { key: "action", header: "Action", render: (r) => <span className="font-mono text-xs">{r.action || r.event}</span> },
                { key: "resource", header: "Resource", render: (r) => r.resource || r.target || "—" },
                { key: "result", header: "Result", render: (r) => <span className={r.result === "denied" ? "text-accent-red" : "text-accent-green"}>{r.result || r.status || "ok"}</span> },
              ]}
            />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
