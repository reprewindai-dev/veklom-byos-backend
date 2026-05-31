import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Send, Sparkles, RotateCcw, Cpu, ShieldCheck, FileLock2, Wallet, Copy } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Chip, LiveBadge, LatencyChip, CostChip, RouteChip } from "@/components/brand/StatusChips";
import { ErrorState } from "@/components/data/States";
import { aiApi, billingApi } from "@/api";
import type { AIModelEntry } from "@/api/ai";
import { useToast } from "@/hooks/useToast";
import { IS_DEMO_MODE } from "@/lib/env";
import { formatNumber, formatUSD } from "@/lib/format";
import { cn } from "@/lib/utils";

type Msg = {
  role: "user" | "assistant";
  content: string;
  latency?: number;
  tokens?: number;
  cost?: number;
  model?: string;
  ts?: string;
};

export default function Playground() {
  const { toast } = useToast();

  const modelsQ = useQuery({
    queryKey: ["ai/models"],
    queryFn: () => aiApi.models(),
    enabled: !IS_DEMO_MODE,
  });
  const walletQ = useQuery({
    queryKey: ["wallet/balance"],
    queryFn: () => billingApi.wallet.balance(),
    enabled: !IS_DEMO_MODE,
    refetchInterval: 60_000,
  });

  const models: AIModelEntry[] = modelsQ.data?.models ?? [];
  const [activeModelId, setActiveModelId] = useState<string>("");
  useEffect(() => {
    if (!activeModelId && models.length > 0) setActiveModelId(models[0].id);
  }, [models, activeModelId]);
  const activeModel = models.find((m) => m.id === activeModelId);

  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [maxTokens, setMaxTokens] = useState(1024);

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const sessionCost = useMemo(() => messages.reduce((s, m) => s + (m.cost ?? 0), 0), [messages]);

  async function send() {
    if (!input.trim() || !activeModel) return;
    if (IS_DEMO_MODE) {
      toast({
        title: "Demo mode",
        description: "Configure VITE_VEKLOM_API_BASE to run real inference.",
        variant: "warn",
      });
      return;
    }
    const userMsg: Msg = { role: "user", content: input, ts: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setBusy(true);
    const startedAt = performance.now();
    try {
      const res = await aiApi.complete({
        model: activeModel.id,
        prompt: input,
        max_tokens: maxTokens,
      });
      const latency = Math.round(performance.now() - startedAt);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.response_text,
          latency,
          tokens: res.output_tokens,
          cost: res.tokens_deducted * 0.0001,
          model: res.model,
          ts: res.timestamp,
        },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Inference failed";
      toast({ title: "Inference failed", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Workspace · Playground"
        title="Playground"
        subtitle="Production-grade prompt theater. Every call routes through your policy engine, charges the token wallet, and writes a signed audit entry."
        meta={
          <>
            <LiveBadge label={IS_DEMO_MODE ? "DEMO" : "POLICY ENGINE LIVE"} />
            {activeModel && <Chip tone="primary" icon={<Cpu className="h-3 w-3" />}>{activeModel.name}</Chip>}
            <CostChip usd={sessionCost} label={`session · ${messages.length} msg`} />
            {walletQ.data && (
              <Chip tone="info" icon={<Wallet className="h-3 w-3" />}>
                wallet · {formatNumber(walletQ.data.balance)} tokens
              </Chip>
            )}
            <Chip tone="success" icon={<ShieldCheck className="h-3 w-3" />}>policy: standard</Chip>
            <Chip tone="muted" icon={<FileLock2 className="h-3 w-3" />}>audit: signed</Chip>
          </>
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setMessages([])}>
              <RotateCcw className="h-3.5 w-3.5" />
              Clear
            </Button>
          </>
        }
      />

      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            {/* Conversation */}
            <section className="frame col-span-12 xl:col-span-9 overflow-hidden">
              <div
                ref={scrollRef}
                className="max-h-[58vh] min-h-[420px] space-y-4 overflow-y-auto px-5 py-5"
              >
                {modelsQ.isLoading && <Skeleton className="h-32" />}
                {modelsQ.error && <ErrorState error={modelsQ.error} />}
                {!modelsQ.isLoading && messages.length === 0 && (
                  <div className="rounded-md border border-dashed border-border/60 bg-muted/20 px-4 py-6 text-center">
                    <p className="text-[13px] text-muted-foreground">
                      Connected to <strong className="text-foreground">{activeModel?.name ?? "—"}</strong>. Ask anything — every prompt is
                      policed before any model is called.
                    </p>
                  </div>
                )}
                {messages.map((m, i) => (
                  <Bubble key={i} m={m} />
                ))}
                {busy && <Bubble m={{ role: "assistant", content: "▌" }} pulsing />}
              </div>

              {/* Composer */}
              <div className="border-t border-border/70 bg-card/50 p-3">
                <div className="rounded-lg border bg-background/40 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/30">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
                    }}
                    placeholder="Ask anything. ⌘/Ctrl + Enter to send…"
                    className="min-h-[88px] resize-none border-0 bg-transparent text-[13px] shadow-none focus-visible:ring-0"
                  />
                  <div className="flex items-center justify-between border-t border-border/60 px-3 py-2">
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="font-mono">~{Math.ceil(input.length / 4) || 0} tok in</span>
                      <span>·</span>
                      <span>
                        max tokens:{" "}
                        <input
                          type="number"
                          min={1}
                          max={8192}
                          value={maxTokens}
                          onChange={(e) => setMaxTokens(parseInt(e.target.value || "1024", 10))}
                          className="w-16 rounded border bg-transparent px-1 py-0.5 font-mono text-[11px]"
                        />
                      </span>
                    </div>
                    <Button size="sm" onClick={send} disabled={busy || !input.trim() || !activeModel}>
                      <Send className="h-3.5 w-3.5" /> {busy ? "Generating…" : "Send"}
                    </Button>
                  </div>
                </div>
              </div>
            </section>

            {/* Sidebar */}
            <aside className="col-span-12 xl:col-span-3 space-y-3">
              <div className="frame p-3">
                <div className="text-eyebrow mb-2 flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5" /> Model
                </div>
                {modelsQ.isLoading ? (
                  <Skeleton className="h-9" />
                ) : models.length === 0 ? (
                  <div className="text-[11.5px] text-muted-foreground">
                    No models exposed by <code className="font-mono">/api/v1/ai/models</code>.
                  </div>
                ) : (
                  <select
                    value={activeModelId}
                    onChange={(e) => setActiveModelId(e.target.value)}
                    className="h-9 w-full rounded-md border border-input bg-card/60 px-2 text-[12px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} {m.provider ? `· ${m.provider}` : ""}
                      </option>
                    ))}
                  </select>
                )}
                {activeModel && (
                  <div className="mt-3 grid grid-cols-2 gap-1.5 text-[10.5px]">
                    {activeModel.context && (
                      <Stat label="Context" v={`${Math.round(activeModel.context / 1000)}K`} />
                    )}
                    {activeModel.modality && <Stat label="Modality" v={activeModel.modality} />}
                    {activeModel.pricing?.input != null && (
                      <Stat label="In $/1K" v={formatUSD(activeModel.pricing.input * 1000)} />
                    )}
                    {activeModel.pricing?.output != null && (
                      <Stat label="Out $/1K" v={formatUSD(activeModel.pricing.output * 1000)} />
                    )}
                  </div>
                )}
              </div>

              <div className="frame p-3">
                <div className="text-eyebrow mb-2 flex items-center gap-1.5">
                  <Wallet className="h-3.5 w-3.5" /> Wallet
                </div>
                {walletQ.isLoading ? (
                  <Skeleton className="h-6" />
                ) : walletQ.data ? (
                  <div>
                    <div className="font-display text-[16px] font-semibold">
                      {formatNumber(walletQ.data.balance)} <span className="text-[11px] text-muted-foreground">tokens</span>
                    </div>
                    <div className="mt-1 text-[10.5px] text-muted-foreground font-mono">
                      used: {formatNumber(walletQ.data.total_used ?? 0)} · topped:{" "}
                      {formatNumber(walletQ.data.total_topped_up ?? 0)}
                    </div>
                  </div>
                ) : (
                  <div className="text-[11.5px] text-muted-foreground">No wallet data.</div>
                )}
              </div>

              <div className="frame p-3">
                <div className="text-eyebrow mb-1">Routing</div>
                <RouteChip route="hetzner" />
                <p className="mt-2 text-[10.5px] leading-snug text-muted-foreground">
                  Every prompt is route-classified by the deterministic substrate before any model is called.
                </p>
              </div>
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}

