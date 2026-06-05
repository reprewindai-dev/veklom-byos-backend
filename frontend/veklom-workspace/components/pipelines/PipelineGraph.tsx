"use client";

import React, { useState, useCallback, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection,
  ReactFlowProvider,
  BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import CustomNode from './CustomNode';
import NodePalette from './NodePalette';

const nodeTypes = {
  custom: CustomNode,
};

// Default initial nodes matching the clinical-rag pipeline from screenshot
const initialNodes: Node[] = [
  { id: '1', type: 'custom', position: { x: 50, y: 300 }, data: { label: 'Input', subtitle: 'v1', icon: 'LogIn', typeCategory: 'input' } },
  { id: '2', type: 'custom', position: { x: 300, y: 300 }, data: { label: 'Policy gate', subtitle: 'clinical', icon: 'Filter', typeCategory: 'routing' } },
  { id: '3', type: 'custom', position: { x: 550, y: 220 }, data: { label: 'Embed (BGE-M3)', subtitle: 'v2', icon: 'Network', typeCategory: 'models' } },
  { id: '4', type: 'custom', position: { x: 550, y: 380 }, data: { label: 'Retrieve - pgvector', subtitle: 'clinical', icon: 'Database', typeCategory: 'retrieval' } },
  { id: '5', type: 'custom', position: { x: 800, y: 380 }, data: { label: 'Rerank - cross-encoder', subtitle: 'clinical', icon: 'Layers', typeCategory: 'models' } },
  { id: '6', type: 'custom', position: { x: 1050, y: 300 }, data: { label: 'LLM - Llama 3.1 70B', subtitle: 'Ollama', icon: 'Cpu', typeCategory: 'models' } },
  { id: '7', type: 'custom', position: { x: 1300, y: 300 }, data: { label: 'PII redact', subtitle: 'clinical', icon: 'ShieldAlert', typeCategory: 'routing' } },
  { id: '8', type: 'custom', position: { x: 1550, y: 220 }, data: { label: 'Audit signer', subtitle: 'v1', icon: 'FileSignature', typeCategory: 'output' } },
  { id: '9', type: 'custom', position: { x: 1550, y: 380 }, data: { label: 'Webhook', subtitle: 'out', icon: 'Webhook', typeCategory: 'output' } },
];

const edgeStyle = {
  stroke: 'rgba(255,255,255,0.2)',
  strokeWidth: 2,
};

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e2-3', source: '2', target: '3', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e2-4', source: '2', target: '4', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e4-5', source: '4', target: '5', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e3-6', source: '3', target: '6', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e5-6', source: '5', target: '6', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e6-7', source: '6', target: '7', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e7-8', source: '7', target: '8', type: 'smoothstep', animated: true, style: edgeStyle },
  { id: 'e7-9', source: '7', target: '9', type: 'smoothstep', animated: true, style: edgeStyle },
];

function FlowComponent() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep', animated: true, style: edgeStyle }, eds)),
    []
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const type = event.dataTransfer.getData('application/reactflow');
      const nodeDataStr = event.dataTransfer.getData('application/reactflow-data');

      if (typeof type === 'undefined' || !type || !nodeDataStr) {
        return;
      }

      const nodeData = JSON.parse(nodeDataStr);
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode: Node = {
        id: `node_${Date.now()}`,
        type,
        position,
        data: nodeData,
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance]
  );

  return (
    <div className="flex w-full h-[600px] border border-white/5 rounded-xl overflow-hidden bg-bg-950 shadow-2xl relative">
      <div className="flex-1 h-full" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          className="bg-bg-950"
        >
          <Background 
            variant={BackgroundVariant.Dots} 
            gap={24} 
            size={1} 
            color="rgba(255,255,255,0.05)" 
          />
          <Controls 
            className="fill-white bg-neutral-900 border border-white/5 rounded-lg overflow-hidden flex flex-col shadow-lg"
            showInteractive={false}
          />
        </ReactFlow>

        {/* Bottom Status Bar overlay on canvas */}
        <div className="absolute bottom-4 left-4 right-4 flex justify-between items-center text-[10px] font-mono tracking-widest text-ink-400 pointer-events-none">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse" />
            <span className="text-emerald-500 uppercase font-semibold">POLICY ENGINE INLINE</span>
          </div>
          <div>
            {nodes.length} nodes · {edges.length} edges · est. p50 ~ 240ms
          </div>
        </div>
      </div>
      
      <NodePalette />
    </div>
  );
}

export default function PipelineGraph() {
  return (
    <ReactFlowProvider>
      <FlowComponent />
    </ReactFlowProvider>
  );
}
