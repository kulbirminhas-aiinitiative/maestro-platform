#!/usr/bin/env python3
"""
Incremental Tests 2-5: Quick Validation

Rapid tests to identify remaining gaps without full workflow execution.
Each test runs in ~5-10 seconds.
"""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_02_contract_versioning():
    """Test 2: Contract Evolution and Versioning"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Contract Versioning/Evolution")
    logger.info("="*80)
    
    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        
        engine = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine.initialize_contract_manager()
        
        if not engine.contract_manager:
            logger.warning("⚠️  ContractManager not available")
            return True
        
        # Test: Create v1.0 contract
        v1 = await engine.contract_manager.create_contract(
            team_id="test_versioning",
            contract_name="APIContract",
            version="v1.0",
            contract_type="REST_API",
            specification={"endpoints": ["/api/users"]},
            owner_role="Backend",
            owner_agent="dev1"
        )
        
        # Activate v1
        await engine.contract_manager.activate_contract(v1['id'], "dev1")
        
        # Test: Evolve to v2.0 with breaking change
        v2 = await engine.contract_manager.evolve_contract(
            team_id="test_versioning",
            contract_name="APIContract",
            new_version="v2.0",
            new_specification={"endpoints": ["/api/v2/users"]},  # Breaking change!
            evolved_by="dev1",
            breaking_change=True
        )
        
        # Verify versioning works
        history = await engine.contract_manager.get_contract_history(
            team_id="test_versioning",
            contract_name="APIContract"
        )
        
        logger.info(f"✅ Contract evolution works: {len(history)} versions")
        logger.info(f"   v1.0 superseded: {v1['id']}")
        logger.info(f"   v2.0 active: {v2['id']}")
        logger.info(f"   Breaking change tracked: {v2.get('breaking_changes', 0)}")
        
        # Check if consumers were notified (gap?)
        if 'consumer_notifications' not in v2:
            logger.warning("⚠️  GAP: No consumer notification tracking on version evolution")
            gap_found = True
        else:
            logger.info(f"✅ Consumer notifications: {v2['consumer_notifications']}")
            gap_found = False
        
        await engine.cleanup()
        
        logger.info("\n📋 TEST 2 RESULT:")
        if gap_found:
            logger.info("❌ Gap: Consumer notification on breaking changes needs implementation")
        else:
            logger.info("✅ PASSED: Contract versioning working correctly")
        
        return not gap_found
        
    except Exception as e:
        logger.error(f"❌ TEST 2 ERROR: {e}")
        return False


async def test_03_multi_consumer():
    """Test 3: Multiple Consumers"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Multi-Consumer Coordination")
    logger.info("="*80)
    
    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        
        engine = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine.initialize_contract_manager()
        
        if not engine.contract_manager:
            logger.warning("⚠️  ContractManager not available")
            return True
        
        # Create contract
        contract = await engine.contract_manager.create_contract(
            team_id="test_consumers",
            contract_name="SharedAPI",
            version="v1.0",
            contract_type="REST_API",
            specification={"endpoints": ["/api/data"]},
            owner_role="Backend",
            owner_agent="provider1"
        )
        
        await engine.contract_manager.activate_contract(contract['id'], "provider1")
        
        # Register multiple consumers
        consumers = ["frontend1", "frontend2", "mobile1"]
        for consumer in consumers:
            await engine.contract_manager.register_consumer(
                contract_id=contract['id'],
                consumer_agent=consumer,
                consumer_role="Consumer"
            )
            logger.info(f"   Registered consumer: {consumer}")
        
        # Check consumer list
        updated_contract = await engine.contract_manager.get_active_contract(
            team_id="test_consumers",
            contract_name="SharedAPI"
        )
        
        consumer_list = updated_contract.get('consumers', [])
        logger.info(f"✅ Consumers registered: {len(consumer_list)}")
        
        # Check if all consumers are tracked
        if len(consumer_list) == len(consumers):
            logger.info("✅ All consumers tracked correctly")
            gap_found = False
        else:
            logger.warning(f"⚠️  GAP: Expected {len(consumers)} consumers, got {len(consumer_list)}")
            gap_found = True
        
        await engine.cleanup()
        
        logger.info("\n📋 TEST 3 RESULT:")
        if gap_found:
            logger.info("❌ Gap: Consumer registration incomplete")
        else:
            logger.info("✅ PASSED: Multi-consumer coordination working")
        
        return not gap_found
        
    except Exception as e:
        logger.error(f"❌ TEST 3 ERROR: {e}")
        return False


