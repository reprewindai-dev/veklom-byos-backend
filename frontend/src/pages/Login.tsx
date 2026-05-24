import React, { useState } from 'react';
import { api, getApiBase, setToken } from '../api/client';
import {
  AlertCircle,
  ArrowRight,
  Building2,
  Cpu,
  Github,
  KeyRound,
  LockKeyhole,
  Mail,
  ShieldCheck,
  User,
} from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: any) => void;
}

type AuthMode = 'signin' | 'signup';

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState<AuthMode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [error, setError] = useState('');

  const isSignup = mode === 'signup';

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password || (isSignup && !fullName)) {
      setError(isSignup ? 'Full name, work email, and password are required.' : 'Work email and password are required.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const endpoint = isSignup ? '/auth/register' : '/auth/login';
      const bodyPayload = isSignup
        ? {
            email,
            password,
            full_name: fullName,
            workspace_name: workspaceName,
          }
        : { email, password };

      const data = await api(endpoint, {
        method: 'POST',
        body: JSON.stringify(bodyPayload),
      });

      if (!data?.access_token || !data?.user) {
        throw new Error('Authentication returned an invalid session.');
      }

      setToken(data.access_token);
      localStorage.setItem('veklom_refresh_token', data.refresh_token || '');
      localStorage.setItem('veklom_user', JSON.stringify(data.user));
      onLoginSuccess(data.user);
    } catch (err: any) {
      setError(err.message || (isSignup ? 'Account creation failed.' : 'Invalid email or password.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleGithubLogin = async () => {
    setGithubLoading(true);
    setError('');

    try {
      const status = await api('/auth/github/status');
      if (!status?.configured) {
        setError('GitHub sign-in is not configured on this deployment yet. Use email sign-in for this workspace.');
        return;
      }

      window.location.href = `${getApiBase()}/auth/github/login`;
    } catch (err: any) {
      setError(err.message || 'GitHub sign-in is unavailable right now.');
    } finally {
      setGithubLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-layout">
        <section className="auth-brand-copy" aria-label="Veklom workspace access">
          <div className="auth-lockup">
            <img src="/favicon.svg" alt="" className="auth-mark" />
            <div className="auth-wordmark">
              <strong>Veklom</strong>
              <span>Sovereign AI Hub</span>
            </div>
          </div>

          <div className="auth-eyebrow">Workspace access</div>
          <h1>Enter the governed execution layer.</h1>
          <p>
            Sign in to manage agent workflows, marketplace tools, policy gates, audit evidence, and tenant-isolated
            runtime controls from one workspace.
          </p>

          <div className="auth-proof-grid" aria-label="Workspace controls">
            <div className="auth-proof">
              <ShieldCheck size={19} />
              <span>Tenant isolated</span>
              <small>Sessions resolve to one workspace boundary.</small>
            </div>
            <div className="auth-proof">
              <KeyRound size={19} />
              <span>JWT secured</span>
              <small>Bearer sessions are verified before workspace access.</small>
            </div>
            <div className="auth-proof">
              <Building2 size={19} />
              <span>BYOS ready</span>
              <small>Hosted, dedicated, and self-hosted paths share one login.</small>
            </div>
          </div>
        </section>

        <section className="auth-card" aria-label={isSignup ? 'Create Veklom account' : 'Sign in to Veklom'}>
          <div className="auth-card-header">
            <div className="auth-toggle" role="tablist" aria-label="Authentication mode">
              <button
                type="button"
                className={mode === 'signin' ? 'active' : ''}
                onClick={() => switchMode('signin')}
                aria-selected={mode === 'signin'}
              >
                Sign in
              </button>
              <button
                type="button"
                className={mode === 'signup' ? 'active' : ''}
                onClick={() => switchMode('signup')}
                aria-selected={mode === 'signup'}
              >
                Create account
              </button>
            </div>

            <h2>{isSignup ? 'Create your workspace' : 'Access your workspace'}</h2>
            <p>
              {isSignup
                ? 'A new tenant workspace is created for this account and separated from every other customer.'
                : 'Use the same account for Playground, Command Center, GPC, marketplace, billing, and evidence logs.'}
            </p>
          </div>

          {error && (
            <div className="auth-error" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            {isSignup && (
              <>
                <div className="auth-field">
                  <label htmlFor="full-name-input">Full name</label>
                  <div className="auth-input-wrap">
                    <User size={16} />
                    <input
                      id="full-name-input"
                      type="text"
                      placeholder="Your name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="auth-input"
                      autoComplete="name"
                      disabled={isLoading}
                      required
                    />
                  </div>
                </div>

                <div className="auth-field">
                  <label htmlFor="workspace-name-input">Workspace name</label>
                  <div className="auth-input-wrap">
                    <Building2 size={16} />
                    <input
                      id="workspace-name-input"
                      type="text"
                      placeholder="Company or team name"
                      value={workspaceName}
                      onChange={(e) => setWorkspaceName(e.target.value)}
                      className="auth-input"
                      autoComplete="organization"
                      disabled={isLoading}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="auth-field">
              <label htmlFor="email-input">Work email</label>
              <div className="auth-input-wrap">
                <Mail size={16} />
                <input
                  id="email-input"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="auth-input"
                  disabled={isLoading}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="password-input">Password</label>
              <div className="auth-input-wrap">
                <LockKeyhole size={16} />
                <input
                  id="password-input"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-input"
                  disabled={isLoading}
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                  required
                />
              </div>
            </div>

            <div className="auth-actions">
              <button type="submit" className="auth-primary" disabled={isLoading || githubLoading}>
                {isLoading ? (
                  <>
                    <Cpu size={16} className="animate-spin" />
                    {isSignup ? 'Creating workspace' : 'Signing in'}
                  </>
                ) : (
                  <>
                    {isSignup ? 'Create workspace' : 'Sign in'}
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleGithubLogin}
                className="auth-secondary"
                disabled={isLoading || githubLoading}
              >
                {githubLoading ? <Cpu size={16} className="animate-spin" /> : <Github size={16} />}
                Continue with GitHub
              </button>
            </div>
          </form>

          <div className="auth-footer">
            <span>JWT bearer</span>
            <span>Tenant scoped</span>
            <span>Audit ready</span>
          </div>
        </section>
      </div>
    </div>
  );
};
