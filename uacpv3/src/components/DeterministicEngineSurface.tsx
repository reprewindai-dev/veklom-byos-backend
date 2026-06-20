import { type ReactNode, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BrainCircuit,
  ChevronRight,
  Cpu,
  Disc,
  Info,
  Layers,
  Lock,
  Play,
  Search,
  ShieldCheck,
  Users,
  Zap,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import type {
  Committee,
  EngineObservability,
  EngineSignal,
  EventItem,
  GovernedRun,
  InstitutionalPlan,
} from "../types";

type EngineTab = "intent" | "execution" | "ops";

type DeterministicEngineSurfaceProps = {
  identity: string;
  intent: string;
  loading: boolean;
  plans: InstitutionalPlan[];
  runs: GovernedRun[];
  events: EventItem[];
  committees: Committee[];
  signals: EngineSignal[];
  observability: EngineObservability | null;
  onIntentChange: (value: string) => void;
  onCreatePlan: () => Promise<InstitutionalPlan | null>;
  onRouteToSunnyvale: (planId: string) => void;
};

export function DeterministicEngineSurface({
  identity,
  intent,
  loading,
  plans,
  runs,
  events,
  committees,
  signals,
  observability,
  onIntentChange,
  onCreatePlan,
  onRouteToSunnyvale,
}: DeterministicEngineSurfaceProps) {
  const [activeTab, setActiveTab] = useState<EngineTab>("intent");
  const primaryPlan = plans[0];
  const primaryPlanPillars = asArray(primaryPlan?.pillars);
  const primaryPlanCommitteeIds = asArray(primaryPlan?.committeeIds);
  const primaryPlanWorkflowIds = asArray(primaryPlan?.workflowIds);
  const primaryPlanSkillIds = asArray(primaryPlan?.skillIds);
  const primaryPlanEscalationRuleIds = asArray(primaryPlan?.escalationRuleIds);
  const primaryPlanGuardrails = asArray(primaryPlan?.guardrails);
  const primaryPlanSuccessMetrics = asArray(primaryPlan?.successMetrics);
  const primaryPlanVotes = asArray(primaryPlan?.votes);
  const primaryPlanResearchReferences = asArray(primaryPlan?.researchReferences);
  const primaryPlanProposals = asArray(primaryPlan?.proposals);
  const gopherAlignment = observability?.gopher_policy_alignment ?? 0;
  const quantumCoherence = observability?.quantum_coherence ?? 0;
  const pressureSignal = (observability?.horowitz_signals ?? []).find((signal) => signal.id === "UACP_PRESSURE")
    || (observability?.horowitz_signals ?? []).find((signal) => signal.id === "EXECUTION_PRESSURE");
  const pressureLoad = Math.max(observability?.uacp_pressure ?? 0, pressureSignal?.value ?? 0);
  const pressurePrimed = pressureLoad >= 0.85;
  const certaintyIndex = pressurePrimed ? "99999" : "0.00000";
  const entropyBudget = `${Math.max(0, 100 - quantumCoherence).toFixed(1)}%`;
  const determinismRatio = pressurePrimed ? "99999" : "0.00000";
  const primeState = pressureLoad >= 0.95 ? "PRIME LOCK" : pressurePrimed ? "PRESSURE COOKER" : "NO SIGNAL";

  const mappedNodes = useMemo(
    () =>
      asArray(primaryPlan?.graph?.nodes).map((node, index) => ({
        id: node.id,
        title: node.label,
        description: node.summary,
        entropy: normalizeEntropy(node.latencyMs, index),
        committee: resolveCommittee(node.ownerCommitteeId, committees),
        stage: node.stage,
      })),
    [committees, primaryPlan],
  );

  const handleCompile = async () => {
    const plan = await onCreatePlan();
    if (plan) {
      setActiveTab("execution");
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#050505] text-[#e0e0e0] font-sans selection:bg-blue-500/30 overflow-hidden relative rounded-[28px] border border-white/5">
      <div className="absolute inset-0 scanner pointer-events-none z-0 opacity-50" />

      <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-[#0a0a0a] z-10 shadow-2xl relative">
        <div className="flex items-center gap-6">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 via-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-500/20 group cursor-pointer overflow-hidden relative">
            <motion.div
              className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            />
            <Zap size={16} className="text-white fill-current relative z-10" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif italic text-xl tracking-tight leading-none text-white/90">The Deterministic Engine</span>
            <span className="text-[8px] font-mono tracking-[0.4em] uppercase text-blue-400/60 mt-1">UACP V3 / V2 Engine Core</span>
          </div>
        </div>

        <nav className="flex items-center gap-12 text-[10px] uppercase tracking-[0.25em] font-bold text-white/40">
          <TabButton active={activeTab === "intent"} onClick={() => setActiveTab("intent")} label="Signal Feed" />
          <TabButton active={activeTab === "execution"} onClick={() => setActiveTab("execution")} label="Probability Matrix" />
          <TabButton active={activeTab === "ops"} onClick={() => setActiveTab("ops")} label="Deterministic Ops" />

          <div className="h-8 w-px bg-white/5 mx-2" />

          <div className="flex items-center gap-3 px-4 py-1.5 border border-white/10 rounded-full bg-white/5 backdrop-blur-sm group cursor-help">
            <ShieldCheck size={12} className="text-blue-400" />
            <span className="text-[9px] font-mono lowercase tracking-normal text-white/60">
              policy {(gopherAlignment * 100).toFixed(1)}%
            </span>
            <ArrowUpRight size={10} className="text-white/20 group-hover:text-blue-400 transition-colors" />
          </div>
        </nav>
      </header>

      <main className="flex-1 min-h-0 grid grid-cols-12 gap-1 p-1 bg-white/5 overflow-hidden">
        <section className="col-span-3 min-h-0 bg-[#0a0a0a] flex flex-col border border-white/5 overflow-hidden glass-panel">
          <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
            <h2 className="text-[10px] uppercase tracking-[0.2em] text-blue-400 font-bold mb-1 flex items-center gap-2">
              <Search size={10} />
              Signal Ingestion Feed
            </h2>
            <p className="text-[10px] text-white/30 italic">Continuous scanning of research and opportunity nodes.</p>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-1 pb-24">
            <div className="space-y-px">
              {signals.length === 0 && (
                <div className="p-6 text-sm text-white/45 italic">
                  No live research signals are loaded yet. Compile a plan or refresh research ingress to pull public-source evidence into the engine.
                </div>
              )}
              {signals.map((signal) => (
                <div
                  key={signal.id}
                  className="p-4 bg-white/[0.01] hover:bg-white/[0.03] transition-colors border-b border-white/[0.03] last:border-0 group cursor-default"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[9px] font-mono text-blue-400/80 tracking-tighter uppercase">{signal.id}</span>
                    <span className="text-[9px] text-white/20 font-mono">{signal.category}</span>
                  </div>
                  <h3 className="text-xs text-white/80 font-light leading-snug group-hover:text-white transition-colors">{signal.title}</h3>
                  <div className="mt-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-blue-500 animate-pulse" />
                      <span className="text-[8px] font-mono text-white/30 tracking-widest uppercase">Match Strength</span>
                    </div>
                    <span className="text-[10px] font-mono text-green-500/80">{signal.strength}%</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-6 border-t border-white/5 mt-4">
              <h3 className="text-[9px] uppercase tracking-widest text-white/20 font-bold mb-4">Event Sequence Log</h3>
              <div className="space-y-3">
                {events.slice(0, 8).map((event) => (
                  <div key={event.id} className="flex gap-3 items-start group">
                    <div className="mt-1 w-1.5 h-1.5 rounded-full border border-white/20 group-hover:border-blue-400 transition-colors shrink-0" />
                    <div className="flex flex-col gap-0.5" title={event.message}>
                      <span className="text-[9px] text-white/80 font-mono tracking-tighter leading-none">{event.type}</span>
                      <span className="text-[9px] text-white/30 italic truncate max-w-[180px]">{event.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="p-6 border-t border-white/5 bg-black/40">
            <div className="flex justify-between items-center text-[10px] mb-3 text-white/40 uppercase font-mono tracking-tighter">
              <span>Policy Evaluation</span>
              <span className="text-blue-400">Gopher v4.1</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden relative">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-600 to-purple-600"
                animate={{ width: `${gopherAlignment * 100}%` }}
              />
            </div>
            <p className="mt-3 text-[9px] text-white/20 italic leading-relaxed">
              Plans stay reviewable before Sunnyvale admission opens execution.
            </p>
          </div>
        </section>

        <section className="col-span-6 min-h-0 flex flex-col bg-[#080808] border border-white/5 overflow-hidden technical-grid relative">
          <AnimatePresence mode="wait">
            {activeTab === "intent" && (
              <motion.div
                key="intent"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-12 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-12">
                  <div className="space-y-4">
                    <span className="text-[10px] uppercase tracking-[0.4em] text-white/20 font-mono">Input Deterministic Strategy</span>
                    <h1 className="font-serif italic text-5xl text-white/90 leading-tight">
                      "Probability is merely the shadow of a hidden order."
                    </h1>
                  </div>

                  <div className="w-full relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-indigo-500/10 rounded-xl blur-xl opacity-0 group-focus-within:opacity-100 transition duration-1000" />
                    <div className="relative glass-panel rounded-xl overflow-hidden border border-white/10 shadow-2xl">
                      <textarea
                        className="w-full h-48 bg-black/80 p-8 text-xl font-light italic text-white/90 placeholder:text-white/10 focus:outline-none resize-none transition-all focus:bg-black relative z-20"
                        placeholder="State your orchestration intent..."
                        value={intent}
                        onChange={(event) => onIntentChange(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            void handleCompile();
                          }
                        }}
                        autoFocus
                      />

                      {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/90 backdrop-blur-md z-50">
                          <div className="flex flex-col items-center gap-6">
                            <div className="relative">
                              <motion.div
                                className="w-16 h-16 rounded-full border-2 border-t-blue-500 border-r-transparent border-b-purple-500 border-l-transparent"
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                              />
                            </div>
                            <div className="space-y-2 text-center">
                              <span className="text-[11px] font-mono tracking-[0.3em] text-blue-400 block uppercase">Analyzing Complexity</span>
                              <span className="text-[9px] font-mono text-white/30 uppercase">Negotiating with UACP V3 planning core...</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    disabled={loading || !intent.trim()}
                    onClick={() => void handleCompile()}
                    className="w-full max-w-sm py-5 bg-white text-black text-[12px] uppercase tracking-[0.5em] font-black hover:bg-blue-600 hover:text-white transition-all disabled:opacity-10 group active:scale-[0.98] shadow-[0_20px_50px_rgba(255,255,255,0.1)] hover:shadow-blue-500/40"
                  >
                    <span className="flex items-center justify-center gap-4">
                      SEND SIGNAL / EXECUTE
                      <ChevronRight size={16} className="group-hover:translate-x-2 transition-transform" />
                    </span>
                  </button>
                  <p className="text-[9px] uppercase tracking-[0.4em] text-white/10 font-mono">Press [Enter] to transmit</p>
                </div>

                <div className="mt-auto flex justify-between items-end border-t border-white/5 pt-6 text-[9px] uppercase tracking-[0.2em] font-mono text-white/20">
                  <div className="space-y-1">
                    <div>Station: CONTROL_PLANE_ALPHA</div>
                    <div>Identity: {identity}</div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="text-3xl font-serif italic text-white/70">{entropyBudget}</div>
                    <div>Observed Entropy Envelope</div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === "execution" && (
              <motion.div
                key="execution"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-8 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex justify-between items-center mb-12 border-b border-white/5 pb-6">
                  <div className="space-y-1">
                    <h2 className="font-serif italic text-3xl text-white/90">Probability Matrix</h2>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold">Plan Hierarchy Revision {primaryPlan?.revision ?? 0}.0</p>
                  </div>
                  <div className="flex gap-4">
                    {primaryPlan && (
                      <div className="px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-md flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                        <span className="text-[9px] font-mono text-blue-200 uppercase tracking-widest">Directive: {primaryPlan.title}</span>
                      </div>
                    )}
                    <button
                      className="text-[10px] font-mono text-white/50 hover:text-blue-400 transition-colors px-4 py-2 border border-white/10 rounded uppercase tracking-widest"
                      onClick={() => primaryPlan && onRouteToSunnyvale(primaryPlan.id)}
                      disabled={!primaryPlan}
                    >
                      Route To Sunnyvale
                    </button>
                  </div>
                </div>

                {primaryPlan ? (
                  <>
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mb-8 p-4 bg-white/[0.02] border border-white/5 rounded-lg backdrop-blur-sm"
                    >
                      <div className="flex items-start gap-4">
                        <div className="mt-1 p-1.5 bg-blue-500/10 rounded text-blue-400">
                          <Info size={14} />
                        </div>
                        <div className="flex-1">
                          <span className="text-[9px] font-mono text-white/20 uppercase tracking-widest block mb-1">Strategic Briefing</span>
                          <p className="text-xs text-white/60 leading-relaxed italic">
                            "{primaryPlan.intent}" - {primaryPlan.objective}
                          </p>
                          <div className="mt-4 grid grid-cols-2 gap-3 text-[10px] font-mono uppercase tracking-[0.2em] text-white/35">
                            <div>Paying user: <span className="text-white/70 normal-case tracking-normal">{primaryPlan.payingUser || "Unknown"}</span></div>
                            <div>Pricing: <span className="text-white/70 normal-case tracking-normal">{primaryPlan.pricingModel || "Unknown"}</span></div>
                            <div>Risk tier: <span className="text-white/70 normal-case tracking-normal">{primaryPlan.riskTier || "unknown"}</span></div>
                            <div>Votes: <span className="text-white/70 normal-case tracking-normal">{primaryPlanVotes.length}</span></div>
                          </div>
                        </div>
                      </div>
                    </motion.div>

                    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.9fr_1.1fr] mb-10">
                      <InfoPanel title="Pillars">
                        <PillList items={primaryPlanPillars} />
                      </InfoPanel>
                      <InfoPanel title="Committees">
                        <PillList items={primaryPlanCommitteeIds.map((committeeId) => resolveCommittee(committeeId, committees))} />
                      </InfoPanel>
                      <InfoPanel title="Workflows">
                        <PillList items={primaryPlanWorkflowIds} />
                      </InfoPanel>
                      <InfoPanel title="Skills">
                        <PillList items={primaryPlanSkillIds} />
                      </InfoPanel>
                      <InfoPanel title="Escalation Rules">
                        <PillList items={primaryPlanEscalationRuleIds} />
                      </InfoPanel>
                      <InfoPanel title="Guardrails">
                        <TextList items={primaryPlanGuardrails} />
                      </InfoPanel>
                      <InfoPanel title="Success Metrics">
                        <TextList items={primaryPlanSuccessMetrics} />
                      </InfoPanel>
                      <InfoPanel title="Research Query">
                        <div className="text-xs text-white/70 leading-relaxed">
                          {primaryPlan.researchQuery || "No live research query was recorded for this plan."}
                        </div>
                      </InfoPanel>
                      <InfoPanel title="Live References">
                        {primaryPlanResearchReferences.length > 0 ? (
                          <ReferenceList references={primaryPlanResearchReferences} />
                        ) : (
                          <div className="text-xs text-white/45 italic">No live references attached to this plan.</div>
                        )}
                      </InfoPanel>
                      <InfoPanel title="Registry Proposals">
                        {primaryPlanProposals.length > 0 ? (
                          <ProposalList proposals={primaryPlanProposals} />
                        ) : (
                          <div className="text-xs text-white/45 italic">No new governance objects were proposed.</div>
                        )}
                      </InfoPanel>
                    </div>

                    <div className="mb-10">
                      <div className="flex items-center gap-3 mb-6">
                        <Layers size={14} className="text-blue-400" />
                        <span className="text-[10px] uppercase tracking-[0.3em] text-white/20 font-bold">Execution Topology</span>
                      </div>
                      <div className="overflow-x-auto custom-scrollbar pb-6">
                        <div className="flex items-center gap-12 min-w-max px-2 py-2">
                          {mappedNodes.map((node, index) => {
                            const middleIndex = Math.floor(mappedNodes.length / 2);
                            const isMiddle = index === middleIndex;
                            if (!isMiddle) return null;
                            return (
                              <div key={node.id} className="relative">
                                <motion.div
                                  initial={{ opacity: 0, y: 10 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ delay: index * 0.05 }}
                                  className="w-72 min-h-[260px] glass-panel p-6 relative group hover:border-blue-500/20 transition-colors"
                                >
                                  <div className="flex justify-between items-start mb-5">
                                    <div>
                                      <div className="text-[9px] font-mono uppercase tracking-[0.3em] text-white/20">{node.stage}</div>
                                      <div className="text-white text-lg mt-2">{node.title}</div>
                                    </div>
                                    <div className="px-2 py-1 rounded-full border border-white/10 text-[8px] font-mono uppercase tracking-widest text-blue-300">
                                      {node.committee}
                                    </div>
                                  </div>

                                  <div className="text-xs text-white/50 leading-relaxed font-light italic h-20 overflow-hidden mb-6 group-hover:text-white/80 transition-colors">
                                    {node.description}
                                  </div>

                                  <div className="grid grid-cols-2 gap-3 text-[9px] font-mono uppercase tracking-[0.2em] text-white/30 mb-4">
                                    <div>Entropy: <span className="text-white/70">{node.entropy}</span></div>
                                    <div>Node: <span className="text-white/70">{node.id}</span></div>
                                  </div>

                                  <div className="pt-5 border-t border-white/5">
                                    <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.2em] text-white/30">
                                      <Users size={10} className="text-blue-400" />
                                      <span>{node.committee}</span>
                                    </div>
                                  </div>

                                  <div className="absolute -bottom-2 -left-2 text-[7px] font-mono text-white/10 opacity-0 group-hover:opacity-100 transition-opacity">
                                    X: {index.toFixed(2)} Y: 0.00
                                  </div>
                                </motion.div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    <div className="mb-8">
                      <div className="flex items-center gap-3 mb-4">
                        <BrainCircuit size={14} className="text-blue-400" />
                        <span className="text-[10px] uppercase tracking-[0.3em] text-white/20 font-bold">Committee Votes</span>
                      </div>
                      <div className="space-y-3">
                        {primaryPlanVotes.map((vote) => (
                          <div key={`${vote.member}-${vote.model}`} className="glass-panel p-4 rounded-lg">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-white text-sm">{vote.member}</div>
                              <div className={`text-[9px] font-mono uppercase tracking-[0.3em] ${
                                vote.vote === "approve" ? "text-green-400" : vote.vote === "veto" ? "text-red-400" : "text-amber-300"
                              }`}>
                                {vote.vote}
                              </div>
                            </div>
                            <div className="mt-1 text-[10px] font-mono uppercase tracking-[0.2em] text-white/25">{vote.model}</div>
                            <div className="mt-3 text-xs text-white/55 italic">{vote.rationale}</div>
                          </div>
                        ))}
                        {primaryPlanVotes.length === 0 && (
                          <div className="glass-panel p-4 rounded-lg text-xs text-white/45 italic">
                            No committee votes are recorded for this plan revision.
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center gap-6 opacity-30">
                    <Layers size={48} className="animate-pulse" />
                    <span className="font-serif italic text-lg">No deterministic plans compiled.</span>
                  </div>
                )}

                <div className="mt-auto pt-12 flex justify-center">
                  {primaryPlan && (
                    <button
                      onClick={() => onRouteToSunnyvale(primaryPlan.id)}
                      className="px-12 py-3 border border-white/10 text-[10px] uppercase font-bold tracking-[0.4em] hover:bg-white hover:text-black transition-all shadow-xl active:scale-95"
                    >
                      Commit Sequence To Sunnyvale
                    </button>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === "ops" && (
              <motion.div
                key="ops"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex-1 flex flex-col p-12 pb-32 overflow-y-auto custom-scrollbar"
              >
                <div className="flex justify-between items-end mb-12 border-b border-white/5 pb-6">
                  <div className="space-y-1">
                    <h2 className="font-serif italic text-3xl text-white/90">Archives of Order</h2>
                    <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold">Live Execution Telemetry</p>
                  </div>
                  <div className="flex items-center gap-4 text-right">
                    <div className="flex flex-col">
                      <span className="text-[8px] font-mono text-white/30">Latency</span>
                      <span className="text-xs font-mono text-blue-400">{observability?.classical_latency?.toFixed(1) || "0"}ms</span>
                    </div>
                    <div className="h-8 w-px bg-white/5" />
                    <div className="flex flex-col">
                      <span className="text-[8px] font-mono text-white/30">Coherence</span>
                      <span className="text-xs font-mono text-purple-400">{observability?.quantum_coherence?.toFixed(1) || "0"}%</span>
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-8 pr-6">
                  {runs.map((run) => {
                    const compiledPlan = plans.find((plan) => plan.id === run.planId);
                    const artifact = run.artifact;

                    return (
                    <div key={run.id} className="glass-panel p-8 relative overflow-hidden group">
                      <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-20 group-hover:opacity-100 transition-opacity" />

                      <div className="flex justify-between items-start mb-8">
                        <div className="space-y-2">
                          <div className="flex items-center gap-4">
                            <span className="font-mono text-xs font-bold text-white tracking-widest">{run.id}</span>
                            <span
                              className={`text-[9px] px-2 py-0.5 border rounded-full uppercase tracking-widest font-bold ${
                                run.status === "completed"
                                  ? "border-green-500/20 text-green-500 bg-green-500/5"
                                  : "border-blue-500/20 text-blue-400 bg-blue-500/5"
                              }`}
                            >
                              {run.status.toUpperCase()}
                            </span>
                          </div>
                          <button
                            onClick={() => onRouteToSunnyvale(run.planId)}
                            className="text-[10px] text-white/40 font-mono italic hover:text-blue-300 transition-colors"
                          >
                            Compiled Reference: {artifact?.title || compiledPlan?.title || run.planId}
                          </button>
                        </div>
                        <div className="text-right">
                          <div className="text-4xl font-serif italic text-white/90 tabular-nums">{run.progress}%</div>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div className="flex justify-between text-[10px] font-mono uppercase tracking-[0.2em] text-white/40">
                          <span className="flex items-center gap-2">
                            <Disc size={10} className={run.status === "completed" ? "" : "animate-spin"} />
                            Active Phase: {run.currentStage}
                          </span>
                          <span>TS INITIATION: {new Date(run.startedAt).toLocaleTimeString()}</span>
                        </div>
                        <div className="w-full h-2 bg-white/5 overflow-hidden relative rounded-full">
                          <motion.div
                            className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 shadow-[0_0_15px_rgba(59,130,246,0.6)]"
                            animate={{ width: `${run.progress}%` }}
                          />
                          <motion.div
                            animate={{ x: ["0%", "100%"], opacity: [0, 1, 0] }}
                            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                            className="absolute top-0 bottom-0 w-20 bg-white/20 skew-x-12"
                          />
                        </div>

                        <div className="grid grid-cols-3 gap-3 text-[10px] font-mono uppercase tracking-[0.2em] text-white/30">
                          <div>Progress: <span className="text-white/70">{run.progress}%</span></div>
                          <div>Approvals: <span className="text-white/70">{run.approvals}</span></div>
                          <div>Evidence: <span className="text-white/70">{run.evidenceCount}</span></div>
                        </div>
                        {run.stages && run.stages.length > 0 && (
                          <div className="grid grid-cols-1 gap-2 pt-2">
                            {run.stages.map((stage) => (
                              <div key={`${run.id}-${stage.stage}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                                <div className="flex items-center justify-between gap-3">
                                  <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">{stage.stage}</span>
                                  <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-white/30">
                                    {stage.sourceCount ? `${stage.sourceCount} sources` : stage.status}
                                  </span>
                                </div>
                                <p className="mt-2 text-xs text-white/60 italic leading-relaxed">{stage.summary}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {run.status === "completed" && run.output && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="mt-8 p-6 bg-blue-500/5 border border-blue-500/10 rounded-lg relative overflow-hidden"
                        >
                          <div className="absolute top-0 right-0 p-2 text-blue-500/20">
                            <Activity size={40} className="opacity-10" />
                          </div>
                          <div className="flex gap-4 relative z-10">
                            <div className="shrink-0 p-2 bg-blue-500/10 rounded text-blue-400 h-fit">
                              <BrainCircuit size={16} />
                            </div>
                            <div className="flex-1 space-y-4">
                              <div>
                                <span className="text-[9px] font-mono text-blue-300 uppercase tracking-widest block">Deterministic Outcome Report</span>
                                <p className="text-xs text-white/70 leading-relaxed font-light italic mt-2">{run.output}</p>
                              </div>

                              {artifact ? (
                                <div className="space-y-4">
                                  <div className="grid grid-cols-2 gap-3">
                                    <ArtifactStat label="Artifact" value={artifact.id} />
                                    <ArtifactStat label="Objective" value={artifact.title} />
                                    <ArtifactStat label="Sources" value={String(artifact.sourceCount)} />
                                    <ArtifactStat label="Workflows" value={artifact.workflowIds.join(", ") || "none"} />
                                    <ArtifactStat label="Skills" value={artifact.skillIds.join(", ") || "none"} />
                                    <ArtifactStat label="Signal Sources" value={artifact.signalSources.join(", ") || "none"} />
                                    <ArtifactStat label="Approvals" value={String(run.approvals)} />
                                    <ArtifactStat label="Evidence" value={String(run.evidenceCount)} />
                                  </div>

                                  <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                                    <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-white/25 mb-2">Compiled Artifact</div>
                                    <p className="text-sm text-white/75">{artifact.objective}</p>
                                    <p className="mt-3 text-xs text-white/60 italic leading-relaxed">{artifact.governanceSummary}</p>
                                    <div className="mt-4 grid grid-cols-1 gap-2">
                                      {artifact.phaseOutputs.map((phase) => (
                                        <div key={`${artifact.id}-${phase.stage}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                                          <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-blue-300">{phase.stage}</div>
                                          <div className="mt-2 text-xs text-white/65">{phase.summary}</div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>

                                  <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                                    <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-white/25 mb-2">Live References</div>
                                    <ReferenceList references={artifact.references} />
                                  </div>

                                  <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                                    <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-white/25 mb-2">Next Action</div>
                                    <p className="text-sm text-white/70">{artifact.nextAction}</p>
                                  </div>

                                  <button
                                    onClick={() => onRouteToSunnyvale(run.planId)}
                                    className="px-4 py-2 border border-white/10 text-[10px] uppercase tracking-[0.3em] font-bold hover:bg-white hover:text-black transition-all"
                                  >
                                    Open Compiled Artifact
                                  </button>
                                </div>
                              ) : compiledPlan ? (
                                <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                                  <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-white/25 mb-2">Plan Reference</div>
                                  <p className="text-sm text-white/75">{compiledPlan.objective}</p>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </div>
                  )})}

                  {runs.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center opacity-20 space-y-6">
                      <Lock size={48} />
                      <span className="font-serif italic text-xl">Operational plane locked. Route a reviewed plan into Sunnyvale first.</span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        <section className="col-span-3 min-h-0 bg-[#0a0a0a] flex flex-col border border-white/5 overflow-hidden glass-panel">
          <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
            <h2 className="text-[10px] uppercase tracking-[0.2em] text-purple-400 font-bold mb-1 flex items-center gap-2">
              <Activity size={10} />
              Asset Convergence
            </h2>
            <p className="text-[10px] text-white/30 italic">Real-time heuristics & deterministic alpha</p>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-24 space-y-10">
            {(observability?.market_convergence ?? []).map((metric, index) => (
              <ConvergenceBar
                key={`${metric.label}-${index}`}
                label={metric.label}
                value={metric.value}
                progress={metric.progress}
                color={index % 2 === 0 ? "blue" : "purple"}
              />
            ))}

            <div className="pt-8 border-t border-white/5 space-y-6">
              <h3 className="text-[9px] uppercase tracking-widest text-white/20 font-bold">Observability Signals</h3>
              {(observability?.horowitz_signals ?? []).map((signal, index) => (
                <div key={`${signal.id}-${index}`} className="space-y-4">
                  <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                      <span className="text-[9px] font-mono text-white/40 uppercase tracking-tighter">{signal.id}</span>
                      <span className="text-xs font-serif italic text-white/80">Value Trace</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] font-mono text-white/60">{formatSignalValue(signal.value)}</span>
                      <span
                        className={`text-[9px] font-mono uppercase font-bold ${
                          signal.trend === "up" ? "text-green-500" : signal.trend === "down" ? "text-red-400" : "text-blue-400"
                        }`}
                      >
                        {signal.trend}
                      </span>
                    </div>
                  </div>

                  <div
                    className={`h-16 w-full overflow-hidden transition-all duration-700 ${
                      signal.value >= 0.95 ? "opacity-100 grayscale-0" : "opacity-50 grayscale hover:grayscale-0"
                    }`}
                  >
                    {signal.history && signal.history.length > 1 ? (
                      <ResponsiveContainer width="100%" height="100%" minHeight={60} minWidth={100}>
                        <AreaChart data={toHistorySeries(signal.history)}>
                          <defs>
                            <linearGradient id={`grad-${signal.id}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor={signal.trend === "up" ? "#10b981" : signal.trend === "down" ? "#f87171" : "#3b82f6"} stopOpacity={0.3} />
                              <stop offset="95%" stopColor={signal.trend === "up" ? "#10b981" : signal.trend === "down" ? "#f87171" : "#3b82f6"} stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <Area
                            type="monotone"
                            dataKey="val"
                            stroke={signal.trend === "up" ? "#10b981" : signal.trend === "down" ? "#f87171" : "#3b82f6"}
                            fillOpacity={1}
                            fill={`url(#grad-${signal.id})`}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center">
                        <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className={`h-full ${
                              signal.trend === "up" ? "bg-green-500/60" : signal.trend === "down" ? "bg-red-400/60" : "bg-blue-500/60"
                            }`}
                            style={{ width: `${signal.value * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[10px] uppercase tracking-[0.25em] text-white/25">Pressure state</div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-green-400">
                    {primeState}
                  </div>
                </div>
                <div className="mt-2 text-sm text-white/55">
                  Pressure is derived from live runs, archives, workers, providers, research, backend events, and escalations.
                </div>
              </div>
            </div>

            <div className="p-5 glass-panel rounded border-white/5 bg-white/[0.01] mt-8">
              <h3 className="text-[9px] uppercase tracking-widest text-white/30 font-bold mb-4 flex items-center gap-2">
                <Info size={10} className="text-blue-400" />
                Agent Consensus
              </h3>
              <div className="text-xs text-white/60 italic leading-relaxed font-light">
                "The engine extracts order from signal. UACP V3 decides whether that order is admissible, profitable, and replayable."
              </div>
              <div className="mt-4 flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-blue-500/10 flex items-center justify-center text-[8px] text-blue-400 italic">g</div>
                <span className="text-[8px] font-mono text-white/20 uppercase tracking-widest">- UACP V3 CONTROL PLANE</span>
              </div>
            </div>
          </div>

          <div className="p-8 border-t border-white/5 bg-black/40">
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center text-[9px] font-mono text-white/20 uppercase tracking-widest">
                <span>Certainty Index</span>
                <div className="flex items-center gap-3">
                  <span className="text-green-300 text-[9px]">{primeState}</span>
                  <span className="text-white text-sm font-serif italic">{certaintyIndex}</span>
                </div>
              </div>
              <div className="h-[2px] w-full bg-white/5 relative overflow-hidden">
                <motion.div
                  className="absolute inset-0 bg-blue-500/40"
                  animate={{ x: [-100, 400] }}
                  transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
                />
                <div
                  className="absolute right-0 top-0 h-full bg-blue-400 shadow-[0_0_10px_rgba(59,130,246,1)]"
                  style={{ width: `${pressurePrimed ? 100 : Math.max(0, Math.min(100, pressureLoad * 100))}%` }}
                />
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="h-8 bg-[#050505] border-t border-white/10 flex items-center justify-between px-8 text-[9px] uppercase tracking-[0.3em] text-white/30 font-mono z-10">
        <div className="flex gap-10">
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
            Uplink Established
          </span>
          <span className="flex items-center gap-2">
            <Activity size={10} className="text-blue-500/50" />
            Control Plane: Stable
          </span>
          <span className="flex items-center gap-2">
            <Cpu size={10} className="text-purple-500/50" />
            Determinism Ratio: {determinismRatio}
          </span>
        </div>
        <div className="flex gap-6 items-center">
          <span>AI Studio Build 2026.05.08</span>
          <div className="h-3 w-px bg-white/10" />
          <span>(c) DETERMINISTIC RESEARCH - UACP V3</span>
        </div>
      </footer>
    </div>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`relative py-1 transition-all group outline-none ${active ? "text-white" : "text-white/40 hover:text-white/70"}`}
    >
      {label}
      {active && (
        <motion.div
          layoutId="engine-tab"
          className="absolute -bottom-1 left-0 right-0 h-[2px] bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]"
        />
      )}
    </button>
  );
}

function ConvergenceBar({
  label,
  value,
  progress,
  color,
}: {
  label: string;
  value: string;
  progress: number;
  color: "blue" | "purple";
}) {
  return (
    <div className="group cursor-default">
      <div className="flex justify-between items-end mb-3">
        <span className="text-[10px] text-white/40 italic font-light tracking-wide group-hover:text-white/60 transition-colors">{label}</span>
        <span className="text-green-400 font-mono font-bold tracking-tighter text-xs">{value}</span>
      </div>
      <div className="h-10 w-full glass-panel overflow-hidden relative group-hover:border-white/10 transition-colors bg-white/[0.01]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress * 100}%` }}
          className={`absolute bottom-0 left-0 h-full ${color === "blue" ? "bg-blue-500/10" : "bg-purple-500/10"}`}
        />
        <div className="absolute inset-0 flex items-center px-4 overflow-hidden">
          <div className="w-full flex gap-0.5 opacity-10">
            {[...Array(40)].map((_, index) => (
              <div key={index} className="flex-1 h-3 border-r border-white/20 last:border-0" />
            ))}
          </div>
        </div>
        <motion.div
          initial={{ x: -200 }}
          animate={{ x: 400 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          className={`absolute top-0 w-32 h-[1px] ${color === "blue" ? "bg-blue-400/50" : "bg-purple-400/50"} blur-sm`}
        />
      </div>
    </div>
  );
}

function InfoPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="glass-panel p-4 rounded-lg min-h-0">
      <div className="text-[9px] font-mono text-white/20 uppercase tracking-widest mb-3">{title}</div>
      {children}
    </div>
  );
}

function ArtifactStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
      <div className="text-[9px] font-mono uppercase tracking-[0.25em] text-white/25">{label}</div>
      <div className="mt-2 text-xs text-white/75 break-all">{value}</div>
    </div>
  );
}

function ReferenceList({
  references,
}: {
  references: Array<{ title: string; source: string; url?: string; publishedAt?: string }>;
}) {
  return (
    <div className="max-h-64 overflow-y-auto custom-scrollbar pr-2 space-y-3">
      {references.map((reference) => (
        <div key={`${reference.source}-${reference.title}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <div className="text-xs text-white/80 leading-relaxed">{reference.title}</div>
          <div className="mt-2 text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
            {reference.source}
            {reference.publishedAt ? ` / ${new Date(reference.publishedAt).toLocaleDateString()}` : ""}
          </div>
          {reference.url && (
            <a
              href={reference.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-[10px] font-mono uppercase tracking-[0.2em] text-white/45 hover:text-blue-300 transition-colors"
            >
              Open source
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

function ProposalList({
  proposals,
}: {
  proposals: Array<{ id: string; type: string; name: string; rationale: string; status: string }>;
}) {
  return (
    <div className="max-h-64 overflow-y-auto custom-scrollbar pr-2 space-y-3">
      {proposals.map((proposal) => (
        <div key={proposal.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-white/80">{proposal.name}</div>
            <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-amber-300">{proposal.status}</div>
          </div>
          <div className="mt-2 text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">{proposal.type}</div>
          <div className="mt-2 text-xs text-white/60 italic leading-relaxed">{proposal.rationale}</div>
        </div>
      ))}
    </div>
  );
}

function PillList({ items }: { items: string[] }) {
  return (
    <div className="max-h-40 overflow-y-auto custom-scrollbar pr-2 flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className="px-3 py-1 rounded-full border border-white/10 text-[10px] font-mono text-white/60">
          {item}
        </span>
      ))}
    </div>
  );
}

function TextList({ items }: { items: string[] }) {
  return (
    <div className="max-h-48 overflow-y-auto custom-scrollbar pr-2 space-y-2">
      {items.map((item) => (
        <div key={item} className="flex gap-2 text-xs text-white/60 italic leading-relaxed">
          <Play size={10} className="mt-0.5 shrink-0 text-blue-400" />
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}

function asArray<T>(value: T[] | null | undefined) {
  return Array.isArray(value) ? value : [];
}

function resolveCommittee(id: string, committees: Committee[]) {
  return committees.find((committee) => committee.id === id)?.name || id;
}

function normalizeEntropy(latencyMs: number, index: number) {
  const value = Math.min(0.92, Math.max(0.12, latencyMs / 420 + index * 0.03));
  return value.toFixed(2);
}

function toHistorySeries(values: number[]) {
  return values.map((value, index) => ({
    index,
    val: Math.max(0, Math.min(1, value)),
  }));
}

function formatSignalValue(value: number) {
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(2)}%`;
}
