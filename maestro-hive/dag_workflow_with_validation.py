#!/usr/bin/env python3
"""
DAG Workflow with Integrated Validation
Generates workflows with quality gates, sub-phases, and validation nodes
"""

import logging
from typing import Dict, Any, Optional, List

from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    NodeType,
    ExecutionMode,
    RetryPolicy,
)
from dag_compatibility import PhaseNodeExecutor
from dag_validation_nodes import (
    ValidationNodeType,
    create_validation_node,
    create_handoff_validation_node,
)

logger = logging.getLogger(__name__)


def generate_validated_linear_workflow(
    workflow_name: str = "sdlc_validated_linear",
    team_engine: Optional[Any] = None,
    enable_validation: bool = True,
    enable_handoff_validation: bool = True,
    fail_on_validation_error: bool = True,
) -> WorkflowDAG:
    """
    Generate linear workflow with validation gates

    Architecture:
    - requirement_analysis
    - [validate_requirements]
    - design
    - [validate_design]
    - [handoff: design -> backend]
    - backend_development
    - [validate_backend]
    - [handoff: backend -> frontend]
    - frontend_development
    - [validate_frontend]
    - [handoff: frontend -> testing]
    - testing
    - [validate_testing]
    - [handoff: testing -> review]
    - review
    - [final_validation]

    Args:
        workflow_name: Name for the workflow
        team_engine: TeamExecutionEngineV2SplitMode instance
        enable_validation: Add validation gates after phases
        enable_handoff_validation: Add handoff validators between phases
        fail_on_validation_error: Whether validation failures should stop workflow

    Returns:
        WorkflowDAG with validation gates
    """
    logger.info(f"Generating validated linear workflow: {workflow_name}")

    workflow = WorkflowDAG(name=workflow_name)
    workflow.metadata['type'] = 'linear_validated'
    workflow.metadata['validation_enabled'] = enable_validation
    workflow.metadata['handoff_validation_enabled'] = enable_handoff_validation

    phases = [
        "requirement_analysis",
        "design",
        "backend_development",
        "frontend_development",
        "testing",
        "review"
    ]

    previous_node_id = None

    for i, phase in enumerate(phases):
        phase_node_id = f"phase_{phase}"

        # Create phase node
        executor = PhaseNodeExecutor(phase_name=phase, team_engine=team_engine)
        phase_node = WorkflowNode(
            node_id=phase_node_id,
            name=phase,
            node_type=NodeType.PHASE,
            executor=executor.execute,
            dependencies=[previous_node_id] if previous_node_id else [],
            execution_mode=ExecutionMode.SEQUENTIAL,
            retry_policy=RetryPolicy(
                max_attempts=2,
                retry_on_failure=True,
                retry_delay_seconds=10,
            ),
            config={'phase': phase},
            metadata={'phase_name': phase}
        )
        workflow.add_node(phase_node)

        if previous_node_id:
            workflow.add_edge(previous_node_id, phase_node_id)

        # Add validation gate after phase
        if enable_validation:
            validator_node_id = f"validate_{phase}"
            validator_node = create_validation_node(
                node_id=validator_node_id,
                validation_type=ValidationNodeType.PHASE_VALIDATOR,
                phase_to_validate=phase,
                dependencies=[phase_node_id],
                fail_on_error=fail_on_validation_error,
            )
            workflow.add_node(validator_node)
            workflow.add_edge(phase_node_id, validator_node_id)
            previous_node_id = validator_node_id
        else:
            previous_node_id = phase_node_id

        # Add handoff validation before next phase
        if enable_handoff_validation and i < len(phases) - 1:
            next_phase = phases[i + 1]
            handoff_node_id = f"handoff_{phase}_to_{next_phase}"
            handoff_node = create_handoff_validation_node(
                node_id=handoff_node_id,
                from_phase=phase,
                to_phase=next_phase,
                dependencies=[previous_node_id],
                fail_on_error=fail_on_validation_error,
            )
            workflow.add_node(handoff_node)
            workflow.add_edge(previous_node_id, handoff_node_id)
            previous_node_id = handoff_node_id

    # Add final validation and gap detection
    if enable_validation:
        # Gap detection after all phases
        gap_detector_id = "final_gap_detection"
        gap_detector = create_validation_node(
            node_id=gap_detector_id,
            validation_type=ValidationNodeType.GAP_DETECTOR,
            dependencies=[previous_node_id],
            fail_on_error=fail_on_validation_error,
            generate_recovery_context=True,
        )
        workflow.add_node(gap_detector)
        workflow.add_edge(previous_node_id, gap_detector_id)

    logger.info(f"Generated validated linear workflow with {len(workflow.nodes)} nodes")
    return workflow


