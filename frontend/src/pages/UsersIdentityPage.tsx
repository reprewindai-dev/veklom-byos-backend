import React, { useState, useEffect } from 'react';
import { Users, RefreshCw, AlertCircle, ShieldAlert, Clock } from 'lucide-react';
import { api } from '../api/client';

export const UsersIdentityPage: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [wsRes, membersRes] = await Promise.allSettled([
        api('/workspace/me'),
        api('/workspace/members'),
      ]);
      if (wsRes.status === 'fulfilled') setStats(wsRes.value);
      if (membersRes.status === 'fulfilled') setMembers(Array.isArray(membersRes.value) ? membersRes.value : membersRes.value?.members || []);
    } catch {
      setError('Could not load user data.');
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
            <Users size={18} className="text-[var(--orange)] animate-pulse" /> Users & Identity
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">User roster, roles, active sessions, security events, and access control.</p>
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

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Users', value: stats?.member_count ?? '—', icon: Users, color: 'text-white' },
          { label: 'Online Now', value: stats?.online_count ?? '—', icon: Clock, color: 'text-emerald-400' },
          { label: 'Active Sessions', value: stats?.session_count ?? '—', icon: ShieldAlert, color: 'text-[var(--orange)]' },
          { label: 'Security Events', value: stats?.security_events ?? '—', icon: AlertCircle, color: 'text-red-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glow-card p-4">
            <span className="block font-mono text-[10px] uppercase text-[var(--text-secondary)]">{label}</span>
            <span className={`mt-2 block font-mono text-xl font-bold ${color}`}>{value}</span>
          </div>
        ))}
      </div>

      {/* Members table */}
      <div className="glow-card">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 border-b border-white/5 pb-2">User Roster</h3>
        {loading ? (
          <p className="text-xs font-mono text-[var(--text-muted)]">Loading...</p>
        ) : members.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-white/5 text-[var(--text-muted)] text-[10px] uppercase">
                  <th className="text-left pb-2 pr-4">User</th>
                  <th className="text-left pb-2 pr-4">Role</th>
                  <th className="text-left pb-2 pr-4">Status</th>
                  <th className="text-left pb-2">Joined</th>
                </tr>
              </thead>
              <tbody className="space-y-1">
                {members.map((m: any, i: number) => (
                  <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                    <td className="py-2 pr-4 text-white">{m.email || m.username || `User ${i + 1}`}</td>
                    <td className="py-2 pr-4 text-[var(--text-secondary)]">{m.role || 'MEMBER'}</td>
                    <td className="py-2 pr-4">
                      <span className="text-[8px] font-bold uppercase border rounded px-1.5 py-0.5 text-emerald-400 border-emerald-500/30 bg-emerald-500/10">ACTIVE</span>
                    </td>
                    <td className="py-2 text-[var(--text-muted)]">{m.created_at?.slice(0, 10) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs font-mono text-[var(--text-muted)]">No members returned. Requires workspace configuration.</p>
        )}
      </div>
    </div>
  );
};
