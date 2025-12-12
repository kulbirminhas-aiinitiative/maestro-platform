"""
Tests for Identity Verification module.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-5: Add identity verification workflow for agent communication
"""

import pytest
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from maestro_hive.agora.identity.agent_identity import AgentIdentity
from maestro_hive.agora.identity.trust_registry import TrustRegistry, TrustLevel
from maestro_hive.agora.identity.verification import (
    Challenge,
    HandshakeProtocol,
    IdentityVerifier,
    MutualVerification,
    VerificationResult,
    VerificationStatus,
)


class TestChallenge:
    """Tests for Challenge class."""

    def test_challenge_data(self):
        """Test challenge data generation."""
        challenge = Challenge(
            challenge_id="challenge:123",
            verifier_did="did:agora:verifier",
            target_did="did:agora:target",
            nonce="abc123",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        data = challenge.challenge_data
        assert b"challenge:123" in data
        assert b"abc123" in data
        assert b"did:agora:target" in data

    def test_is_expired_false(self):
        """Test non-expired challenge."""
        challenge = Challenge(
            challenge_id="test",
            verifier_did="verifier",
            target_did="target",
            nonce="nonce",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert challenge.is_expired is False

    def test_is_expired_true(self):
        """Test expired challenge."""
        challenge = Challenge(
            challenge_id="test",
            verifier_did="verifier",
            target_did="target",
            nonce="nonce",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        assert challenge.is_expired is True

    def test_to_dict(self):
        """Test challenge serialization."""
        challenge = Challenge(
            challenge_id="test",
            verifier_did="verifier",
            target_did="target",
            nonce="nonce123",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        data = challenge.to_dict()

        assert data["challenge_id"] == "test"
        assert data["nonce"] == "nonce123"
        assert data["status"] == "pending"


class TestIdentityVerifier:
    """Tests for IdentityVerifier class."""

    @pytest.fixture
    def registry(self):
        """Create a trust registry."""
        return TrustRegistry()

    @pytest.fixture
    def verifier_identity(self):
        """Create verifier identity."""
        return AgentIdentity.create(name="verifier")

    @pytest.fixture
    def target_identity(self):
        """Create target identity."""
        return AgentIdentity.create(name="target")

    @pytest.fixture
    def verifier(self, registry, verifier_identity, target_identity):
        """Create identity verifier with registered agents."""
        registry.register(verifier_identity)
        registry.register(target_identity)
        v = IdentityVerifier(registry)
        v.set_verifier_identity(verifier_identity)
        return v

    def test_create_challenge(self, verifier, target_identity):
        """Test creating a verification challenge."""
        challenge = verifier.create_challenge(target_identity.did)

        assert challenge.challenge_id.startswith("challenge:")
        assert challenge.target_did == target_identity.did
        assert len(challenge.nonce) > 0
        assert challenge.status == VerificationStatus.PENDING

    def test_create_challenge_no_verifier_did(self, registry, target_identity):
        """Test error when verifier DID not set."""
        registry.register(target_identity)
        v = IdentityVerifier(registry)

        with pytest.raises(ValueError, match="Verifier DID not set"):
            v.create_challenge(target_identity.did)

    def test_create_challenge_unregistered_target(self, verifier):
        """Test error for unregistered target."""
        with pytest.raises(ValueError, match="Target agent not registered"):
            verifier.create_challenge("did:agora:unknown")

    def test_verify_response_success(self, verifier, target_identity):
        """Test successful verification."""
        challenge = verifier.create_challenge(target_identity.did)

        # Target signs the challenge
        response = target_identity.sign(challenge.challenge_data)

        result = verifier.verify_response(challenge.challenge_id, response)

        assert result.success is True
        assert result.status == VerificationStatus.SUCCESS
        assert result.target_did == target_identity.did

    def test_verify_response_invalid_signature(self, verifier, target_identity):
        """Test verification with invalid signature."""
        challenge = verifier.create_challenge(target_identity.did)

        # Use wrong signature
        fake_response = b"invalid_signature"

        result = verifier.verify_response(challenge.challenge_id, fake_response)

        assert result.success is False
        assert result.status == VerificationStatus.FAILED

    def test_verify_response_wrong_signer(self, verifier, target_identity, verifier_identity):
        """Test verification with wrong signer."""
        challenge = verifier.create_challenge(target_identity.did)

        # Verifier signs instead of target
        response = verifier_identity.sign(challenge.challenge_data)

        result = verifier.verify_response(challenge.challenge_id, response)

        assert result.success is False

    def test_verify_response_unknown_challenge(self, verifier):
        """Test verification with unknown challenge."""
        result = verifier.verify_response("unknown", b"response")

        assert result.success is False
        assert "not found" in result.message

    def test_verify_response_expired(self, registry, target_identity):
        """Test verification with expired challenge."""
        registry.register(target_identity)
        v = IdentityVerifier(registry, challenge_ttl_seconds=0)
        verifier_id = AgentIdentity.create(name="verifier")
        registry.register(verifier_id)
        v.set_verifier_identity(verifier_id)

        challenge = v.create_challenge(target_identity.did)
        # Challenge immediately expired due to TTL=0

        response = target_identity.sign(challenge.challenge_data)
        result = v.verify_response(challenge.challenge_id, response)

        assert result.success is False
        assert result.status == VerificationStatus.EXPIRED

    def test_challenge_cleanup(self, verifier, target_identity):
        """Test that expired challenges are cleaned up."""
        # Create multiple challenges
        for _ in range(5):
            verifier.create_challenge(target_identity.did)

        assert verifier.get_pending_count() == 5

    def test_max_pending_challenges(self, registry, target_identity):
        """Test maximum pending challenges limit."""
        registry.register(target_identity)
        verifier_id = AgentIdentity.create(name="verifier")
        registry.register(verifier_id)

        v = IdentityVerifier(registry, max_pending_challenges=3)
        v.set_verifier_identity(verifier_id)

        # Create more than max
        for _ in range(5):
            v.create_challenge(target_identity.did)

        assert v.get_pending_count() == 3


class TestVerificationResult:
    """Tests for VerificationResult class."""

    def test_to_dict(self):
        """Test result serialization."""
        result = VerificationResult(
            success=True,
            challenge_id="test",
            target_did="did:agora:target",
            verifier_did="did:agora:verifier",
            status=VerificationStatus.SUCCESS,
            message="Verified",
            trust_level="trusted",
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["status"] == "success"
        assert data["trust_level"] == "trusted"


class TestMutualVerification:
    """Tests for MutualVerification class."""

    @pytest.fixture
    def registry(self):
        """Create registry with agents."""
        r = TrustRegistry()
        return r

    def test_initiate_mutual_verification(self, registry):
        """Test initiating mutual verification."""
        agent_a = AgentIdentity.create(name="agent_a")
        agent_b = AgentIdentity.create(name="agent_b")
        registry.register(agent_a)
        registry.register(agent_b)

        mutual = MutualVerification(registry)
        outgoing, incoming = mutual.initiate(agent_a, agent_b.did)

        assert outgoing.target_did == agent_b.did
        assert incoming.target_did == agent_a.did


class TestHandshakeProtocol:
    """Tests for HandshakeProtocol class."""

    @pytest.fixture
    def registry(self):
        """Create registry."""
        return TrustRegistry()

    def test_create_handshake_request(self, registry):
        """Test creating handshake request."""
        initiator = AgentIdentity.create(
            name="initiator",
            capabilities=["coding"],
        )
        target = AgentIdentity.create(name="target")
        registry.register(initiator)
        registry.register(target)

        protocol = HandshakeProtocol(registry)
        request = protocol.create_handshake_request(
            initiator,
            target.did,
            requested_capabilities=["testing"],
        )

        assert request["type"] == "handshake_request"
        assert request["initiator_did"] == initiator.did
        assert request["target_did"] == target.did
        assert request["requested_capabilities"] == ["testing"]
        assert "outgoing_challenge" in request


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert VerificationStatus.PENDING.value == "pending"
        assert VerificationStatus.SUCCESS.value == "success"
        assert VerificationStatus.FAILED.value == "failed"
        assert VerificationStatus.EXPIRED.value == "expired"


class TestIntegration:
    """Integration tests for full verification flow."""

    def test_full_verification_flow(self):
        """Test complete verification flow."""
        # Setup
        registry = TrustRegistry()
        agent_a = AgentIdentity.create(name="agent_a")
        agent_b = AgentIdentity.create(name="agent_b")
        registry.register(agent_a, initial_trust=TrustLevel.VERIFIED)
        registry.register(agent_b, initial_trust=TrustLevel.UNKNOWN)

        # Agent A wants to verify Agent B
        verifier = IdentityVerifier(registry)
        verifier.set_verifier_identity(agent_a)

        # Create challenge
        challenge = verifier.create_challenge(agent_b.did)

        # Agent B signs the challenge
        response = agent_b.sign(challenge.challenge_data)

        # Agent A verifies
        result = verifier.verify_response(challenge.challenge_id, response)

        assert result.success is True
        assert result.target_did == agent_b.did

        # Check interaction was recorded
        record = registry.get(agent_b.did)
        assert record.successful_interactions == 1
