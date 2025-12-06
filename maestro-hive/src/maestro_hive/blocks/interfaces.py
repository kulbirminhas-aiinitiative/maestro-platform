"""
Block Interfaces - AC-1: Clear Interface Definitions

This module defines the standard interfaces for all certified blocks.
Each interface extends BlockInterface and provides domain-specific contracts.

Reference: MD-2507 Acceptance Criterion 1
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..core.block_interface import BlockInterface, BlockResult, BlockStatus


# ============================================================================
# Common Types
# ============================================================================

@dataclass
class ValidationResult:
    """Standard validation result across all blocks"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class ExecutionResult:
    """Standard execution result for workflow operations"""
    success: bool
    execution_id: str
    status: str
    output: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class PhaseResult:
    """Result of phase execution"""
    phase: str
    passed: bool
    score: float
    gates_passed: List[str]
    gates_failed: List[str]
    requires_rework: bool
    output: Dict[str, Any]


@dataclass
class ContractValidation:
    """Contract validation outcome"""
    contract_id: str
    passed: bool
    violations: List[Dict[str, Any]]
    score: float


@dataclass
class IssueData:
    """Standard issue data structure"""
    key: str
    summary: str
    description: Optional[str]
    status: str
    issue_type: str
    priority: Optional[str]
    labels: List[str]
    parent_key: Optional[str]


@dataclass
class HealthStatus:
    """Block health status"""
    healthy: bool
    status: str
    version: str
    uptime_seconds: float
    last_error: Optional[str]


# ============================================================================
# IDAGExecutor Interface
# ============================================================================

