"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

export function useApi<T = unknown>(path: string | null) {
  return useSWR<T>(path, fetcher, { revalidateOnFocus: false });
}
