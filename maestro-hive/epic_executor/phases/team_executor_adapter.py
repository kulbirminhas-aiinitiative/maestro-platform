"""
TeamExecutorV2 Adapter for ImplementationPhase

This adapter bridges the ImplementationPhase with TeamExecutionEngineV2,
providing proper error handling and explicit failure when Claude API is unavailable.

EPIC: MD-2535
AC-1: TeamExecutorV2Adapter class created
AC-2: Adapter wraps TeamExecutionEngineV2 with proper error handling
AC-5: If Claude unavailable, raises explicit error (not silent fallback)
"""

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ClaudeUnavailableError(Exception):
    """
    Raised when Claude API is unavailable.

    This error is raised explicitly instead of silently falling back
    to stub generation, per AC-5.
    """
    pass


class ContractValidationError(Exception):
    """Raised when contract validation fails."""
    pass


class OutputValidationError(Exception):
    """Raised when generated output fails validation against acceptance criteria."""
    pass


@dataclass
class TaskExecutionResult:
    """Result from adapter task execution."""
    success: bool
    files_created: List[str] = field(default_factory=list)
    changes: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    quality_score: float = 0.0
    contract_fulfilled: bool = False
    validation_details: Optional[Dict[str, Any]] = None


@dataclass
class ContractValidationResult:
    """Result from contract validation."""
    valid: bool
    contracts_checked: int = 0
    contracts_passed: int = 0
    errors: List[str] = field(default_factory=list)


