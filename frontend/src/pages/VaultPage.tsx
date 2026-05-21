import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Key, Plus, Trash, ShieldAlert, Check, Copy } from 'lucide-react';

export const VaultPage: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [subError, setSubError] = useState('');
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchKeys = async () => {
    setIsLoading(true);
    setSubError('');
    try {
      const res = await api('/workspace/api-keys');
      setApiKeys(res);
    } catch (err: any) {
      setSubError(err.message || 'Gateway sync aborted.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateAPIKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setSubError('');
    setGeneratedKey('');
    setCopied(false);
    try {
      const res = await api('/workspace/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: newKeyName })
      });
      setGeneratedKey(res.key);
      setNewKeyName('');
      
      // refresh list
      const updated = await api('/workspace/api-keys');
      setApiKeys(updated);
    } catch (err: any) {
      setSubError(err.message || 'Key compilation failed.');
    }
  };

  const handleDeleteKey = async (id: string) => {
    try {
      await api(`/workspace/api-keys/${id}`, { method: 'DELETE' });
      setApiKeys(prev => prev.filter(k => k.id !== id));
    } catch (err: any) {
      setSubError(err.message || 'Purging key failed.');
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-white/5 pb-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-3">
          <Key size={18} className="text-[var(--orange)] animate-pulse" /> Cryptographic Key Vault
        </h2>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">Manage sovereign API keys for external application gateways.</p>
      </div>

      {subError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded font-mono">
          {subError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Creator panel */}
        <div className="glow-card lg:col-span-4 self-start bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
            <Plus size={14} className="text-[var(--orange)]" /> GENERATE SECURITY KEY
          </h3>
          <form onSubmit={handleCreateAPIKey} className="space-y-4">
            <div>
              <label className="form-label" htmlFor="key-label">Key Identifier</label>
              <input
                id="key-label"
                type="text"
                placeholder="e.g. acme-backend-production"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="form-input text-xs font-mono"
                required
              />
            </div>
            <button 
              type="submit" 
              className="btn btn-primary w-full py-2.5 text-xs font-bold font-mono tracking-wider flex items-center justify-center gap-1.5"
            >
              <Plus size={13} /> GENERATE KEY
            </button>
          </form>

          {generatedKey && (
            <div className="mt-6 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded font-mono text-[10px] space-y-3 text-white">
              <div className="text-[var(--orange)] font-bold uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert size={12} className="animate-pulse" /> COPY PRIVATE KEY NOW:
              </div>
              <div className="flex items-center gap-2 bg-black border border-emerald-500/20 rounded p-2">
                <span className="break-all select-all text-emerald-400 font-bold flex-1">{generatedKey}</span>
                <button 
                  onClick={copyToClipboard}
                  className="p-1 hover:bg-neutral-800 rounded transition-colors text-[var(--text-secondary)] hover:text-white"
                  title="Copy Key"
                >
                  {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                </button>
              </div>
              <p className="text-[9px] text-[var(--text-muted)] leading-relaxed uppercase">
                This token is salted and cryptographically hashed. For your security, it CANNOT be retrieved or viewed again after you navigate away or refresh.
              </p>
            </div>
          )}
        </div>

        {/* List panel */}
        <div className="glow-card lg:col-span-8 bg-[rgba(10,10,12,0.6)] backdrop-blur-sm">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
            <Key size={14} className="text-[var(--orange)]" /> ACTIVE SOVEREIGN KEYS
          </h3>
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-xs font-mono text-[var(--text-secondary)]">
              <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-spin">
                <circle cx="50" cy="50" r="40" stroke="rgba(255,184,0,0.1)" strokeWidth="10" />
                <path d="M50 10 A40 40 0 0 1 90 50" stroke="#ffb800" strokeWidth="10" strokeLinecap="round" />
              </svg>
              <span>DECRYPTING KEYS ROSTER...</span>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="py-12 border border-dashed border-white/5 rounded-xl flex flex-col items-center justify-center gap-2 text-center text-xs font-mono text-[var(--text-secondary)]">
              <Key size={24} className="text-[var(--text-muted)] mb-2" />
              <span>NO ACTIVE GATEWAY KEYS FOUND</span>
              <span className="text-[10px] text-[var(--text-muted)]">Generate an access key above to begin authenticating incoming API requests.</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Key Label</th>
                    <th>Token Prefix</th>
                    <th>Audit Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((k) => (
                    <tr key={k.id} className="hover:bg-white/[0.01]">
                      <td className="font-semibold text-white font-mono text-xs">{k.name}</td>
                      <td className="font-mono text-white text-xs">{k.key_prefix}••••••••</td>
                      <td>
                        <span className={`badge ${k.is_active ? 'badge-green' : 'badge-orange'} uppercase font-mono text-[9px]`}>
                          {k.is_active ? 'active' : 'revoked'}
                        </span>
                      </td>
                      <td className="text-right">
                        {k.is_active && (
                          <button
                            onClick={() => handleDeleteKey(k.id)}
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-1.5 rounded transition-colors inline-flex items-center justify-center"
                            title="Revoke and delete key"
                          >
                            <Trash size={12} />
                          </button>
                        )}
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
