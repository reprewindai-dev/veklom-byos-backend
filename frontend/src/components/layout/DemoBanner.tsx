import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { IS_DEMO_MODE } from "@/lib/env";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "veklom_demo_banner_dismissed";

export function DemoBanner() {
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => {
    try {
      setDismissed(sessionStorage.getItem(STORAGE_KEY) === "1");
    } catch { /* noop */ }
  }, []);

  if (!IS_DEMO_MODE || dismissed) return null;
  return (
    <div className={cn(
      "border-b border-warn/30 bg-warn/10 px-4 py-2 text-[12.5px] text-foreground",
      "flex items-center justify-between gap-3",
    )}>
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-warn" />
        <span>
          <strong className="font-semibold text-warn">Demo mode.</strong>{" "}
          The dashboard is not wired to a backend yet. Set{" "}
          <code className="rounded bg-background/60 px-1 py-0.5 font-mono text-[11px]">
            VITE_VEKLOM_API_BASE
          </code>{" "}
          to your{" "}
          <a
            href="https://github.com/reprewindai-dev/veklom-byos-backend"
            target="_blank"
            rel="noreferrer"
            className="text-primary underline-offset-4 hover:underline"
          >
            veklom-byos-backend
          </a>{" "}
          URL and rebuild.
        </span>
      </div>
      <button
        onClick={() => {
          try { sessionStorage.setItem(STORAGE_KEY, "1"); } catch { /* noop */ }
          setDismissed(true);
        }}
        className="hover-elevate rounded-md p-1 text-muted-foreground"
        aria-label="Dismiss banner"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
