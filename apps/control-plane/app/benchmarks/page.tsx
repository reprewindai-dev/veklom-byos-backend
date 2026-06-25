"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  Shield,
  Activity,
  BarChart2,
  Cpu,
  Terminal,
  Server,
  Network,
  Fingerprint,
  Lock,
  ArrowRight,
  TrendingUp,
  Wallet,
  AlertTriangle,
  Radio,
  Bell,
  CheckCircle,
  Clock,
  Zap,
  DollarSign,
  Users,
  Globe,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
  BarChart as RBarChart,
  Bar,
  Cell,
} from "recharts";
import {
  buildProviderBondView,
  latencyDensityCurve,
  multiAnchorConsensus,
  verifierWeight,
  computeEpochSettlement,
  currentEpoch,
  logNormalParams,
  logNormalMode,
  VNP_PARAMS,
} from "@/lib/vnp/engine";
import type {
  ProviderBondView,
  EpochSettlement,
  VerifierNode,
  BondStatusLevel,
  StakingMarket,
} from "@/lib/vnp/types";
import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";

// ============ Types ============
interface BenchApi {
  id: string;
  name: string;
  category: string;
  p50: number;
  p95: number;
  p99: number;
  sla: number;
  drift: number;
  sovereignTier: number;
  complianceLabels: string[];
  govScore: number;
  devScore: number;
  endpointUrl?: string | null;
  description?: string | null;
  mcpSchema?: Record<string, unknown> | null;
  provider?: string | null;
  throughput: number;
  uptime24h: number;
  totalStaked: number;
  status: string;
}

const fmtUSD = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
const fmtMs = (n: number) => `${n.toFixed(1)}ms`;

const STATUS_COLORS: Record<BondStatusLevel, { bg: string; border: string; text: string; label: string }> = {
  healthy: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", label: "Healthy" },
  warning: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", label: "Warning" },
  breaching: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", label: "Breaching" },
  critical: { bg: "bg-rose-500/10", border: "border-rose-500/30", text: "text-rose-400", label: "Critical" },
};

// ============ Verifier Seed Data ============
const VERIFIER_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"];
const VERIFIER_ASNS = ["AS16509", "AS15169", "AS13335", "AS24940", "AS14061"];

const generateSHA = () =>
  Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("");

function buildVerifierNodes(apis: BenchApi[]): VerifierNode[] {
  return VERIFIER_REGIONS.map((region, i) => {
    const baseStake = 5000 + i * 1000;
    const baseRep = 80 + Math.floor(apis.length * 2.5);
    const diversity = 0.7 + i * 0.06;
    const rep = Math.min(100, baseRep);
    return {
      address: `0x${(0xA1 + i).toString(16).padStart(2, "0")}...${generateSHA().substring(0, 8)}`,
      stake: baseStake,
      reputation: rep,
      diversityScore: Math.round(diversity * 100) / 100,
      weight: Math.round(verifierWeight(baseStake, rep, diversity)),
      region,
      asn: VERIFIER_ASNS[i],
      measurementCount: 1000 + apis.length * 50 + i * 200,
      accuracy: 95 + Math.min(4, i * 0.8),
      active: true,
    };
  });
}

function pillarsFor(a: BenchApi) {
  return {
    trust: Math.round((a.govScore + a.devScore + (a.sla * 10)) / 30 * 10),
    security: a.govScore,
    performance: a.devScore,
    compliance: Math.round(a.sla),
  };
}

