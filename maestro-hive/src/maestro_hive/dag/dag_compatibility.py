"""
DAG Compatibility Layer

Provides compatibility wrappers to run existing SDLC phases within the DAG framework.
This allows gradual migration without breaking existing functionality.

Architecture: Phase 1 of AGENT3_DAG_MIGRATION_GUIDE.md
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    NodeType,
    ExecutionMode,
    RetryPolicy,
)


logger = logging.getLogger(__name__)


# SDLC Phase definitions (from existing system)
SDLC_PHASES = [
    "requirement_analysis",
    "design",
    "backend_development",
    "frontend_development",
    "testing",
    "review"
]


@dataclass
class PhaseExecutionContext:
    """Context passed to phase executors"""
    phase_name: str
    requirement: str
    previous_phase_outputs: Dict[str, Dict[str, Any]]
    previous_phase_artifacts: Dict[str, List[str]]
    previous_phase_contracts: List[Any]
    global_context: Dict[str, Any]
    all_outputs: Dict[str, Dict[str, Any]]
    all_artifacts: Dict[str, List[str]]


class PhaseNodeExecutor:
    """
    Wrapper that adapts existing phase execution to DAG node interface.

    This allows existing TeamExecutionEngineV2SplitMode phases to run
    within the DAG framework without modification.
    """

    def __init__(
        self,
        phase_name: str,
        team_engine: Optional[Any] = None,  # TeamExecutionEngineV2SplitMode instance
    ):
        """
        Initialize phase node executor.

        Args:
            phase_name: Name of the SDLC phase (e.g., 'requirement_analysis')
            team_engine: Instance of TeamExecutionEngineV2SplitMode (set later if not provided)
        """
        self.phase_name = phase_name
        self.team_engine = team_engine
        logger.info(f"Initialized PhaseNodeExecutor for phase: {phase_name}")

    def set_team_engine(self, team_engine: Any) -> None:
        """Set the team execution engine instance"""
        self.team_engine = team_engine

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the phase within DAG context.

        Args:
            node_input: Dictionary with:
                - node_id: ID of the current node
                - node_name: Name of the current node
                - node_config: Configuration for this node
                - dependency_outputs: Outputs from dependency nodes
                - dependency_artifacts: Artifacts from dependency nodes
                - global_context: Global workflow context
                - all_outputs: All node outputs so far
                - all_artifacts: All artifacts so far

        Returns:
            Dictionary with:
                - phase: Phase name
                - status: 'completed' or 'failed'
                - output: Phase execution output
                - artifacts: List of artifact paths
                - contracts: Contracts generated/updated
                - error: Error message (if failed)
        """
        logger.info(f"Executing phase {self.phase_name} as DAG node")

        try:
            # Extract context
            global_context = node_input.get('global_context', {})
            requirement = global_context.get('requirement', '')
            dependency_outputs = node_input.get('dependency_outputs', {})
            dependency_artifacts = node_input.get('dependency_artifacts', {})

            # Build phase execution context
            phase_context = PhaseExecutionContext(
                phase_name=self.phase_name,
                requirement=requirement,
                previous_phase_outputs=dependency_outputs,
                previous_phase_artifacts=dependency_artifacts,
                previous_phase_contracts=self._extract_contracts(dependency_outputs),
                global_context=global_context,
                all_outputs=node_input.get('all_outputs', {}),
                all_artifacts=node_input.get('all_artifacts', {}),
            )

            # Execute phase using existing engine
            if not self.team_engine:
                raise ValueError(f"Team engine not set for phase {self.phase_name}")

            result = await self._execute_phase_with_engine(phase_context)

            # Format output
            output = {
                'phase': self.phase_name,
                'status': 'completed',
                'output': result.get('output', {}),
                'artifacts': result.get('artifacts', []),
                'contracts': result.get('contracts', []),
                'execution_time': result.get('execution_time', 0),
                'personas_executed': result.get('personas_executed', []),
            }

            logger.info(f"Phase {self.phase_name} completed successfully")
            return output

        except Exception as e:
            logger.error(f"Phase {self.phase_name} failed: {e}", exc_info=True)
            return {
                'phase': self.phase_name,
                'status': 'failed',
                'error': str(e),
                'output': {},
                'artifacts': [],
                'contracts': [],
            }

    async def _execute_phase_with_engine(
        self,
        phase_context: PhaseExecutionContext,
    ) -> Dict[str, Any]:
        """
        Execute phase using the existing TeamExecutionEngineV2SplitMode.

        This is where we bridge to the existing implementation.
        """
        # Import here to avoid circular dependencies
        from team_execution_context import TeamExecutionContext

        # Build TeamExecutionContext from PhaseExecutionContext
        team_context = TeamExecutionContext(
            requirement=phase_context.requirement,
            phase_order=SDLC_PHASES,
        )

        # Populate previous phase outputs
        for prev_phase, prev_output in phase_context.previous_phase_outputs.items():
            team_context.set_phase_output(prev_phase, prev_output)

        # Get the phase requirement with full context
        phase_requirement = self._build_phase_requirement(phase_context)

        # Execute the phase using existing engine
        logger.info(f"Delegating to team engine for phase {self.phase_name}")
        result = await self.team_engine._execute_single_phase(
            phase_name=self.phase_name,
            context=team_context,
            requirement=phase_requirement,
        )

        return {
            'output': result,
            'artifacts': self._extract_artifacts(result),
            'contracts': self._extract_contracts_from_result(result),
            'execution_time': result.get('execution_time', 0),
            'personas_executed': result.get('personas_executed', []),
        }

    def _build_phase_requirement(self, phase_context: PhaseExecutionContext) -> str:
        """
        Build comprehensive phase requirement with full context.

        This ensures phases receive all previous phase outputs, artifacts, and contracts.
        """
        requirement_parts = [f"## Original Requirement:\n{phase_context.requirement}\n"]

        # Add previous phase outputs
        if phase_context.previous_phase_outputs:
            requirement_parts.append("\n## Previous Phase Outputs:")
            for prev_phase, output in phase_context.previous_phase_outputs.items():
                requirement_parts.append(f"\n### {prev_phase}:")
                requirement_parts.append(self._format_output(output))

        # Add artifacts
        if phase_context.previous_phase_artifacts:
            requirement_parts.append("\n## Available Artifacts:")
            for prev_phase, artifacts in phase_context.previous_phase_artifacts.items():
                if artifacts:
                    requirement_parts.append(f"\n### {prev_phase}:")
                    for artifact in artifacts:
                        requirement_parts.append(f"- {artifact}")

        # Add contracts
        if phase_context.previous_phase_contracts:
            requirement_parts.append("\n## Previous Phase Contracts:")
            for contract in phase_context.previous_phase_contracts:
                requirement_parts.append(self._format_contract(contract))

        return "\n".join(requirement_parts)

    def _format_output(self, output: Dict[str, Any]) -> str:
        """Format output for inclusion in requirement"""
        import json
        try:
            return json.dumps(output, indent=2)
        except Exception:
            return str(output)

    def _format_contract(self, contract: Any) -> str:
        """Format contract for inclusion in requirement"""
        import json
        try:
            if hasattr(contract, 'to_dict'):
                return json.dumps(contract.to_dict(), indent=2)
            elif isinstance(contract, dict):
                return json.dumps(contract, indent=2)
            else:
                return str(contract)
        except Exception:
            return str(contract)

    def _extract_artifacts(self, result: Dict[str, Any]) -> List[str]:
        """Extract artifact paths from phase result"""
        artifacts = []

        # Check for artifacts in result
        if 'artifacts' in result:
            artifacts.extend(result['artifacts'])

        # Check for file paths in output
        if 'files' in result:
            artifacts.extend(result['files'])

        # Check for generated files
        if 'generated_files' in result:
            artifacts.extend(result['generated_files'])

        return artifacts

    def _extract_contracts(self, outputs: Dict[str, Dict[str, Any]]) -> List[Any]:
        """Extract contracts from previous phase outputs"""
        contracts = []
        for phase_output in outputs.values():
            if 'contracts' in phase_output:
                contracts.extend(phase_output['contracts'])
        return contracts

    def _extract_contracts_from_result(self, result: Dict[str, Any]) -> List[Any]:
        """Extract contracts from phase execution result"""
        if 'contracts' in result:
            return result['contracts']
        return []


