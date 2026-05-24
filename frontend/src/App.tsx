import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  Settings, 
  User, 
  Activity, 
  RefreshCw 
} from "lucide-react";
import Sidebar from "./components/Sidebar";
import DashboardTab from "./components/DashboardTab";
import PlaygroundTab from "./components/PlaygroundTab";
import SecurityTab from "./components/SecurityTab";
import WorkspaceTab from "./components/WorkspaceTab";
import PipelinesTab from "./components/PipelinesTab";
import GpcTab from "./components/GpcTab";
import { api } from "./services/api";

export default function App() {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);
  const [workspaceName, setWorkspaceName] = useState<string>("Veklom Baltic Mainframe");
  const [systemUptime, setSystemUptime] = useState<string>("Uptime: Checking...");
  const [byosConnected, setByosConnected] = useState<boolean>(false);
  const [byosUrl, setByosUrl] = useState<string>("");

  const syncDetails = async () => {
    // 1. Fetch BYOS config independently so the connection status indicator is always strictly aligned
    try {
      const byos = await api.getByosConfig();
      setByosConnected(byos.byosConnected);
      setByosUrl(byos.byosBackendUrl);
    } catch (err) {
      console.error("Veklom BYOS state check failed:", err);
    }

    // 2. Fetch workspace and health details separately
    try {
      const summary = await api.getWorkspaceOverview();
      setWorkspaceName(summary.workspace.name);
    } catch {
      setWorkspaceName("Veklom Baltic Mainframe");
    }

    try {
      const health = await api.getHealthDetailed();
      const minutes = Math.floor(health.uptimeSeconds / 60);
      setSystemUptime(`Uptime: ${minutes} min`);
    } catch {
      setSystemUptime("Uptime: Simulated");
    }
  };

  useEffect(() => {
    syncDetails();
    const interval = setInterval(syncDetails, 8000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const renderActiveTab = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardTab isDarkMode={isDarkMode} onNavigateToPlayground={() => setActiveTab("playground")} />;
      case "playground":
        return <PlaygroundTab isDarkMode={isDarkMode} />;
      case "security":
        return <SecurityTab isDarkMode={isDarkMode} />;
      case "workspace":
        return <WorkspaceTab isDarkMode={isDarkMode} />;
      case "pipelines":
        return <PipelinesTab isDarkMode={isDarkMode} />;
      case "gpc":
        return (
          <div className="w-full h-[calc(100vh-200px)] rounded-2xl overflow-hidden border border-zinc-800 bg-[#080b0f]">
            <iframe
              src="https://uacpv3.onrender.com?api_base=https%3A%2F%2Fveklom.com%2Fapi%2Fv1&source=veklom-byos-backend&provider=ollama&public_demo=1"
              className="w-full h-full border-none"
              title="Veklom V3 Governed Plan Compiler"
              loading="lazy"
            />
          </div>
        );
      case "command-center":
        return (
          <div className="w-full h-[calc(100vh-200px)] rounded-2xl overflow-hidden border border-zinc-800">
            <iframe src="/command-center/" className="w-full h-full border-none bg-[#0a0a0a]" title="Veklom Command Center" allow="clipboard-write" />
          </div>
        );
      case "irongrid":
        return (
          <div className="w-full h-[calc(100vh-200px)] rounded-2xl overflow-hidden border border-zinc-800">
            <iframe src="/irongrid/" className="w-full h-full border-none bg-[#0a0a0a]" title="PYO3 IronGrid Simulator" />
          </div>
        );
      case "terminal":
        return (
          <div className="w-full h-[calc(100vh-200px)] rounded-2xl overflow-hidden border border-zinc-800">
            <iframe src="/uacp-quantum-terminal.html" className="w-full h-full border-none bg-[#0a0a0a]" title="UACP Quantum Terminal" />
          </div>
        );
      default:
        return <DashboardTab isDarkMode={isDarkMode} onNavigateToPlayground={() => setActiveTab("playground")} />;
    }
  };

  return (
    <div className={`min-h-screen font-sans transition-all duration-300 ${
      isDarkMode ? "bg-[#060606] text-zinc-100" : "bg-zinc-50 text-zinc-900"
    }`}>
      
      {/* Top Header Controls bar */}
      <header className={`border-b sticky top-0 z-40 backdrop-blur-md ${
        isDarkMode ? "bg-[#060606]/80 border-zinc-900" : "bg-white/80 border-zinc-200"
      }`}>
        <div className="max-w-7xl mx-auto px-6 py-4.5 flex flex-col md:flex-row items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-tr from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-600/10">
              <ShieldCheck className="w-5.5 h-5.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-black tracking-tight font-sans">
                  Veklom Sovereign AI Hub
                </h1>
                <span className="text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-1.5 py-0.5 rounded font-bold font-mono">
                  OAS 3.1 COMPLIANT
                </span>
              </div>
              <p className="text-[10px] text-zinc-500 mt-0.5 font-medium">
                Unified security interface managing {workspaceName}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-bold">
            
            {/* BYOS Status Indicator Pill */}
            <div 
              onClick={() => setActiveTab("workspace")}
              title={byosConnected ? `Active alignment tunnel connection to Veklom BYOS backend at: ${byosUrl}` : "Simulated offline sandbox database"}
              className={`px-3 py-1.5 rounded-lg border text-[10px] uppercase font-mono tracking-wider cursor-pointer hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center gap-1.5 ${
                byosConnected 
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                  : isDarkMode ? "bg-amber-500/10 border-amber-500/20 text-text-amber-400/90 text-amber-400" : "bg-amber-100 border-amber-300 text-amber-800"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${byosConnected ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              {byosConnected ? "BYOS: Aligned" : "BYOS: Sandboxed"}
            </div>

            {/* Uptime */}
            <div className={`px-3 py-1.5 rounded-lg border text-[10px] uppercase font-mono tracking-wider ${
              isDarkMode ? "bg-zinc-950 border-zinc-800 text-zinc-400" : "bg-zinc-100 border-zinc-200 text-zinc-600"
            }`}>
              {systemUptime}
            </div>

            <button 
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`px-4 py-1.5 border hover:scale-[1.01] active:scale-[0.99] transition-all rounded-xl text-xs font-bold tracking-tight cursor-pointer ${
                isDarkMode 
                  ? "bg-zinc-900 hover:bg-zinc-850 border-zinc-800 text-zinc-300" 
                  : "bg-white hover:bg-zinc-50 border-zinc-200 text-zinc-700"
              }`}
            >
              Theme: {isDarkMode ? "Dark" : "Light"}
            </button>

            <div className="w-px h-6 bg-zinc-800/60 hidden sm:block"></div>

            {/* Profile widget */}
            <div className="flex items-center gap-2">
              <div className="text-right hidden sm:block">
                <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest leading-none">Admin Profile</p>
                <p className="text-[11px] text-zinc-300 mt-0.5 leading-none font-semibold">chomp.pixel@gmail.com</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 shadow border border-indigo-500/20"></div>
            </div>

          </div>
        </div>
      </header>

      {/* Main responsive grid workspace */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex flex-col lg:flex-row gap-6">
        
        {/* Left column navigation panel (Sidebar scales to 72px / full on desktop) */}
        <Sidebar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          isDarkMode={isDarkMode} 
          systemName={workspaceName}
        />

        {/* Right column active workspace View */}
        <div className="flex-1 flex flex-col gap-6" id="workspace-content-pane">
          {renderActiveTab()}
        </div>

      </main>

    </div>
  );
}
