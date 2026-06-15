export interface Agent {
  id: string;
  name: string;
  type: string;
  status: 'Idle' | 'Planning' | 'Executing' | 'Anchoring' | 'Done';
  energyUsed: number; // in mJ
  carbonIntensity: number; // gCO2/kWh
  currentTask: string;
  progress: number;
  solanaTxSignature?: string;
  pda?: string;
}

export interface MCPResource {
  id: string;
  name: string;
  type: 'sensor' | 'database' | 'context' | 'model';
  value: number;
  unit: string;
  threshold: number;
  lastUpdated: string;
  history: number[];
  state: 'healthy' | 'warning' | 'anomaly';
}

export interface AnomalyLog {
  id: string;
  timestamp: string;
  resourceId: string;
  resourceName: string;
  testStatF: number;
  criticalValueF: number;
  pValue: number;
  description: string;
  severity: 'warning' | 'critical';
  automatedResponseTriggered: boolean;
}

export interface AlertChannel {
  id: string;
  type: 'ui_toast' | 'webhook';
  name: string;
  endpoint?: string;
  active: boolean;
}

export interface NotificationLog {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  payload: string; // JSON
  status: 'delivered' | 'failed' | 'pending';
}

export interface GridCell {
  x: number;
  y: number;
  type: 'empty' | 'start' | 'target' | 'obstacle' | 'path';
  potential: number; // Gradient field value
}

export interface FaultMatrixEvent {
  event: string;
  impact: string;
  recovery: string;
  active: boolean;
}

export interface LedgerBlock {
  blockNumber: number;
  timestamp: string;
  txHash: string;
  eventType: string; // 'IDENTITY' | 'AUTHORITY' | 'EXECUTION' | 'PROOF';
  agentId: string;
  action: string;
  gasPaidLamports: number;
  pdaAddress: string;
  memo: string;
  replayable: boolean;
}
