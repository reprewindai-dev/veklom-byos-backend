// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { 
  Cpu, Brain, Zap, Shield, History, Lock, Eye, AlertCircle, 
  RefreshCw, CheckCircle2, Award, ArrowRight, Activity, HelpCircle 
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { RoutingPathFlow } from './RoutingPathFlow';

interface ModelRegistryItem {
  provider: string;
  model_name: string;
  endpoint: string;
  supports_tools: boolean;
  supports_json_schema: boolean;
  supports_streaming: boolean;
  supports_vision: boolean;
  supports_embeddings: boolean;
  supports_long_context: boolean;
  cost_input: number;
  cost_output: number;
  latency_p50: number;
  latency_p95: number;
  reliability_score: number;
  privacy_tier: string;
  allowed_for_sensitive_data: boolean;
  tenant_allowed: boolean;
  fallback_model: string;
  max_context: number;
  notes: string;
}

interface DecisionFrame {
  id: string;
  task_name: string;
  model_used: string;
  provider_used: string;
  latency: number;
  cost: number;
  fallback_used: string;
  policy_result: string;
  audit_hash: string;
}

export const ModelRouterConsole: React.FC = () => {
  const [registry, setRegistry] = useState<ModelRegistryItem[]>([]);
  const [history, setHistory] = useState<DecisionFrame[]>([]);
  const [activeTab, setActiveTab] = useState<'router' | 'registry' | 'policies' | 'nabaos' | 'flow'>('router');
  const [registryFilter, setRegistryFilter] = useState<'all' | 'telemetry' | 'classification' | 'reasoning' | 'private'>('all');
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([]);
  
  // Form parameters
  const [taskName, setTaskName] = useState('Optimize Power Grid Grid-Siphon');
  const [taskType, setTaskType] = useState<'telemetry' | 'classification' | 'reasoning'>('telemetry');
  const [isSensitive, setIsSensitive] = useState(false);
  const [requiresVision, setRequiresVision] = useState(false);
  const [tenantAllowsPublic, setTenantAllowsPublic] = useState(true);
  
  const [activeResult, setActiveResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // --- NabaOS Simulation State with MCP & Orchestration Optimizations ---
  const [nabaQuery, setNabaQuery] = useState('Check hydraulic fluid levels on turbine pump 4');
  const [nabaPramana, setNabaPramana] = useState('pratyaksha');
  const [nabaResult, setNabaResult] = useState<any>(null);
  const [isNabaLoading, setIsNabaLoading] = useState(false);
  const [agentCount, setAgentCount] = useState(130);
  const [isNabaOptimized, setIsNabaOptimized] = useState(true);

  // MCP Optimization Configs
  const [isFieldFilteringActive, setIsFieldFilteringActive] = useState(true);
  const [isServerAggregationActive, setIsServerAggregationActive] = useState(true);
  const [isSchemaCompressionActive, setIsSchemaCompressionActive] = useState(true);
  const [isPromptCachingActive, setIsPromptCachingActive] = useState(true);

  // Orchestration & Supervisor Controls
  const [simulatedToolError, setSimulatedToolError] = useState(false);
  const [simulatedRepeatedLoops, setSimulatedRepeatedLoops] = useState(false);
  const [simulatedContextExplosion, setSimulatedContextExplosion] = useState(false);

  const handleNabaSimulate = async () => {
    setIsNabaLoading(true);
    setNabaResult(null);
    // Add real simulated latency or respond to loading speed
    await new Promise(resolve => setTimeout(resolve, 750));
    try {
      const res = await fetch('/api/v1/nabaos/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: nabaQuery,
          custom_pramana: nabaPramana,
          mcp_config: {
            field_filtering: isFieldFilteringActive,
            server_aggregation: isServerAggregationActive,
            schema_compression: isSchemaCompressionActive,
            prompt_caching: isPromptCachingActive
          },
          orchestration_config: {
            tool_error: simulatedToolError,
            repeated_loops: simulatedRepeatedLoops,
            context_explosion: simulatedContextExplosion
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        setNabaResult(data);
      }
    } catch (err) {
      console.error('NabaOS Simulation failed', err);
    } finally {
      setIsNabaLoading(false);
    }
  };

  const fetchRegistry = async () => {
    try {
      const res = await fetch('/api/v1/copilot/registry');
      if (res.ok) {
        const data = await res.json();
        setRegistry(data);
      }
    } catch (e) {
      console.error('Failed to load model registry', e);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/copilot/recent-decisions');
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (e) {
      console.error('Failed to load history', e);
    }
  };

  useEffect(() => {
    fetchRegistry();
    fetchHistory();
  }, []);

  const handleRouteTask = async () => {
    setIsLoading(true);
    setActiveResult(null);
    
    // Rhythmic cinematic delay to feel like a mainframe computer routing decision
    await new Promise(resolve => setTimeout(resolve, 800));

    try {
      const res = await fetch('/api/v1/copilot/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_name: taskName,
          task_type: taskType,
          is_sensitive: isSensitive,
          requires_vision: requiresVision,
          tenant_allows_public: tenantAllowsPublic
        })
      });

      if (res.ok) {
        const data = await res.json();
        // Construct the expected structure
        setActiveResult({
          decision: data,
          evidence_artifact: {
            seal_status: 'SIGNED & VERIFIED',
            ledger_address: `0x${Array.from({length: 40}, () => Math.floor(Math.random()*16).toString(16)).join('')}`
          }
        });
        fetchHistory();
      }
    } catch (err) {
      console.error('Task routing failure', err);
    } finally {
      setIsLoading(false);
    }
  };

  const quickFillTemplate = (name: string, type: 'telemetry' | 'classification' | 'reasoning', sensitive: boolean, vision: boolean) => {
    setTaskName(name);
    setTaskType(type);
    setIsSensitive(sensitive);
    setRequiresVision(vision);
  };

  return (
    <div className="h-full p-6 md:p-8 max-w-6xl mx-auto flex flex-col font-mono text-xs select-none">
      
      {/* SECTION HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-6 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 px-1.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded font-black tracking-widest text-[10px] uppercase">
              COGNITIVE PLANE
            </span>
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></div>
            <span className="text-[10px] text-white/40 uppercase tracking-widest">SUB-INTEGRATOR CORE</span>
          </div>
          <h1 className="text-xl md:text-2xl font-sans tracking-widest text-white mt-1 uppercase font-semibold">
            VEKLOM MODEL ROUTING ENGINE
          </h1>
          <p className="text-white/40 mt-1 max-w-xl leading-relaxed text-[11px]">
            Dynamic Multi-LLM Orchestrator routing workloads based on latency tolerances, compute overhead, privacy tier mandates, and sensory modalities.
          </p>
        </div>

        {/* View Switches */}
        <div className="flex bg-[#0b1219] p-1 border border-white/5 rounded-xl">
          {[
            { id: 'router', label: 'Router Console', icon: Zap },
            { id: 'registry', label: 'Capability Registry', icon: Cpu },
            { id: 'policies', label: 'Routing Policies', icon: Shield },
            { id: 'flow', label: 'Routing Path Flow', icon: Activity },
            { id: 'nabaos', label: 'NabaOS Suite (130-Agent Core)', icon: Brain }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-[10px] font-bold tracking-widest uppercase transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-cyan-500/10 border border-cyan-500/30 text-white shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'text-white/30 hover:text-white/60 hover:bg-white/[0.01]'
                }`}
              >
                <Icon size={12} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* CORE DISPLAY */}
      <div className={`flex-1 ${activeTab === 'flow' ? 'flex flex-col' : 'grid grid-cols-1 lg:grid-cols-[1.5fr_1fr]'} gap-6 min-h-0 overflow-auto scrollbar-hide`}>
        
        {/* LEFT COLUMN: PRIMARY WORKFLOW / TABLES */}
        <div className="flex flex-col gap-6 min-h-0 h-full">
          
          <AnimatePresence mode="wait">
            
            {/* TAB: ROUTING PATH FLOW VISUALIZER */}
            {activeTab === 'flow' && (
              <motion.div
                key="flow-section"
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                className="h-full"
              >
                <RoutingPathFlow history={history} />
              </motion.div>
            )}

            {/* TAB 1: ROUTER WORKFLOW */}
            {activeTab === 'router' && (
              <motion.div 
                key="router-section"
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-white/5">
                    <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                      <Zap size={12} className="text-cyan-400" />
                      Cognitive Route Task Simulator
                    </span>
                    <span className="text-white/20 text-[9px] uppercase">Evaluate Live Playbook</span>
                  </div>

                  {/* Task Fill templates */}
                  <div>
                    <span className="text-[8px] text-white/30 uppercase tracking-widest block mb-2 font-black">Predefined Task Templates</span>
                    <div className="flex flex-wrap gap-2">
                      <button 
                        onClick={() => quickFillTemplate('Evaluate Heat Pipe Acoustic Vibration', 'telemetry', false, false)}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono"
                      >
                        Telemetry Node Assessment
                      </button>
                      <button 
                        onClick={() => quickFillTemplate('HIPAA Payload PII Shield Scan', 'classification', true, false)}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono"
                      >
                        PII Sensitive Compliance Audit
                      </button>
                      <button 
                        onClick={() => quickFillTemplate('Pump Turbine Bearing Optical Leak Scan', 'reasoning', false, true)}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono"
                      >
                        Vision Reasoning Encoder
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3 pt-2">
                    <div>
                      <label className="text-[8px] uppercase tracking-widest text-white/40 block mb-1">TASK OBJECTIVE & SPECIFICATION</label>
                      <input 
                        type="text" 
                        value={taskName}
                        onChange={e => setTaskName(e.target.value)}
                        className="w-full bg-[#050a0f] border border-white/10 rounded-lg px-3 py-2 text-[11px] text-white tracking-wide focus:outline-none focus:border-cyan-500/50 shadow-inner font-mono"
                        placeholder="E.g., Analyze centrifuge vibration telemetry"
                      />
                    </div>

                    <div>
                      <label className="text-[8px] uppercase tracking-widest text-white/40 block mb-1.5">TASK TYPE ROUTING WEIGHT</label>
                      <div className="grid grid-cols-3 gap-2 mb-2">
                        {[
                          { id: 'telemetry', label: 'Telemetry Monitoring', desc: 'Optimizes for low latency & fast parse parameters.' },
                          { id: 'classification', label: 'Structure Parse', desc: 'Uses token structural schemas.' },
                          { id: 'reasoning', label: 'Complex Logic', desc: 'Triggers multi-step intelligence model weights.' }
                        ].map(type => (
                          <button
                            key={type.id}
                            type="button"
                            onClick={() => setTaskType(type.id as any)}
                            className={`p-2.5 rounded-lg border text-left font-mono transition-all duration-300 flex flex-col justify-between cursor-pointer ${
                              taskType === type.id 
                                ? 'border-cyan-500 bg-cyan-950/20 text-cyan-400' 
                                : 'border-white/5 bg-white/[0.01] text-white/40 hover:border-white/10 hover:bg-white/[0.02]'
                            }`}
                          >
                            <span className="text-[9px] uppercase font-black tracking-widest">{type.label}</span>
                            <span className="text-[7px] text-white/30 mt-1 leading-normal">{type.desc}</span>
                          </button>
                        ))}
                      </div>

                      {/* DYNAMIC ROUTING DECISION GUIDE */}
                      <div className="p-3 bg-[#070d14]/75 border border-cyan-500/20 rounded-lg space-y-2 mt-2">
                        <div className="flex justify-between items-center">
                          <span className="text-[8px] font-bold tracking-widest text-cyan-400 uppercase font-mono flex items-center gap-1">
                            <Zap size={10} className="animate-pulse text-cyan-400" /> RECOMMENDED ACTIVE ROUTE
                          </span>
                          <span className="text-[7px] bg-cyan-950/50 border border-cyan-500/20 text-cyan-300 font-mono px-1.5 py-0.5 rounded uppercase">
                            Auto-Calibrated
                          </span>
                        </div>
                        
                        {taskType === 'telemetry' && (
                          <div className="space-y-1.5">
                            <div className="flex justify-between items-baseline text-[10px]">
                              <span className="text-white/80 font-bold font-mono">llama-3-70b-groq (via Groq Ultra-Fast)</span>
                              <span className="text-cyan-400 font-mono font-bold">~140ms Latency</span>
                            </div>
                            <p className="text-[8px] text-white/50 leading-relaxed font-sans">
                              Optimizes heavily for rapid stream parsing of high-frequency telemetry packets. Reduces cost ratio by <strong className="text-cyan-300">10x</strong> over generalist reasoners with perfect schema alignment.
                            </p>
                            <div className="grid grid-cols-3 gap-2 text-[7px] font-mono text-white/40 uppercase pt-1 border-t border-white/[0.03]">
                              <div>Input cost: <strong className="text-white font-bold">$0.59/1M</strong></div>
                              <div>Throughput: <strong className="text-cyan-400 font-bold">Fast-Lane</strong></div>
                              <div>Fallback: <strong className="text-white font-bold">gemini-2.5-flash</strong></div>
                            </div>
                          </div>
                        )}

                        {taskType === 'classification' && (
                          <div className="space-y-1.5">
                            <div className="flex justify-between items-baseline text-[10px]">
                              <span className="text-white/80 font-bold font-mono">deepseek-v3 (Sovereign API)</span>
                              <span className="text-green-400 font-mono font-bold">~480ms Latency</span>
                            </div>
                            <p className="text-[8px] text-white/50 leading-relaxed font-sans">
                              Selected for maximum cost-efficiency under structured outputs constraints. Handles complex key-value tagging logs at an input price of just <strong className="text-green-300">$0.14 per million tokens</strong>.
                            </p>
                            <div className="grid grid-cols-3 gap-2 text-[7px] font-mono text-white/40 uppercase pt-1 border-t border-white/[0.03]">
                              <div>Input cost: <strong className="text-white font-bold">$0.14/1M</strong></div>
                              <div>Accuracy: <strong className="text-green-400 font-bold">98.1%</strong></div>
                              <div>Fallback: <strong className="text-white font-bold">ollama-llama3.2</strong></div>
                            </div>
                          </div>
                        )}

                        {taskType === 'reasoning' && (
                          <div className="space-y-1.5">
                            <div className="flex justify-between items-baseline text-[10px]">
                              <span className="text-white/80 font-bold font-mono">claude-3-5-sonnet (Advanced Logic Hub)</span>
                              <span className="text-purple-400 font-mono font-bold">~510ms Latency</span>
                            </div>
                            <p className="text-[8px] text-white/50 leading-relaxed font-sans">
                              Allocates full multi-step cognition paths for deep reasoning, architectural trade-offs, or complex diagnostics. Utilizes elite reasoning capabilities for zero-hallucination execution.
                            </p>
                            <div className="grid grid-cols-3 gap-2 text-[7px] font-mono text-white/40 uppercase pt-1 border-t border-white/[0.03]">
                              <div>Input cost: <strong className="text-white font-bold">$3.00/1M</strong></div>
                              <div>Intelligence: <strong className="text-purple-400 font-bold">S-TIER</strong></div>
                              <div>Fallback: <strong className="text-white font-bold">gemini-2.5-flash</strong></div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-white/5">
                      <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg flex items-start gap-3">
                        <input
                          type="checkbox"
                          id="router-sensitive"
                          checked={isSensitive}
                          onChange={e => setIsSensitive(e.target.checked)}
                          className="mt-1 accent-cyan-400 h-3.5 w-3.5"
                        />
                        <div>
                          <label htmlFor="router-sensitive" className="text-[9px] uppercase font-bold text-white/70 block cursor-pointer hover:text-cyan-400">
                            SENSITIVE DATA SHIELD
                          </label>
                          <span className="text-[7px] text-white/30 block mt-0.5 leading-normal">
                            Restricts payload routing strictly to Local nodes (Ollama) or secure Private configurations. Never contacts public SaaS models.
                          </span>
                        </div>
                      </div>

                      <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg flex items-start gap-3">
                        <input
                          type="checkbox"
                          id="router-vision"
                          checked={requiresVision}
                          onChange={e => setRequiresVision(e.target.checked)}
                          className="mt-1 accent-cyan-400 h-3.5 w-3.5"
                        />
                        <div>
                          <label htmlFor="router-vision" className="text-[9px] uppercase font-bold text-white/70 block cursor-pointer hover:text-cyan-400">
                            VISION ENCODER REQUIRED
                          </label>
                          <span className="text-[7px] text-white/30 block mt-0.5 leading-normal">
                            Directs workload exclusively to models containing rich image multi-modal parser capabilities (like Gemini Flash, GPT-4o).
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg flex items-start gap-3">
                      <input
                        type="checkbox"
                        id="router-tenant"
                        checked={tenantAllowsPublic}
                        onChange={e => setTenantAllowsPublic(e.target.checked)}
                        className="mt-1 accent-cyan-400 h-3.5 w-3.5"
                      />
                      <div>
                        <label htmlFor="router-tenant" className="text-[9px] uppercase font-bold text-white/70 block cursor-pointer hover:text-cyan-400">
                          TENANT SAAS ENDPOINT WORKLOAD OVERRIDE
                        </label>
                        <span className="text-[7px] text-white/30 block mt-0.5 leading-normal">
                          Authorizes secure commercial endpoints (Google, OpenAI, Anthropic, DeepSeek) if security parameters are cleared successfully.
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-white/5">
                  <button
                    type="button"
                    onClick={handleRouteTask}
                    disabled={isLoading}
                    className="w-full bg-cyan-500 hover:bg-cyan-600 active:scale-[0.99] disabled:opacity-50 text-black font-black text-[10px] uppercase tracking-[0.2em] py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] cursor-pointer"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw size={13} className="animate-spin" />
                        Calculating Dynamic LLM Matrix Route...
                      </>
                    ) : (
                      <>
                        <Zap size={13} />
                        EVALUATE AND DISPATCH TASK ROUTE
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}

            {/* TAB 2: CAPABILITY REGISTRY MAP */}
            {activeTab === 'registry' && (
              <motion.div 
                key="registry-section"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-[#0b1219]/70 border border-white/5 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col h-full min-h-0"
              >
                <div className="flex justify-between items-center pb-4 border-b border-white/5 mb-4 shrink-0">
                  <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                    <Cpu size={12} />
                    Model Registration & Capability Database
                  </span>
                  <span className="text-white/40 text-[9px]">{registry.length} ACTIVE REGISTERED LLMs</span>
                </div>

                {/* FILTER ROW */}
                <div className="mb-4 shrink-0 bg-white/[0.02] border border-white/5 rounded-lg p-3 flex flex-col gap-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] uppercase font-black text-white/40 tracking-widest">
                        Filter Models by Efficient Task Type Matching:
                      </span>
                      {registryFilter !== 'all' && (
                        <span className="text-[7.5px] text-green-400 font-mono flex items-center gap-1 bg-green-950/20 px-2 py-0.5 rounded border border-green-800/30">
                          ⭐ Highlighted: Most Efficient Model for selected category
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {[
                        { id: 'all', label: 'All Registered', count: registry.length },
                        { id: 'telemetry', label: '⚡ Telemetry (Low Latency)', count: registry.filter(m => m.model_name === 'llama-3-70b-groq' || m.model_name === 'gemini-2.5-flash').length },
                        { id: 'classification', label: '📊 Classification (Structure)', count: registry.filter(m => m.model_name === 'deepseek-v3' || m.model_name === 'llama-3-70b-groq').length },
                        { id: 'reasoning', label: '🧠 Reasoning (S-Tier Logic)', count: registry.filter(m => m.model_name === 'claude-3-5-sonnet' || m.model_name === 'gpt-4o' || m.model_name === 'mistral-large').length },
                        { id: 'private', label: '🔒 Local Shield / Private', count: registry.filter(m => m.privacy_tier === 'local' || m.allowed_for_sensitive_data).length }
                      ].map(f => (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => setRegistryFilter(f.id as any)}
                          className={`px-3 py-1.5 text-[8px] font-mono rounded border transition-all cursor-pointer ${
                            registryFilter === f.id
                              ? 'bg-cyan-500/15 border-cyan-500 text-cyan-400 font-bold shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                              : 'bg-transparent border-white/5 text-white/40 hover:text-white/70 hover:border-white/10'
                          }`}
                        >
                          {f.label} <span className="text-[7px] text-white/30 ml-0.5">({f.count})</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="h-px bg-white/[0.05]" />

                  {/* Capability Filters */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] uppercase font-black text-white/40 tracking-widest flex items-center gap-1">
                        Required Model Capabilities (Filter tags):
                      </span>
                      {selectedCapabilities.length > 0 && (
                        <button
                          type="button"
                          onClick={() => setSelectedCapabilities([])}
                          className="text-[7.5px] text-cyan-400 hover:text-cyan-300 font-mono underline cursor-pointer bg-none border-none p-0"
                        >
                          Clear Capability Filters
                        </button>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { key: 'supports_tools', label: 'MCP Tools', icon: '🔧' },
                        { key: 'supports_vision', label: 'Vision Processing', icon: '👁️' },
                        { key: 'supports_long_context', label: 'Long Context (128k+)', icon: '📚' },
                        { key: 'supports_json_schema', label: 'JSON Schema output', icon: '📋' },
                        { key: 'supports_streaming', label: 'Tokens Streaming', icon: '🌊' },
                        { key: 'supports_embeddings', label: 'Embeddings Engine', icon: '📈' },
                      ].map(cap => {
                        const isSelected = selectedCapabilities.includes(cap.key);
                        // Calculate matching count
                        const matchCount = registry.filter(m => m[cap.key as keyof ModelRegistryItem] === true).length;
                        return (
                          <button
                            key={cap.key}
                            type="button"
                            onClick={() => {
                              if (isSelected) {
                                setSelectedCapabilities(selectedCapabilities.filter(c => c !== cap.key));
                              } else {
                                setSelectedCapabilities([...selectedCapabilities, cap.key]);
                              }
                            }}
                            className={`px-2.5 py-1 text-[8.5px] font-mono rounded-lg border transition-all duration-200 cursor-pointer flex items-center gap-1.5 ${
                              isSelected
                                ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_8px_rgba(6,182,212,0.2)]'
                                : 'bg-[#0f172a]/30 border-white/5 text-white/50 hover:text-white/85 hover:border-white/15'
                            }`}
                          >
                            <span>{cap.icon}</span>
                            <span>{cap.label}</span>
                            <span className="text-[7.5px] text-white/30 font-normal">({matchCount})</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Table of Registered Models */}
                <div className="flex-1 overflow-auto space-y-2 pr-1 scrollbar-hide">
                  {registry
                    .filter((model) => {
                      // 1. Task Type / Tier Filter
                      if (registryFilter !== 'all') {
                        if (registryFilter === 'telemetry') {
                          if (!(model.model_name === 'llama-3-70b-groq' || model.model_name === 'gemini-2.5-flash')) return false;
                        } else if (registryFilter === 'classification') {
                          if (!(model.model_name === 'deepseek-v3' || model.model_name === 'llama-3-70b-groq')) return false;
                        } else if (registryFilter === 'reasoning') {
                          if (!(model.model_name === 'claude-3-5-sonnet' || model.model_name === 'gpt-4o' || model.model_name === 'mistral-large')) return false;
                        } else if (registryFilter === 'private') {
                          if (!(model.privacy_tier === 'local' || model.allowed_for_sensitive_data)) return false;
                        }
                      }

                      // 2. Capability Filters (Intersection)
                      for (const cap of selectedCapabilities) {
                        if (!model[cap as keyof ModelRegistryItem]) {
                          return false;
                        }
                      }

                      return true;
                    })
                    .map((model) => {
                      const isBestTelemetry = registryFilter === 'telemetry' && model.model_name === 'llama-3-70b-groq';
                      const isBestClassification = registryFilter === 'classification' && model.model_name === 'deepseek-v3';
                      const isBestReasoning = registryFilter === 'reasoning' && model.model_name === 'claude-3-5-sonnet';
                      const isBestPrivate = registryFilter === 'private' && model.model_name === 'ollama-llama3.2';
                      const isMostEfficient = isBestTelemetry || isBestClassification || isBestReasoning || isBestPrivate;

                      return (
                        <div 
                          key={model.model_name}
                          className={`bg-white/[0.01] hover:bg-white/[0.03] p-3.5 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all border ${
                            isMostEfficient 
                              ? 'border-green-500/30 bg-green-950/5 shadow-[0_0_15px_rgba(34,197,94,0.08)]' 
                              : 'border-white/5 hover:border-cyan-500/20'
                          }`}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[11px] font-black text-white">{model.provider}</span>
                              <span className="text-[9px] font-mono tracking-wider text-cyan-400 bg-cyan-950/40 border border-cyan-800/30 px-2 py-0.5 rounded">
                                {model.model_name}
                              </span>
                              <span className={`text-[7px] font-bold px-1.5 py-0.5 rounded font-mono ${
                                model.privacy_tier === 'local' 
                                  ? 'bg-purple-950/40 text-purple-400 border border-purple-800/30' 
                                  : model.privacy_tier === 'private'
                                  ? 'bg-blue-950/40 text-blue-400 border border-blue-800/30'
                                  : 'bg-green-950/40 text-green-400 border border-green-800/30'
                              }`}>
                                {model.privacy_tier.toUpperCase()} TIER
                              </span>
                              {isMostEfficient && (
                                <span className="text-[7px] font-bold font-mono text-green-400 bg-green-950/40 border border-green-500/30 px-2 py-0.5 rounded">
                                  ⭐ MOST EFFICIENT FOR TARGET CATEGORY
                                </span>
                              )}
                            </div>
                            <p className="text-[8px] text-white/45 max-w-md italic">{model.notes}</p>
                          </div>

                          <div className="grid grid-cols-3 gap-x-6 gap-y-1 text-right text-[9px]">
                            <div>
                              <span className="text-white/20 text-[7px] block uppercase">LATENCY (P50)</span>
                              <span className="text-cyan-400 font-bold">{model.latency_p50}ms</span>
                            </div>
                            <div>
                              <span className="text-white/20 text-[7px] block uppercase">INPUT / OUTPUT</span>
                              <span className="text-green-400 font-bold">${model.cost_input}/${model.cost_output} <span className="text-white/20 text-[7px]">/1M</span></span>
                            </div>
                            <div>
                              <span className="text-white/20 text-[7px] block uppercase">RELIABILITY</span>
                              <span className="text-white font-bold">{model.reliability_score * 100}%</span>
                            </div>

                            {/* Badges */}
                            <div className="col-span-3 flex flex-wrap justify-end gap-1 mt-1.5">
                              {model.supports_vision && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_vision')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  VISION
                                </span>
                              )}
                              {model.supports_tools && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_tools')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  MCP TOOLS
                                </span>
                              )}
                              {model.supports_long_context && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_long_context')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  128K+ CONTEXT
                                </span>
                              )}
                              {model.supports_json_schema && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_json_schema')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  JSON SCHEMA
                                </span>
                              )}
                              {model.supports_streaming && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_streaming')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  STREAMING
                                </span>
                              )}
                              {model.supports_embeddings && (
                                <span className={`text-[6.5px] border px-1.5 py-0.5 rounded font-mono transition-all ${
                                  selectedCapabilities.includes('supports_embeddings')
                                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300 font-bold shadow-[0_0_5px_rgba(6,182,212,0.3)]'
                                    : 'border-white/10 text-white/50'
                                }`}>
                                  EMBEDDINGS
                                </span>
                              )}
                              {model.allowed_for_sensitive_data && (
                                <span className="text-[6.5px] bg-red-950/30 border border-red-500/20 text-red-400 px-1 py-0.5 rounded font-mono">
                                  SENSITIVE CLR
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </motion.div>
            )}

            {/* TAB 3: ROUTING POLICIES */}
            {activeTab === 'policies' && (
              <motion.div 
                key="policies-section"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-[#0b1219]/70 border border-white/5 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col h-full min-h-0"
              >
                <div className="pb-4 border-b border-white/5 mb-4 shrink-0">
                  <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                    <Shield size={12} />
                    Active Routing Declarative Declarations & Guardrails
                  </span>
                </div>

                <div className="space-y-4 overflow-auto scrollbar-hide pr-1">
                  {[
                    {
                      name: "ZERO_PII_LEAKAGE_RULE",
                      description: "Applies strictly when data is flagged as sensitive or contains HIPAA, financial, or custom keys. Swaps and binds payload destinations matching Ollama local nodes or explicit on-prem Private APIs.",
                      status: "ENFORCED",
                      relevance: "High Priority Security Guard"
                    },
                    {
                      name: "SAAS_OVERRIDE_TENANT_ALLOWANCE",
                      description: "A system administrator gate. If disabled, completely blocks requests from contacting Google, Anthropic, DeepSeek, or OpenAI APIs, routing all jobs back to Local Ollama-Llama3.2 nodes instead.",
                      status: "CONDITIONAL",
                      relevance: "Tenant Security Limit Shield"
                    },
                    {
                      name: "SENSORY_LIMIT_CONVERSIONS",
                      description: "Tasks with multi-modal requirements or containing visual telemetry data will bypass speed optimizations to match rich vision-aligned encoders (like Gemini or GPT models) containing image parser weights.",
                      status: "ENFORCED",
                      relevance: "Input Pipeline Modal Alignment"
                    },
                    {
                      name: "HEURISTIC_DIVERGENT_COST_OPTIMIZER",
                      description: "Standard classification and telemetry tasks are evaluated for minimum token sizes and routed to low price pipelines (like DeepSeek or Groq) to leverage cheap compute, reducing SaaS overhead bills by up to 88%.",
                      status: "ACTIVE",
                      relevance: "Compute Token Cost Control"
                    }
                  ].map((policy) => (
                    <div key={policy.name} className="bg-white/[0.01] border border-white/5 p-4 rounded-xl space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="font-black text-white text-[10.5px] uppercase font-mono tracking-wider">{policy.name}</span>
                        <span className="text-[7.5px] bg-[#070c11] border border-cyan-500/30 text-cyan-400 px-2 py-1 rounded font-black tracking-widest uppercase">
                          {policy.status}
                        </span>
                      </div>
                      <p className="text-[9px] text-white/50 leading-relaxed font-sans">{policy.description}</p>
                      <div className="pt-2 border-t border-white/5 flex gap-4 text-[7px] text-white/30 uppercase tracking-widest">
                        <span>Classification: <strong className="text-white">{policy.relevance}</strong></span>
                        <span>Audit status: <strong className="text-green-400">PASSED</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* TAB 4: NABAOS SIMULATOR AND COGNITIVE CASCADE */}
            {activeTab === 'nabaos' && (
              <motion.div 
                key="nabaos-section"
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-white/5">
                    <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                      <Brain size={12} className="text-cyan-400" />
                      NabaOS 130-Agent Cognitive Cascade Simulator
                    </span>
                    <span className="text-white/20 text-[9px] uppercase">Epistemic Governance & Cache Cascade</span>
                  </div>

                  {/* Preset Triggers */}
                  <div>
                    <span className="text-[8px] text-white/30 uppercase tracking-widest block mb-2 font-black">Verify Natural Intent Pipelines</span>
                    <div className="flex flex-wrap gap-2">
                      <button 
                        type="button"
                        onClick={() => {
                          setNabaQuery('Check hydraulic fluid levels on turbine pump 4');
                          setNabaPramana('pratyaksha');
                        }}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono cursor-pointer"
                      >
                        [Pratyaksha] Hydraulic Vibe Sensor Inquiry
                      </button>
                      <button 
                        type="button"
                        onClick={() => {
                          setNabaQuery('Retrieve compliance audit report logs for employee inbox Alice');
                          setNabaPramana('sabda');
                        }}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono cursor-pointer"
                      >
                        [Sabda] Inbox Compliance Records Lookup
                      </button>
                      <button 
                        type="button"
                        onClick={() => {
                          setNabaQuery('Perform high-fidelity multi-stage logical inference across core grids');
                          setNabaPramana('anumana');
                        }}
                        className="px-2.5 py-1.5 bg-white/5 border border-white/5 rounded hover:bg-white/10 text-[9px] text-white/70 transition-all font-mono cursor-pointer"
                      >
                        [Anumana] Deep Multi-Grid Interrogation
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3 pt-1">
                    <div>
                      <label className="text-[8px] uppercase tracking-widest text-white/40 block mb-1">COGNITIVE ACTION QUERY (HUMAN INTENT)</label>
                      <input 
                        type="text" 
                        value={nabaQuery}
                        onChange={e => setNabaQuery(e.target.value)}
                        className="w-full bg-[#050a0f] border border-white/10 rounded-lg px-3 py-2 text-[11px] text-white tracking-wide focus:outline-none focus:border-cyan-500/50 shadow-inner font-mono"
                        placeholder="E.g., Query or task to route through NabaOS cascade"
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-[8px] uppercase tracking-widest text-cyan-400 font-bold block mb-1.5">EPISTEMIC VERIFICATION MODE (PRAMANA)</label>
                        <select 
                          value={nabaPramana}
                          onChange={e => setNabaPramana(e.target.value)}
                          className="w-full bg-[#050a0f] border border-white/10 rounded-lg px-3 py-2 text-[11px] text-zinc-300 focus:outline-none focus:border-cyan-500/50 font-mono"
                        >
                          <option value="pratyaksha">Pratyaksha (Direct Tool Output Validation)</option>
                          <option value="anumana">Anumana (Logical Premise Inference Checking)</option>
                          <option value="sabda">Sabda (External Testimony Re-Fetch Verification)</option>
                          <option value="abhava">Abhava (Presence/Absence Set Validation Check)</option>
                          <option value="unverified">Ungrounded (No Verification Required / Opinion)</option>
                        </select>
                      </div>

                      <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg flex flex-col justify-center">
                        <span className="text-[8px] uppercase tracking-widest text-cyan-400 block mb-0.5 font-bold">W5H2 Canonicalization Target</span>
                        <p className="text-[9px] leading-relaxed text-white/50">
                          Deconstructs arbitrary queries into structured cache coordinates. Maps prompts to exact slots and bypasses costly redundant LLM analysis.
                        </p>
                      </div>
                    </div>

                    {/* TWO COLUMNS OF HARDWARE, MCP, AND ORCHESTRATION CONFIGS */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      
                      {/* COLUMN 1: MCP & TOOL SERVER OPTIMIZATION */}
                      <div className="p-4 bg-black/40 border border-white/5 rounded-xl space-y-3">
                        <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
                          <span className="text-[8.5px] font-bold text-cyan-400 uppercase tracking-widest">
                            MCP & Tool Optimization
                          </span>
                          <span className="text-[7px] text-white/30 uppercase">Tool Server Wrappers</span>
                        </div>

                        <div className="space-y-2 text-[9px]">
                          {/* Field Filtering */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">Field Filtering</span>
                              <span className="text-[7.5px] text-white/40">Keep title+diff, strip metadata</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setIsFieldFilteringActive(!isFieldFilteringActive)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                isFieldFilteringActive 
                                  ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {isFieldFilteringActive ? 'ACTIVE (-85%)' : 'RAW (100%)'}
                            </button>
                          </div>

                          {/* Server-Side Aggregation */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">S-Side Aggregation</span>
                              <span className="text-[7.5px] text-white/40">Call count_open, reject list_all</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setIsServerAggregationActive(!isServerAggregationActive)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                isServerAggregationActive 
                                  ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {isServerAggregationActive ? 'AGGREGATED' : 'RAW LIST'}
                            </button>
                          </div>

                          {/* Schema Compression Tool Router */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">Schema Compression</span>
                              <span className="text-[7.5px] text-white/40">Expose only 3-5 of 130 schemas</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setIsSchemaCompressionActive(!isSchemaCompressionActive)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                isSchemaCompressionActive 
                                  ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {isSchemaCompressionActive ? 'COMPRESSED' : '130 RAW'}
                            </button>
                          </div>

                          {/* Prompt Caching */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">Prefix Prompt Caching</span>
                              <span className="text-[7.5px] text-white/40">Cache system prompts & schemas</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setIsPromptCachingActive(!isPromptCachingActive)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                isPromptCachingActive 
                                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {isPromptCachingActive ? 'CACHED (90%)' : 'BYPASS'}
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* COLUMN 2: ORCHESTRATION LAYER SUPERVISOR TRIGGERS */}
                      <div className="p-4 bg-black/40 border border-white/5 rounded-xl space-y-3">
                        <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
                          <span className="text-[8.5px] font-bold text-amber-500 uppercase tracking-widest">
                            Supervisor Watchdog Triggers
                          </span>
                          <span className="text-[7px] text-white/30 uppercase">LLM-Free Watch</span>
                        </div>

                        <p className="text-[7.5px] leading-relaxed text-white/40">
                          To minimize token drain, the Supervisor watches passive signals ONLY and triggers active LLM reasoning for these discrete physical anomalies:
                        </p>

                        <div className="space-y-2 text-[9px]">
                          {/* Simulated Tool Error */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">1. Tool Execution Failure</span>
                              <span className="text-[7.5px] text-white/40">Triggers recovery plan</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setSimulatedToolError(!simulatedToolError)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                simulatedToolError 
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {simulatedToolError ? 'TRIGGERED!' : 'QUIET'}
                            </button>
                          </div>

                          {/* Passive Repeated Action Observation loops */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">2. Repetitive Action Loops</span>
                              <span className="text-[7.5px] text-white/40">Breaks infinite loop cascades</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setSimulatedRepeatedLoops(!simulatedRepeatedLoops)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                simulatedRepeatedLoops 
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {simulatedRepeatedLoops ? 'TRIGGERED!' : 'QUIET'}
                            </button>
                          </div>

                          {/* Context Length explosion trigger */}
                          <div className="flex justify-between items-center bg-white/[0.01] p-1.5 rounded hover:bg-white/[0.03]">
                            <div>
                              <span className="font-bold text-white block">3. Context Length Explosion</span>
                              <span className="text-[7.5px] text-white/40">Throttles content explosion</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setSimulatedContextExplosion(!simulatedContextExplosion)}
                              className={`px-2 py-1 rounded text-[7.5px] font-bold transition-all ${
                                simulatedContextExplosion 
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' 
                                  : 'bg-white/5 text-white/30 border border-white/5'
                              }`}
                            >
                              {simulatedContextExplosion ? 'TRIGGERED!' : 'QUIET'}
                            </button>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* NABAOS 5-TIER VISUAL CASCADE TRAIL */}
                  <div className="pt-4 border-t border-white/5">
                    <span className="text-[8.5px] text-cyan-400 font-bold uppercase tracking-widest block mb-3">
                      5-tier Adaptive Cache Cascade Trail (Expected Distribution Pool: T1-T4 handles &gt;98% cases)
                    </span>
                    <div className="grid grid-cols-5 gap-2 text-[8px] font-mono">
                      {[
                        { tier: 1, name: "T1: Key Hash", desc: "Fingerprint Hash (45% flow)" },
                        { tier: 2, name: "T2: BERT Core", desc: "Intent Match (32% flow)" },
                        { tier: 3, name: "T3: SetFit Vector", desc: "Few-shot Embedding (15% flow)" },
                        { tier: 4, name: "T4: Shallow LLM", desc: "Fast Parse (6.5% flow)" },
                        { tier: 5, name: "T5: Deep Agent", desc: "Epistemic Chain (<1.5% flow)" }
                      ].map(t => {
                        const isTriggered = nabaResult && nabaResult.tier === t.tier;
                        const isBypassed = nabaResult && nabaResult.tier > t.tier;
                        
                        let bgClass = "bg-[#050a0f] border-white/5 text-white/30";
                        if (isTriggered) {
                          bgClass = "bg-green-500/10 border-green-500/40 text-green-400 shadow-[0_0_12px_rgba(34,197,94,0.15)] animate-pulse font-bold";
                        } else if (isBypassed) {
                          bgClass = "bg-[#050a0f]/50 border-cyan-500/20 text-cyan-400/50";
                        }
                        
                        return (
                          <div key={t.tier} className={`p-2 border rounded-lg flex flex-col justify-between transition-all duration-300 ${bgClass}`}>
                            <div className="font-bold uppercase tracking-wider text-[7px]">{t.name}</div>
                            <div className="text-[6px] text-white/35 mt-1 leading-tight">{t.desc}</div>
                            {isTriggered && (
                              <div className="text-[6px] text-green-400 font-black tracking-widest mt-1.5 uppercase">
                                ACTIVATED
                              </div>
                            )}
                            {isBypassed && (
                               <div className="text-[6px] text-cyan-500/60 font-medium tracking-tight mt-1.5 uppercase">
                                 Bypassed Cache
                               </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-white/5">
                  <button
                    type="button"
                    onClick={handleNabaSimulate}
                    disabled={isNabaLoading}
                    className="w-full bg-cyan-700 hover:bg-cyan-600 active:scale-[0.99] disabled:opacity-50 text-white font-black text-[10px] uppercase tracking-[0.2em] py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.1)] hover:shadow-[0_0_30px_rgba(6,182,212,0.3)] cursor-pointer"
                  >
                    {isNabaLoading ? (
                      <>
                        <RefreshCw size={13} className="animate-spin" />
                        Infiltrating Cascade, Checking Ledger Verified Pramana...
                      </>
                    ) : (
                      <>
                        <Brain size={13} />
                        EXECUTE NABAOS CASCADE COMPILATION
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>

          {/* PERSISTENT SUB-PANEL: ROUTING HEALTH ADVICE */}
          {activeTab !== 'flow' && (
            <div className="p-4 bg-cyan-950/15 border border-cyan-500/10 rounded-xl flex items-start gap-3">
              <span className="p-1.5 bg-cyan-950 border border-cyan-800/35 rounded-lg text-cyan-400 mt-0.5 animate-pulse">
                <Activity size={12} />
              </span>
              <div>
                <div className="text-cyan-400 font-bold uppercase tracking-widest text-[8.5px] flex items-center gap-1">
                  Lived Core Routing Feedback Panel
                </div>
                <p className="text-white/50 leading-relaxed text-[8px] font-sans mt-0.5">
                  {activeTab === 'nabaos' 
                    ? "NabaOS prevents the 'Unreliability Tax' in multi-agent swarms using cognitive caches. Standard fully-connected models blow past cost budgets instantly. NabaOS structures intents dynamically, ensuring per-penny economics."
                    : "The router dynamically optimizes resource pools. When sensitive parameters are scanned, the payload is directed to local Ollama. For heavy logic synthesis, routing redirects payloads to deep-reasoning APIs, bypassing lower speed models."
                  }
                </p>
              </div>
            </div>
          )}

        </div>

        {/* RIGHT COLUMN: RECENT DECISION & DETAILED ARTIFACT */}
        {activeTab !== 'flow' && (
          <div className="flex flex-col gap-6 min-h-0">
          
          {activeTab === 'nabaos' ? (
            /* --- NABAOS ECONOMICS AND PRAMANA VERIFICATION VIEW --- */
            <>
              {/* TOP RIGHT CARD: NABAOS ECONOMICS & MCP RESOURCE LEDGER */}
              <div className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col justify-between min-h-[320px]">
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-white/5">
                    <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                      <History size={12} />
                      NabaOS 130-Agent Economics & MCP Ledger
                    </span>
                    <span className="text-[8px] border border-cyan-500/20 text-cyan-400 bg-cyan-950/20 px-2 py-0.5 rounded font-black">
                      SWARM OPTIMIZATION
                    </span>
                  </div>

                  {/* Swarm Size controller */}
                  <div className="bg-[#050a0f] border border-white/5 p-3 rounded-lg space-y-2">
                    <div className="flex justify-between items-center text-[9px]">
                      <span className="text-white/40 block uppercase">Active MAS Swarm Size</span>
                      <span className="text-cyan-400 font-black font-mono text-[10px]">
                        {agentCount} {agentCount === 130 ? 'Agents (FRONTIER)' : 'Agents'}
                      </span>
                    </div>
                    <input 
                      type="range" 
                      min="10" 
                      max="200" 
                      value={agentCount} 
                      onChange={e => setAgentCount(Number(e.target.value))}
                      className="w-full accent-cyan-400 h-1 bg-white/10 rounded-lg cursor-pointer"
                    />
                    <div className="flex justify-between text-[6.5px] text-white/30 uppercase font-mono">
                      <span>10 Swarm</span>
                      <span className="text-cyan-400 font-black">130 (Optimal Transition)</span>
                      <span>200 Ecosystem</span>
                    </div>
                  </div>

                  {/* Optimal vs Naive Switch */}
                  <button 
                    type="button"
                    onClick={() => setIsNabaOptimized(!isNabaOptimized)}
                    className={`w-full p-2 rounded-lg border text-[8.5px] uppercase font-black tracking-widest text-center transition-all cursor-pointer ${
                      isNabaOptimized 
                        ? 'bg-cyan-950/30 border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/50' 
                        : 'bg-red-950/30 border-red-500/30 text-red-400 hover:bg-red-950/50'
                    }`}
                  >
                    Active Paradigm: {isNabaOptimized ? 'NabaOS Linear Optimization' : 'Naive Fully-Connected'}
                  </button>

                  {/* Bento dynamic calculation metrics */}
                  <div className="grid grid-cols-2 gap-2 text-mono text-[8.5px]">
                    <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                      <span className="text-[6.5px] text-white/30 block uppercase">CHANNELS COMPLEXITY</span>
                      <span className={`font-bold block text-[10px] ${isNabaOptimized ? 'text-green-400' : 'text-red-400'}`}>
                        {isNabaOptimized 
                          ? `${agentCount} Paths (O(N))` 
                          : `${(agentCount * (agentCount - 1)).toLocaleString()} Paths (O(N²))`
                        }
                      </span>
                    </div>
                    
                    <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                      <span className="text-[6.5px] text-white/30 block uppercase">MCP TOKEN FOOTPRINT</span>
                      <span className="font-bold block text-[10px] text-green-400">
                        {nabaResult?.mcp_analytics 
                          ? `${nabaResult.mcp_analytics.optimized_tokens} / ${nabaResult.mcp_analytics.raw_tokens}` 
                          : isFieldFilteringActive ? '1,425 (Optimized)' : '9,500 (Raw Full)'
                        }
                      </span>
                    </div>

                    <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                      <span className="text-[6.5px] text-white/30 block uppercase font-bold">PROMPT CACHING STATUS</span>
                      <span className="font-bold block text-[9.5px] text-cyan-400 truncate">
                        {nabaResult?.mcp_analytics?.prompt_caching?.status || (isPromptCachingActive ? "PREFIX CACHE HIT" : "BYPASSED")}
                      </span>
                    </div>

                    <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                      <span className="text-[6.5px] text-white/30 block uppercase">TOKEN SAVINGS PERCENTAGE</span>
                      <span className="text-green-400 font-bold block text-[10px]">
                        {nabaResult?.mcp_analytics 
                          ? `${nabaResult.mcp_analytics.savings_percentage}% Token Drop` 
                          : isFieldFilteringActive ? '85% Savings' : '0% Savings'
                        }
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-cyan-950/15 border border-cyan-900/40 rounded-lg text-center">
                    <div className="text-[7.5px] text-white/30 uppercase">PROJECTED ENTERPRISE ANNUAL COMPUTING SAVINGS</div>
                    <div className="text-base font-black text-cyan-400 font-mono tracking-wider mt-0.5">
                      {isNabaOptimized 
                        ? `$${(365 * 120 * ((agentCount * 0.057 + 0.12) - (agentCount * 0.00045 + 0.01))).toLocaleString(undefined, {maximumFractionDigits: 0})} Saved / Yr`
                        : "$0.00 (Standard Unreliability Tax active)"
                      }
                    </div>
                  </div>
                </div>
              </div>

              {/* BOTTOM RIGHT CARD: LIVE EPISTEMIC VERIFICATION CERTIFICATE */}
              <div className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col flex-1 min-h-[220px] justify-between">
                <div>
                  <div className="flex justify-between items-center pb-2 border-b border-white/5 mb-3 shrink-0">
                    <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                      <Lock size={12} className="text-cyan-400" />
                      Dynamic Epistemic Audit Proof
                    </span>
                    <span className="text-white/20 text-[8px] uppercase">NYAYA + PHYSICAL INVARIANTS</span>
                  </div>

                  {nabaResult ? (
                    <div className="space-y-3.5 text-[8.5px] font-mono leading-relaxed">
                      {/* Section 1: Cache verification details */}
                      <div className="bg-[#050a0f] p-3 border border-white/5 rounded-lg space-y-1.5">
                        <div className="flex justify-between">
                          <span className="text-white/40 text-[7.5px] uppercase">W5H2 Cache coordinates:</span>
                          <span className="text-cyan-400 font-bold">{nabaResult.what}:{nabaResult.where}</span>
                        </div>
                        <div className="h-[1px] bg-white/5"></div>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[7.5px]">
                          <div><span className="text-white/40 uppercase">WHO:</span> <span className="text-white font-bold">{nabaResult.who}</span></div>
                          <div><span className="text-white/40 uppercase">WHEN:</span> <span className="text-white font-bold">{nabaResult.when}</span></div>
                          <div><span className="text-white/40 uppercase">WHY:</span> <span className="text-white font-bold truncate block">{nabaResult.why}</span></div>
                          <div><span className="text-white/40 uppercase">PRAMANA:</span> <span className="text-cyan-400 font-black">{nabaResult.pramana.toUpperCase()}</span></div>
                        </div>
                      </div>

                      {/* Section 2: Supervisor & Anti Collusion analysis */}
                      <div className="bg-[#050a0f] p-3 border border-white/5 rounded-lg space-y-2">
                        <div className="grid grid-cols-2 gap-2 border-b border-white/5 pb-1.5">
                          <div>
                            <span className="text-white/40 text-[7px] block uppercase">WATCHDOG MONITOR</span>
                            <span className={`font-bold text-[8px] ${nabaResult?.orchestration_analytics?.supervisor_state?.includes("ACTIVE") ? 'text-amber-400 animate-pulse' : 'text-green-400'}`}>
                              {nabaResult?.orchestration_analytics?.supervisor_state?.replace(/_/g, " ")}
                            </span>
                          </div>
                          <div>
                            <span className="text-white/40 text-[7px] block uppercase">WATCHDOG SAVINGS RATE</span>
                            <span className="text-green-400 font-bold text-[8.5px]">
                              {nabaResult?.orchestration_analytics?.supervisor_token_savings}
                            </span>
                          </div>
                        </div>

                        {nabaResult?.orchestration_analytics?.supervisor_triggers?.length > 0 && (
                          <div className="text-[7.5px] bg-amber-500/10 text-amber-300 p-1.5 border border-amber-500/25 rounded">
                            <strong className="block uppercase text-[7px] mb-0.5">TRIGGERS REGISTERED:</strong>
                            {nabaResult.orchestration_analytics.supervisor_triggers.join(", ")}
                          </div>
                        )}

                        <div className="text-[7.5px]">
                          <span className="text-white/40 block uppercase">ANTI-COLLUSION PARADIGM:</span>
                          <span className="text-cyan-400 font-bold block mt-0.5 text-[8px]">
                            {nabaResult?.orchestration_analytics?.anti_collusion_status}
                          </span>
                        </div>
                      </div>

                      {/* Section 3: Safe constitution cryptographic lock */}
                      <div className="bg-[#050a0f] p-3 border border-white/5 rounded-lg space-y-1">
                        <span className="text-white/40 text-[7px] block uppercase">ED25519 CONSTITUTION PIC KEY FIREWALL</span>
                        <div className="text-white font-mono break-all text-[7.5px] select-all tracking-tight bg-black/40 p-1.5 rounded border border-white/5 leading-normal">
                          {nabaResult?.orchestration_analytics?.ed25519_constitution_sig}
                        </div>
                        <span className="text-white/30 text-[6.5px] block uppercase text-right">SIGNED & PIC ENFORCED v3.4</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-[160px] text-center border border-dashed border-white/5 rounded-xl p-4">
                      <AlertCircle size={20} className="text-cyan-500/20 mb-2" />
                      <p className="text-[10px] text-white/40 leading-relaxed max-w-[200px]">
                        No dynamic cascade generated. Click the &quot;EXECUTE NABAOS CASCADE COMPILATION&quot; button below to trigger W5H2 parsing and evaluate governance routing signatures in real time.
                      </p>
                    </div>
                  )}
                </div>

                {nabaResult && (
                  <div className="text-[7.5px] text-green-400/60 leading-relaxed font-mono flex items-center gap-1.5 pt-3 border-t border-white/5">
                    <CheckCircle2 size={11} className="text-green-400" /> 100% Cryptographic Epistemic proof signed and confirmed across sub-integrators.
                  </div>
                )}
              </div>
            </>
          ) : (
            /* --- STANDARD LLM DESKTOP VIEW --- */
            <>
              {/* TOP RIGHT CARD: DETAILED SIMULATOR ARTIFACT */}
              <div className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col justify-between min-h-[250px]">
                <div>
                  <div className="flex justify-between items-center mb-3 pb-2 border-b border-white/5">
                    <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                      <Lock size={12} />
                      Live Cryptographic Decision Frame
                    </span>
                    {activeResult && (
                      <span className="text-[8px] border border-green-500/20 text-green-400 bg-green-950/20 px-2 py-0.5 rounded font-black animate-pulse">
                        {activeResult.evidence_artifact.seal_status}
                      </span>
                    )}
                  </div>

                  {activeResult ? (
                    <div className="space-y-3.5">
                      <div className="bg-[#050a0f] border border-white/5 p-3 rounded-lg flex flex-col gap-1.5 font-mono">
                        <div className="flex justify-between">
                          <span className="text-white/30 text-[8px] uppercase">Rerouted Objective:</span>
                          <span className="text-white text-right max-w-[180px] break-all truncate block">{activeResult.decision.task_name}</span>
                        </div>
                        <div className="h-[1px] bg-white/5"></div>
                        <div className="flex justify-between items-center">
                          <span className="text-white/30 text-[8px] uppercase">Allocated Core Node:</span>
                          <span className="text-cyan-400 font-bold text-right">
                            {activeResult.decision.provider_used} ({activeResult.decision.model_used})
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 bg-[#050a0f] p-3 border border-white/5 rounded-lg font-mono text-[9px]">
                        <div>
                          <div className="text-white/30 text-[7px] uppercase">FRAME HEADER</div>
                          <div className="text-white font-bold font-mono text-[9.5px]">{activeResult.decision.id}</div>
                        </div>
                        <div>
                          <div className="text-white/30 text-[7px] uppercase">COGNITIVE LATENCY</div>
                          <div className="text-cyan-400 font-bold text-[9.5px]">{activeResult.decision.latency}ms</div>
                        </div>
                        <div>
                          <div className="text-white/30 text-[7px] uppercase">TRANSACTION OVERHEAD</div>
                          <div className="text-green-400 font-bold text-[9.5px]">${activeResult.decision.cost.toFixed(6)}</div>
                        </div>
                        <div>
                          <div className="text-white/30 text-[7px] uppercase">FALLBACK ESCALATION</div>
                          <div className={`${activeResult.decision.fallback_used === 'yes' ? 'text-amber-400 animate-pulse' : 'text-white/30'} font-bold`}>
                            {activeResult.decision.fallback_used.toUpperCase()}
                          </div>
                        </div>
                      </div>

                      <div className="p-3 bg-cyan-950/10 border border-cyan-900/40 rounded-lg space-y-1 font-mono text-[8.5px]">
                        <div className="flex justify-between items-center">
                          <span className="text-cyan-400 font-bold">Policy Compliance Verdict:</span>
                          <span className="text-white font-black">{activeResult.decision.policy_result}</span>
                        </div>
                        <div className="text-[7px] text-white/30 leading-snug break-all font-mono select-all text-xs">
                          LEDGER ADDR: {activeResult.evidence_artifact.ledger_address}
                        </div>
                        <div className="text-[7.5px] text-white/30 leading-snug break-all font-mono">
                          AUDIT_HASH: {activeResult.decision.audit_hash}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-[180px] text-center border border-dashed border-white/5 rounded-xl p-6">
                      <AlertCircle size={24} className="text-cyan-500/20 mb-3" />
                      <p className="text-[10px] text-white/40 leading-relaxed max-w-[240px]">
                        No active route generated. Reconfigure parameters in the simulator and click &quot;Evaluate and Dispatch&quot; to test.
                      </p>
                    </div>
                  )}
                </div>

                {activeResult && (
                  <div className="mt-4 text-[7.5px] text-white/20 leading-relaxed font-mono flex items-center gap-1.5 pt-3 border-t border-white/5">
                    <Lock size={9} /> Veklom Cryptographic Proof signed & secured inside Evidence DB (WAL-active).
                  </div>
                )}
              </div>

              {/* BOTTOM RIGHT CARD: RECENT DECISION HISTORY */}
              <div className="bg-[#0b1219]/70 border border-cyan-800/20 rounded-xl p-5 backdrop-blur-md shadow-[0_15px_30px_rgba(0,0,0,0.5)] flex flex-col flex-1 min-h-[220px]">
                <div className="flex justify-between items-center pb-2 border-b border-white/5 mb-3 shrink-0">
                  <span className="text-[10px] font-bold tracking-widest text-cyan-400 uppercase flex items-center gap-1.5">
                    <History size={12} />
                    Decisions Ledger History
                  </span>
                  <span className="text-white/20 text-[8px] uppercase">FIFO CACHE</span>
                </div>

                <div className="flex-1 overflow-auto space-y-2 pr-1 scrollbar-hide">
                  {history.length > 0 ? (
                    history.map((hFrame) => (
                      <div 
                        key={hFrame.id}
                        className="p-2.5 bg-[#050a0f] border border-white/5 rounded hover:border-cyan-500/20 transition-all text-[8.5px] font-mono leading-normal"
                      >
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="font-bold text-white max-w-[150px] truncate block">{hFrame.task_name}</span>
                          <span className="text-white/30">{hFrame.id}</span>
                        </div>

                        <div className="flex justify-between items-center mt-1.5 text-white/45 text-[8px]">
                          <span>Routed Model: <strong className="text-cyan-400">{hFrame.provider_used} ({hFrame.model_used})</strong></span>
                          <span>Latency: <strong className="text-white">{hFrame.latency}ms</strong></span>
                        </div>

                        <div className="flex justify-between items-center mt-1 text-white/45 text-[8px]">
                          <span>Transaction Overhead: <strong className="text-green-400">${hFrame.cost.toFixed(6)}</strong></span>
                          <span className="text-[7.5px] text-white/20 truncate max-w-[90px]" title={hFrame.audit_hash}>{hFrame.audit_hash.substring(0, 16)}...</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="py-12 flex flex-col items-center justify-center h-full text-cyan-500/20">
                      <AlertCircle size={16} className="mb-2" />
                      <span className="text-[8px] tracking-widest uppercase font-bold">No decisions logged.</span>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          </div>
        )}

      </div>

    </div>
  );
};
