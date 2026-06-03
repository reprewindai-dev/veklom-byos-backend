"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { meetsTier, TIER_LABEL, Tier } from "@/lib/tiers";
import { Lock, HelpCircle, Eye, ChevronRight } from "lucide-react";
import { useState } from "react";

interface GateDetails {
  requiredTier: string;
  reason: string;
  unlockedValue: string;
  targetAudience: string;
  alternatives: string;
}

const DETAILS: Record<string, GateDetails> = {
  "Audit Log": {
    requiredTier: "Pro",
    reason: "Governed immutable logging and cryptographic audit trails are locked to prevent tampering on evaluation accounts.",
    unlockedValue: "SHA-256 tamper-evident hash chaining, automated auditor packages, exportable PDF reports, and real-time operator action streaming.",
    targetAudience: "Compliance Officers, System Administrators, Security Teams",
    alternatives: "Check the local console stdout logs, or configure third-party syslog forwarding."
  },
  "Governance": {
    requiredTier: "Sovereign",
    reason: "Dynamic policy enforcement, compliance limits, and agent rules require a dedicated compliance node to compile and enforce.",
    unlockedValue: "Human-in-the-loop policies, auto-abort limits, multi-sig agent actions, and regulatory evidence collection.",
    targetAudience: "Corporate Counsel, Operations Executives, Risk Managers",
    alternatives: "Manual script gating or external smart contract locks on public chains."
  },
  "Smart Routing": {
    requiredTier: "Pro",
    reason: "Dynamic multi-host routing, latency-based load balancing, and carbon-aware scheduling are locked for evaluation workspaces.",
    unlockedValue: "Auto-routing between cloud and on-premise clusters, live failover, latency optimization, and cost-aware scheduling.",
    targetAudience: "Infrastructure Engineers, DevOps Architects",
    alternatives: "Manual model selection or static API proxy configurations."
  },
  "Compliance": {
    requiredTier: "Sovereign",
    reason: "Continuous SOC2, HIPAA, GDPR control verification, and signed evidence packages require the sovereign tier.",
    unlockedValue: "Pre-wired control mappings across frameworks, continuous automated evidence collection, and signed auditor packages.",
    targetAudience: "Audit Leads, Data Protection Officers",
    alternatives: "Manual evidence collection spreadsheets, or external auditing services."
  },
  "Content Safety": {
    requiredTier: "Pro",
    reason: "Real-time PHI, PII redaction, toxic content detection, and custom safety filters are locked on evaluation.",
    unlockedValue: "Zero-leak PII/PHI masking at the API gateway, toxic prompt prevention, and automated safety alerts.",
    targetAudience: "Safety teams, data privacy officers",
    alternatives: "Basic string filters or client-side regex cleaning."
  },
  "Billing": {
    requiredTier: "Starter",
    reason: "Allocation, invoices, and Stripe portal integration are locked.",
    unlockedValue: "Live invoice tracking, reserve payouts, credit card management, and subscription settings.",
    targetAudience: "Account Owner, Finance Manager",
    alternatives: "Email support@veklom.com for manual billing."
  },
  "Workspace Settings": {
    requiredTier: "Starter",
    reason: "Workspace configuration, workspace naming, and custom base URL are locked.",
    unlockedValue: "Full configuration of workspace metadata, workspace deletion, and name binding.",
    targetAudience: "Workspace Administrator",
    alternatives: "Default workspace settings."
  },
  "API Keys": {
    requiredTier: "Starter",
    reason: "Scoped developer API credentials and automation token generation are locked.",
    unlockedValue: "Generate secure, tenant-scoped API keys with specific permissions to call the Veklom gateway.",
    targetAudience: "Developers, API Integrators",
    alternatives: "Session JWT authentication via the console."
  },
  "Autonomous Jobs": {
    requiredTier: "Pro",
    reason: "Unsupervised long-running agent loops and cron scheduling are locked to conserve compute resources.",
    unlockedValue: "Schedule agentic cron loops, persistent browser automation, and run-until-goal autonomous task execution.",
    targetAudience: "Automation Architects, Developers",
    alternatives: "Local cron scheduling via SDK loops."
  },
  "Locker Security": {
    requiredTier: "Sovereign",
    reason: "Hardware Security Module (HSM) secrets encryption and strict access rules require the sovereign tier.",
    unlockedValue: "Scoped tenant secrets, hardware-level key sealing, auto-rotation rules.",
    targetAudience: "DevSecOps, Compliance",
    alternatives: "Local environment variable secrets."
  }
};

