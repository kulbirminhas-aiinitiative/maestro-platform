# Secure Message Bus User Guide

This guide explains how to use the cryptographically secured message bus in the Agora.

## Overview

The Secure Message Bus ensures all agent-to-agent communication is:
- **Authenticated**: Messages are signed by the sender
- **Verified**: Receivers validate signatures before processing
- **Non-repudiable**: Cryptographic proof of message origin

## Quick Start

### 1. Create Agent Identities

```python
from maestro_hive.agora.identity import AgentIdentity

# Create identities for two agents
agent_a = AgentIdentity.generate(name="CoderAgent")
agent_b = AgentIdentity.generate(name="ReviewerAgent")
```

### 2. Create Secure Event Bus

```python
from maestro_hive.agora import SecureEventBus, TrustRegistry

# Create registry and register agents
registry = TrustRegistry()
registry.register_identity(agent_a)
registry.register_identity(agent_b)

# Create secure bus with registry
bus = SecureEventBus(trust_registry=registry)
```

### 3. Subscribe and Publish

```python
from maestro_hive.agora import AgoraMessage, Performative, SignedMessage

# Agent B subscribes to "code-review" topic
def handle_review_request(msg: SignedMessage):
    print(f"Received verified message from: {msg.message.sender}")
    print(f"Content: {msg.message.content}")

sub_id = bus.subscribe("code-review", handle_review_request)

# Agent A publishes a signed message
message = AgoraMessage(
    sender=agent_a.did,
    performative=Performative.REQUEST,
    content={"task": "review PR #123"}
)

bus.publish("code-review", message, signer=agent_a)
```

### 4. Verify Messages Manually

```python
# Create and sign a message
msg = AgoraMessage(
    sender=agent_a.did,
    performative=Performative.INFORM,
    content={"status": "complete"}
)
msg.sign(agent_a)

# Verify the signature
is_valid = msg.verify(agent_a)
print(f"Signature valid: {is_valid}")  # True

# Tamper detection
msg.content["status"] = "hacked"
is_valid = msg.verify(agent_a)
print(f"Signature valid: {is_valid}")  # False
```

## Security Features

### Tamper Detection

If a message is modified after signing, verification fails:

```python
msg.sign(agent_a)
original_content = msg.content.copy()

# Tamper with the message
msg.content["extra"] = "injected"

# Verification now fails
assert not msg.verify(agent_a)
```

### Spoofing Prevention

Agents cannot impersonate others without their private key:

```python
# Agent C tries to impersonate Agent A
agent_c = AgentIdentity.generate(name="EvilAgent")

# Message claims to be from Agent A
spoofed_msg = AgoraMessage(
    sender=agent_a.did,  # Claims to be A
    performative=Performative.REQUEST,
    content={"task": "steal secrets"}
)

# But signed by C
spoofed_msg.sign(agent_c)

# Verification against A fails
assert not spoofed_msg.verify(agent_a)
```

### Unsigned Message Rejection

The SecureEventBus rejects unsigned messages:

```python
unsigned_msg = AgoraMessage(
    sender=agent_a.did,
    performative=Performative.REQUEST,
    content={"task": "unsigned task"}
)

# This raises SecurityError
try:
    bus.publish("topic", unsigned_msg)  # No signer!
except SecurityError as e:
    print(f"Rejected: {e}")
```

## Best Practices

1. **Always use SecureEventBus** for production agents
2. **Store private keys securely** - never log or expose
3. **Verify sender identity** against TrustRegistry
4. **Rotate keys periodically** (feature in roadmap)
5. **Log verification failures** for security auditing

## Error Handling

```python
from maestro_hive.agora import SecurityError

try:
    bus.publish("topic", message, signer=identity)
except SecurityError as e:
    # Handle security violations
    logger.error(f"Security violation: {e}")
```

## Performance Considerations

- Ed25519 signing: ~0.05ms per operation
- HMAC fallback: ~0.01ms per operation
- Batch signing available for high-throughput scenarios

## Related Documentation

- [Agent Identity & Trust](./agent-identity-guide.md)
- [ADR: Secure Message Bus](../adr/secure-message-bus.md)
- [Event Bus Reference](../api/event-bus.md)
