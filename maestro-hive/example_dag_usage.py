"""
DAG Workflow System - Complete Examples

This file demonstrates various ways to use the DAG workflow system.

Run with:
    python example_dag_usage.py
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import DAG components
from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    NodeType,
    ExecutionMode,
    RetryPolicy,
)
from dag_executor import (
    DAGExecutor,
    WorkflowContextStore,
    ExecutionEvent,
    ExecutionEventType,
)
from dag_compatibility import (
    generate_linear_workflow,
    generate_parallel_workflow,
)


# =============================================================================
# Example 1: Simple Linear Workflow
# =============================================================================

async def example_1_simple_linear():
    """
    Example 1: Create and execute a simple linear workflow.

    Workflow: Step1 -> Step2 -> Step3
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Linear Workflow")
    print("="*80)

    # Create workflow
    workflow = WorkflowDAG(name="simple_linear")

    # Define node executors
    async def step1(input_data):
        logger.info("Executing Step 1")
        await asyncio.sleep(0.5)  # Simulate work
        return {"result": "Step 1 complete", "data": [1, 2, 3]}

    async def step2(input_data):
        logger.info("Executing Step 2")
        prev_data = input_data['dependency_outputs']['step1']['data']
        await asyncio.sleep(0.5)
        return {"result": "Step 2 complete", "data": [x * 2 for x in prev_data]}

    async def step3(input_data):
        logger.info("Executing Step 3")
        prev_data = input_data['dependency_outputs']['step2']['data']
        await asyncio.sleep(0.5)
        total = sum(prev_data)
        return {"result": "Step 3 complete", "total": total}

    # Create nodes
    node1 = WorkflowNode(
        node_id="step1",
        name="Step 1: Initialize",
        node_type=NodeType.PHASE,
        executor=step1,
    )

    node2 = WorkflowNode(
        node_id="step2",
        name="Step 2: Process",
        node_type=NodeType.PHASE,
        executor=step2,
        dependencies=["step1"],
    )

    node3 = WorkflowNode(
        node_id="step3",
        name="Step 3: Finalize",
        node_type=NodeType.PHASE,
        executor=step3,
        dependencies=["step2"],
    )

    # Add to workflow
    workflow.add_node(node1)
    workflow.add_node(node2)
    workflow.add_node(node3)
    workflow.add_edge("step1", "step2")
    workflow.add_edge("step2", "step3")

    # Execute
    executor = DAGExecutor(workflow)
    context = await executor.execute()

    # Display results
    print("\n✓ Workflow completed!")
    print(f"Execution ID: {context.execution_id}")
    print(f"Completed nodes: {len(context.get_completed_nodes())}/{len(workflow.nodes)}")
    print("\nNode outputs:")
    for node_id, output in context.node_outputs.items():
        print(f"  {node_id}: {output}")


# =============================================================================
# Example 2: Parallel Workflow
# =============================================================================

