#!/usr/bin/env python3
"""
Example: Running Validated DAG Workflows
Demonstrates how to use the integrated validation system
"""

import asyncio
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_1_validated_linear_workflow():
    """Example 1: Run a linear workflow with validation gates"""
    logger.info("="*80)
    logger.info("EXAMPLE 1: Validated Linear Workflow")
    logger.info("="*80)

    from dag_workflow_with_validation import generate_validated_linear_workflow
    from dag_executor import DAGExecutor
    from team_execution_engine_v2 import TeamExecutionEngineV2SplitMode

    # Create team engine
    engine = TeamExecutionEngineV2SplitMode()

    # Generate workflow with validation
    workflow = generate_validated_linear_workflow(
        workflow_name="example_linear",
        team_engine=engine,
        enable_validation=True,
        enable_handoff_validation=True,
        fail_on_validation_error=True  # Block on critical failures
    )

    logger.info(f"Generated workflow with {len(workflow.nodes)} nodes")
    logger.info(f"Execution order: {workflow.get_execution_order()}")

    # Create executor
    executor = DAGExecutor(workflow)

    # Define global context
    context = {
        'requirement': 'Build a simple todo app with React frontend and Node.js backend',
        'workflow_dir': '/tmp/example_linear_workflow',
        'output_dir': '/tmp/example_linear_workflow',
        'project_name': 'todo-app'
    }

    try:
        # Execute workflow
        logger.info("Starting workflow execution...")
        result = await executor.execute(global_context=context)

        logger.info("✓ Workflow completed successfully!")
        logger.info(f"Final status: {result.status}")
        logger.info(f"Completed nodes: {len(result.context.get_completed_nodes())}")

        # Check final validation
        final_validation = result.context.get_node_output("final_gap_detection")
        if final_validation:
            logger.info(f"Deployable: {final_validation.get('is_deployable', False)}")
            logger.info(f"Gaps detected: {final_validation.get('gaps_detected', 0)}")

    except Exception as e:
        logger.error(f"✗ Workflow execution failed: {e}")

        # Get failure details
        if hasattr(e, 'context'):
            failed_nodes = [
                node_id for node_id, state in e.context.node_states.items()
                if state.status.value == 'failed'
            ]
            logger.error(f"Failed nodes: {failed_nodes}")

            # Check for recovery context
            for node_id in failed_nodes:
                node_output = e.context.get_node_output(node_id)
                if node_output and 'recovery_context' in node_output:
                    logger.info("📋 Recovery context available")
                    recovery_file = Path(f"/tmp/{node_id}_recovery.json")
                    recovery_file.write_text(json.dumps(node_output['recovery_context'], indent=2))
                    logger.info(f"Saved to: {recovery_file}")


async def example_2_validated_parallel_workflow():
    """Example 2: Run a parallel workflow with validation gates"""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: Validated Parallel Workflow")
    logger.info("="*80)

    from dag_workflow_with_validation import generate_validated_parallel_workflow
    from dag_executor import DAGExecutor
    from team_execution_engine_v2 import TeamExecutionEngineV2SplitMode

    # Create team engine
    engine = TeamExecutionEngineV2SplitMode()

    # Generate parallel workflow with validation
    workflow = generate_validated_parallel_workflow(
        workflow_name="example_parallel",
        team_engine=engine,
        enable_validation=True,
        enable_handoff_validation=True,
        fail_on_validation_error=True
    )

    logger.info(f"Generated workflow with {len(workflow.nodes)} nodes")

    # Show execution groups (parallel nodes)
    execution_order = workflow.get_execution_order()
    logger.info("Execution groups:")
    for i, group in enumerate(execution_order):
        logger.info(f"  Group {i+1}: {group}")
        if len(group) > 1:
            logger.info(f"    ^ These {len(group)} nodes will run in parallel")

    # Create executor
    executor = DAGExecutor(workflow)

    # Define global context
    context = {
        'requirement': 'Build an e-commerce platform with product catalog and shopping cart',
        'workflow_dir': '/tmp/example_parallel_workflow',
        'output_dir': '/tmp/example_parallel_workflow',
        'project_name': 'ecommerce-platform'
    }

    try:
        logger.info("Starting parallel workflow execution...")
        result = await executor.execute(global_context=context)

        logger.info("✓ Workflow completed successfully!")

        # Check implementation completeness
        completeness_output = result.context.get_node_output("check_implementation_completeness")
        if completeness_output:
            logger.info(f"Overall completion: {completeness_output.get('overall_completion', 0)*100:.1f}%")
            logger.info(f"Backend complete: {completeness_output.get('backend_complete', False)}")
            logger.info(f"Frontend complete: {completeness_output.get('frontend_complete', False)}")

    except Exception as e:
        logger.error(f"✗ Workflow execution failed: {e}")


