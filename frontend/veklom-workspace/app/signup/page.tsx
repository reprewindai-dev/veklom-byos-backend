"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button, ErrorBox } from "@/components/ui";

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [name, setName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(undefined);
    try {
      await signup(email, pw, name || undefined, workspaceName || undefined);
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
            <div className="font-semibold">Create account</div>
            <div className="text-[11px] text-ink-400 uppercase tracking-widest">14-day free trial</div>
          </div>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-ink-400">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500" />
          </div>
          <div>
            <label className="text-xs text-ink-400">Workspace Name</label>
            <input required value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)}
              placeholder="e.g. Acme Corp"
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500" />
          </div>
          <div>
            <label className="text-xs text-ink-400">Work email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500" />
          </div>
          <div>
            <label className="text-xs text-ink-400">Password</label>
            <input type="password" required value={pw} onChange={(e) => setPw(e.target.value)}
              className="mt-1 w-full bg-bg-700 border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-brand-500" />
          </div>
          {err && <ErrorBox message={err} />}
          <Button type="submit" disabled={busy} className="w-full justify-center">
            {busy ? "Creating…" : "Create account"}
          </Button>
        </form>

        <div className="mt-6 flex items-center justify-between">
          <div className="w-full h-px bg-border"></div>
          <span className="px-3 text-xs text-ink-400 bg-bg-800 absolute left-1/2 -translate-x-1/2">or continue with</span>
        </div>

        <Button 
          variant="ghost"
          className="w-full justify-center mt-6 bg-bg-700 hover:bg-bg-600 text-ink-50"
          onClick={() => {
            const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "https://veklom.com/api/v1";
            const nextUrl = encodeURIComponent(window.location.origin + "/control-plane-next/dashboard");
            window.location.href = `${apiBase}/auth/github/login?next=${nextUrl}`;
          }}
        >
          <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24"><path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd"/></svg>
          GitHub
        </Button>

        <p className="text-xs text-ink-400 mt-5 text-center">
          Have an account? <Link href="/login" className="text-brand-400 hover:underline">Sign in</Link>
        </p>
      </div>
    </main>
  );
}
