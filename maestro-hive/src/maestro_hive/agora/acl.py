"""
Agent Communication Language (ACL) Schema.

This module defines the standardized message format for agent communication
in the Agora, inspired by FIPA-ACL standards adapted for LLM agents.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-102)
Reference: docs/vision/AI_ECOSYSTEM.md (Section 4: Lingua Franca)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import json
import uuid


class ValidationError(Exception):
    """Raised when message validation fails."""
    pass


class Performative(Enum):
    """
    Message performatives (speech acts) based on FIPA-ACL.

    The performative defines the intent behind a message,
    allowing agents to reason about conversation state.

    Values:
        REQUEST: Asking another agent to perform an action
        PROPOSE: Offering to perform an action (bid response)
        AGREE: Accepting a proposal
        REFUSE: Declining a request or proposal
        INFORM: Sharing information without requesting action
        FAILURE: Reporting that an action has failed

    Example Flow (Contract Net):
        1. Manager sends REQUEST (CFP - Call for Proposals)
        2. Workers send PROPOSE (bids)
        3. Manager sends AGREE to winner, REFUSE to others
        4. Worker sends INFORM on completion, or FAILURE on error
    """
    REQUEST = "REQUEST"
    PROPOSE = "PROPOSE"
    AGREE = "AGREE"
    REFUSE = "REFUSE"
    INFORM = "INFORM"
    FAILURE = "FAILURE"


@dataclass
class AgoraMessage:
    """
    Standardized message format for the Agora event bus.

    Every message in the Town Square follows this schema to enable:
    - Deterministic conversation flows
    - Message routing and filtering
    - Audit trails and non-repudiation
    - Protocol adherence verification

    Required Fields:
        sender: The agent ID of the message originator
        performative: The intent/speech act of the message
        content: The payload (task description, bid details, results, etc.)

    Auto-Generated Fields:
        message_id: UUID for tracking and deduplication
        timestamp: ISO8601 creation timestamp
        receiver: Target agent or "BROADCAST" (default)
        protocol: Interaction pattern (default: "direct")

    Example:
        >>> msg = AgoraMessage(
        ...     sender="agent-coder-123",
        ...     performative=Performative.PROPOSE,
        ...     content={"bid_amount": 500, "eta_hours": 4}
        ... )
        >>> json_str = msg.to_json()
        >>> restored = AgoraMessage.from_json(json_str)
        >>> assert restored.sender == "agent-coder-123"
    """
    # Required fields
    sender: str
    performative: Performative
    content: Dict[str, Any]

    # Auto-generated fields with defaults
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    receiver: str = "BROADCAST"
    protocol: str = "direct"

    def __post_init__(self):
        """Validate the message after initialization."""
        self._validate()

    def _validate(self) -> None:
        """
        Validate all required fields.

        Raises:
            ValidationError: If any required field is missing or invalid
        """
        errors = []

        # Sender validation
        if not self.sender or not isinstance(self.sender, str):
            errors.append("sender must be a non-empty string")
        elif len(self.sender) > 256:
            errors.append("sender must be <= 256 characters")

        # Performative validation
        if not isinstance(self.performative, Performative):
            try:
                # Allow string values during deserialization
                if isinstance(self.performative, str):
                    self.performative = Performative(self.performative)
                else:
                    errors.append(
                        f"performative must be a Performative enum, "
                        f"got {type(self.performative)}"
                    )
            except ValueError:
                valid_values = [p.value for p in Performative]
                errors.append(
                    f"Invalid performative '{self.performative}'. "
                    f"Must be one of: {valid_values}"
                )

        # Content validation
        if not isinstance(self.content, dict):
            errors.append("content must be a dictionary")

        # Message ID validation
        if not self.message_id or not isinstance(self.message_id, str):
            errors.append("message_id must be a non-empty string")

        # Timestamp validation
        if not self.timestamp or not isinstance(self.timestamp, str):
            errors.append("timestamp must be a non-empty string")
        else:
            try:
                datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"timestamp must be ISO8601 format, got '{self.timestamp}'"
                )

        # Receiver validation
        if not isinstance(self.receiver, str):
            errors.append("receiver must be a string")

        # Protocol validation
        if not isinstance(self.protocol, str):
            errors.append("protocol must be a string")

        if errors:
            raise ValidationError(
                f"Message validation failed: {'; '.join(errors)}"
            )

    def to_json(self) -> str:
        """
        Serialize the message to JSON string.

        Returns:
            JSON string representation of the message

        Example:
            >>> msg = AgoraMessage(
            ...     sender="agent-1",
            ...     performative=Performative.REQUEST,
            ...     content={"task": "optimize"}
            ... )
            >>> json_str = msg.to_json()
            >>> '"sender": "agent-1"' in json_str
            True
        """
        data = {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "receiver": self.receiver,
            "performative": self.performative.value,
            "content": self.content,
            "protocol": self.protocol,
        }
        return json.dumps(data, indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.

        Returns:
            Dictionary representation with performative as string value
        """
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "receiver": self.receiver,
            "performative": self.performative.value,
            "content": self.content,
            "protocol": self.protocol,
        }

    @classmethod
    def from_json(cls, json_str: str) -> "AgoraMessage":
        """
        Deserialize a message from JSON string.

        Args:
            json_str: JSON string representation of a message

        Returns:
            AgoraMessage instance

        Raises:
            ValidationError: If JSON is invalid or missing required fields
            json.JSONDecodeError: If JSON parsing fails

        Example:
            >>> json_str = '{"sender": "a1", "performative": "REQUEST", "content": {}}'
            >>> msg = AgoraMessage.from_json(json_str)
            >>> msg.sender
            'a1'
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgoraMessage":
        """
        Create a message from a dictionary.

        Args:
            data: Dictionary with message fields

        Returns:
            AgoraMessage instance

        Raises:
            ValidationError: If missing required fields or invalid values
        """
        required_fields = ["sender", "performative", "content"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            raise ValidationError(
                f"Missing required fields: {missing}"
            )

        # Convert performative string to enum
        performative_value = data["performative"]
        if isinstance(performative_value, str):
            try:
                performative = Performative(performative_value)
            except ValueError:
                valid_values = [p.value for p in Performative]
                raise ValidationError(
                    f"Invalid performative '{performative_value}'. "
                    f"Must be one of: {valid_values}"
                )
        else:
            performative = performative_value

        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get(
                "timestamp",
                datetime.now(timezone.utc).isoformat()
            ),
            sender=data["sender"],
            receiver=data.get("receiver", "BROADCAST"),
            performative=performative,
            content=data["content"],
            protocol=data.get("protocol", "direct"),
        )

    def reply(
        self,
        sender: str,
        performative: Performative,
        content: Dict[str, Any]
    ) -> "AgoraMessage":
        """
        Create a reply to this message.

        The reply will have:
        - receiver set to original sender
        - protocol inherited from original
        - content.in_reply_to set to original message_id

        Args:
            sender: The replying agent's ID
            performative: The reply's performative
            content: The reply content

        Returns:
            New AgoraMessage as a reply

        Example:
            >>> request = AgoraMessage(
            ...     sender="manager",
            ...     performative=Performative.REQUEST,
            ...     content={"task": "code review"}
            ... )
            >>> response = request.reply(
            ...     sender="reviewer",
            ...     performative=Performative.AGREE,
            ...     content={"eta": "2 hours"}
            ... )
            >>> response.receiver
            'manager'
        """
        reply_content = {
            "in_reply_to": self.message_id,
            **content
        }

        return AgoraMessage(
            sender=sender,
            receiver=self.sender,
            performative=performative,
            content=reply_content,
            protocol=self.protocol,
        )

    def __repr__(self) -> str:
        """Return a concise string representation."""
        return (
            f"AgoraMessage(id={self.message_id[:8]}..., "
            f"sender={self.sender}, "
            f"performative={self.performative.value}, "
            f"receiver={self.receiver})"
        )
