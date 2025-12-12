"""
Secure Event Bus with Cryptographic Message Signing.

EPIC: MD-3117 - Agora Phase 2: Secure Message Bus (Signed Messages)
AC-3: SecureEventBus enforces message signing and verification

This module provides a secure wrapper around the EventBus that enforces
cryptographic signing and verification of all messages.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-104)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from maestro_hive.agora.acl import AgoraMessage
from maestro_hive.agora.signed_message import (
    SecurityError,
    SignableMessage,
    SignedMessage,
    sign_message,
)

if TYPE_CHECKING:
    from maestro_hive.agora.identity.agent_identity import AgentIdentity
    from maestro_hive.agora.identity.trust_registry import TrustRegistry

logger = logging.getLogger(__name__)


# Type aliases for callbacks
MessageCallback = Callable[[SignedMessage], None]
AsyncMessageCallback = Callable[[SignedMessage], Any]


@dataclass
class Subscription:
    """Represents a subscription to a topic."""
    subscription_id: str
    topic: str
    callback: MessageCallback
    subscriber_did: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SecureEventBus:
    """
    Event Bus with mandatory message signing and verification.

    This class wraps standard pub/sub functionality with security:
    - All published messages must be signed
    - All delivered messages are verified before callback invocation
    - Invalid/tampered messages are rejected with SecurityError

    EPIC: MD-3117 AC-3

    Example:
        >>> from maestro_hive.agora.identity import AgentIdentity, TrustRegistry
        >>>
        >>> # Setup identities
        >>> alice = AgentIdentity.generate(name="Alice")
        >>> bob = AgentIdentity.generate(name="Bob")
        >>>
        >>> # Create registry and bus
        >>> registry = TrustRegistry()
        >>> registry.register_identity(alice)
        >>> registry.register_identity(bob)
        >>>
        >>> bus = SecureEventBus(trust_registry=registry)
        >>>
        >>> # Subscribe
        >>> def on_message(msg: SignedMessage):
        ...     print(f"Received: {msg.message.content}")
        >>>
        >>> bus.subscribe("tasks", on_message)
        >>>
        >>> # Publish signed message
        >>> msg = AgoraMessage(sender=alice.did, ...)
        >>> bus.publish("tasks", msg, signer=alice)
    """

    def __init__(
        self,
        trust_registry: Optional["TrustRegistry"] = None,
        require_signing: bool = True,
        verify_on_receive: bool = True,
    ):
        """
        Initialize the secure event bus.

        Args:
            trust_registry: Registry to lookup public keys for verification
            require_signing: If True, reject unsigned messages (default True)
            verify_on_receive: If True, verify signatures before delivery (default True)
        """
        self._trust_registry = trust_registry
        self._require_signing = require_signing
        self._verify_on_receive = verify_on_receive

        # Topic -> list of subscriptions
        self._subscriptions: Dict[str, List[Subscription]] = {}

        # Track subscription IDs
        self._subscription_ids: Set[str] = set()

        # Store identities for verification (DID -> AgentIdentity)
        self._identities: Dict[str, "AgentIdentity"] = {}

        # Message queue for async processing
        self._message_queue: asyncio.Queue = asyncio.Queue()

        # Statistics
        self._stats = {
            "messages_published": 0,
            "messages_delivered": 0,
            "messages_rejected": 0,
            "verification_failures": 0,
        }

        logger.info(
            f"SecureEventBus initialized (require_signing={require_signing}, "
            f"verify_on_receive={verify_on_receive})"
        )

    def register_identity(self, identity: "AgentIdentity") -> None:
        """
        Register an identity for signature verification.

        Args:
            identity: The agent identity to register
        """
        self._identities[identity.did] = identity
        logger.debug(f"Identity registered: {identity.did[:16]}")

    def subscribe(
        self,
        topic: str,
        callback: MessageCallback,
        subscriber_did: Optional[str] = None,
    ) -> str:
        """
        Subscribe to a topic.

        Args:
            topic: The topic to subscribe to
            callback: Function to call when messages arrive
            subscriber_did: Optional DID of the subscriber

        Returns:
            Subscription ID for unsubscribing
        """
        subscription_id = str(uuid4())

        subscription = Subscription(
            subscription_id=subscription_id,
            topic=topic,
            callback=callback,
            subscriber_did=subscriber_did,
        )

        if topic not in self._subscriptions:
            self._subscriptions[topic] = []

        self._subscriptions[topic].append(subscription)
        self._subscription_ids.add(subscription_id)

        logger.debug(f"Subscription {subscription_id[:8]} created for topic '{topic}'")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.

        Args:
            subscription_id: The subscription to remove

        Returns:
            True if subscription was found and removed
        """
        if subscription_id not in self._subscription_ids:
            return False

        for topic, subs in self._subscriptions.items():
            for sub in subs:
                if sub.subscription_id == subscription_id:
                    subs.remove(sub)
                    self._subscription_ids.remove(subscription_id)
                    logger.debug(f"Subscription {subscription_id[:8]} removed")
                    return True

        return False

    def publish(
        self,
        topic: str,
        message: AgoraMessage,
        signer: Optional["AgentIdentity"] = None,
    ) -> bool:
        """
        Publish a signed message to a topic.

        Args:
            topic: The topic to publish to
            message: The message to publish
            signer: The identity to sign with (required if require_signing=True)

        Returns:
            True if message was delivered to at least one subscriber

        Raises:
            SecurityError: If signing required but no signer provided
        """
        # Enforce signing requirement
        if self._require_signing and signer is None:
            raise SecurityError(
                "SecureEventBus requires all messages to be signed. "
                "Provide a signer identity or set require_signing=False."
            )

        # Sign the message
        if signer:
            signed_msg = sign_message(message, signer)
            logger.debug(
                f"Message {message.message_id[:8]} signed by {signer.did[:16]}"
            )
        else:
            # Create unsigned wrapper (only if require_signing=False)
            signable = SignableMessage.from_agora_message(message)
            signed_msg = SignedMessage(
                message=signable,
                signer_did=message.sender,
                signature=b"",
                signed_at=datetime.now(timezone.utc).isoformat(),
            )

        self._stats["messages_published"] += 1

        # Deliver to subscribers
        delivered = self._deliver_to_subscribers(topic, signed_msg)

        return delivered > 0

    def _deliver_to_subscribers(
        self,
        topic: str,
        signed_msg: SignedMessage,
    ) -> int:
        """
        Deliver a message to all topic subscribers.

        Args:
            topic: The topic to deliver to
            signed_msg: The signed message

        Returns:
            Number of successful deliveries
        """
        if topic not in self._subscriptions:
            logger.debug(f"No subscribers for topic '{topic}'")
            return 0

        delivered = 0
        for subscription in self._subscriptions[topic]:
            try:
                # Verify signature if required
                if self._verify_on_receive:
                    if not self._verify_message(signed_msg):
                        self._stats["verification_failures"] += 1
                        logger.warning(
                            f"Message {signed_msg.message.message_id[:8]} "
                            f"verification failed, not delivering"
                        )
                        continue

                # Deliver to callback
                subscription.callback(signed_msg)
                delivered += 1
                self._stats["messages_delivered"] += 1

            except Exception as e:
                logger.error(
                    f"Error delivering to subscription "
                    f"{subscription.subscription_id[:8]}: {e}"
                )

        return delivered

    def _verify_message(self, signed_msg: SignedMessage) -> bool:
        """
        Verify a message's signature using the trust registry.

        Args:
            signed_msg: The message to verify

        Returns:
            True if signature is valid or verification is disabled
        """
        if not self._verify_on_receive:
            return True

        if not signed_msg.signature:
            logger.warning("Message has no signature")
            return False

        # Lookup signer's record in trust registry
        if not self._trust_registry:
            logger.warning(
                "No trust registry configured, cannot verify signatures"
            )
            return False

        # Get trust record - it stores the signer identity
        trust_record = self._trust_registry.get(signed_msg.signer_did)
        if not trust_record:
            logger.warning(
                f"Unknown signer {signed_msg.signer_did[:16]}, "
                f"cannot verify signature"
            )
            return False

        # Use the stored identity for verification
        signer_identity = self._identities.get(signed_msg.signer_did)
        if not signer_identity:
            logger.warning(
                f"No identity stored for {signed_msg.signer_did[:16]}"
            )
            return False

        return signed_msg.verify(signer_identity)

    def publish_broadcast(
        self,
        message: AgoraMessage,
        signer: "AgentIdentity",
        topics: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Publish a message to multiple topics.

        Args:
            message: The message to broadcast
            signer: Identity to sign with
            topics: List of topics (defaults to all subscribed topics)

        Returns:
            Dict mapping topic -> whether delivery succeeded
        """
        if topics is None:
            topics = list(self._subscriptions.keys())

        results = {}
        for topic in topics:
            results[topic] = self.publish(topic, message, signer)

        return results

    async def publish_async(
        self,
        topic: str,
        message: AgoraMessage,
        signer: Optional["AgentIdentity"] = None,
    ) -> bool:
        """
        Async version of publish.

        Args:
            topic: The topic to publish to
            message: The message to publish
            signer: The identity to sign with

        Returns:
            True if message was delivered
        """
        # Run sync publish in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.publish(topic, message, signer)
        )

    def get_subscribers(self, topic: str) -> List[str]:
        """Get list of subscription IDs for a topic."""
        if topic not in self._subscriptions:
            return []
        return [s.subscription_id for s in self._subscriptions[topic]]

    def get_topics(self) -> List[str]:
        """Get all topics with active subscriptions."""
        return list(self._subscriptions.keys())

    def get_stats(self) -> Dict[str, int]:
        """Get bus statistics."""
        return self._stats.copy()

    def clear_subscriptions(self) -> None:
        """Remove all subscriptions."""
        self._subscriptions.clear()
        self._subscription_ids.clear()
        logger.info("All subscriptions cleared")

    def set_trust_registry(self, registry: "TrustRegistry") -> None:
        """Set or update the trust registry."""
        self._trust_registry = registry
        logger.info("Trust registry updated")


class InMemorySecureEventBus(SecureEventBus):
    """
    In-memory implementation of SecureEventBus for testing.

    Provides same security guarantees as SecureEventBus but with
    additional testing utilities.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._message_log: List[SignedMessage] = []

    def publish(
        self,
        topic: str,
        message: AgoraMessage,
        signer: Optional["AgentIdentity"] = None,
    ) -> bool:
        """Publish with message logging."""
        # Log before delivery attempt
        if signer:
            signed_msg = sign_message(message, signer)
            self._message_log.append(signed_msg)

        return super().publish(topic, message, signer)

    def get_message_log(self) -> List[SignedMessage]:
        """Get all published messages for testing."""
        return self._message_log.copy()

    def clear_message_log(self) -> None:
        """Clear the message log."""
        self._message_log.clear()

    def get_last_message(self) -> Optional[SignedMessage]:
        """Get the last published message."""
        if self._message_log:
            return self._message_log[-1]
        return None


# Convenience functions
def create_secure_bus(
    trust_registry: Optional["TrustRegistry"] = None,
) -> SecureEventBus:
    """Create a secure event bus with default settings."""
    return SecureEventBus(trust_registry=trust_registry)


def create_test_bus() -> InMemorySecureEventBus:
    """Create a test bus without signature requirements."""
    return InMemorySecureEventBus(
        require_signing=False,
        verify_on_receive=False,
    )
