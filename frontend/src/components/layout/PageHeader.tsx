import React from 'react';

interface PageHeaderProps {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  chips?: React.ReactNode;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ eyebrow, title, description, chips, actions }) => (
  <div className="flex flex-col gap-4 mb-6">
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div className="min-w-0">
        {eyebrow && (
          <span className="block text-[10px] font-bold font-mono tracking-[0.18em] uppercase text-[var(--text-muted)] mb-2">
            {eyebrow}
          </span>
        )}
        <h1 className="text-2xl font-bold text-white leading-tight">{title}</h1>
        {description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 max-w-2xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
    {chips && <div className="flex items-center gap-2 flex-wrap">{chips}</div>}
  </div>
);
