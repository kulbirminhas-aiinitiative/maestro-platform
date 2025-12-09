"""
Tests for Branch Protection Rules module (MD-2382 AC-1).

Verifies:
- Rule creation and configuration
- Template generation for GitHub, GitLab, Azure DevOps
- Platform-specific API output
- Manager functionality
"""

import pytest
import json
import yaml

from maestro_hive.blocks.templates.cicd.branch_protection import (
    BranchProtectionRule,
    BranchProtectionTemplate,
    BranchProtectionManager,
    RequiredStatusCheck,
    RequiredReview,
    SignatureRequirement,
    Platform,
    MergeMethod,
)


class TestRequiredStatusCheck:
    """Tests for RequiredStatusCheck dataclass."""

    def test_basic_status_check(self):
        """Test creating a basic status check."""
        check = RequiredStatusCheck(context="ci/build")
        assert check.context == "ci/build"
        assert check.strict is True  # default
        assert check.app_id is None

    def test_status_check_with_app_id(self):
        """Test status check with app ID."""
        check = RequiredStatusCheck(
            context="ci/test",
            app_id=12345,
            strict=False
        )
        assert check.app_id == 12345
        assert check.strict is False

    def test_to_dict(self):
        """Test converting status check to dict."""
        check = RequiredStatusCheck(context="ci/build", strict=True)
        result = check.to_dict()
        assert result["context"] == "ci/build"
        assert result["strict"] is True


class TestRequiredReview:
    """Tests for RequiredReview dataclass."""

    def test_basic_review_requirement(self):
        """Test creating basic review requirement."""
        review = RequiredReview(required_approving_review_count=2)
        assert review.required_approving_review_count == 2
        assert review.dismiss_stale_reviews is True  # default
        assert review.require_code_owner_reviews is False  # default

    def test_strict_review_requirement(self):
        """Test strict review settings."""
        review = RequiredReview(
            required_approving_review_count=3,
            dismiss_stale_reviews=True,
            require_code_owner_reviews=True,
            require_last_push_approval=True
        )
        assert review.required_approving_review_count == 3
        assert review.require_code_owner_reviews is True
        assert review.require_last_push_approval is True

    def test_to_dict(self):
        """Test converting review to dict."""
        review = RequiredReview(required_approving_review_count=2)
        result = review.to_dict()
        assert result["required_approving_review_count"] == 2
        assert "dismiss_stale_reviews" in result


class TestSignatureRequirement:
    """Tests for SignatureRequirement dataclass."""

    def test_default_signature_requirement(self):
        """Test default signature requirement."""
        sig = SignatureRequirement()
        assert sig.require_signed_commits is False
        assert sig.require_verified_signatures is False

    def test_enabled_signature_requirement(self):
        """Test enabled signature requirement."""
        sig = SignatureRequirement(
            require_signed_commits=True,
            require_verified_signatures=True
        )
        assert sig.require_signed_commits is True
        assert sig.require_verified_signatures is True


