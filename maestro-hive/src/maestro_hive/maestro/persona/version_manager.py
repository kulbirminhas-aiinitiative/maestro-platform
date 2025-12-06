"""
Persona Version Manager

Central coordinator for persona version control operations.
Implements all acceptance criteria:
- AC-1: Each persona change creates a new version
- AC-2: Version history queryable (who changed, when, what)
- AC-3: Rollback to previous version supported
- AC-4: Diff between versions visualizable
- AC-5: Semantic versioning (major.minor.patch) based on change impact

Epic: MD-2555
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
import logging

from .version import PersonaVersion, PersonaSnapshot, VersionChange
from .version_store import PersonaVersionStore, JSONVersionStore
from .diff_engine import PersonaDiffEngine, DiffResult
from .semantic_version import SemanticVersionCalculator, SemanticVersion, ChangeType

logger = logging.getLogger(__name__)


@dataclass
class VersionCreateResult:
    """Result of version creation operation"""
    success: bool
    version: Optional[PersonaVersion]
    previous_version: Optional[PersonaVersion]
    change_type: ChangeType
    changed_fields: Set[str]
    error: Optional[str] = None


@dataclass
class RollbackResult:
    """Result of rollback operation (AC-3)"""
    success: bool
    rolled_back_to: Optional[PersonaVersion]
    new_version: Optional[PersonaVersion]
    error: Optional[str] = None


class PersonaVersionManager:
    """
    Central manager for persona version control.

    Provides high-level operations for:
    - Creating versions with automatic semantic versioning (AC-1, AC-5)
    - Querying version history (AC-2)
    - Rolling back to previous versions (AC-3)
    - Computing diffs between versions (AC-4)
    """

    def __init__(
        self,
        store: Optional[PersonaVersionStore] = None,
        version_dir: str = "/tmp/maestro/persona_versions"
    ):
        """
        Initialize the version manager.

        Args:
            store: Optional custom version store
            version_dir: Directory for JSON store if no custom store provided
        """
        self.store = store or JSONVersionStore(version_dir=version_dir)
        self.diff_engine = PersonaDiffEngine()
        self.version_calculator = SemanticVersionCalculator()

    def create_version(
        self,
        snapshot: PersonaSnapshot,
        change_summary: str,
        author: str,
        force_change_type: Optional[VersionChange] = None
    ) -> VersionCreateResult:
        """
        Create a new version for a persona.

        AC-1: Each persona change creates a new version.
        AC-5: Semantic versioning based on change impact.

        Args:
            snapshot: The new persona state snapshot
            change_summary: Description of what changed
            author: Who made the change
            force_change_type: Optional override for change type

        Returns:
            VersionCreateResult with success status and version details
        """
        try:
            persona_id = snapshot.persona_id

            # Get current latest version
            latest = self.store.get_latest_version(persona_id)

            if latest is None:
                # First version
                new_version = PersonaVersion(
                    version_id=PersonaVersion.generate_version_id(),
                    persona_id=persona_id,
                    version_number=str(SemanticVersion.initial()),
                    snapshot=snapshot,
                    change_summary=change_summary,
                    change_type=force_change_type or VersionChange.MINOR,
                    author=author,
                    timestamp=datetime.utcnow(),
                    parent_version_id=None
                )

                self.store.save_version(new_version)

                return VersionCreateResult(
                    success=True,
                    version=new_version,
                    previous_version=None,
                    change_type=ChangeType.FEATURE,
                    changed_fields=set()
                )

            # Compute diff to detect changed fields
            temp_version = PersonaVersion(
                version_id="temp",
                persona_id=persona_id,
                version_number="0.0.0",
                snapshot=snapshot,
                change_summary="",
                change_type=VersionChange.PATCH,
                author=author,
                timestamp=datetime.utcnow()
            )

            diff = self.diff_engine.diff_versions(latest, temp_version)
            changed_fields = diff.changed_fields

            # Check if there are actually changes
            if not changed_fields:
                return VersionCreateResult(
                    success=False,
                    version=None,
                    previous_version=latest,
                    change_type=ChangeType.NO_CHANGE,
                    changed_fields=set(),
                    error="No changes detected"
                )

            # Calculate new version number
            current_semver = SemanticVersion.parse(latest.version_number)
            new_semver, change_type = self.version_calculator.calculate_bump(
                changed_fields, current_semver
            )

            # Determine version change type
            if force_change_type:
                version_change = force_change_type
            elif change_type == ChangeType.BREAKING:
                version_change = VersionChange.MAJOR
            elif change_type == ChangeType.FEATURE:
                version_change = VersionChange.MINOR
            else:
                version_change = VersionChange.PATCH

            # Create new version
            new_version = PersonaVersion(
                version_id=PersonaVersion.generate_version_id(),
                persona_id=persona_id,
                version_number=str(new_semver),
                snapshot=snapshot,
                change_summary=change_summary,
                change_type=version_change,
                author=author,
                timestamp=datetime.utcnow(),
                parent_version_id=latest.version_id
            )

            self.store.save_version(new_version)

            logger.info(
                f"Created persona version {new_version.version_number} "
                f"for {persona_id} (type: {version_change.value})"
            )

            return VersionCreateResult(
                success=True,
                version=new_version,
                previous_version=latest,
                change_type=change_type,
                changed_fields=changed_fields
            )

        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            return VersionCreateResult(
                success=False,
                version=None,
                previous_version=None,
                change_type=ChangeType.NO_CHANGE,
                changed_fields=set(),
                error=str(e)
            )

    def get_history(
        self,
        persona_id: str,
        limit: int = 100
    ) -> List[PersonaVersion]:
        """
        Get version history for a persona.

        AC-2: Version history queryable (who changed, when, what).

        Args:
            persona_id: The persona identifier
            limit: Maximum versions to return

        Returns:
            List of PersonaVersions, most recent first
        """
        return self.store.get_history(persona_id, limit)

    def get_version(
        self,
        persona_id: str,
        version_id: str
    ) -> Optional[PersonaVersion]:
        """
        Get a specific version by ID.

        Args:
            persona_id: The persona identifier
            version_id: The version identifier

        Returns:
            PersonaVersion if found, None otherwise
        """
        return self.store.get_version(persona_id, version_id)

    def get_latest(self, persona_id: str) -> Optional[PersonaVersion]:
        """
        Get the latest version of a persona.

        Args:
            persona_id: The persona identifier

        Returns:
            Latest PersonaVersion if any exist
        """
        return self.store.get_latest_version(persona_id)

    def rollback(
        self,
        persona_id: str,
        target_version_id: str,
        author: str,
        reason: str = "Rollback to previous version"
    ) -> RollbackResult:
        """
        Rollback persona to a previous version.

        AC-3: Rollback to previous version supported.

        This creates a new version based on the target version's snapshot,
        maintaining the version history integrity.

        Args:
            persona_id: The persona identifier
            target_version_id: Version ID to rollback to
            author: Who is performing the rollback
            reason: Reason for the rollback

        Returns:
            RollbackResult with success status and version details
        """
        try:
            # Get target version
            target_version = self.store.get_version(persona_id, target_version_id)
            if not target_version:
                return RollbackResult(
                    success=False,
                    rolled_back_to=None,
                    new_version=None,
                    error=f"Version {target_version_id} not found"
                )

            # Create new version with target's snapshot
            change_summary = (
                f"Rollback to version {target_version.version_number}: {reason}"
            )

            result = self.create_version(
                snapshot=target_version.snapshot,
                change_summary=change_summary,
                author=author,
                force_change_type=VersionChange.PATCH
            )

            if not result.success:
                return RollbackResult(
                    success=False,
                    rolled_back_to=target_version,
                    new_version=None,
                    error=result.error
                )

            logger.info(
                f"Rolled back persona {persona_id} to version "
                f"{target_version.version_number}"
            )

            return RollbackResult(
                success=True,
                rolled_back_to=target_version,
                new_version=result.version
            )

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return RollbackResult(
                success=False,
                rolled_back_to=None,
                new_version=None,
                error=str(e)
            )

    def diff(
        self,
        persona_id: str,
        from_version_id: str,
        to_version_id: str
    ) -> Optional[DiffResult]:
        """
        Compute diff between two versions.

        AC-4: Diff between versions visualizable.

        Args:
            persona_id: The persona identifier
            from_version_id: Earlier version ID
            to_version_id: Later version ID

        Returns:
            DiffResult if both versions found, None otherwise
        """
        from_version = self.store.get_version(persona_id, from_version_id)
        to_version = self.store.get_version(persona_id, to_version_id)

        if not from_version or not to_version:
            return None

        return self.diff_engine.diff_versions(from_version, to_version)

    def diff_with_latest(
        self,
        persona_id: str,
        from_version_id: str
    ) -> Optional[DiffResult]:
        """
        Compute diff between a version and the latest.

        Args:
            persona_id: The persona identifier
            from_version_id: Version to compare from

        Returns:
            DiffResult if both versions found
        """
        from_version = self.store.get_version(persona_id, from_version_id)
        latest = self.store.get_latest_version(persona_id)

        if not from_version or not latest:
            return None

        return self.diff_engine.diff_versions(from_version, latest)

    def format_diff_report(
        self,
        persona_id: str,
        from_version_id: str,
        to_version_id: str
    ) -> str:
        """
        Generate formatted diff report.

        AC-4: Visualization support.

        Args:
            persona_id: The persona identifier
            from_version_id: Earlier version ID
            to_version_id: Later version ID

        Returns:
            Formatted diff report string
        """
        diff = self.diff(persona_id, from_version_id, to_version_id)
        if not diff:
            return "Unable to compute diff - one or both versions not found"

        return self.diff_engine.format_diff_report(diff)

    def get_version_by_number(
        self,
        persona_id: str,
        version_number: str
    ) -> Optional[PersonaVersion]:
        """
        Get a version by its semantic version number.

        Args:
            persona_id: The persona identifier
            version_number: Semantic version (e.g., "1.2.3")

        Returns:
            PersonaVersion if found
        """
        return self.store.get_version_by_number(persona_id, version_number)

    def list_personas(self) -> List[str]:
        """List all persona IDs with version history"""
        return self.store.list_personas()

    def get_breaking_changes(
        self,
        persona_id: str,
        since_version_id: Optional[str] = None
    ) -> List[PersonaVersion]:
        """
        Get all breaking change versions.

        Args:
            persona_id: The persona identifier
            since_version_id: Only get breaking changes after this version

        Returns:
            List of versions with breaking changes
        """
        history = self.get_history(persona_id)
        breaking = [v for v in history if v.change_type == VersionChange.MAJOR]

        if since_version_id:
            # Filter to only versions after the specified one
            found_marker = False
            filtered = []
            for v in breaking:
                if v.version_id == since_version_id:
                    found_marker = True
                    continue
                if not found_marker:
                    filtered.append(v)
            return filtered

        return breaking
