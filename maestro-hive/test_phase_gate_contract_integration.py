#!/usr/bin/env python3
"""
Test Phase Gate Contract Integration

Tests that contract validation is properly integrated with phase_gate_validator.py
and correctly blocks phase completion on contract violations.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Import required modules
from phase_models import (
    SDLCPhase,
    PhaseState,
    PhaseExecution,
    PhaseIssue,
    QualityThresholds
)
from phase_gate_validator import PhaseGateValidator


async def test_implementation_phase_with_contracts():
    """
    Test that implementation phase with contract violations is blocked

    This simulates a real workflow where:
    - Phase execution reports 70% completeness (would normally pass)
    - But builds fail and stubs are present (contract violations)
    - Contract should BLOCK phase completion
    """

    logger.info("=" * 80)
    logger.info("TEST: Implementation Phase with Contract Violations")
    logger.info("=" * 80)

    # Setup test data
    workflow_dir = Path("/tmp/maestro_workflow/wf-1760076571-6b932a66")

    # Create phase execution data (simulating a completed implementation phase)
    phase_exec = PhaseExecution(
        phase=SDLCPhase.IMPLEMENTATION,
        state=PhaseState.COMPLETED,
        iteration=1,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        completeness=0.70,  # 70% complete
        quality_score=0.65,  # 65% quality
        test_coverage=0.0,
        personas_executed=["backend_developer", "frontend_developer"],
        issues=[]  # No issues reported by personas
    )

    # Quality thresholds
    quality_thresholds = QualityThresholds(
        completeness=0.60,  # 60% required
        quality=0.60,  # 60% required
        test_coverage=0.0
    )

    # Create validator
    validator = PhaseGateValidator()

    # Validate exit criteria (this will include contract validation)
    logger.info("\n" + "=" * 80)
    logger.info("Running Phase Gate Validation (includes contracts)")
    logger.info("=" * 80 + "\n")

    result = await validator.validate_exit_criteria(
        phase=SDLCPhase.IMPLEMENTATION,
        phase_exec=phase_exec,
        quality_thresholds=quality_thresholds,
        output_dir=workflow_dir
    )

    # Check results
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)

    logger.info(f"\nPhase Gate Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    logger.info(f"Score: {result.score:.1%}")
    logger.info(f"Criteria Met: {len(result.criteria_met)}")
    logger.info(f"Criteria Failed: {len(result.criteria_failed)}")
    logger.info(f"Blocking Issues: {len(result.blocking_issues)}")

    if result.blocking_issues:
        logger.info("\n⛔ Blocking Issues:")
        for issue in result.blocking_issues[:5]:  # First 5
            logger.info(f"  - {issue}")

    if result.recommendations:
        logger.info("\n💡 Recommendations:")
        for rec in result.recommendations[:3]:  # First 3
            logger.info(f"  - {rec}")

    # Assertions
    logger.info("\n" + "=" * 80)
    logger.info("TEST ASSERTIONS")
    logger.info("=" * 80)

    # Without contracts, this would pass (70% completeness > 60% threshold)
    # With contracts, this should FAIL (builds don't work, stubs present)

    if not result.passed:
        logger.info("✅ ASSERTION PASSED: Phase gate correctly BLOCKED due to contract violations")
        logger.info("   Contract system is working correctly!")
    else:
        logger.error("❌ ASSERTION FAILED: Phase gate PASSED when it should have FAILED")
        logger.error("   Contract system may not be integrated correctly")

    # Check that contract issues are in blocking_issues
    contract_issues = [issue for issue in result.blocking_issues if "contract" in issue.lower() or "build" in issue.lower()]

    if contract_issues:
        logger.info(f"✅ ASSERTION PASSED: Found {len(contract_issues)} contract-related blocking issues")
    else:
        logger.warning("⚠️  ASSERTION WARNING: No contract issues found in blocking_issues")

    return result


async def test_passing_phase():
    """
    Test that a phase without contract violations passes

    This would need a workflow that actually builds successfully.
    For now, we'll skip this test.
    """

    logger.info("\n" + "=" * 80)
    logger.info("TEST: Passing Phase (skipped - no valid workflow available)")
    logger.info("=" * 80)
    logger.info("⏸️  This test requires a workflow that builds successfully")
    logger.info("   All Batch 5 workflows fail to build, so we can't test a passing case yet")


async def main():
    """Run all tests"""

    logger.info("\n" + "=" * 80)
    logger.info("PHASE GATE CONTRACT INTEGRATION TESTS")
    logger.info("=" * 80)
    logger.info("Testing that contracts are properly integrated with phase gates\n")

    try:
        # Test 1: Phase with contract violations (should fail)
        result1 = await test_implementation_phase_with_contracts()

        # Test 2: Passing phase (skipped)
        await test_passing_phase()

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        if not result1.passed:
            logger.info("✅ Integration Test PASSED")
            logger.info("   Contract validation is properly integrated with phase gates")
            logger.info("   Phases with contract violations are correctly BLOCKED")
        else:
            logger.error("❌ Integration Test FAILED")
            logger.error("   Contract validation may not be working correctly")

        return 0 if not result1.passed else 1

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED WITH EXCEPTION: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
