import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { ArrowUpRight, Filter, Search, Star } from "lucide-react";
import { PageBody, PageHeader } from "@/components/layout/PageHeader";
import { Chip, LiveBadge } from "@/components/brand/StatusChips";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/data/States";
import { marketplaceApi, type MarketplaceListing } from "@/api";
import { cn } from "@/lib/utils";

export default function Marketplace() {
  const q = useQuery({
    queryKey: ["marketplace/all"],
    queryFn: () => marketplaceApi.allListings(),
  });

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("All");
  const items = q.data?.items ?? [];

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const x of items) {
      const c = x.category ?? x.type;
      if (c) set.add(c);
    }
    return ["All", ...[...set].sort()];
  }, [items]);

  const filtered = items.filter((l) => {
    if (category !== "All" && (l.category ?? l.type) !== category) return false;
    const hay = `${l.title ?? l.name ?? ""} ${l.provider ?? ""} ${l.description ?? ""}`.toLowerCase();
    return !search || hay.includes(search.toLowerCase());
  });

  return (
    <>
      <PageHeader
        eyebrow="Marketplace"
        title="Marketplace products built for governed execution"
        subtitle="Live catalog from your tenant marketplace plus the public veklom.com catalog. Every listing inherits Veklom's policy engine, audit trail, and tenant binding."
        meta={
          <>
            <LiveBadge label={q.data?.source === "merged" ? "WORKSPACE + PUBLIC" : (q.data?.source ?? "loading").toUpperCase()} />
            <Chip tone="muted">{items.length} listings</Chip>
          </>
        }
      />

      <PageBody>
        <div className="frame mb-4">
          <div className="flex flex-wrap items-center gap-2 px-4 py-3">
            <div className="flex flex-1 items-center gap-2 rounded-md border bg-muted/40 px-2.5 py-1.5 min-w-[280px]">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
                placeholder="Search listings, providers…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="text-eyebrow flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5" /> Filter
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1 border-t border-border/60 px-3 py-2">
            {categories.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={cn(
                  "hover-elevate rounded-md border px-2.5 py-1 text-[11.5px]",
                  category === c
                    ? "bg-primary/15 border-primary/40 text-foreground"
                    : "bg-background/40 text-muted-foreground",
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {q.isLoading ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-48" />
            ))}
          </div>
        ) : q.error ? (
          <ErrorState error={q.error} />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((l) => (
              <ListingCard key={l.id} l={l} />
            ))}
          </div>
        )}
      </PageBody>
    </>
  );
}

function ListingCard({ l }: { l: MarketplaceListing }) {
  const title = l.title ?? l.name ?? l.id;
  const cat = l.category ?? l.type ?? "Listing";
  const price =
    l.pricing?.amount != null
      ? `${(l.pricing.currency ?? "USD")} ${l.pricing.amount}${l.pricing.type ? ` / ${l.pricing.type}` : ""}`
      : null;

  const cardBody = (
    <>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-eyebrow">{cat}{l.provider ? ` · ${l.provider}` : ""}</div>
          <h4 className="font-display text-[14.5px] font-semibold leading-tight">{title}</h4>
        </div>
        {l.rating != null && (
          <div className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
            <Star className="h-3 w-3 text-warn" />
            <span>{l.rating}</span>
          </div>
        )}
      </div>
      {l.description && (
        <p className="mt-2 line-clamp-3 text-[12.5px] leading-relaxed text-muted-foreground">
          {l.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {l.compliance?.map((c) => <Chip key={c} tone="primary">{c}</Chip>)}
        {l.badges?.slice(0, 3).map((b) => <Chip key={b} tone="muted">{b}</Chip>)}
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-border/60 pt-3">
        <div className="text-[11px] text-muted-foreground">
          {price ?? (l.installs != null ? `${l.installs} installs` : "—")}
        </div>
        <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition" />
      </div>
    </>
  );

  // Listings that point at an external URL go off-platform; tenant listings open
  // the internal detail page (driven by /marketplace/listings/{id}).
  if (l.url && /^https?:\/\//i.test(l.url)) {
    return (
      <a
        href={l.url}
        target="_blank"
        rel="noreferrer"
        className="frame group block p-4 hover:border-primary/30 transition"
      >
        {cardBody}
      </a>
    );
  }
  return (
    <Link
      href={`/marketplace/${encodeURIComponent(l.id)}`}
      className="frame group block p-4 hover:border-primary/30 transition"
    >
      {cardBody}
    </Link>
  );
}
