import { type ReactNode } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { IS_DEMO_MODE } from "@/lib/env";
import { NoBackendError } from "@/lib/http";

export function LoadingState({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 text-muted-foreground text-[12px]", className)}>
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("frame-quiet p-8 text-center", className)}>
      <div className="font-display text-[14px] font-semibold">{title}</div>
      {description && (
        <div className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{description}</div>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({
  error,
  className,
  hint,
}: {
  error: unknown;
  className?: string;
  hint?: string;
}) {
  if (error instanceof NoBackendError || IS_DEMO_MODE) {
    return (
      <EmptyState
        title="Backend not wired"
        description={
          <>
            This page reads live data from your veklom-byos-backend. Set{" "}
            <code className="rounded bg-background/60 px-1 py-0.5 font-mono text-[11px]">
              VITE_VEKLOM_API_BASE
            </code>{" "}
            to your backend URL to enable.
          </>
        }
        className={className}
      />
    );
  }
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className={cn("frame border-destructive/30 bg-destructive/5 p-4 text-[12.5px]", className)}>
      <div className="flex items-center gap-2 text-destructive font-medium">
        <AlertTriangle className="h-4 w-4" />
        Request failed
      </div>
      <div className="mt-1 font-mono text-[11.5px] text-muted-foreground">{message}</div>
      {hint && <div className="mt-2 text-[11.5px] text-muted-foreground">{hint}</div>}
    </div>
  );
}
