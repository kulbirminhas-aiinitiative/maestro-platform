/**
 * Human Oversight System
 * EU AI Act Article 14 Compliance
 * EPIC: MD-2158
 *
 * This module provides comprehensive human oversight capabilities for AI systems
 * as required by EU AI Act Article 14, including:
 * - AC-1: Agent override mechanism (kill-switch)
 * - AC-2: Quality gate bypass with audit trail
 * - AC-3: Escalation paths for edge cases
 * - AC-4: Contract amendment/renegotiation
 * - AC-5: Workflow pause and review capability
 * - AC-6: Human approval for critical decisions
 */

// Type exports
export * from './types';

// Service exports
export { AgentOverrideService } from './agentOverrideService';
export { QualityGateBypassService } from './qualityGateBypassService';
export { EscalationService } from './escalationService';
export { ContractAmendmentService } from './contractAmendmentService';
export { WorkflowPauseService } from './workflowPauseService';
export { CriticalDecisionService } from './criticalDecisionService';
export { ComplianceLogger } from './complianceLogger';

// Default exports for convenience
import { AgentOverrideService } from './agentOverrideService';
import { QualityGateBypassService } from './qualityGateBypassService';
import { EscalationService } from './escalationService';
import { ContractAmendmentService } from './contractAmendmentService';
import { WorkflowPauseService } from './workflowPauseService';
import { CriticalDecisionService } from './criticalDecisionService';
import { ComplianceLogger } from './complianceLogger';

export default {
  AgentOverrideService,
  QualityGateBypassService,
  EscalationService,
  ContractAmendmentService,
  WorkflowPauseService,
  CriticalDecisionService,
  ComplianceLogger,
};
