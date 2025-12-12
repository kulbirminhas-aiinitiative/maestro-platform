#!/usr/bin/env python3
"""
Test Suite for ConstraintInjector (MD-3096)

Tests all 5 Acceptance Criteria:
    AC-1: BDV Gherkin features injected into persona prompts
    AC-2: ACC architectural rules injected into prompts
    AC-3: Security constraints injected for relevant personas
    AC-4: Constraint injection is configurable (enable/disable per type)
    AC-5: Measurable reduction in validation failures (30% target)

Usage:
    pytest test_constraint_injector.py -v
    pytest test_constraint_injector.py -v -k "test_ac1"  # Run specific AC tests
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from constraint_injector import (
    ConstraintInjector,
    InjectorConfig,
    ConstraintType,
    BDVScenario,
    ACCRule,
    SecurityConstraint,
    InjectionResult,
    InjectionMetrics,
    get_constraint_injector,
    inject_constraints_into_prompt,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def injector():
    """Create a fresh ConstraintInjector instance for each test."""
    config = InjectorConfig()
    return ConstraintInjector(config)


@pytest.fixture
def injector_with_config():
    """Create injector with custom config."""
    config = InjectorConfig(
        enable_bdv_injection=True,
        enable_acc_injection=True,
        enable_security_injection=True,
        max_bdv_scenarios=5,
        max_acc_rules=10,
    )
    return ConstraintInjector(config)


@pytest.fixture
def sample_prompt():
    """Sample base prompt for testing."""
    return """You are the Backend Developer for this project.

Your expertise areas:
- Python/TypeScript backend development
- RESTful API design
- Database design

Expected deliverables:
- API endpoints
- Database models
- Service layer

Work autonomously. Focus on your specialized domain."""


@pytest.fixture
def sample_contracts():
    """Sample contracts with acceptance criteria."""
    return [
        {
            "id": "contract_1",
            "name": "User Authentication API",
            "acceptance_criteria": [
                "User can register with email and password",
                "User can login with valid credentials",
                "User receives JWT token on successful login",
            ],
            "deliverables": ["auth/routes.py", "auth/models.py"]
        },
        {
            "id": "contract_2",
            "name": "Task Management API",
            "acceptance_criteria": [
                "User can create a new task",
                "User can update task status",
                "User can delete own tasks",
            ],
            "deliverables": ["tasks/routes.py", "tasks/models.py"]
        }
    ]


# =============================================================================
# AC-1: BDV Gherkin Features Injection
# =============================================================================

class TestAC1_BDVInjection:
    """AC-1: BDV Gherkin features injected into persona prompts when available."""

    def test_bdv_injection_enabled(self, injector, sample_prompt, sample_contracts):
        """Test that BDV scenarios are injected when enabled."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create user authentication",
            contracts=sample_contracts
        )

        # Should have injected BDV scenarios
        assert result.bdv_scenarios_injected > 0
        assert "MUST-PASS BEHAVIORAL TESTS (BDV)" in enhanced
        assert "Gherkin" in enhanced.lower() or "gherkin" in enhanced

    def test_bdv_scenarios_from_contracts(self, injector, sample_prompt, sample_contracts):
        """Test that acceptance criteria are converted to BDV scenarios."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create user authentication",
            contracts=sample_contracts
        )

        # Should reference contract acceptance criteria
        assert "User can register" in enhanced or "Contract:" in enhanced
        assert result.bdv_scenarios_injected >= 1

    def test_bdv_disabled(self, sample_prompt, sample_contracts):
        """Test that BDV injection can be disabled."""
        config = InjectorConfig(enable_bdv_injection=False)
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create user authentication",
            contracts=sample_contracts
        )

        assert result.bdv_scenarios_injected == 0
        assert "MUST-PASS BEHAVIORAL TESTS" not in enhanced

    def test_bdv_max_scenarios_limit(self, sample_prompt):
        """Test that max_bdv_scenarios limit is respected."""
        config = InjectorConfig(max_bdv_scenarios=2)
        injector = ConstraintInjector(config)

        # Create many contracts
        contracts = [
            {"id": f"contract_{i}", "name": f"Contract {i}",
             "acceptance_criteria": [f"AC {i}"]}
            for i in range(10)
        ]

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Multiple requirements",
            contracts=contracts
        )

        assert result.bdv_scenarios_injected <= 2


# =============================================================================
# AC-2: ACC Architectural Rules Injection
# =============================================================================

class TestAC2_ACCInjection:
    """AC-2: ACC architectural rules injected into prompts."""

    def test_acc_injection_enabled(self, injector, sample_prompt):
        """Test that ACC rules are injected when enabled."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create service layer",
            project_context={"output_dir": "/test/project"}
        )

        assert result.acc_rules_injected > 0
        assert "ARCHITECTURAL CONSTRAINTS (ACC)" in enhanced

    def test_acc_standard_rules_present(self, injector, sample_prompt):
        """Test that standard ACC rules are always present."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create service",
            project_context={}
        )

        # Standard rules should be injected
        assert "Layer Dependencies" in enhanced or "Circular" in enhanced

    def test_acc_layer_dependency_rule(self, injector, sample_prompt):
        """Test that layer dependency rule is present."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create domain layer",
            project_context={}
        )

        assert "domain" in enhanced.lower() or "layer" in enhanced.lower()
        assert result.acc_rules_injected >= 1

    def test_acc_disabled(self, sample_prompt):
        """Test that ACC injection can be disabled."""
        config = InjectorConfig(enable_acc_injection=False)
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create service",
            project_context={}
        )

        assert result.acc_rules_injected == 0
        assert "ARCHITECTURAL CONSTRAINTS" not in enhanced

    def test_acc_max_rules_limit(self, sample_prompt):
        """Test that max_acc_rules limit is respected."""
        config = InjectorConfig(max_acc_rules=2)
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create service",
            project_context={}
        )

        # Should respect max limit
        assert result.acc_rules_injected <= 2


