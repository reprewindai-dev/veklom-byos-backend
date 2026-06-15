import React, { useState } from 'react';
import { Database, Shield, Activity, Clock, Server, Fingerprint, Coins, Cpu, Link, ChevronDown, ChevronUp } from 'lucide-react';

export interface TelemetryData {
  tenant_id: string;
  workspace_id?: string;
  log_id: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  provider: string;
  model: string;
  cost?: string | number;
  acp402_receipt?: string;
  self_learning?: boolean;
}

interface TelemetryPanelProps {
  data: TelemetryData | null;
  className?: string;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ data, className = '' }) => {
  const [expanded, setExpanded] = useState(false);
  
  if (!data) return null;

  const isAcpPaid = !!data.acp402_receipt || !!data.cost;
  const isLearning = data.self_learning ?? true;

  return (
    <div className={`glow-card border border-[rgba(255,255,255,0.05)] rounded-lg p-3 bg-[#0a0f16] font-mono text-[10px] space-y-3 ${className}`}>
      {/* Minimal Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-emerald-400" />
          <span className="font-bold text-xs uppercase tracking-widest text-emerald-400">PGL AUDIT</span>
        </div>
        <div className="flex items-center gap-2">
          {isLearning && (
            <span className="bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded border border-purple-500/20 uppercase tracking-wider text-[8px] font-bold flex items-center gap-1" title="Self-Learning Active">
              <Cpu size={10} />
            </span>
          )}
          {isAcpPaid && (
            <span className="bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20 uppercase tracking-wider text-[8px] font-bold flex items-center gap-1" title="ACP-402 Verified">
              <Coins size={10} /> Paid
            </span>
          )}
          <button 
            onClick={() => setExpanded(!expanded)}
            className="ml-2 text-[var(--text-muted)] hover:text-white transition-colors flex items-center gap-1 bg-white/5 px-2 py-1 rounded"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            <span className="text-[9px] uppercase tracking-wider">{expanded ? 'Hide Details' : 'View Trace'}</span>
          </button>
        </div>
      </div>

      {/* Expanded Technical Details */}
      {expanded && (
        <div className="pt-3 border-t border-[rgba(255,255,255,0.05)] grid grid-cols-2 gap-x-4 gap-y-4 text-[var(--text-secondary)] animate-in slide-in-from-top-2 fade-in duration-200">
          
          <div className="flex items-center gap-2">
            <Fingerprint size={14} className="text-[var(--orange)] shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-[var(--text-muted)] font-bold">Tenant Space</span>
              <span className="text-white truncate font-medium text-[11px]" title={data.tenant_id}>{data.tenant_id || 'default-tenant'}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Shield size={14} className="text-blue-400 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-[var(--text-muted)] font-bold">Immutable Audit ID</span>
              <span className="text-blue-300 truncate font-medium text-[11px]" title={data.log_id}>{data.log_id}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Database size={14} className="text-zinc-400 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-[var(--text-muted)] font-bold">Compute (Tokens)</span>
              <span className="text-white font-medium text-[11px]">{data.total_tokens} (P:{data.prompt_tokens} | C:{data.completion_tokens})</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Server size={14} className="text-pink-400 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-[var(--text-muted)] font-bold">Node Route</span>
              <span className="text-white font-medium text-[11px] truncate">{data.provider} / {data.model}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Clock size={14} className="text-yellow-400 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-[var(--text-muted)] font-bold">Latency</span>
              <span className="text-white font-medium text-[11px]">{data.latency_ms} ms</span>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-emerald-950/20 p-1.5 rounded border border-emerald-900/50">
            <Link size={14} className="text-emerald-400 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="uppercase text-[8px] text-emerald-500 font-bold">ACP-402 Settlement</span>
              <span className="text-emerald-400 font-bold text-[11px]">
                {data.acp402_receipt ? `Tx: ${data.acp402_receipt.substring(0,8)}...` : (data.cost ? `$${data.cost}` : '$0.000000')}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
