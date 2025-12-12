# Review of MD-3127: Persona University

## 1. Assessment
The document `MD-3127_PERSONA_UNIVERSITY.md` provides a strong conceptual foundation for the "University" model. The distinction between "Foundry" (Creation) and "University" (Training) is architecturally sound and aligns with the goal of evolving agents from "Workers" to "Citizens".

However, I have identified several technical gaps that need to be addressed before implementation can begin.

## 2. Challenges & Corrections

### Challenge 1: Enforcer "Strict Mode" (Section 4.1)
**Issue:** The document proposes `self.enforcer.set_mode("strict")`.
**Fact:** The current `Enforcer` implementation (`src/maestro_hive/governance/enforcer.py`) **does not support modes**. It is stateless and purely policy-driven.
**Correction:** Instead of a stateful "mode", we should pass a `context` flag to the `check()` method, or load a specific `policy_exam.yaml` for the duration of the simulation.
**Action:** Update MD-3127 to specify "Policy Overrides" instead of "Strict Mode".

> **UPDATE (2025-12-11):** Verified - `Enforcer` has `load_policy()` method (line 191) that can be used to temporarily load stricter policy. Recommend adding `load_temporary_policy()` wrapper that restores original policy after exam.

### Challenge 2: Credential Storage (Section 2 / Phase 4)
**Issue:** The document states credentials are stored in "The agent's `metadata`".
**Fact:** The `personas.py` file currently relies on `maestro-engine` (external) or `personas_fallback.py` (local). The fallback definitions are static dictionaries. They have no mutable `metadata` field to store credentials.
**Correction:** We need a persistent `AgentProfile` database (SQLite/Postgres) to store the dynamic state of an agent (Reputation, Credentials, History) separate from their static Persona Definition.
**Action:** Add a requirement for `AgentProfileService` to manage mutable state.

> **UPDATE (2025-12-11):** ✅ PARTIALLY RESOLVED by MD-3118 implementation:
> - `AgentIdentity` class now has `metadata: Dict[str, Any]` field (identity.py:55)
> - `GovernancePersistence` provides storage backends (File/Redis)
> - `IdentityManager.create_identity(agent_id, metadata={...})` supports metadata
>
> **Remaining Gap:** Need to extend `AgentIdentity.metadata` to store credentials, or create dedicated `CredentialStore` using `GovernancePersistence`.

### Challenge 3: "Ghost Users" (Section 2 / Phase 2)
**Issue:** The concept of "Ghost Users" is vague.
**Fact:** To simulate a user, we need a "User Persona" (an LLM acting as a user) driven by a script.
**Correction:** Define `UserSimulatorAgent` as a specific component that consumes `scenario.yaml` and generates natural language prompts to test the student agent.

> **UPDATE (2025-12-11):** Still valid. No `UserSimulatorAgent` exists. Recommend:
> ```python
> class UserSimulatorAgent:
>     """Simulates user behavior for exam scenarios."""
>     def __init__(self, scenario_path: str):
>         self.scenario = yaml.safe_load(open(scenario_path))
>
>     def generate_prompt(self, step: int) -> str:
>         """Generate user prompt for current exam step."""
>         return self.scenario["steps"][step]["user_input"]
> ```

## 3. Revised Plan (Proposed Updates to JIRA)

I recommend updating the JIRA ticket with these technical refinements:

1.  **Architecture:** ~~Introduce `AgentProfileService` (Database) to store VCs.~~ → Use existing `IdentityManager` + `GovernancePersistence` from MD-3118
2.  **Enforcer:** Define `Enforcer.load_temporary_policy()` for exams.
3.  **Simulator:** Define `UserSimulatorAgent` for interaction.
4.  **NEW:** Define `CredentialStore` class to manage VCs with expiry/revocation

## 4. Conclusion
The vision is approved, but the technical implementation details regarding state management (Credentials) and policy enforcement (Strict Mode) need refinement.

**Status:** `REVIEWED_WITH_CHANGES`

---

## 5. Follow-up Review (2025-12-11)

### What's Changed Since Original Review
| Challenge | Original Status | Current Status |
|-----------|-----------------|----------------|
| Enforcer Strict Mode | ❌ No modes | ⚠️ Has `load_policy()`, need wrapper |
| Credential Storage | ❌ No persistence | ✅ `GovernancePersistence` exists (MD-3118) |
| Ghost Users | ❌ Undefined | ❌ Still undefined |

### Additional Issues Found in MD-3127
1. **Ticket Number Mismatch:** Document says MD-3210, but JIRA is MD-3127
2. **Time Dilation:** Too complex for MVP - recommend deferring to v2
3. **Integration not specified:** No code samples for how University integrates with existing systems

### Actions Taken
- [x] Updated `MD-3127_PERSONA_UNIVERSITY.md` with integration code samples (Section 4.1)
- [x] Added Curriculum YAML schema (Section 4.2)
- [x] Expanded ACs from 4 to 10
- [x] Added sub-task breakdown (Section 6)
- [x] Updated JIRA MD-3127 with review comment

