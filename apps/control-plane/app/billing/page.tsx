"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";

export default function BillingPage() {
  const invoices = useApi<any>("/api/v1/billing/invoices");
  const breakdown = useApi<any>("/api/v1/billing/breakdown");

  async function portal() {
    const res = await api<any>("/api/v1/subscriptions/portal", { method: "POST" });
    if (res?.url) window.location.href = res.url;
  }

  return (
    <Shell>
      <TierGate required="starter" feature="Billing">
        <PageHeader title="Billing" subtitle="Invoices, allocation, and Stripe portal access." actions={
          <Button onClick={portal}>Open billing portal</Button>
        } />
        <Card className="p-0 mb-4">
          <div className="p-5 pb-3 text-sm font-medium">Invoices</div>
          {invoices.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(invoices.data)}
              rowKey={(r) => r.id || r.invoice_id}
              empty="No invoices"
              columns={[
                { key: "id", header: "Invoice", render: (r) => <span className="font-mono text-xs">{r.id || r.invoice_id}</span> },
                { key: "date", header: "Date", render: (r) => r.date || r.created_at },
                { key: "amount", header: "Amount", render: (r) => `$${r.amount ?? r.total ?? "0"}` },
                { key: "status", header: "Status", render: (r) => r.status },
                { key: "pdf", header: "", render: (r) => {
                  const url = r.invoice_pdf || r.hosted_invoice_url || r.pdf_url;
                  return url ? <a className="text-brand-400 hover:underline text-xs" href={url} target="_blank" rel="noreferrer">PDF</a> : null;
                }, width: "80px" },
              ]}
            />
          }
        </Card>
        <Card>
          <div className="text-sm font-medium mb-3">Breakdown</div>
          <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(breakdown.data, null, 2)}</pre>
        </Card>
      </TierGate>
    </Shell>
  );
}
