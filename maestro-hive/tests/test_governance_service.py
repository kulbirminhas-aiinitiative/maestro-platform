"""
Tests for Governance Service (MD-2107)

Tests for:
- Governance Protocol schema (MD-2121)
- GovernanceService (MD-2122)
- Phase gate integration (MD-2123)
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from services.governance_service import (
    GovernanceService,
    GovernanceCheckResult,
    PhaseGate,
    DocumentRequirement,
    ApprovalRequirement,
    ValidationRule,
    ValidationResult,
    Approval,
    AuditEntry,
    get_governance_service,
    reset_governance_service
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def governance_service():
    """Create a governance service with test protocol"""
    reset_governance_service()
    protocol_path = Path(__file__).parent.parent / "config" / "governance_protocol.yaml"
    service = GovernanceService(protocol_path=str(protocol_path))
    return service


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service before each test"""
    reset_governance_service()
    yield
    reset_governance_service()


# =============================================================================
# Test Data Classes
# =============================================================================

class TestDocumentRequirement:
    """Tests for DocumentRequirement"""

    def test_creation(self):
        """Test DocumentRequirement creation"""
        doc = DocumentRequirement(
            doc_type="requirements_spec",
            name="Requirements Specification",
            required=True
        )
        assert doc.doc_type == "requirements_spec"
        assert doc.name == "Requirements Specification"
        assert doc.required is True

    def test_optional_fields(self):
        """Test optional fields"""
        doc = DocumentRequirement(
            doc_type="test_doc",
            name="Test Document",
            template="test_template",
            required=False
        )
        assert doc.template == "test_template"
        assert doc.required is False


class TestApprovalRequirement:
    """Tests for ApprovalRequirement"""

    def test_creation(self):
        """Test ApprovalRequirement creation"""
        appr = ApprovalRequirement(role="tech_lead", required=True)
        assert appr.role == "tech_lead"
        assert appr.required is True


class TestValidationRule:
    """Tests for ValidationRule"""

    def test_creation(self):
        """Test ValidationRule creation"""
        rule = ValidationRule(
            rule_id="test_coverage",
            description="Test coverage threshold",
            threshold=80.0
        )
        assert rule.rule_id == "test_coverage"
        assert rule.threshold == 80.0


class TestPhaseGate:
    """Tests for PhaseGate"""

    def test_creation(self):
        """Test PhaseGate creation"""
        gate = PhaseGate(
            phase="requirements",
            display_name="Requirements Analysis",
            required_documents=[
                DocumentRequirement("req_spec", "Requirements", required=True)
            ],
            required_approvals=[
                ApprovalRequirement("product_owner", required=True)
            ]
        )
        assert gate.phase == "requirements"
        assert len(gate.required_documents) == 1
        assert len(gate.required_approvals) == 1


class TestGovernanceCheckResult:
    """Tests for GovernanceCheckResult"""

    def test_passed_result(self):
        """Test passed result"""
        result = GovernanceCheckResult(phase="testing", passed=True)
        assert result.passed is True
        assert result.errors == []

    def test_failed_result(self):
        """Test failed result with errors"""
        result = GovernanceCheckResult(
            phase="testing",
            passed=False,
            errors=["Missing document"]
        )
        assert result.passed is False
        assert len(result.errors) == 1

    def test_to_dict(self):
        """Test serialization"""
        result = GovernanceCheckResult(
            phase="testing",
            passed=True,
            document_checks={"test_plan": ValidationResult.PASSED}
        )
        data = result.to_dict()
        assert data['phase'] == "testing"
        assert data['passed'] is True
        assert data['document_checks']['test_plan'] == "passed"


class TestApproval:
    """Tests for Approval"""

    def test_creation(self):
        """Test Approval creation"""
        approval = Approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            approver="john.doe"
        )
        assert approval.workflow_id == "wf-123"
        assert approval.role == "architect"

    def test_expiration(self):
        """Test approval with expiration"""
        expires = datetime.utcnow() + timedelta(hours=24)
        approval = Approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            approver="john.doe",
            expires_at=expires
        )
        assert approval.expires_at == expires


