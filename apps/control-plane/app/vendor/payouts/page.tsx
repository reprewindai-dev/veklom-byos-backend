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
  const status = useApi<any>("/api/v1/stripe/connect/status");
  const vendorId = (me as any)?.vendor_id || (me as any)?.org_id;
  const payouts = useApi<any>(vendorId ? `/api/v1/payouts/vendor/${vendorId}` : null);
  const [busy, setBusy] = useState(false);

  const connected = !!(status.data?.connected || status.data?.charges_enabled);

  async function request() {
    if (!connected) {
      alert("Your Stripe account is not connected. Redirecting to Stripe onboarding...");
      window.location.href = "/control-plane-next/vendor/stripe";
      return;
    }
    const amountStr = prompt("Enter amount to payout:");
    if (!amountStr) return;
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
      alert("Invalid amount.");
      return;
    }
    setBusy(true);
    try { 
      await api("/api/v1/payouts/create", { body: { vendor_id: vendorId, amount } }); 
      payouts.mutate(); 
      alert("Payout request submitted successfully.");
    } catch (e) {
      alert((e as Error).message);
    } finally { 
      setBusy(false); 
    }
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
