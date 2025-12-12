# Agora Epics & User Stories

This document defines the JIRA Epics and Stories required to build the Agora Vision.

## EPIC-1: Durable Execution Core (MD-3097)
**Summary**: Enable agents to persist state across restarts and crashes.
**Priority**: P0 (Blocker)
**Stories**:
1.  **[MD-3097-1] Define State Schema**: Create the JSON schema for an agent's "Mind" (Memory, History, Wallet, Config).
2.  **[MD-3097-2] Implement FileStateManager**: Create a local disk backend for saving/loading agent state.
3.  **[MD-3097-3] Integrate Persistence Hooks**: Modify `PersonaExecutor.run()` to load state at start and save state after every step.
4.  **[MD-3097-4] Replay Mechanism**: Allow an agent to "resume" a workflow from a saved state file.

## EPIC-2: Token Economy & Scarcity (MD-3099)
**Summary**: Implement resource constraints to drive efficiency.
**Priority**: P1
**Stories**:
1.  **[MD-3099-1] Token Counter**: Implement a utility to count tokens for input/output messages.
2.  **[MD-3099-2] Budget Enforcement**: Throw `BudgetExceededException` if an agent tries to act without funds.
3.  **[MD-3099-3] Wallet Class**: Create a `Wallet` object to hold the agent's balance.
4.  **[MD-3099-4] Cost Reporting**: Generate a report of "Cost per Task" to identify inefficient agents.

## EPIC-3: The Town Square (Event Bus)
**Summary**: Decouple agents using a Pub/Sub architecture.
**Priority**: P2
**Stories**:
1.  **[AGORA-3-1] Event Bus Interface**: Define `publish(topic, message)` and `subscribe(topic, callback)`.
2.  **[AGORA-3-2] In-Memory Bus**: Implement a simple Python queue-based bus for local testing.
3.  **[AGORA-3-3] Agent Listener Loop**: Refactor agents to run a background loop listening for events.
4.  **[AGORA-3-4] Broadcast Intent**: Create a standard "Help Wanted" message format.

## EPIC-4: Identity & Trust
**Summary**: Give agents verifiable identities.
**Priority**: P2
**Stories**:
1.  **[AGORA-4-1] Key Generation**: Auto-generate public/private keys on agent creation.
2.  **[AGORA-4-2] Message Signing**: Sign every log entry and output with the private key.
3.  **[AGORA-4-3] Trust Score Database**: Create a simple KV store mapping `AgentID` -> `TrustScore`.

## EPIC-5: Guilds & Specialization
**Summary**: Organize agents into functional groups.
**Priority**: P3
**Stories**:
1.  **[AGORA-5-1] Guild Config**: Add `guild` field to `persona_config.json` (e.g., "Coder", "Reviewer").
2.  **[AGORA-5-2] Guild Router**: Create a helper to "Find an agent in Guild X".
3.  **[AGORA-5-3] Capability Manifest**: Allow agents to self-report their tools and skills.
