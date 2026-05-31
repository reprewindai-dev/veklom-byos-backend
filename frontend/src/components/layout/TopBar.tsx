import { useQuery } from "@tanstack/react-query";
import { Bell, BookOpen, Database, KeyRound, Layers, LogOut, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Chip, HealthChip } from "@/components/brand/StatusChips";
import { monitoringApi } from "@/api";
import { IS_DEMO_MODE, WORKSPACE_LABEL } from "@/lib/env";
import { useAuth } from "@/hooks/useAuth";

export function TopBar() {
  const { user, authenticated, logout } = useAuth();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => monitoringApi.health(),
    enabled: !IS_DEMO_MODE,
    refetchInterval: 30_000,
  });

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border/80 bg-background/85 px-5 backdrop-blur-md">
      <div className="flex items-center gap-2 whitespace-nowrap">
        <Chip tone="muted" icon={<Layers className="h-3 w-3" />}>
          {WORKSPACE_LABEL}
        </Chip>
        {health.data?.version && <Chip tone="muted">v{health.data.version}</Chip>}
      </div>

      <div className="ml-2 hidden md:flex items-center gap-2 rounded-md border bg-muted/40 px-2.5 py-1">
        <Search className="h-3.5 w-3.5 text-muted-foreground" />
        <input
          className="w-72 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
          placeholder="Jump to model, deployment, log, or doc…"
          aria-label="Search"
        />
        <kbd className="hidden lg:inline rounded border border-border/60 bg-background/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </div>

      <div className="ml-auto flex items-center gap-2">
        {!IS_DEMO_MODE && (
          <HealthChip
            status={
              health.isLoading ? "degraded" : health.data?.status === "ok" || health.data?.status === "healthy" ? "healthy" : "down"
            }
          />
        )}
        <Chip tone="info" icon={<Database className="h-3 w-3" />}>
          EU-sovereign
        </Chip>
        <Button size="sm" variant="ghost" className="h-8 px-2" asChild>
          <a href="https://github.com/reprewindai-dev/veklom-byos-backend#readme" target="_blank" rel="noreferrer">
            <BookOpen className="h-4 w-4" />
          </a>
        </Button>
        <Button size="sm" variant="ghost" className="h-8 px-2">
          <KeyRound className="h-4 w-4" />
        </Button>
        <Button size="sm" variant="ghost" className="h-8 px-2">
          <Bell className="h-4 w-4" />
        </Button>
        {authenticated && (
          <div className="flex items-center gap-2">
            <span className="hidden md:inline text-[12px] text-muted-foreground">
              {user?.email ?? "signed in"}
            </span>
            <Button size="sm" variant="ghost" className="h-8 px-2" onClick={() => void logout()} title="Sign out">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
