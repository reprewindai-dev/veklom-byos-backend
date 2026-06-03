"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { Card, PageHeader, Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { useRouter } from "next/navigation";
import clsx from "clsx";

export default function VendorOnboardingPage() {
  const me = useApi<any>("/api/v1/vendors/me/listings");
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();
  const [form, setForm] = useState({ name: "", website: "", contact_email: "" });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  async function onboard() {
    // Client-side validation
    const errors: Record<string, string> = {};
    if (!form.name.trim()) {
      errors.name = "Company name is required";
    }
    if (!form.website.trim()) {
      errors.website = "Website is required";
    } else if (
      !/^https?:\/\/[^\s/$.?#].[^\s]*$/i.test(form.website) &&
      !/^[^\s/$.?#].[^\s]*\.[^\s]*$/i.test(form.website)
    ) {
      errors.website = "Please enter a valid website URL (e.g. example.com)";
    }
    if (!form.contact_email.trim()) {
      errors.contact_email = "Contact email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contact_email)) {
      errors.contact_email = "Please enter a valid email address";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
    setBusy(true); 
    setErr(undefined);
    try {
      await api("/api/v1/vendors/onboard", { body: form });
      setSuccess(true);
      me.mutate();
      // Redirect after a brief moment to allow reading success feedback
      setTimeout(() => {
        router.push("/vendor/stripe/");
      }, 1500);
    } catch (e) { 
      setErr((e as Error).message); 
    } finally { 
      setBusy(false); 
    }
  }

  return (
    <Shell>
      <TierGate required="starter" feature="Vendor Onboarding">
        <PageHeader title="Vendor Onboarding" subtitle="Register as a marketplace vendor and start submitting listings." />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        {success && (
          <div className="mb-4 card p-4 border-brand-500/40 text-brand-400 text-sm bg-brand-500/10 font-medium">
            Onboarding successful! Redirecting to Stripe setup...
          </div>
        )}
        <Card className="max-w-xl">
          <div className="space-y-4">
            <Field 
              label="Company name" 
              value={form.name} 
              onChange={(v) => setForm({ ...form, name: v })} 
              error={fieldErrors.name}
            />
            <Field 
              label="Website" 
              value={form.website} 
              onChange={(v) => setForm({ ...form, website: v })} 
              error={fieldErrors.website}
            />
            <Field 
              label="Contact email" 
              value={form.contact_email} 
              onChange={(v) => setForm({ ...form, contact_email: v })} 
              error={fieldErrors.contact_email}
            />
          </div>
          <div className="mt-6 flex justify-end">
            <Button onClick={onboard} disabled={busy || success}>
              {busy ? "Submitting…" : success ? "Redirecting…" : "Submit"}
            </Button>
          </div>
        </Card>
      </TierGate>
    </Shell>
  );
}

function Field({ label, value, onChange, error }: { label: string; value: string; onChange: (v: string) => void; error?: string }) {
  return (
    <div>
      <label className="text-xs text-ink-400">{label}</label>
      <input 
        value={value} 
        onChange={(e) => onChange(e.target.value)}
        className={clsx(
          "mt-1 w-full bg-bg-700 border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500",
          error ? "border-accent-red focus:border-accent-red" : "border-border"
        )}
      />
      {error && <p className="mt-1 text-xs text-accent-red">{error}</p>}
    </div>
  );
}
