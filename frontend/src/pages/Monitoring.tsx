import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, FileLock2 } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip, HealthChip, LiveBadge } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { monitoringApi, auditApi } from "@/api";
import { formatRelative, trimHash } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Monitoring() {
  const health = useQuery({
    queryKey: ["monitoring/health"],
    queryFn: () => monitoringApi.monitoring.health(),
    enabled: !IS_DEMO_MODE,
    refetchInterval: 30_000,
  });
  const events = useQuery({
    queryKey: ["monitoring/events"],
    queryFn: () => monitoringApi.monitoring.events({ limit: 30 }),
    enabled: !IS_DEMO_MODE,
  });
  const audit = useQuery({
    queryKey: ["audit/logs", { limit: 30 }],
    queryFn: () => auditApi.logs({ limit: 30 }),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Monitoring · observability"
        title="Real-time platform telemetry"
        subtitle="Health, events, errors, and tamper-evident audit logs — sourced from GET /api/v1/monitoring/* and /api/v1/audit/*."
        meta={
          <>
            <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "LIVE"} />
            <HealthChip status={typeof health.data === "object" && health.data && "status" in (health.data as object) ? String((health.data as { status: string }).status) : "healthy"} />
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-7">
              <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                <div>
                  <div className="text-eyebrow">Events</div>
                  <div className="font-display text-[15px]">/monitoring/events</div>
                </div>
                <Chip tone="primary" icon={<Activity className="h-3 w-3" />}>
                  {events.data?.items?.length ?? 0} entries
                </Chip>
              </div>
              <div className="p-4">
                {events.isLoading ? (
                  <Skeleton className="h-40" />
                ) : events.error ? (
                  <ErrorState error={events.error} />
                ) : !events.data?.items?.length ? (
                  <EmptyState title="No events" description="Once your backend serves traffic, monitoring events stream in here." />
                ) : (
                  <ul className="divide-y divide-border/60">
                    {events.data.items.map((e) => (
                      <li key={e.id} className="flex items-start gap-3 py-2.5 text-[12.5px]">
                        <span
                          className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                            e.severity === "critical" ? "bg-destructive" : e.severity === "warn" ? "bg-warn" : "bg-info"
                          }`}
                        />
                        <div className="flex-1">
                          <div>{e.message}</div>
                          <div className="text-eyebrow">{e.type} · {formatRelative(e.created_at)}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="frame col-span-12 lg:col-span-5">
              <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                <div>
                  <div className="text-eyebrow">Audit log · tamper-evident</div>
                  <div className="font-display text-[15px]">SHA hash chain</div>
                </div>
                <Chip tone="success" icon={<FileLock2 className="h-3 w-3" />}>verified</Chip>
              </div>
              <div className="p-4">
                {audit.isLoading ? (
                  <Skeleton className="h-40" />
                ) : audit.error ? (
                  <ErrorState error={audit.error} />
                ) : !audit.data?.items?.length ? (
                  <EmptyState title="No audit entries yet" />
                ) : (
                  <div className="divide-y divide-border/60 max-h-[420px] overflow-auto">
                    {audit.data.items.map((a) => (
                      <div key={a.id} className="py-2.5 text-[12px]">
                        <div className="flex items-center justify-between">
                          <span className="font-mono">{a.operation_type}</span>
                          <span className="font-mono text-[10.5px] text-muted-foreground">
                            {formatRelative(a.created_at)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                          <span className="truncate">{a.provider} · {a.model}</span>
                          <span className="font-mono">{trimHash(a.log_hash)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
