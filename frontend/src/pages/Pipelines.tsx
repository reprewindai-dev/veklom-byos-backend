import { useQuery } from "@tanstack/react-query";
import { Workflow, Play } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { pipelinesApi } from "@/api";
import { formatNumber, formatRelative } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Pipelines() {
  const q = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => pipelinesApi.list(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Pipelines"
        title="Governed inference pipelines"
        subtitle="Each pipeline chains retrieval, tools, models, redaction, and audit. Backed by GET /api/v1/pipelines."
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : q.isLoading ? (
          <Skeleton className="h-40" />
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : !q.data?.items?.length ? (
          <EmptyState title="No pipelines yet" description="Create one via POST /api/v1/pipelines or the Playground builder." />
        ) : (
          <div className="frame">
            <table className="w-full text-[12.5px]">
              <thead className="border-b border-border/60 bg-muted/30 text-eyebrow">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Template</th>
                  <th className="px-4 py-2 text-left">Vector store</th>
                  <th className="px-4 py-2 text-right">Nodes</th>
                  <th className="px-4 py-2 text-right">Invocations</th>
                  <th className="px-4 py-2 text-left">Last run</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((p) => (
                  <tr key={p.id} className="border-b border-border/40 last:border-0 hover-elevate">
                    <td className="px-4 py-2">{p.name}</td>
                    <td className="px-4 py-2 text-muted-foreground">{p.template ?? "—"}</td>
                    <td className="px-4 py-2">{p.vector_store ? <Chip tone="muted">{p.vector_store}</Chip> : "—"}</td>
                    <td className="px-4 py-2 text-right font-mono">{p.nodes ?? "—"}</td>
                    <td className="px-4 py-2 text-right font-mono">{p.invocations != null ? formatNumber(p.invocations) : "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{p.last_run ? formatRelative(p.last_run) : "—"}</td>
                    <td className="px-4 py-2">
                      {p.status === "deployed" ? (
                        <Chip tone="success" dot>deployed</Chip>
                      ) : (
                        <Chip tone="muted" dot>{p.status ?? "draft"}</Chip>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button size="sm" variant="ghost" className="h-7 px-2">
                        <Play className="h-3.5 w-3.5" />
                      </Button>
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