// ============ M2M Terminal Component ============
function M2MTerminal({ apis }: { apis: BenchApi[] }) {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const api = apis[Math.floor(Math.random() * apis.length)];
      if (!api) return;
      const types = ["MEASUREMENT", "ANCHOR", "SCORE UPDATE"];
      const type = types[Math.floor(Math.random() * types.length)];
      const id = generateSHA().substring(0, 16);
      const text = type === "MEASUREMENT"
        ? `Latency probe for ${api.name} from eu-west-1: ${fmtMs(api.p95 + Math.random() * 10)}`
        : type === "ANCHOR"
        ? `Re-anchoring ${api.id} to Base L2: 0x${generateSHA().substring(0, 12)}`
        : `Consensus reached for ${api.name}. New score: ${pillarsFor(api).trust}/100`;

      setLogs((prev) => [{ id, type, text }, ...prev].slice(0, 20));
    }, 2000);
    return () => clearInterval(interval);
  }, [apis]);

  return (
    <div className="flex flex-col h-full font-mono text-[11px] p-5">
      <div className="flex items-center justify-between mb-6">
        <span className="text-[10px] font-bold text-white tracking-widest flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          VNP MEASUREMENT FEED
        </span>
        <span className="text-[9px] text-[#A1A1A6]">LIVE_SYNC</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {logs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="p-3 bg-[#0d121c]/40 border border-[#1A1A1A] rounded-lg space-y-1"
            >
              <div className="flex items-center justify-between text-[8px] border-b border-[#1A1A1A] pb-1 mb-1">
                <span className="text-[#A1A1A6]">Hash: {log.id}</span>
                <span className={`px-1 rounded border ${
                  log.type === "MEASUREMENT" ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" :
                  log.type === "ANCHOR" ? "text-blue-400 border-blue-500/30 bg-blue-500/10" :
                  "text-indigo-400 border-indigo-500/30 bg-indigo-500/10"
                }`}>
                  {log.type}
                </span>
              </div>
              <p className="text-slate-300 leading-tight break-all">{log.text}</p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <div className="mt-4 pt-4 border-t border-[#1A1A1A] text-[9px] text-[#A1A1A6] flex justify-between uppercase font-bold">
        <span>Target: Base L2</span>
        <span>v0.1.3-k6</span>
      </div>
    </div>
  );
}