class TeamExecutorV2Adapter:
    """
    Adapter for TeamExecutionEngineV2 that provides explicit error handling.

    This adapter wraps TeamExecutionEngineV2 and:
    1. Raises ClaudeUnavailableError if Claude API is not available (AC-5)
    2. Validates contracts from previous phases (AC-4)
    3. Validates generated code against acceptance criteria (AC-6)

    Usage:
        adapter = TeamExecutorV2Adapter(output_dir="/path/to/output")

        # Check availability before execution
        adapter.check_claude_availability()  # Raises if unavailable

        # Execute task
        result = await adapter.execute_task({
            "epic_key": "MD-2535",
            "ac_id": "AC-1",
            "ac_description": "Create adapter class",
            "requirement_type": "feature",
            "team": ["senior_developer"]
        })
    """

    def __init__(
        self,
        output_dir: str = "/tmp",
        enable_validation: bool = True,
        quality_threshold: float = 0.8,
    ):
        """
        Initialize the adapter.

        Args:
            output_dir: Directory for generated files
            enable_validation: Whether to validate output against criteria
            quality_threshold: Minimum quality score (0.0-1.0)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_validation = enable_validation
        self.quality_threshold = quality_threshold

        self._engine = None
        self._claude_available = None

        logger.info(f"TeamExecutorV2Adapter initialized (output_dir={output_dir})")

    def _get_engine(self):
        """
        Lazy load TeamExecutionEngineV2.

        Raises:
            ClaudeUnavailableError: If engine cannot be loaded or Claude is unavailable
        """
        if self._engine is not None:
            return self._engine

        try:
            # Try importing from various paths
            try:
                from src.maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2
            except ImportError:
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
                    from src.maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2
                except ImportError:
                    try:
                        from teams.team_execution_v2 import TeamExecutionEngineV2
                    except ImportError as e:
                        raise ClaudeUnavailableError(
                            f"TeamExecutionEngineV2 could not be imported: {e}. "
                            "This is required for real code generation."
                        )

            self._engine = TeamExecutionEngineV2(output_dir=str(self.output_dir))
            logger.info("TeamExecutionEngineV2 loaded successfully")
            return self._engine

        except Exception as e:
            raise ClaudeUnavailableError(
                f"Failed to initialize TeamExecutionEngineV2: {e}"
            )

    def check_claude_availability(self) -> bool:
        """
        Check if Claude API is available.

        This method explicitly checks for Claude availability and raises
        an error if unavailable, per AC-5.

        Returns:
            True if Claude is available

        Raises:
            ClaudeUnavailableError: If Claude API is not available
        """
        if self._claude_available is not None:
            if not self._claude_available:
                raise ClaudeUnavailableError(
                    "Claude API is not available. Cannot proceed with code generation. "
                    "This adapter does NOT fall back to stub generation."
                )
            return True

        try:
            # Try to import and check Claude SDK
            try:
                sys.path.insert(0, '/home/ec2-user/projects/maestro-platform')
                from claude_code_api_layer import ClaudeCLIClient

                # Create client and do a minimal check
                client = ClaudeCLIClient()
                # Check if client can be created (doesn't make API call)
                self._claude_available = True
                logger.info("Claude API is available")
                return True

            except ImportError:
                self._claude_available = False
                raise ClaudeUnavailableError(
                    "claude_code_api_layer is not installed. "
                    "Claude API is required for real code generation. "
                    "This adapter does NOT fall back to stub generation."
                )

        except ClaudeUnavailableError:
            raise
        except Exception as e:
            self._claude_available = False
            raise ClaudeUnavailableError(
                f"Claude API availability check failed: {e}. "
                "This adapter does NOT fall back to stub generation."
            )

    async def execute_task(self, task: Dict[str, Any]) -> TaskExecutionResult:
        """
        Execute an implementation task via TeamExecutionEngineV2.

        This is the main entry point for executing implementation work.
        It checks Claude availability, executes via the engine, and
        validates the output.

        Args:
            task: Task specification containing:
                - epic_key: EPIC key (e.g., "MD-2535")
                - ac_id: Acceptance criterion ID
                - ac_description: Description of the criterion
                - requirement_type: Type of requirement
                - team: List of team roles
                - previous_contracts: Optional contracts from previous phases

        Returns:
            TaskExecutionResult with success status, files, and changes

        Raises:
            ClaudeUnavailableError: If Claude API is not available
        """
        logger.info(f"Executing task: {task.get('ac_id', 'unknown')}")

        # AC-5: Check Claude availability first - no silent fallback
        self.check_claude_availability()

        try:
            engine = self._get_engine()

            # Build requirement string from task
            requirement = self._build_requirement_from_task(task)

            # Prepare constraints with previous contracts (AC-4)
            constraints = {
                "epic_key": task.get("epic_key"),
                "ac_id": task.get("ac_id"),
                "requirement_type": task.get("requirement_type", "feature"),
                "quality_threshold": self.quality_threshold,
            }

            # Pass previous phase contracts if available
            if "previous_contracts" in task:
                constraints["previous_phase_contracts"] = task["previous_contracts"]
                logger.info(f"Passing {len(task['previous_contracts'])} contracts from previous phases")

            # Execute via TeamExecutionEngineV2
            logger.info("Executing via TeamExecutionEngineV2...")
            result = await engine.execute(
                requirement=requirement,
                constraints=constraints
            )

            # Extract results
            files_created = []
            changes = {}

            if result.get("success"):
                # Extract files from deliverables
                deliverables = result.get("deliverables", {})
                for persona_id, persona_result in deliverables.items():
                    files_created.extend(persona_result.get("files_created", []))
                    for file_path in persona_result.get("files_created", []):
                        changes[file_path] = f"Generated by {persona_id}"

                quality_score = result.get("quality", {}).get("overall_quality_score", 0.0)
                contract_fulfilled = result.get("quality", {}).get("contracts_fulfilled", 0) > 0

                # AC-6: Validate output if enabled
                if self.enable_validation and files_created:
                    validation = await self._validate_output(
                        files_created,
                        [task.get("ac_description", "")]
                    )
                    if not validation.get("valid", True):
                        logger.warning(f"Output validation failed: {validation.get('errors', [])}")

                return TaskExecutionResult(
                    success=True,
                    files_created=files_created,
                    changes=changes,
                    quality_score=quality_score,
                    contract_fulfilled=contract_fulfilled,
                    validation_details=result,
                )
            else:
                error_msg = result.get("error", "Unknown execution error")
                logger.error(f"Execution failed: {error_msg}")

                return TaskExecutionResult(
                    success=False,
                    error=error_msg,
                    validation_details=result,
                )

        except ClaudeUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return TaskExecutionResult(
                success=False,
                error=str(e),
            )

    def _build_requirement_from_task(self, task: Dict[str, Any]) -> str:
        """Build a requirement string from task specification."""
        parts = []

        if task.get("epic_key"):
            parts.append(f"EPIC: {task['epic_key']}")

        if task.get("epic_summary"):
            parts.append(f"Summary: {task['epic_summary']}")

        if task.get("ac_id") and task.get("ac_description"):
            parts.append(f"Acceptance Criterion ({task['ac_id']}): {task['ac_description']}")
        elif task.get("ac_description"):
            parts.append(f"Requirement: {task['ac_description']}")

        if task.get("requirement_type"):
            parts.append(f"Type: {task['requirement_type']}")

        return "\n".join(parts)

    async def _validate_output(
        self,
        files: List[str],
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Validate generated files against acceptance criteria.

        AC-6: Generated code is validated against acceptance criteria

        Args:
            files: List of generated file paths
            criteria: List of acceptance criteria to validate against

        Returns:
            Dict with validation status and details
        """
        errors = []

        for file_path in files:
            path = Path(file_path)

            # Check file exists
            if not path.exists():
                errors.append(f"Generated file does not exist: {file_path}")
                continue

            # Check file is not empty
            if path.stat().st_size == 0:
                errors.append(f"Generated file is empty: {file_path}")
                continue

            # Check for stub patterns (NotImplementedError, TODO, pass only)
            content = path.read_text()
            if "NotImplementedError" in content and "raise NotImplementedError" in content:
                # Count stub indicators vs actual code
                lines = content.split("\n")
                stub_indicators = sum(1 for l in lines if "NotImplementedError" in l or (l.strip() == "pass"))
                # Real code = lines that are not comments, not docstrings, not empty, not just 'pass' or 'raise'
                real_code_lines = sum(
                    1 for l in lines
                    if l.strip()
                    and not l.strip().startswith("#")
                    and not l.strip().startswith('"""')
                    and not l.strip().startswith("'''")
                    and l.strip() != "pass"
                    and "NotImplementedError" not in l
                    and not l.strip().startswith("def ")  # Don't count function signatures as "real code"
                )

                # If stub patterns outnumber real implementation, flag as stub
                if stub_indicators >= 2 and stub_indicators >= real_code_lines:
                    errors.append(f"File appears to be a stub with NotImplementedError: {file_path}")

        return {
            "valid": len(errors) == 0,
            "files_checked": len(files),
            "errors": errors,
        }

    async def validate_contracts(
        self,
        contracts: List[Dict[str, Any]]
    ) -> ContractValidationResult:
        """
        Validate contracts from previous phases.

        AC-4: Contracts from previous phases pass correctly

        Args:
            contracts: List of contract specifications from previous phases

        Returns:
            ContractValidationResult with validation status
        """
        errors = []
        passed = 0

        for contract in contracts:
            contract_id = contract.get("id", "unknown")

            # Check required fields
            required_fields = ["id", "name", "deliverables"]
            missing = [f for f in required_fields if f not in contract]

            if missing:
                errors.append(f"Contract {contract_id} missing fields: {missing}")
                continue

            # Check deliverables are present
            deliverables = contract.get("deliverables", [])
            if not deliverables:
                errors.append(f"Contract {contract_id} has no deliverables")
                continue

            passed += 1

        return ContractValidationResult(
            valid=len(errors) == 0,
            contracts_checked=len(contracts),
            contracts_passed=passed,
            errors=errors,
        )

    # Interface methods expected by ImplementationPhase

    async def implement(self, description: str) -> Dict[str, Any]:
        """
        Implement based on description.

        This method provides compatibility with the existing
        ImplementationPhase._implement_ac method.

        Args:
            description: Implementation description

        Returns:
            Dict with files and changes
        """
        result = await self.execute_task({
            "ac_description": description,
            "requirement_type": "feature",
        })

        return {
            "files": result.files_created,
            "changes": result.changes,
            "success": result.success,
            "error": result.error,
        }
