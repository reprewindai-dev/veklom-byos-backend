"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { Card, PageHeader, Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";

export default function VendorOnboardingPage() {
  const me = useApi<any>("/api/v1/vendors/me/listings");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();
  const [form, setForm] = useState({ name: "", website: "", contact_email: "" });

  async function onboard() {
    setBusy(true); setErr(undefined);
    try {
      await api("/api/v1/vendors/onboard", { body: form });
      me.mutate();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="starter" feature="Vendor Onboarding">
        <PageHeader title="Vendor Onboarding" subtitle="Register as a marketplace vendor and start submitting listings." />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <Card className="max-w-xl">
          <div className="space-y-3">
            <Field label="Company name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
            <Field label="Website" value={form.website} onChange={(v) => setForm({ ...form, website: v })} />
            <Field label="Contact email" value={form.contact_email} onChange={(v) => setForm({ ...form, contact_email: v })} />
          </div>
          <div className="mt-4 flex justify-end"><Button onClick={onboard} disabled={busy}>{busy ? "Submitting…" : "Submit"}</Button></div>
        </Card>
      </TierGate>
    </Shell>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-xs text-ink-400">{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500" />
    </div>
  );
}
