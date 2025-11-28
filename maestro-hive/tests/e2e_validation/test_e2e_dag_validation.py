#!/usr/bin/env python3
"""
End-to-End DAG Validation Test - Phase 1 Smoke Test

Tests the complete integration of:
- DAG workflow execution
- PolicyLoader (contract-as-code)
- QualityFabricClient integration
- Phase gate validation
- Audit trail logging

This is the critical validation that Phase 0 integration actually works.
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import DAG components
from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    WorkflowContext,
    NodeType,
    NodeStatus,
    RetryPolicy
)
from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent

# Import policy components
from policy_loader import get_policy_loader
from quality_fabric_client import QualityFabricClient


# =============================================================================
# MOCK PHASE EXECUTORS
# =============================================================================

async def mock_requirements_phase(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock requirements phase executor.
    Returns realistic outputs that should PASS policy validation.
    """
    logger.info("🎭 Executing Mock Requirements Phase")

    await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'phase': 'requirements',
        'documentation_completeness': 0.95,  # 95% > 90% threshold ✓
        'stakeholder_approval': 1.0,  # 100% ✓
        'acceptance_criteria_defined': 1.0,  # 100% ✓
        'requirements_traceability': 0.97,  # 97% > 95% ✓
        'clarity_score': 0.85,  # 85% > 80% ✓
        'deliverables': {
            'prd_document': 'requirements/PRD.md',
            'user_stories': 'requirements/user_stories.md',
            'acceptance_criteria': 'requirements/acceptance.md'
        },
        'message': 'Requirements phase completed successfully'
    }


async def mock_design_phase(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock design phase executor.
    Returns realistic outputs that should PASS policy validation.
    """
    logger.info("🎭 Executing Mock Design Phase")

    await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'phase': 'design',
        'architecture_documentation': 0.95,  # 95% > 90% ✓
        'design_review_approval': 1.0,  # 100% ✓
        'api_specification_completeness': 0.98,  # 98% > 95% ✓
        'database_schema_defined': 1.0,  # 100% ✓
        'security_design_review': 1.0,  # 100% ✓
        'scalability_assessment': 0.90,  # 90% > 80% ✓
        'deliverables': {
            'architecture_diagram': 'design/architecture.png',
            'api_specification': 'design/api_spec.yaml',
            'database_schema': 'design/schema.sql'
        },
        'message': 'Design phase completed successfully'
    }


async def mock_implementation_phase_pass(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock implementation phase executor - PASSING scenario.
    Returns outputs that meet all quality gates.
    """
    logger.info("🎭 Executing Mock Implementation Phase (PASS scenario)")

    await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'phase': 'implementation',
        'build_success_rate': 0.98,  # 98% > 95% ✓
        'code_quality_score': 8.5,  # 8.5 > 8.0 ✓
        'test_coverage': 0.85,  # 85% > 80% ✓
        'stub_rate': 0.02,  # 2% < 5% ✓
        'security_vulnerabilities': 0,  # 0 ✓
        'code_review_completion': 1.0,  # 100% ✓
        'documentation_coverage': 0.75,  # 75% > 70% ✓
        'completeness': 0.95,
        'deliverables': {
            'source_code': 'src/',
            'unit_tests': 'tests/',
            'build_logs': 'logs/build.log'
        },
        'message': 'Implementation phase completed successfully'
    }


async def mock_implementation_phase_fail(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock implementation phase executor - FAILING scenario.
    Returns outputs that FAIL code quality gate (BLOCKING).
    """
    logger.info("🎭 Executing Mock Implementation Phase (FAIL scenario)")

    await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'phase': 'implementation',
        'build_success_rate': 0.98,  # 98% > 95% ✓
        'code_quality_score': 6.5,  # 6.5 < 8.0 ❌ BLOCKING FAILURE
        'test_coverage': 0.85,  # 85% > 80% ✓
        'stub_rate': 0.02,  # 2% < 5% ✓
        'security_vulnerabilities': 0,  # 0 ✓
        'code_review_completion': 1.0,  # 100% ✓
        'documentation_coverage': 0.60,  # 60% < 70% ⚠️ WARNING
        'completeness': 0.85,
        'deliverables': {
            'source_code': 'src/',
            'unit_tests': 'tests/',
            'build_logs': 'logs/build.log'
        },
        'message': 'Implementation phase completed with quality issues'
    }


async def mock_implementation_phase_bypass(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock implementation phase executor - BYPASS scenario.
    Returns outputs that have WARNING failures (bypassable).
    """
    logger.info("🎭 Executing Mock Implementation Phase (BYPASS scenario)")

    await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'phase': 'implementation',
        'build_success_rate': 0.98,  # 98% > 95% ✓
        'code_quality_score': 8.2,  # 8.2 > 8.0 ✓
        'test_coverage': 0.85,  # 85% > 80% ✓
        'stub_rate': 0.02,  # 2% < 5% ✓
        'security_vulnerabilities': 0,  # 0 ✓
        'code_review_completion': 1.0,  # 100% ✓
        'documentation_coverage': 0.55,  # 55% < 70% ⚠️ WARNING (bypassable)
        'completeness': 0.90,
        'deliverables': {
            'source_code': 'src/',
            'unit_tests': 'tests/',
            'build_logs': 'logs/build.log'
        },
        'message': 'Implementation phase completed (documentation below threshold)'
    }


