#!/usr/bin/env python3
"""
Execute Elth.ai Health Platform - Simplified Direct Execution

Uses the existing parallel SDLC workflow with ContractManager integration.
Demonstrates full DAG-based execution with real AI personas.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_compatibility import generate_parallel_workflow
from dag_executor import DAGExecutor
from database import DatabaseWorkflowContextStore
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

ELTH_AI_REQUIREMENT = """
Elth.ai is an intelligent health platform designed to simplify how individuals and
families manage their medical information and wellness journeys. It securely organizes
health records, connects insights across lab reports and prescriptions, and uses AI to
provide personalized health summaries and reminders. By bridging the gap between patients,
caregivers, and healthcare providers, Elth.ai empowers users to stay informed, proactive,
and in control of their health—anytime, anywhere.

Key Features:
- Secure health record storage and organization
- Lab report and prescription tracking
- AI-powered health insights and summaries
- Personalized health reminders
- Family health management
- Healthcare provider integration
- Mobile and web access
- HIPAA compliance
"""


async def execute_elth_ai_workflow():
    """Execute the Elth.ai DAG workflow"""

    logger.info("="*80)
    logger.info("🏥 ELTH.AI HEALTH PLATFORM - DAG Execution")
    logger.info("="*80)
    logger.info("")
    logger.info("Platform: Intelligent Health Management System")
    logger.info("Execution: DAG orchestration with ContractManager")
    logger.info("Features: HIPAA compliance, AI insights, family health")
    logger.info("")

    try:
        # Create team execution engine with ContractManager
        logger.info("🔧 Initializing team execution engine...")
        engine = TeamExecutionEngineV2SplitMode(enable_contracts=True)
        await engine.initialize_contract_manager()
        logger.info("✅ Team engine initialized with ContractManager")
        logger.info("")

        # Generate parallel workflow
        logger.info("📋 Generating parallel SDLC workflow...")
        workflow = generate_parallel_workflow(
            workflow_name="elth_ai_platform",
            team_engine=engine
        )
        logger.info(f"✅ Workflow generated: {len(workflow.nodes)} nodes")
        logger.info("")

        # Create executor
        context_store = DatabaseWorkflowContextStore()
        executor = DAGExecutor(
            workflow=workflow,
            context_store=context_store
        )

        # Prepare initial context
        initial_context = {
            'requirement': ELTH_AI_REQUIREMENT,
            'project_name': 'elth_ai_health_platform',
            'workflow_id': workflow.workflow_id
        }

        logger.info("🚀 Starting DAG execution...")
        logger.info(f"   Workflow: {workflow.name}")
        logger.info(f"   Phases: {', '.join([n.name for n in workflow.nodes.values()])}")
        logger.info("")

        # Execute workflow
        result_context = await executor.execute(initial_context=initial_context)

        logger.info("")
        logger.info("="*80)
        logger.info("✅ Workflow execution completed!")
        logger.info("="*80)
        logger.info(f"Workflow ID: {workflow.workflow_id}")
        logger.info(f"Total phases: {len(workflow.nodes)}")
        logger.info(f"Status: Completed")
        logger.info("")

        # Cleanup
        await engine.cleanup()

        return True

    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ Workflow execution failed: {e}")
        logger.error("="*80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(execute_elth_ai_workflow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Execution interrupted by user")
        sys.exit(130)
