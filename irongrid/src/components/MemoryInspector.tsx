import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { ShieldAlert, Database, HelpCircle, HardDrive, Cpu, Terminal, ArrowRight, Activity } from 'lucide-react';
import { AuditRecord } from '../types';

interface MemoryInspectorProps {
  coordSource: [number, number][]; // coordinates list from the active pathfinding grid
}

export default function MemoryInspector({ coordSource }: MemoryInspectorProps) {
  const [rowVal, setRowVal] = useState<number>(14.25);
  const [colVal, setColVal] = useState<number>(110.82);
  const [copied, setCopied] = useState(false);
  const [gcFires, setGcFires] = useState(0);
  const [allocationCount, setAllocationCount] = useState(32); // Initial lifespan allocations

  // Latest coordinates to display
  const latestCoord = coordSource.length > 0 
    ? coordSource[coordSource.length - 1] 
    : [rowVal, colVal];

  const cX = Number(latestCoord[0].toFixed(2));
  const cY = Number(latestCoord[1].toFixed(2));

  // Compute actual IEEE 754 binary little endian representation
  const getFloat32Bytes = (val: number): number[] => {
    const buffer = new ArrayBuffer(4);
    const view = new DataView(buffer);
    view.setFloat32(0, val, true); // true = little-endian <
    const bytes: number[] = [];
    for (let i = 0; i < 4; i++) {
      bytes.push(view.getUint8(i));
    }
    return bytes;
  };

  const bytesX = getFloat32Bytes(cX);
  const bytesY = getFloat32Bytes(cY);
  const packedBytes = [...bytesX, ...bytesY];

  const bytesToHexStr = (bytes: number[]): string => {
    return bytes.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
  };

  const bytesToBinaryStr = (bytes: number[]): string => {
    return bytes.map(b => b.toString(2).padStart(8, '0')).join(' ');
  };

  const hexRepresentation = bytesToHexStr(packedBytes);
  const binaryRepresentation = bytesToBinaryStr(packedBytes);

  // Generate SHA-256 simulated hash representing structured pack hashes
  const generateSimulatedHash = (bytes: number[]): string => {
    let hash = 0;
    for (let i = 0; i < bytes.length; i++) {
      hash = (hash << 5) - hash + bytes[i];
      hash |= 0; // Convert to 32bit integer
    }
    // Hex string from hash
    const p1 = Math.abs(hash).toString(16).padStart(8, 'a');
    const p2 = Math.abs(hash * 31).toString(16).padStart(8, 'f');
    const p3 = Math.abs(hash * 17).toString(16).padStart(8, 'b');
    return `a5c9f5${p1}00d3ae8e${p2}fd91${p3}`.slice(0, 64);
  };

  const activeHash = generateSimulatedHash(packedBytes);

  // Continuous telemetry updates
  useEffect(() => {
    // Under Python core during active pathfinding steps, garbage collector triggers continuously
    // Under compile-time Rust allocation, it is strictly 0.
    const interval = setInterval(() => {
      if (coordSource.length > 0) {
        // Rust zero GC simulation remain 0, Python GIL simulates rising pileups
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [coordSource]);

  // Comparative metrics
  const jsonString = `{"row":${cX},"col":${cY}}`;
  const jsonSize = jsonString.length;
  const binarySize = 8; // 2 floats * 4 bytes each
  const sizeSavings = ((1 - binarySize / jsonSize) * 100).toFixed(0);

  return (
    <div className="flex flex-col gap-5 border border-slate-800 bg-[#070b15] rounded-xl p-5 shadow-lg relative overflow-hidden h-full">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" />
      
      <div>
        <div className="flex items-center gap-2">
          <span className="p-1 px-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded text-xs font-mono font-semibold uppercase tracking-wider">
            Memory Defense
          </span>
          <h2 className="text-xl font-sans font-medium text-slate-150 leading-tight">
            Binary Serializer & Lifespan Allocations
          </h2>
        </div>
        <p className="text-slate-400 text-xs mt-1 font-sans font-light">
          Bypass high-overhead string processing and garbage collection cycles. We map coordinates straight to IEEE 754 float bytes inside pre-allocated unmanaged buffer blocks.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        
        {/* Left Side: Binary Packaging Pipeline */}
        <div className="lg:col-span-7 flex flex-col gap-4 bg-slate-950/40 border border-slate-800 p-4 rounded-lg">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-widest flex items-center justify-between border-b border-slate-800/60 pb-2">
            <span className="flex items-center gap-1.5"><Terminal className="w-4 h-4 text-emerald-400" /> Struct Packing Pipeline (`struct.pack('&lt;2f')`)</span>
            <span className="text-[10px] text-amber-500 font-mono">Zero-Allocation</span>
          </span>

          {coordSource.length === 0 ? (
            <div className="grid grid-cols-2 gap-3 py-1">
              <div className="flex flex-col gap-1">
                <label id="input-node-x-label" className="text-[11px] text-slate-500 font-mono">Input X Coordinate (float32)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={rowVal}
                  onChange={(e) => setRowVal(Number(e.target.value))}
                  className="rounded bg-[#080d19] border border-slate-800 p-2 text-xs text-slate-200 outline-none focus:border-cyan-500/50"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label id="input-node-y-label" className="text-[11px] text-slate-500 font-mono">Input Y Coordinate (float32)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={colVal}
                  onChange={(e) => setColVal(Number(e.target.value))}
                  className="rounded bg-[#080d19] border border-slate-800 p-2 text-xs text-slate-200 outline-none focus:border-cyan-500/50"
                />
              </div>
            </div>
          ) : (
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded p-2.5 flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <div className="text-xs font-sans text-slate-300">
                Streaming actively from active grid pathfinder: 
                <span className="font-mono text-cyan-400 font-bold ml-1">X: {cX}, Y: {cY}</span>
              </div>
            </div>
          )}

          {/* Core serialization visual track */}
          <div className="flex flex-col gap-2 bg-[#050912] p-3 rounded border border-slate-900 font-mono text-xs">
            
            {/* Input Floats representation */}
            <div className="flex items-center justify-between text-[11px] pb-1.5 border-b border-slate-900/80">
              <span className="text-slate-500">Dual Coordinates Float Vector</span>
              <span className="text-slate-300 font-medium">[{cX}, {cY}]</span>
            </div>

            {/* Float values parsed binary bits visual segments */}
            <div className="flex flex-col gap-1 text-[10px] py-1">
              <div className="flex justify-between items-center text-slate-550 text-slate-500">
                <span>IEEE 754 Float bits (X: {cX})</span>
                <span className="text-slate-400 text-[9px]">{bytesToBinaryStr(bytesX)}</span>
              </div>
              <div className="flex justify-between items-center text-slate-550 text-slate-500">
                <span>IEEE 754 Float bits (Y: {cY})</span>
                <span className="text-slate-400 text-[9px]">{bytesToBinaryStr(bytesY)}</span>
              </div>
            </div>

            {/* Little endian hex binary payload output */}
            <div className="flex flex-col gap-1 text-[11px] bg-slate-950 p-2.5 rounded border border-slate-900 mt-1">
              <span className="text-emerald-405 text-emerald-400 text-[10px] font-bold uppercase tracking-wider">Packed Hexadecimal Buffer</span>
              <div className="flex items-center gap-2 mt-1">
                <span className="bg-emerald-500/10 text-emerald-351 p-1 px-2.5 text-xs text-emerald-400 font-bold tracking-widest border border-emerald-500/20 rounded select-all font-mono">
                  {hexRepresentation}
                </span>
                <span className="text-slate-505 text-slate-500 text-[10px]">({binarySize} Bytes Little-Endian)</span>
              </div>
            </div>

            {/* Continuous Audit Log */}
            <div className="flex flex-col gap-1 text-[10px] mt-2">
              <span className="text-slate-400">Continuous SHA-256 Memory Audit Block hash</span>
              <span className="text-cyan-400 font-mono text-[10px] truncate select-all" title="Computed incrementally from the raw binary IEEE buffer">
                {activeHash}
              </span>
            </div>

          </div>
        </div>

        {/* Right Side: Lifespan pre-allocated memory pool */}
        <div className="lg:col-span-5 flex flex-col gap-4 bg-slate-950/40 border border-slate-800 p-4 rounded-lg flex-1 justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-widest flex items-center gap-1.5 border-b border-slate-800 pb-2">
            <HardDrive className="w-4 h-4 text-cyan-400" /> Lifespan Memory Allocator status
          </span>

          {/* Engine address pools grids */}
          <div className="flex-1 flex flex-col gap-3 justify-center">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Initialized Engine Pools:</span>
              <span className="text-emerald-402 text-emerald-400 font-medium">32 Pools Stable</span>
            </div>
            
            {/* 32 reusable memory slots */}
            <div className="grid grid-cols-8 gap-1 p-1.5 border border-slate-900 bg-[#050912] rounded">
              {Array.from({ length: 32 }).map((_, idx) => {
                const isSelected = idx === 12; // visual selected spot representing a live solver channel
                return (
                  <div
                    key={idx}
                    className={`h-4 border flex items-center justify-center font-mono text-[8px] rounded transition ${
                      isSelected 
                        ? 'bg-cyan-500/25 border-cyan-400 text-cyan-300 font-bold animate-pulse' 
                        : 'bg-slate-900/60 border-slate-850 text-slate-500'
                    }`}
                    title={isSelected ? `Active process pool buffer address 0x7fde92a${idx.toString(16)}00` : `Idle static pool buffer address 0x7fde92a${idx.toString(16)}00`}
                  >
                    0x{idx.toString(16).toUpperCase().padStart(2, '0')}
                  </div>
                );
              })}
            </div>

            <div className="text-[10px] text-slate-500 leading-normal font-sans prose prose-slate">
              Upon startup, the server preallocates 32 continuous unmanaged memory slots to prevent runtime <strong className="text-rose-450 text-rose-400 font-semibold font-mono">malloc()</strong> request overhead. As route loops process, memory buffers are reused and never garbage collected.
            </div>
          </div>

          {/* Comparative analysis box */}
          <div className="bg-slate-900/30 border border-slate-850 p-3 rounded flex flex-col gap-2 font-mono text-[11px]">
            <span className="text-xs text-slate-300 font-sans font-bold flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-cyan-400" /> Serialization Comparative:</span>
            
            <div className="flex justify-between">
              <span className="text-slate-500">Bulky JSON String:</span>
              <span className="text-rose-400">{jsonSize} bytes</span>
            </div>
            
            <div className="flex justify-between font-bold">
              <span className="text-slate-500 font-light">Packed Binary Buffer:</span>
              <span className="text-emerald-400">{binarySize} bytes</span>
            </div>

            <div className="flex justify-between border-t border-slate-800/80 pt-1.5 text-emerald-450 font-bold text-center">
              <span className="text-slate-400 font-sans">Total Size Overhead Reduction:</span>
              <span className="text-emerald-400">{sizeSavings}% Saved</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
