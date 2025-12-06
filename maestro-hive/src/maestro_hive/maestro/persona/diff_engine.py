"""
Persona Diff Engine

Implements AC-4: Diff between versions visualizable.

Provides detailed comparison between persona versions including:
- Field-level differences
- Added/removed/modified tracking
- Change categorization

Epic: MD-2555
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional
from enum import Enum

from .version import PersonaSnapshot, PersonaVersion


class DiffType(str, Enum):
    """Type of difference between values"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class FieldDiff:
    """
    Difference for a single field between versions.

    Represents what changed in a specific field.
    """
    field_name: str
    diff_type: DiffType
    old_value: Any = None
    new_value: Any = None
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "field_name": self.field_name,
            "diff_type": self.diff_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details
        }

    def is_change(self) -> bool:
        """Check if this represents an actual change"""
        return self.diff_type != DiffType.UNCHANGED


@dataclass
class DiffResult:
    """
    Complete diff result between two persona versions.

    Implements AC-4: Version diff visualization.
    """
    from_version_id: str
    to_version_id: str
    from_version_number: str
    to_version_number: str
    persona_id: str
    field_diffs: List[FieldDiff] = field(default_factory=list)
    summary: str = ""
    has_breaking_changes: bool = False
    changed_field_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "from_version_id": self.from_version_id,
            "to_version_id": self.to_version_id,
            "from_version_number": self.from_version_number,
            "to_version_number": self.to_version_number,
            "persona_id": self.persona_id,
            "field_diffs": [d.to_dict() for d in self.field_diffs],
            "summary": self.summary,
            "has_breaking_changes": self.has_breaking_changes,
            "changed_field_count": self.changed_field_count
        }

    @property
    def added_fields(self) -> List[FieldDiff]:
        """Get all added fields"""
        return [d for d in self.field_diffs if d.diff_type == DiffType.ADDED]

    @property
    def removed_fields(self) -> List[FieldDiff]:
        """Get all removed fields"""
        return [d for d in self.field_diffs if d.diff_type == DiffType.REMOVED]

    @property
    def modified_fields(self) -> List[FieldDiff]:
        """Get all modified fields"""
        return [d for d in self.field_diffs if d.diff_type == DiffType.MODIFIED]

    @property
    def changed_fields(self) -> Set[str]:
        """Get names of all changed fields"""
        return {d.field_name for d in self.field_diffs if d.is_change()}

    def format_summary(self) -> str:
        """Generate human-readable summary"""
        parts = []
        if self.added_fields:
            parts.append(f"{len(self.added_fields)} added")
        if self.removed_fields:
            parts.append(f"{len(self.removed_fields)} removed")
        if self.modified_fields:
            parts.append(f"{len(self.modified_fields)} modified")

        if not parts:
            return "No changes"
        return f"{', '.join(parts)} ({self.from_version_number} -> {self.to_version_number})"


