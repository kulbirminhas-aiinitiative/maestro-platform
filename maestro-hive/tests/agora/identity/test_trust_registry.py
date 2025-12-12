"""
Tests for TrustRegistry module.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-4: Create TrustRegistry for managing agent trust levels
"""

import json
import pytest
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from maestro_hive.agora.identity.agent_identity import AgentIdentity
from maestro_hive.agora.identity.trust_registry import (
    TrustLevel,
    TrustRecord,
    TrustRegistry,
    get_trust_registry,
    reset_trust_registry,
)


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_level_values(self):
        """Test trust level values."""
        assert TrustLevel.UNKNOWN.value == "unknown"
        assert TrustLevel.VERIFIED.value == "verified"
        assert TrustLevel.TRUSTED.value == "trusted"
        assert TrustLevel.HIGHLY_TRUSTED.value == "highly_trusted"

    def test_level_comparison(self):
        """Test trust level comparison."""
        assert TrustLevel.UNKNOWN < TrustLevel.VERIFIED
        assert TrustLevel.VERIFIED < TrustLevel.TRUSTED
        assert TrustLevel.TRUSTED < TrustLevel.HIGHLY_TRUSTED
        assert TrustLevel.HIGHLY_TRUSTED > TrustLevel.UNKNOWN

    def test_level_ordering(self):
        """Test level numeric values."""
        assert TrustLevel.UNKNOWN.numeric_value == 0
        assert TrustLevel.VERIFIED.numeric_value == 1
        assert TrustLevel.TRUSTED.numeric_value == 2
        assert TrustLevel.HIGHLY_TRUSTED.numeric_value == 3


class TestTrustRecord:
    """Tests for TrustRecord."""

    def test_record_creation(self):
        """Test creating a trust record."""
        record = TrustRecord(
            did="did:agora:test",
            name="test_agent",
            public_key_hex="abc123",
            trust_level=TrustLevel.VERIFIED,
            capabilities=["testing"],
        )

        assert record.did == "did:agora:test"
        assert record.name == "test_agent"
        assert record.trust_level == TrustLevel.VERIFIED

    def test_reputation_score_no_interactions(self):
        """Test reputation score with no interactions."""
        record = TrustRecord(
            did="did:agora:test",
            name="test",
            public_key_hex="abc",
        )
        assert record.reputation_score == 0.5  # Neutral

    def test_reputation_score_successful(self):
        """Test reputation score with successful interactions."""
        record = TrustRecord(
            did="did:agora:test",
            name="test",
            public_key_hex="abc",
            successful_interactions=9,
            failed_interactions=1,
        )
        assert record.reputation_score == 0.9

    def test_reputation_score_failed(self):
        """Test reputation score with failed interactions."""
        record = TrustRecord(
            did="did:agora:test",
            name="test",
            public_key_hex="abc",
            successful_interactions=1,
            failed_interactions=9,
        )
        assert record.reputation_score == 0.1

    def test_total_interactions(self):
        """Test total interactions calculation."""
        record = TrustRecord(
            did="did:agora:test",
            name="test",
            public_key_hex="abc",
            successful_interactions=5,
            failed_interactions=3,
        )
        assert record.total_interactions == 8

    def test_to_dict(self):
        """Test record serialization."""
        record = TrustRecord(
            did="did:agora:test",
            name="test",
            public_key_hex="abc123",
            trust_level=TrustLevel.TRUSTED,
        )
        data = record.to_dict()

        assert data["did"] == "did:agora:test"
        assert data["trust_level"] == "trusted"
        assert "reputation_score" in data

    def test_from_dict(self):
        """Test record deserialization."""
        data = {
            "did": "did:agora:test",
            "name": "test",
            "public_key_hex": "abc",
            "trust_level": "verified",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "successful_interactions": 5,
            "failed_interactions": 2,
        }
        record = TrustRecord.from_dict(data)

        assert record.did == "did:agora:test"
        assert record.trust_level == TrustLevel.VERIFIED
        assert record.successful_interactions == 5


