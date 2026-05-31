import { Router, Switch, Route } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { AppShell } from "@/components/layout/AppShell";
import LoginPage from "@/pages/Login";
import Overview from "@/pages/Overview";
import Playground from "@/pages/Playground";
import Marketplace from "@/pages/Marketplace";
import MarketplaceListing from "@/pages/MarketplaceListing";
import Models from "@/pages/Models";
import Pipelines from "@/pages/Pipelines";
import Deployments from "@/pages/Deployments";
import Routing from "@/pages/Routing";
import Monitoring from "@/pages/Monitoring";
import Vault from "@/pages/Vault";
import Compliance from "@/pages/Compliance";
import Billing from "@/pages/Billing";
import Team from "@/pages/Team";
import Settings from "@/pages/Settings";
import CommandCenter from "@/pages/CommandCenter";
import GpcTerminal from "@/pages/GpcTerminal";
import GpcPage from "@/pages/Gpc";
import Agents from "@/pages/Agents";
import NotFound from "@/pages/NotFound";
import { useAuth } from "@/hooks/useAuth";
import { IS_DEMO_MODE } from "@/lib/env";

function ProtectedRoutes() {
  const { authenticated, loading } = useAuth();

  // In demo mode we let users browse the dashboard without auth so they can
  // see the shape of the product. Real backends require login.
  if (!IS_DEMO_MODE && !authenticated && !loading) {
    return <LoginPage />;
  }

  return (
    <AppShell>
      <Switch>
        <Route path="/" component={Overview} />
        <Route path="/playground" component={Playground} />
        <Route path="/marketplace" component={Marketplace} />
        <Route path="/marketplace/:id" component={MarketplaceListing} />
        <Route path="/models" component={Models} />
        <Route path="/pipelines" component={Pipelines} />
        <Route path="/deployments" component={Deployments} />
        <Route path="/routing" component={Routing} />
        <Route path="/monitoring" component={Monitoring} />
        <Route path="/vault" component={Vault} />
        <Route path="/compliance" component={Compliance} />
        <Route path="/gpc" component={GpcPage} />
        <Route path="/agents" component={Agents} />
        <Route path="/billing" component={Billing} />
        <Route path="/team" component={Team} />
        <Route path="/settings" component={Settings} />
        <Route path="/command-center" component={CommandCenter} />
        <Route path="/terminal" component={GpcTerminal} />
        <Route component={NotFound} />
      </Switch>
    </AppShell>
  );
}

export default function App() {
  return (
    <Router hook={useHashLocation}>
      <Switch>
        <Route path="/login" component={LoginPage} />
        <Route>{() => <ProtectedRoutes />}</Route>
      </Switch>
    </Router>
  );
}
