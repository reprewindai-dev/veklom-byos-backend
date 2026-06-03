"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useState } from "react";

export default function ContentSafetyPage() {
  const ageStatus = useApi<any>("/api/v1/content-safety/age-verify/status");
  const [text, setText] = useState("");
  const [result, setResult] = useState<any>();
  const [err, setErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  async function scan() {
    setBusy(true); setErr(undefined); setResult(undefined);
    try { setResult(await api<any>("/api/v1/content-safety/scan", { body: { text } })); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Content Safety">
        <PageHeader title="Content Safety" subtitle="Scan content for unsafe categories. Age verification status for restricted flows." />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <div className="text-sm font-medium mb-3">Live scan</div>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={6}
              placeholder="Paste content to evaluate…"
              className="w-full bg-bg-900 border border-border rounded-md p-3 text-sm font-mono outline-none focus:border-brand-500" />
            <div className="mt-3 flex justify-end"><Button onClick={scan} disabled={busy || !text}>{busy ? "Scanning…" : "Scan"}</Button></div>
            {err && <div className="mt-3"><ErrorBox message={err} /></div>}
            {result && <pre className="mt-3 text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(result, null, 2)}</pre>}
          </Card>
          <Card>
            <div className="text-sm font-medium mb-3">Age verification status</div>
            <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(ageStatus.data, null, 2)}</pre>
          </Card>
        </div>
      </TierGate>
    </Shell>
  );
}
