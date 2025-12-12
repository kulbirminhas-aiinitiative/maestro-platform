# JIRA TICKET: MD-3127

**Type:** Epic
**Summary:** Persona University: The Evolution & Accreditation System
**Priority:** High
**Component:** Core / Persona Engine
**Status:** To Do
**Last Updated:** 2025-12-11

---

## 0. Review Notes (2025-12-11)

### Strengths
- **Clear Vision**: The "Foundry builds, University trains" metaphor is compelling and easy to understand
- **Well-Structured Phases**: Four distinct phases (Curriculum → Simulator → Evaluation → Accreditation) provide a clear learning pipeline
- **Cryptographic Trust**: Using Verifiable Credentials aligns with modern identity standards

### Critical Gaps Identified
1. **No Integration with Existing Systems**: How does this integrate with:
   - `ReputationEngine` (MD-3118) - Should exam performance affect reputation?
   - `IdentityManager` (MD-3118) - Should credentials use the same Ed25519 signing?
   - `Enforcer` (MD-3115) - Already implemented, but "Strict Mode" not defined

2. **Missing Technical Specifications**:
   - No curriculum YAML schema defined
   - No database schema for exam history
   - No API contracts (REST/gRPC endpoints)
   - No VC format specification (W3C VC standard?)

3. **Frontend Files Don't Exist**: Referenced files not found:
   - `PersonaGrowthDashboard.tsx` ❌
   - `TraitEvolutionDashboard.tsx` ❌

### Key Challenges
| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| Time Dilation complexity | High | Start with 1:1 time, add dilation in v2 |
| Mock API fidelity | High | Use contract-based mocking (OpenAPI) |
| Credential revocation | Medium | Add expiry + revocation registry |
| Exam cheating prevention | Medium | Use deterministic seeds, hash verification |
| Cross-system integration | High | Define clear event contracts first |

### Recommended Priority Order
1. Define Curriculum YAML schema (foundation)
2. Build `PersonaUniversityService` (backend first)
3. Integrate with existing `IdentityManager` for credential signing
4. Simple Simulator (no time dilation initially)
5. Frontend dashboard (last)

---

## 1. Vision: From "Foundry" to "University"
We are merging the existing "Persona Evolution" concepts (Traits, Skills, Growth) into a formalized **Persona University**. This is not just about tracking stats; it is about **active curriculum management, rigorous testing, and cryptographic accreditation**.

The "Foundry" builds the agent (Birth). The "University" trains the agent (Life).

## 2. The Architecture of Learning

### Phase 1: The Curriculum (Input)
*   **Concept:** Agents don't just "learn"; they follow a syllabus.
*   **Components:**
    *   **Core Curriculum:** Mandatory for all agents (e.g., "Constitution 101", "JSON Formatting").
    *   **Major/Specialization:** Role-specific paths (e.g., "Python Backend Engineering", "React Frontend Design").
    *   **Electives:** Optional skills (e.g., "Creative Writing", "Advanced SQL Optimization").

### Phase 2: The Simulator (The Classroom)
*   **Concept:** Learning happens in a safe, sandboxed environment, not in production.
*   **Mechanism:**
    *   **The Matrix:** A mocked environment where the agent interacts with "Ghost Users" and "Mock APIs".
    *   **Scenarios:** Pre-defined challenges (e.g., "The database is down, fix it without losing data").
    *   **Enforcer Integration:** The Enforcer (MD-3115) uses policy override during exams to fail agents instantly for violations.
    *   **User Simulator:** `UserSimulatorAgent` generates realistic user prompts from scenario scripts.

### Phase 3: Evaluation & Grading (The Exam)
*   **Concept:** Performance is measured objectively.
*   **Metrics:**
    *   **Accuracy:** Did the code compile? Did the tests pass?
    *   **Efficiency:** Token usage, Latency, Cost.
    *   **Safety:** Number of governance violations (must be 0 for certification).
    *   **Creativity:** (Optional) Novelty of the solution (judged by LLM).
*   **Grading Scale:**
    *   **S-Tier (Master):** >98% score. Allowed to run in Production without supervision.
    *   **A-Tier (Expert):** >90% score. Production allowed with Auditor oversight.
    *   **B-Tier (Competent):** >80% score. Limited Production access.
    *   **C-Tier (Apprentice):** <80% score. Sandbox only.

