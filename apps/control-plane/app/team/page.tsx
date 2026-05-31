"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, Table, Button, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { api } from "@/lib/api";
import { useState } from "react";

export default function TeamPage() {
  const members = useApi<any>("/api/v1/team/members");
  const roles = useApi<any>("/api/v1/team/roles");
  const sso = useApi<any>("/api/v1/team/sso/status");
  const scim = useApi<any>("/api/v1/team/scim/status");
  const mfa = useApi<any>("/api/v1/team/mfa/status");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();

  async function invite() {
    const email = prompt("Email to invite:");
    if (!email) return;
    setBusy(true); setErr(undefined);
    try { await api("/api/v1/team/invite", { body: { email } }); members.mutate(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function remove(id: string) {
    if (!confirm("Remove this member?")) return;
    await api(`/api/v1/team/members/${id}`, { method: "DELETE" });
    members.mutate();
  }

  return (
    <Shell>
      <TierGate required="pro" feature="Team & RBAC">
        <PageHeader title="Team & RBAC" subtitle="Members, roles, MFA, SSO, and SCIM provisioning." actions={
          <Button onClick={invite} disabled={busy}>Invite member</Button>
        } />
        {err && <div className="mb-4"><ErrorBox message={err} /></div>}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">MFA</div><div className="text-lg mt-1">{mfa.data?.enforced ? "Enforced" : "Optional"}</div></Card>
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">SSO</div><div className="text-lg mt-1">{sso.data?.configured ? "Configured" : "Not set"}</div></Card>
          <Card><div className="text-xs uppercase tracking-widest text-ink-400">SCIM</div><div className="text-lg mt-1">{scim.data?.configured ? "Configured" : "Not set"}</div></Card>
        </div>
        <Card className="p-0">
          <div className="p-5 pb-3 text-sm font-medium">Members</div>
          {members.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table
              rows={unwrapList<any>(members.data)}
              rowKey={(r) => r.id || r.member_id || r.email}
              empty="No members"
              columns={[
                { key: "email", header: "Email", render: (r) => r.email },
                { key: "name", header: "Name", render: (r) => r.name || "—" },
                { key: "role", header: "Role", render: (r) => r.role },
                { key: "mfa", header: "MFA", render: (r) => r.mfa_enabled ? "✓" : "—" },
                { key: "actions", header: "", render: (r) => <Button variant="danger" onClick={() => remove(r.id || r.member_id)}>Remove</Button>, width: "100px" },
              ]}
            />
          }
        </Card>
        <Card className="mt-4">
          <div className="text-sm font-medium mb-3">Roles</div>
          <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(roles.data, null, 2)}</pre>
        </Card>
      </TierGate>
    </Shell>
  );
}
