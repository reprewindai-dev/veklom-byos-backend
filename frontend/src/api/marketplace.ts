/**
 * Marketplace — /api/v1/marketplace/* and /api/v1/listings/*
 * Source: backend/apps/api/routers/marketplace.py
 *
 * Also handles the **public** marketplace at https://veklom.com/marketplace
 * (no auth required) as a discovery fallback for unauthenticated users.
 */
import { http } from "@/lib/http";
import { IS_DEMO_MODE } from "@/lib/env";
import type { MarketplaceListing } from "./types";

const PUBLIC_VEKLOM_MARKETPLACE = "https://veklom.com/marketplace";

export const marketplaceApi = {
  /** Authenticated, tenant-aware listings from the workspace. */
  listings: () => http.get<MarketplaceListing[]>("/marketplace/listings"),
  listing: (id: string) =>
    http.get<MarketplaceListing>(`/marketplace/listings/${encodeURIComponent(id)}`),
  categories: () => http.get<{ categories: string[] }>("/marketplace/categories"),
  installed: () => http.get<MarketplaceListing[]>("/marketplace/installed"),
  install: (id: string, body: { target?: "hetzner" | "aws" | "both" } = {}) =>
    http.post<{ status: string }>(`/marketplace/listings/${encodeURIComponent(id)}/install`, body),
  datasheet: (id: string) =>
    http.get<{ url: string; sha256?: string }>(
      `/marketplace/listings/${encodeURIComponent(id)}/datasheet`,
    ),
  provider: (slug: string) =>
    http.get<{ slug: string; name: string; listings: MarketplaceListing[] }>(
      `/marketplace/providers/${encodeURIComponent(slug)}`,
    ),
  createListing: (body: Partial<MarketplaceListing>) =>
    http.post<MarketplaceListing>("/marketplace/listings", body),
  updateListing: (id: string, body: Partial<MarketplaceListing>) =>
    http.patch<MarketplaceListing>(`/marketplace/listings/${encodeURIComponent(id)}`, body),
  deleteListing: (id: string) =>
    http.delete<void>(`/marketplace/listings/${encodeURIComponent(id)}`),

  /** Public, unauthenticated marketplace catalog (veklom.com/marketplace). */
  async publicListings(): Promise<MarketplaceListing[]> {
    // Available regardless of API base (it's a static JSON endpoint).
    const res = await fetch(PUBLIC_VEKLOM_MARKETPLACE, {
      headers: { Accept: "application/json" },
      credentials: "omit",
    });
    if (!res.ok) throw new Error(`veklom.com/marketplace responded ${res.status}`);
    const json = (await res.json()) as { products?: MarketplaceListing[] };
    return json.products ?? [];
  },

  /** Best-effort merged listings: authenticated workspace catalog + public fallback. */
  async allListings(): Promise<{ source: "workspace" | "public" | "merged"; items: MarketplaceListing[] }> {
    const publicItems = await marketplaceApi.publicListings().catch(() => [] as MarketplaceListing[]);
    if (IS_DEMO_MODE) return { source: "public", items: publicItems };
    try {
      const items = await marketplaceApi.listings();
      const merged = mergeById([...items, ...publicItems]);
      return { source: "merged", items: merged };
    } catch {
      return { source: "public", items: publicItems };
    }
  },
};

function mergeById(rows: MarketplaceListing[]): MarketplaceListing[] {
  const seen = new Map<string, MarketplaceListing>();
  for (const r of rows) {
    if (!r?.id) continue;
    seen.set(r.id, { ...(seen.get(r.id) ?? {}), ...r });
  }
  return [...seen.values()];
}