### Phase 4: Accreditation (The Diploma)
*   **Concept:** Trust is portable and cryptographic.
*   **Mechanism:**
    *   **Verifiable Credentials (VC):** When an agent passes an exam, the University issues a VC signed by the `University_Authority_Key`.
    *   **The Resume:** The agent's `metadata` stores these VCs.
    *   **Hiring:** When a user asks for a "Python Expert", the Orchestrator checks for the `Python_Level_5` credential.

## 3. Implementation Plan

### Step 1: Merge Frontend Concepts
*   **Retain:** `SkillLevel`, `Milestone`, `GrowthMetrics` from `PersonaGrowthDashboard.tsx`.
*   **Retain:** `Trait`, `DecayResult` from `TraitEvolutionDashboard.tsx`.
*   **Enhance:** Add `Certifications` and `ExamHistory` to the data model.

### Step 2: Build the Backend (The Dean)
*   **New Service:** `PersonaUniversityService`.
*   **Responsibilities:**
    *   Manage Curriculums (YAML definitions).
    *   Schedule Exams.
    *   Issue Credentials.

### Step 3: Build the Simulator (The Matrix)
*   **New Engine:** `SimulationEngine` (extends `TeamExecutionEngine`).
*   **Features:**
    *   Mocked Event Bus.
    *   Mocked Tool Outputs.
    *   Time dilation (run 1 hour of simulation in 1 minute).

## 4. Acceptance Criteria

### Core Functionality
*   [ ] **AC-1 (Curriculum):** A curriculum can be defined in YAML and loaded by `PersonaUniversityService`
*   [ ] **AC-2 (Enrollment):** A "Fresh" agent cannot be hired for a "Senior" role without credentials
*   [ ] **AC-3 (Exam):** An agent can take a "Python 101" exam in the simulator
*   [ ] **AC-4 (Grading):** Exam results include Accuracy, Efficiency, and Safety scores
*   [ ] **AC-5 (Credential):** Upon passing (>80%), the agent receives a `Python_Novice` VC

### Integration
*   [ ] **AC-6 (Identity):** Credentials are signed using `IdentityManager` Ed25519 keys
*   [ ] **AC-7 (Reputation):** Exam pass/fail events update agent reputation (+10/-5 points)
*   [ ] **AC-8 (Enforcer):** Governance violations during exam result in instant failure

### Persistence & Frontend
*   [ ] **AC-9 (Storage):** Credentials survive system restart (use `GovernancePersistence`)
*   [ ] **AC-10 (Dashboard):** Frontend displays agent credentials and exam history

## 4.1 Integration with Existing Systems

### With `IdentityManager` (MD-3118)
```python
# Credential signing should use existing identity infrastructure
from maestro_hive.governance import IdentityManager

class PersonaUniversityService:
    def issue_credential(self, agent_id: str, credential_type: str) -> SignedCredential:
        # Use existing identity manager for signing
        action = self.identity_manager.sign_action(
            agent_id=agent_id,
            action_type="credential_issued",
            payload={"credential": credential_type, "issued_at": datetime.utcnow().isoformat()}
        )
        return SignedCredential(action)
```

### With `ReputationEngine` (MD-3118)
```python
# Exam results should affect reputation
class ExamGrader:
    def grade_exam(self, agent_id: str, results: ExamResults):
        if results.passed:
            self.reputation_engine.record_event(agent_id, ReputationEvent.TEST_PASSED)
        else:
            self.reputation_engine.record_event(agent_id, ReputationEvent.TEST_FAILED)
```

### With `Enforcer` (MD-3115)
```python
# Policy override for exams - any violation = instant fail
# NOTE: Enforcer doesn't support modes. Use load_policy() instead.
class ExamSimulator:
    def __init__(self, enforcer: Enforcer, default_policy_path: str):
        self.enforcer = enforcer
        self.default_policy_path = default_policy_path

    def run_exam(self, agent_id: str):
        # Load strict exam policy
        self.enforcer.load_policy("config/governance/policy_exam_strict.yaml")
        try:
            # Run exam with zero-tolerance policy...
            pass
        finally:
            # Restore original policy using the known default path
            self.enforcer.load_policy(self.default_policy_path)
```

## 4.2 Proposed Curriculum YAML Schema

