import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  CreditCard, 
  TrendingUp, 
  DollarSign, 
  Calendar, 
  AlertCircle, 
  CheckCircle, 
  ArrowUpRight,
  ArrowDownRight,
  Users,
  Activity,
  Download,
  ExternalLink,
  Zap,
  Shield,
  Star,
  ChevronRight,
  Loader
} from 'lucide-react';

interface PricingTier {
  id: string;
  name: string;
  display_name: string;
  description: string;
  tier_level: number;
  monthly_price: number;
  annual_price: number;
  currency: string;
  features: { [key: string]: any };
  limits: { [key: string]: any };
  is_active: boolean;
  is_public: boolean;
}

interface CurrentPricing {
  current_tier: PricingTier | null;
  subscription: {
    id: string | null;
    status: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  };
  usage: Array<{
    metric_name: string;
    metric_value: number;
    metric_unit: string;
    tier_limit: number | null;
    usage_percentage: number;
    period_start: string;
    period_end: string;
  }>;
}

interface WalletTransaction {
  id: string;
  amount: number;
  type: string;
  status: string;
  description: string;
  created_at: string;
}

export const BillingPage: React.FC = () => {
  const [currentPricing, setCurrentPricing] = useState<CurrentPricing | null>(null);
  const [pricingTiers, setPricingTiers] = useState<PricingTier[]>([]);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    try {
      const [pricingData, currentData, transactionsData] = await Promise.all([
        api('/api/v1/pricing/tiers'),
        api('/api/v1/pricing/current'),
        api('/api/v1/billing/wallet/transactions')
      ]);

      setPricingTiers(pricingData.tiers || []);
      setCurrentPricing(currentData);
      setTransactions(transactionsData.transactions || []);
    } catch (error) {
      console.error('Failed to load billing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const initiateUpgrade = async (tierId: string) => {
    setUpgrading(tierId);
    try {
      const response = await api('/api/v1/pricing/upgrade', {
        method: 'POST',
        body: JSON.stringify({
          tier_id: tierId,
          billing_cycle: billingCycle,
          upgrade_type: 'immediate'
        })
      });

      if (response.checkout_url) {
        window.open(response.checkout_url, '_blank');
      }
    } catch (error) {
      console.error('Failed to initiate upgrade:', error);
    } finally {
      setUpgrading(null);
    }
  };

  const formatPrice = (price: number, cycle: 'monthly' | 'annual') => {
    const actualPrice = cycle === 'annual' ? price * 12 * 0.8 : price; // 20% discount for annual
    return `$${actualPrice.toFixed(2)}/${cycle === 'annual' ? 'year' : 'month'}`;
  };

  const getUsageIcon = (metricName: string) => {
    switch (metricName) {
      case 'api_calls': return Activity;
      case 'agents': return Users;
      case 'storage': return Download;
      default: return Activity;
    }
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'credit': return ArrowDownRight;
      case 'debit': return ArrowUpRight;
      default: return DollarSign;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-gray-400">Loading billing information...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Billing & Plans</h1>
          <p className="text-gray-400">Manage your subscription and payment methods</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'annual' : 'monthly')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              billingCycle === 'annual'
                ? 'bg-green-500 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Annual (Save 20%)
          </button>
        </div>
      </div>

      {/* Current Plan Overview */}
      {currentPricing?.current_tier && (
        <div className="bg-gradient-to-r from-orange-500/20 to-orange-600/20 border border-orange-500/30 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white mb-2">
                Current Plan: {currentPricing.current_tier.display_name}
              </h2>
              <p className="text-gray-300 mb-4">{currentPricing.current_tier.description}</p>
              <div className="flex items-center gap-4 text-sm text-gray-300">
                <span className="flex items-center gap-1">
                  <Calendar size={14} />
                  {currentPricing.subscription.status === 'active' ? 'Active' : 'Inactive'}
                </span>
                {currentPricing.subscription.current_period_end && (
                  <span>
                    Renews {new Date(currentPricing.subscription.current_period_end).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-orange-400 mb-2">
                {formatPrice(currentPricing.current_tier.monthly_price, billingCycle)}
              </div>
              {currentPricing.subscription.cancel_at_period_end && (
                <div className="flex items-center gap-1 text-yellow-400 text-sm">
                  <AlertCircle size={14} />
                  Cancels at period end
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Usage Overview */}
      {currentPricing?.usage && currentPricing.usage.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity size={18} />
              Usage Overview
            </h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {currentPricing.usage.slice(0, 4).map((usage, index) => {
                const Icon = getUsageIcon(usage.metric_name);
                const percentage = usage.tier_limit ? (usage.metric_value / usage.tier_limit) * 100 : 0;
                
                return (
                  <div key={index} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <Icon className="text-orange-400" size={20} />
                      <span className="text-xs text-gray-400">{usage.metric_unit}</span>
                    </div>
                    <div className="text-2xl font-bold text-white mb-1">
                      {usage.metric_value.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      {usage.tier_limit ? `${usage.tier_limit.toLocaleString()} limit` : 'Unlimited'}
                    </div>
                    {usage.tier_limit && (
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            percentage > 90 ? 'bg-red-500' : percentage > 70 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Available Plans */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Available Plans</h2>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {pricingTiers
              .filter(tier => tier.is_active && tier.is_public)
              .sort((a, b) => a.tier_level - b.tier_level)
              .map(tier => {
                const isCurrentPlan = currentPricing?.current_tier?.id === tier.id;
                const isUpgrade = currentPricing?.current_tier && tier.tier_level > currentPricing.current_tier.tier_level;
                
                return (
                  <div 
                    key={tier.id} 
                    className={`bg-gray-900 rounded-lg border ${
                      isCurrentPlan 
                        ? 'border-orange-500 ring-2 ring-orange-500/20' 
                        : isUpgrade 
                        ? 'border-green-500/50 hover:border-green-500' 
                        : 'border-gray-700'
                    } transition-all`}
                  >
                    {isCurrentPlan && (
                      <div className="bg-orange-500 text-white text-center py-2 text-sm font-semibold">
                        Current Plan
                      </div>
                    )}
                    
                    <div className="p-6">
                      <h3 className="text-xl font-bold text-white mb-2">{tier.display_name}</h3>
                      <p className="text-gray-400 text-sm mb-4">{tier.description}</p>
                      
                      <div className="mb-6">
                        <div className="text-3xl font-bold text-white mb-1">
                          {formatPrice(tier.monthly_price, billingCycle)}
                        </div>
                        {billingCycle === 'annual' && (
                          <div className="text-sm text-green-400">
                            Save ${(tier.monthly_price * 12 * 0.2).toFixed(2)}/year
                          </div>
                        )}
                      </div>
                      
                      <div className="space-y-3 mb-6">
                        {Object.entries(tier.features).slice(0, 5).map(([key, value]) => {
                          if (typeof value === 'boolean' && value) {
                            return (
                              <div key={key} className="flex items-center gap-2 text-sm text-gray-300">
                                <CheckCircle size={14} className="text-green-400" />
                                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                            );
                          }
                          return null;
                        })}
                      </div>
                      
                      <button
                        onClick={() => initiateUpgrade(tier.id)}
                        disabled={isCurrentPlan || upgrading === tier.id}
                        className={`w-full py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                          isCurrentPlan
                            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            : isUpgrade
                            ? 'bg-green-500 text-white hover:bg-green-600'
                            : 'bg-orange-500 text-white hover:bg-orange-600'
                        }`}
                      >
                        {upgrading === tier.id ? (
                          <>
                            <Loader size={16} className="animate-spin" />
                            Processing...
                          </>
                        ) : isCurrentPlan ? (
                          'Current Plan'
                        ) : isUpgrade ? (
                          <>
                            <ArrowUpRight size={16} />
                            Upgrade Now
                          </>
                        ) : (
                          <>
                            <Zap size={16} />
                            Get Started
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* Recent Transactions */}
      {transactions.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <DollarSign size={18} />
              Recent Transactions
            </h2>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {transactions.slice(0, 10).map(transaction => {
                const Icon = getTransactionIcon(transaction.type);
                const isCredit = transaction.type === 'credit';
                
                return (
                  <div key={transaction.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          isCredit ? 'bg-green-500/20' : 'bg-red-500/20'
                        }`}>
                          <Icon size={18} className={isCredit ? 'text-green-400' : 'text-red-400'} />
                        </div>
                        <div>
                          <div className="text-white font-medium">{transaction.description}</div>
                          <div className="text-sm text-gray-400">
                            {new Date(transaction.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-semibold ${
                          isCredit ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {isCredit ? '+' : '-'}${Math.abs(transaction.amount).toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-400 capitalize">{transaction.status}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