async def example_2_parallel():
    """
    Example 2: Workflow with parallel execution.

    Workflow:
        start
          |
        split
         / \
      task1 task2 (parallel)
         \ /
        merge
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Parallel Workflow")
    print("="*80)

    workflow = WorkflowDAG(name="parallel_example")

    # Define executors
    async def start_task(input_data):
        logger.info("Starting workflow")
        return {"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}

    async def task1(input_data):
        logger.info("Task 1 started")
        data = input_data['dependency_outputs']['start']['data']
        await asyncio.sleep(1.0)  # Simulate work
        result = sum(data[:5])  # Process first half
        logger.info(f"Task 1 completed: {result}")
        return {"result": result}

    async def task2(input_data):
        logger.info("Task 2 started")
        data = input_data['dependency_outputs']['start']['data']
        await asyncio.sleep(1.0)  # Simulate work
        result = sum(data[5:])  # Process second half
        logger.info(f"Task 2 completed: {result}")
        return {"result": result}

    async def merge_task(input_data):
        logger.info("Merging results")
        result1 = input_data['dependency_outputs']['task1']['result']
        result2 = input_data['dependency_outputs']['task2']['result']
        total = result1 + result2
        return {"total": total, "message": f"Combined result: {total}"}

    # Create nodes
    nodes = [
        WorkflowNode("start", "Start", NodeType.PHASE, executor=start_task),
        WorkflowNode("task1", "Task 1", NodeType.PHASE, executor=task1, dependencies=["start"]),
        WorkflowNode("task2", "Task 2", NodeType.PHASE, executor=task2, dependencies=["start"]),
        WorkflowNode("merge", "Merge", NodeType.PHASE, executor=merge_task, dependencies=["task1", "task2"]),
    ]

    for node in nodes:
        workflow.add_node(node)

    workflow.add_edge("start", "task1")
    workflow.add_edge("start", "task2")
    workflow.add_edge("task1", "merge")
    workflow.add_edge("task2", "merge")

    # Execute with timing
    start_time = datetime.now()
    executor = DAGExecutor(workflow)
    context = await executor.execute()
    execution_time = (datetime.now() - start_time).total_seconds()

    # Display results
    print("\n✓ Workflow completed!")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Final result: {context.get_node_output('merge')}")
    print("\nNote: task1 and task2 ran in parallel (both took 1s, total ~1s not 2s)")


# =============================================================================
# Example 3: Conditional Execution
# =============================================================================

async def example_3_conditional():
    """
    Example 3: Workflow with conditional nodes.

    Some nodes execute only if conditions are met.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Conditional Execution")
    print("="*80)

    workflow = WorkflowDAG(name="conditional_example")

    # Define executors
    async def check_config(input_data):
        logger.info("Checking configuration")
        return {
            "enable_logging": True,
            "enable_caching": False,
            "enable_monitoring": True,
        }

    async def setup_logging(input_data):
        logger.info("✓ Setting up logging")
        return {"logging_configured": True}

    async def setup_caching(input_data):
        logger.info("✓ Setting up caching")
        return {"caching_configured": True}

    async def setup_monitoring(input_data):
        logger.info("✓ Setting up monitoring")
        return {"monitoring_configured": True}

    async def finalize(input_data):
        logger.info("Finalizing setup")
        outputs = input_data['all_outputs']
        enabled = []
        if 'logging' in outputs:
            enabled.append("logging")
        if 'caching' in outputs:
            enabled.append("caching")
        if 'monitoring' in outputs:
            enabled.append("monitoring")
        return {"enabled_features": enabled}

    # Create nodes with conditions
    nodes = [
        WorkflowNode("config", "Check Config", NodeType.PHASE, executor=check_config),
        WorkflowNode(
            "logging", "Setup Logging", NodeType.CONDITIONAL,
            executor=setup_logging,
            dependencies=["config"],
            condition="outputs['config']['enable_logging']"
        ),
        WorkflowNode(
            "caching", "Setup Caching", NodeType.CONDITIONAL,
            executor=setup_caching,
            dependencies=["config"],
            condition="outputs['config']['enable_caching']"
        ),
        WorkflowNode(
            "monitoring", "Setup Monitoring", NodeType.CONDITIONAL,
            executor=setup_monitoring,
            dependencies=["config"],
            condition="outputs['config']['enable_monitoring']"
        ),
        WorkflowNode(
            "finalize", "Finalize", NodeType.PHASE,
            executor=finalize,
            dependencies=["logging", "caching", "monitoring"]
        ),
    ]

    for node in nodes:
        workflow.add_node(node)

    workflow.add_edge("config", "logging")
    workflow.add_edge("config", "caching")
    workflow.add_edge("config", "monitoring")
    workflow.add_edge("logging", "finalize")
    workflow.add_edge("caching", "finalize")
    workflow.add_edge("monitoring", "finalize")

    # Execute
    executor = DAGExecutor(workflow)
    context = await executor.execute()

    # Display results
    print("\n✓ Workflow completed!")
    print("\nNode states:")
    for node_id, state in context.node_states.items():
        status_icon = "✓" if state.status.value == "completed" else "⊘"
        print(f"  {status_icon} {node_id}: {state.status.value}")
    print(f"\nEnabled features: {context.get_node_output('finalize')['enabled_features']}")


# =============================================================================
# Example 4: Retry Logic
# =============================================================================

