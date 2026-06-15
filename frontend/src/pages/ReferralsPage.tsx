import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Users, 
  Gift, 
  TrendingUp, 
  DollarSign, 
  Copy, 
  ExternalLink,
  Calendar,
  Award,
  Target
} from 'lucide-react';

interface ReferralCode {
  id: string;
  code: string;
  reward_type: string;
  reward_value: number;
  max_uses: number;
  uses_count: number;
  created_at: string;
}

interface Referral {
  id: string;
  referral_code_id: string;
  referred_user_id: string;
  status: string;
  reward_amount: number;
  reward_type: string;
  created_at: string;
  completed_at?: string;
}

interface ReferralPayout {
  id: string;
  referral_id: string;
  amount: number;
  status: string;
  created_at: string;
  processed_at?: string;
}

export const ReferralsPage: React.FC = () => {
  const [referralCodes, setReferralCodes] = useState<ReferralCode[]>([]);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [payouts, setPayouts] = useState<ReferralPayout[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => {
    loadReferralData();
  }, []);

  const loadReferralData = async () => {
    try {
      const [codesData, referralsData, payoutsData, analyticsData] = await Promise.all([
        api('/api/v1/referrals/codes'),
        api('/api/v1/referrals'),
        api('/api/v1/referrals/payouts'),
        api('/api/v1/referrals/analytics')
      ]);

      setReferralCodes(codesData.codes || []);
      setReferrals(referralsData.referrals || []);
      setPayouts(payoutsData.payouts || []);
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Failed to load referral data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createReferralCode = async () => {
    try {
      const response = await api('/api/v1/referrals/codes', {
        method: 'POST',
        body: JSON.stringify({
          reward_type: 'percentage',
          reward_value: 10,
          max_uses: 100
        })
      });
      
      if (response.code) {
        setReferralCodes([...referralCodes, response]);
      }
    } catch (error) {
      console.error('Failed to create referral code:', error);
    }
  };

  const copyToClipboard = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-gray-400">Loading referral data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Referral Program</h1>
          <p className="text-gray-400">Earn rewards by referring new users to Veklom</p>
        </div>
        <button
          onClick={createReferralCode}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
        >
          <Gift size={16} />
          Create Referral Code
        </button>
      </div>

      {/* Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Users className="text-orange-400" size={20} />
              <span className="text-xs text-gray-400">Total</span>
            </div>
            <div className="text-2xl font-bold text-white">{analytics.total_referrals || 0}</div>
            <div className="text-xs text-gray-400">Referrals</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="text-green-400" size={20} />
              <span className="text-xs text-gray-400">Completed</span>
            </div>
            <div className="text-2xl font-bold text-white">{analytics.completed_referrals || 0}</div>
            <div className="text-xs text-gray-400">Conversions</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <DollarSign className="text-blue-400" size={20} />
              <span className="text-xs text-gray-400">Earned</span>
            </div>
            <div className="text-2xl font-bold text-white">${analytics.total_earned || 0}</div>
            <div className="text-xs text-gray-400">Total Rewards</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Target className="text-purple-400" size={20} />
              <span className="text-xs text-gray-400">Pending</span>
            </div>
            <div className="text-2xl font-bold text-white">${analytics.pending_rewards || 0}</div>
            <div className="text-xs text-gray-400">Pending Rewards</div>
          </div>
        </div>
      )}

      {/* Referral Codes */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Gift size={18} />
            Your Referral Codes
          </h2>
        </div>
        <div className="p-4">
          {referralCodes.length === 0 ? (
            <div className="text-center py-8">
              <Gift className="mx-auto text-gray-500 mb-4" size={48} />
              <p className="text-gray-400 mb-4">No referral codes yet</p>
              <button
                onClick={createReferralCode}
                className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
              >
                Create Your First Code
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {referralCodes.map((code) => (
                <div key={code.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-mono text-lg text-orange-400">{code.code}</span>
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                          {code.reward_type === 'percentage' ? `${code.reward_value}%` : `$${code.reward_value}`}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                          <Users size={14} />
                          {code.uses_count}/{code.max_uses} uses
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar size={14} />
                          Created {new Date(code.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => copyToClipboard(code.code)}
                      className="px-3 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors flex items-center gap-2"
                    >
                      {copiedCode === code.code ? (
                        <>
                          <Award size={14} />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy size={14} />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Referrals */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Users size={18} />
            Recent Referrals
          </h2>
        </div>
        <div className="p-4">
          {referrals.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No referrals yet. Share your referral code to start earning!
            </div>
          ) : (
            <div className="space-y-3">
              {referrals.slice(0, 10).map((referral) => (
                <div key={referral.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-white">User {referral.referred_user_id.slice(0, 8)}...</span>
                        <span className={`px-2 py-1 text-xs rounded ${
                          referral.status === 'completed' 
                            ? 'bg-green-500/20 text-green-400'
                            : referral.status === 'pending'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {referral.status}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400">
                        Referred {new Date(referral.created_at).toLocaleDateString()}
                        {referral.completed_at && (
                          <span> • Completed {new Date(referral.completed_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    {referral.reward_amount > 0 && (
                      <div className="text-right">
                        <div className="text-green-400 font-semibold">
                          +${referral.reward_amount}
                        </div>
                        <div className="text-xs text-gray-400">
                          {referral.reward_type}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Payouts */}
      {payouts.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <DollarSign size={18} />
              Payout History
            </h2>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {payouts.slice(0, 5).map((payout) => (
                <div key={payout.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-semibold">${payout.amount}</div>
                      <div className="text-sm text-gray-400">
                        {new Date(payout.created_at).toLocaleDateString()}
                        {payout.processed_at && (
                          <span> • Processed {new Date(payout.processed_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <span className={`px-3 py-1 text-sm rounded ${
                      payout.status === 'processed'
                        ? 'bg-green-500/20 text-green-400'
                        : payout.status === 'pending'
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {payout.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
