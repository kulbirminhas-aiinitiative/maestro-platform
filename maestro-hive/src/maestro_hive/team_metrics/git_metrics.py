#!/usr/bin/env python3
"""
Git Metrics Provider: Fetches commit and code review metrics from Git.

Implements AC-8: Git integration via git_tool.py for commit metrics.
"""

import logging
import os
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GitConfig:
    """Git repository configuration."""
    repo_path: str
    default_branch: str = "main"

    @classmethod
    def from_env(cls) -> 'GitConfig':
        """Load configuration from environment variables."""
        return cls(
            repo_path=os.getenv('GIT_REPO_PATH', os.getcwd()),
            default_branch=os.getenv('GIT_DEFAULT_BRANCH', 'main')
        )


@dataclass
class CommitMetrics:
    """Commit activity metrics."""
    team_id: str
    period_days: int
    total_commits: int
    commits_per_day: float
    unique_authors: int
    files_changed: int
    lines_added: int
    lines_deleted: int
    net_lines: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodeReviewMetrics:
    """Code review metrics."""
    team_id: str
    period_days: int
    prs_opened: int
    prs_merged: int
    prs_closed: int
    average_review_time_hours: float
    average_comments_per_pr: float
    review_coverage: float  # % of PRs with reviews

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuthorStats:
    """Individual author statistics."""
    author_name: str
    author_email: str
    commit_count: int
    lines_added: int
    lines_deleted: int
    files_touched: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GitMetricsProvider:
    """
    Fetches metrics from Git repositories.

    Implements AC-8: Git integration for commit metrics.
    """

    def __init__(self, config: Optional[GitConfig] = None):
        self.config = config or GitConfig.from_env()

    def get_commit_metrics(
        self,
        team_id: str,
        days: int = 30,
        repo_path: Optional[str] = None
    ) -> Optional[CommitMetrics]:
        """
        Get commit metrics for a time period.

        AC-8: Git integration for commit metrics.
        """
        try:
            path = repo_path or self.config.repo_path
            since_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            # Get commit count
            commit_count = self._run_git_command(
                path,
                ['git', 'rev-list', '--count', f'--since={since_date}', 'HEAD']
            )
            total_commits = int(commit_count.strip()) if commit_count else 0

            # Get unique authors
            authors_output = self._run_git_command(
                path,
                ['git', 'log', f'--since={since_date}', '--format=%ae']
            )
            unique_authors = len(set(authors_output.strip().split('\n'))) if authors_output.strip() else 0

            # Get diff stats
            diff_stats = self._run_git_command(
                path,
                ['git', 'diff', '--stat', f'--since={since_date}', f'{self.config.default_branch}@{{0}}', f'{self.config.default_branch}']
            )

            # Parse diff stats (simplified)
            lines_added = 0
            lines_deleted = 0
            files_changed = 0

            # Get shortstat for accurate counts
            shortstat = self._run_git_command(
                path,
                ['git', 'log', f'--since={since_date}', '--shortstat', '--format=']
            )

            if shortstat:
                for line in shortstat.strip().split('\n'):
                    if 'file' in line:
                        parts = line.split(',')
                        for part in parts:
                            part = part.strip()
                            if 'file' in part:
                                try:
                                    files_changed += int(part.split()[0])
                                except (ValueError, IndexError):
                                    pass
                            elif 'insertion' in part:
                                try:
                                    lines_added += int(part.split()[0])
                                except (ValueError, IndexError):
                                    pass
                            elif 'deletion' in part:
                                try:
                                    lines_deleted += int(part.split()[0])
                                except (ValueError, IndexError):
                                    pass

            commits_per_day = total_commits / days if days > 0 else 0

            return CommitMetrics(
                team_id=team_id,
                period_days=days,
                total_commits=total_commits,
                commits_per_day=round(commits_per_day, 2),
                unique_authors=unique_authors,
                files_changed=files_changed,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                net_lines=lines_added - lines_deleted
            )

        except Exception as e:
            logger.error(f"Error fetching commit metrics: {e}")
            return None

    def get_author_stats(
        self,
        team_id: str,
        days: int = 30,
        repo_path: Optional[str] = None
    ) -> List[AuthorStats]:
        """Get per-author statistics."""
        try:
            path = repo_path or self.config.repo_path
            since_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            # Get author commit counts
            author_output = self._run_git_command(
                path,
                ['git', 'shortlog', '-sne', f'--since={since_date}', 'HEAD']
            )

            authors = []
            if author_output:
                for line in author_output.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        parts = line.strip().split('\t')
                        count = int(parts[0].strip())
                        author_info = parts[1] if len(parts) > 1 else "Unknown"

                        # Parse name and email
                        if '<' in author_info:
                            name = author_info.split('<')[0].strip()
                            email = author_info.split('<')[1].rstrip('>')
                        else:
                            name = author_info
                            email = ""

                        authors.append(AuthorStats(
                            author_name=name,
                            author_email=email,
                            commit_count=count,
                            lines_added=0,  # Would require per-author diff analysis
                            lines_deleted=0,
                            files_touched=0
                        ))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing author line: {e}")
                        continue

            return authors

        except Exception as e:
            logger.error(f"Error fetching author stats: {e}")
            return []

    def get_branch_metrics(
        self,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get branch-related metrics."""
        try:
            path = repo_path or self.config.repo_path

            # Count branches
            branches_output = self._run_git_command(
                path,
                ['git', 'branch', '-r']
            )

            branch_count = len([b for b in branches_output.strip().split('\n') if b.strip()]) if branches_output else 0

            # Get stale branches (no commits in 30 days)
            stale_count = 0  # Would require more complex analysis

            return {
                'total_branches': branch_count,
                'stale_branches': stale_count,
                'default_branch': self.config.default_branch
            }

        except Exception as e:
            logger.error(f"Error fetching branch metrics: {e}")
            return {}

    def get_code_review_metrics(
        self,
        team_id: str,
        days: int = 30
    ) -> Optional[CodeReviewMetrics]:
        """
        Get code review metrics.

        Note: This requires GitHub/GitLab API integration for full PR metrics.
        This implementation provides a placeholder structure.
        """
        # Placeholder - would integrate with GitHub/GitLab API
        return CodeReviewMetrics(
            team_id=team_id,
            period_days=days,
            prs_opened=0,
            prs_merged=0,
            prs_closed=0,
            average_review_time_hours=0.0,
            average_comments_per_pr=0.0,
            review_coverage=0.0
        )

    def _run_git_command(self, repo_path: str, command: List[str]) -> Optional[str]:
        """Execute a git command and return output."""
        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.debug(f"Git command failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return None


def get_git_metrics_provider(**kwargs) -> GitMetricsProvider:
    """Get Git metrics provider instance."""
    config = GitConfig(**kwargs) if kwargs else None
    return GitMetricsProvider(config=config)
