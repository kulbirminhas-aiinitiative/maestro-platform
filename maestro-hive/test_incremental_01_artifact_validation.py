#!/usr/bin/env python3
"""
Incremental Test 1: Artifact Validation at Phase Boundaries

Tests that phase boundary validation checks for required artifacts
and properly handles missing artifacts.

Gap Being Tested:
- Does _validate_phase_boundary() check for required artifacts?
- How does it handle missing artifacts?
- Can contracts specify required artifacts from previous phase?
"""

import asyncio
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def test_artifact_validation():
    """Test that phase boundaries validate required artifacts"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Artifact Validation at Phase Boundaries")
    logger.info("="*80)

    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        from team_execution_context import TeamExecutionContext
        from examples.sdlc_workflow_context import PhaseResult, PhaseStatus

        # Create engine
        engine = TeamExecutionEngineV2SplitMode(
            output_dir="./test_artifact_output",
            enable_contracts=True
        )

        # Initialize ContractManager
        await engine.initialize_contract_manager()

        if not engine.contract_manager:
            logger.warning("⚠️  ContractManager not available, skipping test")
            return True

        # Create a phase boundary contract with required artifacts
        contract = await engine.contract_manager.create_contract(
            team_id="test_artifact_team",
            contract_name="phase_boundary_requirements_to_design",
            version="v1.0",
            contract_type="PHASE_TRANSITION",
            specification={
                "from_phase": "requirements",
                "to_phase": "design",
                "required_artifacts": [
                    "requirements.md",
                    "user_stories.md",
                    "acceptance_criteria.md"
                ],
                "validation_rules": {
                    "min_artifacts": 3,
                    "required_fields": ["requirements", "user_stories"]
                }
            },
            owner_role="System",
            owner_agent="phase_validator"
        )

        # Activate contract
        await engine.contract_manager.activate_contract(
            contract_id=contract['id'],
            activated_by="system"
        )

        logger.info(f"✅ Created contract with required artifacts: {contract['specification']['required_artifacts']}")

        # Create context with requirements phase - BUT MISSING ARTIFACTS
        context = TeamExecutionContext.create_new(
            requirement="Test artifact validation",
            workflow_id="test_artifact_team",
            execution_mode="phased"
        )

        # Simulate requirements phase with incomplete artifacts
        phase_result = PhaseResult(
            phase_name="requirements",
            status=PhaseStatus.COMPLETED,
            outputs={"requirements": "Basic requirements doc"},
            context_received={},
            context_passed={},
            contracts_validated=[],
            artifacts_created=["requirements.md"],  # MISSING 2 required artifacts!
            duration_seconds=10.0,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )

        context.workflow.add_phase_result("requirements", phase_result)

        logger.info(f"📦 Requirements phase artifacts: {phase_result.artifacts_created}")
        logger.info(f"⚠️  Missing artifacts: user_stories.md, acceptance_criteria.md")

        # Test validation - should detect missing artifacts
        logger.info("\n🔍 Testing phase boundary validation...")

        try:
            await engine._validate_phase_boundary(
                phase_from="requirements",
                phase_to="design",
                context=context
            )

            # If we get here, validation did NOT detect the missing artifacts
            logger.error("❌ FIX VERIFICATION FAILED: Validation did not raise exception for missing artifacts!")
            await engine.cleanup()
            return False

        except Exception as e:
            # Validation SHOULD raise an exception for missing artifacts
            if "Missing required artifacts" in str(e):
                logger.info(f"✅ Validation correctly detected missing artifacts: {e}")
                validation_working = True
            else:
                logger.error(f"❌ Unexpected error: {e}")
                validation_working = False

        # Cleanup
        await engine.cleanup()

        if validation_working:
            logger.info("\n" + "="*80)
            logger.info("TEST 1 RESULT: ✅ PASSED - Fix Verified!")
            logger.info("="*80)
            logger.info("✅ Phase boundary validation NOW checks required artifacts")
            logger.info("✅ Detects missing artifacts correctly")
            logger.info("✅ Raises ValidationException when artifacts are missing")
            logger.info("="*80)
            return True
        else:
            logger.info("\n" + "="*80)
            logger.info("TEST 1 RESULT: ❌ FAILED")
            logger.info("="*80)
            return False

    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}")
        logger.exception(e)
        return False


if __name__ == "__main__":
    result = asyncio.run(test_artifact_validation())
    sys.exit(0 if result else 1)
