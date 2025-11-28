"""
ACC Suppression System

Provides suppression capabilities for architectural violations with advanced features:
- Pattern-based suppression (file patterns, rule types, violation IDs)
- Time-based expiry with warnings
- Suppression inheritance (directory/file/rule level)
- Comprehensive audit trail
- Performance-optimized for large-scale codebases

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import re
import yaml
import fnmatch
import logging
from enum import Enum

from acc.rule_engine import Violation, RuleType, Severity


logger = logging.getLogger(__name__)


# ============================================================================
# Enumerations
# ============================================================================

class SuppressionLevel(str, Enum):
    """Suppression scope level."""
    VIOLATION = "violation"  # Specific violation ID
    FILE = "file"  # File pattern
    DIRECTORY = "directory"  # Directory pattern
    RULE = "rule"  # Rule type


class PatternType(str, Enum):
    """Pattern matching type."""
    EXACT = "exact"
    GLOB = "glob"
    REGEX = "regex"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SuppressionEntry:
    """Individual suppression entry."""
    id: str
    pattern: str  # What to suppress (violation ID, file pattern, rule type)
    level: SuppressionLevel
    pattern_type: PatternType = PatternType.GLOB
    rule_type: Optional[RuleType] = None
    threshold: Optional[int] = None  # Override threshold for coupling rules
    expires: Optional[datetime] = None
    author: str = "unknown"
    justification: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0
    permanent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if suppression is expired."""
        if self.permanent or not self.expires:
            return False
        return datetime.now() > self.expires

    def expires_soon(self, days: int = 7) -> bool:
        """Check if suppression expires within N days."""
        if self.permanent or not self.expires:
            return False
        warning_date = datetime.now() + timedelta(days=days)
        return datetime.now() < self.expires <= warning_date

    def matches_pattern(self, value: str) -> bool:
        """Check if value matches suppression pattern."""
        if self.pattern_type == PatternType.EXACT:
            return self.pattern == value
        elif self.pattern_type == PatternType.GLOB:
            return fnmatch.fnmatch(value, self.pattern)
        elif self.pattern_type == PatternType.REGEX:
            try:
                return bool(re.match(self.pattern, value))
            except re.error:
                logger.error(f"Invalid regex pattern: {self.pattern}")
                return False
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'pattern': self.pattern,
            'level': self.level.value,
            'pattern_type': self.pattern_type.value,
            'rule_type': self.rule_type.value if self.rule_type else None,
            'threshold': self.threshold,
            'expires': self.expires.isoformat() if self.expires else None,
            'author': self.author,
            'justification': self.justification,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'use_count': self.use_count,
            'permanent': self.permanent,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuppressionEntry':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            pattern=data['pattern'],
            level=SuppressionLevel(data['level']),
            pattern_type=PatternType(data.get('pattern_type', 'glob')),
            rule_type=RuleType(data['rule_type']) if data.get('rule_type') else None,
            threshold=data.get('threshold'),
            expires=datetime.fromisoformat(data['expires']) if data.get('expires') else None,
            author=data.get('author', 'unknown'),
            justification=data.get('justification', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            last_used=datetime.fromisoformat(data['last_used']) if data.get('last_used') else None,
            use_count=data.get('use_count', 0),
            permanent=data.get('permanent', False),
            metadata=data.get('metadata', {})
        )


@dataclass
class SuppressionMatch:
    """Result of suppression matching."""
    suppressed: bool
    suppression: Optional[SuppressionEntry] = None
    reason: str = ""


@dataclass
class SuppressionMetrics:
    """Metrics about suppression usage."""
    total_suppressions: int = 0
    active_suppressions: int = 0
    expired_suppressions: int = 0
    expiring_soon_suppressions: int = 0
    unused_suppressions: int = 0
    permanent_suppressions: int = 0
    violations_suppressed: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    by_rule_type: Dict[str, int] = field(default_factory=dict)
    by_author: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# Pattern Matcher
# ============================================================================