class TestBranchProtectionRule:
    """Tests for BranchProtectionRule dataclass."""

    def test_basic_rule(self):
        """Test creating a basic branch protection rule."""
        rule = BranchProtectionRule(branch_pattern="main")
        assert rule.branch_pattern == "main"
        assert rule.platform == Platform.GITHUB  # default
        assert rule.enforce_admins is True

    def test_rule_with_all_options(self):
        """Test rule with comprehensive configuration."""
        rule = BranchProtectionRule(
            branch_pattern="release/*",
            platform=Platform.GITHUB,
            enforce_admins=True,
            allow_force_pushes=False,
            require_status_checks=True,
            required_status_checks=[
                RequiredStatusCheck(context="ci/build"),
                RequiredStatusCheck(context="ci/test")
            ],
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(required_approving_review_count=2),
            require_linear_history=True,
            signature_requirement=SignatureRequirement(require_signed_commits=True)
        )
        assert rule.enforce_admins is True
        assert len(rule.required_status_checks) == 2
        assert rule.signature_requirement.require_signed_commits is True

    def test_default_reviews_created(self):
        """Test that default reviews are created when requiring PR reviews."""
        rule = BranchProtectionRule(
            branch_pattern="main",
            require_pull_request_reviews=True
        )
        assert rule.required_reviews is not None
        assert rule.required_reviews.required_approving_review_count == 1

    def test_to_github_api(self):
        """Test GitHub API output."""
        rule = BranchProtectionRule(
            branch_pattern="main",
            enforce_admins=True,
            require_pull_request_reviews=True
        )
        result = rule.to_github_api()
        assert result["enforce_admins"] is True
        assert "required_pull_request_reviews" in result

    def test_to_gitlab_api(self):
        """Test GitLab API output."""
        rule = BranchProtectionRule(
            branch_pattern="main",
            platform=Platform.GITLAB,
            allow_force_pushes=False
        )
        result = rule.to_gitlab_api()
        assert result["name"] == "main"
        assert result["allow_force_push"] is False

    def test_to_azure_devops_api(self):
        """Test Azure DevOps API output."""
        rule = BranchProtectionRule(
            branch_pattern="main",
            platform=Platform.AZURE_DEVOPS,
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(required_approving_review_count=2)
        )
        result = rule.to_azure_devops_api()
        assert "policies" in result
        assert len(result["policies"]) > 0

    def test_to_dict_respects_platform(self):
        """Test that to_dict respects platform setting."""
        rule_github = BranchProtectionRule(
            branch_pattern="main",
            platform=Platform.GITHUB
        )
        rule_gitlab = BranchProtectionRule(
            branch_pattern="main",
            platform=Platform.GITLAB
        )

        github_result = rule_github.to_dict()
        gitlab_result = rule_gitlab.to_dict()

        # GitHub uses enforce_admins, GitLab uses name
        assert "enforce_admins" in github_result
        assert "name" in gitlab_result

    def test_to_json(self):
        """Test JSON export."""
        rule = BranchProtectionRule(branch_pattern="main")
        json_output = rule.to_json()
        parsed = json.loads(json_output)
        assert "enforce_admins" in parsed

    def test_to_yaml(self):
        """Test YAML export."""
        rule = BranchProtectionRule(branch_pattern="main")
        yaml_output = rule.to_yaml()
        parsed = yaml.safe_load(yaml_output)
        assert "enforce_admins" in parsed


class TestBranchProtectionTemplate:
    """Tests for BranchProtectionTemplate."""

    def test_production_strict(self):
        """Test production_strict template."""
        rule = BranchProtectionTemplate.production_strict()
        assert rule.branch_pattern == "main"
        assert rule.enforce_admins is True
        assert rule.require_linear_history is True
        assert rule.required_reviews.required_approving_review_count == 2
        assert rule.signature_requirement.require_signed_commits is True

    def test_production_strict_custom_branch(self):
        """Test production_strict with custom branch name."""
        rule = BranchProtectionTemplate.production_strict(branch="master")
        assert rule.branch_pattern == "master"

    def test_development_moderate(self):
        """Test development_moderate template."""
        rule = BranchProtectionTemplate.development_moderate()
        assert rule.branch_pattern == "develop"
        assert rule.enforce_admins is False
        assert rule.required_reviews.required_approving_review_count == 1

    def test_feature_minimal(self):
        """Test feature_minimal template."""
        rule = BranchProtectionTemplate.feature_minimal()
        assert rule.branch_pattern == "feature/*"
        assert rule.allow_force_pushes is True
        assert rule.require_pull_request_reviews is False

    def test_release_locked(self):
        """Test release_locked template."""
        rule = BranchProtectionTemplate.release_locked()
        assert rule.branch_pattern == "release/*"
        assert rule.enforce_admins is True
        assert len(rule.required_status_checks) == 4
        assert rule.signature_requirement.require_signed_commits is True

    def test_template_with_platform(self):
        """Test templates with specific platform."""
        rule = BranchProtectionTemplate.production_strict(
            platform=Platform.GITLAB
        )
        assert rule.platform == Platform.GITLAB


