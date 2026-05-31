"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";

export default function KillSwitchPage() {
  const status = useApi<any>("/api/v1/cost/kill-switch/status");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function engage() {
    if (!confirm("Engage kill switch? This halts all governed execution immediately.")) return;
    setBusy(true); setErr(undefined);
    try { await api("/api/v1/cost/kill-switch", { body: { reason: "manual" } }); status.mutate(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function release() {
    if (!confirm("Release kill switch?")) return;
    setBusy(true);
    try { await api("/api/v1/cost/kill-switch", { method: "DELETE" }); status.mutate(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const engaged = !!(status.data?.engaged ?? status.data?.active ?? status.data?.status === "engaged");

  return (
    <Shell>
      <TierGate required="sovereign" feature="Kill Switch">
        <PageHeader
          title="Kill Switch"
          subtitle="Halt all governed execution. Audit-proofed with timestamp, actor, and reason."
        />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <Card className="text-center py-12">
          <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full mb-4 ${engaged ? "bg-accent-red/20 text-accent-red" : "bg-accent-green/20 text-accent-green"}`}>
            <svg width="36" height="36" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a1 1 0 0 1 1 1v10a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1zm6.4 4.6a8 8 0 1 1-12.8 0 1 1 0 0 1 1.6 1.2 6 6 0 1 0 9.6 0 1 1 0 0 1 1.6-1.2z"/></svg>
          </div>
          <div className="text-2xl font-semibold mb-2">{engaged ? "ENGAGED" : "Standby"}</div>
          <div className="text-ink-400 text-sm mb-6">{status.data?.reason || (engaged ? "Execution halted" : "All systems nominal")}</div>
          {engaged ? (
            <Button variant="ghost" onClick={release} disabled={busy}>Release kill switch</Button>
          ) : (
            <Button variant="danger" onClick={engage} disabled={busy}>Engage kill switch</Button>
          )}
        </Card>
      </TierGate>
    </Shell>
  );
}
