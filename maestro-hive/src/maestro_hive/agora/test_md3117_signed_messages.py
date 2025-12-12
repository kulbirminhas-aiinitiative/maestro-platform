"""
Test Suite for MD-3117: Secure Message Bus (Signed Messages)

EPIC: MD-3117 - Agora Phase 2: Secure Message Bus
AC-4: Unit tests verify tamper detection and valid message flow

Tests cover:
- AC-1: SignableMessage sign/verify methods
- AC-2: SignedMessage wrapper with automatic signing
- AC-3: SecureEventBus signing and verification enforcement
- AC-4: Tamper detection, spoofing prevention, invalid signature rejection
"""

import pytest
import json
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch

from maestro_hive.agora.acl import AgoraMessage, Performative, ValidationError
from maestro_hive.agora.signed_message import (
    SignableMessage,
    SignedMessage,
    SecurityError,
    sign_message,
    verify_message,
)
from maestro_hive.agora.secure_event_bus import (
    SecureEventBus,
    InMemorySecureEventBus,
    Subscription,
    create_secure_bus,
    create_test_bus,
)
from maestro_hive.agora.identity.agent_identity import AgentIdentity
from maestro_hive.agora.identity.trust_registry import TrustRegistry, TrustLevel


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def agent_alice():
    """Create Alice agent identity."""
    return AgentIdentity.create(name="Alice")


@pytest.fixture
def agent_bob():
    """Create Bob agent identity."""
    return AgentIdentity.create(name="Bob")


@pytest.fixture
def agent_eve():
    """Create Eve (attacker) agent identity."""
    return AgentIdentity.create(name="Eve")


@pytest.fixture
def trust_registry(agent_alice, agent_bob):
    """Create trust registry with Alice and Bob registered."""
    registry = TrustRegistry()
    registry.register(agent_alice, TrustLevel.VERIFIED)
    registry.register(agent_bob, TrustLevel.VERIFIED)
    return registry


@pytest.fixture
def secure_bus(trust_registry, agent_alice, agent_bob):
    """Create secure event bus with trust registry."""
    bus = SecureEventBus(trust_registry=trust_registry)
    bus.register_identity(agent_alice)
    bus.register_identity(agent_bob)
    return bus


@pytest.fixture
def test_message(agent_alice):
    """Create a test message from Alice."""
    return AgoraMessage(
        sender=agent_alice.did,
        performative=Performative.REQUEST,
        content={"task": "code_review", "priority": "high"},
        receiver="BROADCAST",
    )


# ============================================================
# AC-1: SignableMessage Sign/Verify Tests
# ============================================================