```yaml
# curriculum/python_101.yaml
curriculum:
  id: python_101
  name: "Python 101: Fundamentals"
  type: "major"
  prerequisites: []

  modules:
    - id: syntax_basics
      name: "Syntax Basics"
      skills:
        - python_syntax
        - variable_types
      exam:
        type: "code_completion"
        time_limit_minutes: 30
        pass_threshold: 0.8

    - id: functions
      name: "Functions & Scope"
      skills:
        - function_definition
        - scope_rules
      exam:
        type: "bug_fix"
        time_limit_minutes: 45
        pass_threshold: 0.8

  certification:
    name: "Python_Novice"
    validity_days: 365  # Credentials expire
    revocable: true
```

## 4.3 UserSimulatorAgent Specification

The "Ghost Users" concept requires a concrete implementation to simulate user interactions during exams.

```python
# src/maestro_hive/university/user_simulator.py
"""
UserSimulatorAgent - Simulates user behavior for exam scenarios.

Replaces the vague "Ghost Users" concept with a concrete, scriptable component.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import yaml


@dataclass
class ScenarioStep:
    """A single step in an exam scenario."""
    step_id: int
    user_input: str                    # What the "user" says/requests
    expected_behavior: str             # What the agent should do
    success_criteria: List[str]        # How to evaluate success
    timeout_seconds: int = 300
    hints: List[str] = field(default_factory=list)


@dataclass
class ExamScenario:
    """Complete exam scenario definition."""
    scenario_id: str
    name: str
    description: str
    difficulty: str                    # easy, medium, hard, expert
    steps: List[ScenarioStep]
    max_total_time_minutes: int
    passing_score: float = 0.8


class UserSimulatorAgent:
    """
    Simulates user behavior for exam scenarios.

    Consumes scenario YAML files and generates natural language prompts
    to test the student agent in a controlled environment.
    """

    def __init__(self, scenario_path: str):
        """
        Initialize with a scenario file.

        Args:
            scenario_path: Path to scenario YAML file
        """
        with open(scenario_path, 'r') as f:
            data = yaml.safe_load(f)

        self.scenario = ExamScenario(
            scenario_id=data['scenario']['id'],
            name=data['scenario']['name'],
            description=data['scenario']['description'],
            difficulty=data['scenario']['difficulty'],
            max_total_time_minutes=data['scenario']['max_time_minutes'],
            passing_score=data['scenario'].get('passing_score', 0.8),
            steps=[
                ScenarioStep(
                    step_id=i,
                    user_input=step['user_input'],
                    expected_behavior=step['expected_behavior'],
                    success_criteria=step.get('success_criteria', []),
                    timeout_seconds=step.get('timeout_seconds', 300),
                    hints=step.get('hints', [])
                )
                for i, step in enumerate(data['scenario']['steps'])
            ]
        )
        self.current_step = 0
        self.start_time: Optional[datetime] = None
        self.step_results: List[Dict[str, Any]] = []

    def start_exam(self) -> str:
        """Start the exam and return the first prompt."""
        self.start_time = datetime.utcnow()
        self.current_step = 0
        return self.get_current_prompt()

    def get_current_prompt(self) -> str:
        """Get the current step's user prompt."""
        if self.current_step >= len(self.scenario.steps):
            return "[EXAM COMPLETE]"
        return self.scenario.steps[self.current_step].user_input

    def evaluate_response(self, agent_response: str) -> Dict[str, Any]:
        """
        Evaluate the agent's response against success criteria.

        Returns:
            Dict with 'passed', 'score', 'feedback' keys
        """
        step = self.scenario.steps[self.current_step]
        # In real implementation, use LLM to evaluate against criteria
        result = {
            'step_id': self.current_step,
            'passed': True,  # Placeholder - real impl uses LLM evaluation
            'score': 1.0,
            'feedback': 'Evaluation pending',
            'criteria_met': step.success_criteria
        }
        self.step_results.append(result)
        return result

    def advance_step(self) -> bool:
        """Move to next step. Returns False if exam is complete."""
        self.current_step += 1
        return self.current_step < len(self.scenario.steps)

    def get_final_score(self) -> float:
        """Calculate final exam score."""
        if not self.step_results:
            return 0.0
        total_score = sum(r['score'] for r in self.step_results)
        return total_score / len(self.step_results)

    def has_passed(self) -> bool:
        """Check if agent passed the exam."""
        return self.get_final_score() >= self.scenario.passing_score
```

### Example Scenario YAML

