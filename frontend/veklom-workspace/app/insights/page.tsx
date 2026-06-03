"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, StatCard } from "@/components/ui";

export default function InsightsPage() {
  const summary = useApi<any>("/api/v1/insights/summary");
  const savings = useApi<any>("/api/v1/insights/savings");
  const projected = useApi<any>("/api/v1/insights/savings/projected");

  return (
    <Shell>
      <TierGate required="pro" feature="Insights">
        <PageHeader title="Insights" subtitle="Realized savings and forecasted opportunities from routing and budget controls." />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <StatCard label="Savings (30d)" value={savings.data?.total ? `$${savings.data.total}` : "—"} accent="text-accent-green" />
          <StatCard label="Projected (next 30d)" value={projected.data?.total ? `$${projected.data.total}` : "—"} accent="text-brand-400" />
          <StatCard label="Top lever" value={summary.data?.top_lever || "—"} />
        </div>
        <Card>
          <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(summary.data, null, 2)}</pre>
        </Card>
      </TierGate>
    </Shell>
  );
}
