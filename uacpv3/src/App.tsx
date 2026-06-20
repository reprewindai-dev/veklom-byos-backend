import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BadgeDollarSign,
  BookMarked,
  BrainCircuit,
  Building2,
  CheckCircle2,
  ChevronRight,
  Database,
  Disc,
  Gavel,
  Layers,
  LibraryBig,
  LoaderCircle,
  Network,
  Radar,
  ShieldCheck,
  Users,
  Zap,
} from "lucide-react";
import { motion } from "motion/react";
import { DeterministicEngineSurface } from "./components/DeterministicEngineSurface";
import type {
  ArchiveEntry,
  BackendProductEvent,
  BackendTruthSummary,
  BootstrapPayload,
  Committee,
  CommandCenterSnapshot,
  ControlTelemetry,
  EngineObservability,
  EngineSignal,
  EventItem,
  GovernedRun,
  InstitutionalPlan,
  ModelProviderSnapshot,
  OperatorCommittee,
  OperatingSignal,
  OperatorRun,
  OperatorWorker,
  Pillar,
  ResearchSignal,
  ResearchSourceStatus,
  SkillArtifact,
  StatusPageSnapshot,
  SunnyvaleInternalSnapshot,
  SurfaceId,
  WorkerRuntimeState,
  WorkflowArtifact,
} from "./types";

type DataState = {
  bootstrap: BootstrapPayload | null;
  pillars: Pillar[];
  committees: Committee[];
  operatorCommittees: OperatorCommittee[];
  workers: OperatorWorker[];
  workerRuntime: WorkerRuntimeState[];
  operatorRuns: OperatorRun[];
  skills: SkillArtifact[];
  workflows: WorkflowArtifact[];
  backendSummary: BackendTruthSummary | null;
  backendEvents: BackendProductEvent[];
  commandCenter: CommandCenterSnapshot | null;
  sunnyvaleInternal: SunnyvaleInternalSnapshot | null;
  plans: InstitutionalPlan[];
  runs: GovernedRun[];
  events: EventItem[];
  archives: ArchiveEntry[];
  researchSignals: ResearchSignal[];
  researchStatus: ResearchSourceStatus[];
  engineSignals: EngineSignal[];
  telemetry: ControlTelemetry | null;
  observability: EngineObservability | null;
  providerSnapshot: ModelProviderSnapshot | null;
  statusPage: StatusPageSnapshot | null;
};

const initialState: DataState = {
  bootstrap: null,
  pillars: [],
  committees: [],
  operatorCommittees: [],
  workers: [],
  workerRuntime: [],
  operatorRuns: [],
  skills: [],
  workflows: [],
  backendSummary: null,
  backendEvents: [],
  commandCenter: null,
  sunnyvaleInternal: null,
  plans: [],
  runs: [],
  events: [],
  archives: [],
  researchSignals: [],
  researchStatus: [],
  engineSignals: [],
  telemetry: null,
  observability: null,
  providerSnapshot: null,
  statusPage: null,
};

const surfaceLabels: Record<SurfaceId, string> = {
  "deterministic-engine": "Deterministic Engine",
  sunnyvale: "Sunnyvale",
  "silicon-valley": "Silicon Valley",
  archives: "Archives",
  status: "Status",
};

