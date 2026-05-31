import { useState, type FormEvent } from "react";
import { useLocation } from "wouter";
import { Github, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VeklomLogo } from "@/components/brand/Logo";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { authApi } from "@/api";
import { useToast } from "@/hooks/useToast";
import { IS_DEMO_MODE, API_BASE } from "@/lib/env";

export default function LoginPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (IS_DEMO_MODE) {
      toast({ title: "Demo mode", description: "Configure VITE_VEKLOM_API_BASE to log in.", variant: "warn" });
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await authApi.login({ email, password });
      else await authApi.register({ email, password, name });
      setLocation("/");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      toast({ title: mode === "login" ? "Login failed" : "Registration failed", description: msg, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="w-full max-w-[420px]">
        <div className="mb-6 flex flex-col items-center gap-3">
          <VeklomLogo />
          <LiveBadge label="SOVEREIGN CONTROL NODE" />
        </div>

        <form onSubmit={submit} className="frame p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-[16px] font-semibold">{mode === "login" ? "Sign in" : "Create workspace"}</h2>
            <button
              type="button"
              onClick={() => setMode((m) => (m === "login" ? "register" : "login"))}
              className="text-[11.5px] text-muted-foreground hover:text-foreground"
            >
              {mode === "login" ? "Need an account?" : "Already have one?"}
            </button>
          </div>

          {mode === "register" && (
            <div>
              <label className="text-eyebrow">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" className="mt-1" />
            </div>
          )}
          <div>
            <label className="text-eyebrow">Email</label>
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mt-1"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="text-eyebrow">Password</label>
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>

          <Button type="submit" className="w-full" disabled={busy}>
            <LogIn className="h-3.5 w-3.5" /> {mode === "login" ? "Sign in" : "Create workspace"}
          </Button>

          {!IS_DEMO_MODE && (
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => (window.location.href = `${API_BASE}/api/v1/auth/oauth/github`)}
            >
              <Github className="h-3.5 w-3.5" /> Continue with GitHub
            </Button>
          )}

          <div className="text-center text-[11px] text-muted-foreground">
            Wired to{" "}
            <code className="font-mono text-foreground">{IS_DEMO_MODE ? "no backend" : API_BASE}</code>
          </div>
        </form>

        <div className="mt-4 flex justify-center">
          <Chip tone="muted">Veklom BYOS · v1</Chip>
        </div>
      </div>
    </div>
  );
}
