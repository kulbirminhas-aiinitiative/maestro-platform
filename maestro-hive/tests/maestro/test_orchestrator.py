"""
Tests for UnifiedMaestroOrchestrator

EPIC: MD-2493 - Unified Maestro CLI
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.maestro.orchestrator import (
    UnifiedMaestroOrchestrator,
    ExecutionMode,
    PhaseType,
    ExecutionState,
    LearningContext,
)


class TestExecutionModeDetection:
    """Test execution mode detection from input."""

    def test_detects_epic_mode_from_jira_key(self):
        """EPIC keys like MD-1234 should be detected as EPIC mode."""
        orchestrator = UnifiedMaestroOrchestrator()

        mode = orchestrator._detect_mode("MD-2493")
        assert mode == ExecutionMode.EPIC

        mode = orchestrator._detect_mode("ABC-1")
        assert mode == ExecutionMode.EPIC

        mode = orchestrator._detect_mode("PROJECT-9999")
        assert mode == ExecutionMode.EPIC

    def test_detects_resume_mode_from_uuid(self):
        """UUIDs should be detected as RESUME mode."""
        orchestrator = UnifiedMaestroOrchestrator()

        mode = orchestrator._detect_mode("550e8400-e29b-41d4-a716-446655440000")
        assert mode == ExecutionMode.RESUME

    def test_detects_adhoc_mode_from_text(self):
        """Free text should be detected as ADHOC mode."""
        orchestrator = UnifiedMaestroOrchestrator()

        mode = orchestrator._detect_mode("Build a REST API for user management")
        assert mode == ExecutionMode.ADHOC

        mode = orchestrator._detect_mode("Fix the login bug")
        assert mode == ExecutionMode.ADHOC


class TestPhaseTypes:
    """Test that all SDLC phases are properly defined."""

    def test_phase_count(self):
        """Should have 10 phases (0-9)."""
        phases = list(PhaseType)
        assert len(phases) == 10

    def test_phase_order(self):
        """Phases should be in correct order."""
        assert PhaseType.RAG_RETRIEVAL.value == 0
        assert PhaseType.UNDERSTANDING.value == 1
        assert PhaseType.DESIGN.value == 2
        assert PhaseType.IMPLEMENTATION.value == 3
        assert PhaseType.TESTING.value == 4
        assert PhaseType.TODO_AUDIT.value == 5
        assert PhaseType.BUILD.value == 6
        assert PhaseType.EVIDENCE.value == 7
        assert PhaseType.COMPLIANCE.value == 8
        assert PhaseType.UPDATE.value == 9


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_default_initialization(self):
        """Should initialize with default settings."""
        orchestrator = UnifiedMaestroOrchestrator()

        assert orchestrator.enable_learning is True
        assert orchestrator.enable_real_execution is True
        assert orchestrator.output_dir == Path("/tmp/maestro")

    def test_custom_initialization(self):
        """Should accept custom settings."""
        orchestrator = UnifiedMaestroOrchestrator(
            output_dir="/custom/output",
            enable_learning=False,
            enable_real_execution=False,
        )

        assert orchestrator.enable_learning is False
        assert orchestrator.enable_real_execution is False
        assert orchestrator.output_dir == Path("/custom/output")


class TestLearningContext:
    """Test LearningContext dataclass."""

    def test_default_context(self):
        """Should have empty defaults."""
        context = LearningContext()

        assert context.similar_executions == []
        assert context.patterns_that_worked == []
        assert context.patterns_that_failed == []
        assert context.recommended_blueprints == []
        assert context.confidence_score == 0.0

    def test_context_with_data(self):
        """Should store provided data."""
        context = LearningContext(
            similar_executions=[{"id": "exec1"}],
            patterns_that_worked=["pattern1"],
            patterns_that_failed=["bad_pattern"],
            recommended_blueprints=["standard_feature_team"],
            confidence_score=0.85,
        )

        assert len(context.similar_executions) == 1
        assert "pattern1" in context.patterns_that_worked
        assert "bad_pattern" in context.patterns_that_failed
        assert context.confidence_score == 0.85


class TestExecutionState:
    """Test ExecutionState dataclass."""

    def test_state_initialization(self):
        """Should initialize with required fields."""
        state = ExecutionState(
            execution_id="test-123",
            mode=ExecutionMode.EPIC,
            input_value="MD-2493",
            current_phase=PhaseType.RAG_RETRIEVAL,
        )

        assert state.execution_id == "test-123"
        assert state.mode == ExecutionMode.EPIC
        assert state.input_value == "MD-2493"
        assert state.current_phase == PhaseType.RAG_RETRIEVAL
        assert state.status == "running"
        assert state.error is None


class TestPhaseExecution:
    """Test individual phase execution."""

    @pytest.mark.asyncio
    async def test_rag_retrieval_phase(self):
        """Phase 0 should populate learning context."""
        orchestrator = UnifiedMaestroOrchestrator(enable_learning=True)
        orchestrator._current_state = ExecutionState(
            execution_id="test-123",
            mode=ExecutionMode.EPIC,
            input_value="MD-2493",
            current_phase=PhaseType.RAG_RETRIEVAL,
        )

        await orchestrator._phase_rag_retrieval()

        assert orchestrator._current_state.learning_context is not None
        assert PhaseType.RAG_RETRIEVAL in orchestrator._current_state.phase_results

    @pytest.mark.asyncio
    async def test_verification_phases(self):
        """Phases 5-8 should complete verification."""
        orchestrator = UnifiedMaestroOrchestrator()
        orchestrator._current_state = ExecutionState(
            execution_id="test-123",
            mode=ExecutionMode.EPIC,
            input_value="MD-2493",
            current_phase=PhaseType.TODO_AUDIT,
        )

        await orchestrator._phase_verification()

        assert PhaseType.TODO_AUDIT in orchestrator._current_state.phase_results
        assert PhaseType.BUILD in orchestrator._current_state.phase_results
        assert PhaseType.EVIDENCE in orchestrator._current_state.phase_results
        assert PhaseType.COMPLIANCE in orchestrator._current_state.phase_results


class TestResultBuilding:
    """Test result building."""

    def test_build_result(self):
        """Should build complete result dictionary."""
        orchestrator = UnifiedMaestroOrchestrator()
        orchestrator._current_state = ExecutionState(
            execution_id="test-123",
            mode=ExecutionMode.EPIC,
            input_value="MD-2493",
            current_phase=PhaseType.UPDATE,
            status="completed",
        )
        orchestrator._current_state.phase_results[PhaseType.RAG_RETRIEVAL] = {"status": "completed"}

        result = orchestrator._build_result()

        assert result["execution_id"] == "test-123"
        assert result["mode"] == "epic"
        assert result["input_value"] == "MD-2493"
        assert result["status"] == "completed"
        assert "RAG_RETRIEVAL" in result["phase_results"]