class TestTrustRegistry:
    """Tests for TrustRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a trust registry."""
        return TrustRegistry(trust_decay_days=30, auto_decay=False)

    @pytest.fixture
    def agent(self):
        """Create an agent identity."""
        return AgentIdentity.create(
            name="test_agent",
            capabilities=["testing"],
        )

    def test_register_agent(self, registry, agent):
        """Test registering an agent."""
        record = registry.register(agent)

        assert record.did == agent.did
        assert record.name == agent.name
        assert record.trust_level == TrustLevel.UNKNOWN

    def test_register_with_initial_trust(self, registry, agent):
        """Test registering with initial trust level."""
        record = registry.register(agent, initial_trust=TrustLevel.VERIFIED)
        assert record.trust_level == TrustLevel.VERIFIED

    def test_get_agent(self, registry, agent):
        """Test getting a registered agent."""
        registry.register(agent)
        record = registry.get(agent.did)

        assert record is not None
        assert record.did == agent.did

    def test_get_nonexistent(self, registry):
        """Test getting nonexistent agent."""
        assert registry.get("nonexistent") is None

    def test_get_by_name(self, registry, agent):
        """Test getting agent by name."""
        registry.register(agent)
        record = registry.get_by_name(agent.name)

        assert record is not None
        assert record.name == agent.name

    def test_is_registered(self, registry, agent):
        """Test checking registration status."""
        assert registry.is_registered(agent.did) is False
        registry.register(agent)
        assert registry.is_registered(agent.did) is True

    def test_unregister(self, registry, agent):
        """Test unregistering an agent."""
        registry.register(agent)
        result = registry.unregister(agent.did)

        assert result is True
        assert registry.is_registered(agent.did) is False

    def test_set_trust_level(self, registry, agent):
        """Test setting trust level."""
        registry.register(agent)
        result = registry.set_trust_level(agent.did, TrustLevel.TRUSTED)

        assert result is True
        assert registry.get_trust_level(agent.did) == TrustLevel.TRUSTED

    def test_get_trust_level_unknown_agent(self, registry):
        """Test getting trust level for unknown agent."""
        level = registry.get_trust_level("nonexistent")
        assert level == TrustLevel.UNKNOWN

    def test_record_successful_interaction(self, registry, agent):
        """Test recording successful interaction."""
        registry.register(agent)
        registry.record_interaction(agent.did, success=True)

        record = registry.get(agent.did)
        assert record.successful_interactions == 1
        assert record.last_interaction is not None

    def test_record_failed_interaction(self, registry, agent):
        """Test recording failed interaction."""
        registry.register(agent)
        registry.record_interaction(agent.did, success=False)

        record = registry.get(agent.did)
        assert record.failed_interactions == 1

    def test_trust_elevation_on_success(self, registry, agent):
        """Test automatic trust elevation."""
        registry.register(agent)

        # Record enough successful interactions
        for _ in range(10):
            registry.record_interaction(agent.did, success=True)

        record = registry.get(agent.did)
        assert record.trust_level >= TrustLevel.VERIFIED

    def test_trust_demotion_on_failure(self, registry, agent):
        """Test trust demotion on failures."""
        registry.register(agent, initial_trust=TrustLevel.TRUSTED)

        # Record mostly failures
        for _ in range(10):
            registry.record_interaction(agent.did, success=False)

        record = registry.get(agent.did)
        assert record.trust_level < TrustLevel.TRUSTED

    def test_get_trusted_agents(self, registry):
        """Test getting agents above trust threshold."""
        agent1 = AgentIdentity.create(name="agent1")
        agent2 = AgentIdentity.create(name="agent2")
        agent3 = AgentIdentity.create(name="agent3")

        registry.register(agent1, initial_trust=TrustLevel.UNKNOWN)
        registry.register(agent2, initial_trust=TrustLevel.VERIFIED)
        registry.register(agent3, initial_trust=TrustLevel.TRUSTED)

        trusted = registry.get_trusted_agents(min_level=TrustLevel.VERIFIED)
        assert len(trusted) == 2

    def test_get_agents_with_capability(self, registry):
        """Test finding agents with specific capability."""
        agent1 = AgentIdentity.create(name="a1", capabilities=["testing"])
        agent2 = AgentIdentity.create(name="a2", capabilities=["coding"])

        registry.register(agent1)
        registry.register(agent2)

        testers = registry.get_agents_with_capability("testing")
        assert len(testers) == 1
        assert testers[0].name == "a1"

    def test_count(self, registry, agent):
        """Test agent count."""
        assert registry.count() == 0
        registry.register(agent)
        assert registry.count() == 1

    def test_clear(self, registry, agent):
        """Test clearing registry."""
        registry.register(agent)
        registry.clear()
        assert registry.count() == 0

    def test_to_dict_and_json(self, registry, agent):
        """Test serialization."""
        registry.register(agent)
        data = registry.to_dict()

        assert "records" in data
        assert len(data["records"]) == 1

        json_str = registry.to_json()
        assert agent.did in json_str

    def test_from_dict(self, registry, agent):
        """Test deserialization."""
        registry.register(agent)
        data = registry.to_dict()

        restored = TrustRegistry.from_dict(data)
        assert restored.count() == 1
        assert restored.is_registered(agent.did)


class TestTrustDecay:
    """Tests for trust decay functionality."""

    def test_decay_after_inactivity(self):
        """Test trust decay after period of inactivity."""
        registry = TrustRegistry(trust_decay_days=1, auto_decay=True)
        agent = AgentIdentity.create(name="decay_test")

        registry.register(agent, initial_trust=TrustLevel.HIGHLY_TRUSTED)

        # Simulate old interaction
        record = registry._records[agent.did]
        record.last_interaction = datetime.now(timezone.utc) - timedelta(days=100)

        # Get record to trigger decay
        decayed = registry.get(agent.did)
        assert decayed.trust_level < TrustLevel.HIGHLY_TRUSTED


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_trust_registry(self):
        """Test getting global registry."""
        reset_trust_registry()
        registry1 = get_trust_registry()
        registry2 = get_trust_registry()
        assert registry1 is registry2

    def test_reset_trust_registry(self):
        """Test resetting global registry."""
        registry1 = get_trust_registry()
        agent = AgentIdentity.create(name="global_test")
        registry1.register(agent)

        reset_trust_registry()
        registry2 = get_trust_registry()
        assert registry2.count() == 0
