"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function BudgetPage() {
  const rules = useApi<any>("/api/v1/budget");
  const forecast = useApi<any>("/api/v1/budget/forecast");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function addRule() {
    const limit = prompt("Monthly limit (tokens):");
    if (!limit) return;
    setBusy(true); setErr(undefined);
    try {
      await api("/api/v1/budget", { body: { period: "month", limit: Number(limit) } });
      rules.mutate();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  async function remove(id: string) {
    if (!confirm("Delete this budget rule?")) return;
    await api(`/api/v1/budget/${id}`, { method: "DELETE" });
    rules.mutate();
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Budget Caps">
        <PageHeader
          title="Budget Caps"
          subtitle="Hard and soft limits on token spend. Forecasted overrun risk shown below."
          actions={<Button onClick={addRule} disabled={busy}>New rule</Button>}
        />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <Card>
            <div className="text-xs uppercase tracking-widest text-ink-400">Forecast (next 30d)</div>
            <div className="text-2xl font-semibold mt-1">{forecast.isLoading ? <Skeleton className="h-7 w-24" /> : (forecast.data?.projected ?? forecast.data?.forecast ?? "—")}</div>
            <div className="text-xs text-ink-400 mt-1">tokens</div>
          </Card>
          <Card>
            <div className="text-xs uppercase tracking-widest text-ink-400">Overrun risk</div>
            <div className="text-2xl font-semibold mt-1 text-accent-amber">{forecast.data?.risk ?? "—"}</div>
          </Card>
          <Card>
            <div className="text-xs uppercase tracking-widest text-ink-400">Current MTD</div>
            <div className="text-2xl font-semibold mt-1">{forecast.data?.mtd ?? "—"}</div>
          </Card>
        </div>
        <Card className="p-0">
          {rules.isLoading ? <div className="p-6"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(rules.data)}
              rowKey={(r) => r.id || r.rule_id}
              empty="No budget rules yet"
              columns={[
                { key: "period", header: "Period", render: (r) => r.period || "month" },
                { key: "limit", header: "Limit", render: (r) => r.limit ?? r.cap },
                { key: "scope", header: "Scope", render: (r) => r.scope || "workspace" },
                { key: "kind", header: "Type", render: (r) => r.kind || (r.hard ? "hard" : "soft") },
                { key: "actions", header: "", render: (r) => <Button variant="danger" onClick={() => remove(r.id || r.rule_id)}>Delete</Button>, width: "100px" },
              ]}
            />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
