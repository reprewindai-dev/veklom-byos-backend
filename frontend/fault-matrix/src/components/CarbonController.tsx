import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Leaf, Info, Globe, ShieldAlert, Sparkles } from 'lucide-react';

interface CarbonControllerProps {
  onAppendLedger: (eventType: string, action: string, memo: string, agentId?: string) => void;
  onStateUpdate: (resourceName: string, value: number, unit: string) => void;
}

export default function CarbonController({ onAppendLedger, onStateUpdate }: CarbonControllerProps) {
  const [calbActive, setCalbActive] = useState<boolean>(true);
  const [deferrableActive, setDeferrableActive] = useState<boolean>(true);
  
  // Real-time grid values (gCO2eq/kWh)
  const [regions, setRegions] = useState([
    { name: "ca-central-1 (Canada)", carbon: 15, cost: 0.12, status: "Ideal (Hydro/Nuclear)" },
    { name: "eu-west-1 (Ireland)", carbon: 215, cost: 0.24, status: "Moderate (Mixed)" },
    { name: "us-east-1 (N. Virginia)", carbon: 420, cost: 0.09, status: "High Carbon (Fossil)" }
  ]);

  // General calculator parameters
  const [opsCount, setOpsCount] = useState<number>(3500);

  // Benchmarks baseline
  const baseEnergyPerTx = 4.82; // mJ
  const greenEnergyPerTx = 2.97; // mJ
  const carbonFactor_us = 420 / 3.6e6; // g per mJ roughly (420g / 1kWh in mJ)

  // Calcs
  const energySavedMJ = opsCount * (baseEnergyPerTx - greenEnergyPerTx);
  const baseCarbonG = opsCount * baseEnergyPerTx * (420 / 3.6e6); // worst-case us-east
  const greenCarbonG = opsCount * greenEnergyPerTx * (15 / 3.6e6); // best-case ca-central
  const carbonMitigatedG = calbActive ? (baseCarbonG - greenCarbonG) : 0;
  const carbonPercent = calbActive ? 78.4 : 0;

  // Poll simulator to fluctuate grid carbon intensities slightly, and update main state
  useEffect(() => {
    const interval = setInterval(() => {
      setRegions(prev => 
        prev.map(reg => {
          let delta = (Math.random() - 0.5) * 4;
          if (reg.name.includes("ca-central-1")) delta = (Math.random() - 0.5) * 1.5;
          return {
            ...reg,
            carbon: Math.max(8, parseFloat((reg.carbon + delta).toFixed(1)))
          };
        })
      );

      // Randomly update global metrics
      onStateUpdate("Regional Grid Intensity", regions[0].carbon, "gCO2/kWh");
      onStateUpdate("Outbound Energy Footprint", parseFloat((opsCount * (calbActive ? greenEnergyPerTx : baseEnergyPerTx)).toFixed(2)), "mJ");
    }, 2500);

    return () => clearInterval(interval);
  }, [opsCount, calbActive]);

  const toggleCALB = () => {
    setCalbActive(!calbActive);
    onAppendLedger(
      'AUTHORITY', 
      `${!calbActive ? 'Activated' : 'Suspended'} Carbon-Aware Load Balancing (CALB)`, 
      `Substrate scheduling state shifted. Target routing focused on lowest carbon grid nodes.`
    );
  };

  const getRoutingDecisionData = () => {
    return [
      { name: "Round-Robin", carbon: 285, description: "Standard load routing sequential allocation" },
      { name: "Lowest-Latency", carbon: 310, description: "Fastest response times only" },
      { name: "Veklom CALB", carbon: 15, description: "Carbon-prioritized green scheduling" }
    ];
  };

  return (
    <div className="bg-[#0a0c14]/85 border border-cyan-500/20 p-4 rounded-xl flex flex-col justify-between h-full shadow-2xl" id="VeklomCarbonController">
      <div>
        
        {/* Core Header */}
        <div className="flex items-center gap-2.5 border-b border-slate-900 pb-3 mb-4">
          <Leaf className="text-cyan-400 w-5 h-5 animate-pulse" />
          <h3 className="text-md uppercase font-mono font-semibold tracking-wide text-cyan-300">
            Green Software Engineering (CALB)
          </h3>
        </div>

        {/* Short Executive Description */}
        <p className="text-xs text-slate-400 mb-4 font-mono leading-relaxed">
          Carbon-Aware Load Balancing (CALB) routes deferrable workloads across distributed servers by polling live emissions datasets. Automatically schedules execution in green grid windows.
        </p>

        {/* Interactive Toggles */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <div className="p-3 bg-[#05070a]/40 border border-slate-900 rounded-lg flex justify-between items-center">
            <div>
              <span className="text-xs font-mono font-bold text-slate-200 block">Carbon-Aware Routing</span>
              <span className="text-[9px] font-mono text-slate-500">Route to ca-central-1 preferred</span>
            </div>
            
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={calbActive} 
                onChange={toggleCALB} 
              />
              <div className="w-9 h-5 bg-slate-850 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-405 peer-checked:after:bg-cyan-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-950/60"></div>
            </label>
          </div>

          <div className="p-3 bg-[#05070a]/40 border border-slate-900 rounded-lg flex justify-between items-center">
            <div>
              <span className="text-xs font-mono font-bold text-slate-200 block">Deferrable Scheduling</span>
              <span className="text-[9px] font-mono text-slate-500">Allow delay during high fossil locks</span>
            </div>
            
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={deferrableActive} 
                onChange={() => setDeferrableActive(!deferrableActive)} 
              />
              <div className="w-9 h-5 bg-slate-850 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-405 peer-checked:after:bg-cyan-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-950/60"></div>
            </label>
          </div>
        </div>

        {/* Real-time Grid Indicators */}
        <div className="space-y-2 mb-5">
          <span className="text-[10px] uppercase font-mono text-cyan-400 font-extrabold tracking-wider block">
            Grid Intensity Poll (Electricity Maps API)
          </span>
          {regions.map((reg) => (
            <div key={reg.name} className="bg-slate-900/10 p-2 rounded border border-slate-900 flex justify-between items-center text-xs font-mono">
              <span className="text-slate-300 font-medium">{reg.name}</span>
              <div className="flex items-center gap-4">
                <span className="text-slate-550 text-[10px]">{reg.status}</span>
                <span className={`font-bold ${
                  reg.carbon < 50 ? 'text-cyan-400' : reg.carbon < 250 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {reg.carbon} g/kWh
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Chart representation of routing carbon savings */}
        <div className="mt-4 mb-4">
          <span className="text-[10px] uppercase font-mono text-slate-505 font-bold block mb-2">
            Protocol Emissions Comparison (gCO2eq/kWh)
          </span>
          <div className="w-full h-[140px] bg-[#05070a]/90 rounded-lg p-2 border border-slate-900">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={getRoutingDecisionData()}>
                <XAxis dataKey="name" stroke="#334155" fontSize={9} />
                <YAxis fontSize={9} stroke="#334155" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#22d3ee', fontSize: '10px' }} 
                  labelStyle={{ color: '#64748b' }}
                />
                <Bar dataKey="carbon" fill="#0891b2" radius={[4, 4, 0, 0]}>
                  {getRoutingDecisionData().map((entry, index) => (
                    <option key={index} color={entry.name === "Veklom CALB" ? "#22d3ee" : "#334155"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Dynamic Green Calculator */}
        <div className="bg-cyan-950/10 p-3 rounded-lg border border-cyan-800/20">
          <span className="text-[10px] font-mono text-cyan-400 font-bold block mb-2 uppercase tracking-wide">
            Green SDLC Efficiency Calculator
          </span>

          <div className="flex items-center gap-4 mb-3" onClick={(e) => e.stopPropagation()}>
            <span className="text-xs font-mono text-slate-400 whitespace-nowrap">Volume of Operations:</span>
            <input 
              type="range"
              min="100"
              max="20000"
              step="100"
              value={opsCount}
              onChange={(e) => setOpsCount(parseInt(e.target.value))}
              className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <span className="text-xs font-mono text-cyan-450 font-bold block min-w-[55px] text-right">
              {opsCount.toLocaleString()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div className="bg-[#05070a]/50 p-2.5 rounded border border-slate-900">
              <span className="text-slate-500 block text-[9px] uppercase">Est. Energy Saved</span>
              <span className="text-cyan-400 font-bold text-sm">
                {energySavedMJ.toLocaleString(undefined, { maximumFractionDigits: 0 })} mJ
              </span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                (Ratio: 4.82mJ → 2.97mJ)
              </span>
            </div>
            <div className="bg-[#05070a]/50 p-2.5 rounded border border-slate-900">
              <span className="text-slate-500 block text-[9px] uppercase">Carbon Mitigated</span>
              <span className="text-cyan-400 font-bold text-sm">
                {carbonMitigatedG.toLocaleString(undefined, { maximumFractionDigits: 1 })} mg CO₂
              </span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                (Overall saving: {carbonPercent}%)
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Sustainable Ledger Footer */}
      <div className="border-t border-slate-900 pt-3 mt-4 text-[10px] font-mono text-slate-500 flex justify-between">
        <span>Green Software Engineering Metrics</span>
        <span className="text-cyan-455 flex items-center gap-1 font-semibold text-cyan-400">
          <Sparkles className="w-3 h-3 text-yellow-400 animate-spin" /> EST. REDUCTION: 34.7%
        </span>
      </div>
      
    </div>
  );
}
