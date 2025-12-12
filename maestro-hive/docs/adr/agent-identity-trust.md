# ADR: Agent Identity and Trust System

**Status**: Accepted
**Date**: 2025-12-11
**EPIC**: MD-3104 (Agora Phase 2: Identity & Trust)

## Context

The Agora architecture requires agents to establish trust relationships for secure communication. Without a robust identity system, agents cannot:
- Verify the authenticity of messages from other agents
- Establish non-repudiation for agent actions
- Build dynamic trust relationships based on past behavior
- Implement access control for sensitive operations

Self-Sovereign Identity (SSI) principles provide a decentralized approach where agents control their own identities without relying on a central authority.

## Decision

Implement a Self-Sovereign Identity (SSI) system for agents with the following components:

### 1. AgentIdentity Class
- Generate unique Decentralized Identifiers (DIDs) using UUID + cryptographic hashing
- Support Ed25519 key pairs for signing and verification
- Store identity metadata (creation time, capabilities, version)

### 2. AgentCredential System
- Issue verifiable credentials attesting to agent capabilities
- Support credential types: `capability`, `role`, `certification`, `trust_delegation`
- Include credential expiration and revocation support

### 3. Signature System
- Sign messages/artifacts using agent's private key
- Verify signatures using public keys from DID documents
- Support both Ed25519 and HMAC-SHA256 algorithms

### 4. TrustRegistry
- Centralized registry of known agent identities
- Trust levels: `unknown`, `verified`, `trusted`, `highly_trusted`
- Trust decay over time without interaction
- Reputation tracking based on successful interactions

### 5. Identity Verification Workflow
- Challenge-response protocol for agent authentication
- Credential exchange during handshake
- Trust level negotiation for sensitive operations

## Consequences

### Positive
- Agents can verify each other's identity cryptographically
- Non-repudiation: agents cannot deny their actions
- Decentralized trust model reduces single points of failure
- Flexible credential system supports various authorization schemes
- Foundation for secure agent-to-agent communication

### Negative
- Key management adds complexity (rotation, revocation)
- Performance overhead for cryptographic operations
- Trust registry needs eventual synchronization in distributed deployments
- Initial trust bootstrapping requires careful design

## Implementation Notes

### File Structure
```
src/maestro_hive/agora/identity/
├── __init__.py
├── agent_identity.py      # AgentIdentity class, DID generation
├── credentials.py         # AgentCredential, CredentialType
├── signatures.py          # Sign/verify operations
├── trust_registry.py      # TrustRegistry, trust levels
└── verification.py        # Challenge-response protocol
```

### Key Dependencies
- `cryptography` library for Ed25519 key operations
- `hashlib` for SHA-256 hashing
- `uuid` for DID generation
- `datetime` for credential expiration

### Integration Points
- Event Bus (MD-3100): Sign messages before publishing
- Persona Executor: Verify agent identity before task delegation
- Quality Fabric: Credential-based access control for validation

## References

- [W3C DID Specification](https://www.w3.org/TR/did-core/)
- [Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)
- [Agora Phase 2 Backlog](docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md)
