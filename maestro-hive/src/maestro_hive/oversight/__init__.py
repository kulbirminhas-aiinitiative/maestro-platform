"""
Human Oversight System - EU AI Act Article 14 Compliance
EPIC: MD-2158

This module provides comprehensive human oversight capabilities for AI systems
as required by EU AI Act Article 14, including:
- AC-1: Agent override mechanism (kill-switch)
- AC-2: Quality gate bypass with audit trail
- AC-3: Escalation paths for edge cases
- AC-4: Contract amendment/renegotiation
- AC-5: Workflow pause and review capability
- AC-6: Human approval for critical decisions
"""

from .compliance_logger import ComplianceLogger, PIIMasker
from .agent_override import AgentOverrideService, AgentState, OverrideSeverity
from .quality_gate_bypass import QualityGateBypassService, BypassScope, BypassStatus
from .escalation import EscalationService, EscalationTier, EscalationPriority
from .contract_amendment import ContractAmendmentService, AmendmentStatus
from .workflow_pause import WorkflowPauseService, WorkflowState
from .critical_decision import CriticalDecisionService, DecisionRiskLevel, ApprovalStatus

__all__ = [
    # Logger
    "ComplianceLogger",
    "PIIMasker",
    # AC-1: Agent Override
    "AgentOverrideService",
    "AgentState",
    "OverrideSeverity",
    # AC-2: Quality Gate Bypass
    "QualityGateBypassService",
    "BypassScope",
    "BypassStatus",
    # AC-3: Escalation
    "EscalationService",
    "EscalationTier",
    "EscalationPriority",
    # AC-4: Contract Amendment
    "ContractAmendmentService",
    "AmendmentStatus",
    # AC-5: Workflow Pause
    "WorkflowPauseService",
    "WorkflowState",
    # AC-6: Critical Decision
    "CriticalDecisionService",
    "DecisionRiskLevel",
    "ApprovalStatus",
]
