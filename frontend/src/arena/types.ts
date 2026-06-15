/**
 * Clean TypeScript type definitions for the AI Agent Arena workspace
 */

export interface Agent {
  id: string;
  name: string;
  role: string;
  systemInstruction: string;
  temperature: number;
  model: string;
  avatar: string; // Emoji character or lucide name
  color: string;  // Tailwind color class
}

export type WorkflowType = "sequential" | "collaboration";

export interface PipelineStep {
  id: string;
  agentId: string;
  instruction: string;
}

export interface SimulationConfig {
  input: string;
  workflowType: WorkflowType;
  agents: Agent[];
  steps: PipelineStep[];
  discussionTurns?: number;
}

export interface StepLog {
  id: string;
  agentId: string;
  agentName: string;
  avatar: string;
  color: string;
  role: string;
  inputUsed: string;
  output: string;
  durationMs: number;
  tokensUsed?: number;
  modelUsed: string;
  completedAt: string;
  timestamp?: number;
  // Backend Telemetry & PGL Audit Receipt
  log_id?: string;
  tenant_id?: string;
  cost?: number | string;
  prompt_tokens?: number;
  completion_tokens?: number;
}

export interface SimulationResult {
  logs: StepLog[];
  finalOutput: string;
  totalDurationMs: number;
}

export interface PresetTemplate {
  id: string;
  title: string;
  description: string;
  icon: string;
  workflowType: WorkflowType;
  customTypeLabel?: string;
  agents: Agent[];
  steps: PipelineStep[];
  discussionTurns?: number;
  defaultInput: string;
}
