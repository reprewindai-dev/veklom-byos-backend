import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { RadioTower, Activity, AlertTriangle, Terminal as TerminalIcon, Users } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { commandCenterApi } from "@/api";
import { formatRelative, formatUSD, formatNumber } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function CommandCenter() {
  const overview = useQuery({
    queryKey: ["cc/overview"],
    queryFn: () => commandCenterApi.overview(),
    enabled: !IS_DEMO_MODE,
    refetchInterval: 30_000,
  });
  const activity = useQuery({
    queryKey: ["cc/activity-feed"],
    queryFn: () => commandCenterApi.activityFeed({ limit: 20 }),
    enabled: !IS_DEMO_MODE,
  });
  const alerts = useQuery({
    queryKey: ["cc/operations/alerts"],
    queryFn: () => commandCenterApi.operations.alerts(),
    enabled: !IS_DEMO_MODE,
  });
  const usersSummary = useQuery({
    queryKey: ["cc/users/summary"],
    queryFn: () => commandCenterApi.usersSummary(),
    enabled: !IS_DEMO_MODE,
  });
  const online = useQuery({
    queryKey: ["cc/users/online"],
    queryFn: () => commandCenterApi.usersOnline(),
    enabled: !IS_DEMO_MODE,
    refetchInterval: 60_000,
  });
  const billing = useQuery({
    queryKey: ["cc/business/billing"],
    queryFn: () => commandCenterApi.business.billing(),
    enabled: !IS_DEMO_MODE,
  });

  const kpis = [
    { label: "Workspaces", value: overview.data?.workspace_count },
    { label: "Active users (now)", value: online.data?.items?.length ?? overview.data?.active_users },
    { label: "Errors · 24h", value: overview.data?.errors_24h },
    { label: "Spend today", value: overview.data?.spend_today_usd != null ? formatUSD(overview.data.spend_today_usd) : undefined },
    { label: "MRR", value: billing.data?.mrr_usd != null ? formatUSD(billing.data.mrr_usd) : undefined },
    { label: "Open invoices", value: billing.data?.open_invoices },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Super User · Command Center"
        title="Operational command center"
        subtitle="Cross-workspace control plane for admins. Backed by GET /api/v1/command-center/*."
        meta={
          <>
            <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "LIVE"} />
            <Chip tone="primary" icon={<RadioTower className="h-3 w-3" />}>Admin scope</Chip>
            {usersSummary.data && (
              <Chip tone="muted">
                {formatNumber(usersSummary.data.total)} users · {formatNumber(usersSummary.data.active)} active · {formatNumber(usersSummary.data.new_24h)} new/24h
              </Chip>
            )}
          </>
        }
        actions={
          <Link href="/terminal">
            <Button size="sm" variant="default">
              <TerminalIcon className="h-3.5 w-3.5" /> Open GPC Terminal
            </Button>
          </Link>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              {kpis.map((k) => (
                <div key={k.label} className="frame p-3">
                  <div className="text-eyebrow">{k.label}</div>
                  <div className="mt-1 font-display text-[19px] font-semibold tracking-tight">
                    {overview.isLoading ? <Skeleton className="h-5 w-16" /> : k.value == null ? "—" : typeof k.value === "number" ? formatNumber(k.value) : k.value}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-12 gap-4">
              <div className="frame col-span-12 lg:col-span-7">
                <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                  <div>
                    <div className="text-eyebrow">Activity feed</div>
                    <div className="font-display text-[15px]">/command-center/activity-feed</div>
                  </div>
                  <Activity className="h-4 w-4 text-primary" />
                </div>
                <div className="p-4">
                  {activity.isLoading ? <Skeleton className="h-40" /> :
                   activity.error ? <ErrorState error={activity.error} /> :
                   !activity.data?.items?.length ? <EmptyState title="No activity" /> : (
                    <ul className="divide-y divide-border/60">
                      {activity.data.items.map((e) => (
                        <li key={e.id} className="py-2.5 text-[12.5px]">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Chip tone="muted">{e.type}</Chip>
                              <span>{e.message}</span>
                            </div>
                            <span className="font-mono text-[10.5px] text-muted-foreground">{formatRelative(e.created_at)}</span>
                          </div>
                          {(e.actor || e.target) && (
                            <div className="mt-0.5 text-[11px] text-muted-foreground">
                              {e.actor ?? "system"}{e.target ? ` → ${e.target}` : ""}
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="frame col-span-12 lg:col-span-5">
                <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                  <div>
                    <div className="text-eyebrow">Operational alerts</div>
                    <div className="font-display text-[15px]">/operations/alerts</div>
                  </div>
                  <AlertTriangle className="h-4 w-4 text-warn" />
                </div>
                <div className="p-4">
                  {alerts.isLoading ? <Skeleton className="h-40" /> :
                   alerts.error ? <ErrorState error={alerts.error} /> :
                   !alerts.data?.items?.length ? <EmptyState title="All clear" /> : (
                    <ul className="space-y-2">
                      {alerts.data.items.map((a) => (
                        <li key={a.id} className="rounded-md border bg-background/40 px-3 py-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[12.5px] font-medium">{a.title}</span>
                            <Chip tone={a.severity === "critical" ? "danger" : a.severity === "warn" ? "warn" : "info"} dot>
                              {a.severity}
                            </Chip>
                          </div>
                          <div className="mt-0.5 flex items-center justify-between text-[11px] text-muted-foreground">
                            <span>{a.source ?? "system"}</span>
                            <span className="font-mono">{formatRelative(a.created_at)}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="frame col-span-12">
                <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                  <div>
                    <div className="text-eyebrow">Online now</div>
                    <div className="font-display text-[15px]">/users/online</div>
                  </div>
                  <Users className="h-4 w-4 text-info" />
                </div>
                <div className="p-4">
                  {online.isLoading ? <Skeleton className="h-20" /> :
                   online.error ? <ErrorState error={online.error} /> :
                   !online.data?.items?.length ? <EmptyState title="No-one online" /> : (
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                      {online.data.items.map((u) => (
                        <Link key={u.id} href={`/command-center/users/${u.id}`} className="hover-elevate rounded-md border bg-background/40 px-3 py-2 block">
                          <div className="flex items-center justify-between">
                            <div className="text-[12.5px]">{u.email}</div>
                            <Chip tone="success" dot>online</Chip>
                          </div>
                          <div className="text-[10.5px] text-muted-foreground font-mono">
                            {u.workspace_id ?? "—"} · {u.role ?? "user"}
                          </div>
                        </Link>
                      ))}
                    </div>
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
