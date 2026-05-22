// @ts-nocheck
import React from 'react';
import { motion } from 'motion/react';
import { ShieldCheck, Search, Scissors, FileText, Globe, AlertTriangle } from 'lucide-react';
import { GatewayStatus } from '../types';

interface MCPGatewayProps {
  status: GatewayStatus;
}

export const MCPGateway: React.FC<MCPGatewayProps> = ({ status }) => {
  const features = [
    { name: 'Payload Sanitization', icon: <Search size={12} />, status: status.sanitization },
    { name: 'PII Redaction', icon: <Scissors size={12} />, status: status.redaction },
    { name: 'Behavior Auditing', icon: <FileText size={12} />, status: status.auditing },
    { name: 'Egress Control', icon: <Globe size={12} />, status: status.egress_control },
  ];

  return (
    <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-emerald-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Zero-Trust MCP Gateway</h2>
        </div>
        <div className="flex gap-2">
           {status.last_scan_result === 'threat_detected' && (
              <span className="flex items-center gap-1 text-[9px] font-mono text-red-400 bg-red-400/10 px-2 py-0.5 rounded border border-red-400/20 animate-pulse">
                <AlertTriangle size={8} /> THREAT DETECTED
              </span>
           )}
           <span className="text-[9px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20">ENFORCEMENT ACTIVE</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {features.map((f) => (
          <div key={f.name} className="flex flex-col items-center justify-center p-3 rounded-xl bg-black/40 border border-white/5 text-center gap-2">
              <div className={`p-2 rounded-lg ${f.status === 'active' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-white/5 text-white/20'}`}>
                {f.icon}
              </div>
              <span className="text-[9px] font-mono uppercase text-white/40 leading-none">{f.name}</span>
              <span className={`text-[8px] font-mono uppercase ${f.status === 'active' ? 'text-emerald-400' : 'text-white/20'}`}>
                {f.status}
              </span>
          </div>
        ))}
      </div>

      <div className="bg-black/40 rounded-xl border border-white/5 p-4 overflow-hidden relative">
         <div className="flex items-center justify-between mb-3 text-[10px] font-mono uppercase text-white/40 italic">
            <span>Real-time Ingress Stream</span>
            <span className="text-emerald-400 animate-pulse">Scanning...</span>
         </div>
         <div className="space-y-1">
            {[...Array(3)].map((_, i) => (
                <div key={i} className="flex gap-2 text-[9px] font-mono text-white/20">
                   <span className="text-emerald-400/50">[{new Date().toLocaleTimeString()}]</span>
                   <span className="truncate">MCP://verify_remote_state/SCHEMA_VALIDATION -&gt; PASS (Hash: 0x9b2a...)</span>
                </div>
            ))}
         </div>
         <motion.div 
            animate={{ top: ['0%', '100%', '0%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="absolute left-0 w-full h-[1px] bg-emerald-400/20 z-10"
         />
      </div>
    </div>
  );
};
