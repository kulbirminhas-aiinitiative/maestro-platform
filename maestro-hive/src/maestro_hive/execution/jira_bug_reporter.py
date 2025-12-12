"""
JIRA Bug Reporter - Automatic bug reporting integration.

This module provides the JiraBugReporter class that automatically creates
JIRA bugs from execution failures.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3030 - Implement JiraBugReporter
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BugPriority(Enum):
    """JIRA bug priority levels."""
    HIGHEST = "1"
    HIGH = "2"
    MEDIUM = "3"
    LOW = "4"
    LOWEST = "5"


class BugStatus(Enum):
    """Bug reporting status."""
    PENDING = "pending"
    CREATED = "created"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class JiraConfig:
    """Configuration for JIRA integration."""
    base_url: str
    email: str
    api_token: str
    project_key: str = "MD"
    issue_type: str = "Bug"
    default_labels: List[str] = field(default_factory=lambda: ["auto-reported", "self-healing"])
    enable_deduplication: bool = True
    dedup_window_hours: int = 24


@dataclass
class BugReport:
    """A bug report to be created in JIRA."""
    title: str
    description: str
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    execution_id: Optional[str] = None
    severity: str = "medium"
    priority: BugPriority = BugPriority.MEDIUM
    labels: List[str] = field(default_factory=list)
    additional_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_error_hash(self) -> str:
        """Generate a hash for deduplication."""
        content = f"{self.error_type}:{self.error_message[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_jira_payload(self, config: JiraConfig) -> Dict[str, Any]:
        """Convert to JIRA API payload format."""
        description_content = []

        # Summary paragraph
        description_content.append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Auto-generated bug report from Self-Healing Execution Loop", "marks": [{"type": "strong"}]}
            ]
        })

        # Error details
        description_content.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Error Details"}]
        })

        description_content.append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": f"Error Type: {self.error_type}"}
            ]
        })

        description_content.append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": f"Error Message: {self.error_message[:500]}"}
            ]
        })

        if self.execution_id:
            description_content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"Execution ID: {self.execution_id}"}
                ]
            })

        # Traceback
        if self.traceback:
            description_content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Traceback"}]
            })
            description_content.append({
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{"type": "text", "text": self.traceback[:2000]}]
            })

        # Metadata
        description_content.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Metadata"}]
        })

        description_content.append({
            "type": "bulletList",
            "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Created: {self.created_at.isoformat()}"}]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Severity: {self.severity}"}]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Error Hash: {self.get_error_hash()}"}]}]},
            ]
        })

        return {
            "fields": {
                "project": {"key": config.project_key},
                "issuetype": {"name": config.issue_type},
                "summary": self.title[:255],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": description_content
                },
                "priority": {"id": self.priority.value},
                "labels": list(set(config.default_labels + self.labels)),
                **self.additional_fields,
            }
        }


@dataclass
class BugReportResult:
    """Result of a bug report attempt."""
    status: BugStatus
    bug_key: Optional[str] = None
    bug_url: Optional[str] = None
    duplicate_of: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "bug_key": self.bug_key,
            "bug_url": self.bug_url,
            "duplicate_of": self.duplicate_of,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


class JiraBugReporter:
    """
    Automatically reports bugs to JIRA from execution failures.

    Features:
    - Automatic bug creation with rich formatting
    - Deduplication to avoid duplicate bugs
    - Priority mapping from error severity
    - Traceback and context inclusion

    Example:
        >>> config = JiraConfig(
        ...     base_url="https://company.atlassian.net",
        ...     email="user@company.com",
        ...     api_token="token",
        ...     project_key="PROJ"
        ... )
        >>> reporter = JiraBugReporter(config)
        >>> result = await reporter.report(
        ...     title="API timeout in data processing",
        ...     error_type="TimeoutError",
        ...     error_message="Request timed out after 30s"
        ... )
        >>> print(result.bug_key)  # PROJ-123
    """

    def __init__(self, config: JiraConfig):
        """
        Initialize the bug reporter.

        Args:
            config: JIRA configuration
        """
        self.config = config
        self._auth_header = self._create_auth_header()
        self._reported_hashes: Dict[str, str] = {}  # hash -> bug_key
        self._report_history: List[BugReportResult] = []

        logger.info(f"JiraBugReporter initialized for project {config.project_key}")

    def _create_auth_header(self) -> str:
        """Create Basic auth header."""
        credentials = f"{self.config.email}:{self.config.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _check_duplicate(self, error_hash: str) -> Optional[str]:
        """
        Check if a bug with this error hash already exists.

        Returns:
            Bug key if duplicate found, None otherwise
        """
        if not self.config.enable_deduplication:
            return None

        # Check local cache first
        if error_hash in self._reported_hashes:
            return self._reported_hashes[error_hash]

        # Search JIRA for existing bug
        jql = (
            f'project = {self.config.project_key} '
            f'AND labels = "auto-reported" '
            f'AND text ~ "{error_hash}" '
            f'AND created >= -{self.config.dedup_window_hours}h'
        )

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.base_url}/rest/api/3/search/jql",
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                    json={"jql": jql, "maxResults": 1, "fields": ["key"]},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("issues"):
                            bug_key = data["issues"][0]["key"]
                            self._reported_hashes[error_hash] = bug_key
                            return bug_key
            except Exception as e:
                logger.warning(f"Duplicate check failed: {e}")

        return None

    async def report(
        self,
        title: str,
        error_type: str,
        error_message: str,
        traceback: Optional[str] = None,
        execution_id: Optional[str] = None,
        severity: str = "medium",
        labels: Optional[List[str]] = None,
    ) -> BugReportResult:
        """
        Report a bug to JIRA.

        Args:
            title: Bug title/summary
            error_type: Type of error (e.g., "TimeoutError")
            error_message: Error message
            traceback: Optional traceback string
            execution_id: Optional execution ID for tracing
            severity: Error severity (low, medium, high, critical)
            labels: Additional labels

        Returns:
            BugReportResult with status and bug key if created
        """
        # Create bug report
        priority_map = {
            "critical": BugPriority.HIGHEST,
            "high": BugPriority.HIGH,
            "medium": BugPriority.MEDIUM,
            "low": BugPriority.LOW,
        }

        report = BugReport(
            title=title,
            description="",
            error_type=error_type,
            error_message=error_message,
            traceback=traceback,
            execution_id=execution_id,
            severity=severity,
            priority=priority_map.get(severity, BugPriority.MEDIUM),
            labels=labels or [],
        )

        error_hash = report.get_error_hash()

        # Check for duplicates
        duplicate_key = await self._check_duplicate(error_hash)
        if duplicate_key:
            result = BugReportResult(
                status=BugStatus.DUPLICATE,
                duplicate_of=duplicate_key,
            )
            self._report_history.append(result)
            logger.info(f"Skipped duplicate bug (existing: {duplicate_key})")
            return result

        # Create bug in JIRA
        payload = report.to_jira_payload(self.config)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.base_url}/rest/api/3/issue",
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    if response.status in (200, 201):
                        data = await response.json()
                        bug_key = data["key"]

                        # Cache the hash
                        self._reported_hashes[error_hash] = bug_key

                        result = BugReportResult(
                            status=BugStatus.CREATED,
                            bug_key=bug_key,
                            bug_url=f"{self.config.base_url}/browse/{bug_key}",
                        )
                        self._report_history.append(result)
                        logger.info(f"Created JIRA bug: {bug_key}")
                        return result
                    else:
                        error_text = await response.text()
                        result = BugReportResult(
                            status=BugStatus.FAILED,
                            error_message=f"HTTP {response.status}: {error_text[:200]}",
                        )
                        self._report_history.append(result)
                        logger.error(f"Failed to create bug: {error_text[:200]}")
                        return result

            except Exception as e:
                result = BugReportResult(
                    status=BugStatus.FAILED,
                    error_message=str(e),
                )
                self._report_history.append(result)
                logger.error(f"Bug report failed: {e}")
                return result

    async def add_comment(
        self,
        bug_key: str,
        comment: str,
    ) -> bool:
        """
        Add a comment to an existing bug.

        Args:
            bug_key: JIRA issue key (e.g., "PROJ-123")
            comment: Comment text

        Returns:
            True if successful
        """
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.base_url}/rest/api/3/issue/{bug_key}/comment",
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    if response.status in (200, 201):
                        logger.info(f"Added comment to {bug_key}")
                        return True
                    else:
                        logger.error(f"Failed to add comment: HTTP {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Comment failed: {e}")
                return False

    async def update_status(
        self,
        bug_key: str,
        status: str,
    ) -> bool:
        """
        Update bug status (transition).

        Args:
            bug_key: JIRA issue key
            status: Target status name

        Returns:
            True if successful
        """
        # Get available transitions
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.config.base_url}/rest/api/3/issue/{bug_key}/transitions",
                    headers={"Authorization": self._auth_header},
                ) as response:
                    if response.status != 200:
                        return False
                    data = await response.json()

                # Find matching transition
                transition_id = None
                for t in data.get("transitions", []):
                    if t["name"].lower() == status.lower():
                        transition_id = t["id"]
                        break

                if not transition_id:
                    logger.warning(f"Transition '{status}' not found for {bug_key}")
                    return False

                # Execute transition
                async with session.post(
                    f"{self.config.base_url}/rest/api/3/issue/{bug_key}/transitions",
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                    json={"transition": {"id": transition_id}},
                ) as response:
                    if response.status in (200, 204):
                        logger.info(f"Transitioned {bug_key} to {status}")
                        return True

            except Exception as e:
                logger.error(f"Status update failed: {e}")

        return False

    def get_report_history(self) -> List[BugReportResult]:
        """Get history of bug reports."""
        return list(self._report_history)

    def get_statistics(self) -> Dict[str, Any]:
        """Get reporter statistics."""
        status_counts = {}
        for result in self._report_history:
            status_counts[result.status.value] = status_counts.get(result.status.value, 0) + 1

        return {
            "total_reports": len(self._report_history),
            "status_counts": status_counts,
            "cached_hashes": len(self._reported_hashes),
            "project_key": self.config.project_key,
        }

    def clear_cache(self) -> None:
        """Clear the duplicate detection cache."""
        self._reported_hashes.clear()


# Factory function
def create_jira_reporter(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str = "MD",
) -> JiraBugReporter:
    """
    Create a JiraBugReporter with the given configuration.

    Args:
        base_url: JIRA instance URL
        email: User email
        api_token: API token
        project_key: Project key

    Returns:
        Configured JiraBugReporter
    """
    config = JiraConfig(
        base_url=base_url,
        email=email,
        api_token=api_token,
        project_key=project_key,
    )
    return JiraBugReporter(config)
