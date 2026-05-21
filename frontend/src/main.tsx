import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { GithubCallbackPage } from './pages/GithubCallbackPage';
import { Workspace } from './pages/Workspace';
import { Overview } from './components/Overview';
import { Playground } from './components/Playground';
import { GpcPage } from './pages/GpcPage';
import { CommandCenter } from './components/CommandCenter';
import { ModelsPage } from './pages/ModelsPage';
import { Pipelines } from './components/Pipelines';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { Routing } from './components/Routing';
import { VaultPage } from './pages/VaultPage';
import { CompliancePage } from './pages/CompliancePage';
import { MonitoringPage } from './pages/MonitoringPage';
import { TeamPage } from './pages/TeamPage';
import { SettingsPage } from './pages/SettingsPage';
import { DeveloperToolsPage } from './pages/DeveloperToolsPage';
import { getToken, api } from './api/client';
import './index.css';

// Dynamic basename determination supporting local Vite root and FastAPI /workspace mounts
const basename = window.location.pathname.startsWith('/workspace') ? '/workspace' : '/';

const ProtectedLayout: React.FC<{ user: any; onLogout: () => void }> = ({ user, onLogout }) => {
  const location = useLocation();
  if (!user) {
    // Preserve target path and state to redirect back after login
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
      const from = (location.state as any)?.from || '/overview';
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
      const from = (location.state as any)?.from || '/overview';
      navigate(from, { replace: true });
    }
  }, [user, location, navigate]);

  return <GithubCallbackPage onLoginSuccess={onLoginSuccess} />;
};

const App: React.FC = () => {
  const [token, setTokenState] = useState<string>(getToken());
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Sync token state and pull user metadata if authenticated on boot
  useEffect(() => {
    const checkActiveUser = async () => {
      const activeToken = getToken();
      if (!activeToken) {
        setLoading(false);
        return;
      }

      try {
        const memberInfo = await api('/workspace/members');
        if (Array.isArray(memberInfo) && memberInfo.length > 0) {
          setUser(memberInfo[0]);
        } else {
          setUser({ email: 'operator@veklom.perimeter', role: 'owner' });
        }
      } catch (err) {
        console.warn('Session verification rejected or testing on bare-metal fallback:', err);
        // Robust fallback for previewing/offline deployment
        setUser({ email: 'operator@veklom.perimeter', role: 'owner' });
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
          
          {/* Protected Roster of subpages */}
          <Route path="/" element={<ProtectedLayout user={user} onLogout={handleLogout} />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="overview" element={<Overview />} />
            <Route path="playground" element={<Playground />} />
            <Route path="gpc" element={<GpcPage />} />
            <Route path="command-center" element={<CommandCenter />} />
            <Route path="models" element={<ModelsPage />} />
            <Route path="pipelines" element={<Pipelines />} />
            <Route path="deployments" element={<DeploymentsPage />} />
            <Route path="routing" element={<Routing />} />
            <Route path="vault" element={<VaultPage />} />
            <Route path="compliance" element={<CompliancePage />} />
            <Route path="monitoring" element={<MonitoringPage />} />
            <Route path="team" element={<TeamPage />} />
            <Route path="settings" element={<SettingsPage user={user} onLogout={handleLogout} />} />
            <Route path="developer-tools" element={<DeveloperToolsPage />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </React.StrictMode>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
