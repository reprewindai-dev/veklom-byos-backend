import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi, 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  Users,
  Globe,
  Clock,
  Zap,
  Shield,
  Database,
  RefreshCw,
  Filter,
  Calendar,
  BarChart3,
  LineChart,
  PieChart,
  Eye,
  AlertCircle
} from 'lucide-react';

interface SystemHealth {
  status: string;
  score: number;
  components: { [key: string]: any };
  timestamp: string;
}

interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_mbps: number;
  active_connections: number;
  requests_per_second: number;
  avg_latency_ms: number;
  error_rate: number;
  total_requests: number;
  memory_available_gb: number;
  disk_free_gb: number;
}

interface Alert {
  id: string;
  name: string;
  description: string;
  severity: string;
  status: string;
  metric_name: string;
  threshold_value: number;
  current_value: number;
  triggered_at: string;
  resolved_at?: string;
  metadata: any;
}

interface PerformanceLog {
  id: string;
  endpoint: string;
  method: string;
  status_code: number;
  duration_ms: number;
  user_id: string;
  timestamp: string;
  metadata: any;
}

export const MonitoringDashboardPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [performanceLogs, setPerformanceLogs] = useState<PerformanceLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedTab, setSelectedTab] = useState('overview');

  useEffect(() => {
    loadMonitoringData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadMonitoringData, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const loadMonitoringData = async () => {
    try {
      setRefreshing(true);
      const hours = timeRange === '1h' ? 1 : timeRange === '24h' ? 24 : 168;
      
      const [healthData, metricsData, alertsData, performanceData] = await Promise.all([
        api('/api/v1/monitoring/health'),
        api(`/api/v1/monitoring/metrics?hours=${hours}`),
        api('/api/v1/monitoring/alerts'),
        api(`/api/v1/monitoring/performance?hours=${hours}`)
      ]);

      setHealth(healthData);
      setMetrics(metricsData);
      setAlerts(alertsData.alerts || []);
      setPerformanceLogs(performanceData.logs || []);
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await api(`/api/v1/monitoring/alerts/${alertId}/resolve`, {
        method: 'POST'
      });
      loadMonitoringData();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-400';
      case 'degraded': return 'text-yellow-400';
      case 'unhealthy': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500/20 border-green-500/30';
      case 'degraded': return 'bg-yellow-500/20 border-yellow-500/30';
      case 'unhealthy': return 'bg-red-500/20 border-red-500/30';
      default: return 'bg-gray-800 border-gray-700';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'info': return 'text-blue-400';
      case 'warning': return 'text-yellow-400';
      case 'error': return 'text-red-400';
      case 'critical': return 'text-purple-400';
      default: return 'text-gray-400';
    }
  };

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'info': return 'bg-blue-500/20';
      case 'warning': return 'bg-yellow-500/20';
      case 'error': return 'bg-red-500/20';
      case 'critical': return 'bg-purple-500/20';
      default: return 'bg-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-gray-400">Loading monitoring data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Monitoring Dashboard</h1>
          <p className="text-gray-400">Real-time system health and performance metrics</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-orange-500"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
          <button
            onClick={loadMonitoringData}
            disabled={refreshing}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white hover:bg-gray-700 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* System Health Overview */}
      {health && (
        <div className={`border rounded-lg p-6 ${getStatusBg(health.status)}`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity size={18} />
              System Health
            </h2>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${getStatusColor(health.status)}`}>
                {health.score}%
              </span>
              <span className={`px-2 py-1 rounded text-sm font-medium ${getStatusBg(health.status)} ${getStatusColor(health.status)}`}>
                {health.status.toUpperCase()}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(health.components).map(([name, component]) => (
              <div key={name} className="bg-gray-800/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white capitalize">{name}</span>
                  <CheckCircle size={14} className={getStatusColor(component.status)} />
                </div>
                <div className="text-xs text-gray-400">
                  {component.latency_ms && `Latency: ${component.latency_ms}ms`}
                  {component.error_rate && ` • Error Rate: ${(component.error_rate * 100).toFixed(2)}%`}
                  {component.usage_percent && ` • Usage: ${component.usage_percent}%`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Cpu className="text-orange-400" size={20} />
              <span className="text-xs text-gray-400">CPU</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.cpu_percent.toFixed(1)}%</div>
            <div className="text-xs text-gray-400">Usage</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Database className="text-blue-400" size={20} />
              <span className="text-xs text-gray-400">Memory</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.memory_percent.toFixed(1)}%</div>
            <div className="text-xs text-gray-400">{metrics.memory_available_gb.toFixed(1)}GB free</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <HardDrive className="text-green-400" size={20} />
              <span className="text-xs text-gray-400">Disk</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.disk_percent.toFixed(1)}%</div>
            <div className="text-xs text-gray-400">{metrics.disk_free_gb.toFixed(1)}GB free</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Wifi className="text-purple-400" size={20} />
              <span className="text-xs text-gray-400">Network</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.network_mbps.toFixed(1)}</div>
            <div className="text-xs text-gray-400">Mbps</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Activity className="text-yellow-400" size={20} />
              <span className="text-xs text-gray-400">Requests</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.requests_per_second.toFixed(1)}</div>
            <div className="text-xs text-gray-400">per second</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Clock className="text-red-400" size={20} />
              <span className="text-xs text-gray-400">Latency</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.avg_latency_ms.toFixed(0)}</div>
            <div className="text-xs text-gray-400">ms average</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <Globe className="text-cyan-400" size={20} />
              <span className="text-xs text-gray-400">Connections</span>
            </div>
            <div className="text-2xl font-bold text-white">{metrics.active_connections}</div>
            <div className="text-xs text-gray-400">active</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="text-orange-400" size={20} />
              <span className="text-xs text-gray-400">Error Rate</span>
            </div>
            <div className="text-2xl font-bold text-white">{(metrics.error_rate * 100).toFixed(2)}%</div>
            <div className="text-xs text-gray-400">of requests</div>
          </div>
        </div>
      )}

      {/* Active Alerts */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <AlertTriangle size={18} />
            Active Alerts
            {alerts.filter(a => a.status === 'active').length > 0 && (
              <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">
                {alerts.filter(a => a.status === 'active').length}
              </span>
            )}
          </h2>
        </div>
        <div className="p-4">
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <CheckCircle className="mx-auto mb-4" size={48} />
              <p>No active alerts</p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 10).map(alert => (
                <div key={alert.id} className={`border rounded-lg p-4 ${getSeverityBg(alert.severity)}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertCircle size={16} className={getSeverityColor(alert.severity)} />
                        <span className="font-medium text-white">{alert.name}</span>
                        <span className={`px-2 py-1 text-xs rounded ${getSeverityBg(alert.severity)} ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                        {alert.status === 'resolved' && (
                          <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                            Resolved
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-300 mb-2">{alert.description}</p>
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        <span>{alert.metric_name}: {alert.current_value} (threshold: {alert.threshold_value})</span>
                        <span>Triggered {new Date(alert.triggered_at).toLocaleString()}</span>
                      </div>
                    </div>
                    {alert.status === 'active' && (
                      <button
                        onClick={() => resolveAlert(alert.id)}
                        className="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600 transition-colors"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Performance Logs */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <BarChart3 size={18} />
            Recent Performance
          </h2>
        </div>
        <div className="p-4">
          {performanceLogs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <BarChart3 className="mx-auto mb-4" size={48} />
              <p>No performance data available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {performanceLogs.slice(0, 10).map(log => (
                <div key={log.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-medium text-white">{log.method} {log.endpoint}</span>
                        <span className={`px-2 py-1 text-xs rounded ${
                          log.status_code < 400 
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {log.status_code}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                          <Clock size={14} />
                          {log.duration_ms.toFixed(0)}ms
                        </span>
                        <span>{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-semibold ${
                        log.duration_ms < 100 ? 'text-green-400' : 
                        log.duration_ms < 500 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {log.duration_ms.toFixed(0)}ms
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
