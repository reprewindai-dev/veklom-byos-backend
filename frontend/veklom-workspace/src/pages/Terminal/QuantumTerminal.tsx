import React, { useEffect, useState, useRef } from 'react';
import './QuantumTerminal.css';
import { api } from '../../api/client';

interface TerminalEndpoint {
  label: string;
  method: string;
  path: string;
}

interface LogLine {
  ts: string;
  prefix: string;
  text: string;
  type: 'sys' | 'info' | 'ok' | 'warn' | 'err' | 'cmd';
}

export const QuantumTerminal: React.FC = () => {
  const [endpoints, setEndpoints] = useState<TerminalEndpoint[]>([]);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [input, setInput] = useState('');
  const [activeEndpoint, setActiveEndpoint] = useState<TerminalEndpoint | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchEndpoints = async () => {
      try {
        const res = await api('/command-center/terminals/quantum');
        if (res && res.endpoints) {
          setEndpoints(res.endpoints);
          simulateBoot(res.endpoints.length);
        }
      } catch (err: any) {
        addLog('SYS', 'Failed to fetch terminal endpoints.', 'err');
      }
    };
    fetchEndpoints();
  }, []);

  const addLog = (prefix: string, text: string, type: LogLine['type'] = 'info') => {
    const ts = new Date().toISOString().substring(11, 23);
    setLogs(prev => [...prev, { ts, prefix, text, type }]);
    setTimeout(() => {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  const simulateBoot = async (count: number) => {
    addLog('BOOT', 'Quantum Context Terminal initializing...', 'sys');
    await new Promise(r => setTimeout(r, 200));
    addLog('NET', `Discovered ${count} endpoints in topology`, 'sys');
    await new Promise(r => setTimeout(r, 200));
    addLog('OK', 'System operational and ready.', 'ok');
  };

  const executeCommand = async () => {
    if (!input.trim()) return;
    const cmd = input.trim();
    setInput('');
    addLog('UACP>', cmd, 'cmd');

    const ep = endpoints.find(e => e.label === cmd || cmd.startsWith(e.label));
    if (ep) {
      try {
        const res = await api(ep.path, { method: ep.method });
        addLog(ep.method, `Execute ${ep.path}`, 'info');
        addLog('RES', JSON.stringify(res, null, 2), 'ok');
      } catch (err: any) {
        addLog('ERR', err.message, 'err');
      }
    } else {
      addLog('ERR', `Command not found: ${cmd}`, 'err');
    }
  };

  return (
    <div className="quantum-terminal-wrapper">
      <header className="hdr">
        <div className="hdr-logo">
          <span>UACP // Quantum Context Terminal</span>
        </div>
        <div className="hdr-sep"></div>
        <span className="hdr-tag live">live</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="status-dot"></div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CONNECTED</span>
        </div>
      </header>
      
      <div className="layout">
        <nav className="sidebar">
          <div className="sb-label">Connection Map</div>
          {endpoints.map((ep, i) => (
            <div 
              key={i} 
              className={`route-item ${activeEndpoint === ep ? 'active' : ''}`}
              onClick={() => { setActiveEndpoint(ep); setInput(ep.label); }}
            >
              <span className={`route-method method-${ep.method.toLowerCase()}`}>{ep.method}</span>
              {ep.path}
            </div>
          ))}
        </nav>

        <main className="main">
          <div className="terminal-output">
            {logs.map((log, i) => (
              <div key={i} className="t-line">
                <span className="t-ts">{log.ts}</span>
                <span className={`t-prefix p-${log.type}`}>[{log.prefix}]</span>
                <span className={`t-text ${log.type}`}>{log.text}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
          <div className="input-bar">
            <span className="input-prompt">UACP&gt;</span>
            <input 
              className="cmd-input" 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && executeCommand()}
              placeholder="Enter command..."
            />
            <button className="exec-btn" onClick={executeCommand}>Execute</button>
          </div>
        </main>

        <aside className="right-panel">
          <div className="panel-section">
            <div className="panel-title">
              <span className="panel-title-dot"></span>Zeno Visualizer
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Zeno Interrogation Active</div>
          </div>
          <div className="panel-section">
            <div className="panel-title">
              <span className="panel-title-dot" style={{background: 'var(--purple)'}}></span>Active Endpoint
            </div>
            {activeEndpoint ? (
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                <div><strong>{activeEndpoint.label}</strong></div>
                <div>{activeEndpoint.method} {activeEndpoint.path}</div>
              </div>
            ) : (
              <div style={{ fontSize: '10px', color: 'var(--text-faint)' }}>None selected</div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};
