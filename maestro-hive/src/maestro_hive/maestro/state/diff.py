"""
State Diff - Compare and merge workflow states

EPIC: MD-2514 - AC-4: State diff and merge for concurrent workflow branches

Provides:
- Deep comparison of workflow states
- Three-way merge for concurrent branches
- Conflict detection and resolution
- Diff visualization helpers
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .checkpoint import WorkflowState

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """Strategy for resolving conflicts."""
    KEEP_LEFT = "keep_left"
    KEEP_RIGHT = "keep_right"
    KEEP_BOTH = "keep_both"
    MERGE = "merge"
    CUSTOM = "custom"


class DiffOperation(Enum):
    """Type of difference operation."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class DiffEntry:
    """
    Single difference entry between two states.

    Attributes:
        path: Path to the changed value (e.g., "data.config.timeout")
        operation: Type of change
        old_value: Value in left/base state
        new_value: Value in right/new state
    """
    path: str
    operation: DiffOperation
    old_value: Any = None
    new_value: Any = None

    def __str__(self) -> str:
        if self.operation == DiffOperation.ADDED:
            return f"+ {self.path}: {self.new_value}"
        elif self.operation == DiffOperation.REMOVED:
            return f"- {self.path}: {self.old_value}"
        elif self.operation == DiffOperation.MODIFIED:
            return f"~ {self.path}: {self.old_value} -> {self.new_value}"
        else:
            return f"= {self.path}"


@dataclass
class Conflict:
    """
    Conflict during merge operation.

    Attributes:
        path: Path to conflicting value
        base_value: Value in base state
        left_value: Value in left branch
        right_value: Value in right branch
        resolved: Whether conflict has been resolved
        resolution: How conflict was resolved
        resolved_value: Final resolved value
    """
    path: str
    base_value: Any
    left_value: Any
    right_value: Any
    resolved: bool = False
    resolution: Optional[ConflictResolution] = None
    resolved_value: Any = None


@dataclass
class StateDiffResult:
    """
    Result of comparing two workflow states.

    Attributes:
        entries: List of differences
        added_count: Number of added fields
        removed_count: Number of removed fields
        modified_count: Number of modified fields
        unchanged_count: Number of unchanged fields
    """
    entries: List[DiffEntry] = field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return (
            self.added_count > 0 or
            self.removed_count > 0 or
            self.modified_count > 0
        )

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return self.added_count + self.removed_count + self.modified_count

    def format(self, show_unchanged: bool = False) -> str:
        """Format diff as human-readable string."""
        lines = []
        for entry in self.entries:
            if entry.operation != DiffOperation.UNCHANGED or show_unchanged:
                lines.append(str(entry))
        return "\n".join(lines)


@dataclass
class MergeResult:
    """
    Result of merging workflow states.

    Attributes:
        success: Whether merge succeeded without conflicts
        merged_state: The merged workflow state
        conflicts: List of conflicts (if any)
        resolved_conflicts: Number of auto-resolved conflicts
        unresolved_conflicts: Number of unresolved conflicts
    """
    success: bool
    merged_state: Optional[WorkflowState]
    conflicts: List[Conflict] = field(default_factory=list)
    resolved_conflicts: int = 0
    unresolved_conflicts: int = 0