def generate_linear_workflow(
    workflow_name: str = "sdlc_linear",
    phases: Optional[List[str]] = None,
    team_engine: Optional[Any] = None,
) -> WorkflowDAG:
    """
    Generate a linear DAG workflow from SDLC phases.

    This creates a workflow where phases execute sequentially in order,
    matching the behavior of the existing system.

    Args:
        workflow_name: Name for the workflow
        phases: List of phase names (defaults to SDLC_PHASES)
        team_engine: TeamExecutionEngineV2SplitMode instance

    Returns:
        WorkflowDAG configured with linear phase execution
    """
    if phases is None:
        phases = SDLC_PHASES

    logger.info(f"Generating linear workflow with phases: {phases}")

    # Create workflow
    workflow = WorkflowDAG(name=workflow_name)
    workflow.metadata['type'] = 'linear'
    workflow.metadata['phases'] = phases

    # Create nodes for each phase
    previous_node_id = None
    for phase in phases:
        node_id = f"phase_{phase}"

        # Create phase executor
        executor = PhaseNodeExecutor(phase_name=phase, team_engine=team_engine)

        # Create workflow node
        node = WorkflowNode(
            node_id=node_id,
            name=phase,
            node_type=NodeType.PHASE,
            executor=executor.execute,
            dependencies=[previous_node_id] if previous_node_id else [],
            execution_mode=ExecutionMode.SEQUENTIAL,
            retry_policy=RetryPolicy(
                max_attempts=1,
                retry_on_failure=False,
            ),
            config={
                'phase': phase,
            },
            metadata={
                'phase_name': phase,
                'compatibility_mode': True,
            }
        )

        # Add node to workflow
        workflow.add_node(node)

        # Add edge from previous phase
        if previous_node_id:
            workflow.add_edge(previous_node_id, node_id)

        previous_node_id = node_id

    logger.info(f"Generated linear workflow with {len(phases)} phases")
    return workflow


