"""
Sync Conflict Detection and Resolution.

Handles conflicts when both Maestro and JIRA have changes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum


class ResolutionStrategy(Enum):
    """Conflict resolution strategies."""
    USE_MAESTRO = "use_maestro"  # Always use Maestro value
    USE_JIRA = "use_jira"  # Always use JIRA value
    USE_NEWER = "use_newer"  # Use most recently modified
    MERGE = "merge"  # Attempt to merge values
    MANUAL = "manual"  # Require manual resolution


@dataclass
class SyncConflict:
    """Detected sync conflict."""
    field_name: str
    maestro_value: Any
    jira_value: Any
    detected_at: datetime = field(default_factory=datetime.utcnow)
    workflow_id: Optional[str] = None
    jira_issue_key: Optional[str] = None
    maestro_modified_at: Optional[datetime] = None
    jira_modified_at: Optional[datetime] = None
    resolved: bool = False
    resolution: Optional["Resolution"] = None


@dataclass
class Resolution:
    """Conflict resolution decision."""
    conflict_id: str
    strategy: ResolutionStrategy
    resolved_value: Any
    resolved_by: str  # "auto" or user ID
    resolved_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""


@dataclass
class MergeResult:
    """Result of merge operation."""
    success: bool
    merged_value: Any
    requires_manual: bool = False
    merge_notes: str = ""


class ConflictResolver:
    """
    Conflict resolver for JIRA sync.

    Supports multiple resolution strategies including
    automatic resolution and manual intervention.
    """

    def __init__(
        self,
        default_strategy: ResolutionStrategy = ResolutionStrategy.USE_NEWER,
        field_strategies: Optional[Dict[str, ResolutionStrategy]] = None,
    ):
        """
        Initialize conflict resolver.

        Args:
            default_strategy: Default resolution strategy
            field_strategies: Per-field strategy overrides
        """
        self.default_strategy = default_strategy
        self.field_strategies = field_strategies or {}
        self._pending_conflicts: Dict[str, SyncConflict] = {}
        self._resolution_history: List[Resolution] = []
        self._merge_functions: Dict[str, Callable] = {}

    def register_merge_function(
        self,
        field_name: str,
        merge_fn: Callable[[Any, Any], MergeResult],
    ) -> None:
        """
        Register custom merge function for field.

        Args:
            field_name: Field to merge
            merge_fn: Function taking (maestro_val, jira_val) -> MergeResult
        """
        self._merge_functions[field_name] = merge_fn

    def get_strategy(self, field_name: str) -> ResolutionStrategy:
        """Get resolution strategy for field."""
        return self.field_strategies.get(field_name, self.default_strategy)

    async def resolve(
        self,
        conflict: SyncConflict,
        strategy: Optional[ResolutionStrategy] = None,
    ) -> Resolution:
        """
        Resolve a single conflict.

        Args:
            conflict: Conflict to resolve
            strategy: Override strategy

        Returns:
            Resolution decision
        """
        strategy = strategy or self.get_strategy(conflict.field_name)
        conflict_id = f"{conflict.workflow_id}:{conflict.field_name}"

        resolved_value = None
        resolved_by = "auto"

        if strategy == ResolutionStrategy.USE_MAESTRO:
            resolved_value = conflict.maestro_value

        elif strategy == ResolutionStrategy.USE_JIRA:
            resolved_value = conflict.jira_value

        elif strategy == ResolutionStrategy.USE_NEWER:
            # Use timestamp comparison
            if conflict.maestro_modified_at and conflict.jira_modified_at:
                if conflict.maestro_modified_at > conflict.jira_modified_at:
                    resolved_value = conflict.maestro_value
                else:
                    resolved_value = conflict.jira_value
            else:
                # Default to Maestro if timestamps unavailable
                resolved_value = conflict.maestro_value

        elif strategy == ResolutionStrategy.MERGE:
            merge_result = await self._merge_values(
                conflict.field_name,
                conflict.maestro_value,
                conflict.jira_value,
            )
            if merge_result.success:
                resolved_value = merge_result.merged_value
            else:
                # Fall back to manual resolution
                self._pending_conflicts[conflict_id] = conflict
                return Resolution(
                    conflict_id=conflict_id,
                    strategy=ResolutionStrategy.MANUAL,
                    resolved_value=None,
                    resolved_by="pending",
                    notes=merge_result.merge_notes,
                )

        elif strategy == ResolutionStrategy.MANUAL:
            self._pending_conflicts[conflict_id] = conflict
            return Resolution(
                conflict_id=conflict_id,
                strategy=ResolutionStrategy.MANUAL,
                resolved_value=None,
                resolved_by="pending",
                notes="Requires manual resolution",
            )

        resolution = Resolution(
            conflict_id=conflict_id,
            strategy=strategy,
            resolved_value=resolved_value,
            resolved_by=resolved_by,
        )

        conflict.resolved = True
        conflict.resolution = resolution
        self._resolution_history.append(resolution)

        return resolution

    async def resolve_all(
        self,
        conflicts: List[SyncConflict],
    ) -> Tuple[Dict[str, Any], List[SyncConflict]]:
        """
        Resolve all conflicts.

        Args:
            conflicts: List of conflicts

        Returns:
            Tuple of (resolved_data, unresolved_conflicts)
        """
        resolved_data = {}
        unresolved = []

        for conflict in conflicts:
            resolution = await self.resolve(conflict)

            if resolution.resolved_by == "pending":
                unresolved.append(conflict)
            else:
                resolved_data[conflict.field_name] = resolution.resolved_value

        return resolved_data, unresolved

    async def _merge_values(
        self,
        field_name: str,
        maestro_value: Any,
        jira_value: Any,
    ) -> MergeResult:
        """
        Attempt to merge two values.

        Args:
            field_name: Field being merged
            maestro_value: Value from Maestro
            jira_value: Value from JIRA

        Returns:
            MergeResult
        """
        # Check for custom merge function
        if field_name in self._merge_functions:
            return self._merge_functions[field_name](maestro_value, jira_value)

        # Default merge strategies by type
        if isinstance(maestro_value, str) and isinstance(jira_value, str):
            return self._merge_strings(maestro_value, jira_value)
        elif isinstance(maestro_value, list) and isinstance(jira_value, list):
            return self._merge_lists(maestro_value, jira_value)
        elif isinstance(maestro_value, dict) and isinstance(jira_value, dict):
            return self._merge_dicts(maestro_value, jira_value)

        # Cannot merge - require manual
        return MergeResult(
            success=False,
            merged_value=None,
            requires_manual=True,
            merge_notes="Cannot automatically merge values of different types",
        )

    def _merge_strings(self, s1: str, s2: str) -> MergeResult:
        """Merge two strings."""
        # Simple strategy: if one contains the other, use longer
        if s1 in s2:
            return MergeResult(success=True, merged_value=s2)
        if s2 in s1:
            return MergeResult(success=True, merged_value=s1)

        # Cannot auto-merge different strings
        return MergeResult(
            success=False,
            merged_value=None,
            requires_manual=True,
            merge_notes="Strings differ and cannot be auto-merged",
        )

    def _merge_lists(self, l1: List, l2: List) -> MergeResult:
        """Merge two lists."""
        # Union of both lists
        merged = list(set(l1) | set(l2))
        return MergeResult(
            success=True,
            merged_value=merged,
            merge_notes="Merged as union of both lists",
        )

    def _merge_dicts(self, d1: Dict, d2: Dict) -> MergeResult:
        """Merge two dictionaries."""
        merged = {**d1}

        for key, value in d2.items():
            if key not in merged:
                merged[key] = value
            elif merged[key] != value:
                # Conflict in nested value
                return MergeResult(
                    success=False,
                    merged_value=None,
                    requires_manual=True,
                    merge_notes=f"Conflict in nested field: {key}",
                )

        return MergeResult(success=True, merged_value=merged)

    def resolve_manually(
        self,
        conflict_id: str,
        resolved_value: Any,
        resolved_by: str,
        notes: str = "",
    ) -> Optional[Resolution]:
        """
        Manually resolve a pending conflict.

        Args:
            conflict_id: ID of pending conflict
            resolved_value: Chosen value
            resolved_by: User ID
            notes: Resolution notes

        Returns:
            Resolution if conflict was pending
        """
        conflict = self._pending_conflicts.pop(conflict_id, None)
        if not conflict:
            return None

        resolution = Resolution(
            conflict_id=conflict_id,
            strategy=ResolutionStrategy.MANUAL,
            resolved_value=resolved_value,
            resolved_by=resolved_by,
            notes=notes,
        )

        conflict.resolved = True
        conflict.resolution = resolution
        self._resolution_history.append(resolution)

        return resolution

    def get_pending_conflicts(self) -> List[SyncConflict]:
        """Get all pending conflicts requiring manual resolution."""
        return list(self._pending_conflicts.values())

    def get_resolution_history(
        self,
        limit: int = 100,
    ) -> List[Resolution]:
        """Get resolution history."""
        return sorted(
            self._resolution_history,
            key=lambda r: r.resolved_at,
            reverse=True,
        )[:limit]
