import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Plus, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { authApi, workspaceApi } from "@/api";
import { useToast } from "@/hooks/useToast";
import { formatRelative } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Vault() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const userKeys = useQuery({
    queryKey: ["auth/api-keys"],
    queryFn: () => authApi.apiKeys.list(),
    enabled: !IS_DEMO_MODE,
  });
  const wsKeys = useQuery({
    queryKey: ["workspace/api-keys"],
    queryFn: () => workspaceApi.apiKeys(),
    enabled: !IS_DEMO_MODE,
  });

  const [newName, setNewName] = useState("");
  const create = useMutation({
    mutationFn: (name: string) => authApi.apiKeys.create({ name }),
    onSuccess: (res) => {
      toast({
        title: "API key created",
        description: `Copy your secret now: ${res.key.slice(0, 12)}… — it won't be shown again.`,
        variant: "success",
      });
      qc.invalidateQueries({ queryKey: ["auth/api-keys"] });
      qc.invalidateQueries({ queryKey: ["workspace/api-keys"] });
      setNewName("");
    },
    onError: (e) =>
      toast({ title: "Create failed", description: e instanceof Error ? e.message : String(e), variant: "destructive" }),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => authApi.apiKeys.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["auth/api-keys"] });
      qc.invalidateQueries({ queryKey: ["workspace/api-keys"] });
    },
  });

  return (
    <>
      <PageHeader
        eyebrow="Vault"
        title="Sovereign secret store · API keys"
        subtitle="User-scoped keys come from /api/v1/auth/api-keys; workspace-scoped keys from /api/v1/workspace/api-keys. Both write hash-chained audit entries on rotation."
        meta={
          <>
            <Chip tone="primary" icon={<ShieldCheck className="h-3 w-3" />}>Tenant-isolated</Chip>
            <Chip tone="muted">Runtime injection only</Chip>
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-8">
              <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
                <div>
                  <div className="text-eyebrow">User API keys</div>
                  <div className="font-display text-[14px]">Scoped to your account</div>
                </div>
              </div>
              <div className="p-4">
                {userKeys.isLoading ? (
                  <Skeleton className="h-32" />
                ) : userKeys.error ? (
                  <ErrorState error={userKeys.error} />
                ) : !Array.isArray(userKeys.data) || userKeys.data.length === 0 ? (
                  <EmptyState
                    title="No keys yet"
                    description="Create your first key below."
                  />
                ) : (
                  <table className="w-full text-[12.5px]">
                    <thead className="border-b border-border/60 text-eyebrow">
                      <tr>
                        <th className="py-2 text-left">Name</th>
                        <th className="py-2 text-left">Prefix</th>
                        <th className="py-2 text-left">Scopes</th>
                        <th className="py-2 text-left">Last used</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {(userKeys.data as Array<{ id: string; name: string; prefix: string; scopes: string[]; last_used_at: string | null }>).map((k) => (
                        <tr key={k.id} className="border-b border-border/40 last:border-0 hover-elevate">
                          <td className="py-2">{k.name}</td>
                          <td className="py-2 font-mono text-[11.5px]">{k.prefix}…</td>
                          <td className="py-2">{k.scopes?.map((s) => <Chip key={s} tone="muted" className="mr-1">{s}</Chip>)}</td>
                          <td className="py-2 text-muted-foreground">{k.last_used_at ? formatRelative(k.last_used_at) : "—"}</td>
                          <td className="py-2 text-right">
                            <Button size="sm" variant="ghost" onClick={() => revoke.mutate(k.id)}>Revoke</Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="border-t border-border/70 p-4">
                <form
                  className="flex items-center gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (newName.trim()) create.mutate(newName.trim());
                  }}
                >
                  <KeyRound className="h-4 w-4 text-muted-foreground" />
                  <Input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="key name (e.g. ci-pipeline)"
                    className="max-w-[280px]"
                  />
                  <Button size="sm" type="submit" disabled={!newName.trim() || create.isPending}>
                    <Plus className="h-3.5 w-3.5" /> Create
                  </Button>
                </form>
              </div>
            </div>

            <div className="frame col-span-12 lg:col-span-4">
              <div className="border-b border-border/70 px-4 py-3">
                <div className="text-eyebrow">Workspace keys</div>
                <div className="font-display text-[14px]">Shared across the workspace</div>
              </div>
              <div className="p-4">
                {wsKeys.isLoading ? (
                  <Skeleton className="h-32" />
                ) : wsKeys.error ? (
                  <ErrorState error={wsKeys.error} />
                ) : !wsKeys.data?.keys?.length ? (
                  <EmptyState title="None yet" description="Use POST /api/v1/workspace/api-keys to create." />
                ) : (
                  <ul className="space-y-2">
                    {wsKeys.data.keys.map((k) => (
                      <li key={k.id} className="rounded-md border bg-background/40 px-3 py-2">
                        <div className="flex items-center justify-between">
                          <div className="text-[12.5px]">{k.name}</div>
                          <span className="font-mono text-[11px] text-muted-foreground">{k.prefix}…</span>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {k.scopes?.map((s) => <Chip key={s} tone="muted">{s}</Chip>)}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