class TestAuditEntry:
    """Tests for AuditEntry"""

    def test_creation(self):
        """Test AuditEntry creation"""
        entry = AuditEntry(
            workflow_id="wf-123",
            phase="testing",
            action="check",
            actor="system"
        )
        assert entry.workflow_id == "wf-123"
        assert entry.action == "check"

    def test_to_dict(self):
        """Test serialization"""
        entry = AuditEntry(
            workflow_id="wf-123",
            phase="testing",
            action="approve",
            actor="john.doe"
        )
        data = entry.to_dict()
        assert data['workflow_id'] == "wf-123"
        assert data['action'] == "approve"


# =============================================================================
# Test GovernanceService
# =============================================================================

class TestGovernanceService:
    """Tests for GovernanceService"""

    def test_initialization(self, governance_service):
        """Test service initialization"""
        assert governance_service is not None
        phases = governance_service.get_all_phases()
        assert len(phases) > 0

    def test_load_protocol(self, governance_service):
        """Test protocol loading"""
        info = governance_service.get_protocol_info()
        assert info['version'] == "1.0"
        assert "requirements" in info['phases']

    def test_get_phase_requirements(self, governance_service):
        """Test getting phase requirements"""
        gate = governance_service.get_phase_requirements("requirements")
        assert gate is not None
        assert gate.phase == "requirements"
        assert len(gate.required_documents) > 0

    def test_check_phase_gate_pass(self, governance_service):
        """Test phase gate check passing"""
        # Record required approval first
        governance_service.record_approval(
            workflow_id="wf-test",
            phase="requirements",
            role="product_owner",
            approver="test_owner"
        )

        # Check with required documents
        context = {
            'documents': {
                'requirements_spec': {'id': 'doc-1', 'content': 'Requirements...'}
            }
        }

        result = governance_service.check_phase_gate(
            workflow_id="wf-test",
            phase="requirements",
            context=context
        )

        assert result.passed is True
        assert ValidationResult.PASSED in result.document_checks.values()
        assert ValidationResult.PASSED in result.approval_checks.values()

    def test_check_phase_gate_missing_document(self, governance_service):
        """Test phase gate check failing due to missing document"""
        # Record approval
        governance_service.record_approval(
            workflow_id="wf-test",
            phase="requirements",
            role="product_owner",
            approver="test_owner"
        )

        # Check without required documents
        context = {'documents': {}}

        result = governance_service.check_phase_gate(
            workflow_id="wf-test",
            phase="requirements",
            context=context
        )

        assert result.passed is False
        assert "Missing required document" in result.errors[0]

    def test_check_phase_gate_missing_approval(self, governance_service):
        """Test phase gate check failing due to missing approval"""
        # Check without any approvals
        context = {
            'documents': {
                'requirements_spec': {'id': 'doc-1'}
            }
        }

        result = governance_service.check_phase_gate(
            workflow_id="wf-test",
            phase="requirements",
            context=context
        )

        assert result.passed is False
        assert any("approval" in e.lower() for e in result.errors)

    def test_record_approval(self, governance_service):
        """Test recording an approval"""
        approval = governance_service.record_approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            approver="jane.doe",
            notes="LGTM"
        )

        assert approval.workflow_id == "wf-123"
        assert approval.role == "architect"
        assert approval.approver == "jane.doe"
        assert approval.expires_at is not None

    def test_revoke_approval(self, governance_service):
        """Test revoking an approval"""
        # First record
        governance_service.record_approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            approver="jane.doe"
        )

        # Then revoke
        result = governance_service.revoke_approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            actor="admin"
        )

        assert result is True

        # Verify it's gone
        result = governance_service.revoke_approval(
            workflow_id="wf-123",
            phase="design",
            role="architect",
            actor="admin"
        )
        assert result is False

    def test_register_custom_validator(self, governance_service):
        """Test registering custom validator"""
        def custom_check(context):
            return context.get('custom_field', False)

        governance_service.register_validator("custom_rule", custom_check)

        # The validator is registered but won't be used unless it's in the protocol
        assert "custom_rule" in governance_service._custom_validators

    def test_audit_trail(self, governance_service):
        """Test audit trail recording"""
        governance_service.check_phase_gate(
            workflow_id="wf-audit",
            phase="requirements",
            context={'documents': {}},
            actor="test_actor"
        )

        trail = governance_service.get_audit_trail(workflow_id="wf-audit")
        assert len(trail) > 0
        assert trail[0].workflow_id == "wf-audit"
        assert trail[0].action == "check"

    def test_audit_trail_filtering(self, governance_service):
        """Test audit trail filtering"""
        # Create some entries
        governance_service.check_phase_gate("wf-1", "requirements", {})
        governance_service.check_phase_gate("wf-2", "design", {})
        governance_service.check_phase_gate("wf-1", "design", {})

        # Filter by workflow
        trail = governance_service.get_audit_trail(workflow_id="wf-1")
        assert all(e.workflow_id == "wf-1" for e in trail)

        # Filter by phase
        trail = governance_service.get_audit_trail(phase="design")
        assert all(e.phase == "design" for e in trail)

    def test_clear_workflow_data(self, governance_service):
        """Test clearing workflow data"""
        governance_service.record_approval(
            workflow_id="wf-clear",
            phase="design",
            role="architect",
            approver="test"
        )

        governance_service.clear_workflow_data("wf-clear")

        # Check approval is gone
        result = governance_service.revoke_approval(
            workflow_id="wf-clear",
            phase="design",
            role="architect",
            actor="admin"
        )
        assert result is False

    def test_unknown_phase(self, governance_service):
        """Test checking unknown phase"""
        result = governance_service.check_phase_gate(
            workflow_id="wf-test",
            phase="unknown_phase",
            context={}
        )

        # Should pass with warning
        assert result.passed is True
        assert len(result.warnings) > 0


