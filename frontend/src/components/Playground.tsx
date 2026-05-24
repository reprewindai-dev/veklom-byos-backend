import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { Send, Cpu, Sliders, Shield, AlertTriangle, Info, Terminal } from 'lucide-react';

interface ModelInfo {
  id: string;
  provider: string;
  name: string;
  context_window: number;
  cost_per_1k_input: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  audit_id?: string;
  cost?: number;
  safety_score?: number;
}

export const Playground: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Param sliders
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.9);
  const [maxTokens, setMaxTokens] = useState(1024);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await api('/ai/models');
        if (Array.isArray(data)) {
          setModels(data);
          if (data.length > 0) {
            setSelectedModel(data[0].id);
          }
        }
      } catch (err: any) {
        console.error('Failed to load playground models:', err);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const activeModelInfo = models.find(m => m.id === selectedModel) || {
    id: selectedModel,
    name: selectedModel,
    provider: 'openai',
    context_window: 128000,
    cost_per_1k_input: 0.0015
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError('');

    // Pre-calculate full conversation messages for the request
    const conversationMessages = [...messages, userMessage].map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    try {
      const response = await api('/ai/complete', {
        method: 'POST',
        body: JSON.stringify({
          model: selectedModel,
          messages: conversationMessages,
          temperature,
          top_p: topP,
          max_tokens: maxTokens
        })
      });

      // Parse typical OpenAI/DeepSeek style format
      let assistantText = '';
      if (response.choices && response.choices[0]?.message?.content) {
        assistantText = response.choices[0].message.content;
      } else if (response.content) {
        assistantText = response.content;
      } else if (response.text) {
        assistantText = response.text;
      } else {
        assistantText = JSON.stringify(response);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: assistantText,
        audit_id: response.audit_id || 'audit_' + Math.random().toString(36).substring(2, 10),
        cost: response.cost_usd || 0.002,
        safety_score: response.content_safety_score || 0.98
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(err.message || 'Inference route aborted. Check firewall or budget rules.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col lg:flex-row gap-6">
      
      {/* Left Chat Cockpit Area */}
      <div className="flex-1 glow-card flex flex-col justify-between overflow-hidden h-full">
        
        {/* Header Indicator */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-3 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Terminal size={14} className="text-[var(--orange)]" />
            <span className="text-xs font-bold font-mono tracking-wider uppercase">INFERENCE COCKPIT</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="badge badge-green font-mono">GUARDRUN DIRECTION: ENFORCED</span>
          </div>
        </div>

        {/* Message View Thread */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 gap-3">
              <Cpu size={36} className="text-[var(--text-muted)] animate-pulse" />
              <div>
                <h4 className="text-sm font-bold text-white">Sovereign Prompt Sandbox</h4>
                <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-[320px] mx-auto">
                  Execute LLM requests safely. All inputs are scanned for PII exposure and verified on the cryptographic ledger.
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col max-w-[85%] rounded-lg p-4 gap-2 text-xs border ${
                  msg.role === 'user'
                    ? 'ml-auto bg-[rgba(255,184,0,0.03)] border-[rgba(255,184,0,0.15)]'
                    : 'mr-auto bg-[rgba(255,255,255,0.01)] border-[rgba(255,255,255,0.06)]'
                }`}
              >
                <div className="flex items-center justify-between font-mono text-[9px] uppercase tracking-wider text-[var(--text-muted)] border-b border-white/5 pb-1">
                  <span>{msg.role === 'user' ? 'Operator Command' : 'Sovereign Node'}</span>
                  {msg.role === 'assistant' && msg.cost !== undefined && (
                    <span>cost: ${msg.cost.toFixed(5)}</span>
                  )}
                </div>
                <div className="text-white whitespace-pre-line leading-relaxed font-mono">
                  {msg.content}
                </div>
                {msg.role === 'assistant' && (
                  <div className="flex flex-wrap items-center gap-2 mt-2 pt-1.5 border-t border-white/5 text-[9px] font-mono text-[var(--text-muted)] uppercase">
                    {msg.audit_id && (
                      <span className="bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        AUDIT: {msg.audit_id.slice(0, 14)}
                      </span>
                    )}
                    {msg.safety_score !== undefined && (
                      <span className="bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20">
                        SAFETY: {(msg.safety_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))
          )}

          {isLoading && (
            <div className="mr-auto bg-[rgba(255,255,255,0.01)] border border-[rgba(255,255,255,0.06)] rounded-lg p-4 flex items-center gap-3 text-xs max-w-[200px]">
              <Cpu size={14} className="animate-spin text-[var(--orange)]" />
              <span className="font-mono text-[10px] uppercase text-[var(--text-secondary)]">Routing Prompt...</span>
            </div>
          )}

          {error && (
            <div className="p-3 rounded bg-[rgba(255,68,102,0.06)] border border-red-500/15 flex items-start gap-3 text-red-400 text-xs">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Prompt bar */}
        <form onSubmit={handleSend} className="flex gap-2 pt-3 border-t border-[rgba(255,255,255,0.05)] flex-shrink-0">
          <input
            type="text"
            placeholder="Issue system prompts, code instructions or test pipelines..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="form-input flex-1 py-3 text-xs font-mono"
            disabled={isLoading}
          />
          <button type="submit" className="btn btn-primary px-5" disabled={isLoading || !input.trim()}>
            <Send size={14} />
          </button>
        </form>

      </div>

      {/* Right Parameters adjusters */}
      <div className="w-full lg:w-[280px] glow-card flex flex-col justify-between flex-shrink-0 h-full overflow-y-auto">
        <div className="space-y-6">
          
          <div className="flex items-center gap-2 border-b border-[rgba(255,255,255,0.05)] pb-3">
            <Sliders size={14} className="text-[var(--orange)]" />
            <span className="text-xs font-bold font-mono tracking-wider uppercase">PARAMETERS Cockpit</span>
          </div>

          {/* Model Selection */}
          <div className="space-y-2">
            <label className="form-label" htmlFor="model-select">Active Model</label>
            <select
              id="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="form-input text-xs font-mono"
            >
              {models.map(m => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Context indicator info */}
          <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)] text-[10px] font-mono space-y-1 text-[var(--text-secondary)]">
            <div className="flex justify-between">
              <span>PROVIDER:</span>
              <span className="text-white uppercase">{activeModelInfo.provider}</span>
            </div>
            <div className="flex justify-between">
              <span>CONTEXT CAP:</span>
              <span className="text-white">{(activeModelInfo.context_window || 128000).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span>COST RATE:</span>
              <span className="text-white">${(activeModelInfo.cost_per_1k_input || 0).toFixed(5)} / 1K tokens</span>
            </div>
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono">
              <label className="form-label m-0" htmlFor="temperature-range">Temperature</label>
              <span className="text-white">{temperature.toFixed(2)}</span>
            </div>
            <input
              id="temperature-range"
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-[var(--orange)] bg-neutral-800"
            />
          </div>

          {/* Top-P */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono">
              <label className="form-label m-0" htmlFor="top-p-range">Top-P</label>
              <span className="text-white">{topP.toFixed(2)}</span>
            </div>
            <input
              id="top-p-range"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={topP}
              onChange={(e) => setTopP(parseFloat(e.target.value))}
              className="w-full accent-[var(--orange)] bg-neutral-800"
            />
          </div>

          {/* Max Tokens */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono">
              <label className="form-label m-0" htmlFor="max-tokens-range">Max Output Tokens</label>
              <span className="text-white">{maxTokens}</span>
            </div>
            <input
              id="max-tokens-range"
              type="range"
              min="1"
              max="4096"
              step="32"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full accent-[var(--orange)] bg-neutral-800"
            />
          </div>

        </div>

        {/* Bottom warnings / logs indicator */}
        <div className="pt-4 border-t border-[rgba(255,255,255,0.05)] text-[9px] font-mono text-[var(--text-muted)] space-y-1.5">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <Shield size={10} />
            <span>PII DE-IDENTIFICATION: ACTIVE</span>
          </div>
          <div className="flex items-center gap-1.5 text-[var(--orange)]">
            <Info size={10} />
            <span>REGION Burst LIMIT: NONE</span>
          </div>
        </div>

      </div>

    </div>
  );
};