def generate_parallel_workflow(
    workflow_name: str = "sdlc_parallel",
    team_engine: Optional[Any] = None,
) -> WorkflowDAG:
    """
    Generate a DAG workflow with parallel development phases.

    Architecture:
    - requirement_analysis
    - design
    - backend_development (parallel with frontend_development)
    - frontend_development (parallel with backend_development)
    - testing (depends on both development phases)
    - review

    Args:
        workflow_name: Name for the workflow
        team_engine: TeamExecutionEngineV2SplitMode instance

    Returns:
        WorkflowDAG configured with parallel execution
    """
    logger.info("Generating parallel workflow with concurrent development phases")

    workflow = WorkflowDAG(name=workflow_name)
    workflow.metadata['type'] = 'parallel'

    # Phase 1: Requirement Analysis (no dependencies)
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

    # Phase 2: Design (depends on requirement_analysis)
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

    # Phase 3a: Backend Development (depends on design, parallel with frontend)
    backend_executor = PhaseNodeExecutor("backend_development", team_engine)
    backend_node = WorkflowNode(
        node_id="phase_backend_development",
        name="backend_development",
        node_type=NodeType.PHASE,
        executor=backend_executor.execute,
        dependencies=["phase_design"],
        execution_mode=ExecutionMode.PARALLEL,
        config={'phase': 'backend_development'},
    )
    workflow.add_node(backend_node)
    workflow.add_edge("phase_design", "phase_backend_development")

    # Phase 3b: Frontend Development (depends on design, parallel with backend)
    frontend_executor = PhaseNodeExecutor("frontend_development", team_engine)
    frontend_node = WorkflowNode(
        node_id="phase_frontend_development",
        name="frontend_development",
        node_type=NodeType.PHASE,
        executor=frontend_executor.execute,
        dependencies=["phase_design"],
        execution_mode=ExecutionMode.PARALLEL,
        config={'phase': 'frontend_development'},
    )
    workflow.add_node(frontend_node)
    workflow.add_edge("phase_design", "phase_frontend_development")

    # Phase 4: Testing (depends on both development phases)
    testing_executor = PhaseNodeExecutor("testing", team_engine)
    testing_node = WorkflowNode(
        node_id="phase_testing",
        name="testing",
        node_type=NodeType.PHASE,
        executor=testing_executor.execute,
        dependencies=["phase_backend_development", "phase_frontend_development"],
        config={'phase': 'testing'},
    )
    workflow.add_node(testing_node)
    workflow.add_edge("phase_backend_development", "phase_testing")
    workflow.add_edge("phase_frontend_development", "phase_testing")

    # Phase 5: Review (depends on testing)
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

    logger.info("Generated parallel workflow with 6 phases (2 parallel development phases)")
    return workflow


# Export public API
__all__ = [
    'PhaseNodeExecutor',
    'PhaseExecutionContext',
    'generate_linear_workflow',
    'generate_parallel_workflow',
    'SDLC_PHASES',
]
