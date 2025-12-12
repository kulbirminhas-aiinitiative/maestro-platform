"""
Tests for AgentCredential module.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-2: Create AgentCredential system for verifiable credentials
"""

import json
import pytest
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from maestro_hive.agora.identity.agent_identity import AgentIdentity
from maestro_hive.agora.identity.credentials import (
    AgentCredential,
    CredentialClaim,
    CredentialStatus,
    CredentialStore,
    CredentialType,
)


class TestCredentialType:
    """Tests for CredentialType enum."""

    def test_credential_types(self):
        """Test all credential types exist."""
        assert CredentialType.CAPABILITY.value == "capability"
        assert CredentialType.ROLE.value == "role"
        assert CredentialType.CERTIFICATION.value == "certification"
        assert CredentialType.TRUST_DELEGATION.value == "trust_delegation"


class TestCredentialClaim:
    """Tests for CredentialClaim."""

    def test_claim_creation(self):
        """Test creating a claim."""
        claim = CredentialClaim(
            claim_type="capability",
            value="code_generation",
            evidence="http://example.com/proof",
        )
        assert claim.claim_type == "capability"
        assert claim.value == "code_generation"
        assert claim.evidence == "http://example.com/proof"

    def test_claim_to_dict(self):
        """Test claim serialization."""
        claim = CredentialClaim(
            claim_type="role",
            value="admin",
        )
        data = claim.to_dict()
        assert data["type"] == "role"
        assert data["value"] == "admin"
        assert "evidence" not in data


class TestAgentCredential:
    """Tests for AgentCredential class."""

    @pytest.fixture
    def issuer(self):
        """Create an issuer identity."""
        return AgentIdentity.create(
            name="issuer",
            capabilities=["credential_issuance"],
        )

    @pytest.fixture
    def subject(self):
        """Create a subject identity."""
        return AgentIdentity.create(
            name="subject",
            capabilities=["code_generation"],
        )

    def test_create_credential(self, issuer, subject):
        """Test creating a credential."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "code_generation", "level": "expert"},
        )

        assert credential.credential_id.startswith("vc:")
        assert credential.issuer_did == issuer.did
        assert credential.subject_did == subject.did
        assert credential.credential_type == CredentialType.CAPABILITY
        assert credential.signature is not None
        assert credential.status == CredentialStatus.ACTIVE

    def test_credential_with_expiry(self, issuer, subject):
        """Test credential with expiration."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.ROLE,
            claims={"role": "developer"},
            expires_in_days=30,
        )

        assert credential.expires_at is not None
        expected_expiry = credential.issued_at + timedelta(days=30)
        assert abs((credential.expires_at - expected_expiry).total_seconds()) < 1

    def test_verify_credential(self, issuer, subject):
        """Test credential signature verification."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        is_valid = credential.verify(issuer.public_key)
        assert is_valid is True

    def test_verify_invalid_credential(self, issuer, subject):
        """Test detecting invalid credential signature."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        # Tamper with the credential
        credential.subject_did = "did:agora:fake"

        is_valid = credential.verify(issuer.public_key)
        assert is_valid is False

    def test_is_valid_active(self, issuer, subject):
        """Test validity check for active credential."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        assert credential.is_valid() is True

    def test_is_valid_revoked(self, issuer, subject):
        """Test validity check for revoked credential."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        credential.revoke()

        assert credential.is_valid() is False
        assert credential.status == CredentialStatus.REVOKED

    def test_suspend_and_reinstate(self, issuer, subject):
        """Test suspending and reinstating credential."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.ROLE,
            claims={"role": "tester"},
        )

        credential.suspend()
        assert credential.status == CredentialStatus.SUSPENDED
        assert credential.is_valid() is False

        credential.reinstate()
        assert credential.status == CredentialStatus.ACTIVE
        assert credential.is_valid() is True

    def test_get_claim(self, issuer, subject):
        """Test getting specific claim value."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={
                "capability": "code_generation",
                "level": "expert",
            },
        )

        assert credential.get_claim("capability") == "code_generation"
        assert credential.get_claim("level") == "expert"
        assert credential.get_claim("nonexistent") is None

    def test_has_claim(self, issuer, subject):
        """Test checking for claim existence."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        assert credential.has_claim("capability") is True
        assert credential.has_claim("capability", "testing") is True
        assert credential.has_claim("capability", "other") is False
        assert credential.has_claim("nonexistent") is False

    def test_to_dict(self, issuer, subject):
        """Test credential serialization."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        data = credential.to_dict()
        assert "@context" in data
        assert data["issuer"] == issuer.did
        assert data["credentialSubject"]["id"] == subject.did
        assert "proof" in data

    def test_to_json(self, issuer, subject):
        """Test JSON serialization."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.ROLE,
            claims={"role": "admin"},
        )

        json_str = credential.to_json()
        data = json.loads(json_str)
        assert data["issuer"] == issuer.did

    def test_from_dict(self, issuer, subject):
        """Test credential deserialization."""
        original = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        data = original.to_dict()
        restored = AgentCredential.from_dict(data)

        assert restored.credential_id == original.credential_id
        assert restored.issuer_did == original.issuer_did
        assert restored.subject_did == original.subject_did
        assert restored.credential_type == original.credential_type

    def test_repr(self, issuer, subject):
        """Test string representation."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        repr_str = repr(credential)
        assert "AgentCredential" in repr_str
        assert "capability" in repr_str


