import React, { useState } from 'react';
import { LedgerBlock } from '../types';
import { ShieldCheck, Search, HelpCircle, AlertOctagon, Terminal, FileCode, CheckCircle2, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface LedgerViewerProps {
  ledger: LedgerBlock[];
  onAppendLedger: (eventType: string, action: string, memo: string, agentId?: string) => void;
}

export default function LedgerViewer({ ledger, onAppendLedger }: LedgerViewerProps) {
  const [aiPrompt, setAiPrompt] = useState<string>("Analyze the recent audit trail. Identify if there are any potential authorization policy exceptions, steganographic anomalies, or physical worker node crashes.");
  const [aiResponse, setAiResponse] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'block_explorer' | 'ai_auditor'>('block_explorer');

  // Prebuilt audit prompts for convenience and high engagement
  const promptMacros = [
    {
      title: "Evaluate VectorSmuggle Risk",
      prompt: "Execute process-isolation audits. Identify if any recent L4 semantic token outputs represent potential high-dimensional steganographical exfiltration vectors (VectorSmuggle)."
    },
    {
      title: "Assess EU AI Act Compliance",
      prompt: "Analyze our Ledger entries against the latest EU AI Act requirements. Verify model-opaque credential management, sandbox boundaries, and deterministic L5 human-consent gating."
    },
    {
      title: "Verify Little-Endian Byte Drift",
      prompt: "Check state consistency between ARM64 and x86 execution blocks. Review if struct.pack('<...d') little-endian standards are successfully mitigating byte drift."
    }
  ];

  const handleAuditRequest = async (chosenPrompt?: string) => {
    setIsLoading(true);
    setAiResponse("");
    const targetPrompt = chosenPrompt || aiPrompt;
    if (chosenPrompt) {
      setAiPrompt(chosenPrompt);
    }

    try {
      const response = await fetch("/api/analyze-ledger", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          prompt: targetPrompt,
          items: ledger.slice(0, 15) // send latest 15 transactions
        })
      });

      if (response.ok) {
        const data = await response.json();
        setAiResponse(data.text || "No feedback received from the auditor.");
        onAppendLedger('PROOF', `Executed Gemini AI audit analysis`, `Query: "${targetPrompt.substring(0, 60)}..."`);
      } else {
        setAiResponse("### [Server Connection Lost]\nExpress backend did not return a successful model compilation. Ensure API keys are active.");
      }
    } catch (err: any) {
      setAiResponse(`### [Error Invoking Auditor]\nInternal server path execution failed: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getEventBadgeClass = (type: string) => {
    switch (type) {
      case 'IDENTITY': return 'bg-cyan-950/80 text-cyan-400 border border-cyan-805/30';
      case 'AUTHORITY': return 'bg-purple-950/80 text-purple-400 border border-purple-705/30';
      case 'EXECUTION': return 'bg-amber-950/80 text-amber-400 border border-amber-705/30';
      case 'PROOF': return 'bg-cyan-950/45 text-cyan-300 border border-cyan-600/35';
      default: return 'bg-slate-950 text-slate-400 border border-slate-850';
    }
  };

  return (
    <div className="bg-[#0a0c14]/85 border border-cyan-500/20 p-4 rounded-xl flex flex-col justify-between h-full shadow-2xl" id="VeklomLedgerViewer">
      <div>
        
        {/* Core Header with Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-900 pb-3 mb-4">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="text-cyan-400 w-5 h-5 animate-pulse" />
            <h3 className="text-md uppercase font-mono font-semibold tracking-wide text-cyan-300">
              Sovereign Cryptographic Ledger (L5)
            </h3>
          </div>

          <div className="flex bg-[#05070a]/80 p-0.5 rounded-lg border border-slate-900 text-xs font-mono">
            <button
              onClick={() => setActiveTab('block_explorer')}
              className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                activeTab === 'block_explorer' 
                  ? 'bg-cyan-950/50 text-cyan-450 font-bold border border-cyan-500/10 shadow-[0_0_8px_rgba(6,182,212,0.15)] text-cyan-400' 
                  : 'text-slate-450 hover:text-slate-200'
              }`}
            >
              ⛓️ Solana Block Explorer
            </button>
            <button
              onClick={() => setActiveTab('ai_auditor')}
              className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                activeTab === 'ai_auditor' 
                  ? 'bg-cyan-950/50 text-cyan-455 font-bold border border-cyan-500/10 shadow-[0_0_8px_rgba(6,182,212,0.15)] text-cyan-400' 
                  : 'text-slate-450 hover:text-slate-200'
              }`}
            >
              🤖 Gemini AI Auditor
            </button>
          </div>
        </div>

        {/* Tab 1: Solana Block Explorer */}
        {activeTab === 'block_explorer' && (
          <div>
            <p className="text-xs text-slate-400 mb-4 font-mono leading-relaxed">
              Live block explorer indexing tamper-evident agent execution records anchored with <span className="text-cyan-400">Solana Memo v2</span> and Program Derived Addresses (PDAs). Every authority decision is mathematically bounded and replayable.
            </p>

            {/* Blocks Stream */}
            <div className="flex flex-col gap-3 max-h-[420px] overflow-y-auto custom-scroll pr-1">
              {ledger.map((block) => (
                <div 
                  key={block.txHash} 
                  className="bg-slate-900/15 border border-slate-900/60 p-3 rounded-lg font-mono text-[11px] leading-relaxed relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300"
                >
                  {/* Event Type Stripe on Left */}
                  <div className={`absolute left-0 top-0 h-full w-1 ${
                    block.eventType === 'IDENTITY' ? 'bg-cyan-500' :
                    block.eventType === 'AUTHORITY' ? 'bg-purple-500' :
                    block.eventType === 'EXECUTION' ? 'bg-amber-500' : 'bg-cyan-400'
                  }`} />

                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pl-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-500 font-bold">BLOCK #{block.blockNumber}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold uppercase ${getEventBadgeClass(block.eventType)}`}>
                        {block.eventType}
                      </span>
                    </div>
                    <span className="text-slate-550 text-[10px]">
                      {new Date(block.timestamp).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="pl-2 space-y-1 text-slate-300">
                    <div>
                      <span className="text-slate-500 font-bold">STATE ACTION:</span> {block.action}
                    </div>
                    <div>
                      <span className="text-slate-500 font-bold">MEMO EVIDENCE:</span> <span className="text-cyan-305/90 italic">"{block.memo}"</span>
                    </div>
                    
                    {/* Collapsible cryptographic signatures */}
                    <details className="text-[10px] text-slate-500 pt-1.5 border-t border-slate-900/40 mt-1.5">
                      <summary className="cursor-pointer hover:text-slate-300 select-none">Show technical cryptography</summary>
                      <div className="bg-[#05070a]/80 border border-slate-900 p-2 rounded text-[9px] mt-1 space-y-1 text-slate-400 font-mono">
                        <div className="truncate"><span className="text-cyan-400 font-bold">TX HASH:</span> {block.txHash}</div>
                        <div className="truncate"><span className="text-cyan-400 font-bold">PDA SEED:</span> {block.pdaAddress}</div>
                        <div>
                          <span className="text-cyan-400 font-bold">ECONOMIC METER (x402):</span> {block.gasPaidLamports} Lamports (PAID)
                        </div>
                        <div className="flex items-center gap-1.5 text-cyan-400 text-[8px] font-extrabold mt-1">
                          <CheckCircle2 className="w-3 h-3" /> VERIFIED REPLAYABLE METADATA BY DEFAULT
                        </div>
                      </div>
                    </details>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Gemini AI Auditor */}
        {activeTab === 'ai_auditor' && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-400 font-mono leading-relaxed">
              Query the LLM as a probabilistic governor. Analyze security drift, evaluate compliance bounds, or review F-distribution anomalies on the active Solana settlement queue.
            </p>

            {/* Prompt Macros */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {promptMacros.map((m) => (
                <button
                  key={m.title}
                  onClick={() => handleAuditRequest(m.prompt)}
                  disabled={isLoading}
                  className="bg-[#05070a]/40 hover:bg-[#05070a]/90 border border-slate-900 hover:border-cyan-500/30 p-2.5 rounded text-left transition-all cursor-pointer group"
                >
                  <span className="text-[10px] font-mono font-bold text-cyan-400 group-hover:text-cyan-300 block mb-1">
                    {m.title}
                  </span>
                  <span className="text-[9px] font-mono text-slate-500 line-clamp-2">
                    {m.prompt}
                  </span>
                </button>
              ))}
            </div>

            {/* Custom Input */}
            <div className="bg-[#05070a]/40 p-3 rounded-lg border border-slate-900">
              <label className="text-[10px] uppercase font-mono text-cyan-400 font-bold block mb-1.5">
                Custom Auditor Prompt Strategy
              </label>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-900 rounded p-2 text-xs font-mono text-slate-200 h-16 focus:outline-none focus:border-cyan-500 custom-scroll resize-none"
                placeholder="Ask Gemini to analyze the ledger..."
              />
              <button
                onClick={() => handleAuditRequest()}
                disabled={isLoading || !aiPrompt.trim()}
                className="w-full mt-2.5 py-2 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-850 disabled:text-slate-550 text-slate-950 font-mono font-bold rounded text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-[0_0_12px_rgba(6,182,212,0.3)]"
              >
                <Bot className="w-4 h-4 fill-[#05070a]" /> {isLoading ? "COMPILING SYSTEM VERDICT..." : "EXECUTE REASONING AUDIT"}
              </button>
            </div>

            {/* Response Area */}
            <div className="bg-[#05070a]/65 border border-slate-900 rounded-lg p-4 font-mono text-xs max-h-[290px] overflow-y-auto custom-scroll min-h-[140px] relative">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-full absolute inset-0 text-slate-400">
                  <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-2" />
                  <span>Invoking L5 AI Audit Governor...</span>
                </div>
              ) : aiResponse ? (
                <div className="prose prose-invert max-w-none text-slate-300 markdown-body text-[11px] leading-relaxed">
                  <ReactMarkdown>{aiResponse}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-slate-600 text-center">
                  <Terminal className="w-8 h-8 text-slate-800 mb-2" />
                  <span>Awaiting audit instructions. Let Gemini review your active substrate ledger.</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Trust Ledger Footer */}
      <div className="border-t border-slate-900 pt-3 mt-4 text-[10px] font-mono text-slate-500 flex justify-between">
        <span>Solana Settlement Layer (PDA-bound)</span>
        <span>Axiom 6.6 Observability Pass</span>
      </div>
      
    </div>
  );
}