# =============================================================================
# Test Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_governance_service(self):
        """Test singleton getter"""
        service1 = get_governance_service()
        service2 = get_governance_service()
        assert service1 is service2

    def test_reset_governance_service(self):
        """Test singleton reset"""
        service1 = get_governance_service()
        reset_governance_service()
        service2 = get_governance_service()
        assert service1 is not service2


# =============================================================================
# Test ValidationResult Enum
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult enum"""

    def test_values(self):
        """Test enum values"""
        assert ValidationResult.PASSED.value == "passed"
        assert ValidationResult.FAILED.value == "failed"
        assert ValidationResult.SKIPPED.value == "skipped"
        assert ValidationResult.PENDING.value == "pending"


# =============================================================================
# Integration Tests
# =============================================================================

class TestGovernanceIntegration:
    """Integration tests for governance workflow"""

    def test_full_phase_workflow(self, governance_service):
        """Test complete phase governance workflow"""
        workflow_id = "wf-integration"

        # 1. Record product owner approval
        governance_service.record_approval(
            workflow_id=workflow_id,
            phase="requirements",
            role="product_owner",
            approver="po@test.com"
        )

        # 2. Check with documents
        context = {
            'documents': {
                'requirements_spec': {'id': 'doc-1', 'title': 'Requirements'}
            }
        }

        result = governance_service.check_phase_gate(
            workflow_id=workflow_id,
            phase="requirements",
            context=context,
            actor="system"
        )

        assert result.passed is True

        # 3. Verify audit trail
        trail = governance_service.get_audit_trail(workflow_id=workflow_id)
        actions = [e.action for e in trail]
        assert "approve" in actions
        assert "check" in actions

    def test_multi_phase_workflow(self, governance_service):
        """Test governance across multiple phases"""
        workflow_id = "wf-multi"

        # Requirements phase
        governance_service.record_approval(workflow_id, "requirements", "product_owner", "po")
        req_result = governance_service.check_phase_gate(
            workflow_id, "requirements",
            {'documents': {'requirements_spec': {}}}
        )

        # Design phase
        governance_service.record_approval(workflow_id, "design", "architect", "arch")
        design_result = governance_service.check_phase_gate(
            workflow_id, "design",
            {'documents': {'design_doc': {}, 'architecture_diagram': {}}}
        )

        # Both should pass
        assert req_result.passed is True
        assert design_result.passed is True
