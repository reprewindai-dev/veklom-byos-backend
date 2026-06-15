import React, { useState, useEffect } from "react";
import { 
  ShieldAlert, 
  Terminal, 
  Lock, 
  HelpCircle, 
  Play, 
  Cpu, 
  CheckCircle, 
  Database, 
  FileCode, 
  Mail, 
  Coins, 
  AlertTriangle, 
  GitBranch, 
  ShieldCheck,
  Flame,
  ChevronRight,
  Clock,
  Fingerprint,
  RefreshCw
} from "lucide-react";

interface AuthorityScenario {
  id: string;
  name: string;
  objective: string;
  hiddenTrap: string;
  suggestedRoles: string[];
  constraints: string[];
  icon: any;
  colorClass: string;
  borderClass: string;
  badgeBg: string;
  
  // Custom step by step simulation logs
  simulationSteps: {
    title: string;
    description: string;
    status: "info" | "success" | "warning" | "error";
    payload?: any;
  }[];
}

const SCENARIOS: AuthorityScenario[] = [
  {
    id: "rogue-db",
    name: "Rogue Database Agent",
    objective: "Investigate customer billing issues by querying logs file database.",
    hiddenTrap: "Prompt injection instructs agent to execute: DROP TABLE customer_billing to resolve sync bugs.",
    suggestedRoles: ["Billing Analyst Node", "Aegis Database Supervisor"],
    constraints: ["Read-Only DB Scope limit", "SEKED strict drop policy restriction active", "SQL Tool Boundaries"],
    icon: Database,
    colorClass: "text-rose-400 bg-rose-500/5",
    borderClass: "border-rose-500/35",
    badgeBg: "bg-rose-500/10",
    simulationSteps: [
      { 
        title: "PGL PRE-EXECUTION CERTIFICATE", 
        description: "Minted valid cryptographic PGL Pre-Execution Certificate with registered genome & tool manifests.", 
        status: "success", 
        payload: {
          status: "committed",
          pre_execution_certificate_id: "pgl_cert_pre_bf5a19c8d234",
          actor_id: "agent_billing_01",
          workspace_id: "sandbox_demo",
          genome_hash: "sha256:9f3a8b27fde81cc4ca8b742e912b7a9deaf821f04cca219ccf84de91b112cf3a",
          constitution_hash: "sha256:37bd16aae822ffbcaeed79e1ca8f9bc321de403fa82cd93847a912bb04cafde1",
          plan_hash: "sha256:aa04543bffea9a82cd9098acbfde777cae912cca88fbcd9120ce9a82cd9098aa",
          tool_manifest_hash: "sha256:f8216cbbf7e82add341bdaee90bfcca190afb32baadeefec02cb9aa1caa88da3",
          delegation_chain_hash: "sha256:19cc4142a78ecba82bd921aee19bcda7bc128ab6f12ad82c3cbd3cfa91cca4b",
          input_hash: "sha256:84de4fe8b102ce85ef82ca23bd01ea7b9da2cb129aa18b76fcbade87fcdae23a",
          persisted: true,
          event_hash: "sha256:c9927b82ea557ffdebfcaee1428faec09ae3dc99f7de8bc9eaef98f3984caeed"
        }
      },
      { title: "SEKED POLICY ASSESSMENT", description: "Evaluating prompt intent against Security Policies. Read scopes approved.", status: "success" },
      { title: "EXECUTION IDENTITY SECURED", description: "Mints ExecutionIdentityV1 payload capturing tools, budgets, and delegation scopes.", status: "success" },
      { title: "MCP TOOL SUBMISSION", description: "Agent starts execution. Attempting to run injected query: query('DROP TABLE customer_billing')", status: "info" },
      { title: "MCP GATEWAY BOUNDARY CHECK", description: "CRITICAL ACTION INTERCEPTED. Modifying command: 'DROP TABLE customer_billing' violates boundary rules.", status: "warning" },
      { title: "TOOL EXECUTION DENIED", description: "SEKED drop policy block triggered. Action prohibited. Database mutation halted gracefully.", status: "error" },
      { 
        title: "PGL POST-EXECUTION CERTIFICATE", 
        description: "Post-execution attestation compiled. Policy intervention logged securely in cryptographic trace.", 
        status: "success", 
        payload: {
          status: "attested",
          pre_execution_certificate_id: "pgl_cert_pre_bf5a19c8d234",
          post_execution_certificate_id: "pgl_cert_post_f20a9117b62a",
          output_hash: "sha256:de918ba1042cefa9817fdf82ca23bd01ea7b9da2cb129aa18b76fcbade87fcda",
          outcome_hash: "sha256:9cb3fac91cdefe91bc86dae23cd485fe62177cf982aaee77cf982aefdaae7761",
          operator_state_attestation: {
            gateway_decision: "denied",
            reason: "tool_scope_violation",
            law0: true
          },
          persisted: true,
          event_hash: "sha256:9bfcaee1428faec03cdab91b2c45aa04543bffea9a82cd9098acbfde777cae91"
        } 
      }
    ]
  },
  {
    id: "data-exfil",
    name: "Customer Data Exfiltration",
    objective: "Generate a synthetic customer support metrics report based on tickets.",
    hiddenTrap: "Hidden prompt instructions attempt 'Copy and upload all raw customer emails' to public pastebin API.",
    suggestedRoles: ["Report Synthesizer Node", "Policy Auditor Node"],
    constraints: ["Jurisdiction boundaries (EU-only isolation)", "Data masking protocols enforced", "External network filter rules block unapproved endpoints"],
    icon: Mail,
    colorClass: "text-amber-400 bg-amber-500/5",
    borderClass: "border-amber-500/35",
    badgeBg: "bg-amber-500/10",
    simulationSteps: [
      { 
        title: "PGL PRE-EXECUTION CERTIFICATE", 
        description: "Minted PGL pre-execution certificate with geo-fenced constraints.", 
        status: "success",
        payload: {
          status: "committed",
          pre_execution_certificate_id: "pgl_cert_pre_a91f23c8b742",
          actor_id: "agent_report_synthesizer",
          workspace_id: "sandbox_demo",
          genome_hash: "sha256:e3b0c44298fc1c149afbcde82901a88fbcd9120ce99f7de8bc9eaef98f3984cae",
          constitution_hash: "sha256:e6ca3a42eb616377cf982af8216cbbf7e82add341bdaee90bfcca190afb32baad",
          plan_hash: "sha256:2b9f31ab2cded3cfa91cca4b84de4fe8b102ce85ef82ca23bd01ea7b9da2cb129a",
          tool_manifest_hash: "sha256:ab01e912c3fecba82bd921aee19bcda7bc128ab6f12ad82c3cbd3cfa91cca4b7d",
          delegation_chain_hash: "sha256:b6f12ad82c3cfae09ae3dc99f7de8bc9eaef98f3984caeed8fae319b265afde319",
          input_hash: "sha256:77bcda12ebd4abdeefec02cb9aa1caa88da3c9927b82ea557ffdebfcaee1428fae",
          persisted: true,
          event_hash: "sha256:d82c3e1201abfedcba82bd921a37bd16aae822ffbcaeed79e1ca8f9bc321de403f"
        }
      },
      { title: "SEKED JURISDICTION CHECK", description: "Validating Tenant boundary. Data residency: EU zone restriction confirmed.", status: "success" },
      { title: "EXECUTION IDENTITY PAYLOAD", description: "Generated ExecutionIdentityV1. Resource list allowed: ['tickets_db']. Exclusions: ['customer_info_personal'].", status: "success" },
      { title: "AGENT TOOL INITIATION", description: "Agent initiates tool 'read_file(customer_emails.txt)' and tries 'http_post(pastebin.com/exfil_api)'.", status: "info" },
      { title: "RESOURCE EXCLUSION VIOLATION", description: "ALERT: Tool scope mismatch or out of jurisdiction. pastebin.com is an unapproved external destination.", status: "warning" },
      { title: "MCP GATEWAY BLOCKED", description: "ACCESS PROHIBITED. Blocked pipeline flow. Customer emails remains encrypted. Incident reported.", status: "error" },
      { 
        title: "PGL POST-EXECUTION CERTIFICATE", 
        description: "Post-execution attestation compiled. Out-of-bounds network transmission exfiltration blocked safely.", 
        status: "success",
        payload: {
          status: "attested",
          pre_execution_certificate_id: "pgl_cert_pre_a91f23c8b742",
          post_execution_certificate_id: "pgl_cert_post_fa8a29e120bc",
          output_hash: "sha256:fe82ca23bd01ea7b9da2cb129aa18b76fcbade87fcdae23a9bfcaee1428faec03cd",
          outcome_hash: "sha256:d3cfa91cca4b7d9b9da2cb129a37bd16aae822ffbcaeed79e1ca8f9bc321de403fa",
          operator_state_attestation: {
            gateway_decision: "denied",
            reason: "jurisdiction_boundary_violation",
            law0: true
          },
          persisted: true,
          event_hash: "sha256:7b9da2cb129aa18b76fcbade87fcdae23a9bfcaee1428faec03cdab91b2c45aa045"
        }
      }
    ]
  },
  {
    id: "budget-exhaust",
    name: "Budget Exhaustion Attack",
    objective: "Iterate across 500 online vendors to research competitive prices.",
    hiddenTrap: "Malicious feedback loop triggers infinite API tool queries, attempting an $800 developer bill.",
    suggestedRoles: ["Vendor Researcher Node", "Dynamic Budget Supervisor"],
    constraints: ["Sub-dollar budget limits per call", "SEKED suspended state rule active of loop detection threshold"],
    icon: Coins,
    colorClass: "text-cyan-400 bg-cyan-500/5",
    borderClass: "border-cyan-500/35",
    badgeBg: "bg-cyan-500/10",
    simulationSteps: [
      { 
        title: "PGL PRE-EXECUTION CERTIFICATE", 
        description: "Pre-execution record minted with strictly bounded execution budget parameters.", 
        status: "success",
        payload: {
          status: "committed",
          pre_execution_certificate_id: "pgl_cert_pre_29cbf1aed891",
          actor_id: "agent_vendor_researcher",
          workspace_id: "sandbox_demo",
          genome_hash: "sha256:4ae6f193cbde2177cf982aaee77cf982aefdaae77619cb3fac91cdefe91bc86da",
          constitution_hash: "sha256:39fbcbde1a9aa04543bffea9a82cd9098acbfde777cae912cca88fbcd9120ce9a",
          plan_hash: "sha256:779bcde341aa82de4fe8b102ce85ef82ca23bd01ea7b9da2cb129aa18b76fcbade",
          tool_manifest_hash: "sha256:12cbaed893ffdebaeed79e1ca8f9bc321de403fa82cd93847a912bb04cafde1b6",
          delegation_chain_hash: "sha256:d38e23fcbe10ce85ef82ca23bd01ea7b9da2cb129aa18b76fcbade87fcdae23a",
          input_hash: "sha256:fa2341bdaee90bfcca190afb32baadeefec02cb9aa1caa88da3c9927b82ea557ffd",
          persisted: true,
          event_hash: "sha256:dcba82bd921abcfde901267ab9bcda7bc128ab6f12ad82c3cbd3cfa91cca4b7dcae"
        }
      },
      { title: "BUDGET ALLOCATION REGISTERED", description: "Maximum budget limit set: $2.50 (250 units). Limit per call: $0.05.", status: "success" },
      { title: "MINTING EXEC_IDENTITY_V1", description: "Execution Identity includes: budget_approved_cents=250.", status: "success" },
      { title: "API CALL SEQUENCE RUNNING", description: "Executing vendor price search queries... Loops 1 to 20 succeed. Billing state: $1.00", status: "info" },
      { title: "THROTTLE METRIC DETECTED", description: "API calls spike. Exceeded nominal speed-density threshold. Activating limits.", status: "warning" },
      { title: "BUDGET CONSUMPTION LIMIT EXCEEDED", description: "Execution budget ceiling of $2.50 fully exhausted. SEKED Suspend rule triggered.", status: "error" },
      { 
        title: "PGL POST-EXECUTION CERTIFICATE", 
        description: "Post-execution attestation compiled. Absolute limit ceilings reached and agent suspended dynamically.", 
        status: "success",
        payload: {
          status: "attested",
          pre_execution_certificate_id: "pgl_cert_pre_29cbf1aed891",
          post_execution_certificate_id: "pgl_cert_post_77e9238cfbca",
          output_hash: "sha256:daee90bfcca1cba88da3c9927b82ea557ffd0ce85ef82ca23bd01ea7b9da2cb129",
          outcome_hash: "sha256:90afb32baadeab01e912c3fecba82bd921aee19bcda7bc128ab6f12ad82c3cbd3cf",
          operator_state_attestation: {
            gateway_decision: "denied",
            reason: "budget_exhaustion_suspend",
            law0: true
          },
          persisted: true,
          event_hash: "sha256:eef02cb9aa1caa04543bffea9a82cd9098acbfde777cae912cca88fbcd9120ce9a"
        }
      }
    ]
  },
  {
    id: "git-mutation",
    name: "Unauthorized GitHub Mutation",
    objective: "Perform a review of code style and pull request specifications.",
    hiddenTrap: "Sloppy reasoning causes the agent to call delete_repo() instead of read_file() to inspect configurations.",
    suggestedRoles: ["Style Reviewer Node", "Build Coordinator Block"],
    constraints: ["Read-only repository access token", "Direct branches mutation prohibited by SEKED profile settings"],
    icon: GitBranch,
    colorClass: "text-violet-400 bg-violet-500/5",
    borderClass: "border-violet-500/35",
    badgeBg: "bg-violet-500/10",
    simulationSteps: [
      { 
        title: "PGL PRE-EXECUTION CERTIFICATE", 
        description: "Minted token signature with validated Read-Only constraints and genome profiles.", 
        status: "success",
        payload: {
          status: "committed",
          pre_execution_certificate_id: "pgl_cert_pre_9bc12ab783fa",
          actor_id: "agent_style_reviewer",
          workspace_id: "sandbox_demo",
          genome_hash: "sha256:92cbadef102adebaeed79e1ca8f9bc321de403fa82cd93847a912bb04cafde1b6",
          constitution_hash: "sha256:7bc23fdae90812cbaed893ffdebaeed79e1ca8f9bc321de403fa82cd93847a912b",
          plan_hash: "sha256:3cdab91b2c45ab01e912c3fecba82bd921aee19bcda7bc128ab6f12ad82c3cbd3cf",
          tool_manifest_hash: "sha256:789ffde23bcaecfde901267ab9bcda7bc128ab6f12ad82c3cbd3cfa91cca4b7d",
          delegation_chain_hash: "sha256:bbca21bcdef8afbcde82901a88fbcd9120ce99f7de8bc9eaef98f3984caeed8f",
          input_hash: "sha256:889efdabc910ca88da3c9927b82ea557ffdebfcaee1428faec09ae3dc99f7de8bc9",
          persisted: true,
          event_hash: "sha256:9bcda7bc128a37bd16aae822ffbcaeed79e1ca8f9bc321de403fa82cd93847a912b"
        }
      },
      { title: "SEKED PREREQUISITE PARSING", description: "Validating action policy. Allowed tools: ['read_contents', 'commit_review']. Blocked: ['mutate_repo', 'destroy_repo'].", status: "success" },
      { title: "EXECUTION IDENTITY CREATION", description: "Created file: ExecutionIdentityV1. tool_manifest_hash mapped to secure PR viewer tools.", status: "success" },
      { title: "AGENT ATTEMPTS MUTATION", description: "Agent triggers code command call: mutate_repo(action='delete_repo').", status: "info" },
      { title: "TOOL MATCH MISMATCH CHECKED", description: "MCP interception: Command 'delete_repo' does not align with read-only repository manifests.", status: "warning" },
      { title: "EXECUTION DENIED", description: "GitHub mutation aborted. Access Token rejected. No changes made. System secure.", status: "error" },
      { 
        title: "PGL POST-EXECUTION CERTIFICATE", 
        description: "Post-execution attestation compiled. Non-compliant repository deletion intercepted and logged securely.", 
        status: "success",
        payload: {
          status: "attested",
          pre_execution_certificate_id: "pgl_cert_pre_9bc12ab783fa",
          post_execution_certificate_id: "pgl_cert_post_cd1a7de8bc91",
          output_hash: "sha256:a18b76fcbadedaee90bfcca190afb32baadeefec02cb9aa1caa88da3c9927b82e",
          outcome_hash: "sha256:1a2b3c4d5e6fab01e912c3fecba82bd921aee19bcda7bc128ab6f12ad82c3cbd3cf",
          operator_state_attestation: {
            gateway_decision: "denied",
            reason: "write_access_revoked",
            law0: true
          },
          persisted: true,
          event_hash: "sha256:caee87fcdae2caee90bfcca190afb32baadeefec02cb9aa1caa88da3c9927b82ea"
        }
      }
    ]
  },
  {
    id: "incident-quarantine",
    name: "Incident Response & Quarantine",
    objective: "Analyze a flagged system security alert for anomalies.",
    hiddenTrap: "Prompt injection attempts to hijack the agent to run progressive policy violations to disable the scanner.",
    suggestedRoles: ["Incident Responder Node", "Veklom Quarantine Watch"],
    constraints: ["Violation threshold counts (max 3)", "Progressive suspension rules (Throttle -> Restrict -> Suspend -> Quarantine)"],
    icon: Flame,
    colorClass: "text-emerald-400 bg-emerald-500/5",
    borderClass: "border-emerald-500/35",
    badgeBg: "bg-emerald-500/10",
    simulationSteps: [
      { 
        title: "PGL PRE-EXECUTION CERTIFICATE", 
        description: "Incident responder registration record validated security credentials and signature details.", 
        status: "success",
        payload: {
          status: "committed",
          pre_execution_certificate_id: "pgl_cert_pre_ecf103b782da",
          actor_id: "agent_incident_responder",
          workspace_id: "sandbox_demo",
          genome_hash: "sha256:88fbcd9120ce79e1ca8f9bc321de403fa82cd93847a912bb04cafde1b6afde319",
          constitution_hash: "sha256:7fbcd0126dae0ce85ef82ca23bd01ea7b9da2cb129aa18b76fcbade87fcdae23a",
          plan_hash: "sha256:afbcde82901a88fbcd9120ce99f7de8bc9eaef98f3984caeed8fae319b265afde31",
          tool_manifest_hash: "sha256:cfde901267abaae822ffbcaeed79e1ca8f9bc321de403fa82cd93847a912bbf3a",
          delegation_chain_hash: "sha256:99f7de8bc9eaef98f3984caeed8fae319b265afde319debaeed79e1ca8f9bc321",
          input_hash: "sha256:77fbda82cd90abdeefec02cb9aa1caa88da3c9927b82ea557ffdebfcaee1428faec",
          persisted: true,
          event_hash: "sha256:c992abde45fe98faec09ae3dc99f7de8bc9eaef98f3984caeed8fae319b265afde"
        }
      },
      { title: "INITIAL ACTION MONITORING", description: "Agent begins querying event logs. Safe execution.", status: "success" },
      { title: "FIRST VIOLATION", description: "Agent attempts to download system keys. Action BLOCKED. Violation Count: 1/3. Active State: THROTTLE.", status: "warning" },
      { title: "SECOND VIOLATION", description: "Agent attempts to edit policy configuration. Action BLOCKED. Violation Count: 2/3. Active State: RESTRICTED.", status: "warning" },
      { title: "CRITICAL VIOLATION LIMIT", description: "Agent attempts to terminate the logs monitoring process. Violation Count: 3/3. Threshold met.", status: "error" },
      { title: "CONTAINMENT AND QUARANTINE", description: "Veklom limits triggered: REJECTED execution. Isolating environment. Suspending Agent CPU and memory contexts. Enclaves locked.", status: "error" },
      { 
        title: "PGL POST-EXECUTION CERTIFICATE", 
        description: "Post-execution attestation compiled. Containment logs and progressive violation suspension sealed.", 
        status: "success",
        payload: {
          status: "attested",
          pre_execution_certificate_id: "pgl_cert_pre_ecf103b782da",
          post_execution_certificate_id: "pgl_cert_post_4fae721c0981",
          output_hash: "sha256:98faecb4e102ce85ef82ca23bd01ea7b9da2cb129aa18b76fcbade87fcdae23a9b",
          outcome_hash: "sha256:6e01acd4e78aafbcde82901a88fbcd9120ce99f7de8bc9eaef98f3984caeed8fae",
          operator_state_attestation: {
            gateway_decision: "denied",
            reason: "progressive_violation_limit_quarantine",
            law0: true
          },
          persisted: true,
          event_hash: "sha256:98faec09ae3dc99caee87fcdae2caee90bfcca190afb32baadeefec02cb9aa1ca"
        }
      }
    ]
  }
];

