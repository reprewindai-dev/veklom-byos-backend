import React from 'react';

// ---- Card / Panel ---------------------------------------------------------
export const Panel: React.FC<React.HTMLAttributes<HTMLDivElement> & { highlight?: boolean }> = ({
  highlight,
  className = '',
  children,
  ...rest
}) => (
  <div className={`glow-card ${highlight ? 'glow-card-highlight' : ''} ${className}`} {...rest}>
    {children}
  </div>
);

// ---- Section eyebrow + title ---------------------------------------------
export const Eyebrow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = '',
}) => (
  <span
    className={`block text-[9px] font-bold font-mono tracking-[0.18em] uppercase text-[var(--text-muted)] ${className}`}
  >
    {children}
  </span>
);

export const PanelTitle: React.FC<{
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
}> = ({ eyebrow, title, right, className = '' }) => (
  <div className={`flex items-start justify-between gap-3 ${className}`}>
    <div>
      {eyebrow && <Eyebrow className="mb-1">{eyebrow}</Eyebrow>}
      <h3 className="text-sm font-bold text-white leading-tight">{title}</h3>
    </div>
    {right}
  </div>
);

// ---- Badge ----------------------------------------------------------------
type Tone = 'green' | 'red' | 'blue' | 'orange' | 'muted';
export const Badge: React.FC<{ tone?: Tone; children: React.ReactNode; className?: string }> = ({
  tone = 'muted',
  children,
  className = '',
}) => {
  const map: Record<Tone, string> = {
    green: 'badge-green',
    red: 'badge-red',
    blue: 'badge-blue',
    orange: 'badge-orange',
    muted: 'text-[var(--text-secondary)] border-[var(--border)] bg-white/[0.02]',
  };
  return <span className={`badge ${map[tone]} ${className}`}>{children}</span>;
};

// ---- Stat card (top KPI row) ---------------------------------------------
export const StatCard: React.FC<{
  label: string;
  value: React.ReactNode;
  delta?: string;
  deltaTone?: Tone;
  children?: React.ReactNode; // sparkline slot
}> = ({ label, value, delta, deltaTone = 'green', children }) => (
  <div className="glow-card !p-4 flex flex-col gap-2">
    <div className="flex items-center justify-between">
      <Eyebrow>{label}</Eyebrow>
      {delta && (
        <span
          className={`text-[10px] font-mono font-semibold ${
            deltaTone === 'red' ? 'text-[var(--red)]' : 'text-[var(--green)]'
          }`}
        >
          {delta}
        </span>
      )}
    </div>
    <div className="text-2xl font-bold text-white font-mono leading-none">{value}</div>
    {children && <div className="h-8 -mb-1">{children}</div>}
  </div>
);

// ---- State helpers --------------------------------------------------------
export const Loading: React.FC<{ label?: string }> = ({ label = 'Loading' }) => (
  <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-secondary)] py-8 justify-center">
    <span className="pulse-dot" /> {label}…
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="p-4 rounded-lg border border-[var(--red-dim)] bg-[var(--red-dim)] text-[var(--red)] text-xs font-mono flex items-center justify-between gap-3">
    <span>{message}</span>
    {onRetry && (
      <button onClick={onRetry} className="btn btn-sm btn-secondary !text-[var(--red)]">
        Retry
      </button>
    )}
  </div>
);

export const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="py-10 text-center text-xs font-mono text-[var(--text-muted)]">{message}</div>
);

// ---- Gated (paid-plan / capability) notice -------------------------------
export const GatedNotice: React.FC<{ title: string; detail: string; cta?: React.ReactNode }> = ({
  title,
  detail,
  cta,
}) => (
  <div className="glow-card flex flex-col items-center text-center gap-3 py-12">
    <span className="badge badge-orange">Upgrade required</span>
    <h3 className="text-base font-bold text-white">{title}</h3>
    <p className="text-xs text-[var(--text-secondary)] max-w-md">{detail}</p>
    {cta}
  </div>
);
