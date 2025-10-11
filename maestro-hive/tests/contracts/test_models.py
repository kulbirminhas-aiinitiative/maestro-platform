"""
Unit Tests for Contract Protocol Data Models

Tests all canonical data models including:
- ContractLifecycle and state transitions
- AcceptanceCriterion and CriterionResult
- VerificationResult and caching
- Contract events
- ValidationPolicy
- UniversalContract and lifecycle
"""

import pytest
from datetime import datetime
from contracts.models import (
    ContractLifecycle,
    ContractEventType,
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult,
    ContractEvent,
    ContractProposedEvent,
    ContractAcceptedEvent,
    ContractFulfilledEvent,
    ContractVerifiedEvent,
    ContractBreachedEvent,
    ValidationPolicy,
    ContractBreach,
    UniversalContract,
    ExecutionPlan,
)


# ============================================================================
# Test ContractLifecycle
# ============================================================================

class TestContractLifecycle:
    """Test ContractLifecycle enum"""

    def test_lifecycle_states(self):
        """Test all lifecycle states are defined"""
        assert ContractLifecycle.DRAFT.value == "draft"
        assert ContractLifecycle.PROPOSED.value == "proposed"
        assert ContractLifecycle.NEGOTIATING.value == "negotiating"
        assert ContractLifecycle.ACCEPTED.value == "accepted"
        assert ContractLifecycle.IN_PROGRESS.value == "in_progress"
        assert ContractLifecycle.FULFILLED.value == "fulfilled"
        assert ContractLifecycle.VERIFIED.value == "verified"
        assert ContractLifecycle.VERIFIED_WITH_WARNINGS.value == "verified_with_warnings"
        assert ContractLifecycle.BREACHED.value == "breached"
        assert ContractLifecycle.REJECTED.value == "rejected"
        assert ContractLifecycle.AMENDED.value == "amended"


# ============================================================================
# Test AcceptanceCriterion
# ============================================================================

class TestAcceptanceCriterion:
    """Test AcceptanceCriterion data model"""

    def test_create_criterion(self):
        """Test creating an acceptance criterion"""
        criterion = AcceptanceCriterion(
            criterion_id="crit_001",
            description="Test criterion",
            validator_type="test_validator",
            validation_config={"threshold": 95},
        )

        assert criterion.criterion_id == "crit_001"
        assert criterion.description == "Test criterion"
        assert criterion.validator_type == "test_validator"
        assert criterion.validation_config["threshold"] == 95
        assert criterion.required is True
        assert criterion.blocking is True
        assert criterion.timeout_seconds == 300

    def test_criterion_with_custom_enforcement(self):
        """Test criterion with custom enforcement settings"""
        criterion = AcceptanceCriterion(
            criterion_id="crit_002",
            description="Non-blocking criterion",
            validator_type="test_validator",
            validation_config={},
            required=False,
            blocking=False,
            timeout_seconds=60,
        )

        assert criterion.required is False
        assert criterion.blocking is False
        assert criterion.timeout_seconds == 60


# ============================================================================
# Test CriterionResult
# ============================================================================

class TestCriterionResult:
    """Test CriterionResult data model"""

    def test_create_result(self):
        """Test creating a criterion result"""
        result = CriterionResult(
            criterion_id="crit_001",
            passed=True,
            actual_value=98,
            expected_value=95,
            message="Criterion passed",
        )

        assert result.criterion_id == "crit_001"
        assert result.passed is True
        assert result.actual_value == 98
        assert result.expected_value == 95
        assert result.message == "Criterion passed"

    def test_result_with_evidence(self):
        """Test result with evidence"""
        result = CriterionResult(
            criterion_id="crit_001",
            passed=False,
            actual_value=85,
            expected_value=95,
            message="Below threshold",
            evidence={"details": "Missing alt text on 3 images"},
            evaluator="axe_core",
            duration_ms=1234,
        )

        assert result.evidence["details"] == "Missing alt text on 3 images"
        assert result.evaluator == "axe_core"
        assert result.duration_ms == 1234


