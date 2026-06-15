// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Play, Clipboard, Terminal, Shield, Cpu, Zap, Activity, Calculator, Coins } from 'lucide-react';

interface Tool {
  name: string;
  description: string;
  inputSchema: any;
}

interface HistoryEntry {
  id: string;
  toolName: string;
  args: any;
  result: any;
  timestamp: string;
}

export const ToolExecutor: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [args, setArgs] = useState<string>('{}');
  const [isJsonValid, setIsJsonValid] = useState(true);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Predictive Cost Calculator States & Handler ---
  const [activeTab, setActiveTab] = useState<'primitives' | 'predictor'>('primitives');
  const [predictionText, setPredictionText] = useState('Verify telemetry indexes for high-temperature hydraulic manifold 4B');
  const [predictionProvider, setPredictionProvider] = useState('openai');
  const [predictionResult, setPredictionResult] = useState<any>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);

  const runPrediction = async () => {
    setPredictionLoading(true);
    setPredictionError(null);
    setPredictionResult(null);
    try {
      const res = await fetch('/api/mcp/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'get_cost_prediction',
          arguments: {
            input_text: predictionText,
            provider: predictionProvider,
          },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.details || 'Prediction failed');
      
      if (data.content && data.content[0] && data.content[0].text) {
        const parsedText = JSON.parse(data.content[0].text);
        setPredictionResult(parsedText);
      } else {
        setPredictionResult(data);
      }
    } catch (e: any) {
      setPredictionError(e.message);
    } finally {
      setPredictionLoading(false);
    }
  };

  useEffect(() => {
    fetchTools();
  }, []);

  useEffect(() => {
    try {
      if (args.trim() === '') {
        setIsJsonValid(true);
        setJsonError(null);
        return;
      }
      JSON.parse(args);
      setIsJsonValid(true);
      setJsonError(null);
    } catch (e: any) {
      setIsJsonValid(false);
      setJsonError(e.message);
    }
  }, [args]);

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(args);
      setArgs(JSON.stringify(parsed, null, 2));
    } catch (e: any) {
      setError(`Format failed: ${e.message}`);
    }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      const data = await res.json();
      setTools(data.tools || []);
    } catch (e) {
      console.error('Failed to fetch tools', e);
    }
  };

  const handleRun = async (name: string, inputArgs: any) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/mcp/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, arguments: inputArgs }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.details || 'Execution failed');
      setResult(data);
      
      const newEntry: HistoryEntry = {
        id: Date.now().toString(),
        toolName: name,
        args: inputArgs,
        result: data,
        timestamp: new Date().toLocaleTimeString()
      };
      setHistory(prev => [newEntry, ...prev].slice(0, 5));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const executeSelected = async () => {
    if (!selectedTool) return;
    if (!isJsonValid) {
      setError(`Cannot execute: ${jsonError}`);
      return;
    }
    const parsedArgs = args.trim() === '' ? {} : JSON.parse(args);
    await handleRun(selectedTool.name, parsedArgs);
  };

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-[#0b1219]/40 rounded-2xl border border-cyan-900/30 overflow-auto scrollbar-hide">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyan-900/30 pb-3 mb-2 shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-[0.2em] text-cyan-200 uppercase">MCP Tool Orchestrator</h2>
        </div>
        <div className="flex bg-black/60 p-1 rounded-xl border border-cyan-950">
          <button
            onClick={() => setActiveTab('primitives')}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-mono uppercase tracking-wider transition-all ${
              activeTab === 'primitives'
                ? 'bg-cyan-500/10 border border-cyan-500/25 text-cyan-400/90 font-bold'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'
            }`}
          >
            Primitive Orchestration
          </button>
          <button
            onClick={() => setActiveTab('predictor')}
            className={`px-4 py-1.5 rounded-lg text-[10px] font-mono uppercase tracking-wider transition-all ${
              activeTab === 'predictor'
                ? 'bg-cyan-500/10 border border-cyan-500/25 text-cyan-400/90 font-bold'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'
            }`}
          >
            Predictive Cost Calculator
          </button>
        </div>
      </div>

      {activeTab === 'primitives' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Tool List */}
          <div className="flex flex-col gap-2">
            <div className="text-[10px] uppercase tracking-widest text-cyan-500/50 mb-1">Available Primitives</div>
            <div className="flex flex-col gap-2">
              {tools.map((tool) => (
                <button
                  key={tool.name}
                  onClick={() => setSelectedTool(tool)}
                  className={`flex flex-col p-3 rounded-xl border transition-all text-left ${
                    selectedTool?.name === tool.name
                      ? 'bg-cyan-500/10 border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                      : 'bg-[#0f172a]/40 border-cyan-900/20 hover:border-cyan-500/30'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className={`text-sm font-medium ${selectedTool?.name === tool.name ? 'text-cyan-400' : 'text-slate-300'}`}>
                      {tool.name}
                    </span>
                    {selectedTool?.name === tool.name && <Zap className="w-3 h-3 text-cyan-400 fill-cyan-400" />}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {tool.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Execution Area */}
          <div className="flex flex-col gap-4">
            <AnimatePresence mode="wait">
              {selectedTool ? (
                <motion.div
                  key={selectedTool.name}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="flex flex-col gap-4"
                >
                  <div className="bg-[#0f172a]/60 p-4 rounded-xl border border-cyan-500/20 backdrop-blur-sm">
                    <div className="text-[10px] uppercase tracking-widest text-cyan-400 mb-3 flex items-center gap-2">
                      <Cpu className="w-3 h-3" /> Parameter Synthesis
                    </div>
                    
                    <div className="flex flex-col gap-2 relative">
                      <div className="flex justify-between items-center">
                        <label className="text-[9px] text-slate-500 uppercase tracking-tighter">Arguments (JSON)</label>
                        <button 
                          onClick={handleFormat}
                          className="text-[9px] text-cyan-500 hover:text-cyan-400 font-mono uppercase tracking-tighter"
                        >
                          [ Format ]
                        </button>
                      </div>
                      <textarea
                        value={args}
                        onChange={(e) => setArgs(e.target.value)}
                        className={`w-full h-32 bg-black/40 border rounded-lg p-3 font-mono text-xs outline-none transition-all ${
                          isJsonValid 
                            ? 'border-cyan-900/40 text-cyan-300 focus:border-cyan-500/50' 
                            : 'border-red-500/50 text-red-300 focus:border-red-500'
                        }`}
                        placeholder='{"param": "value"}'
                      />
                      {!isJsonValid && (
                        <div className="text-[8px] text-red-500 font-mono mt-1">
                          Parse Error: {jsonError}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={executeSelected}
                      disabled={loading}
                      className={`mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-bold text-xs tracking-widest uppercase transition-all ${
                        loading
                          ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                          : 'bg-cyan-500 text-black hover:bg-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                      }`}
                    >
                      {loading ? (
                        <Activity className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Play className="w-3 h-3 fill-current" />
                          Execute Primitive
                        </>
                      )}
                    </button>
                  </div>

                  {/* History Section */}
                  {history.length > 0 && (
                    <div className="bg-[#0f172a]/60 p-4 rounded-xl border border-cyan-900/30">
                       <div className="text-[10px] uppercase tracking-widest text-cyan-500 mb-3">Recent Actions</div>
                       <div className="space-y-2">
                          {history.map(entry => (
                            <div key={entry.id} className="flex justify-between items-center bg-black/40 p-2 rounded text-[10px] border border-cyan-900/40">
                               <div>
                                  <span className="font-bold text-cyan-400">{entry.toolName}</span>
                                  <span className="ml-2 text-white/50 font-mono">{entry.timestamp}</span>
                               </div>
                               <button
                                 onClick={() => handleRun(entry.toolName, entry.args)}
                                 className="text-cyan-500 hover:text-white"
                               >
                                  <Zap className="w-3 h-3" />
                               </button>
                            </div>
                          ))}
                       </div>
                    </div>
                  )}

                  {/* Result Display */}
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-black/60 p-4 rounded-xl border border-green-500/20"
                    >
                      <div className="text-[10px] uppercase tracking-widest text-green-400 mb-2 flex items-center gap-2">
                        <Shield className="w-3 h-3" /> Execution Trace
                      </div>
                      <pre className="text-[10px] font-mono text-green-500/80 overflow-auto max-h-48 whitespace-pre-wrap">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    </motion.div>
                  )}

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-red-500/10 p-4 rounded-xl border border-red-500/20"
                    >
                      <div className="text-[10px] uppercase tracking-widest text-red-400 mb-1">Fault Detected</div>
                      <p className="text-[10px] text-red-300 font-mono">{error}</p>
                    </motion.div>
                  )}
                </motion.div>
              ) : (
                <div className="flex items-center justify-center h-64 border border-dashed border-cyan-900/30 rounded-xl bg-cyan-900/5">
                  <div className="text-[10px] text-cyan-900 uppercase tracking-widest text-center">
                    Select a primitive<br />to begin execution
                  </div>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Form Side */}
          <div className="bg-[#0f172a]/40 border border-cyan-900/20 p-5 rounded-2xl flex flex-col gap-4">
            <div className="flex items-center gap-2 border-b border-white/5 pb-2.5">
              <Calculator className="w-4 h-4 text-cyan-400" />
              <span className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold font-mono">Cost Estimation Control Panel</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold font-mono">Target Model Provider</label>
              <select
                value={predictionProvider}
                onChange={e => setPredictionProvider(e.target.value)}
                className="w-full bg-black/50 border border-cyan-900/40 rounded-xl px-3 py-2.5 text-xs text-cyan-400 focus:outline-none focus:border-cyan-500/50 font-mono"
              >
                <option value="openai">OpenAI (SaaS Premium standard)</option>
                <option value="google">Google Gemini (Highly efficient Flash pricing)</option>
                <option value="groq">Groq (Ultra-low latency inference discount)</option>
                <option value="bedrock">AWS Bedrock (Scalable Enterprise agent)</option>
                <option value="ollama">Ollama (Local BYOS node execution - FREE)</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold font-mono">Sample Task Prompt</label>
                <span className="text-[8px] font-mono text-slate-600">{predictionText.length} characters</span>
              </div>
              <textarea
                value={predictionText}
                onChange={e => setPredictionText(e.target.value)}
                rows={5}
                className="w-full bg-black/50 border border-cyan-900/40 rounded-xl p-3 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 leading-relaxed font-mono resize-none"
                placeholder="Enter sample prompt or task instructions here..."
              />
            </div>

            {/* Quick Presets */}
            <div className="space-y-1.5">
              <span className="text-[8.5px] uppercase font-bold tracking-wider text-slate-500 block">Preset Test Cases</span>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: "Brief Query", text: "What is the status of the hydraulic backup pump?" },
                  { label: "Complex Audit", text: "Scan code repository, identify all 14 outdated dependencies and compile custom Dockerfile overrides with multi-stage builds." },
                  { label: "Swarm Analytics", text: "Synthesize telemetry logs for all 130 nodes. Enact deep vector search embeddings using SetFit, detect cluster outliers with 99.5% confidence, and trigger emergency bypass on all failing components." }
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setPredictionText(preset.text)}
                    className="text-[8.5px] bg-[#050a0f] text-cyan-400 hover:text-white border border-cyan-500/10 hover:border-cyan-500/30 px-2.5 py-1 rounded transition-all font-mono"
                  >
                    + {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={runPrediction}
              disabled={predictionLoading}
              className={`mt-2 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-bold text-xs tracking-widest uppercase transition-all ${
                predictionLoading
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-500 text-black hover:bg-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
              }`}
            >
              {predictionLoading ? (
                <Activity className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Coins className="w-4 h-4 text-black" />
                  Predict Transaction Cost
                </>
              )}
            </button>
          </div>

          {/* Results Side */}
          <div className="flex flex-col gap-4 justify-between h-full">
            {predictionResult ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#0b1219]/65 p-5 rounded-2xl border border-green-500/20 backdrop-blur-md flex flex-col justify-between flex-1 gap-4"
              >
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-white/5 mb-4">
                    <span className="text-[10px] font-mono font-bold tracking-widest text-green-400 uppercase flex items-center gap-1.5">
                      <Coins size={12} className="text-green-400 animate-pulse" />
                      Prediction Ledger
                    </span>
                    <span className="text-[8px] bg-green-500/10 text-green-400 px-2 py-0.5 rounded font-black font-mono">
                      CALCULATION COMPLETE
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div className="bg-[#050a0f] p-4 border border-zinc-900 rounded-xl text-center relative overflow-hidden">
                      <span className="text-[7.5px] text-white/40 uppercase tracking-widest block mb-1">PROJECTED COGNITIVE COST</span>
                      <div className="text-2xl font-mono font-black text-green-400 tracking-wider">
                        ${predictionResult.predicted_cost === "0.000000" ? "0.00 (Local Compute)" : predictionResult.predicted_cost}
                        <span className="text-xs text-white/45 ml-1 font-normal font-mono">{predictionResult.currency || "USD"}</span>
                      </div>
                      
                      {predictionResult.provider_rate_per_1k_tokens === 0 && (
                        <div className="text-[7.5px] text-emerald-400 font-bold bg-emerald-500/10 p-1.5 rounded mt-2.5 uppercase">
                          Zero External API Cost Incurred
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-mono text-[9px]">
                      <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                        <span className="text-[6.5px] text-white/35 block uppercase">ESTIMATED TOKENS</span>
                        <span className="font-bold text-white text-[11px] block">{predictionResult.estimated_tokens || "~24"}</span>
                      </div>
                      
                      <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                        <span className="text-[6.5px] text-white/35 block uppercase">PROVIDER BASE RATE</span>
                        <span className="font-bold text-cyan-400 text-[11px] block">
                          ${(predictionResult.provider_rate_per_1k_tokens || 0).toFixed(6)} <span className="text-[7px] text-white/30 uppercase">/1k tokens</span>
                        </span>
                      </div>

                      <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                        <span className="text-[6.5px] text-white/35 block uppercase font-bold">CONFIDENCE SCORE</span>
                        <span className="font-bold text-white text-[11px] block">
                          {(predictionResult.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div className="bg-[#050a0f] p-2.5 border border-white/5 rounded-lg">
                        <span className="text-[6.5px] text-white/35 block uppercase">HEURISTIC ENGINE</span>
                        <span className="text-amber-400 font-bold text-[11px] block">
                          {predictionResult.calculation_method?.replace(/_/g, " ").toUpperCase() || "MCP AGENT RULE"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-3.5 bg-cyan-950/15 border border-cyan-500/10 rounded-xl text-[8px] leading-relaxed text-slate-400 font-mono">
                  *This prediction model is evaluated via the neural-symbolic MCP proxy against active token metrics. Values are precise heuristics designed to optimize billing paths prior to worker dispatch.
                </div>
              </motion.div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 border border-dashed border-cyan-900/30 rounded-2xl bg-cyan-900/5 flex-1 min-h-[220px]">
                <Calculator className="w-8 h-8 text-cyan-500/20 mb-2 animate-bounce" />
                <span className="text-[10px] text-cyan-400 uppercase tracking-wider text-center font-bold font-mono">Inference Matrix Pending</span>
                <p className="text-[9px] text-slate-500 text-center uppercase tracking-normal font-mono mt-1 max-w-[240px] leading-relaxed">
                  Input model details and press &ldquo;Predict Transaction Cost&rdquo; to execute the prediction query under MCP.
                </p>
              </div>
            )}

            {predictionError && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-500/10 p-4 rounded-xl border border-red-500/20"
              >
                <div className="text-[10px] uppercase tracking-widest text-red-400 mb-1">Fault Detected</div>
                <p className="text-[10px] text-red-300 font-mono">{predictionError}</p>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