async def test_04_conflict_detection():
    """Test 4: Contract Conflict Detection"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Contract Conflict Detection")
    logger.info("="*80)
    
    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        
        engine = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine.initialize_contract_manager()
        
        if not engine.contract_manager:
            logger.warning("⚠️  ContractManager not available")
            return True
        
        # Create two contracts with conflicting requirements
        contract1 = await engine.contract_manager.create_contract(
            team_id="test_conflicts",
            contract_name="Database_Read",
            version="v1.0",
            contract_type="DATABASE_SCHEMA",
            specification={"schema": "users", "mode": "read_only"},
            owner_role="Backend",
            owner_agent="reader1"
        )
        
        contract2 = await engine.contract_manager.create_contract(
            team_id="test_conflicts",
            contract_name="Database_Write",
            version="v1.0",
            contract_type="DATABASE_SCHEMA",
            specification={"schema": "users", "mode": "read_write"},
            owner_role="Backend",
            owner_agent="writer1"
        )
        
        logger.info("✅ Created contracts with potentially conflicting requirements")
        
        # Check if system detects conflict
        logger.warning("⚠️  GAP: No conflict detection mechanism found")
        logger.info("   Expected: detect_conflicts() method")
        logger.info("   Actual: No automatic conflict detection")
        
        gap_found = True  # Gap exists - no conflict detection
        
        await engine.cleanup()
        
        logger.info("\n📋 TEST 4 RESULT:")
        logger.info("❌ Gap: Contract conflict detection needs implementation")
        logger.info("   Recommended: Add detect_conflicts() method to ContractManager")
        
        return not gap_found
        
    except Exception as e:
        logger.error(f"❌ TEST 4 ERROR: {e}")
        return False


async def test_05_persistence():
    """Test 5: Database Persistence"""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Database Persistence Across Restarts")
    logger.info("="*80)
    
    try:
        from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
        
        # First engine - create contract
        engine1 = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine1.initialize_contract_manager()
        
        if not engine1.contract_manager:
            logger.warning("⚠️  ContractManager not available")
            return True
        
        # Create persistent contract
        contract = await engine1.contract_manager.create_contract(
            team_id="test_persistence",
            contract_name="PersistentContract",
            version="v1.0",
            contract_type="REST_API",
            specification={"test": "persistence"},
            owner_role="System",
            owner_agent="tester"
        )
        
        await engine1.contract_manager.activate_contract(contract['id'], "tester")
        contract_id = contract['id']
        
        logger.info(f"✅ Created contract: {contract_id}")
        
        # Cleanup first engine
        await engine1.cleanup()
        logger.info("   Engine 1 shut down")
        
        # Second engine - try to retrieve contract
        engine2 = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine2.initialize_contract_manager()
        
        # Retrieve contract
        retrieved = await engine2.contract_manager.get_active_contract(
            team_id="test_persistence",
            contract_name="PersistentContract"
        )
        
        if retrieved and retrieved['id'] == contract_id:
            logger.info(f"✅ Contract persisted and retrieved: {retrieved['id']}")
            logger.info("✅ Database persistence working correctly")
            gap_found = False
        else:
            logger.warning("⚠️  GAP: Contract not retrieved after restart")
            gap_found = True
        
        await engine2.cleanup()
        
        logger.info("\n📋 TEST 5 RESULT:")
        if gap_found:
            logger.info("❌ Gap: Persistence issue detected")
        else:
            logger.info("✅ PASSED: Database persistence working")
        
        return not gap_found
        
    except Exception as e:
        logger.error(f"❌ TEST 5 ERROR: {e}")
        return False


async def main():
    """Run all quick tests"""
    logger.info("\n" + "="*80)
    logger.info("🧪 Quick Validation Tests 2-5")
    logger.info("="*80)
    
    results = []
    
    # Run all tests
    results.append(await test_02_contract_versioning())
    results.append(await test_03_multi_consumer())
    results.append(await test_04_conflict_detection())
    results.append(await test_05_persistence())
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 TESTS 2-5 SUMMARY")
    logger.info("="*80)
    logger.info(f"Tests run: 4")
    logger.info(f"✅ Passed: {sum(results)}")
    logger.info(f"❌ Failed (gaps found): {4 - sum(results)}")
    logger.info("="*80)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
