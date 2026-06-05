"use client";

import React, { DragEvent } from 'react';
import * as LucideIcons from 'lucide-react';
import { CustomNodeData } from './CustomNode';

interface PaletteItem {
  typeCategory: CustomNodeData['typeCategory'];
  label: string;
  icon: string;
}

const PALETTE_CATEGORIES: { name: string; items: PaletteItem[] }[] = [
  {
    name: 'MODELS',
    items: [
      { typeCategory: 'models', label: 'LLM (deployed)', icon: 'Cpu' },
      { typeCategory: 'models', label: 'Reranker', icon: 'Layers' },
      { typeCategory: 'models', label: 'Embedding', icon: 'Network' },
    ]
  },
  {
    name: 'RETRIEVAL',
    items: [
      { typeCategory: 'retrieval', label: 'pgvector', icon: 'Database' },
      { typeCategory: 'retrieval', label: 'Weaviate', icon: 'Database' },
      { typeCategory: 'retrieval', label: 'Qdrant', icon: 'Database' },
      { typeCategory: 'retrieval', label: 'Document loader', icon: 'FileText' },
    ]
  },
  {
    name: 'TOOLS',
    items: [
      { typeCategory: 'tools', label: 'HTTP', icon: 'Globe' },
      { typeCategory: 'tools', label: 'Python', icon: 'Code' },
      { typeCategory: 'tools', label: 'SQL', icon: 'DatabaseZap' },
      { typeCategory: 'tools', label: 'File reader', icon: 'File' },
    ]
  },
  {
    name: 'ROUTING',
    items: [
      { typeCategory: 'routing', label: 'Policy gate', icon: 'Filter' },
      { typeCategory: 'routing', label: 'If / else', icon: 'GitBranch' },
      { typeCategory: 'routing', label: 'Semantic router', icon: 'SplitSquareHorizontal' },
    ]
  },
  {
    name: 'OUTPUT',
    items: [
      { typeCategory: 'output', label: 'JSON formatter', icon: 'Braces' },
      { typeCategory: 'output', label: 'Webhook', icon: 'Webhook' },
      { typeCategory: 'output', label: 'Markdown render', icon: 'Type' },
      { typeCategory: 'output', label: 'Audit signer', icon: 'FileSignature' },
    ]
  }
];

export default function NodePalette() {
  const onDragStart = (event: DragEvent, nodeType: string, nodeData: any) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/reactflow-data', JSON.stringify(nodeData));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-64 h-full border-l border-white/5 bg-bg-950 flex flex-col">
      <div className="p-3 border-b border-white/5">
        <div className="relative">
          <LucideIcons.Search className="absolute left-2.5 top-2 text-ink-400" size={14} />
          <input 
            type="text" 
            placeholder="Search nodes..." 
            className="w-full bg-neutral-900 border border-white/5 rounded-md py-1.5 pl-8 pr-3 text-xs text-white placeholder-ink-400 focus:outline-none focus:border-white/10"
          />
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-4 custom-scrollbar">
        {PALETTE_CATEGORIES.map(category => (
          <div key={category.name}>
            <div className="text-[10px] font-semibold text-ink-400 tracking-widest mb-2 uppercase">
              {category.name}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {category.items.map(item => {
                // @ts-ignore
                const IconComponent = LucideIcons[item.icon] || LucideIcons.Box;
                return (
                  <div
                    key={item.label}
                    className="flex items-center gap-2 px-2 py-1.5 rounded bg-neutral-900 border border-white/5 cursor-grab hover:bg-neutral-800 hover:border-white/10 transition-colors"
                    draggable
                    onDragStart={(e) => onDragStart(e, 'custom', { label: item.label, typeCategory: item.typeCategory, icon: item.icon })}
                  >
                    <IconComponent size={12} className="text-ink-400" />
                    <span className="text-[10px] text-ink-200 truncate">{item.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
