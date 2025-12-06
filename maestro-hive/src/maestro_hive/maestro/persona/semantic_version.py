"""
Semantic Version Calculator

Implements AC-5: Semantic versioning (major.minor.patch) based on change impact.

Version bump rules:
- Major: Breaking changes to role, personality, core_traits
- Minor: New capabilities, tools additions
- Patch: Description, metadata changes

Epic: MD-2555
"""

from dataclasses import dataclass
from typing import Set, Tuple
from enum import Enum


class ChangeType(str, Enum):
    """Classification of field changes for semantic versioning"""
    BREAKING = "breaking"      # Major bump
    FEATURE = "feature"        # Minor bump
    FIX = "fix"               # Patch bump
    NO_CHANGE = "no_change"   # No bump


@dataclass
class SemanticVersion:
    """
    Semantic version representation.

    Format: major.minor.patch (e.g., 1.2.3)
    """
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"SemanticVersion({self})"

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """Parse version string like '1.2.3'"""
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_str}")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]),
            patch=int(parts[2])
        )

    @classmethod
    def initial(cls) -> "SemanticVersion":
        """Return initial version 0.1.0"""
        return cls(major=0, minor=1, patch=0)

    def bump_major(self) -> "SemanticVersion":
        """Increment major version, reset minor and patch"""
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        """Increment minor version, reset patch"""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        """Increment patch version"""
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def __lt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))


class SemanticVersionCalculator:
    """
    Calculates semantic version bumps based on persona field changes.

    AC-5 Implementation:
    - Major bump: role, personality, core_traits changes (breaking)
    - Minor bump: capabilities, tools additions (feature)
    - Patch bump: description, metadata changes (fix)
    """

    # Fields that trigger major version bumps (breaking changes)
    BREAKING_FIELDS: Set[str] = {"role", "personality", "core_traits", "name"}

    # Fields that trigger minor version bumps (new features)
    FEATURE_FIELDS: Set[str] = {"capabilities", "tools"}

    # Fields that trigger patch version bumps (fixes)
    PATCH_FIELDS: Set[str] = {"description", "metadata", "tags"}

    @classmethod
    def classify_field_change(cls, field_name: str) -> ChangeType:
        """
        Classify a field change by its semantic impact.

        Args:
            field_name: Name of the changed field

        Returns:
            ChangeType indicating the impact level
        """
        if field_name in cls.BREAKING_FIELDS:
            return ChangeType.BREAKING
        elif field_name in cls.FEATURE_FIELDS:
            return ChangeType.FEATURE
        elif field_name in cls.PATCH_FIELDS:
            return ChangeType.FIX
        else:
            # Unknown fields default to patch
            return ChangeType.FIX

    @classmethod
    def calculate_bump(
        cls,
        changed_fields: Set[str],
        current_version: SemanticVersion
    ) -> Tuple[SemanticVersion, ChangeType]:
        """
        Calculate new version based on changed fields.

        Uses highest-impact change to determine bump type.

        Args:
            changed_fields: Set of field names that changed
            current_version: Current semantic version

        Returns:
            Tuple of (new_version, change_type)
        """
        if not changed_fields:
            return current_version, ChangeType.NO_CHANGE

        # Find highest impact change type
        has_breaking = any(f in cls.BREAKING_FIELDS for f in changed_fields)
        has_feature = any(f in cls.FEATURE_FIELDS for f in changed_fields)

        if has_breaking:
            return current_version.bump_major(), ChangeType.BREAKING
        elif has_feature:
            return current_version.bump_minor(), ChangeType.FEATURE
        else:
            return current_version.bump_patch(), ChangeType.FIX

    @classmethod
    def get_change_description(cls, change_type: ChangeType) -> str:
        """Get human-readable description of change type"""
        descriptions = {
            ChangeType.BREAKING: "Breaking change - may affect dependent systems",
            ChangeType.FEATURE: "New feature or capability added",
            ChangeType.FIX: "Bug fix or minor improvement",
            ChangeType.NO_CHANGE: "No changes detected"
        }
        return descriptions.get(change_type, "Unknown change type")