async def example_4_retry():
    """
    Example 4: Node with retry logic on failure.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Retry Logic")
    print("="*80)

    workflow = WorkflowDAG(name="retry_example")

    attempt_count = 0

    async def flaky_task(input_data):
        nonlocal attempt_count
        attempt_count += 1
        logger.info(f"Attempt {attempt_count}")

        if attempt_count < 3:
            raise Exception(f"Temporary failure (attempt {attempt_count})")

        logger.info("Success!")
        return {"attempts": attempt_count, "status": "success"}

    # Create node with retry policy
    node = WorkflowNode(
        node_id="flaky",
        name="Flaky Task",
        node_type=NodeType.PHASE,
        executor=flaky_task,
        retry_policy=RetryPolicy(
            max_attempts=5,
            retry_on_failure=True,
            retry_delay_seconds=0.5,
            exponential_backoff=False,
        ),
    )

    workflow.add_node(node)

    # Execute
    executor = DAGExecutor(workflow)
    context = await executor.execute()

    # Display results
    print("\n✓ Workflow completed!")
    state = context.get_node_state("flaky")
    output = context.get_node_output("flaky")
    print(f"Node succeeded after {state.attempt_count} attempts")
    print(f"Output: {output}")


# =============================================================================
# Example 5: Event Tracking
# =============================================================================

async def example_5_events():
    """
    Example 5: Track workflow execution with events.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Event Tracking")
    print("="*80)

    workflow = WorkflowDAG(name="events_example")

    # Define simple workflow
    async def task1(input_data):
        await asyncio.sleep(0.3)
        return {"result": "task1"}

    async def task2(input_data):
        await asyncio.sleep(0.3)
        return {"result": "task2"}

    workflow.add_node(WorkflowNode("task1", "Task 1", NodeType.PHASE, executor=task1))
    workflow.add_node(WorkflowNode("task2", "Task 2", NodeType.PHASE, executor=task2, dependencies=["task1"]))
    workflow.add_edge("task1", "task2")

    # Define event handler
    events = []

    async def handle_event(event: ExecutionEvent):
        events.append(event)

        icon = {
            'workflow_started': '🚀',
            'node_started': '▶',
            'node_completed': '✓',
            'node_failed': '✗',
            'workflow_completed': '🎉',
        }.get(event.event_type.value, '•')

        if event.node_id:
            print(f"{icon} {event.event_type.value}: {event.node_id}")
        else:
            print(f"{icon} {event.event_type.value}")

    # Execute with event handler
    executor = DAGExecutor(workflow, event_handler=handle_event)
    context = await executor.execute()

    # Display event summary
    print(f"\n✓ Workflow completed!")
    print(f"Total events: {len(events)}")
    print("\nEvent types:")
    event_types = {}
    for event in events:
        event_type = event.event_type.value
        event_types[event_type] = event_types.get(event_type, 0) + 1
    for event_type, count in event_types.items():
        print(f"  {event_type}: {count}")


# =============================================================================
# Example 6: State Persistence (Pause/Resume)
# =============================================================================

