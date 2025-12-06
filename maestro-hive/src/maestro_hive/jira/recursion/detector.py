"""
Circular Reference Detector for JIRA Sub-EPIC Recursion.

Implements AC-3: Handle circular references gracefully.

Tracks visited EPICs during traversal to detect and handle
circular references that would otherwise cause infinite loops.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CircularReferenceError(Exception):
    """Raised when a circular reference causes an error (strict mode)."""

    def __init__(self, epic_key: str, cycle_path: List[str]):
        self.epic_key = epic_key
        self.cycle_path = cycle_path
        super().__init__(f"Circular reference detected: {' -> '.join(cycle_path)} -> {epic_key}")


@dataclass
class CircularReferenceDetector:
    """
    Detects and handles circular references in EPIC hierarchy.

    Uses a visited set to track EPICs already processed in the current
    traversal path. When a circular reference is detected, behavior
    depends on the configured handling mode (warn, skip, or error).

    Attributes:
        mode: Handling mode - "warn" logs warning, "skip" silently skips,
              "error" raises CircularReferenceError
        _visited: Set of EPIC keys visited in current traversal
        _current_path: Current traversal path for error reporting
        _circular_refs: List of detected circular reference keys
        _cycle_paths: Full paths of detected cycles
    """
    mode: str = "warn"  # warn, skip, error
    _visited: Set[str] = field(default_factory=set)
    _current_path: List[str] = field(default_factory=list)
    _circular_refs: List[str] = field(default_factory=list)
    _cycle_paths: List[List[str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate mode after initialization."""
        if self.mode not in ("warn", "skip", "error"):
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'warn', 'skip', or 'error'")

    def enter(self, epic_key: str) -> bool:
        """
        Enter a node in the traversal.

        Call this before processing an EPIC. Returns False if the EPIC
        creates a circular reference.

        Args:
            epic_key: EPIC key being entered

        Returns:
            True if traversal should continue, False if circular ref detected

        Raises:
            CircularReferenceError: If mode is "error" and circular ref found
        """
        if epic_key in self._visited:
            # Circular reference detected
            cycle_path = self._current_path.copy()
            self._circular_refs.append(epic_key)
            self._cycle_paths.append(cycle_path + [epic_key])

            if self.mode == "error":
                raise CircularReferenceError(epic_key, cycle_path)
            elif self.mode == "warn":
                logger.warning(
                    f"Circular reference detected: {' -> '.join(cycle_path)} -> {epic_key}. "
                    f"Skipping to prevent infinite loop."
                )

            return False

        # Mark as visited and add to path
        self._visited.add(epic_key)
        self._current_path.append(epic_key)
        return True

    def exit(self, epic_key: str) -> None:
        """
        Exit a node in the traversal.

        Call this after processing an EPIC (including all its children).
        Removes the EPIC from the current path but keeps it in visited
        to allow proper sibling traversal.

        Args:
            epic_key: EPIC key being exited
        """
        if self._current_path and self._current_path[-1] == epic_key:
            self._current_path.pop()

    def check(self, epic_key: str) -> bool:
        """
        Check if an EPIC was already visited without entering.

        Useful for pre-checking before fetching children.

        Args:
            epic_key: EPIC key to check

        Returns:
            True if already visited (would be circular)
        """
        return epic_key in self._visited

    def reset(self) -> None:
        """Reset detector state for a new traversal."""
        self._visited.clear()
        self._current_path.clear()
        # Don't clear circular_refs - keep them for reporting

    def clear_all(self) -> None:
        """Clear all state including detected circular refs."""
        self._visited.clear()
        self._current_path.clear()
        self._circular_refs.clear()
        self._cycle_paths.clear()

    @property
    def circular_references(self) -> List[str]:
        """Return list of detected circular reference keys."""
        return self._circular_refs.copy()

    @property
    def cycle_paths(self) -> List[List[str]]:
        """Return full paths of detected cycles."""
        return self._cycle_paths.copy()

    @property
    def has_circular_refs(self) -> bool:
        """Check if any circular references were detected."""
        return len(self._circular_refs) > 0

    @property
    def visited_count(self) -> int:
        """Get count of visited EPICs."""
        return len(self._visited)

    @property
    def current_depth(self) -> int:
        """Get current traversal depth."""
        return len(self._current_path)

    def get_visited(self) -> Set[str]:
        """Get set of all visited EPIC keys."""
        return self._visited.copy()

    def to_dict(self) -> Dict:
        """Convert detector state to dictionary."""
        return {
            "mode": self.mode,
            "visited_count": self.visited_count,
            "current_depth": self.current_depth,
            "circular_refs_detected": self._circular_refs,
            "cycle_paths": self._cycle_paths,
            "has_circular_refs": self.has_circular_refs,
        }


class DepthLimitDetector:
    """
    Tracks recursion depth and enforces maximum depth limit.

    Works alongside CircularReferenceDetector to prevent
    both infinite loops and overly deep hierarchies.
    """

    def __init__(self, max_depth: int = 10):
        """
        Initialize depth detector.

        Args:
            max_depth: Maximum allowed recursion depth
        """
        if max_depth < 1:
            raise ValueError(f"max_depth must be at least 1, got {max_depth}")

        self.max_depth = max_depth
        self._current_depth = 0
        self._max_reached = 0
        self._depth_exceeded_keys: List[str] = []

    def enter(self, epic_key: str) -> bool:
        """
        Enter a node, incrementing depth.

        Args:
            epic_key: EPIC key being entered

        Returns:
            True if depth is within limit, False if exceeded
        """
        self._current_depth += 1
        self._max_reached = max(self._max_reached, self._current_depth)

        if self._current_depth > self.max_depth:
            self._depth_exceeded_keys.append(epic_key)
            logger.warning(
                f"Max depth {self.max_depth} exceeded at {epic_key} "
                f"(current depth: {self._current_depth})"
            )
            return False

        return True

    def exit(self) -> None:
        """Exit a node, decrementing depth."""
        if self._current_depth > 0:
            self._current_depth -= 1

    @property
    def current_depth(self) -> int:
        """Get current depth."""
        return self._current_depth

    @property
    def max_depth_reached(self) -> int:
        """Get maximum depth reached during traversal."""
        return self._max_reached

    @property
    def depth_exceeded_keys(self) -> List[str]:
        """Get EPIC keys where depth was exceeded."""
        return self._depth_exceeded_keys.copy()

    def reset(self) -> None:
        """Reset for a new traversal."""
        self._current_depth = 0
        # Keep max_reached for reporting

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "max_depth": self.max_depth,
            "current_depth": self._current_depth,
            "max_depth_reached": self._max_reached,
            "depth_exceeded_keys": self._depth_exceeded_keys,
        }
