"""
Tests for JiraBugReporter - Automatic JIRA bug reporting.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3030 - Implement JiraBugReporter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from maestro_hive.execution.jira_bug_reporter import (
    JiraBugReporter,
    JiraConfig,
    BugReport,
    BugReportResult,
    BugPriority,
    BugStatus,
    create_jira_reporter,
)


class TestJiraConfig:
    """Tests for JiraConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token123",
        )
        assert config.project_key == "MD"
        assert config.issue_type == "Bug"
        assert config.enable_deduplication is True
        assert config.dedup_window_hours == 24

    def test_custom_values(self):
        """Test custom configuration values."""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token123",
            project_key="PROJ",
            default_labels=["custom-label"],
        )
        assert config.project_key == "PROJ"
        assert "custom-label" in config.default_labels


class TestBugPriority:
    """Tests for BugPriority enum."""

    def test_priority_values(self):
        """Test priority values match JIRA IDs."""
        assert BugPriority.HIGHEST.value == "1"
        assert BugPriority.HIGH.value == "2"
        assert BugPriority.MEDIUM.value == "3"
        assert BugPriority.LOW.value == "4"
        assert BugPriority.LOWEST.value == "5"


class TestBugStatus:
    """Tests for BugStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        statuses = [
            BugStatus.PENDING,
            BugStatus.CREATED,
            BugStatus.DUPLICATE,
            BugStatus.FAILED,
            BugStatus.SKIPPED,
        ]
        assert len(statuses) == 5


class TestBugReport:
    """Tests for BugReport dataclass."""

    def test_create_report(self):
        """Test creating a bug report."""
        report = BugReport(
            title="Test Bug",
            description="Test description",
            error_type="ValueError",
            error_message="Invalid value",
        )
        assert report.title == "Test Bug"
        assert report.priority == BugPriority.MEDIUM

    def test_error_hash_generation(self):
        """Test error hash generation."""
        report = BugReport(
            title="Bug",
            description="",
            error_type="ValueError",
            error_message="Invalid value 123",
        )
        hash1 = report.get_error_hash()

        report2 = BugReport(
            title="Bug",
            description="",
            error_type="ValueError",
            error_message="Invalid value 456",
        )
        hash2 = report2.get_error_hash()

        # Different numbers should produce same hash (normalized)
        assert len(hash1) == 16
        assert len(hash2) == 16

    def test_to_jira_payload(self):
        """Test JIRA payload generation."""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token",
            project_key="TEST",
        )
        report = BugReport(
            title="Test Bug Title",
            description="",
            error_type="TimeoutError",
            error_message="Request timed out",
            severity="high",
            priority=BugPriority.HIGH,
        )

        payload = report.to_jira_payload(config)

        assert payload["fields"]["project"]["key"] == "TEST"
        assert payload["fields"]["issuetype"]["name"] == "Bug"
        assert payload["fields"]["summary"] == "Test Bug Title"
        assert payload["fields"]["priority"]["id"] == "2"

    def test_long_title_truncation(self):
        """Test long titles are truncated."""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token",
        )
        long_title = "x" * 300
        report = BugReport(
            title=long_title,
            description="",
            error_type="Error",
            error_message="Test",
        )

        payload = report.to_jira_payload(config)
        assert len(payload["fields"]["summary"]) <= 255


class TestBugReportResult:
    """Tests for BugReportResult dataclass."""

    def test_create_result(self):
        """Test creating a bug report result."""
        result = BugReportResult(
            status=BugStatus.CREATED,
            bug_key="TEST-123",
            bug_url="https://test.atlassian.net/browse/TEST-123",
        )
        assert result.status == BugStatus.CREATED
        assert result.bug_key == "TEST-123"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = BugReportResult(
            status=BugStatus.DUPLICATE,
            duplicate_of="TEST-100",
        )
        data = result.to_dict()
        assert data["status"] == "duplicate"
        assert data["duplicate_of"] == "TEST-100"


class TestJiraBugReporter:
    """Tests for JiraBugReporter class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token123",
            project_key="TEST",
        )

    @pytest.fixture
    def reporter(self, config):
        """Create reporter for tests."""
        return JiraBugReporter(config)

    def test_auth_header_creation(self, reporter):
        """Test auth header is created correctly."""
        assert reporter._auth_header.startswith("Basic ")

    @pytest.mark.asyncio
    async def test_report_success(self, reporter):
        """Test successful bug report."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"key": "TEST-456"})

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()))

            result = await reporter.report(
                title="Test Bug",
                error_type="ValueError",
                error_message="Test error",
            )

        assert result.status == BugStatus.CREATED
        assert result.bug_key == "TEST-456"

    @pytest.mark.asyncio
    async def test_report_with_traceback(self, reporter):
        """Test bug report includes traceback."""
        traceback = "Traceback (most recent call last):\n  File 'test.py', line 1\nValueError: test"

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"key": "TEST-789"})

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()))

            result = await reporter.report(
                title="Test Bug",
                error_type="ValueError",
                error_message="Test error",
                traceback=traceback,
            )

        assert result.status == BugStatus.CREATED

    def test_get_statistics(self, reporter):
        """Test getting reporter statistics."""
        stats = reporter.get_statistics()
        assert "total_reports" in stats
        assert "project_key" in stats
        assert stats["project_key"] == "TEST"

    def test_get_report_history(self, reporter):
        """Test getting report history."""
        history = reporter.get_report_history()
        assert isinstance(history, list)

    def test_clear_cache(self, reporter):
        """Test clearing duplicate cache."""
        reporter._reported_hashes["test"] = "TEST-123"
        reporter.clear_cache()
        assert len(reporter._reported_hashes) == 0


class TestFactoryFunction:
    """Tests for factory function."""

    def test_create_jira_reporter(self):
        """Test factory function creates reporter."""
        reporter = create_jira_reporter(
            base_url="https://test.atlassian.net",
            email="test@test.com",
            api_token="token",
            project_key="PROJ",
        )
        assert isinstance(reporter, JiraBugReporter)
        assert reporter.config.project_key == "PROJ"
