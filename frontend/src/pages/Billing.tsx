import { useQuery } from "@tanstack/react-query";
import { CreditCard, Receipt, Wallet } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/data/States";
import { billingApi } from "@/api";
import { formatUSD, formatNumber, formatRelative } from "@/lib/format";
import { IS_DEMO_MODE } from "@/lib/env";

export default function Billing() {
  const wallet = useQuery({
    queryKey: ["wallet/balance"],
    queryFn: () => billingApi.wallet.balance(),
    enabled: !IS_DEMO_MODE,
  });
  const txns = useQuery({
    queryKey: ["wallet/transactions"],
    queryFn: () => billingApi.wallet.transactions({ limit: 20 }),
    enabled: !IS_DEMO_MODE,
  });
  const sub = useQuery({
    queryKey: ["subscriptions/current"],
    queryFn: () => billingApi.subscriptions.current(),
    enabled: !IS_DEMO_MODE,
  });
  const plans = useQuery({
    queryKey: ["subscriptions/plans"],
    queryFn: () => billingApi.subscriptions.plans(),
  });
  const invoices = useQuery({
    queryKey: ["billing/invoices"],
    queryFn: () => billingApi.invoices(),
    enabled: !IS_DEMO_MODE,
  });

  return (
    <>
      <PageHeader
        eyebrow="Billing · wallet · subscriptions"
        title="Spend, wallet, plan"
        subtitle="Backed by /api/v1/wallet/*, /api/v1/subscriptions/*, and /api/v1/billing/invoices."
        meta={
          <>
            {wallet.data && (
              <Chip tone="primary" icon={<Wallet className="h-3 w-3" />}>
                wallet · {formatNumber(wallet.data.balance)} tok
              </Chip>
            )}
            {sub.data && (
              <Chip tone={sub.data.status === "active" ? "success" : "warn"} dot>
                {sub.data.tier} · {sub.data.status}
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
            <div className="frame col-span-12 lg:col-span-7 p-4">
              <div className="text-eyebrow flex items-center gap-1.5"><Receipt className="h-3.5 w-3.5" /> Recent transactions</div>
              {txns.isLoading ? (
                <Skeleton className="mt-3 h-40" />
              ) : txns.error ? (
                <ErrorState error={txns.error} />
              ) : !txns.data?.items?.length ? (
                <EmptyState title="No transactions" />
              ) : (
                <table className="mt-3 w-full text-[12.5px]">
                  <thead className="border-b border-border/60 text-eyebrow">
                    <tr>
                      <th className="py-2 text-left">When</th>
                      <th className="py-2 text-left">Type</th>
                      <th className="py-2 text-right">Amount</th>
                      <th className="py-2 text-left">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txns.data.items.map((t) => (
                      <tr key={t.id} className="border-b border-border/40 last:border-0">
                        <td className="py-2 text-muted-foreground">{formatRelative(t.created_at)}</td>
                        <td className="py-2"><Chip tone="muted">{t.type}</Chip></td>
                        <td className="py-2 text-right font-mono">{formatNumber(t.amount)}</td>
                        <td className="py-2 text-muted-foreground">{t.description ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="frame col-span-12 lg:col-span-5 p-4">
              <div className="text-eyebrow flex items-center gap-1.5"><CreditCard className="h-3.5 w-3.5" /> Plans</div>
              {plans.isLoading ? (
                <Skeleton className="mt-3 h-40" />
              ) : plans.error ? (
                <ErrorState error={plans.error} />
              ) : !plans.data?.plans?.length ? (
                <EmptyState title="No plans configured" />
              ) : (
                <ul className="mt-3 space-y-2">
                  {plans.data.plans.map((p) => (
                    <li key={p.id} className="rounded-md border bg-background/40 p-3">
                      <div className="flex items-center justify-between">
                        <div className="font-display text-[14px] font-semibold">{p.name}</div>
                        <div className="font-mono text-[12px]">{formatUSD(p.price_usd)}{p.period ? ` / ${p.period}` : ""}</div>
                      </div>
                      {p.features?.length ? (
                        <ul className="mt-2 list-disc pl-4 text-[11.5px] text-muted-foreground">
                          {p.features.map((f) => <li key={f}>{f}</li>)}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="frame col-span-12 p-4">
              <div className="text-eyebrow">Invoices</div>
              {invoices.isLoading ? (
                <Skeleton className="mt-3 h-24" />
              ) : invoices.error ? (
                <ErrorState error={invoices.error} />
              ) : !invoices.data?.items?.length ? (
                <EmptyState title="No invoices" />
              ) : (
                <table className="mt-3 w-full text-[12.5px]">
                  <thead className="border-b border-border/60 text-eyebrow">
                    <tr>
                      <th className="py-2 text-left">Period</th>
                      <th className="py-2 text-right">Total</th>
                      <th className="py-2 text-right">PDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.data.items.map((iv) => (
                      <tr key={iv.id} className="border-b border-border/40 last:border-0">
                        <td className="py-2">{iv.period}</td>
                        <td className="py-2 text-right font-mono">{formatUSD(iv.total_usd)}</td>
                        <td className="py-2 text-right">
                          {iv.pdf_url ? (
                            <a className="text-primary underline-offset-4 hover:underline" href={iv.pdf_url} target="_blank" rel="noreferrer">
                              download
                            </a>
                          ) : (
                            "—"
                          )}
                        </td>
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
