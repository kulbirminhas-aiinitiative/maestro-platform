"""
Persona Version Control Tests

Comprehensive test suite for MD-2555: Persona Version Control.

Tests all acceptance criteria:
- AC-1: Each persona change creates a new version
- AC-2: Version history queryable (who changed, when, what)
- AC-3: Rollback to previous version supported
- AC-4: Diff between versions visualizable
- AC-5: Semantic versioning (major.minor.patch) based on change impact

Epic: MD-2555
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from maestro_hive.maestro.persona.version import (
    PersonaVersion, PersonaSnapshot, VersionChange
)
from maestro_hive.maestro.persona.semantic_version import (
    SemanticVersion, SemanticVersionCalculator, ChangeType
)
from maestro_hive.maestro.persona.version_store import JSONVersionStore
from maestro_hive.maestro.persona.version_manager import PersonaVersionManager
from maestro_hive.maestro.persona.diff_engine import (
    PersonaDiffEngine, DiffResult, DiffType
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_version_dir():
    """Create temporary directory for version storage"""
    temp_dir = tempfile.mkdtemp(prefix="persona_version_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def version_store(temp_version_dir):
    """Create a JSON version store"""
    return JSONVersionStore(version_dir=temp_version_dir)


@pytest.fixture
def version_manager(temp_version_dir):
    """Create a version manager with temporary storage"""
    return PersonaVersionManager(version_dir=temp_version_dir)


@pytest.fixture
def sample_snapshot():
    """Create a sample persona snapshot"""
    return PersonaSnapshot(
        persona_id="test-persona-001",
        name="Test Analyst",
        role="Requirements Analyst",
        personality="Analytical and detail-oriented",
        core_traits=["thorough", "analytical", "precise"],
        capabilities=["requirements_analysis", "documentation"],
        tools=["jira", "confluence"],
        description="A test persona for unit testing",
        metadata={"created_by": "test"}
    )


@pytest.fixture
def sample_version(sample_snapshot):
    """Create a sample persona version"""
    return PersonaVersion(
        version_id=PersonaVersion.generate_version_id(),
        persona_id=sample_snapshot.persona_id,
        version_number="0.1.0",
        snapshot=sample_snapshot,
        change_summary="Initial version",
        change_type=VersionChange.MINOR,
        author="test_author",
        timestamp=datetime.utcnow()
    )


# =============================================================================
# AC-1: Each persona change creates a new version
# =============================================================================

class TestAC1_VersionCreation:
    """Tests for AC-1: Each persona change creates a new version"""

    def test_create_initial_version(self, version_manager, sample_snapshot):
        """First version creation should succeed"""
        result = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial creation",
            author="test_user"
        )

        assert result.success
        assert result.version is not None
        assert result.version.version_number == "0.1.0"
        assert result.previous_version is None

    def test_create_second_version_with_change(self, version_manager, sample_snapshot):
        """Modification should create a new version"""
        # Create initial version
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user1"
        )

        # Modify snapshot
        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities + ["new_capability"],
            tools=sample_snapshot.tools,
            description="Updated description",
            metadata=sample_snapshot.metadata
        )

        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Added new capability",
            author="user2"
        )

        assert result.success
        assert result.version is not None
        assert result.version.version_number != "0.1.0"
        assert result.previous_version is not None

    def test_no_version_without_changes(self, version_manager, sample_snapshot):
        """Identical snapshot should not create new version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user1"
        )

        # Try to create with same snapshot
        result = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="No actual change",
            author="user2"
        )

        assert not result.success
        assert result.change_type == ChangeType.NO_CHANGE
        assert "No changes" in result.error

    def test_version_id_uniqueness(self, version_manager, sample_snapshot):
        """Each version should have unique ID"""
        ids = set()
        for i in range(5):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"Version {i}",
                metadata=sample_snapshot.metadata
            )
            result = version_manager.create_version(
                snapshot=modified,
                change_summary=f"Version {i}",
                author="user"
            )
            if result.success:
                ids.add(result.version.version_id)

        assert len(ids) == 5

    def test_version_has_content_hash(self, sample_version):
        """Version should have content hash"""
        assert sample_version.content_hash
        assert len(sample_version.content_hash) == 16


