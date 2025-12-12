"""
Tests for RepoManager.

EPIC: MD-3022
Child Task: MD-2920
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.maestro_hive.gap_analysis.repo_manager import (
    RepoManager,
    RepoConfig,
    RepoInfo,
    RepoSource,
    RepoStatus,
    CloneResult,
    create_repo_manager,
)


class TestRepoConfig:
    """Tests for RepoConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RepoConfig()
        assert config.cache_dir == "/tmp/maestro_repo_cache"
        assert config.cache_ttl_hours == 24
        assert config.clone_depth == 1
        assert "github.com" in config.allowed_hosts

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RepoConfig(
            cache_dir="/custom/cache",
            cache_ttl_hours=48,
            clone_depth=5,
        )
        assert config.cache_dir == "/custom/cache"
        assert config.cache_ttl_hours == 48
        assert config.clone_depth == 5


class TestRepoInfo:
    """Tests for RepoInfo dataclass."""

    def test_repo_info_creation(self):
        """Test creating RepoInfo."""
        info = RepoInfo(
            url="https://github.com/user/repo",
            local_path="/tmp/repo",
            source=RepoSource.GITHUB,
            status=RepoStatus.READY,
        )
        assert info.url == "https://github.com/user/repo"
        assert info.source == RepoSource.GITHUB
        assert info.status == RepoStatus.READY

    def test_repo_info_to_dict(self):
        """Test RepoInfo serialization."""
        info = RepoInfo(
            url="https://github.com/user/repo",
            local_path="/tmp/repo",
            source=RepoSource.GITHUB,
            status=RepoStatus.READY,
            branch="main",
        )
        result = info.to_dict()
        assert result["url"] == "https://github.com/user/repo"
        assert result["source"] == "github"
        assert result["status"] == "ready"


class TestRepoManager:
    """Tests for RepoManager class."""

    @pytest.fixture
    def manager(self):
        """Create a RepoManager instance."""
        config = RepoConfig(cache_dir=tempfile.mkdtemp())
        return RepoManager(config)

    def test_manager_creation(self, manager):
        """Test manager initialization."""
        assert manager.config is not None
        assert manager._repos == {}

    def test_detect_source_github(self, manager):
        """Test detecting GitHub source."""
        assert manager._detect_source("https://github.com/user/repo") == RepoSource.GITHUB

    def test_detect_source_gitlab(self, manager):
        """Test detecting GitLab source."""
        assert manager._detect_source("https://gitlab.com/user/repo") == RepoSource.GITLAB

    def test_detect_source_bitbucket(self, manager):
        """Test detecting Bitbucket source."""
        assert manager._detect_source("https://bitbucket.org/user/repo") == RepoSource.BITBUCKET

    def test_detect_source_local(self, manager):
        """Test detecting local source."""
        assert manager._detect_source("/local/path") == RepoSource.LOCAL

    def test_detect_source_unknown(self, manager):
        """Test detecting unknown source."""
        assert manager._detect_source("https://unknown.example.com/repo") == RepoSource.UNKNOWN

    def test_is_allowed_host_github(self, manager):
        """Test GitHub is allowed by default."""
        assert manager._is_allowed_host("https://github.com/user/repo") is True

    def test_is_allowed_host_local(self, manager):
        """Test local paths are always allowed."""
        assert manager._is_allowed_host("/local/path") is True

    def test_is_allowed_host_unknown(self, manager):
        """Test unknown hosts are not allowed."""
        assert manager._is_allowed_host("https://malicious.com/repo") is False

    def test_get_cache_key(self, manager):
        """Test cache key generation."""
        key1 = manager._get_cache_key("https://github.com/user/repo", "main")
        key2 = manager._get_cache_key("https://github.com/user/repo", "main")
        key3 = manager._get_cache_key("https://github.com/user/repo", "develop")

        assert key1 == key2  # Same URL and branch
        assert key1 != key3  # Different branch

    def test_clone_local_path(self, manager):
        """Test cloning a local path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = manager.clone(tmpdir)
            assert result.success is True
            assert result.repo_info is not None
            assert result.repo_info.source == RepoSource.LOCAL

    def test_clone_nonexistent_local_path(self, manager):
        """Test cloning nonexistent local path."""
        result = manager.clone("/nonexistent/path/12345")
        assert result.success is False
        assert "does not exist" in result.error

    def test_clone_disallowed_host(self, manager):
        """Test cloning from disallowed host."""
        result = manager.clone("https://malicious.example.com/repo")
        assert result.success is False
        assert "not in allowed list" in result.error

    def test_list_repos_empty(self, manager):
        """Test listing repos when empty."""
        repos = manager.list_repos()
        assert repos == []

    def test_list_repos_after_clone(self, manager):
        """Test listing repos after cloning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager.clone(tmpdir)
            repos = manager.list_repos()
            assert len(repos) == 1

    def test_get_repo_not_found(self, manager):
        """Test getting nonexistent repo."""
        result = manager.get_repo("https://github.com/user/nonexistent")
        assert result is None

    def test_cleanup_all(self, manager):
        """Test cleanup all repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager.clone(tmpdir)
            assert len(manager.list_repos()) == 1
            removed = manager.cleanup_all()
            assert removed == 1
            assert len(manager.list_repos()) == 0

    def test_get_cache_stats(self, manager):
        """Test getting cache statistics."""
        stats = manager.get_cache_stats()
        assert "total_repos" in stats
        assert "cache_dir" in stats
        assert stats["total_repos"] == 0


class TestCloneResult:
    """Tests for CloneResult dataclass."""

    def test_clone_result_success(self):
        """Test successful clone result."""
        result = CloneResult(success=True, duration_seconds=1.5)
        assert result.success is True
        assert result.error is None

    def test_clone_result_failure(self):
        """Test failed clone result."""
        result = CloneResult(success=False, error="Clone failed")
        assert result.success is False
        assert result.error == "Clone failed"


class TestFactoryFunction:
    """Tests for create_repo_manager factory."""

    def test_create_repo_manager_default(self):
        """Test creating manager with defaults."""
        manager = create_repo_manager()
        assert isinstance(manager, RepoManager)

    def test_create_repo_manager_with_config(self):
        """Test creating manager with custom config."""
        import tempfile
        custom_cache = tempfile.mkdtemp()
        manager = create_repo_manager({
            "cache_dir": custom_cache,
            "cache_ttl_hours": 12,
        })
        assert manager.config.cache_dir == custom_cache
        assert manager.config.cache_ttl_hours == 12
