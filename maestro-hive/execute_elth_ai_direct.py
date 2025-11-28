#!/usr/bin/env python3
"""
Execute Elth.ai Health Platform - Direct DAG Execution

Bypasses the API server and executes directly using DAGExecutor.
This demonstrates true DAG-based orchestration with ContractManager integration.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
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


async def create_elth_ai_workflow() -> WorkflowDAG:
    """
    Create DAG workflow for Elth.ai platform.

    In production, this DAG structure would be AI-generated from the requirement.
    For demo purposes, we use a predefined parallel SDLC structure.
    """

    logger.info("📋 Creating Elth.ai DAG workflow...")

    # Create team execution engine
    engine = TeamExecutionEngineV2SplitMode(enable_contracts=True)
    await engine.initialize_contract_manager()

    # Create workflow
    workflow_id = f"elth_ai_platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    workflow = WorkflowDAG(
        workflow_id=workflow_id,
        name="Elth.ai Health Platform"
    )

    # Phase 1: Requirements (can all run in parallel)
    workflow.add_node(
        node_id="requirements",
        node_type=NodeType.PHASE,
        function=lambda ctx: engine.execute_phase(
            phase_name="requirements",
            requirement=ELTH_AI_REQUIREMENT,
            context=ctx
        ),
        name="Requirements Analysis",
        description="Analyze requirements, security, and AI/ML needs"
    )

    # Phase 2: Architecture & Design (depends on requirements)
    workflow.add_node(
        node_id="architecture",
        node_type=NodeType.PHASE,
        function=lambda ctx: engine.execute_phase(
            phase_name="architecture",
            requirement="Design scalable, HIPAA-compliant system architecture for health platform",
            context=ctx
        ),
        name="System Architecture",
        description="Design overall system architecture"
    )

    # Phase 3: Implementation (depends on architecture)
    workflow.add_node(
        node_id="implementation",
        node_type=NodeType.PHASE,
        function=lambda ctx: engine.execute_phase(
            phase_name="implementation",
            requirement="Implement backend API, database, security, AI models, and frontend",
            context=ctx
        ),
        name="Implementation",
        description="Build the platform"
    )

    # Phase 4: Testing (depends on implementation)
    workflow.add_node(
        node_id="testing",
        node_type=NodeType.PHASE,
        function=lambda ctx: engine.execute_phase(
            phase_name="testing",
            requirement="Test API, security, AI models, and end-to-end workflows",
            context=ctx
        ),
        name="Testing",
        description="Comprehensive testing"
    )

    # Phase 5: Deployment (depends on testing)
    workflow.add_node(
        node_id="deployment",
        node_type=NodeType.PHASE,
        function=lambda ctx: engine.execute_phase(
            phase_name="deployment",
            requirement="Create documentation and setup deployment infrastructure",
            context=ctx
        ),
        name="Deployment",
        description="Documentation and deployment"
    )

    # Define dependencies (sequential for now, but DAG supports parallel execution)
    workflow.add_edge("requirements", "architecture")
    workflow.add_edge("architecture", "implementation")
    workflow.add_edge("implementation", "testing")
    workflow.add_edge("testing", "deployment")

    logger.info(f"✅ Created workflow: {workflow_id}")
    logger.info(f"   Nodes: {len(workflow.nodes)}")
    logger.info(f"   Edges: {len(list(workflow.graph.edges()))}")

    return workflow, engine


async def execute_elth_ai_workflow():
    """Execute the Elth.ai DAG workflow"""

    logger.info("="*80)
    logger.info("🏥 ELTH.AI HEALTH PLATFORM - Direct DAG Execution")
    logger.info("="*80)
    logger.info("")
    logger.info("Platform: Intelligent Health Management System")
    logger.info("Execution: True DAG orchestration with ContractManager")
    logger.info("Features: HIPAA compliance, AI insights, family health")
    logger.info("")

    try:
        # Create workflow
        workflow, engine = await create_elth_ai_workflow()

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

        logger.info("🚀 Starting workflow execution...")
        logger.info("")

        # Execute workflow
        result_context = await executor.execute(initial_context=initial_context)

        logger.info("")
        logger.info("="*80)
        logger.info("✅ Workflow execution completed!")
        logger.info("="*80)
        logger.info(f"Workflow ID: {workflow.workflow_id}")
        logger.info(f"Total nodes: {len(workflow.nodes)}")
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