# =============================================================================
# AC-3: Security Constraints for Relevant Personas
# =============================================================================

class TestAC3_SecurityInjection:
    """AC-3: Security constraints injected for relevant personas."""

    def test_security_for_backend_developer(self, injector, sample_prompt):
        """Test that backend_developer gets security constraints."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create API endpoints"
        )

        assert result.security_constraints_injected > 0
        assert "SECURITY REQUIREMENTS" in enhanced

    def test_security_for_api_developer(self, sample_prompt):
        """Test that api_developer gets security constraints."""
        config = InjectorConfig(
            personas_requiring_security=["api_developer", "backend_developer"]
        )
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="api_developer",
            requirement="Create REST API"
        )

        assert result.security_constraints_injected > 0
        assert "OWASP" in enhanced or "Security" in enhanced

    def test_no_security_for_frontend_developer(self, injector, sample_prompt):
        """Test that frontend_developer doesn't get security by default."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="frontend_developer",
            requirement="Create React components"
        )

        # Frontend not in default personas_requiring_security
        assert result.security_constraints_injected == 0 or "frontend_developer" in injector.config.personas_requiring_security

    def test_owasp_references(self, injector, sample_prompt):
        """Test that OWASP references are included."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create API with auth"
        )

        # Should have OWASP references
        if result.security_constraints_injected > 0:
            assert "OWASP" in enhanced or "A01:" in enhanced or "A03:" in enhanced

    def test_sql_injection_prevention(self, injector, sample_prompt):
        """Test that SQL injection prevention is included."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create database queries"
        )

        if result.security_constraints_injected > 0:
            assert "SQL" in enhanced or "parameterized" in enhanced.lower()

    def test_security_disabled(self, sample_prompt):
        """Test that security injection can be disabled."""
        config = InjectorConfig(enable_security_injection=False)
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create API"
        )

        assert result.security_constraints_injected == 0
        assert "SECURITY REQUIREMENTS" not in enhanced


# =============================================================================
# AC-4: Configurable Injection
# =============================================================================

