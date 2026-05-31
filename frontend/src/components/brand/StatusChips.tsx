import { ReactNode } from "react";
import { Activity, Cloud, Lock, ShieldCheck, Server, AlertTriangle, CircleDashed, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export type Tone = "neutral" | "success" | "warn" | "info" | "primary" | "danger" | "muted";

const toneClasses: Record<Tone, string> = {
  neutral: "border-border/70 bg-background/60 text-foreground/85",
  success: "border-success/30 bg-success/10 text-success",
  warn: "border-warn/30 bg-warn/10 text-warn",
  info: "border-info/30 bg-info/10 text-info",
  primary: "border-primary/40 bg-primary/10 text-primary",
  danger: "border-destructive/30 bg-destructive/10 text-destructive",
  muted: "border-border/60 bg-muted/40 text-muted-foreground",
};

export function Chip({
  children,
  tone = "neutral",
  icon,
  dot,
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("chip", toneClasses[tone], className)}>
      {dot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full", {
            "bg-success": tone === "success",
            "bg-warn": tone === "warn",
            "bg-destructive": tone === "danger",
            "bg-info": tone === "info",
            "bg-primary": tone === "primary",
            "bg-muted-foreground": tone === "muted" || tone === "neutral",
          })}
        />
      )}
      {icon}
      {children}
    </span>
  );
}

export function LiveBadge({ label = "LIVE" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-success">
      <span className="live-dot" />
      {label}
    </span>
  );
}

export function RouteChip({ route }: { route?: string }) {
  const map: Record<string, { label: string; icon: ReactNode; tone: Tone }> = {
    hetzner: { label: "Hetzner · Primary", icon: <Server className="h-3 w-3" />, tone: "primary" },
    "aws-burst": { label: "AWS · Burst", icon: <Cloud className="h-3 w-3" />, tone: "info" },
    edge: { label: "Edge", icon: <Zap className="h-3 w-3" />, tone: "warn" },
    local: { label: "Local · Air-gapped", icon: <Lock className="h-3 w-3" />, tone: "neutral" },
  };
  const cfg = map[route ?? ""] ?? { label: route ?? "—", icon: <Server className="h-3 w-3" />, tone: "muted" as Tone };
  return <Chip tone={cfg.tone} icon={cfg.icon}>{cfg.label}</Chip>;
}

export function ComplianceTag({ tag }: { tag: string }) {
  const tone: Tone = tag === "PHI" || tag === "PII" ? "warn" : tag === "Standard" ? "muted" : "primary";
  return <Chip tone={tone} icon={<ShieldCheck className="h-3 w-3" />}>{tag}</Chip>;
}

export function LatencyChip({ ms, p }: { ms: number; p?: "p50" | "p95" | "p99" }) {
  const tone: Tone = ms < 250 ? "success" : ms < 700 ? "warn" : "danger";
  return (
    <Chip tone={tone} icon={<Activity className="h-3 w-3" />}>
      {p ? `${p.toUpperCase()} ` : ""}
      {ms} ms
    </Chip>
  );
}

export function CostChip({ usd, label = "spent" }: { usd: number; label?: string }) {
  return (
    <Chip tone="neutral">
      <span className="text-foreground">${usd.toFixed(usd < 1 ? 4 : 2)}</span>
      <span className="text-muted-foreground">{label}</span>
    </Chip>
  );
}

export function HealthChip({ status }: { status: "healthy" | "degraded" | "down" | string }) {
  const map: Record<string, { tone: Tone; icon: ReactNode; label: string }> = {
    healthy: { tone: "success", icon: <ShieldCheck className="h-3 w-3" />, label: "Healthy" },
    degraded: { tone: "warn", icon: <AlertTriangle className="h-3 w-3" />, label: "Degraded" },
    down: { tone: "danger", icon: <CircleDashed className="h-3 w-3" />, label: "Down" },
  };
  const c = map[status] ?? { tone: "muted" as Tone, icon: <CircleDashed className="h-3 w-3" />, label: status };
  return <Chip tone={c.tone} icon={c.icon} dot>{c.label}</Chip>;
}