export default function App() {
  const [state, setState] = useState<DataState>(initialState);
  const [activeSurface, setActiveSurface] = useState<SurfaceId>("deterministic-engine");
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [intent, setIntent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [launchingPlanId, setLaunchingPlanId] = useState<string | null>(null);
  const [launchRunError, setLaunchRunError] = useState<string | null>(null);
  const [eventStreamStatus, setEventStreamStatus] = useState({
    connected: false,
    redisBacked: false,
    route: "/api/v1/internal/uacp/event-stream",
  });
  const socketRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    void loadAll();

    const interval = setInterval(() => {
      void Promise.all([
        fetchJson<ControlTelemetry>("/api/v1/gpc/stats"),
        fetchJson<EngineObservability>("/api/v1/gpc/stats"),
        fetchJson<WorkerRuntimeState[]>("/api/operator-runtime"),
        fetchJson<OperatorRun[]>("/api/operator-runs"),
        fetchJson<BackendTruthSummary>("/api/backend-summary"),
        fetchJson<BackendProductEvent[]>("/api/backend-events"),
        fetchJson<CommandCenterSnapshot>("/api/command-center"),
        fetchJson<SunnyvaleInternalSnapshot>("/api/sunnyvale-internal"),
        fetchJson<ModelProviderSnapshot>("/api/provider-readiness"),
        fetchJson<StatusPageSnapshot>("/api/status-page"),
      ])
        .then(([telemetry, observability, workerRuntime, operatorRuns, backendSummary, backendEvents, commandCenter, sunnyvaleInternal, providerSnapshot, statusPage]) =>
          setState((current) => ({
            ...current,
            telemetry,
            observability,
            workerRuntime,
            operatorRuns,
            backendSummary,
            backendEvents,
            commandCenter,
            sunnyvaleInternal,
            providerSnapshot,
            statusPage,
          })),
        )
        .catch(() => {});
    }, 4000);

    connectEventStream();
    connectSocket();

    return () => {
      clearInterval(interval);
      socketRef.current?.close();
      eventSourceRef.current?.close();
    };
  }, []);

  const approvedSkills = useMemo(
    () => state.skills.filter((skill) => skill.status === "approved").length,
    [state.skills],
  );

  const activePlan = useMemo(() => {
    if (selectedPlanId) {
      const selected = state.plans.find((plan) => plan.id === selectedPlanId);
      if (selected) return selected;
    }
    return state.plans[0];
  }, [selectedPlanId, state.plans]);

  const latestRun = state.runs[0];

  async function loadAll() {
    const [
      bootstrap,
      pillars,
      committees,
      operatorCommittees,
      workers,
      workerRuntime,
      operatorRuns,
      skills,
      workflows,
      backendSummary,
      backendEvents,
      commandCenter,
      sunnyvaleInternal,
      providerSnapshot,
      plans,
      runs,
      events,
      archives,
      researchSignals,
      researchStatus,
      engineSignals,
      telemetry,
      observability,
      statusPage,
    ] = await Promise.all([
      fetchJson<BootstrapPayload>("/api/bootstrap"),
      fetchJson<Pillar[]>("/api/pillars"),
      fetchJson<Committee[]>("/api/committees"),
      fetchJson<OperatorCommittee[]>("/api/operator-committees"),
      fetchJson<OperatorWorker[]>("/api/operators"),
      fetchJson<WorkerRuntimeState[]>("/api/operator-runtime"),
      fetchJson<OperatorRun[]>("/api/operator-runs"),
      fetchJson<SkillArtifact[]>("/api/enterprise-skills"),
      fetchJson<WorkflowArtifact[]>("/api/workflows"),
      fetchJson<BackendTruthSummary>("/api/backend-summary"),
      fetchJson<BackendProductEvent[]>("/api/backend-events"),
      fetchJson<CommandCenterSnapshot>("/api/command-center"),
      fetchJson<SunnyvaleInternalSnapshot>("/api/sunnyvale-internal"),
      fetchJson<ModelProviderSnapshot>("/api/provider-readiness"),
      fetchJson<InstitutionalPlan[]>("/api/v1/gpc/compile"),
      fetchJson<GovernedRun[]>("/api/v1/gpc/runs"),
      fetchJson<EventItem[]>("/api/v1/gpc/events"),
      fetchJson<ArchiveEntry[]>("/api/archives"),
      fetchJson<ResearchSignal[]>("/api/research-signals"),
      fetchJson<ResearchSourceStatus[]>("/api/research-status"),
      fetchJson<EngineSignal[]>("/api/v1/gpc/ssrn-signals"),
      fetchJson<ControlTelemetry>("/api/v1/gpc/stats"),
      fetchJson<EngineObservability>("/api/v1/gpc/stats"),
      fetchJson<StatusPageSnapshot>("/api/status-page"),
    ]);

    setState({
      bootstrap,
      pillars,
      committees,
      operatorCommittees,
      workers,
      workerRuntime,
      operatorRuns,
      skills,
      workflows,
      backendSummary,
      backendEvents,
      commandCenter,
      sunnyvaleInternal,
      providerSnapshot,
      plans,
      runs,
      events,
      archives,
      researchSignals,
      researchStatus,
      engineSignals,
      telemetry,
      observability,
      statusPage,
    });

    if (!selectedPlanId && plans[0]) {
      setSelectedPlanId(plans[0].id);
    }
  }

  function connectSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}`);
    socketRef.current = socket;

    socket.onmessage = (event) => applyRealtimePayload(JSON.parse(event.data));

    socket.onclose = () => {
      setTimeout(connectSocket, 2500);
    };
  }

  function applyRealtimePayload(payload: any) {
    if (payload.type === "event") {
      setState((current) => ({
        ...current,
        events: current.events.some((item) => item.id === payload.data.id)
          ? current.events
          : [payload.data, ...current.events].slice(0, 120),
      }));
    }

    if (payload.type === "archive") {
      setState((current) => ({
        ...current,
        archives: current.archives.some((item) => item.id === payload.data.id)
          ? current.archives
          : [payload.data, ...current.archives].slice(0, 80),
      }));
    }

    if (payload.type === "run_update") {
      setState((current) => ({
        ...current,
        runs: upsertById(current.runs, payload.data),
      }));
    }

    if (payload.type === "operator_run_update") {
      setState((current) => ({
        ...current,
        operatorRuns: upsertById(current.operatorRuns, payload.data),
      }));
    }

    if (payload.type === "backend_event") {
      setState((current) => ({
        ...current,
        backendEvents: current.backendEvents.some((item) => item.eventId === payload.data.eventId)
          ? current.backendEvents
          : [payload.data, ...current.backendEvents].slice(0, 200),
      }));
    }
  }

  function connectEventStream() {
    const source = new EventSource("/api/v1/internal/uacp/event-stream");
    eventSourceRef.current = source;

    source.addEventListener("uacp_frame", (event) => {
      const envelope = JSON.parse((event as MessageEvent).data);
      setEventStreamStatus({
        connected: true,
        redisBacked: Boolean(envelope.redis_backed),
        route: "/api/v1/internal/uacp/event-stream",
      });

      if (envelope.payload?.type === "stream_init") {
        const data = envelope.payload.data || {};
        setState((current) => ({
          ...current,
          events: Array.isArray(data.recentEvents) ? data.recentEvents : current.events,
          runs: Array.isArray(data.recentRuns) ? data.recentRuns : current.runs,
          archives: Array.isArray(data.recentArchives) ? data.recentArchives : current.archives,
        }));
        return;
      }

      if (envelope.payload?.type !== "heartbeat") {
        applyRealtimePayload(envelope.payload);
      }
    });

    source.onerror = () => {
      setEventStreamStatus((current) => ({ ...current, connected: false }));
    };
  }

  async function createPlan(): Promise<InstitutionalPlan | null> {
    if (!intent.trim() || submitting) return null;
    setSubmitting(true);
    try {
      const plan = await fetchJson<InstitutionalPlan>("/api/v1/gpc/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent }),
      });
      setState((current) => ({
        ...current,
        plans: [plan, ...current.plans.filter((entry) => entry.id !== plan.id)],
      }));
      setSelectedPlanId(plan.id);
      setIntent("");
      await loadAll();
      return plan;
    } finally {
      setSubmitting(false);
    }
  }

  async function launchRun(planId: string) {
    if (launchingPlanId === planId) return;

    setLaunchingPlanId(planId);
    setLaunchRunError(null);

    try {
      const run = await fetchJson<GovernedRun>("/api/v1/gpc/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planId }),
      });

      setState((current) => ({
        ...current,
        runs: [run, ...current.runs.filter((entry) => entry.id !== run.id)],
      }));
    } catch (error) {
      setLaunchRunError(error instanceof Error ? error.message : "Unable to launch governed run.");
    } finally {
      setLaunchingPlanId(null);
    }
  }

  function routeToSunnyvale(planId: string) {
    setSelectedPlanId(planId);
    setActiveSurface("sunnyvale");
  }

  return (
    <div className="h-screen flex flex-col bg-[#050505] text-[#e0e0e0] font-sans selection:bg-blue-500/30 overflow-hidden relative">
      <div className="absolute inset-0 scanner pointer-events-none z-0 opacity-40" />

      <header className="relative z-10 border-b border-white/10 bg-[#0a0a0a] shadow-2xl">
        <div className="h-16 px-8 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 via-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-500/20 overflow-hidden relative">
              <motion.div
                className="absolute inset-0 bg-white/20 opacity-0 hover:opacity-100 transition-opacity"
                animate={{ rotate: 360 }}
                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              />
              <Zap size={16} className="text-white fill-current relative z-10" />
            </div>
            <div className="flex flex-col">
              <span className="font-serif italic text-xl tracking-tight leading-none text-white/90">UACP V3</span>
              <span className="text-[8px] font-mono tracking-[0.4em] uppercase text-blue-400/60 mt-1">
                V2 executes / V3 governs
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-10 text-[10px] uppercase tracking-[0.25em] font-bold text-white/40">
            {(state.bootstrap?.surfaces ?? []).map((surface) => (
              <SurfaceButton
                key={surface.id}
                active={activeSurface === surface.id}
                label={surface.name}
                onClick={() => setActiveSurface(surface.id)}
              />
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <MetricPill label="Policy" value={`${percent(state.telemetry?.policyAlignment)}%`} />
            <MetricPill label="LLM" value={providerLabel(state.providerSnapshot?.activeProvider)} />
            <MetricPill label="Committees" value={String(state.committees.length)} />
            <MetricPill label="Skills" value={String(approvedSkills)} />
          </div>
        </div>

        <div className="px-8 pb-4 grid grid-cols-1 gap-3 lg:grid-cols-[1.25fr_1fr]">
          <div className="flex flex-wrap gap-2">
            {(state.bootstrap?.doctrines ?? []).map((doctrine) => (
              <span
                key={doctrine}
                className="px-3 py-1 rounded-full border border-white/10 bg-white/[0.03] text-[10px] text-white/55"
              >
                {doctrine}
              </span>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <SummaryCard label="Top plan" value={activePlan?.title || "No active plan"} />
            <SummaryCard label="Risk tier" value={activePlan?.riskTier || "idle"} />
            <SummaryCard label="Revision" value={activePlan ? String(activePlan.revision) : "0"} />
            <SummaryCard label="Votes" value={activePlan ? String(activePlan.votes.length) : "0"} />
          </div>
        </div>
      </header>

      <main className="relative z-10 flex-1 overflow-hidden p-4">
        {activeSurface === "deterministic-engine" ? (
          <DeterministicEngineSurface
            identity={state.bootstrap?.userEmail || "FOUNDER"}
            intent={intent}
            loading={submitting}
            plans={state.plans}
            runs={state.runs}
            events={state.events}
            committees={state.committees}
            signals={state.engineSignals}
            observability={state.observability}
            onIntentChange={setIntent}
            onCreatePlan={createPlan}
            onRouteToSunnyvale={routeToSunnyvale}
          />
        ) : (
          <div className="h-full min-h-0 grid grid-cols-12 gap-4">
            {activeSurface === "sunnyvale" && (
              <SunnyvaleSurface
                plan={activePlan}
                plans={state.plans}
                runs={state.runs}
                workflows={state.workflows}
                committees={state.committees}
                workers={state.workers}
                sunnyvaleInternal={state.sunnyvaleInternal}
                launchingPlanId={launchingPlanId}
                launchRunError={launchRunError}
                onSelectPlan={(planId) => setSelectedPlanId(planId)}
                onLaunchRun={launchRun}
              />
            )}

            {activeSurface === "silicon-valley" && (
              <SiliconValleySurface
                pillars={state.pillars}
                committees={state.committees}
                operatorCommittees={state.operatorCommittees}
                workers={state.workers}
                workerRuntime={state.workerRuntime}
                operatorRuns={state.operatorRuns}
                skills={state.skills}
                backendSummary={state.backendSummary}
                backendEvents={state.backendEvents}
                commandCenter={state.commandCenter}
                providerSnapshot={state.providerSnapshot}
                researchStatus={state.researchStatus}
                telemetry={state.telemetry}
                observability={state.observability}
              />
            )}

            {activeSurface === "archives" && (
              <ArchivesSurface
                archives={state.archives}
                events={state.events}
                latestRun={latestRun}
                eventStreamStatus={eventStreamStatus}
              />
            )}

            {activeSurface === "status" && (
              <StatusSurface statusPage={state.statusPage} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function SunnyvaleSurface({
  plan,
  plans,
  runs,
  workflows,
  committees,
  workers,
  sunnyvaleInternal,
  launchingPlanId,
  launchRunError,
  onSelectPlan,
  onLaunchRun,
}: {
  plan?: InstitutionalPlan;
  plans: InstitutionalPlan[];
  runs: GovernedRun[];
  workflows: WorkflowArtifact[];
  committees: Committee[];
  workers: OperatorWorker[];
  sunnyvaleInternal: SunnyvaleInternalSnapshot | null;
  launchingPlanId: string | null;
  launchRunError: string | null;
  onSelectPlan: (planId: string) => void;
  onLaunchRun: (planId: string) => Promise<void>;
}) {
  const [activeRoom, setActiveRoom] = useState<"overview" | "evaluation-surgeon" | "hub-growth-navigator" | "field-intelligence">("overview");
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<string | null>(null);
  const [selectedGrowthId, setSelectedGrowthId] = useState<string | null>(null);
  const [selectedIntelligenceId, setSelectedIntelligenceId] = useState<string | null>(null);

  const evaluationSignals = sunnyvaleInternal?.evaluationSignals ?? [];
  const growthSignals = sunnyvaleInternal?.growthOpportunities ?? [];
  const intelligenceSignals = sunnyvaleInternal?.fieldIntelligence ?? [];
  const selectedEvaluation = evaluationSignals.find((signal) => signal.id === selectedEvaluationId) ?? evaluationSignals[0];
  const selectedGrowth = growthSignals.find((signal) => signal.id === selectedGrowthId) ?? growthSignals[0];
  const selectedIntelligence =
    intelligenceSignals.find((signal) => signal.id === selectedIntelligenceId) ?? intelligenceSignals[0];
  const dataMode = sunnyvaleInternal?.mode || "waiting";
  const bridgeStatus = sunnyvaleInternal?.bridgeStatus;
  const usingBackendTruth = sunnyvaleInternal?.source === "backend-truth";
  const bridgeOverviewMessage = describeSunnyvaleBridgeState("overview", bridgeStatus);
  const evaluationFallbackMessage = describeSunnyvaleBridgeState("evaluation", bridgeStatus);
  const growthFallbackMessage = describeSunnyvaleBridgeState("growth", bridgeStatus);
  const modeLabel = usingBackendTruth
    ? "live backend"
    : dataMode === "research-only"
      ? "local fallback"
      : "waiting";
  const liveRuns = runs.slice(0, 5);

  return (
    <>
      <section className="col-span-8 h-full min-h-0 overflow-hidden glass-panel border border-white/5 flex flex-col">
        <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-serif italic text-3xl text-white/90">Sunnyvale</h2>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold mt-1">
                Internal operator intelligence / governed execution floor
              </p>
            </div>
            <div className="rounded-full border border-white/10 px-4 py-2 text-[9px] font-mono uppercase tracking-[0.25em] text-blue-300">
              {modeLabel}
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <SunnyvaleRoomButton
              label="Overview"
              active={activeRoom === "overview"}
              onClick={() => setActiveRoom("overview")}
            />
            <SunnyvaleRoomButton
              label="Evaluation Surgeon"
              active={activeRoom === "evaluation-surgeon"}
              onClick={() => setActiveRoom("evaluation-surgeon")}
            />
            <SunnyvaleRoomButton
              label="Hub Growth Navigator"
              active={activeRoom === "hub-growth-navigator"}
              onClick={() => setActiveRoom("hub-growth-navigator")}
            />
            <SunnyvaleRoomButton
              label="Field Intelligence"
              active={activeRoom === "field-intelligence"}
              onClick={() => setActiveRoom("field-intelligence")}
            />
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-6 space-y-6">
          {activeRoom === "overview" && (
            <>
              <Panel title="UACP business pulse" icon={<Radar size={14} className="text-blue-400" />}>
                {sunnyvaleInternal ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
                      <MiniStat
                        icon={<Users size={12} />}
                        label="Active evaluations"
                        value={String(sunnyvaleInternal.overview.activeEvaluations)}
                      />
                      <MiniStat
                        icon={<ShieldCheck size={12} />}
                        label="Serious signals"
                        value={String(sunnyvaleInternal.overview.seriousSignals)}
                      />
                      <MiniStat
                        icon={<BadgeDollarSign size={12} />}
                        label="Reserve live"
                        value={`$${sunnyvaleInternal.overview.reserveBalance.toFixed(2)}`}
                      />
                      <MiniStat
                        icon={<BrainCircuit size={12} />}
                        label="Worker confidence"
                        value={`${sunnyvaleInternal.overview.workerConfidence}%`}
                      />
                      <MiniStat
                        icon={<Activity size={12} />}
                        label="Live workers"
                        value={String(sunnyvaleInternal.overview.liveWorkers)}
                      />
                      <MiniStat
                        icon={<Gavel size={12} />}
                        label="Failed routes"
                        value={String(sunnyvaleInternal.overview.failedRoutes)}
                      />
                      <MiniStat
                        icon={<BookMarked size={12} />}
                        label="Evidence exports"
                        value={String(sunnyvaleInternal.overview.evidenceExports)}
                      />
                      <MiniStat
                        icon={<Layers size={12} />}
                        label="Operating signals"
                        value={String(sunnyvaleInternal.overview.totalSignals)}
                      />
                    </div>

                    <div className="text-xs text-white/45">
                      {!usingBackendTruth && bridgeOverviewMessage
                        ? bridgeOverviewMessage
                        : sunnyvaleInternal.overview.lastBackendEventAt
                          ? `Last backend truth arrived ${new Date(sunnyvaleInternal.overview.lastBackendEventAt).toLocaleString()}.`
                          : "Sunnyvale is waiting for normalized backend truth before it can rank real evaluation accounts."}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-white/45 italic">Sunnyvale read model is still loading.</div>
                )}
              </Panel>

              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <Panel title="Evaluation Surgeon queue" icon={<Users size={14} className="text-blue-400" />}>
                  {evaluationSignals.length > 0 ? (
                    <div className="space-y-3">
                      {evaluationSignals.slice(0, 5).map((signal) => (
                        <button
                          key={signal.id}
                          onClick={() => {
                            setSelectedEvaluationId(signal.id);
                            setActiveRoom("evaluation-surgeon");
                          }}
                          className="w-full text-left p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-white">{signal.accountLabel}</div>
                            <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                              {signal.score}% activation
                            </div>
                          </div>
                          <div className="mt-2 text-sm text-white/55">{signal.summary}</div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <span className="px-2 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                              risk {signal.riskScore}
                            </span>
                            <span className="px-2 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                              {signal.assignedWorkerIds.map((workerId) => resolveWorker(workerId, workers)).join(" / ")}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={<Users size={40} />}
                      title="No live evaluation queue yet"
                      body={
                        !usingBackendTruth
                          ? evaluationFallbackMessage
                          : "Sunnyvale will rank workspaces here once the backend starts sending evaluation, billing, endpoint, evidence, and security events into UACP."
                      }
                    />
                  )}
                </Panel>

                <Panel title="Hub Growth Navigator" icon={<ArrowUpRight size={14} className="text-blue-400" />}>
                  {growthSignals.length > 0 ? (
                    <div className="space-y-3">
                      {growthSignals.slice(0, 4).map((signal) => (
                        <button
                          key={signal.id}
                          onClick={() => {
                            setSelectedGrowthId(signal.id);
                            setActiveRoom("hub-growth-navigator");
                          }}
                          className="w-full text-left p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-white">{signal.title}</div>
                            <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                              {signal.score}% opportunity
                            </div>
                          </div>
                          <div className="mt-2 text-sm text-white/55">{signal.summary}</div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={<ArrowUpRight size={40} />}
                      title="No qualified growth opportunities yet"
                      body={
                        !usingBackendTruth
                          ? growthFallbackMessage
                          : "Growth Navigator will populate when backend marketplace or integration events land, or when live research finds a concrete build path worth routing."
                      }
                    />
                  )}
                </Panel>
              </div>

              <Panel title="Field intelligence" icon={<LibraryBig size={14} className="text-blue-400" />}>
                {intelligenceSignals.length > 0 ? (
                  <div className="space-y-3">
                    {intelligenceSignals.slice(0, 3).map((signal) => (
                      <button
                        key={signal.id}
                        onClick={() => {
                          setSelectedIntelligenceId(signal.id);
                          setActiveRoom("field-intelligence");
                        }}
                        className="w-full text-left p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-white">{signal.title}</div>
                          <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                            {signal.confidence.toFixed(2)} confidence
                          </div>
                        </div>
                        <div className="mt-2 text-sm text-white/55">{signal.summary}</div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<LibraryBig size={40} />}
                    title="No institutional patterns yet"
                    body="Field Intelligence appears when enough live product behavior accumulates for UACP to describe a repeatable pattern instead of a one-off event."
                  />
                )}
              </Panel>
            </>
          )}

          {activeRoom === "evaluation-surgeon" && (
            <>
              {evaluationSignals.length > 0 ? (
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-7 space-y-3">
                    <div className="grid grid-cols-[1.5fr_0.9fr_0.7fr_0.8fr_0.8fr_1.3fr] gap-3 px-4 text-[10px] uppercase tracking-[0.25em] text-white/25">
                      <div>Workspace</div>
                      <div>Stage</div>
                      <div>Runs</div>
                      <div>Endpoint</div>
                      <div>Risk</div>
                      <div>Top action</div>
                    </div>
                    {evaluationSignals.map((signal) => (
                      <button
                        key={signal.id}
                        onClick={() => setSelectedEvaluationId(signal.id)}
                        className={`w-full text-left grid grid-cols-[1.5fr_0.9fr_0.7fr_0.8fr_0.8fr_1.3fr] gap-3 p-4 rounded-xl border transition ${
                          selectedEvaluation?.id === signal.id
                            ? "border-blue-500/30 bg-blue-500/10"
                            : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                        }`}
                      >
                        <div>
                          <div className="text-white">{signal.accountLabel}</div>
                          <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">{signal.tier}</div>
                        </div>
                        <div className="text-sm text-white/60">{signal.evaluationStage}</div>
                        <div className="text-sm text-white/60">
                          {signal.runsUsed ?? 0}
                          {signal.runsLimit ? `/${signal.runsLimit}` : ""}
                        </div>
                        <div className="text-sm text-white/60">{signal.endpointStatus}</div>
                        <div className="text-sm text-white/60">{signal.riskScore}</div>
                        <div className="text-sm text-white/60">{signal.recommendedAction}</div>
                      </button>
                    ))}
                  </div>

                  <div className="col-span-5">
                    {selectedEvaluation && (
                      <OperatingSignalDetail
                        signal={selectedEvaluation}
                        workers={workers}
                        committees={committees}
                        scoreLabel="activation"
                      />
                    )}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<Users size={44} />}
                  title="Evaluation Surgeon is waiting for backend truth"
                  body={
                    !usingBackendTruth
                      ? evaluationFallbackMessage
                      : "Send real workspace, evaluation, endpoint, evidence, billing, and security events into `/api/v1/internal/backend/events` and UACP will rank them here."
                  }
                />
              )}
            </>
          )}

          {activeRoom === "hub-growth-navigator" && (
            <>
              {growthSignals.length > 0 ? (
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-7 space-y-3">
                    {growthSignals.map((signal) => (
                      <button
                        key={signal.id}
                        onClick={() => setSelectedGrowthId(signal.id)}
                        className={`w-full text-left p-4 rounded-xl border transition ${
                          selectedGrowth?.id === signal.id
                            ? "border-blue-500/30 bg-blue-500/10"
                            : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="text-white">{signal.title}</div>
                            <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">
                              {signal.category} / {signal.accountLabel}
                            </div>
                          </div>
                          <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                            {signal.score}% opportunity
                          </div>
                        </div>
                        <div className="mt-3 text-sm text-white/55">{signal.summary}</div>
                      </button>
                    ))}
                  </div>

                  <div className="col-span-5">
                    {selectedGrowth && (
                      <OperatingSignalDetail
                        signal={selectedGrowth}
                        workers={workers}
                        committees={committees}
                        scoreLabel="opportunity"
                      />
                    )}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<ArrowUpRight size={44} />}
                  title="No governed growth queue yet"
                  body={
                    !usingBackendTruth
                      ? growthFallbackMessage
                      : "Growth Navigator will populate when real marketplace, integration, buyer, vendor, or live research opportunities are available for UACP to route."
                  }
                />
              )}
            </>
          )}

          {activeRoom === "field-intelligence" && (
            <>
              {intelligenceSignals.length > 0 ? (
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-7 space-y-3">
                    {intelligenceSignals.map((signal) => (
                      <button
                        key={signal.id}
                        onClick={() => setSelectedIntelligenceId(signal.id)}
                        className={`w-full text-left p-4 rounded-xl border transition ${
                          selectedIntelligence?.id === signal.id
                            ? "border-blue-500/30 bg-blue-500/10"
                            : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="text-white">{signal.title}</div>
                            <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">{signal.category}</div>
                          </div>
                          <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                            {(signal.confidence * 100).toFixed(0)}% confidence
                          </div>
                        </div>
                        <div className="mt-3 text-sm text-white/55">{signal.summary}</div>
                      </button>
                    ))}
                  </div>

                  <div className="col-span-5">
                    {selectedIntelligence && (
                      <OperatingSignalDetail
                        signal={selectedIntelligence}
                        workers={workers}
                        committees={committees}
                        scoreLabel="signal"
                      />
                    )}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<LibraryBig size={44} />}
                  title="No field intelligence patterns yet"
                  body="Field Intelligence appears after repeated product behavior reveals a stable pattern worth routing back into the institution."
                />
              )}
            </>
          )}
        </div>
      </section>

      <section className="col-span-4 h-full min-h-0 overflow-hidden grid grid-rows-[minmax(0,1.45fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.9fr)] gap-4 pr-1">
        <Panel title="Governed admission queue" icon={<BrainCircuit size={14} className="text-blue-400" />}>
          {plan ? (
            <div className="space-y-4">
              <div>
                <div className="text-white text-xl">{plan.title}</div>
                <p className="mt-2 text-sm text-white/55 italic">{plan.objective}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <MiniStat icon={<Building2 size={12} />} label="Paying user" value={plan.payingUser} />
                <MiniStat icon={<BadgeDollarSign size={12} />} label="Pricing" value={plan.pricingModel} />
                <MiniStat icon={<Gavel size={12} />} label="Risk" value={plan.riskTier} />
                <MiniStat icon={<Layers size={12} />} label="Revision" value={String(plan.revision)} />
              </div>

              <TokenPanel title="Pillars" items={plan.pillars} />
              <TokenPanel
                title="Committees"
                items={plan.committeeIds.map((committeeId) => resolveCommittee(committeeId, committees))}
              />
              <ListPanel title="Guardrails" items={plan.guardrails} />
              <ReferencePanel title="Live references" references={plan.researchReferences || []} />

              <button
                onClick={() => void onLaunchRun(plan.id)}
                disabled={launchingPlanId === plan.id}
                aria-busy={launchingPlanId === plan.id}
                className={`w-full px-5 py-3 border text-[10px] uppercase font-bold tracking-[0.3em] transition-all ${
                  launchingPlanId === plan.id
                    ? "border-blue-400/30 bg-blue-500/10 text-blue-100 cursor-wait"
                    : "border-white/10 hover:bg-white hover:text-black active:scale-95"
                }`}
              >
                {launchingPlanId === plan.id ? (
                  <span className="inline-flex items-center justify-center gap-2">
                    <LoaderCircle size={14} className="animate-spin" />
                    Launching Governed Run
                  </span>
                ) : (
                  "Approve & Launch Run"
                )}
              </button>
              {launchRunError && <div className="text-xs text-red-300/80">{launchRunError}</div>}
            </div>
          ) : (
            <div className="text-sm text-white/45 italic">Compile a plan in the Deterministic Engine first, then review and admit it here.</div>
          )}
        </Panel>

        <Panel title="Queued plans" icon={<Network size={14} className="text-blue-400" />}>
          <div className="space-y-3">
            {plans.length > 0 ? (
              plans.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => onSelectPlan(entry.id)}
                  className={`w-full text-left p-4 rounded-xl border transition ${
                    plan?.id === entry.id
                      ? "border-blue-500/30 bg-blue-500/10"
                      : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-white">{entry.title}</div>
                    <ChevronRight size={14} className="text-white/30" />
                  </div>
                  <div className="mt-2 text-sm text-white/50">{entry.objective}</div>
                </button>
              ))
            ) : (
              <div className="text-sm text-white/45 italic">No governed plans are queued yet.</div>
            )}
          </div>
        </Panel>

        <Panel title="Live runs" icon={<Activity size={14} className="text-blue-400" />}>
          <div className="space-y-4">
            {liveRuns.length === 0 && (
              <div className="text-sm text-white/45 italic">No runs yet. Approval here opens the first governed run.</div>
            )}
            {liveRuns.map((run) => (
              <div key={run.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-white">{run.id}</div>
                    <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">{run.currentStage}</div>
                  </div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">{run.status}</div>
                </div>
                <div className="mt-4 h-2 bg-white/5 overflow-hidden rounded-full">
                  <motion.div className="h-full bg-gradient-to-r from-blue-600 to-indigo-500" animate={{ width: `${run.progress}%` }} />
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <MiniStat icon={<ShieldCheck size={12} />} label="Approvals" value={String(run.approvals)} />
                  <MiniStat icon={<BookMarked size={12} />} label="Evidence" value={String(run.evidenceCount)} />
                </div>
                {run.output && <p className="mt-4 text-sm text-white/55 italic">{run.output}</p>}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Workflow doctrine" icon={<LibraryBig size={14} className="text-blue-400" />}>
          <div className="space-y-3">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="text-white">{workflow.name}</div>
                <div className="mt-2 text-sm text-white/55">{workflow.description}</div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-white/25">{workflow.outcome}</div>
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </>
  );
}

function SiliconValleySurface({
  pillars,
  committees,
  operatorCommittees,
  workers,
  workerRuntime,
  operatorRuns,
  skills,
  backendSummary,
  backendEvents,
  commandCenter,
  providerSnapshot,
  researchStatus,
  telemetry,
  observability,
}: {
  pillars: Pillar[];
  committees: Committee[];
  operatorCommittees: OperatorCommittee[];
  workers: OperatorWorker[];
  workerRuntime: WorkerRuntimeState[];
  operatorRuns: OperatorRun[];
  skills: SkillArtifact[];
  backendSummary: BackendTruthSummary | null;
  backendEvents: BackendProductEvent[];
  commandCenter: CommandCenterSnapshot | null;
  providerSnapshot: ModelProviderSnapshot | null;
  researchStatus: ResearchSourceStatus[];
  telemetry: ControlTelemetry | null;
  observability: EngineObservability | null;
}) {
  const runtimeByWorkerId = new Map(workerRuntime.map((runtime) => [runtime.workerId, runtime]));

  return (
    <>
      <section className="col-span-4 h-full min-h-0 overflow-y-auto custom-scrollbar glass-panel border border-white/5">
        <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <h2 className="font-serif italic text-3xl text-white/90">Silicon Valley</h2>
          <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold mt-1">
            Founder governance / backend truth / worker ownership
          </p>
        </div>

        <div className="p-6 min-h-0 space-y-4">
          <Panel title="Command Center truth" icon={<Building2 size={14} className="text-blue-400" />}>
            {commandCenter ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <MiniStat icon={<Users size={12} />} label="Workers" value={String(commandCenter.institution.workerCount)} />
                  <MiniStat icon={<Activity size={12} />} label="Operator runs" value={String(commandCenter.institution.operatorRunCount)} />
                  <MiniStat icon={<ShieldCheck size={12} />} label="Escalations" value={String(commandCenter.institution.openEscalations)} />
                  <MiniStat icon={<Disc size={12} />} label="Archives" value={String(commandCenter.institution.archiveCount)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <MiniStat icon={<Users size={12} />} label="Live users" value={String(commandCenter.backend.liveUsers)} />
                  <MiniStat icon={<BadgeDollarSign size={12} />} label="Revenue" value={`$${commandCenter.backend.revenue.toFixed(2)}`} />
                  <MiniStat icon={<LibraryBig size={12} />} label="Evaluations" value={String(commandCenter.backend.evaluationsStarted)} />
                  <MiniStat icon={<Gavel size={12} />} label="Reserve" value={`$${commandCenter.backend.reserveBalance.toFixed(2)}`} />
                </div>
              </div>
            ) : (
              <div className="text-sm text-white/45 italic">Command Center state is still loading.</div>
            )}
          </Panel>

          <Panel title="Backend truth" icon={<Radar size={14} className="text-blue-400" />}>
            {backendSummary ? (
              <div className="grid grid-cols-2 gap-3">
                <MiniStat icon={<Users size={12} />} label="Signups" value={String(backendSummary.signups)} />
                <MiniStat icon={<Building2 size={12} />} label="Marketplace installs" value={String(backendSummary.marketplaceInstalls)} />
                <MiniStat icon={<LibraryBig size={12} />} label="Evidence exports" value={String(backendSummary.evidenceExports)} />
                <MiniStat icon={<ShieldCheck size={12} />} label="MFA events" value={String(backendSummary.mfaEvents)} />
                <MiniStat icon={<Activity size={12} />} label="Endpoint calls" value={String(backendSummary.endpointCalls)} />
                <MiniStat icon={<Gavel size={12} />} label="Failed routes" value={String(backendSummary.failedRoutes)} />
              </div>
            ) : (
              <div className="text-sm text-white/45 italic">No backend truth has been ingested yet.</div>
            )}
          </Panel>

          <Panel title="Model providers" icon={<BrainCircuit size={14} className="text-blue-400" />}>
            {providerSnapshot ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <MiniStat icon={<BrainCircuit size={12} />} label="Primary" value={providerLabel(providerSnapshot.defaultProvider)} />
                  <MiniStat icon={<Zap size={12} />} label="Active" value={providerLabel(providerSnapshot.activeProvider)} />
                </div>
                <div className="space-y-3">
                  {providerSnapshot.statuses.map((provider) => (
                    <div key={provider.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-white">{provider.label}</div>
                        <div
                          className={`text-[10px] font-mono uppercase tracking-[0.25em] ${
                            provider.health === "ready"
                              ? "text-green-400"
                              : provider.health === "degraded"
                                ? "text-amber-300"
                                : provider.health === "missing"
                                  ? "text-white/35"
                                  : "text-blue-300"
                          }`}
                        >
                          {provider.health}
                        </div>
                      </div>
                      <div className="mt-2 text-sm text-white/55">{provider.detail}</div>
                      <div className="mt-3 grid grid-cols-2 gap-3">
                        <MiniStat icon={<Zap size={12} />} label="Model" value={provider.model || "n/a"} />
                        <MiniStat icon={<Network size={12} />} label="Role" value={provider.active ? "active" : "standby"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-sm text-white/45 italic">Provider readiness is still loading.</div>
            )}
          </Panel>

          {pillars.map((pillar) => (
            <div key={pillar.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
              <div className="text-white">{pillar.name}</div>
              <div className="mt-2 text-sm text-white/55">{pillar.mandate}</div>
              <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-blue-300">{pillar.kpi}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="col-span-5 h-full min-h-0 overflow-y-auto custom-scrollbar glass-panel border border-white/5">
        <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <div className="flex items-center gap-3">
            <Users size={16} className="text-blue-400" />
            <div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-white/30 font-bold">Institutional ownership</div>
              <div className="text-white text-xl mt-1">Committees, worker registry, and run accountability</div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-4">
          {committees.map((committee) => (
            <div key={committee.id} className="p-5 rounded-xl border border-white/10 bg-white/[0.02]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-white text-lg">{committee.name}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-blue-300">{committee.authority}</div>
                </div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-white/25">{committee.chair}</div>
              </div>
              <p className="mt-3 text-sm text-white/55">{committee.purpose}</p>
              <div className="mt-4">
                <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-2">Allowed actions</div>
                <div className="flex flex-wrap gap-2">
                  {committee.allowedActions.map((action) => (
                    <span key={action} className="px-3 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                      {action}
                    </span>
                  ))}
                </div>
              </div>
              <div className="mt-4">
                <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-2">Veto conditions</div>
                <div className="space-y-2">
                  {committee.vetoConditions.map((condition) => (
                    <div key={condition} className="text-sm text-white/50 italic">{condition}</div>
                  ))}
                </div>
              </div>
            </div>
          ))}

          <Panel title="Operator committees" icon={<Layers size={14} className="text-blue-400" />}>
            <div className="space-y-3">
              {operatorCommittees.map((committee) => (
                <div key={committee.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                  <div className="text-white">{committee.name}</div>
                  <div className="mt-2 text-sm text-white/55">{committee.purpose}</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {committee.workerIds.map((workerId) => (
                      <span key={workerId} className="px-3 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                        {workers.find((worker) => worker.id === workerId)?.displayName || workerId}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Named worker registry" icon={<Network size={14} className="text-blue-400" />}>
            <div className="space-y-3">
              {workers.map((worker) => {
                const runtime = runtimeByWorkerId.get(worker.id);
                return (
                  <div key={worker.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-white">{worker.displayName}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-blue-300">{worker.schedule}</div>
                      </div>
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-white/35">
                        {runtime?.status || "idle"}
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-white/55">{worker.purpose}</div>
                    <div className="mt-3 grid grid-cols-2 gap-3">
                      <MiniStat
                        icon={<Building2 size={12} />}
                        label="Committee"
                        value={operatorCommittees.find((committee) => committee.id === worker.committeeId)?.name || worker.committeeId}
                      />
                      <MiniStat icon={<Layers size={12} />} label="Primary pillar" value={worker.primaryPillar} />
                      <MiniStat icon={<Activity size={12} />} label="Last run" value={runtime?.lastRunAt ? new Date(runtime.lastRunAt).toLocaleTimeString() : "none"} />
                      <MiniStat icon={<Radar size={12} />} label="Next run" value={runtime?.nextRunAt ? new Date(runtime.nextRunAt).toLocaleTimeString() : "paused"} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Recent operator runs" icon={<Disc size={14} className="text-blue-400" />}>
            <div className="space-y-3">
              {operatorRuns.length === 0 && (
                <div className="text-sm text-white/45 italic">No operator runs have been recorded yet.</div>
              )}
              {operatorRuns.slice(0, 10).map((run) => (
                <div key={run.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-white">{workers.find((worker) => worker.id === run.workerId)?.displayName || run.workerId}</div>
                      <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">{run.id}</div>
                    </div>
                    <div className={`text-[10px] font-mono uppercase tracking-[0.25em] ${run.status === "completed" ? "text-green-400" : run.status === "escalated" ? "text-amber-300" : run.status === "failed" ? "text-red-400" : "text-blue-300"}`}>
                      {run.status}
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-white/55">{run.nextRecommendation}</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </section>

      <section className="col-span-3 h-full min-h-0 overflow-hidden grid grid-rows-[minmax(0,1.35fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(0,0.85fr)] gap-4">
        <Panel title="Skill governance" icon={<BookMarked size={14} className="text-blue-400" />} contentClassName="space-y-3">
            {skills.map((skill) => (
              <div key={skill.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white break-words">{skill.name}</div>
                  <div className={`text-[10px] font-mono uppercase tracking-[0.25em] ${skill.status === "approved" ? "text-green-400" : "text-amber-300"}`}>
                    {skill.status}
                  </div>
                </div>
                <div className="mt-2 text-sm text-white/55">{skill.description}</div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <MiniStat icon={<Users size={12} />} label="Owner" value={skill.governingCommitteeId || "n/a"} />
                  <MiniStat icon={<Layers size={12} />} label="SLA" value={skill.sla || "n/a"} />
                  <MiniStat icon={<Network size={12} />} label="Input" value={skill.inputType || "n/a"} />
                  <MiniStat icon={<ChevronRight size={12} />} label="Output" value={skill.outputType || "n/a"} />
                </div>
                <div className="mt-3">
                  <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-2">Required evidence</div>
                  <div className="flex flex-wrap gap-2">
                    {(skill.requiredEvidence || []).map((requirement) => (
                      <span key={requirement} className="px-3 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                        {requirement}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="mt-3 text-[10px] uppercase tracking-[0.25em] text-white/25 break-all">{skill.source} / {skill.ref}</div>
              </div>
            ))}
        </Panel>

        <Panel title="Backend event feed" icon={<Activity size={14} className="text-blue-400" />} contentClassName="space-y-3">
            {backendEvents.length === 0 && (
              <div className="text-sm text-white/45 italic">No backend events have been ingested into UACP yet.</div>
            )}
            {backendEvents.slice(0, 8).map((event) => (
              <div key={event.eventId} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white">{event.eventType}</div>
                  <div className={`text-[10px] font-mono uppercase tracking-[0.25em] ${event.severity === "critical" ? "text-red-400" : event.severity === "warning" ? "text-amber-300" : "text-blue-300"}`}>
                    {event.severity}
                  </div>
                </div>
                <div className="mt-2 text-sm text-white/55">{event.entityType} / {event.entityId}</div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-white/25">
                  {event.workerIds.length} workers / {event.committeeIds.length} committees
                </div>
              </div>
            ))}
        </Panel>

        <Panel title="Research ingress" icon={<LibraryBig size={14} className="text-blue-400" />} contentClassName="space-y-3">
            {researchStatus.length === 0 && (
              <div className="text-sm text-white/45 italic">No source status yet. Trigger a research refresh or compile a plan.</div>
            )}
            {researchStatus.map((status) => (
              <div key={status.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white">{status.name}</div>
                  <div
                    className={`text-[10px] font-mono uppercase tracking-[0.25em] ${
                      status.status === "online"
                        ? "text-green-400"
                        : status.status === "degraded"
                          ? "text-amber-300"
                          : "text-red-400"
                    }`}
                  >
                    {status.status}
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  <MiniStat icon={<Activity size={12} />} label="Items" value={String(status.itemCount)} />
                  <MiniStat icon={<Radar size={12} />} label="Latency" value={status.lastLatencyMs ? `${status.lastLatencyMs}ms` : "n/a"} />
                </div>
                {status.error && <div className="mt-3 text-xs text-white/45 italic">{status.error}</div>}
              </div>
            ))}
        </Panel>

        <Panel title="Institutional metrics" icon={<Radar size={14} className="text-blue-400" />} contentClassName="space-y-3">
            {(telemetry?.metrics ?? []).map((metric) => (
              <div key={metric.label} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white">{metric.label}</div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-blue-300">
                    {metric.value}{metric.unit}
                  </div>
                </div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-white/25">{metric.trend}</div>
              </div>
            ))}
            {observability && (
              <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="text-white">UACP Pressure</div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-blue-300">
                  {(observability.uacp_pressure * 100).toFixed(2)}%
                </div>
              </div>
            )}
        </Panel>
      </section>
    </>
  );
}

function ArchivesSurface({
  archives,
  events,
  latestRun,
  eventStreamStatus,
}: {
  archives: ArchiveEntry[];
  events: EventItem[];
  latestRun?: GovernedRun;
  eventStreamStatus: { connected: boolean; redisBacked: boolean; route: string };
}) {
  async function downloadRunProof(runId: string) {
    const response = await fetch(`/api/v1/gpc/runs/${encodeURIComponent(runId)}/proof`);
    if (!response.ok) return;
    const proof = await response.json();
    const blob = new Blob([JSON.stringify(proof, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${runId}-veklom-run-proof.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <section className="col-span-7 h-full min-h-0 overflow-y-auto custom-scrollbar glass-panel border border-white/5">
        <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <h2 className="font-serif italic text-3xl text-white/90">Archives</h2>
          <p className="text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold mt-1">
            Replayable evidence / lineage / ordered memory
          </p>
        </div>

        <div className="p-6 min-h-0 space-y-4">
          {archives.map((archive) => (
            <div key={archive.id} className="p-5 rounded-xl border border-white/10 bg-white/[0.02]">
              <div className="flex items-center justify-between gap-3">
                <div className="text-white text-lg">{archive.title}</div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-blue-300">{archive.category}</div>
              </div>
              <p className="mt-3 text-sm text-white/55">{archive.summary}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {archive.lineage.map((item) => (
                  <span key={item} className="px-3 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="col-span-5 h-full min-h-0 overflow-y-auto custom-scrollbar flex flex-col gap-4">
        <Panel title="Ordered events" icon={<CheckCircle2 size={14} className="text-blue-400" />} className="min-h-0 max-h-[34rem]" contentClassName="space-y-3">
            {events.map((event) => (
              <div key={event.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white">{event.type}</div>
                  <div className="text-[10px] uppercase tracking-[0.25em] text-white/25">{surfaceLabels[event.surface]}</div>
                </div>
                <p className="mt-2 text-sm text-white/55">{event.message}</p>
                <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-blue-300">
                  {new Date(event.timestamp).toLocaleString()}
                </div>
              </div>
            ))}
        </Panel>

        <Panel title="Latest run evidence" icon={<Disc size={14} className="text-blue-400" />}>
          {latestRun ? (
            <div className="space-y-4">
              <div>
                <div className="text-white text-lg">{latestRun.id}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-white/25">{latestRun.currentStage}</div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <MiniStat icon={<ShieldCheck size={12} />} label="Approvals" value={String(latestRun.approvals)} />
                <MiniStat icon={<BookMarked size={12} />} label="Evidence" value={String(latestRun.evidenceCount)} />
                <MiniStat icon={<Activity size={12} />} label="Progress" value={`${latestRun.progress}%`} />
                <MiniStat icon={<Disc size={12} />} label="Status" value={latestRun.status} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <MiniStat
                  icon={<Network size={12} />}
                  label="Event stream"
                  value={eventStreamStatus.connected ? "live" : "reconnecting"}
                />
                <MiniStat
                  icon={<Database size={12} />}
                  label="Redis backed"
                  value={eventStreamStatus.redisBacked ? "true" : "false"}
                />
              </div>
              {latestRun.output && <p className="text-sm text-white/55 italic">{latestRun.output}</p>}
              {latestRun.artifact && (
                <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-4">
                  <div className="text-white">{latestRun.artifact.title}</div>
                  <div className="text-sm text-white/55">{latestRun.artifact.summary}</div>
                  <div className="grid grid-cols-2 gap-3">
                    <MiniStat icon={<LibraryBig size={12} />} label="Sources" value={String(latestRun.artifact.sourceCount)} />
                    <MiniStat icon={<Layers size={12} />} label="Workflows" value={String(latestRun.artifact.workflowIds.length)} />
                  </div>
                  <div className="text-xs text-white/50 italic">{latestRun.artifact.nextAction}</div>
                  <div className="flex flex-wrap gap-2 pt-2">
                    <button
                      onClick={() => downloadRunProof(latestRun.id)}
                      className="px-3 py-2 rounded-lg border border-blue-400/30 bg-blue-500/10 text-[10px] uppercase tracking-[0.25em] text-blue-200 hover:bg-blue-500/20"
                    >
                      Export Run Proof
                    </button>
                    <a
                      href={`/api/v1/gpc/runs/${encodeURIComponent(latestRun.id)}/proof/export`}
                      className="px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-[10px] uppercase tracking-[0.25em] text-white/60 hover:text-white"
                    >
                      Download JSON
                    </a>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-white/45 italic">No run evidence yet.</div>
          )}
        </Panel>
      </section>
    </>
  );
}

function StatusSurface({ statusPage }: { statusPage: StatusPageSnapshot | null }) {
  if (!statusPage) {
    return (
      <section className="col-span-12 h-full min-h-0 overflow-y-auto custom-scrollbar glass-panel border border-white/5 p-6">
        <div className="text-sm text-white/45 italic">Loading observed status...</div>
      </section>
    );
  }

  const statusTone = statusPage.service.status === "operational"
    ? "text-green-300 border-green-400/30 bg-green-500/10"
    : statusPage.service.status === "degraded"
      ? "text-amber-300 border-amber-400/30 bg-amber-500/10"
      : "text-rose-300 border-rose-400/30 bg-rose-500/10";

  return (
    <>
      <section className="col-span-8 h-full min-h-0 overflow-y-auto custom-scrollbar glass-panel border border-white/5">
        <div className="p-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-serif italic text-3xl text-white/90">Veklom Status</h2>
              <p className="mt-1 text-[10px] uppercase tracking-[0.3em] text-white/30 font-bold">
                Observed uptime / incident history / proof-backed stats
              </p>
            </div>
            <div className={`rounded-full border px-4 py-2 text-[10px] uppercase tracking-[0.25em] ${statusTone}`}>
              {statusPage.service.status}
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatusStat label="Observed uptime" value={`${statusPage.stats.observedUptimePercent}%`} />
            <StatusStat label="Run success" value={`${statusPage.stats.runSuccessRate}%`} />
            <StatusStat label="Archive proof" value={`${statusPage.stats.archiveProofCoverage}%`} />
            <StatusStat label="Provider routes" value={`${statusPage.stats.providerReadyCount}/${statusPage.stats.providerConfiguredCount}`} />
            <StatusStat label="Policy alignment" value={`${statusPage.stats.policyAlignment}%`} />
            <StatusStat label="Determinism" value={`${statusPage.stats.determinismScore}%`} />
            <StatusStat label="Evidence exports" value={String(statusPage.stats.evidenceExports)} />
            <StatusStat label="Redis stream" value={statusPage.stats.redisBackedEventStream ? "true" : "false"} />
          </div>

          <Panel title="Uptime history" icon={<Activity size={14} className="text-blue-400" />}>
            <div className="grid grid-cols-7 lg:grid-cols-14 gap-2">
              {statusPage.history.map((day) => (
                <div key={day.date} className="space-y-2">
                  <div
                    title={`${day.date}: ${day.status}, ${day.runCount} runs, ${day.archiveCount} archives`}
                    className={`h-16 rounded-lg border ${
                      day.status === "operational"
                        ? "border-green-400/20 bg-green-500/20"
                        : day.status === "degraded"
                          ? "border-amber-400/20 bg-amber-500/20"
                          : "border-rose-400/20 bg-rose-500/20"
                    }`}
                  />
                  <div className="text-[8px] text-white/30 font-mono">{day.date.slice(5)}</div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Component health" icon={<ShieldCheck size={14} className="text-blue-400" />} contentClassName="grid grid-cols-1 md:grid-cols-2 gap-3">
            {statusPage.components.map((component) => (
              <div key={component.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white">{component.name}</div>
                  <div className={`text-[9px] uppercase tracking-[0.2em] ${
                    component.status === "operational" ? "text-green-300" : component.status === "degraded" ? "text-amber-300" : "text-rose-300"
                  }`}>
                    {component.status}
                  </div>
                </div>
                <p className="mt-2 text-sm text-white/50">{component.detail}</p>
              </div>
            ))}
          </Panel>
        </div>
      </section>

      <section className="col-span-4 h-full min-h-0 overflow-y-auto custom-scrollbar flex flex-col gap-4">
        <Panel title="Incident history" icon={<Radar size={14} className="text-blue-400" />}>
          <div className="space-y-3">
            {statusPage.incidents.length === 0 ? (
              <div className="text-sm text-white/45 italic">No observed incidents in the last 14 days.</div>
            ) : statusPage.incidents.map((incident) => (
              <div key={incident.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-white text-sm">{incident.title}</div>
                  <div className={`text-[9px] uppercase tracking-[0.2em] ${incident.severity === "critical" ? "text-rose-300" : "text-amber-300"}`}>
                    {incident.status}
                  </div>
                </div>
                <p className="mt-2 text-xs text-white/50">{incident.summary}</p>
                <div className="mt-3 text-[10px] uppercase tracking-[0.2em] text-blue-300">
                  {new Date(incident.startedAt).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Public proof posture" icon={<LibraryBig size={14} className="text-blue-400" />}>
          <div className="space-y-3 text-sm text-white/55">
            <p>Stats are computed from current runtime events, governed runs, archives, provider readiness, and Redis stream state.</p>
            <p>No inflated uptime claim is made beyond observed runtime history.</p>
            <p className="text-[10px] uppercase tracking-[0.25em] text-white/25">Generated {new Date(statusPage.generatedAt).toLocaleString()}</p>
          </div>
        </Panel>
      </section>
    </>
  );
}

function StatusStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div className="text-[9px] uppercase tracking-[0.22em] text-white/30">{label}</div>
      <div className="mt-2 text-2xl font-serif italic text-white">{value}</div>
    </div>
  );
}

function SurfaceButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative py-1 transition-all group outline-none ${active ? "text-white" : "text-white/40 hover:text-white/70"}`}
    >
      {label}
      {active && (
        <motion.div
          layoutId="surface-tab"
          className="absolute -bottom-1 left-0 right-0 h-[2px] bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]"
        />
      )}
    </button>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-1.5 border border-white/10 rounded-full bg-white/5 backdrop-blur-sm">
      <ArrowUpRight size={10} className="text-blue-400" />
      <span className="text-[9px] font-mono lowercase tracking-normal text-white/60">{label} {value}</span>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2">
      <div className="text-[9px] uppercase tracking-[0.25em] text-white/25 font-mono">{label}</div>
      <div className="mt-1 text-sm text-white/75 truncate">{value}</div>
    </div>
  );
}

function Panel({
  title,
  icon,
  children,
  className = "",
  contentClassName = "",
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <div className={`glass-panel border border-white/5 overflow-hidden min-h-0 flex flex-col ${className}`}>
      <div className="p-5 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent flex items-center gap-3">
        {icon}
        <div className="text-[10px] uppercase tracking-[0.25em] text-white/30 font-bold">{title}</div>
      </div>
      <div className={`flex-1 min-h-0 overflow-y-auto custom-scrollbar p-5 ${contentClassName}`}>{children}</div>
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
      <div className="flex items-center gap-2 text-blue-300 mb-1">
        {icon}
        <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-white/25">{label}</span>
      </div>
      <div className="text-[11px] text-white/70">{value}</div>
    </div>
  );
}

function TokenPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
      <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-3">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className="px-3 py-1 rounded-full border border-white/10 text-[10px] text-white/55">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function ListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
      <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-3">{title}</div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item} className="text-sm text-white/55 italic">{item}</div>
        ))}
      </div>
    </div>
  );
}

function ValuePanel({ title, value }: { title: string; value: string }) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
      <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-3">{title}</div>
      <div className="text-sm text-white/65 leading-relaxed">{value}</div>
    </div>
  );
}

function ReferencePanel({
  title,
  references,
}: {
  title: string;
  references: Array<{ title: string; source: string; url?: string; publishedAt?: string }>;
}) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
      <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-3">{title}</div>
      <div className="space-y-3">
        {references.length === 0 && <div className="text-sm text-white/45 italic">No live references attached yet.</div>}
        {references.map((reference) => (
          <div key={`${reference.source}-${reference.title}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
            <div className="text-sm text-white/70">{reference.title}</div>
            <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-blue-300">
              {reference.source}
              {reference.publishedAt ? ` / ${new Date(reference.publishedAt).toLocaleDateString()}` : ""}
            </div>
            {reference.url && (
              <a
                href={reference.url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block text-[10px] uppercase tracking-[0.25em] text-white/45 hover:text-blue-300 transition-colors"
              >
                Open source
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ProposalPanel({
  title,
  proposals,
}: {
  title: string;
  proposals: Array<{ id: string; type: string; name: string; rationale: string; status: string }>;
}) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
      <div className="text-[10px] uppercase tracking-[0.25em] text-white/25 mb-3">{title}</div>
      <div className="space-y-3">
        {proposals.length === 0 && <div className="text-sm text-white/45 italic">No new governance objects were proposed.</div>}
        {proposals.map((proposal) => (
          <div key={proposal.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm text-white/70">{proposal.name}</div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-amber-300">{proposal.status}</div>
            </div>
            <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-blue-300">{proposal.type}</div>
            <div className="mt-2 text-sm text-white/55 italic">{proposal.rationale}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  body,
}: {
  icon: ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="h-full flex flex-col items-center justify-center opacity-30 space-y-6">
      {icon}
      <span className="font-serif italic text-xl">{title}</span>
      <p className="max-w-xl text-center text-sm text-white/45">{body}</p>
    </div>
  );
}

function SunnyvaleRoomButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full border text-[10px] uppercase tracking-[0.25em] font-bold transition ${
        active
          ? "border-blue-500/30 bg-blue-500/10 text-blue-300"
          : "border-white/10 bg-white/[0.02] text-white/45 hover:bg-white/[0.04]"
      }`}
    >
      {label}
    </button>
  );
}

function OperatingSignalDetail({
  signal,
  workers,
  committees,
  scoreLabel,
}: {
  signal: OperatingSignal;
  workers: OperatorWorker[];
  committees: Committee[];
  scoreLabel: string;
}) {
  return (
    <Panel
      title="Signal detail"
      icon={<ChevronRight size={14} className="text-blue-400" />}
      className="max-h-[36rem]"
      contentClassName="overflow-y-auto custom-scrollbar"
    >
      <div className="space-y-4">
        <div>
          <div className="text-white text-xl">{signal.title}</div>
          <div className="mt-2 text-sm text-white/55">{signal.summary}</div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MiniStat icon={<Radar size={12} />} label={scoreLabel} value={`${signal.score}%`} />
          <MiniStat icon={<ShieldCheck size={12} />} label="Risk" value={`${signal.riskScore}`} />
          <MiniStat icon={<BrainCircuit size={12} />} label="Confidence" value={`${(signal.confidence * 100).toFixed(0)}%`} />
          <MiniStat icon={<Gavel size={12} />} label="Status" value={signal.status} />
        </div>

        <div className="grid grid-cols-1 gap-4">
          <TokenPanel title="Assigned workers" items={signal.assignedWorkerIds.map((workerId) => resolveWorker(workerId, workers))} />
          <TokenPanel title="Pillars" items={signal.pillarIds} />
          <ValuePanel title="Committee" value={signal.committeeId ? resolveCommittee(signal.committeeId, committees) : "No committee mapping yet."} />
          {signal.kind === "evaluation" && (
            <div className="grid grid-cols-2 gap-3">
              <MiniStat icon={<Users size={12} />} label="Stage" value={signal.evaluationStage || "n/a"} />
              <MiniStat icon={<Building2 size={12} />} label="Tier" value={signal.tier || "n/a"} />
              <MiniStat
                icon={<Activity size={12} />}
                label="Runs"
                value={`${signal.runsUsed ?? 0}${signal.runsLimit ? `/${signal.runsLimit}` : ""}`}
              />
              <MiniStat icon={<Network size={12} />} label="Endpoint" value={signal.endpointStatus || "n/a"} />
              <MiniStat icon={<BookMarked size={12} />} label="Evidence" value={signal.evidenceActivity || "n/a"} />
              <MiniStat icon={<BadgeDollarSign size={12} />} label="Reserve" value={signal.reserveState || "n/a"} />
              <MiniStat icon={<ShieldCheck size={12} />} label="MFA" value={signal.mfaState || "n/a"} />
              <MiniStat icon={<Disc size={12} />} label="Errors" value={String(signal.errorsCount ?? 0)} />
            </div>
          )}
          <ListPanel title="Evidence" items={signal.evidence} />
          <ValuePanel title="Recommended action" value={signal.recommendedAction} />
          <ValuePanel title="Archive reference" value={signal.archiveRef || "No archive link yet for this signal."} />
          <ValuePanel title="Source events" value={signal.sourceEventIds.join(", ") || "No source events recorded."} />
          {signal.lastActivityAt && <ValuePanel title="Last activity" value={new Date(signal.lastActivityAt).toLocaleString()} />}
        </div>
      </div>
    </Panel>
  );
}

function describeSunnyvaleBridgeState(
  scope: "overview" | "evaluation" | "growth",
  bridgeStatus: SunnyvaleInternalSnapshot["bridgeStatus"] | undefined,
) {
  const missingConfigReason =
    !bridgeStatus?.baseUrlConfigured && !bridgeStatus?.internalKeyConfigured
      ? "UACP_BACKEND_BASE_URL and UACP_INTERNAL_API_KEY are not configured on this runtime."
      : !bridgeStatus?.baseUrlConfigured
        ? "UACP_BACKEND_BASE_URL is not configured on this runtime."
        : !bridgeStatus?.internalKeyConfigured
          ? "UACP_INTERNAL_API_KEY is not configured on this runtime."
          : null;

  if (scope === "overview") {
    if (missingConfigReason) {
      return `Sunnyvale is running in local fallback because ${missingConfigReason}`;
    }
    return bridgeStatus?.lastError ? `Sunnyvale backend bridge degraded: ${bridgeStatus.lastError}` : null;
  }

  if (scope === "evaluation") {
    return missingConfigReason
      ? `Sunnyvale is still on local fallback because ${missingConfigReason} Configure both values on the runtime so Evaluation Surgeon can pull the protected backend queue.`
      : "Sunnyvale will rank workspaces here once the backend starts sending evaluation, billing, endpoint, evidence, and security events into UACP.";
  }

  return missingConfigReason
    ? `Sunnyvale is still on local fallback because ${missingConfigReason} Configure both values on the runtime so Hub Growth Navigator can pull the protected backend opportunity queue.`
    : "Growth Navigator will populate when backend marketplace or integration events land, or when live research finds a concrete build path worth routing.";
}

function resolveWorker(id: string, workers: OperatorWorker[]) {
  return workers.find((worker) => worker.id === id)?.displayName || id;
}

function resolveCommittee(id: string, committees: Committee[]) {
  return committees.find((committee) => committee.id === id)?.name || id;
}

function upsertById<T extends { id: string }>(list: T[], item: T) {
  const index = list.findIndex((entry) => entry.id === item.id);
  if (index === -1) return [item, ...list];
  const next = [...list];
  next[index] = item;
  return next;
}

function percent(value?: number) {
  if (typeof value !== "number") return "0.0";
  return (Math.round(value * 1000) / 10).toFixed(1);
}

function providerLabel(provider?: string) {
  switch (provider) {
    case "groq":
      return "Groq";
    case "huggingface":
      return "Hugging Face";
    case "ollama":
      return "Ollama";
    case "gemini":
      return "Gemini";
    case "deterministic":
      return "Deterministic";
    default:
      return "Unknown";
  }
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
