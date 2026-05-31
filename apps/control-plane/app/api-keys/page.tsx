"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function ApiKeysPage() {
  const keys = useApi<any>("/api/v1/auth/api-keys");
  const [newKey, setNewKey] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function create() {
    const name = prompt("Name for this key:");
    if (!name) return;
    setBusy(true); setErr(undefined); setNewKey(undefined);
    try {
      const res = await api<any>("/api/v1/auth/api-keys", { body: { name } });
      setNewKey(res.key || res.api_key || res.token);
      keys.mutate();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function revoke(id: string) {
    if (!confirm("Revoke this key? Existing clients will stop working.")) return;
    await api(`/api/v1/auth/api-keys/${id}`, { method: "DELETE" });
    keys.mutate();
  }

  return (
    <Shell>
      <TierGate required="starter" feature="API Keys">
        <PageHeader title="API Keys" subtitle="Issue, rotate, and revoke programmatic access tokens." actions={
          <Button onClick={create} disabled={busy}>New key</Button>
        } />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        {newKey && (
          <Card className="mb-4 border-accent-green/40">
            <div className="text-sm font-medium text-accent-green mb-2">New key — copy now, it won't be shown again</div>
            <code className="text-xs bg-bg-900 px-3 py-2 rounded-md block break-all">{newKey}</code>
          </Card>
        )}
        <Card className="p-0">
          {keys.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(keys.data)}
              rowKey={(r) => r.id || r.key_id}
              empty="No API keys yet"
              columns={[
                { key: "name", header: "Name", render: (r) => r.name },
                { key: "prefix", header: "Prefix", render: (r) => <code className="text-xs">{r.prefix || r.preview || "—"}</code> },
                { key: "created", header: "Created", render: (r) => <span className="text-ink-400 text-xs">{r.created_at}</span> },
                { key: "last_used", header: "Last used", render: (r) => <span className="text-ink-400 text-xs">{r.last_used_at || "never"}</span> },
                { key: "actions", header: "", render: (r) => <Button variant="danger" onClick={() => revoke(r.id || r.key_id)}>Revoke</Button>, width: "100px" },
              ]}
            />
          }
        </Card>
      </TierGate>
    </Shell>
  );
}
