"""
Git Branching Strategy Implementation.

Provides GitFlow-compatible branching strategy with configurable
branch rules, protection levels, and merge policies.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProtectionLevel(Enum):
    """Branch protection levels."""

    NONE = "none"
    STANDARD = "standard"
    STRICT = "strict"
    FULL = "full"

    @property
    def requires_reviews(self) -> bool:
        """Check if reviews are required."""
        return self in (ProtectionLevel.STANDARD, ProtectionLevel.STRICT,
                        ProtectionLevel.FULL)

    @property
    def requires_status_checks(self) -> bool:
        """Check if status checks are required."""
        return self in (ProtectionLevel.STRICT, ProtectionLevel.FULL)

    @property
    def allows_force_push(self) -> bool:
        """Check if force push is allowed."""
        return self == ProtectionLevel.NONE


class StrategyType(Enum):
    """Branching strategy types."""

    GITFLOW = "gitflow"
    GITHUB_FLOW = "github_flow"
    GITLAB_FLOW = "gitlab_flow"
    TRUNK_BASED = "trunk_based"


@dataclass
class BranchRule:
    """Branch protection rule."""

    pattern: str
    protection_level: ProtectionLevel = ProtectionLevel.NONE
    required_reviewers: int = 0
    required_checks: List[str] = field(default_factory=list)
    auto_merge_allowed: bool = True
    dismiss_stale_reviews: bool = False
    require_up_to_date: bool = False
    restrict_push_access: bool = False
    allowed_pushers: List[str] = field(default_factory=list)

    def matches(self, branch_name: str) -> bool:
        """
        Check if branch name matches this rule's pattern.

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch matches pattern
        """
        # Convert glob pattern to regex
        regex_pattern = self.pattern.replace("*", ".*").replace("?", ".")
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, branch_name))

    def to_dict(self) -> Dict:
        """Convert rule to dictionary."""
        return {
            "pattern": self.pattern,
            "protection_level": self.protection_level.value,
            "required_reviewers": self.required_reviewers,
            "required_checks": self.required_checks,
            "auto_merge_allowed": self.auto_merge_allowed,
            "dismiss_stale_reviews": self.dismiss_stale_reviews,
            "require_up_to_date": self.require_up_to_date,
            "restrict_push_access": self.restrict_push_access,
        }


@dataclass
class BranchValidationResult:
    """Result of branch name validation."""

    valid: bool
    branch_type: Optional[str] = None
    matched_rule: Optional[BranchRule] = None
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class BranchStrategy:
    """Git branching strategy implementation."""

    # Default GitFlow branch rules
    GITFLOW_RULES = [
        BranchRule(
            pattern="main",
            protection_level=ProtectionLevel.FULL,
            required_reviewers=2,
            required_checks=["unit_tests", "integration_tests", "security_scan"],
            auto_merge_allowed=False,
            dismiss_stale_reviews=True,
            require_up_to_date=True,
        ),
        BranchRule(
            pattern="develop",
            protection_level=ProtectionLevel.STANDARD,
            required_reviewers=1,
            required_checks=["unit_tests"],
            auto_merge_allowed=True,
            dismiss_stale_reviews=True,
        ),
        BranchRule(
            pattern="feature/*",
            protection_level=ProtectionLevel.NONE,
            required_reviewers=0,
            auto_merge_allowed=True,
        ),
        BranchRule(
            pattern="release/*",
            protection_level=ProtectionLevel.STRICT,
            required_reviewers=1,
            required_checks=["unit_tests", "integration_tests"],
            auto_merge_allowed=False,
        ),
        BranchRule(
            pattern="hotfix/*",
            protection_level=ProtectionLevel.STANDARD,
            required_reviewers=1,
            required_checks=["unit_tests"],
            auto_merge_allowed=False,
        ),
        BranchRule(
            pattern="bugfix/*",
            protection_level=ProtectionLevel.NONE,
            required_reviewers=0,
            auto_merge_allowed=True,
        ),
    ]

    def __init__(
        self,
        strategy_type: StrategyType = StrategyType.GITFLOW,
        custom_rules: Optional[List[BranchRule]] = None,
    ):
        """
        Initialize branch strategy.

        Args:
            strategy_type: Type of branching strategy
            custom_rules: Optional custom branch rules
        """
        self.strategy_type = strategy_type
        self._rules: Dict[str, BranchRule] = {}

        if custom_rules:
            for rule in custom_rules:
                self._rules[rule.pattern] = rule
        else:
            self._initialize_default_rules()

        logger.info(f"BranchStrategy initialized: {strategy_type.value}")

    def _initialize_default_rules(self) -> None:
        """Initialize default rules based on strategy type."""
        if self.strategy_type == StrategyType.GITFLOW:
            for rule in self.GITFLOW_RULES:
                self._rules[rule.pattern] = rule
        elif self.strategy_type == StrategyType.TRUNK_BASED:
            self._rules["main"] = BranchRule(
                pattern="main",
                protection_level=ProtectionLevel.FULL,
                required_reviewers=1,
                required_checks=["unit_tests"],
                auto_merge_allowed=True,
            )
            self._rules["feature/*"] = BranchRule(
                pattern="feature/*",
                protection_level=ProtectionLevel.NONE,
            )

    def get_branch_rules(self, pattern: str) -> Optional[BranchRule]:
        """
        Get rules for branch pattern.

        Args:
            pattern: Branch pattern

        Returns:
            Branch rule or None if not found
        """
        return self._rules.get(pattern)

    def add_rule(self, rule: BranchRule) -> None:
        """
        Add or update branch rule.

        Args:
            rule: Branch rule to add
        """
        self._rules[rule.pattern] = rule
        logger.info(f"Branch rule added/updated: {rule.pattern}")

    def remove_rule(self, pattern: str) -> bool:
        """
        Remove branch rule.

        Args:
            pattern: Branch pattern to remove

        Returns:
            True if removed, False if not found
        """
        if pattern in self._rules:
            del self._rules[pattern]
            logger.info(f"Branch rule removed: {pattern}")
            return True
        return False

    def list_rules(self) -> List[BranchRule]:
        """
        List all branch rules.

        Returns:
            List of branch rules
        """
        return list(self._rules.values())

    def find_matching_rule(self, branch_name: str) -> Optional[BranchRule]:
        """
        Find the rule that matches a branch name.

        Args:
            branch_name: Branch name to match

        Returns:
            Matching rule or None
        """
        for rule in self._rules.values():
            if rule.matches(branch_name):
                return rule
        return None

    def validate_branch_name(self, name: str) -> BranchValidationResult:
        """
        Validate branch name against strategy.

        Args:
            name: Branch name to validate

        Returns:
            Validation result with details
        """
        errors = []
        suggestions = []

        # Basic validation
        if not name or not name.strip():
            return BranchValidationResult(
                valid=False,
                errors=["Branch name cannot be empty"]
            )

        # Check for invalid characters (allow dots for version numbers)
        if not re.match(r"^[a-zA-Z0-9/_.-]+$", name):
            errors.append("Branch name contains invalid characters")
            suggestions.append("Use only letters, numbers, /, _, -, and .")

        # Check if matches any rule
        matched_rule = self.find_matching_rule(name)

        if matched_rule:
            branch_type = self._get_branch_type(name)
            return BranchValidationResult(
                valid=len(errors) == 0,
                branch_type=branch_type,
                matched_rule=matched_rule,
                errors=errors,
                suggestions=suggestions,
            )

        # No matching rule found
        if self.strategy_type == StrategyType.GITFLOW:
            suggestions.extend([
                "Use 'feature/<name>' for new features",
                "Use 'bugfix/<name>' for bug fixes",
                "Use 'release/<version>' for releases",
                "Use 'hotfix/<name>' for emergency fixes",
            ])

        return BranchValidationResult(
            valid=False,
            errors=errors + ["Branch name does not match any configured pattern"],
            suggestions=suggestions,
        )

    def _get_branch_type(self, branch_name: str) -> str:
        """Get branch type from name."""
        if "/" in branch_name:
            return branch_name.split("/")[0]
        return branch_name

    def get_merge_target(self, source_branch: str) -> Optional[str]:
        """
        Get appropriate merge target for source branch.

        Args:
            source_branch: Source branch name

        Returns:
            Target branch name or None
        """
        if self.strategy_type == StrategyType.GITFLOW:
            branch_type = self._get_branch_type(source_branch)

            merge_targets = {
                "feature": "develop",
                "bugfix": "develop",
                "release": "main",
                "hotfix": "main",
                "develop": "main",
            }

            return merge_targets.get(branch_type)

        elif self.strategy_type == StrategyType.TRUNK_BASED:
            return "main"

        return None

    def get_required_reviewers(self, branch_name: str) -> int:
        """
        Get required reviewer count for branch.

        Args:
            branch_name: Branch name

        Returns:
            Required reviewer count
        """
        rule = self.find_matching_rule(branch_name)
        return rule.required_reviewers if rule else 0

    def get_required_checks(self, branch_name: str) -> List[str]:
        """
        Get required status checks for branch.

        Args:
            branch_name: Branch name

        Returns:
            List of required check names
        """
        rule = self.find_matching_rule(branch_name)
        return rule.required_checks if rule else []

    def is_auto_merge_allowed(self, branch_name: str) -> bool:
        """
        Check if auto-merge is allowed for branch.

        Args:
            branch_name: Branch name

        Returns:
            True if auto-merge is allowed
        """
        rule = self.find_matching_rule(branch_name)
        return rule.auto_merge_allowed if rule else False

    def to_dict(self) -> Dict:
        """Convert strategy to dictionary."""
        return {
            "strategy_type": self.strategy_type.value,
            "rules": {pattern: rule.to_dict() for pattern, rule in self._rules.items()},
        }
