import React, { useState } from 'react';
import { api, setToken } from '../api/client';
import { Shield, Key, AlertCircle, Cpu, Github, User } from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: any) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || (isSignup && !username)) {
      setError('Please fill in all required credentials.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const endpoint = isSignup ? '/auth/register' : '/auth/login';
      const bodyPayload = isSignup 
        ? { email, password, username, full_name: fullName } 
        : { email, password };

      const data = await api(endpoint, {
        method: 'POST',
        body: JSON.stringify(bodyPayload),
      });

      if (data && data.access_token) {
        setToken(data.access_token);
        onLoginSuccess(data.user);
      } else {
        throw new Error('Authentication returned an invalid response token.');
      }
    } catch (err: any) {
      setError(err.message || (isSignup ? 'Registration failed.' : 'Invalid email or password. Access Denied.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleGithubLogin = () => {
    // A true GitHub login must use a full window redirect to the backend's OAuth endpoint,
    // which then 307 redirects to GitHub. We cannot use `fetch()` for this.
    const apiBase = (window as any).__VEKLOM_API_BASE__ || '/api/v1';
    window.location.href = `${apiBase}/auth/github/login`;
  };

  return (
    <div className="grid-bg min-h-screen flex items-center justify-center p-4">
      {/* Decorative center grid glow */}
      <div className="absolute w-96 h-96 rounded-full bg-[#ffb800] opacity-[0.03] blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-[420px] glow-card bg-[rgba(10,10,12,0.8)] border border-[rgba(255,255,255,0.06)] rounded-xl p-8 backdrop-blur-md relative z-10">
        
        <div className="flex flex-col items-center mb-8">
          <img
            src="/static/branding/veklom-wordmark.png"
            alt="Veklom"
            className="veklom-wordmark h-14 mb-4"
          />
          <h1 className="text-xl font-bold tracking-[0.05em] text-white">SOVEREIGN AI HUB</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1 tracking-[0.02em]">SOVEREIGN AI CONTROL PLANE</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-md bg-[rgba(255,68,102,0.08)] border border-[rgba(255,68,102,0.2)] flex items-start gap-3 text-red-400 text-xs">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {isSignup && (
            <>
              <div>
                <label className="form-label" htmlFor="username-input">Operator Alias</label>
                <div className="relative">
                  <span className="absolute left-3 top-3.5 text-[var(--text-muted)]">
                    <User size={14} />
                  </span>
                  <input
                    id="username-input"
                    type="text"
                    placeholder="operator_1"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="form-input pl-9"
                    disabled={isLoading}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="form-label" htmlFor="fullname-input">Full Designation (Optional)</label>
                <div className="relative">
                  <span className="absolute left-3 top-3.5 text-[var(--text-muted)]">
                    <User size={14} />
                  </span>
                  <input
                    id="fullname-input"
                    type="text"
                    placeholder="John Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="form-input pl-9"
                    disabled={isLoading}
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="form-label" htmlFor="email-input">Perimeter Email</label>
            <div className="relative">
              <span className="absolute left-3 top-3.5 text-[var(--text-muted)]">
                <Shield size={14} />
              </span>
              <input
                id="email-input"
                type="email"
                placeholder="operator@veklom.perimeter"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="form-input pl-9"
                disabled={isLoading}
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div>
            <label className="form-label" htmlFor="password-input">Runtime Key</label>
            <div className="relative">
              <span className="absolute left-3 top-3.5 text-[var(--text-muted)]">
                <Key size={14} />
              </span>
              <input
                id="password-input"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input pl-9"
                disabled={isLoading}
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="btn btn-primary w-full py-3 text-xs tracking-[0.08em] font-bold mb-3"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Cpu size={14} className="animate-spin" />
                  {isSignup ? 'PROVISIONING ACCOUNT...' : 'DECRYPTING CONTROL PLANE...'}
                </>
              ) : (
                isSignup ? 'INITIALIZE NEW PERIMETER' : 'ESTABLISH SECURE ACCESS'
              )}
            </button>

            <button
              type="button"
              onClick={handleGithubLogin}
              className="w-full py-3 text-xs tracking-[0.08em] font-bold bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.08)] transition-colors rounded-md flex items-center justify-center gap-2 text-white mb-4"
              disabled={isLoading}
            >
              <Github size={16} />
              AUTHENTICATE WITH GITHUB
            </button>
            
            <div className="text-center mt-2">
              <button
                type="button"
                onClick={() => setIsSignup(!isSignup)}
                className="text-[10px] text-[var(--text-secondary)] hover:text-[var(--orange)] font-mono tracking-wider transition-colors"
                disabled={isLoading}
              >
                {isSignup ? 'ALREADY HAVE AN ACCOUNT? SIGN IN' : 'NO ACCOUNT YET? CREATE PERIMETER'}
              </button>
            </div>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-[rgba(255,255,255,0.05)] text-[10px] text-center text-[var(--text-muted)] flex flex-col gap-1 font-mono">
          <div>REGIONAL GATEWAY: HETZNER-FSN1</div>
          <div>ENCRYPTION: AES-GCM-256-CHAOS</div>
        </div>

      </div>
    </div>
  );
};
