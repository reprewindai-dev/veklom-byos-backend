import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { Login } from './pages/Login';
import { AppShell } from './components/layout/AppShell';
import { Overview } from './pages/Overview';
import { PageStub } from './pages/PageStub';
import { me, type AuthUser } from './api/auth';
import { getToken, clearSession, onUnauthorized } from './lib/http';
import './index.css';

const navigate = (id: string) => {
  window.location.hash = `#/${id}`;
};

function renderPage(route: string): React.ReactNode {
  const base = route.split('?')[0];
  switch (base) {
    case 'overview':
      return <Overview onNavigate={navigate} />;
    case 'playground':
      return <PageStub title="Playground" routes={['POST /api/v1/playground/inference', 'GET /api/v1/playground/sessions', 'GET /api/v1/ai/models']} />;
    case 'marketplace':
      return <PageStub title="Marketplace" routes={['GET /api/v1/marketplace/listings', 'GET /api/v1/marketplace/listings/{id}']} />;
    case 'models':
      return <PageStub title="Models" routes={['GET /api/v1/workspace/models', 'PATCH /api/v1/workspace/models/{id}', 'GET /api/v1/workspace/models/{id}/versions']} />;
    case 'pipelines':
      return <PageStub title="Pipelines" routes={['GET /api/v1/pipelines', 'POST /api/v1/pipelines', 'POST /api/v1/pipelines/{id}/run']} />;
    case 'deployments':
      return <PageStub title="Deployments" routes={['GET /api/v1/deployments', 'POST /api/v1/deployments']} />;
    case 'vault':
      return <PageStub title="Vault" routes={['GET /api/v1/workspace/api-keys', 'POST /api/v1/workspace/api-keys', 'DELETE /api/v1/workspace/api-keys/{id}']} />;
    case 'compliance':
      return <PageStub title="Compliance" routes={['GET /api/v1/compliance/regulations', 'POST /api/v1/compliance/check']} />;
    case 'monitoring':
      return <PageStub title="Monitoring" routes={['GET /api/v1/monitoring/events', 'GET /api/v1/workspace/observability']} />;
    case 'billing':
      return <PageStub title="Billing" routes={['GET /api/v1/wallet/balance', 'GET /api/v1/subscriptions/plans', 'GET /api/v1/billing/invoices']} />;
    case 'team':
      return <PageStub title="Team" routes={['GET /api/v1/workspace/members', 'POST /api/v1/workspace/members/invite']} />;
    case 'settings':
      return <PageStub title="Settings" routes={['GET /api/v1/workspace/settings', 'PATCH /api/v1/workspace/settings']} />;
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