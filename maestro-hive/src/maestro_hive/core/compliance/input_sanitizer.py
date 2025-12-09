"""
Input Sanitizer: Input validation and security sanitization for CLI.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)
AC-3: Input Sanitization

Provides security-focused input validation to prevent:
- Command injection attacks
- Path traversal attacks
- SQL injection patterns
- XSS patterns
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set
import threading

logger = logging.getLogger(__name__)


class SanitizationPattern(Enum):
    """Types of security patterns to check."""
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    SHELL_METACHAR = "shell_metachar"
    TEMPLATE_INJECTION = "template_injection"


@dataclass
class SecurityWarning:
    """A security warning from input validation."""
    pattern: SanitizationPattern
    severity: str  # low, medium, high, critical
    message: str
    position: Optional[int] = None
    matched_text: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern.value,
            "severity": self.severity,
            "message": self.message,
            "position": self.position,
            "matched_text": self.matched_text,
            "timestamp": self.timestamp,
        }


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    original: str
    sanitized: str
    was_modified: bool
    warnings: List[SecurityWarning] = field(default_factory=list)
    is_safe: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_length": len(self.original),
            "sanitized_length": len(self.sanitized),
            "was_modified": self.was_modified,
            "warnings": [w.to_dict() for w in self.warnings],
            "is_safe": self.is_safe,
            "metadata": self.metadata,
        }


class InputSanitizer:
    """
    Security-focused input validation and sanitization.

    Provides protection against common injection attacks while
    maintaining usability for legitimate inputs.

    Thread-safe implementation with configurable patterns.
    """

    # Default patterns for security checks
    DEFAULT_PATTERNS: Dict[SanitizationPattern, List[Dict[str, Any]]] = {
        SanitizationPattern.COMMAND_INJECTION: [
            {"regex": r"[;&|`$]", "severity": "high", "message": "Shell metacharacter detected"},
            {"regex": r"\$\([^)]+\)", "severity": "critical", "message": "Command substitution detected"},
            {"regex": r"`[^`]+`", "severity": "critical", "message": "Backtick execution detected"},
            {"regex": r"(?:^|;)\s*(?:rm|mv|cp|chmod|chown|kill)\s", "severity": "high", "message": "Dangerous command detected"},
        ],
        SanitizationPattern.PATH_TRAVERSAL: [
            {"regex": r"\.\./", "severity": "high", "message": "Path traversal pattern detected"},
            {"regex": r"\.\.\\", "severity": "high", "message": "Windows path traversal detected"},
            {"regex": r"(?:/etc/|/var/|/usr/|/root/)", "severity": "medium", "message": "System path detected"},
            {"regex": r"~\/", "severity": "low", "message": "Home directory reference"},
        ],
        SanitizationPattern.SQL_INJECTION: [
            {"regex": r"(?i)(union\s+select|select\s+\*|drop\s+table|delete\s+from)", "severity": "critical", "message": "SQL injection pattern"},
            {"regex": r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)", "severity": "high", "message": "SQL tautology pattern"},
            {"regex": r"['\"];\s*--", "severity": "high", "message": "SQL comment injection"},
        ],
        SanitizationPattern.XSS: [
            {"regex": r"<script[^>]*>", "severity": "critical", "message": "Script tag detected"},
            {"regex": r"javascript:", "severity": "high", "message": "JavaScript protocol detected"},
            {"regex": r"on\w+\s*=", "severity": "medium", "message": "Event handler detected"},
            {"regex": r"<iframe", "severity": "high", "message": "Iframe detected"},
        ],
        SanitizationPattern.SHELL_METACHAR: [
            {"regex": r"[\n\r]", "severity": "medium", "message": "Newline character in input"},
            {"regex": r"\x00", "severity": "critical", "message": "Null byte detected"},
            {"regex": r"\\x[0-9a-fA-F]{2}", "severity": "medium", "message": "Hex escape sequence"},
        ],
        SanitizationPattern.TEMPLATE_INJECTION: [
            {"regex": r"\{\{[^}]+\}\}", "severity": "high", "message": "Template expression detected"},
            {"regex": r"\$\{[^}]+\}", "severity": "high", "message": "Variable interpolation detected"},
            {"regex": r"<%[^%]+%>", "severity": "high", "message": "Server-side template detected"},
        ],
    }

    # Valid EPIC ID pattern
    EPIC_ID_PATTERN = re.compile(r"^[A-Z]{2,5}-\d{1,6}$")

    # Valid path pattern (conservative)
    SAFE_PATH_PATTERN = re.compile(r"^[\w\-./]+$")

    def __init__(
        self,
        enabled_patterns: Optional[Set[SanitizationPattern]] = None,
        custom_patterns: Optional[Dict[SanitizationPattern, List[Dict]]] = None,
        strict_mode: bool = False,
        enabled: bool = True
    ):
        """
        Initialize the input sanitizer.

        Args:
            enabled_patterns: Which pattern types to check (None = all)
            custom_patterns: Additional custom patterns
            strict_mode: Block any suspicious input (vs. warning only)
            enabled: Whether sanitization is active
        """
        self._enabled_patterns = enabled_patterns or set(SanitizationPattern)
        self._patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            for pattern_type, patterns in custom_patterns.items():
                if pattern_type in self._patterns:
                    self._patterns[pattern_type].extend(patterns)
                else:
                    self._patterns[pattern_type] = patterns

        self._strict_mode = strict_mode
        self._enabled = enabled
        self._lock = threading.Lock()
        self._compiled_patterns: Dict[SanitizationPattern, List[tuple]] = {}

        # Pre-compile regex patterns
        self._compile_patterns()

        logger.info(f"InputSanitizer initialized, strict_mode={strict_mode}")

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        for pattern_type, patterns in self._patterns.items():
            compiled = []
            for p in patterns:
                try:
                    regex = re.compile(p["regex"])
                    compiled.append((regex, p["severity"], p["message"]))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern: {p['regex']}: {e}")
            self._compiled_patterns[pattern_type] = compiled

    def sanitize(self, input_str: str) -> SanitizationResult:
        """
        Sanitize input string and check for security issues.

        Args:
            input_str: Input string to sanitize

        Returns:
            SanitizationResult with sanitized string and warnings
        """
        if not self._enabled:
            return SanitizationResult(
                original=input_str,
                sanitized=input_str,
                was_modified=False,
                is_safe=True,
                metadata={"sanitization_disabled": True}
            )

        with self._lock:
            warnings = []
            sanitized = input_str
            was_modified = False

            # Check each enabled pattern type
            for pattern_type in self._enabled_patterns:
                compiled = self._compiled_patterns.get(pattern_type, [])
                for regex, severity, message in compiled:
                    matches = list(regex.finditer(sanitized))
                    for match in matches:
                        warning = SecurityWarning(
                            pattern=pattern_type,
                            severity=severity,
                            message=message,
                            position=match.start(),
                            matched_text=match.group()[:20],  # Limit matched text
                        )
                        warnings.append(warning)

                        # In strict mode, replace dangerous patterns
                        if self._strict_mode and severity in ("high", "critical"):
                            sanitized = regex.sub("", sanitized)
                            was_modified = True

            # Determine if input is safe
            is_safe = not any(
                w.severity in ("high", "critical") for w in warnings
            )

            result = SanitizationResult(
                original=input_str,
                sanitized=sanitized.strip(),
                was_modified=was_modified,
                warnings=warnings,
                is_safe=is_safe,
                metadata={
                    "warning_count": len(warnings),
                    "critical_count": sum(1 for w in warnings if w.severity == "critical"),
                }
            )

            if warnings:
                logger.warning(
                    f"Input sanitization found {len(warnings)} issues, "
                    f"is_safe={is_safe}"
                )

            return result

    def validate_epic_id(self, epic_id: str) -> bool:
        """
        Validate EPIC ID format.

        Args:
            epic_id: EPIC ID to validate (e.g., "MD-2801")

        Returns:
            True if valid EPIC ID format
        """
        if not epic_id:
            return False
        return bool(self.EPIC_ID_PATTERN.match(epic_id.strip()))

    def validate_path(self, path: str) -> bool:
        """
        Validate path for safety.

        Args:
            path: File path to validate

        Returns:
            True if path appears safe
        """
        if not path:
            return False

        # Check for path traversal
        if ".." in path:
            return False

        # Check for shell metacharacters
        if any(c in path for c in [";", "|", "&", "`", "$", "("]):
            return False

        return bool(self.SAFE_PATH_PATTERN.match(path))

    def check_injection(self, input_str: str) -> List[SecurityWarning]:
        """
        Check input for injection attacks without modifying.

        Args:
            input_str: Input to check

        Returns:
            List of security warnings
        """
        result = self.sanitize(input_str)
        return result.warnings

    def sanitize_command_args(self, args: List[str]) -> List[str]:
        """
        Sanitize command line arguments.

        Args:
            args: List of command arguments

        Returns:
            Sanitized argument list
        """
        sanitized_args = []
        for arg in args:
            result = self.sanitize(arg)
            if result.is_safe or not self._strict_mode:
                sanitized_args.append(result.sanitized)
            else:
                logger.warning(f"Blocked unsafe argument: {arg[:20]}...")
        return sanitized_args

    def sanitize_dict(
        self,
        data: Dict[str, Any],
        keys_to_sanitize: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Sanitize string values in a dictionary.

        Args:
            data: Dictionary to sanitize
            keys_to_sanitize: Specific keys to sanitize (None = all strings)

        Returns:
            Sanitized dictionary
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                if keys_to_sanitize is None or key in keys_to_sanitize:
                    sanitized = self.sanitize(value)
                    result[key] = sanitized.sanitized
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value, keys_to_sanitize)
            else:
                result[key] = value
        return result

    def enable(self) -> None:
        """Enable sanitization."""
        self._enabled = True
        logger.info("Input sanitization enabled")

    def disable(self) -> None:
        """Disable sanitization."""
        self._enabled = False
        logger.info("Input sanitization disabled")

    def set_strict_mode(self, strict: bool) -> None:
        """Set strict mode."""
        self._strict_mode = strict
        logger.info(f"Strict mode set to: {strict}")

    @property
    def is_enabled(self) -> bool:
        """Check if sanitization is enabled."""
        return self._enabled

    @property
    def is_strict(self) -> bool:
        """Check if strict mode is enabled."""
        return self._strict_mode


def get_input_sanitizer(**kwargs) -> InputSanitizer:
    """Get an InputSanitizer instance."""
    return InputSanitizer(**kwargs)
