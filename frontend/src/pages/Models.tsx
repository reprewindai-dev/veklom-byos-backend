import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Boxes, Cpu, RefreshCcw } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { workspaceApi } from "@/api";
import { useToast } from "@/hooks/useToast";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Models() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const q = useQuery({
    queryKey: ["workspace/models"],
    queryFn: () => workspaceApi.models(),
    enabled: !IS_DEMO_MODE,
  });
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      workspaceApi.toggleModel(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace/models"] }),
    onError: (e) =>
      toast({ title: "Toggle failed", description: e instanceof Error ? e.message : String(e), variant: "destructive" }),
  });

  return (
    <>
      <PageHeader
        eyebrow="Models · catalog"
        title="Workspace model configurations"
        subtitle="Enable, disable, and inspect every model your workspace exposes. Backed by GET /api/v1/workspace/models."
        actions={
          <Button variant="outline" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ["workspace/models"] })}>
            <RefreshCcw className="h-3.5 w-3.5" /> Refresh
          </Button>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : q.isLoading ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
          </div>
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : !q.data?.models?.length ? (
          <EmptyState title="No models configured" description="Connect provider credentials in Settings → Providers." />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {q.data.models.map((m) => (
              <div key={m.id} className="frame p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-eyebrow">{m.bedrock_model_id ?? "model"}</div>
                    <div className="font-display text-[15px] font-semibold">{m.slug}</div>
                  </div>
                  <div className="grid h-8 w-8 place-items-center rounded-md bg-primary/10 text-primary">
                    <Cpu className="h-4 w-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <Chip tone={m.enabled ? "success" : "muted"} dot>
                    {m.enabled ? "enabled" : "disabled"}
                  </Chip>
                  {m.connected != null && (
                    <Chip tone={m.connected ? "info" : "warn"}>
                      {m.connected ? "connected" : "no credentials"}
                    </Chip>
                  )}
                </div>
                <div className="mt-3 flex items-center justify-end">
                  <Button
                    size="sm"
                    variant={m.enabled ? "outline" : "default"}
                    onClick={() => toggle.mutate({ id: m.id, enabled: !m.enabled })}
                    disabled={toggle.isPending}
                  >
                    {m.enabled ? "Disable" : "Enable"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </PageBody>
    </>
  );
}
