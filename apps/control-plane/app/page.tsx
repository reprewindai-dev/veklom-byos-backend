"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { me, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) router.replace(me ? "/dashboard" : "/login");
  }, [loading, me, router]);
  return (
    <main className="min-h-screen grid place-items-center">
      <div className="text-ink-400 text-sm">
        <Link href="/login" className="underline">Continue to sign in</Link>
      </div>
    </main>
  );
}
