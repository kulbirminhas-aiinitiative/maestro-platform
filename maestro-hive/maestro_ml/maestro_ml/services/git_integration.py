#!/usr/bin/env python3
"""
Git Integration Service - Team Metrics Collection

Collects development metrics from Git repositories:
- Commit frequency and patterns
- Pull request metrics
- Code churn and collaboration
- Contributor activity
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import subprocess
import re
from dataclasses import dataclass


@dataclass
class GitMetrics:
    """Git repository metrics"""
    commits_per_week: float
    unique_contributors: int
    avg_pr_merge_time_hours: float
    code_churn_rate: float
    collaboration_score: float
    active_branches: int
    metadata: Dict[str, Any]


class GitIntegration:
    """Service for collecting Git repository metrics"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    async def collect_metrics(
        self,
        since_days: int = 7
    ) -> GitMetrics:
        """
        Collect Git metrics for the past N days

        Args:
            since_days: Number of days to look back for metrics

        Returns:
            GitMetrics object with collected metrics
        """
        since_date = datetime.now() - timedelta(days=since_days)
        since_str = since_date.strftime("%Y-%m-%d")

        # Collect various metrics
        commits_count = await self._count_commits(since_str)
        contributors = await self._count_unique_contributors(since_str)
        branches = await self._count_active_branches()
        churn = await self._calculate_code_churn(since_str)
        collaboration = await self._calculate_collaboration_score(since_str)

        # Calculate weekly rate
        weeks = since_days / 7.0
        commits_per_week = commits_count / weeks if weeks > 0 else 0.0

        return GitMetrics(
            commits_per_week=commits_per_week,
            unique_contributors=contributors,
            avg_pr_merge_time_hours=0.0,  # Requires GitHub/GitLab API
            code_churn_rate=churn,
            collaboration_score=collaboration,
            active_branches=branches,
            metadata={
                "repo_path": self.repo_path,
                "since_date": since_str,
                "collection_date": datetime.now().isoformat()
            }
        )

    async def _count_commits(self, since: str) -> int:
        """Count commits since a given date"""
        try:
            cmd = [
                "git", "-C", self.repo_path,
                "rev-list", "--count",
                f"--since={since}",
                "HEAD"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0

    async def _count_unique_contributors(self, since: str) -> int:
        """Count unique contributors since a given date"""
        try:
            cmd = [
                "git", "-C", self.repo_path,
                "log", f"--since={since}",
                "--format=%ae"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            emails = set(result.stdout.strip().split("\n"))
            return len([e for e in emails if e])
        except subprocess.CalledProcessError:
            return 0

    async def _count_active_branches(self) -> int:
        """Count active branches"""
        try:
            cmd = ["git", "-C", self.repo_path, "branch", "-a"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            branches = [b.strip() for b in result.stdout.split("\n") if b.strip()]
            return len(branches)
        except subprocess.CalledProcessError:
            return 0

    async def _calculate_code_churn(self, since: str) -> float:
        """
        Calculate code churn rate (lines added + lines deleted / total lines)

        Returns value between 0-100
        """
        try:
            cmd = [
                "git", "-C", self.repo_path,
                "log", f"--since={since}",
                "--numstat", "--pretty=tformat:"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            total_added = 0
            total_deleted = 0

            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        try:
                            added = int(parts[0]) if parts[0] != "-" else 0
                            deleted = int(parts[1]) if parts[1] != "-" else 0
                            total_added += added
                            total_deleted += deleted
                        except ValueError:
                            continue

            # Calculate churn as percentage
            total_changes = total_added + total_deleted
            if total_changes > 0:
                # Normalize to 0-100 scale (arbitrary scaling)
                churn_rate = min(100.0, (total_changes / 1000.0) * 100)
                return round(churn_rate, 2)
            return 0.0

        except subprocess.CalledProcessError:
            return 0.0

    async def _calculate_collaboration_score(self, since: str) -> float:
        """
        Calculate collaboration score based on:
        - Number of contributors
        - Commits per contributor
        - Branch activity

        Returns value between 0-100
        """
        try:
            contributors = await self._count_unique_contributors(since)
            commits = await self._count_commits(since)
            branches = await self._count_active_branches()

            if contributors == 0:
                return 0.0

            # Calculate metrics
            commits_per_contributor = commits / contributors
            branch_diversity = min(branches / 10.0, 1.0)  # Normalize to 0-1

            # Weighted score
            score = (
                (min(contributors / 10.0, 1.0) * 40) +  # 40% weight on team size
                (min(commits_per_contributor / 20.0, 1.0) * 40) +  # 40% on activity
                (branch_diversity * 20)  # 20% on branch diversity
            )

            return round(score, 2)

        except Exception:
            return 0.0

    async def get_commit_authors(
        self,
        since_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get list of commit authors with their contribution stats

        Returns:
            List of author dictionaries with name, email, and commit count
        """
        since_date = datetime.now() - timedelta(days=since_days)
        since_str = since_date.strftime("%Y-%m-%d")

        try:
            cmd = [
                "git", "-C", self.repo_path,
                "log", f"--since={since_str}",
                "--format=%an|%ae"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Count commits per author
            author_commits: Dict[str, Dict[str, Any]] = {}
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    name, email = line.split("|", 1)
                    key = email.lower()
                    if key not in author_commits:
                        author_commits[key] = {
                            "name": name,
                            "email": email,
                            "commits": 0
                        }
                    author_commits[key]["commits"] += 1

            return list(author_commits.values())

        except subprocess.CalledProcessError:
            return []

    async def detect_collaboration_patterns(
        self,
        since_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect collaboration patterns:
        - Pair programming indicators
        - Code review activity
        - Cross-team contributions
        """
        authors = await self.get_commit_authors(since_days)
        metrics = await self.collect_metrics(since_days)

        # Detect patterns
        has_pair_programming = len(authors) > 1 and metrics.commits_per_week > 10
        high_collaboration = metrics.collaboration_score > 70

        return {
            "pair_programming_likely": has_pair_programming,
            "high_collaboration": high_collaboration,
            "team_size": len(authors),
            "collaboration_score": metrics.collaboration_score,
            "patterns": {
                "distributed_team": len(authors) > 5,
                "solo_developer": len(authors) == 1,
                "small_team": 2 <= len(authors) <= 5
            }
        }


class GitHubIntegration:
    """
    Integration with GitHub API for PR metrics

    Requires GitHub token for API access
    """

    def __init__(self, token: str, repo: str):
        """
        Initialize GitHub integration

        Args:
            token: GitHub personal access token
            repo: Repository in format "owner/repo"
        """
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"

    async def get_pr_metrics(
        self,
        since_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get Pull Request metrics from GitHub

        Returns:
            Dictionary with PR metrics including merge times, review counts, etc.
        """
        # This would use httpx/aiohttp to call GitHub API
        # Placeholder for now - will be implemented with actual API calls

        return {
            "avg_pr_merge_time_hours": 4.5,
            "total_prs": 25,
            "merged_prs": 23,
            "pr_success_rate": 0.92,
            "avg_review_comments": 3.2,
            "avg_reviewers_per_pr": 2.1
        }


class GitLabIntegration:
    """
    Integration with GitLab API for MR metrics

    Requires GitLab token for API access
    """

    def __init__(self, token: str, project_id: int):
        """
        Initialize GitLab integration

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID
        """
        self.token = token
        self.project_id = project_id
        self.base_url = "https://gitlab.com/api/v4"

    async def get_mr_metrics(
        self,
        since_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get Merge Request metrics from GitLab

        Returns:
            Dictionary with MR metrics
        """
        # Placeholder - will be implemented with actual API calls

        return {
            "avg_mr_merge_time_hours": 5.2,
            "total_mrs": 20,
            "merged_mrs": 19,
            "mr_success_rate": 0.95,
            "avg_review_comments": 4.1,
            "avg_reviewers_per_mr": 2.0
        }
