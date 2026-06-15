import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Shield, 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Zap, 
  Eye, 
  Lock,
  Database,
  GitBranch,
  DollarSign,
  Users,
  Settings,
  ChevronDown,
  ChevronUp,
  RefreshCw
} from 'lucide-react';

interface AuthorityStatus {
  identity: {
    operator_id: string;
    workspace_id: string;
    status: 'active' | 'pending' | 'suspended';
    verified: boolean;
  };
  policy: {
    enforcement_level: 'strict' | 'moderate' | 'permissive';
    active_rules: number;
    violations_today: number;
    last_violation?: string;
  };
  execution: {
    active_runs: number;
    total_executions_today: number;
    success_rate: number;
    avg_response_time: number;
  };
  evidence: {
    total_proofs: number;
    verified_proofs: number;
    last_proof: string;
    chain_integrity: 'valid' | 'warning' | 'invalid';
  };
  cost: {
    daily_spend: number;
    monthly_budget: number;
    budget_utilization: number;
    cost_per_execution: number;
  };
  risk: {
    overall_score: number;
    threat_level: 'low' | 'medium' | 'high' | 'critical';
    active_alerts: number;
    last_assessment: string;
  };
}

interface AuthorityPanelHUDProps {
  className?: string;
  compact?: boolean;
}

