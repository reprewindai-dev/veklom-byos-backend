"use client";

import Shell from "@/components/Shell";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Button, Skeleton, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { TIER_LABEL, normalizeTier } from "@/lib/tiers";
import { useState } from "react";

export default function SubscriptionsPage() {
  const plans = useApi<any>("/api/v1/subscriptions/plans");
  const current = useApi<any>("/api/v1/subscriptions/current");
  const { tier } = useAuth();
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
            return (
              <Card key={p.id || p.name} className={isCurrent ? "border-brand-500" : ""}>
                <div className="text-[11px] uppercase tracking-widest text-ink-400">{TIER_LABEL[t]}</div>
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
