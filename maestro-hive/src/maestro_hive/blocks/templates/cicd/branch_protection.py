"""
Branch Protection Rules Module

Provides automated branch protection configuration for multiple platforms:
- GitHub Branch Protection Rules
- GitLab Protected Branches
- Azure DevOps Branch Policies

Acceptance Criteria: AC-1 - Branch Protection Rules
Reference: MD-2382 Quality Fabric & Evolutionary Templates
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import yaml


class Platform(Enum):
    """Supported Git hosting platforms."""
    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE_DEVOPS = "azure_devops"
    BITBUCKET = "bitbucket"


class MergeMethod(Enum):
    """Allowed merge methods."""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


@dataclass
class RequiredStatusCheck:
    """Configuration for required status checks."""
    context: str
    app_id: Optional[int] = None
    strict: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {"context": self.context, "strict": self.strict}
        if self.app_id:
            result["app_id"] = self.app_id
        return result


@dataclass
class RequiredReview:
    """Configuration for required code reviews."""
    required_approving_review_count: int = 1
    dismiss_stale_reviews: bool = True
    require_code_owner_reviews: bool = False
    require_last_push_approval: bool = False
    restrict_dismissals: bool = False
    dismissal_restrictions_users: List[str] = field(default_factory=list)
    dismissal_restrictions_teams: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "required_approving_review_count": self.required_approving_review_count,
            "dismiss_stale_reviews": self.dismiss_stale_reviews,
            "require_code_owner_reviews": self.require_code_owner_reviews,
            "require_last_push_approval": self.require_last_push_approval,
            "restrict_dismissals": self.restrict_dismissals,
            "dismissal_restrictions": {
                "users": self.dismissal_restrictions_users,
                "teams": self.dismissal_restrictions_teams,
            }
        }


@dataclass
class SignatureRequirement:
    """Configuration for commit signature requirements."""
    require_signed_commits: bool = False
    require_verified_signatures: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "require_signed_commits": self.require_signed_commits,
            "require_verified_signatures": self.require_verified_signatures,
        }


@dataclass
class BranchProtectionRule:
    """
    Branch protection rule configuration.

    Supports GitHub, GitLab, and Azure DevOps branch protection patterns.
    """
    branch_pattern: str
    platform: Platform = Platform.GITHUB

    # Enforcement settings
    enforce_admins: bool = True
    allow_force_pushes: bool = False
    allow_deletions: bool = False
    block_creations: bool = False

    # Required status checks
    require_status_checks: bool = True
    required_status_checks: List[RequiredStatusCheck] = field(default_factory=list)
    strict_status_checks: bool = True

    # Required reviews
    require_pull_request_reviews: bool = True
    required_reviews: Optional[RequiredReview] = None

    # Linear history
    require_linear_history: bool = False

    # Merge restrictions
    allowed_merge_methods: List[MergeMethod] = field(default_factory=lambda: [MergeMethod.SQUASH])

    # Signature requirements
    signature_requirement: Optional[SignatureRequirement] = None

    # Restrictions
    restrict_pushes: bool = False
    push_restrictions_users: List[str] = field(default_factory=list)
    push_restrictions_teams: List[str] = field(default_factory=list)
    push_restrictions_apps: List[str] = field(default_factory=list)

    # Conversation resolution
    require_conversation_resolution: bool = True

    # Lock branch (read-only)
    lock_branch: bool = False

    def __post_init__(self):
        """Initialize default required reviews if not provided."""
        if self.require_pull_request_reviews and not self.required_reviews:
            self.required_reviews = RequiredReview()

    def to_github_api(self) -> Dict[str, Any]:
        """
        Generate GitHub API payload for branch protection.

        Returns:
            Dict suitable for GitHub REST API /repos/{owner}/{repo}/branches/{branch}/protection
        """
        payload = {
            "enforce_admins": self.enforce_admins,
            "allow_force_pushes": self.allow_force_pushes,
            "allow_deletions": self.allow_deletions,
            "block_creations": self.block_creations,
            "required_linear_history": self.require_linear_history,
            "required_conversation_resolution": self.require_conversation_resolution,
            "lock_branch": self.lock_branch,
        }

        # Status checks
        if self.require_status_checks and self.required_status_checks:
            payload["required_status_checks"] = {
                "strict": self.strict_status_checks,
                "checks": [check.to_dict() for check in self.required_status_checks]
            }
        else:
            payload["required_status_checks"] = None

        # Pull request reviews
        if self.require_pull_request_reviews and self.required_reviews:
            payload["required_pull_request_reviews"] = self.required_reviews.to_dict()
        else:
            payload["required_pull_request_reviews"] = None

        # Push restrictions
        if self.restrict_pushes:
            payload["restrictions"] = {
                "users": self.push_restrictions_users,
                "teams": self.push_restrictions_teams,
                "apps": self.push_restrictions_apps,
            }
        else:
            payload["restrictions"] = None

        # Signature requirements
        if self.signature_requirement and self.signature_requirement.require_signed_commits:
            payload["required_signatures"] = True

        return payload

    def to_gitlab_api(self) -> Dict[str, Any]:
        """
        Generate GitLab API payload for protected branches.

        Returns:
            Dict suitable for GitLab API /projects/:id/protected_branches
        """
        # Map approval count to GitLab access levels
        access_level = 40  # Maintainer by default
        if self.required_reviews and self.required_reviews.required_approving_review_count > 0:
            access_level = 30  # Developer

        payload = {
            "name": self.branch_pattern,
            "push_access_level": 0 if not self.allow_force_pushes else access_level,
            "merge_access_level": access_level,
            "allow_force_push": self.allow_force_pushes,
            "code_owner_approval_required": (
                self.required_reviews.require_code_owner_reviews
                if self.required_reviews else False
            ),
        }

        return payload

    def to_azure_devops_api(self) -> Dict[str, Any]:
        """
        Generate Azure DevOps API payload for branch policies.

        Returns:
            Dict suitable for Azure DevOps Branch Policy API
        """
        policies = []

        # Minimum reviewers policy
        if self.require_pull_request_reviews and self.required_reviews:
            policies.append({
                "type": {
                    "id": "fa4e907d-c16b-4a4c-9dfa-4916e5d171ab"  # Minimum number of reviewers
                },
                "isEnabled": True,
                "isBlocking": True,
                "settings": {
                    "minimumApproverCount": self.required_reviews.required_approving_review_count,
                    "creatorVoteCounts": False,
                    "allowDownvotes": False,
                    "resetOnSourcePush": self.required_reviews.dismiss_stale_reviews,
                    "scope": [{"refName": f"refs/heads/{self.branch_pattern}"}]
                }
            })

        # Required build policy
        if self.require_status_checks:
            for check in self.required_status_checks:
                policies.append({
                    "type": {
                        "id": "0609b952-1397-4640-95ec-e00a01b2c241"  # Build validation
                    },
                    "isEnabled": True,
                    "isBlocking": True,
                    "settings": {
                        "buildDefinitionId": check.app_id or 0,
                        "queueOnSourceUpdateOnly": True,
                        "manualQueueOnly": False,
                        "displayName": check.context,
                        "validDuration": 720,
                        "scope": [{"refName": f"refs/heads/{self.branch_pattern}"}]
                    }
                })

        # Comment resolution policy
        if self.require_conversation_resolution:
            policies.append({
                "type": {
                    "id": "c6a1889d-b943-4856-b76f-9e46bb6b0df2"  # Comment requirements
                },
                "isEnabled": True,
                "isBlocking": True,
                "settings": {
                    "scope": [{"refName": f"refs/heads/{self.branch_pattern}"}]
                }
            })

        return {"policies": policies}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to platform-specific dictionary."""
        if self.platform == Platform.GITHUB:
            return self.to_github_api()
        elif self.platform == Platform.GITLAB:
            return self.to_gitlab_api()
        elif self.platform == Platform.AZURE_DEVOPS:
            return self.to_azure_devops_api()
        else:
            # Default to GitHub format
            return self.to_github_api()

    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_yaml(self) -> str:
        """Export as YAML string (for configuration files)."""
        return yaml.dump(self.to_dict(), default_flow_style=False)