export default function TierGate({
  required,
  feature,
  children,
}: {
  required: Tier;
  feature: string;
  children: React.ReactNode;
}) {
  const { tier } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  if (meetsTier(tier, required)) return <>{children}</>;

  const detail = DETAILS[feature] || {
    requiredTier: TIER_LABEL[required] || required,
    reason: `This feature is locked under the ${TIER_LABEL[required] || required} tier to ensure governed, secure execution.`,
    unlockedValue: `Full access to ${feature} features and automated execution capabilities.`,
    targetAudience: "Workspace Operators and Administrators",
    alternatives: "Standard manual processes or basic local configurations."
  };

  if (dismissed) {
    return (
      <div className="relative w-full h-full">
        <div className="pointer-events-none select-none filter blur-[1px] opacity-50">
          {children}
        </div>
        <div className="fixed bottom-6 right-6 z-50 max-w-sm bg-bg-900 border border-brand-500/40 p-4 rounded-xl shadow-2xl flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Eye size={16} className="text-brand-400" />
            <span className="text-xs font-semibold text-ink-100 uppercase tracking-wider">Read-only Preview</span>
          </div>
          <p className="text-xs text-ink-300">
            You are browsing {feature} in evaluation mode. Actions are locked.
          </p>
          <div className="flex gap-2">
            <Link
              href={`/subscriptions/?tier=${required}`}
              className="flex-1 text-center py-1.5 px-3 rounded bg-brand-500 hover:bg-brand-600 text-bg-950 font-medium text-xs transition"
            >
              Upgrade Plan
            </Link>
            <button
              onClick={() => setDismissed(false)}
              className="px-3 py-1.5 rounded bg-bg-800 hover:bg-bg-750 text-ink-200 border border-border text-xs transition"
            >
              More info
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[500px]">
      <div className="pointer-events-none select-none filter blur-[4px] opacity-30">
        {children}
      </div>
      <div className="absolute inset-0 bg-bg-950/70 backdrop-blur-[2px] flex items-center justify-center p-6 z-40 overflow-y-auto">
        <div className="card max-w-lg w-full border-brand-500/30 bg-bg-900/90 shadow-2xl p-6 md:p-8 flex flex-col gap-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />
          
          <div className="flex items-start gap-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20 shrink-0">
              <Lock size={22} className="stroke-[2px]" />
            </div>
            <div>
              <div className="text-[10px] font-bold text-brand-400 uppercase tracking-widest mb-1">
                Evaluation Limit
              </div>
              <h2 className="text-xl font-bold text-ink-50 leading-tight">
                {feature} requires {TIER_LABEL[required] || required} Tier
              </h2>
            </div>
          </div>

          <div className="space-y-4 text-sm text-ink-300 border-t border-b border-border/40 py-4 my-1">
            <div>
              <span className="text-[11px] font-bold text-ink-500 uppercase block mb-1">Gated Reason</span>
              <p className="text-xs text-ink-200">{detail.reason}</p>
            </div>
            
            <div>
              <span className="text-[11px] font-bold text-ink-500 uppercase block mb-1">Value Unlocked by Upgrade</span>
              <p className="text-xs text-ink-200">{detail.unlockedValue}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-[11px] font-bold text-ink-500 uppercase block mb-1">Target Audience</span>
                <p className="text-xs text-ink-200">{detail.targetAudience}</p>
              </div>
              <div>
                <span className="text-[11px] font-bold text-ink-500 uppercase block mb-1">Standalone Alternatives</span>
                <p className="text-xs text-ink-200">{detail.alternatives}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href={`/subscriptions/?tier=${required}`}
              className="flex-1 inline-flex items-center justify-center px-4 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-bg-950 font-bold text-sm shadow-lg shadow-brand-500/20 transition-all"
            >
              Upgrade to {TIER_LABEL[required] || required} <ChevronRight size={16} className="ml-1" />
            </Link>
            
            <button
              onClick={() => setDismissed(true)}
              className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg bg-bg-800 hover:bg-bg-750 text-ink-100 font-medium text-sm border border-border/80 transition-all"
            >
              Keep exploring
            </button>
          </div>

          <div className="text-[10px] text-center text-ink-500 flex items-center justify-center gap-1.5 mt-2">
            <HelpCircle size={12} />
            Free evaluation accounts are limited to 15 governed runs.
          </div>
        </div>
      </div>
    </div>
  );
}
