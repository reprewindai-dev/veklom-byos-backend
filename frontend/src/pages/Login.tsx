import React, { useState } from 'react';
import { api, setToken } from '../api/client';
import { Shield, Key, AlertCircle, Cpu } from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: any) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all credentials.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const data = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      if (data && data.access_token) {
        setToken(data.access_token);
        onLoginSuccess(data.user);
      } else {
        throw new Error('Authentication returned an invalid response token.');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid email or password. Access Denied.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid-bg min-h-screen flex items-center justify-center p-4">
      {/* Decorative center grid glow */}
      <div className="absolute w-96 h-96 rounded-full bg-[#ffb800] opacity-[0.03] blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-[420px] glow-card bg-[rgba(10,10,12,0.8)] border border-[rgba(255,255,255,0.06)] rounded-xl p-8 backdrop-blur-md relative z-10">
        
        {/* Custom Glowing SVG Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative mb-3 flex items-center justify-center">
            {/* Pulsing outer aura */}
            <div className="absolute w-12 h-12 rounded-full border border-[rgba(255,184,0,0.4)] animate-ping opacity-25"></div>
            
            {/* SVG Glowing V Logo */}
            <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-[0_0_8px_rgba(255,184,0,0.5)]">
              <path d="M15 15 L45 85 C48 91, 52 91, 55 85 L85 15" stroke="#ffb800" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
              {/* Central Sovereignty Dot */}
              <circle cx="50" cy="48" r="8" fill="#ffffff" className="animate-pulse" />
            </svg>
          </div>
          <h1 className="text-xl font-bold tracking-[0.05em] text-white">VEKLOM</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1 tracking-[0.02em]">SOVEREIGN AI CONTROL PLANE</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-md bg-[rgba(255,68,102,0.08)] border border-[rgba(255,68,102,0.2)] flex items-start gap-3 text-red-400 text-xs">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
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
                placeholder="ΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇóΓÇó"
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
              className="btn btn-primary w-full py-3 text-xs tracking-[0.08em] font-bold"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Cpu size={14} className="animate-spin" />
                  DECRYPTING CONTROL PLANE...
                </>
              ) : (
                'ESTABLISH SECURE ACCESS'
              )}
            </button>
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