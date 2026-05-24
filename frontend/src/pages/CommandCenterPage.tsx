import React from 'react';

export const CommandCenterPage: React.FC = () => {
  return (
    <div className="w-full h-[calc(100vh-92px)] relative rounded-xl border border-white/5 bg-black overflow-hidden flex flex-col shadow-[0_0_20px_rgba(255,184,0,0.05)]">
      <div className="h-8 bg-neutral-900 border-b border-white/5 px-4 flex items-center justify-between font-mono text-[9px] text-[var(--orange)] uppercase tracking-wider select-none shrink-0">
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--orange)] animate-pulse"></span>
          VEKLOM COMMAND CENTER — OPERATOR INTELLIGENCE CONSOLE
        </span>
        <span className="text-white/20">INTERNAL ONLY · AUTH REQUIRED</span>
      </div>
      <iframe
        src="/command-center/"
        className="flex-1 w-full border-none bg-[#0a0a0a]"
        title="Veklom Command Center"
        allow="clipboard-write"
      />
    </div>
  );
};