async def example_6_persistence():
    """
    Example 6: Persist workflow state and resume.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: State Persistence")
    print("="*80)

    # Create context store
    context_store = WorkflowContextStore()

    # Create workflow
    workflow = WorkflowDAG(name="persistence_example")

    async def task1(input_data):
        logger.info("Task 1 executing")
        await asyncio.sleep(0.3)
        return {"result": "task1 complete"}

    async def task2(input_data):
        logger.info("Task 2 executing")
        await asyncio.sleep(0.3)
        return {"result": "task2 complete"}

    async def task3(input_data):
        logger.info("Task 3 executing")
        await asyncio.sleep(0.3)
        return {"result": "task3 complete"}

    workflow.add_node(WorkflowNode("task1", "Task 1", NodeType.PHASE, executor=task1))
    workflow.add_node(WorkflowNode("task2", "Task 2", NodeType.PHASE, executor=task2, dependencies=["task1"]))
    workflow.add_node(WorkflowNode("task3", "Task 3", NodeType.PHASE, executor=task3, dependencies=["task2"]))
    workflow.add_edge("task1", "task2")
    workflow.add_edge("task2", "task3")

    # Execute and save state
    print("\n▶ Starting execution...")
    executor = DAGExecutor(workflow, context_store=context_store)
    context = await executor.execute()

    execution_id = context.execution_id
    print(f"\n✓ Execution completed")
    print(f"Execution ID: {execution_id}")
    print(f"Completed nodes: {len(context.get_completed_nodes())}")

    # Simulate loading state later
    print("\n▶ Loading saved state...")
    loaded_context = await context_store.load_context(execution_id)
    print(f"✓ Loaded context for execution {loaded_context.execution_id}")
    print(f"Restored {len(loaded_context.node_states)} node states")
    print(f"Restored {len(loaded_context.node_outputs)} node outputs")


# =============================================================================
# Example 7: SDLC Workflow (Compatibility Layer)
# =============================================================================

async def example_7_sdlc():
    """
    Example 7: Generate SDLC workflow using compatibility layer.

    This demonstrates how existing SDLC phases work with DAG system.
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: SDLC Workflow")
    print("="*80)

    # Mock team engine (in real usage, use actual TeamExecutionEngineV2SplitMode)
    class MockTeamEngine:
        async def _execute_single_phase(self, phase_name, context, requirement):
            logger.info(f"Executing phase: {phase_name}")
            await asyncio.sleep(0.2)
            return {
                "phase": phase_name,
                "status": "completed",
                "artifacts": [f"/output/{phase_name}/file.txt"],
            }

    mock_engine = MockTeamEngine()

    # Generate linear SDLC workflow
    print("\n▶ Generating linear SDLC workflow...")
    workflow = generate_linear_workflow(
        phases=["requirement_analysis", "design", "development"],
        team_engine=mock_engine
    )

    print(f"✓ Generated workflow with {len(workflow.nodes)} phases")
    print(f"Execution order: {' -> '.join([p[0].split('_')[1] for p in workflow.get_execution_order()])}")

    # Execute
    print("\n▶ Executing workflow...")
    executor = DAGExecutor(workflow)
    context = await executor.execute(
        initial_context={"requirement": "Build a todo app"}
    )

    print("\n✓ SDLC workflow completed!")
    print(f"Phases completed: {len(context.get_completed_nodes())}")
    print("\nPhase outputs:")
    for node_id, output in context.node_outputs.items():
        phase_name = node_id.replace("phase_", "")
        print(f"  • {phase_name}: {output.get('status', 'unknown')}")


# =============================================================================
# Example 8: Parallel SDLC Workflow
# =============================================================================

async def example_8_parallel_sdlc():
    """
    Example 8: Parallel SDLC workflow (backend + frontend in parallel).
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Parallel SDLC Workflow")
    print("="*80)

    class MockTeamEngine:
        async def _execute_single_phase(self, phase_name, context, requirement):
            logger.info(f"Executing phase: {phase_name}")
            # Simulate longer execution for dev phases
            if "development" in phase_name:
                await asyncio.sleep(1.0)
            else:
                await asyncio.sleep(0.2)
            return {"phase": phase_name, "status": "completed"}

    mock_engine = MockTeamEngine()

    # Generate parallel workflow
    print("\n▶ Generating parallel SDLC workflow...")
    workflow = generate_parallel_workflow(team_engine=mock_engine)

    print(f"✓ Generated workflow with {len(workflow.nodes)} phases")
    print("\nExecution plan:")
    for i, group in enumerate(workflow.get_execution_order(), 1):
        phases = [node_id.replace("phase_", "") for node_id in group]
        if len(phases) > 1:
            print(f"  Group {i}: {' + '.join(phases)} (PARALLEL)")
        else:
            print(f"  Group {i}: {phases[0]}")

    # Execute with timing
    print("\n▶ Executing workflow...")
    start_time = datetime.now()
    executor = DAGExecutor(workflow)
    context = await executor.execute(
        initial_context={"requirement": "Build a todo app"}
    )
    execution_time = (datetime.now() - start_time).total_seconds()

    print("\n✓ Parallel SDLC workflow completed!")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Phases completed: {len(context.get_completed_nodes())}")
    print("\nNote: Backend and Frontend ran in parallel, saving ~1 second")


# =============================================================================
# Main
# =============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("DAG WORKFLOW SYSTEM - EXAMPLES")
    print("="*80)

    examples = [
        ("Simple Linear Workflow", example_1_simple_linear),
        ("Parallel Workflow", example_2_parallel),
        ("Conditional Execution", example_3_conditional),
        ("Retry Logic", example_4_retry),
        ("Event Tracking", example_5_events),
        ("State Persistence", example_6_persistence),
        ("SDLC Workflow", example_7_sdlc),
        ("Parallel SDLC", example_8_parallel_sdlc),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        try:
            await example_func()
        except Exception as e:
            print(f"\n✗ Example {i} failed: {e}")
            import traceback
            traceback.print_exc()

        # Pause between examples
        if i < len(examples):
            await asyncio.sleep(0.5)

    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