### Remaining Actions
- [x] Update MD-3127 to use "Policy Overrides" instead of `set_mode("strict")` ✅ Fixed
- [x] Define `UserSimulatorAgent` specification ✅ Added Section 4.3
- [x] Create `CredentialStore` class design ✅ Added Section 4.4
- [x] Clarify ticket numbering (MD-3210 vs MD-3127) ✅ Header updated

**Reviewer:** Claude (AI Assistant)
**Review Date:** 2025-12-11
**Final Update:** 2025-12-11 - All review actions completed

---

## 6. Final Status

| Item | Status |
|------|--------|
| Original Review Challenges | All addressed |
| UserSimulatorAgent | ✅ Full specification with scenario YAML |
| CredentialStore | ✅ Full design with revocation registry |
| Enforcer Integration | ✅ Uses `load_policy()` pattern |
| Document Quality | ✅ Production-ready specifications |

**Review Status:** `APPROVED_FOR_IMPLEMENTATION`

---

## 7. Technical Audit (2025-12-11) - REOPENED

I have performed a deep-dive code analysis of the proposed implementation plan against the actual codebase (`src/maestro_hive/governance/`) and identified two critical blockers that will cause immediate runtime failures.

### Challenge 4: Enforcer Integration Bug (Section 4.1)
**Issue:** The proposed code `original_policy = self.enforcer._policy_path` will raise `AttributeError`.
**Fact:** Analysis of `src/maestro_hive/governance/enforcer.py` reveals that `load_policy()` reads the file but **does not store the path** in the instance. The `Enforcer` class has no `_policy_path` attribute.
**Correction:**
1.  Modify `Enforcer` to store `self.current_policy_path`.
2.  Or, update the design to require the caller to know the original policy path.
**Action:** Updated MD-3127 Section 4.1 to reflect a safer implementation pattern.

### Challenge 5: Persistence Layer Pollution (Section 4.4)
**Issue:** The `CredentialStore` design reuses `save_reputation_score` to store credentials.
**Fact:** `GovernancePersistence.save_reputation_score` forces the key prefix `reputation:scores:`. Storing credentials here will:
1.  Pollute the reputation namespace.
2.  Cause `load_reputation_score` to return `VerifiableCredential` dicts instead of reputation scores, potentially crashing the `ReputationEngine`.
**Correction:** The `GovernancePersistence` class must be extended with dedicated methods:
-   `save_credential(credential_id, data)`
-   `load_credential(credential_id)`
**Action:** Updated MD-3127 Section 4.4 to explicitly require extending `GovernancePersistence`.

**Revised Status:** `CHANGES_REQUESTED`

---

## 8. Resolution Verification (2025-12-11)

### Challenge 4 Resolution: ✅ VERIFIED
The updated `ExamSimulator` in MD-3127 Section 4.1 now:
- Requires `default_policy_path` via constructor injection
- No longer accesses non-existent `_policy_path` attribute
- Pattern is safe and follows dependency injection best practices

### Challenge 5 Resolution: ✅ VERIFIED
The updated `CredentialStore` in MD-3127 Section 4.4 now:
- Explicitly requires `GovernancePersistence` extension
- Uses `hasattr()` checks before calling credential methods
- Raises `NotImplementedError` if persistence layer is not extended
- No longer pollutes `reputation:scores` namespace

### Implementation Prerequisite
Before `CredentialStore` can be implemented, `GovernancePersistence` must be extended with:

```python
# Add to persistence.py
KEY_CREDENTIALS = "credentials:store"

def save_credential(self, credential_id: str, data: Dict[str, Any]) -> bool:
    key = f"{self.KEY_CREDENTIALS}:{credential_id}"
    return self._backend.set(key, json.dumps(data))

def load_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
    key = f"{self.KEY_CREDENTIALS}:{credential_id}"
    value = self._backend.get(key)
    return json.loads(value) if value else None

def load_all_credentials(self) -> Dict[str, Dict[str, Any]]:
    credentials = {}
    pattern = f"{self.KEY_CREDENTIALS}:*"
    for key in self._backend.keys(pattern):
        cred_id = key.split(":")[-1]
        value = self._backend.get(key)
        if value:
            credentials[cred_id] = json.loads(value)
    return credentials
```

### Updated Sub-Task Order
1. **MD-3127-0 (NEW):** Extend `GovernancePersistence` with credential methods
2. MD-3127-1: Define Curriculum YAML schema ✅
3. MD-3127-2: Build PersonaUniversityService
4. MD-3127-3: Build UserSimulatorAgent ✅
5. MD-3127-4: Build CredentialStore ✅ (depends on MD-3127-0)

**Final Status:** `APPROVED_WITH_PREREQUISITES`

The design is technically sound. Implementation can proceed once `GovernancePersistence` is extended.
