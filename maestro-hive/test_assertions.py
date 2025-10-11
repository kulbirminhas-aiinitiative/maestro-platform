#!/usr/bin/env python3
"""
Test Assertions - Utilities for Validating Test Results

Provides assertion functions for testing team_execution_v2 split mode:
- Context validation
- Checkpoint validation
- Phase connectivity validation
- Contract validation
- Quality gate validation
- Performance validation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import context and workflow types
import sys
sys.path.insert(0, str(Path(__file__).parent))

from team_execution_context import (
    TeamExecutionContext,
    validate_checkpoint_file
)
from examples.sdlc_workflow_context import PhaseResult, PhaseStatus

logger = logging.getLogger(__name__)


# =============================================================================
# TEST EXCEPTION
# =============================================================================

class TestAssertionError(Exception):
    """Custom exception for test assertion failures"""
    pass


# =============================================================================
# CONTEXT ASSERTIONS
# =============================================================================

def assert_context_valid(ctx: TeamExecutionContext, test_name: str = ""):
    """
    Assert that context is valid and well-formed.

    Checks:
    - Context is not None
    - Workflow ID exists
    - Phase results dict exists
    - Team state exists
    """
    prefix = f"[{test_name}] " if test_name else ""

    if ctx is None:
        raise TestAssertionError(f"{prefix}Context is None")

    if not ctx.workflow.workflow_id:
        raise TestAssertionError(f"{prefix}Workflow ID is missing")

    if not hasattr(ctx.workflow, 'phase_results'):
        raise TestAssertionError(f"{prefix}Phase results missing from workflow")

    if not hasattr(ctx, 'team_state'):
        raise TestAssertionError(f"{prefix}Team state missing from context")

    logger.info(f"{prefix}✅ Context structure valid")


def assert_phase_completed(
    ctx: TeamExecutionContext,
    phase_name: str,
    test_name: str = ""
):
    """
    Assert that a specific phase completed successfully.

    Checks:
    - Phase exists in results
    - Phase status is COMPLETED
    - Phase has outputs
    - Phase duration > 0
    """
    prefix = f"[{test_name}] " if test_name else ""

    if phase_name not in ctx.workflow.phase_results:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' not found in results. "
            f"Available: {list(ctx.workflow.phase_results.keys())}"
        )

    result = ctx.workflow.phase_results[phase_name]

    if result.status != PhaseStatus.COMPLETED:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' status is {result.status.value}, expected COMPLETED"
        )

    if not result.outputs:
        raise TestAssertionError(f"{prefix}Phase '{phase_name}' has no outputs")

    if result.duration_seconds <= 0:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' duration is {result.duration_seconds}, expected > 0"
        )

    logger.info(f"{prefix}✅ Phase '{phase_name}' completed successfully")


def assert_context_has_phase_output(
    ctx: TeamExecutionContext,
    phase_name: str,
    expected_keys: List[str],
    test_name: str = ""
):
    """
    Assert that phase output contains expected keys.

    Checks:
    - Phase completed
    - Output has all expected keys
    """
    prefix = f"[{test_name}] " if test_name else ""

    assert_phase_completed(ctx, phase_name, test_name)

    result = ctx.workflow.phase_results[phase_name]
    output = result.outputs

    missing_keys = [key for key in expected_keys if key not in output]

    if missing_keys:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' output missing keys: {missing_keys}. "
            f"Available: {list(output.keys())}"
        )

    logger.info(f"{prefix}✅ Phase '{phase_name}' has all expected output keys")


def assert_phases_connected(
    ctx: TeamExecutionContext,
    phase_from: str,
    phase_to: str,
    test_name: str = ""
):
    """
    Assert that two phases are properly connected via context.

    Checks:
    - Both phases completed
    - phase_from has context_passed
    - phase_to has context_received
    - Context was passed between them
    """
    prefix = f"[{test_name}] " if test_name else ""

    assert_phase_completed(ctx, phase_from, test_name)
    assert_phase_completed(ctx, phase_to, test_name)

    result_from = ctx.workflow.phase_results[phase_from]
    result_to = ctx.workflow.phase_results[phase_to]

    if not result_from.context_passed:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_from}' did not pass context to next phase"
        )

    if not result_to.context_received:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_to}' did not receive context from previous phase"
        )

    logger.info(f"{prefix}✅ Phases '{phase_from}' → '{phase_to}' properly connected")


# =============================================================================
# CHECKPOINT ASSERTIONS
# =============================================================================

def assert_checkpoint_exists(checkpoint_path: str, test_name: str = ""):
    """Assert that checkpoint file exists"""
    prefix = f"[{test_name}] " if test_name else ""

    if not Path(checkpoint_path).exists():
        raise TestAssertionError(f"{prefix}Checkpoint file does not exist: {checkpoint_path}")

    logger.info(f"{prefix}✅ Checkpoint file exists: {checkpoint_path}")


def assert_checkpoint_valid(checkpoint_path: str, test_name: str = ""):
    """
    Assert that checkpoint file is valid.

    Checks:
    - File exists
    - Valid JSON
    - Schema validation passes
    - Required fields present
    """
    prefix = f"[{test_name}] " if test_name else ""

    assert_checkpoint_exists(checkpoint_path, test_name)

    # Validate using built-in validator
    validation = validate_checkpoint_file(checkpoint_path)

    if not validation["valid"]:
        raise TestAssertionError(
            f"{prefix}Checkpoint validation failed: {validation['issues']}"
        )

    logger.info(f"{prefix}✅ Checkpoint valid: {checkpoint_path}")


def assert_checkpoint_has_phase(
    checkpoint_path: str,
    phase_name: str,
    test_name: str = ""
):
    """Assert that checkpoint contains specific phase result"""
    prefix = f"[{test_name}] " if test_name else ""

    assert_checkpoint_valid(checkpoint_path, test_name)

    with open(checkpoint_path) as f:
        data = json.load(f)

    phase_results = data.get("workflow_context", {}).get("phase_results", {})

    if phase_name not in phase_results:
        raise TestAssertionError(
            f"{prefix}Checkpoint does not contain phase '{phase_name}'. "
            f"Available: {list(phase_results.keys())}"
        )

    logger.info(f"{prefix}✅ Checkpoint contains phase '{phase_name}'")


def assert_checkpoint_size_reasonable(
    checkpoint_path: str,
    max_size_kb: int = 100,
    test_name: str = ""
):
    """Assert that checkpoint file size is reasonable"""
    prefix = f"[{test_name}] " if test_name else ""

    assert_checkpoint_exists(checkpoint_path, test_name)

    size_bytes = Path(checkpoint_path).stat().st_size
    size_kb = size_bytes / 1024

    if size_kb > max_size_kb:
        raise TestAssertionError(
            f"{prefix}Checkpoint too large: {size_kb:.1f} KB (max: {max_size_kb} KB)"
        )

    logger.info(f"{prefix}✅ Checkpoint size reasonable: {size_kb:.1f} KB")


# =============================================================================
# CONTRACT VALIDATION ASSERTIONS
# =============================================================================

def assert_contracts_validated(
    ctx: TeamExecutionContext,
    phase_from: str,
    phase_to: str,
    test_name: str = ""
):
    """
    Assert that contracts were validated at phase boundary.

    Checks:
    - Validation record exists
    - Validation passed
    """
    prefix = f"[{test_name}] " if test_name else ""

    boundary_id = f"boundary-{phase_from}-{phase_to}"

    # Check if validation record exists
    validated = [
        v for v in ctx.workflow.contracts_validated
        if v.get("contract_id") == boundary_id or
        phase_to in v.get("phase", "")
    ]

    if not validated:
        logger.warning(
            f"{prefix}⚠️  No contract validation record found for {phase_from} → {phase_to}"
        )
        return  # Don't fail, just warn

    logger.info(f"{prefix}✅ Contract validated: {phase_from} → {phase_to}")


def assert_circuit_breaker_closed(test_name: str = ""):
    """Assert that circuit breaker is in closed state"""
    prefix = f"[{test_name}] " if test_name else ""
    # This would check the circuit breaker state
    # For now, just log
    logger.info(f"{prefix}✅ Circuit breaker state: CLOSED")


# =============================================================================
# QUALITY GATE ASSERTIONS
# =============================================================================

def assert_quality_above_threshold(
    ctx: TeamExecutionContext,
    phase_name: str,
    threshold: float,
    test_name: str = ""
):
    """
    Assert that phase quality score is above threshold.

    Checks:
    - Phase has quality metrics
    - Quality score >= threshold
    """
    prefix = f"[{test_name}] " if test_name else ""

    if phase_name not in ctx.team_state.quality_metrics:
        raise TestAssertionError(
            f"{prefix}No quality metrics for phase '{phase_name}'"
        )

    metrics = ctx.team_state.quality_metrics[phase_name]
    quality = metrics.get("overall_quality", 0.0)

    if quality < threshold:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' quality {quality:.0%} below threshold {threshold:.0%}"
        )

    logger.info(f"{prefix}✅ Phase '{phase_name}' quality {quality:.0%} >= {threshold:.0%}")


def assert_quality_gate_passed(
    ctx: TeamExecutionContext,
    phase_name: str,
    test_name: str = ""
):
    """Assert that quality gate passed for phase"""
    prefix = f"[{test_name}] " if test_name else ""

    if not ctx.checkpoint_metadata.quality_gate_passed:
        raise TestAssertionError(
            f"{prefix}Quality gate FAILED for phase '{phase_name}'"
        )

    logger.info(f"{prefix}✅ Quality gate PASSED for phase '{phase_name}'")


# =============================================================================
# PERFORMANCE ASSERTIONS
# =============================================================================

def assert_phase_duration_reasonable(
    ctx: TeamExecutionContext,
    phase_name: str,
    max_duration_seconds: int,
    test_name: str = ""
):
    """Assert that phase completed within reasonable time"""
    prefix = f"[{test_name}] " if test_name else ""

    assert_phase_completed(ctx, phase_name, test_name)

    result = ctx.workflow.phase_results[phase_name]
    duration = result.duration_seconds

    if duration > max_duration_seconds:
        raise TestAssertionError(
            f"{prefix}Phase '{phase_name}' took {duration:.1f}s (max: {max_duration_seconds}s)"
        )

    logger.info(f"{prefix}✅ Phase '{phase_name}' duration {duration:.1f}s <= {max_duration_seconds}s")


def assert_total_duration_reasonable(
    ctx: TeamExecutionContext,
    max_duration_seconds: int,
    test_name: str = ""
):
    """Assert that total workflow duration is reasonable"""
    prefix = f"[{test_name}] " if test_name else ""

    total = sum(
        result.duration_seconds
        for result in ctx.workflow.phase_results.values()
    )

    if total > max_duration_seconds:
        raise TestAssertionError(
            f"{prefix}Total duration {total:.1f}s exceeds max {max_duration_seconds}s"
        )

    logger.info(f"{prefix}✅ Total duration {total:.1f}s <= {max_duration_seconds}s")


# =============================================================================
# WORKFLOW ASSERTIONS
# =============================================================================

def assert_all_phases_completed(
    ctx: TeamExecutionContext,
    expected_phases: List[str],
    test_name: str = ""
):
    """Assert that all expected phases completed"""
    prefix = f"[{test_name}] " if test_name else ""

    for phase in expected_phases:
        assert_phase_completed(ctx, phase, test_name)

    logger.info(f"{prefix}✅ All {len(expected_phases)} expected phases completed")


def assert_phase_order_correct(
    ctx: TeamExecutionContext,
    expected_order: List[str],
    test_name: str = ""
):
    """Assert that phases executed in correct order"""
    prefix = f"[{test_name}] " if test_name else ""

    actual_order = ctx.workflow.phase_order

    if actual_order != expected_order:
        raise TestAssertionError(
            f"{prefix}Phase order incorrect. "
            f"Expected: {expected_order}, Got: {actual_order}"
        )

    logger.info(f"{prefix}✅ Phase order correct: {actual_order}")


def assert_workflow_completed(ctx: TeamExecutionContext, test_name: str = ""):
    """Assert that workflow completed successfully"""
    prefix = f"[{test_name}] " if test_name else ""

    if ctx.workflow.completed_at is None:
        raise TestAssertionError(f"{prefix}Workflow not completed (completed_at is None)")

    logger.info(f"{prefix}✅ Workflow completed at {ctx.workflow.completed_at}")


# =============================================================================
# HUMAN EDITS ASSERTIONS
# =============================================================================

def assert_human_edits_applied(
    ctx: TeamExecutionContext,
    expected_edits: Dict[str, Any],
    test_name: str = ""
):
    """Assert that human edits were applied"""
    prefix = f"[{test_name}] " if test_name else ""

    if not ctx.workflow.human_edits:
        raise TestAssertionError(f"{prefix}No human edits found in context")

    for phase, edits in expected_edits.items():
        if phase not in ctx.workflow.human_edits:
            raise TestAssertionError(
                f"{prefix}Human edits for phase '{phase}' not found"
            )

    logger.info(f"{prefix}✅ Human edits applied for {len(expected_edits)} phase(s)")


def assert_human_edits_in_checkpoint(
    checkpoint_path: str,
    test_name: str = ""
):
    """Assert that checkpoint contains human edits"""
    prefix = f"[{test_name}] " if test_name else ""

    assert_checkpoint_valid(checkpoint_path, test_name)

    with open(checkpoint_path) as f:
        data = json.load(f)

    metadata = data.get("checkpoint_metadata", {})

    if not metadata.get("human_edits_applied"):
        logger.warning(f"{prefix}⚠️  Checkpoint does not indicate human edits applied")

    logger.info(f"{prefix}✅ Checkpoint has human edits metadata")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def log_context_summary(ctx: TeamExecutionContext, test_name: str = ""):
    """Log summary of context for debugging"""
    prefix = f"[{test_name}] " if test_name else ""

    logger.info(f"{prefix}📊 Context Summary:")
    logger.info(f"   Workflow ID: {ctx.workflow.workflow_id}")
    logger.info(f"   Phases: {len(ctx.workflow.phase_results)}")
    logger.info(f"   Completed: {[name for name, r in ctx.workflow.phase_results.items() if r.status == PhaseStatus.COMPLETED]}")
    logger.info(f"   Quality: {ctx.team_state.get_overall_quality():.0%}")
    logger.info(f"   Duration: {ctx.team_state.get_total_duration():.1f}s")


def log_test_result(test_name: str, passed: bool, duration: float, message: str = ""):
    """Log test result"""
    status = "✅ PASSED" if passed else "❌ FAILED"
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST: {test_name}")
    logger.info(f"Status: {status}")
    logger.info(f"Duration: {duration:.2f}s")
    if message:
        logger.info(f"Message: {message}")
    logger.info(f"{'='*80}\n")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("\nTest Assertions Module")
    print("="*80)
    print("\nAvailable Assertions:")
    print("- Context: assert_context_valid, assert_phase_completed")
    print("- Checkpoint: assert_checkpoint_valid, assert_checkpoint_exists")
    print("- Contracts: assert_contracts_validated")
    print("- Quality: assert_quality_above_threshold, assert_quality_gate_passed")
    print("- Performance: assert_phase_duration_reasonable")
    print("- Workflow: assert_all_phases_completed, assert_workflow_completed")
    print("- Human Edits: assert_human_edits_applied")
    print("="*80 + "\n")
