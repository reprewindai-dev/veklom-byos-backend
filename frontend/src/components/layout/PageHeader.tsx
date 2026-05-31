import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  meta,
  className,
}: {
  eyebrow?: ReactNode;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("border-b border-border/70 px-6 pt-6 pb-5 lg:px-8", className)}>
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          {eyebrow && <div className="text-eyebrow mb-2">{eyebrow}</div>}
          <h1 className="font-display text-[22px] font-semibold tracking-tight text-foreground">{title}</h1>
          {subtitle && (
            <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-muted-foreground">{subtitle}</p>
          )}
          {meta && <div className="mt-3 flex flex-wrap items-center gap-2">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function PageBody({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("mx-auto max-w-[1400px] px-6 py-6 lg:px-8", className)}>{children}</div>
  );
}
