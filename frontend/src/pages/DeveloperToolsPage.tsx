import React, { useState } from 'react';
import { Terminal, Code, Cpu, ShieldCheck, Github, Layers, Layout, Zap, Package, Compass } from 'lucide-react';

interface ToolItem {
  name: string;
  type: string;
  install: string;
  description: string;
  icon: React.ReactNode;
  madeByVeklom?: boolean;
}

export const DeveloperToolsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'python' | 'ts' | 'java' | 'net' | 'go' | 'arch'>('python');

  const tools: Record<string, ToolItem[]> = {
    python: [
      { name: 'Veklom SDK for Python', type: 'SDK', install: 'pip install veklom', description: 'Official Python client for governed inference, audit logging, model routing, and compliance via the Veklom API.', icon: <Code size={20} />, madeByVeklom: true },
      { name: 'Veklom Toolkit for VS Code', type: 'IDE Plugin', install: '[coming soon]', description: 'Prompt testing, audit log inspector, deployment manager inside VS Code.', icon: <Layout size={20} />, madeByVeklom: true },
      { name: 'Veklom Toolkit for PyCharm', type: 'IDE Plugin', install: '[coming soon]', description: 'Same as VS Code toolkit — for PyCharm and all JetBrains IDEs.', icon: <Layout size={20} />, madeByVeklom: true },
      { name: 'Veklom Powertools for Python', type: 'Framework', install: 'pip install veklom-powertools', description: 'Lambda-style utilities: structured logging, tracing, audit chain, budget guard.', icon: <Zap size={20} />, madeByVeklom: true },
    ],
    ts: [
      { name: 'Veklom SDK for JavaScript', type: 'SDK', install: 'npm install @veklom/sdk', description: 'Official JS/TS client — works in Node.js and browser. Full type safety with TypeScript.', icon: <Code size={20} />, madeByVeklom: true },
      { name: 'Veklom Toolkit for VS Code', type: 'IDE Plugin', install: '[coming soon]', description: 'Shared with Python toolkit — covers JS/TS projects too.', icon: <Layout size={20} />, madeByVeklom: true },
    ],
    java: [
      { name: 'Veklom SDK for Java', type: 'SDK', install: 'Maven/Gradle [coming soon]', description: 'Official Java client for governed inference and audit logging.', icon: <Code size={20} />, madeByVeklom: true },
      { name: 'Veklom Toolkit for IntelliJ IDEA', type: 'IDE Plugin', install: '[coming soon]', description: 'Prompt testing and audit inspection inside IntelliJ.', icon: <Layout size={20} />, madeByVeklom: true },
    ],
    net: [
      { name: 'Veklom SDK for .NET', type: 'SDK', install: 'NuGet [coming soon]', description: 'Official .NET client — full async/await support.', icon: <Code size={20} />, madeByVeklom: true },
      { name: 'Veklom Toolkit for Visual Studio', type: 'IDE Plugin', install: '[coming soon]', description: 'Governed inference testing inside Visual Studio.', icon: <Layout size={20} />, madeByVeklom: true },
    ],
    go: [
      { name: 'Veklom SDK for Go', type: 'SDK', install: 'go get github.com/veklom/sdk-go [coming soon]', description: 'Idiomatic Go client for governed inference and audit.', icon: <Code size={20} />, madeByVeklom: true },
    ],
    arch: [
      { name: 'Veklom Control Plane CLI', type: 'CLI Tool', install: 'npm i -g @veklom/cli', description: 'Advanced command-line interface for managing deployments, routing configurations, and viewing audit logs natively in terminal.', icon: <Terminal size={20} />, madeByVeklom: true },
      { name: 'Veklom CI/CD Shield', type: 'DevOps Action', install: 'GitHub Actions Marketplace', description: 'Injects governance checks directly into your CI pipeline, ensuring no ungoverned models are ever merged to main.', icon: <ShieldCheck size={20} />, madeByVeklom: true },
      { name: 'PY03 IronGrid Route Optimizer', type: 'Marketplace Add-on', install: 'SKU PY03-IRONGRID', description: 'Deterministic routing mesh sold as a GPC add-on for route scoring, latency topology, and data movement economics.', icon: <Cpu size={20} />, madeByVeklom: true },
      { name: 'UACP Blueprint Designer', type: 'Architecture Tool', install: 'Web Dashboard Extension', description: 'Visual node-based designer for planning Universal AI Control Plane state machines and worker fleets.', icon: <Layers size={20} />, madeByVeklom: true }
    ]
  };

  return (
    <div className="space-y-6">
      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="glass-panel p-4 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-[var(--text-muted)] text-xs font-mono mb-2"><Terminal size={14}/> API BASE URL</div>
          <div className="font-mono text-sm text-[var(--orange)]">https://api.veklom.com/api/v1</div>
        </div>
        <div className="glass-panel p-4 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-[var(--text-muted)] text-xs font-mono mb-2"><ShieldCheck size={14}/> AUTHENTICATION</div>
          <div className="font-mono text-sm text-white">JWT or <span className="text-[var(--orange)]">Bearer &lt;token&gt;</span></div>
        </div>
        <div className="glass-panel p-4 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-[var(--text-muted)] text-xs font-mono mb-2"><Github size={14}/> OPEN SOURCE</div>
          <div className="font-mono text-sm text-white">100% Transparent SDKs</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[rgba(255,255,255,0.05)] overflow-x-auto no-scrollbar">
        {[
          { id: 'python', label: 'Python' },
          { id: 'ts', label: 'JS/TypeScript' },
          { id: 'java', label: 'Java' },
          { id: 'net', label: '.NET/C#' },
          { id: 'go', label: 'Go' },
          { id: 'arch', label: 'Runtime Add-ons' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-6 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-[var(--orange)] text-white'
                : 'border-transparent text-[var(--text-muted)] hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-6 pt-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Tools List */}
          <div className="space-y-4">
            {tools[activeTab].map((tool, idx) => (
              <div key={idx} className={`glass-panel p-5 relative overflow-hidden group hover:border-[var(--orange)]/30 transition-all ${tool.madeByVeklom ? 'marketplace-card' : ''}`}>
                <div className="absolute top-0 left-0 w-1 h-full bg-[rgba(255,255,255,0.05)] group-hover:bg-[var(--orange)] transition-colors"></div>
                
                <div className="flex items-start justify-between mb-3 pl-2">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-neutral-900 border border-white/5 text-[var(--orange)]">
                      {tool.icon}
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">{tool.name}</h3>
                      <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{tool.type}</span>
                      {tool.madeByVeklom && (
                        <span className="mt-1 inline-flex items-center gap-1 rounded border border-[rgba(255,184,0,0.22)] bg-[rgba(255,184,0,0.08)] px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wider text-[var(--orange)]">
                          Veklom made
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="pl-2">
                  <p className="text-xs text-[var(--text-secondary)] mb-4 leading-relaxed h-10">
                    {tool.description}
                  </p>
                  
                  <div className="bg-neutral-950 border border-white/5 rounded p-2 flex items-center justify-between font-mono text-[11px]">
                    <span className="text-emerald-400">{tool.install}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Code Example Area (Only show for Python/JS) */}
          <div className="h-full">
            {(activeTab === 'python' || activeTab === 'ts') ? (
              <div className="glass-panel h-full flex flex-col overflow-hidden">
                <div className="border-b border-[rgba(255,255,255,0.05)] px-4 py-3 flex justify-between items-center bg-neutral-900/50">
                  <span className="text-xs font-mono font-bold tracking-wider text-[var(--text-muted)]">QUICK_START.{activeTab === 'python' ? 'py' : 'ts'}</span>
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/20"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/20"></div>
                  </div>
                </div>
                <div className="p-4 bg-[#0a0a0c] flex-1 overflow-x-auto text-[13px] font-mono leading-loose text-neutral-300">
                  {activeTab === 'python' && (
                    <pre>
<span className="text-pink-400">from</span> veklom <span className="text-pink-400">import</span> VeklomClient{'\n\n'}
<span className="text-neutral-500"># Connect securely to the governance perimeter</span>{'\n'}
client = VeklomClient(api_key=<span className="text-yellow-300">"your-api-key"</span>){'\n\n'}
<span className="text-neutral-500"># Execute governed inference</span>{'\n'}
response = client.complete({'\n'}
    prompt=<span className="text-yellow-300">"Summarize this contract clause:"</span>,{'\n'}
    model=<span className="text-yellow-300">"qwen2.5:1.5b"</span>{'\n'}
){'\n\n'}
<span className="text-blue-400">print</span>(response.text){'\n'}
<span className="text-blue-400">print</span>(response.audit_log_id)  <span className="text-neutral-500"># tamper-evident log entry</span>{'\n'}
<span className="text-blue-400">print</span>(response.provider)      <span className="text-neutral-500"># ollama | groq</span>
                    </pre>
                  )}
                  {activeTab === 'ts' && (
                    <pre>
<span className="text-pink-400">import</span> {'{ VeklomClient }'} <span className="text-pink-400">from</span> <span className="text-yellow-300">'@veklom/sdk'</span>;{'\n\n'}
<span className="text-neutral-500">// Connect securely to the governance perimeter</span>{'\n'}
<span className="text-pink-400">const</span> client = <span className="text-pink-400">new</span> VeklomClient({'{'} apiKey: <span className="text-yellow-300">'your-api-key'</span> {'}'});{'\n\n'}
<span className="text-neutral-500">// Execute governed inference</span>{'\n'}
<span className="text-pink-400">const</span> response = <span className="text-pink-400">await</span> client.complete({'{'}{'\n'}
  prompt: <span className="text-yellow-300">'Summarize this contract clause:'</span>,{'\n'}
  model: <span className="text-yellow-300">'qwen2.5:1.5b'</span>,{'\n'}
{'}'});{'\n\n'}
<span className="text-blue-400">console</span>.log(response.text);{'\n'}
<span className="text-blue-400">console</span>.log(response.auditLogId); <span className="text-neutral-500">// tamper-evident entry</span>{'\n'}
<span className="text-blue-400">console</span>.log(response.provider);
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <div className="glass-panel h-full flex flex-col items-center justify-center text-center p-8 border border-dashed border-white/10 bg-neutral-900/20">
                <Compass className="text-[var(--text-muted)] mb-4" size={48} />
                <h3 className="text-white font-bold mb-2">SDK Currently in Development</h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  The Official {tools[activeTab][0]?.name} is currently undergoing high-end architectural compliance checks. 
                  It will be available for early-access download shortly.
                </p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};