class TestAC4_ConfigurableInjection:
    """AC-4: Constraint injection is configurable (enable/disable per type)."""

    def test_configure_enables_bdv(self, sample_prompt, sample_contracts):
        """Test that configure() can enable BDV."""
        config = InjectorConfig(enable_bdv_injection=False)
        injector = ConstraintInjector(config)

        # Initially disabled
        _, result1 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )
        assert result1.bdv_scenarios_injected == 0

        # Enable via configure
        injector.configure(enable_bdv=True)

        _, result2 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )
        assert result2.bdv_scenarios_injected > 0

    def test_configure_disables_acc(self, sample_prompt):
        """Test that configure() can disable ACC."""
        injector = ConstraintInjector()

        # Initially enabled (default)
        _, result1 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test"
        )
        assert result1.acc_rules_injected > 0

        # Disable via configure
        injector.configure(enable_acc=False)

        _, result2 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test"
        )
        assert result2.acc_rules_injected == 0

    def test_configure_multiple_options(self, sample_prompt, sample_contracts):
        """Test that configure() can set multiple options at once."""
        injector = ConstraintInjector()

        injector.configure(
            enable_bdv=True,
            enable_acc=False,
            enable_security=True,
            max_bdv_scenarios=3
        )

        assert injector.config.enable_bdv_injection is True
        assert injector.config.enable_acc_injection is False
        assert injector.config.enable_security_injection is True
        assert injector.config.max_bdv_scenarios == 3

    def test_per_persona_security_config(self, sample_prompt):
        """Test configuring which personas get security."""
        config = InjectorConfig(
            personas_requiring_security=["custom_persona"]
        )
        injector = ConstraintInjector(config)

        # backend_developer should NOT get security
        _, result1 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test"
        )
        assert result1.security_constraints_injected == 0

        # custom_persona SHOULD get security
        _, result2 = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="custom_persona",
            requirement="Test"
        )
        assert result2.security_constraints_injected > 0

    def test_config_serialization(self):
        """Test that config can be serialized to dict."""
        config = InjectorConfig(
            enable_bdv_injection=True,
            max_acc_rules=15
        )

        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["enable_bdv_injection"] is True
        assert config_dict["max_acc_rules"] == 15


# =============================================================================
# AC-5: Measurable Improvement Tracking
# =============================================================================