```yaml
# scenarios/python_debug_101.yaml
scenario:
  id: python_debug_101
  name: "Python Debugging Challenge"
  description: "Fix bugs in a Python function"
  difficulty: easy
  max_time_minutes: 30
  passing_score: 0.8

  steps:
    - user_input: |
        I have this Python function but it's not working:

        def calculate_average(numbers):
            total = 0
            for num in numbers:
                total += num
            return total / len(numbers)

        When I call calculate_average([]) it crashes. Can you fix it?
      expected_behavior: "Add check for empty list"
      success_criteria:
        - "Handles empty list without crashing"
        - "Returns 0 or None for empty list"
        - "Original functionality preserved"
      timeout_seconds: 180

    - user_input: "Great! Now can you add type hints to the function?"
      expected_behavior: "Add proper type annotations"
      success_criteria:
        - "Has List[float] or similar input type"
        - "Has float return type"
        - "Optional return type if None is returned"
      timeout_seconds: 120
```

## 4.4 CredentialStore Design

Manages Verifiable Credentials (VCs) with expiry, revocation, and persistence.

```python
# src/maestro_hive/university/credential_store.py
"""
CredentialStore - Manages Verifiable Credentials for agents.

Integrates with GovernancePersistence (MD-3118) for storage and
IdentityManager for cryptographic signing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import json
import logging

from maestro_hive.governance import (
    IdentityManager,
    GovernancePersistence,
    SignedAction,
)

logger = logging.getLogger(__name__)


class CredentialStatus(Enum):
    """Status of a credential."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class VerifiableCredential:
    """
    A Verifiable Credential issued by the University.

    Based on W3C VC Data Model (simplified).
    """
    credential_id: str
    agent_id: str
    credential_type: str           # e.g., "Python_Novice", "React_Expert"
    issuer: str = "PersonaUniversity"
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.ACTIVE

    # Exam context
    exam_id: Optional[str] = None
    exam_score: Optional[float] = None

    # Cryptographic proof
    signature: str = ""            # Ed25519 signature from IdentityManager

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if credential is currently valid."""
        if self.status != CredentialStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "credential_id": self.credential_id,
            "agent_id": self.agent_id,
            "credential_type": self.credential_type,
            "issuer": self.issuer,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "exam_id": self.exam_id,
            "exam_score": self.exam_score,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerifiableCredential":
        """Deserialize from dictionary."""
        return cls(
            credential_id=data["credential_id"],
            agent_id=data["agent_id"],
            credential_type=data["credential_type"],
            issuer=data.get("issuer", "PersonaUniversity"),
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=CredentialStatus(data.get("status", "active")),
            exam_id=data.get("exam_id"),
            exam_score=data.get("exam_score"),
            signature=data.get("signature", ""),
            metadata=data.get("metadata", {}),
        )


class CredentialStore:
    """
    Manages Verifiable Credentials for agents.

    Features:
    - Issue credentials with Ed25519 signatures
    - Check credential validity (expiry, revocation)
    - Revoke/suspend credentials
    - Query agent credentials
    - Persist to GovernancePersistence
    """

    STORAGE_KEY_PREFIX = "credentials"
    REVOCATION_REGISTRY_KEY = "credentials:revoked"

    def __init__(
        self,
        identity_manager: IdentityManager,
        persistence: GovernancePersistence,
        default_validity_days: int = 365,
    ):
        """
        Initialize the credential store.

        Args:
            identity_manager: For signing credentials
            persistence: For storing credentials
            default_validity_days: Default credential validity
        """
        self._identity_manager = identity_manager
        self._persistence = persistence
        self._default_validity_days = default_validity_days
        self._revocation_registry: Set[str] = set()

        # Load revocation registry
        self._load_revocation_registry()

        logger.info("CredentialStore initialized")

    def issue_credential(
        self,
        agent_id: str,
        credential_type: str,
        exam_id: Optional[str] = None,
        exam_score: Optional[float] = None,
        validity_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerifiableCredential:
        """
        Issue a new credential to an agent.

        Args:
            agent_id: Agent receiving the credential
            credential_type: Type of credential (e.g., "Python_Novice")
            exam_id: Optional exam that earned this credential
            exam_score: Optional exam score
            validity_days: Days until expiry (default: 365)
            metadata: Additional metadata

        Returns:
            The issued VerifiableCredential
        """
        import uuid

        validity = validity_days or self._default_validity_days
        credential = VerifiableCredential(
            credential_id=f"vc_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            credential_type=credential_type,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=validity),
            exam_id=exam_id,
            exam_score=exam_score,
            metadata=metadata or {},
        )

        # Sign with IdentityManager
        signed_action = self._identity_manager.sign_action(
            agent_id="university_authority",
            action_type="credential_issued",
            payload=credential.to_dict(),
        )
        credential.signature = signed_action.signature

        # Persist
        self._save_credential(credential)

        logger.info(f"Issued credential {credential.credential_id} ({credential_type}) to {agent_id}")
        return credential

    def verify_credential(self, credential: VerifiableCredential) -> bool:
        """
        Verify a credential is valid.

        Checks:
        - Status is ACTIVE
        - Not expired
        - Not in revocation registry
        - Signature is valid
        """
        # Check status
        if credential.status != CredentialStatus.ACTIVE:
            logger.debug(f"Credential {credential.credential_id} status: {credential.status}")
            return False

        # Check expiry
        if credential.expires_at and datetime.utcnow() > credential.expires_at:
            logger.debug(f"Credential {credential.credential_id} expired")
            return False

        # Check revocation registry
        if credential.credential_id in self._revocation_registry:
            logger.debug(f"Credential {credential.credential_id} revoked")
            return False

        # TODO: Verify signature with IdentityManager

        return True

    def revoke_credential(self, credential_id: str, reason: str = "") -> bool:
        """Revoke a credential."""
        credential = self.get_credential(credential_id)
        if not credential:
            return False

        credential.status = CredentialStatus.REVOKED
        credential.metadata["revoked_at"] = datetime.utcnow().isoformat()
        credential.metadata["revocation_reason"] = reason

        self._revocation_registry.add(credential_id)
        self._save_credential(credential)
        self._save_revocation_registry()

        logger.info(f"Revoked credential {credential_id}: {reason}")
        return True

    def get_credential(self, credential_id: str) -> Optional[VerifiableCredential]:
        """Get a credential by ID."""
        # Requires extending GovernancePersistence with load_credential method.
        if hasattr(self._persistence, "load_credential"):
            data = self._persistence.load_credential(credential_id)
            if data:
                return VerifiableCredential.from_dict(data)
        return None

    def get_agent_credentials(
        self,
        agent_id: str,
        valid_only: bool = True,
    ) -> List[VerifiableCredential]:
        """Get all credentials for an agent."""
        # In real impl, would query by agent_id index
        # For now, scan all credentials
        credentials = []
        
        # Requires extending GovernancePersistence with load_all_credentials method.
        if hasattr(self._persistence, "load_all_credentials"):
            all_data = self._persistence.load_all_credentials()
            
            for cred_id, data in all_data.items():
                if data.get("agent_id") == agent_id:
                    cred = VerifiableCredential.from_dict(data)
                    if not valid_only or self.verify_credential(cred):
                        credentials.append(cred)

        return credentials

    def has_credential(self, agent_id: str, credential_type: str) -> bool:
        """Check if agent has a valid credential of given type."""
        credentials = self.get_agent_credentials(agent_id, valid_only=True)
        return any(c.credential_type == credential_type for c in credentials)

    def _save_credential(self, credential: VerifiableCredential) -> None:
        """Save credential to persistence."""
        # CRITICAL: Do not reuse reputation scores.
        # Requires extending GovernancePersistence with save_credential method.
        if hasattr(self._persistence, "save_credential"):
            self._persistence.save_credential(
                credential.credential_id,
                credential.to_dict()
            )
        else:
            # Fallback or Error - Persistence layer must be updated first
            raise NotImplementedError("GovernancePersistence.save_credential not implemented")

    def _load_revocation_registry(self) -> None:
        """Load revocation registry from persistence."""
        data = self._persistence._backend.get(self.REVOCATION_REGISTRY_KEY)
        if data:
            self._revocation_registry = set(json.loads(data))

    def _save_revocation_registry(self) -> None:
        """Save revocation registry to persistence."""
        self._persistence._backend.set(
            self.REVOCATION_REGISTRY_KEY,
            json.dumps(list(self._revocation_registry))
        )
```