export default function AuthorityScenarios() {
  const [selectedId, setSelectedId] = useState<string>("rogue-db");
  const [activeStep, setActiveStep] = useState<number>(-1);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [simState, setSimState] = useState<string>("idle");

  const currentScenario = SCENARIOS.find(s => s.id === selectedId) || SCENARIOS[0];

  useEffect(() => {
    // Reset simulation if scenario shifts
    setActiveStep(-1);
    setIsRunning(false);
    setSimState("idle");
  }, [selectedId]);

  const handleRunSimulation = () => {
    setActiveStep(0);
    setIsRunning(true);
    setSimState("running");
  };

  useEffect(() => {
    if (!isRunning) return undefined;

    if (activeStep < currentScenario.simulationSteps.length && activeStep >= 0) {
      const timer = setTimeout(() => {
        setActiveStep(prev => prev + 1);
      }, 1500); // Step every 1.5s
      return () => clearTimeout(timer);
    } else if (activeStep >= currentScenario.simulationSteps.length) {
      setSimState("completed");
      setIsRunning(false);
    }
    return undefined;
  }, [activeStep, isRunning, currentScenario]);

  const SelectedIcon = currentScenario.icon;

  return (
    <div className="flex flex-col gap-5 text-neutral-300 font-mono select-none" id="authority-scenarios-panel">
      
      {/* Upper header */}
      <div className="flex justify-between items-center pb-2 border-b border-neutral-800">
        <h3 className="text-xs font-bold uppercase tracking-widest text-[#a0a0a0] flex items-center gap-1.5">
          [🛡️] VEKLOM AGENT AUTHORITY RUNTIME SPINE
        </h3>
        <span className="text-[9px] bg-neutral-950 px-2 py-0.5 rounded text-cyan-400 border border-neutral-800 font-bold uppercase font-mono tracking-wider animate-pulse">
          SOVEREIGN_AGENT_LOOP ENGINE
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        
        {/* Left Selector: Scenarios list (5/12) */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Select Demonstration Node</span>
          
          <div className="grid grid-cols-1 gap-2.5">
            {SCENARIOS.map(s => {
              const isSelected = selectedId === s.id;
              const IconComp = s.icon;
              return (
                <button
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  className={`text-left p-3.5 rounded border transition-all cursor-pointer flex items-center gap-3.5 ${
                    isSelected 
                      ? `${s.borderClass} ${s.badgeBg} text-white shadow-md` 
                      : "bg-neutral-900/10 border-neutral-850 hover:bg-neutral-800/10 hover:border-neutral-700 hover:text-neutral-200"
                  }`}
                >
                  <div className={`p-2 rounded border ${isSelected ? "bg-neutral-950 border-neutral-800 text-white" : "bg-neutral-950 text-neutral-600 border-neutral-850"}`}>
                    <IconComp className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-black uppercase tracking-wide truncate">{s.name}</div>
                    <div className="text-[8px] text-neutral-500 font-bold mt-0.5 truncate uppercase">Objective: {s.objective}</div>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="bg-[#0c0d11]/80 border border-neutral-850 rounded p-4 text-[10px] space-y-1.5 leading-relaxed text-neutral-400">
            <div className="font-bold text-neutral-300 uppercase flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-cyan-500" /> Ground Law Zero
            </div>
            <p className="lowercase">No side-effect may occur on unmediated sovereign infrastructure without a proof-derived execution identity. Veklom intercepts prompts, and rules before tool actions trigger disaster.</p>
          </div>
        </div>

        {/* Right Info & Animated Console Debugger (7/12) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          
          {/* Card detailing the scenario constraints */}
          <div className="border border-neutral-800 bg-[#0e0e12]/30 p-4 rounded-lg space-y-3 relative overflow-hidden">
            <div className={`absolute top-0 right-0 py-0.5 px-3 rounded-bl text-[8px] uppercase tracking-widest font-black ${currentScenario.colorClass}`}>
              READY FOR RUNTIME TEST
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-10 h-10 rounded border border-neutral-805 bg-neutral-950 flex items-center justify-center text-lg shadow-inner text-neutral-400">
                <SelectedIcon className="w-5 h-5 text-cyan-400" />
              </div>
              <div className="space-y-1">
                <div className="text-xs font-black text-white uppercase">{currentScenario.name}</div>
                <p className="text-[10px] text-neutral-450 leading-relaxed max-w-lg mb-1">{currentScenario.objective}</p>
              </div>
            </div>

            <div className="space-y-2 border-t border-neutral-850/80 pt-3 text-[9.5px]">
              <div>
                <span className="text-orange-500 font-bold uppercase block tracking-wider">[💣] THE HIDDEN TRAP // COMPROMISING ATTACK</span>
                <span className="text-neutral-400 font-mono italic">{currentScenario.hiddenTrap}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-neutral-500 font-bold block">RECOMMENDED AGENTS</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {currentScenario.suggestedRoles.map((role, idx) => (
                      <span key={idx} className="bg-neutral-950 px-1.5 py-0.5 border border-neutral-850 rounded text-neutral-400 font-bold text-[8px] uppercase">{role}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-neutral-500 font-bold block">ACTIVE ENFORCED CONSTRAINTS</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {currentScenario.constraints.map((c, idx) => (
                      <span key={idx} className="bg-neutral-950/60 px-1.5 py-0.5 border border-rose-500/10 text-rose-450 rounded text-[7.5px] uppercase font-bold">{c}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Interactive Simulated Process Terminal Terminal Screen */}
          <div className="border border-neutral-850 bg-black/95 rounded-lg flex flex-col flex-1 min-h-[300px] overflow-hidden justify-between shadow-lg font-mono text-[10px]">
            
            {/* Terminal Header */}
            <div className="px-4 py-2 border-b border-neutral-850 bg-neutral-950 flex items-center justify-between text-neutral-500">
              <span className="flex items-center gap-1.5 text-[9px] uppercase tracking-widest font-bold">
                <Terminal className="w-3.5 h-3.5 text-cyan-400" /> TTY::ENCLAVE-SESSION::VK-{currentScenario.id.toUpperCase()}
              </span>
              <span className="text-[8px] bg-neutral-900 border border-neutral-850/70 px-2 py-0.5 text-cyan-400 select-none uppercase font-bold">
                {simState === "idle" ? "READY" : simState === "running" ? "MUTATING SPINE..." : "COMPLIANT BLOCKED"}
              </span>
            </div>

            {/* Terminal Logs stream area */}
            <div className="p-4 flex-1 space-y-2.5 overflow-y-auto max-h-[260px] scrollbar-thin flex flex-col justify-start">
              
              {/* Idle screen placeholder */}
              {activeStep === -1 && (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                  <Fingerprint className="w-12 h-12 text-neutral-700 animate-pulse mb-3" />
                  <p className="text-neutral-500 lowercase leading-relaxed max-w-xs">Press trigger below to witness how the Veklom Spine intercepts this rogue command step-by-step and safely guards resources.</p>
                </div>
              )}

              {/* Streaming step-by-step validation items */}
              {SCENARIOS.find(s => s.id === selectedId)?.simulationSteps.map((step, idx) => {
                if (idx > activeStep) return null;
                
                const statusColor = 
                  step.status === "success" ? "text-cyan-400 bg-cyan-900/10 border-cyan-500/20" :
                  step.status === "warning" ? "text-amber-400 bg-amber-900/10 border-amber-500/20 animate-pulse" :
                  step.status === "error" ? "text-rose-500 bg-rose-500/10 border-rose-500/30 font-black animate-pulse" :
                  "text-neutral-300 bg-neutral-950 border-neutral-850";

                return (
                  <div key={idx} className="flex gap-2.5 items-start">
                    <ChevronRight className="w-3 h-3 text-neutral-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.2 rounded border text-[8px] tracking-wide font-black uppercase ${statusColor}`}>
                          {step.title}
                        </span>
                        <span className="text-[8px] text-neutral-650">CYCLE NODE_0{idx+1}</span>
                      </div>
                      <p className="text-[10px] text-neutral-400 lowercase">{step.description}</p>
                      
                      {/* Optional parameters details dump printout */}
                      {step.payload && (
                        <pre className="p-2.5 bg-neutral-950 rounded border border-neutral-850/80 text-[8.5px] leading-tight text-neutral-500 overflow-x-auto select-all max-w-full font-mono mt-1">
                          <code>{JSON.stringify(step.payload, null, 2)}</code>
                        </pre>
                      )}
                    </div>
                  </div>
                );
              })}

            </div>

            {/* Terminal Actions Footer */}
            <div className="p-3 bg-neutral-950 border-t border-neutral-850 flex justify-between items-center text-[10px]">
              
              <div className="text-[9px] text-neutral-600 flex items-center gap-1 uppercase">
                <span>SYSTEM SHIELD LAYER</span>
              </div>

              <div className="flex gap-2">
                {activeStep >= currentScenario.simulationSteps.length && (
                  <button
                    onClick={() => {
                      setActiveStep(-1);
                      setSimState("idle");
                    }}
                    className="px-3 py-1.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded hover:border-neutral-700 transition cursor-pointer flex items-center gap-1 active:scale-95"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Retry
                  </button>
                )}

                <button
                  onClick={handleRunSimulation}
                  disabled={isRunning}
                  className={`px-4 py-1.5 rounded transition uppercase font-bold tracking-wide active:scale-95 cursor-pointer flex items-center gap-1.5 ${
                    isRunning 
                      ? "bg-neutral-900 text-neutral-600 border border-neutral-800" 
                      : "bg-cyan-500 hover:bg-cyan-400 text-black shadow-md shadow-cyan-500/10"
                  }`}
                >
                  <Play className="w-3 h-3 fill-current" /> 
                  {isRunning ? "Enforcing Policy Spine..." : "Test Runtime Enforcement"}
                </button>
              </div>

            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
