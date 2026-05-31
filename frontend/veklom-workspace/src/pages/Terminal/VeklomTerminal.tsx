import React, { useEffect, useRef, useState } from 'react';
import './VeklomTerminal.css';
import { api } from '../../api/client';
import { Terminal as TerminalIcon, Cpu, GitBranch, Crosshair } from 'lucide-react';

interface TerminalEndpoint {
  label: string;
  method: string;
  path: string;
}

interface LogLine {
  text: string;
  type: 'sys' | 'pmt' | 'out' | 'ok' | 'warn' | 'err' | 'dim' | 'pur' | 'hdr' | 'sep';
}

export const VeklomTerminal: React.FC = () => {
  const [activeView, setActiveView] = useState<'terminal'|'mesh'|'tele'>('terminal');
  const [endpoints, setEndpoints] = useState<TerminalEndpoint[]>([]);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch allowed commands on mount
  useEffect(() => {
    const fetchEndpoints = async () => {
      try {
        const res = await api('/command-center/terminals/veklom');
        if (res && res.endpoints) {
          setEndpoints(res.endpoints);
          simulateBoot(res.endpoints.length);
        }
      } catch (err: any) {
        addLog('Failed to fetch terminal endpoints from backend.', 'err');
      }
    };
    fetchEndpoints();
    startZenoAnimation();
  }, []);

  const startZenoAnimation = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let zenoPhase = 0;
    const draw = () => {
      const w = canvas.offsetWidth;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      ctx.beginPath();
      for (let x = 0; x < w; x++) {
        const amp = 2.5, fr = 0.035;
        const y = h / 2 + Math.sin(x * fr + zenoPhase) * amp + Math.sin(x * fr * 2.1 + zenoPhase * 1.6) * (amp * 0.35);
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(99,179,237,0.5)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      zenoPhase += 0.016;
      requestAnimationFrame(draw);
    };
    draw();
  };

  const addLog = (text: string, type: LogLine['type'] = 'out') => {
    setLogs(prev => [...prev, { text, type }]);
    setTimeout(() => {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  const simulateBoot = async (endpointCount: number) => {
    addLog('────────────────────────────────────────────', 'sep');
    addLog('  PERPLEXTERMINAL  //  UACP v4.1', 'hdr');
    addLog('  Neural Orchestration Engine · Antigravity v4.1', 'dim');
    addLog('────────────────────────────────────────────', 'sep');
    await new Promise(r => setTimeout(r, 200));
    addLog('[BOOT]  Quantum context surface…', 'sys');
    await new Promise(r => setTimeout(r, 200));
    addLog('[BOOT]  MCP host adapter loaded', 'sys');
    await new Promise(r => setTimeout(r, 200));
    addLog(`        ✓  Loaded ${endpointCount} secure endpoints`, 'ok');
    addLog('[BOOT]  Zeno Interrogator: ONLINE', 'sys');
    await new Promise(r => setTimeout(r, 200));
    addLog('[BOOT]  Cognitive Engine: CONNECTED', 'ok');
    addLog('', 'out');
  };

  const handleCommand = async () => {
    if (!input.trim()) return;
    const cmd = input.trim();
    setInput('');
    addLog(`$ ${cmd}`, 'pmt');

    setIsTyping(true);
    
    // Find matching endpoint
    const matched = endpoints.find(e => e.label === cmd || cmd.startsWith(e.label));
    
    if (matched) {
      try {
        const res = await api(matched.path, { method: matched.method });
        setIsTyping(false);
        addLog(`[${matched.method}] ${matched.path} -> OK`, 'ok');
        addLog(JSON.stringify(res, null, 2), 'out');
      } catch (err: any) {
        setIsTyping(false);
        addLog(`[${matched.method}] ${matched.path} -> ERROR`, 'err');
        addLog(err.message, 'err');
      }
    } else {
      setTimeout(() => {
        setIsTyping(false);
        addLog(`Command not found or unauthorized: ${cmd}`, 'warn');
        addLog(`Type a valid command from the endpoint map.`, 'dim');
      }, 500);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleCommand();
  };

  return (
    <div className="perplex-terminal-wrapper">
      <div className="shell">
        {/* TITLEBAR */}
        <div className="titlebar">
          <div className="tb-inner">
            <div className="tb-l">
              <div className="dots"><div className="dot r"></div><div className="dot a"></div><div className="dot g"></div></div>
              <div className="tb-title"><b>PerplexTerminal</b> · UACP v4.1</div>
            </div>
            <div className="tb-stat"><div className="live-dot"></div>LIVE</div>
          </div>
        </div>

        {/* ZENO STRIP */}
        <div className="zeno-strip">
          <div className="z-lbl">Zeno</div>
          <div className="z-wrap"><canvas ref={canvasRef} id="zeno" height="26"></canvas></div>
          <div className="z-state" id="zeno-state">PHASE_LOCKED</div>
        </div>

        {/* VIEWS */}
        <div className="views">
          
          {/* TERMINAL VIEW */}
          <div className={`view ${activeView === 'terminal' ? 'active' : ''}`}>
            <div className="chips-bar">
              {endpoints.map(ep => (
                <div key={ep.label} className="chip" onClick={() => setInput(ep.label)}>
                  {ep.label}
                </div>
              ))}
            </div>
            <div className="output">
              {logs.map((log, i) => (
                <div key={i} className={`ln ${log.type}`}>{log.text}</div>
              ))}
              <div ref={logsEndRef} />
            </div>
            {isTyping && (
              <div className="typing on">
                <div className="td"></div><div className="td"></div><div className="td"></div>
                <div className="typing-lbl">Cognitive Engine…</div>
              </div>
            )}
            <div className="input-bar">
              <span className="i-pmt">$</span>
              <input 
                className="i-field" 
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                type="text" 
                placeholder="Enter command…"
                autoComplete="off" 
                autoCorrect="off" 
                spellCheck="false"
              />
              <button className="run-btn" onClick={handleCommand}>RUN</button>
            </div>
          </div>

          {/* MESH VIEW */}
          <div className={`view ${activeView === 'mesh' ? 'active' : ''}`}>
            <div className="mesh-view">
              <div className="section-hdr">MCP Host–Client–Server Topology</div>
              <div className="data-card">
                <div className="data-row"><span className="data-key">UACP HOST</span><span className="data-val ok">PerplexTerminal</span></div>
                <div className="data-row"><span className="data-key">MCP CLIENT</span><span className="data-val">Protocol Translator</span></div>
                <div className="data-row"><span className="data-key">SERVERS</span><span className="data-val">filesystem, quantum</span></div>
              </div>
            </div>
          </div>

        </div>

        {/* BOTTOM NAV */}
        <div className="bnav">
          <div className={`bt ${activeView === 'terminal' ? 'active' : ''}`} onClick={() => setActiveView('terminal')}>
            <TerminalIcon size={16} /> Terminal
          </div>
          <div className={`bt ${activeView === 'mesh' ? 'active' : ''}`} onClick={() => setActiveView('mesh')}>
            <GitBranch size={16} /> Mesh
          </div>
          <div className={`bt ${activeView === 'tele' ? 'active' : ''}`} onClick={() => setActiveView('tele')}>
            <Crosshair size={16} /> Telemetry
          </div>
        </div>

      </div>
    </div>
  );
};
