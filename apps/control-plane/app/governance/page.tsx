"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function GovernancePage() {
  const health = useApi<any>("/api/v1/governance/health");
  const benchmarks = useApi<any>("/api/v1/governance/gladiator/benchmarks");
  const routes = useApi<any>("/api/v1/governance/gladiator/routes");

  return (
    <Shell>
      <TierGate required="sovereign" feature="Governance">
        <PageHeader title="Governance" subtitle="Gladiator routes, Zeno coherence, and overall governance health." />
        <Card className="mb-4">
          <div className="text-sm font-medium mb-2">Health</div>
          <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(health.data, null, 2)}</pre>
        </Card>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Benchmarks</div>
            {benchmarks.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(benchmarks.data)} rowKey={(r) => r.id || r.name} empty="No benchmarks" columns={[
                { key: "name", header: "Benchmark", render: (r) => r.name },
                { key: "score", header: "Score", render: (r) => r.score },
                { key: "ts", header: "When", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
              ]} />
            }
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Forged routes</div>
            {routes.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(routes.data)} rowKey={(r) => r.id || r.route_id} empty="No routes" columns={[
                { key: "name", header: "Route", render: (r) => r.name || r.id },
                { key: "status", header: "Status", render: (r) => r.status },
                { key: "load", header: "Load", render: (r) => r.load ?? "—" },
              ]} />
            }
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