export const AuthorityPanelHUD: React.FC<AuthorityPanelHUDProps> = ({ 
  className = '', 
  compact = false 
}) => {
  const [authorityStatus, setAuthorityStatus] = useState<AuthorityStatus | null>(null);
  const [isExpanded, setIsExpanded] = useState(!compact);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchAuthorityStatus = async () => {
    try {
      const [identityRes, policyRes, executionRes, evidenceRes, costRes, riskRes] = await Promise.allSettled([
        api('/api/v1/pgl/profile'),
        api('/api/v1/authority/runs/summary'),
        api('/api/v1/authority/executions/summary'),
        api('/api/v1/evidence/summary'),
        api('/api/v1/billing/summary'),
        api('/api/v1/security/risk-assessment')
      ]);

      // Mock data for demonstration
      const mockStatus: AuthorityStatus = {
        identity: {
          operator_id: 'operator_abc123',
          workspace_id: 'workspace_def456',
          status: 'active',
          verified: true
        },
        policy: {
          enforcement_level: 'strict',
          active_rules: 12,
          violations_today: 0,
          last_violation: undefined
        },
        execution: {
          active_runs: 3,
          total_executions_today: 47,
          success_rate: 98.5,
          avg_response_time: 245
        },
        evidence: {
          total_proofs: 1247,
          verified_proofs: 1245,
          last_proof: '2026-01-15T10:30:00Z',
          chain_integrity: 'valid'
        },
        cost: {
          daily_spend: 23.45,
          monthly_budget: 500.00,
          budget_utilization: 68.2,
          cost_per_execution: 0.12
        },
        risk: {
          overall_score: 92,
          threat_level: 'low',
          active_alerts: 0,
          last_assessment: '2026-01-15T09:00:00Z'
        }
      };

      setAuthorityStatus(mockStatus);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch authority status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuthorityStatus();
    const interval = setInterval(fetchAuthorityStatus, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'valid':
      case 'low':
        return 'text-emerald-400';
      case 'pending':
      case 'moderate':
      case 'medium':
        return 'text-yellow-400';
      case 'suspended':
      case 'strict':
      case 'high':
        return 'text-orange-400';
      case 'invalid':
      case 'critical':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'valid':
      case 'low':
        return <CheckCircle size={12} />;
      case 'pending':
      case 'moderate':
      case 'medium':
        return <Clock size={12} />;
      case 'suspended':
      case 'strict':
      case 'high':
        return <AlertTriangle size={12} />;
      case 'invalid':
      case 'critical':
        return <AlertTriangle size={12} />;
      default:
        return <Activity size={12} />;
    }
  };

  if (isLoading) {
    return (
      <div className={`bg-neutral-900/80 border border-neutral-800 rounded-lg p-4 backdrop-blur-sm ${className}`}>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <RefreshCw size={12} className="animate-spin" />
          Loading Authority Panel...
        </div>
      </div>
    );
  }

  if (!authorityStatus) {
    return (
      <div className={`bg-red-500/10 border border-red-500/30 rounded-lg p-4 backdrop-blur-sm ${className}`}>
        <div className="flex items-center gap-2 text-xs text-red-400">
          <AlertTriangle size={12} />
          Authority Panel unavailable
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-neutral-900/80 border border-neutral-800 rounded-lg backdrop-blur-sm ${className}`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-neutral-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Shield className="text-orange-500" size={16} />
          <span className="text-xs font-semibold text-white">Authority Panel</span>
          <div className={`flex items-center gap-1 ${getStatusColor(authorityStatus.identity.status)}`}>
            {getStatusIcon(authorityStatus.identity.status)}
            <span className="text-xs capitalize">{authorityStatus.identity.status}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-gray-500">
            {lastUpdate.toLocaleTimeString()}
          </span>
          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-neutral-800">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 p-4">
            
            {/* Identity */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <Users size={10} />
                IDENTITY
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${authorityStatus.identity.verified ? 'bg-emerald-400' : 'bg-yellow-400'}`}></div>
                  <span className="text-xs text-white">
                    {authorityStatus.identity.operator_id.slice(0, 12)}...
                  </span>
                </div>
                <div className="text-[9px] text-gray-500">
                  WS: {authorityStatus.identity.workspace_id.slice(0, 8)}...
                </div>
              </div>
            </div>

            {/* Policy */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <Shield size={10} />
                POLICY
              </div>
              <div className="space-y-1">
                <div className={`text-xs capitalize ${getStatusColor(authorityStatus.policy.enforcement_level)}`}>
                  {authorityStatus.policy.enforcement_level}
                </div>
                <div className="text-[9px] text-gray-500">
                  {authorityStatus.policy.active_rules} rules
                </div>
                {authorityStatus.policy.violations_today > 0 && (
                  <div className="text-[9px] text-red-400">
                    {authorityStatus.policy.violations_today} violations
                  </div>
                )}
              </div>
            </div>

            {/* Execution */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <Zap size={10} />
                EXECUTION
              </div>
              <div className="space-y-1">
                <div className="text-xs text-white">
                  {authorityStatus.execution.active_runs} active
                </div>
                <div className="text-[9px] text-gray-500">
                  {authorityStatus.execution.success_rate}% success
                </div>
                <div className="text-[9px] text-gray-500">
                  {authorityStatus.execution.avg_response_time}ms avg
                </div>
              </div>
            </div>

            {/* Evidence */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <Database size={10} />
                EVIDENCE
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(authorityStatus.evidence.chain_integrity)}`}></div>
                  <span className="text-xs text-white">
                    {authorityStatus.evidence.total_proofs} proofs
                  </span>
                </div>
                <div className="text-[9px] text-gray-500">
                  {authorityStatus.evidence.verified_proofs} verified
                </div>
              </div>
            </div>

            {/* Cost */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <DollarSign size={10} />
                COST
              </div>
              <div className="space-y-1">
                <div className="text-xs text-white">
                  ${authorityStatus.cost.daily_spend.toFixed(2)}
                </div>
                <div className="text-[9px] text-gray-500">
                  {authorityStatus.cost.budget_utilization}% budget
                </div>
                <div className="text-[9px] text-gray-500">
                  ${authorityStatus.cost.cost_per_execution}/exec
                </div>
              </div>
            </div>

            {/* Risk */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400">
                <Eye size={10} />
                RISK
              </div>
              <div className="space-y-1">
                <div className={`text-xs capitalize ${getStatusColor(authorityStatus.risk.threat_level)}`}>
                  {authorityStatus.risk.threat_level}
                </div>
                <div className="text-xs text-white">
                  Score: {authorityStatus.risk.overall_score}
                </div>
                {authorityStatus.risk.active_alerts > 0 && (
                  <div className="text-[9px] text-orange-400">
                    {authorityStatus.risk.active_alerts} alerts
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Quick Actions */}
          <div className="border-t border-neutral-800 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors">
                  <Settings size={10} />
                  Settings
                </button>
                <button className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors">
                  <GitBranch size={10} />
                  Lineage
                </button>
                <button className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors">
                  <Lock size={10} />
                  Security
                </button>
              </div>
              <button 
                onClick={fetchAuthorityStatus}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
              >
                <RefreshCw size={10} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
