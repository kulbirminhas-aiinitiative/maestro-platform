"""
Agora Module - Agent Marketplace Architecture

Provides infrastructure for agent-to-agent communication, identity,
and trust in the Maestro Hive ecosystem.

Phase 2 Components:
- identity: Self-Sovereign Identity (SSI) for agents (MD-3104)
- event_bus: Pub/Sub event communication (MD-3100)
- acl: Agent Communication Language schema
- guilds: Guild definitions for agent capabilities (MD-3107)
- registry: Agent registration and discovery (MD-3107)
- router: Capability-based agent routing (MD-3107)
- signed_message: Cryptographic message signing (MD-3117)
- secure_event_bus: Secure pub/sub with signing (MD-3117)
"""

from . import identity
from .event_bus import EventBus
from .event_bus_memory import InMemoryEventBus
from .acl import (
    AgoraMessage,
    Performative,
    ValidationError,
)
from .guilds import Guild, GuildProfile, GuildType
from .registry import AgentRegistry, RegisteredAgent, AgentCapabilities, AgentStatus
from .router import GuildRouter, RoutingRequest, RoutingResult, RoutingStrategy
from .signed_message import (
    SignableMessage,
    SignedMessage,
    SecurityError,
    sign_message,
    verify_message,
)
from .secure_event_bus import (
    SecureEventBus,
    InMemorySecureEventBus,
    create_secure_bus,
    create_test_bus,
)

__all__ = [
    # Identity
    "identity",
    # Event Bus
    "EventBus",
    "InMemoryEventBus",
    # ACL
    "AgoraMessage",
    "Performative",
    "ValidationError",
    # Guilds (MD-3107 AC-1)
    "Guild",
    "GuildProfile",
    "GuildType",
    # Registry (MD-3107 AC-2, AC-4)
    "AgentRegistry",
    "RegisteredAgent",
    "AgentCapabilities",
    "AgentStatus",
    # Router (MD-3107 AC-3)
    "GuildRouter",
    "RoutingRequest",
    "RoutingResult",
    "RoutingStrategy",
    # Signed Messages (MD-3117 AC-1, AC-2)
    "SignableMessage",
    "SignedMessage",
    "SecurityError",
    "sign_message",
    "verify_message",
    # Secure Event Bus (MD-3117 AC-3)
    "SecureEventBus",
    "InMemorySecureEventBus",
    "create_secure_bus",
    "create_test_bus",
]