class PersonaDiffEngine:
    """
    Engine for computing differences between persona versions.

    AC-4 Implementation: Provides detailed diff visualization.
    """

    # Fields considered breaking if changed
    BREAKING_FIELDS: Set[str] = {"role", "personality", "core_traits", "name"}

    @classmethod
    def diff_versions(
        cls,
        from_version: PersonaVersion,
        to_version: PersonaVersion
    ) -> DiffResult:
        """
        Compute diff between two persona versions.

        Args:
            from_version: Earlier version (base)
            to_version: Later version (target)

        Returns:
            DiffResult with detailed field-level differences
        """
        field_diffs = cls._diff_snapshots(from_version.snapshot, to_version.snapshot)

        # Check for breaking changes
        has_breaking = any(
            d.field_name in cls.BREAKING_FIELDS and d.is_change()
            for d in field_diffs
        )

        result = DiffResult(
            from_version_id=from_version.version_id,
            to_version_id=to_version.version_id,
            from_version_number=from_version.version_number,
            to_version_number=to_version.version_number,
            persona_id=from_version.persona_id,
            field_diffs=field_diffs,
            has_breaking_changes=has_breaking,
            changed_field_count=sum(1 for d in field_diffs if d.is_change())
        )
        result.summary = result.format_summary()
        return result

    @classmethod
    def _diff_snapshots(
        cls,
        old_snapshot: PersonaSnapshot,
        new_snapshot: PersonaSnapshot
    ) -> List[FieldDiff]:
        """Compute field-by-field diff between snapshots"""
        diffs = []
        old_dict = old_snapshot.to_dict()
        new_dict = new_snapshot.to_dict()

        # Get all field names
        all_fields = set(old_dict.keys()) | set(new_dict.keys())

        for field_name in sorted(all_fields):
            old_val = old_dict.get(field_name)
            new_val = new_dict.get(field_name)

            diff = cls._diff_field(field_name, old_val, new_val)
            diffs.append(diff)

        return diffs

    @classmethod
    def _diff_field(
        cls,
        field_name: str,
        old_value: Any,
        new_value: Any
    ) -> FieldDiff:
        """Compute diff for a single field"""
        # Handle None cases
        if old_value is None and new_value is not None:
            return FieldDiff(
                field_name=field_name,
                diff_type=DiffType.ADDED,
                old_value=None,
                new_value=new_value,
                details=f"Added field: {field_name}"
            )

        if old_value is not None and new_value is None:
            return FieldDiff(
                field_name=field_name,
                diff_type=DiffType.REMOVED,
                old_value=old_value,
                new_value=None,
                details=f"Removed field: {field_name}"
            )

        # Compare values
        if old_value == new_value:
            return FieldDiff(
                field_name=field_name,
                diff_type=DiffType.UNCHANGED,
                old_value=old_value,
                new_value=new_value
            )

        # Handle list comparisons with more detail
        details = cls._generate_diff_details(field_name, old_value, new_value)

        return FieldDiff(
            field_name=field_name,
            diff_type=DiffType.MODIFIED,
            old_value=old_value,
            new_value=new_value,
            details=details
        )

    @classmethod
    def _generate_diff_details(
        cls,
        field_name: str,
        old_value: Any,
        new_value: Any
    ) -> str:
        """Generate detailed diff description"""
        if isinstance(old_value, list) and isinstance(new_value, list):
            old_set = set(old_value) if all(isinstance(x, str) for x in old_value) else set()
            new_set = set(new_value) if all(isinstance(x, str) for x in new_value) else set()

            if old_set and new_set:
                added = new_set - old_set
                removed = old_set - new_set

                parts = []
                if added:
                    parts.append(f"+{list(added)}")
                if removed:
                    parts.append(f"-{list(removed)}")
                if parts:
                    return f"{field_name}: {' '.join(parts)}"

        if isinstance(old_value, str) and isinstance(new_value, str):
            if len(old_value) > 50 or len(new_value) > 50:
                return f"{field_name}: text content changed"
            return f"{field_name}: '{old_value}' -> '{new_value}'"

        return f"{field_name} modified"

    @classmethod
    def format_diff_report(cls, diff: DiffResult) -> str:
        """
        Generate a formatted diff report for visualization.

        Args:
            diff: DiffResult to format

        Returns:
            Human-readable diff report string
        """
        lines = [
            f"=== Persona Diff Report ===",
            f"Persona: {diff.persona_id}",
            f"From: {diff.from_version_number} ({diff.from_version_id})",
            f"To: {diff.to_version_number} ({diff.to_version_id})",
            f"",
            f"Summary: {diff.summary}",
            f"Breaking Changes: {'Yes' if diff.has_breaking_changes else 'No'}",
            f"",
            "--- Changes ---"
        ]

        for field_diff in diff.field_diffs:
            if not field_diff.is_change():
                continue

            symbol = {
                DiffType.ADDED: "+",
                DiffType.REMOVED: "-",
                DiffType.MODIFIED: "~"
            }.get(field_diff.diff_type, "?")

            lines.append(f"  {symbol} {field_diff.field_name}")
            if field_diff.details:
                lines.append(f"      {field_diff.details}")

        if diff.changed_field_count == 0:
            lines.append("  (no changes)")

        return "\n".join(lines)
