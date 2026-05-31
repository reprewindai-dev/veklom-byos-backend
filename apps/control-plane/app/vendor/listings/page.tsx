"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function VendorListingsPage() {
  const listings = useApi<any>("/api/v1/vendors/me/listings");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function newListing() {
    const name = prompt("Listing name:");
    if (!name) return;
    setBusy(true); setErr(undefined);
    try { await api("/api/v1/listings/create", { body: { name } }); listings.mutate(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function submit(id: string) {
    if (!confirm("Submit for compliance review?")) return;
    await api("/api/v1/listings/submit", { body: { listing_id: id } });
    listings.mutate();
  }

  return (
    <Shell>
      <TierGate required="starter" feature="My Listings">
        <PageHeader title="My Listings" subtitle="Create, submit, and track marketplace listings." actions={
          <Button onClick={newListing} disabled={busy}>New listing</Button>
        } />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <Card className="p-0">
          {listings.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table rows={unwrapList<any>(listings.data)} rowKey={(r) => r.id || r.listing_id} empty="No listings yet" columns={[
              { key: "name", header: "Listing", render: (r) => r.name || r.title },
              { key: "status", header: "Status", render: (r) => r.status },
              { key: "compliance", header: "Compliance", render: (r) => r.compliance_status || "—" },
              { key: "installs", header: "Installs", render: (r) => r.installs ?? 0 },
              { key: "actions", header: "", render: (r) => r.status !== "submitted" ? <Button variant="ghost" onClick={() => submit(r.id || r.listing_id)}>Submit</Button> : null, width: "120px" },
            ]} />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
