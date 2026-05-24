export interface Agent {
  id: string;
  name: string;
  scope: string;
  description: string;
  trustScore: number;
  icon: string;
  dataset: string;
}

export interface Policy {
  id: string;
  citizenEmail: string;
  agentId: string;
  action: string;
  status: "granted" | "revoked";
  validUntil: string;
}

export interface GateResult {
  passed: boolean;
  details: string;
  costUsd?: number;
  blockHash?: string;
}

export interface GatesResult {
  gate1_signature: GateResult;
  gate2_consent: GateResult;
  gate3_boundary: GateResult;
  gate4_quota: GateResult;
  gate5_ledger: GateResult;
}

export interface LedgerBlock {
  index: number;
  timestamp: string;
  citizenEmail: string;
  agentId: string;
  query: string;
  signature: string;
  gatesResult: GatesResult;
  response: string;
  previousHash: string;
  hash: string;
}

export interface ExecutionReport {
  success: boolean;
  block: LedgerBlock;
}
