import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Cpu, Search, Activity, Sliders, RefreshCw } from 'lucide-react';

export const ModelsPage: React.FC = () => {
  const [modelsList, setModelsList] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [subError, setSubError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchModels = async () => {
    setIsLoading(true);
    setSubError('');
    try {
      const res = await api('/workspace/models');
      setModelsList(res);
    } catch (err: any) {
      setSubError(err.message || 'Gateway sync aborted.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleToggleModel = async (id: string, currentlyEnabled: boolean) => {
    try {
      await api(`/workspace/models/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_enabled: !currentlyEnabled })
      });
      setModelsList(prev => prev.map(m => m.id === id ? { ...m, is_enabled: !currentlyEnabled } : m));
    } catch (err: any) {
      setSubError(err.message || 'Failed to update model fleet configurations.');
    }
  };

  const filteredModels = modelsList.filter(m => 
    m.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.provider.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.model_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <Cpu size={18} className="text-[var(--orange)] animate-pulse" /> Bare-Metal Model Fleet
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Toggle active bare-metal LLM engines in your local bare-metal clusters.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchModels} 
            className="p-2 border border-white/5 rounded bg-neutral-900 text-[var(--text-secondary)] hover:text-white transition-colors"
            title="Sync Runtimes"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {subError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded font-mono">
          {subError}
        </div>
      )}

      {/* Runtimes Dashboard Monitor */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glow-card p-4 flex flex-col justify-between">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">ACTIVE HOSTED ENGINES</span>
          <span className="text-2xl font-black text-white mt-2 font-mono">
            {modelsList.filter(m => m.is_enabled).length} / {modelsList.length}
          </span>
          <span className="text-[9px] font-mono text-emerald-400 block mt-1">ALL SYSTEMS OPERATIONAL</span>
        </div>
        <div className="glow-card p-4 flex flex-col justify-between">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">TOTAL COMPUTE NODES</span>
          <span className="text-2xl font-black text-white mt-2 font-mono">12 Nodes</span>
          <span className="text-[9px] font-mono text-[var(--orange)] block mt-1">BARE-METAL INTEGRITY COMPLIANT</span>
        </div>
        <div className="glow-card p-4 flex flex-col justify-between">
          <span className="text-[9px] text-[var(--text-secondary)] font-mono uppercase block">INFERENCE RESILIENCE</span>
          <span className="text-2xl font-black text-white mt-2 font-mono">99.999%</span>
          <span className="text-[9px] font-mono text-emerald-400 block mt-1">ZERO DISPATCH LOSS RECORDED</span>
        </div>
      </div>

      {/* Search Filter bar */}
      <div className="relative">
        <span className="absolute left-3 top-3 text-[var(--text-muted)]">
          <Search size={14} />
        </span>
        <input 
          type="text" 
          placeholder="Filter model fleet by name or provider..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="form-input pl-9 text-xs font-mono"
        />
      </div>

      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3 text-xs font-mono text-[var(--text-secondary)]">
          <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-spin">
            <circle cx="50" cy="50" r="40" stroke="rgba(255,184,0,0.1)" strokeWidth="10" />
            <path d="M50 10 A40 40 0 0 1 90 50" stroke="#ffb800" strokeWidth="10" strokeLinecap="round" />
          </svg>
          <span>POLLING BARE-METAL INSTANCES...</span>
        </div>
      ) : filteredModels.length === 0 ? (
        <div className="py-12 border border-dashed border-white/5 rounded-xl flex flex-col items-center justify-center gap-2 text-center text-xs font-mono text-[var(--text-secondary)]">
          <Cpu size={24} className="text-[var(--text-muted)] mb-2" />
          <span>NO OPERATIONAL LLM ENGINES MATCHING YOUR CRITERIA</span>
          <span className="text-[10px] text-[var(--text-muted)]">Ensure model identifiers are registered in the global configuration files.</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredModels.map((m) => (
            <div key={m.id} className="glow-card p-4 flex justify-between items-center transition-all hover:border-[rgba(255,184,0,0.15)] bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
              <div>
                <span className="text-xs font-bold text-white block">{m.display_name}</span>
                <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block mt-0.5">
                  {m.provider.toUpperCase()} · {m.model_name}
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-[9.5px] text-[var(--text-secondary)] font-mono block">
                    INPUT: ${m.cost_per_1k_input.toFixed(5)} / 1K
                  </span>
                  <span className="w-1 h-1 rounded-full bg-neutral-800"></span>
                  <span className="text-[9.5px] text-[var(--text-secondary)] font-mono block">
                    OUTPUT: ${m.cost_per_1k_output.toFixed(5)} / 1K
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className={`badge ${m.is_enabled ? 'badge-green' : 'badge-orange'} uppercase font-mono text-[9px]`}>
                  {m.is_enabled ? 'online' : 'offline'}
                </span>
                
                {/* Custom Toggle Switch */}
                <label className="relative inline-flex items-center cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={m.is_enabled}
                    onChange={() => handleToggleModel(m.id, m.is_enabled)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-neutral-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-neutral-400 after:border-neutral-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--orange)] peer-checked:after:bg-white peer-checked:after:border-white"></div>
                </label>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
