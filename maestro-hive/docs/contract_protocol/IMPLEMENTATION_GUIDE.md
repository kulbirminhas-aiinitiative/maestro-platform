# Implementation Guide
## Technical Implementation of Universal Contract Protocol

**Version:** 1.1.0
**Date:** 2025-10-11
**Status:** Phase 1 Corrections Applied

---

## Overview

This guide provides step-by-step instructions for implementing the Universal Contract Protocol (ACP) in the maestro-hive system. It covers:
- File changes required
- New classes and data structures
- Integration with existing system
- Migration strategy
- Testing approach

---

## Table of Contents

1. [Architecture Changes](#architecture-changes)
2. [New Files to Create](#new-files-to-create)
3. [Existing Files to Modify](#existing-files-to-modify)
4. [Data Models](#data-models)
5. [Contract Registry Implementation](#contract-registry-implementation)
6. [Validator Framework](#validator-framework)
7. [Agent Integration](#agent-integration)
8. [Phase Execution Integration](#phase-execution-integration)
9. [Migration Strategy](#migration-strategy)
10. [Testing Strategy](#testing-strategy)

---

## Architecture Changes

### Current Architecture
```
team_execution_v2_split_mode.py (Phase orchestration)
    ↓
team_execution_v2.py (AI-driven execution)
    ↓
parallel_coordinator_v2.py (Persona orchestration)
    ↓
persona_executor_v2.py (Individual persona execution)
```

### New Architecture with ACP
```
team_execution_v2_split_mode.py (Phase orchestration)
    ↓
contract_registry.py (Contract management) ← NEW
    ↓
team_execution_v2.py (Contract-aware execution) ← MODIFIED
    ↓
parallel_coordinator_v2.py (Contract distribution) ← MODIFIED
    ↓
persona_executor_v2.py (Contract fulfillment) ← MODIFIED
    ↓
contract_validators/ (Validation framework) ← NEW
```

---

## New Files to Create

### 1. contract_registry.py

**Location:** `/home/ec2-user/projects/maestro-platform/maestro-hive/contract_registry.py`

**Purpose:** Central registry for all contracts with lifecycle management and dependency orchestration

**Key Classes:**
```python
# contract_registry.py

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import networkx as nx
import logging

logger = logging.getLogger(__name__)


class ContractLifecycle(Enum):
    """Contract lifecycle states"""
    DRAFT = "draft"
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    VERIFIED = "verified"
    BREACHED = "breached"
    REJECTED = "rejected"
    AMENDED = "amended"


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion"""
    criterion: str
    validator: str
    threshold: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_critical: bool = True
    description: str = ""


@dataclass
class CriterionResult:
    """Result of validating a single criterion"""
    criterion_name: str
    passed: bool
    score: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class VerificationResult:
    """Result of contract verification"""
    contract_id: str
    passed: bool
    score: Optional[float] = None
    criterion_results: List[CriterionResult] = field(default_factory=list)
    verified_at: datetime = field(default_factory=datetime.now)
    verified_by: str = ""
    artifact_paths: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    remediation_suggestions: List[str] = field(default_factory=list)


@dataclass
class UniversalContract:
    """Universal contract specification"""
    # Identity
    contract_id: str
    contract_type: str
    name: str
    description: str = ""

    # Parties
    provider_agent: str = ""
    consumer_agents: List[str] = field(default_factory=list)

    # Specification (flexible structure)
    specification: Dict[str, Any] = field(default_factory=dict)

    # Validation
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)

    # Lifecycle
    lifecycle_state: ContractLifecycle = ContractLifecycle.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # Enforcement
    is_blocking: bool = True
    priority: str = "MEDIUM"
    breach_consequences: List[str] = field(default_factory=list)

    # Verification
    verification_method: str = "automated"
    verification_result: Optional[VerificationResult] = None

    # Metadata
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContractRegistry:
    """
    Central registry for all contracts.
    Manages contract lifecycle, dependencies, and verification.
    """

    def __init__(self):
        self.contracts: Dict[str, UniversalContract] = {}
        self.dependency_graph = nx.DiGraph()
        self.validators = {}  # validator_name -> validator_instance

    def register_contract(self, contract: UniversalContract):
        """Register a new contract in the system"""
        self.contracts[contract.contract_id] = contract

        # Add to dependency graph
        self.dependency_graph.add_node(contract.contract_id)
        for dep_id in contract.depends_on:
            self.dependency_graph.add_edge(dep_id, contract.contract_id)

        logger.info(f"Registered contract {contract.contract_id} ({contract.contract_type})")

    def get_executable_contracts(self) -> List[UniversalContract]:
        """Get contracts ready to execute (dependencies fulfilled)"""
        executable = []
        for contract_id, contract in self.contracts.items():
            if contract.lifecycle_state == ContractLifecycle.ACCEPTED:
                # Check if all dependencies are fulfilled
                deps_fulfilled = all(
                    self.contracts[dep_id].lifecycle_state == ContractLifecycle.VERIFIED
                    for dep_id in contract.depends_on
                    if dep_id in self.contracts
                )
                if deps_fulfilled:
                    executable.append(contract)
        return executable

    def get_contract(self, contract_id: str) -> Optional[UniversalContract]:
        """Retrieve a contract by ID"""
        return self.contracts.get(contract_id)

    def get_contracts_by_type(self, contract_type: str) -> List[UniversalContract]:
        """Get all contracts of a specific type"""
        return [c for c in self.contracts.values() if c.contract_type == contract_type]

    def get_contracts_for_agent(
        self,
        agent_id: str,
        role: str = "both"
    ) -> List[UniversalContract]:
        """
        Get contracts for an agent.

        Args:
            agent_id: Agent identifier
            role: "provider", "consumer", or "both"
        """
        contracts = []
        for contract in self.contracts.values():
            if role in ["provider", "both"] and contract.provider_agent == agent_id:
                contracts.append(contract)
            if role in ["consumer", "both"] and agent_id in contract.consumer_agents:
                contracts.append(contract)
        return contracts

    def get_dependency_chain(self, contract_id: str) -> List[str]:
        """Get all contracts in dependency chain"""
        if contract_id not in self.dependency_graph:
            return []
        ancestors = nx.ancestors(self.dependency_graph, contract_id)
        return list(ancestors)

    def update_contract_state(
        self,
        contract_id: str,
        new_state: ContractLifecycle
    ):
        """Update contract lifecycle state"""
        if contract_id in self.contracts:
            contract = self.contracts[contract_id]
            old_state = contract.lifecycle_state
            contract.lifecycle_state = new_state

            # Update timestamps
            if new_state == ContractLifecycle.ACCEPTED:
                contract.accepted_at = datetime.now()
            elif new_state == ContractLifecycle.FULFILLED:
                contract.fulfilled_at = datetime.now()
            elif new_state == ContractLifecycle.VERIFIED:
                contract.verified_at = datetime.now()

            logger.info(f"Contract {contract_id} state: {old_state.value} → {new_state.value}")

    def register_validator(self, validator_name: str, validator_instance):
        """Register a validator"""
        self.validators[validator_name] = validator_instance
        logger.info(f"Registered validator: {validator_name}")

    def verify_contract_fulfillment(
        self,
        contract_id: str,
        artifacts: Dict[str, Any]
    ) -> VerificationResult:
        """Verify that a contract has been fulfilled"""
        contract = self.contracts[contract_id]

        criterion_results = []
        all_passed = True

        for criterion in contract.acceptance_criteria:
            validator = self.validators.get(criterion.validator)
            if not validator:
                logger.warning(f"Validator {criterion.validator} not found, skipping")
                continue

            try:
                result = validator.validate(
                    artifacts=artifacts,
                    specification=contract.specification,
                    criterion=criterion
                )
                criterion_results.append(result)

                if not result.passed and criterion.is_critical:
                    all_passed = False
            except Exception as e:
                logger.error(f"Validation failed for {criterion.criterion}: {e}")
                criterion_results.append(CriterionResult(
                    criterion_name=criterion.criterion,
                    passed=False,
                    message=str(e)
                ))
                if criterion.is_critical:
                    all_passed = False

        verification = VerificationResult(
            contract_id=contract_id,
            passed=all_passed,
            criterion_results=criterion_results,
            verified_at=datetime.now(),
            verified_by="automated",
            artifact_paths=list(artifacts.keys())
        )

        # Update contract
        contract.verification_result = verification
        if all_passed:
            self.update_contract_state(contract_id, ContractLifecycle.VERIFIED)
        else:
            self.update_contract_state(contract_id, ContractLifecycle.BREACHED)

        return verification

    def get_blocked_contracts(self, contract_id: str) -> List[str]:
        """Get contracts that are blocked by this contract"""
        if contract_id not in self.dependency_graph:
            return []
        descendants = nx.descendants(self.dependency_graph, contract_id)
        return list(descendants)

    def export_contracts(self) -> Dict[str, Any]:
        """Export all contracts to JSON-serializable format"""
        from dataclasses import asdict
        return {
            contract_id: asdict(contract)
            for contract_id, contract in self.contracts.items()
        }

    def import_contracts(self, contracts_data: Dict[str, Any]):
        """Import contracts from JSON-serializable format"""
        for contract_id, contract_data in contracts_data.items():
            contract = UniversalContract(**contract_data)
            self.register_contract(contract)
```

**Lines of Code:** ~250

---

### 2. contract_validators/

**Location:** `/home/ec2-user/projects/maestro-platform/maestro-hive/contract_validators/`

**Purpose:** Pluggable validator framework

**Files:**
- `__init__.py`: Validator base classes
- `ux_validators.py`: UX design validators
- `api_validators.py`: API contract validators
- `security_validators.py`: Security policy validators
- `performance_validators.py`: Performance validators

See **VALIDATOR_FRAMEWORK.md** for detailed implementation.

---

### 3. contract_aware_agent.py

**Location:** `/home/ec2-user/projects/maestro-platform/maestro-hive/contract_aware_agent.py`

**Purpose:** Base class for agents that participate in contract protocol

```python
# contract_aware_agent.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from contract_registry import (
    ContractRegistry,
    UniversalContract,
    ContractLifecycle,
    VerificationResult
)

logger = logging.getLogger(__name__)


class ContractAwareAgent(ABC):
    """
    Base class for agents that participate in contract protocol.
    """

    def __init__(self, agent_id: str, registry: ContractRegistry):
        self.agent_id = agent_id
        self.registry = registry

    async def propose_contract(self, contract: UniversalContract):
        """Propose a contract to downstream consumers"""
        contract.lifecycle_state = ContractLifecycle.PROPOSED
        contract.provider_agent = self.agent_id

        # Register in registry
        self.registry.register_contract(contract)

        # Notify consumers
        for consumer in contract.consumer_agents:
            await self._notify_agent(consumer, "contract_proposed", contract)

        logger.info(f"Agent {self.agent_id} proposed contract {contract.contract_id}")

    async def accept_contract(self, contract_id: str):
        """Accept a contract as a consumer"""
        contract = self.registry.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if self.agent_id not in contract.consumer_agents:
            raise ValueError(f"Agent {self.agent_id} is not a consumer of {contract_id}")

        self.registry.update_contract_state(contract_id, ContractLifecycle.ACCEPTED)
        logger.info(f"Agent {self.agent_id} accepted contract {contract_id}")

    async def fulfill_contract(
        self,
        contract_id: str,
        artifacts: Dict[str, Any]
    ) -> VerificationResult:
        """Fulfill a contract by producing deliverables"""
        contract = self.registry.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if contract.provider_agent != self.agent_id:
            raise ValueError(f"Agent {self.agent_id} is not provider of {contract_id}")

        # Mark as in progress
        self.registry.update_contract_state(contract_id, ContractLifecycle.IN_PROGRESS)

        # Execute work to fulfill contract
        await self.execute_work(contract, artifacts)

        # Mark as fulfilled
        self.registry.update_contract_state(contract_id, ContractLifecycle.FULFILLED)

        # Submit for verification
        verification = self.registry.verify_contract_fulfillment(
            contract_id,
            artifacts
        )

        if not verification.passed and contract.is_blocking:
            logger.error(f"BLOCKING contract {contract_id} verification failed!")
            raise ContractBreachException(contract_id, verification)

        return verification

    @abstractmethod
    async def execute_work(
        self,
        contract: UniversalContract,
        artifacts: Dict[str, Any]
    ):
        """Execute work to fulfill the contract (implemented by subclasses)"""
        pass

    async def _notify_agent(self, agent_id: str, event_type: str, data: Any):
        """Notify another agent (implementation depends on system architecture)"""
        logger.info(f"Notify {agent_id}: {event_type}")


class ContractBreachException(Exception):
    """Raised when a blocking contract is breached"""

    def __init__(self, contract_id: str, verification_result: VerificationResult):
        self.contract_id = contract_id
        self.verification_result = verification_result
        super().__init__(f"Contract {contract_id} verification failed")
```

**Lines of Code:** ~100

---

## Existing Files to Modify

### 1. team_execution_context.py

**Modifications:**
- Add `contract_registry: ContractRegistry` field
- Add methods to store/retrieve contracts
- Add contract verification results to phase results

```python
# Add to TeamExecutionContext class

from contract_registry import ContractRegistry, UniversalContract, VerificationResult

@dataclass
class TeamExecutionContext:
    # ... existing fields ...

    # NEW: Contract registry
    contract_registry: Optional[ContractRegistry] = field(default_factory=ContractRegistry)

    def add_contract(self, contract: UniversalContract):
        """Add a contract to the context"""
        if self.contract_registry is None:
            self.contract_registry = ContractRegistry()
        self.contract_registry.register_contract(contract)

    def get_contracts_for_phase(self, phase_name: str) -> List[UniversalContract]:
        """Get all contracts for a phase"""
        if not self.contract_registry:
            return []

        # Map phase names to agent roles
        phase_agent_map = {
            "requirements": ["requirement_analyst"],
            "design": ["solution_architect", "ux_designer"],
            "implementation": ["backend_developer", "frontend_developer"],
            "testing": ["qa_engineer"],
            "deployment": ["devops_engineer"]
        }

        agents = phase_agent_map.get(phase_name, [])
        contracts = []
        for agent in agents:
            contracts.extend(
                self.contract_registry.get_contracts_for_agent(agent, role="provider")
            )
        return contracts

    def add_contract_verification(
        self,
        phase_name: str,
        contract_id: str,
        verification: VerificationResult
    ):
        """Store contract verification result"""
        phase_result = self.workflow.get_phase_result(phase_name)
        if phase_result:
            if not hasattr(phase_result, 'contract_verifications'):
                phase_result.contract_verifications = {}
            phase_result.contract_verifications[contract_id] = verification
```

**Lines Changed:** ~50

---

### 2. team_execution_v2_split_mode.py

**Modifications:**
- Initialize ContractRegistry
- Pass contracts to phase execution
- Verify contracts after phase completion

```python
# In TeamExecutionEngineV2SplitMode class

def __init__(self, ...):
    # ... existing init ...

    # NEW: Initialize contract registry
    self.contract_registry = ContractRegistry()

async def execute_phase(
    self,
    phase_name: str,
    checkpoint: Optional[TeamExecutionContext] = None,
    requirement: Optional[str] = None,
    progress_callback: Optional[callable] = None
) -> TeamExecutionContext:
    # ... existing code ...

    # NEW: Get contracts for this phase
    if checkpoint and checkpoint.contract_registry:
        phase_contracts = checkpoint.contract_registry.get_contracts_for_phase(phase_name)
        logger.info(f"Phase {phase_name} has {len(phase_contracts)} contracts to fulfill")
    else:
        phase_contracts = []

    # ... execute phase ...

    # NEW: Verify contracts after execution
    for contract in phase_contracts:
        if contract.lifecycle_state == ContractLifecycle.FULFILLED:
            artifacts = self._extract_artifacts_for_contract(contract, execution_result)
            verification = self.contract_registry.verify_contract_fulfillment(
                contract.contract_id,
                artifacts
            )

            # Store verification
            context.add_contract_verification(phase_name, contract.contract_id, verification)

            # Handle blocking contracts
            if not verification.passed and contract.is_blocking:
                logger.error(f"BLOCKING contract {contract.contract_id} failed verification!")
                context.checkpoint_metadata.quality_gate_passed = False
                # Optionally halt workflow

    return context
```

**Lines Changed:** ~100

---

### 3. persona_executor_v2.py

**Modifications:**
- Accept contracts in execution context
- Build prompts with contract specifications
- Track contract fulfillment

```python
# In PersonaExecutorV2 class

def _build_persona_prompt(
    self,
    persona_id: str,
    requirement: str,
    contract: Optional[Dict[str, Any]],
    context: Dict[str, Any]
) -> str:
    # ... existing prompt building ...

    # NEW: Add contract specification if present
    if contract:
        prompt_parts.append("\n## 🎯 Your Contract\n\n")
        prompt_parts.append(f"**Contract ID:** {contract.get('contract_id')}\n")
        prompt_parts.append(f"**Contract Type:** {contract.get('contract_type')}\n\n")

        prompt_parts.append("### Specification\n")
        prompt_parts.append("```json\n")
        prompt_parts.append(json.dumps(contract.get('specification', {}), indent=2))
        prompt_parts.append("\n```\n\n")

        prompt_parts.append("### Acceptance Criteria\n")
        for criterion in contract.get('acceptance_criteria', []):
            prompt_parts.append(f"- **{criterion['criterion']}**: ")
            prompt_parts.append(f"{criterion.get('description', '')}\n")
            if 'threshold' in criterion:
                prompt_parts.append(f"  Threshold: {criterion['threshold']}\n")

        if contract.get('is_blocking'):
            prompt_parts.append("\n⚠️ **This contract is BLOCKING**: ")
            prompt_parts.append("The workflow will halt if acceptance criteria are not met.\n")

    return "\n".join(prompt_parts)
```

**Lines Changed:** ~50

---

## Migration Strategy

### Phase 1: Foundation (Week 1)
- Create `contract_registry.py`
- Create `contract_aware_agent.py`
- Create validator base classes
- Add unit tests

### Phase 2: Core Integration (Week 2)
- Modify `team_execution_context.py`
- Modify `team_execution_v2_split_mode.py`
- Add contract tracking to phase execution
- Integration tests

### Phase 3: Agent Integration (Week 3)
- Modify `persona_executor_v2.py`
- Add contract-aware prompts
- Implement basic validators (UX, API)
- End-to-end tests

### Phase 4: Advanced Features (Week 4)
- Add negotiation support
- Add contract versioning
- Add more validators (security, performance)
- Performance optimization

### Phase 5: Production Rollout (Week 5)
- Documentation
- Training materials
- Gradual rollout to non-critical contracts
- Monitoring and iteration

---

## Testing Strategy

### Unit Tests
```python
# test_contract_registry.py

def test_contract_registration():
    registry = ContractRegistry()
    contract = UniversalContract(
        contract_id="TEST_001",
        contract_type="TEST",
        name="Test Contract"
    )
    registry.register_contract(contract)
    assert registry.get_contract("TEST_001") == contract

def test_dependency_resolution():
    registry = ContractRegistry()
    # Create contracts with dependencies
    # Verify executable contracts are correctly identified
```

### Integration Tests
```python
# test_contract_workflow.py

async def test_phase_with_contracts():
    # Create phase with contracts
    # Execute phase
    # Verify contracts fulfilled
    # Check verification results
```

### End-to-End Tests
```python
# test_full_workflow_with_contracts.py

async def test_full_sdlc_with_contracts():
    # Requirements phase creates UX contracts
    # Design phase creates API contracts
    # Implementation phase fulfills contracts
    # Verification happens at each stage
    # Assert all contracts verified
```

---

## Performance Considerations

1. **Contract Storage**: Use efficient data structures
2. **Dependency Graph**: Use NetworkX for efficient graph operations
3. **Validation**: Run validators in parallel where possible
4. **Caching**: Cache verification results
5. **Lazy Loading**: Load full contract specs only when needed

---

## Breaking Changes

1. **Phase Execution**: Now requires contracts
2. **Persona Context**: Must include contract specifications
3. **Quality Gates**: Based on contract verification, not just code quality
4. **Workflow State**: Must include ContractRegistry

**Migration Path:**
- Make contracts optional initially
- Gradual adoption per phase
- Feature flags for contract enforcement

---

## New API Methods Implementation

As part of Phase 1 corrections, the ContractRegistry API has been expanded with additional methods. Here's implementation guidance for each:

### 1. can_execute_contract()

```python
def can_execute_contract(self, contract_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if contract can execute (dependencies satisfied).

    Returns:
        (can_execute, reason_if_not)
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        return False, f"Contract {contract_id} not found"

    # Check lifecycle state
    if contract.lifecycle_state != ContractLifecycle.ACCEPTED:
        return False, f"Contract not in ACCEPTED state (currently: {contract.lifecycle_state.value})"

    # Check dependencies
    for dep_id in contract.depends_on:
        dep_contract = self.contracts.get(dep_id)
        if not dep_contract:
            return False, f"Dependency {dep_id} not found"

        if dep_contract.lifecycle_state != ContractLifecycle.VERIFIED:
            return False, f"Dependency {dep_id} not verified (state: {dep_contract.lifecycle_state.value})"

    return True, None
```

### 2. get_contracts_blocked_by()

```python
def get_contracts_blocked_by(self, contract_id: str) -> List[str]:
    """
    Get contracts blocked by this contract (inverse of get_blocked_contracts).
    Alias for get_blocked_contracts() for API consistency.
    """
    return self.get_blocked_contracts(contract_id)
```

### 3. get_execution_plan()

```python
@dataclass
class ExecutionPlan:
    """Topologically sorted execution plan"""
    phases: List[List[str]]  # Each phase is a list of contract IDs that can run in parallel
    total_contracts: int
    estimated_duration_minutes: int = 0

def get_execution_plan(self) -> ExecutionPlan:
    """
    Generate topologically sorted execution plan for all accepted contracts.
    Groups contracts into phases where contracts in the same phase can execute in parallel.
    """
    # Get all accepted contracts
    accepted_contracts = [
        cid for cid, c in self.contracts.items()
        if c.lifecycle_state == ContractLifecycle.ACCEPTED
    ]

    # Create subgraph of accepted contracts
    subgraph = self.dependency_graph.subgraph(accepted_contracts)

    # Topological sort to get execution levels
    phases = []
    remaining = set(accepted_contracts)

    while remaining:
        # Find contracts with no dependencies in remaining set
        ready = [
            cid for cid in remaining
            if all(
                dep not in remaining
                for dep in self.contracts[cid].depends_on
            )
        ]

        if not ready:
            # Circular dependency detected
            logger.error(f"Circular dependency detected in contracts: {remaining}")
            break

        phases.append(ready)
        remaining -= set(ready)

    return ExecutionPlan(
        phases=phases,
        total_contracts=len(accepted_contracts)
    )
```

### 4. log_contract_warning()

```python
@dataclass
class ContractWarning:
    """Non-blocking warning for a contract"""
    warning_id: str
    contract_id: str
    severity: str  # "low", "medium", "high"
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

def log_contract_warning(
    self,
    contract_id: str,
    warning: ContractWarning
) -> None:
    """
    Log non-blocking warning for contract.
    Warnings don't prevent verification but should be reviewed.
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Store warning in contract metadata
    if 'warnings' not in contract.metadata:
        contract.metadata['warnings'] = []

    contract.metadata['warnings'].append(asdict(warning))

    logger.warning(
        f"Contract {contract_id} warning [{warning.severity}]: {warning.message}"
    )
```

### 5. handle_late_breach()

```python
@dataclass
class ContractBreach:
    """Details of a contract breach"""
    breach_id: str
    contract_id: str
    discovered_at: datetime
    criterion_id: str
    failure_message: str
    severity: str  # "critical", "major", "minor"
    evidence: Dict[str, Any]

@dataclass
class BreachResolution:
    """Resolution of a contract breach"""
    breach_id: str
    resolution_type: str  # "fixed", "waived", "escalated"
    resolved_at: datetime
    resolved_by: str
    notes: str

def handle_late_breach(
    self,
    contract_id: str,
    breach: ContractBreach
) -> BreachResolution:
    """
    Handle breach discovered after initial verification.
    This handles cases where issues are found in production or during later phases.
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Store breach in contract metadata
    if 'breaches' not in contract.metadata:
        contract.metadata['breaches'] = []

    contract.metadata['breaches'].append(asdict(breach))

    # Update contract state based on severity
    if breach.severity == "critical" and contract.is_blocking:
        self.update_contract_state(contract_id, ContractLifecycle.BREACHED)
        logger.error(f"CRITICAL breach in contract {contract_id}: {breach.failure_message}")

        # Block dependent contracts
        blocked = self.get_contracts_blocked_by(contract_id)
        logger.error(f"Blocking {len(blocked)} dependent contracts")

    return BreachResolution(
        breach_id=breach.breach_id,
        resolution_type="escalated",  # Default to escalation
        resolved_at=datetime.utcnow(),
        resolved_by="system",
        notes=f"Late breach detected: {breach.failure_message}"
    )
```

### 6. negotiate_contract()

```python
@dataclass
class ContractChange:
    """Proposed change to a contract"""
    field_path: str  # e.g., "specification.response_time.p95_ms"
    old_value: Any
    new_value: Any
    rationale: str

@dataclass
class ContractNegotiation:
    """Contract negotiation session"""
    negotiation_id: str
    contract_id: str
    proposed_changes: List[ContractChange]
    proposer: str
    status: str  # "pending", "accepted", "rejected"
    created_at: datetime = field(default_factory=datetime.utcnow)

def negotiate_contract(
    self,
    contract_id: str,
    changes: List[ContractChange]
) -> ContractNegotiation:
    """
    Initiate contract negotiation with proposed changes.
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Can only negotiate if PROPOSED or NEGOTIATING
    if contract.lifecycle_state not in [
        ContractLifecycle.PROPOSED,
        ContractLifecycle.NEGOTIATING
    ]:
        raise ValueError(
            f"Cannot negotiate contract in {contract.lifecycle_state.value} state"
        )

    # Create negotiation session
    negotiation = ContractNegotiation(
        negotiation_id=str(uuid.uuid4()),
        contract_id=contract_id,
        proposed_changes=changes,
        proposer="consumer",  # Or pass as parameter
        status="pending"
    )

    # Store in contract metadata
    if 'negotiations' not in contract.metadata:
        contract.metadata['negotiations'] = []

    contract.metadata['negotiations'].append(asdict(negotiation))

    # Update state
    self.update_contract_state(contract_id, ContractLifecycle.NEGOTIATING)

    logger.info(f"Negotiation {negotiation.negotiation_id} initiated for contract {contract_id}")

    return negotiation

def accept_negotiation(self, negotiation_id: str) -> UniversalContract:
    """Accept negotiated contract changes"""
    # Find contract with this negotiation
    for contract in self.contracts.values():
        negotiations = contract.metadata.get('negotiations', [])
        for neg in negotiations:
            if neg['negotiation_id'] == negotiation_id:
                # Apply changes
                for change in neg['proposed_changes']:
                    # Apply change to contract (simplified)
                    logger.info(f"Applying change: {change['field_path']}")

                # Update negotiation status
                neg['status'] = 'accepted'

                # Update contract state
                self.update_contract_state(
                    contract.contract_id,
                    ContractLifecycle.ACCEPTED
                )

                return contract

    raise ValueError(f"Negotiation {negotiation_id} not found")

def reject_negotiation(self, negotiation_id: str, reason: str) -> None:
    """Reject negotiated contract changes"""
    for contract in self.contracts.values():
        negotiations = contract.metadata.get('negotiations', [])
        for neg in negotiations:
            if neg['negotiation_id'] == negotiation_id:
                neg['status'] = 'rejected'
                neg['rejection_reason'] = reason

                # Revert to PROPOSED
                self.update_contract_state(
                    contract.contract_id,
                    ContractLifecycle.PROPOSED
                )

                logger.info(f"Negotiation {negotiation_id} rejected: {reason}")
                return

    raise ValueError(f"Negotiation {negotiation_id} not found")
```

### 7. amend_contract() and update_contract_with_clarification()

```python
@dataclass
class ContractAmendment:
    """Amendment to an existing contract"""
    amendment_id: str
    contract_id: str
    changes: List[ContractChange]
    reason: str
    requires_reacceptance: bool
    amended_by: str
    amended_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ContractClarification:
    """Clarification added to contract without changing criteria"""
    clarification_id: str
    contract_id: str
    field: str
    clarification_text: str
    added_by: str
    added_at: datetime = field(default_factory=datetime.utcnow)

def amend_contract(
    self,
    contract_id: str,
    amendment: ContractAmendment
) -> UniversalContract:
    """
    Amend an existing contract with changes.
    May require re-acceptance from consumers.
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Store amendment
    if 'amendments' not in contract.metadata:
        contract.metadata['amendments'] = []

    contract.metadata['amendments'].append(asdict(amendment))

    # Apply changes (simplified - would need deep path resolution)
    for change in amendment.changes:
        logger.info(f"Amending {change.field_path}: {change.old_value} → {change.new_value}")

    # Increment contract version
    if hasattr(contract, 'contract_version'):
        contract.contract_version += 1

    # If requires reacceptance, revert to PROPOSED
    if amendment.requires_reacceptance:
        self.update_contract_state(contract_id, ContractLifecycle.PROPOSED)
        logger.info(f"Contract {contract_id} requires re-acceptance after amendment")

    return contract

def update_contract_with_clarification(
    self,
    contract_id: str,
    clarification: ContractClarification
) -> UniversalContract:
    """
    Add clarification to contract without changing acceptance criteria.
    Does not require re-acceptance.
    """
    contract = self.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Store clarification
    if 'clarifications' not in contract.metadata:
        contract.metadata['clarifications'] = []

    contract.metadata['clarifications'].append(asdict(clarification))

    logger.info(f"Added clarification to contract {contract_id}: {clarification.clarification_text}")

    return contract
```

---

## Validator Runtime Requirements

All validators must declare their runtime requirements and handle failures gracefully. This section outlines requirements for each validator type.

### General Requirements

All validators must:

1. **Declare dependencies**: List all required packages, tools, and services
2. **Handle timeouts**: Enforce maximum execution time
3. **Sandbox execution**: Run in isolated environment for security validators
4. **Return structured results**: Use CriterionResult format
5. **Log appropriately**: Use structured logging

### Base Validator Implementation

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidatorMetadata:
    """Metadata about validator requirements"""
    name: str
    version: str
    dependencies: List[str]  # ["selenium>=4.0.0", "axe-selenium-python"]
    runtime_requirements: List[str]  # ["chrome-driver", "headless-browser"]
    timeout_seconds: int = 300
    requires_network: bool = False
    requires_sandboxing: bool = False


class BaseValidator(ABC):
    """Base class for all validators"""

    @property
    @abstractmethod
    def metadata(self) -> ValidatorMetadata:
        """Return validator metadata"""
        pass

    async def validate(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """
        Validate with timeout enforcement.
        Subclasses should implement validate_impl().
        """
        try:
            return await asyncio.wait_for(
                self.validate_impl(criterion, context),
                timeout=self.metadata.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Validator {self.metadata.name} timed out after {self.metadata.timeout_seconds}s")
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="timeout",
                expected_value="completion",
                message=f"Validation timed out after {self.metadata.timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Validator {self.metadata.name} failed: {e}")
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="error",
                expected_value="success",
                message=f"Validation failed: {str(e)}"
            )

    @abstractmethod
    async def validate_impl(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """Implement validation logic in subclasses"""
        pass
```

### Validator-Specific Requirements

#### OpenAPI Validator

**Dependencies:**
- `openapi-core>=0.18.0`
- `pyyaml>=6.0`
- `requests`

**Runtime Requirements:**
- API endpoint must be accessible
- OpenAPI spec file must exist

**Example Implementation:** See `PROTOCOL_CORRECTIONS.md` Section 4.

#### Accessibility Validator

**Dependencies:**
- `selenium>=4.0.0`
- `axe-selenium-python>=2.1.0`

**Runtime Requirements:**
- Chrome/Chromium browser installed
- chromedriver in PATH
- Headless mode for CI

**Timeouts:**
- Page load: 30 seconds
- axe scan: 60 seconds

**Example Implementation:** See `PROTOCOL_CORRECTIONS.md` Section 4.

#### Performance Validator

**Dependencies:**
- `locust>=2.0.0`

**Runtime Requirements:**
- Separate Locust process
- Results written to JSON file
- Target system must be accessible

**Example Implementation:** See `PROTOCOL_CORRECTIONS.md` Section 4.

#### Security Validators (Bandit, Snyk, ZAP)

**Dependencies:**
- Varies by validator

**Runtime Requirements:**
- **Sandboxing**: Must run in Docker container
- **No network access**: Use `--network none`
- **Read-only filesystem**: Use `--read-only`
- **Non-root user**: Use `--user nobody`
- **Timeout enforcement**: Max 5 minutes
- **Log sanitization**: Remove secrets before storing

**Example Implementation:** See `PROTOCOL_CORRECTIONS.md` Section 4.

---

## Event Handling

Contract lifecycle events enable real-time notification and integration with external systems.

### Event Types

All contract state transitions emit events:

```python
# Import canonical event definitions
from contract_protocol.types import (
    ContractEvent,
    ContractProposedEvent,
    ContractAcceptedEvent,
    ContractFulfilledEvent,
    ContractVerifiedEvent,
    ContractBreachedEvent
)
```

### Event Handler Interface

```python
from abc import ABC, abstractmethod
from typing import Callable, List

class EventHandler(ABC):
    """Base class for contract event handlers"""

    @abstractmethod
    async def handle_event(self, event: ContractEvent) -> None:
        """Handle a contract event"""
        pass


class WebSocketEventHandler(EventHandler):
    """Send events over WebSocket"""

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.ws = None

    async def handle_event(self, event: ContractEvent) -> None:
        """Send event over WebSocket"""
        if not self.ws:
            self.ws = await websockets.connect(self.websocket_url)

        await self.ws.send(json.dumps({
            'event_type': event.event_type,
            'contract_id': event.contract_id,
            'timestamp': event.timestamp.isoformat(),
            'metadata': event.metadata
        }))


class LoggingEventHandler(EventHandler):
    """Log events to structured logger"""

    async def handle_event(self, event: ContractEvent) -> None:
        logger.info(
            f"Contract event: {event.event_type}",
            extra={
                'contract_id': event.contract_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat()
            }
        )
```

### Integrating Event Handlers into ContractRegistry

```python
class ContractRegistry:
    def __init__(self):
        # ... existing init ...
        self.event_handlers: List[EventHandler] = []

    def register_event_handler(self, handler: EventHandler):
        """Register an event handler"""
        self.event_handlers.append(handler)
        logger.info(f"Registered event handler: {handler.__class__.__name__}")

    async def emit_event(self, event: ContractEvent):
        """Emit event to all registered handlers"""
        for handler in self.event_handlers:
            try:
                await handler.handle_event(event)
            except Exception as e:
                logger.error(f"Event handler {handler.__class__.__name__} failed: {e}")

    async def update_contract_state(
        self,
        contract_id: str,
        new_state: ContractLifecycle
    ):
        """Update state and emit event"""
        contract = self.contracts[contract_id]
        old_state = contract.lifecycle_state
        contract.lifecycle_state = new_state

        # Emit appropriate event
        if new_state == ContractLifecycle.PROPOSED:
            event = ContractProposedEvent(
                event_id=str(uuid.uuid4()),
                event_type="contract_proposed",
                contract_id=contract_id,
                proposer=contract.provider_agent,
                contract=contract
            )
        elif new_state == ContractLifecycle.ACCEPTED:
            event = ContractAcceptedEvent(
                event_id=str(uuid.uuid4()),
                event_type="contract_accepted",
                contract_id=contract_id,
                acceptor="system"  # Or track actual acceptor
            )
        # ... other event types ...

        await self.emit_event(event)
```

### Usage Example

```python
# Set up event handlers
registry = ContractRegistry()

# Add WebSocket handler for real-time UI updates
ws_handler = WebSocketEventHandler("ws://localhost:8000/contracts/events")
registry.register_event_handler(ws_handler)

# Add logging handler for audit trail
log_handler = LoggingEventHandler()
registry.register_event_handler(log_handler)

# Now all state transitions will emit events
await registry.update_contract_state("CONTRACT_001", ContractLifecycle.VERIFIED)
```

---

## Caching and Memoization

Contract verification can be expensive. Implement caching to avoid redundant validations.

### Cache Key Generation

Contracts and verification results include `cache_key()` methods:

```python
# From UniversalContract
def cache_key(self) -> str:
    """Generate deterministic cache key"""
    key_components = [
        self.contract_id,
        self.contract_type,
        str(self.contract_version),
        self.schema_version,
        json.dumps(self.acceptance_criteria, sort_keys=True, default=str)
    ]
    return hashlib.sha256("|".join(key_components).encode()).hexdigest()


# From VerificationResult
def cache_key(self) -> str:
    """Generate cache key including validator versions"""
    key_components = [
        self.contract_id,
        json.dumps(self.validator_versions, sort_keys=True),
        json.dumps(self.environment, sort_keys=True)
    ]
    return hashlib.sha256("|".join(key_components).encode()).hexdigest()
```

### Cache Implementation

```python
from typing import Optional
import redis
import pickle

class VerificationCache:
    """Cache for verification results"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.ttl_seconds = 86400  # 24 hours

    def get(self, cache_key: str) -> Optional[VerificationResult]:
        """Get cached verification result"""
        data = self.redis_client.get(f"verification:{cache_key}")
        if data:
            return pickle.loads(data)
        return None

    def set(self, cache_key: str, result: VerificationResult):
        """Cache verification result"""
        data = pickle.dumps(result)
        self.redis_client.setex(
            f"verification:{cache_key}",
            self.ttl_seconds,
            data
        )

    def invalidate(self, contract_id: str):
        """Invalidate all cache entries for a contract"""
        pattern = f"verification:*{contract_id}*"
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)


# Integrate into ContractRegistry
class ContractRegistry:
    def __init__(self, cache: Optional[VerificationCache] = None):
        # ... existing init ...
        self.cache = cache or VerificationCache()

    async def verify_contract_fulfillment(
        self,
        contract_id: str,
        artifacts: Dict[str, Any]
    ) -> VerificationResult:
        """Verify with caching"""
        contract = self.contracts[contract_id]

        # Generate cache key
        cache_key = contract.cache_key()

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Using cached verification for {contract_id}")
            return cached_result

        # Perform validation
        result = await self._perform_validation(contract_id, artifacts)

        # Cache result
        self.cache.set(cache_key, result)

        return result
```

### Determinism for LLM Validators

When using LLM-driven validators, include model version and temperature in cache key:

```python
@dataclass
class LLMValidatorContext:
    """Context for LLM-driven validation"""
    model: str  # "claude-3-opus-20240229"
    temperature: float  # 0.0 for determinism
    prompt_version: str  # "1.0.0"

# Include in VerificationResult
verification_result.environment = {
    "llm_model": "claude-3-opus-20240229",
    "llm_temperature": "0.0",
    "prompt_version": "1.0.0"
}
```

---

## Integration with Existing Systems

### Adapter Pattern for Existing ContractManager

If your system already has a `ContractManager`, use an adapter to avoid duplication:

```python
from typing import Dict, Any

class UniversalContractAdapter:
    """Adapter wrapping existing ContractManager"""

    def __init__(self, contract_manager: ContractManager):
        self.contract_manager = contract_manager
        self.universal_contracts: Dict[str, UniversalContract] = {}

    def register_contract(self, contract: UniversalContract) -> str:
        """Register universal contract via existing manager"""
        # Convert to legacy format
        legacy_contract = self._to_legacy_contract(contract)

        # Register with existing manager
        contract_id = self.contract_manager.add_contract(legacy_contract)

        # Store universal contract
        self.universal_contracts[contract_id] = contract

        return contract_id

    def _to_legacy_contract(self, contract: UniversalContract) -> dict:
        """Convert universal contract to legacy format"""
        return {
            "id": contract.contract_id,
            "type": contract.contract_type,
            "requirements": [c.description for c in contract.acceptance_criteria],
            "provider": contract.provider_agent,
            "consumers": contract.consumer_agents,
            "blocking": contract.is_blocking
        }

    def _from_legacy_contract(self, legacy: dict) -> UniversalContract:
        """Convert legacy contract to universal format"""
        return UniversalContract(
            contract_id=legacy["id"],
            contract_type=legacy["type"],
            name=legacy.get("name", legacy["id"]),
            description=legacy.get("description", ""),
            provider_agent=legacy.get("provider", ""),
            consumer_agents=legacy.get("consumers", []),
            is_blocking=legacy.get("blocking", True),
            acceptance_criteria=[
                AcceptanceCriterion(
                    criterion_id=str(uuid.uuid4()),
                    description=req,
                    validator_type="legacy_validator",
                    validation_config={}
                )
                for req in legacy.get("requirements", [])
            ]
        )
```

### Composition Pattern

Alternatively, use composition to layer ACP on top of existing system:

```python
class HybridContractRegistry:
    """
    Hybrid registry supporting both legacy and ACP contracts.
    Uses composition instead of inheritance.
    """

    def __init__(self, legacy_manager: ContractManager):
        self.legacy_manager = legacy_manager  # Low-level storage
        self.acp_registry = ContractRegistry()  # High-level ACP

    def register_contract(self, contract: UniversalContract):
        """Register in both systems"""
        # Register in ACP
        self.acp_registry.register_contract(contract)

        # Also register in legacy system for backward compatibility
        legacy_contract = self._to_legacy(contract)
        self.legacy_manager.add_contract(legacy_contract)

    def get_contract(self, contract_id: str) -> Optional[UniversalContract]:
        """Get from ACP first, fall back to legacy"""
        # Try ACP first
        contract = self.acp_registry.get_contract(contract_id)
        if contract:
            return contract

        # Fall back to legacy
        legacy = self.legacy_manager.get_contract(contract_id)
        if legacy:
            return self._from_legacy(legacy)

        return None
```

### Migration Strategy

```python
class GradualMigration:
    """Helper for gradual migration to ACP"""

    def __init__(self):
        self.legacy_contracts = set()
        self.acp_contracts = set()

    def is_migrated(self, contract_id: str) -> bool:
        """Check if contract has been migrated to ACP"""
        return contract_id in self.acp_contracts

    def migrate_contract(
        self,
        contract_id: str,
        legacy_manager: ContractManager,
        acp_registry: ContractRegistry
    ):
        """Migrate single contract from legacy to ACP"""
        legacy = legacy_manager.get_contract(contract_id)
        if not legacy:
            raise ValueError(f"Legacy contract {contract_id} not found")

        # Convert to ACP
        acp_contract = self._convert_to_acp(legacy)

        # Register in ACP
        acp_registry.register_contract(acp_contract)

        # Track migration
        self.legacy_contracts.add(contract_id)
        self.acp_contracts.add(contract_id)

        logger.info(f"Migrated contract {contract_id} to ACP")
```

---

## Next Steps

1. Review this implementation plan
2. Create ticket/task breakdown
3. Set up development branch
4. Begin Phase 1 implementation
5. Establish CI/CD for contract tests

See **VALIDATOR_FRAMEWORK.md** for validator implementation details.
