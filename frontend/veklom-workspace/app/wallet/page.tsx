"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, StatCard, Table, Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { unwrapList } from "@/types/api";
import { useState } from "react";

export default function WalletPage() {
  const balance = useApi<any>("/api/v1/wallet/balance");
  const tx = useApi<any>("/api/v1/wallet/transactions");
  const usage = useApi<any>("/api/v1/wallet/stats/usage");
  const options = useApi<any>("/api/v1/wallet/topup/options");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function topup(amount?: number) {
    setBusy(true); setErr(undefined);
    try {
      const res = await api<any>("/api/v1/wallet/topup/checkout", { body: { amount } });
      if (res?.url) window.location.href = res.url;
    } catch (e) {
      setErr((e as Error).message);
    } finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="starter" feature="Token Wallet">
        <PageHeader
          title="Token Wallet"
          subtitle="Track balance, top-ups, and per-endpoint consumption."
          actions={<Button onClick={() => topup()} disabled={busy}>{busy ? "Loading…" : "Top up"}</Button>}
        />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard label="Balance" value={balance.isLoading ? <Skeleton className="h-8 w-24" /> : (balance.data?.balance ?? balance.data?.tokens ?? "—")} hint={balance.data?.currency || "tokens"} accent="text-brand-400" />
          <StatCard label="Spent (30d)" value={usage.data?.last_30d ?? usage.data?.spent_30d ?? "—"} />
          <StatCard label="Avg/day" value={usage.data?.avg_per_day ?? "—"} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card>
            <div className="text-sm font-medium mb-3">Top-up options</div>
            <div className="space-y-2">
              {unwrapList<any>(options.data).slice(0, 6).map((o, i) => (
                <button key={i} onClick={() => topup(o.amount || o.tokens)}
                  className="w-full text-left px-3 py-2 rounded-md bg-bg-700 hover:bg-bg-600 text-sm flex justify-between">
                  <span>{o.label || `${o.tokens || o.amount} tokens`}</span>
                  <span className="text-ink-400">{o.price ? `$${o.price}` : ""}</span>
                </button>
              ))}
              {unwrapList(options.data).length === 0 && <div className="text-ink-400 text-sm">No options configured</div>}
            </div>
          </Card>
          <Card className="lg:col-span-2 p-0">
            <div className="p-5 pb-3 text-sm font-medium">Recent transactions</div>
            <Table
              rows={unwrapList<any>(tx.data).slice(0, 50)}
              rowKey={(r) => r.id || JSON.stringify(r).slice(0, 32)}
              empty="No transactions"
              columns={[
                { key: "ts", header: "Time", render: (r) => <span className="text-ink-400">{r.ts || r.created_at}</span> },
                { key: "type", header: "Type", render: (r) => r.type || r.kind },
                { key: "amount", header: "Amount", render: (r) => <span className={r.amount < 0 ? "text-accent-red" : "text-accent-green"}>{r.amount ?? r.tokens}</span> },
                { key: "ref", header: "Reference", render: (r) => <span className="text-ink-400">{r.reference || r.endpoint || "—"}</span> },
              ]}
            />
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
