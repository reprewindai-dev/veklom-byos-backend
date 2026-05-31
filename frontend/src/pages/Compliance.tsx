import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, ShieldCheck } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { complianceApi } from "@/api";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Compliance() {
  const regulations = useQuery({
    queryKey: ["compliance/regulations"],
    queryFn: () => complianceApi.regulations(),
    enabled: !IS_DEMO_MODE,
  });
  const privacy = useQuery({
    queryKey: ["privacy/status"],
    queryFn: () => complianceApi.privacyStatus(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Compliance Center"
        title="Operational evidence, not a marketing page"
        subtitle="Backed by /api/v1/compliance/regulations + /api/v1/privacy/status. Run on-demand checks with POST /compliance/check."
        meta={
          <>
            <Chip tone="primary" icon={<ClipboardCheck className="h-3 w-3" />}>Auditor-grade evidence</Chip>
            {privacy.data && (
              <Chip tone={privacy.data.pii_detected || privacy.data.phi_detected ? "warn" : "success"} icon={<ShieldCheck className="h-3 w-3" />}>
                {privacy.data.pii_detected ? "PII detected" : "no PII"}
                {privacy.data.phi_detected ? " · PHI detected" : ""}
              </Chip>
            )}
          </>
        }
      />
      <PageBody>
        {IS_DEMO_MODE ? (
          <ErrorState error={new Error("no backend")} />
        ) : regulations.isLoading ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
          </div>
        ) : regulations.error ? (
          <ErrorState error={regulations.error} />
        ) : !regulations.data?.regulations?.length ? (
          <EmptyState title="No frameworks loaded" />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {regulations.data.regulations.map((f) => (
              <div key={f.id} className="frame p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-eyebrow">Framework</div>
                    <div className="font-display text-[15px] font-semibold">{f.name}</div>
                  </div>
                  {f.state && (
                    <Chip tone={f.state === "Audit-ready" ? "success" : f.state === "Continuous" ? "info" : "warn"} dot>
                      {f.state}
                    </Chip>
                  )}
                </div>
                {f.coverage_pct != null && (
                  <>
                    <div className="mt-3 flex items-baseline justify-between">
                      <span className="font-display text-[22px] font-semibold">{f.coverage_pct}%</span>
                      <span className="text-[11px] text-muted-foreground">coverage · {f.controls_total ?? "—"} controls</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted/50">
                      <div className="h-full bg-primary" style={{ width: `${f.coverage_pct}%` }} />
                    </div>
                  </>
                )}
                {f.evidence_rows != null && (
                  <div className="mt-3 border-t border-border/60 pt-3 text-[11px] text-muted-foreground">
                    Evidence rows: <span className="font-mono text-foreground">{f.evidence_rows}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </PageBody>
    </>
  );
}