## 5. References

### Implementation Dependencies (Completed)
*   **Enforcer (MD-3115):** `src/maestro_hive/governance/enforcer.py` ✅
*   **Reputation Engine (MD-3118):** `src/maestro_hive/governance/reputation.py` ✅
*   **Identity Manager (MD-3118):** `src/maestro_hive/governance/identity.py` ✅
*   **Persistence Layer (MD-3118):** `src/maestro_hive/governance/persistence.py` ✅

### Frontend (To Be Created)
*   `frontend/src/components/university/PersonaUniversityDashboard.tsx` (NEW)
*   `frontend/src/components/university/ExamHistoryPanel.tsx` (NEW)
*   `frontend/src/components/university/CredentialBadge.tsx` (NEW)

### Related Documentation
*   **Governance EPIC:** `docs/tickets/MD-3200_GOVERNANCE_EPIC.md`
*   **Policy Configuration:** `config/governance/policy.yaml`

## 6. Sub-Tasks Breakdown

| Task ID | Description | Estimate | Dependencies | Status |
|---------|-------------|----------|--------------|--------|
| **MD-3127-0** | **Extend GovernancePersistence with credential methods** | **S** | **MD-3118** | **⚠️ PREREQUISITE** |
| MD-3127-1 | Define Curriculum YAML schema | S | None | ✅ Designed |
| MD-3127-2 | Build PersonaUniversityService | M | MD-3127-1 | Pending |
| MD-3127-3 | Build UserSimulatorAgent | M | MD-3127-1 | ✅ Designed |
| MD-3127-4 | Build CredentialStore | M | **MD-3127-0**, MD-3118 | ✅ Designed |
| MD-3127-5 | Build ExamSimulator (basic) | L | MD-3127-2, MD-3127-3 | Pending |
| MD-3127-6 | Integrate with IdentityManager | S | MD-3127-4 | Pending |
| MD-3127-7 | Integrate with ReputationEngine | S | MD-3127-2, MD-3118 | Pending |
| MD-3127-8 | Create policy_exam_strict.yaml | S | MD-3115 | Pending |
| MD-3127-9 | Frontend Dashboard | M | MD-3127-2 | Pending |
| MD-3127-10 | Add Time Dilation (v2) | L | MD-3127-5 | Deferred |