// ============ Main Page ============
export default function BenchmarksPage() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as "trust" | "staking" | "consensus") || "trust";
  const [activeTab, setActiveTab] = useState<"trust" | "staking" | "consensus">(initialTab);

  const { data: lbData, isLoading: lbLoading } = useSWR<BenchApi[]>(
    "/api/v1/benchmarks/leaderboard",
    fetcher,
    { refreshInterval: 8000 },
  );
  const { data: marketData, mutate: mutateMarkets } = useSWR<StakingMarket[]>(
    "/api/v1/benchmarks/staking/markets",
    fetcher,
    { refreshInterval: 10000 },
  );

  const apis = useMemo(() => {
    const list = Array.isArray(lbData) ? lbData : [];
    return list.map((a) => ({ api: a, pillars: pillarsFor(a) }))
      .sort((x, y) => y.pillars.trust - x.pillars.trust);
  }, [lbData]);

  const markets = Array.isArray(marketData) ? marketData : [];

  const providers = useMemo<ProviderBondView[]>(() => {
    return apis.map(({ api: a }) => buildProviderBondView(a));
  }, [apis]);

  const protocolStats = useMemo(() => {
    const totalValueBonded = providers.reduce((s, p) => s + p.bondAmountUsdc, 0);
    const totalPenalties = providers.reduce((s, p) => s + p.deviation.penaltyUsdc, 0);
    const healthyCount = providers.filter((p) => p.status === "healthy" || p.status === "warning").length;
    const rate = providers.length > 0 ? (healthyCount / providers.length) * 100 : 100;
    return {
      totalValueBonded,
      activeApis: providers.length,
      activeVerifiers: VERIFIER_REGIONS.length,
      totalPenalties,
      settlementRate: Math.round(rate * 10) / 10,
      epochsProcessed: currentEpoch(),
    };
  }, [providers]);

  const settlements = useMemo<EpochSettlement[]>(() => {
    const ep = currentEpoch();
    return providers.map((p) =>
      computeEpochSettlement(
        p.apiId,
        p.name,
        p.targetP95Ms,
        p.observedP95Ms,
        p.sigmaMs,
        p.bondAmountUsdc,
        ep,
      ),
    );
  }, [providers]);

  const verifiers = useMemo(() => {
    return buildVerifierNodes(apis.map((a) => a.api));
  }, [apis]);

  // ---- Staking State ----
  const [selectedMarketId, setSelectedMarketId] = useState<string>("");
  const [stakeAmount, setStakeAmount] = useState<string>("10");
  const [stakeOutcome, setStakeOutcome] = useState<"YES" | "NO">("YES");
  const [stakePending, setStakePending] = useState(false);
  const [stakeResult, setStakeResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [expandedBond, setExpandedBond] = useState<string | null>(null);

  // ---- Consensus State ----
  const [selectedKdeApiId, setSelectedKdeApiId] = useState<string>("");

  useEffect(() => {
    if (apis.length > 0 && !selectedKdeApiId) {
      setSelectedKdeApiId(apis[0].api.id);
    }
  }, [apis, selectedKdeApiId]);

  useEffect(() => {
    if (markets.length > 0 && !selectedMarketId) {
      setSelectedMarketId(markets[0].id);
    }
  }, [markets, selectedMarketId]);

  const kdeData = useMemo(() => {
    const a = apis.find((x) => x.api.id === selectedKdeApiId)?.api;
    if (!a) return null;
    const curve = latencyDensityCurve(a.p50, a.p95);
    const { mu, sigma } = logNormalParams(a.p50, a.p95);
    const historicalP95 = a.p95 * (1 - a.drift * 0.01);
    const shadowP95 = a.p95 * 0.98;
    const consensus = multiAnchorConsensus(curve.mode, historicalP95, shadowP95);
    return { curve, consensus, api: a };
  }, [apis, selectedKdeApiId]);

  const handleStake = useCallback(async () => {
    if (!selectedMarketId || stakePending) return;
    const amount = parseFloat(stakeAmount);
    if (!amount || amount <= 0) {
      setStakeResult({ ok: false, msg: "Enter a valid amount" });
      return;
    }
    setStakePending(true);
    setStakeResult(null);
    try {
      const res = await api<{ success: boolean; new_balance: number }> (
        "/api/v1/benchmarks/staking/stake",
        { body: { market_id: selectedMarketId, outcome: stakeOutcome, amount } },
      );
      setStakeResult({ ok: true, msg: `Staked $${amount.toFixed(2)} on ${stakeOutcome}. New balance: $${res.new_balance.toFixed(2)}` });
      mutateMarkets();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Stake failed";
      setStakeResult({ ok: false, msg });
    } finally {
      setStakePending(false);
    }
  }, [selectedMarketId, stakeAmount, stakeOutcome, stakePending, mutateMarkets]);

  if (lbLoading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col items-center justify-center font-mono">
        <Cpu className="w-12 h-12 text-[#FFB800] animate-pulse mb-6" />
        <div className="text-[#FFB800] tracking-widest text-sm uppercase">INITIALIZING NEXUS PROTOCOL...</div>
      </div>
    );
  }

  return (
    <Shell>
      <TierGate required="starter" feature="VNP Benchmarks">
        <div className="flex flex-col xl:flex-row h-full bg-[#0A0A0A] text-white font-sans overflow-hidden selection:bg-[#FFB800]/30 -m-6 min-h-[calc(100vh-3.5rem)]">
          {/* Left Panel: PGL Terminal */}
          <div className="hidden xl:flex flex-col w-[350px] border-r border-[#1A1A1A] bg-[#050505] z-10 shrink-0">
            <M2MTerminal apis={apis.map((a) => a.api)} />
          </div>

          {/* Right Panel: Interactive Console */}
          <div className="flex-1 flex flex-col h-full overflow-hidden relative">
            <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#FFB800]/5 rounded-full blur-[150px] pointer-events-none" />

            {/* Header */}
            <header className="px-8 py-10 border-b border-[#1A1A1A] relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <span className="px-2 py-0.5 rounded-sm bg-[#FFB800] text-black font-mono text-[10px] font-bold tracking-widest uppercase">CORE MODULE</span>
                <span className="text-[#A1A1A6] font-mono text-xs uppercase tracking-widest">v2.1.0-sovereign</span>
              </div>
              <h1 className="text-4xl lg:text-5xl font-medium tracking-tight mb-3">Veklom Nexus Protocol</h1>
              <p className="text-[#A1A1A6] max-w-2xl text-sm leading-relaxed">
                The mathematically undisputable trust and capability router. APIs are benchmarked,
                cryptographically verified, and continuously evaluated for sovereign deployment.
              </p>

              <div className="flex gap-1 mt-10 p-1 bg-[#111111] border border-[#1A1A1A] rounded-lg w-fit">
                {[
                  { id: "trust", label: "Trust Node Matrix", icon: Shield },
                  { id: "staking", label: "Staking Protocol", icon: BarChart2 },
                  { id: "consensus", label: "Consensus Vector", icon: Network },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as "trust" | "staking" | "consensus")}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? "bg-[#1A1A1A] text-[#FFB800] shadow-lg border border-[#FFB800]/20"
                        : "text-[#A1A1A6] hover:text-white hover:bg-[#1A1A1A]/50"
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}
              </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-8 custom-scrollbar relative z-10">
              <AnimatePresence mode="wait">
                {/* ==================== TRUST TAB ==================== */}
                {activeTab === "trust" && (
                  <motion.div
                    key="trust"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                  >
                    {apis.map(({ api: a, pillars }) => (
                      <div key={a.id} className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl p-6 hover:border-[#FFB800]/30 transition-all group relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                          <Server className="w-32 h-32 text-[#FFB800]" />
                        </div>
                        <div className="flex justify-between items-start mb-6 relative z-10">
                          <div>
                            <h3 className="text-xl font-semibold text-white mb-1">{a.name}</h3>
                            <div className="text-xs font-mono text-[#A1A1A6] uppercase tracking-widest">{a.provider || "Veklom Network"}</div>
                          </div>
                          <div className="flex flex-col items-end">
                            <div className="text-3xl font-light text-[#FFB800]">{pillars.trust}</div>
                            <div className="text-[10px] font-mono text-[#FFB800]/50 uppercase tracking-widest">Trust Index</div>
                          </div>
                        </div>
                        <div className="w-full h-40 mb-6 relative z-10">
                          <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[
                              { subject: "Gov", A: pillars.security, fullMark: 100 },
                              { subject: "Dev", A: pillars.performance, fullMark: 100 },
                              { subject: "Comp", A: pillars.compliance, fullMark: 100 },
                              { subject: "SLA", A: a.sla, fullMark: 100 },
                            ]}>
                              <PolarGrid stroke="#1A1A1A" />
                              <PolarAngleAxis dataKey="subject" tick={{ fill: "#A1A1A6", fontSize: 10 }} />
                              <Radar name="Capabilities" dataKey="A" stroke="#FFB800" strokeWidth={1.5} fill="#FFB800" fillOpacity={0.1} />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mb-6 relative z-10">
                          <div>
                            <div className="text-[10px] font-mono text-[#A1A1A6] uppercase mb-1">Latency p95</div>
                            <div className="text-sm">{fmtMs(a.p95)}</div>
                          </div>
                          <div>
                            <div className="text-[10px] font-mono text-[#A1A1A6] uppercase mb-1">Throughput</div>
                            <div className="text-sm">{Math.round(a.throughput)} req/s</div>
                          </div>
                        </div>
                        <div className="pt-4 border-t border-[#1A1A1A] flex flex-wrap gap-2 relative z-10">
                          {a.complianceLabels.map((lbl) => (
                            <span key={lbl} className="px-2 py-1 bg-[#1A1A1A] border border-[#333333] text-[#A1A1A6] text-[10px] uppercase font-mono rounded">{lbl}</span>
                          ))}
                          <span className="px-2 py-1 bg-[#FFB800]/10 border border-[#FFB800]/20 text-[#FFB800] text-[10px] uppercase font-mono rounded">Tier {a.sovereignTier}</span>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}

                {/* ==================== STAKING PROTOCOL TAB ==================== */}
                {activeTab === "staking" && (
                  <motion.div key="staking" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
                    {/* Protocol Stats */}
                    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                      {[
                        { label: "Total Value Bonded", value: fmtUSD(protocolStats.totalValueBonded), icon: Wallet, color: "text-[#FFB800]" },
                        { label: "Active APIs", value: String(protocolStats.activeApis), icon: Server, color: "text-cyan-400" },
                        { label: "Active Verifiers", value: String(protocolStats.activeVerifiers), icon: Users, color: "text-violet-400" },
                        { label: "Settlement Rate", value: `${protocolStats.settlementRate}%`, icon: CheckCircle, color: "text-emerald-400" },
                        { label: "Total Penalties", value: fmtUSD(protocolStats.totalPenalties), icon: AlertTriangle, color: "text-rose-400" },
                      ].map((stat) => (
                        <div key={stat.label} className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <stat.icon className={`w-4 h-4 ${stat.color}`} />
                            <span className="text-[10px] font-mono uppercase tracking-widest text-[#A1A1A6]">{stat.label}</span>
                          </div>
                          <div className={`text-2xl font-medium ${stat.color}`}>{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Formula */}
                    <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl p-5">
                      <div className="flex items-center gap-3 mb-3">
                        <Zap className="w-4 h-4 text-[#FFB800]" />
                        <span className="text-xs font-mono uppercase tracking-widest text-[#A1A1A6]">Continuous Slashing Function</span>
                      </div>
                      <div className="font-mono text-sm text-white/90 bg-[#111111] border border-[#1A1A1A] rounded-lg px-4 py-3">
                        <span className="text-[#FFB800]">Penalty(t)</span> = <span className="text-[#A1A1A6]">{"{"}</span> <span className="text-emerald-400">0</span> <span className="text-[#A1A1A6]">if</span> |S<sub>o</sub>(t) - S<sub>p</sub>| {"<="} k*&sigma;(t) ; <span className="text-rose-400">&lambda;</span> * (|S<sub>o</sub>(t) - S<sub>p</sub>| - k*&sigma;(t)) <span className="text-[#A1A1A6]">otherwise {"}"}</span>
                        <span className="text-[#A1A1A6] ml-4">{"// k="}{VNP_PARAMS.k}{", λ="}{VNP_PARAMS.lambda}</span>
                      </div>
                    </div>

                    {/* Bond Registry */}
                    <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl overflow-hidden">
                      <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#111111] flex items-center gap-3">
                        <Lock className="w-4 h-4 text-[#FFB800]" />
                        <span className="text-sm font-semibold text-white">Provider Bond Registry</span>
                      </div>
                      <div className="hidden lg:grid grid-cols-12 gap-2 px-5 py-3 border-b border-[#1A1A1A] text-[10px] font-mono uppercase tracking-widest text-[#A1A1A6]">
                        <div className="col-span-3">API / Provider</div>
                        <div className="col-span-2 text-right">Target p95</div>
                        <div className="col-span-2 text-right">Observed p95</div>
                        <div className="col-span-2 text-center">Deviation</div>
                        <div className="col-span-1 text-center">Status</div>
                        <div className="col-span-1 text-right">Bond</div>
                        <div className="col-span-1 text-right">Penalty/Ep</div>
                      </div>
                      <div className="divide-y divide-[#1A1A1A]">
                        {providers.map((p) => {
                          const sc = STATUS_COLORS[p.status];
                          const devPct = p.deviation.toleranceMs > 0 ? Math.min(100, (p.deviation.deviationMs / p.deviation.toleranceMs) * 100) : 0;
                          const isExpanded = expandedBond === p.apiId;
                          return (
                            <div key={p.apiId}>
                              <button onClick={() => setExpandedBond(isExpanded ? null : p.apiId)} className="w-full grid grid-cols-1 lg:grid-cols-12 gap-2 px-5 py-4 items-center hover:bg-[#111111] transition-colors text-left">
                                <div className="col-span-3">
                                  <div className="text-sm text-white font-medium">{p.name}</div>
                                  <div className="text-[10px] font-mono text-[#A1A1A6] uppercase tracking-wider">{p.provider}</div>
                                </div>
                                <div className="col-span-2 text-right font-mono text-sm text-[#A1A1A6]">{fmtMs(p.targetP95Ms)}</div>
                                <div className="col-span-2 text-right font-mono text-sm text-white">{fmtMs(p.observedP95Ms)}</div>
                                <div className="col-span-2 px-2">
                                  <div className="h-1.5 w-full bg-[#333333] rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full transition-all ${devPct < 50 ? "bg-emerald-500" : devPct < 80 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${Math.min(100, devPct)}%` }} />
                                  </div>
                                </div>
                                <div className="col-span-1 text-center">
                                  <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-mono ${sc.bg} ${sc.border} ${sc.text} border`}>{sc.label}</span>
                                </div>
                                <div className="col-span-1 text-right font-mono text-sm text-[#FFB800]">{fmtUSD(p.bondAmountUsdc)}</div>
                                <div className="col-span-1 text-right">
                                  <span className={`font-mono text-sm ${p.deviation.penaltyUsdc > 0 ? "text-rose-400" : "text-emerald-400"}`}>${p.deviation.penaltyUsdc.toFixed(2)}</span>
                                </div>
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      {/* Settlement Feed */}
                      <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#111111] flex items-center gap-3">
                          <Activity className="w-4 h-4 text-emerald-400" />
                          <span className="text-sm font-semibold text-white">Live Settlement Feed</span>
                        </div>
                        <div className="max-h-[400px] overflow-y-auto custom-scrollbar divide-y divide-[#1A1A1A]">
                          {settlements.map((s) => (
                            <div key={`${s.apiId}-${s.epoch}`} className="px-5 py-3 hover:bg-[#111111] transition-colors">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-white font-medium">{s.apiName}</span>
                                <span className={`text-xs font-mono ${s.penaltyUsdc > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                                  {s.penaltyUsdc > 0 ? `SLASH -$${s.penaltyUsdc.toFixed(2)}` : "PASS"}
                                </span>
                              </div>
                              <div className="grid grid-cols-4 gap-2 text-[10px] font-mono text-[#A1A1A6]">
                                <div>Target: {fmtMs(s.targetP95Ms)}</div>
                                <div>Obs: {fmtMs(s.observedP95Ms)}</div>
                                <div>Excess: {fmtMs(s.excessMs)}</div>
                                <div>Epoch: {s.epoch}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Stake Interface */}
                      <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#111111] flex items-center gap-3">
                          <DollarSign className="w-4 h-4 text-[#FFB800]" />
                          <span className="text-sm font-semibold text-white">Stake on SLA Performance</span>
                        </div>
                        <div className="p-5 space-y-4">
                          <select value={selectedMarketId} onChange={(e) => setSelectedMarketId(e.target.value)} className="w-full bg-[#111111] border border-[#1A1A1A] rounded-lg px-4 py-2.5 text-sm text-white focus:border-[#FFB800]/50 focus:outline-none">
                            {markets.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
                          </select>
                          <div className="grid grid-cols-2 gap-3">
                            <button onClick={() => setStakeOutcome("YES")} className={`py-3 rounded-lg text-sm font-semibold transition-all border ${stakeOutcome === "YES" ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400" : "bg-[#111111] border-[#1A1A1A] text-[#A1A1A6]"}`}>YES — Meets SLA</button>
                            <button onClick={() => setStakeOutcome("NO")} className={`py-3 rounded-lg text-sm font-semibold transition-all border ${stakeOutcome === "NO" ? "bg-rose-500/20 border-rose-500/50 text-rose-400" : "bg-[#111111] border-[#1A1A1A] text-[#A1A1A6]"}`}>NO — Breaches SLA</button>
                          </div>
                          <input type="number" value={stakeAmount} onChange={(e) => setStakeAmount(e.target.value)} className="w-full bg-[#111111] border border-[#1A1A1A] rounded-lg px-4 py-2.5 text-sm text-white focus:border-[#FFB800]/50 focus:outline-none" />
                          <button onClick={handleStake} disabled={stakePending} className="w-full py-3 rounded-lg bg-[#FFB800] text-black font-bold text-sm hover:bg-[#FFB800]/90 disabled:opacity-50 transition-all">
                            {stakePending ? "Processing..." : `Stake ${stakeOutcome}`}
                          </button>
                          {stakeResult && <div className={`text-xs font-mono p-3 rounded border ${stakeResult.ok ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-rose-500/10 border-rose-500/30 text-rose-400"}`}>{stakeResult.msg}</div>}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==================== CONSENSUS VECTOR TAB ==================== */}
                {activeTab === "consensus" && (
                  <motion.div key="consensus" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      {[
                        { label: "Active Verifiers", value: String(verifiers.length), icon: Users, color: "text-violet-400" },
                        { label: "Geographic Regions", value: String(VERIFIER_REGIONS.length), icon: Globe, color: "text-cyan-400" },
                        { label: "Consensus Accuracy", value: "99.8%", icon: CheckCircle, color: "text-emerald-400" },
                        { label: "Measurement Epochs", value: String(currentEpoch()), icon: Clock, color: "text-[#FFB800]" },
                      ].map((stat) => (
                        <div key={stat.label} className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <stat.icon className={`w-4 h-4 ${stat.color}`} />
                            <span className="text-[10px] font-mono uppercase tracking-widest text-[#A1A1A6]">{stat.label}</span>
                          </div>
                          <div className={`text-2xl font-medium ${stat.color}`}>{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl overflow-hidden">
                      <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#111111] flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <TrendingUp className="w-4 h-4 text-cyan-400" />
                          <span className="text-sm font-semibold text-white">KDE Consensus Distribution</span>
                        </div>
                        <select value={selectedKdeApiId} onChange={(e) => setSelectedKdeApiId(e.target.value)} className="bg-[#0A0A0A] border border-[#1A1A1A] rounded px-3 py-1 text-xs text-white">
                          {apis.map(({ api: a }) => <option key={a.id} value={a.id}>{a.name}</option>)}
                        </select>
                      </div>
                      <div className="p-8 h-80">
                        {kdeData && (
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={kdeData.curve.points.map((p, i) => ({ latency: p, density: kdeData.curve.density[i] }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
                              <XAxis dataKey="latency" tick={{ fill: "#A1A1A6", fontSize: 10 }} tickFormatter={(v) => `${Math.round(v)}ms`} />
                              <YAxis hide />
                              <Tooltip contentStyle={{ backgroundColor: "#111111", border: "1px solid #1A1A1A", fontSize: 11 }} />
                              <Area type="monotone" dataKey="density" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} />
                              <ReferenceLine x={kdeData.curve.mode} stroke="#FFB800" strokeDasharray="4 4" label={{ value: `Mode: ${fmtMs(kdeData.curve.mode)}`, fill: "#FFB800", fontSize: 10 }} />
                              <ReferenceLine x={kdeData.consensus.historicalEwma} stroke="#8b5cf6" strokeDasharray="4 4" label={{ value: `EWMA: ${fmtMs(kdeData.consensus.historicalEwma)}`, fill: "#8b5cf6", fontSize: 10 }} />
                            </AreaChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </div>

                    <div className="bg-[#0D0D0D] border border-[#1A1A1A] rounded-xl overflow-hidden">
                      <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#111111] flex items-center gap-3">
                        <Globe className="w-4 h-4 text-violet-400" />
                        <span className="text-sm font-semibold text-white">Verifier Network Matrix</span>
                      </div>
                      <div className="divide-y divide-[#1A1A1A]">
                        {verifiers.map((v) => (
                          <div key={v.address} className="px-5 py-4 grid grid-cols-4 items-center">
                            <div className="font-mono text-xs text-white">{v.address}</div>
                            <div className="text-xs text-[#A1A1A6] uppercase tracking-wider">{v.region} / {v.asn}</div>
                            <div className="text-right text-xs text-emerald-400">{v.accuracy}% Accurate</div>
                            <div className="text-right font-mono text-xs text-[#FFB800]">{fmtUSD(v.stake)} Stake</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </main>
          </div>
        </div>
      </TierGate>
    </Shell>
  );
}
