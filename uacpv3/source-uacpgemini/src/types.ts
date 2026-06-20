export enum PlanStatus {
  DRAFT = 'draft',
  VERIFIED = 'verified',
  LOCKED = 'locked'
}

export enum RunStatus {
  PENDING = 'pending',
  EXECUTING = 'executing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface Plan {
  id: string;
  name: string;
  intent: string;
  revision: number;
  status: PlanStatus;
  graph: any;
  createdAt: string;
}

export interface Run {
  id: string;
  planId: string;
  status: RunStatus;
  currentStep: string;
  progress: number;
  output?: any;
  startTime: string;
  endTime?: string;
}

export interface AppEvent {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  metadata?: any;
}

export interface ObservabilitySignals {
  quantum_coherence: number;
  classical_latency: number;
  uacp_pressure: number;
  gopher_policy_alignment: number;
  horowitz_signals: Array<{ id: string; value: number; trend: string }>;
}
