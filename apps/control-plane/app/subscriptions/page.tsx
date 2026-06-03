"use client";

import Shell from "@/components/Shell";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Button, Skeleton, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { TIER_LABEL, normalizeTier } from "@/lib/tiers";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function SubscriptionsContent() {
  const plans = useApi<any>("/api/v1/subscriptions/plans");
  const current = useApi<any>("/api/v1/subscriptions/current");
  const { tier } = useAuth();
  const searchParams = useSearchParams();
  const highlightedTier = searchParams.get("tier") || undefined;
  const [busy, setBusy] = useState<string | undefined>();
  const [err, setErr] = useState<string | undefined>();

  async function checkout(planId: string) {
    setBusy(planId); setErr(undefined);
    try {
      const res = await api<any>("/api/v1/subscriptions/checkout", { body: { plan_id: planId } });
      if (res?.url) window.location.href = res.url;
    } catch (e) { setErr((e as Error).message); } finally { setBusy(undefined); }
  }
  async function portal() {
    const res = await api<any>("/api/v1/subscriptions/portal", { method: "POST" });
    if (res?.url) window.location.href = res.url;
  }

  return (
    <Shell>
      <PageHeader
        title="Subscription"
        subtitle={`Currently on ${TIER_LABEL[tier]}. Upgrade to unlock more of the control plane.`}
        actions={current.data?.plan ? <Button variant="ghost" onClick={portal}>Manage in Stripe</Button> : null}
      />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {plans.isLoading ? <Skeleton className="h-64 w-full" /> :
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {unwrapList<any>(plans.data).map((p) => {
            const t = normalizeTier(p.tier || p.id || p.name);
            const isCurrent = t === tier;
            const isHighlighted = t === highlightedTier;
            
            return (
              <Card 
                key={p.id || p.name} 
                className={
                  isCurrent 
                    ? "border-brand-500 ring-1 ring-brand-500/20" 
                    : isHighlighted 
                      ? "border-accent-amber ring-2 ring-accent-amber/50 scale-[1.02] shadow-lg shadow-accent-amber/5 transition-all duration-300" 
                      : "transition-all duration-300"
                }
              >
                <div className="text-[11px] uppercase tracking-widest text-ink-400">
                  {TIER_LABEL[t]}
                  {isHighlighted && <span className="ml-2 text-accent-amber font-semibold text-[9px] px-1.5 py-0.5 rounded bg-accent-amber/10 border border-accent-amber/20">Recommended</span>}
                </div>
                <div className="text-2xl font-semibold mt-1">{p.price_label || (p.price ? `$${p.price}` : "—")}</div>
                <div className="text-xs text-ink-400 mt-1">{p.period || "month"}</div>
                <ul className="mt-4 space-y-1 text-xs text-ink-200">
                  {(p.features || p.bullets || []).slice(0, 6).map((f: string, i: number) => <li key={i}>• {f}</li>)}
                </ul>
                <div className="mt-5">
                  {isCurrent ? <Button variant="ghost" disabled>Current plan</Button>
                    : <Button onClick={() => checkout(p.id || p.plan_id)} disabled={busy === (p.id || p.plan_id)}>{busy === (p.id || p.plan_id) ? "Loading…" : "Upgrade"}</Button>}
                </div>
              </Card>
            );
          })}
          {unwrapList(plans.data).length === 0 && <Card className="col-span-full text-center py-10 text-ink-400">No plans available.</Card>}
        </div>
      }
    </Shell>
  );
}

export default function SubscriptionsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen grid place-items-center text-ink-400">Loading…</div>}>
      <SubscriptionsContent />
    </Suspense>
  );
}

