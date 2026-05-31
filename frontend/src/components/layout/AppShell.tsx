import { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { DemoBanner } from "./DemoBanner";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative z-10 flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <DemoBanner />
        <main className="flex-1 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}
