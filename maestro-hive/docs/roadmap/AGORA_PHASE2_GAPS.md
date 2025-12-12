# Agora Phase 2: Gap Analysis & Evolution Plan

## 1. Executive Summary
The "Foundation" phase (MD-3097, MD-3099) established the *physics* of the agent world: they now have **Time** (Persistence) and **Energy** (Token Budgets). 

The "Next Level" of evolution is **Society**. Currently, agents are solitary workers. They cannot talk to each other, they have no identity, and they cannot form teams dynamically. To realize the "Agora" vision, we must implement the **Social Layer**.

## 2. Gap Analysis: From "Script" to "Citizen"

| Feature Area | Current State (As-Is) | Target State (To-Be) | Gap Severity |
| :--- | :--- | :--- | :--- |
| **Identity** | Agents are just strings (`"persona_id": "coder"`). No verification. | Agents have **Cryptographic Identity** (Public/Private Keys). They sign their work. | **CRITICAL** (No trust possible without ID) |
| **Communication** | Orchestrator calls Agent functions directly (Tight Coupling). | **Event Bus (The Town Square)**. Agents publish intents ("I need code") and subscribe to topics. | **HIGH** (Prevents dynamic swarming) |
| **Discovery** | Hardcoded lists of personas in `persona_config.json`. | **Dynamic Registry**. Agents "register" their skills and availability. | **MEDIUM** (Hard to scale to 100+ agents) |
| **Collaboration** | Serial execution (A then B then C). | **Contract Net Protocol**. Manager broadcasts task -> Agents bid -> Winner executes. | **HIGH** (Inefficient resource allocation) |
| **Memory** | Local JSON files (Siloed). | **Shared Knowledge Graph**. Agents can query a central "Library" of past solutions. | **MEDIUM** (Reinventing the wheel) |

## 3. Proposed Evolution: The "Society" Epics

We propose creating the following JIRA Epics to bridge these gaps.

### EPIC-3: The Town Square (Event Bus Architecture)
**Goal**: Decouple the Orchestrator from the Agents.
- **Ticket 3.1**: Design the `EventBus` Interface (Pub/Sub).
- **Ticket 3.2**: Implement `InMemoryEventBus` for local development.
- **Ticket 3.3**: Define the `AgoraMessage` Protocol (ACL - Agent Communication Language).
    - *Schema*: `sender_id`, `receiver_id`, `performative` (REQUEST, INFORM, PROPOSE), `content`.

### EPIC-4: Self-Sovereign Identity (SSI)
**Goal**: Enable trust and non-repudiation.
- **Ticket 4.1**: Implement `IdentityManager`.
    - Generate `Ed25519` keypairs on agent birth.
    - Store private keys in a secure `Wallet` (encrypted file for now).
- **Ticket 4.2**: Implement `MessageSigner`.
    - All messages on the Event Bus must be signed.
- **Ticket 4.3**: Implement `TrustRegistry`.
    - A database mapping `Public Key` -> `Trust Score`.

### EPIC-5: The Guild Registry
**Goal**: Dynamic discovery of capabilities.
- **Ticket 5.1**: Define `Guild` schemas (Coder, Reviewer, Architect).
- **Ticket 5.2**: Implement `AgentRegistry`.
    - Agents "check in" at startup: "I am Agent X, I speak Python, I am online."
- **Ticket 5.3**: Implement `GuildRouter`.
    - "Find me a Coder who costs < $0.05 per token."

## 4. Technical Architecture for Phase 2

```python
# Conceptual Architecture

class AgoraNode:
    def __init__(self):
        self.bus = EventBus()
        self.registry = AgentRegistry()

class CitizenAgent:
    def __init__(self, name):
        self.identity = IdentityManager.create_new()
        self.wallet = TokenWallet()
        self.bus_handle = EventBus.connect()
    
    def on_message(self, msg):
        if msg.performative == 'CFP' (Call For Proposal):
            if self.can_do(msg.task):
                bid = self.calculate_bid(msg.task)
                self.bus_handle.publish(bid)
```

## 5. Recommendation
We should immediately proceed with **EPIC-3 (The Town Square)**. Without a communication bus, the Identity and Guild features have nowhere to live. The Event Bus is the central nervous system of the Agora.