class StateDiff:
    """
    Compares and merges workflow states.

    Features:
    - Deep recursive comparison
    - Three-way merge (base + two branches)
    - Configurable conflict resolution
    - Path-based conflict handlers
    """

    def __init__(
        self,
        conflict_resolver: Optional[Callable[[Conflict], Any]] = None,
    ):
        """
        Initialize state diff.

        Args:
            conflict_resolver: Default conflict resolver function
        """
        self._conflict_resolver = conflict_resolver
        self._path_resolvers: Dict[str, Callable[[Conflict], Any]] = {}

    def register_path_resolver(
        self,
        path_pattern: str,
        resolver: Callable[[Conflict], Any],
    ) -> None:
        """
        Register a conflict resolver for specific paths.

        Args:
            path_pattern: Path pattern (supports * for wildcard)
            resolver: Resolver function
        """
        self._path_resolvers[path_pattern] = resolver

    def _get_value_at_path(
        self,
        obj: Dict[str, Any],
        path: str,
    ) -> Tuple[bool, Any]:
        """
        Get value at path in nested dict.

        Returns:
            Tuple of (exists, value)
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False, None

        return True, current

    def _set_value_at_path(
        self,
        obj: Dict[str, Any],
        path: str,
        value: Any,
    ) -> None:
        """Set value at path in nested dict."""
        parts = path.split(".")
        current = obj

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _delete_at_path(
        self,
        obj: Dict[str, Any],
        path: str,
    ) -> bool:
        """Delete value at path. Returns True if deleted."""
        parts = path.split(".")
        current = obj

        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            return True
        return False

    def _compare_values(
        self,
        left: Any,
        right: Any,
        path: str,
        entries: List[DiffEntry],
    ) -> None:
        """Recursively compare two values."""
        if left == right:
            entries.append(DiffEntry(
                path=path,
                operation=DiffOperation.UNCHANGED,
                old_value=left,
                new_value=right,
            ))
            return

        if isinstance(left, dict) and isinstance(right, dict):
            # Compare nested dicts
            all_keys = set(left.keys()) | set(right.keys())

            for key in sorted(all_keys):
                sub_path = f"{path}.{key}" if path else key

                if key not in left:
                    entries.append(DiffEntry(
                        path=sub_path,
                        operation=DiffOperation.ADDED,
                        new_value=right[key],
                    ))
                elif key not in right:
                    entries.append(DiffEntry(
                        path=sub_path,
                        operation=DiffOperation.REMOVED,
                        old_value=left[key],
                    ))
                else:
                    self._compare_values(
                        left[key],
                        right[key],
                        sub_path,
                        entries,
                    )
        else:
            # Values are different types or primitives
            entries.append(DiffEntry(
                path=path,
                operation=DiffOperation.MODIFIED,
                old_value=left,
                new_value=right,
            ))

    def diff(
        self,
        state_a: WorkflowState,
        state_b: WorkflowState,
    ) -> StateDiffResult:
        """
        Compare two workflow states.

        Args:
            state_a: Left/base state
            state_b: Right/new state

        Returns:
            StateDiffResult with all differences
        """
        entries: List[DiffEntry] = []

        # Compare data dicts
        self._compare_values(
            state_a.data,
            state_b.data,
            "",
            entries,
        )

        # Count operations
        added = sum(1 for e in entries if e.operation == DiffOperation.ADDED)
        removed = sum(1 for e in entries if e.operation == DiffOperation.REMOVED)
        modified = sum(1 for e in entries if e.operation == DiffOperation.MODIFIED)
        unchanged = sum(1 for e in entries if e.operation == DiffOperation.UNCHANGED)

        return StateDiffResult(
            entries=entries,
            added_count=added,
            removed_count=removed,
            modified_count=modified,
            unchanged_count=unchanged,
        )

    def _find_resolver(self, path: str) -> Optional[Callable[[Conflict], Any]]:
        """Find resolver for a path."""
        # Exact match
        if path in self._path_resolvers:
            return self._path_resolvers[path]

        # Wildcard match
        for pattern, resolver in self._path_resolvers.items():
            if "*" in pattern:
                parts = pattern.split("*")
                if len(parts) == 2:
                    prefix, suffix = parts
                    if path.startswith(prefix) and path.endswith(suffix):
                        return resolver

        return self._conflict_resolver

    def _detect_conflicts(
        self,
        base: Dict[str, Any],
        left: Dict[str, Any],
        right: Dict[str, Any],
        path: str,
        conflicts: List[Conflict],
    ) -> None:
        """Detect conflicts between three versions."""
        # Get all keys
        base_keys = set(base.keys()) if isinstance(base, dict) else set()
        left_keys = set(left.keys()) if isinstance(left, dict) else set()
        right_keys = set(right.keys()) if isinstance(right, dict) else set()
        all_keys = base_keys | left_keys | right_keys

        for key in all_keys:
            sub_path = f"{path}.{key}" if path else key

            in_base = key in base_keys
            in_left = key in left_keys
            in_right = key in right_keys

            base_val = base.get(key) if in_base else None
            left_val = left.get(key) if in_left else None
            right_val = right.get(key) if in_right else None

            # Check if values are dicts for recursion
            if (
                isinstance(base_val, dict) or
                isinstance(left_val, dict) or
                isinstance(right_val, dict)
            ):
                self._detect_conflicts(
                    base_val or {},
                    left_val or {},
                    right_val or {},
                    sub_path,
                    conflicts,
                )
                continue

            # Check for conflict
            left_changed = left_val != base_val
            right_changed = right_val != base_val
            both_changed = left_changed and right_changed
            different = left_val != right_val

            if both_changed and different:
                conflicts.append(Conflict(
                    path=sub_path,
                    base_value=base_val,
                    left_value=left_val,
                    right_value=right_val,
                ))

    def merge(
        self,
        base: WorkflowState,
        state_a: WorkflowState,
        state_b: WorkflowState,
        conflict_resolver: Optional[Callable[[Conflict], Any]] = None,
    ) -> MergeResult:
        """
        Three-way merge of workflow states.

        Args:
            base: Common ancestor state
            state_a: First branch state
            state_b: Second branch state
            conflict_resolver: Optional resolver override

        Returns:
            MergeResult with merged state and conflicts
        """
        # Detect conflicts
        conflicts: List[Conflict] = []
        self._detect_conflicts(
            base.data,
            state_a.data,
            state_b.data,
            "",
            conflicts,
        )

        # Start with copy of state_a data
        merged_data = self._deep_copy(state_a.data)

        # Apply non-conflicting changes from state_b
        diff_base_b = self.diff(base, state_b)

        for entry in diff_base_b.entries:
            # Skip if this path has a conflict
            if any(c.path == entry.path for c in conflicts):
                continue

            if entry.operation == DiffOperation.ADDED:
                self._set_value_at_path(merged_data, entry.path, entry.new_value)
            elif entry.operation == DiffOperation.REMOVED:
                self._delete_at_path(merged_data, entry.path)
            elif entry.operation == DiffOperation.MODIFIED:
                # Check if left also modified (would be conflict)
                exists, left_val = self._get_value_at_path(state_a.data, entry.path)
                _, base_val = self._get_value_at_path(base.data, entry.path)

                if not exists or left_val == base_val:
                    # Only right changed, apply
                    self._set_value_at_path(merged_data, entry.path, entry.new_value)

        # Resolve conflicts
        resolved_count = 0
        unresolved_count = 0
        resolver = conflict_resolver or self._conflict_resolver

        for conflict in conflicts:
            path_resolver = self._find_resolver(conflict.path)
            effective_resolver = path_resolver or resolver

            if effective_resolver:
                try:
                    resolved_value = effective_resolver(conflict)
                    conflict.resolved = True
                    conflict.resolved_value = resolved_value
                    self._set_value_at_path(merged_data, conflict.path, resolved_value)
                    resolved_count += 1
                except Exception as e:
                    logger.warning(f"Conflict resolver failed for {conflict.path}: {e}")
                    unresolved_count += 1
            else:
                unresolved_count += 1

        # Create merged state
        merged_state = WorkflowState(
            workflow_id=state_a.workflow_id,
            phase=state_a.phase if state_a.phase == state_b.phase else f"{state_a.phase}/{state_b.phase}",
            step=max(state_a.step, state_b.step),
            data=merged_data,
            metadata=state_a.metadata,
        )

        return MergeResult(
            success=unresolved_count == 0,
            merged_state=merged_state,
            conflicts=conflicts,
            resolved_conflicts=resolved_count,
            unresolved_conflicts=unresolved_count,
        )

    def _deep_copy(self, obj: Any) -> Any:
        """Create deep copy of object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        elif isinstance(obj, set):
            return {self._deep_copy(item) for item in obj}
        else:
            return obj

    @staticmethod
    def create_resolver(strategy: ConflictResolution) -> Callable[[Conflict], Any]:
        """
        Create a resolver function for a given strategy.

        Args:
            strategy: Conflict resolution strategy

        Returns:
            Resolver function
        """
        if strategy == ConflictResolution.KEEP_LEFT:
            return lambda c: c.left_value
        elif strategy == ConflictResolution.KEEP_RIGHT:
            return lambda c: c.right_value
        elif strategy == ConflictResolution.KEEP_BOTH:
            return lambda c: {"left": c.left_value, "right": c.right_value}
        elif strategy == ConflictResolution.MERGE:
            def merge_resolver(c: Conflict) -> Any:
                if isinstance(c.left_value, list) and isinstance(c.right_value, list):
                    return list(set(c.left_value + c.right_value))
                elif isinstance(c.left_value, dict) and isinstance(c.right_value, dict):
                    return {**c.left_value, **c.right_value}
                else:
                    return c.right_value  # Default to right
            return merge_resolver
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
