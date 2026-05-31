"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table } from "@/components/ui";
import { unwrapList } from "@/types/api";

export default function WorkspacePage() {
  const overview = useApi<any>("/api/v1/workspace/overview");
  const models = useApi<any>("/api/v1/workspace/models");
  const providers = useApi<any>("/api/v1/workspace/providers");
  const integrations = useApi<any>("/api/v1/workspace/integrations");
  const obs = useApi<any>("/api/v1/workspace/observability");

  return (
    <Shell>
      <TierGate required="starter" feature="Workspace Settings">
        <PageHeader title="Workspace Settings" subtitle="Models, providers, integrations, and observability config." />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <div className="text-sm font-medium mb-2">Overview</div>
            <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(overview.data, null, 2)}</pre>
          </Card>
          <Card>
            <div className="text-sm font-medium mb-2">Observability</div>
            <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(obs.data, null, 2)}</pre>
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Models</div>
            {models.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(models.data)} rowKey={(r) => r.id || r.model_id || r.name} empty="No models" columns={[
                { key: "name", header: "Model", render: (r) => r.name || r.id },
                { key: "provider", header: "Provider", render: (r) => r.provider },
                { key: "status", header: "Status", render: (r) => r.status || (r.deployed ? "deployed" : "—") },
              ]} />
            }
          </Card>
          <Card className="p-0">
            <div className="p-5 pb-3 text-sm font-medium">Providers</div>
            {providers.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(providers.data)} rowKey={(r) => r.id || r.name} empty="No providers" columns={[
                { key: "name", header: "Provider", render: (r) => r.name },
                { key: "region", header: "Region", render: (r) => r.region || "—" },
                { key: "status", header: "Status", render: (r) => r.status },
              ]} />
            }
          </Card>
          <Card className="lg:col-span-2 p-0">
            <div className="p-5 pb-3 text-sm font-medium">Integrations</div>
            {integrations.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
              <Table rows={unwrapList<any>(integrations.data)} rowKey={(r) => r.id || r.name} empty="No integrations" columns={[
                { key: "name", header: "Integration", render: (r) => r.name },
                { key: "status", header: "Status", render: (r) => r.status || (r.connected ? "connected" : "—") },
              ]} />
            }
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