class TestAC1_SignableMessage:
    """Tests for AgoraMessage signature field and sign/verify methods."""

    def test_signable_message_creation(self, agent_alice):
        """SignableMessage can be created with required fields."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )

        assert msg.sender == agent_alice.did
        assert msg.performative == Performative.REQUEST
        assert msg.content == {"task": "test"}
        assert msg.signature is None  # Unsigned by default

    def test_sign_message(self, agent_alice):
        """Message can be signed with agent identity."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )

        msg.sign(agent_alice)

        assert msg.signature is not None
        assert len(msg.signature) > 0
        assert msg.is_signed()

    def test_verify_valid_signature(self, agent_alice):
        """Valid signature verifies successfully."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )

        msg.sign(agent_alice)
        assert msg.verify(agent_alice) is True

    def test_verify_fails_for_different_identity(self, agent_alice, agent_bob):
        """Signature doesn't verify against wrong identity."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )

        msg.sign(agent_alice)

        # Bob's identity should not verify Alice's signature
        assert msg.verify(agent_bob) is False

    def test_unsigned_message_fails_verification(self, agent_alice):
        """Unsigned message fails verification."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )

        # Never signed
        assert msg.verify(agent_alice) is False

    def test_signable_bytes_deterministic(self, agent_alice):
        """to_signable_bytes produces deterministic output."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test", "priority": 1},
            message_id="fixed-id",
            timestamp="2025-01-01T00:00:00+00:00",
        )

        bytes1 = msg.to_signable_bytes()
        bytes2 = msg.to_signable_bytes()

        assert bytes1 == bytes2

    def test_different_content_different_bytes(self, agent_alice):
        """Different content produces different signable bytes."""
        msg1 = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test1"},
            message_id="id1",
            timestamp="2025-01-01T00:00:00+00:00",
        )

        msg2 = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test2"},
            message_id="id1",
            timestamp="2025-01-01T00:00:00+00:00",
        )

        assert msg1.to_signable_bytes() != msg2.to_signable_bytes()

    def test_serialization_preserves_signature(self, agent_alice):
        """Signature survives JSON serialization."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )
        msg.sign(agent_alice)

        json_str = msg.to_json()
        restored = SignableMessage.from_json(json_str)

        assert restored.signature is not None
        assert restored.verify(agent_alice) is True

    def test_from_agora_message(self, test_message, agent_alice):
        """Can convert AgoraMessage to SignableMessage."""
        signable = SignableMessage.from_agora_message(test_message)

        assert signable.sender == test_message.sender
        assert signable.performative == test_message.performative
        assert signable.content == test_message.content
        assert signable.signature is None

    def test_to_agora_message(self, agent_alice):
        """Can convert SignableMessage back to AgoraMessage."""
        signable = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.INFORM,
            content={"result": "done"},
        )
        signable.sign(agent_alice)

        agora_msg = signable.to_agora_message()

        assert isinstance(agora_msg, AgoraMessage)
        assert agora_msg.sender == signable.sender
        # Note: Signature is lost in conversion (AgoraMessage doesn't have it)


# ============================================================
# AC-2: SignedMessage Wrapper Tests
# ============================================================

class TestAC2_SignedMessageWrapper:
    """Tests for SignedMessage automatic signing wrapper."""

    def test_create_signed_message(self, test_message, agent_alice):
        """SignedMessage.create signs automatically."""
        signed = SignedMessage.create(test_message, agent_alice)

        assert signed.signature is not None
        assert signed.signer_did == agent_alice.did
        assert signed.message.is_signed()

    def test_signed_message_verification(self, test_message, agent_alice):
        """SignedMessage can be verified."""
        signed = SignedMessage.create(test_message, agent_alice)

        assert signed.verify(agent_alice) is True

    def test_signed_message_wrong_verifier(self, test_message, agent_alice, agent_bob):
        """SignedMessage fails verification with wrong identity."""
        signed = SignedMessage.create(test_message, agent_alice)

        assert signed.verify(agent_bob) is False

    def test_get_underlying_message(self, test_message, agent_alice):
        """Can extract original message from SignedMessage."""
        signed = SignedMessage.create(test_message, agent_alice)
        extracted = signed.get_message()

        assert extracted.sender == test_message.sender
        assert extracted.content == test_message.content

    def test_signed_message_serialization(self, test_message, agent_alice):
        """SignedMessage survives serialization."""
        signed = SignedMessage.create(test_message, agent_alice)

        json_str = signed.to_json()
        restored = SignedMessage.from_json(json_str)

        assert restored.signer_did == signed.signer_did
        assert restored.signature == signed.signature
        assert restored.verify(agent_alice) is True

    def test_sign_message_convenience_function(self, test_message, agent_alice):
        """sign_message() convenience function works."""
        signed = sign_message(test_message, agent_alice)

        assert isinstance(signed, SignedMessage)
        assert signed.verify(agent_alice) is True

    def test_verify_message_convenience_function(self, test_message, agent_alice):
        """verify_message() convenience function works."""
        signed = sign_message(test_message, agent_alice)

        assert verify_message(signed, agent_alice) is True


# ============================================================
# AC-3: SecureEventBus Tests
# ============================================================

class TestAC3_SecureEventBus:
    """Tests for SecureEventBus signing and verification enforcement."""

    def test_subscribe_returns_id(self, secure_bus):
        """subscribe() returns a subscription ID."""
        sub_id = secure_bus.subscribe("test-topic", lambda msg: None)

        assert sub_id is not None
        assert len(sub_id) > 0

    def test_unsubscribe(self, secure_bus):
        """unsubscribe() removes subscription."""
        sub_id = secure_bus.subscribe("test-topic", lambda msg: None)

        assert secure_bus.unsubscribe(sub_id) is True
        assert secure_bus.unsubscribe(sub_id) is False  # Already removed

    def test_publish_requires_signer(self, secure_bus, test_message):
        """SecureEventBus requires signer for publish()."""
        with pytest.raises(SecurityError) as exc_info:
            secure_bus.publish("topic", test_message)  # No signer!

        assert "requires all messages to be signed" in str(exc_info.value)

    def test_publish_with_signer(self, secure_bus, test_message, agent_alice):
        """Signed message is published successfully."""
        received_messages: List[SignedMessage] = []

        def callback(msg: SignedMessage):
            received_messages.append(msg)

        secure_bus.subscribe("tasks", callback)
        result = secure_bus.publish("tasks", test_message, signer=agent_alice)

        assert result is True
        assert len(received_messages) == 1
        assert received_messages[0].signer_did == agent_alice.did

    def test_publish_verifies_before_delivery(
        self, trust_registry, test_message, agent_alice, agent_eve
    ):
        """Messages with invalid signatures are not delivered."""
        # Eve is NOT in the trust registry
        bus = SecureEventBus(trust_registry=trust_registry)

        received_messages: List[SignedMessage] = []

        def callback(msg: SignedMessage):
            received_messages.append(msg)

        bus.subscribe("tasks", callback)

        # Create message claiming to be from Alice but signed by Eve
        spoofed_msg = AgoraMessage(
            sender=agent_alice.did,  # Claims Alice
            performative=Performative.REQUEST,
            content={"malicious": True},
        )

        # Eve signs it (but Eve isn't trusted)
        result = bus.publish("tasks", spoofed_msg, signer=agent_eve)

        # Message should not be delivered
        assert len(received_messages) == 0

    def test_multiple_subscribers(self, secure_bus, test_message, agent_alice):
        """Message delivered to multiple subscribers."""
        received1: List[SignedMessage] = []
        received2: List[SignedMessage] = []

        secure_bus.subscribe("tasks", lambda m: received1.append(m))
        secure_bus.subscribe("tasks", lambda m: received2.append(m))

        secure_bus.publish("tasks", test_message, signer=agent_alice)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_topic_isolation(self, secure_bus, test_message, agent_alice):
        """Messages only go to subscribed topics."""
        received: List[SignedMessage] = []

        secure_bus.subscribe("other-topic", lambda m: received.append(m))
        secure_bus.publish("tasks", test_message, signer=agent_alice)

        assert len(received) == 0

    def test_get_stats(self, secure_bus, test_message, agent_alice):
        """Bus tracks statistics."""
        secure_bus.subscribe("tasks", lambda m: None)
        secure_bus.publish("tasks", test_message, signer=agent_alice)

        stats = secure_bus.get_stats()

        assert stats["messages_published"] == 1
        assert stats["messages_delivered"] == 1

    def test_get_topics(self, secure_bus):
        """Can list subscribed topics."""
        secure_bus.subscribe("topic-a", lambda m: None)
        secure_bus.subscribe("topic-b", lambda m: None)

        topics = secure_bus.get_topics()

        assert "topic-a" in topics
        assert "topic-b" in topics

    def test_clear_subscriptions(self, secure_bus):
        """Can clear all subscriptions."""
        secure_bus.subscribe("topic", lambda m: None)
        secure_bus.clear_subscriptions()

        assert len(secure_bus.get_topics()) == 0

    def test_bus_without_signing_requirement(self, trust_registry, test_message):
        """Bus can be configured to not require signing."""
        bus = SecureEventBus(
            trust_registry=trust_registry,
            require_signing=False,
            verify_on_receive=False,
        )

        received: List[SignedMessage] = []
        bus.subscribe("tasks", lambda m: received.append(m))

        # Publish without signer
        result = bus.publish("tasks", test_message)

        assert result is True
        assert len(received) == 1


# ============================================================
# AC-4: Tamper Detection Tests
# ============================================================

class TestAC4_TamperDetection:
    """Tests for tamper detection and security enforcement."""

    def test_tampered_content_detected(self, agent_alice):
        """Modification of content after signing is detected."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"amount": 100},
        )
        msg.sign(agent_alice)

        # Verify original is valid
        assert msg.verify(agent_alice) is True

        # Tamper with content
        msg.content["amount"] = 1000000  # Changed!

        # Verification should now fail
        assert msg.verify(agent_alice) is False

    def test_tampered_sender_detected(self, agent_alice, agent_bob):
        """Modification of sender after signing is detected."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
        )
        msg.sign(agent_alice)

        # Change sender
        msg.sender = agent_bob.did

        # Verification fails
        assert msg.verify(agent_alice) is False

    def test_tampered_receiver_detected(self, agent_alice, agent_bob):
        """Modification of receiver after signing is detected."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "test"},
            receiver=agent_bob.did,
        )
        msg.sign(agent_alice)

        # Change receiver
        msg.receiver = "attacker"

        # Verification fails
        assert msg.verify(agent_alice) is False

    def test_spoofing_attempt_rejected(self, agent_alice, agent_eve):
        """Agent cannot impersonate another agent."""
        # Eve creates a message claiming to be Alice
        spoofed_msg = SignableMessage(
            sender=agent_alice.did,  # Claims to be Alice
            performative=Performative.REQUEST,
            content={"steal": "secrets"},
        )

        # But signs with her own key
        spoofed_msg.sign(agent_eve)

        # Verification against Alice fails
        assert spoofed_msg.verify(agent_alice) is False

        # Verification against Eve succeeds (she did sign it)
        assert spoofed_msg.verify(agent_eve) is True

    def test_replay_attack_mitigation(self, agent_alice):
        """Message ID prevents naive replay attacks."""
        msg1 = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "transfer"},
        )
        msg1.sign(agent_alice)

        # Create second message with same content but different ID
        msg2 = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "transfer"},
        )
        msg2.sign(agent_alice)

        # Both are valid but have different IDs
        assert msg1.message_id != msg2.message_id

    def test_secure_bus_rejects_unknown_signer(self, trust_registry, agent_eve):
        """SecureEventBus rejects messages from unknown signers."""
        bus = SecureEventBus(trust_registry=trust_registry)

        received: List[SignedMessage] = []
        bus.subscribe("tasks", lambda m: received.append(m))

        # Eve is not in trust registry
        msg = AgoraMessage(
            sender=agent_eve.did,
            performative=Performative.REQUEST,
            content={"malicious": True},
        )

        bus.publish("tasks", msg, signer=agent_eve)

        # Message not delivered (unknown signer)
        assert len(received) == 0

    def test_verification_failure_tracked(
        self, trust_registry, test_message, agent_eve
    ):
        """Bus tracks verification failures."""
        bus = SecureEventBus(trust_registry=trust_registry)
        bus.subscribe("tasks", lambda m: None)

        # Eve tries to publish (not trusted)
        msg = AgoraMessage(
            sender=agent_eve.did,
            performative=Performative.REQUEST,
            content={},
        )
        bus.publish("tasks", msg, signer=agent_eve)

        stats = bus.get_stats()
        assert stats["verification_failures"] >= 1


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests for secure message flow."""

    def test_full_message_flow(self, agent_alice, agent_bob):
        """Complete flow: create, sign, serialize, restore, verify."""
        # Alice creates and signs a message
        original = AgoraMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "review", "file": "main.py"},
            receiver=agent_bob.did,
        )
        signed = SignedMessage.create(original, agent_alice)

        # Serialize (simulate network transmission)
        json_str = signed.to_json()

        # Bob receives and restores
        restored = SignedMessage.from_json(json_str)

        # Bob verifies using Alice's public key (from registry)
        assert restored.verify(agent_alice) is True

        # Bob processes the message
        msg = restored.get_message()
        assert msg.content["task"] == "review"

    def test_conversation_flow(self, trust_registry, agent_alice, agent_bob):
        """Multi-message conversation with signing."""
        bus = SecureEventBus(trust_registry=trust_registry)
        # Register identities for verification
        bus.register_identity(agent_alice)
        bus.register_identity(agent_bob)

        bob_inbox: List[SignedMessage] = []
        alice_inbox: List[SignedMessage] = []

        bus.subscribe("bob-inbox", lambda m: bob_inbox.append(m))
        bus.subscribe("alice-inbox", lambda m: alice_inbox.append(m))

        # Alice sends request to Bob
        request = AgoraMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"task": "code review"},
            receiver=agent_bob.did,
        )
        bus.publish("bob-inbox", request, signer=agent_alice)

        # Bob receives and responds
        assert len(bob_inbox) == 1
        received_request = bob_inbox[0].get_message()

        response = received_request.reply(
            sender=agent_bob.did,
            performative=Performative.AGREE,
            content={"eta": "2 hours"},
        )
        bus.publish("alice-inbox", response, signer=agent_bob)

        # Alice receives response
        assert len(alice_inbox) == 1
        assert alice_inbox[0].verify(agent_bob) is True

    def test_broadcast_to_all_topics(self, trust_registry, agent_alice):
        """Test broadcast functionality."""
        bus = SecureEventBus(trust_registry=trust_registry)
        # Register identity for verification
        bus.register_identity(agent_alice)

        topic_a_msgs: List[SignedMessage] = []
        topic_b_msgs: List[SignedMessage] = []

        bus.subscribe("topic-a", lambda m: topic_a_msgs.append(m))
        bus.subscribe("topic-b", lambda m: topic_b_msgs.append(m))

        msg = AgoraMessage(
            sender=agent_alice.did,
            performative=Performative.INFORM,
            content={"announcement": "system update"},
        )

        results = bus.publish_broadcast(msg, agent_alice)

        assert results["topic-a"] is True
        assert results["topic-b"] is True
        assert len(topic_a_msgs) == 1
        assert len(topic_b_msgs) == 1


# ============================================================
# Edge Cases and Error Handling
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_content_signable(self, agent_alice):
        """Message with empty content can be signed."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.INFORM,
            content={},
        )
        msg.sign(agent_alice)

        assert msg.verify(agent_alice) is True

    def test_large_content_signable(self, agent_alice):
        """Message with large content can be signed."""
        large_content = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.INFORM,
            content=large_content,
        )
        msg.sign(agent_alice)

        assert msg.verify(agent_alice) is True

    def test_special_characters_in_content(self, agent_alice):
        """Content with special characters signs correctly."""
        msg = SignableMessage(
            sender=agent_alice.did,
            performative=Performative.INFORM,
            content={
                "unicode": "Hello World",
                "quotes": 'He said "test"',
                "newlines": "line1\nline2",
            },
        )
        msg.sign(agent_alice)

        assert msg.verify(agent_alice) is True

    def test_callback_exception_handled(self, secure_bus, test_message, agent_alice):
        """Bus handles callback exceptions gracefully."""
        def bad_callback(msg):
            raise ValueError("Callback error!")

        secure_bus.subscribe("tasks", bad_callback)

        # Should not raise, but message not delivered
        result = secure_bus.publish("tasks", test_message, signer=agent_alice)

        # Other subscribers would still receive
        stats = secure_bus.get_stats()
        assert stats["messages_published"] == 1


