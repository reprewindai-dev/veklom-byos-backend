"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export default function VendorPayoutsPage() {
  const { me } = useAuth();
  const vendorId = (me as any)?.vendor_id || (me as any)?.org_id;
  const payouts = useApi<any>(vendorId ? `/api/v1/payouts/vendor/${vendorId}` : null);
  const [busy, setBusy] = useState(false);

  async function request() {
    if (!confirm("Request a manual payout?")) return;
    setBusy(true);
    try { await api("/api/v1/payouts/create", { body: { vendor_id: vendorId } }); payouts.mutate(); }
    finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="starter" feature="Payouts">
        <PageHeader title="Payouts" subtitle="Stripe Connect payouts and history." actions={
          <Button onClick={request} disabled={busy || !vendorId}>{busy ? "Requesting…" : "Request payout"}</Button>
        } />
        <Card className="p-0">
          {payouts.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table rows={unwrapList<any>(payouts.data)} rowKey={(r) => r.id || r.payout_id} empty="No payouts" columns={[
              { key: "ts", header: "Date", render: (r) => <span className="text-ink-400 text-xs">{r.ts || r.created_at}</span> },
              { key: "amount", header: "Amount", render: (r) => `$${r.amount}` },
              { key: "status", header: "Status", render: (r) => r.status },
              { key: "ref", header: "Stripe", render: (r) => <code className="text-xs">{r.stripe_payout_id || "—"}</code> },
            ]} />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
