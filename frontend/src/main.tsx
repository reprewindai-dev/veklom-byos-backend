import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { GithubCallbackPage } from './pages/GithubCallbackPage';
import { Workspace } from './pages/Workspace';
import { CommandCenterPage } from './pages/CommandCenterPage';
import { Playground } from './components/Playground';
import { GpcPage } from './pages/GpcPage';
import { MarketplaceLayout } from './components/Marketplace/MarketplaceLayout';
import { DeveloperToolsPage } from './pages/DeveloperToolsPage';
import { IronGridPage } from './pages/IronGridPage';
import { GreenVisionPage } from './pages/GreenVisionPage';
import { AgentWorkforcePage } from './pages/AgentWorkforcePage';
import { ChainOpsPage } from './pages/ChainOpsPage';
import { EvidenceAuditPage } from './pages/EvidenceAuditPage';
import { TerminalsPage } from './pages/TerminalsPage';
import { UsersIdentityPage } from './pages/UsersIdentityPage';
import { BillingPage } from './pages/BillingPage';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { SettingsPage } from './pages/SettingsPage';
import { getToken, setToken, api } from './api/client';
import './index.css';

const basename = window.location.pathname.startsWith('/workspace') ? '/workspace' : '/';

const ProtectedLayout: React.FC<{ user: any; onLogout: () => void }> = ({ user, onLogout }) => {
  const location = useLocation();
  if (!user) {
    const targetPath = location.pathname + location.search + location.hash;
    return <Navigate to="/login" state={{ from: targetPath }} replace />;
  }
  return <Workspace user={user} onLogout={onLogout} />;
};

const LoginWrapper: React.FC<{ user: any; onLoginSuccess: (u: any) => void }> = ({ user, onLoginSuccess }) => {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    if (user) {
      const from = (location.state as any)?.from || '/command-center';
      navigate(from, { replace: true });
    }
  }, [user, location, navigate]);
  return <Login onLoginSuccess={onLoginSuccess} />;
};

const GithubCallbackWrapper: React.FC<{ user: any; onLoginSuccess: (u: any) => void }> = ({ user, onLoginSuccess }) => {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    if (user) {
      const from = (location.state as any)?.from || '/command-center';
      navigate(from, { replace: true });
    }
  }, [user, location, navigate]);
  return <GithubCallbackPage onLoginSuccess={onLoginSuccess} />;
};

const App: React.FC = () => {
  const [token, setTokenState] = useState<string>(getToken());
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkActiveUser = async () => {
      const activeToken = getToken();
      if (!activeToken) { setLoading(false); return; }
      try {
        const activeUser = await api('/auth/me');
        setUser(activeUser);
      } catch (err) {
        console.warn('Session verification rejected:', err);
        setToken('');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkActiveUser();
  }, [token]);

  const handleLoginSuccess = (loggedInUser: any) => {
    setUser(loggedInUser);
    setTokenState(getToken());
  };

  const handleLogout = () => {
    setToken('');
    setUser(null);
    setTokenState('');
  };

  if (loading) {
    return (
      <div className="grid-bg min-h-screen flex flex-col items-center justify-center gap-4 text-xs font-mono text-[var(--text-secondary)]">
        <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-pulse drop-shadow-[0_0_8px_rgba(255,184,0,0.4)]">
          <path d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15" stroke="#ffb800" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="50" cy="48" r="8" fill="#ffffff" />
        </svg>
        <span className="tracking-widest uppercase">BOOTING SOVEREIGN AGENT SYSTEM...</span>
      </div>
    );
  }

  return (
    <React.StrictMode>
      <BrowserRouter basename={basename}>
        <Routes>
          <Route path="/login" element={<LoginWrapper user={user} onLoginSuccess={handleLoginSuccess} />} />
          <Route path="/github/callback" element={<GithubCallbackWrapper user={user} onLoginSuccess={handleLoginSuccess} />} />

          <Route path="/" element={<ProtectedLayout user={user} onLogout={handleLogout} />}>
            <Route index element={<Navigate to="/command-center" replace />} />

            {/* ── 12-item workspace spine ── */}
            <Route path="command-center" element={<CommandCenterPage />} />
            <Route path="playground" element={<Playground />} />
            <Route path="gpc" element={<GpcPage />} />
            <Route path="marketplace" element={<MarketplaceLayout />}>
              <Route index element={<DeveloperToolsPage />} />
              <Route path="irongrid" element={<IronGridPage />} />
              <Route path="greenvision" element={<GreenVisionPage />} />
            </Route>
            <Route path="agent-workforce" element={<AgentWorkforcePage />} />
            <Route path="chainops" element={<ChainOpsPage />} />
            <Route path="evidence" element={<EvidenceAuditPage />} />
            <Route path="terminals" element={<TerminalsPage />} />
            <Route path="users" element={<UsersIdentityPage />} />
            <Route path="billing" element={<BillingPage />} />
            <Route path="deployments" element={<DeploymentsPage />} />
            <Route path="settings" element={<SettingsPage user={user} onLogout={handleLogout} />} />

            {/* Legacy redirects */}
            <Route path="overview" element={<Navigate to="/command-center" replace />} />
            <Route path="monitoring" element={<Navigate to="/users" replace />} />
            <Route path="team" element={<Navigate to="/users" replace />} />
            <Route path="compliance" element={<Navigate to="/evidence" replace />} />
            <Route path="developer-tools" element={<Navigate to="/marketplace" replace />} />
            <Route path="*" element={<Navigate to="/command-center" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </React.StrictMode>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
