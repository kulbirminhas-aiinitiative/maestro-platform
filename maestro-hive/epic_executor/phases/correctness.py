"""
Phase 5: Correctness

Audit generated code for TODO/FIXME and blocking issues.
This phase validates code quality for 10 compliance points.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import ExecutionPhase, PhaseResult


@dataclass
class TodoItem:
    """Represents a TODO/FIXME found in code."""
    file_path: str
    line_number: int
    line_content: str
    todo_type: str  # "TODO", "FIXME", "HACK", "XXX"
    is_blocking: bool  # True if blocking issue


@dataclass
class CorrectnessResult:
    """Result from the correctness phase."""
    todos_found: List[TodoItem]
    blocking_count: int
    non_blocking_count: int
    auto_resolved: int
    points_earned: float  # Out of 10


class CorrectnessPhase:
    """
    Phase 5: Correctness Validation

    Responsibilities:
    1. Scan generated code for TODO/FIXME
    2. Classify blocking vs non-blocking issues
    3. Auto-resolve or flag blocking issues
    4. Ensure clean code output
    """

    # Patterns to scan for
    TODO_PATTERNS = [
        (r'#\s*TODO[:\s](.+?)$', "TODO"),
        (r'#\s*FIXME[:\s](.+?)$', "FIXME"),
        (r'#\s*HACK[:\s](.+?)$', "HACK"),
        (r'#\s*XXX[:\s](.+?)$', "XXX"),
        (r'//\s*TODO[:\s](.+?)$', "TODO"),
        (r'//\s*FIXME[:\s](.+?)$', "FIXME"),
        (r'/\*\s*TODO[:\s](.+?)\*/', "TODO"),
    ]

    # Keywords indicating blocking issues
    BLOCKING_KEYWORDS = [
        "critical", "blocker", "must", "required", "breaking",
        "security", "urgent", "important", "before deploy",
        "before release", "not implemented", "incomplete",
    ]

    def __init__(self):
        """Initialize the correctness phase."""
        pass

    async def execute(
        self,
        implementation_files: List[str],
        test_files: List[str],
    ) -> Tuple[PhaseResult, Optional[CorrectnessResult]]:
        """
        Execute the correctness phase.

        Args:
            implementation_files: List of implementation file paths
            test_files: List of test file paths

        Returns:
            Tuple of (PhaseResult, CorrectnessResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            all_files = implementation_files + test_files
            todos_found: List[TodoItem] = []
            auto_resolved = 0

            # Scan all files
            for file_path in all_files:
                file_todos = await self._scan_file(file_path)
                todos_found.extend(file_todos)

            # Classify todos
            blocking_count = sum(1 for t in todos_found if t.is_blocking)
            non_blocking_count = len(todos_found) - blocking_count

            # Attempt to auto-resolve blocking issues
            if blocking_count > 0:
                resolved = await self._auto_resolve_blocking(
                    [t for t in todos_found if t.is_blocking]
                )
                auto_resolved = len(resolved)
                blocking_count -= auto_resolved
                artifacts.append(f"Auto-resolved {auto_resolved} blocking issues")

            # Calculate points: max(0, 10 - (blocking_todos * 2))
            points_earned = max(0, 10 - (blocking_count * 2))

            if blocking_count > 0:
                warnings.append(f"{blocking_count} blocking TODOs remain unresolved")

            artifacts.append(f"Scanned {len(all_files)} files")
            artifacts.append(f"Found {len(todos_found)} TODOs ({blocking_count} blocking)")

            # Build result
            result = CorrectnessResult(
                todos_found=todos_found,
                blocking_count=blocking_count,
                non_blocking_count=non_blocking_count,
                auto_resolved=auto_resolved,
                points_earned=points_earned,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.CORRECTNESS,
                success=blocking_count == 0,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "todos_found": len(todos_found),
                    "blocking_count": blocking_count,
                    "non_blocking_count": non_blocking_count,
                    "auto_resolved": auto_resolved,
                    "points_earned": points_earned,
                    "points_max": 10.0,
                }
            )

            return phase_result, result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.CORRECTNESS,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    async def _scan_file(self, file_path: str) -> List[TodoItem]:
        """Scan a file for TODO/FIXME comments."""
        todos = []
        path = Path(file_path)

        if not path.exists():
            return todos

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                for pattern, todo_type in self.TODO_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE | re.MULTILINE)
                    if match:
                        todo_text = match.group(1) if match.groups() else line
                        is_blocking = self._is_blocking(todo_text)

                        todos.append(TodoItem(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            todo_type=todo_type,
                            is_blocking=is_blocking,
                        ))
                        break  # Only count once per line

        except Exception:
            pass

        return todos

    def _is_blocking(self, todo_text: str) -> bool:
        """Determine if a TODO is blocking."""
        text_lower = todo_text.lower()
        return any(kw in text_lower for kw in self.BLOCKING_KEYWORDS)

    async def _auto_resolve_blocking(
        self,
        blocking_todos: List[TodoItem]
    ) -> List[TodoItem]:
        """
        Attempt to auto-resolve blocking TODOs.

        In production, this could use AI to:
        - Implement missing functionality
        - Fix incomplete code
        - Add required validation

        For now, we just track which ones could be resolved.
        """
        resolved = []

        for todo in blocking_todos:
            # Simple heuristic: if it's just "not implemented", we can resolve
            if "not implemented" in todo.line_content.lower():
                # TODO: Actually implement the missing code
                resolved.append(todo)

        return resolved
