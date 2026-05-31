import { cn } from "@/lib/utils";

export function VeklomLogo({
  className,
  withWordmark = true,
  showTagline = true,
}: {
  className?: string;
  withWordmark?: boolean;
  showTagline?: boolean;
}) {
  return (
    <div className={cn("inline-flex items-center gap-2.5", className)} aria-label="Veklom">
      <svg viewBox="0 0 32 32" className="h-7 w-7 shrink-0" fill="none" aria-hidden="true">
        <rect
          x="0.5"
          y="0.5"
          width="31"
          height="31"
          rx="7.5"
          className="stroke-foreground/15"
          fill="hsl(var(--background))"
        />
        <path
          d="M9 9 L16 22.5 L23 9"
          className="stroke-primary"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="16" r="1.6" className="fill-primary" />
      </svg>
      {withWordmark && (
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="font-display text-[15px] font-semibold tracking-tight">Veklom</span>
          {showTagline && (
            <span className="hidden lg:inline text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground whitespace-nowrap">
              Sovereign Control Node
            </span>
          )}
        </div>
      )}
    </div>
  );
}