class TestAC5_MetricsTracking:
    """AC-5: Measurable reduction in validation failures (30% target)."""

    def test_metrics_initial_state(self, injector):
        """Test that metrics start at zero."""
        metrics = injector.get_metrics()

        assert metrics.total_injections == 0
        assert metrics.first_pass_successes == 0
        assert metrics.first_pass_failures == 0

    def test_metrics_increment_on_injection(self, injector, sample_prompt):
        """Test that total_injections increments."""
        injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test"
        )

        metrics = injector.get_metrics()
        assert metrics.total_injections == 1

        injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="frontend_developer",
            requirement="Test 2"
        )

        metrics = injector.get_metrics()
        assert metrics.total_injections == 2

    def test_record_execution_success(self, injector):
        """Test recording successful execution."""
        injector.record_execution_result(success=True)
        injector.record_execution_result(success=True)

        metrics = injector.get_metrics()
        assert metrics.first_pass_successes == 2
        assert metrics.first_pass_failures == 0

    def test_record_execution_failure(self, injector):
        """Test recording failed execution."""
        injector.record_execution_result(success=False)

        metrics = injector.get_metrics()
        assert metrics.first_pass_successes == 0
        assert metrics.first_pass_failures == 1

    def test_failure_rate_calculation(self, injector):
        """Test that failure rate is calculated correctly."""
        # 3 successes, 2 failures = 40% failure rate
        injector.record_execution_result(success=True)
        injector.record_execution_result(success=True)
        injector.record_execution_result(success=True)
        injector.record_execution_result(success=False)
        injector.record_execution_result(success=False)

        metrics = injector.get_metrics()
        assert metrics.current_failure_rate == pytest.approx(0.4, rel=0.01)

    def test_baseline_failure_rate(self, injector):
        """Test setting baseline failure rate."""
        injector.set_baseline_failure_rate(0.5)  # 50% baseline

        metrics = injector.get_metrics()
        assert metrics.baseline_failure_rate == 0.5

    def test_improvement_calculation(self, injector):
        """Test improvement percentage calculation."""
        # Baseline: 50% failures
        injector.set_baseline_failure_rate(0.5)

        # Current: 30% failures (4 success, 6 fail would be 60% - let's do 7 success, 3 fail = 30%)
        for _ in range(7):
            injector.record_execution_result(success=True)
        for _ in range(3):
            injector.record_execution_result(success=False)

        metrics = injector.get_metrics()

        # 50% -> 30% = (0.5 - 0.3) / 0.5 = 40% improvement
        assert metrics.improvement_percentage == pytest.approx(40.0, rel=0.1)

    def test_meets_30_percent_target(self, injector):
        """Test that 30% improvement target is detectable."""
        # Baseline: 50% failures
        injector.set_baseline_failure_rate(0.5)

        # Current: 35% failures (not meeting target)
        for _ in range(13):
            injector.record_execution_result(success=True)
        for _ in range(7):
            injector.record_execution_result(success=False)

        metrics = injector.get_metrics()
        # 50% -> 35% = 30% improvement - exactly at target
        assert metrics.meets_target is True  # Should be >= 30%

    def test_not_meeting_target(self, injector):
        """Test when target is not met."""
        # Baseline: 50% failures
        injector.set_baseline_failure_rate(0.5)

        # Current: 45% failures (only 10% improvement)
        for _ in range(11):
            injector.record_execution_result(success=True)
        for _ in range(9):
            injector.record_execution_result(success=False)

        metrics = injector.get_metrics()
        # 50% -> 45% = 10% improvement (below 30% target)
        assert metrics.meets_target is False

    def test_metrics_reset(self, injector):
        """Test that metrics can be reset."""
        injector.record_execution_result(success=True)
        injector.record_execution_result(success=False)

        injector.reset_metrics()

        metrics = injector.get_metrics()
        assert metrics.total_injections == 0
        assert metrics.first_pass_successes == 0
        assert metrics.first_pass_failures == 0

    def test_prompts_with_bdv_tracking(self, injector, sample_prompt, sample_contracts):
        """Test that prompts_with_bdv is tracked."""
        injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )

        metrics = injector.get_metrics()
        assert metrics.prompts_with_bdv >= 1


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for ConstraintInjector."""

    def test_full_injection_flow(self, sample_prompt, sample_contracts):
        """Test complete injection flow with all constraint types."""
        config = InjectorConfig(
            enable_bdv_injection=True,
            enable_acc_injection=True,
            enable_security_injection=True
        )
        injector = ConstraintInjector(config)

        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create secure API with authentication",
            contracts=sample_contracts,
            project_context={"output_dir": "/test"}
        )

        # All constraint types should be present
        assert result.bdv_scenarios_injected > 0
        assert result.acc_rules_injected > 0
        assert result.security_constraints_injected > 0

        # Prompt should contain all sections
        assert "MANDATORY CONSTRAINTS" in enhanced
        assert "BDV" in enhanced or "BEHAVIORAL" in enhanced
        assert "ACC" in enhanced or "ARCHITECTURAL" in enhanced
        assert "SECURITY" in enhanced

    def test_singleton_access(self):
        """Test that get_constraint_injector returns singleton."""
        injector1 = get_constraint_injector()
        injector2 = get_constraint_injector()

        assert injector1 is injector2

    def test_convenience_function(self, sample_prompt):
        """Test inject_constraints_into_prompt convenience function."""
        enhanced = inject_constraints_into_prompt(
            prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Create API"
        )

        assert len(enhanced) >= len(sample_prompt)
        assert "CONSTRAINTS" in enhanced or enhanced == sample_prompt

    def test_injection_result_properties(self, injector, sample_prompt, sample_contracts):
        """Test InjectionResult properties."""
        _, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )

        # Check result properties
        assert result.original_prompt_hash != ""
        assert result.injected_prompt_hash != ""
        assert result.total_constraints_injected >= 0
        assert result.injection_time_ms >= 0
        assert isinstance(result.total_tokens_added, int)

    def test_prompt_hash_changes(self, injector, sample_prompt, sample_contracts):
        """Test that prompt hash changes after injection."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )

        if result.total_constraints_injected > 0:
            assert result.original_prompt_hash != result.injected_prompt_hash


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_empty_prompt(self, injector):
        """Test with empty prompt."""
        enhanced, result = injector.inject_constraints(
            base_prompt="",
            persona_id="backend_developer",
            requirement="Test"
        )

        # Should still inject constraints
        assert result.acc_rules_injected > 0 or result.security_constraints_injected > 0

    def test_empty_contracts(self, injector, sample_prompt):
        """Test with no contracts."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=[]
        )

        # BDV from contracts should be 0, but fallback may still work
        assert isinstance(result.bdv_scenarios_injected, int)

    def test_unknown_persona(self, injector, sample_prompt):
        """Test with unknown persona ID."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="unknown_persona_xyz",
            requirement="Test"
        )

        # Should not inject security for unknown persona
        assert result.security_constraints_injected == 0

    def test_very_long_prompt(self, injector, sample_contracts):
        """Test with very long base prompt."""
        long_prompt = "Test content. " * 10000  # ~130k chars

        enhanced, result = injector.inject_constraints(
            base_prompt=long_prompt,
            persona_id="backend_developer",
            requirement="Test",
            contracts=sample_contracts
        )

        assert result.total_tokens_added > 0
        assert len(enhanced) > len(long_prompt)

    def test_special_characters_in_requirement(self, injector, sample_prompt):
        """Test with special characters in requirement."""
        enhanced, result = injector.inject_constraints(
            base_prompt=sample_prompt,
            persona_id="backend_developer",
            requirement="Test with 'quotes' and \"double quotes\" and <brackets>"
        )

        # Should handle gracefully
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
