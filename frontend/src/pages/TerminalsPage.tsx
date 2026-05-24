import React, { useState } from 'react';
import { MonitorDot } from 'lucide-react';

type TerminalTab = 'uacp' | 'runtime';

export const TerminalsPage: React.FC = () => {
  const [activeTerminal, setActiveTerminal] = useState<TerminalTab>('uacp');

  return (
    <div className="space-y-4 h-[calc(100vh-130px)] flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/5 pb-4 flex-shrink-0">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <MonitorDot size={18} className="text-[var(--orange)]" /> Terminals
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Governed execution consoles — every event is policy-traced.</p>
        </div>
        <div className="flex p-0.5 rounded-lg bg-black/40 border border-white/5 font-mono text-[11px]">
          <button
            onClick={() => setActiveTerminal('uacp')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all ${
              activeTerminal === 'uacp'
                ? 'bg-[var(--orange)] text-black'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            UACP Terminal
          </button>
          <button
            onClick={() => setActiveTerminal('runtime')}
            className={`px-3 py-1.5 rounded-md font-bold tracking-wide transition-all ${
              activeTerminal === 'runtime'
                ? 'bg-emerald-600 text-white'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            Veklom Runtime
          </button>
        </div>
      </div>

      <div className="flex-1 rounded-xl border overflow-hidden relative border-white/5 bg-black">
        {activeTerminal === 'uacp' && (
          <>
            <div className="h-7 bg-neutral-900 border-b border-white/5 px-3 flex items-center justify-between font-mono text-[9px] text-[var(--orange)] uppercase tracking-wider">
              <span>UACP TERMINAL — GOVERNANCE / CONTROL-PLANE CONSOLE</span>
              <span className="text-white/20">MCP · GPC GATES · POLICY TRACES · AUDIT EVENTS</span>
            </div>
            <iframe
              src="/command-center/quantum-terminal/"
              className="w-full border-none bg-black"
              style={{ height: 'calc(100% - 28px)' }}
              title="UACP Terminal"
            />
          </>
        )}
        {activeTerminal === 'runtime' && (
          <>
            <div className="h-7 bg-neutral-900 border-b border-emerald-500/10 px-3 flex items-center justify-between font-mono text-[9px] text-emerald-400 uppercase tracking-wider">
              <span>VEKLOM RUNTIME TERMINAL — EXECUTION / PROVIDER CONSOLE</span>
              <span className="text-white/20">REPO SCANS · TOOL CALLS · MODEL CALLS · LATENCY · COST</span>
            </div>
            <iframe
              src="/command-center/veklom-terminal/"
              className="w-full border-none bg-black"
              style={{ height: 'calc(100% - 28px)' }}
              title="Veklom Runtime Terminal"
            />
          </>
        )}
      </div>
    </div>
  );
};
