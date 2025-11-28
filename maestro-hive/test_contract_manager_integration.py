#!/usr/bin/env python3
"""
Test ContractManager Integration

Validates that ContractManager works properly with StateManager and
can be integrated with TeamExecutionEngineV2SplitMode.

Usage:
    python3 test_contract_manager_integration.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def test_state_manager_initialization():
    """Test 1: StateManager initializes correctly"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: StateManager Initialization")
    logger.info("="*80)

    try:
        from state_manager_init import init_state_manager_for_testing, cleanup_state_manager

        # Initialize StateManager
        state_mgr = await init_state_manager_for_testing(
            db_path="./test_maestro_contracts.db",
            use_mock_redis=True
        )

        # Test database health
        db_health = await state_mgr.db.health_check()
        logger.info(f"✅ Database health: {db_health}")

        # Test Redis health
        redis_health = await state_mgr.redis.health_check()
        logger.info(f"✅ Redis health: {redis_health}")

        # Cleanup
        await cleanup_state_manager(state_mgr)
        logger.info("✅ StateManager cleanup successful")

        logger.info("✅ TEST 1 PASSED: StateManager initialization works")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}")
        logger.exception(e)
        return False


async def test_contract_manager_with_state_manager():
    """Test 2: ContractManager works with StateManager"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: ContractManager with StateManager")
    logger.info("="*80)

    try:
        from state_manager_init import init_state_manager_for_testing, cleanup_state_manager
        from contract_manager import ContractManager

        # Initialize StateManager
        state_mgr = await init_state_manager_for_testing(
            db_path="./test_maestro_contracts.db",
            use_mock_redis=True
        )

        # Create ContractManager
        contract_mgr = ContractManager(state_mgr)
        logger.info("✅ ContractManager created successfully")

        # Test: Create a contract
        contract = await contract_mgr.create_contract(
            team_id="test_team_001",
            contract_name="TestAPIContract",
            version="v1.0",
            contract_type="REST_API",
            specification={
                "endpoints": ["/api/test", "/api/health"],
                "methods": ["GET", "POST"]
            },
            owner_role="Tech Lead",
            owner_agent="test_agent_001"
        )

        logger.info(f"✅ Contract created: {contract['id']}")
        logger.info(f"   Name: {contract['contract_name']}")
        logger.info(f"   Version: {contract['version']}")
        logger.info(f"   Status: {contract['status']}")

        # Test: Activate the contract
        activated = await contract_mgr.activate_contract(
            contract_id=contract['id'],
            activated_by="test_user"
        )
        logger.info(f"✅ Contract activated: {activated['status']}")

        # Test: Get active contract
        active_contract = await contract_mgr.get_active_contract(
            team_id="test_team_001",
            contract_name="TestAPIContract"
        )

        if active_contract:
            logger.info(f"✅ Retrieved active contract: {active_contract['version']}")
        else:
            raise Exception("Failed to retrieve active contract")

        # Test: Get contract history
        history = await contract_mgr.get_contract_history(
            team_id="test_team_001",
            contract_name="TestAPIContract"
        )
        logger.info(f"✅ Contract history: {len(history)} version(s)")

        # Cleanup
        await cleanup_state_manager(state_mgr)
        logger.info("✅ StateManager cleanup successful")

        logger.info("✅ TEST 2 PASSED: ContractManager integration works")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}")
        logger.exception(e)
        return False


async def test_engine_initialization():
    """Test 3: TeamExecutionEngineV2SplitMode initializes with ContractManager"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Engine Initialization with ContractManager")
    logger.info("="*80)

    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

        # Create engine
        engine = TeamExecutionEngineV2SplitMode(
            output_dir="./test_output",
            checkpoint_dir="./test_checkpoints",
            quality_threshold=0.70,
            enable_contracts=True
        )
        logger.info("✅ Engine created successfully")

        # Initialize ContractManager
        await engine.initialize_contract_manager()

        if engine.contract_manager is not None:
            logger.info("✅ ContractManager initialized in engine")
        else:
            raise Exception("ContractManager is None after initialization")

        if engine._state_manager is not None:
            logger.info("✅ StateManager initialized in engine")
        else:
            raise Exception("StateManager is None after initialization")

        # Cleanup
        await engine.cleanup()
        logger.info("✅ Engine cleanup successful")

        logger.info("✅ TEST 3 PASSED: Engine initialization with ContractManager works")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}")
        logger.exception(e)
        return False


async def test_phase_boundary_validation():
    """Test 4: Phase boundary validation logic"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Phase Boundary Validation")
    logger.info("="*80)

    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        from team_execution_context import TeamExecutionContext
        from state_manager_init import init_state_manager_for_testing
        from contract_manager import ContractManager

        # Create engine
        engine = TeamExecutionEngineV2SplitMode(
            output_dir="./test_output",
            checkpoint_dir="./test_checkpoints",
            enable_contracts=True
        )

        # Initialize ContractManager
        await engine.initialize_contract_manager()

        # Create a test contract for phase boundary
        if engine.contract_manager:
            contract = await engine.contract_manager.create_contract(
                team_id="test_workflow_001",
                contract_name="phase_boundary_requirements_to_design",
                version="v1.0",
                contract_type="PHASE_TRANSITION",
                specification={
                    "from_phase": "requirements",
                    "to_phase": "design",
                    "required_artifacts": ["requirements.md", "user_stories.md"]
                },
                owner_role="System",
                owner_agent="phase_validator"
            )

            # Activate the contract
            await engine.contract_manager.activate_contract(
                contract_id=contract['id'],
                activated_by="system"
            )

            logger.info(f"✅ Created phase boundary contract: {contract['id']}")

        # Create a mock context with a completed requirements phase
        context = TeamExecutionContext.create_new(
            requirement="Test project",
            workflow_id="test_workflow_001",
            execution_mode="phased"
        )

        # Simulate requirements phase completion
        from examples.sdlc_workflow_context import PhaseResult, PhaseStatus
        from datetime import datetime

        phase_result = PhaseResult(
            phase_name="requirements",
            status=PhaseStatus.COMPLETED,
            outputs={"requirements": "Test requirements"},
            context_received={},
            context_passed={},
            contracts_validated=[],
            artifacts_created=["requirements.md"],
            duration_seconds=10.0,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )

        context.workflow.add_phase_result("requirements", phase_result)

        # Test boundary validation (should find the contract)
        await engine._validate_phase_boundary(
            phase_from="requirements",
            phase_to="design",
            context=context
        )

        logger.info("✅ Phase boundary validation executed successfully")

        # Cleanup
        await engine.cleanup()
        logger.info("✅ Engine cleanup successful")

        logger.info("✅ TEST 4 PASSED: Phase boundary validation works")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}")
        logger.exception(e)
        return False


async def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("🧪 ContractManager Integration Tests")
    logger.info("="*80)

    results = []

    # Test 1: StateManager initialization
    results.append(await test_state_manager_initialization())

    # Test 2: ContractManager with StateManager
    results.append(await test_contract_manager_with_state_manager())

    # Test 3: Engine initialization
    results.append(await test_engine_initialization())

    # Test 4: Phase boundary validation
    results.append(await test_phase_boundary_validation())

    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*80)

    total_tests = len(results)
    passed_tests = sum(results)
    failed_tests = total_tests - passed_tests

    logger.info(f"Total tests: {total_tests}")
    logger.info(f"✅ Passed: {passed_tests}")
    logger.info(f"❌ Failed: {failed_tests}")

    if failed_tests == 0:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error(f"\n❌ {failed_tests} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
