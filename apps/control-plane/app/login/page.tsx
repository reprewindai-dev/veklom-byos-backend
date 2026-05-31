"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button, ErrorBox } from "@/components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(undefined);
    try {
      await login(email, pw);
      router.replace("/dashboard");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center px-6">
      <div className="card w-full max-w-md p-8">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-md bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center font-bold">V</div>
          <div>
            <div className="font-semibold">Veklom Control Plane</div>
            <div className="text-[11px] text-ink-400 uppercase tracking-widest">Sovereign sign-in</div>
          </div>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-ink-400">Email</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-ink-400">Password</label>
            <input
              type="password" required value={pw} onChange={(e) => setPw(e.target.value)}
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>
          {err && <ErrorBox message={err} />}
          <Button type="submit" disabled={busy} className="w-full justify-center">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="text-xs text-ink-400 mt-5 text-center">
          New here? <Link href="/signup" className="text-brand-400 hover:underline">Create an account</Link>
        </p>
      </div>
    </main>
  );
}