function Stat({ label, v }: { label: string; v: string }) {
  return (
    <div className="rounded-md border bg-background/40 px-2 py-1">
      <div className="text-eyebrow">{label}</div>
      <div className="font-mono text-[11.5px] text-foreground">{v}</div>
    </div>
  );
}

function Bubble({ m, pulsing }: { m: Msg; pulsing?: boolean }) {
  const isUser = m.role === "user";
  return (
    <div className={cn("flex items-start gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-primary/15 text-primary">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
      )}
      <div className={cn("max-w-[78%] flex-1", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl border px-4 py-3 text-[13px] leading-relaxed whitespace-pre-wrap",
            isUser ? "border-primary/30 bg-primary/10 text-foreground" : "border-border/70 bg-card/60",
            pulsing && "animate-pulse",
          )}
        >
          {m.content}
        </div>
        {!isUser && (m.latency || m.tokens || m.cost) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {m.latency != null && <LatencyChip ms={m.latency} />}
            {m.tokens != null && <Chip tone="muted">{m.tokens} tok</Chip>}
            {m.cost != null && <CostChip usd={m.cost} label="run" />}
            <Chip tone="success" icon={<ShieldCheck className="h-3 w-3" />}>policy passed</Chip>
            <button
              onClick={() => navigator.clipboard?.writeText(m.content)}
              className="ml-auto inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
            >
              <Copy className="h-3 w-3" /> copy
            </button>
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-foreground/10 font-display text-[10px] font-semibold text-foreground">
          YOU
        </div>
      )}
    </div>
  );
}
