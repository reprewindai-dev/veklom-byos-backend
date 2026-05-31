import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "wouter";
import { ArrowLeft, ExternalLink, ShieldCheck } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/data/States";
import { Button } from "@/components/ui/button";
import { marketplaceApi } from "@/api";

export default function MarketplaceListing() {
  const { id } = useParams<{ id: string }>();
  const q = useQuery({
    queryKey: ["marketplace/listing", id],
    queryFn: () => marketplaceApi.listing(id),
    enabled: Boolean(id),
  });

  return (
    <>
      <PageHeader
        eyebrow={
          <Link href="/marketplace" className="inline-flex items-center gap-1 hover:text-foreground">
            <ArrowLeft className="h-3 w-3" /> Marketplace
          </Link>
        }
        title={q.data?.title ?? q.data?.name ?? "Listing"}
        subtitle={q.data?.description ?? ""}
        meta={
          <>
            {q.data?.compliance?.map((c) => <Chip key={c} tone="primary">{c}</Chip>)}
            {q.data?.badges?.map((b) => <Chip key={b} tone="muted">{b}</Chip>)}
          </>
        }
      />
      <PageBody>
        {q.isLoading ? (
          <Skeleton className="h-60" />
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : q.data ? (
          <div className="grid grid-cols-12 gap-4">
            <div className="frame col-span-12 lg:col-span-8 p-5">
              <div className="text-eyebrow">About</div>
              <p className="mt-2 text-[13px] leading-relaxed">{q.data.description ?? "—"}</p>
              {q.data.url && (
                <div className="mt-4">
                  <Button asChild>
                    <a href={q.data.url} target="_blank" rel="noreferrer">
                      Open <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                </div>
              )}
            </div>
            <aside className="col-span-12 lg:col-span-4 space-y-3">
              <div className="frame p-4">
                <div className="text-eyebrow">Provider</div>
                <div className="mt-1 font-display text-[14px] font-semibold">{q.data.provider ?? "—"}</div>
                <div className="text-[11.5px] text-muted-foreground">{q.data.category ?? q.data.type}</div>
              </div>
              <div className="frame p-4">
                <div className="text-eyebrow">Distribution</div>
                <ul className="mt-2 space-y-1.5 text-[12px]">
                  <li className="flex items-center gap-2">
                    <ShieldCheck className="h-3.5 w-3.5 text-success" />
                    Workspace-bound · revocable
                  </li>
                  {q.data.install && <li className="font-mono text-[11.5px]">install: {q.data.install}</li>}
                  {q.data.target?.length ? (
                    <li className="font-mono text-[11.5px]">target: {q.data.target.join(", ")}</li>
                  ) : null}
                </ul>
              </div>
            </aside>
          </div>
        ) : null}
      </PageBody>
    </>
  );
}
