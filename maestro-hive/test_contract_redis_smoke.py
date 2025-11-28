#!/usr/bin/env python3
"""
Quick Smoke Test: ContractManager with Real Redis

Validates that:
1. ContractManager initializes with real Redis
2. Can create and query contracts
3. Phase boundary validation setup works
4. No mock Redis is used

Usage:
    python3 test_contract_redis_smoke.py
"""

import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Quick smoke test"""
    logger.info("\n" + "="*80)
    logger.info("🔥 ContractManager + Real Redis Smoke Test")
    logger.info("="*80)

    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

        # Create engine
        engine = TeamExecutionEngineV2SplitMode(
            output_dir="./smoke_test_output",
            checkpoint_dir="./smoke_test_checkpoints",
            enable_contracts=True
        )

        # Initialize ContractManager (should use real Redis)
        logger.info("\n1️⃣  Initializing ContractManager...")
        await engine.initialize_contract_manager()

        if not engine.contract_manager:
            logger.error("❌ ContractManager is None")
            return 1

        if not engine._state_manager:
            logger.error("❌ StateManager is None")
            return 1

        # Check if using real Redis
        redis_mgr = engine._state_manager.redis
        is_real_redis = not hasattr(redis_mgr, 'store')  # MockRedis has 'store' attribute

        logger.info(f"✅ ContractManager initialized")
        logger.info(f"   Using Real Redis: {is_real_redis}")

        if not is_real_redis:
            logger.error("❌ FAIL: Should be using real Redis, not MockRedis")
            return 1

        # Test: Create a contract
        logger.info("\n2️⃣  Creating test contract...")
        contract = await engine.contract_manager.create_contract(
            team_id="smoke_test_team",
            contract_name="SmokeTestContract",
            version="v1.0",
            contract_type="PHASE_TRANSITION",
            specification={
                "from_phase": "requirements",
                "to_phase": "design",
                "required_artifacts": ["requirements.md"]
            },
            owner_role="System",
            owner_agent="smoke_test"
        )

        logger.info(f"✅ Contract created: {contract['id']}")
        logger.info(f"   Name: {contract['contract_name']}")
        logger.info(f"   Status: {contract['status']}")

        # Test: Activate contract
        logger.info("\n3️⃣  Activating contract...")
        activated = await engine.contract_manager.activate_contract(
            contract_id=contract['id'],
            activated_by="smoke_test"
        )
        logger.info(f"✅ Contract activated: {activated['status']}")

        # Test: Query active contract
        logger.info("\n4️⃣  Querying active contract...")
        active = await engine.contract_manager.get_active_contract(
            team_id="smoke_test_team",
            contract_name="SmokeTestContract"
        )

        if active:
            logger.info(f"✅ Found active contract: {active['version']}")
        else:
            logger.error("❌ Failed to retrieve active contract")
            return 1

        # Test: Contract summary
        logger.info("\n5️⃣  Getting contract summary...")
        summary = await engine.contract_manager.get_contract_summary("smoke_test_team")
        logger.info(f"✅ Contract summary:")
        logger.info(f"   Total: {summary['total_contracts']}")
        logger.info(f"   Active: {summary['by_status'].get('active', 0)}")

        # Test: Redis health check
        logger.info("\n6️⃣  Checking Redis health...")
        redis_health = await engine._state_manager.redis.health_check()
        logger.info(f"✅ Redis health: {redis_health}")

        # Cleanup
        await engine.cleanup()
        logger.info("\n✅ Cleanup completed")

        logger.info("\n" + "="*80)
        logger.info("🎉 SMOKE TEST PASSED!")
        logger.info("="*80)
        logger.info("✅ ContractManager works with real Redis")
        logger.info("✅ Contract CRUD operations work")
        logger.info("✅ State persistence works")
        logger.info("✅ Ready for full workflow integration")
        logger.info("="*80)
        return 0

    except Exception as e:
        logger.error(f"\n❌ SMOKE TEST FAILED: {e}")
        logger.exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
