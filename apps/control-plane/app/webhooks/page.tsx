"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { Card, PageHeader, Button } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";

export default function WebhooksPage() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>();

  async function test() {
    setBusy(true);
    try { setResult(await api<any>("/api/v1/webhooks/test", { body: { event: "ping" } })); }
    finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Webhooks">
        <PageHeader title="Webhooks" subtitle="Outgoing alert and event webhooks. Inbound endpoints for GitHub, Stripe, Resend." actions={
          <Button onClick={test} disabled={busy}>Send test event</Button>
        } />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">GitHub</div><code className="text-xs block mt-2 break-all">/api/v1/webhooks/github</code></Card>
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">Stripe</div><code className="text-xs block mt-2 break-all">/api/v1/webhooks/stripe</code></Card>
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">Resend</div><code className="text-xs block mt-2 break-all">/api/v1/webhooks/resend</code></Card>
        </div>
        {result && <Card><pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(result, null, 2)}</pre></Card>}
      </TierGate>
    </Shell>
  );
}
