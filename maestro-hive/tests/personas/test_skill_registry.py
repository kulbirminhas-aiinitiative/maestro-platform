#!/usr/bin/env python3
"""
E2E Tests for SkillRegistry - REAL MODULE IMPORTS
EPIC: MD-3075 - Remediation for MD-3036
Story: MD-3076 - Rewrite E2E tests with real module imports

CRITICAL: This file imports from the REAL maestro_hive.personas.skill_registry
module, NOT mock implementations.
"""
import pytest
import sys
import os

# Add maestro-hive to path for real imports
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive/src')

# REAL IMPORTS - NOT MOCKS
from maestro_hive.personas.skill_registry import (
    SkillRegistry,
    SkillDefinition,
    SkillCategory,
    SkillStatus,
    SkillCompatibility,
    SkillRequirement,
    SkillMetrics,
    get_skill_registry,
)


class TestSkillRegistryRealModule:
    """
    E2E tests for SkillRegistry using REAL module imports.

    AC-1: Test file imports from maestro_hive.personas
    """

    def test_skill_registry_import_is_real(self):
        """Verify we're testing the real SkillRegistry, not a mock."""
        # Check module path to ensure it's the real implementation
        assert 'maestro_hive.personas.skill_registry' in sys.modules
        # Real methods: register, get, list_all, find_by_category
        assert hasattr(SkillRegistry, 'register')
        assert hasattr(SkillRegistry, 'get')
        assert hasattr(SkillRegistry, 'list_all')

    def test_skill_definition_creation(self):
        """Test creating a real SkillDefinition instance."""
        skill = SkillDefinition(
            id="test-skill-001",
            name="Test Skill",
            description="A test skill for E2E testing",
            category=SkillCategory.TESTING,
            version="1.0.0",
            prompt_template="Execute test: {input}",
            input_schema={"type": "object", "properties": {"input": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            requirements=[],
            compatibility=SkillCompatibility.UNIVERSAL,
        )

        assert skill.id == "test-skill-001"
        assert skill.name == "Test Skill"
        assert skill.category == SkillCategory.TESTING
        assert skill.compatibility == SkillCompatibility.UNIVERSAL

    def test_skill_category_enum_values(self):
        """Test SkillCategory enum has expected values."""
        assert SkillCategory.CODE_GENERATION.value == "code_generation"
        assert SkillCategory.CODE_ANALYSIS.value == "code_analysis"
        assert SkillCategory.TESTING.value == "testing"
        assert SkillCategory.SECURITY.value == "security"
        assert SkillCategory.DOCUMENTATION.value == "documentation"

    def test_skill_status_enum_values(self):
        """Test SkillStatus enum has expected values."""
        assert SkillStatus.AVAILABLE.value == "available"
        assert SkillStatus.DEPRECATED.value == "deprecated"
        assert SkillStatus.BETA.value == "beta"
        assert SkillStatus.DISABLED.value == "disabled"

    def test_skill_compatibility_enum_values(self):
        """Test SkillCompatibility enum has expected values."""
        assert SkillCompatibility.UNIVERSAL.value == "universal"
        assert SkillCompatibility.SPECIALIZED.value == "specialized"
        assert SkillCompatibility.RESTRICTED.value == "restricted"

    def test_skill_requirement_creation(self):
        """Test creating SkillRequirement instances."""
        requirement = SkillRequirement(
            type="capability",
            value="code_execution",
            optional=False
        )

        assert requirement.type == "capability"
        assert requirement.value == "code_execution"
        assert requirement.optional is False

    def test_skill_metrics_initialization(self):
        """Test SkillMetrics default initialization."""
        metrics = SkillMetrics()

        assert metrics.injection_count == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert metrics.average_execution_time_ms == 0.0
        assert metrics.last_used is None

    def test_skill_metrics_record_usage_success(self):
        """Test recording successful skill usage."""
        metrics = SkillMetrics()

        metrics.record_usage(success=True, execution_time_ms=100.0)

        assert metrics.injection_count == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0
        assert metrics.average_execution_time_ms == 100.0
        assert metrics.last_used is not None

    def test_skill_metrics_record_usage_failure(self):
        """Test recording failed skill usage."""
        metrics = SkillMetrics()

        metrics.record_usage(success=False, execution_time_ms=50.0)

        assert metrics.injection_count == 1
        assert metrics.success_count == 0
        assert metrics.failure_count == 1
        assert metrics.average_execution_time_ms == 50.0

    def test_skill_metrics_rolling_average(self):
        """Test rolling average calculation for execution time."""
        metrics = SkillMetrics()

        metrics.record_usage(success=True, execution_time_ms=100.0)
        metrics.record_usage(success=True, execution_time_ms=200.0)
        metrics.record_usage(success=True, execution_time_ms=300.0)

        assert metrics.injection_count == 3
        # Average should be (100 + 200 + 300) / 3 = 200
        assert metrics.average_execution_time_ms == 200.0

    def test_get_skill_registry_singleton(self):
        """Test that get_skill_registry returns a singleton instance."""
        registry1 = get_skill_registry()
        registry2 = get_skill_registry()

        assert registry1 is registry2
        assert isinstance(registry1, SkillRegistry)

    def test_skill_registry_has_required_methods(self):
        """Test SkillRegistry has all required methods."""
        registry = get_skill_registry()

        # Check for required methods (real implementation method names)
        assert callable(getattr(registry, 'register', None))
        assert callable(getattr(registry, 'get', None))
        assert callable(getattr(registry, 'list_all', None))
        assert callable(getattr(registry, 'update_status', None))
        assert callable(getattr(registry, 'unregister', None))


class TestSkillRegistryOperations:
    """Test actual registry operations with real module."""

    @pytest.fixture
    def fresh_registry(self):
        """Create a fresh registry for testing."""
        # Reset singleton for isolated tests
        return SkillRegistry()

    def test_register_and_retrieve_skill(self, fresh_registry):
        """Test registering and retrieving a skill."""
        skill = SkillDefinition(
            id="e2e-test-skill",
            name="E2E Test Skill",
            description="Skill for E2E testing",
            category=SkillCategory.TESTING,
            version="1.0.0",
            prompt_template="Test: {input}",
            input_schema={"type": "string"},
            output_schema={"type": "string"},
        )

        fresh_registry.register(skill)
        retrieved = fresh_registry.get("e2e-test-skill")

        assert retrieved is not None
        assert retrieved.id == "e2e-test-skill"
        assert retrieved.name == "E2E Test Skill"

    def test_list_skills_by_category(self, fresh_registry):
        """Test listing skills filtered by category."""
        # Register multiple skills
        for i, category in enumerate([SkillCategory.TESTING, SkillCategory.TESTING, SkillCategory.CODE_ANALYSIS]):
            skill = SkillDefinition(
                id=f"skill-{i}",
                name=f"Skill {i}",
                description=f"Description {i}",
                category=category,
                version="1.0.0",
                prompt_template="Template",
                input_schema={},
                output_schema={},
            )
            fresh_registry.register(skill)

        # Filter by category using find_by_category
        testing_skills = fresh_registry.find_by_category(SkillCategory.TESTING)

        assert len(testing_skills) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
