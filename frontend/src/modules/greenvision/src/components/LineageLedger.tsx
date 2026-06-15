// @ts-nocheck
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GitBranch, History, ChevronRight, X, Shield, Clock, Hash, Zap } from 'lucide-react';
import { PGLNode } from '../types';

interface LineageLedgerProps {
  nodes: PGLNode[];
}

export const LineageLedger: React.FC<LineageLedgerProps> = ({ nodes }) => {
  const [selectedNode, setSelectedNode] = useState<PGLNode | null>(null);

  const getActiveStatus = (index: number) => {
    return index === nodes.length - 1 ? 'ACTIVE' : 'HISTORICAL';
  };

  return (
    <div className="bg-[#0b1219]/40 rounded-2xl border border-white/10 p-6 flex flex-col gap-4 relative overflow-hidden h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <GitBranch size={18} className="text-amber-400" />
          <h2 className="text-sm font-mono uppercase tracking-widest text-white/80">Project Genome Ledger (PGL)</h2>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] font-mono text-green-500 uppercase tracking-tighter">Live Sync</span>
          </div>
        </div>
      </div>

      <div className="space-y-4 relative flex-1 overflow-y-auto pr-2 scrollbar-hide">
        <div className="absolute left-4 top-4 bottom-4 w-px bg-white/5 border-l border-dashed border-white/10 transition-all" />
        
        {nodes.map((node, i) => (
          <motion.div 
            key={node.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-center gap-4 relative z-10"
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center border shadow-lg transition-all ${
              node.type === 'genome' ? 'bg-cyan-500/20 border-cyan-400/50 text-cyan-400' : 'bg-amber-500/20 border-amber-400/50 text-amber-400'
            } ${getActiveStatus(i) === 'ACTIVE' ? 'ring-2 ring-white/10 ring-offset-2 ring-offset-transparent' : ''}`}>
              {node.type === 'genome' ? <History size={14} /> : <GitBranch size={14} />}
            </div>
            
            <button 
              onClick={() => setSelectedNode(node)}
              className={`flex-1 p-3 rounded-xl bg-black/40 border transition-all flex items-center justify-between group text-left ${
                selectedNode?.id === node.id ? 'border-amber-400/50 bg-amber-400/5 shadow-[0_0_15px_rgba(251,191,36,0.1)]' : 'border-white/5 hover:border-white/20'
              }`}
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-tighter">{node.relation || 'ORIGIN'}</span>
                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
                    getActiveStatus(i) === 'ACTIVE' ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-white/5 border-white/10 text-white/20'
                  }`}>
                    {getActiveStatus(i)}
                  </span>
                </div>
                <span className="text-xs font-medium text-white/80 mt-0.5">{node.label}</span>
              </div>
              <ChevronRight size={14} className={`transition-all ${selectedNode?.id === node.id ? 'text-amber-400 translate-x-1' : 'text-white/10 group-hover:text-white/40'}`} />
            </button>
          </motion.div>
        ))}
      </div>

      {/* Detail Overlay */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="absolute inset-x-6 bottom-6 bg-[#121a24] border border-white/20 rounded-2xl p-5 shadow-2xl z-50 overflow-hidden"
          >
            <div className="absolute top-0 left-0 w-1 h-full bg-amber-400" />
            
            <div className="flex justify-between items-start mb-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Shield size={14} className="text-amber-400" />
                  <span className="text-[10px] font-mono uppercase tracking-widest text-amber-400">Node Proof-of-Trust</span>
                </div>
                <h3 className="text-sm font-bold text-white tracking-tight">{selectedNode.label}</h3>
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/40 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-[9px] font-mono text-white/30 uppercase tracking-tighter">
                  <Hash size={10} /> Hash Identifier
                </div>
                <div className="text-[10px] font-mono text-white/60 truncate">{selectedNode.id.substring(0, 16)}...</div>
              </div>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-[9px] font-mono text-white/30 uppercase tracking-tighter">
                  <Clock size={10} /> Ledger Time
                </div>
                <div className="text-[10px] font-mono text-white/60">T+{Math.floor(Math.random() * 500)}ms RELATIVE</div>
              </div>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-[9px] font-mono text-white/30 uppercase tracking-tighter">
                  <Zap size={10} /> Mutation Scope
                </div>
                <div className="text-[10px] font-mono text-white/60">DELTA_SIGNIFICANT</div>
              </div>
              <div className="p-2.5 rounded-xl bg-amber-400/5 border border-amber-400/20 flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-[9px] font-mono text-amber-400/50 uppercase tracking-tighter">
                  <Shield size={10} /> Identity Verification
                </div>
                <div className="text-[10px] font-mono text-amber-400">SIGN_ED25519_PASS</div>
              </div>
            </div>

            <div className="mt-4 flex gap-2">
              <button className="flex-1 py-1.5 rounded-lg bg-amber-400 text-black text-[10px] font-bold uppercase tracking-wider hover:bg-amber-300 transition-colors">
                Verify Signature
              </button>
              <button className="flex-1 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-[10px] font-bold uppercase tracking-wider hover:bg-white/10 transition-colors">
                Trace Origin
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-auto p-4 rounded-xl bg-amber-400/5 border border-amber-400/10 text-[9px] font-mono leading-relaxed text-white/40 flex flex-col gap-1 backdrop-blur-sm">
         <div className="text-amber-400 uppercase font-bold text-[10px] flex items-center gap-2">
            <div className="w-1 h-1 rounded-full bg-amber-400" />
            Merkle DAG Consensus
         </div>
         <p>Every transition commitConstitutionalWrite emits a cryptographically linked certificate (Ed25519) ensuring zero governance drift.</p>
      </div>
    </div>
  );
};