class PatternMatcher:
    """Efficient pattern matching for suppressions."""

    def __init__(self):
        """Initialize pattern matcher."""
        self._exact_cache: Dict[str, Set[str]] = {}
        self._glob_patterns: List[str] = []
        self._regex_patterns: List[re.Pattern] = []

    def add_pattern(self, pattern: str, pattern_type: PatternType) -> None:
        """Add a pattern for matching."""
        if pattern_type == PatternType.EXACT:
            if 'exact' not in self._exact_cache:
                self._exact_cache['exact'] = set()
            self._exact_cache['exact'].add(pattern)
        elif pattern_type == PatternType.GLOB:
            self._glob_patterns.append(pattern)
        elif pattern_type == PatternType.REGEX:
            try:
                compiled = re.compile(pattern)
                self._regex_patterns.append(compiled)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")

    def matches(self, value: str, pattern: str, pattern_type: PatternType) -> bool:
        """Check if value matches pattern."""
        if pattern_type == PatternType.EXACT:
            return pattern == value
        elif pattern_type == PatternType.GLOB:
            return fnmatch.fnmatch(value, pattern)
        elif pattern_type == PatternType.REGEX:
            try:
                return bool(re.match(pattern, value))
            except re.error:
                return False
        return False

    def clear(self) -> None:
        """Clear all cached patterns."""
        self._exact_cache.clear()
        self._glob_patterns.clear()
        self._regex_patterns.clear()


# ============================================================================
# Suppression Manager
# ============================================================================

