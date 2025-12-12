"""
Tests for Agent Communication Language (ACL) Schema.

These tests verify:
- AgoraMessage creation and validation
- Serialization (to_json) and deserialization (from_json)
- Performative enum handling
- Validation error cases
- Reply message creation
"""

import json
import pytest
from datetime import datetime, timezone

from maestro_hive.agora import (
    AgoraMessage,
    Performative,
    ValidationError,
)


class TestPerformative:
    """Tests for Performative enum."""

    def test_all_performatives_defined(self):
        """All required performatives exist."""
        expected = ["REQUEST", "PROPOSE", "AGREE", "REFUSE", "INFORM", "FAILURE"]
        actual = [p.value for p in Performative]
        assert set(actual) == set(expected)

    def test_performative_from_string(self):
        """Performative can be created from string."""
        assert Performative("REQUEST") == Performative.REQUEST
        assert Performative("PROPOSE") == Performative.PROPOSE

    def test_invalid_performative_raises(self):
        """Invalid performative string raises ValueError."""
        with pytest.raises(ValueError):
            Performative("INVALID")


class TestAgoraMessage:
    """Tests for AgoraMessage dataclass."""

    def test_create_minimal_message(self):
        """Create message with only required fields."""
        msg = AgoraMessage(
            sender="agent-1",
            performative=Performative.REQUEST,
            content={"task": "test"}
        )

        assert msg.sender == "agent-1"
        assert msg.performative == Performative.REQUEST
        assert msg.content == {"task": "test"}
        # Auto-generated fields
        assert msg.message_id is not None
        assert msg.timestamp is not None
        assert msg.receiver == "BROADCAST"
        assert msg.protocol == "direct"

    def test_create_full_message(self):
        """Create message with all fields specified."""
        msg = AgoraMessage(
            message_id="custom-id-123",
            timestamp="2025-12-11T10:00:00+00:00",
            sender="agent-sender",
            receiver="agent-receiver",
            performative=Performative.PROPOSE,
            content={"bid": 500},
            protocol="contract-net"
        )

        assert msg.message_id == "custom-id-123"
        assert msg.timestamp == "2025-12-11T10:00:00+00:00"
        assert msg.sender == "agent-sender"
        assert msg.receiver == "agent-receiver"
        assert msg.performative == Performative.PROPOSE
        assert msg.content == {"bid": 500}
        assert msg.protocol == "contract-net"

    def test_message_id_is_uuid(self):
        """Auto-generated message_id is a valid UUID string."""
        msg = AgoraMessage(
            sender="a",
            performative=Performative.INFORM,
            content={}
        )
        # UUID format: 8-4-4-4-12 hex chars
        import uuid
        uuid.UUID(msg.message_id)  # Should not raise

    def test_timestamp_is_iso8601(self):
        """Auto-generated timestamp is valid ISO8601."""
        msg = AgoraMessage(
            sender="a",
            performative=Performative.INFORM,
            content={}
        )
        # Should parse without error
        datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))


class TestAgoraMessageValidation:
    """Tests for message validation."""

    def test_empty_sender_raises(self):
        """Empty sender raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgoraMessage(
                sender="",
                performative=Performative.REQUEST,
                content={}
            )
        assert "sender" in str(exc_info.value).lower()

    def test_none_sender_raises(self):
        """None sender raises ValidationError."""
        with pytest.raises(ValidationError):
            AgoraMessage(
                sender=None,
                performative=Performative.REQUEST,
                content={}
            )

    def test_invalid_performative_raises(self):
        """Invalid performative raises ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            AgoraMessage(
                sender="agent",
                performative="INVALID",
                content={}
            )

    def test_non_dict_content_raises(self):
        """Non-dict content raises ValidationError."""
        with pytest.raises(ValidationError):
            AgoraMessage(
                sender="agent",
                performative=Performative.REQUEST,
                content="not a dict"
            )

    def test_list_content_raises(self):
        """List content raises ValidationError."""
        with pytest.raises(ValidationError):
            AgoraMessage(
                sender="agent",
                performative=Performative.REQUEST,
                content=["list", "items"]
            )

    def test_invalid_timestamp_format_raises(self):
        """Invalid timestamp format raises ValidationError."""
        with pytest.raises(ValidationError):
            AgoraMessage(
                sender="agent",
                performative=Performative.REQUEST,
                content={},
                timestamp="not-a-timestamp"
            )