async def example_3_subphased_implementation():
    """Example 3: Run a workflow with granular implementation sub-phases"""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: Sub-Phased Implementation Workflow")
    logger.info("="*80)

    from dag_workflow_with_validation import generate_subphased_implementation_workflow
    from dag_executor import DAGExecutor
    from team_execution_engine_v2 import TeamExecutionEngineV2SplitMode

    # Create team engine
    engine = TeamExecutionEngineV2SplitMode()

    # Generate sub-phased workflow
    workflow = generate_subphased_implementation_workflow(
        workflow_name="example_subphased",
        team_engine=engine,
        enable_validation=True
    )

    logger.info(f"Generated workflow with {len(workflow.nodes)} nodes")
    logger.info("Implementation broken into 8 sub-phases:")
    logger.info("  1. backend_models")
    logger.info("  2. backend_core")
    logger.info("  3. backend_api")
    logger.info("  4. backend_middleware")
    logger.info("  5. frontend_structure")
    logger.info("  6. frontend_core")
    logger.info("  7. frontend_features")
    logger.info("  8. integration")

    # Create executor
    executor = DAGExecutor(workflow)

    # Define global context
    context = {
        'requirement': 'Build a project management tool with task tracking and team collaboration',
        'workflow_dir': '/tmp/example_subphased_workflow',
        'output_dir': '/tmp/example_subphased_workflow',
        'project_name': 'project-manager'
    }

    try:
        logger.info("Starting sub-phased workflow execution...")
        result = await executor.execute(global_context=context)

        logger.info("✓ Workflow completed successfully!")

        # Show sub-phase completion status
        logger.info("\nSub-phase completion status:")
        for subphase in ["backend_models", "backend_core", "backend_api", "backend_middleware",
                        "frontend_structure", "frontend_core", "frontend_features", "integration"]:
            node_id = f"subphase_{subphase}"
            state = result.context.get_node_state(node_id)
            if state:
                status_icon = "✓" if state.status.value == "completed" else "✗"
                logger.info(f"  {status_icon} {subphase}: {state.status.value}")

                # Show validation result if available
                validator_id = f"validate_{subphase}"
                validator_output = result.context.get_node_output(validator_id)
                if validator_output:
                    completion = validator_output.get('overall_completion', 0)
                    logger.info(f"      Completion: {completion*100:.1f}%")

    except Exception as e:
        logger.error(f"✗ Workflow execution failed: {e}")

        # Identify which sub-phase failed
        if hasattr(e, 'context'):
            for node_id, state in e.context.node_states.items():
                if state.status.value == 'failed' and 'subphase' in node_id:
                    logger.error(f"Failed at sub-phase: {node_id}")
                    logger.info(f"Blockers: {state.output.get('blockers', [])}")


