import React from "react";
import { 
  ShieldCheck, 
  Terminal, 
  Network, 
  ShieldAlert, 
  CreditCard, 
  Settings, 
  Activity, 
  Cpu, 
  FileText,
  LayoutDashboard,
  Grid3x3,
  MonitorDot
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isDarkMode: boolean;
  systemName: string;
}

export default function Sidebar({ activeTab, setActiveTab, isDarkMode, systemName }: SidebarProps) {
  const tabs = [
    { id: "dashboard", label: "Dashboard", desc: "Observability Metrics", icon: Activity },
    { id: "playground", label: "AI Playground", desc: "Sovereign Query Engine", icon: Terminal },
    { id: "security", label: "Identity & Security", desc: "API Vault & Kill Switch", icon: ShieldAlert },
    { id: "workspace", label: "Workspace & Cost", desc: "Quota Budget Rules", icon: CreditCard },
    { id: "pipelines", label: "Pipelines & Route", desc: "Canary Deployments", icon: Network },
    { id: "gpc", label: "GPC Controller", desc: "Air Gap Flight Systems", icon: Cpu },
    { id: "command-center", label: "Command Center", desc: "Sovereign Operations", icon: LayoutDashboard },
    { id: "irongrid", label: "PYO3 IronGrid", desc: "FFI Gradient Pathfinding", icon: Grid3x3 },
    { id: "terminal", label: "Quantum Terminal", desc: "UACP Context Engine", icon: MonitorDot }
  ];

  return (
    <div className={`w-full lg:w-72 flex flex-col gap-5 p-6 rounded-3xl border ${
      isDarkMode 
        ? "bg-zinc-950/40 border-zinc-900 text-zinc-100" 
        : "bg-white border-zinc-200 text-zinc-900"
    }`}>
      <div className="flex items-center gap-3 pb-4 border-b border-zinc-800/40">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shrink-0 shadow-md shadow-indigo-600/20">
          <ShieldCheck className="w-5 h-5 animate-pulse" />
        </div>
        <div className="overflow-hidden">
          <h2 className="text-sm font-bold truncate tracking-tight">{systemName}</h2>
          <span className="text-[10px] text-zinc-550 block font-semibold truncate leading-tight uppercase tracking-wider">
            Sovereign Control Node
          </span>
        </div>
      </div>

      <nav className="flex flex-col gap-1.5 flex-1">
        {tabs.map((tab) => {
          const IconComponent = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full text-left p-3.5 rounded-2xl flex items-start gap-3 transition-all cursor-pointer group relative ${
                isActive 
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10" 
                  : isDarkMode 
                    ? "hover:bg-zinc-900/60 text-zinc-400 hover:text-zinc-200" 
                    : "hover:bg-zinc-50 text-zinc-600 hover:text-zinc-900"
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-3.5 bottom-3.5 w-1 bg-white rounded-r"></div>
              )}
              <IconComponent className={`w-5 h-5 shrink-0 mt-0.5 ${isActive ? "text-white" : "text-indigo-400 group-hover:text-indigo-300"}`} />
              <div className="overflow-hidden">
                <p className="text-xs font-bold leading-tight tracking-tight">{tab.label}</p>
                <p className={`text-[10px] mt-0.5 font-medium leading-none truncate ${isActive ? "text-indigo-200" : "text-zinc-500"}`}>
                  {tab.desc}
                </p>
              </div>
            </button>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-zinc-805/40 text-center">
        <p className="text-[9px] text-zinc-500 font-mono tracking-wide leading-tight">
          Veklom Sovereign OS v1.0.0<br/>
          Secured with Merkle Ledger v6
        </p>
      </div>
    </div>
  );
}
