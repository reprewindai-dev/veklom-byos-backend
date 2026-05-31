import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Users, UserPlus } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { workspaceApi } from "@/api";
import { useToast } from "@/hooks/useToast";
import { formatRelative } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Team() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const q = useQuery({
    queryKey: ["workspace/members"],
    queryFn: () => workspaceApi.members(),
    enabled: !IS_DEMO_MODE,
  });
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("Developer");
  const invite = useMutation({
    mutationFn: () => workspaceApi.inviteMember({ email, role }),
    onSuccess: () => {
      toast({ title: "Invite sent", description: email, variant: "success" });
      setEmail("");
      qc.invalidateQueries({ queryKey: ["workspace/members"] });
    },
    onError: (e) => toast({ title: "Invite failed", description: e instanceof Error ? e.message : String(e), variant: "destructive" }),
  });

  return (
    <>
      <PageHeader
        eyebrow="Team & access"
        title="Members · roles · MFA"
        subtitle="Backed by GET /api/v1/workspace/members + POST /api/v1/workspace/members/invite."
        meta={<Chip tone="primary" icon={<Users className="h-3 w-3" />}>RBAC + MFA</Chip>}
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="frame">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 px-4 py-3">
              <div className="text-eyebrow">Members · {q.data?.members?.length ?? 0}</div>
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (email.trim()) invite.mutate();
                }}
              >
                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  className="w-[220px]"
                />
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="h-9 rounded-md border border-input bg-card/60 px-2 text-[12px]"
                >
                  <option>Owner</option>
                  <option>Admin</option>
                  <option>Developer</option>
                  <option>Viewer</option>
                  <option>Billing</option>
                </select>
                <Button size="sm" type="submit" disabled={!email.trim() || invite.isPending}>
                  <UserPlus className="h-3.5 w-3.5" /> Invite
                </Button>
              </form>
            </div>
            <div className="p-4">
              {q.isLoading ? (
                <Skeleton className="h-40" />
              ) : q.error ? (
                <ErrorState error={q.error} />
              ) : !q.data?.members?.length ? (
                <EmptyState title="No members yet" description="Invite teammates with the form above." />
              ) : (
                <table className="w-full text-[12.5px]">
                  <thead className="border-b border-border/60 text-eyebrow">
                    <tr>
                      <th className="py-2 text-left">Name / Email</th>
                      <th className="py-2 text-left">Role</th>
                      <th className="py-2 text-left">MFA</th>
                      <th className="py-2 text-left">Last active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {q.data.members.map((m) => (
                      <tr key={m.id} className="border-b border-border/40 last:border-0 hover-elevate">
                        <td className="py-2">
                          <div>{m.name ?? m.email}</div>
                          {m.name && <div className="text-[11px] text-muted-foreground">{m.email}</div>}
                        </td>
                        <td className="py-2"><Chip tone={m.role === "Owner" ? "primary" : m.role === "Admin" ? "info" : "muted"}>{m.role}</Chip></td>
                        <td className="py-2">
                          <Chip tone={m.mfa ? "success" : "warn"} dot>
                            {m.mfa ? "on" : "off"}
                          </Chip>
                        </td>
                        <td className="py-2 text-muted-foreground">{m.last_active ? formatRelative(m.last_active) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
