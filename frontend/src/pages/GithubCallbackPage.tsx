import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Cpu, AlertCircle, ShieldCheck } from "lucide-react";
import { api, setToken } from "../api/client";

interface GithubCallbackProps {
  onLoginSuccess: (user: any) => void;
}

export const GithubCallbackPage: React.FC<GithubCallbackProps> = ({ onLoginSuccess }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code") || "";
    const state = searchParams.get("state") || "";

    if (!code || !state) {
      setLoading(false);
      setError("Missing GitHub OAuth callback parameters.");
      return;
    }

    const processCallback = async () => {
      try {
        const payload = await api("/auth/github/callback", {
          method: "POST",
          body: JSON.stringify({ code, state })
        });

        if (payload && payload.access_token) {
          setToken(payload.access_token);
          onLoginSuccess(payload.user);
        } else {
          throw new Error("Invalid response from authentication server.");
        }
      } catch (err: any) {
        setError(err.message || "GitHub sign-in failed. Session rejected.");
        setLoading(false);
      }
    };

    processCallback();
  }, [searchParams, navigate, onLoginSuccess]);

  return (
    <div className="grid-bg min-h-screen flex items-center justify-center p-4">
      <div className="absolute w-96 h-96 rounded-full bg-[#ffb800] opacity-[0.03] blur-[100px] pointer-events-none"></div>
      
      <div className="w-full max-w-[420px] glow-card bg-[rgba(10,10,12,0.8)] border border-[rgba(255,255,255,0.06)] rounded-xl p-8 backdrop-blur-md relative z-10 text-center">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[rgba(255,184,0,0.1)] mb-4">
            <ShieldCheck className="h-6 w-6 text-[var(--orange)]" />
          </div>
          <h1 className="text-xl font-bold tracking-[0.05em] text-white">GITHUB OAUTH</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1 tracking-[0.02em]">VERIFYING SECURE PERIMETER</p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 text-xs font-mono text-[var(--text-secondary)] py-4">
            <Cpu size={24} className="animate-spin text-[var(--orange)] drop-shadow-[0_0_8px_rgba(255,184,0,0.4)]" />
            <span className="tracking-widest uppercase">Completing GitHub sign-in...</span>
          </div>
        ) : error ? (
          <div className="p-4 rounded-md bg-[rgba(255,68,102,0.08)] border border-[rgba(255,68,102,0.2)] flex flex-col items-center gap-3 text-red-400 text-xs">
            <AlertCircle size={24} className="shrink-0" />
            <span className="text-center">{error}</span>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="mt-4 px-4 py-2 border border-[rgba(255,255,255,0.1)] rounded-md hover:bg-[rgba(255,255,255,0.05)] text-white transition-colors"
            >
              RETURN TO LOGIN
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