### ⚠️ Critical Prerequisite: MD-3127-0

Before `CredentialStore` can be implemented, `GovernancePersistence` (`persistence.py`) must be extended:

```python
# Add to GovernancePersistence class in persistence.py
KEY_CREDENTIALS = "credentials:store"

def save_credential(self, credential_id: str, data: Dict[str, Any]) -> bool:
    """Save a credential."""
    key = f"{self.KEY_CREDENTIALS}:{credential_id}"
    return self._backend.set(key, json.dumps(data))

def load_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
    """Load a credential by ID."""
    key = f"{self.KEY_CREDENTIALS}:{credential_id}"
    value = self._backend.get(key)
    return json.loads(value) if value else None

def load_all_credentials(self) -> Dict[str, Dict[str, Any]]:
    """Load all credentials."""
    credentials = {}
    pattern = f"{self.KEY_CREDENTIALS}:*"
    for key in self._backend.keys(pattern):
        cred_id = key.split(":")[-1]
        value = self._backend.get(key)
        if value:
            credentials[cred_id] = json.loads(value)
    return credentials
```

## 7. Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-11 | Original | Initial document |
| 2025-12-11 | Claude | Added Section 0: Review Notes |
| 2025-12-11 | Claude | Expanded ACs from 4 to 10 |
| 2025-12-11 | Claude | Added Section 4.1: Integration code samples |
| 2025-12-11 | Claude | Added Section 4.2: Curriculum YAML schema |
| 2025-12-11 | Claude | Added Section 4.3: UserSimulatorAgent specification |
| 2025-12-11 | Claude | Added Section 4.4: CredentialStore design |
| 2025-12-11 | Claude | Fixed Enforcer reference (MD-3201 → MD-3115) |
| 2025-12-11 | Claude | Updated sub-tasks with new components |
| 2025-12-11 | User | **AUDIT:** Fixed Enforcer `_policy_path` bug (Challenge 4) |
| 2025-12-11 | User | **AUDIT:** Fixed Persistence pollution bug (Challenge 5) |
| 2025-12-11 | Claude | Added MD-3127-0 prerequisite task |
| 2025-12-11 | Claude | Added credential methods specification for persistence.py |
| 2025-12-11 | Claude | Renamed MD-3210 to MD-3127 |

---

**Review Status:** `APPROVED_WITH_PREREQUISITES`
**Prerequisite:** Extend `GovernancePersistence` with credential methods (MD-3127-0)
**Related JIRA:** MD-3127
**Last Updated:** 2025-12-11
