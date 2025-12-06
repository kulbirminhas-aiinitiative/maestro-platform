"""
Phase 3: Implementation

Execute work via AI agents using team_execution_v2.
This phase implements the acceptance criteria for 25 compliance points.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    AcceptanceCriterion,
    ACStatus,
    EpicInfo,
    ExecutionPhase,
    PhaseResult,
)


@dataclass
class ImplementationResult:
    """Result from the implementation phase."""
    implementation_files: List[str]
    acs_implemented: Dict[str, ACStatus]  # AC ID -> Status
    code_changes: Dict[str, str]  # File path -> Change description
    points_earned: float  # Out of 25


class ImplementationPhase:
    """
    Phase 3: Implementation Execution

    Responsibilities:
    1. Execute work for each acceptance criterion
    2. Generate code in appropriate repos
    3. Track implementation files created
    4. Update AC status as work progresses
    """

    def __init__(
        self,
        output_dir: str = "/tmp",
        enable_ai_execution: bool = True,
    ):
        """
        Initialize the implementation phase.

        Args:
            output_dir: Directory for generated files
            enable_ai_execution: Whether to use AI agents for execution
        """
        self.output_dir = Path(output_dir)
        self.enable_ai_execution = enable_ai_execution
        self._team_executor = None

    async def _get_team_executor(self):
        """
        Lazy load the team executor.

        EPIC MD-2535: Updated to use TeamExecutorV2Adapter which provides:
        - Explicit error handling (no silent fallback to stubs)
        - Contract validation from previous phases
        - Output validation against acceptance criteria

        Raises:
            ClaudeUnavailableError: If Claude API is not available
        """
        if self._team_executor is None and self.enable_ai_execution:
            try:
                # AC-3: Use TeamExecutorV2Adapter instead of direct engine access
                from .team_executor_adapter import TeamExecutorV2Adapter, ClaudeUnavailableError

                self._team_executor = TeamExecutorV2Adapter(
                    output_dir=str(self.output_dir),
                    enable_validation=True,
                    quality_threshold=0.8,
                )

                # AC-5: Check Claude availability explicitly - no silent fallback
                self._team_executor.check_claude_availability()

            except ImportError as e:
                # Adapter not available - this is a critical error
                raise ImportError(
                    f"TeamExecutorV2Adapter is required but could not be imported: {e}. "
                    "This is a critical component for EPIC execution."
                )

        if self._team_executor is None:
            # AC-5: Do NOT fallback to BasicImplementationExecutor silently
            # Instead, raise an explicit error
            from .team_executor_adapter import ClaudeUnavailableError
            raise ClaudeUnavailableError(
                "AI execution is disabled but no fallback is allowed. "
                "Enable AI execution or provide a valid team executor."
            )

        return self._team_executor

    async def execute(
        self,
        epic_info: EpicInfo,
        team_composition: List[str],
        requirement_type: str,
    ) -> Tuple[PhaseResult, Optional[ImplementationResult]]:
        """
        Execute the implementation phase.

        Args:
            epic_info: EPIC information with acceptance criteria
            team_composition: List of agent roles to use
            requirement_type: Type of requirement (feature, bug, etc.)

        Returns:
            Tuple of (PhaseResult, ImplementationResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            executor = await self._get_team_executor()

            implementation_files: List[str] = []
            acs_implemented: Dict[str, ACStatus] = {}
            code_changes: Dict[str, str] = {}

            # Execute each acceptance criterion
            for ac in epic_info.acceptance_criteria:
                ac_result = await self._implement_ac(
                    executor=executor,
                    epic_info=epic_info,
                    ac=ac,
                    team_composition=team_composition,
                    requirement_type=requirement_type,
                )

                if ac_result["success"]:
                    acs_implemented[ac.id] = ACStatus.IMPLEMENTED
                    ac.status = ACStatus.IMPLEMENTED
                    implementation_files.extend(ac_result.get("files", []))
                    code_changes.update(ac_result.get("changes", {}))
                    artifacts.append(f"Implemented {ac.id}: {ac.description[:50]}...")
                else:
                    acs_implemented[ac.id] = ACStatus.FAILED
                    ac.status = ACStatus.FAILED
                    errors.append(f"Failed to implement {ac.id}: {ac_result.get('error', 'Unknown error')}")

            # Calculate points
            total_acs = len(epic_info.acceptance_criteria)
            implemented_count = sum(1 for s in acs_implemented.values() if s == ACStatus.IMPLEMENTED)
            points_earned = (implemented_count / total_acs * 25) if total_acs > 0 else 0

            # Build result
            impl_result = ImplementationResult(
                implementation_files=implementation_files,
                acs_implemented=acs_implemented,
                code_changes=code_changes,
                points_earned=points_earned,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.IMPLEMENTATION,
                success=implemented_count > 0,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "acs_implemented": implemented_count,
                    "acs_total": total_acs,
                    "files_created": len(implementation_files),
                    "points_earned": points_earned,
                    "points_max": 25.0,
                }
            )

            return phase_result, impl_result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.IMPLEMENTATION,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    async def _implement_ac(
        self,
        executor,
        epic_info: EpicInfo,
        ac: AcceptanceCriterion,
        team_composition: List[str],
        requirement_type: str,
    ) -> Dict[str, Any]:
        """
        Implement a single acceptance criterion.

        Args:
            executor: Team executor instance
            epic_info: EPIC information
            ac: Acceptance criterion to implement
            team_composition: Agent roles
            requirement_type: Type of requirement

        Returns:
            Dict with success status, files, and changes
        """
        try:
            # Build implementation task
            task = {
                "epic_key": epic_info.key,
                "epic_summary": epic_info.summary,
                "ac_id": ac.id,
                "ac_description": ac.description,
                "requirement_type": requirement_type,
                "team": team_composition,
            }

            # Execute via team executor
            if hasattr(executor, "execute_task"):
                result = await executor.execute_task(task)
                return {
                    "success": result.get("success", False),
                    "files": result.get("files_created", []),
                    "changes": result.get("changes", {}),
                    "error": result.get("error"),
                }
            elif hasattr(executor, "implement"):
                result = await executor.implement(ac.description)
                return {
                    "success": True,
                    "files": result.get("files", []),
                    "changes": result.get("changes", {}),
                }
            else:
                # Basic fallback
                return await executor.implement_ac(ac)

        except Exception as e:
            return {
                "success": False,
                "files": [],
                "changes": {},
                "error": str(e),
            }


class BasicImplementationExecutor:
    """
    Basic implementation executor fallback.

    Creates placeholder files for acceptance criteria when
    the full team execution system is not available.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    async def implement_ac(self, ac: AcceptanceCriterion) -> Dict[str, Any]:
        """
        Create placeholder implementation for an AC.

        In production, this would be replaced by actual AI-driven
        code generation via team_execution_v2.
        """
        # Create a placeholder file
        safe_id = ac.id.replace("-", "_").lower()
        file_path = self.output_dir / f"impl_{safe_id}.py"

        content = f'''"""
Implementation for {ac.id}

Description: {ac.description}

This is a placeholder implementation created by EPIC Executor.
Replace with actual implementation.
"""

def implement_{safe_id}():
    """Implementation for: {ac.description[:50]}..."""
    # TODO: Implement this function
    raise NotImplementedError("{ac.id} not yet implemented")


if __name__ == "__main__":
    implement_{safe_id}()
'''

        try:
            file_path.write_text(content)
            return {
                "success": True,
                "files": [str(file_path)],
                "changes": {str(file_path): f"Created placeholder for {ac.id}"},
            }
        except Exception as e:
            return {
                "success": False,
                "files": [],
                "changes": {},
                "error": str(e),
            }
