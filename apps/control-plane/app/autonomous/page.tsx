"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function AutonomousPage() {
  const decisions = useApi<any>("/api/v1/autonomous/decisions");
  const flags = useApi<any>("/api/v1/autonomous/feature-flags");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function execute() {
    const goal = prompt("Goal for autonomous run:");
    if (!goal) return;
    setBusy(true); setErr(undefined);
    try { await api("/api/v1/autonomous/execute", { body: { goal } }); decisions.mutate(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function override(id: string) {
    if (!confirm("Override this decision?")) return;
    try { await api("/api/v1/autonomous/override", { body: { id } }); decisions.mutate(); } catch {}
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Autonomous Jobs">
        <PageHeader
          title="Autonomous Jobs"
          subtitle="Run, monitor, and override autonomous execution sessions."
          actions={<Button onClick={execute} disabled={busy}>{busy ? "Starting…" : "New run"}</Button>}
        />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <Card className="p-0 mb-4">
          <div className="p-5 pb-3 text-sm font-medium">Recent decisions</div>
          {decisions.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(decisions.data)}
              rowKey={(r) => r.id || r.decision_id}
              empty="No autonomous decisions yet"
              columns={[
                { key: "ts", header: "Time", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
                { key: "goal", header: "Goal", render: (r) => r.goal || r.objective },
                { key: "action", header: "Action", render: (r) => <span className="font-mono text-xs">{r.action || r.decision}</span> },
                { key: "status", header: "Status", render: (r) => r.status },
                { key: "actions", header: "", render: (r) => <Button variant="ghost" onClick={() => override(r.id || r.decision_id)}>Override</Button>, width: "120px" },
              ]}
            />
          }
        </Card>
        <Card>
          <div className="text-sm font-medium mb-3">Feature flags</div>
          {flags.isLoading ? <Skeleton className="h-16 w-full" /> :
            <pre className="text-xs text-ink-200 bg-bg-900 rounded-md p-3 overflow-x-auto">{JSON.stringify(flags.data, null, 2)}</pre>
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