class TestBranchProtectionManager:
    """Tests for BranchProtectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        return BranchProtectionManager(platform=Platform.GITHUB)

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.platform == Platform.GITHUB
        assert len(manager.rules) == 0

    def test_add_rule(self, manager):
        """Test adding a rule."""
        rule = BranchProtectionRule(branch_pattern="main")
        manager.add_rule(rule)
        assert len(manager.rules) == 1
        assert manager.rules[0].branch_pattern == "main"

    def test_add_rule_overrides_platform(self, manager):
        """Test that adding a rule overrides the platform."""
        rule = BranchProtectionRule(
            branch_pattern="main",
            platform=Platform.GITLAB
        )
        manager.add_rule(rule)
        assert manager.rules[0].platform == Platform.GITHUB

    def test_add_standard_rules(self, manager):
        """Test adding standard rules."""
        manager.add_standard_rules()
        assert len(manager.rules) == 4
        patterns = [r.branch_pattern for r in manager.rules]
        assert "main" in patterns
        assert "develop" in patterns
        assert "feature/*" in patterns
        assert "release/*" in patterns

    def test_get_rules(self, manager):
        """Test getting rules."""
        manager.add_standard_rules()
        rules = manager.get_rules()
        assert len(rules) == 4

    def test_to_config(self, manager):
        """Test exporting configuration."""
        manager.add_standard_rules()
        config = manager.to_config()
        assert config["platform"] == "github"
        assert len(config["rules"]) == 4

    def test_gitlab_manager(self):
        """Test manager with GitLab platform."""
        manager = BranchProtectionManager(platform=Platform.GITLAB)
        manager.add_standard_rules()
        config = manager.to_config()
        assert config["platform"] == "gitlab"

    def test_azure_manager(self):
        """Test manager with Azure DevOps platform."""
        manager = BranchProtectionManager(platform=Platform.AZURE_DEVOPS)
        manager.add_standard_rules()
        config = manager.to_config()
        assert config["platform"] == "azure_devops"


class TestPlatformSpecificOutput:
    """Tests for platform-specific configuration output."""

    @pytest.fixture
    def strict_rule(self):
        """Create a strict rule for testing."""
        return BranchProtectionRule(
            branch_pattern="main",
            enforce_admins=True,
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(
                required_approving_review_count=2,
                require_code_owner_reviews=True
            ),
            required_status_checks=[
                RequiredStatusCheck(context="ci/build"),
                RequiredStatusCheck(context="ci/test")
            ],
            require_linear_history=True
        )

    def test_github_status_checks(self, strict_rule):
        """Test GitHub status checks output."""
        result = strict_rule.to_github_api()
        assert "required_status_checks" in result
        assert result["required_status_checks"]["strict"] is True
        assert len(result["required_status_checks"]["checks"]) == 2

    def test_github_reviews(self, strict_rule):
        """Test GitHub review requirements output."""
        result = strict_rule.to_github_api()
        assert "required_pull_request_reviews" in result
        reviews = result["required_pull_request_reviews"]
        assert reviews["required_approving_review_count"] == 2
        assert reviews["require_code_owner_reviews"] is True

    def test_gitlab_merge_settings(self, strict_rule):
        """Test GitLab merge settings output."""
        strict_rule.platform = Platform.GITLAB
        result = strict_rule.to_gitlab_api()
        assert "merge_access_level" in result
        assert "code_owner_approval_required" in result

    def test_azure_policies(self, strict_rule):
        """Test Azure DevOps policies output."""
        strict_rule.platform = Platform.AZURE_DEVOPS
        result = strict_rule.to_azure_devops_api()
        policies = result["policies"]

        # Should have minimum reviewers policy
        policy_types = [p["type"]["id"] for p in policies]
        assert "fa4e907d-c16b-4a4c-9dfa-4916e5d171ab" in policy_types  # Minimum reviewers


class TestMergeMethod:
    """Tests for MergeMethod enum."""

    def test_merge_methods(self):
        """Test merge method values."""
        assert MergeMethod.MERGE.value == "merge"
        assert MergeMethod.SQUASH.value == "squash"
        assert MergeMethod.REBASE.value == "rebase"

    def test_default_merge_method(self):
        """Test default merge method in rule."""
        rule = BranchProtectionRule(branch_pattern="main")
        assert MergeMethod.SQUASH in rule.allowed_merge_methods


class TestPlatform:
    """Tests for Platform enum."""

    def test_platform_values(self):
        """Test platform values."""
        assert Platform.GITHUB.value == "github"
        assert Platform.GITLAB.value == "gitlab"
        assert Platform.AZURE_DEVOPS.value == "azure_devops"
        assert Platform.BITBUCKET.value == "bitbucket"
