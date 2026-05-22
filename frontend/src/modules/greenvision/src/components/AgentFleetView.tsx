// @ts-nocheck
import React, { useState, useEffect } from 'react';

interface Agent {
  number: number;
  codename: string;
  group: string;
  tier: string;
  status: string;
  governance: { trust_score: number };
}

export const AgentFleetView: React.FC = () => {
    const [agents, setAgents] = useState<Agent[]>([]);
    
    useEffect(() => {
        fetch('/api/v1/agents')
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error ${res.status}`);
                }
                const contentType = res.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    throw new Error("Response is not JSON");
                }
                return res.json();
            })
            .then(data => {
                if (data) {
                    setAgents(data);
                }
            })
            .catch(console.error);
    }, []);

    const opAgents = agents.filter(a => a.tier === 'OPERATIONAL');
    const controlAgents = agents.filter(a => a.tier === 'CONTROL' || a.tier === 'SPECIAL');

    return (
        <div className="bg-[#0b1219]/60 border border-white/5 rounded-2xl p-5 backdrop-blur-3xl">
            <div className="text-[10px] tracking-[0.3em] text-white/90 font-black mb-6 uppercase flex justify-between">
                <span>Fleet Management</span>
                <span className="text-cyan-500">{agents.length} AGENTS TOTAL</span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                    <div className="text-[8px] text-white/40 uppercase">Operational</div>
                    <div className="text-xl font-black text-white">{opAgents.length}</div>
                </div>
                <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                    <div className="text-[8px] text-white/40 uppercase">Governance/Control</div>
                    <div className="text-xl font-black text-white">{controlAgents.length}</div>
                </div>
            </div>

            <div className="space-y-2 h-[200px] overflow-y-auto scrollbar-hide">
                {agents.slice(0, 10).map(a => (
                    <div key={a.number} className="flex justify-between items-center bg-white/[0.02] p-2 rounded text-[10px]">
                        <span className="font-mono text-cyan-400">{a.codename}</span>
                        <span className="text-white/60">{a.group}</span>
                        <span className="text-green-500 font-bold">{a.governance.trust_score.toFixed(0)}% trust</span>
                    </div>
                ))}
            </div>

            <div className="mt-6 p-4 bg-cyan-950/20 border border-cyan-900/50 rounded-xl">
                <div className="text-cyan-400 font-bold text-[10px] mb-2 uppercase tracking-wide">Helper Box: Optimization Recommedations</div>
                <p className="text-[9px] text-white/60">
                    To increase agent trust, increase the regularity of "Zeno interrogation" cycles for Phase Engineering agents. 
                    Monitor trust score decay in HRM-Workforce agents and trigger automated retraining.
                </p>
            </div>
        </div>
    );
};
