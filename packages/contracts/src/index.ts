export type RiskTier = "read_only" | "reversible_local" | "external_consequential" | "high_impact";
export type RunStatus = "queued" | "planning" | "awaiting_approval" | "running" | "verifying" | "succeeded" | "partial" | "failed" | "cancelled";

export interface ProjectReference {
  id: string;
  name: string;
  status: "active" | "paused" | "archived";
}

export interface AgentTask {
  id: string;
  objective: string;
  projectId?: string;
  specialist: "engineering" | "cybersecurity" | "analytics" | "research" | "design" | "operations";
  status: RunStatus;
  createdAt: string;
}

export interface ToolManifest {
  name: string;
  version: string;
  riskTier: RiskTier;
  requiredScopes: string[];
  timeoutMs: number;
  idempotent: boolean;
  requiresApproval: boolean;
}

export interface ApprovalRequest {
  id: string;
  actionHash: string;
  summary: string;
  target: string;
  expiresAt: string;
}

export interface EvidenceReference {
  kind: "url" | "file" | "commit" | "test" | "log";
  value: string;
  observedAt: string;
}

export interface ToolExecutionResult<T = unknown> {
  status: "verified" | "partial" | "failed" | "unverified";
  data?: T;
  evidence: EvidenceReference[];
  message: string;
}
