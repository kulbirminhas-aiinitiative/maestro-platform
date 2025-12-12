#!/usr/bin/env python3
"""
Tests for CLI Path Resolver
MD-3068: Part of EPIC MD-3089 - Core Platform Stability & Tooling
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path


# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from maestro_hive.teams.cli_path_resolver import (
    CLIPathResolver,
    PathResolutionError,
    get_claude_cli_path,
    get_claude_cli_path_safe,
    is_claude_available,
)


class TestCLIPathResolver:
    """Test suite for CLIPathResolver class."""

    def setup_method(self):
        """Reset singleton before each test."""
        CLIPathResolver.reset()

    def test_singleton_pattern(self):
        """Test that CLIPathResolver is a singleton."""
        resolver1 = CLIPathResolver()
        resolver2 = CLIPathResolver()
        assert resolver1 is resolver2

    def test_reset_clears_cache(self):
        """Test that reset clears the cached path."""
        resolver = CLIPathResolver()
        resolver._cached_path = "/fake/path"
        resolver._resolved = True

        CLIPathResolver.reset()

        assert resolver._cached_path is None
        assert resolver._resolved is False

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '', 'NVM_DIR': '/nonexistent'}, clear=False)
    @patch('shutil.which', return_value=None)
    @patch('os.path.isfile', return_value=False)
    @patch('os.access', return_value=False)
    def test_resolve_raises_when_not_found(self, mock_access, mock_isfile, mock_which):
        """Test that PathResolutionError is raised when CLI not found."""
        resolver = CLIPathResolver()

        with pytest.raises(PathResolutionError) as exc_info:
            resolver.resolve()

        assert "Claude CLI not found" in str(exc_info.value)

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '/custom/path/claude'}, clear=False)
    @patch('os.path.isfile', return_value=True)
    @patch('os.access', return_value=True)
    def test_explicit_env_path_takes_priority(self, mock_access, mock_isfile):
        """Test that CLAUDE_CLI_PATH environment variable is used first."""
        resolver = CLIPathResolver()
        result = resolver.resolve()

        assert result == '/custom/path/claude'

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': ''}, clear=False)
    @patch('shutil.which', return_value='/usr/bin/claude')
    def test_which_path_used_when_available(self, mock_which):
        """Test that shutil.which result is used when available."""
        resolver = CLIPathResolver()
        result = resolver.resolve()

        assert result == '/usr/bin/claude'
        mock_which.assert_called_once_with('claude')

    def test_resolve_caches_result(self):
        """Test that resolve caches the result."""
        resolver = CLIPathResolver()

        with patch('shutil.which', return_value='/usr/bin/claude') as mock_which:
            result1 = resolver.resolve()
            result2 = resolver.resolve()

        # Should only call which once due to caching
        assert mock_which.call_count == 1
        assert result1 == result2

    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh=True bypasses cache."""
        resolver = CLIPathResolver()

        with patch('shutil.which', return_value='/usr/bin/claude') as mock_which:
            result1 = resolver.resolve()
            result2 = resolver.resolve(force_refresh=True)

        # Should call which twice due to force refresh
        assert mock_which.call_count == 2

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '', 'NVM_DIR': '/nonexistent'}, clear=False)
    @patch('shutil.which', return_value=None)
    @patch('os.path.isfile', return_value=False)
    @patch('os.access', return_value=False)
    def test_resolve_or_default_returns_default(self, mock_access, mock_isfile, mock_which):
        """Test resolve_or_default returns default when CLI not found."""
        resolver = CLIPathResolver()
        result = resolver.resolve_or_default("fallback")

        assert result == "fallback"

    @patch('shutil.which', return_value='/usr/bin/claude')
    def test_is_available_returns_true_when_found(self, mock_which):
        """Test is_available returns True when CLI is found."""
        resolver = CLIPathResolver()
        assert resolver.is_available() is True

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '', 'NVM_DIR': '/nonexistent'}, clear=False)
    @patch('shutil.which', return_value=None)
    @patch('os.path.isfile', return_value=False)
    @patch('os.access', return_value=False)
    def test_is_available_returns_false_when_not_found(self, mock_access, mock_isfile, mock_which):
        """Test is_available returns False when CLI not found."""
        resolver = CLIPathResolver()
        assert resolver.is_available() is False


class TestModuleFunctions:
    """Test suite for module-level convenience functions."""

    def setup_method(self):
        """Reset singleton before each test."""
        CLIPathResolver.reset()

    @patch('shutil.which', return_value='/usr/bin/claude')
    def test_get_claude_cli_path(self, mock_which):
        """Test get_claude_cli_path function."""
        result = get_claude_cli_path()
        assert result == '/usr/bin/claude'

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '', 'NVM_DIR': '/nonexistent'}, clear=False)
    @patch('shutil.which', return_value=None)
    @patch('os.path.isfile', return_value=False)
    @patch('os.access', return_value=False)
    def test_get_claude_cli_path_safe(self, mock_access, mock_isfile, mock_which):
        """Test get_claude_cli_path_safe function."""
        result = get_claude_cli_path_safe("default_claude")
        assert result == "default_claude"

    @patch('shutil.which', return_value='/usr/bin/claude')
    def test_is_claude_available(self, mock_which):
        """Test is_claude_available function."""
        assert is_claude_available() is True


class TestNVMPathResolution:
    """Test NVM-specific path resolution."""

    def setup_method(self):
        """Reset singleton before each test."""
        CLIPathResolver.reset()

    @patch.dict(os.environ, {'CLAUDE_CLI_PATH': '', 'NVM_DIR': '/custom/nvm'}, clear=False)
    @patch('shutil.which', return_value=None)
    @patch('os.path.isfile')
    @patch('os.access')
    def test_nvm_path_resolution(self, mock_access, mock_isfile, mock_which):
        """Test that NVM paths are checked."""
        resolver = CLIPathResolver()

        # Make the NVM path succeed
        def isfile_side_effect(path):
            return path == '/custom/nvm/versions/node/v22.19.0/bin/claude'

        mock_isfile.side_effect = isfile_side_effect
        mock_access.return_value = True

        result = resolver.resolve()
        assert '/custom/nvm' in result


class TestThreadSafety:
    """Test thread safety of the resolver."""

    def setup_method(self):
        """Reset singleton before each test."""
        CLIPathResolver.reset()

    @patch('shutil.which', return_value='/usr/bin/claude')
    def test_concurrent_resolution(self, mock_which):
        """Test that concurrent resolution is safe."""
        import threading

        results = []
        errors = []

        def resolve_cli():
            try:
                resolver = CLIPathResolver()
                result = resolver.resolve()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=resolve_cli) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All results should be the same
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == '/usr/bin/claude' for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