# =============================================================================
# TEST SCENARIOS
# =============================================================================

async def test_scenario_1_pass():
    """
    TEST 1: Complete workflow with all gates passing.

    Workflow: Requirements → Design → Implementation
    Expected: All phases pass, workflow completes successfully
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: PASS SCENARIO - All gates should pass")
    logger.info("=" * 80)

    # Create workflow
    workflow = WorkflowDAG(
        workflow_id="test-pass-workflow",
        name="E2E Validation Test - PASS"
    )

    # Add nodes
    req_node = WorkflowNode(
        node_id="requirements",
        name="Requirements Phase",
        node_type=NodeType.PHASE,
        executor=mock_requirements_phase,
        dependencies=[],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(req_node)

    design_node = WorkflowNode(
        node_id="design",
        name="Design Phase",
        node_type=NodeType.PHASE,
        executor=mock_design_phase,
        dependencies=["requirements"],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(design_node)
    workflow.add_edge("requirements", "design")

    impl_node = WorkflowNode(
        node_id="implementation",
        name="Implementation Phase",
        node_type=NodeType.PHASE,
        executor=mock_implementation_phase_pass,
        dependencies=["design"],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(impl_node)
    workflow.add_edge("design", "implementation")

    # Create executor with contract validation enabled
    context_store = WorkflowContextStore()

    events = []
    async def event_handler(event: ExecutionEvent):
        events.append(event)
        logger.info(f"  Event: {event.event_type.value} - {event.node_id or 'workflow'}")

    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        event_handler=event_handler,
        enable_contract_validation=True  # ← CRITICAL: This enables our new integration
    )

    # Execute workflow
    try:
        context = await executor.execute()

        # Verify results
        logger.info("\n📊 TEST 1 RESULTS:")
        logger.info("-" * 80)

        # Check all nodes completed
        for node_id in ["requirements", "design", "implementation"]:
            state = context.get_node_state(node_id)
            if state and state.status == NodeStatus.COMPLETED:
                logger.info(f"  ✅ {node_id}: {state.status.value}")

                # Check for validation results
                if state.output and 'validation_results' in state.output:
                    val_results = state.output['validation_results']
                    policy_status = val_results.get('policy_validation', {}).get('status', 'unknown')
                    logger.info(f"     Policy validation: {policy_status}")
            else:
                logger.error(f"  ❌ {node_id}: {state.status.value if state else 'NO STATE'}")
                return False

        logger.info("\n✅ TEST 1 PASSED: All phases completed successfully")
        return True

    except Exception as e:
        logger.error(f"\n❌ TEST 1 FAILED: {e}")
        return False


async def test_scenario_2_fail():
    """
    TEST 2: Workflow with BLOCKING gate failure.

    Workflow: Implementation phase fails code_quality gate
    Expected: Node fails, workflow stops
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: FAIL SCENARIO - Code quality gate should block")
    logger.info("=" * 80)

    # Create workflow
    workflow = WorkflowDAG(
        workflow_id="test-fail-workflow",
        name="E2E Validation Test - FAIL"
    )

    # Single implementation node (for focused testing)
    impl_node = WorkflowNode(
        node_id="implementation",
        name="Implementation Phase",
        node_type=NodeType.PHASE,
        executor=mock_implementation_phase_fail,
        dependencies=[],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(impl_node)

    # Create executor
    context_store = WorkflowContextStore()
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        enable_contract_validation=True
    )

    # Execute workflow (should fail)
    try:
        context = await executor.execute()

        # Should NOT reach here
        logger.error("\n❌ TEST 2 FAILED: Workflow should have failed but succeeded")
        return False

    except Exception as e:
        # Expected failure
        logger.info(f"\n✅ Workflow failed as expected: {e}")

        # Verify node state
        executions = await context_store.list_executions(workflow.workflow_id)
        if executions:
            context = await context_store.load_context(executions[-1])
            state = context.get_node_state("implementation")

            if state and state.status == NodeStatus.FAILED:
                logger.info(f"  ✅ Node status: {state.status.value}")
                logger.info(f"  ✅ Error: {state.error_message}")

                # Check validation results
                if state.output and 'validation_results' in state.output:
                    val_results = state.output['validation_results']
                    policy_result = val_results.get('policy_validation', {})
                    logger.info(f"  ✅ Policy validation status: {policy_result.get('status')}")
                    logger.info(f"  ✅ Gates failed: {len(policy_result.get('gates_failed', []))}")

                logger.info("\n✅ TEST 2 PASSED: Blocking gate correctly failed the workflow")
                return True
            else:
                logger.error(f"  ❌ Node should be FAILED, got: {state.status.value if state else 'NO STATE'}")
                return False
        else:
            logger.error("  ❌ No execution found in context store")
            return False


