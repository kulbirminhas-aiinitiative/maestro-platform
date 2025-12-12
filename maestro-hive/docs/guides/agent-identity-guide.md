# Agent Identity & Trust Guide

This guide explains how to use the Agent Identity and Trust system in Maestro Hive.

## Overview

The Identity & Trust system provides Self-Sovereign Identity (SSI) for agents, enabling:
- Cryptographic identity verification
- Non-repudiation of agent actions
- Trust relationship management
- Verifiable credentials

## Quick Start

### Creating an Agent Identity

```python
from maestro_hive.agora.identity import AgentIdentity, TrustRegistry

# Create a new agent identity
identity = AgentIdentity.create(
    name="backend_developer",
    capabilities=["code_generation", "code_review", "testing"]
)

print(f"Agent DID: {identity.did}")
print(f"Public Key: {identity.public_key_hex}")
```

### Signing Messages

```python
# Sign a message
message = "Task completed: implemented login feature"
signature = identity.sign(message.encode())

print(f"Signature: {signature.hex()}")
```

### Verifying Signatures

```python
# Verify a signature
is_valid = identity.verify(message.encode(), signature)
print(f"Signature valid: {is_valid}")
```

## Working with Credentials

### Issuing Credentials

```python
from maestro_hive.agora.identity import AgentCredential, CredentialType

# Issue a capability credential
credential = AgentCredential.create(
    issuer=identity,
    subject_did=other_agent.did,
    credential_type=CredentialType.CAPABILITY,
    claims={"capability": "code_generation", "level": "expert"},
    expires_in_days=365
)

print(f"Credential ID: {credential.credential_id}")
```

### Verifying Credentials

```python
# Verify credential authenticity
is_authentic = credential.verify(issuer_public_key=identity.public_key)
print(f"Credential authentic: {is_authentic}")

# Check if credential is expired
is_valid = credential.is_valid()
print(f"Credential valid: {is_valid}")
```

## Trust Registry

### Registering Agents

```python
# Create a trust registry
registry = TrustRegistry()

# Register an agent
registry.register(identity)

# Look up an agent by DID
agent = registry.get(identity.did)
```

### Managing Trust Levels

```python
from maestro_hive.agora.identity import TrustLevel

# Set trust level
registry.set_trust_level(identity.did, TrustLevel.TRUSTED)

# Get current trust level
level = registry.get_trust_level(identity.did)
print(f"Trust level: {level.value}")

# Record successful interaction (increases trust)
registry.record_interaction(identity.did, success=True)
```

### Trust Decay

Trust levels decay over time without interaction:

```python
# Trust decays automatically based on last interaction
# Configure decay rate in environment:
# TRUST_DECAY_DAYS=30  # Days until trust decays one level
```

## Identity Verification Workflow

### Challenge-Response Authentication

```python
from maestro_hive.agora.identity import IdentityVerifier

verifier = IdentityVerifier(registry)

# Generate a challenge
challenge = verifier.create_challenge(target_did=agent.did)

# Agent signs the challenge
response = agent_identity.sign(challenge.encode())

# Verify the response
is_verified = verifier.verify_challenge(
    target_did=agent.did,
    challenge=challenge,
    response=response
)
print(f"Agent verified: {is_verified}")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SSI_KEY_ALGORITHM` | Key algorithm (ed25519, secp256k1) | `ed25519` |
| `TRUST_DECAY_DAYS` | Days until trust decays | `30` |
| `CREDENTIAL_DEFAULT_EXPIRY_DAYS` | Default credential expiry | `365` |
| `IDENTITY_STORAGE_PATH` | Path to store identities | `/tmp/identities` |

### Programmatic Configuration

```python
from maestro_hive.agora.identity import IdentityConfig

config = IdentityConfig(
    key_algorithm="ed25519",
    trust_decay_days=30,
    default_credential_expiry_days=365
)

identity = AgentIdentity.create(name="agent", config=config)
```

## Best Practices

### Key Management

1. **Never share private keys** - Private keys should never leave the agent's secure storage
2. **Rotate keys periodically** - Generate new key pairs at regular intervals
3. **Backup identities** - Store encrypted backups of agent identities

### Credential Management

1. **Set appropriate expiration** - Credentials should expire based on sensitivity
2. **Implement revocation** - Have a process to revoke compromised credentials
3. **Verify before trust** - Always verify credentials before granting access

### Trust Management

1. **Start with low trust** - New agents should start at `unknown` trust level
2. **Require credentials for elevation** - Trust elevation should require credential verification
3. **Monitor for anomalies** - Track unusual trust changes

## Troubleshooting

### Common Issues

**Signature verification fails**
- Ensure you're using the correct public key
- Check that the message hasn't been modified
- Verify the signature algorithm matches

**Credential expired**
- Issue a new credential with updated expiration
- Check system clock synchronization

**Agent not found in registry**
- Ensure the agent was registered before lookup
- Check for DID format consistency

## API Reference

See the full API documentation at:
- `src/maestro_hive/agora/identity/agent_identity.py`
- `src/maestro_hive/agora/identity/credentials.py`
- `src/maestro_hive/agora/identity/trust_registry.py`
