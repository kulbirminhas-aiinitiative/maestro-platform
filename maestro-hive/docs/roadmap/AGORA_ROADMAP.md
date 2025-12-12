# The Agora: Strategic Roadmap & Execution Plan

## 1. Vision Summary
The Agora is a transition from "Agents as Tools" to "Agents as Citizens". It envisions a digital economy where autonomous agents:
- **Persist** indefinitely (State as Physics).
- **Own** resources and pay for existence (Token Economy).
- **Communicate** via a formal ontology (ACL).
- **Specialize** into Guilds and trade services in a marketplace.

## 2. Phased Execution Plan

### Phase 1: The Foundation (Physics & Economy)
**Goal**: Establish the immutable laws of the universe—Time, State, and Energy.
**Status**: **IN PROGRESS** (MD-3097, MD-3099)
- **Objective 1.1**: Durable Execution. Agents must survive restarts.
- **Objective 1.2**: Token Budgeting. Agents must respect resource limits.
- **Objective 1.3**: Basic Safety. Prompt injection defenses.

### Phase 2: The Society (Identity & Communication)
**Goal**: Define "Who" an agent is and "How" they speak.
**Status**: **PLANNED**
- **Objective 2.1**: Cryptographic Identity (SSI). Key-based agent IDs.
- **Objective 2.2**: The Town Square. A Pub/Sub event bus for broadcasting intent.
- **Objective 2.3**: Agent Communication Language (ACL). Standardized message formats (REQUEST, PROPOSE, AGREE).

### Phase 3: The Market (Bidding & Negotiation)
**Goal**: Enable the "Invisible Hand" to allocate resources.
**Status**: **FUTURE**
- **Objective 3.1**: Contract Net Protocol. Bidding on tasks.
- **Objective 3.2**: Trust Scores. Reputation tracking based on outcome verification.
- **Objective 3.3**: The Court. Dispute resolution mechanisms.

---

## 3. Epic Breakdown & Story Mapping

### Epic 1: Durable Execution (MD-3097)
**Theme**: "State as Physics"
- **Story 1.1**: Implement `StateManager` interface (Load/Save/Snapshot).
- **Story 1.2**: Integrate `StateManager` into `PersonaExecutor`.
- **Story 1.3**: Implement File-based State Backend (MVP).
- **Story 1.4**: Implement Redis/Database State Backend (Production).
- **Task**: Add `_load_state` and `_save_state` hooks to `persona_executor.py`.

### Epic 2: The Token Economy (MD-3099)
**Theme**: "Scarcity drives Efficiency"
- **Story 2.1**: Define `TokenBudget` class.
- **Story 2.2**: Implement `check_budget()` decorator for LLM calls.
- **Story 2.3**: Implement "Bankruptcy" logic (Agent death on zero balance).
- **Task**: Modify `PersonaExecutor` to track usage against a budget.

### Epic 3: Agent Identity & Registry (New)
**Theme**: "I am, therefore I sign"
- **Story 3.1**: Generate RSA/Ed25519 Keypairs for Agents on initialization.
- **Story 3.2**: Create `AgentRegistry` (The Phonebook).
- **Story 3.3**: Implement Message Signing (Non-repudiation).

### Epic 4: The Town Square (New)
**Theme**: "Broadcast, don't couple"
- **Story 4.1**: Implement `EventBus` (Pub/Sub interface).
- **Story 4.2**: Create `BroadcastMessage` schema.
- **Story 4.3**: Refactor `ParallelCoordinator` to use Event Bus instead of direct calls.

### Epic 5: The Guild System (New)
**Theme**: "Specialization of Labor"
- **Story 5.1**: Define `Guild` attributes in `persona_config.json`.
- **Story 5.2**: Implement `CapabilityManifest` (What can I do?).
- **Story 5.3**: Implement `GuildRouter` to route tasks to the right specialist.

---

## 4. Immediate Action Plan (Next 48 Hours)

1.  **Execute MD-3097**: Fix the "Hollow Shell" of `PersonaExecutor`.
    -   *Why*: Without state, there is no citizen.
2.  **Execute MD-3099**: Add the "Energy" constraint.
    -   *Why*: Without scarcity, there is no evolution.
3.  **Design Phase 2**: Draft the `AgentIdentity` class structure.