async def example_4_custom_validation_configuration():
    """Example 4: Custom validation configuration"""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 4: Custom Validation Configuration")
    logger.info("="*80)

    from dag_workflow import WorkflowDAG, WorkflowNode, NodeType, ExecutionMode
    from dag_compatibility import PhaseNodeExecutor
    from dag_validation_nodes import create_validation_node, ValidationNodeType

    # Create custom workflow manually
    workflow = WorkflowDAG(name="custom_validated")

    # Add requirement analysis phase
    req_executor = PhaseNodeExecutor("requirement_analysis", None)
    req_node = WorkflowNode(
        node_id="phase_requirements",
        name="requirement_analysis",
        node_type=NodeType.PHASE,
        executor=req_executor.execute,
        dependencies=[],
        config={'phase': 'requirement_analysis'}
    )
    workflow.add_node(req_node)

    # Add CUSTOM validation with specific configuration
    req_validator = create_validation_node(
        node_id="validate_requirements",
        validation_type=ValidationNodeType.PHASE_VALIDATOR,
        phase_to_validate="requirement_analysis",
        dependencies=["phase_requirements"],
        fail_on_error=False,  # Only warn, don't block
        severity_threshold="high",  # Block on HIGH or CRITICAL, not just CRITICAL
        output_dir="/tmp/custom_workflow"
    )
    workflow.add_node(req_validator)
    workflow.add_edge("phase_requirements", "validate_requirements")

    # Add design phase
    design_executor = PhaseNodeExecutor("design", None)
    design_node = WorkflowNode(
        node_id="phase_design",
        name="design",
        node_type=NodeType.PHASE,
        executor=design_executor.execute,
        dependencies=["validate_requirements"],
        config={'phase': 'design'}
    )
    workflow.add_node(design_node)
    workflow.add_edge("validate_requirements", "phase_design")

    # Add gap detector that generates recovery context
    gap_detector = create_validation_node(
        node_id="detect_gaps",
        validation_type=ValidationNodeType.GAP_DETECTOR,
        dependencies=["phase_design"],
        fail_on_error=True,  # Block if critical gaps found
        generate_recovery_context=True,  # Generate recovery instructions
        output_dir="/tmp/custom_workflow"
    )
    workflow.add_node(gap_detector)
    workflow.add_edge("phase_design", "detect_gaps")

    logger.info(f"Created custom workflow with {len(workflow.nodes)} nodes")
    logger.info("Validation configuration:")
    logger.info("  - Requirements: Warn only, threshold=HIGH")
    logger.info("  - Gap Detection: Block on critical, generate recovery context")


async def example_5_workflow_recovery():
    """Example 5: Recovering from a failed workflow"""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 5: Workflow Recovery")
    logger.info("="*80)

    logger.info("Scenario: A workflow failed at backend validation")
    logger.info("Let's see how to recover...")

    # Simulate a failed workflow with recovery context
    recovery_context = {
        "workflow_id": "example_recovery",
        "resume_from_phase": "backend_development",
        "gaps_summary": {
            "total_gaps": 5,
            "critical_gaps": 3,
            "estimated_completion": 0.30
        },
        "recovery_instructions": [
            {
                "phase": "implementation",
                "subphase": "backend_api",
                "action": "create_routes",
                "components": ["authRoutes", "userRoutes", "productRoutes"],
                "priority": 1
            },
            {
                "phase": "implementation",
                "subphase": "backend_core",
                "action": "create_services",
                "details": "Create business logic services layer",
                "priority": 1
            },
            {
                "phase": "implementation",
                "subphase": "backend_api",
                "action": "create_controllers",
                "details": "Create request handler controllers",
                "priority": 1
            }
        ],
        "recommended_approach": "INCREMENTAL COMPLETION: 30-60% complete. Resume implementation phase focusing on missing backend services/routes."
    }

    logger.info("\n📋 Recovery Instructions:")
    for instruction in recovery_context['recovery_instructions']:
        logger.info(f"  Priority {instruction['priority']}: {instruction['action']}")
        if 'components' in instruction:
            logger.info(f"    Components: {', '.join(instruction['components'])}")
        if 'details' in instruction:
            logger.info(f"    Details: {instruction['details']}")

    logger.info(f"\n💡 Recommended Approach:")
    logger.info(f"  {recovery_context['recommended_approach']}")

    logger.info("\nTo resume the workflow after fixing:")
    logger.info("  1. Fix the issues identified in recovery instructions")
    logger.info("  2. Load the workflow and context:")
    logger.info("     workflow = load_workflow('example_recovery')")
    logger.info("     executor = DAGExecutor(workflow)")
    logger.info("  3. Resume from failed node:")
    logger.info("     result = await executor.execute(")
    logger.info("         resume_execution_id='exec-abc123',")
    logger.info("         global_context=context")
    logger.info("     )")


