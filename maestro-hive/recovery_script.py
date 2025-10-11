#!/usr/bin/env python3
"""
DAG Workflow Recovery Script

Resumes interrupted or paused workflow executions from saved context.

Usage:
    python3 recovery_script.py <execution_id>
    python3 recovery_script.py <execution_id> --dry-run
    python3 recovery_script.py --list
    python3 recovery_script.py <execution_id> --workflow-type=parallel

Examples:
    # List all stored executions
    python3 recovery_script.py --list

    # Resume a workflow (dry-run first)
    python3 recovery_script.py abc123-def456-ghi789 --dry-run

    # Resume a workflow (actual execution)
    python3 recovery_script.py abc123-def456-ghi789

    # Resume with specific workflow type
    python3 recovery_script.py abc123-def456-ghi789 --workflow-type=parallel
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_executor import DAGExecutor, WorkflowContextStore
from dag_workflow import WorkflowDAG, WorkflowContext
from dag_compatibility import generate_parallel_workflow, generate_linear_workflow
from team_execution_dual import FeatureFlags

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowRecoveryError(Exception):
    """Exception raised during workflow recovery"""
    pass


def recreate_workflow(
    workflow_id: str,
    workflow_type: str = "linear",
    team_engine: Optional[object] = None
) -> WorkflowDAG:
    """
    Recreate the workflow DAG from workflow_id and type.

    This function reconstructs the workflow structure based on the
    workflow_id pattern and type.

    Args:
        workflow_id: Workflow ID from context
        workflow_type: Type of workflow ('linear' or 'parallel')
        team_engine: TeamExecutionEngineV2SplitMode instance (optional)

    Returns:
        WorkflowDAG instance

    Raises:
        WorkflowRecoveryError: If workflow cannot be recreated
    """
    logger.info(f"Recreating workflow: {workflow_id} (type: {workflow_type})")

    # Try to infer workflow type from ID if not specified
    if workflow_type == "auto":
        if "parallel" in workflow_id.lower():
            workflow_type = "parallel"
        else:
            workflow_type = "linear"
        logger.info(f"Auto-detected workflow type: {workflow_type}")

    # Create mock team engine if not provided
    # In production, you would inject the actual engine
    if team_engine is None:
        logger.warning("No team engine provided, using mock executor")

        class MockTeamEngine:
            async def _execute_single_phase(self, phase_name, context, requirement):
                """Mock phase execution"""
                logger.info(f"[MOCK] Executing phase: {phase_name}")
                await asyncio.sleep(0.1)
                return {
                    "phase": phase_name,
                    "status": "completed",
                    "artifacts": [],
                }

        team_engine = MockTeamEngine()

    # Generate workflow based on type
    try:
        if workflow_type == "parallel":
            workflow = generate_parallel_workflow(
                workflow_name=workflow_id,
                team_engine=team_engine
            )
            logger.info(f"✓ Created parallel workflow with {len(workflow.nodes)} nodes")
        else:
            workflow = generate_linear_workflow(
                workflow_name=workflow_id,
                team_engine=team_engine
            )
            logger.info(f"✓ Created linear workflow with {len(workflow.nodes)} nodes")

        return workflow

    except Exception as e:
        raise WorkflowRecoveryError(f"Failed to recreate workflow: {e}")


async def resume_workflow(
    execution_id: str,
    workflow_type: str = "auto",
    dry_run: bool = False,
    context_store: Optional[WorkflowContextStore] = None
) -> Optional[WorkflowContext]:
    """
    Resume a paused or interrupted workflow.

    Args:
        execution_id: Execution ID to resume
        workflow_type: Type of workflow ('linear', 'parallel', or 'auto')
        dry_run: If True, only validate without executing
        context_store: Context store instance (creates new if None)

    Returns:
        WorkflowContext if successful, None otherwise

    Raises:
        WorkflowRecoveryError: If recovery fails
    """
    logger.info("="*80)
    logger.info("WORKFLOW RECOVERY")
    logger.info("="*80)
    logger.info(f"Execution ID: {execution_id}")
    logger.info(f"Workflow Type: {workflow_type}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("="*80)

    # Initialize context store
    if context_store is None:
        context_store = WorkflowContextStore()
        logger.info("✓ Initialized context store")

    # Step 1: Load saved context
    logger.info("\n[1/5] Loading saved context...")
    context = await context_store.load_context(execution_id)

    if not context:
        raise WorkflowRecoveryError(f"Context not found for execution {execution_id}")

    logger.info(f"✓ Found context for workflow {context.workflow_id}")
    logger.info(f"   Execution ID: {context.execution_id}")
    logger.info(f"   Total nodes: {len(context.node_states)}")

    completed_nodes = context.get_completed_nodes()
    logger.info(f"   Completed nodes: {len(completed_nodes)}")
    logger.info(f"   Nodes: {', '.join(completed_nodes)}")

    # Step 2: Analyze state
    logger.info("\n[2/5] Analyzing workflow state...")

    pending_nodes = []
    failed_nodes = []
    running_nodes = []

    for node_id, state in context.node_states.items():
        if state.status.value == "completed":
            continue
        elif state.status.value == "failed":
            failed_nodes.append(node_id)
        elif state.status.value == "running":
            running_nodes.append(node_id)
        else:
            pending_nodes.append(node_id)

    logger.info(f"   Pending nodes: {len(pending_nodes)}")
    if pending_nodes:
        logger.info(f"      {', '.join(pending_nodes)}")

    logger.info(f"   Failed nodes: {len(failed_nodes)}")
    if failed_nodes:
        logger.warning(f"      {', '.join(failed_nodes)}")

    logger.info(f"   Running nodes (interrupted): {len(running_nodes)}")
    if running_nodes:
        logger.warning(f"      {', '.join(running_nodes)}")

    # Step 3: Recreate workflow DAG
    logger.info("\n[3/5] Recreating workflow DAG...")

    try:
        workflow = recreate_workflow(
            workflow_id=context.workflow_id,
            workflow_type=workflow_type
        )
        logger.info(f"✓ Workflow recreated successfully")
        logger.info(f"   Workflow ID: {workflow.workflow_id}")
        logger.info(f"   Total nodes: {len(workflow.nodes)}")
    except Exception as e:
        raise WorkflowRecoveryError(f"Failed to recreate workflow: {e}")

    # Step 4: Validate workflow structure matches context
    logger.info("\n[4/5] Validating workflow structure...")

    context_node_ids = set(context.node_states.keys())
    workflow_node_ids = set(workflow.nodes.keys())

    if context_node_ids != workflow_node_ids:
        logger.error("   ✗ Workflow structure mismatch!")
        logger.error(f"      Context has: {context_node_ids}")
        logger.error(f"      Workflow has: {workflow_node_ids}")
        logger.error(f"      Missing in workflow: {context_node_ids - workflow_node_ids}")
        logger.error(f"      Extra in workflow: {workflow_node_ids - context_node_ids}")
        raise WorkflowRecoveryError("Workflow structure does not match saved context")

    logger.info("✓ Workflow structure matches saved context")

    # Dry run stops here
    if dry_run:
        logger.info("\n" + "="*80)
        logger.info("DRY RUN - Recovery validation successful")
        logger.info("="*80)
        logger.info("Recovery would resume execution with:")
        logger.info(f"  • {len(completed_nodes)} nodes already completed")
        logger.info(f"  • {len(pending_nodes)} nodes to execute")
        if failed_nodes:
            logger.warning(f"  • {len(failed_nodes)} failed nodes would retry")
        logger.info("\nTo proceed with actual recovery, run without --dry-run")
        logger.info("="*80)
        return context

    # Step 5: Resume execution
    logger.info("\n[5/5] Resuming workflow execution...")

    executor = DAGExecutor(workflow, context_store=context_store)

    try:
        logger.info("▶  Starting execution...")
        start_time = datetime.now()

        resumed_context = await executor.execute(resume_execution_id=execution_id)

        duration = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "="*80)
        logger.info("✓ WORKFLOW RECOVERY SUCCESSFUL")
        logger.info("="*80)
        logger.info(f"Execution ID: {resumed_context.execution_id}")
        logger.info(f"Workflow ID: {resumed_context.workflow_id}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Completed nodes: {len(resumed_context.get_completed_nodes())}/{len(workflow.nodes)}")
        logger.info("="*80)

        return resumed_context

    except Exception as e:
        logger.error("\n" + "="*80)
        logger.error("✗ WORKFLOW RECOVERY FAILED")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        logger.error("="*80)
        raise WorkflowRecoveryError(f"Execution failed: {e}")


async def list_executions(context_store: Optional[WorkflowContextStore] = None):
    """
    List all stored workflow executions.

    Args:
        context_store: Context store instance (creates new if None)
    """
    if context_store is None:
        context_store = WorkflowContextStore()

    executions = await context_store.list_executions()

    if not executions:
        print("\nNo stored workflow executions found.")
        return

    print("\n" + "="*80)
    print("STORED WORKFLOW EXECUTIONS")
    print("="*80)
    print(f"Total: {len(executions)}\n")

    for i, execution_id in enumerate(executions, 1):
        context = await context_store.load_context(execution_id)
        if context:
            completed = len(context.get_completed_nodes())
            total = len(context.node_states)
            status = "✓ Complete" if completed == total else f"⏸ Paused ({completed}/{total})"

            print(f"{i}. {execution_id}")
            print(f"   Workflow: {context.workflow_id}")
            print(f"   Status: {status}")
            print(f"   Nodes: {completed}/{total} completed")
            print()

    print("="*80)
    print(f"\nTo resume an execution:")
    print(f"  python3 recovery_script.py <execution_id>")
    print("="*80 + "\n")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Resume interrupted or paused DAG workflows',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all stored executions
  python3 recovery_script.py --list

  # Dry run (validate only)
  python3 recovery_script.py abc123-def456 --dry-run

  # Resume execution
  python3 recovery_script.py abc123-def456

  # Resume with specific workflow type
  python3 recovery_script.py abc123-def456 --workflow-type=parallel
        """
    )

    parser.add_argument(
        'execution_id',
        nargs='?',
        help='Execution ID to resume'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all stored executions'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate recovery without executing'
    )
    parser.add_argument(
        '--workflow-type',
        choices=['auto', 'linear', 'parallel'],
        default='auto',
        help='Type of workflow to recreate (default: auto)'
    )

    args = parser.parse_args()

    try:
        if args.list:
            await list_executions()
        elif args.execution_id:
            await resume_workflow(
                execution_id=args.execution_id,
                workflow_type=args.workflow_type,
                dry_run=args.dry_run
            )
        else:
            parser.print_help()
            sys.exit(1)

    except WorkflowRecoveryError as e:
        logger.error(f"\n❌ Recovery Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n\n⚠  Recovery interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