# =============================================================================
# AC-2: Version history queryable (who changed, when, what)
# =============================================================================

class TestAC2_VersionHistory:
    """Tests for AC-2: Version history queryable"""

    def test_get_history_returns_all_versions(self, version_manager, sample_snapshot):
        """History should return all versions for persona"""
        # Create multiple versions
        for i in range(5):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"Version {i}",
                metadata=sample_snapshot.metadata
            )
            version_manager.create_version(
                snapshot=modified,
                change_summary=f"Version {i}",
                author=f"author_{i}"
            )

        history = version_manager.get_history(sample_snapshot.persona_id)
        assert len(history) == 5

    def test_history_ordered_by_timestamp(self, version_manager, sample_snapshot):
        """History should be ordered most recent first"""
        for i in range(3):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"Version {i}",
                metadata=sample_snapshot.metadata
            )
            version_manager.create_version(
                snapshot=modified,
                change_summary=f"Version {i}",
                author="user"
            )

        history = version_manager.get_history(sample_snapshot.persona_id)

        for i in range(len(history) - 1):
            assert history[i].timestamp >= history[i + 1].timestamp

    def test_history_includes_author(self, version_manager, sample_snapshot):
        """History should track who made changes"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="alice"
        )

        history = version_manager.get_history(sample_snapshot.persona_id)
        assert history[0].author == "alice"

    def test_history_includes_timestamp(self, version_manager, sample_snapshot):
        """History should track when changes were made"""
        before = datetime.utcnow()
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )
        after = datetime.utcnow()

        history = version_manager.get_history(sample_snapshot.persona_id)
        assert before <= history[0].timestamp <= after

    def test_history_includes_change_summary(self, version_manager, sample_snapshot):
        """History should track what changed"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Added new analysis capability",
            author="user"
        )

        history = version_manager.get_history(sample_snapshot.persona_id)
        assert "analysis capability" in history[0].change_summary

    def test_history_limit_parameter(self, version_manager, sample_snapshot):
        """History should respect limit parameter"""
        for i in range(10):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"Version {i}",
                metadata=sample_snapshot.metadata
            )
            version_manager.create_version(
                snapshot=modified,
                change_summary=f"Version {i}",
                author="user"
            )

        history = version_manager.get_history(sample_snapshot.persona_id, limit=5)
        assert len(history) == 5

    def test_get_version_by_id(self, version_manager, sample_snapshot):
        """Should retrieve specific version by ID"""
        result = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        retrieved = version_manager.get_version(
            sample_snapshot.persona_id,
            result.version.version_id
        )

        assert retrieved is not None
        assert retrieved.version_id == result.version.version_id

    def test_get_latest_version(self, version_manager, sample_snapshot):
        """Should return most recent version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="First",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=["updated"],
            tools=sample_snapshot.tools,
            description="Updated",
            metadata=sample_snapshot.metadata
        )
        version_manager.create_version(
            snapshot=modified,
            change_summary="Second",
            author="user"
        )

        latest = version_manager.get_latest(sample_snapshot.persona_id)
        assert latest is not None
        assert "Second" in latest.change_summary


# =============================================================================
# AC-3: Rollback to previous version supported
# =============================================================================

class TestAC3_Rollback:
    """Tests for AC-3: Rollback to previous version supported"""

    def test_rollback_to_previous_version(self, version_manager, sample_snapshot):
        """Rollback should restore previous snapshot"""
        # Create initial version
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        # Create modified version
        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name="Changed Name",
            role="Changed Role",
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        version_manager.create_version(
            snapshot=modified,
            change_summary="Breaking change",
            author="user"
        )

        # Rollback
        rollback_result = version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id=result1.version.version_id,
            author="admin",
            reason="Reverting breaking change"
        )

        assert rollback_result.success
        assert rollback_result.rolled_back_to is not None
        assert rollback_result.new_version is not None

        # Verify latest matches original
        latest = version_manager.get_latest(sample_snapshot.persona_id)
        assert latest.snapshot.name == sample_snapshot.name
        assert latest.snapshot.role == sample_snapshot.role

    def test_rollback_creates_new_version(self, version_manager, sample_snapshot):
        """Rollback should create new version, not delete history"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name="Changed",
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        version_manager.create_version(
            snapshot=modified,
            change_summary="Change",
            author="user"
        )

        version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id=result1.version.version_id,
            author="admin",
            reason="Rollback"
        )

        history = version_manager.get_history(sample_snapshot.persona_id)
        assert len(history) == 3  # Initial + change + rollback

    def test_rollback_preserves_history(self, version_manager, sample_snapshot):
        """Rollback should preserve full version history"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="V1",
            author="user"
        )

        for i in range(2, 5):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"V{i}",
                metadata=sample_snapshot.metadata
            )
            version_manager.create_version(
                snapshot=modified,
                change_summary=f"V{i}",
                author="user"
            )

        history_before = version_manager.get_history(sample_snapshot.persona_id)
        rollback_target = history_before[2]  # V2

        version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id=rollback_target.version_id,
            author="admin",
            reason="Rollback to V2"
        )

        history_after = version_manager.get_history(sample_snapshot.persona_id)
        # All original versions should still exist
        assert len(history_after) == len(history_before) + 1

    def test_rollback_to_nonexistent_version(self, version_manager, sample_snapshot):
        """Rollback to invalid version should fail gracefully"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        result = version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id="nonexistent-id",
            author="admin",
            reason="Bad rollback"
        )

        assert not result.success
        assert "not found" in result.error

    def test_rollback_includes_reason(self, version_manager, sample_snapshot):
        """Rollback version should include reason"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name="Changed",
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        version_manager.create_version(
            snapshot=modified,
            change_summary="Change",
            author="user"
        )

        rollback = version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id=result1.version.version_id,
            author="admin",
            reason="Production issue"
        )

        assert "Production issue" in rollback.new_version.change_summary


# =============================================================================
# AC-4: Diff between versions visualizable
# =============================================================================

class TestAC4_VersionDiff:
    """Tests for AC-4: Diff between versions visualizable"""

    def test_diff_detects_added_fields(self, version_manager, sample_snapshot):
        """Diff should detect added list items"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities + ["new_capability"],
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result2 = version_manager.create_version(
            snapshot=modified,
            change_summary="Added capability",
            author="user"
        )

        diff = version_manager.diff(
            sample_snapshot.persona_id,
            result1.version.version_id,
            result2.version.version_id
        )

        assert diff is not None
        assert "capabilities" in diff.changed_fields

    def test_diff_detects_removed_fields(self, version_manager, sample_snapshot):
        """Diff should detect removed list items"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits[:1],  # Remove items
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result2 = version_manager.create_version(
            snapshot=modified,
            change_summary="Removed traits",
            author="user"
        )

        diff = version_manager.diff(
            sample_snapshot.persona_id,
            result1.version.version_id,
            result2.version.version_id
        )

        assert diff is not None
        assert "core_traits" in diff.changed_fields

    def test_diff_detects_modified_fields(self, version_manager, sample_snapshot):
        """Diff should detect modified string fields"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name="New Name",
            role="New Role",
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result2 = version_manager.create_version(
            snapshot=modified,
            change_summary="Changed name and role",
            author="user"
        )

        diff = version_manager.diff(
            sample_snapshot.persona_id,
            result1.version.version_id,
            result2.version.version_id
        )

        assert diff is not None
        assert "name" in diff.changed_fields
        assert "role" in diff.changed_fields

    def test_diff_has_breaking_changes_flag(self, version_manager, sample_snapshot):
        """Diff should indicate breaking changes"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role="Completely Different Role",  # Breaking change
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result2 = version_manager.create_version(
            snapshot=modified,
            change_summary="Role change",
            author="user"
        )

        diff = version_manager.diff(
            sample_snapshot.persona_id,
            result1.version.version_id,
            result2.version.version_id
        )

        assert diff is not None
        assert diff.has_breaking_changes

    def test_diff_report_generation(self, version_manager, sample_snapshot):
        """Should generate human-readable diff report"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name="Updated Name",
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result2 = version_manager.create_version(
            snapshot=modified,
            change_summary="Name update",
            author="user"
        )

        report = version_manager.format_diff_report(
            sample_snapshot.persona_id,
            result1.version.version_id,
            result2.version.version_id
        )

        assert "Persona Diff Report" in report
        assert sample_snapshot.persona_id in report
        assert "name" in report.lower()

    def test_diff_with_latest(self, version_manager, sample_snapshot):
        """Should diff any version against latest"""
        result1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="V1",
            author="user"
        )

        for i in range(3):
            modified = PersonaSnapshot(
                persona_id=sample_snapshot.persona_id,
                name=sample_snapshot.name,
                role=sample_snapshot.role,
                personality=sample_snapshot.personality,
                core_traits=sample_snapshot.core_traits,
                capabilities=[f"cap_{i}"],
                tools=sample_snapshot.tools,
                description=f"V{i+2}",
                metadata=sample_snapshot.metadata
            )
            version_manager.create_version(
                snapshot=modified,
                change_summary=f"V{i+2}",
                author="user"
            )

        diff = version_manager.diff_with_latest(
            sample_snapshot.persona_id,
            result1.version.version_id
        )

        assert diff is not None
        assert diff.changed_field_count > 0


