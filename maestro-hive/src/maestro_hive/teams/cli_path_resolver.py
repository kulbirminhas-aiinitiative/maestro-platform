#!/usr/bin/env python3
"""
Claude CLI Path Resolver - Safe Path Detection Without Filesystem Interference
MD-3068: Part of EPIC MD-3089 - Core Platform Stability & Tooling

Problem:
    The original path detection code in team_execution.py and claude_client_adapter.py
    calls shutil.which() and os.path.isfile() during module import, which can cause
    issues when the module is imported in environments where:
    - The filesystem is not fully mounted (containerized environments)
    - The PATH environment is not yet configured
    - NVM or other version managers haven't initialized

Solution:
    This module provides lazy, cached path resolution that:
    1. Defers filesystem operations until actually needed (not at import time)
    2. Caches the result to avoid repeated filesystem calls
    3. Provides explicit methods for different resolution strategies
    4. Falls back gracefully when claude CLI is not found

Design Decisions (ADR):
    - Lazy initialization prevents import-time side effects
    - Caching prevents repeated filesystem scans
    - Multiple resolution strategies for different deployment contexts
    - Thread-safe singleton pattern for global path cache
"""

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional, List
import logging


logger = logging.getLogger(__name__)


class PathResolutionError(Exception):
    """Raised when Claude CLI path cannot be resolved."""
    pass


class CLIPathResolver:
    """
    Safe, lazy path resolver for Claude CLI.

    Avoids filesystem operations at import time by deferring all
    path resolution until explicitly requested.

    Thread-safe with cached results.

    Example:
        >>> resolver = CLIPathResolver()
        >>> path = resolver.resolve()
        >>> print(f"Using claude at: {path}")

    Environment Variables:
        CLAUDE_CLI_PATH: Explicit path to claude CLI (highest priority)
        NVM_DIR: NVM directory for Node version detection
        HOME: User home directory for fallback paths
    """

    _instance: Optional['CLIPathResolver'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'CLIPathResolver':
        """Thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize resolver (only runs once due to singleton)."""
        if getattr(self, '_initialized', False):
            return

        self._cached_path: Optional[str] = None
        self._resolved = False
        self._resolution_lock = threading.Lock()
        self._initialized = True

    def _get_explicit_path(self) -> Optional[str]:
        """
        Check for explicitly configured path via environment variable.

        This is the highest priority resolution method - if set, we trust it.
        """
        explicit_path = os.environ.get('CLAUDE_CLI_PATH')
        if explicit_path:
            # Expand any shell variables or ~
            expanded = os.path.expandvars(os.path.expanduser(explicit_path))
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                logger.debug(f"Using explicit CLAUDE_CLI_PATH: {expanded}")
                return expanded
            else:
                logger.warning(f"CLAUDE_CLI_PATH set but invalid: {expanded}")
        return None

    def _get_path_from_which(self) -> Optional[str]:
        """
        Find claude in PATH using which command.

        Wrapped in try/except to handle edge cases where PATH is corrupted
        or subprocess fails.
        """
        import shutil
        try:
            path = shutil.which('claude')
            if path:
                logger.debug(f"Found claude via which: {path}")
                return path
        except Exception as e:
            logger.debug(f"shutil.which failed: {e}")
        return None

    def _get_nvm_paths(self) -> List[str]:
        """
        Get potential NVM-based installation paths.

        Checks common NVM node versions without scanning the entire directory.
        """
        nvm_dir = os.environ.get('NVM_DIR', os.path.expanduser('~/.nvm'))
        home = os.path.expanduser('~')

        # Common node versions in order of preference (most recent first)
        node_versions = [
            'v22.19.0', 'v22.18.0', 'v22.17.0',
            'v20.18.0', 'v20.12.0', 'v20.11.0',
            'v18.20.0', 'v18.18.0',
        ]

        paths = []
        for version in node_versions:
            paths.append(f"{nvm_dir}/versions/node/{version}/bin/claude")

        # Also check current nvm symlink if it exists
        paths.insert(0, f"{nvm_dir}/current/bin/claude")

        return paths

    def _get_global_paths(self) -> List[str]:
        """
        Get global installation paths for claude CLI.

        Checks common global npm and system paths.
        """
        home = os.path.expanduser('~')
        return [
            f"{home}/.local/bin/claude",
            f"{home}/node_modules/.bin/claude",
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            "/opt/homebrew/bin/claude",  # macOS Homebrew
        ]

    def _scan_paths(self, paths: List[str]) -> Optional[str]:
        """
        Scan a list of paths and return the first valid executable.

        Only performs filesystem operations when explicitly called.
        """
        for path in paths:
            try:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    logger.debug(f"Found claude at: {path}")
                    return path
            except (OSError, IOError) as e:
                # Handle filesystem errors gracefully
                logger.debug(f"Error checking path {path}: {e}")
                continue
        return None

    def resolve(self, force_refresh: bool = False) -> str:
        """
        Resolve the Claude CLI path.

        Uses lazy initialization and caching to avoid repeated filesystem
        operations.

        Args:
            force_refresh: If True, bypass cache and re-resolve

        Returns:
            Path to claude CLI executable

        Raises:
            PathResolutionError: If claude CLI cannot be found
        """
        with self._resolution_lock:
            if self._resolved and not force_refresh:
                if self._cached_path:
                    return self._cached_path
                raise PathResolutionError("Claude CLI not found (cached failure)")

            # Resolution order:
            # 1. Explicit environment variable
            # 2. PATH lookup via which
            # 3. NVM installation paths
            # 4. Global installation paths

            path = self._get_explicit_path()
            if path:
                self._cached_path = path
                self._resolved = True
                return path

            path = self._get_path_from_which()
            if path:
                self._cached_path = path
                self._resolved = True
                return path

            path = self._scan_paths(self._get_nvm_paths())
            if path:
                self._cached_path = path
                self._resolved = True
                return path

            path = self._scan_paths(self._get_global_paths())
            if path:
                self._cached_path = path
                self._resolved = True
                return path

            # Mark as resolved (with failure) to cache the negative result
            self._resolved = True
            raise PathResolutionError(
                "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            )

    def resolve_or_default(self, default: str = "claude") -> str:
        """
        Resolve path or return default without raising exception.

        Useful for graceful degradation when claude may not be available.

        Args:
            default: Default value to return if resolution fails

        Returns:
            Resolved path or default value
        """
        try:
            return self.resolve()
        except PathResolutionError:
            logger.warning(f"Claude CLI not found, using default: {default}")
            return default

    def is_available(self) -> bool:
        """
        Check if claude CLI is available.

        Returns:
            True if claude CLI can be resolved, False otherwise
        """
        try:
            self.resolve()
            return True
        except PathResolutionError:
            return False

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        Useful for testing or when environment changes.
        """
        with cls._lock:
            if cls._instance:
                cls._instance._cached_path = None
                cls._instance._resolved = False


# Module-level convenience functions
def get_claude_cli_path() -> str:
    """
    Get the Claude CLI path using the singleton resolver.

    Returns:
        Path to claude CLI executable

    Raises:
        PathResolutionError: If claude CLI cannot be found
    """
    return CLIPathResolver().resolve()


def get_claude_cli_path_safe(default: str = "claude") -> str:
    """
    Get the Claude CLI path or a safe default.

    Args:
        default: Default value if resolution fails

    Returns:
        Path to claude CLI or default
    """
    return CLIPathResolver().resolve_or_default(default)


def is_claude_available() -> bool:
    """
    Check if Claude CLI is available on this system.

    Returns:
        True if available, False otherwise
    """
    return CLIPathResolver().is_available()
