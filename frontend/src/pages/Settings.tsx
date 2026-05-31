import { useQuery } from "@tanstack/react-query";
import { Settings2, Layers, Server, ShieldCheck } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/data/States";
import { workspaceApi } from "@/api";
import { IS_DEMO_MODE, API_BASE } from "@/lib/env";

export default function Settings() {
  const q = useQuery({
    queryKey: ["workspace"],
    queryFn: () => workspaceApi.current(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Workspace administration"
        subtitle="Sourced from GET /api/v1/workspace. Update via PATCH /api/v1/workspace/settings."
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : q.isLoading ? (
          <Skeleton className="h-40" />
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-8 p-4">
              <div className="flex items-center gap-2 border-b border-border/60 pb-3">
                <Layers className="h-4 w-4 text-primary" />
                <div className="font-display text-[14px] font-semibold">Workspace</div>
              </div>
              <dl className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                <DL label="Name" v={q.data?.name ?? "—"} />
                <DL label="Slug" v={q.data?.slug ?? "—"} />
                <DL label="Region" v={q.data?.region ?? "—"} />
                <DL label="Plan" v={q.data?.plan ?? "—"} />
                <DL label="Monthly cap" v={q.data?.budget?.monthly_cap != null ? `$${q.data.budget.monthly_cap}` : "—"} />
                <DL label="Current spend" v={q.data?.budget?.current_spend != null ? `$${q.data.budget.current_spend}` : "—"} />
              </dl>

              <div className="mt-6 flex items-center gap-2 border-b border-border/60 pb-3">
                <ShieldCheck className="h-4 w-4 text-info" />
                <div className="font-display text-[14px] font-semibold">Connection</div>
              </div>
              <dl className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                <DL label="Backend URL" v={API_BASE || "—"} />
                <DL label="Auth" v="JWT Bearer (auto)" />
              </dl>
            </div>

            <aside className="col-span-12 lg:col-span-4 space-y-3">
              <div className="frame p-4">
                <div className="text-eyebrow">Status</div>
                <div className="mt-2 space-y-1.5 text-[12px]">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2"><Server className="h-3.5 w-3.5 text-primary" /> Backend</span>
                    <Chip tone="success" dot>reachable</Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2"><Settings2 className="h-3.5 w-3.5 text-info" /> Settings RW</span>
                    <Chip tone="info">PATCH /workspace/settings</Chip>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}

function DL({ label, v }: { label: string; v: string }) {
  return (
    <div className="rounded-md border bg-background/40 px-3 py-2">
      <div className="text-eyebrow">{label}</div>
      <div className="mt-0.5 font-mono text-[12.5px] text-foreground">{v}</div>
    </div>
  );
}