# =============================================================================
# AC-5: Semantic versioning (major.minor.patch) based on change impact
# =============================================================================

class TestAC5_SemanticVersioning:
    """Tests for AC-5: Semantic versioning based on change impact"""

    def test_initial_version_is_0_1_0(self, version_manager, sample_snapshot):
        """Initial version should be 0.1.0"""
        result = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        assert result.version.version_number == "0.1.0"

    def test_patch_bump_for_description_change(self, version_manager, sample_snapshot):
        """Description change should bump patch version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description="Updated description text",
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Description update",
            author="user"
        )

        assert result.version.version_number == "0.1.1"

    def test_minor_bump_for_capabilities_change(self, version_manager, sample_snapshot):
        """Capabilities change should bump minor version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities + ["new_feature"],
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Added capability",
            author="user"
        )

        assert result.version.version_number == "0.2.0"

    def test_major_bump_for_role_change(self, version_manager, sample_snapshot):
        """Role change should bump major version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role="Completely Different Role",  # Breaking change
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Role overhaul",
            author="user"
        )

        assert result.version.version_number == "1.0.0"

    def test_major_bump_for_personality_change(self, version_manager, sample_snapshot):
        """Personality change should bump major version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality="Completely different personality",  # Breaking
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Personality redesign",
            author="user"
        )

        assert result.version.version_number == "1.0.0"

    def test_major_bump_for_core_traits_change(self, version_manager, sample_snapshot):
        """Core traits change should bump major version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=["completely", "different", "traits"],  # Breaking
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Traits overhaul",
            author="user"
        )

        assert result.version.version_number == "1.0.0"

    def test_minor_bump_for_tools_change(self, version_manager, sample_snapshot):
        """Tools change should bump minor version"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools + ["new_tool"],
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Added tool",
            author="user"
        )

        assert result.version.version_number == "0.2.0"

    def test_highest_impact_wins(self, version_manager, sample_snapshot):
        """When multiple fields change, highest impact determines bump"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role="New Role",  # Major
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities + ["new"],  # Minor
            tools=sample_snapshot.tools,
            description="Updated",  # Patch
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Multiple changes",
            author="user"
        )

        # Major wins over minor and patch
        assert result.version.version_number == "1.0.0"

    def test_semantic_version_parsing(self):
        """Semantic version should parse correctly"""
        v = SemanticVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_semantic_version_comparison(self):
        """Semantic versions should compare correctly"""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(1, 1, 0)
        v3 = SemanticVersion(2, 0, 0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

    def test_version_change_type_tracking(self, version_manager, sample_snapshot):
        """Version should track change type"""
        version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial",
            author="user"
        )

        modified = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role="Breaking Change",
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities,
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        result = version_manager.create_version(
            snapshot=modified,
            change_summary="Breaking",
            author="user"
        )

        assert result.version.change_type == VersionChange.MAJOR


# =============================================================================
# Additional Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for persona version control"""

    def test_full_workflow(self, version_manager, sample_snapshot):
        """Test complete version control workflow"""
        # 1. Create initial version
        v1 = version_manager.create_version(
            snapshot=sample_snapshot,
            change_summary="Initial persona",
            author="admin"
        )
        assert v1.success

        # 2. Make minor change
        snapshot2 = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role=sample_snapshot.role,
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=sample_snapshot.capabilities + ["code_review"],
            tools=sample_snapshot.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        v2 = version_manager.create_version(
            snapshot=snapshot2,
            change_summary="Added code review capability",
            author="developer"
        )
        assert v2.success
        assert v2.version.version_number == "0.2.0"

        # 3. Make breaking change
        snapshot3 = PersonaSnapshot(
            persona_id=sample_snapshot.persona_id,
            name=sample_snapshot.name,
            role="Senior Architect",  # Breaking
            personality=sample_snapshot.personality,
            core_traits=sample_snapshot.core_traits,
            capabilities=snapshot2.capabilities,
            tools=snapshot2.tools,
            description=sample_snapshot.description,
            metadata=sample_snapshot.metadata
        )
        v3 = version_manager.create_version(
            snapshot=snapshot3,
            change_summary="Promoted to architect",
            author="hr"
        )
        assert v3.success
        assert v3.version.version_number == "1.0.0"

        # 4. Query history
        history = version_manager.get_history(sample_snapshot.persona_id)
        assert len(history) == 3
        assert history[0].author == "hr"
        assert history[1].author == "developer"
        assert history[2].author == "admin"

        # 5. Diff versions
        diff = version_manager.diff(
            sample_snapshot.persona_id,
            v1.version.version_id,
            v3.version.version_id
        )
        assert diff is not None
        assert diff.has_breaking_changes
        assert "role" in diff.changed_fields
        assert "capabilities" in diff.changed_fields

        # 6. Rollback
        rollback = version_manager.rollback(
            persona_id=sample_snapshot.persona_id,
            target_version_id=v2.version.version_id,
            author="admin",
            reason="Reverting promotion"
        )
        assert rollback.success

        # 7. Verify rollback
        latest = version_manager.get_latest(sample_snapshot.persona_id)
        assert latest.snapshot.role == sample_snapshot.role
        assert "code_review" in latest.snapshot.capabilities

        # 8. Check full history preserved
        final_history = version_manager.get_history(sample_snapshot.persona_id)
        assert len(final_history) == 4

    def test_concurrent_version_creation(self, temp_version_dir, sample_snapshot):
        """Test thread-safe version creation"""
        import threading

        manager = PersonaVersionManager(version_dir=temp_version_dir)
        errors = []
        versions_created = []

        def create_version(i):
            try:
                modified = PersonaSnapshot(
                    persona_id=sample_snapshot.persona_id,
                    name=sample_snapshot.name,
                    role=sample_snapshot.role,
                    personality=sample_snapshot.personality,
                    core_traits=sample_snapshot.core_traits,
                    capabilities=[f"cap_{i}"],
                    tools=sample_snapshot.tools,
                    description=f"Thread {i}",
                    metadata=sample_snapshot.metadata
                )
                result = manager.create_version(
                    snapshot=modified,
                    change_summary=f"Thread {i}",
                    author=f"user_{i}"
                )
                if result.success:
                    versions_created.append(result.version)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=create_version, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        # At least some versions should be created
        assert len(versions_created) >= 1

    def test_list_personas(self, version_manager, sample_snapshot):
        """Test listing all personas with versions"""
        # Create versions for multiple personas
        for persona_id in ["persona-1", "persona-2", "persona-3"]:
            snapshot = PersonaSnapshot(
                persona_id=persona_id,
                name=f"Persona {persona_id}",
                role="Test Role",
                personality="Test",
                core_traits=["test"],
                capabilities=["test"],
                tools=["test"],
                description="Test",
                metadata={}
            )
            version_manager.create_version(
                snapshot=snapshot,
                change_summary="Initial",
                author="user"
            )

        personas = version_manager.list_personas()
        assert len(personas) == 3
        assert "persona-1" in personas
        assert "persona-2" in personas
        assert "persona-3" in personas
