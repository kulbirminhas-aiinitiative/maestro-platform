# ADR-005: Persona University - Evolution & Accreditation System

## Status
Accepted

## Date
2025-12-11

## Context
The Maestro Hive platform needs a formalized system for training, evaluating, and accrediting AI agents. Currently, agents are either "born" with static capabilities or evolve through ad-hoc mechanisms. We need:

1. **Structured Learning**: Agents should follow curricula, not randomly acquire skills
2. **Objective Evaluation**: Performance must be measured with clear metrics
3. **Portable Trust**: Credentials should be cryptographically verifiable
4. **Integration**: Must work with existing Governance systems (Enforcer, Identity, Reputation)

## Decision
We will implement the **Persona University** system with four phases:

### Phase 1: Curriculum (Input)
- YAML-defined curricula with modules, skills, and exams
- Three types: Core (mandatory), Major (specialization), Electives
- Schema validation ensures consistency

### Phase 2: Simulator (Classroom)
- `UserSimulatorAgent` generates realistic exam scenarios
- `ExamSimulator` provides sandboxed execution environment
- Mocked event bus and tool outputs for safe testing
- Enforcer integration with strict exam policies

### Phase 3: Evaluation (Exam)
- Metrics: Accuracy, Efficiency, Safety, Creativity
- Grading scale: S-Tier (>98%), A-Tier (>90%), B-Tier (>80%), C-Tier (<80%)
- Zero-tolerance for governance violations during exams

### Phase 4: Accreditation (Diploma)
- Verifiable Credentials (VCs) signed with Ed25519 keys
- Integration with `IdentityManager` for cryptographic signing
- `CredentialStore` manages expiry, revocation, and persistence

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PersonaUniversityService                    │
├─────────────────────────────────────────────────────────────┤
│  - Manages curricula                                         │
│  - Schedules exams                                           │
│  - Issues credentials                                        │
│  - Coordinates with Governance systems                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│UserSimulator  │ │ExamSimulator  │ │CredentialStore│
│Agent          │ │               │ │               │
├───────────────┤ ├───────────────┤ ├───────────────┤
│- Scenario YAML│ │- Sandboxed env│ │- Issue VCs    │
│- Step prompts │ │- Mock tools   │ │- Verify/Revoke│
│- Evaluation   │ │- Enforcer     │ │- Persist      │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Integration Points

### With IdentityManager (MD-3118)
```python
# Credentials signed using existing identity infrastructure
signed_action = identity_manager.sign_action(
    agent_id="university_authority",
    action_type="credential_issued",
    payload=credential.to_dict()
)
```

### With ReputationEngine (MD-3118)
```python
# Exam results affect reputation
if results.passed:
    reputation_engine.record_event(agent_id, ReputationEvent.TEST_PASSED)
```

### With Enforcer (MD-3115/MD-3116)
```python
# Load strict policy for exam duration
enforcer.load_policy("config/governance/policy_exam_strict.yaml")
```

### With GovernancePersistence (MD-3118)
```python
# Extended with credential methods
persistence.save_credential(credential_id, data)
persistence.load_credential(credential_id)
```

## Consequences

### Positive
- Clear progression path for agents
- Objective, measurable skill verification
- Cryptographic trust enables federated agent systems
- Reuses existing governance infrastructure

### Negative
- Additional complexity in agent lifecycle
- Exam scenarios require maintenance
- Credential expiry requires renewal workflows

### Risks
- Time dilation in simulators is complex (deferred to v2)
- Mock API fidelity may not match production
- Exam cheating prevention needs deterministic seeds

## Acceptance Criteria Mapping

| AC | Description | Component |
|----|-------------|-----------|
| AC-1 | Curriculum YAML loading | PersonaUniversityService |
| AC-2 | Credential-gated hiring | CredentialStore |
| AC-3 | Exam in simulator | ExamSimulator + UserSimulatorAgent |
| AC-4 | Grading metrics | ExamSimulator |
| AC-5 | VC issuance on pass | CredentialStore |
| AC-6 | Ed25519 signature | IdentityManager integration |
| AC-7 | Reputation update | ReputationEngine integration |
| AC-8 | Violation = failure | Enforcer integration |
| AC-9 | Credential persistence | GovernancePersistence |
| AC-10 | Frontend dashboard | Future work |

## References
- MD-3127: JIRA Epic
- MD-3118: Governance Layer (IdentityManager, ReputationEngine, Persistence)
- MD-3115/MD-3116: Enforcer Middleware
- W3C Verifiable Credentials Data Model
