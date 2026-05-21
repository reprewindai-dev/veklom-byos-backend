import React from 'react';

export const GpcPage: React.FC = () => {
  return (
    <div className="w-full h-[calc(100vh-140px)] relative rounded-xl border border-white/5 bg-black overflow-hidden flex flex-col justify-between shadow-[0_0_20px_rgba(255,184,0,0.05)]">
      <div className="h-6 bg-neutral-900 border-b border-white/5 px-3 flex items-center justify-between font-mono text-[9px] text-[var(--orange)] uppercase tracking-wider select-none shrink-0">
        <span>ESTABLISHING GPC BARE-METAL INSTANCE...</span>
        <span>HOST: LOCAL-GPC-COMPILER</span>
      </div>
      <iframe src="/gpc-engine" className="flex-1 w-full border-none bg-[#050505]" title="Governed Plan Compiler" />
    </div>
  );
};
