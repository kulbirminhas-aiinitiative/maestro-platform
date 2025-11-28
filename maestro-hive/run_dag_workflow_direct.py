#!/usr/bin/env python3
"""
Direct DAG Workflow Execution - Bypasses Server
Runs workflow directly with real AI personas
NO MOCKS - Real execution only
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_executor import DAGExecutor
from dag_workflow import WorkflowDAG
from dag_compatibility import generate_parallel_workflow
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
from database import DatabaseWorkflowContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def run_workflow(requirement: str, project_name: str):
    """
    Run DAG workflow with REAL personas - NO MOCKS
    """
    logger.info("="*80)
    logger.info("🚀 REAL DAG Workflow Execution (NO MOCKS)")
    logger.info("="*80)
    logger.info(f"Project: {project_name}")
    logger.info(f"Requirement: {requirement[:100]}...")
    logger.info("")

    # Create real team engine
    logger.info("📦 Creating TeamExecutionEngineV2SplitMode (REAL PERSONAS)...")
    try:
        team_engine = TeamExecutionEngineV2SplitMode()
        logger.info("✅ Team engine created")
    except Exception as e:
        logger.error(f"❌ Failed to create team engine: {e}", exc_info=True)
        return None

    # Generate parallel workflow
    logger.info("🔨 Generating parallel workflow...")
    try:
        workflow = generate_parallel_workflow(
            workflow_name=f"{project_name}_parallel",
            team_engine=team_engine
        )
        logger.info(f"✅ Workflow created with {len(workflow.nodes)} nodes")
        logger.info(f"   Nodes: {list(workflow.nodes.keys())}")
    except Exception as e:
        logger.error(f"❌ Failed to generate workflow: {e}", exc_info=True)
        return None

    # Create context store
    context_store = DatabaseWorkflowContextStore()

    # Create execution ID
    execution_id = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"📝 Execution ID: {execution_id}")

    # Create executor
    logger.info("⚙️  Creating DAG executor...")
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store
    )

    # Execute workflow
    logger.info("")
    logger.info("="*80)
    logger.info("🎯 STARTING REAL EXECUTION")
    logger.info("="*80)
    logger.info("")

    start_time = datetime.now()

    try:
        # Execute with initial context
        initial_context = {
            'requirement': requirement,
            'project_name': project_name,
            'execution_id': execution_id
        }

        context = await executor.execute(initial_context=initial_context)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("")
        logger.info("="*80)
        logger.info("✅ WORKFLOW COMPLETED")
        logger.info("="*80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Execution ID: {execution_id}")
        logger.info("")

        # Check for artifacts
        logger.info("📂 Checking for generated artifacts...")
        artifact_dir = Path("/tmp/maestro_workflow") / project_name
        if artifact_dir.exists():
            logger.info(f"✅ Artifacts found in: {artifact_dir}")

            # List generated files
            files = list(artifact_dir.rglob("*.py")) + list(artifact_dir.rglob("*.tsx")) + list(artifact_dir.rglob("*.ts"))
            if files:
                logger.info(f"📄 Generated {len(files)} code files:")
                for f in files[:10]:  # Show first 10
                    logger.info(f"   - {f.relative_to(artifact_dir)}")
                if len(files) > 10:
                    logger.info(f"   ... and {len(files) - 10} more files")
            else:
                logger.warning("⚠️  No code files found in artifacts")
        else:
            logger.warning(f"⚠️  No artifact directory found: {artifact_dir}")

        logger.info("")
        logger.info("Context outputs:")
        for key, value in context.global_outputs.items():
            if isinstance(value, dict):
                logger.info(f"  {key}: {len(value)} items")
            else:
                logger.info(f"  {key}: {str(value)[:100]}")

        return context

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.error("")
        logger.error("="*80)
        logger.error("❌ WORKFLOW FAILED")
        logger.error("="*80)
        logger.error(f"Duration: {duration:.2f} seconds")
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("")

        return None


async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct DAG Workflow Execution with REAL personas (NO MOCKS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple project
  python3 run_dag_workflow_direct.py \\
      --requirement "Build a simple REST API for user management" \\
      --project-name "user_api"

  # TastyTalk pilot
  python3 run_dag_workflow_direct.py \\
      --requirement "TastyTalk: AI cooking platform in regional languages" \\
      --project-name "tastytalk"

  # Footprint360 pilot
  python3 run_dag_workflow_direct.py \\
      --requirement "Footprint360: Business intelligence for operational optimization" \\
      --project-name "footprint360"
        """
    )

    parser.add_argument("--requirement", required=True, help="Project requirement description")
    parser.add_argument("--project-name", required=True, help="Project name (used for artifact directories)")

    args = parser.parse_args()

    # Run workflow
    context = await run_workflow(
        requirement=args.requirement,
        project_name=args.project_name
    )

    # Exit code
    if context:
        logger.info("✅ Execution successful")
        sys.exit(0)
    else:
        logger.error("❌ Execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
