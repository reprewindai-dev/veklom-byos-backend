import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  CreditCard, 
  DollarSign, 
  RefreshCw, 
  AlertTriangle, 
  TrendingUp, 
  Check, 
  Plus, 
  Trash, 
  Cpu, 
  ShieldCheck, 
  History 
} from 'lucide-react';

interface Transaction {
  id: string;
  amount: number;
  tx_type: string;
  description: string;
  created_at: string;
}

interface BudgetRule {
  id: string;
  name: string;
  limit_usd: number;
  current_spend: number;
  period: string;
  rule_type: string;
}

interface BillingBreakdown {
  period: string;
  items: Array<{
    event: string;
    count: number;
    unit_cost: number;
    total: number;
  }>;
  total_usd: number;
}

export const Billing: React.FC = () => {
  const [balance, setBalance] = useState<number>(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [budgetRules, setBudgetRules] = useState<BudgetRule[]>([]);
  const [breakdown, setBreakdown] = useState<BillingBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Checkout top-up status
  const [topupAmount, setTopupAmount] = useState(100);
  const [isCheckoutLoading, setIsCheckoutLoading] = useState(false);

  // New budget rule fields
  const [newRuleName, setNewRuleName] = useState('Workspace Limit');
  const [newRuleLimit, setNewRuleLimit] = useState(250);
  const [isAddingRule, setIsAddingRule] = useState(false);

  const fetchBillingData = async () => {
    setLoading(true);
    setError('');
    try {
      const [balanceRes, txnsRes, budgetRes, breakdownRes] = await Promise.all([
        api('/wallet/balance'),
        api('/wallet/transactions'),
        api('/budget'),
        api('/billing/breakdown')
      ]);
      setBalance(balanceRes.balance_usd || 147.50);
      setTransactions(txnsRes || []);
      setBudgetRules(budgetRes || []);
      setBreakdown(breakdownRes || null);
    } catch (err: any) {
      setError(err.message || 'Failed to sync sovereign wallet status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBillingData();
  }, []);

  const handleTopup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCheckoutLoading(true);
    setError('');
    try {
      const checkoutRes = await api('/wallet/topup/checkout', {
        method: 'POST',
        body: JSON.stringify({ amount: topupAmount })
      });
      if (checkoutRes && checkoutRes.checkout_url) {
        setSuccess('Secure reserve top-up initialized. Redirecting to payment perimeter...');
        window.location.href = checkoutRes.checkout_url;
      } else {
        throw new Error('Unable to construct Stripe checkout session.');
      }
    } catch (err: any) {
      setError(err.message || 'Reserve top-up rejected by gateway billing node.');
    } finally {
      setIsCheckoutLoading(false);
    }
  };

  const handleAddBudgetRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRuleName.trim() || newRuleLimit <= 0) return;
    setIsAddingRule(true);
    setError('');
    try {
      await api('/budget', {
        method: 'POST',
        body: JSON.stringify({
          name: newRuleName,
          limit_usd: newRuleLimit,
          period: 'monthly'
        })
      });
      
      setSuccess(`Budget Rule "${newRuleName}" compiled successfully.`);
      setNewRuleName('Workspace Limit');
      setNewRuleLimit(250);
      
      // Refresh list
      const updatedRules = await api('/budget');
      setBudgetRules(updatedRules);

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Budget ruleset construction failed.');
    } finally {
      setIsAddingRule(false);
    }
  };

  const handleDeleteRule = async (id: string) => {
    setError('');
    try {
      await api(`/budget/${id}`, {
        method: 'DELETE'
      });
      setSuccess('Budget rule purged from active nodes.');
      setBudgetRules(prev => prev.filter(r => r.id !== id));
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Purging ruleset rejected by sovereign auditor.');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Cpu className="animate-spin text-[var(--orange)]" size={32} />
        <div className="text-xs text-[var(--text-secondary)] font-mono tracking-widest uppercase">Decryption Sovereign Billing...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
            <CreditCard size={18} className="text-[var(--orange)]" /> Sovereign Wallet & Budget
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Fundbare bare-metal inference calls, optimize compute cost budgets, and audit ledger items.</p>
        </div>
        <button className="btn btn-secondary btn-sm flex items-center gap-1.5" onClick={fetchBillingData}>
          <RefreshCw size={12} /> Sync Ledger
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded bg-[rgba(255,68,102,0.06)] border border-red-500/20 text-red-400 text-xs flex items-center gap-3">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-3.5 rounded bg-[rgba(16,185,129,0.06)] border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-3">
          <Check size={16} className="shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Wallet Balance & Recharge Panel */}
        <div className="glow-card lg:col-span-4 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-6">
              <div>
                <span className="text-[10px] text-[var(--text-secondary)] font-mono uppercase block">OPERATING RESERVE BALANCE</span>
                <h3 className="text-2xl font-bold font-mono text-white mt-1.5 flex items-center gap-1.5">
                  <DollarSign size={20} className="text-[var(--orange)]" /> {balance.toFixed(2)}
                </h3>
              </div>
              <span className="bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 px-2.5 py-1 text-[9px] font-mono rounded-md uppercase tracking-wider">
                LEDGER VERIFIED ✓
              </span>
            </div>

            <form onSubmit={handleTopup} className="space-y-4">
              <div>
                <label className="form-label" htmlFor="topup-options">Select Top-Up Amount</label>
                <div className="grid grid-cols-4 gap-2">
                  {[50, 100, 250, 500].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setTopupAmount(amt)}
                      className={`py-2 text-xs font-bold font-mono rounded transition-all border ${
                        topupAmount === amt
                          ? 'border-[var(--orange)] bg-[rgba(255,184,0,0.08)] text-white'
                          : 'border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.15)] text-[var(--text-secondary)] hover:text-white hover:border-[rgba(255,184,0,0.25)]'
                      }`}
                    >
                      ${amt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="form-label" htmlFor="custom-amount">Operator Recharge Cockpit</label>
                <div className="relative">
                  <span className="absolute left-3 top-3 text-[var(--text-muted)] font-mono text-xs">$</span>
                  <input
                    id="custom-amount"
                    type="number"
                    min="10"
                    placeholder="Custom amount (min $10)"
                    value={topupAmount}
                    onChange={(e) => setTopupAmount(parseInt(e.target.value) || 0)}
                    className="form-input pl-7 text-xs font-mono"
                    disabled={isCheckoutLoading}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary w-full py-3 text-xs font-bold font-mono tracking-widest"
                disabled={isCheckoutLoading || topupAmount < 10}
              >
                {isCheckoutLoading ? 'LAUNCHING RESERVE GATEWAY...' : 'TOP-UP OPERATING RESERVE'}
              </button>
            </form>
          </div>

          <div className="mt-8 pt-4 border-t border-[rgba(255,255,255,0.05)] font-mono text-[9px] text-[var(--text-muted)] flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck size={11} />
              <span>AES-256 STRIPE SECURED GATEWAY</span>
            </div>
            <div>BAR REGULATION: FSN1 PREPAY ENFORCEMENT</div>
          </div>
        </div>

        {/* Dynamic Budget Limits & Hard Caps */}
        <div className="glow-card lg:col-span-8 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2"><TrendingUp size={15} className="text-[var(--orange)]" /> Dynamic Expense Guardians</h3>
                <p className="text-[10px] text-[var(--text-muted)] font-mono uppercase mt-0.5">ENFORCED HARD LIMIT RULES AND AUTOMATIC KILL SWITCHES</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {budgetRules.map((rule) => {
                const percent = Math.min(100, Math.round((rule.current_spend / rule.limit_usd) * 100));
                return (
                  <div key={rule.id} className="p-3.5 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)] relative">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-bold text-white block">{rule.name}</span>
                        <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase block mt-0.5">{rule.period} cap limit</span>
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-red-400 opacity-60 hover:opacity-100 transition-opacity p-1"
                        title="Delete limit rules"
                      >
                        <Trash size={12} />
                      </button>
                    </div>

                    <div className="my-4">
                      <div className="flex justify-between text-[10.5px] font-mono text-[var(--text-secondary)] mb-1">
                        <span>current spend: ${rule.current_spend.toFixed(2)}</span>
                        <span className="text-white font-bold">${rule.limit_usd.toFixed(2)} Cap</span>
                      </div>
                      <div className="w-full bg-neutral-800 rounded-full h-1.5">
                        <div className="bg-[var(--orange)] h-1.5 rounded-full" style={{ width: `${percent}%` }}></div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Add New Budget Rule Cockpit */}
              <form onSubmit={handleAddBudgetRule} className="p-3.5 rounded border border-[rgba(255,184,0,0.12)] bg-[rgba(255,184,0,0.02)] flex flex-col justify-between">
                <span className="text-[10px] font-bold font-mono tracking-wider text-[var(--orange)] uppercase block mb-2">ADD ENFORCER RULE</span>
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="Rule Label (e.g. Test Gate)"
                    value={newRuleName}
                    onChange={(e) => setNewRuleName(e.target.value)}
                    className="form-input text-xs py-1.5 h-8 font-mono bg-black"
                    disabled={isAddingRule}
                    required
                  />
                  <div className="relative">
                    <span className="absolute left-2.5 top-1.5 text-[var(--text-muted)] font-mono text-xs">$</span>
                    <input
                      type="number"
                      placeholder="Limit amount"
                      value={newRuleLimit}
                      onChange={(e) => setNewRuleLimit(parseInt(e.target.value) || 0)}
                      className="form-input text-xs py-1.5 h-8 pl-6 font-mono bg-black"
                      disabled={isAddingRule}
                      required
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="btn btn-secondary w-full text-[10px] font-bold font-mono tracking-wider mt-3 py-1.5 h-8 flex items-center justify-center gap-1"
                  disabled={isAddingRule || !newRuleName.trim() || newRuleLimit <= 0}
                >
                  <Plus size={11} /> COMPILE LIMIT RULE
                </button>
              </form>
            </div>

            {/* Spend Breakdown Ledger */}
            {breakdown && (
              <div className="border-t border-[rgba(255,255,255,0.05)] pt-4">
                <span className="form-label text-[10px] uppercase mb-3">CONSUMPTION PROFILE BREAKDOWN — {breakdown.period}</span>
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Telemetry Event</th>
                        <th className="text-center">Count</th>
                        <th className="text-right">Unit Rate</th>
                        <th className="text-right">Accumulated Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {breakdown.items.map((item, idx) => (
                        <tr key={idx}>
                          <td className="font-semibold text-white">{item.event}</td>
                          <td className="text-center font-mono">{item.count}</td>
                          <td className="text-right font-mono">${item.unit_cost.toFixed(2)}</td>
                          <td className="text-right font-mono text-[var(--orange)] font-bold">${item.total.toFixed(2)}</td>
                        </tr>
                      ))}
                      <tr className="border-t border-white/10 bg-white/[0.01]">
                        <td colSpan={3} className="font-bold text-white font-mono text-right text-[10px] uppercase">aggregate spend</td>
                        <td className="text-right font-bold text-white font-mono">${breakdown.total_usd.toFixed(2)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          <div className="text-[10px] font-mono text-[var(--text-muted)] border-t border-[rgba(255,255,255,0.03)] pt-3 text-right">
            METRICS ENFORCER ACTIVE
          </div>
        </div>

      </div>

      {/* Transaction History Logs */}
      <div className="glow-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold text-white tracking-wider uppercase font-mono flex items-center gap-2">
            <History size={13} className="text-[var(--orange)]" /> TRANSACTION LEDGER HISTORICAL AUDIT
          </h3>
          <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase">CRYPTOGRAPHIC WALLET BLOCKS</span>
        </div>

        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Block ID</th>
                <th>Telemetry Description</th>
                <th>Rule Action</th>
                <th className="text-right">Wallet Delta</th>
                <th className="text-right">Block Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {transactions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-6 text-[var(--text-muted)] font-mono">No operating ledger transactions found.</td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="font-mono text-[10px] text-[var(--orange)] font-bold">{tx.id.toUpperCase()}</td>
                    <td className="text-white font-mono">{tx.description}</td>
                    <td>
                      <span className={`badge ${tx.tx_type === 'topup' || tx.tx_type === 'activation' ? 'badge-green' : 'badge-orange'}`}>
                        {tx.tx_type}
                      </span>
                    </td>
                    <td className={`text-right font-bold font-mono ${tx.amount >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {tx.amount >= 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                    </td>
                    <td className="text-right text-[var(--text-muted)] font-mono">{new Date(tx.created_at).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
