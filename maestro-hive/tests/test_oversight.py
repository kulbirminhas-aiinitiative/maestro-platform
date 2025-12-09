"""
Tests for Human Oversight Module
EU AI Act Article 14 Compliance - EPIC: MD-2158
"""

import pytest
from datetime import datetime, timedelta
import asyncio

# Import oversight module
from maestro_hive.oversight import (
    ComplianceLogger,
    PIIMasker,
    AgentOverrideService,
    AgentState,
    OverrideSeverity,
    QualityGateBypassService,
    BypassScope,
    BypassStatus,
    EscalationService,
    EscalationTier,
    EscalationPriority,
    ContractAmendmentService,
    AmendmentStatus,
    WorkflowPauseService,
    WorkflowState,
    CriticalDecisionService,
    DecisionRiskLevel,
    ApprovalStatus,
)
from maestro_hive.oversight.escalation import EscalationStatus
from maestro_hive.oversight.agent_override import AgentOverrideRequest
from maestro_hive.oversight.quality_gate_bypass import QualityGateBypassRequest
from maestro_hive.oversight.escalation import EscalationRequest
from maestro_hive.oversight.contract_amendment import ContractAmendmentRequest, ContractChange
from maestro_hive.oversight.workflow_pause import WorkflowPauseRequest


# ============================================================
# PII Masker Tests
# ============================================================

class TestPIIMasker:
    """Tests for PII masking functionality."""

    def test_mask_email(self):
        """Test email masking."""
        text = "Contact john.doe@example.com for help"
        masked = PIIMasker.mask_string(text)
        assert "[EMAIL_MASKED]" in masked
        assert "john.doe@example.com" not in masked

    def test_mask_phone(self):
        """Test phone number masking."""
        text = "Call 123-456-7890"
        masked = PIIMasker.mask_string(text)
        assert "[PHONE_MASKED]" in masked
        assert "123-456-7890" not in masked

    def test_mask_ssn(self):
        """Test SSN masking."""
        text = "SSN: 123-45-6789"
        masked = PIIMasker.mask_string(text)
        assert "[SSN_MASKED]" in masked
        assert "123-45-6789" not in masked

    def test_mask_ip_address(self):
        """Test IP address masking."""
        text = "Server IP: 192.168.1.100"
        masked = PIIMasker.mask_string(text)
        assert "[IP_MASKED]" in masked
        assert "192.168.1.100" not in masked

    def test_mask_object(self):
        """Test recursive object masking."""
        obj = {
            "user": "john@example.com",
            "phone": "555-123-4567",
            "nested": {
                "email": "jane@test.org"
            }
        }
        masked = PIIMasker.mask_object(obj)
        assert masked["user"] == "[EMAIL_MASKED]"
        assert masked["nested"]["email"] == "[EMAIL_MASKED]"


# ============================================================
# Compliance Logger Tests
# ============================================================

class TestComplianceLogger:
    """Tests for compliance logging."""

    @pytest.fixture
    def logger(self):
        return ComplianceLogger()

    @pytest.mark.asyncio
    async def test_log_action(self, logger):
        """Test basic action logging."""
        from maestro_hive.oversight.compliance_logger import OversightActionType
        entry = await logger.log_action(
            OversightActionType.OVERRIDE,
            "operator1",
            "agent-123",
            {"reason": "Test override"}
        )
        assert entry.id.startswith("audit_")
        assert entry.action == "override"
        assert entry.pii_masked

    @pytest.mark.asyncio
    async def test_log_override(self, logger):
        """Test override logging."""
        entry = await logger.log_override(
            "operator1", "agent-123", "Emergency stop", "hard", True
        )
        assert entry.action == "override"
        assert entry.details["severity"] == "hard"

    @pytest.mark.asyncio
    async def test_log_bypass(self, logger):
        """Test bypass logging."""
        expiry = datetime.utcnow() + timedelta(hours=24)
        entry = await logger.log_bypass(
            "approver1", "gate-abc", "Critical fix required", "single", expiry
        )
        assert entry.action == "bypass"
        assert "justification" in entry.details

    @pytest.mark.asyncio
    async def test_query_logs(self, logger):
        """Test log querying."""
        # Create some entries
        await logger.log_override("op1", "agent-1", "Test", "soft", True)
        await logger.log_override("op1", "agent-2", "Test", "hard", True)

        # Query
        results = logger.query_logs(action="override")
        assert len(results) == 2


