import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowUpRight, CircuitBoard, Cpu, FileLock2, Gauge, Layers, ShieldCheck } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { Sparkline } from "@/components/charts/Mini";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { monitoringApi, auditApi } from "@/api";
import { formatNumber, formatRelative, formatUSD, trimHash } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

const SPARK_PLACEHOLDER = Array.from({ length: 20 }, (_, i) => Math.max(0, 50 + Math.sin(i / 1.6) * 16));

export default function Overview() {
  const pulse = useQuery({ queryKey: ["pulse"], queryFn: () => monitoringApi.pulse(), enabled: !IS_DEMO_MODE, refetchInterval: 30_000 });
  const events = useQuery({
    queryKey: ["monitoring/events", { limit: 8 }],
    queryFn: () => monitoringApi.monitoring.events({ limit: 8 }),
    enabled: !IS_DEMO_MODE,
  });
  const audits = useQuery({
    queryKey: ["audit/logs", { limit: 6 }],
    queryFn: () => auditApi.logs({ limit: 6 }),
    enabled: !IS_DEMO_MODE,
  });

  const kpis = [
    { label: "Requests / min", value: pulse.data?.requests_per_min, icon: <Activity className="h-3.5 w-3.5" /> },
    { label: "P50 latency", value: pulse.data?.p50_latency_ms !== undefined ? `${pulse.data.p50_latency_ms} ms` : undefined, icon: <Gauge className="h-3.5 w-3.5" /> },
    { label: "Tokens / sec", value: pulse.data?.tokens_per_sec, icon: <Cpu className="h-3.5 w-3.5" /> },
    { label: "Spend today", value: formatUSD(pulse.data?.spend_today_usd), icon: <CircuitBoard className="h-3.5 w-3.5" /> },
    { label: "Active models", value: pulse.data?.active_models, icon: <Layers className="h-3.5 w-3.5" /> },
    { label: "Audit entries", value: pulse.data?.audit_entries_total, icon: <ShieldCheck className="h-3.5 w-3.5" /> },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Workspace · Overview"
        title="Sovereign control plane"
        subtitle="Every prompt routed, policed, and audited — across your perimeter — without sacrificing developer velocity."
        meta={
          <>
            <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "LIVE BACKEND"} />
            <Chip tone="muted">SOC2-ready</Chip>
            <Chip tone="muted">HIPAA-aware</Chip>
            <Chip tone="muted">EU-sovereign</Chip>
          </>
        }
      />

      <PageBody>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {kpis.map((k) => (
            <div key={k.label} className="frame p-3">
              <div className="flex items-center justify-between text-eyebrow text-foreground/85">
                <span className="flex items-center gap-1.5">
                  {k.icon}
                  {k.label}
                </span>
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-2">
                {pulse.isLoading && !IS_DEMO_MODE ? (
                  <Skeleton className="h-6 w-16" />
                ) : (
                  <span className="font-display text-[19px] font-semibold tracking-tight">
                    {k.value === undefined || k.value === null
                      ? "—"
                      : typeof k.value === "number"
                        ? formatNumber(k.value)
                        : k.value}
                  </span>
                )}
              </div>
              <div className="mt-1.5 h-9">
                <Sparkline data={SPARK_PLACEHOLDER} />
              </div>
            </div>
          ))}
        </div>

        {/* Events + Audit */}
        <div className="mt-4 grid grid-cols-12 gap-4">
          <div className="frame col-span-12 lg:col-span-7">
            <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
              <div>
                <div className="text-eyebrow">Live events</div>
                <div className="font-display text-[15px]">Monitoring stream</div>
              </div>
              <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "LIVE"} />
            </div>
            <div className="p-4">
              {IS_DEMO_MODE ? (
                <ErrorState error={new (class extends Error {})()} />
              ) : events.isLoading ? (
                <Skeleton className="h-40" />
              ) : events.error ? (
                <ErrorState error={events.error} />
              ) : !events.data?.items?.length ? (
                <EmptyState title="No events yet" description="Once your backend serves traffic, events appear here in real time." />
              ) : (
                <ul className="divide-y divide-border/60">
                  {events.data.items.map((e) => (
                    <li key={e.id} className="flex items-start gap-3 py-2.5">
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                          e.severity === "critical"
                            ? "bg-destructive"
                            : e.severity === "warn"
                              ? "bg-warn"
                              : "bg-info"
                        }`}
                      />
                      <div className="flex-1">
                        <div className="text-[12.5px]">{e.message}</div>
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
                <div className="text-eyebrow">Audit trail · tamper-evident</div>
                <div className="font-display text-[15px]">Hash-chained</div>
              </div>
              <Chip tone="success" icon={<ShieldCheck className="h-3 w-3" />}>verified</Chip>
            </div>
            <div className="p-4">
              {IS_DEMO_MODE ? (
                <ErrorState error={new (class extends Error {})()} />
              ) : audits.isLoading ? (
                <Skeleton className="h-40" />
              ) : audits.error ? (
                <ErrorState error={audits.error} />
              ) : !audits.data?.items?.length ? (
                <EmptyState title="No audit entries yet" />
              ) : (
                <div className="divide-y divide-border/60">
                  {audits.data.items.map((a) => (
                    <div key={a.id} className="py-2.5 text-[12px]">
                      <div className="flex items-center justify-between">
                        <span className="font-mono">{a.operation_type}</span>
                        <span className="font-mono text-[10.5px] text-muted-foreground">
                          {formatRelative(a.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span className="truncate">
                          {a.provider} · {a.model}
                        </span>
                        <span className="font-mono inline-flex items-center gap-1">
                          <FileLock2 className="h-3 w-3" />
                          {trimHash(a.log_hash)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="border-t border-border/70 px-4 py-2 text-[11px] text-muted-foreground flex items-center justify-end">
              <a
                href="#/monitoring"
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                Open audit logs <ArrowUpRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </div>
      </PageBody>
    </>
  );
}
