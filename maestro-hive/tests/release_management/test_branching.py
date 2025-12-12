"""Tests for BranchManager."""

import pytest

from maestro_hive.release_management.branching import BranchManager
from maestro_hive.release_management.models import (
    BranchType,
    ProtectionRules,
    MergeStrategy,
)


class TestBranchManager:
    """Tests for BranchManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh BranchManager instance."""
        return BranchManager(repo="test-repo")

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager.repo == "test-repo"
        # Should have default branches
        assert "main" in manager._branches
        assert "develop" in manager._branches

    def test_default_main_branch(self, manager):
        """Test default main branch configuration."""
        main = manager.get_branch("main")
        assert main is not None
        assert main.branch_type == BranchType.MAIN
        assert main.is_protected is True
        assert main.protection_rules.require_reviews == 2

    def test_default_develop_branch(self, manager):
        """Test default develop branch configuration."""
        develop = manager.get_branch("develop")
        assert develop is not None
        assert develop.branch_type == BranchType.DEVELOP
        assert develop.source_branch == "main"

    def test_create_branch(self, manager):
        """Test creating a new branch."""
        branch = manager.create_branch(
            name="feature/test",
            source="develop",
        )
        assert branch.name == "feature/test"
        assert branch.source_branch == "develop"
        assert branch.branch_type == BranchType.FEATURE

    def test_create_branch_infers_type(self, manager):
        """Test that branch type is inferred from name."""
        feature = manager.create_branch("feature/new", "develop")
        assert feature.branch_type == BranchType.FEATURE

        release = manager.create_branch("release/1.0", "develop")
        assert release.branch_type == BranchType.RELEASE

        hotfix = manager.create_branch("hotfix/fix-bug", "main")
        assert hotfix.branch_type == BranchType.HOTFIX

    def test_create_duplicate_branch_raises(self, manager):
        """Test creating duplicate branch raises error."""
        manager.create_branch("feature/test", "develop")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_branch("feature/test", "develop")

    def test_create_branch_from_invalid_source(self, manager):
        """Test creating branch from non-existent source raises error."""
        with pytest.raises(ValueError, match="not found"):
            manager.create_branch("feature/test", "nonexistent")

    def test_create_stable_demo(self, manager):
        """Test creating stable-demo branch."""
        branch = manager.create_stable_demo()
        assert branch.name == "stable-demo"
        assert branch.branch_type == BranchType.STABLE_DEMO
        assert branch.is_protected is True
        assert branch.source_branch == "main"

    def test_create_stable_demo_idempotent(self, manager):
        """Test creating stable-demo twice returns existing."""
        branch1 = manager.create_stable_demo()
        branch2 = manager.create_stable_demo()
        assert branch1.name == branch2.name

    def test_create_working_beta(self, manager):
        """Test creating working-beta branch."""
        branch = manager.create_working_beta()
        assert branch.name == "working-beta"
        assert branch.branch_type == BranchType.WORKING_BETA
        assert branch.is_protected is True
        assert branch.source_branch == "develop"

    def test_create_working_beta_custom_source(self, manager):
        """Test creating working-beta from custom source."""
        branch = manager.create_working_beta(source="main")
        assert branch.source_branch == "main"

    def test_get_branch(self, manager):
        """Test getting a branch."""
        branch = manager.get_branch("main")
        assert branch is not None
        assert branch.name == "main"

    def test_get_branch_not_found(self, manager):
        """Test getting non-existent branch."""
        branch = manager.get_branch("nonexistent")
        assert branch is None

    def test_list_branches(self, manager):
        """Test listing all branches."""
        manager.create_branch("feature/1", "develop")
        manager.create_branch("feature/2", "develop")

        branches = manager.list_branches()
        # main, develop, feature/1, feature/2
        assert len(branches) == 4

    def test_list_branches_by_type(self, manager):
        """Test listing branches filtered by type."""
        manager.create_branch("feature/1", "develop")
        manager.create_branch("feature/2", "develop")
        manager.create_branch("hotfix/fix", "main")

        features = manager.list_branches(branch_type=BranchType.FEATURE)
        assert len(features) == 2

    def test_list_protected_branches(self, manager):
        """Test listing only protected branches."""
        manager.create_branch("feature/unprotected", "develop")

        protected = manager.list_branches(protected_only=True)
        # main and develop are protected by default
        assert len(protected) == 2

    def test_delete_branch(self, manager):
        """Test deleting a branch."""
        manager.create_branch("feature/test", "develop")

        result = manager.delete_branch("feature/test")
        assert result is True
        assert manager.get_branch("feature/test") is None

    def test_delete_protected_branch_fails(self, manager):
        """Test deleting protected branch fails without force."""
        result = manager.delete_branch("main")
        assert result is False
        assert manager.get_branch("main") is not None

    def test_delete_protected_branch_force(self, manager):
        """Test force deleting protected branch."""
        result = manager.delete_branch("main", force=True)
        assert result is True

    def test_delete_nonexistent_branch(self, manager):
        """Test deleting non-existent branch."""
        result = manager.delete_branch("nonexistent")
        assert result is False

    def test_apply_protection(self, manager):
        """Test applying protection rules."""
        manager.create_branch("feature/test", "develop")

        rules = ProtectionRules(require_reviews=2, require_ci=True)
        result = manager.apply_protection("feature/test", rules)

        assert result is True
        branch = manager.get_branch("feature/test")
        assert branch.is_protected is True
        assert branch.protection_rules.require_reviews == 2

    def test_apply_protection_not_found(self, manager):
        """Test applying protection to non-existent branch."""
        rules = ProtectionRules()
        result = manager.apply_protection("nonexistent", rules)
        assert result is False

    def test_remove_protection(self, manager):
        """Test removing protection from branch."""
        result = manager.remove_protection("develop")

        assert result is True
        branch = manager.get_branch("develop")
        assert branch.is_protected is False
        assert branch.protection_rules is None

    def test_merge_branches(self, manager):
        """Test merging branches."""
        manager.create_branch("feature/test", "develop")

        result = manager.merge("feature/test", "develop")

        assert result.success is True
        assert result.source_branch == "feature/test"
        assert result.target_branch == "develop"
        assert result.commit_sha is not None

    def test_merge_with_strategy(self, manager):
        """Test merging with specific strategy."""
        manager.create_branch("feature/test", "develop")

        result = manager.merge(
            "feature/test",
            "develop",
            strategy=MergeStrategy.SQUASH,
        )

        assert result.success is True
        assert result.strategy_used == MergeStrategy.SQUASH

    def test_merge_source_not_found(self, manager):
        """Test merge with non-existent source fails."""
        result = manager.merge("nonexistent", "develop")

        assert result.success is False
        assert "not found" in result.error

    def test_merge_target_not_found(self, manager):
        """Test merge with non-existent target fails."""
        manager.create_branch("feature/test", "develop")

        result = manager.merge("feature/test", "nonexistent")

        assert result.success is False
        assert "not found" in result.error

    def test_merge_linear_history_requirement(self, manager):
        """Test merge fails when linear history required but using merge strategy."""
        # Main requires linear history
        manager.create_branch("feature/test", "develop")

        result = manager.merge(
            "feature/test",
            "main",
            strategy=MergeStrategy.MERGE,
        )

        assert result.success is False
        assert "linear history" in result.error

    def test_merge_linear_history_with_squash(self, manager):
        """Test merge succeeds with squash when linear history required."""
        manager.create_branch("feature/test", "develop")

        result = manager.merge(
            "feature/test",
            "main",
            strategy=MergeStrategy.SQUASH,
        )

        assert result.success is True

    def test_sync_branch(self, manager):
        """Test syncing branch with its source."""
        manager.create_branch("feature/test", "develop")

        result = manager.sync_branch("feature/test")

        assert result.success is True
        assert result.source_branch == "develop"
        assert result.target_branch == "feature/test"

    def test_sync_branch_custom_source(self, manager):
        """Test syncing branch with custom source."""
        manager.create_branch("feature/test", "develop")

        result = manager.sync_branch("feature/test", source="main")

        assert result.success is True
        assert result.source_branch == "main"

    def test_sync_branch_no_source(self, manager):
        """Test sync fails when no source specified for main."""
        result = manager.sync_branch("main")

        assert result.success is False
        assert "No source" in result.error

    def test_get_branch_status(self, manager):
        """Test getting branch status."""
        status = manager.get_branch_status("main")

        assert status["name"] == "main"
        assert status["type"] == "main"
        assert status["is_protected"] is True
        assert status["protection_rules"] is not None

    def test_get_branch_status_not_found(self, manager):
        """Test status for non-existent branch."""
        status = manager.get_branch_status("nonexistent")
        assert "error" in status

    def test_validate_merge(self, manager):
        """Test validating merge operation."""
        manager.create_branch("feature/test", "develop")

        validation = manager.validate_merge("feature/test", "develop")

        assert validation["valid"] is True
        assert validation["target_protected"] is True
        assert len(validation["requirements"]) > 0

    def test_validate_merge_invalid_source(self, manager):
        """Test validate merge with invalid source."""
        validation = manager.validate_merge("nonexistent", "develop")

        assert validation["valid"] is False
        assert "not found" in validation["error"]

    def test_infer_branch_type_feature(self, manager):
        """Test inferring feature branch type."""
        assert manager._infer_branch_type("feature/new") == BranchType.FEATURE
        assert manager._infer_branch_type("feat/new") == BranchType.FEATURE

    def test_infer_branch_type_release(self, manager):
        """Test inferring release branch type."""
        assert manager._infer_branch_type("release/1.0") == BranchType.RELEASE

    def test_infer_branch_type_hotfix(self, manager):
        """Test inferring hotfix branch type."""
        assert manager._infer_branch_type("hotfix/fix") == BranchType.HOTFIX
        assert manager._infer_branch_type("fix/bug") == BranchType.HOTFIX

    def test_infer_branch_type_stable(self, manager):
        """Test inferring stable-demo branch type."""
        assert manager._infer_branch_type("stable-demo") == BranchType.STABLE_DEMO
        assert manager._infer_branch_type("demo-stable") == BranchType.STABLE_DEMO

    def test_infer_branch_type_beta(self, manager):
        """Test inferring working-beta branch type."""
        assert manager._infer_branch_type("working-beta") == BranchType.WORKING_BETA
        assert manager._infer_branch_type("beta-test") == BranchType.WORKING_BETA
