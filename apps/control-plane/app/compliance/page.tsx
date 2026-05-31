"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function CompliancePage() {
  const frameworks = useApi<any>("/api/v1/compliance/frameworks");
  const checks = useApi<any>("/api/v1/compliance/checks");
  const schedule = useApi<any>("/api/v1/compliance/schedule");
  const [busy, setBusy] = useState(false);

  async function exportEvidence(frameworkId: string) {
    setBusy(true);
    try {
      const res = await api<any>(`/api/v1/compliance/evidence/${frameworkId}/export`, { body: {} });
      if (res?.url) window.open(res.url, "_blank");
    } catch {} finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="sovereign" feature="Compliance">
        <PageHeader title="Compliance" subtitle="Frameworks, evidence packages, and scheduled exports for auditors." />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Frameworks</div>
            {frameworks.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table
                rows={unwrapList<any>(frameworks.data)}
                rowKey={(r) => r.id || r.framework_id}
                empty="No frameworks"
                columns={[
                  { key: "name", header: "Framework", render: (r) => r.name || r.id },
                  { key: "coverage", header: "Coverage", render: (r) => `${r.coverage ?? "—"}${r.coverage ? "%" : ""}` },
                  { key: "last", header: "Last export", render: (r) => <span className="text-ink-400 text-xs">{r.last_export || "—"}</span> },
                  { key: "actions", header: "", render: (r) => <Button variant="ghost" onClick={() => exportEvidence(r.id || r.framework_id)} disabled={busy}>Export</Button>, width: "120px" },
                ]}
              />
            }
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Recent checks</div>
            {checks.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table
                rows={unwrapList<any>(checks.data).slice(0, 20)}
                rowKey={(r) => r.id || JSON.stringify(r).slice(0, 24)}
                empty="No checks run"
                columns={[
                  { key: "ts", header: "Time", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
                  { key: "name", header: "Check", render: (r) => r.name || r.rule },
                  { key: "result", header: "Result", render: (r) => <span className={r.passed ? "text-accent-green" : "text-accent-red"}>{r.passed ? "pass" : "fail"}</span> },
                ]}
              />
            }
          </Card>
        </div>
        <Card className="mt-4">
          <div className="text-sm font-medium mb-3">Scheduled exports</div>
          {schedule.isLoading ? <Skeleton className="h-16 w-full" /> :
            <pre className="text-xs text-ink-200 bg-bg-900 rounded-md p-3 overflow-x-auto">{JSON.stringify(schedule.data, null, 2)}</pre>
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