# ============================================================================
# Test VerificationResult
# ============================================================================

class TestVerificationResult:
    """Test VerificationResult data model"""

    def test_create_verification_result(self):
        """Test creating a verification result"""
        criteria_results = [
            CriterionResult(
                criterion_id="crit_001",
                passed=True,
                actual_value=98,
                expected_value=95,
                message="Passed",
            )
        ]

        result = VerificationResult(
            contract_id="contract_001",
            passed=True,
            overall_message="All criteria passed",
            criteria_results=criteria_results,
        )

        assert result.contract_id == "contract_001"
        assert result.passed is True
        assert len(result.criteria_results) == 1
        assert result.criteria_results[0].passed is True

    def test_cache_key_generation(self):
        """Test cache key generation"""
        result = VerificationResult(
            contract_id="contract_001",
            passed=True,
            overall_message="Test",
            criteria_results=[],
            validator_versions={"axe": "4.4.0", "openapi": "0.18.0"},
            environment={"python": "3.11"},
        )

        cache_key = result.cache_key()
        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA-256 hex digest

        # Same inputs should produce same cache key
        result2 = VerificationResult(
            contract_id="contract_001",
            passed=True,
            overall_message="Different message",  # Should not affect cache key
            criteria_results=[],
            validator_versions={"axe": "4.4.0", "openapi": "0.18.0"},
            environment={"python": "3.11"},
        )
        assert result.cache_key() == result2.cache_key()


# ============================================================================
# Test Contract Events
# ============================================================================

class TestContractEvents:
    """Test contract event models"""

    def test_base_event(self):
        """Test base ContractEvent"""
        event = ContractEvent(
            event_id="evt_001",
            event_type="test",
            contract_id="contract_001",
        )

        assert event.event_id == "evt_001"
        assert event.event_type == "test"
        assert event.contract_id == "contract_001"
        assert isinstance(event.timestamp, datetime)

    def test_proposed_event(self):
        """Test ContractProposedEvent"""
        contract = UniversalContract(
            contract_id="contract_001",
            contract_type="TEST",
            name="Test Contract",
            description="Test",
            provider_agent="agent_1",
            consumer_agents=["agent_2"],
            specification={},
            acceptance_criteria=[],
        )

        event = ContractProposedEvent(
            event_id="evt_001",
            event_type="proposed",
            contract_id="contract_001",
            proposer="agent_1",
            contract=contract,
        )

        assert event.proposer == "agent_1"
        assert event.contract.contract_id == "contract_001"

    def test_breached_event(self):
        """Test ContractBreachedEvent"""
        breach = ContractBreach(
            breach_id="breach_001",
            contract_id="contract_001",
            severity="major",
            description="Failed verification",
            failed_criteria=["crit_001"],
        )

        event = ContractBreachedEvent(
            event_id="evt_001",
            event_type="breached",
            contract_id="contract_001",
            breach=breach,
            severity="major",
        )

        assert event.breach.breach_id == "breach_001"
        assert event.severity == "major"


# ============================================================================
# Test ValidationPolicy
# ============================================================================

class TestValidationPolicy:
    """Test ValidationPolicy"""

    def test_default_policy(self):
        """Test default validation policy"""
        policy = ValidationPolicy(environment="production")

        assert policy.environment == "production"
        assert policy.accessibility_min_score == 95
        assert policy.response_time_p95_ms == 500
        assert policy.test_coverage_min == 80

    def test_environment_specific_policies(self):
        """Test environment-specific policies"""
        dev_policy = ValidationPolicy.for_environment("development")
        assert dev_policy.accessibility_min_score == 90
        assert dev_policy.response_time_p95_ms == 1000
        assert dev_policy.test_coverage_min == 70

        staging_policy = ValidationPolicy.for_environment("staging")
        assert staging_policy.accessibility_min_score == 95
        assert staging_policy.response_time_p95_ms == 500

        prod_policy = ValidationPolicy.for_environment("production")
        assert prod_policy.accessibility_min_score == 98
        assert prod_policy.response_time_p95_ms == 300

    def test_custom_policy(self):
        """Test custom validation policy"""
        policy = ValidationPolicy(
            environment="custom",
            accessibility_min_score=97,
            response_time_p95_ms=250,
            test_coverage_min=85,
        )

        assert policy.accessibility_min_score == 97
        assert policy.response_time_p95_ms == 250
        assert policy.test_coverage_min == 85