def generate_validated_parallel_workflow(
    workflow_name: str = "sdlc_validated_parallel",
    team_engine: Optional[Any] = None,
    enable_validation: bool = True,
    enable_handoff_validation: bool = True,
    fail_on_validation_error: bool = True,
) -> WorkflowDAG:
    """
    Generate parallel workflow with validation gates

    Architecture:
    - requirement_analysis
    - [validate_requirements]
    - design
    - [validate_design]
    - [handoff: design -> backend/frontend]
    - backend_development (parallel)
    - frontend_development (parallel)
    - [validate_backend]
    - [validate_frontend]
    - [handoff: backend/frontend -> testing]
    - testing
    - [validate_testing]
    - review
    - [final_validation]

    Args:
        workflow_name: Name for the workflow
        team_engine: TeamExecutionEngineV2SplitMode instance
        enable_validation: Add validation gates after phases
        enable_handoff_validation: Add handoff validators between phases
        fail_on_validation_error: Whether validation failures should stop workflow

    Returns:
        WorkflowDAG with parallel development and validation gates
    """
    logger.info(f"Generating validated parallel workflow: {workflow_name}")

    workflow = WorkflowDAG(name=workflow_name)
    workflow.metadata['type'] = 'parallel_validated'
    workflow.metadata['validation_enabled'] = enable_validation

    # Phase 1: Requirement Analysis
    req_executor = PhaseNodeExecutor("requirement_analysis", team_engine)
    req_node = WorkflowNode(
        node_id="phase_requirement_analysis",
        name="requirement_analysis",
        node_type=NodeType.PHASE,
        executor=req_executor.execute,
        dependencies=[],
        config={'phase': 'requirement_analysis'},
    )
    workflow.add_node(req_node)

    previous_node_id = "phase_requirement_analysis"

    # Validation after requirements
    if enable_validation:
        req_validator = create_validation_node(
            node_id="validate_requirement_analysis",
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="requirement_analysis",
            dependencies=[previous_node_id],
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(req_validator)
        workflow.add_edge(previous_node_id, "validate_requirement_analysis")
        previous_node_id = "validate_requirement_analysis"

    # Phase 2: Design
    design_executor = PhaseNodeExecutor("design", team_engine)
    design_node = WorkflowNode(
        node_id="phase_design",
        name="design",
        node_type=NodeType.PHASE,
        executor=design_executor.execute,
        dependencies=[previous_node_id],
        config={'phase': 'design'},
    )
    workflow.add_node(design_node)
    workflow.add_edge(previous_node_id, "phase_design")
    previous_node_id = "phase_design"

    # Validation after design
    if enable_validation:
        design_validator = create_validation_node(
            node_id="validate_design",
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="design",
            dependencies=[previous_node_id],
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(design_validator)
        workflow.add_edge(previous_node_id, "validate_design")
        previous_node_id = "validate_design"

    # Phase 3a: Backend Development (parallel with frontend)
    backend_executor = PhaseNodeExecutor("backend_development", team_engine)
    backend_node = WorkflowNode(
        node_id="phase_backend_development",
        name="backend_development",
        node_type=NodeType.PHASE,
        executor=backend_executor.execute,
        dependencies=[previous_node_id],
        execution_mode=ExecutionMode.PARALLEL,
        config={'phase': 'backend_development'},
        retry_policy=RetryPolicy(
            max_attempts=2,
            retry_on_failure=True,
            retry_delay_seconds=30,
        ),
    )
    workflow.add_node(backend_node)
    workflow.add_edge(previous_node_id, "phase_backend_development")

    # Phase 3b: Frontend Development (parallel with backend)
    frontend_executor = PhaseNodeExecutor("frontend_development", team_engine)
    frontend_node = WorkflowNode(
        node_id="phase_frontend_development",
        name="frontend_development",
        node_type=NodeType.PHASE,
        executor=frontend_executor.execute,
        dependencies=[previous_node_id],
        execution_mode=ExecutionMode.PARALLEL,
        config={'phase': 'frontend_development'},
        retry_policy=RetryPolicy(
            max_attempts=2,
            retry_on_failure=True,
            retry_delay_seconds=30,
        ),
    )
    workflow.add_node(frontend_node)
    workflow.add_edge(previous_node_id, "phase_frontend_development")

    # Validation after backend
    validation_dependencies = []
    if enable_validation:
        backend_validator = create_validation_node(
            node_id="validate_backend_development",
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="backend_development",
            dependencies=["phase_backend_development"],
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(backend_validator)
        workflow.add_edge("phase_backend_development", "validate_backend_development")
        validation_dependencies.append("validate_backend_development")

        # Validation after frontend
        frontend_validator = create_validation_node(
            node_id="validate_frontend_development",
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="frontend_development",
            dependencies=["phase_frontend_development"],
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(frontend_validator)
        workflow.add_edge("phase_frontend_development", "validate_frontend_development")
        validation_dependencies.append("validate_frontend_development")

        # Implementation completeness check (depends on both validations)
        completeness_checker = create_validation_node(
            node_id="check_implementation_completeness",
            validation_type=ValidationNodeType.COMPLETENESS_CHECKER,
            dependencies=validation_dependencies,
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(completeness_checker)
        workflow.add_edge("validate_backend_development", "check_implementation_completeness")
        workflow.add_edge("validate_frontend_development", "check_implementation_completeness")

        testing_dependencies = ["check_implementation_completeness"]
    else:
        testing_dependencies = ["phase_backend_development", "phase_frontend_development"]

    # Phase 4: Testing
    testing_executor = PhaseNodeExecutor("testing", team_engine)
    testing_node = WorkflowNode(
        node_id="phase_testing",
        name="testing",
        node_type=NodeType.PHASE,
        executor=testing_executor.execute,
        dependencies=testing_dependencies,
        config={'phase': 'testing'},
    )
    workflow.add_node(testing_node)
    for dep in testing_dependencies:
        workflow.add_edge(dep, "phase_testing")

    previous_node_id = "phase_testing"

    # Validation after testing
    if enable_validation:
        testing_validator = create_validation_node(
            node_id="validate_testing",
            validation_type=ValidationNodeType.PHASE_VALIDATOR,
            phase_to_validate="testing",
            dependencies=[previous_node_id],
            fail_on_error=fail_on_validation_error,
        )
        workflow.add_node(testing_validator)
        workflow.add_edge(previous_node_id, "validate_testing")
        previous_node_id = "validate_testing"

    # Phase 5: Review
    review_executor = PhaseNodeExecutor("review", team_engine)
    review_node = WorkflowNode(
        node_id="phase_review",
        name="review",
        node_type=NodeType.PHASE,
        executor=review_executor.execute,
        dependencies=[previous_node_id],
        config={'phase': 'review'},
    )
    workflow.add_node(review_node)
    workflow.add_edge(previous_node_id, "phase_review")
    previous_node_id = "phase_review"

    # Final validation and gap detection
    if enable_validation:
        gap_detector = create_validation_node(
            node_id="final_gap_detection",
            validation_type=ValidationNodeType.GAP_DETECTOR,
            dependencies=[previous_node_id],
            fail_on_error=fail_on_validation_error,
            generate_recovery_context=True,
        )
        workflow.add_node(gap_detector)
        workflow.add_edge(previous_node_id, "final_gap_detection")

    logger.info(f"Generated validated parallel workflow with {len(workflow.nodes)} nodes")
    return workflow


def generate_subphased_implementation_workflow(
    workflow_name: str = "sdlc_subphased",
    team_engine: Optional[Any] = None,
    enable_validation: bool = True,
) -> WorkflowDAG:
    """
    Generate workflow with granular implementation sub-phases

    Implementation broken into:
    1. backend_models - Data models and types
    2. backend_core - Services and business logic
    3. backend_api - Routes and controllers
    4. backend_middleware - Auth, validation, error handling
    5. frontend_structure - Basic app structure
    6. frontend_core - Core components and routing
    7. frontend_features - Feature-specific components
    8. integration - Frontend-backend integration

    Each sub-phase has validation before moving to next

    Args:
        workflow_name: Name for the workflow
        team_engine: TeamExecutionEngineV2SplitMode instance
        enable_validation: Add validation gates after each sub-phase

    Returns:
        WorkflowDAG with granular sub-phases
    """
    logger.info(f"Generating sub-phased implementation workflow: {workflow_name}")

    workflow = WorkflowDAG(name=workflow_name)
    workflow.metadata['type'] = 'subphased_implementation'

    # Phase 1: Requirement Analysis
    req_executor = PhaseNodeExecutor("requirement_analysis", team_engine)
    req_node = WorkflowNode(
        node_id="phase_requirement_analysis",
        name="requirement_analysis",
        node_type=NodeType.PHASE,
        executor=req_executor.execute,
        dependencies=[],
        config={'phase': 'requirement_analysis'},
    )
    workflow.add_node(req_node)

    # Phase 2: Design
    design_executor = PhaseNodeExecutor("design", team_engine)
    design_node = WorkflowNode(
        node_id="phase_design",
        name="design",
        node_type=NodeType.PHASE,
        executor=design_executor.execute,
        dependencies=["phase_requirement_analysis"],
        config={'phase': 'design'},
    )
    workflow.add_node(design_node)
    workflow.add_edge("phase_requirement_analysis", "phase_design")

    # Backend Sub-Phases (sequential)
    backend_subphases = [
        ("backend_models", "Data models and schemas", None),
        ("backend_core", "Services and business logic", "backend_models"),
        ("backend_api", "Routes and controllers", "backend_core"),
        ("backend_middleware", "Auth and middleware", "backend_api"),
    ]

    previous_backend_node = "phase_design"
    for subphase_name, description, _ in backend_subphases:
        node_id = f"subphase_{subphase_name}"

        # Create sub-phase node (using backend_development executor with specific config)
        executor = PhaseNodeExecutor("backend_development", team_engine)
        node = WorkflowNode(
            node_id=node_id,
            name=subphase_name,
            node_type=NodeType.PHASE,
            executor=executor.execute,
            dependencies=[previous_backend_node],
            config={
                'phase': 'backend_development',
                'subphase': subphase_name,
                'description': description
            },
            metadata={'subphase': subphase_name}
        )
        workflow.add_node(node)
        workflow.add_edge(previous_backend_node, node_id)

        # Add validation after each sub-phase
        if enable_validation:
            validator_id = f"validate_{subphase_name}"
            validator = create_validation_node(
                node_id=validator_id,
                validation_type=ValidationNodeType.COMPLETENESS_CHECKER,
                phase_to_validate=subphase_name,
                dependencies=[node_id],
                fail_on_error=True,
            )
            workflow.add_node(validator)
            workflow.add_edge(node_id, validator_id)
            previous_backend_node = validator_id
        else:
            previous_backend_node = node_id

    # Frontend Sub-Phases (can start after backend_api is done)
    frontend_subphases = [
        ("frontend_structure", "Basic app structure"),
        ("frontend_core", "Core components and routing"),
        ("frontend_features", "Feature components"),
    ]

    # Frontend starts after backend_api (or its validator)
    frontend_start_dependency = "validate_backend_api" if enable_validation else "subphase_backend_api"

    previous_frontend_node = frontend_start_dependency
    for subphase_name, description in frontend_subphases:
        node_id = f"subphase_{subphase_name}"

        executor = PhaseNodeExecutor("frontend_development", team_engine)
        node = WorkflowNode(
            node_id=node_id,
            name=subphase_name,
            node_type=NodeType.PHASE,
            executor=executor.execute,
            dependencies=[previous_frontend_node],
            config={
                'phase': 'frontend_development',
                'subphase': subphase_name,
                'description': description
            },
            metadata={'subphase': subphase_name}
        )
        workflow.add_node(node)
        workflow.add_edge(previous_frontend_node, node_id)

        # Add validation
        if enable_validation:
            validator_id = f"validate_{subphase_name}"
            validator = create_validation_node(
                node_id=validator_id,
                validation_type=ValidationNodeType.COMPLETENESS_CHECKER,
                phase_to_validate=subphase_name,
                dependencies=[node_id],
                fail_on_error=True,
            )
            workflow.add_node(validator)
            workflow.add_edge(node_id, validator_id)
            previous_frontend_node = validator_id
        else:
            previous_frontend_node = node_id

    # Integration sub-phase (depends on both backend and frontend complete)
    integration_dependencies = [previous_backend_node, previous_frontend_node]
    integration_node_id = "subphase_integration"
    executor = PhaseNodeExecutor("backend_development", team_engine)  # Could be either
    integration_node = WorkflowNode(
        node_id=integration_node_id,
        name="integration",
        node_type=NodeType.PHASE,
        executor=executor.execute,
        dependencies=integration_dependencies,
        config={
            'phase': 'integration',
            'subphase': 'integration',
            'description': 'Frontend-backend integration'
        },
        metadata={'subphase': 'integration'}
    )
    workflow.add_node(integration_node)
    for dep in integration_dependencies:
        workflow.add_edge(dep, integration_node_id)

    # Testing phase
    testing_executor = PhaseNodeExecutor("testing", team_engine)
    testing_node = WorkflowNode(
        node_id="phase_testing",
        name="testing",
        node_type=NodeType.PHASE,
        executor=testing_executor.execute,
        dependencies=[integration_node_id],
        config={'phase': 'testing'},
    )
    workflow.add_node(testing_node)
    workflow.add_edge(integration_node_id, "phase_testing")

    # Review phase
    review_executor = PhaseNodeExecutor("review", team_engine)
    review_node = WorkflowNode(
        node_id="phase_review",
        name="review",
        node_type=NodeType.PHASE,
        executor=review_executor.execute,
        dependencies=["phase_testing"],
        config={'phase': 'review'},
    )
    workflow.add_node(review_node)
    workflow.add_edge("phase_testing", "phase_review")

    # Final gap detection
    if enable_validation:
        gap_detector = create_validation_node(
            node_id="final_gap_detection",
            validation_type=ValidationNodeType.GAP_DETECTOR,
            dependencies=["phase_review"],
            fail_on_error=True,
            generate_recovery_context=True,
        )
        workflow.add_node(gap_detector)
        workflow.add_edge("phase_review", "final_gap_detection")

    logger.info(f"Generated sub-phased workflow with {len(workflow.nodes)} nodes")
    return workflow


# Export public API
__all__ = [
    'generate_validated_linear_workflow',
    'generate_validated_parallel_workflow',
    'generate_subphased_implementation_workflow',
]
