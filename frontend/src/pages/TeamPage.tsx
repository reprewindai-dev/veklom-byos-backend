import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { UserCheck, Plus, Shield, RefreshCw, Send, Check } from 'lucide-react';

export const TeamPage: React.FC = () => {
  const [members, setMembers] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('developer');
  const [subError, setSubError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  const fetchMembers = async () => {
    setIsLoading(true);
    setSubError('');
    try {
      const res = await api('/workspace/members');
      setMembers(res);
    } catch (err: any) {
      setSubError(err.message || 'Failed to sync members list.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setSubError('');
    setSuccessMsg('');
    setIsSending(true);

    try {
      const res = await api('/workspace/members/invite', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail, role: inviteRole })
      });
      setSuccessMsg(res.message || `Invitation successfully sent to ${inviteEmail}.`);
      setInviteEmail('');
      
      // refresh roster
      fetchMembers();
    } catch (err: any) {
      setSubError(err.message || 'Invitation transit failed.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-3">
            <UserCheck size={18} className="text-[var(--orange)] animate-pulse" /> Team Cockpit
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Manage operator roles, credentials, and access credentials within this tenant perimeter.</p>
        </div>
        <div>
          <button 
            onClick={fetchMembers} 
            className="btn btn-secondary px-3 py-1.5 text-xs font-mono tracking-wider flex items-center gap-1.5"
            disabled={isLoading}
          >
            <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
            SYNC ROSTER
          </button>
        </div>
      </div>

      {subError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded font-mono">
          {subError}
        </div>
      )}

      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded font-mono flex items-center gap-2">
          <Check size={14} className="text-emerald-400" />
          {successMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Invitation Panel */}
        <div className="glow-card lg:col-span-4 self-start bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
            <Plus size={14} className="text-[var(--orange)]" /> PROVISE OPERATOR ACCESS
          </h3>
          <form onSubmit={handleInviteSubmit} className="space-y-4">
            <div>
              <label className="form-label" htmlFor="invite-email">Operator Email</label>
              <input
                id="invite-email"
                type="email"
                placeholder="developer@veklom.perimeter"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="form-input text-xs font-mono"
                required
              />
            </div>
            <div>
              <label className="form-label" htmlFor="invite-role">Permitted Security Role</label>
              <select
                id="invite-role"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="form-input text-xs font-mono bg-neutral-950 border-white/5 cursor-pointer text-white"
              >
                <option value="owner">Owner (Full Operations)</option>
                <option value="developer">Developer (Playground & Pipelines)</option>
                <option value="auditor">Auditor (Compliance & Vault)</option>
                <option value="viewer">Viewer (Observability Only)</option>
              </select>
            </div>
            <button 
              type="submit" 
              className="btn btn-primary w-full py-2.5 text-xs font-bold font-mono tracking-wider flex items-center justify-center gap-1.5"
              disabled={isSending}
            >
              {isSending ? (
                <>
                  <RefreshCw size={13} className="animate-spin" /> PROVISIONING ACCESS...
                </>
              ) : (
                <>
                  <Send size={13} /> SECURE INVITE
                </>
              )}
            </button>
          </form>
        </div>

        {/* Members Roster List */}
        <div className="glow-card lg:col-span-8 bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
            <UserCheck size={14} className="text-[var(--orange)]" /> ACTIVE TENANT ROSTER
          </h3>
          
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-xs font-mono text-[var(--text-secondary)]">
              <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-spin">
                <circle cx="50" cy="50" r="40" stroke="rgba(255,184,0,0.1)" strokeWidth="10" />
                <path d="M50 10 A40 40 0 0 1 90 50" stroke="#ffb800" strokeWidth="10" strokeLinecap="round" />
              </svg>
              <span>DECRYPTING ROSTER SIGNATURES...</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Operator Email</th>
                    <th>Security Level</th>
                    <th>Joined Timestamp</th>
                    <th className="text-right">MFA Auth</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-white/[0.01]">
                      <td className="font-semibold text-white font-mono text-xs">{m.email}</td>
                      <td>
                        <span className="badge badge-orange text-[9px] uppercase font-mono tracking-wider flex items-center gap-1 w-fit">
                          <Shield size={10} />
                          {m.role}
                        </span>
                      </td>
                      <td className="font-mono text-neutral-400 text-xs">
                        {new Date(m.joined_at).toLocaleString()}
                      </td>
                      <td className="text-right font-mono text-emerald-400 font-bold uppercase text-xs">
                        ENFORCED ✓
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