# ============================================================
# Agent Override Tests (AC-1)
# ============================================================

class TestAgentOverrideService:
    """Tests for agent override (kill-switch) functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return AgentOverrideService(logger)

    @pytest.mark.asyncio
    async def test_register_agent(self, service):
        """Test agent registration."""
        agent = service.register_agent("agent-123")
        assert agent.id == "agent-123"
        assert agent.state == AgentState.RUNNING

    @pytest.mark.asyncio
    async def test_soft_override(self, service):
        """Test soft override (graceful stop)."""
        service.register_agent("agent-123")

        result = await service.override_agent(AgentOverrideRequest(
            agent_id="agent-123",
            reason="Testing soft override",
            operator_id="operator-1",
            severity=OverrideSeverity.SOFT
        ))

        assert result.success
        assert result.new_state == AgentState.STOPPED
        assert result.previous_state == AgentState.RUNNING

    @pytest.mark.asyncio
    async def test_hard_override(self, service):
        """Test hard override (immediate termination)."""
        service.register_agent("agent-456")

        result = await service.override_agent(AgentOverrideRequest(
            agent_id="agent-456",
            reason="Emergency termination",
            operator_id="operator-1",
            severity=OverrideSeverity.HARD
        ))

        assert result.success
        assert result.new_state == AgentState.TERMINATED

    @pytest.mark.asyncio
    async def test_resume_stopped_agent(self, service):
        """Test resuming a stopped agent."""
        service.register_agent("agent-789")

        # First stop
        stop_result = await service.override_agent(AgentOverrideRequest(
            agent_id="agent-789",
            reason="Temporary stop",
            operator_id="operator-1",
            severity=OverrideSeverity.SOFT
        ))

        # Then resume
        resume_result = await service.resume_agent(
            "agent-789",
            stop_result.override_id,
            "operator-1",
            "Review complete"
        )

        assert resume_result.success
        assert resume_result.new_state == AgentState.RUNNING

    @pytest.mark.asyncio
    async def test_cannot_resume_terminated(self, service):
        """Test that terminated agents cannot be resumed."""
        service.register_agent("agent-term")

        result = await service.override_agent(AgentOverrideRequest(
            agent_id="agent-term",
            reason="Hard termination",
            operator_id="operator-1",
            severity=OverrideSeverity.HARD
        ))

        with pytest.raises(ValueError, match="Cannot resume terminated"):
            await service.resume_agent(
                "agent-term",
                result.override_id,
                "operator-1"
            )

    @pytest.mark.asyncio
    async def test_emergency_stop_all(self, service):
        """Test emergency stop of all agents."""
        service.register_agent("agent-1")
        service.register_agent("agent-2")
        service.register_agent("agent-3")

        count = await service.emergency_stop_all("admin", "System emergency")
        assert count == 3


# ============================================================
# Quality Gate Bypass Tests (AC-2)
# ============================================================

class TestQualityGateBypassService:
    """Tests for quality gate bypass functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return QualityGateBypassService(logger, max_duration_hours=72)

    @pytest.mark.asyncio
    async def test_create_bypass(self, service):
        """Test bypass creation."""
        bypass = await service.create_bypass(QualityGateBypassRequest(
            gate_id="gate-security-scan",
            justification="Known false positive, ticket JIRA-123",
            approver_id="senior-dev",
            expiry_hours=24,
            scope=BypassScope.SINGLE
        ))

        assert bypass.id.startswith("bypass_")
        assert bypass.status == BypassStatus.ACTIVE
        assert bypass.is_valid()

    @pytest.mark.asyncio
    async def test_justification_required(self, service):
        """Test that justification is required."""
        with pytest.raises(ValueError, match="Justification must be"):
            await service.create_bypass(QualityGateBypassRequest(
                gate_id="gate-1",
                justification="Too short",
                approver_id="approver",
                expiry_hours=24,
                scope=BypassScope.SINGLE
            ))

    @pytest.mark.asyncio
    async def test_max_duration_enforced(self, service):
        """Test that max duration is enforced."""
        with pytest.raises(ValueError, match="cannot exceed"):
            await service.create_bypass(QualityGateBypassRequest(
                gate_id="gate-1",
                justification="This is a valid justification",
                approver_id="approver",
                expiry_hours=100,  # > 72
                scope=BypassScope.SINGLE
            ))

    @pytest.mark.asyncio
    async def test_check_bypass(self, service):
        """Test checking for active bypass."""
        await service.create_bypass(QualityGateBypassRequest(
            gate_id="gate-test",
            justification="Valid justification for bypass",
            approver_id="approver",
            expiry_hours=24,
            scope=BypassScope.SESSION
        ))

        bypass = service.check_bypass("gate-test")
        assert bypass is not None
        assert bypass.gate_id == "gate-test"

    @pytest.mark.asyncio
    async def test_revoke_bypass(self, service):
        """Test bypass revocation."""
        bypass = await service.create_bypass(QualityGateBypassRequest(
            gate_id="gate-revoke",
            justification="Valid justification for bypass",
            approver_id="approver",
            expiry_hours=24,
            scope=BypassScope.SINGLE
        ))

        result = await service.revoke_bypass(bypass.id, "admin", "No longer needed")
        assert result is True
        assert bypass.status == BypassStatus.REVOKED


