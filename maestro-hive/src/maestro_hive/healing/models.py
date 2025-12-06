"""
Data models for the Self-Healing Mechanism.

Defines the core data structures for:
- Failure patterns and types
- Healing actions
- Sessions and feedback
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json


class FailureType(Enum):
    """Classification of failure types."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class ActionType(Enum):
    """Types of healing actions."""
    REFACTOR = "refactor"
    RETRY = "retry"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"
    PATCH = "patch"
    REGENERATE = "regenerate"


@dataclass
class FailurePattern:
    """
    Represents a detected failure pattern from execution history.

    Attributes:
        pattern_id: Unique identifier for the pattern
        pattern_type: Classification of the failure
        signature: Hash signature for pattern matching
        error_regex: Regex pattern to match error messages
        frequency: How often this pattern occurs
        fix_template: Template for automated fix
        confidence_score: Confidence in the fix (0.0-1.0)
        last_seen: When the pattern was last observed
        examples: Sample error messages that match
    """
    pattern_id: str
    pattern_type: FailureType
    signature: str
    error_regex: str
    frequency: int = 0
    fix_template: Optional[str] = None
    confidence_score: float = 0.0
    last_seen: Optional[datetime] = None
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def generate_signature(cls, error_message: str, context: Dict[str, Any]) -> str:
        """Generate a unique signature for a failure pattern."""
        normalized = error_message.lower().strip()
        context_str = json.dumps(context, sort_keys=True)
        combined = f"{normalized}:{context_str}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def matches(self, error_message: str) -> bool:
        """Check if an error message matches this pattern."""
        import re
        try:
            return bool(re.search(self.error_regex, error_message, re.IGNORECASE))
        except re.error:
            return self.signature in error_message.lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "signature": self.signature,
            "error_regex": self.error_regex,
            "frequency": self.frequency,
            "fix_template": self.fix_template,
            "confidence_score": self.confidence_score,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "examples": self.examples,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailurePattern":
        """Create from dictionary."""
        last_seen = None
        if data.get("last_seen"):
            last_seen = datetime.fromisoformat(data["last_seen"])
        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=FailureType(data["pattern_type"]),
            signature=data["signature"],
            error_regex=data["error_regex"],
            frequency=data.get("frequency", 0),
            fix_template=data.get("fix_template"),
            confidence_score=data.get("confidence_score", 0.0),
            last_seen=last_seen,
            examples=data.get("examples", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class HealingAction:
    """
    Represents an automated healing action.

    Attributes:
        action_id: Unique identifier for the action
        pattern_id: Reference to the triggering pattern
        action_type: Type of healing action
        code_diff: The code changes applied
        target_file: File being modified
        success_rate: Historical success rate
        applied_count: Number of times applied
        status: Current status of the action
    """
    action_id: str
    pattern_id: str
    action_type: ActionType
    code_diff: str
    target_file: str
    success_rate: float = 0.0
    applied_count: int = 0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def mark_success(self) -> None:
        """Mark the action as successful."""
        self.status = "success"
        self.applied_at = datetime.utcnow()
        self.applied_count += 1
        # Update success rate with exponential moving average
        alpha = 0.1
        self.success_rate = alpha * 1.0 + (1 - alpha) * self.success_rate

    def mark_failure(self, error: str) -> None:
        """Mark the action as failed."""
        self.status = "failed"
        self.applied_at = datetime.utcnow()
        self.applied_count += 1
        self.result = {"error": error}
        # Update success rate
        alpha = 0.1
        self.success_rate = alpha * 0.0 + (1 - alpha) * self.success_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action_id": self.action_id,
            "pattern_id": self.pattern_id,
            "action_type": self.action_type.value,
            "code_diff": self.code_diff,
            "target_file": self.target_file,
            "success_rate": self.success_rate,
            "applied_count": self.applied_count,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "result": self.result,
        }


@dataclass
class HealingSession:
    """
    Represents an active healing session.

    A session tracks the entire healing workflow from
    failure detection to fix application.
    """
    session_id: str
    execution_id: str
    failure_type: FailureType
    error_message: str
    context: Dict[str, Any] = field(default_factory=dict)
    detected_patterns: List[FailurePattern] = field(default_factory=list)
    proposed_actions: List[HealingAction] = field(default_factory=list)
    applied_action: Optional[HealingAction] = None
    status: str = "analyzing"
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def add_pattern(self, pattern: FailurePattern) -> None:
        """Add a detected pattern to the session."""
        self.detected_patterns.append(pattern)

    def propose_action(self, action: HealingAction) -> None:
        """Add a proposed healing action."""
        self.proposed_actions.append(action)

    def apply_action(self, action: HealingAction) -> None:
        """Mark an action as applied."""
        self.applied_action = action
        self.status = "healing"

    def complete(self, success: bool) -> None:
        """Complete the healing session."""
        self.completed_at = datetime.utcnow()
        self.status = "success" if success else "failed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "context": self.context,
            "detected_patterns": [p.to_dict() for p in self.detected_patterns],
            "proposed_actions": [a.to_dict() for a in self.proposed_actions],
            "applied_action": self.applied_action.to_dict() if self.applied_action else None,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class UserFeedback:
    """
    User feedback on a healing action.

    Used to improve the healing model over time.
    """
    feedback_id: str
    action_id: str
    helpful: bool
    comment: Optional[str] = None
    suggested_fix: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "action_id": self.action_id,
            "helpful": self.helpful,
            "comment": self.comment,
            "suggested_fix": self.suggested_fix,
            "submitted_at": self.submitted_at.isoformat(),
            "user_id": self.user_id,
        }


# Predefined pattern templates for common issues
COMMON_PATTERNS = {
    "missing_import": FailurePattern(
        pattern_id="builtin-missing-import",
        pattern_type=FailureType.SYNTAX,
        signature="missing_import",
        error_regex=r"(NameError|ImportError|ModuleNotFoundError):.*'(\w+)'",
        fix_template="from {module} import {name}",
        confidence_score=0.9,
        examples=["NameError: name 'json' is not defined"],
    ),
    "syntax_parenthesis": FailurePattern(
        pattern_id="builtin-syntax-paren",
        pattern_type=FailureType.SYNTAX,
        signature="syntax_paren",
        error_regex=r"SyntaxError:.*\(|\)",
        fix_template="# Check parenthesis balance",
        confidence_score=0.85,
        examples=["SyntaxError: unexpected EOF while parsing"],
    ),
    "type_error": FailurePattern(
        pattern_id="builtin-type-error",
        pattern_type=FailureType.RUNTIME,
        signature="type_error",
        error_regex=r"TypeError:.*",
        fix_template="# Add type conversion or check",
        confidence_score=0.7,
        examples=["TypeError: unsupported operand type(s)"],
    ),
    "key_error": FailurePattern(
        pattern_id="builtin-key-error",
        pattern_type=FailureType.RUNTIME,
        signature="key_error",
        error_regex=r"KeyError:.*'(\w+)'",
        fix_template="# Use .get() with default or check key existence",
        confidence_score=0.8,
        examples=["KeyError: 'missing_key'"],
    ),
    "attribute_error": FailurePattern(
        pattern_id="builtin-attr-error",
        pattern_type=FailureType.RUNTIME,
        signature="attr_error",
        error_regex=r"AttributeError:.*has no attribute '(\w+)'",
        fix_template="# Check attribute existence or add hasattr() guard",
        confidence_score=0.75,
        examples=["AttributeError: 'NoneType' object has no attribute 'split'"],
    ),
}