async def example_6_validation_node_outputs():
    """Example 6: Accessing validation node outputs"""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 6: Accessing Validation Node Outputs")
    logger.info("="*80)

    logger.info("Validation nodes produce rich outputs that can be used by downstream nodes:")

    example_outputs = {
        "phase_validator_output": {
            "status": "completed",
            "validation_passed": False,
            "validation_result": {
                "has_critical_failures": True,
                "critical_count": 2,
                "high_count": 1,
                "critical_failures": [
                    {
                        "phase": "implementation",
                        "check": "backend_structure",
                        "message": "Routes directory missing",
                        "fix": "Create routes/ directory with API endpoints"
                    },
                    {
                        "phase": "implementation",
                        "check": "backend_code_volume",
                        "message": "Only 11 files (need 20+)",
                        "fix": "Add services, controllers, and middleware"
                    }
                ]
            }
        },
        "gap_detector_output": {
            "status": "completed",
            "gaps_detected": 7,
            "critical_gaps": 3,
            "estimated_completion": 0.25,
            "is_deployable": False,
            "recovery_priority": 1,
            "recovery_context": {
                "recovery_instructions": [
                    {"action": "create_routes", "priority": 1},
                    {"action": "create_services", "priority": 1}
                ]
            }
        },
        "completeness_checker_output": {
            "status": "completed",
            "overall_completion": 0.34,
            "current_sub_phase": "backend_core",
            "backend_complete": False,
            "frontend_complete": False,
            "blockers": [
                "backend_core: Only 0/3 required files created",
                "frontend_structure: Only 0/4 required files created"
            ]
        }
    }

    logger.info("\n1. Phase Validator Output:")
    logger.info(json.dumps(example_outputs["phase_validator_output"], indent=2))

    logger.info("\n2. Gap Detector Output:")
    logger.info(json.dumps(example_outputs["gap_detector_output"], indent=2))

    logger.info("\n3. Completeness Checker Output:")
    logger.info(json.dumps(example_outputs["completeness_checker_output"], indent=2))

    logger.info("\nAccessing these outputs in your code:")
    logger.info("  context = workflow_execution_result.context")
    logger.info("  validation_output = context.get_node_output('validate_backend')")
    logger.info("  if not validation_output['validation_passed']:")
    logger.info("      # Handle validation failure")
    logger.info("      print(validation_output['validation_result']['critical_failures'])")


async def main():
    """Run all examples"""
    logger.info("DAG VALIDATION SYSTEM - EXAMPLES")
    logger.info("="*80 + "\n")

    # Note: These examples are demonstrations. In practice, you would:
    # 1. Uncomment the example you want to run
    # 2. Ensure team_execution_engine_v2 is available
    # 3. Ensure dag_executor is available
    # 4. Provide valid context and requirements

    # Example 1: Linear workflow with validation
    # await example_1_validated_linear_workflow()

    # Example 2: Parallel workflow with validation
    # await example_2_validated_parallel_workflow()

    # Example 3: Sub-phased implementation
    # await example_3_subphased_implementation()

    # Example 4: Custom validation configuration
    await example_4_custom_validation_configuration()

    # Example 5: Workflow recovery
    await example_5_workflow_recovery()

    # Example 6: Validation node outputs
    await example_6_validation_node_outputs()

    logger.info("\n" + "="*80)
    logger.info("Examples complete! Check the documentation for more details.")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
