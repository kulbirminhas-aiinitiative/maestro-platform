"""
Trust Registry Module - Managing Agent Trust Relationships

Implements a registry for tracking agent identities and their
trust levels within the Agora architecture.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-4: Create TrustRegistry for managing agent trust levels
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .agent_identity import AgentIdentity


class TrustLevel(str, Enum):
    """Trust levels for agents."""
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    HIGHLY_TRUSTED = "highly_trusted"

    @property
    def numeric_value(self) -> int:
        """Get numeric value for comparison."""
        return {
            TrustLevel.UNKNOWN: 0,
            TrustLevel.VERIFIED: 1,
            TrustLevel.TRUSTED: 2,
            TrustLevel.HIGHLY_TRUSTED: 3,
        }[self]

    def __lt__(self, other: "TrustLevel") -> bool:
        return self.numeric_value < other.numeric_value

    def __le__(self, other: "TrustLevel") -> bool:
        return self.numeric_value <= other.numeric_value

    def __gt__(self, other: "TrustLevel") -> bool:
        return self.numeric_value > other.numeric_value

    def __ge__(self, other: "TrustLevel") -> bool:
        return self.numeric_value >= other.numeric_value


@dataclass
class TrustRecord:
    """
    Record of an agent's trust status.

    Tracks trust level, interaction history, and reputation.
    """
    did: str
    name: str
    public_key_hex: str
    trust_level: TrustLevel = TrustLevel.UNKNOWN
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_interaction: Optional[datetime] = None
    successful_interactions: int = 0
    failed_interactions: int = 0
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def reputation_score(self) -> float:
        """
        Calculate reputation score (0.0 to 1.0).

        Based on successful/total interaction ratio.
        """
        total = self.successful_interactions + self.failed_interactions
        if total == 0:
            return 0.5  # Neutral for new agents
        return self.successful_interactions / total

    @property
    def total_interactions(self) -> int:
        """Get total number of interactions."""
        return self.successful_interactions + self.failed_interactions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "did": self.did,
            "name": self.name,
            "public_key_hex": self.public_key_hex,
            "trust_level": self.trust_level.value,
            "registered_at": self.registered_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "successful_interactions": self.successful_interactions,
            "failed_interactions": self.failed_interactions,
            "capabilities": self.capabilities,
            "reputation_score": self.reputation_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustRecord":
        """Create from dictionary."""
        last_interaction = None
        if data.get("last_interaction"):
            last_interaction = datetime.fromisoformat(data["last_interaction"])

        return cls(
            did=data["did"],
            name=data["name"],
            public_key_hex=data["public_key_hex"],
            trust_level=TrustLevel(data.get("trust_level", "unknown")),
            registered_at=datetime.fromisoformat(data["registered_at"]),
            last_interaction=last_interaction,
            successful_interactions=data.get("successful_interactions", 0),
            failed_interactions=data.get("failed_interactions", 0),
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
        )


class TrustRegistry:
    """
    Registry for managing agent identities and trust relationships.

    Features:
    - Agent registration and lookup
    - Trust level management
    - Interaction tracking
    - Trust decay over time
    - Reputation calculation

    Example:
        >>> registry = TrustRegistry()
        >>> registry.register(identity)
        >>> registry.set_trust_level(identity.did, TrustLevel.TRUSTED)
        >>> registry.record_interaction(identity.did, success=True)
    """

    def __init__(
        self,
        trust_decay_days: int = 30,
        auto_decay: bool = True,
    ):
        """
        Initialize the trust registry.

        Args:
            trust_decay_days: Days of inactivity before trust decays
            auto_decay: Whether to automatically decay trust on lookup
        """
        self._records: Dict[str, TrustRecord] = {}
        self._by_name: Dict[str, str] = {}  # name -> did
        self._trust_decay_days = trust_decay_days
        self._auto_decay = auto_decay

    def register(
        self,
        identity: "AgentIdentity",
        initial_trust: TrustLevel = TrustLevel.UNKNOWN,
    ) -> TrustRecord:
        """
        Register an agent identity.

        Args:
            identity: The agent identity to register
            initial_trust: Initial trust level

        Returns:
            The created TrustRecord
        """
        record = TrustRecord(
            did=identity.did,
            name=identity.name,
            public_key_hex=identity.public_key_hex,
            trust_level=initial_trust,
            capabilities=identity.capabilities.copy(),
            metadata=identity.metadata.copy(),
        )
        self._records[identity.did] = record
        self._by_name[identity.name] = identity.did
        return record

    def get(self, did: str) -> Optional[TrustRecord]:
        """
        Get a trust record by DID.

        Args:
            did: Decentralized Identifier

        Returns:
            TrustRecord if found, None otherwise
        """
        record = self._records.get(did)
        if record and self._auto_decay:
            self._apply_decay(record)
        return record

    def get_by_name(self, name: str) -> Optional[TrustRecord]:
        """Get a trust record by agent name."""
        did = self._by_name.get(name)
        if did:
            return self.get(did)
        return None

    def is_registered(self, did: str) -> bool:
        """Check if an agent is registered."""
        return did in self._records

    def unregister(self, did: str) -> bool:
        """
        Remove an agent from the registry.

        Args:
            did: Decentralized Identifier

        Returns:
            True if removed, False if not found
        """
        record = self._records.pop(did, None)
        if record:
            self._by_name.pop(record.name, None)
            return True
        return False

    def set_trust_level(self, did: str, level: TrustLevel) -> bool:
        """
        Set the trust level for an agent.

        Args:
            did: Decentralized Identifier
            level: New trust level

        Returns:
            True if updated, False if agent not found
        """
        record = self._records.get(did)
        if record:
            record.trust_level = level
            return True
        return False

    def get_trust_level(self, did: str) -> TrustLevel:
        """
        Get the current trust level for an agent.

        Args:
            did: Decentralized Identifier

        Returns:
            Trust level (UNKNOWN if not found)
        """
        record = self.get(did)
        if record:
            return record.trust_level
        return TrustLevel.UNKNOWN

    def record_interaction(
        self,
        did: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record an interaction with an agent.

        Args:
            did: Decentralized Identifier
            success: Whether the interaction was successful
            details: Optional interaction details

        Returns:
            True if recorded, False if agent not found
        """
        record = self._records.get(did)
        if not record:
            return False

        record.last_interaction = datetime.now(timezone.utc)

        if success:
            record.successful_interactions += 1
            # Potentially elevate trust based on consistent success
            self._consider_trust_elevation(record)
        else:
            record.failed_interactions += 1
            # Consider trust demotion on failures
            self._consider_trust_demotion(record)

        return True

    def _consider_trust_elevation(self, record: TrustRecord) -> None:
        """Consider elevating trust based on interaction history."""
        # Require minimum interactions and high reputation
        if record.total_interactions < 5:
            return

        if record.reputation_score < 0.9:
            return

        # Elevate by one level if conditions met
        if record.trust_level == TrustLevel.UNKNOWN:
            record.trust_level = TrustLevel.VERIFIED
        elif record.trust_level == TrustLevel.VERIFIED and record.total_interactions >= 20:
            record.trust_level = TrustLevel.TRUSTED
        elif record.trust_level == TrustLevel.TRUSTED and record.total_interactions >= 50:
            record.trust_level = TrustLevel.HIGHLY_TRUSTED

    def _consider_trust_demotion(self, record: TrustRecord) -> None:
        """Consider demoting trust based on failures."""
        # Demote if reputation drops significantly
        if record.reputation_score < 0.5:
            if record.trust_level == TrustLevel.HIGHLY_TRUSTED:
                record.trust_level = TrustLevel.TRUSTED
            elif record.trust_level == TrustLevel.TRUSTED:
                record.trust_level = TrustLevel.VERIFIED
            elif record.trust_level == TrustLevel.VERIFIED:
                record.trust_level = TrustLevel.UNKNOWN

    def _apply_decay(self, record: TrustRecord) -> None:
        """Apply trust decay based on inactivity."""
        if not record.last_interaction:
            return

        days_inactive = (
            datetime.now(timezone.utc) - record.last_interaction
        ).days

        if days_inactive < self._trust_decay_days:
            return

        # Decay one level per decay period
        decay_periods = days_inactive // self._trust_decay_days

        for _ in range(decay_periods):
            if record.trust_level == TrustLevel.HIGHLY_TRUSTED:
                record.trust_level = TrustLevel.TRUSTED
            elif record.trust_level == TrustLevel.TRUSTED:
                record.trust_level = TrustLevel.VERIFIED
            elif record.trust_level == TrustLevel.VERIFIED:
                record.trust_level = TrustLevel.UNKNOWN
            else:
                break  # Already at UNKNOWN

    def get_trusted_agents(
        self,
        min_level: TrustLevel = TrustLevel.VERIFIED,
    ) -> List[TrustRecord]:
        """
        Get all agents with at least the specified trust level.

        Args:
            min_level: Minimum trust level

        Returns:
            List of matching TrustRecords
        """
        results = []
        for record in self._records.values():
            if self._auto_decay:
                self._apply_decay(record)
            if record.trust_level >= min_level:
                results.append(record)
        return results

    def get_agents_with_capability(
        self,
        capability: str,
        min_level: TrustLevel = TrustLevel.UNKNOWN,
    ) -> List[TrustRecord]:
        """
        Find agents with a specific capability.

        Args:
            capability: Required capability
            min_level: Minimum trust level

        Returns:
            List of matching TrustRecords
        """
        results = []
        for record in self._records.values():
            if capability in record.capabilities and record.trust_level >= min_level:
                results.append(record)
        return results

    def count(self) -> int:
        """Get total number of registered agents."""
        return len(self._records)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dictionary."""
        return {
            "trust_decay_days": self._trust_decay_days,
            "records": [r.to_dict() for r in self._records.values()],
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustRegistry":
        """Create from dictionary."""
        registry = cls(
            trust_decay_days=data.get("trust_decay_days", 30),
        )
        for record_data in data.get("records", []):
            record = TrustRecord.from_dict(record_data)
            registry._records[record.did] = record
            registry._by_name[record.name] = record.did
        return registry

    @classmethod
    def from_json(cls, json_str: str) -> "TrustRegistry":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        """Save registry to file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "TrustRegistry":
        """Load registry from file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
        self._by_name.clear()


# Global registry instance
_global_registry: Optional[TrustRegistry] = None


def get_trust_registry() -> TrustRegistry:
    """Get the global trust registry instance."""
    global _global_registry
    if _global_registry is None:
        decay_days = int(os.environ.get("TRUST_DECAY_DAYS", "30"))
        _global_registry = TrustRegistry(trust_decay_days=decay_days)
    return _global_registry


def reset_trust_registry() -> None:
    """Reset the global trust registry."""
    global _global_registry
    _global_registry = None
