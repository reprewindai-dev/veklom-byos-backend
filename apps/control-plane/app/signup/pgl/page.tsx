"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Button, ErrorBox } from "@/components/ui";

export default function PGLOnboardPage() {
  const { me, refresh } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function onConnect() {
    setBusy(true);
    setErr(undefined);
    try {
      await api("/api/v1/auth/pgl-onboard", { method: "POST" });
      await refresh();
      router.replace("/dashboard");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function onSkip() {
    router.replace("/dashboard");
  }

  return (
    <main className="min-h-screen grid place-items-center px-6 bg-bg-900">
      <div className="card w-full max-w-md p-8 relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-[-50px] right-[-50px] w-48 h-48 bg-brand-500/10 blur-[64px] rounded-full pointer-events-none"></div>
        
        <div className="flex flex-col items-center text-center mb-8 relative z-10">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-600 to-brand-400 grid place-items-center mb-4 shadow-lg shadow-brand-500/20">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-white">Secure Governance Ledger</h1>
          <p className="text-sm text-ink-400 mt-2">
            Link your Provenance Governance Layer (PGL) identity to ensure your autonomous agents are cryptographically governed and audited.
          </p>
        </div>

        {err && <ErrorBox message={err} className="mb-6" />}

        <div className="space-y-4 relative z-10">
          <Button onClick={onConnect} disabled={busy} className="w-full justify-center py-5 text-sm font-medium">
            {busy ? "Provisioning Identity..." : "Connect PGL Identity"}
          </Button>
          <Button variant="ghost" onClick={onSkip} disabled={busy} className="w-full justify-center text-ink-500 hover:text-ink-300">
            I'll do this later
          </Button>
        </div>
        
        <div className="mt-8 pt-6 border-t border-border/50">
          <p className="text-[11px] text-ink-500 text-center leading-relaxed">
            By connecting, you establish a cryptographic root of trust for all AI operations within your workspace. 
            No governed action executes anonymously.
          </p>
        </div>
      </div>
    </main>
  );
}
