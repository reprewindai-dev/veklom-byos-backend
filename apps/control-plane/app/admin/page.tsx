"use client";

import Shell from "@/components/Shell";
import { useApi } from "@/hooks/useApi";
import { Card, PageHeader, Skeleton, StatCard, Table, ErrorBox } from "@/components/ui";
import { unwrapList } from "@/types/api";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function AdminPage() {
  const { me } = useAuth();
  const workspaces = useApi<any>(me?.is_superuser ? "/api/v1/admin/workspaces" : null);
  const users = useApi<any>(me?.is_superuser ? "/api/v1/admin/users" : null);
  const audit = useApi<any>(me?.is_superuser ? "/api/v1/admin/audit" : null);
  const recon = useApi<any>(me?.is_superuser ? "/api/v1/admin/billing/recon-summary" : null);

  if (!me?.is_superuser) {
    return (
      <Shell>
        <Card className="max-w-md mx-auto text-center py-8">
          <div className="text-lg font-semibold">Admin restricted</div>
          <div className="text-ink-400 text-sm mt-1">Only superusers can access this area.</div>
          <Link href="/dashboard" className="text-brand-400 hover:underline text-sm mt-3 inline-block">Back to dashboard</Link>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <PageHeader title="Admin" subtitle="Superuser view: workspaces, users, billing reconciliation, audit." />
      {workspaces.error && <div className="mb-4"><ErrorBox message={workspaces.error.message} /></div>}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <StatCard label="Workspaces" value={unwrapList(workspaces.data).length} />
        <StatCard label="Users" value={unwrapList(users.data).length} />
        <StatCard label="Recon findings" value={recon.data?.findings ?? "—"} accent="text-accent-amber" />
        <StatCard label="Audit (24h)" value={unwrapList(audit.data).length} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-0">
          <div className="p-5 pb-3 text-sm font-medium">Workspaces</div>
          {workspaces.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table rows={unwrapList<any>(workspaces.data)} rowKey={(r) => r.id} empty="No workspaces" columns={[
              { key: "id", header: "ID", render: (r) => <code className="text-xs">{r.id}</code> },
              { key: "name", header: "Name", render: (r) => r.name },
              { key: "plan", header: "Plan", render: (r) => r.plan || r.tier },
              { key: "status", header: "Status", render: (r) => r.status },
            ]} />
          }
        </Card>
        <Card className="p-0">
          <div className="p-5 pb-3 text-sm font-medium">Users</div>
          {users.isLoading ? <div className="p-5"><Skeleton className="h-32 w-full" /></div> :
            <Table rows={unwrapList<any>(users.data)} rowKey={(r) => r.id} empty="No users" columns={[
              { key: "email", header: "Email", render: (r) => r.email },
              { key: "role", header: "Role", render: (r) => r.role },
              { key: "status", header: "Status", render: (r) => r.status || (r.active ? "active" : "—") },
            ]} />
          }
        </Card>
      </div>
    </Shell>
  );
}
