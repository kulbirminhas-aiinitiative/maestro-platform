"""
Tests for AgentIdentity module.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-1: Implement AgentIdentity class with DID generation
AC-3: Implement signature generation and verification
"""

import json
import pytest
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from maestro_hive.agora.identity.agent_identity import (
    AgentIdentity,
    DIDDocument,
    IdentityConfig,
    KeyAlgorithm,
)


class TestIdentityConfig:
    """Tests for IdentityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = IdentityConfig()
        assert config.key_algorithm == "ed25519"
        assert config.trust_decay_days == 30
        assert config.default_credential_expiry_days == 365

    def test_custom_config(self):
        """Test custom configuration."""
        config = IdentityConfig(
            key_algorithm="hmac-sha256",
            trust_decay_days=60,
            default_credential_expiry_days=180,
        )
        assert config.key_algorithm == "hmac-sha256"
        assert config.trust_decay_days == 60
        assert config.default_credential_expiry_days == 180


class TestDIDDocument:
    """Tests for DIDDocument."""

    def test_to_dict(self):
        """Test DID Document serialization."""
        doc = DIDDocument(
            did="did:agora:test123",
            public_key_hex="abcd1234",
            key_algorithm="ed25519",
            created_at="2025-01-01T00:00:00+00:00",
            capabilities=["code_generation"],
        )
        data = doc.to_dict()

        assert data["id"] == "did:agora:test123"
        assert data["@context"] == "https://www.w3.org/ns/did/v1"
        assert len(data["verificationMethod"]) == 1
        assert data["verificationMethod"][0]["publicKeyHex"] == "abcd1234"
        assert data["capabilities"] == ["code_generation"]

    def test_to_json(self):
        """Test DID Document JSON serialization."""
        doc = DIDDocument(
            did="did:agora:test123",
            public_key_hex="abcd1234",
            key_algorithm="ed25519",
            created_at="2025-01-01T00:00:00+00:00",
        )
        json_str = doc.to_json()
        data = json.loads(json_str)
        assert data["id"] == "did:agora:test123"

    def test_from_dict(self):
        """Test DID Document deserialization."""
        data = {
            "id": "did:agora:test456",
            "verificationMethod": [
                {
                    "id": "did:agora:test456#key-1",
                    "type": "ed25519VerificationKey2020",
                    "publicKeyHex": "xyz789",
                }
            ],
            "created": "2025-01-01T00:00:00+00:00",
            "capabilities": ["testing"],
        }
        doc = DIDDocument.from_dict(data)
        assert doc.did == "did:agora:test456"
        assert doc.public_key_hex == "xyz789"
        assert doc.capabilities == ["testing"]


class TestAgentIdentity:
    """Tests for AgentIdentity class."""

    def test_create_identity(self):
        """Test creating a new identity."""
        identity = AgentIdentity.create(
            name="test_agent",
            capabilities=["code_generation", "testing"],
        )

        assert identity.name == "test_agent"
        assert identity.did.startswith("did:agora:")
        assert len(identity.public_key_hex) > 0
        assert identity.capabilities == ["code_generation", "testing"]
        assert identity.has_private_key is True

    def test_did_uniqueness(self):
        """Test that DIDs are unique."""
        identity1 = AgentIdentity.create(name="agent1")
        identity2 = AgentIdentity.create(name="agent2")
        assert identity1.did != identity2.did

    def test_sign_and_verify(self):
        """Test signature generation and verification."""
        identity = AgentIdentity.create(name="signer")
        message = b"Hello, World!"

        signature = identity.sign(message)
        assert len(signature) > 0

        is_valid = identity.verify(message, signature)
        assert is_valid is True

    def test_verify_invalid_signature(self):
        """Test that invalid signatures are rejected."""
        identity = AgentIdentity.create(name="signer")
        message = b"Hello, World!"
        fake_signature = b"fake_signature_bytes_here"

        is_valid = identity.verify(message, fake_signature)
        assert is_valid is False

    def test_verify_tampered_message(self):
        """Test that tampered messages are detected."""
        identity = AgentIdentity.create(name="signer")
        original = b"Original message"
        tampered = b"Tampered message"

        signature = identity.sign(original)
        is_valid = identity.verify(tampered, signature)
        assert is_valid is False

    def test_from_public_key(self):
        """Test creating verification-only identity."""
        # Create original identity
        original = AgentIdentity.create(name="original")
        message = b"Test message"
        signature = original.sign(message)

        # Create verification-only identity
        verifier = AgentIdentity.from_public_key(
            did=original.did,
            name="verifier",
            public_key_hex=original.public_key_hex,
        )

        assert verifier.has_private_key is False
        is_valid = verifier.verify(message, signature)
        assert is_valid is True

    def test_cannot_sign_without_private_key(self):
        """Test that signing fails without private key."""
        verifier = AgentIdentity.from_public_key(
            did="did:agora:test",
            name="verifier",
            public_key_hex="a" * 64,
        )

        with pytest.raises(ValueError, match="Cannot sign without private key"):
            verifier.sign(b"message")

    def test_get_did_document(self):
        """Test getting DID Document from identity."""
        identity = AgentIdentity.create(
            name="doc_test",
            capabilities=["cap1", "cap2"],
        )
        doc = identity.get_did_document()

        assert doc.did == identity.did
        assert doc.public_key_hex == identity.public_key_hex
        assert doc.capabilities == identity.capabilities

    def test_to_dict(self):
        """Test serialization to dictionary."""
        identity = AgentIdentity.create(
            name="serial_test",
            capabilities=["cap1"],
            metadata={"key": "value"},
        )
        data = identity.to_dict()

        assert data["did"] == identity.did
        assert data["name"] == "serial_test"
        assert data["capabilities"] == ["cap1"]
        assert data["metadata"] == {"key": "value"}
        assert "private_key_hex" not in data

    def test_to_dict_with_private(self):
        """Test serialization including private key."""
        identity = AgentIdentity.create(name="private_test")
        data = identity.to_dict(include_private=True)

        assert "private_key_hex" in data
        assert len(data["private_key_hex"]) > 0

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        original = AgentIdentity.create(
            name="from_dict_test",
            capabilities=["cap1"],
        )
        data = original.to_dict(include_private=True)
        restored = AgentIdentity.from_dict(data)

        assert restored.did == original.did
        assert restored.name == original.name
        assert restored.public_key_hex == original.public_key_hex
        assert restored.capabilities == original.capabilities

        # Verify signing works after restoration
        message = b"Test message"
        signature = restored.sign(message)
        assert original.verify(message, signature)

    def test_equality(self):
        """Test identity equality based on DID."""
        identity1 = AgentIdentity.create(name="eq_test")
        identity2 = AgentIdentity.from_dict(identity1.to_dict())

        assert identity1 == identity2
        assert hash(identity1) == hash(identity2)

    def test_repr(self):
        """Test string representation."""
        identity = AgentIdentity.create(name="repr_test")
        repr_str = repr(identity)

        assert "AgentIdentity" in repr_str
        assert identity.did in repr_str
        assert "repr_test" in repr_str

    def test_created_at_timestamp(self):
        """Test that created_at is set correctly."""
        before = datetime.now(timezone.utc)
        identity = AgentIdentity.create(name="time_test")
        after = datetime.now(timezone.utc)

        assert before <= identity.created_at <= after

    def test_metadata_storage(self):
        """Test metadata storage."""
        identity = AgentIdentity.create(
            name="meta_test",
            metadata={
                "version": "1.0",
                "environment": "test",
            },
        )

        assert identity.metadata["version"] == "1.0"
        assert identity.metadata["environment"] == "test"


class TestKeyAlgorithm:
    """Tests for KeyAlgorithm enum."""

    def test_algorithm_values(self):
        """Test algorithm enum values."""
        assert KeyAlgorithm.ED25519.value == "ed25519"
        assert KeyAlgorithm.HMAC_SHA256.value == "hmac-sha256"


class TestCrossAgentVerification:
    """Tests for cross-agent signature verification."""

    def test_agent_a_signs_agent_b_verifies(self):
        """Test that one agent can verify another's signature."""
        agent_a = AgentIdentity.create(name="agent_a")
        agent_b = AgentIdentity.create(name="agent_b")

        message = b"Message from Agent A"
        signature = agent_a.sign(message)

        # Agent B creates verification identity from A's public key
        verifier = AgentIdentity.from_public_key(
            did=agent_a.did,
            name="agent_a_verifier",
            public_key_hex=agent_a.public_key_hex,
        )

        assert verifier.verify(message, signature) is True
        assert agent_b.verify(message, signature) is False
