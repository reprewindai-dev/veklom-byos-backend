import React, { useState, useEffect } from 'react';
import { CreditCard, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

export const BillingPage: React.FC = () => {
  const [wallet, setWallet] = useState<any>(null);
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [walletRes, subRes] = await Promise.allSettled([
        api('/wallet/balance'),
        api('/subscriptions/current'),
      ]);
      if (walletRes.status === 'fulfilled') setWallet(walletRes.value);
      if (subRes.status === 'fulfilled') setSubscription(subRes.value);
    } catch {
      setError('Billing routes unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <CreditCard size={18} className="text-[var(--orange)] animate-pulse" /> Billing & Usage
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Token usage, provider spend, wallet balance, budget caps, and subscriptions.</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="btn btn-secondary px-3 py-1.5 text-xs font-mono flex items-center gap-1.5">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REFRESH
        </button>
      </div>

      {error && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs rounded font-mono flex items-center gap-2">
          <AlertCircle size={13} /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="glow-card p-5">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Wallet Balance</span>
          <span className="mt-2 block font-mono text-2xl font-bold text-white">
            {wallet ? `$${Number(wallet.balance_usd ?? wallet.balance ?? 0).toFixed(2)}` : '—'}
          </span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-emerald-400">
            {wallet ? 'Live balance' : loading ? 'Loading...' : 'Not wired'}
          </span>
        </div>

        <div className="glow-card p-5">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Current Plan</span>
          <span className="mt-2 block font-mono text-2xl font-bold text-[var(--orange)]">
            {subscription?.plan_name ?? subscription?.plan ?? (loading ? '...' : '—')}
          </span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--text-muted)]">
            {subscription?.status ?? 'Requires configuration'}
          </span>
        </div>

        <div className="glow-card p-5">
          <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">Tokens This Month</span>
          <span className="mt-2 block font-mono text-2xl font-bold text-white">
            {wallet?.tokens_used ?? '—'}
          </span>
          <span className="mt-1 block font-mono text-[9px] uppercase text-[var(--text-muted)]">
            {wallet?.budget_cap ? `Budget cap: $${wallet.budget_cap}` : 'No cap set'}
          </span>
        </div>
      </div>

      <div className="glow-card">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-3 border-b border-white/5 pb-2">Billing Routes</h3>
        <div className="space-y-2 font-mono text-[10px] text-[var(--text-secondary)]">
          {[
            ['GET', '/api/v1/wallet/balance', 'Token wallet balance'],
            ['GET', '/api/v1/subscriptions/current', 'Active subscription plan'],
            ['GET', '/api/v1/cost/summary', 'Cost per run / provider'],
            ['GET', '/api/v1/budget/rules', 'Hard/soft budget limits'],
            ['GET', '/api/v1/billing/invoices', 'Stripe invoice history'],
          ].map(([method, path, desc]) => (
            <div key={path} className="flex items-center gap-3 border-b border-white/[0.04] pb-2">
              <span className="text-[var(--orange)] font-bold w-8">{method}</span>
              <span className="text-white/60 flex-1">{path}</span>
              <span className="text-[var(--text-muted)]">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
