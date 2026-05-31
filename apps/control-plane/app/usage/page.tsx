"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, StatCard, Table } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function UsagePage() {
  const usage = useApi<any>("/api/v1/billing/usage");
  const breakdown = useApi<any>("/api/v1/billing/breakdown");
  const insights = useApi<any>("/api/v1/insights/summary");

  return (
    <Shell>
      <TierGate required="pro" feature="Usage Analytics">
        <PageHeader title="Usage Analytics" subtitle="Endpoint-level usage, cost, and trends across the workspace." />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Calls (30d)" value={usage.data?.calls_30d ?? usage.data?.total_calls ?? "—"} />
          <StatCard label="Tokens (30d)" value={usage.data?.tokens_30d ?? "—"} />
          <StatCard label="Cost (30d)" value={usage.data?.cost_30d ? `$${usage.data.cost_30d}` : "—"} accent="text-brand-400" />
          <StatCard label="Top endpoint" value={insights.data?.top_endpoint || "—"} />
        </div>
        <Card className="p-0">
          <div className="p-5 pb-3 text-sm font-medium">Breakdown by endpoint</div>
          {breakdown.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(breakdown.data)}
              rowKey={(r) => r.endpoint || r.route || JSON.stringify(r).slice(0, 24)}
              empty="No usage data"
              columns={[
                { key: "endpoint", header: "Endpoint", render: (r) => <span className="font-mono text-xs">{r.endpoint || r.route}</span> },
                { key: "calls", header: "Calls", render: (r) => r.calls ?? r.count },
                { key: "tokens", header: "Tokens", render: (r) => r.tokens },
                { key: "cost", header: "Cost", render: (r) => r.cost != null ? `$${r.cost}` : "—" },
              ]}
            />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