# ============================================================
# Escalation Tests (AC-3)
# ============================================================

class TestEscalationService:
    """Tests for escalation functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return EscalationService(logger)

    @pytest.mark.asyncio
    async def test_create_escalation(self, service):
        """Test escalation creation."""
        escalation = await service.create_escalation(EscalationRequest(
            context_id="ctx-123",
            tier=EscalationTier.TIER_1,
            reason="Cannot resolve issue",
            priority=EscalationPriority.MEDIUM
        ))

        assert escalation.id.startswith("esc_")
        assert escalation.tier == EscalationTier.TIER_1
        assert not escalation.is_overdue()

    @pytest.mark.asyncio
    async def test_assign_escalation(self, service):
        """Test escalation assignment."""
        escalation = await service.create_escalation(EscalationRequest(
            context_id="ctx-456",
            tier=EscalationTier.TIER_1,
            reason="Needs review",
            priority=EscalationPriority.HIGH
        ))

        result = await service.assign_escalation(escalation.id, "reviewer-1")
        assert result is True
        assert escalation.assigned_to == "reviewer-1"

    @pytest.mark.asyncio
    async def test_resolve_escalation(self, service):
        """Test escalation resolution."""
        escalation = await service.create_escalation(EscalationRequest(
            context_id="ctx-789",
            tier=EscalationTier.TIER_1,
            reason="Issue found",
            priority=EscalationPriority.LOW
        ))

        result = await service.resolve_escalation(
            escalation.id, "resolver-1", "Issue addressed"
        )
        assert result is True
        assert escalation.status == EscalationStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_escalate_to_next_tier(self, service):
        """Test escalation to next tier."""
        tier1 = await service.create_escalation(EscalationRequest(
            context_id="ctx-tier",
            tier=EscalationTier.TIER_1,
            reason="Initial issue",
            priority=EscalationPriority.HIGH
        ))

        tier2 = await service.escalate_to_next_tier(tier1.id, "Needs senior review")
        assert tier2 is not None
        assert tier2.tier == EscalationTier.TIER_2
        assert tier1.status == EscalationStatus.RESOLVED


# ============================================================
# Contract Amendment Tests (AC-4)
# ============================================================

class TestContractAmendmentService:
    """Tests for contract amendment functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return ContractAmendmentService(logger)

    @pytest.mark.asyncio
    async def test_create_amendment(self, service):
        """Test amendment creation."""
        amendment = await service.create_amendment(ContractAmendmentRequest(
            contract_id="contract-123",
            amendments=[
                ContractChange(
                    field="payment_terms",
                    old_value="net-30",
                    new_value="net-60",
                    change_type="modify"
                )
            ],
            requester_id="user-1",
            reason="Customer request"
        ))

        assert amendment.id.startswith("amend_")
        assert amendment.status == AmendmentStatus.DRAFT

    @pytest.mark.asyncio
    async def test_amendment_approval_workflow(self, service):
        """Test full amendment approval workflow."""
        # Create
        amendment = await service.create_amendment(ContractAmendmentRequest(
            contract_id="contract-456",
            amendments=[
                ContractChange("scope", "A", "B", "modify")
            ],
            requester_id="user-1",
            reason="Scope change"
        ))

        # Submit
        await service.submit_for_approval(amendment.id)
        assert amendment.status == AmendmentStatus.PENDING_APPROVAL

        # Approve
        result = await service.approve_amendment(amendment.id, "approver-1", "Approved")
        assert result is True
        assert amendment.status == AmendmentStatus.APPROVED

        # Apply
        result = await service.apply_amendment(amendment.id)
        assert result is True
        assert amendment.status == AmendmentStatus.APPLIED

    @pytest.mark.asyncio
    async def test_amendment_rejection(self, service):
        """Test amendment rejection."""
        amendment = await service.create_amendment(ContractAmendmentRequest(
            contract_id="contract-789",
            amendments=[ContractChange("price", 100, 50, "modify")],
            requester_id="user-1",
            reason="Price reduction"
        ))

        await service.submit_for_approval(amendment.id)
        result = await service.reject_amendment(amendment.id, "approver-1", "Invalid request")

        assert result is True
        assert amendment.status == AmendmentStatus.REJECTED


