import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Terminal as TerminalIcon, Play } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/data/States";
import { commandCenterApi } from "@/api";
import type { TerminalDescriptor, TerminalEndpoint } from "@/api/commandCenter";
import { http, HttpError } from "@/lib/http";
import { IS_DEMO_MODE, API_BASE } from "@/lib/env";

/**
 * GPC / Quantum Terminal.
 *
 * The backend exposes two **allowlist** terminals:
 *   - /api/v1/command-center/terminals/veklom   (Veklom Runtime — health, pulse, gpc, audit, ...)
 *   - /api/v1/command-center/terminals/quantum  (UACP Quantum — uacp.summary/events/runs/...)
 *
 * Both endpoints describe the routes a terminal command can dispatch.
 * The terminal frontend MUST refuse any command not present in the allowlist.
 * This screen mirrors that contract exactly.
 */

type Bus = "veklom" | "quantum";

type ResultLine =
  | { kind: "prompt"; text: string }
  | { kind: "ok"; body: string }
  | { kind: "err"; body: string }
  | { kind: "info"; body: string };

export default function GpcTerminal() {
  const veklom = useQuery({
    queryKey: ["cc/terminals/veklom"],
    queryFn: () => commandCenterApi.terminals.veklom(),
    enabled: !IS_DEMO_MODE,
  });
  const quantum = useQuery({
    queryKey: ["cc/terminals/quantum"],
    queryFn: () => commandCenterApi.terminals.quantum(),
    enabled: !IS_DEMO_MODE,
  });

  const [bus, setBus] = useState<Bus>("veklom");
  const active: TerminalDescriptor | undefined = bus === "veklom" ? veklom.data : quantum.data;

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lines, setLines] = useState<ResultLine[]>([
    { kind: "info", body: "Veklom Sovereign Terminal · type `help` to list allowed commands" },
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [lines, busy]);

  const commandIndex = useMemo(() => {
    const m = new Map<string, TerminalEndpoint>();
    for (const ep of active?.endpoints ?? []) m.set(ep.label, ep);
    return m;
  }, [active]);

  async function run(raw: string) {
    const cmd = raw.trim();
    if (!cmd) return;
    setLines((prev) => [...prev, { kind: "prompt", text: `${bus}$ ${cmd}` }]);

    if (cmd === "help" || cmd === "?" || cmd === "ls") {
      const list = (active?.endpoints ?? []).map((e) => `  ${e.label.padEnd(28)}  ${e.method}  ${e.path}`).join("\n");
      setLines((prev) => [
        ...prev,
        { kind: "info", body: `Allowed commands on ${active?.name ?? bus}:\n${list || "(none)"}` },
      ]);
      return;
    }
    if (cmd === "clear" || cmd === "cls") {
      setLines([{ kind: "info", body: "cleared" }]);
      return;
    }
    if (cmd === "whoami") {
      setLines((prev) => [
        ...prev,
        { kind: "info", body: `terminal: ${active?.name} v${active?.version} · auth: ${active?.auth_required ? "required" : "open"} · backend: ${API_BASE || "(unconfigured)"}` },
      ]);
      return;
    }
    if (cmd.startsWith("switch ")) {
      const target = cmd.slice(7).trim();
      if (target === "veklom" || target === "quantum") {
        setBus(target);
        setLines((prev) => [...prev, { kind: "info", body: `switched to ${target}` }]);
      } else {
        setLines((prev) => [...prev, { kind: "err", body: `unknown bus '${target}'. Use 'switch veklom' or 'switch quantum'.` }]);
      }
      return;
    }

    const ep = commandIndex.get(cmd);
    if (!ep) {
      setLines((prev) => [
        ...prev,
        { kind: "err", body: `unauthorized command '${cmd}'. The ${active?.name} allowlist does not include this label.\nType 'help' to list valid commands.` },
      ]);
      return;
    }

    setBusy(true);
    try {
      const method = ep.method.toLowerCase() as "get" | "post" | "put" | "patch" | "delete";
      const fn = (http as unknown as Record<string, (path: string, body?: unknown) => Promise<unknown>>)[method];
      const body = ep.method !== "GET" ? ep.body ?? {} : undefined;
      const data = await fn(ep.path, body);
      setLines((prev) => [
        ...prev,
        { kind: "ok", body: JSON.stringify(data, null, 2) },
      ]);
    } catch (err) {
      const message = err instanceof HttpError ? `${err.status}: ${err.message}` : err instanceof Error ? err.message : String(err);
      setLines((prev) => [...prev, { kind: "err", body: message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Super User · Terminal"
        title="GPC / Quantum terminal"
        subtitle="Allowlist-bound dispatch. Every command resolves to a real backend route and writes a hash-chained audit entry."
        meta={
          <>
            <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "BOUND"} />
            <Chip tone={bus === "veklom" ? "primary" : "muted"}>veklom bus</Chip>
            <Chip tone={bus === "quantum" ? "primary" : "muted"}>quantum bus</Chip>
          </>
        }
        actions={
          <>
            <Button size="sm" variant={bus === "veklom" ? "default" : "outline"} onClick={() => setBus("veklom")}>
              Veklom Runtime
            </Button>
            <Button size="sm" variant={bus === "quantum" ? "default" : "outline"} onClick={() => setBus("quantum")}>
              UACP Quantum
            </Button>
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <section className="frame col-span-12 xl:col-span-9 overflow-hidden">
              <div className="flex items-center justify-between border-b border-border/70 bg-card/60 px-4 py-2">
                <div className="flex items-center gap-2">
                  <TerminalIcon className="h-4 w-4 text-primary" />
                  <span className="font-display text-[13px] font-semibold">{active?.name ?? "Loading…"}</span>
                  {active && <Chip tone="muted">v{active.version}</Chip>}
                </div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {(active?.endpoints?.length ?? 0)} allowed commands
                </div>
              </div>
              <div
                ref={scrollRef}
                className="h-[60vh] min-h-[420px] overflow-y-auto bg-background/70 px-4 py-3 font-mono text-[12px] leading-relaxed"
              >
                {(bus === "veklom" ? veklom.isLoading : quantum.isLoading) ? (
                  <Skeleton className="h-40" />
                ) : (bus === "veklom" ? veklom.error : quantum.error) ? (
                  <ErrorState error={(bus === "veklom" ? veklom.error : quantum.error) as Error} />
                ) : (
                  lines.map((l, i) => <Line key={i} l={l} />)
                )}
                {busy && <span className="animate-pulse text-muted-foreground">…dispatching…</span>}
              </div>
              <form
                className="flex items-center gap-2 border-t border-border/70 bg-card/60 px-3 py-2"
                onSubmit={(e: React.FormEvent<HTMLFormElement>) => {
                  e.preventDefault();
                  const v = input;
                  setInput("");
                  void run(v);
                }}
              >
                <span className="font-mono text-[12px] text-primary">{bus}$</span>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="type a command — try 'help'"
                  className="flex-1 bg-transparent font-mono text-[12px] outline-none"
                  autoFocus
                  spellCheck={false}
                  autoComplete="off"
                />
                <Button type="submit" size="sm" disabled={busy || !input.trim()}>
                  <Play className="h-3.5 w-3.5" /> Run
                </Button>
              </form>
            </section>

            <aside className="col-span-12 xl:col-span-3">
              <div className="frame p-3">
                <div className="text-eyebrow mb-2">Allowed commands</div>
                {!active ? (
                  <Skeleton className="h-40" />
                ) : (
                  <ul className="space-y-1 max-h-[60vh] overflow-y-auto">
                    {active.endpoints.map((ep: TerminalEndpoint) => (
                      <li key={ep.label}>
                        <button
                          onClick={() => void run(ep.label)}
                          className="hover-elevate w-full rounded-md border bg-background/40 px-2 py-1.5 text-left text-[11px]"
                        >
                          <div className="font-mono text-foreground">{ep.label}</div>
                          <div className="font-mono text-[10px] text-muted-foreground">{ep.method} {ep.path}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}

function Line({ l }: { l: ResultLine }) {
  if (l.kind === "prompt") {
    return <div className="text-primary">{l.text}</div>;
  }
  if (l.kind === "err") {
    return (
      <pre className="my-1 whitespace-pre-wrap rounded border border-destructive/30 bg-destructive/5 px-2 py-1 text-destructive">
{l.body}
      </pre>
    );
  }
  if (l.kind === "ok") {
    return (
      <pre className="my-1 whitespace-pre-wrap rounded border border-border/60 bg-card/60 px-2 py-1 text-foreground/90">
{l.body}
      </pre>
    );
  }
  return <div className="my-1 whitespace-pre-wrap text-muted-foreground">{l.body}</div>;
}
