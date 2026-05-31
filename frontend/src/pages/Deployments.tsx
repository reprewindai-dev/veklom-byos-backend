import { useQuery } from "@tanstack/react-query";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { deploymentsApi } from "@/api";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Deployments() {
  const q = useQuery({
    queryKey: ["deployments"],
    queryFn: () => deploymentsApi.list(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Deployments · endpoints"
        title="OpenAI-compatible endpoints"
        subtitle="Live tenant endpoints with auth, rate limits, region pinning, and traffic stats. Backed by GET /api/v1/deployments."
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : q.isLoading ? (
          <Skeleton className="h-40" />
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : !q.data?.items?.length ? (
          <EmptyState title="No deployments yet" description="Create one with POST /api/v1/deployments." />
        ) : (
          <div className="frame">
            <table className="w-full text-[12.5px]">
              <thead className="border-b border-border/60 bg-muted/30 text-eyebrow">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Model</th>
                  <th className="px-4 py-2 text-left">Region</th>
                  <th className="px-4 py-2 text-left">Auth</th>
                  <th className="px-4 py-2 text-right">RPS</th>
                  <th className="px-4 py-2 text-right">Errors</th>
                  <th className="px-4 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((d) => (
                  <tr key={d.id} className="border-b border-border/40 last:border-0 hover-elevate">
                    <td className="px-4 py-2">
                      <div className="font-mono">{d.name}</div>
                      {d.endpoint && (
                        <div className="text-[11px] text-muted-foreground truncate max-w-[300px]">{d.endpoint}</div>
                      )}
                    </td>
                    <td className="px-4 py-2"><Chip tone="muted">{d.type}</Chip></td>
                    <td className="px-4 py-2 font-mono text-[11.5px] text-muted-foreground">{d.model ?? "—"}</td>
                    <td className="px-4 py-2 font-mono">{d.region ?? "—"}</td>
                    <td className="px-4 py-2"><Chip tone="info">{d.auth ?? "—"}</Chip></td>
                    <td className="px-4 py-2 text-right font-mono">{d.rps ?? 0}</td>
                    <td className="px-4 py-2 text-right font-mono">{((d.error_rate ?? 0) * 100).toFixed(2)}%</td>
                    <td className="px-4 py-2">
                      <Chip
                        tone={d.status === "live" ? "success" : d.status === "paused" ? "warn" : "muted"}
                        dot
                      >
                        {d.status}
                      </Chip>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageBody>
    </>
  );
}
