import React from 'react';
import { Handle, Position } from '@xyflow/react';
import * as LucideIcons from 'lucide-react';

export interface CustomNodeData {
  label: string;
  subtitle?: string;
  icon?: string;
  typeCategory: 'models' | 'retrieval' | 'tools' | 'routing' | 'output' | 'input';
}

const CATEGORY_COLORS = {
  models: 'border-orange-500/80',
  retrieval: 'border-cyan-500/80',
  tools: 'border-neutral-400',
  routing: 'border-amber-500/80',
  output: 'border-emerald-500/80',
  input: 'border-indigo-500/80',
};

const CATEGORY_BG = {
  models: 'bg-orange-950/20 text-orange-400',
  retrieval: 'bg-cyan-950/20 text-cyan-400',
  tools: 'bg-neutral-900 text-neutral-400',
  routing: 'bg-amber-950/20 text-amber-400',
  output: 'bg-emerald-950/20 text-emerald-400',
  input: 'bg-indigo-950/20 text-indigo-400',
};

export default function CustomNode({ data, selected }: { data: CustomNodeData, selected: boolean }) {
  // @ts-ignore
  const IconComponent = LucideIcons[data.icon || 'Box'] || LucideIcons.Box;
  
  const borderColor = CATEGORY_COLORS[data.typeCategory] || 'border-neutral-500';
  const bgIconColor = CATEGORY_BG[data.typeCategory] || 'bg-neutral-900 text-neutral-400';
  
  return (
    <div className={`relative flex items-center min-w-[200px] px-3 py-2 rounded-md bg-neutral-900/80 backdrop-blur-md border ${selected ? 'border-brand-500 shadow-[0_0_15px_rgba(255,184,0,0.2)]' : 'border-white/5'} transition-all`}>
      <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-md ${borderColor}`} />
      
      <div className={`w-6 h-6 flex items-center justify-center rounded border border-white/5 ${bgIconColor} mr-3`}>
        <IconComponent size={12} strokeWidth={2.5} />
      </div>
      
      <div className="flex flex-col">
        <span className="text-xs font-semibold text-white tracking-wide">{data.label}</span>
        {data.subtitle && (
          <span className="text-[10px] text-ink-400 uppercase tracking-widest">{data.subtitle}</span>
        )}
      </div>

      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-1 h-3 rounded-sm bg-neutral-600 border-none opacity-0" 
      />
      <Handle 
        type="source" 
        position={Position.Right} 
        className="w-1 h-3 rounded-sm bg-neutral-600 border-none opacity-0" 
      />
    </div>
  );
}
