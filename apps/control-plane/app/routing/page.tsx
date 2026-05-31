"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, StatCard } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function RoutingPage() {
  const rules = useApi<any>("/api/v1/routing");
  const economics = useApi<any>("/api/v1/routing/economics");
  const topology = useApi<any>("/api/v1/routing/topology");
  const tier = useApi<any>("/api/v1/ai/routing/tier");
  const stack = useApi<any>("/api/v1/routing/stack");

  return (
    <Shell>
      <TierGate required="pro" feature="Smart Routing">
        <PageHeader title="Smart Routing" subtitle="Provider routing rules, economics, and live topology across the model stack." />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Routing tier" value={tier.data?.tier || tier.data?.name || "—"} accent="text-brand-400" />
          <StatCard label="Active rules" value={unwrapList(rules.data).length} />
          <StatCard label="$ saved (30d)" value={economics.data?.savings_30d ?? "—"} accent="text-accent-green" />
          <StatCard label="Avg latency" value={economics.data?.avg_latency_ms ? `${economics.data.avg_latency_ms}ms` : "—"} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Routing rules</div>
            {rules.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table
                rows={unwrapList<any>(rules.data)}
                rowKey={(r) => r.id || r.rule_id}
                empty="No routing rules"
                columns={[
                  { key: "pattern", header: "Match", render: (r) => <span className="font-mono text-xs">{r.pattern || r.match || "*"}</span> },
                  { key: "target", header: "Route to", render: (r) => r.target || r.provider || r.model },
                  { key: "policy", header: "Policy", render: (r) => r.policy || "default" },
                  { key: "priority", header: "Pri", render: (r) => r.priority ?? "—" },
                ]}
              />
            }
          </Card>
          <Card>
            <div className="text-sm font-medium mb-3">Stack / providers</div>
            {stack.isLoading ? <Skeleton className="h-32 w-full" /> :
              <ul className="space-y-2 text-sm">
                {unwrapList<any>(stack.data).map((p, i) => (
                  <li key={i} className="flex justify-between border-b border-border/60 pb-2 last:border-0">
                    <span>{p.provider || p.name}</span>
                    <span className="text-ink-400 text-xs">{p.models ? `${p.models.length} models` : (p.status || "")}</span>
                  </li>
                ))}
              </ul>
            }
            <div className="text-xs text-ink-400 mt-3">
              Topology: {topology.data?.regions?.join(", ") || topology.data?.summary || "—"}
            </div>
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
