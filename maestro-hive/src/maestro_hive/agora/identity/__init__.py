"""
Agent Identity and Trust Module

Provides Self-Sovereign Identity (SSI) for agents in the Agora architecture.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)

Components:
- AgentIdentity: DID-based identity with cryptographic keys
- AgentCredential: Verifiable credentials for capabilities
- TrustRegistry: Managing agent trust relationships
- IdentityVerifier: Challenge-response authentication

Example:
    >>> from maestro_hive.agora.identity import (
    ...     AgentIdentity,
    ...     TrustRegistry,
    ...     TrustLevel,
    ... )
    >>>
    >>> # Create an identity
    >>> identity = AgentIdentity.create(
    ...     name="backend_developer",
    ...     capabilities=["code_generation", "testing"],
    ... )
    >>>
    >>> # Register in trust registry
    >>> registry = TrustRegistry()
    >>> registry.register(identity)
    >>> registry.set_trust_level(identity.did, TrustLevel.TRUSTED)
"""

from .agent_identity import (
    AgentIdentity,
    DIDDocument,
    IdentityConfig,
    KeyAlgorithm,
)
from .credentials import (
    AgentCredential,
    CredentialClaim,
    CredentialStatus,
    CredentialStore,
    CredentialType,
)
from .trust_registry import (
    TrustLevel,
    TrustRecord,
    TrustRegistry,
    get_trust_registry,
    reset_trust_registry,
)
from .verification import (
    Challenge,
    HandshakeProtocol,
    IdentityVerifier,
    MutualVerification,
    VerificationResult,
    VerificationStatus,
)

__all__ = [
    # Agent Identity
    "AgentIdentity",
    "DIDDocument",
    "IdentityConfig",
    "KeyAlgorithm",
    # Credentials
    "AgentCredential",
    "CredentialClaim",
    "CredentialStatus",
    "CredentialStore",
    "CredentialType",
    # Trust Registry
    "TrustLevel",
    "TrustRecord",
    "TrustRegistry",
    "get_trust_registry",
    "reset_trust_registry",
    # Verification
    "Challenge",
    "HandshakeProtocol",
    "IdentityVerifier",
    "MutualVerification",
    "VerificationResult",
    "VerificationStatus",
]