class IDAGExecutor(BlockInterface):
    """
    Interface for DAG workflow execution.

    Wraps: dag_workflow.py, dag_executor.py
    Block ID: dag-executor
    Version: 2.0.0

    Contract:
        - execute() must return ExecutionResult
        - validate() must return ValidationResult
        - get_status() must return current execution status
        - Supports async execution with event callbacks
    """

    @property
    def block_id(self) -> str:
        return "dag-executor"

    @property
    def version(self) -> str:
        return "2.0.0"

    @abstractmethod
    def execute_dag(self, dag_definition: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a DAG workflow.

        Args:
            dag_definition: DAG structure with nodes and edges

        Returns:
            ExecutionResult with execution_id and status
        """
        pass

    @abstractmethod
    def validate_dag(self, dag_definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate a DAG definition without executing.

        Args:
            dag_definition: DAG structure to validate

        Returns:
            ValidationResult with any errors or warnings
        """
        pass

    @abstractmethod
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of an execution.

        Args:
            execution_id: ID from execute_dag result

        Returns:
            Current execution status and progress
        """
        pass

    @abstractmethod
    def pause_execution(self, execution_id: str) -> bool:
        """Pause an active execution"""
        pass

    @abstractmethod
    def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution"""
        pass


# ============================================================================
# IPhaseOrchestrator Interface
# ============================================================================

class IPhaseOrchestrator(BlockInterface):
    """
    Interface for SDLC phase orchestration.

    Wraps: phased_autonomous_executor.py, phase_models.py
    Block ID: phase-orchestrator
    Version: 1.5.0

    Contract:
        - run_phase() must execute a single phase with quality gates
        - transition() must validate phase transitions
        - Supports progressive quality thresholds
        - Handles rework and retry logic
    """

    @property
    def block_id(self) -> str:
        return "phase-orchestrator"

    @property
    def version(self) -> str:
        return "1.5.0"

    @abstractmethod
    def run_phase(self, phase: str, context: Dict[str, Any]) -> PhaseResult:
        """
        Execute a single SDLC phase.

        Args:
            phase: Phase name (requirements, design, implementation, testing, deployment)
            context: Execution context with inputs and configuration

        Returns:
            PhaseResult with quality scores and gate status
        """
        pass

    @abstractmethod
    def transition(self, from_phase: str, to_phase: str) -> bool:
        """
        Validate and perform phase transition.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition is valid and performed
        """
        pass

    @abstractmethod
    def get_current_phase(self) -> str:
        """Get the current active phase"""
        pass

    @abstractmethod
    def validate_entry_criteria(self, phase: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate phase entry criteria"""
        pass

    @abstractmethod
    def validate_exit_criteria(self, phase: str, outputs: Dict[str, Any]) -> ValidationResult:
        """Validate phase exit criteria"""
        pass


# ============================================================================
# IContractRegistry Interface
# ============================================================================

class IContractRegistry(BlockInterface):
    """
    Interface for output contract management.

    Wraps: output_contracts.py, contract_manager.py
    Block ID: contract-registry
    Version: 1.0.0

    Contract:
        - register() must store contracts with unique IDs
        - validate() must check outputs against registered contracts
        - Supports contract versioning and evolution
    """

    @property
    def block_id(self) -> str:
        return "contract-registry"

    @property
    def version(self) -> str:
        return "1.0.0"

    @abstractmethod
    def register_contract(self, contract: Dict[str, Any]) -> str:
        """
        Register a new output contract.

        Args:
            contract: Contract definition with requirements

        Returns:
            Contract ID
        """
        pass

    @abstractmethod
    def validate_output(self, block_id: str, output: Dict[str, Any]) -> ContractValidation:
        """
        Validate output against registered contract.

        Args:
            block_id: Block/phase ID to validate
            output: Output to validate

        Returns:
            ContractValidation with pass/fail and violations
        """
        pass

    @abstractmethod
    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered contract by ID"""
        pass

    @abstractmethod
    def list_contracts(self) -> List[str]:
        """List all registered contract IDs"""
        pass

    @abstractmethod
    def evolve_contract(self, contract_id: str, new_version: Dict[str, Any]) -> str:
        """Create a new version of an existing contract"""
        pass


# ============================================================================
# IJiraAdapter Interface
# ============================================================================

class IJiraAdapter(BlockInterface):
    """
    Interface for JIRA integration.

    Wraps: jira_adapter.py
    Block ID: jira-adapter
    Version: 3.1.0

    Contract:
        - CRUD operations on issues
        - Comment management
        - Epic hierarchy support
        - Async HTTP operations
    """

    @property
    def block_id(self) -> str:
        return "jira-adapter"

    @property
    def version(self) -> str:
        return "3.1.0"

    @abstractmethod
    def create_issue(self, issue: Dict[str, Any]) -> IssueData:
        """
        Create a new JIRA issue.

        Args:
            issue: Issue data (summary, description, type, etc.)

        Returns:
            Created issue with key
        """
        pass

    @abstractmethod
    def update_issue(self, key: str, updates: Dict[str, Any]) -> IssueData:
        """
        Update an existing issue.

        Args:
            key: Issue key (e.g., "MD-1234")
            updates: Fields to update

        Returns:
            Updated issue
        """
        pass

    @abstractmethod
    def get_issue(self, key: str) -> Optional[IssueData]:
        """Get issue by key"""
        pass

    @abstractmethod
    def add_comment(self, key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue"""
        pass

    @abstractmethod
    def transition_issue(self, key: str, target_status: str) -> bool:
        """Transition issue to a new status"""
        pass

    @abstractmethod
    def search_issues(self, jql: str) -> List[IssueData]:
        """Search issues using JQL"""
        pass


# ============================================================================
# IQualityFabric Interface
# ============================================================================

class IQualityFabric(BlockInterface):
    """
    Interface for Quality Fabric integration.

    Wraps: quality_fabric_client.py
    Block ID: quality-fabric
    Version: 2.0.0

    Contract:
        - validate_persona() must validate persona outputs
        - evaluate_gate() must evaluate phase quality gates
        - Health check endpoint
    """

    @property
    def block_id(self) -> str:
        return "quality-fabric"

    @property
    def version(self) -> str:
        return "2.0.0"

    @abstractmethod
    def validate_persona(
        self,
        persona_id: str,
        persona_type: str,
        artifacts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate persona output artifacts.

        Args:
            persona_id: Unique persona identifier
            persona_type: Type of persona
            artifacts: Output artifacts to validate

        Returns:
            Validation result with score and gates
        """
        pass

    @abstractmethod
    def evaluate_gate(
        self,
        phase: str,
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate phase quality gate.

        Args:
            phase: SDLC phase name
            outputs: Phase outputs to evaluate

        Returns:
            Gate evaluation result
        """
        pass

    @abstractmethod
    def get_health(self) -> HealthStatus:
        """Get Quality Fabric health status"""
        pass

    @abstractmethod
    def publish_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Publish quality metrics"""
        pass