# ============================================================
# Workflow Pause Tests (AC-5)
# ============================================================

class TestWorkflowPauseService:
    """Tests for workflow pause functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return WorkflowPauseService(logger)

    @pytest.mark.asyncio
    async def test_register_workflow(self, service):
        """Test workflow registration."""
        workflow = service.register_workflow("wf-123", "Test Workflow")
        assert workflow.id == "wf-123"
        assert workflow.state == WorkflowState.RUNNING

    @pytest.mark.asyncio
    async def test_pause_workflow(self, service):
        """Test workflow pause."""
        service.register_workflow("wf-pause", "Pausable Workflow")

        result = await service.pause_workflow(WorkflowPauseRequest(
            workflow_id="wf-pause",
            reason="Manual review required",
            operator_id="operator-1",
            capture_checkpoint=True
        ))

        assert result.success
        assert result.checkpoint is not None
        assert result.previous_state == WorkflowState.RUNNING

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, service):
        """Test pause and resume workflow."""
        service.register_workflow("wf-resume", "Resume Test")

        # Pause
        pause_result = await service.pause_workflow(WorkflowPauseRequest(
            workflow_id="wf-resume",
            reason="Review needed",
            operator_id="operator-1"
        ))

        # Resume
        resume_result = await service.resume_workflow(
            "wf-resume",
            pause_result.pause_id,
            "operator-1",
            review_notes="Review complete"
        )

        assert resume_result.success
        assert resume_result.previous_state == WorkflowState.PAUSED

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, service):
        """Test resume from specific checkpoint."""
        service.register_workflow("wf-chkpt", "Checkpoint Test")
        service.update_workflow_step("wf-chkpt", 5, "step_5", {"data": "value"})

        pause_result = await service.pause_workflow(WorkflowPauseRequest(
            workflow_id="wf-chkpt",
            reason="Checkpoint test",
            operator_id="operator-1",
            capture_checkpoint=True
        ))

        # Resume from checkpoint
        await service.resume_workflow(
            "wf-chkpt",
            pause_result.pause_id,
            "operator-1",
            from_checkpoint=pause_result.checkpoint.id
        )

        status = service.get_workflow_status("wf-chkpt")
        assert status["current_step"] == 5


# ============================================================
# Critical Decision Tests (AC-6)
# ============================================================

class TestCriticalDecisionService:
    """Tests for critical decision approval functionality."""

    @pytest.fixture
    def service(self):
        logger = ComplianceLogger()
        return CriticalDecisionService(logger)

    @pytest.mark.asyncio
    async def test_create_decision(self, service):
        """Test critical decision creation."""
        decision = await service.create_decision(
            decision_type="contract_approval",
            description="High-value contract approval",
            risk_level=DecisionRiskLevel.HIGH,
            context={"contract_value": 100000},
            ai_recommendation="Approve",
            ai_confidence=0.85
        )

        assert decision.id.startswith("dec_")
        assert decision.status == ApprovalStatus.PENDING
        assert decision.required_approvers == 2  # HIGH risk requires 2

    @pytest.mark.asyncio
    async def test_single_approval(self, service):
        """Test single approver decision."""
        decision = await service.create_decision(
            decision_type="minor_change",
            description="Minor configuration change",
            risk_level=DecisionRiskLevel.LOW,
            context={}
        )

        approval = await service.submit_approval(
            decision.id, "approver-1", True, "Approved"
        )

        assert approval is not None
        assert decision.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_multi_approval_required(self, service):
        """Test decision requiring multiple approvers."""
        decision = await service.create_decision(
            decision_type="critical_operation",
            description="Critical system change",
            risk_level=DecisionRiskLevel.CRITICAL,
            context={}
        )

        # First approval - not enough
        await service.submit_approval(decision.id, "approver-1", True, "Approved")
        assert decision.status == ApprovalStatus.PENDING

        # Second approval - still not enough (CRITICAL needs 3)
        await service.submit_approval(decision.id, "approver-2", True, "Approved")
        assert decision.status == ApprovalStatus.PENDING

        # Third approval - now approved
        await service.submit_approval(decision.id, "approver-3", True, "Approved")
        assert decision.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_rejection(self, service):
        """Test decision rejection."""
        decision = await service.create_decision(
            decision_type="risky_change",
            description="Potentially risky change",
            risk_level=DecisionRiskLevel.HIGH,
            context={}
        )

        # One rejection rejects the whole decision
        await service.submit_approval(decision.id, "approver-1", False, "Too risky")
        assert decision.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_duplicate_approver_blocked(self, service):
        """Test that same approver cannot vote twice."""
        decision = await service.create_decision(
            decision_type="test_decision",
            description="Test",
            risk_level=DecisionRiskLevel.MEDIUM,
            context={}
        )

        # First vote
        result1 = await service.submit_approval(decision.id, "approver-1", True, "First vote")
        assert result1 is not None

        # Second vote by same approver
        result2 = await service.submit_approval(decision.id, "approver-1", True, "Second vote")
        assert result2 is None

    @pytest.mark.asyncio
    async def test_get_pending_decisions(self, service):
        """Test getting pending decisions."""
        await service.create_decision(
            "type1", "Decision 1", DecisionRiskLevel.LOW, {}
        )
        await service.create_decision(
            "type2", "Decision 2", DecisionRiskLevel.HIGH, {}
        )

        pending = service.get_pending_decisions()
        assert len(pending) == 2
        # Should be sorted by risk (HIGH first)
        assert pending[0].risk_level == DecisionRiskLevel.HIGH


# ============================================================
# Integration Test
# ============================================================

class TestOversightIntegration:
    """Integration tests for the oversight module."""

    @pytest.mark.asyncio
    async def test_full_oversight_workflow(self):
        """Test complete oversight workflow."""
        logger = ComplianceLogger()

        # Create services
        agent_service = AgentOverrideService(logger)
        decision_service = CriticalDecisionService(logger)
        escalation_service = EscalationService(logger)

        # Register an agent
        agent_service.register_agent("ai-agent-001")

        # AI makes a low-confidence decision - requires oversight
        decision = await decision_service.create_decision(
            decision_type="automated_response",
            description="AI-generated customer response",
            risk_level=DecisionRiskLevel.MEDIUM,
            context={"customer_id": "cust-123"},
            ai_recommendation="Approve refund",
            ai_confidence=0.65
        )

        # Decision gets approved
        await decision_service.submit_approval(
            decision.id, "human-reviewer", True, "Response looks appropriate"
        )

        assert decision.status == ApprovalStatus.APPROVED

        # Later, issue detected - escalate
        escalation = await escalation_service.create_escalation(EscalationRequest(
            context_id=decision.id,
            tier=EscalationTier.TIER_1,
            reason="Customer complained about response",
            priority=EscalationPriority.HIGH
        ))

        # While investigating, pause the agent
        result = await agent_service.override_agent(AgentOverrideRequest(
            agent_id="ai-agent-001",
            reason="Investigation in progress",
            operator_id="supervisor",
            severity=OverrideSeverity.SOFT
        ))

        assert result.success
        assert result.new_state == AgentState.STOPPED

        # Verify audit trail exists
        logs = logger.query_logs(limit=10)
        assert len(logs) >= 3  # Decision approval, escalation, override
