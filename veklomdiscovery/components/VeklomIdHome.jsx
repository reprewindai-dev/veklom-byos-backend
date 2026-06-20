"use client";

import { CheckCircle2, Copy, ExternalLink, Fingerprint, ShieldCheck, Wallet } from "lucide-react";
import { useMemo, useState } from "react";
import { BASE_APP_ID, VEKLOM_COM_ADDRESS, VEKLOM_ID_ADDRESS } from "../config/veklomIdentity";

const identityRows = [
  ["Base App ID", BASE_APP_ID],
  ["Veklom ID Wallet", VEKLOM_ID_ADDRESS],
  ["Veklom.com Payment Wallet", VEKLOM_COM_ADDRESS],
  ["Network", "Base Mainnet"],
  ["Verification Domain", "veklom-id.vercel.app"],
];

export default function VeklomIdHome() {
  const [copied, setCopied] = useState(null);

  const verificationTag = useMemo(
    () => `<meta name="base:app_id" content="${BASE_APP_ID}" />`,
    []
  );

  const copyValue = async (label, value) => {
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1600);
  };

  return (
    <main className="min-h-screen bg-[#05070b] text-white">
      <section className="border-b border-white/10 bg-[radial-gradient(circle_at_20%_0%,rgba(55,125,255,0.22),transparent_32%),linear-gradient(180deg,#07111f_0%,#05070b_78%)]">
        <div className="mx-auto flex min-h-[88vh] max-w-6xl flex-col px-5 py-8 sm:px-8">
          <header className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-lg border border-blue-400/40 bg-blue-500/12">
                <Fingerprint className="h-6 w-6 text-blue-300" />
              </div>
              <div>
                <p className="text-xl font-semibold tracking-normal">Veklom ID</p>
                <p className="text-xs text-slate-400">Base App identity verification</p>
              </div>
            </div>
            <a
              href="/health"
              className="inline-flex items-center gap-2 rounded-md border border-white/12 bg-white/6 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-white/10"
            >
              Health
              <ExternalLink className="h-4 w-4" />
            </a>
          </header>

          <div className="grid flex-1 items-center gap-10 py-14 lg:grid-cols-[1.02fr_0.98fr]">
            <div className="max-w-2xl">
              <h1 className="text-4xl font-semibold leading-tight tracking-normal text-white sm:text-6xl">
                Veklom ID is the verified Base identity layer.
              </h1>
              <p className="mt-6 max-w-xl text-base leading-7 text-slate-300 sm:text-lg">
                This app owns the Base App registration for Veklom ID. Veklom.com keeps its payment wallet separate from the identity wallet.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a
                  href="https://base.org"
                  className="inline-flex items-center gap-2 rounded-md bg-blue-500 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-400"
                >
                  Open Base
                  <ExternalLink className="h-4 w-4" />
                </a>
                <button
                  onClick={() => copyValue("meta", verificationTag)}
                  className="inline-flex items-center gap-2 rounded-md border border-white/12 bg-white/7 px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-white/12"
                >
                  <Copy className="h-4 w-4" />
                  {copied === "meta" ? "Copied" : "Copy meta tag"}
                </button>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-[#0b111d]/90 p-5 shadow-2xl shadow-black/30">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-5 w-5 text-emerald-300" />
                  <h2 className="text-lg font-semibold">Identity Registry</h2>
                </div>
                <span className="rounded-md bg-emerald-400/10 px-2.5 py-1 text-xs font-semibold text-emerald-300">
                  Live
                </span>
              </div>

              <div className="mt-5 space-y-3">
                {identityRows.map(([label, value]) => (
                  <div key={label} className="rounded-md border border-white/8 bg-white/[0.035] p-3">
                    <div className="mb-1 text-xs font-medium text-slate-500">{label}</div>
                    <div className="flex items-center justify-between gap-3">
                      <code className="min-w-0 truncate text-sm text-slate-100">{value}</code>
                      <button
                        onClick={() => copyValue(label, value)}
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-white/10 text-slate-300 hover:bg-white/10"
                        title={`Copy ${label}`}
                      >
                        {copied === label ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-md border border-blue-400/20 bg-blue-400/8 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-blue-200">
                  <Wallet className="h-4 w-4" />
                  Wallet split
                </div>
                <p className="text-sm leading-6 text-slate-300">
                  Veklom ID uses the ID wallet for app identity. Veklom.com routes x402 payments to its production wallet.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
