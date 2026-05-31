import { useQuery } from "@tanstack/react-query";
import { Network, Cpu, Cloud, Zap } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/data/States";
import { routingApi } from "@/api";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Routing() {
  const topology = useQuery({
    queryKey: ["routing/topology"],
    queryFn: () => routingApi.topology(),
    enabled: !IS_DEMO_MODE,
  });
  const economics = useQuery({
    queryKey: ["routing/economics"],
    queryFn: () => routingApi.economics(),
    enabled: !IS_DEMO_MODE,
  });
  const autonomous = useQuery({
    queryKey: ["autonomous/decisions"],
    queryFn: () => routingApi.autonomous.decisions(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Routing · deterministic substrate"
        title="Route classes, topology, py03-irongrid"
        subtitle="The deterministic routing contract from GET /api/v1/routing/topology + autonomous decision log."
        meta={
          <>
            <Chip tone="primary" icon={<Cpu className="h-3 w-3" />}>py03-irongrid</Chip>
            <Chip tone="info" icon={<Cloud className="h-3 w-3" />}>Cloudflare edge</Chip>
            <Chip tone="muted" icon={<Zap className="h-3 w-3" />}>Hetzner primary</Chip>
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-7 p-4">
              <div className="text-eyebrow">Topology</div>
              {topology.isLoading ? (
                <Skeleton className="mt-2 h-40" />
              ) : topology.error ? (
                <ErrorState error={topology.error} />
              ) : (
                <pre className="mt-2 max-h-[400px] overflow-auto rounded-md border bg-background/60 p-3 font-mono text-[11.5px] leading-relaxed">
                  {JSON.stringify(topology.data, null, 2)}
                </pre>
              )}
            </div>
            <div className="frame col-span-12 lg:col-span-5 p-4">
              <div className="text-eyebrow">Economics</div>
              {economics.isLoading ? (
                <Skeleton className="mt-2 h-40" />
              ) : economics.error ? (
                <ErrorState error={economics.error} />
              ) : (
                <pre className="mt-2 max-h-[400px] overflow-auto rounded-md border bg-background/60 p-3 font-mono text-[11.5px] leading-relaxed">
                  {JSON.stringify(economics.data, null, 2)}
                </pre>
              )}
            </div>
            <div className="frame col-span-12 p-4">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-primary" />
                <div className="text-eyebrow">Autonomous decisions</div>
              </div>
              {autonomous.isLoading ? (
                <Skeleton className="mt-2 h-32" />
              ) : autonomous.error ? (
                <ErrorState error={autonomous.error} />
              ) : (
                <pre className="mt-2 max-h-[260px] overflow-auto rounded-md border bg-background/60 p-3 font-mono text-[11.5px] leading-relaxed">
                  {JSON.stringify(autonomous.data, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
