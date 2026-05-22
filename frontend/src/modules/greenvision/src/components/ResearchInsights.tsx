// @ts-nocheck
import React, { useState } from 'react';
import { 
  FileText, Cpu, Compass, BookOpen, Search, Filter, 
  ShieldCheck, HelpCircle, Activity, ArrowRight, Zap, 
  RefreshCw, Layers, Award, Radio, CheckCircle2, AlertTriangle, Database
} from 'lucide-react';

interface InsightItem {
  id: string;
  title: string;
  finding: string;
  category: string;
}

export const ResearchInsights: React.FC = () => {
  const [activeSegment, setActiveSegment] = useState<'roadmap' | 'architecture' | 'glossary'>('roadmap');
  
  // Roadmap states
  const [selectedPhase, setSelectedPhase] = useState<number>(0);
  const [activeTelemetryRow, setActiveTelemetryRow] = useState<number | null>(null);
  const [activeWorkflowStep, setActiveWorkflowStep] = useState<number>(0);

  // Architecture Simulation states
  const [simStep, setSimStep] = useState<number>(0);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simRegisters, setSimRegisters] = useState<{A: string; B: string; C: string; D: string}>({
    A: 'Earth (Vibration Basis)',
    B: 'Mars (Thermal Limit)',
    C: 'Jupiter (Pressure Crest)',
    D: 'Saturn (Acoustic Noise)'
  });
  const [simHistory, setSimHistory] = useState<string[]>([
    'System Initialized: All cognitive sensor pointers mapped correctly.'
  ]);

  // Glossary States
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedGlossaryCategory, setSelectedGlossaryCategory] = useState<string>('all');

  // --- GLOSSARY DATA ---
  const GLOSSARY_ITEMS = [
    {
      term: 'Time-Based Maintenance',
      category: 'maintenance',
      definition: 'Replacing parts or scheduling servicing purely based on calendar time or run-hour thresholds rather than actual wear. It ignores the fact that 89% of industrial failures are random and non-age-related, often leading to premature replacement of healthy components.',
      impact: 'Wasteful schedule overhead, misses latent faults.'
    },
    {
      term: 'Condition-Based Maintenance',
      category: 'maintenance',
      definition: 'Maintenance performed only when physical parameters indicate degradation is underway. It relies heavily on basic indicator triggers (alarms, visual checks, standard thresholds) or human observations.',
      impact: 'Incurs risk since detection occurs late in the degrade cycle.'
    },
    {
      term: 'Predictive Maintenance (PdM)',
      category: 'maintenance',
      definition: 'Using real-time sensor data paired with advanced trended AI analysis to forecast the precise future moment of failures. This allows servicing to be scheduled exactly when required—weeks or months before catastrophic damage.',
      impact: 'Eliminates unexpected shutdown cycles entirely.'
    },
    {
      term: 'The 11% vs. 89% Rule',
      category: 'maintenance',
      definition: 'Studies in reliability engineering showing that only 11% of industrial assets fail strictly due to age-related wear. The remaining 89% fail randomly due to operational stresses, installation misalignment, load transients, or manufacturer defects.',
      impact: 'Proves the standard calendar-based maintenance paradigm flawed.'
    },
    {
      term: 'Fast Fourier Transform (FFT)',
      category: 'vibration',
      definition: 'The mathematical algorithm that deconstructs a chaotic time-domain vibration waveform into a frequency-domain spectrogram. It isolates individual frequencies, allowing technicians to diagnose specific faults.',
      impact: 'Decodes a messy acoustic wave into diagnostic elements.'
    },
    {
      term: '1x vs 2x RPM Frequency Peaks',
      category: 'vibration',
      definition: 'In vibration analytics, a peak corresponding precisely to the motor rotational frequency (1x) suggests mechanical unbalance in the rotor. A peak at twice the speed (2x) signals angular alignment issues or coupling slack.',
      impact: 'Identifies the precise physical root cause of a shaking asset.'
    },
    {
      term: 'ISO 10816 Standard',
      category: 'vibration',
      definition: 'An international standard establishing vibration velocity criteria (measured in mm/s RMS) to classify machinery operating severity. It sets universal boundaries for Normal, Caution, Alert, and Danger thresholds.',
      impact: 'Enforces a unified, regulatory baseline of physical health.'
    },
    {
      term: 'The P-F Interval Curve',
      category: 'pf curve',
      definition: 'The time window extending between point (P) when a potential failure first becomes physically detectable via high-frequency sensors, and point (F) when the asset experiences total functional failure.',
      impact: 'Vibration monitoring maximizes this lead time to order parts gracefully.'
    },
    {
      term: 'Potential Failure (Point P)',
      category: 'pf curve',
      definition: 'The earliest detection point where physical degradation first surfaces. Usually detectable only by sub-audible high-frequency sensors (vibration spectral analysis) long before humans hear heat or noise.',
      impact: 'Gives weeks or months of operational safety head-start.'
    },
    {
      term: 'Functional Failure (Point F)',
      category: 'pf curve',
      definition: 'The catastrophic crossing point where an asset seizes or crashes, losing its ability to perform its designed function, typically provoking secondary damage.',
      impact: 'Halts production, resulting in emergency repairs and immense financial losses.'
    },
    {
      term: 'Unlabeled Data Paradox',
      category: 'data science',
      definition: 'The industrial reality where continuous sensor streams produce massive volumes of unlabeled telemetry, but scarce failure logs exist. Requires unsupervised clustering algorithms to isolate deviations.',
      impact: 'Bridges raw continuous data and target fault tags.'
    },
    {
      term: 'Imbalanced Data / SMOTE',
      category: 'data science',
      definition: 'Machines run healthy 99.9% of the time, making raw failure records rare. Synthetic Minority Over-sampling Technique (SMOTE) artificially generates balanced failure signatures so AI models don\'t overlook anomalies.',
      impact: 'Ensures reasoning agents aren\'t biased toward "always healthy" states.'
    },
    {
      term: 'MCAR, MAR, and MNAR Data',
      category: 'data science',
      definition: 'Telemetry missingness types: Missing Completely at Random (MCAR), Missing at Random (MAR), and Missing Not at Random (MNAR). A failed high-temperature sensor that melted because the system exceeded limits represents a critical MNAR state.',
      impact: 'Requires correlated pressure/vibration cross-checks rather than raw imputation.'
    },
    {
      term: 'One-Class Anomaly Detection',
      category: 'data science',
      definition: 'An algorithmic design where the AI is trained strictly on standard baseline behavior, flagging any telemetry cluster situated outside this boundaries as a potential rare failure mode.',
      impact: 'Detects previously unseen or collective mechanical failures.'
    },
    {
      term: 'Behavioral Observability Layer',
      category: 'agent observability',
      definition: 'Monitoring the AI agent\'s reasoning pathways, cognitive tree choices, and branching plans to ensure its physical intervention commands align directly with intent.',
      impact: 'Prevents rogue planning or runaway loop iterations.'
    },
    {
      term: 'Operational Observability Layer',
      category: 'agent observability',
      definition: 'Tracks physical CPU temperatures, active API gateway latencies, raw token usage metrics, and database write latencies of the running co-pilot system.',
      impact: 'Maintains system-level resource efficiency.'
    },
    {
      term: 'Decision Observability Layer',
      category: 'agent observability',
      definition: 'Validates individual output correctness and policy choices against verified domain catalogs (e.g. comparing structural work proposals with ISO severity limits).',
      impact: 'Confirms proposed maintenance tasks are physically safe and optimized.'
    },
    {
      term: 'Governance Observability Layer',
      category: 'agent observability',
      definition: 'Enforces hard policy invariants, privacy filters, real-time PII redaction rules, and cryptographic DID audit logs using Model Context Protocols (MCP) and Agent-to-Agent (A2A) handshakes.',
      impact: 'Verifies continuous regulatory compliance across hardware networks.'
    },
    {
      term: 'NabaOS Framework',
      category: 'agent observability',
      definition: 'An architectural paradigm for scaling token-optimized multi-agent systems. It avoids the exponential compute accumulation of traditional agent networks by implementing a 5-tier cache cascade alongside semantic deduplication.',
      impact: 'Reduces 130-agent swarm communication costs from thousands to pennies (penny-perfect constraint).'
    },
    {
      term: 'W5H2 Canonicalization',
      category: 'agent observability',
      definition: 'A semantic structuring approach that decomposes natural language prompts into What, Where, Who, When, Why, How, and How Much keys, creating unique cache identifiers.',
      impact: 'Bridges arbitrary user triggers to exact, repeatable cache slots, bypassing LLM parsing.'
    },
    {
      term: 'Epistemic Verification (Pramana)',
      category: 'agent observability',
      definition: 'The evaluation of tool and agent findings classified under Indian Epistemological Shastra (Pratyaksha: direct outputs, Anumana: logical inferences, Sabda: authority testimony, Abhava: absence proofs) to eradicate hallucinations.',
      impact: 'Guarantees each executed command carries an authorized, audited cryptographic validation receipt.'
    }
  ];

  // --- ROADMAP DATA ---
  const ROADMAP_PHASES = [
    {
      title: 'Phase I: Instrumentation & Telemetry Standardization',
      timeline: 'Q1-Q2 2026',
      objective: 'Establish a unified signal-sharing baseline across physical sensors and cognitive agent layers using OpenTelemetry semantic structures.',
      deliverables: [
        'Deploy high-frequency MEMS multi-axial vibration sensors to critical rotating assets.',
        'Configure OTlp collectors with GenAI semantic convention metadata tags.',
        'Initialize unified telemetry streaming spanning AI token tracking alongside vibration mm/s baselines.'
      ],
      progress: 100,
      badge: 'Completed'
    },
    {
      title: 'Phase II: Decision Observability & Guardrail Enforcement',
      timeline: 'Q3-Q4 2026',
      objective: 'Secure deep tracking of autonomous decisions to prevent semantic drift, executing deterministic UUID verification ledgers.',
      deliverables: [
        'Enforce mandatory SHA256 cryptographic hashes for every scheduled LLM task execution.',
        'Integrate "LLM-as-a-judge" grading nodes monitoring the reliability of reasoning traces.',
        'Deploy real-time PII scrubbing and automatic sensor error boundary checks.'
      ],
      progress: 65,
      badge: 'Active'
    },
    {
      title: 'Phase III: Automated Operations & Adaptive Behavior',
      timeline: '2027',
      objective: 'Complete the loop: synchronize the AI detection system with automated CMMS (Oxmaint) work scheduling, optimizing maintenance.',
      deliverables: [
        'Inaugurate autonomous API-driven CMMS dispatch containing attached raw FFT spectrogram markers.',
        'Shift from rigid date-based plant lubing to friction-coefficient-driven grease requests.',
        'Optimize multi-agent planning frameworks to resolve complex multi-asset pipeline outages.'
      ],
      progress: 10,
      badge: 'Scheduled'
    }
  ];

  // --- TELEMETRY INTEGRATION MATRIX DATA ---
  const TELEMETRY_MATRIX = [
    {
      type: 'Metrics',
      agent: 'Token consumption, per-step planning latency, API throughput.',
      sensor: 'Continuous vibration velocity (mm/s), thermal sensor indexes, psi values.',
      impact: 'Yields a continuous operational cost-to-health ratio score per physical asset.'
    },
    {
      type: 'Events',
      agent: 'Active MCP tool calls, agent state swaps, safety guardrail triggers.',
      sensor: 'ISO 10816 threshold breach, digital circuit trips, operator manual adjustments.',
      impact: 'Captures the exact microsecond an autonomous agent decides to trigger a bypass.'
    },
    {
      type: 'Logs',
      agent: 'Step reasoning traces, prompt prompts, model fallback triggers.',
      sensor: 'Local CMMS history records, operator shift notations, vibration audit files.',
      impact: 'Supplies the comprehensive auditable story required for high-stakes audits.'
    },
    {
      type: 'Traces',
      agent: 'End-to-end trace context (Planning → Active Validation → Tool Trigger).',
      sensor: 'High-frequency raw Time Waveforms, FFT spectrogram peak updates.',
      impact: 'Correlates an automated work order directly with physical transducer stress spikes.'
    }
  ];

  // --- AUTOMATED WORKFLOW STEPS ---
  const WORKFLOW_STEPS = [
    {
      title: '1. Anomalous Event Detection',
      actor: 'Physical MEMS Accelerometer',
      description: 'A sensor detects emerging 2x vibration velocity harmonics on Pump Alpha\'s outer bearing race exceeding caution thresholds.',
      code: '{\"vibration_velocity_rms\": \"8.4 mm/s\", \"frequency_peak_hz\": 60.2}'
    },
    {
      title: '2. Cognitive State Alignment',
      actor: 'Veklom Hybrid Agent Core',
      description: 'The agent maps the 2x frequency peak directly with its dynamic state model, assessing the asset\'s lead time on the P-F curve (18 days to failure).',
      code: '{\"pf_interval_lead_days\": 18, \"recommended_action\": \"Inspect shaft alignment\"}'
    },
    {
      title: '3. API CMMS Work Order Dispatch',
      actor: 'Orchestration Gateway (MCP)',
      description: 'An automated MCP handshake packages the FFT vibration plot with reasoning evidence, generating a CMMS ticket on the Oxmaint interface.',
      code: 'POST /api/v1/cmms/work_order {\"asset_id\": \"PUMP_ALPHA\", \"priority\": \"CRITICAL\", \"instructions\": \"Align and grease coupling\"}'
    },
    {
      title: '4. Human Closure & Re-zero Baseline',
      actor: 'Maintenance Technician',
      description: 'A technician aligns the coupling shaft. A subsequent sensor check records a healthy status, clearing the active alarm and re-zeroing the model\'s memory ledger.',
      code: '{\"repair_status\": \"CLOSED\", \"resolved_by_technician_id\": \"TECH-9912\"}'
    }
  ];

  // --- ARCHITECTURE SIMULATOR CONTROLS ---
  const handleSimulateStep = () => {
    if (simStep >= 4) {
      // Reset
      setSimStep(0);
      setSimRegisters({
        A: 'Earth (Vibration Basis)',
        B: 'Mars (Thermal Limit)',
        C: 'Jupiter (Pressure Crest)',
        D: 'Saturn (Acoustic Noise)'
      });
      setSimHistory(['Simulator Re-initialized. All cognitive pointers set.']);
      return;
    }

    const nextStep = simStep + 1;
    setSimStep(nextStep);
    
    if (nextStep === 1) {
      // Step 1: Swap A & B (Simulating sensor shift)
      setSimRegisters(prev => ({ ...prev, A: prev.B, B: prev.A }));
      setSimHistory(p => [
        ...p,
        'Instruction: Swap Register A (Vibration) & Register B (Thermal).',
        'Transformer State Update: KV attention maps shifted. Softmax uncertainty introduced (+12%).',
        'Hybrid State Update: Recurrent hidden registers updated in linear time. Coherence 100%'
      ]);
    } else if (nextStep === 2) {
      // Step 2: Swap B & C
      setSimRegisters(prev => ({ ...prev, B: prev.C, C: prev.B }));
      setSimHistory(p => [
        ...p,
        'Instruction: Swap Register B (Vibration) & Register C (Pressure).',
        'Transformer State Update: Softmax entropy increased. Model "attention sink" starting to decay.',
        'Hybrid State Update: Relational variables consolidated. Perfect index tracking sustained.'
      ]);
    } else if (nextStep === 3) {
      // Step 3: Swap C & D
      setSimRegisters(prev => ({ ...prev, C: prev.D, D: prev.C }));
      setSimHistory(p => [
        ...p,
        'Instruction: Swap Register C (Vibration) & Register D (Acoustic).',
        'Transformer State Update: Critical decay. The self-attention matrix loses sequential dependency tracking.',
        'Hybrid State Update: Memory remains stabilized by recurrent feedback nodes.'
      ]);
    } else if (nextStep === 4) {
      // Final readout state matches target
      setSimHistory(p => [
        ...p,
        'Execution Terminated: Reading final slot for "Vibration Basis"...',
        'Transformer Final Output ❌: "Mars (Thermal Limit)" [Incorrect - context corrupted by token-drift]',
        'Hybrid Final Output   ✓: "Saturn (Acoustic Noise)" [100% Correct - state preserved across recurrent sequence!]'
      ]);
    }
  };

  const filteredGlossary = GLOSSARY_ITEMS.filter(item => {
    const matchesSearch = item.term.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          item.definition.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedGlossaryCategory === 'all' || item.category === selectedGlossaryCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="bg-[#0b1219]/70 border border-cyan-800/40 rounded-xl p-5 backdrop-blur-md relative overflow-hidden shadow-[0_4px_30px_rgba(0,0,0,0.8)]">
      
      {/* Decorative background grid and glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-cyan-500/5 rounded-full filter blur-[80px] -z-10 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-60 h-60 bg-purple-500/5 rounded-full filter blur-[60px] -z-10 pointer-events-none"></div>

      {/* Frame Top Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-cyan-950/60 pb-4 mb-5 gap-3">
        <div>
          <div className="text-[12px] font-black text-white px-2 py-0.5 bg-cyan-950/80 border border-cyan-500/20 max-w-fit rounded text-xs mb-1.5 uppercase tracking-widest flex items-center gap-1.5">
            <Radio size={12} className="text-cyan-400 animate-pulse" />
            Veklom Research Center
          </div>
          <div className="text-sm font-bold text-white tracking-wide">
            Unified Agentic-Industrial Observability Framework
          </div>
          <div className="text-[9px] text-cyan-400/70 font-mono uppercase tracking-wider mt-0.5">
            Operational Resilience & Dynamic Reasoning Systems // Live Documentation
          </div>
        </div>

        {/* Tab Selection Segments */}
        <div className="flex gap-1.5 p-0.5 bg-black/40 border border-white/5 rounded-lg w-full md:w-auto overflow-x-auto">
          {[
            { id: 'roadmap', label: 'Strategic Roadmap', icon: Compass },
            { id: 'architecture', label: 'Backend Architecture', icon: Cpu },
            { id: 'glossary', label: 'Predictive Glossary', icon: BookOpen }
          ].map(seg => {
            const IconComp = seg.icon;
            return (
              <button
                key={seg.id}
                onClick={() => setActiveSegment(seg.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[9px] font-extrabold uppercase tracking-widest rounded-md transition-all whitespace-nowrap cursor-pointer ${
                  activeSegment === seg.id 
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold' 
                    : 'text-white/40 hover:text-white/70 border border-transparent'
                }`}
              >
                <IconComp size={10} />
                {seg.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB CONTAINER VIEWPORT */}
      <div className="min-h-[380px]">

        {/* ----------------- ROADMAP SEGMENT ----------------- */}
        {activeSegment === 'roadmap' && (
          <div className="space-y-6">
            
            <div className="bg-cyan-950/10 border border-cyan-900/30 p-4 rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-white uppercase block">
                  Merging AI Reasoning with Physical Reliability
                </span>
                <p className="text-[9px] text-white/50 font-sans leading-relaxed">
                  In critical facilities, 89% of failures occur randomly due to latent stresses. Opaque &quot;black box&quot; models are replaced by a unified signaling telemetry layer (MELT mapped directly with high-frequency time waveforms).
                </p>
              </div>
              <div className="text-center bg-[#070b10] border border-cyan-800/20 px-4 py-2 rounded shrink-0 w-full md:w-auto">
                <div className="text-xl font-black text-cyan-400 font-mono">89%</div>
                <div className="text-[7.5px] text-white/40 uppercase tracking-widest">Random Stress Failures</div>
              </div>
            </div>

            {/* Interactive Timeline Phasing */}
            <div className="space-y-3">
              <span className="text-[9px] font-bold tracking-widest text-cyan-500/80 uppercase block">
                Phased Integration Strategy (2026-2027)
              </span>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {ROADMAP_PHASES.map((phase, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedPhase(idx)}
                    className={`p-3 border rounded-xl transition-all duration-300 cursor-pointer ${
                      selectedPhase === idx 
                        ? 'border-cyan-500 bg-cyan-950/20 shadow-[0_0_15px_rgba(6,182,212,0.1)]' 
                        : 'border-white/5 bg-white/[0.01] opacity-75 hover:opacity-100 hover:border-white/10'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[7.5px] font-mono tracking-widest text-cyan-400 font-bold uppercase block">
                        {phase.timeline}
                      </span>
                      <span className={`text-[7px] font-bold px-1.5 py-0.5 rounded uppercase ${
                        phase.badge === 'Completed' ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-500/20' : 
                        phase.badge === 'Active' ? 'bg-amber-900/30 text-amber-400 border border-amber-500/20 animate-pulse' : 
                        'bg-white/5 text-white/30 border border-white/10'
                      }`}>
                        {phase.badge}
                      </span>
                    </div>

                    <div className="text-[10px] font-bold text-white mb-2 leading-tight">
                      {phase.title}
                    </div>

                    {/* Miniature progress meter */}
                    <div className="h-1 bg-black/40 rounded-full overflow-hidden mb-1">
                      <div 
                        className={`h-full transition-all duration-500 ${phase.badge === 'Completed' ? 'bg-emerald-400' : 'bg-cyan-400'}`} 
                        style={{ width: `${phase.progress}%` }}
                      ></div>
                    </div>
                    <div className="text-[7px] text-white/30 text-right uppercase font-mono">{phase.progress}% Transmitted</div>
                  </div>
                ))}
              </div>

              {/* Collapsed Description Area for chosen phase */}
              <div className="bg-[#060b0f] border border-cyan-900/40 p-4 rounded-xl space-y-3 font-mono text-[9px]">
                <div className="flex justify-between items-center pb-1.5 border-b border-cyan-950">
                  <span className="text-[8px] font-bold text-cyan-400 uppercase tracking-widest">
                    Milestone Overview: {ROADMAP_PHASES[selectedPhase].timeline}
                  </span>
                  <span className="text-white/30">TECHNICAL STACK SPECIFICATIONS</span>
                </div>
                <p className="text-white/80 font-sans text-[10px] leading-relaxed">
                  {ROADMAP_PHASES[selectedPhase].objective}
                </p>
                <div className="space-y-1.5 pt-1.5">
                  <span className="text-[7.5px] text-white/40 block uppercase font-bold">Action Deliverables Required:</span>
                  {ROADMAP_PHASES[selectedPhase].deliverables.map((del, i) => (
                    <div key={i} className="flex gap-2 items-start py-0.5">
                      <CheckCircle2 size={10} className="text-cyan-400 shrink-0 mt-0.5" />
                      <span className="text-white/75 leading-relaxed font-sans text-[9px]">{del}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Interactive Telemetry Matrix */}
            <div className="space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-[9px] font-bold tracking-widest text-cyan-500/80 uppercase">
                  Telemetry Synchronization Matrix (OPENTELEMETRY BASE)
                </span>
                <span className="text-[7.5px] text-white/30 lowercase italic">Click a row to inspect its causal trace logic</span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-cyan-900/30">
                <table className="w-full text-left font-mono text-[9px] border-collapse bg-black/20">
                  <thead>
                    <tr className="border-b border-cyan-950 bg-cyan-950/20 text-white/40 uppercase text-[8px] tracking-wider">
                      <th className="p-2.5">Telemetry Type</th>
                      <th className="p-2.5">Agent Signal (MELT)</th>
                      <th className="p-2.5">Industrial Equivalent (Sensor)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-purple-950/20">
                    {TELEMETRY_MATRIX.map((row, idx) => (
                      <tr 
                        key={idx}
                        onClick={() => setActiveTelemetryRow(activeTelemetryRow === idx ? null : idx)}
                        className={`hover:bg-cyan-950/10 transition-colors cursor-pointer ${
                          activeTelemetryRow === idx ? 'bg-cyan-950/20 text-white' : 'text-white/70'
                        }`}
                      >
                        <td className="p-2.5 font-bold text-cyan-400 border-r border-cyan-950/25">{row.type}</td>
                        <td className="p-2.5 border-r border-cyan-950/25">{row.agent}</td>
                        <td className="p-2.5">{row.sensor}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Explanatory impact card based on selected telemetry model */}
              {activeTelemetryRow !== null && (
                <div className="p-3 bg-cyan-900/10 border border-cyan-500/20 rounded-lg flex items-center gap-3 animate-fade-in font-mono text-[8.5px]">
                  <Award size={14} className="text-cyan-400 shrink-0 animate-pulse" />
                  <div>
                    <span className="text-white/30 uppercase font-black block">Causal Trace Link Impact ({TELEMETRY_MATRIX[activeTelemetryRow].type})</span>
                    <span className="text-cyan-300 font-sans text-[9.5px] block mt-0.5 leading-relaxed">
                      {TELEMETRY_MATRIX[activeTelemetryRow].impact}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Vibration-Triggered Workflow Cycle */}
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-cyan-950 pb-1">
                <span className="text-[9px] font-bold tracking-widest text-cyan-500/80 uppercase">
                  Vibration-Triggered Agent Workflow
                </span>
                <span className="text-[7.5px] text-white/30 font-medium">REAL-TIME EXECUTION BLOCK (2026 STANDARDS)</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                {WORKFLOW_STEPS.map((step, i) => (
                  <div
                    key={i}
                    onClick={() => setActiveWorkflowStep(i)}
                    className={`p-2.5 border rounded-lg transition-all duration-300 cursor-pointer ${
                      activeWorkflowStep === i 
                        ? 'border-purple-500 bg-purple-950/10 shadow-[0_0_12px_rgba(168,85,247,0.15)]' 
                        : 'border-white/5 bg-white/[0.01] hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="text-[8px] font-bold text-purple-400 uppercase tracking-wider mb-1">
                      {step.title}
                    </div>
                    <span className="text-[7px] text-white/30 font-mono italic block mb-1">ACTOR: {step.actor}</span>
                    <p className="text-[8px] text-white/60 font-sans leading-relaxed line-clamp-2">
                      {step.description}
                    </p>
                  </div>
                ))}
              </div>

              {/* Code execution envelope detailed mockup */}
              <div className="bg-[#05090c] border border-cyan-950 p-3 rounded-lg flex flex-col md:flex-row gap-4 font-mono text-[9px] justify-between">
                <div className="md:w-1/2 space-y-1">
                  <span className="text-white/40 uppercase text-[8px] block">Trace Diagnostic Details</span>
                  <div className="text-white text-[10px] font-bold">{WORKFLOW_STEPS[activeWorkflowStep].title}</div>
                  <p className="text-white/70 font-sans text-[9px] leading-relaxed pt-1">
                    {WORKFLOW_STEPS[activeWorkflowStep].description}
                  </p>
                  <div className="text-[7.5px] text-purple-400 font-bold uppercase tracking-widest pt-2.5 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-ping"></span>
                    Audit Hash generated & cataloged securely.
                  </div>
                </div>

                <div className="flex-1 bg-black/40 border border-white/[0.02] p-2.5 rounded text-[8px] font-mono select-all">
                  <span className="text-cyan-500 font-bold block mb-1 uppercase tracking-widest">TRANSDUCER JSON PAYLOAD</span>
                  <pre className="text-white/80 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {WORKFLOW_STEPS[activeWorkflowStep].code}
                  </pre>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ----------------- ARCHITECTURE SEGMENT ----------------- */}
        {activeSegment === 'architecture' && (
          <div className="space-y-6 font-mono text-[10px]">
            
            <div className="bg-purple-950/10 border border-purple-500/20 p-4 rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-white uppercase block">
                  Why Standard Transformers Collapse on States
                </span>
                <p className="text-[9px] text-white/50 font-sans leading-relaxed">
                  Softmax-based self-attention scales at <strong>O(n²)</strong>. Because standard Transformers rely entirely on the token sequence scratchpad (External State), they drift rapidly as sequential dependencies deepen. Hybrid recurrent nodes (like Olmo3) compress context linearly to secure stability in mission-critical asset workflows.
                </p>
              </div>
              <div className="bg-[#070b10] border border-cyan-800/20 px-4 py-2 rounded text-center shrink-0 w-full md:w-auto">
                <div className="text-base font-black text-rose-400 font-mono">O(n²) Complexity</div>
                <span className="text-[7px] text-white/30 uppercase tracking-widest">Transformer Peak Penalty</span>
              </div>
            </div>

            {/* Simulated Live Variable-Swap Astro-Recall Simulator */}
            <div className="bg-[#060b0f] border border-cyan-900/30 p-4 rounded-xl space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-cyan-950">
                <div>
                  <span className="text-[9px] font-bold tracking-widest text-cyan-400 uppercase">
                    Astro Recall State-Tracking simulator
                  </span>
                  <span className="text-[7px] text-white/30 block mt-0.5 uppercase">VERIFYING COMBINATORIAL REGISTER SWAPS STABILITY</span>
                </div>

                <button
                  onClick={handleSimulateStep}
                  className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-600 active:scale-95 text-black font-extrabold text-[8px] uppercase tracking-widest rounded transition-all flex items-center justify-center gap-1 shadow-[0_0_10px_rgba(6,182,212,0.25)] cursor-pointer"
                >
                  <RefreshCw size={9} className={simStep > 0 && simStep < 4 ? 'animate-spin' : ''} />
                  {simStep === 0 ? 'START REGISTER RUN' : simStep === 4 ? 'RESET SYSTEM' : `STEP FORWARD (${simStep}/3)`}
                </button>
              </div>

              {/* Memory Register Boxes Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-black/40 p-3 rounded-lg border border-cyan-950/40 text-center">
                {[
                  { key: 'A', name: 'Register A', val: simRegisters.A, color: 'text-cyan-400 border-cyan-500/20' },
                  { key: 'B', name: 'Register B', val: simRegisters.B, color: 'text-amber-400 border-amber-500/20' },
                  { key: 'C', name: 'Register C', val: simRegisters.C, color: 'text-purple-400 border-purple-500/20' },
                  { key: 'D', name: 'Register D', val: simRegisters.D, color: 'text-pink-400 border-pink-500/20' }
                ].map((reg) => (
                  <div key={reg.key} className={`p-2.5 bg-[#05090c] border rounded-lg ${reg.color}`}>
                    <span className="text-white/30 text-[7px] uppercase tracking-widest block mb-1">{reg.name}</span>
                    <span className="text-[10px] font-black tracking-normal block text-white">{reg.val}</span>
                  </div>
                ))}
              </div>

              {/* Dual System Progress Output Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Standard Transformer Indicator */}
                <div className="bg-[#05090c]/80 border border-rose-950/30 p-3 rounded-lg flex flex-col justify-between">
                  <div className="space-y-1">
                    <span className="text-[8px] font-black text-rose-400 uppercase block">1. Standard Transformer Backbone</span>
                    <div className="flex justify-between text-[7.5px] text-white/40 uppercase">
                      <span>Attention Grid Drift:</span>
                      <span className="text-rose-400 font-bold">{simStep * 28}% (high)</span>
                    </div>
                    <div className="h-1.5 bg-black rounded-full overflow-hidden mt-1">
                      <div className="h-full bg-rose-500" style={{ width: `${Math.min(100, simStep * 28)}%` }}></div>
                    </div>
                  </div>
                  <div className="text-[7.5px] italic text-rose-300/60 leading-tight pt-3">
                    {simStep === 0 && 'Stable baseline: Attention anchors linked to start context.'}
                    {simStep === 1 && 'Minor Drift: Keys and query matrices mismatch during alignment lookup.'}
                    {simStep === 2 && 'Substantial Drift: Accumulating Softmax denominators corrupting historical weights.'}
                    {simStep === 3 && 'Severe Drift: Attention focus collapses under index sequence dependencies.'}
                    {simStep === 4 && 'Output Breakdown ❌: Returns raw error parameters. System accuracy falls to zero.'}
                  </div>
                </div>

                {/* Hybrid Recurrent (Olmo3) Indicator */}
                <div className="bg-[#05090c]/80 border border-emerald-950/30 p-3 rounded-lg flex flex-col justify-between">
                  <div className="space-y-1">
                    <span className="text-[8px] font-black text-emerald-400 uppercase block">2. Hybrid Recurrent Node (Olmo3)</span>
                    <div className="flex justify-between text-[7.5px] text-white/40 uppercase">
                      <span>Internal Alignment Stability:</span>
                      <span className="text-emerald-400 font-bold">100% Constant</span>
                    </div>
                    <div className="h-1.5 bg-black rounded-full overflow-hidden mt-1">
                      <div className="h-full bg-emerald-500" style={{ width: '100%' }}></div>
                    </div>
                  </div>
                  <div className="text-[7.5px] italic text-emerald-300/60 leading-tight pt-3">
                    {simStep === 0 && 'Stable baseline: Linear recurrence state vector loaded.'}
                    {simStep === 1 && 'Astro swap executed smoothly: latent vectors updated explicitly.'}
                    {simStep === 2 && 'Recursive variables locked securely in compressed hidden registers.'}
                    {simStep === 3 && 'Sustained State: Constant sequence memory maintained.'}
                    {simStep === 4 && 'Execution Verifed ✓: Accurately retrieves Saturn values without context loss.'}
                  </div>
                </div>

              </div>

              {/* Dynamic Action logs ticker */}
              <div className="space-y-1 dark-logs text-[8px] bg-black/60 p-2.5 border border-white/5 rounded-lg max-h-[85px] overflow-y-auto scrollbar-hide">
                <span className="text-white/20 uppercase font-black text-[7px] block border-b border-white/[0.02] pb-0.5 mb-1.5">COLLISION SIMULATOR ACTIVITY REGISTER</span>
                {simHistory.map((hist, idx) => (
                  <div key={idx} className="text-cyan-400/80 leading-relaxed font-mono">
                    {hist}
                  </div>
                ))}
              </div>
            </div>

            {/* Architectural Matrix Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              <div className="bg-white/[0.01] border border-white/5 p-4 rounded-xl space-y-3">
                <span className="text-[9px] font-black tracking-widest text-purple-400 uppercase block">
                  Foundational Reasoning Alternatives
                </span>

                <div className="space-y-3">
                  <div className="bg-black/30 p-2 rounded border border-white/5">
                    <span className="text-[8px] font-bold text-white block">RECALL (Associative Memory)</span>
                    <p className="text-[8px] text-white/50 leading-relaxed font-sans mt-0.5">
                      Retrieve specific isolated facts from passive memory indexes. Acts as a high-precision static lookup (e.g., retrieving bearing lubrication viscosity targets from 400-page installation records).
                    </p>
                  </div>

                  <div className="bg-black/30 p-2 rounded border border-white/5">
                    <span className="text-[8px] font-bold text-white block">STATE-TRACKING (Symbolic Propagation)</span>
                    <p className="text-[8px] text-white/50 leading-relaxed font-sans mt-0.5">
                      Maintaining and explicitly transforming structured status configurations as sequential dynamics evolve (e.g. keeping variable logs stable when motor parameters degrade).
                    </p>
                  </div>

                  <div className="bg-cyan-950/25 p-2 rounded border border-cyan-800/30">
                    <span className="text-[8px] font-bold text-cyan-300 block">STATE-BASED RECALL</span>
                    <p className="text-[8px] text-cyan-400/80 leading-relaxed font-sans mt-0.5">
                      The high-value synthesis where retrieval targets are fully dictated by the output of nested, intermediate state alterations. If state-tracking fails, the retrieval target is corrupted.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-[#05090d] border border-cyan-900/30 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <span className="text-[9px] font-black tracking-widest text-cyan-400 uppercase block mb-3">
                    Strategic Selection Guidelines
                  </span>

                  <div className="space-y-2.5 font-sans text-[9px] leading-relaxed text-white/70">
                    <div className="flex gap-2 items-start">
                      <Zap size={10} className="text-cyan-400 shrink-0 mt-0.5" />
                      <p>
                        <strong>Deploy Transformers when:</strong> The objectives emphasize isolated query accuracy, document lookup precision, or low-dependency operations requiring standard semantic index comparisons.
                      </p>
                    </div>

                    <div className="flex gap-2 items-start">
                      <Layers size={10} className="text-purple-400 shrink-0 mt-0.5" />
                      <p>
                        <strong>Deploy Hybrids when:</strong> Complex step sequences require constant state adjustments, long-term timeline memory, or massive structural updates where <strong>O(n²)</strong> context-window decay poses financial or physical risks.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="text-[7.5px] border-t border-cyan-950 pt-2 text-white/30 tracking-wide font-mono leading-snug">
                  * Note: Utilizing token generation (&quot;Think&quot; models) provides valuable visual scaffolding to help guide complex processes.
                </div>
              </div>

            </div>

          </div>
        )}

        {/* ----------------- GLOSSARY SEGMENT ----------------- */}
        {activeSegment === 'glossary' && (
          <div className="space-y-4">
            
            {/* Filter and Search Bar */}
            <div className="flex flex-col md:flex-row gap-2">
              <div className="flex-1 bg-black/40 border border-white/10 rounded-lg flex items-center px-3 gap-2">
                <Search size={12} className="text-cyan-400" />
                <input
                  type="text"
                  placeholder="Query predictive glossary (e.g. FFT, P-F, SMOTE)..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="bg-transparent border-none outline-none text-[10px] py-1.5 text-white w-full placeholder:text-white/20 font-mono"
                />
              </div>

              <div className="flex gap-1 overflow-x-auto p-0.5 bg-black/40 border border-white/5 rounded-lg">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'maintenance', label: 'Maintenance' },
                  { id: 'vibration', label: 'Vibration' },
                  { id: 'pf curve', label: 'P-F Curve' },
                  { id: 'data science', label: 'Small Data' },
                  { id: 'agent observability', label: 'Observability' }
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedGlossaryCategory(cat.id)}
                    className={`px-2.5 py-1 text-[8.5px] uppercase tracking-wider font-extrabold rounded transition-all whitespace-nowrap cursor-pointer ${
                      selectedGlossaryCategory === cat.id 
                        ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                        : 'text-white/40 hover:text-white/75'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Glossary Listing */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[420px] overflow-y-auto pr-1 scrollbar-hide border border-cyan-900/10 p-2.5 rounded-xl bg-black/20">
              {filteredGlossary.length > 0 ? (
                filteredGlossary.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 bg-white/[0.01] hover:bg-cyan-950/5 border border-white/5 rounded-xl transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex justify-between items-start mb-1.5 gap-2">
                        <span className="text-[10px] font-black text-cyan-400 font-mono">{item.term}</span>
                        <span className="text-[6.5px] bg-[#070b10] px-1.5 py-0.5 border border-cyan-800/10 text-white/40 uppercase tracking-widest rounded shrink-0 font-mono">
                          {item.category}
                        </span>
                      </div>
                      <p className="text-[9px] text-white/60 leading-relaxed font-sans mt-1">
                        {item.definition}
                      </p>
                    </div>
                    
                    <div className="mt-2.5 pt-2 border-t border-white/[0.02] flex justify-between items-center text-[7.5px] text-white/30 font-mono uppercase tracking-widest">
                      <span>Impact Category:</span>
                      <span className="text-cyan-300 font-sans tracking-normal font-bold lowercase italic">{item.impact}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-2 flex flex-col items-center justify-center p-8 text-center border border-dashed border-white/5 rounded-lg h-[180px]">
                  <AlertTriangle size={18} className="text-cyan-500/40 mb-1.5" />
                  <p className="text-[10px] text-white/40 italic font-mono uppercase">
                    No results found matching &quot;{searchQuery}&quot;
                  </p>
                </div>
              )}
            </div>

            {/* Visual Mini Diagram - P-F Curve and FFT spectrum breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2.5">
              
              <div className="bg-black/40 border border-cyan-950/40 p-3 rounded-lg flex flex-col justify-between font-mono text-[8.5px]">
                <div>
                  <span className="text-[8px] font-black tracking-widest text-cyan-400 uppercase block mb-1">
                    VIBRATION DECONSTRUCTION ECOSYSTEM (FFT)
                  </span>
                  <div className="flex items-center gap-2 text-[8px] text-white/60 pb-2 border-b border-cyan-950/40 mb-2">
                    <Database size={10} className="text-cyan-400 shrink-0" />
                    <span>Raw Waveform EKG → FFT Algorithm → Frequency Spectrum Peaks</span>
                  </div>
                  <p className="font-sans leading-relaxed text-white/50">
                    A piezoelectric sensor translates physical acceleration curves into a cumulative raw microsec voltage signal. Evaluating an FFT converts this composite spike array into standalone static frequency peaks (e.g. unbalance vs coupling tolerances), enabling immediate anomaly categorization.
                  </p>
                </div>
                <div className="text-[7.5px] text-cyan-300 italic pt-2 border-t border-cyan-950/20">
                  Standards: Automated ISO 10816 monitoring prevents secondary asset collapses.
                </div>
              </div>

              <div className="bg-black/40 border border-cyan-950/40 p-3 rounded-lg flex flex-col justify-between font-mono text-[8.5px]">
                <div>
                  <span className="text-[8px] font-black tracking-widest text-purple-400 uppercase block mb-1">
                    THE WINDOW OF OPPORTUNITY (P-F CURVE)
                  </span>
                  <div className="flex items-center gap-2 text-[8px] text-white/60 pb-2 border-b border-cyan-950/40 mb-2">
                    <Activity size={10} className="text-purple-400 shrink-0 animate-pulse" />
                    <span>Point Potential Failure (P) → weeks context lead → Point Failure (F)</span>
                  </div>
                  <p className="font-sans leading-relaxed text-white/50">
                    Traditional calendar cycles miss random installation/load stresses. High-frequency vibration observation catches potential defects (P) at sub-audible physical stages. Fixing issues during this window cuts plant labor and repair costs by 10x compared to reactive emergency halts (F).
                  </p>
                </div>
                <div className="text-[7.5px] text-purple-300 italic pt-2 border-t border-cyan-950/20">
                  Outcome: Increases asset uptime by transforming chaotic halts into planned work orders.
                </div>
              </div>

            </div>

          </div>
        )}

      </div>

    </div>
  );
};