class BranchProtectionTemplate:
    """
    Pre-configured branch protection templates for common scenarios.
    """

    @staticmethod
    def production_strict(branch: str = "main", platform: Platform = Platform.GITHUB) -> BranchProtectionRule:
        """
        Strict production branch protection.

        - Requires 2 approving reviews
        - Requires code owner review
        - Dismisses stale reviews
        - Requires all status checks to pass
        - No force pushes or deletions
        - Enforces admin rules
        - Requires linear history
        """
        return BranchProtectionRule(
            branch_pattern=branch,
            platform=platform,
            enforce_admins=True,
            allow_force_pushes=False,
            allow_deletions=False,
            require_status_checks=True,
            required_status_checks=[
                RequiredStatusCheck(context="ci/build", strict=True),
                RequiredStatusCheck(context="ci/test", strict=True),
                RequiredStatusCheck(context="ci/security-scan", strict=True),
            ],
            strict_status_checks=True,
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(
                required_approving_review_count=2,
                dismiss_stale_reviews=True,
                require_code_owner_reviews=True,
                require_last_push_approval=True,
            ),
            require_linear_history=True,
            allowed_merge_methods=[MergeMethod.SQUASH],
            require_conversation_resolution=True,
            signature_requirement=SignatureRequirement(
                require_signed_commits=True,
                require_verified_signatures=True,
            ),
        )

    @staticmethod
    def development_moderate(branch: str = "develop", platform: Platform = Platform.GITHUB) -> BranchProtectionRule:
        """
        Moderate protection for development branches.

        - Requires 1 approving review
        - Requires status checks to pass
        - Allows squash and rebase merges
        """
        return BranchProtectionRule(
            branch_pattern=branch,
            platform=platform,
            enforce_admins=False,
            allow_force_pushes=False,
            allow_deletions=False,
            require_status_checks=True,
            required_status_checks=[
                RequiredStatusCheck(context="ci/build", strict=True),
                RequiredStatusCheck(context="ci/test", strict=True),
            ],
            strict_status_checks=True,
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(
                required_approving_review_count=1,
                dismiss_stale_reviews=True,
                require_code_owner_reviews=False,
            ),
            require_linear_history=False,
            allowed_merge_methods=[MergeMethod.SQUASH, MergeMethod.REBASE],
            require_conversation_resolution=True,
        )

    @staticmethod
    def feature_minimal(branch: str = "feature/*", platform: Platform = Platform.GITHUB) -> BranchProtectionRule:
        """
        Minimal protection for feature branches.

        - Requires status checks to pass
        - No review requirements
        - Allows force pushes for rebasing
        """
        return BranchProtectionRule(
            branch_pattern=branch,
            platform=platform,
            enforce_admins=False,
            allow_force_pushes=True,
            allow_deletions=True,
            require_status_checks=True,
            required_status_checks=[
                RequiredStatusCheck(context="ci/build", strict=False),
            ],
            strict_status_checks=False,
            require_pull_request_reviews=False,
            require_linear_history=False,
            allowed_merge_methods=[MergeMethod.MERGE, MergeMethod.SQUASH, MergeMethod.REBASE],
            require_conversation_resolution=False,
        )

    @staticmethod
    def release_locked(branch: str = "release/*", platform: Platform = Platform.GITHUB) -> BranchProtectionRule:
        """
        Locked release branches.

        - Requires 2 approving reviews including code owner
        - All status checks including security
        - No force pushes
        - Signed commits required
        """
        return BranchProtectionRule(
            branch_pattern=branch,
            platform=platform,
            enforce_admins=True,
            allow_force_pushes=False,
            allow_deletions=False,
            block_creations=False,
            require_status_checks=True,
            required_status_checks=[
                RequiredStatusCheck(context="ci/build", strict=True),
                RequiredStatusCheck(context="ci/test", strict=True),
                RequiredStatusCheck(context="ci/security-scan", strict=True),
                RequiredStatusCheck(context="ci/integration", strict=True),
            ],
            strict_status_checks=True,
            require_pull_request_reviews=True,
            required_reviews=RequiredReview(
                required_approving_review_count=2,
                dismiss_stale_reviews=True,
                require_code_owner_reviews=True,
                require_last_push_approval=True,
            ),
            require_linear_history=True,
            allowed_merge_methods=[MergeMethod.MERGE],
            require_conversation_resolution=True,
            signature_requirement=SignatureRequirement(
                require_signed_commits=True,
                require_verified_signatures=True,
            ),
        )


