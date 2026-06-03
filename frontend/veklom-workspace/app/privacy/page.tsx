"use client";

import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { Card, PageHeader } from "@/components/ui";
import { useApi } from "@/hooks/useApi";

export default function PrivacyPage() {
  const cfg = useApi<any>("/api/v1/config");
  return (
    <Shell>
      <TierGate required="sovereign" feature="Privacy Controls">
        <PageHeader title="Privacy Controls" subtitle="Data residency, redaction policies, and retention windows." />
        <Card>
          <div className="text-sm font-medium mb-3">Effective privacy config</div>
          <pre className="text-xs bg-bg-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(cfg.data, null, 2)}</pre>
        </Card>
      </TierGate>
    </Shell>
  );
}