class TestInMemorySecureBus:
    """Tests for InMemorySecureEventBus testing utilities."""

    def test_message_log(self, trust_registry, test_message, agent_alice):
        """Test bus logs all messages."""
        bus = InMemorySecureEventBus(trust_registry=trust_registry)

        bus.subscribe("tasks", lambda m: None)
        bus.publish("tasks", test_message, signer=agent_alice)

        log = bus.get_message_log()
        assert len(log) == 1

    def test_get_last_message(self, trust_registry, agent_alice):
        """Can get last published message."""
        bus = InMemorySecureEventBus(trust_registry=trust_registry)
        bus.subscribe("tasks", lambda m: None)

        msg1 = AgoraMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"seq": 1},
        )
        msg2 = AgoraMessage(
            sender=agent_alice.did,
            performative=Performative.REQUEST,
            content={"seq": 2},
        )

        bus.publish("tasks", msg1, signer=agent_alice)
        bus.publish("tasks", msg2, signer=agent_alice)

        last = bus.get_last_message()
        assert last.message.content["seq"] == 2

    def test_clear_message_log(self, trust_registry, test_message, agent_alice):
        """Can clear message log."""
        bus = InMemorySecureEventBus(trust_registry=trust_registry)
        bus.subscribe("tasks", lambda m: None)
        bus.publish("tasks", test_message, signer=agent_alice)

        bus.clear_message_log()

        assert len(bus.get_message_log()) == 0

    def test_create_test_bus_no_signing(self):
        """create_test_bus() creates permissive bus for testing."""
        bus = create_test_bus()

        msg = AgoraMessage(
            sender="test-agent",
            performative=Performative.INFORM,
            content={},
        )

        received: List[SignedMessage] = []
        bus.subscribe("test", lambda m: received.append(m))

        # Should work without signing
        bus.publish("test", msg)

        assert len(received) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
