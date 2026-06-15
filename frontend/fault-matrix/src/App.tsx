import React, { useState } from 'react';
import { LedgerBlock, NotificationLog } from './types';
import GridSimulator from './components/GridSimulator';
import AnomalyDetector from './components/AnomalyDetector';
import AlertSystem from './components/AlertSystem';
import LedgerViewer from './components/LedgerViewer';
import CarbonController from './components/CarbonController';
import { Layers, Activity, Bell, Shield, Leaf, HeartPulse, ChevronRight, CornerDownRight } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'pathfinder' | 'anomaly' | 'alerts' | 'ledger' | 'carbon'>('pathfinder');
  
  // Historical Pre-Seeded Ledger Blocks
  const [ledger, setLedger] = useState<LedgerBlock[]>([
    {
      blockNumber: 84281382,
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      txHash: "5v6F8pTxUdBwMy9e28d5ecd23e4f406b03de43890z8b9n",
      eventType: 'PROOF',
      agentId: "AGT-001",
      action: "Verify little-endian IEEE-754 serialization",
      gasPaidLamports: 5000,
      pdaAddress: "PDA_OOBE_SEED_01_little_endian",
      memo: "Validated little-endian IEEE-754 bytes to prevent heterogeneous ARM64 / x86-64 float drift",
      replayable: true
    },
    {
      blockNumber: 84281381,
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      txHash: "9z4ff866c7d1bc132bcb01ce817ed6c3d24440c23d3a",
      eventType: 'AUTHORITY',
      agentId: "AGT-004",
      action: "Configure MCP boundary permissions",
      gasPaidLamports: 5000,
      pdaAddress: "PDA_OOBE_BOUND_04_mcp",
      memo: "Affirmed L4 semantic tool invocation credentials hidden from the probabilistic reasoning plane",
      replayable: true
    },
    {
      blockNumber: 84281380,
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      txHash: "3ddf9be5c28fe27dad143a5dc76eea25222ad1dd68934",
      eventType: 'IDENTITY',
      agentId: "AGT-102",
      action: "Registered sovereign OOBE client node",
      gasPaidLamports: 10000,
      pdaAddress: "PDA_OOBE_CLIENT_102_sovereign",
      memo: "Dispatched sovereign identity marker verifying planning & context loading limits",
      replayable: true
    }
  ]);

  const [notificationLog, setNotificationLog] = useState<NotificationLog[]>([]);

  // Consolidated real-time Telemetry metrics shared across components
  const [telemetry, setTelemetry] = useState<Record<string, { value: number; unit: string }>>({
    "Pathfinding Compute Load": { value: 0, unit: "Hz" },
    "Active System Thread Locks": { value: 0, unit: "Units" },
    "Active Cell Compute Latency": { value: 48, unit: "ms" },
    "Gradient Deviation Magnitude": { value: 12, unit: "mRad" },
    "Regional Grid Intensity": { value: 15, unit: "gCO2/kWh" },
    "Outbound Energy Footprint": { value: 0, unit: "mJ" },
    "Telemetry Stream Accuracy": { value: 100, unit: "%" },
    "Veklom Network Response Delay": { value: 48, unit: "ms" }
  });

  const handleAppendLedger = (eventType: string, action: string, memo: string, agentId: string = "SYS-000") => {
    const nextBlockNum = (ledger[0]?.blockNumber || 84281382) + 1;
    const randomHex = () => Math.random().toString(16).substr(2, 8);
    const txHash = `${randomHex()}${randomHex()}${randomHex()}${randomHex()}`;
    const pdaAddress = `pda_seed_${eventType.toLowerCase()}_${Math.random().toString(36).substr(2, 6)}`;

    const newBlock: LedgerBlock = {
      blockNumber: nextBlockNum,
      timestamp: new Date().toISOString(),
      txHash,
      eventType,
      agentId,
      action,
      gasPaidLamports: 5000,
      pdaAddress,
      memo,
      replayable: true
    };

    setLedger(prev => [newBlock, ...prev]);
  };

  const handleStateUpdate = (resourceName: string, value: number, unit: string) => {
    setTelemetry(prev => ({
      ...prev,
      [resourceName]: { value, unit }
    }));
  };

  // Helper to trigger a notification popup
  const handleTriggerRealtimeNotification = (title: string, message: string, payload: object) => {
    const id = `NTF-${Math.random().toString(36).substr(2, 5).toUpperCase()}`;
    const timestamp = new Date().toISOString();
    
    // Auto append to notification logs
    const log: NotificationLog = {
      id,
      timestamp,
      type: "ANOMALY_TRIGGERED",
      message: `${title}: ${message}`,
      payload: JSON.stringify(payload, null, 2),
      status: 'delivered'
    };

    setNotificationLog(prev => [log, ...prev].slice(0, 15));
  };

  return (
    <div className="min-h-screen bg-[#05070a] text-slate-300 flex flex-col justify-between selection:bg-cyan-500 selection:text-slate-950 font-sans antialiased">
      
      {/* Top System Bar */}
      <header className="border-b border-cyan-500/20 bg-[#0a0c14] sticky top-0 z-50 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-transparent to-transparent"></div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          
          {/* Logo & Headline */}
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 border border-cyan-400 flex items-center justify-center rotate-45 bg-cyan-950/40 shrink-0 shadow-[0_0_10px_rgba(34,211,238,0.2)]">
              <div className="w-6 h-6 border border-cyan-200/50 -rotate-45 flex items-center justify-center">
                <span className="text-[10px] font-bold text-cyan-400 font-mono">OS</span>
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black tracking-tighter text-white uppercase font-sans leading-none">
                  VEKLOM
                </h1>
                <span className="text-[10px] font-mono bg-cyan-950 text-cyan-400 font-bold px-1.5 py-0.5 rounded border border-cyan-500/30">
                  AGENT OS v5.2.0
                </span>
              </div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-500 font-bold italic mt-0.5 animate-pulse">
                Agentic Authority Runtime // Fault Matrix
              </p>
            </div>
          </div>

          {/* Quick Substrate Health HUD */}
          <div className="flex flex-wrap items-center gap-6 text-[11px] font-mono text-slate-400 bg-[#0d1117] border border-cyan-500/15 rounded-lg p-2.5 shadow-inner">
            <div className="flex flex-col">
              <span className="text-[9px] uppercase opacity-40">OOBE SUBSTRATE</span>
              <span className="text-sm font-bold text-cyan-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></span> ONLINE
              </span>
            </div>
            <div className="flex flex-col border-l border-slate-800/80 pl-4">
              <span className="text-[9px] uppercase opacity-40">ACTIVE LEDGER HEIGHT</span>
              <span className="text-sm font-bold text-white">#{ledger[0]?.blockNumber || 84281382}</span>
            </div>
            <div className="flex flex-col border-l border-slate-800/80 pl-4">
              <span className="text-[9px] uppercase opacity-40">SOLANA SETTLEMENT</span>
              <span className="text-sm font-bold text-[#22c55e]">ACTIVE</span>
            </div>
          </div>

        </div>
      </header>

      {/* Main Command Center Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6">
        
        {/* Global Live Telemetry Stream Grid (Top HUD) */}
        <section className="bg-[#0a0c14]/90 border border-cyan-500/20 p-4 rounded-xl shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/2 to-transparent pointer-events-none"></div>
          <div className="flex items-center gap-2 mb-3 relative z-10">
            <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold">
              Live Substrate Telemetry Stream
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 relative z-10">
            {Object.entries(telemetry).map(([key, value]) => {
              // Custom colors based on key states
              let metricColor = "text-white";
              if (key.includes("Response Delay") && value.value > 150) metricColor = "text-amber-400 animate-pulse";
              else if (key.includes("Stream Accuracy") && value.value < 50) metricColor = "text-red-400 animate-flash";
              else if (value.value > 0 && typeof value.value === "number") metricColor = "text-cyan-400";

              return (
                <div key={key} className="bg-[#0d1117] p-2.5 rounded-lg border border-slate-800/80 font-mono text-xs hover:border-cyan-500/20 transition-all">
                  <span className="text-[9px] text-slate-500 block truncate uppercase tracking-wider">{key}</span>
                  <span className={`text-sm font-bold block mt-1 ${metricColor}`}>
                    {value.value.toLocaleString(undefined, { maximumFractionDigits: 1 })} <span className="text-[9px] font-normal text-slate-500">{value.unit}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Navigation Tabs Bar */}
        <nav className="flex overflow-x-auto bg-[#0a0c14] p-1.5 rounded-xl border border-cyan-500/20 gap-2 custom-scroll max-w-full">
          <button
            onClick={() => setActiveTab('pathfinder')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase transition-all whitespace-nowrap cursor-pointer border ${
              activeTab === 'pathfinder' 
                ? 'bg-[#0d1117] text-cyan-400 border-cyan-500/30 font-bold shadow-[0_0_12px_rgba(34,211,238,0.15)] animate-pulse' 
                : 'text-slate-400 border-transparent hover:text-cyan-300 hover:bg-cyan-950/10'
            }`}
          >
            <Layers className="w-4 h-4" /> 🚧 OOBE Substrate Runbook
          </button>
          <button
            onClick={() => setActiveTab('anomaly')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase transition-all whitespace-nowrap cursor-pointer border ${
              activeTab === 'anomaly' 
                ? 'bg-[#0d1117] text-cyan-400 border-cyan-500/30 font-bold shadow-[0_0_12px_rgba(34,211,238,0.15)] animate-pulse' 
                : 'text-slate-400 border-transparent hover:text-cyan-300 hover:bg-cyan-950/10'
            }`}
          >
            <Activity className="w-4 h-4" /> 📈 Probabilistic Anomaly Monitor
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase transition-all whitespace-nowrap cursor-pointer border ${
              activeTab === 'alerts' 
                ? 'bg-[#0d1117] text-cyan-400 border-cyan-500/30 font-bold shadow-[0_0_12px_rgba(34,211,238,0.15)]' 
                : 'text-slate-400 border-transparent hover:text-cyan-300 hover:bg-cyan-950/10'
            }`}
          >
            <Bell className="w-4 h-4" /> 🔔 Real-Time Notice Engine
          </button>
          <button
            onClick={() => setActiveTab('ledger')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase transition-all whitespace-nowrap cursor-pointer border ${
              activeTab === 'ledger' 
                ? 'bg-[#0d1117] text-cyan-400 border-cyan-500/30 font-bold shadow-[0_0_12px_rgba(34,211,238,0.15)] animate-pulse' 
                : 'text-slate-400 border-transparent hover:text-cyan-300 hover:bg-cyan-950/10'
            }`}
          >
            <Shield className="w-4 h-4" /> ⛓️ Sovereign Auditing Ledger
          </button>
          <button
            onClick={() => setActiveTab('carbon')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase transition-all whitespace-nowrap cursor-pointer border ${
              activeTab === 'carbon' 
                ? 'bg-[#0d1117] text-cyan-400 border-cyan-500/30 font-bold shadow-[0_0_12px_rgba(34,211,238,0.15)]' 
                : 'text-slate-400 border-transparent hover:text-cyan-300 hover:bg-cyan-950/10'
            }`}
          >
            <Leaf className="w-4 h-4" /> 🌿 CALB Green Controller
          </button>
        </nav>

        {/* Tab Modules Routing Hub */}
        <section className="flex-1 w-full relative">
          
          <div className={`${activeTab === 'pathfinder' ? 'block animate-fade-in' : 'hidden'}`}>
            <GridSimulator 
              onAppendLedger={handleAppendLedger} 
              onStateUpdate={handleStateUpdate} 
            />
          </div>

          <div className={`${activeTab === 'anomaly' ? 'block animate-fade-in' : 'hidden'}`}>
            <AnomalyDetector 
              onAppendLedger={handleAppendLedger} 
              onStateUpdate={handleStateUpdate}
              onTriggerRealtimeNotification={handleTriggerRealtimeNotification}
            />
          </div>

          <div className={`${activeTab === 'alerts' ? 'block animate-fade-in' : 'hidden'}`}>
            <AlertSystem 
              onAppendLedger={handleAppendLedger} 
              onStateUpdate={handleStateUpdate}
              notificationLog={notificationLog}
              setNotificationLog={setNotificationLog}
            />
          </div>

          <div className={`${activeTab === 'ledger' ? 'block animate-fade-in' : 'hidden'}`}>
            <LedgerViewer 
              ledger={ledger} 
              onAppendLedger={handleAppendLedger} 
            />
          </div>

          <div className={`${activeTab === 'carbon' ? 'block animate-fade-in' : 'hidden'}`}>
            <CarbonController 
              onAppendLedger={handleAppendLedger} 
              onStateUpdate={handleStateUpdate} 
            />
          </div>

        </section>

      </main>

      {/* Sustainable Architectural Footer */}
      <footer className="border-t border-slate-900 bg-[#0a0c14] py-4 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
          <div>
            <span>Deterministic Routing Matrix // Operational Integrity Verified // Secure Substrate v5.2</span>
          </div>
          <div className="flex gap-4">
            <span className="text-cyan-400">Identity → Authority → Execution → Proof</span>
            <span className="text-slate-700">|</span>
            <span>Est. Node carbon optimization: -34.7%</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
