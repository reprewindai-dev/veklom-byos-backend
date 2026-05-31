import { useQuery } from "@tanstack/react-query";
import { GitBranch, ListChecks } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { gpcApi } from "@/api";
import { formatRelative } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function GpcPage() {
  const stats = useQuery({
    queryKey: ["gpc/stats"],
    queryFn: () => gpcApi.stats(),
    enabled: !IS_DEMO_MODE,
  });
  const plans = useQuery({
    queryKey: ["gpc/plans"],
    queryFn: () => gpcApi.plans(),
    enabled: !IS_DEMO_MODE,
  });
  const runs = useQuery({
    queryKey: ["gpc/runs"],
    queryFn: () => gpcApi.runs({ limit: 20 }),
    enabled: !IS_DEMO_MODE,
  });
  const frames = useQuery({
    queryKey: ["decision-frames"],
    queryFn: () => gpcApi.decisionFrames.list({ limit: 20 }),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Governance · GPC"
        title="Governed Process Control"
        subtitle="Plans, runs, and decision frames from /api/v1/gpc/* + /api/v1/decision-frames/*."
        meta={
          <>
            <Chip tone="primary" icon={<GitBranch className="h-3 w-3" />}>Plans</Chip>
            <Chip tone="info" icon={<ListChecks className="h-3 w-3" />}>Decision frames</Chip>
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                ["Plans", stats.data?.plans],
                ["Runs", stats.data?.runs],
                ["Pending frames", stats.data?.pending_frames],
                ["Success rate", stats.data?.success_rate != null ? `${Math.round((stats.data.success_rate ?? 0) * 100)}%` : undefined],
              ].map(([label, value]) => (
                <div key={label as string} className="frame p-3">
                  <div className="text-eyebrow">{label as string}</div>
                  <div className="mt-1 font-display text-[19px] font-semibold tracking-tight">
                    {stats.isLoading ? <Skeleton className="h-5 w-12" /> : value == null ? "—" : String(value)}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-12 gap-4">
              <div className="frame col-span-12 lg:col-span-7">
                <div className="border-b border-border/70 px-4 py-3">
                  <div className="text-eyebrow">Recent runs</div>
                  <div className="font-display text-[14px]">/gpc/runs</div>
                </div>
                <div className="p-4">
                  {runs.isLoading ? <Skeleton className="h-32" /> :
                   runs.error ? <ErrorState error={runs.error} /> :
                   !runs.data?.items?.length ? <EmptyState title="No runs yet" /> : (
                    <table className="w-full text-[12.5px]">
                      <thead className="border-b border-border/60 text-eyebrow">
                        <tr>
                          <th className="py-2 text-left">Run</th>
                          <th className="py-2 text-left">Plan</th>
                          <th className="py-2 text-left">Status</th>
                          <th className="py-2 text-left">Started</th>
                        </tr>
                      </thead>
                      <tbody>
                        {runs.data.items.map((r) => (
                          <tr key={r.id} className="border-b border-border/40 last:border-0">
                            <td className="py-2 font-mono text-[11.5px]">{r.id.slice(0, 12)}</td>
                            <td className="py-2 font-mono text-[11.5px] text-muted-foreground">{r.plan_id ?? "—"}</td>
                            <td className="py-2">
                              <Chip
                                tone={r.status === "succeeded" ? "success" : r.status === "failed" || r.status === "halted" ? "danger" : "info"}
                                dot
                              >
                                {r.status}
                              </Chip>
                            </td>
                            <td className="py-2 text-muted-foreground">{r.started_at ? formatRelative(r.started_at) : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="frame col-span-12 lg:col-span-5">
                <div className="border-b border-border/70 px-4 py-3">
                  <div className="text-eyebrow">Plans</div>
                  <div className="font-display text-[14px]">/gpc/plans</div>
                </div>
                <div className="p-4">
                  {plans.isLoading ? <Skeleton className="h-32" /> :
                   plans.error ? <ErrorState error={plans.error} /> :
                   !plans.data?.items?.length ? <EmptyState title="No plans" /> : (
                    <ul className="space-y-2">
                      {plans.data.items.map((p) => (
                        <li key={p.id} className="rounded-md border bg-background/40 p-3">
                          <div className="flex items-center justify-between">
                            <div className="text-[12.5px] font-medium">{p.name ?? p.id}</div>
                            {p.status && <Chip tone="muted">{p.status}</Chip>}
                          </div>
                          {p.intent && <p className="mt-0.5 text-[11.5px] text-muted-foreground line-clamp-2">{p.intent}</p>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="frame col-span-12">
                <div className="border-b border-border/70 px-4 py-3">
                  <div className="text-eyebrow">Decision frames</div>
                  <div className="font-display text-[14px]">/decision-frames</div>
                </div>
                <div className="p-4">
                  {frames.isLoading ? <Skeleton className="h-32" /> :
                   frames.error ? <ErrorState error={frames.error} /> :
                   !frames.data?.items?.length ? <EmptyState title="None pending" /> : (
                    <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
                      {frames.data.items.map((f) => (
                        <li key={f.id} className="rounded-md border bg-background/40 p-3">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11.5px]">{f.id.slice(0, 12)}</span>
                            <Chip tone={f.status === "approved" ? "success" : f.status === "rejected" ? "danger" : "warn"} dot>
                              {f.status}
                            </Chip>
                          </div>
                          {f.rationale && <p className="mt-1 text-[11.5px] text-muted-foreground line-clamp-2">{f.rationale}</p>}
                          <div className="mt-1 text-[10.5px] text-muted-foreground font-mono">{formatRelative(f.created_at)}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </PageBody>
    </>
  );
}