# ============================================================================
# Test ContractBreach
# ============================================================================

class TestContractBreach:
    """Test ContractBreach"""

    def test_create_breach(self):
        """Test creating a contract breach"""
        breach = ContractBreach(
            breach_id="breach_001",
            contract_id="contract_001",
            severity="critical",
            description="Security vulnerability detected",
            failed_criteria=["crit_security_001"],
            remediation_steps=["Update dependencies", "Run security scan"],
        )

        assert breach.breach_id == "breach_001"
        assert breach.severity == "critical"
        assert len(breach.failed_criteria) == 1
        assert len(breach.remediation_steps) == 2


# ============================================================================
# Test UniversalContract
# ============================================================================

class TestUniversalContract:
    """Test UniversalContract"""

    def create_test_contract(self) -> UniversalContract:
        """Helper to create a test contract"""
        return UniversalContract(
            contract_id="contract_001",
            contract_type="UX_DESIGN",
            name="Login Form Design",
            description="Design the login form",
            provider_agent="ux_designer",
            consumer_agents=["frontend_developer"],
            specification={"component": "LoginForm"},
            acceptance_criteria=[
                AcceptanceCriterion(
                    criterion_id="crit_001",
                    description="Visual consistency",
                    validator_type="screenshot_diff",
                    validation_config={"threshold": 0.95},
                )
            ],
        )

    def test_create_contract(self):
        """Test creating a contract"""
        contract = self.create_test_contract()

        assert contract.contract_id == "contract_001"
        assert contract.contract_type == "UX_DESIGN"
        assert contract.lifecycle_state == ContractLifecycle.DRAFT
        assert len(contract.acceptance_criteria) == 1
        assert contract.is_blocking is True
        assert contract.priority == "MEDIUM"

    def test_state_transition_valid(self):
        """Test valid state transitions"""
        contract = self.create_test_contract()

        # DRAFT → PROPOSED
        assert contract.transition_to(ContractLifecycle.PROPOSED) is True
        assert contract.lifecycle_state == ContractLifecycle.PROPOSED

        # PROPOSED → ACCEPTED
        assert contract.transition_to(ContractLifecycle.ACCEPTED) is True
        assert contract.lifecycle_state == ContractLifecycle.ACCEPTED

        # ACCEPTED → IN_PROGRESS
        assert contract.transition_to(ContractLifecycle.IN_PROGRESS) is True
        assert contract.lifecycle_state == ContractLifecycle.IN_PROGRESS

        # IN_PROGRESS → FULFILLED
        assert contract.transition_to(ContractLifecycle.FULFILLED) is True
        assert contract.lifecycle_state == ContractLifecycle.FULFILLED

        # FULFILLED → VERIFIED
        assert contract.transition_to(ContractLifecycle.VERIFIED) is True
        assert contract.lifecycle_state == ContractLifecycle.VERIFIED

    def test_state_transition_invalid(self):
        """Test invalid state transitions"""
        contract = self.create_test_contract()

        # Cannot go directly from DRAFT to VERIFIED
        assert contract.transition_to(ContractLifecycle.VERIFIED) is False
        assert contract.lifecycle_state == ContractLifecycle.DRAFT

        # Move to PROPOSED
        contract.transition_to(ContractLifecycle.PROPOSED)

        # Cannot go from PROPOSED to IN_PROGRESS (must be ACCEPTED first)
        assert contract.transition_to(ContractLifecycle.IN_PROGRESS) is False
        assert contract.lifecycle_state == ContractLifecycle.PROPOSED

    def test_state_transition_terminal(self):
        """Test terminal states don't allow transitions"""
        contract = self.create_test_contract()

        # Move to VERIFIED (terminal state)
        contract.transition_to(ContractLifecycle.PROPOSED)
        contract.transition_to(ContractLifecycle.ACCEPTED)
        contract.transition_to(ContractLifecycle.IN_PROGRESS)
        contract.transition_to(ContractLifecycle.FULFILLED)
        contract.transition_to(ContractLifecycle.VERIFIED)

        # Cannot transition from terminal state
        assert contract.transition_to(ContractLifecycle.AMENDED) is False
        assert contract.lifecycle_state == ContractLifecycle.VERIFIED

    def test_add_event(self):
        """Test adding events to contract"""
        contract = self.create_test_contract()

        event = ContractEvent(
            event_id="evt_001",
            event_type="test",
            contract_id="contract_001",
        )

        contract.add_event(event)
        assert len(contract.events) == 1
        assert contract.events[0].event_id == "evt_001"

    def test_is_fulfilled(self):
        """Test is_fulfilled check"""
        contract = self.create_test_contract()

        assert contract.is_fulfilled() is False

        # Move to FULFILLED
        contract.transition_to(ContractLifecycle.PROPOSED)
        contract.transition_to(ContractLifecycle.ACCEPTED)
        contract.transition_to(ContractLifecycle.IN_PROGRESS)
        contract.transition_to(ContractLifecycle.FULFILLED)

        assert contract.is_fulfilled() is True

        # VERIFIED is also fulfilled
        contract.transition_to(ContractLifecycle.VERIFIED)
        assert contract.is_fulfilled() is True

    def test_is_terminal(self):
        """Test is_terminal check"""
        contract = self.create_test_contract()

        assert contract.is_terminal() is False

        # Move to VERIFIED (terminal)
        contract.transition_to(ContractLifecycle.PROPOSED)
        contract.transition_to(ContractLifecycle.ACCEPTED)
        contract.transition_to(ContractLifecycle.IN_PROGRESS)
        contract.transition_to(ContractLifecycle.FULFILLED)
        contract.transition_to(ContractLifecycle.VERIFIED)

        assert contract.is_terminal() is True

    def test_can_start_work(self):
        """Test can_start_work check"""
        contract = self.create_test_contract()

        assert contract.can_start_work() is False

        # Move to ACCEPTED
        contract.transition_to(ContractLifecycle.PROPOSED)
        contract.transition_to(ContractLifecycle.ACCEPTED)

        assert contract.can_start_work() is True

    def test_contract_with_dependencies(self):
        """Test contract with dependencies"""
        contract = UniversalContract(
            contract_id="contract_002",
            contract_type="API_SPECIFICATION",
            name="Auth API",
            description="Authentication API",
            provider_agent="backend_dev",
            consumer_agents=["frontend_dev"],
            specification={},
            acceptance_criteria=[],
            depends_on=["contract_001"],  # Depends on login form design
        )

        assert len(contract.depends_on) == 1
        assert "contract_001" in contract.depends_on


# ============================================================================
# Test ExecutionPlan
# ============================================================================

class TestExecutionPlan:
    """Test ExecutionPlan"""

    def test_create_execution_plan(self):
        """Test creating an execution plan"""
        contracts = [
            UniversalContract(
                contract_id="c1",
                contract_type="TEST",
                name="Contract 1",
                description="Test",
                provider_agent="agent_1",
                consumer_agents=["agent_2"],
                specification={},
                acceptance_criteria=[],
            ),
            UniversalContract(
                contract_id="c2",
                contract_type="TEST",
                name="Contract 2",
                description="Test",
                provider_agent="agent_1",
                consumer_agents=["agent_2"],
                specification={},
                acceptance_criteria=[],
                depends_on=["c1"],
            ),
        ]

        plan = ExecutionPlan(
            plan_id="plan_001",
            contracts=contracts,
            execution_order=["c1", "c2"],
            dependency_graph={"c1": [], "c2": ["c1"]},
            parallel_groups=[["c1"], ["c2"]],
        )

        assert plan.plan_id == "plan_001"
        assert len(plan.contracts) == 2
        assert plan.execution_order == ["c1", "c2"]
        assert len(plan.parallel_groups) == 2


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
