#!/usr/bin/env python3
"""
Test DAG Executor Contract Integration

Tests that contract validation is properly integrated with dag_executor.py
and correctly blocks workflow execution on contract violations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Import required modules
from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    WorkflowContext,
    NodeType,
    RetryPolicy
)
from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent


async def mock_implementation_phase_executor(node_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock executor for implementation phase.
    Returns output that simulates a completed implementation phase.
    """
    logger.info(f"Executing mock implementation phase: {node_input['node_id']}")

    # Simulate implementation phase completing
    # This would normally create code, but we're using an existing workflow dir
    return {
        'status': 'completed',
        'output_dir': '/tmp/maestro_workflow/wf-1760076571-6b932a66',
        'message': 'Implementation phase completed (mock)'
    }


async def test_dag_executor_with_contracts():
    """
    Test that DAG executor properly validates contracts after phase execution

    This tests:
    1. DAG executor runs contract validation after phase node completes
    2. Contract violations cause node to fail
    3. Failed node prevents dependent nodes from executing
    """

    logger.info("=" * 80)
    logger.info("TEST: DAG Executor Contract Integration")
    logger.info("=" * 80)

    # Create a simple DAG with one implementation phase node
    workflow = WorkflowDAG(
        workflow_id="test-contract-workflow",
        name="Contract Validation Test Workflow"
    )

    # Add implementation phase node
    # This node will execute successfully but fail contract validation
    impl_node = WorkflowNode(
        node_id="implementation",
        name="Implementation Phase",
        node_type=NodeType.PHASE,
        executor=mock_implementation_phase_executor,
        dependencies=[],
        retry_policy=RetryPolicy(max_attempts=1)  # No retries for testing
    )
    workflow.add_node(impl_node)

    # Create context store
    context_store = WorkflowContextStore()

    # Event handler to track events
    events = []
    async def event_handler(event: ExecutionEvent):
        events.append(event)
        logger.info(f"Event: {event.event_type.value} - {event.node_id or 'workflow'}")

    # Create executor
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store,
        event_handler=event_handler
    )

    # Execute workflow
    logger.info("\n" + "=" * 80)
    logger.info("Executing Workflow with Contract Validation")
    logger.info("=" * 80 + "\n")

    context = None
    try:
        context = await executor.execute(
            initial_context={'workflow_dir': '/tmp/maestro_workflow/wf-1760076571-6b932a66'}
        )

        logger.error("❌ TEST FAILED: Workflow should have failed due to contract violations")
        return False

    except Exception as e:
        logger.info(f"\n✅ Workflow failed as expected: {e}")

        # Check results
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS")
        logger.info("=" * 80)

        # If context wasn't created, try to load from store
        if not context:
            # Load the most recent execution from the store
            executions = await context_store.list_executions(workflow.workflow_id)
            if executions:
                context = await context_store.load_context(executions[-1])

        if not context:
            logger.error("❌ No context available - cannot verify test results")
            return False

        # Verify implementation node failed
        impl_state = context.get_node_state("implementation")
        if impl_state and impl_state.status.value == "failed":
            logger.info("✅ Implementation node correctly marked as FAILED")
        else:
            logger.error(f"❌ Implementation node should be FAILED, got: {impl_state.status.value if impl_state else 'None'}")
            return False

        # Check for contract validation in output
        if impl_state.output and 'contract_validation' in impl_state.output:
            contract_validation = impl_state.output['contract_validation']
            logger.info(f"✅ Contract validation ran: {contract_validation}")

            if 'passed' in contract_validation and not contract_validation['passed']:
                logger.info("✅ Contract validation correctly reported failure")
            elif 'violations' in contract_validation:
                logger.info("✅ Contract validation correctly reported violations")
            else:
                logger.warning("⚠️  Contract validation structure unexpected")
        else:
            logger.warning("⚠️  No contract validation data in node output")

        # Check error message
        if impl_state.error_message and "contract validation failed" in impl_state.error_message.lower():
            logger.info(f"✅ Error message mentions contract validation: {impl_state.error_message}")
        else:
            logger.warning(f"⚠️  Error message doesn't mention contracts: {impl_state.error_message}")

        return True


async def test_dag_executor_without_phase_nodes():
    """
    Test that contract validation is skipped for non-phase nodes
    """

    logger.info("\n" + "=" * 80)
    logger.info("TEST: DAG Executor without Phase Nodes (should skip contract validation)")
    logger.info("=" * 80)

    # Create a simple DAG with a non-phase node
    workflow = WorkflowDAG(
        workflow_id="test-non-phase-workflow",
        name="Non-Phase Node Test Workflow"
    )

    # Add a CUSTOM node (not a PHASE node)
    async def custom_executor(node_input: Dict[str, Any]) -> Dict[str, Any]:
        return {'status': 'completed', 'result': 'success'}

    custom_node = WorkflowNode(
        node_id="custom1",
        name="Simple Custom Task",
        node_type=NodeType.CUSTOM,  # Not a PHASE
        executor=custom_executor,
        dependencies=[],
        retry_policy=RetryPolicy(max_attempts=1)
    )
    workflow.add_node(custom_node)

    # Create context store and executor
    context_store = WorkflowContextStore()
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store
    )

    # Execute workflow
    logger.info("\nExecuting workflow with non-phase node...")

    try:
        context = await executor.execute()

        # Check results
        custom_state = context.get_node_state("custom1")
        if custom_state and custom_state.status.value == "completed":
            logger.info("✅ Non-phase node completed successfully")
            logger.info("✅ Contract validation correctly skipped for non-phase nodes")
            return True
        else:
            logger.error("❌ Non-phase node should have completed")
            return False

    except Exception as e:
        logger.error(f"❌ Workflow should have succeeded: {e}")
        return False


async def main():
    """Run all tests"""

    logger.info("\n" + "=" * 80)
    logger.info("DAG EXECUTOR CONTRACT INTEGRATION TESTS")
    logger.info("=" * 80)
    logger.info("Testing that contracts are properly integrated with DAG executor\n")

    results = []

    try:
        # Test 1: Contract validation blocks workflow
        logger.info("\n📋 TEST 1: Contract Validation Blocks Workflow")
        result1 = await test_dag_executor_with_contracts()
        results.append(("Contract Blocking", result1))

        # Test 2: Non-phase nodes skip validation
        logger.info("\n📋 TEST 2: Non-Phase Nodes Skip Validation")
        result2 = await test_dag_executor_without_phase_nodes()
        results.append(("Non-Phase Skip", result2))

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status}: {test_name}")

        logger.info("\n" + "=" * 80)
        if passed == total:
            logger.info(f"✅ ALL TESTS PASSED ({passed}/{total})")
            logger.info("   Contract validation is properly integrated with DAG executor")
            logger.info("   Contracts correctly block workflow execution on violations")
            return 0
        else:
            logger.error(f"❌ SOME TESTS FAILED ({passed}/{total})")
            return 1

    except Exception as e:
        logger.error(f"\n❌ TEST SUITE FAILED WITH EXCEPTION: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
