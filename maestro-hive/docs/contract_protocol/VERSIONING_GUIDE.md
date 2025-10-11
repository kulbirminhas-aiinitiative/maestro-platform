# Universal Contract Protocol - Versioning and Compatibility Guide

**Document Type:** Strategic Enhancement (Phase 2)
**Version:** 1.0.0
**Last Updated:** 2025-10-11
**Status:** Phase 2 - Production Feature
**Priority:** HIGH (needed for production deployments)
**Author:** Claude (Sonnet 4.5)

---

## Executive Summary

This guide provides comprehensive guidance on versioning contracts, managing schema evolution, and ensuring backward/forward compatibility in the Universal Contract Protocol.

**Key Topics:**
- Semantic versioning for contracts and schemas
- Compatibility modes (backward, forward, full, transitive)
- Breaking vs. non-breaking changes
- Migration strategies and rollback procedures
- Version negotiation protocols
- Cache invalidation strategies

**Why This Matters:**
- Enables safe contract evolution without breaking existing systems
- Supports gradual rollout of protocol upgrades
- Facilitates multi-team collaboration with different protocol versions
- Enables A/B testing and canary deployments
- Provides clear deprecation and migration paths

---

## Table of Contents

1. [Version Number Format](#version-number-format)
2. [Schema Version vs. Contract Version](#schema-version-vs-contract-version)
3. [Compatibility Modes](#compatibility-modes)
4. [Breaking vs. Non-Breaking Changes](#breaking-vs-non-breaking-changes)
5. [Version Negotiation Protocol](#version-negotiation-protocol)
6. [Migration Strategies](#migration-strategies)
7. [Rollback Procedures](#rollback-procedures)
8. [Deprecation Policy](#deprecation-policy)
9. [Examples and Patterns](#examples-and-patterns)
10. [Best Practices](#best-practices)

---

## Version Number Format

### Semantic Versioning 2.0.0

The Universal Contract Protocol uses **Semantic Versioning 2.0.0** for both schema and contract versions.

**Format:** `MAJOR.MINOR.PATCH`

```python
schema_version = "1.2.3"
#                 │ │ └── PATCH: Bug fixes, clarifications (backward compatible)
#                 │ └──── MINOR: New features, additive changes (backward compatible)
#                 └────── MAJOR: Breaking changes (not backward compatible)
```

### Version Components

| Component | When to Increment | Example Change | Compatibility |
|-----------|------------------|----------------|---------------|
| **MAJOR** | Breaking changes | Remove required field | ❌ Breaking |
| **MAJOR** | Change field type | `string` → `number` | ❌ Breaking |
| **MAJOR** | Remove enum value | Remove `ContractLifecycle.DRAFT` | ❌ Breaking |
| **MAJOR** | Rename field | `contract_id` → `id` | ❌ Breaking |
| **MINOR** | Add optional field | Add `tags: List[str]` | ✅ Compatible |
| **MINOR** | Add enum value | Add `ContractLifecycle.SUSPENDED` | ✅ Compatible |
| **MINOR** | Add new contract type | Add `DEPLOYMENT` type | ✅ Compatible |
| **MINOR** | Add new validator | Add `GraphQLValidator` | ✅ Compatible |
| **PATCH** | Fix documentation | Clarify field description | ✅ Compatible |
| **PATCH** | Fix typo | `occured` → `occurred` | ✅ Compatible |
| **PATCH** | Add examples | Add code samples | ✅ Compatible |

### Version Comparison

```python
from typing import Tuple

class Version:
    """Semantic version implementation"""

    def __init__(self, version_string: str):
        self.major, self.minor, self.patch = self.parse(version_string)

    @staticmethod
    def parse(version_string: str) -> Tuple[int, int, int]:
        """Parse version string into components"""
        parts = version_string.split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_string}")

        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def __eq__(self, other: 'Version') -> bool:
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch)

    def __lt__(self, other: 'Version') -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __gt__(self, other: 'Version') -> bool:
        return not (self < other or self == other)

    def __le__(self, other: 'Version') -> bool:
        return self < other or self == other

    def __ge__(self, other: 'Version') -> bool:
        return self > other or self == other

    def is_compatible_with(self, other: 'Version') -> bool:
        """Check if versions are compatible (same major version)"""
        return self.major == other.major

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

# Usage
v1 = Version("1.2.3")
v2 = Version("1.3.0")
v3 = Version("2.0.0")

assert v1 < v2  # True
assert v1.is_compatible_with(v2)  # True (same major version)
assert not v1.is_compatible_with(v3)  # False (different major version)
```

---

## Schema Version vs. Contract Version

The protocol distinguishes between **schema version** (protocol evolution) and **contract version** (contract amendments).

### Schema Version

**Purpose:** Tracks the version of the Universal Contract Protocol specification itself.

**Scope:** Global (applies to all contracts)

**Changes:** Protocol enhancements, new features, data model changes

**Example:**
```python
@dataclass
class UniversalContract:
    schema_version: str = "1.1.0"  # Protocol version
    # ... other fields
```

**When to Change:**
- Protocol specification is updated
- New contract types added
- New validators introduced
- Data model fields added/changed
- API methods added/changed

### Contract Version

**Purpose:** Tracks amendments to a specific contract instance.

**Scope:** Per-contract (each contract has its own version)

**Changes:** Contract renegotiations, clarifications, amendments

**Example:**
```python
@dataclass
class UniversalContract:
    contract_version: int = 1  # Contract amendment number
    # ... other fields
```

**When to Increment:**
- Contract is renegotiated
- Acceptance criteria are amended
- Thresholds are adjusted
- New agents added as consumers
- Clarifications added to specification

### Combined Example

```python
# Original contract (schema v1.0.0, contract v1)
original_contract = UniversalContract(
    contract_id="API_AUTH_001",
    schema_version="1.0.0",
    contract_version=1,
    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="response_time",
            threshold=200  # Original threshold
        )
    ]
)

# Amended contract (same schema, contract v2)
amended_contract = UniversalContract(
    contract_id="API_AUTH_001",
    schema_version="1.0.0",  # Protocol version unchanged
    contract_version=2,  # Contract amended
    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="response_time",
            threshold=500  # Renegotiated threshold
        )
    ]
)

# Protocol upgraded (schema v1.1.0, new contract v1)
upgraded_contract = UniversalContract(
    contract_id="API_AUTH_002",
    schema_version="1.1.0",  # Protocol upgraded
    contract_version=1,  # New contract
    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="response_time",
            threshold=500,
            # New field in schema v1.1.0
            retry_policy={"max_retries": 3, "backoff": "exponential"}
        )
    ]
)
```

---

## Compatibility Modes

The protocol supports multiple compatibility modes for version checking.

### Compatibility Mode Enum

```python
from enum import Enum

class CompatibilityMode(Enum):
    """Version compatibility checking modes"""

    # Non-transitive (check only adjacent versions)
    BACKWARD = "backward"           # New code reads old data
    FORWARD = "forward"            # Old code reads new data
    FULL = "full"                  # Bidirectional compatibility
    BREAKING = "breaking"          # No compatibility required

    # Transitive (check entire version history)
    BACKWARD_TRANSITIVE = "backward_transitive"   # New code reads all old data
    FORWARD_TRANSITIVE = "forward_transitive"    # All old code reads new data
    FULL_TRANSITIVE = "full_transitive"          # All versions compatible
```

### Compatibility Definitions

#### 1. BACKWARD Compatibility

**Definition:** New consumers can read contracts from old producers.

**Use Case:** Rolling upgrades where consumers are upgraded first.

**Example:**
```python
# Old producer creates contract (v1.0.0)
old_contract = UniversalContract(
    schema_version="1.0.0",
    name="Login API"
)

# New consumer reads contract (v1.1.0)
# New consumer must understand v1.0.0 contracts
if new_consumer_version.is_compatible_with(old_contract.schema_version):
    process_contract(old_contract)
```

**Rules:**
- ✅ Add optional fields
- ✅ Add new enum values (with defaults)
- ✅ Widen validation ranges
- ❌ Remove fields
- ❌ Change required fields to different types
- ❌ Narrow validation ranges

#### 2. FORWARD Compatibility

**Definition:** Old consumers can read contracts from new producers.

**Use Case:** Rolling upgrades where producers are upgraded first.

**Example:**
```python
# New producer creates contract (v1.1.0)
new_contract = UniversalContract(
    schema_version="1.1.0",
    name="Login API",
    retry_policy={"max_retries": 3}  # New optional field
)

# Old consumer reads contract (v1.0.0)
# Old consumer ignores unknown fields
contract_dict = {k: v for k, v in new_contract.to_dict().items()
                 if k in OLD_SCHEMA_FIELDS}
process_contract(from_dict(contract_dict))
```

**Rules:**
- ✅ Add optional fields (old code ignores them)
- ✅ Add new enum values (old code treats as unknown)
- ❌ Remove fields (old code expects them)
- ❌ Change field types
- ❌ Add required fields

#### 3. FULL Compatibility

**Definition:** Contracts can be exchanged in both directions.

**Use Case:** Mixed environments with multiple versions.

**Requirements:**
- Must satisfy BACKWARD compatibility
- Must satisfy FORWARD compatibility

**Example:**
```python
# Version 1.0.0 → 1.1.0 changes
# Added optional field: retry_policy

# Backward: v1.1.0 consumer reads v1.0.0 contract ✅
# Forward: v1.0.0 consumer reads v1.1.0 contract ✅
# (ignores retry_policy)

# This is FULL compatible
```

#### 4. BACKWARD_TRANSITIVE Compatibility

**Definition:** New consumers can read contracts from ALL previous versions.

**Use Case:** Long-lived systems with archived contracts.

**Example:**
```python
# Version history: 1.0.0 → 1.1.0 → 1.2.0

# v1.2.0 consumer must read:
- v1.0.0 contracts ✅
- v1.1.0 contracts ✅
- v1.2.0 contracts ✅

# Check transitive compatibility
def is_backward_transitive_compatible(
    consumer_version: Version,
    contract_versions: List[Version]
) -> bool:
    """Check if consumer can read all contract versions"""
    return all(
        consumer_version.major == v.major and consumer_version >= v
        for v in contract_versions
    )
```

#### 5. FORWARD_TRANSITIVE Compatibility

**Definition:** All old consumers can read contracts from new producers.

**Use Case:** Rare - requires extreme caution with schema changes.

**Example:**
```python
# Version history: 1.0.0 → 1.1.0 → 1.2.0

# v1.2.0 contract must be readable by:
- v1.0.0 consumers ✅
- v1.1.0 consumers ✅
- v1.2.0 consumers ✅

# Very restrictive - only optional fields can be added
```

#### 6. FULL_TRANSITIVE Compatibility

**Definition:** All versions can exchange contracts in both directions.

**Use Case:** Critical systems requiring maximum compatibility.

**Example:**
```python
# Any version can read any other version within the same major version
# Extremely restrictive - essentially forbids changes except:
- Documentation updates
- Adding optional fields
- Bug fixes that don't change data structure
```

#### 7. BREAKING Compatibility

**Definition:** No compatibility required.

**Use Case:** Major version upgrades, migration windows.

**Example:**
```python
# v1.x → v2.x: Breaking changes allowed
# Requires coordinated upgrade or migration period
```

### Compatibility Checker Implementation

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CompatibilityResult:
    """Result of compatibility check"""
    compatible: bool
    mode: CompatibilityMode
    consumer_version: Version
    producer_version: Version
    violations: List[str]
    warnings: List[str]

class CompatibilityChecker:
    """Check version compatibility between contracts"""

    @staticmethod
    def check_compatibility(
        consumer_version: Version,
        producer_version: Version,
        mode: CompatibilityMode
    ) -> CompatibilityResult:
        """Check if versions are compatible under given mode"""

        violations = []
        warnings = []

        if mode == CompatibilityMode.BREAKING:
            # No compatibility required
            return CompatibilityResult(
                compatible=True,
                mode=mode,
                consumer_version=consumer_version,
                producer_version=producer_version,
                violations=[],
                warnings=[]
            )

        # Check major version match (required for all non-breaking modes)
        if consumer_version.major != producer_version.major:
            violations.append(
                f"Major version mismatch: consumer={consumer_version.major}, "
                f"producer={producer_version.major}"
            )

        # BACKWARD: Consumer version >= Producer version
        if mode in [CompatibilityMode.BACKWARD, CompatibilityMode.BACKWARD_TRANSITIVE]:
            if consumer_version < producer_version:
                violations.append(
                    f"BACKWARD compatibility violation: consumer version "
                    f"{consumer_version} < producer version {producer_version}"
                )

        # FORWARD: Consumer version <= Producer version
        if mode in [CompatibilityMode.FORWARD, CompatibilityMode.FORWARD_TRANSITIVE]:
            if consumer_version > producer_version:
                violations.append(
                    f"FORWARD compatibility violation: consumer version "
                    f"{consumer_version} > producer version {producer_version}"
                )

        # FULL: Versions must be equal or within minor version range
        if mode in [CompatibilityMode.FULL, CompatibilityMode.FULL_TRANSITIVE]:
            # Both BACKWARD and FORWARD must be satisfied
            if consumer_version != producer_version:
                warnings.append(
                    f"FULL compatibility: versions differ "
                    f"(consumer={consumer_version}, producer={producer_version})"
                )

        compatible = len(violations) == 0

        return CompatibilityResult(
            compatible=compatible,
            mode=mode,
            consumer_version=consumer_version,
            producer_version=producer_version,
            violations=violations,
            warnings=warnings
        )

    @staticmethod
    def can_upgrade(
        from_version: Version,
        to_version: Version
    ) -> bool:
        """Check if upgrade from one version to another is allowed"""
        # Same major version: Always allowed
        if from_version.major == to_version.major:
            return to_version >= from_version

        # Major version upgrade: Only forward (not downgrade)
        return to_version.major > from_version.major

# Usage examples
checker = CompatibilityChecker()

# Example 1: Backward compatibility
result = checker.check_compatibility(
    consumer_version=Version("1.2.0"),
    producer_version=Version("1.1.0"),
    mode=CompatibilityMode.BACKWARD
)
print(f"Compatible: {result.compatible}")  # True

# Example 2: Forward compatibility violation
result = checker.check_compatibility(
    consumer_version=Version("1.1.0"),
    producer_version=Version("1.2.0"),
    mode=CompatibilityMode.FORWARD
)
print(f"Compatible: {result.compatible}")  # False
```

---

## Breaking vs. Non-Breaking Changes

### Breaking Changes (Require MAJOR Version Bump)

#### 1. Removing Fields

❌ **Breaking:**
```python
# v1.0.0
@dataclass
class UniversalContract:
    contract_id: str
    deprecated_field: str  # Will be removed

# v2.0.0
@dataclass
class UniversalContract:
    contract_id: str
    # deprecated_field removed → BREAKING
```

✅ **Non-Breaking Alternative:**
```python
# v1.1.0
@dataclass
class UniversalContract:
    contract_id: str
    deprecated_field: Optional[str] = None  # Mark as deprecated, keep field
```

#### 2. Changing Field Types

❌ **Breaking:**
```python
# v1.0.0
priority: str  # "HIGH", "MEDIUM", "LOW"

# v2.0.0
priority: int  # 1, 2, 3 → BREAKING
```

✅ **Non-Breaking Alternative:**
```python
# v1.1.0
priority_str: str  # Keep old field
priority_numeric: Optional[int] = None  # Add new field

# v2.0.0 (later, with migration period)
priority: int  # Remove priority_str after migration
```

#### 3. Renaming Fields

❌ **Breaking:**
```python
# v1.0.0
contract_id: str

# v2.0.0
id: str  # Renamed → BREAKING
```

✅ **Non-Breaking Alternative:**
```python
# v1.1.0
contract_id: str  # Keep old name
id: Optional[str] = None  # Add alias

# Property for backward compatibility
@property
def id(self):
    return self.contract_id
```

#### 4. Removing Enum Values

❌ **Breaking:**
```python
# v1.0.0
class ContractLifecycle(Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    DEPRECATED_STATE = "deprecated"  # Will be removed

# v2.0.0
class ContractLifecycle(Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    # DEPRECATED_STATE removed → BREAKING
```

✅ **Non-Breaking Alternative:**
```python
# v1.1.0
class ContractLifecycle(Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    DEPRECATED_STATE = "deprecated"  # Mark as deprecated in docs, keep value
```

#### 5. Tightening Validation

❌ **Breaking:**
```python
# v1.0.0
threshold: float  # 0-100

# v2.0.0
threshold: float  # 80-100 only → BREAKING (rejects previously valid values)
```

✅ **Non-Breaking Alternative:**
```python
# v1.1.0
threshold: float  # 0-100 (keep old range)
recommended_threshold: Optional[float] = None  # 80-100 (new strict range)
```

### Non-Breaking Changes (MINOR or PATCH Version Bump)

#### 1. Adding Optional Fields (MINOR)

✅ **Non-Breaking:**
```python
# v1.0.0
@dataclass
class UniversalContract:
    contract_id: str

# v1.1.0
@dataclass
class UniversalContract:
    contract_id: str
    tags: Optional[List[str]] = None  # New optional field
```

#### 2. Adding Enum Values (MINOR)

✅ **Non-Breaking:**
```python
# v1.0.0
class ContractType(Enum):
    FEATURE = "feature"
    BUG_FIX = "bug_fix"

# v1.1.0
class ContractType(Enum):
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    DEPLOYMENT = "deployment"  # New value
```

**Note:** Old consumers may treat new values as "unknown" - provide sensible defaults.

#### 3. Relaxing Validation (MINOR)

✅ **Non-Breaking:**
```python
# v1.0.0
threshold: float  # 90-100

# v1.1.0
threshold: float  # 80-100 (relaxed lower bound)
```

#### 4. Documentation Updates (PATCH)

✅ **Non-Breaking:**
```python
# v1.0.0
contract_id: str  # Unique identifier

# v1.0.1
contract_id: str  # Unique identifier (UUID4 format recommended)
```

#### 5. Bug Fixes (PATCH)

✅ **Non-Breaking:**
```python
# v1.0.0
def validate_email(email: str) -> bool:
    return "@" in email  # Bug: too simplistic

# v1.0.1
def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))  # Fixed regex
```

### Change Decision Tree

```
Is the change removing a field?
├─ YES → MAJOR (breaking)
└─ NO
   ├─ Is the change altering a field type?
   │  ├─ YES → MAJOR (breaking)
   │  └─ NO
   │     ├─ Is the change adding a required field?
   │     │  ├─ YES → MAJOR (breaking)
   │     │  └─ NO
   │     │     ├─ Is the change adding an optional field?
   │     │     │  ├─ YES → MINOR (compatible)
   │     │     │  └─ NO
   │     │     │     ├─ Is the change tightening validation?
   │     │     │     │  ├─ YES → MAJOR (breaking)
   │     │     │     │  └─ NO
   │     │     │     │     ├─ Is the change relaxing validation?
   │     │     │     │     │  ├─ YES → MINOR (compatible)
   │     │     │     │     │  └─ NO
   │     │     │     │     │     ├─ Is the change documentation-only?
   │     │     │     │     │     │  ├─ YES → PATCH (compatible)
   │     │     │     │     │     │  └─ NO → Analyze specific case
```

---

## Version Negotiation Protocol

### Negotiation Flow

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VersionNegotiation:
    """Version negotiation request"""
    negotiation_id: str
    requesting_agent: str
    supported_versions: List[Version]  # Versions the agent supports
    preferred_version: Version  # Agent's preferred version
    compatibility_mode: CompatibilityMode
    message: Optional[str] = None

@dataclass
class VersionNegotiationResult:
    """Result of version negotiation"""
    negotiation_id: str
    agreed_version: Optional[Version]
    success: bool
    reason: Optional[str] = None

class VersionNegotiator:
    """Negotiates protocol version between agents"""

    def __init__(self, registry_version: Version):
        self.registry_version = registry_version

    def negotiate(
        self,
        negotiation: VersionNegotiation
    ) -> VersionNegotiationResult:
        """Negotiate protocol version with requesting agent"""

        # Find common versions
        compatible_versions = [
            v for v in negotiation.supported_versions
            if self._is_compatible(v, negotiation.compatibility_mode)
        ]

        if not compatible_versions:
            return VersionNegotiationResult(
                negotiation_id=negotiation.negotiation_id,
                agreed_version=None,
                success=False,
                reason=f"No compatible versions found. Registry version: {self.registry_version}, "
                       f"Agent versions: {[str(v) for v in negotiation.supported_versions]}"
            )

        # Choose version (prefer agent's preferred version if compatible)
        if negotiation.preferred_version in compatible_versions:
            agreed_version = negotiation.preferred_version
        else:
            # Fall back to highest compatible version
            agreed_version = max(compatible_versions)

        return VersionNegotiationResult(
            negotiation_id=negotiation.negotiation_id,
            agreed_version=agreed_version,
            success=True,
            reason=f"Agreed on version {agreed_version}"
        )

    def _is_compatible(
        self,
        agent_version: Version,
        mode: CompatibilityMode
    ) -> bool:
        """Check if agent version is compatible with registry version"""

        result = CompatibilityChecker.check_compatibility(
            consumer_version=self.registry_version,
            producer_version=agent_version,
            mode=mode
        )

        return result.compatible

# Usage example
registry_version = Version("1.2.0")
negotiator = VersionNegotiator(registry_version)

# Agent requests negotiation
negotiation = VersionNegotiation(
    negotiation_id="NEG_001",
    requesting_agent="frontend_agent",
    supported_versions=[
        Version("1.0.0"),
        Version("1.1.0"),
        Version("1.2.0")
    ],
    preferred_version=Version("1.2.0"),
    compatibility_mode=CompatibilityMode.BACKWARD
)

result = negotiator.negotiate(negotiation)
if result.success:
    print(f"✅ Agreed on version: {result.agreed_version}")
else:
    print(f"❌ Negotiation failed: {result.reason}")
```

### Capability Advertisement

Agents should advertise their capabilities:

```python
@dataclass
class AgentCapabilities:
    """Agent's protocol capabilities"""
    agent_id: str
    supported_schema_versions: List[Version]
    preferred_schema_version: Version
    supported_contract_types: List[str]
    supported_validators: List[str]
    compatibility_mode: CompatibilityMode

# Example advertisement
frontend_capabilities = AgentCapabilities(
    agent_id="frontend_developer_001",
    supported_schema_versions=[
        Version("1.0.0"),
        Version("1.1.0"),
        Version("1.2.0")
    ],
    preferred_schema_version=Version("1.2.0"),
    supported_contract_types=["UX_DESIGN", "FEATURE", "BUG_FIX"],
    supported_validators=["axe_core", "lighthouse", "screenshot_diff"],
    compatibility_mode=CompatibilityMode.BACKWARD
)
```

---

## Migration Strategies

### Strategy 1: Blue-Green Deployment

**Scenario:** Migrate from v1.0.0 to v2.0.0 (major version, breaking changes)

**Steps:**

1. **Prepare v2.0.0 environment** (blue)
2. **Keep v1.0.0 running** (green)
3. **Route new traffic to v2.0.0**
4. **Migrate existing contracts**
5. **Drain v1.0.0 traffic**
6. **Decommission v1.0.0**

**Implementation:**
```python
class MigrationOrchestrator:
    """Orchestrates contract migration between versions"""

    def __init__(self, old_registry, new_registry):
        self.old_registry = old_registry  # v1.0.0
        self.new_registry = new_registry  # v2.0.0

    def migrate_contract(
        self,
        contract_id: str,
        migration_func: Callable
    ) -> bool:
        """Migrate single contract from old to new registry"""

        # 1. Retrieve contract from old registry
        old_contract = self.old_registry.get_contract(contract_id)

        # 2. Transform contract to new schema
        new_contract = migration_func(old_contract)

        # 3. Validate new contract
        if not self._validate_migrated_contract(new_contract):
            return False

        # 4. Register in new registry
        self.new_registry.register_contract(new_contract)

        # 5. Mark as migrated in old registry
        old_contract.metadata["migrated_to_v2"] = True
        old_contract.metadata["migration_timestamp"] = datetime.utcnow().isoformat()

        return True

    def _validate_migrated_contract(self, contract: UniversalContract) -> bool:
        """Validate that migrated contract is valid in new schema"""
        # Run schema validators
        # Check required fields
        # Verify data types
        return True

# Migration function for v1 → v2
def migrate_v1_to_v2(v1_contract: UniversalContract) -> UniversalContract:
    """Transform v1 contract to v2 schema"""

    # Example: v2 renames 'contract_id' to 'id'
    v2_contract = UniversalContract(
        id=v1_contract.contract_id,  # Renamed field
        schema_version="2.0.0",
        contract_version=1,  # Reset contract version
        # ... map other fields
    )

    return v2_contract

# Usage
orchestrator = MigrationOrchestrator(old_registry_v1, new_registry_v2)

# Migrate all contracts
for contract_id in old_registry_v1.list_contracts():
    success = orchestrator.migrate_contract(contract_id, migrate_v1_to_v2)
    if success:
        print(f"✅ Migrated {contract_id}")
    else:
        print(f"❌ Migration failed for {contract_id}")
```

### Strategy 2: Gradual Migration (Rolling Upgrade)

**Scenario:** Minor version upgrade (v1.1.0 → v1.2.0) with backward compatibility

**Steps:**

1. **Deploy v1.2.0 alongside v1.1.0**
2. **Route percentage of traffic to v1.2.0** (e.g., 10%)
3. **Monitor for errors**
4. **Gradually increase percentage** (25%, 50%, 75%, 100%)
5. **Decommission v1.1.0**

**Implementation:**
```python
class GradualMigrationOrchestrator:
    """Manages gradual migration with traffic splitting"""

    def __init__(
        self,
        old_registry,
        new_registry,
        traffic_split: float = 0.1  # 10% to new version
    ):
        self.old_registry = old_registry
        self.new_registry = new_registry
        self.traffic_split = traffic_split

    def route_contract_operation(
        self,
        operation: str,
        *args,
        **kwargs
    ):
        """Route operation to old or new registry based on traffic split"""

        # Random routing based on traffic split
        if random.random() < self.traffic_split:
            # Route to new registry
            return getattr(self.new_registry, operation)(*args, **kwargs)
        else:
            # Route to old registry
            return getattr(self.old_registry, operation)(*args, **kwargs)

    def increase_traffic_split(self, new_split: float):
        """Gradually increase traffic to new version"""
        self.traffic_split = min(new_split, 1.0)
        print(f"Traffic split updated: {self.traffic_split * 100}% to v1.2.0")

# Usage
gradual_migration = GradualMigrationOrchestrator(
    old_registry=registry_v1_1,
    new_registry=registry_v1_2,
    traffic_split=0.1  # Start with 10%
)

# Gradually increase over time
gradual_migration.increase_traffic_split(0.25)  # Day 1: 25%
# Monitor metrics
gradual_migration.increase_traffic_split(0.50)  # Day 2: 50%
# Monitor metrics
gradual_migration.increase_traffic_split(1.0)   # Day 3: 100%
```

### Strategy 3: Feature Flags

**Scenario:** A/B testing new schema features

**Implementation:**
```python
from dataclasses import dataclass
from typing import Set

@dataclass
class FeatureFlag:
    """Feature flag for gradual feature rollout"""
    flag_name: str
    enabled_for: Set[str]  # Agent IDs
    enabled_percentage: float  # 0.0 - 1.0

class FeatureFlaggedRegistry(ContractRegistry):
    """Registry with feature flag support"""

    def __init__(self):
        super().__init__()
        self.feature_flags: Dict[str, FeatureFlag] = {}

    def is_feature_enabled(
        self,
        flag_name: str,
        agent_id: str
    ) -> bool:
        """Check if feature is enabled for agent"""

        flag = self.feature_flags.get(flag_name)
        if not flag:
            return False

        # Check explicit enable
        if agent_id in flag.enabled_for:
            return True

        # Check percentage rollout
        return random.random() < flag.enabled_percentage

    def create_contract_v1_2(
        self,
        agent_id: str,
        **kwargs
    ) -> UniversalContract:
        """Create contract with v1.2.0 features if enabled"""

        if self.is_feature_enabled("schema_v1_2", agent_id):
            # Use v1.2.0 schema with new features
            kwargs["schema_version"] = "1.2.0"
            kwargs["retry_policy"] = kwargs.get("retry_policy", {"max_retries": 3})
        else:
            # Use v1.1.0 schema (no retry_policy)
            kwargs["schema_version"] = "1.1.0"

        return UniversalContract(**kwargs)

# Usage
registry = FeatureFlaggedRegistry()

# Enable for specific agents
registry.feature_flags["schema_v1_2"] = FeatureFlag(
    flag_name="schema_v1_2",
    enabled_for={"frontend_agent_001", "backend_agent_005"},
    enabled_percentage=0.1  # 10% general rollout
)

# Check if enabled
if registry.is_feature_enabled("schema_v1_2", "frontend_agent_001"):
    print("v1.2.0 features enabled for frontend_agent_001")
```

---

## Rollback Procedures

### Rollback Decision Tree

```
Is rollback needed?
├─ YES
│  ├─ Is data migration reversible?
│  │  ├─ YES → Execute rollback procedure
│  │  └─ NO
│  │     ├─ Is forward-fix possible?
│  │     │  ├─ YES → Apply forward-fix
│  │     │  └─ NO → **CRITICAL: Manual intervention required**
└─ NO → Continue with new version
```

### Rollback Strategy

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RollbackPlan:
    """Plan for rolling back to previous version"""
    from_version: Version
    to_version: Version
    reason: str
    affected_contracts: List[str]
    reversible: bool
    rollback_steps: List[str]

class RollbackOrchestrator:
    """Manages rollback to previous version"""

    def __init__(self, current_registry, backup_registry):
        self.current_registry = current_registry
        self.backup_registry = backup_registry

    def create_rollback_plan(
        self,
        from_version: Version,
        to_version: Version,
        reason: str
    ) -> RollbackPlan:
        """Create plan for rolling back"""

        affected_contracts = self.current_registry.list_contracts()

        # Check if rollback is reversible
        reversible = self._check_reversibility(from_version, to_version)

        steps = []
        if reversible:
            steps = [
                "1. Stop routing traffic to new version",
                "2. Restore contracts from backup",
                "3. Verify contract integrity",
                "4. Resume traffic to old version",
                "5. Monitor for errors"
            ]
        else:
            steps = [
                "1. STOP: Rollback not reversible",
                "2. Assess forward-fix options",
                "3. Consult architecture team"
            ]

        return RollbackPlan(
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            affected_contracts=affected_contracts,
            reversible=reversible,
            rollback_steps=steps
        )

    def _check_reversibility(
        self,
        from_version: Version,
        to_version: Version
    ) -> bool:
        """Check if rollback is reversible (no data loss)"""

        # Same major version: Usually reversible
        if from_version.major == to_version.major:
            return True

        # Major version downgrade: Check for breaking changes
        if from_version.major > to_version.major:
            # Analyze schema differences
            # Check for removed fields, type changes, etc.
            return self._analyze_schema_diff(from_version, to_version)

        return False

    def _analyze_schema_diff(
        self,
        from_version: Version,
        to_version: Version
    ) -> bool:
        """Analyze schema differences to determine reversibility"""
        # Placeholder: Implement schema diff analysis
        # Check for:
        # - Removed required fields (not reversible)
        # - Changed field types (not reversible)
        # - Added optional fields (reversible)
        return True

    def execute_rollback(
        self,
        plan: RollbackPlan
    ) -> bool:
        """Execute rollback plan"""

        if not plan.reversible:
            print(f"❌ Rollback from {plan.from_version} to {plan.to_version} is NOT reversible")
            return False

        print(f"🔄 Rolling back from {plan.from_version} to {plan.to_version}")
        print(f"Reason: {plan.reason}")

        for step in plan.rollback_steps:
            print(f"  {step}")
            # Execute step
            # ...

        # Restore from backup
        for contract_id in plan.affected_contracts:
            backup_contract = self.backup_registry.get_contract(contract_id)
            self.current_registry.register_contract(backup_contract)

        print("✅ Rollback complete")
        return True

# Usage
orchestrator = RollbackOrchestrator(
    current_registry=registry_v1_2,
    backup_registry=registry_v1_1
)

# Create rollback plan
plan = orchestrator.create_rollback_plan(
    from_version=Version("1.2.0"),
    to_version=Version("1.1.0"),
    reason="Critical bug in v1.2.0 validator"
)

# Execute if reversible
if plan.reversible:
    orchestrator.execute_rollback(plan)
else:
    print("Rollback not reversible. Consider forward-fix.")
```

---

## Deprecation Policy

### Deprecation Lifecycle

**Timeline:** 3 versions or 6 months (whichever is longer)

**Phases:**

1. **Announcement** (Version N)
   - Add `@deprecated` annotation
   - Update documentation
   - Add warning logs

2. **Grace Period** (Versions N+1, N+2)
   - Feature still works
   - Warnings continue
   - Provide migration guide

3. **Removal** (Version N+3 or MAJOR version)
   - Remove deprecated feature
   - Breaking change (MAJOR version bump)

### Deprecation Implementation

```python
import warnings
from functools import wraps

def deprecated(
    since: str,
    removal: str,
    alternative: Optional[str] = None
):
    """Decorator to mark functions/classes as deprecated"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = (
                f"{func.__name__} is deprecated since version {since} "
                f"and will be removed in version {removal}."
            )
            if alternative:
                message += f" Use {alternative} instead."

            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        # Add deprecation metadata
        wrapper._deprecated = True
        wrapper._deprecation_info = {
            "since": since,
            "removal": removal,
            "alternative": alternative
        }

        return wrapper
    return decorator

# Usage
class ContractRegistry:

    @deprecated(
        since="1.1.0",
        removal="2.0.0",
        alternative="verify_contract_fulfillment"
    )
    def verify_contract(self, contract_id: str):
        """Old method name - deprecated"""
        return self.verify_contract_fulfillment(contract_id)

    def verify_contract_fulfillment(self, contract_id: str):
        """New method name"""
        # Implementation
        pass

# When called, logs deprecation warning:
registry = ContractRegistry()
registry.verify_contract("CONTRACT_001")
# DeprecationWarning: verify_contract is deprecated since version 1.1.0
# and will be removed in version 2.0.0. Use verify_contract_fulfillment instead.
```

### Deprecation Documentation

```python
@dataclass
class DeprecationNotice:
    """Deprecation notice for protocol features"""
    feature_name: str
    deprecated_in: Version
    removal_in: Version
    reason: str
    alternative: Optional[str]
    migration_guide_url: Optional[str]

# Example deprecations
DEPRECATIONS = [
    DeprecationNotice(
        feature_name="ContractRegistry.verify_contract",
        deprecated_in=Version("1.1.0"),
        removal_in=Version("2.0.0"),
        reason="Method name was ambiguous",
        alternative="ContractRegistry.verify_contract_fulfillment",
        migration_guide_url="https://docs.example.com/migration/verify-contract"
    ),
    DeprecationNotice(
        feature_name="UniversalContract.priority (string)",
        deprecated_in=Version("1.2.0"),
        removal_in=Version("2.0.0"),
        reason="Numeric priority is more flexible",
        alternative="UniversalContract.priority_numeric",
        migration_guide_url="https://docs.example.com/migration/priority-field"
    )
]
```

---

## Examples and Patterns

### Example 1: Version-Aware Contract Creation

```python
def create_contract_for_agent(
    agent_id: str,
    agent_version: Version,
    registry_version: Version,
    **kwargs
) -> UniversalContract:
    """Create contract compatible with agent's version"""

    # Check compatibility
    compatible = CompatibilityChecker.check_compatibility(
        consumer_version=registry_version,
        producer_version=agent_version,
        mode=CompatibilityMode.BACKWARD
    )

    if not compatible.compatible:
        raise ValueError(f"Agent version {agent_version} incompatible with registry {registry_version}")

    # Create contract with appropriate schema version
    contract = UniversalContract(
        schema_version=str(min(agent_version, registry_version)),
        contract_version=1,
        **kwargs
    )

    # Remove fields not supported by agent's version
    if agent_version < Version("1.1.0"):
        # v1.0.0 doesn't support retry_policy
        if hasattr(contract, 'retry_policy'):
            delattr(contract, 'retry_policy')

    return contract

# Usage
frontend_agent_version = Version("1.0.0")
registry_version = Version("1.2.0")

contract = create_contract_for_agent(
    agent_id="frontend_001",
    agent_version=frontend_agent_version,
    registry_version=registry_version,
    contract_type=ContractType.FEATURE,
    name="Login Feature"
)

print(f"Contract schema version: {contract.schema_version}")  # "1.0.0"
```

### Example 2: Multi-Version Contract Storage

```python
class VersionedContractStore:
    """Store contracts with multiple schema versions"""

    def __init__(self):
        self.contracts_by_version: Dict[Version, List[UniversalContract]] = defaultdict(list)

    def store(self, contract: UniversalContract):
        """Store contract indexed by schema version"""
        version = Version(contract.schema_version)
        self.contracts_by_version[version].append(contract)

    def retrieve(
        self,
        contract_id: str,
        requested_version: Optional[Version] = None
    ) -> Optional[UniversalContract]:
        """Retrieve contract, optionally in specific version"""

        # Find contract in any version
        for version, contracts in self.contracts_by_version.items():
            for contract in contracts:
                if contract.contract_id == contract_id:
                    # Found contract
                    if requested_version and version != requested_version:
                        # Transform to requested version
                        return self._transform_contract(contract, requested_version)
                    return contract

        return None

    def _transform_contract(
        self,
        contract: UniversalContract,
        target_version: Version
    ) -> UniversalContract:
        """Transform contract to different schema version"""
        # Implement transformation logic
        # Handle field additions, removals, renames, etc.
        pass

# Usage
store = VersionedContractStore()

# Store contracts in different versions
store.store(UniversalContract(schema_version="1.0.0", contract_id="C1"))
store.store(UniversalContract(schema_version="1.1.0", contract_id="C2"))
store.store(UniversalContract(schema_version="1.2.0", contract_id="C3"))

# Retrieve in original version
contract = store.retrieve("C1")  # Returns v1.0.0

# Retrieve transformed to newer version
contract_v1_2 = store.retrieve("C1", requested_version=Version("1.2.0"))
```

---

## Best Practices

### 1. Version Early, Version Often

**✅ DO:**
- Start with v1.0.0 from day one
- Increment versions for every protocol change
- Document version changes in CHANGELOG.md

**❌ DON'T:**
- Use unversioned schemas
- Skip version numbers
- Retroactively add versions

### 2. Plan for Compatibility

**✅ DO:**
- Add optional fields instead of required fields
- Use feature flags for gradual rollout
- Maintain backward compatibility within major versions

**❌ DON'T:**
- Make breaking changes in MINOR versions
- Remove deprecated features without grace period
- Change field types without migration path

### 3. Test Version Compatibility

**✅ DO:**
```python
def test_backward_compatibility():
    """Test that new version reads old contracts"""
    # Create contract with old schema
    old_contract = UniversalContract(schema_version="1.0.0")

    # Verify new registry can read it
    registry_v1_2 = ContractRegistry()
    result = registry_v1_2.verify_contract_fulfillment(old_contract.contract_id)

    assert result is not None
```

**❌ DON'T:**
- Skip compatibility tests
- Test only happy paths
- Ignore edge cases

### 4. Communicate Version Changes

**✅ DO:**
- Publish migration guides
- Announce deprecations in advance
- Provide code examples for migration

**❌ DON'T:**
- Make surprise breaking changes
- Hide deprecations in fine print
- Force immediate upgrades

### 5. Use Version Prefixes in APIs

**✅ DO:**
```python
# API versioning
/api/v1/contracts
/api/v2/contracts

# Protocol negotiation
GET /api/version → {"versions": ["1.0.0", "1.1.0", "1.2.0"]}
```

**❌ DON'T:**
```python
# No versioning
/api/contracts  # Which version?
```

---

## Conclusion

Version management is critical for production deployments of the Universal Contract Protocol. This guide provides:

- **Semantic versioning** for predictable version progression
- **Compatibility modes** for flexible version checking
- **Migration strategies** for smooth upgrades
- **Rollback procedures** for safety
- **Deprecation policy** for graceful feature removal

**Key Takeaways:**

1. Use semantic versioning (MAJOR.MINOR.PATCH)
2. Distinguish schema version (protocol) from contract version (amendments)
3. Choose appropriate compatibility mode for your use case
4. Plan migrations carefully (blue-green, gradual, feature flags)
5. Always maintain rollback capability
6. Deprecate features with 3-version grace period
7. Test version compatibility rigorously

**Next Steps:**

- Implement `Version` and `CompatibilityChecker` classes
- Add version negotiation to contract registry
- Create migration scripts for v1 → v2 upgrade
- Set up feature flags for gradual rollout
- Document deprecation timeline

---

**Document Version:** 1.0.0
**Protocol Version:** 1.1.0+
**Status:** Phase 2 Strategic Enhancement
**Author:** Claude (Sonnet 4.5)

This document is part of the Universal Contract Protocol (ACP) Phase 2 specification suite.

**See Also:**
- `RUNTIME_MODES.md` - Environment-specific configurations
- `CONSUMER_DRIVEN_CONTRACTS.md` - Pact-style testing
- `SCHEMA_REGISTRY_INTEGRATION.md` - Centralized schema management
