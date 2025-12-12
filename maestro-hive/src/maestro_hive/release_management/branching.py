"""
Branch Manager for Release Management.

This module provides the BranchManager class for managing Git branching
strategy including stable-demo and working-beta branches.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from .models import (
    Branch,
    BranchType,
    ProtectionRules,
    MergeStrategy,
    MergeResult,
)

logger = logging.getLogger(__name__)


class BranchManager:
    """
    Manages Git branching strategy and branch operations.

    Provides functionality to create branches, apply protection rules,
    and manage merges following the defined branching strategy.
    """

    def __init__(self, repo: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the BranchManager.

        Args:
            repo: Repository name or path
            config: Optional configuration dictionary
        """
        self.repo = repo
        self.config = config or {}
        self._branches: Dict[str, Branch] = {}
        self._default_branch = "main"
        self._initialize_default_branches()
        logger.info(f"BranchManager initialized for repo '{repo}'")

    def _initialize_default_branches(self) -> None:
        """Initialize default branch structure."""
        # Main branch
        main_branch = Branch(
            name="main",
            branch_type=BranchType.MAIN,
            is_protected=True,
            protection_rules=ProtectionRules(
                require_reviews=2,
                require_ci=True,
                require_signed=True,
                prevent_force_push=True,
                require_linear_history=True,
            ),
        )
        self._branches["main"] = main_branch

        # Develop branch
        develop_branch = Branch(
            name="develop",
            branch_type=BranchType.DEVELOP,
            source_branch="main",
            is_protected=True,
            protection_rules=ProtectionRules(
                require_reviews=1,
                require_ci=True,
            ),
        )
        self._branches["develop"] = develop_branch

    def create_branch(
        self,
        name: str,
        source: str,
        branch_type: Optional[BranchType] = None,
    ) -> Branch:
        """
        Create a new branch from a source branch.

        Args:
            name: New branch name
            source: Source branch name
            branch_type: Optional branch type (inferred if not provided)

        Returns:
            Created Branch instance

        Raises:
            ValueError: If branch already exists or source not found
        """
        if name in self._branches:
            logger.error(f"Branch '{name}' already exists")
            raise ValueError(f"Branch '{name}' already exists")

        if source not in self._branches:
            logger.error(f"Source branch '{source}' not found")
            raise ValueError(f"Source branch '{source}' not found")

        # Infer branch type if not provided
        if branch_type is None:
            branch_type = self._infer_branch_type(name)

        source_branch = self._branches[source]

        branch = Branch(
            name=name,
            branch_type=branch_type,
            source_branch=source,
            last_commit=source_branch.last_commit,
        )

        self._branches[name] = branch
        logger.info(f"Created branch '{name}' from '{source}'")
        return branch

    def create_stable_demo(self, source: str = "main") -> Branch:
        """
        Create the stable-demo branch.

        Args:
            source: Source branch (default: main)

        Returns:
            Created Branch instance
        """
        if "stable-demo" in self._branches:
            logger.warning("stable-demo branch already exists")
            return self._branches["stable-demo"]

        branch = Branch(
            name="stable-demo",
            branch_type=BranchType.STABLE_DEMO,
            source_branch=source,
            is_protected=True,
            protection_rules=ProtectionRules(
                require_reviews=1,
                require_ci=True,
                prevent_force_push=True,
            ),
        )

        self._branches["stable-demo"] = branch
        logger.info(f"Created stable-demo branch from '{source}'")
        return branch

    def create_working_beta(self, source: str = "develop") -> Branch:
        """
        Create the working-beta branch.

        Args:
            source: Source branch (default: develop)

        Returns:
            Created Branch instance
        """
        if "working-beta" in self._branches:
            logger.warning("working-beta branch already exists")
            return self._branches["working-beta"]

        branch = Branch(
            name="working-beta",
            branch_type=BranchType.WORKING_BETA,
            source_branch=source,
            is_protected=True,
            protection_rules=ProtectionRules(
                require_reviews=1,
                require_ci=True,
            ),
        )

        self._branches["working-beta"] = branch
        logger.info(f"Created working-beta branch from '{source}'")
        return branch

    def get_branch(self, name: str) -> Optional[Branch]:
        """
        Get a branch by name.

        Args:
            name: Branch name

        Returns:
            Branch instance or None if not found
        """
        return self._branches.get(name)

    def list_branches(
        self,
        branch_type: Optional[BranchType] = None,
        protected_only: bool = False,
    ) -> List[Branch]:
        """
        List all branches, optionally filtered.

        Args:
            branch_type: Optional type filter
            protected_only: If True, only return protected branches

        Returns:
            List of Branch instances
        """
        branches = list(self._branches.values())

        if branch_type is not None:
            branches = [b for b in branches if b.branch_type == branch_type]

        if protected_only:
            branches = [b for b in branches if b.is_protected]

        return branches

    def delete_branch(self, name: str, force: bool = False) -> bool:
        """
        Delete a branch.

        Args:
            name: Branch name
            force: Force deletion of protected branches

        Returns:
            True if deleted, False otherwise
        """
        branch = self._branches.get(name)
        if branch is None:
            logger.warning(f"Branch '{name}' not found")
            return False

        if branch.is_protected and not force:
            logger.error(f"Cannot delete protected branch '{name}'")
            return False

        if branch.protection_rules and not branch.protection_rules.allow_deletions:
            if not force:
                logger.error(f"Branch '{name}' has deletions disabled")
                return False

        del self._branches[name]
        logger.info(f"Deleted branch '{name}'")
        return True

    def apply_protection(
        self,
        branch_name: str,
        rules: ProtectionRules,
    ) -> bool:
        """
        Apply protection rules to a branch.

        Args:
            branch_name: Branch name
            rules: Protection rules to apply

        Returns:
            True if applied, False if branch not found
        """
        branch = self._branches.get(branch_name)
        if branch is None:
            logger.warning(f"Branch '{branch_name}' not found")
            return False

        branch.protection_rules = rules
        branch.is_protected = True
        logger.info(f"Applied protection rules to branch '{branch_name}'")
        return True

    def remove_protection(self, branch_name: str) -> bool:
        """
        Remove protection from a branch.

        Args:
            branch_name: Branch name

        Returns:
            True if removed, False if branch not found
        """
        branch = self._branches.get(branch_name)
        if branch is None:
            logger.warning(f"Branch '{branch_name}' not found")
            return False

        branch.protection_rules = None
        branch.is_protected = False
        logger.info(f"Removed protection from branch '{branch_name}'")
        return True

    def merge(
        self,
        source: str,
        target: str,
        strategy: MergeStrategy = MergeStrategy.MERGE,
        message: Optional[str] = None,
    ) -> MergeResult:
        """
        Merge source branch into target branch.

        Args:
            source: Source branch name
            target: Target branch name
            strategy: Merge strategy to use
            message: Optional merge commit message

        Returns:
            MergeResult with success status and details
        """
        source_branch = self._branches.get(source)
        target_branch = self._branches.get(target)

        if source_branch is None:
            return MergeResult(
                success=False,
                source_branch=source,
                target_branch=target,
                error=f"Source branch '{source}' not found",
            )

        if target_branch is None:
            return MergeResult(
                success=False,
                source_branch=source,
                target_branch=target,
                error=f"Target branch '{target}' not found",
            )

        # Check protection rules
        if target_branch.protection_rules:
            # Validate merge strategy is allowed
            if target_branch.protection_rules.require_linear_history:
                if strategy not in [MergeStrategy.SQUASH, MergeStrategy.REBASE]:
                    return MergeResult(
                        success=False,
                        source_branch=source,
                        target_branch=target,
                        error="Target branch requires linear history (use squash or rebase)",
                    )

        # Simulate merge
        commit_sha = str(uuid.uuid4())[:8]

        # Update target branch
        target_branch.last_commit = commit_sha
        target_branch.last_commit_at = datetime.utcnow()

        logger.info(f"Merged '{source}' into '{target}' using {strategy.value}")
        return MergeResult(
            success=True,
            source_branch=source,
            target_branch=target,
            commit_sha=commit_sha,
            strategy_used=strategy,
            merged_at=datetime.utcnow(),
        )

    def sync_branch(
        self,
        branch_name: str,
        source: Optional[str] = None,
    ) -> MergeResult:
        """
        Sync a branch with its source or specified source.

        Args:
            branch_name: Branch to sync
            source: Optional specific source (uses branch's source if not provided)

        Returns:
            MergeResult with sync status
        """
        branch = self._branches.get(branch_name)
        if branch is None:
            return MergeResult(
                success=False,
                source_branch=source or "",
                target_branch=branch_name,
                error=f"Branch '{branch_name}' not found",
            )

        sync_source = source or branch.source_branch
        if sync_source is None:
            return MergeResult(
                success=False,
                source_branch="",
                target_branch=branch_name,
                error="No source branch specified for sync",
            )

        return self.merge(sync_source, branch_name, MergeStrategy.MERGE)

    def get_branch_status(self, name: str) -> Dict[str, Any]:
        """
        Get detailed status of a branch.

        Args:
            name: Branch name

        Returns:
            Dictionary with branch status details
        """
        branch = self._branches.get(name)
        if branch is None:
            return {"error": f"Branch '{name}' not found"}

        return {
            "name": branch.name,
            "type": branch.branch_type.value,
            "is_protected": branch.is_protected,
            "source_branch": branch.source_branch,
            "last_commit": branch.last_commit,
            "last_commit_at": (
                branch.last_commit_at.isoformat() if branch.last_commit_at else None
            ),
            "protection_rules": (
                {
                    "require_reviews": branch.protection_rules.require_reviews,
                    "require_ci": branch.protection_rules.require_ci,
                    "require_signed": branch.protection_rules.require_signed,
                    "prevent_force_push": branch.protection_rules.prevent_force_push,
                }
                if branch.protection_rules
                else None
            ),
        }

    def validate_merge(
        self,
        source: str,
        target: str,
    ) -> Dict[str, Any]:
        """
        Validate if a merge is allowed between branches.

        Args:
            source: Source branch name
            target: Target branch name

        Returns:
            Dictionary with validation results
        """
        source_branch = self._branches.get(source)
        target_branch = self._branches.get(target)

        if source_branch is None:
            return {
                "valid": False,
                "error": f"Source branch '{source}' not found",
            }

        if target_branch is None:
            return {
                "valid": False,
                "error": f"Target branch '{target}' not found",
            }

        issues = []

        if target_branch.protection_rules:
            rules = target_branch.protection_rules

            if rules.require_reviews > 0:
                issues.append(f"Requires {rules.require_reviews} review(s)")

            if rules.require_ci:
                issues.append("Requires CI to pass")

            if rules.require_signed:
                issues.append("Requires signed commits")

        return {
            "valid": True,
            "source": source,
            "target": target,
            "requirements": issues,
            "target_protected": target_branch.is_protected,
        }

    def _infer_branch_type(self, name: str) -> BranchType:
        """Infer branch type from name."""
        name_lower = name.lower()

        if name_lower.startswith("feature/") or name_lower.startswith("feat/"):
            return BranchType.FEATURE
        elif name_lower.startswith("release/"):
            return BranchType.RELEASE
        elif name_lower.startswith("hotfix/") or name_lower.startswith("fix/"):
            return BranchType.HOTFIX
        elif name_lower == "main" or name_lower == "master":
            return BranchType.MAIN
        elif name_lower == "develop" or name_lower == "dev":
            return BranchType.DEVELOP
        elif "stable" in name_lower or "demo" in name_lower:
            return BranchType.STABLE_DEMO
        elif "beta" in name_lower or "working" in name_lower:
            return BranchType.WORKING_BETA

        return BranchType.FEATURE
