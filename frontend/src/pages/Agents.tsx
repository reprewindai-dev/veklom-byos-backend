import { useQuery } from "@tanstack/react-query";
import { Bot, ShieldCheck, AlertTriangle } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { agentsApi } from "@/api";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Agents() {
  const fleet = useQuery({ queryKey: ["agents/fleet"], queryFn: () => agentsApi.fleet(), enabled: !IS_DEMO_MODE });
  const registry = useQuery({ queryKey: ["agents/registry"], queryFn: () => agentsApi.registry(), enabled: !IS_DEMO_MODE });
  const guardrails = useQuery({ queryKey: ["agents/guardrails"], queryFn: () => agentsApi.guardrails(), enabled: !IS_DEMO_MODE });
  const violations = useQuery({ queryKey: ["agents/violations"], queryFn: () => agentsApi.violations(), enabled: !IS_DEMO_MODE });
  const skills = useQuery({ queryKey: ["agents/skills"], queryFn: () => agentsApi.skills(), enabled: !IS_DEMO_MODE });

  return (
    <>
      <PageHeader
        eyebrow="Governance · Agent Workforce"
        title="Autonomous agent fleet"
        subtitle="Backed by /api/v1/agents/* and /api/v1/agents/hrm/*. Every action governed by Veklom law + guardrails."
        meta={
          <>
            <Chip tone="primary" icon={<Bot className="h-3 w-3" />}>Workforce</Chip>
            {fleet.data && (
              <Chip tone="muted">
                {fleet.data.active} active · {fleet.data.idle} idle · {fleet.data.failed} failed
              </Chip>
            )}
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-7">
              <div className="border-b border-border/70 px-4 py-3">
                <div className="text-eyebrow">Registry</div>
                <div className="font-display text-[14px]">/agents/registry</div>
              </div>
              <div className="p-4">
                {registry.isLoading ? <Skeleton className="h-32" /> :
                 registry.error ? <ErrorState error={registry.error} /> :
                 !registry.data?.items?.length ? <EmptyState title="No agents registered" /> : (
                  <table className="w-full text-[12.5px]">
                    <thead className="border-b border-border/60 text-eyebrow">
                      <tr>
                        <th className="py-2 text-left">Name / #</th>
                        <th className="py-2 text-left">Tier</th>
                        <th className="py-2 text-left">Squad</th>
                        <th className="py-2 text-left">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registry.data.items.map((a) => (
                        <tr key={String(a.id ?? a.agent_number)} className="border-b border-border/40 last:border-0">
                          <td className="py-2">{a.name ?? `#${a.agent_number}`}</td>
                          <td className="py-2">{a.tier ? <Chip tone="primary">{a.tier}</Chip> : "—"}</td>
                          <td className="py-2 font-mono text-[11.5px] text-muted-foreground">{a.squad_id ?? "—"}</td>
                          <td className="py-2"><Chip tone={a.status === "active" ? "success" : "muted"} dot>{a.status ?? "—"}</Chip></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="frame col-span-12 lg:col-span-5">
              <div className="border-b border-border/70 px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="text-eyebrow">Guardrails</div>
                  <div className="font-display text-[14px]">/agents/guardrails</div>
                </div>
                <ShieldCheck className="h-4 w-4 text-success" />
              </div>
              <div className="p-4">
                {guardrails.isLoading ? <Skeleton className="h-32" /> :
                 guardrails.error ? <ErrorState error={guardrails.error} /> :
                 !guardrails.data?.items?.length ? <EmptyState title="No guardrails defined" /> : (
                  <ul className="space-y-1.5">
                    {guardrails.data.items.map((g) => (
                      <li key={g.id} className="rounded-md border bg-background/40 px-3 py-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11.5px]">{g.id}</span>
                          <Chip tone={g.severity === "critical" ? "danger" : g.severity === "warn" ? "warn" : "info"}>
                            {g.severity}
                          </Chip>
                        </div>
                        <div className="text-[11.5px] text-muted-foreground">{g.rule}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="frame col-span-12 lg:col-span-7">
              <div className="border-b border-border/70 px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="text-eyebrow">Skills</div>
                  <div className="font-display text-[14px]">/agents/skills</div>
                </div>
              </div>
              <div className="p-4">
                {skills.isLoading ? <Skeleton className="h-32" /> :
                 skills.error ? <ErrorState error={skills.error} /> :
                 !skills.data?.items?.length ? <EmptyState title="No skills available" /> : (
                  <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {skills.data.items.map((s) => (
                      <li key={s.id} className="rounded-md border bg-background/40 p-3">
                        <div className="font-mono text-[12px]">{s.name}</div>
                        {s.description && <div className="mt-0.5 text-[11.5px] text-muted-foreground line-clamp-2">{s.description}</div>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="frame col-span-12 lg:col-span-5">
              <div className="border-b border-border/70 px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="text-eyebrow">Violations</div>
                  <div className="font-display text-[14px]">/agents/violations</div>
                </div>
                <AlertTriangle className="h-4 w-4 text-warn" />
              </div>
              <div className="p-4">
                {violations.isLoading ? <Skeleton className="h-32" /> :
                 violations.error ? <ErrorState error={violations.error} /> :
                 !violations.data?.items?.length ? <EmptyState title="No violations" /> : (
                  <pre className="max-h-[200px] overflow-auto rounded-md border bg-background/60 p-3 font-mono text-[11px]">
                    {JSON.stringify(violations.data.items, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
