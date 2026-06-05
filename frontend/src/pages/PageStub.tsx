import React from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Panel } from '../components/ui/primitives';

// Honest placeholder for pages still being wired. Lists the REAL backend
// routes the finished page will call — never renders fake data.
export const PageStub: React.FC<{ title: string; routes: string[] }> = ({ title, routes }) => (
  <>
    <PageHeader eyebrow="Under construction" title={title} description="This page is being wired to live backend routes. No placeholder data is shown." />
    <Panel>
      <div className="text-[10px] font-bold font-mono uppercase tracking-wider text-[var(--text-muted)] mb-3">
        Will call
      </div>
      <ul className="space-y-1.5">
        {routes.map((r) => (
          <li key={r} className="font-mono text-xs text-[var(--text-secondary)] flex items-center gap-2">
            <span className="pulse-dot" /> {r}
          </li>
        ))}
      </ul>
    </Panel>
  </>
);