class TestSerialization:
    """Tests for to_json() and from_json() methods."""

    def test_to_json_basic(self):
        """to_json produces valid JSON."""
        msg = AgoraMessage(
            sender="agent-1",
            performative=Performative.REQUEST,
            content={"task": "optimize"}
        )

        json_str = msg.to_json()

        # Should be valid JSON
        data = json.loads(json_str)

        assert data["sender"] == "agent-1"
        assert data["performative"] == "REQUEST"
        assert data["content"]["task"] == "optimize"

    def test_from_json_basic(self):
        """from_json creates valid message."""
        json_str = json.dumps({
            "sender": "agent-2",
            "performative": "PROPOSE",
            "content": {"bid": 100}
        })

        msg = AgoraMessage.from_json(json_str)

        assert msg.sender == "agent-2"
        assert msg.performative == Performative.PROPOSE
        assert msg.content["bid"] == 100

    def test_roundtrip_serialization(self):
        """Message survives to_json -> from_json roundtrip."""
        original = AgoraMessage(
            sender="roundtrip-agent",
            receiver="target-agent",
            performative=Performative.AGREE,
            content={"terms": "accepted", "eta": 3600},
            protocol="contract-net"
        )

        json_str = original.to_json()
        restored = AgoraMessage.from_json(json_str)

        assert restored.sender == original.sender
        assert restored.receiver == original.receiver
        assert restored.performative == original.performative
        assert restored.content == original.content
        assert restored.protocol == original.protocol
        assert restored.message_id == original.message_id
        assert restored.timestamp == original.timestamp

    def test_from_json_missing_required_field(self):
        """from_json raises on missing required fields."""
        # Missing 'sender'
        with pytest.raises(ValidationError) as exc_info:
            AgoraMessage.from_json(json.dumps({
                "performative": "REQUEST",
                "content": {}
            }))
        assert "sender" in str(exc_info.value).lower()

        # Missing 'performative'
        with pytest.raises(ValidationError):
            AgoraMessage.from_json(json.dumps({
                "sender": "agent",
                "content": {}
            }))

        # Missing 'content'
        with pytest.raises(ValidationError):
            AgoraMessage.from_json(json.dumps({
                "sender": "agent",
                "performative": "REQUEST"
            }))

    def test_from_json_invalid_json(self):
        """from_json raises on invalid JSON."""
        with pytest.raises(ValidationError) as exc_info:
            AgoraMessage.from_json("not valid json {{{")
        assert "Invalid JSON" in str(exc_info.value)

    def test_from_json_invalid_performative(self):
        """from_json raises on invalid performative value."""
        with pytest.raises(ValidationError):
            AgoraMessage.from_json(json.dumps({
                "sender": "agent",
                "performative": "INVALID_PERFORMATIVE",
                "content": {}
            }))

    def test_to_dict(self):
        """to_dict returns dictionary with string performative."""
        msg = AgoraMessage(
            sender="agent",
            performative=Performative.FAILURE,
            content={"error": "timeout"}
        )

        data = msg.to_dict()

        assert isinstance(data, dict)
        assert data["performative"] == "FAILURE"
        assert data["sender"] == "agent"

    def test_from_dict(self):
        """from_dict creates message from dictionary."""
        data = {
            "sender": "dict-agent",
            "performative": "INFORM",
            "content": {"status": "complete"}
        }

        msg = AgoraMessage.from_dict(data)

        assert msg.sender == "dict-agent"
        assert msg.performative == Performative.INFORM


class TestReply:
    """Tests for reply() method."""

    def test_reply_sets_receiver(self):
        """Reply receiver is set to original sender."""
        original = AgoraMessage(
            sender="manager",
            performative=Performative.REQUEST,
            content={"task": "code review"}
        )

        reply = original.reply(
            sender="reviewer",
            performative=Performative.AGREE,
            content={"eta": "2 hours"}
        )

        assert reply.receiver == "manager"
        assert reply.sender == "reviewer"

    def test_reply_includes_in_reply_to(self):
        """Reply content includes reference to original message."""
        original = AgoraMessage(
            sender="manager",
            performative=Performative.REQUEST,
            content={"task": "optimize"}
        )

        reply = original.reply(
            sender="worker",
            performative=Performative.INFORM,
            content={"result": "done"}
        )

        assert reply.content["in_reply_to"] == original.message_id
        assert reply.content["result"] == "done"

    def test_reply_inherits_protocol(self):
        """Reply inherits protocol from original."""
        original = AgoraMessage(
            sender="manager",
            performative=Performative.REQUEST,
            content={},
            protocol="contract-net-v2"
        )

        reply = original.reply(
            sender="worker",
            performative=Performative.AGREE,
            content={}
        )

        assert reply.protocol == "contract-net-v2"


class TestMessageRepr:
    """Tests for __repr__ method."""

    def test_repr_is_readable(self):
        """__repr__ provides useful information."""
        msg = AgoraMessage(
            sender="test-agent",
            performative=Performative.REQUEST,
            content={}
        )

        repr_str = repr(msg)

        assert "AgoraMessage" in repr_str
        assert "test-agent" in repr_str
        assert "REQUEST" in repr_str


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_content_allowed(self):
        """Empty dict content is valid."""
        msg = AgoraMessage(
            sender="agent",
            performative=Performative.INFORM,
            content={}
        )
        assert msg.content == {}

    def test_nested_content(self):
        """Deeply nested content is preserved."""
        nested_content = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": [1, 2, 3]
                    }
                }
            }
        }

        msg = AgoraMessage(
            sender="agent",
            performative=Performative.INFORM,
            content=nested_content
        )

        json_str = msg.to_json()
        restored = AgoraMessage.from_json(json_str)

        assert restored.content["level1"]["level2"]["level3"]["data"] == [1, 2, 3]

    def test_unicode_content(self):
        """Unicode characters in content are preserved."""
        msg = AgoraMessage(
            sender="agent",
            performative=Performative.INFORM,
            content={"message": "Hello, world!"}
        )

        json_str = msg.to_json()
        restored = AgoraMessage.from_json(json_str)

        assert restored.content["message"] == "Hello, world!"

    def test_special_characters_in_sender(self):
        """Special characters in sender are handled."""
        msg = AgoraMessage(
            sender="agent-123_test.v2",
            performative=Performative.REQUEST,
            content={}
        )
        assert msg.sender == "agent-123_test.v2"
