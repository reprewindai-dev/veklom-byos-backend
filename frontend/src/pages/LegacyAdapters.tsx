import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const LegacyAdaptersPage: React.FC = () => {
  const [adapters, setAdapters] = useState<any>({
    snmp: { status: 'inactive' },
    modbus: { status: 'disconnected' },
    webhook: { status: 'listening', events_received: 0 }
  });
  const [simulation, setSimulation] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await api('/api/v1/legacy/status');
      setAdapters(res);
    } catch (err) {
      console.error('Failed to fetch legacy adapter status', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const toggleAdapter = async (type: string) => {
    try {
      setLoading(true);
      await api(`/api/v1/legacy/${type}/toggle`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error(`Failed to toggle ${type}`, err);
    } finally {
      setLoading(false);
    }
  };

  const simulateEvent = async (type: string) => {
    try {
      setLoading(true);
      const res = await api(`/api/v1/legacy/simulate?adapter_type=${type}`, { method: 'POST' });
      setSimulation(res);
      await fetchStatus();
    } catch (err: any) {
      console.error(`Failed to simulate event for ${type}`, err);
      alert(err.message || `Failed to simulate ${type}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] font-display tracking-tight flex items-center gap-3">
          <svg className="w-8 h-8 text-[var(--brand-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Legacy Ingestion Translation
        </h1>
        <p className="text-[var(--text-secondary)] mt-2 max-w-3xl">
          Connect your existing legacy enterprise systems (SNMP, Modbus, Enterprise Webhooks) directly to the sovereign agent runtime. 
          Veklom's edge gateways automatically normalize legacy protocols into standard UACP event envelopes, eliminating the need for expensive custom middleware.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* SNMP Adapter */}
        <div className="panel p-6 flex flex-col relative overflow-hidden group hover:border-[var(--brand-primary)] transition-colors">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--brand-primary)]/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-[var(--text-primary)]">SNMP Normalization</h2>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">Translate traps & polling to JSON</p>
            </div>
            <div className={`px-2 py-1 rounded text-xs font-medium border ${adapters.snmp?.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
              {adapters.snmp?.status === 'active' ? 'ACTIVE' : 'INACTIVE'}
            </div>
          </div>
          
          <div className="space-y-4 flex-grow">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Port</span>
              <span className="font-mono text-[var(--text-primary)]">{adapters.snmp?.port || 162}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">MIBs Supported</span>
              <span className="font-mono text-[var(--text-primary)]">{adapters.snmp?.supported_mibs || 3}</span>
            </div>
          </div>
          
          <div className="mt-6 flex gap-3">
            <button 
              onClick={() => toggleAdapter('snmp')}
              disabled={loading}
              className={`flex-1 py-2 px-4 rounded text-sm font-medium transition-colors ${adapters.snmp?.status === 'active' ? 'bg-[var(--surface-sunken)] text-[var(--text-secondary)] hover:text-red-400' : 'btn-primary'}`}
            >
              {adapters.snmp?.status === 'active' ? 'Disable Listener' : 'Enable Listener'}
            </button>
            <button 
              onClick={() => simulateEvent('snmp')}
              disabled={loading || adapters.snmp?.status !== 'active'}
              className="py-2 px-4 rounded bg-[var(--surface-sunken)] text-[var(--text-primary)] text-sm font-medium hover:bg-[var(--surface-raised)] transition-colors disabled:opacity-50"
              title="Simulate Event"
            >
              Test
            </button>
          </div>
        </div>

        {/* Modbus Adapter */}
        <div className="panel p-6 flex flex-col relative overflow-hidden group hover:border-[var(--brand-primary)] transition-colors">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--brand-primary)]/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-[var(--text-primary)]">Modbus TCP/RTU</h2>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">Industrial OT telemetry bridge</p>
            </div>
            <div className={`px-2 py-1 rounded text-xs font-medium border ${adapters.modbus?.status === 'connected' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
              {adapters.modbus?.status === 'connected' ? 'CONNECTED' : 'DISCONNECTED'}
            </div>
          </div>
          
          <div className="space-y-4 flex-grow">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Host</span>
              <span className="font-mono text-[var(--text-primary)]">{adapters.modbus?.host || '127.0.0.1'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Mapped Registers</span>
              <span className="font-mono text-[var(--text-primary)]">{adapters.modbus?.mapped_registers || 0}</span>
            </div>
          </div>
          
          <div className="mt-6 flex gap-3">
            <button 
              onClick={() => toggleAdapter('modbus')}
              disabled={loading}
              className={`flex-1 py-2 px-4 rounded text-sm font-medium transition-colors ${adapters.modbus?.status === 'connected' ? 'bg-[var(--surface-sunken)] text-[var(--text-secondary)] hover:text-red-400' : 'btn-primary'}`}
            >
              {adapters.modbus?.status === 'connected' ? 'Disconnect' : 'Connect'}
            </button>
            <button 
              onClick={() => simulateEvent('modbus')}
              disabled={loading || adapters.modbus?.status !== 'connected'}
              className="py-2 px-4 rounded bg-[var(--surface-sunken)] text-[var(--text-primary)] text-sm font-medium hover:bg-[var(--surface-raised)] transition-colors disabled:opacity-50"
              title="Simulate Poll"
            >
              Test
            </button>
          </div>
        </div>

        {/* Webhook Adapter */}
        <div className="panel p-6 flex flex-col relative overflow-hidden group hover:border-[var(--brand-primary)] transition-colors">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--brand-primary)]/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
          
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-[var(--text-primary)]">Enterprise Webhooks</h2>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">SAP, Oracle, ServiceNow ingress</p>
            </div>
            <div className="px-2 py-1 rounded text-xs font-medium border bg-green-500/10 text-green-400 border-green-500/20">
              LISTENING
            </div>
          </div>
          
          <div className="space-y-4 flex-grow">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Events Received</span>
              <span className="font-mono text-[var(--text-primary)]">{adapters.webhook?.events_received || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Supported</span>
              <span className="font-mono text-xs text-[var(--text-primary)] truncate max-w-[120px]">
                {adapters.webhook?.systems_supported?.join(', ')}
              </span>
            </div>
          </div>
          
          <div className="mt-6 flex gap-3">
            <button 
              className="flex-1 py-2 px-4 rounded text-sm font-medium bg-[var(--surface-sunken)] text-[var(--text-secondary)] cursor-not-allowed"
            >
              Always Active
            </button>
            <button 
              onClick={() => simulateEvent('webhook')}
              disabled={loading}
              className="py-2 px-4 rounded bg-[var(--surface-sunken)] text-[var(--text-primary)] text-sm font-medium hover:bg-[var(--surface-raised)] transition-colors disabled:opacity-50"
              title="Simulate Event"
            >
              Test
            </button>
          </div>
        </div>
      </div>

      {/* Simulation Result / Trace comparison */}
      <div className="panel p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-[var(--text-primary)]">Signal Normalization Trace</h2>
          {simulation && (
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Trace: {simulation.normalized?.event_id}
            </span>
          )}
        </div>

        {!simulation ? (
          <div className="py-12 flex flex-col items-center justify-center text-[var(--text-tertiary)] border-2 border-dashed border-[var(--surface-raised)] rounded-lg">
            <svg className="w-12 h-12 mb-3 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <p>Click "Test" on any adapter to view normalization trace</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-red-400"></div>
                <h3 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider">Raw Legacy Signal</h3>
              </div>
              <div className="bg-[#0f1115] border border-[var(--surface-raised)] rounded-lg p-4 h-[300px] overflow-auto font-mono text-sm text-red-300">
                <pre>{JSON.stringify(simulation.raw, null, 2)}</pre>
              </div>
            </div>
            
            <div className="relative">
              <div className="hidden lg:flex absolute top-1/2 -left-6 w-6 items-center justify-center -translate-y-1/2 text-[var(--text-tertiary)]">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]"></div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Normalized Agent Event</h3>
              </div>
              <div className="bg-[#0f1115] border border-[var(--brand-primary)]/30 rounded-lg p-4 h-[300px] overflow-auto font-mono text-sm text-green-300">
                <pre>{JSON.stringify(simulation.normalized, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