class TestCredentialStore:
    """Tests for CredentialStore."""

    @pytest.fixture
    def store(self):
        """Create a credential store."""
        return CredentialStore()

    @pytest.fixture
    def issuer(self):
        """Create an issuer."""
        return AgentIdentity.create(name="issuer")

    @pytest.fixture
    def subject(self):
        """Create a subject."""
        return AgentIdentity.create(name="subject")

    def test_add_and_get(self, store, issuer, subject):
        """Test adding and retrieving credentials."""
        credential = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )

        store.add(credential)
        retrieved = store.get(credential.credential_id)

        assert retrieved is not None
        assert retrieved.credential_id == credential.credential_id

    def test_get_nonexistent(self, store):
        """Test getting nonexistent credential."""
        assert store.get("nonexistent") is None

    def test_get_by_subject(self, store, issuer, subject):
        """Test getting credentials by subject."""
        cred1 = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        cred2 = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.ROLE,
            claims={"role": "developer"},
        )

        store.add(cred1)
        store.add(cred2)

        credentials = store.get_by_subject(subject.did)
        assert len(credentials) == 2

    def test_get_by_subject_with_type_filter(self, store, issuer, subject):
        """Test filtering by credential type."""
        cred1 = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        cred2 = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.ROLE,
            claims={"role": "developer"},
        )

        store.add(cred1)
        store.add(cred2)

        cap_creds = store.get_by_subject(
            subject.did,
            credential_type=CredentialType.CAPABILITY,
        )
        assert len(cap_creds) == 1
        assert cap_creds[0].credential_type == CredentialType.CAPABILITY

    def test_get_by_subject_only_valid(self, store, issuer, subject):
        """Test filtering invalid credentials."""
        cred = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        store.add(cred)
        cred.revoke()

        valid_creds = store.get_by_subject(subject.did, only_valid=True)
        assert len(valid_creds) == 0

        all_creds = store.get_by_subject(subject.did, only_valid=False)
        assert len(all_creds) == 1

    def test_get_by_issuer(self, store, issuer, subject):
        """Test getting credentials by issuer."""
        cred = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        store.add(cred)

        credentials = store.get_by_issuer(issuer.did)
        assert len(credentials) == 1
        assert credentials[0].issuer_did == issuer.did

    def test_revoke_credential(self, store, issuer, subject):
        """Test revoking credential through store."""
        cred = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "testing"},
        )
        store.add(cred)

        result = store.revoke(cred.credential_id)
        assert result is True

        retrieved = store.get(cred.credential_id)
        assert retrieved.status == CredentialStatus.REVOKED

    def test_has_capability(self, store, issuer, subject):
        """Test checking for capability."""
        cred = AgentCredential.create(
            issuer=issuer,
            subject_did=subject.did,
            credential_type=CredentialType.CAPABILITY,
            claims={"capability": "code_generation"},
        )
        store.add(cred)

        assert store.has_capability(subject.did, "code_generation") is True
        assert store.has_capability(subject.did, "other_capability") is False

    def test_count_and_clear(self, store, issuer, subject):
        """Test count and clear operations."""
        for i in range(3):
            cred = AgentCredential.create(
                issuer=issuer,
                subject_did=subject.did,
                credential_type=CredentialType.CAPABILITY,
                claims={"capability": f"cap_{i}"},
            )
            store.add(cred)

        assert store.count() == 3

        store.clear()
        assert store.count() == 0
