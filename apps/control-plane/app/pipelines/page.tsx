"use client";

import React from 'react';
import Shell from "@/components/Shell";
import TierGate from "@/components/TierGate";
import { Card, Table, Badge } from "@/components/ui";
import * as LucideIcons from "lucide-react";
import PipelineGraph from "@/components/pipelines/PipelineGraph";

const mockPipelines = [
  { id: '1', name: 'clinical-rag', template: 'RAG / pgvector', store: 'PGVECTOR', nodes: 9, invocations: '18,420', lastRun: '2 min ago', status: 'DEPLOYED' },
  { id: '2', name: 'patient-intake', template: 'Intake form → triage', store: 'QDRANT', nodes: 12, invocations: '412', lastRun: '12 min ago', status: 'DEPLOYED' },
  { id: '3', name: 'legal-redactor', template: 'PII strip → redline', store: 'WEAVIATE', nodes: 7, invocations: '2,210', lastRun: '1 hr ago', status: 'DEPLOYED' },
  { id: '4', name: 'risk-classifier', template: 'Multi-label classifier', store: 'PGVECTOR', nodes: 5, invocations: '0', lastRun: '—', status: 'DRAFT' },
];

export default function PipelinesPage() {
  return (
    <Shell>
      <TierGate required="starter" feature="Visual Builder">
        <div className="flex flex-col h-full space-y-6">
          
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[10px] font-mono tracking-widest text-ink-400 uppercase mb-2">
                Pipelines
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">Visual builder for governed inference</h1>
              <p className="text-sm text-ink-400 max-w-2xl">
                Drag-and-drop graphs that chain models, retrieval, memory, tools, and routing — every node gated by your policy engine.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-white/10 hover:border-white/20 rounded-md text-sm font-medium transition-colors">
                <LucideIcons.Layers size={16} />
                Templates
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-400 text-black rounded-md text-sm font-bold transition-colors shadow-[0_0_15px_rgba(255,184,0,0.3)]">
                <LucideIcons.Plus size={16} />
                New pipeline
              </button>
            </div>
          </div>

          {/* Canvas Component */}
          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center gap-3 text-sm">
              <LucideIcons.GitFork size={16} className="text-brand-500" />
              <span className="font-bold text-white">clinical-rag</span>
              <Badge variant="outline" className="text-[10px] tracking-wider bg-transparent text-ink-400 border-white/10 px-2 py-0">V3 · DRAFT</Badge>
            </div>
            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-white/5 rounded-md text-sm font-medium transition-colors">
                <LucideIcons.Play size={14} />
                Test
              </button>
              <button className="flex items-center gap-2 px-4 py-1.5 bg-brand-500/20 text-brand-400 border border-brand-500/50 hover:bg-brand-500/30 rounded-md text-sm font-medium transition-colors">
                <LucideIcons.Rocket size={14} />
                Deploy as endpoint
              </button>
            </div>
          </div>

          <PipelineGraph />

          {/* Data Table */}
          <Card className="p-0 border-white/5 bg-bg-950/50 backdrop-blur-sm">
            <div className="flex items-center justify-between p-5 pb-4 border-b border-white/5">
              <div>
                <h3 className="text-xs font-bold text-white tracking-widest uppercase mb-1">Pipelines · Deployed & Draft</h3>
                <p className="text-[10px] font-mono text-ink-400">4 pipelines</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="bg-brand-500/10 text-brand-500 border border-brand-500/20 text-[10px] uppercase font-mono tracking-wider">RAG / PGVECTOR</Badge>
                <Badge className="bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] uppercase font-mono tracking-wider">QDRANT</Badge>
                <Badge className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] uppercase font-mono tracking-wider">WEAVIATE</Badge>
              </div>
            </div>
            <Table
              rows={mockPipelines}
              rowKey={(r) => r.id}
              columns={[
                { key: "name", header: "Name", render: (r) => <span className="font-bold text-sm text-white">{r.name}</span> },
                { key: "template", header: "Template", render: (r) => <span className="text-sm text-ink-300">{r.template}</span> },
                { key: "store", header: "Vector Store", render: (r) => <span className="font-mono text-xs text-ink-400 uppercase">{r.store}</span> },
                { key: "nodes", header: "Nodes", render: (r) => <span className="text-sm">{r.nodes}</span> },
                { key: "invocations", header: "Invocations", render: (r) => <span className="text-sm">{r.invocations}</span> },
                { key: "lastRun", header: "Last Run", render: (r) => <span className="text-sm">{r.lastRun}</span> },
                { key: "status", header: "Status", render: (r) => (
                  <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${r.status === 'DEPLOYED' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-neutral-600'}`} />
                    <span className={`text-[10px] font-mono tracking-wider ${r.status === 'DEPLOYED' ? 'text-emerald-400' : 'text-neutral-500'}`}>{r.status}</span>
                  </div>
                )},
                { key: "actions", header: "", render: () => <button className="text-ink-500 hover:text-white"><LucideIcons.MoreHorizontal size={16} /></button> }
              ]}
            />
          </Card>

        </div>
      </TierGate>
    </Shell>
  );
}
