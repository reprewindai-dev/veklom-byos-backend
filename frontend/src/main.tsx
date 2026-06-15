import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { Login } from './pages/Login';
import { AppShell } from './components/layout/AppShell';
import { Overview } from './pages/Overview';
import { PageStub } from './pages/PageStub';
import { me, type AuthUser } from './api/auth';
import { getToken, clearSession, onUnauthorized } from './lib/http';
import { AgentArena } from './pages/AgentArena';
import { AuditTrace } from './pages/AuditTrace';
import { GatewayConfig } from './pages/GatewayConfig';
import { Governance } from './pages/Governance';
import './index.css';

const navigate = (id: string) => {
  window.location.hash = `#/${id}`;
};

function renderPage(route: string): React.ReactNode {
  const base = route.split('?')[0];
  switch (base) {
    case 'overview':
      return <Overview onNavigate={navigate} />;
    case 'audit-trace':
      return <AuditTrace />;
    case 'gateway':
      return <GatewayConfig />;
    case 'governance':
      return <Governance />;
    case 'arena':
      return <AgentArena />;
    case 'search':
      return <PageStub title="Search" routes={['GET /api/v1/workspace/search?q=']} />;
    default:
      return <Overview onNavigate={navigate} />;
  }
}

const Boot: React.FC = () => (
  <div className="grid-bg min-h-screen flex flex-col items-center justify-center gap-4 text-xs font-mono text-[var(--text-secondary)]">
    <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-pulse drop-shadow-[0_0_8px_rgba(255,184,0,0.4)]">
      <path d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15" stroke="#ffb800" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="50" cy="48" r="8" fill="#ffffff" />
    </svg>
    <span className="tracking-widest uppercase">Booting sovereign control plane…</span>
  </div>
);

const App: React.FC = () => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Verify the session against the backend. No fake-user fallback: if the
    // token is missing/invalid the user is sent to login.
    if (!getToken()) {
      setLoading(false);
      return;
    }
    me()
      .then((profile) => setUser(profile))
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => onUnauthorized(() => setUser(null)), []);

  if (loading) return <Boot />;

  if (!user) return <Login onAuthed={setUser} />;

  return (
    <AppShell user={user} key={user.id}>
      {(route) => renderPage(route)}
    </AppShell>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);