class BranchProtectionManager:
    """
    Manager for branch protection rules across repositories.

    Provides methods to generate protection configurations for multiple branches
    and export them in various formats.
    """

    def __init__(self, platform: Platform = Platform.GITHUB):
        """Initialize with target platform."""
        self.platform = platform
        self.rules: List[BranchProtectionRule] = []

    def add_rule(self, rule: BranchProtectionRule) -> None:
        """Add a branch protection rule."""
        # Override platform if needed
        rule.platform = self.platform
        self.rules.append(rule)

    def add_standard_rules(self) -> None:
        """Add standard production/development/feature branch rules."""
        self.add_rule(BranchProtectionTemplate.production_strict("main", self.platform))
        self.add_rule(BranchProtectionTemplate.development_moderate("develop", self.platform))
        self.add_rule(BranchProtectionTemplate.feature_minimal("feature/*", self.platform))
        self.add_rule(BranchProtectionTemplate.release_locked("release/*", self.platform))

    def get_rules(self) -> List[BranchProtectionRule]:
        """Get all configured rules."""
        return self.rules

    def to_config(self) -> Dict[str, Any]:
        """
        Export all rules as a configuration dictionary.

        Returns:
            Dictionary with all branch protection configurations
        """
        return {
            "platform": self.platform.value,
            "rules": [
                {
                    "branch_pattern": rule.branch_pattern,
                    "config": rule.to_dict()
                }
                for rule in self.rules
            ]
        }

    def to_json(self) -> str:
        """Export configuration as JSON."""
        return json.dumps(self.to_config(), indent=2)

    def to_yaml(self) -> str:
        """Export configuration as YAML."""
        return yaml.dump(self.to_config(), default_flow_style=False)

    def generate_github_workflow(self) -> str:
        """
        Generate a GitHub Actions workflow to apply branch protection.

        Returns:
            YAML string for .github/workflows/branch-protection.yml
        """
        workflow = {
            "name": "Apply Branch Protection Rules",
            "on": {
                "workflow_dispatch": {},
                "push": {
                    "branches": ["main"],
                    "paths": [".github/branch-protection.yml"]
                }
            },
            "jobs": {
                "apply-protection": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "Apply Branch Protection",
                            "uses": "actions/github-script@v7",
                            "with": {
                                "github-token": "${{ secrets.ADMIN_TOKEN }}",
                                "script": self._generate_protection_script()
                            }
                        }
                    ]
                }
            }
        }
        return yaml.dump(workflow, default_flow_style=False)

    def _generate_protection_script(self) -> str:
        """Generate JavaScript for GitHub Actions script."""
        lines = ["const owner = context.repo.owner;", "const repo = context.repo.repo;", ""]

        for rule in self.rules:
            if "*" in rule.branch_pattern:
                # Skip wildcard patterns in GitHub API (would need different approach)
                continue

            config = rule.to_github_api()
            lines.append(f"// Protect {rule.branch_pattern}")
            lines.append(f"await github.rest.repos.updateBranchProtection({{")
            lines.append(f"  owner,")
            lines.append(f"  repo,")
            lines.append(f"  branch: '{rule.branch_pattern}',")
            lines.append(f"  ...{json.dumps(config, indent=2)}")
            lines.append(f"}});")
            lines.append("")

        return "\n".join(lines)


# Convenience functions
def create_production_protection(platform: Platform = Platform.GITHUB) -> BranchProtectionRule:
    """Create production-ready branch protection for main branch."""
    return BranchProtectionTemplate.production_strict(platform=platform)


def create_standard_protection_set(platform: Platform = Platform.GITHUB) -> BranchProtectionManager:
    """Create a standard set of branch protection rules."""
    manager = BranchProtectionManager(platform)
    manager.add_standard_rules()
    return manager