class SuppressionManager:
    """
    Manages violation suppressions with advanced features.

    Features:
    - Multiple suppression levels (violation, file, directory, rule)
    - Pattern matching (exact, glob, regex)
    - Time-based expiry with warnings
    - Suppression inheritance and precedence
    - Comprehensive audit trail
    - Performance optimization for large-scale use
    """

    def __init__(self):
        """Initialize suppression manager."""
        self.suppressions: List[SuppressionEntry] = []
        self._pattern_matcher = PatternMatcher()
        self._suppression_cache: Dict[str, SuppressionMatch] = {}
        self._metrics = SuppressionMetrics()

    def add_suppression(self, suppression: SuppressionEntry) -> None:
        """Add a suppression entry."""
        # Check for duplicates
        if any(s.id == suppression.id for s in self.suppressions):
            raise ValueError(f"Suppression with ID '{suppression.id}' already exists")

        self.suppressions.append(suppression)
        self._pattern_matcher.add_pattern(suppression.pattern, suppression.pattern_type)
        self._clear_cache()
        logger.debug(f"Added suppression: {suppression.id}")

    def remove_suppression(self, suppression_id: str) -> bool:
        """Remove a suppression by ID."""
        for i, suppression in enumerate(self.suppressions):
            if suppression.id == suppression_id:
                self.suppressions.pop(i)
                self._clear_cache()
                logger.debug(f"Removed suppression: {suppression_id}")
                return True
        return False

    def load_from_yaml(self, yaml_path: Path) -> int:
        """
        Load suppressions from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Number of suppressions loaded

        Raises:
            ValueError: If YAML is invalid
        """
        if not yaml_path.exists():
            raise ValueError(f"Suppression file not found: {yaml_path}")

        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        if not isinstance(data, dict):
            raise ValueError("YAML must contain a dictionary")

        suppressions_data = data.get('suppressions', [])
        if not isinstance(suppressions_data, list):
            raise ValueError("'suppressions' must be a list")

        loaded = 0
        for supp_data in suppressions_data:
            try:
                suppression = SuppressionEntry.from_dict(supp_data)
                self.add_suppression(suppression)
                loaded += 1
            except Exception as e:
                logger.error(f"Failed to load suppression {supp_data.get('id', 'unknown')}: {e}")
                raise ValueError(f"Invalid suppression: {e}")

        return loaded

    def save_to_yaml(self, yaml_path: Path) -> None:
        """Save suppressions to YAML file."""
        data = {
            'suppressions': [s.to_dict() for s in self.suppressions],
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_suppressions': len(self.suppressions)
            }
        }

        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def is_suppressed(self, violation: Violation, use_cache: bool = True) -> SuppressionMatch:
        """
        Check if a violation is suppressed.

        Applies suppression precedence rules:
        1. Violation-level (most specific)
        2. File-level
        3. Directory-level
        4. Rule-level (least specific)

        Args:
            violation: Violation to check
            use_cache: Whether to use caching (default True)

        Returns:
            SuppressionMatch indicating if suppressed and why
        """
        # Build cache key
        cache_key = self._build_cache_key(violation)
        if use_cache and cache_key in self._suppression_cache:
            cached_match = self._suppression_cache[cache_key]
            # Update metrics even for cached results
            if cached_match.suppressed and cached_match.suppression:
                self._update_metrics(cached_match.suppression)
            return cached_match

        # Check each suppression level in precedence order
        match = self._check_violation_level(violation)
        if match.suppressed:
            self._update_metrics(match.suppression)
            if use_cache:
                self._suppression_cache[cache_key] = match
            return match

        match = self._check_file_level(violation)
        if match.suppressed:
            self._update_metrics(match.suppression)
            if use_cache:
                self._suppression_cache[cache_key] = match
            return match

        match = self._check_directory_level(violation)
        if match.suppressed:
            self._update_metrics(match.suppression)
            if use_cache:
                self._suppression_cache[cache_key] = match
            return match

        match = self._check_rule_level(violation)
        if match.suppressed:
            self._update_metrics(match.suppression)
            if use_cache:
                self._suppression_cache[cache_key] = match
            return match

        # Not suppressed
        no_match = SuppressionMatch(suppressed=False, reason="No matching suppression")
        if use_cache:
            self._suppression_cache[cache_key] = no_match
        return no_match

    def _check_violation_level(self, violation: Violation) -> SuppressionMatch:
        """Check violation-level suppressions."""
        # Use list comprehension for faster filtering
        violation_suppressions = [
            s for s in self.suppressions
            if s.level == SuppressionLevel.VIOLATION and not s.is_expired()
        ]

        for suppression in violation_suppressions:
            if suppression.matches_pattern(violation.rule_id):
                return SuppressionMatch(
                    suppressed=True,
                    suppression=suppression,
                    reason=f"Suppressed by violation-level rule: {suppression.id}"
                )
        return SuppressionMatch(suppressed=False)

    def _check_file_level(self, violation: Violation) -> SuppressionMatch:
        """Check file-level suppressions."""
        if not violation.source_file:
            return SuppressionMatch(suppressed=False)

        # Use list comprehension for faster filtering
        file_suppressions = [
            s for s in self.suppressions
            if s.level == SuppressionLevel.FILE and not s.is_expired()
            and (not s.rule_type or s.rule_type == violation.rule_type)
        ]

        for suppression in file_suppressions:
            # Check if file matches pattern
            if suppression.matches_pattern(violation.source_file):
                # Check threshold override for coupling rules
                if suppression.threshold is not None and violation.rule_type == RuleType.COUPLING:
                    # Extract coupling value from message
                    match = re.search(r'coupling (\d+)', violation.message)
                    if match:
                        coupling_value = int(match.group(1))
                        if coupling_value <= suppression.threshold:
                            return SuppressionMatch(
                                suppressed=True,
                                suppression=suppression,
                                reason=f"Suppressed by file-level rule with threshold: {suppression.id}"
                            )
                else:
                    return SuppressionMatch(
                        suppressed=True,
                        suppression=suppression,
                        reason=f"Suppressed by file-level rule: {suppression.id}"
                    )
        return SuppressionMatch(suppressed=False)

    def _check_directory_level(self, violation: Violation) -> SuppressionMatch:
        """Check directory-level suppressions (inherited)."""
        if not violation.source_file:
            return SuppressionMatch(suppressed=False)

        # Use list comprehension for faster filtering
        dir_suppressions = [
            s for s in self.suppressions
            if s.level == SuppressionLevel.DIRECTORY and not s.is_expired()
            and (not s.rule_type or s.rule_type == violation.rule_type)
        ]

        for suppression in dir_suppressions:
            # Check if file is in suppressed directory
            file_path = Path(violation.source_file)
            if suppression.matches_pattern(str(file_path.parent)) or \
               any(suppression.matches_pattern(str(p)) for p in file_path.parents):
                # Check threshold override for coupling rules
                if suppression.threshold is not None and violation.rule_type == RuleType.COUPLING:
                    # Extract coupling value from message
                    match = re.search(r'coupling (\d+)', violation.message)
                    if match:
                        coupling_value = int(match.group(1))
                        if coupling_value <= suppression.threshold:
                            return SuppressionMatch(
                                suppressed=True,
                                suppression=suppression,
                                reason=f"Suppressed by directory-level rule: {suppression.id}"
                            )
                else:
                    return SuppressionMatch(
                        suppressed=True,
                        suppression=suppression,
                        reason=f"Suppressed by directory-level rule: {suppression.id}"
                    )
        return SuppressionMatch(suppressed=False)

    def _check_rule_level(self, violation: Violation) -> SuppressionMatch:
        """Check rule-level suppressions."""
        # Use list comprehension for faster filtering
        rule_suppressions = [
            s for s in self.suppressions
            if s.level == SuppressionLevel.RULE and not s.is_expired()
            and s.rule_type == violation.rule_type
        ]

        for suppression in rule_suppressions:
            # Check threshold for coupling rules
            if suppression.threshold is not None and violation.rule_type == RuleType.COUPLING:
                match = re.search(r'coupling (\d+)', violation.message)
                if match:
                    coupling_value = int(match.group(1))
                    if coupling_value <= suppression.threshold:
                        return SuppressionMatch(
                            suppressed=True,
                            suppression=suppression,
                            reason=f"Suppressed by rule-level threshold: {suppression.id}"
                        )
            else:
                return SuppressionMatch(
                    suppressed=True,
                    suppression=suppression,
                    reason=f"Suppressed by rule-level rule: {suppression.id}"
                )
        return SuppressionMatch(suppressed=False)

    def filter_violations(self, violations: List[Violation]) -> tuple[List[Violation], List[Violation]]:
        """
        Filter violations by suppressions.

        Args:
            violations: List of violations to filter

        Returns:
            Tuple of (active_violations, suppressed_violations)
        """
        active = []
        suppressed = []

        for violation in violations:
            match = self.is_suppressed(violation)
            if match.suppressed:
                suppressed.append(violation)
                self._metrics.violations_suppressed += 1
            else:
                active.append(violation)

        return active, suppressed

    def remove_expired_suppressions(self) -> int:
        """Remove all expired suppressions."""
        initial_count = len(self.suppressions)
        self.suppressions = [s for s in self.suppressions if not s.is_expired()]
        removed = initial_count - len(self.suppressions)

        if removed > 0:
            self._clear_cache()
            logger.info(f"Removed {removed} expired suppressions")

        return removed

    def get_expiring_suppressions(self, days: int = 7) -> List[SuppressionEntry]:
        """Get suppressions expiring within N days."""
        return [s for s in self.suppressions if s.expires_soon(days)]

    def get_unused_suppressions(self, min_age_days: int = 30) -> List[SuppressionEntry]:
        """Get suppressions that haven't been used in N days."""
        cutoff = datetime.now() - timedelta(days=min_age_days)
        return [
            s for s in self.suppressions
            if s.last_used is None or s.last_used < cutoff
        ]

    def get_metrics(self) -> SuppressionMetrics:
        """Calculate and return suppression metrics."""
        metrics = SuppressionMetrics()
        metrics.total_suppressions = len(self.suppressions)

        for suppression in self.suppressions:
            # Count by status
            if suppression.is_expired():
                metrics.expired_suppressions += 1
            else:
                metrics.active_suppressions += 1

            if suppression.expires_soon():
                metrics.expiring_soon_suppressions += 1

            if suppression.permanent:
                metrics.permanent_suppressions += 1

            if suppression.use_count == 0:
                metrics.unused_suppressions += 1

            # Count by level
            level_key = suppression.level.value
            metrics.by_level[level_key] = metrics.by_level.get(level_key, 0) + 1

            # Count by rule type
            if suppression.rule_type:
                rule_key = suppression.rule_type.value
                metrics.by_rule_type[rule_key] = metrics.by_rule_type.get(rule_key, 0) + 1

            # Count by author
            metrics.by_author[suppression.author] = metrics.by_author.get(suppression.author, 0) + 1

        metrics.violations_suppressed = self._metrics.violations_suppressed

        return metrics

    def validate_suppression(self, suppression: SuppressionEntry) -> tuple[bool, Optional[str]]:
        """
        Validate a suppression entry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not suppression.id:
            return False, "Suppression ID is required"

        if not suppression.pattern:
            return False, "Pattern is required"

        # Check for duplicate ID
        if any(s.id == suppression.id for s in self.suppressions):
            return False, f"Suppression ID '{suppression.id}' already exists"

        # Validate pattern
        if suppression.pattern_type == PatternType.REGEX:
            try:
                re.compile(suppression.pattern)
            except re.error as e:
                return False, f"Invalid regex pattern: {e}"

        # Validate expiry
        if suppression.expires and not suppression.permanent:
            if suppression.expires < datetime.now():
                return False, "Expiry date must be in the future"

        # Check justification for permanent suppressions
        if suppression.permanent and not suppression.justification:
            return False, "Justification required for permanent suppressions"

        return True, None

    def _build_cache_key(self, violation: Violation) -> str:
        """Build cache key for violation."""
        return f"{violation.rule_id}:{violation.source_file or 'none'}:{violation.rule_type.value}"

    def _update_metrics(self, suppression: Optional[SuppressionEntry]) -> None:
        """Update suppression usage metrics."""
        if suppression:
            suppression.last_used = datetime.now()
            suppression.use_count += 1

    def _clear_cache(self) -> None:
        """Clear suppression cache."""
        self._suppression_cache.clear()
        self._pattern_matcher.clear()

    def clear_all(self) -> None:
        """Clear all suppressions."""
        self.suppressions.clear()
        self._clear_cache()
        self._metrics = SuppressionMetrics()
