/**
 * Human Oversight System - Type Definitions
 * EU AI Act Article 14 Compliance
 * EPIC: MD-2158
 */

// ============================================================
// Common Types
// ============================================================

export interface ComplianceContext {
  sessionId: string;
  userId: string;
  operationType: string;
  timestamp: Date;
  metadata: Record<string, unknown>;
}

export interface AuditLogEntry {
  id: string;
  contextId: string;
  action: string;
  actor: string;
  target: string;
  details: Record<string, unknown>;
  timestamp: Date;
  piiMasked: boolean;
}

export type OversightActionType = 
  | 'override' 
  | 'bypass' 
  | 'escalate' 
  | 'pause' 
  | 'resume' 
  | 'approve' 
  | 'reject'
  | 'amend';

// ============================================================
// AC-1: Agent Override Types
// ============================================================

export type OverrideSeverity = 'soft' | 'hard';
export type AgentState = 'running' | 'paused' | 'stopped' | 'terminated';

export interface AgentOverrideRequest {
  agentId: string;
  reason: string;
  operatorId: string;
  severity: OverrideSeverity;
  context?: ComplianceContext;
}

export interface AgentOverrideResult {
  success: boolean;
  agentId: string;
  previousState: AgentState;
  newState: AgentState;
  overrideId: string;
  timestamp: Date;
  auditLogId: string;
}

export interface AgentResumeRequest {
  agentId: string;
  overrideId: string;
  operatorId: string;
  reviewNotes?: string;
}

// ============================================================
// AC-2: Quality Gate Bypass Types
// ============================================================

export type BypassScope = 'single' | 'session' | 'workflow';
export type BypassStatus = 'active' | 'expired' | 'revoked' | 'used';

export interface QualityGateBypassRequest {
  gateId: string;
  justification: string;
  approverId: string;
  expiry: Date;
  scope: BypassScope;
  context?: ComplianceContext;
}

export interface QualityGateBypass {
  id: string;
  gateId: string;
  justification: string;
  approverId: string;
  expiry: Date;
  scope: BypassScope;
  status: BypassStatus;
  createdAt: Date;
  usedAt?: Date;
  auditLogId: string;
}

// ============================================================
// AC-3: Escalation Types
// ============================================================

export type EscalationTier = 1 | 2 | 3;
export type EscalationPriority = 'low' | 'medium' | 'high' | 'critical';
export type EscalationStatus = 'pending' | 'assigned' | 'in_progress' | 'resolved' | 'expired';

export interface EscalationRequest {
  contextId: string;
  tier: EscalationTier;
  reason: string;
  priority: EscalationPriority;
  context?: ComplianceContext;
}

export interface Escalation {
  id: string;
  contextId: string;
  tier: EscalationTier;
  reason: string;
  priority: EscalationPriority;
  status: EscalationStatus;
  assignedTo?: string;
  resolution?: string;
  createdAt: Date;
  slaDeadline: Date;
  resolvedAt?: Date;
  auditLogId: string;
}

// ============================================================
// AC-4: Contract Amendment Types
// ============================================================

export type AmendmentStatus = 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'applied';

export interface ContractAmendmentRequest {
  contractId: string;
  amendments: ContractChange[];
  requesterId: string;
  reason: string;
  context?: ComplianceContext;
}

export interface ContractChange {
  field: string;
  oldValue: unknown;
  newValue: unknown;
  changeType: 'add' | 'modify' | 'remove';
}

export interface ContractAmendment {
  id: string;
  contractId: string;
  amendments: ContractChange[];
  requesterId: string;
  reason: string;
  status: AmendmentStatus;
  approverId?: string;
  approvalComments?: string;
  createdAt: Date;
  approvedAt?: Date;
  appliedAt?: Date;
  auditLogId: string;
}

// ============================================================
// AC-5: Workflow Pause/Resume Types
// ============================================================

export type WorkflowState = 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

export interface WorkflowCheckpoint {
  id: string;
  workflowId: string;
  stepIndex: number;
  stepName: string;
  state: Record<string, unknown>;
  capturedAt: Date;
}

export interface WorkflowPauseRequest {
  workflowId: string;
  reason: string;
  operatorId: string;
  captureCheckpoint: boolean;
  context?: ComplianceContext;
}

export interface WorkflowPauseResult {
  success: boolean;
  workflowId: string;
  previousState: WorkflowState;
  checkpoint?: WorkflowCheckpoint;
  pauseId: string;
  timestamp: Date;
  auditLogId: string;
}

export interface WorkflowResumeRequest {
  workflowId: string;
  pauseId: string;
  operatorId: string;
  fromCheckpoint?: string;
  reviewNotes?: string;
}

// ============================================================
// AC-6: Critical Decision Approval Types
// ============================================================

export type DecisionRiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'auto_approved';

export interface CriticalDecision {
  id: string;
  decisionType: string;
  description: string;
  riskLevel: DecisionRiskLevel;
  context: Record<string, unknown>;
  requiredApprovers: number;
  expiresAt: Date;
  status: ApprovalStatus;
  createdAt: Date;
  resolvedAt?: Date;
}

export interface DecisionApprovalRequest {
  decisionId: string;
  approved: boolean;
  comments: string;
  approverId: string;
  context?: ComplianceContext;
}

export interface DecisionApproval {
  id: string;
  decisionId: string;
  approved: boolean;
  comments: string;
  approverId: string;
  createdAt: Date;
  auditLogId: string;
}

// ============================================================
// Service Configuration Types
// ============================================================

export interface OversightConfig {
  database: {
    url: string;
    poolSize: number;
  };
  kafka: {
    brokers: string[];
    auditTopic: string;
  };
  escalation: {
    tier1SlaMins: number;
    tier2SlaMins: number;
    tier3SlaMins: number;
  };
  bypass: {
    maxDurationHours: number;
  };
  approval: {
    expiryHours: number;
  };
  override: {
    timeoutMs: number;
  };
}
