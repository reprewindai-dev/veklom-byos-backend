import React, { useEffect, useState } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { findNavItem } from './nav';
import type { AuthUser } from '../../api/auth';
import type { OverviewPayload } from '../../api/workspace';
import { workspaceApi } from '../../api/workspace';

interface AppShellProps {
  user: AuthUser | null;
  children: (route: string) => React.ReactNode;
}

function currentRoute(): string {
  return window.location.hash.replace(/^#\/?/, '') || 'overview';
}

export const AppShell: React.FC<AppShellProps> = ({ user, children }) => {
  const [route, setRoute] = useState<string>(currentRoute());
  const [overview, setOverview] = useState<OverviewPayload | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(currentRoute());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Live burn/budget/health for the topbar. Refreshes on an interval.
  useEffect(() => {
    let active = true;
    const load = () =>
      workspaceApi
        .overviewLive()
        .then((d) => active && setOverview(d))
        .catch(() => {
          /* topbar badges simply hide if unavailable — no fake values */
        });
    load();
    const t = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, []);

  const navigate = (id: string) => {
    window.location.hash = `#/${id}`;
    setRoute(id);
  };

  const item = findNavItem(route);

  return (
    <div className="shell-container grid-bg">
      <Sidebar active={route} onNavigate={navigate} />
      <main className="shell-main">
        <Topbar user={user} overview={overview} onSearch={(q) => navigate(`search?q=${encodeURIComponent(q)}`)} />
        <div className="shell-content">
          {item?.embed ? (
            <div
              className="w-full rounded-xl border border-[var(--border)] bg-black overflow-hidden shadow-[0_0_20px_var(--orange-glow)]"
              style={{ height: 'calc(100vh - 96px)' }}
            >
              <iframe
                src={item.embed}
                title={item.label}
                className="w-full h-full border-none bg-[#0a0a0a]"
              />
            </div>
          ) : (
            children(route)
          )}
        </div>
      </main>
    </div>
  );
};