async def test_scenario_3_bypass():
    """
    TEST 3: Workflow with WARNING gate (bypassable).

    Workflow: Implementation phase has documentation WARNING
    Expected: Node completes with warnings logged
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: BYPASS SCENARIO - WARNING gates should not block")
    logger.info("=" * 80)

    # Create workflow
    workflow = WorkflowDAG(
        workflow_id="test-bypass-workflow",
        name="E2E Validation Test - BYPASS"
    )

    # Implementation node with warning
    impl_node = WorkflowNode(
        node_id="implementation",
        name="Implementation Phase",
        node_type=NodeType.PHASE,
        executor=mock_implementation_phase_bypass,
        dependencies=[],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(impl_node)

    # Create executor
    context_store = WorkflowContextStore()
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        enable_contract_validation=True
    )

    # Execute workflow
    try:
        context = await executor.execute()

        # Verify results
        state = context.get_node_state("implementation")

        if state and state.status == NodeStatus.COMPLETED:
            logger.info(f"\n✅ Node completed despite warnings: {state.status.value}")

            # Check validation results for warnings
            if state.output and 'validation_results' in state.output:
                val_results = state.output['validation_results']
                policy_result = val_results.get('policy_validation', {})

                warnings = [g for g in policy_result.get('gates_failed', [])
                           if g.get('severity') == 'WARNING']

                if warnings:
                    logger.info(f"  ✅ Warnings logged: {len(warnings)} gate(s)")
                    for warn in warnings:
                        logger.info(f"     - {warn.get('gate_name')}: {warn.get('message')}")
                else:
                    logger.warning("  ⚠️  No warnings found in validation results")

            logger.info("\n✅ TEST 3 PASSED: WARNING gates did not block execution")
            return True
        else:
            logger.error(f"\n❌ TEST 3 FAILED: Node should complete, got: {state.status.value if state else 'NO STATE'}")
            return False

    except Exception as e:
        logger.error(f"\n❌ TEST 3 FAILED: Workflow should succeed with warnings: {e}")
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def main():
    """Run all Phase 1 smoke tests"""

    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: END-TO-END DAG VALIDATION - SMOKE TEST")
    logger.info("=" * 80)
    logger.info("Testing: DAG + PolicyLoader + QualityFabric integration")
    logger.info("=" * 80)

    # Verify prerequisites
    logger.info("\n🔍 Verifying prerequisites...")

    try:
        policy_loader = get_policy_loader()
        logger.info("  ✅ PolicyLoader available")

        # Test loading a phase SLO
        impl_slo = policy_loader.get_phase_slo("implementation")
        if impl_slo:
            logger.info(f"  ✅ Implementation phase SLO loaded: {len(impl_slo.success_criteria)} criteria")
        else:
            logger.warning("  ⚠️  Could not load implementation SLO")
    except Exception as e:
        logger.error(f"  ❌ PolicyLoader error: {e}")
        return 1

    try:
        qf_client = QualityFabricClient()
        logger.info("  ✅ QualityFabricClient available")
    except Exception as e:
        logger.warning(f"  ⚠️  QualityFabricClient warning: {e}")

    # Run test scenarios
    results = {}

    try:
        # Test 1: PASS scenario
        logger.info("\n" + "=" * 80)
        logger.info("Running Test Scenario 1: PASS")
        logger.info("=" * 80)
        results['test_1_pass'] = await test_scenario_1_pass()
        await asyncio.sleep(1)  # Brief pause between tests

        # Test 2: FAIL scenario
        logger.info("\n" + "=" * 80)
        logger.info("Running Test Scenario 2: FAIL")
        logger.info("=" * 80)
        results['test_2_fail'] = await test_scenario_2_fail()
        await asyncio.sleep(1)

        # Test 3: BYPASS scenario
        logger.info("\n" + "=" * 80)
        logger.info("Running Test Scenario 3: BYPASS")
        logger.info("=" * 80)
        results['test_3_bypass'] = await test_scenario_3_bypass()

    except Exception as e:
        logger.error(f"\n❌ Test suite failed with exception: {e}", exc_info=True)
        return 2

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 SMOKE TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info("\n" + "-" * 80)
    logger.info(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    logger.info("=" * 80)

    if passed == total:
        logger.info("\n🎉 ALL SMOKE TESTS PASSED!")
        logger.info("   ✅ DAG executor integration working")
        logger.info("   ✅ PolicyLoader integration working")
        logger.info("   ✅ Contract validation working")
        logger.info("   ✅ Phase 0 integration VALIDATED")
        logger.info("\n   Ready to proceed to Phase 2: Comprehensive test suite")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        logger.error(f"   Failed: {total - passed}/{total}")
        logger.error("   Phase 0 integration has issues that need fixing")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
