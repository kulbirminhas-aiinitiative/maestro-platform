# ADR: Secure Message Bus Architecture

**Status**: Accepted
**Date**: 2025-12-11
**EPIC**: MD-3117 - Agora Phase 2: Secure Message Bus
**Author**: EPIC Executor v2.1

## Context

The Agora architecture enables decoupled agent communication through an Event Bus (pub/sub). However, in a marketplace where agents can dynamically join and leave, message authenticity is critical. Without cryptographic signing:

1. Any agent could impersonate another agent ("Admin" spoofing)
2. Messages could be tampered in transit
3. No audit trail for non-repudiation
4. Trust-based routing decisions could be compromised

Reference: `AGORA_PHASE2_DETAILED_BACKLOG.md` - AGORA-104

## Decision

We implement a **layered security model** for the Agora message bus:

### 1. Extended AgoraMessage Schema

Add optional `signature` field to `AgoraMessage`:

```python
@dataclass
class AgoraMessage:
    # ... existing fields ...
    signature: Optional[bytes] = None

    def sign(self, identity: AgentIdentity) -> None:
        """Sign message content with agent's private key."""

    def verify(self, identity: AgentIdentity) -> bool:
        """Verify signature against sender's public key."""
```

### 2. SignedMessage Wrapper

Create `SignedMessage` class that enforces signing at construction:

```python
class SignedMessage:
    def __init__(self, message: AgoraMessage, signer: AgentIdentity):
        self.message = message
        self.signature = signer.sign(message.to_signable_bytes())
```

### 3. SecureEventBus

Create `SecureEventBus` that wraps the standard `EventBus` with security enforcement:

- `publish()` automatically signs if identity provided
- `subscribe()` callbacks receive only verified messages
- Unverified messages raise `SecurityError`

### 4. Identity Resolution

Use existing `TrustRegistry` from MD-3104 to lookup public keys by agent ID.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SecureEventBus                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Agent A     │    │ Event Bus   │    │ Agent B     │ │
│  │ (Identity)  │───>│ (Memory)    │───>│ (Verifier)  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│        │                  │                  │          │
│        ▼                  ▼                  ▼          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Sign(msg)   │    │ Route(msg)  │    │ Verify(sig) │ │
│  │ Ed25519     │    │ Topic-based │    │ Reject bad  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Consequences

### Positive
- Non-repudiation: Agents cannot deny sending messages
- Tamper detection: Modified messages are rejected
- Trust enforcement: Only verified agents can communicate
- Audit trail: Signatures provide cryptographic proof

### Negative
- Performance overhead: ~0.1ms per sign/verify operation
- Complexity: Agents must have identity before communication
- Key management: Lost private keys break agent identity

### Mitigations
- Use HMAC-SHA256 fallback when Ed25519 unavailable
- Identity can be generated on-demand for anonymous agents
- Key rotation mechanism planned for future EPICs

## Implementation Files

| File | Purpose |
|------|---------|
| `acl.py` | Extended with signature field |
| `signed_message.py` | SignedMessage wrapper class |
| `secure_event_bus.py` | SecureEventBus implementation |
| `test_md3117_signed_messages.py` | Comprehensive test suite |

## References

- AGORA-104: Implement Message Signing
- MD-3104: Identity & Trust (AgentIdentity implementation)
- FIPA-ACL Specification: Message Authentication
