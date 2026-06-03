"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { meetsTier, TIER_LABEL, Tier } from "@/lib/tiers";
import { Lock } from "lucide-react";

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
  if (meetsTier(tier, required)) return <>{children}</>;
  return (
    <div className="card p-8 max-w-xl mx-auto text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-bg-700 text-accent-amber mb-3">
        <Lock size={20} />
      </div>
      <h2 className="text-lg font-semibold mb-1">{feature} is on {TIER_LABEL[required]}</h2>
      <p className="text-ink-400 text-sm mb-5">
        Your current plan is <span className="text-ink-50">{TIER_LABEL[tier]}</span>. Upgrade to unlock this module.
      </p>
      <Link
        href="/subscriptions"
        className="inline-flex items-center px-4 py-2 rounded-md bg-brand-500 hover:bg-brand-600 text-bg-900 font-medium text-sm"
      >
        Upgrade plan
      </Link>
    </div>
  );
}
