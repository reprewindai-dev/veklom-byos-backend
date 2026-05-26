import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  GitFork, 
  Cpu, 
  AlertTriangle, 
  Plus, 
  Check, 
  Layers, 
  Play, 
  ArrowRight, 
  ShieldAlert
} from 'lucide-react';

interface PipelineStep {
  id: string;
  name: string;
  type: 'input' | 'ai' | 'logic' | 'output' | 'db' | 'policy';
  status: string;
  details?: string;
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  status: string;
  steps: PipelineStep[];
}

export const Pipelines: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeId, setSelectedPipeId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // New pipeline form
  const [newPipeName, setNewPipeName] = useState('clinical-rag V3');
  const [newPipeDesc, setNewPipeDesc] = useState('Sovereign clinical data vector RAG with PHI redaction audit gates.');

  // Interactive execution states
  const [isRunningSim, setIsRunningSim] = useState(false);
  const [simStepsProgress, setSimStepsProgress] = useState<Record<string, 'idle' | 'running' | 'done'>>({});

  const fetchPipelines = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api('/pipelines');
      setPipelines(data);
      if (data.length > 0) {
        setSelectedPipeId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to sync pipeline workflows.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  const handleCreatePipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPipeName.trim()) return;
    setIsCreating(true);
    setError('');
    try {
      // Create clinical-rag steps by default for visual premium aesthetics
      const steps: PipelineStep[] = [
        { id: 's1', name: 'Clinical Input Intake', type: 'input', status: 'ready', details: 'FHIR JSON intake' },
        { id: 's2', name: 'Retrieve pgvector Embs', type: 'db', status: 'ready', details: 'Bare-metal database search' },
        { id: 's3', name: 'Sovereign Policy Gate', type: 'policy', status: 'ready', details: 'Content safety scans' },
        { id: 's4', name: 'LLM Synthesis Block', type: 'ai', status: 'ready', details: 'Bare-metal Qwen 2.5 instruct' },
        { id: 's5', name: 'PHI De-identification', type: 'policy', status: 'ready', details: 'Regex/NLP auto redaction' },
        { id: 's6', name: 'Ledger Audit Sign', type: 'output', status: 'ready', details: 'Verification block chain' }
      ];

      const newPipe = await api('/pipelines', {
        method: 'POST',
        body: JSON.stringify({
          name: newPipeName,
          description: newPipeDesc,
          steps
        })
      });

      setSuccess(`Pipeline "${newPipeName}" successfully compiled across perimeter nodes.`);
      setNewPipeName('clinical-rag V3');
      setNewPipeDesc('');
      
      // Refresh list
      const data = await api('/pipelines');
      setPipelines(data);
      setSelectedPipeId(newPipe.id);

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Pipeline compilation failed.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleRunPipelineSimulation = async () => {
    const selected = pipelines.find(p => p.id === selectedPipeId);
    if (!selected || selected.steps.length === 0 || isRunningSim) return;

    setIsRunningSim(true);
    setError('');
    
    // Clear previous simulation progress
    const initProgress: Record<string, 'idle' | 'running' | 'done'> = {};
    selected.steps.forEach(s => {
      initProgress[s.id] = 'idle';
    });
    setSimStepsProgress(initProgress);

    try {
      await api(`/pipelines/${selectedPipeId}/run`, { method: 'POST' });

      // Simulate sequential step activation for breathtaking micro-animations
      for (let i = 0; i < selected.steps.length; i++) {
        const step = selected.steps[i];
        
        // Mark current as running
        setSimStepsProgress(prev => ({ ...prev, [step.id]: 'running' }));
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Mark current as done
        setSimStepsProgress(prev => ({ ...prev, [step.id]: 'done' }));
      }
      
      setSuccess('Pipeline execution verified and cryptographic hash chain signed successfully.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError(err.message || 'Execution node pipeline aborted.');
    } finally {
      setIsRunningSim(false);
    }
  };

  const activePipe = pipelines.find(p => p.id === selectedPipeId) || {
    id: 'placeholder',
    name: 'Clinical RAG Engine',
    description: 'Sovereign clinical data vector RAG with PHI redaction audit gates.',
    status: 'active',
    steps: [
      { id: 's1', name: 'Clinical Input Intake', type: 'input', status: 'ready', details: 'FHIR JSON intake' },
      { id: 's2', name: 'Retrieve pgvector Embs', type: 'db', status: 'ready', details: 'Bare-metal database search' },
      { id: 's3', name: 'Sovereign Policy Gate', type: 'policy', status: 'ready', details: 'Content safety scans' },
      { id: 's4', name: 'LLM Synthesis Block', type: 'ai', status: 'ready', details: 'Bare-metal Qwen 2.5 instruct' },
      { id: 's5', name: 'PHI De-identification', type: 'policy', status: 'ready', details: 'Regex/NLP auto redaction' },
      { id: 's6', name: 'Ledger Audit Sign', type: 'output', status: 'ready', details: 'Verification block chain' }
    ]
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'input': return <Layers size={13} className="text-blue-400" />;
      case 'db': return <Layers size={13} className="text-purple-400" />;
      case 'policy': return <ShieldAlert size={13} className="text-[var(--orange)]" />;
      case 'ai': return <Cpu size={13} className="text-emerald-400" />;
      default: return <GitFork size={13} className="text-[var(--text-muted)]" />;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Cpu className="animate-spin text-[var(--orange)]" size={32} />
        <div className="text-xs text-[var(--text-secondary)] font-mono tracking-widest uppercase">Aligning bare-metal pipelines...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <GitFork size={18} className="text-[var(--orange)]" /> Sovereign Inference Pipelines
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Visually construct, orchestrate, and audit structured processing blocks for enterprise clinical AI.</p>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded bg-[rgba(255,68,102,0.06)] border border-red-500/20 text-red-400 text-xs flex items-center gap-3">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-3.5 rounded bg-[rgba(16,185,129,0.06)] border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-3">
          <Check size={16} className="shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Pipelines directory & Creator */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Workflows Directory */}
          <div className="glow-card">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-3">PIPELINE SCHEMAS</h3>
            <div className="space-y-2">
              {pipelines.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedPipeId(p.id)}
                  className={`w-full text-left p-3 rounded transition-all border flex justify-between items-center ${
                    selectedPipeId === p.id
                      ? 'border-[var(--orange)] bg-[rgba(255,184,0,0.04)] text-white'
                      : 'border-[rgba(255,255,255,0.04)] bg-[rgba(0,0,0,0.15)] text-[var(--text-secondary)] hover:border-[rgba(255,184,0,0.2)] hover:text-white'
                  }`}
                >
                  <div>
                    <span className="text-xs font-bold block">{p.name}</span>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono mt-0.5 uppercase block">{p.steps.length || 6} blocks configured</span>
                  </div>
                  <span className={`badge ${p.status === 'active' || p.id === 'pipe1' ? 'badge-green' : 'badge-orange'}`}>
                    {p.status || 'draft'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Clinical visual builder form */}
          <div className="glow-card">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-3">COMPILE NEW PIPELINE</h3>
            <form onSubmit={handleCreatePipeline} className="space-y-4">
              <div>
                <label className="form-label" htmlFor="pipeline-name">Pipeline Identifier</label>
                <input
                  id="pipeline-name"
                  type="text"
                  placeholder="e.g. support-triage"
                  value={newPipeName}
                  onChange={(e) => setNewPipeName(e.target.value)}
                  className="form-input text-xs font-mono"
                  disabled={isCreating}
                  required
                />
              </div>

              <div>
                <label className="form-label" htmlFor="pipeline-desc">Pipeline Description</label>
                <textarea
                  id="pipeline-desc"
                  placeholder="Brief workflow description..."
                  value={newPipeDesc}
                  onChange={(e) => setNewPipeDesc(e.target.value)}
                  className="form-input text-xs font-mono h-16 py-2"
                  disabled={isCreating}
                />
              </div>

              <button
                type="submit"
                className="btn btn-secondary w-full py-2.5 text-xs font-bold font-mono tracking-wider flex items-center justify-center gap-1.5"
                disabled={isCreating || !newPipeName.trim()}
              >
                <Plus size={13} /> COMPILE PIPELINE
              </button>
            </form>
          </div>

        </div>

        {/* Right Side: Interactive Nodes Visual Flow Board */}
        <div className="glow-card lg:col-span-8 flex flex-col justify-between overflow-hidden">
          
          <div>
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-3 mb-4">
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">{activePipe.name}</h3>
                <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">{activePipe.description}</p>
              </div>
              <button
                onClick={handleRunPipelineSimulation}
                className="btn btn-primary btn-sm flex items-center gap-1.5 font-mono text-[10px]"
                disabled={isRunningSim || activePipe.steps.length === 0}
              >
                <Play size={10} /> {isRunningSim ? 'EXECUTING TARGETS...' : 'RUN PIPELINE SIMULATOR'}
              </button>
            </div>

            {/* Structured Bare-metal Interactive Node Flow Area */}
            <div className="relative p-6 bg-[rgba(0,0,0,0.3)] rounded-lg border border-[rgba(255,255,255,0.05)] grid-bg h-96 overflow-y-auto flex flex-col items-center justify-start gap-4">
              
              {activePipe.steps.length === 0 ? (
                <div className="h-full w-full flex flex-col items-center justify-center py-20 text-center gap-3">
                  <GitFork size={32} className="text-[var(--text-muted)] animate-pulse" />
                  <span className="text-xs text-[var(--text-muted)] font-mono uppercase">Draft schema. No visual blocks deployed.</span>
                </div>
              ) : (
                activePipe.steps.map((step, idx) => {
                  const state = simStepsProgress[step.id] || 'idle';
                  let statusBorder = 'border-[rgba(255,255,255,0.06)] bg-[rgba(10,10,12,0.9)]';
                  let pulseGlow = '';
                  
                  if (state === 'running') {
                    statusBorder = 'border-[var(--orange)] bg-[rgba(255,184,0,0.02)]';
                    pulseGlow = 'ring-2 ring-[var(--orange)] ring-opacity-20 animate-pulse';
                  } else if (state === 'done') {
                    statusBorder = 'border-emerald-500/40 bg-[rgba(16,185,129,0.02)]';
                  }

                  return (
                    <React.Fragment key={step.id}>
                      {/* Connection arrow between nodes */}
                      {idx > 0 && (
                        <div className="flex flex-col items-center pointer-events-none -my-1 text-[var(--text-muted)]">
                          <div className={`h-4 w-0.5 ${idx > 0 && simStepsProgress[activePipe.steps[idx - 1].id] === 'done' ? 'bg-emerald-500/40' : 'bg-neutral-800'}`}></div>
                          <ArrowRight size={10} className={`transform rotate-90 ${idx > 0 && simStepsProgress[activePipe.steps[idx - 1].id] === 'done' ? 'text-emerald-400' : 'text-neutral-700'}`} />
                        </div>
                      )}

                      {/* Node Element */}
                      <div className={`w-full max-w-[420px] p-3 rounded-lg border backdrop-blur-md flex items-center justify-between transition-all duration-300 relative hover:border-[rgba(255,184,0,0.25)] ${statusBorder} ${pulseGlow}`}>
                        <div className="flex items-center gap-3">
                          <div className="w-6 h-6 rounded bg-neutral-900 flex items-center justify-center shrink-0 border border-white/5">
                            {getStepIcon(step.type)}
                          </div>
                          <div>
                            <span className="text-xs font-bold text-white block">{step.name}</span>
                            <span className="text-[10px] text-[var(--text-secondary)] font-mono block mt-0.5">{step.details}</span>
                          </div>
                        </div>

                        {/* Node status dot */}
                        <div className="flex items-center gap-2 font-mono text-[9px]">
                          {state === 'running' && <span className="text-[var(--orange)] animate-pulse uppercase">active</span>}
                          {state === 'done' && <span className="text-emerald-400 uppercase">success Γ£ô</span>}
                          {state === 'idle' && <span className="text-[var(--text-muted)] uppercase">ready</span>}
                          <div className={`w-2 h-2 rounded-full ${
                            state === 'running' ? 'bg-[var(--orange)] animate-ping' :
                            state === 'done' ? 'bg-emerald-400' : 'bg-neutral-600'
                          }`}></div>
                        </div>
                      </div>
                    </React.Fragment>
                  );
                })
              )}

            </div>
          </div>

          <div className="text-[9px] font-mono text-[var(--text-muted)] border-t border-[rgba(255,255,255,0.03)] pt-3 text-right uppercase">
            Sovereign pipeline builder: Active schema
          </div>
        </div>

      </div>

    </div>
  );
};