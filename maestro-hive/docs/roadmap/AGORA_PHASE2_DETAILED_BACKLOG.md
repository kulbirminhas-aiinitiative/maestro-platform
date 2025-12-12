# AGORA PHASE 2: DETAILED JIRA BACKLOG

## AGORA-100: Design Event Bus Interface (Pub/Sub)
**Priority**: P0 (Blocker)
**Context**:
The Agora architecture relies on decoupling agents. Currently, the Orchestrator calls agents directly. This prevents "Swarming" and dynamic team formation. We need a "Town Square" where agents can broadcast intent.
**Problem Statement (The Why)**:
Direct function calls create tight coupling. If Agent A wants to talk to Agent B, it must have a reference to B. In a dynamic society, Agent A shouldn't know *who* B is, only that B *can do the job*.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/core/event_bus.py`.
2. Define an abstract base class `EventBus`.
3. Define methods:
   - `publish(topic: str, message: Dict) -> None`
   - `subscribe(topic: str, callback: Callable) -> str` (returns subscription_id)
   - `unsubscribe(subscription_id: str) -> None`
**Acceptance Criteria**:
- The interface is defined using Python's `abc` module.
- Type hints are strict.
- Documentation strings explain the contract.

## AGORA-101: Implement InMemoryEventBus
**Priority**: P0
**Context**:
We need a reference implementation of the Event Bus for local testing and development before moving to distributed infrastructure like Redis or NATS.
**Problem Statement (The Why)**:
Developers and CI/CD pipelines need to run the Agora without spinning up external message brokers.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/core/event_bus_memory.py`.
2. Implement `InMemoryEventBus` inheriting from `EventBus`.
3. Use `asyncio.Queue` or a dictionary of lists for topic routing.
4. Ensure it is thread-safe/async-safe.
**Acceptance Criteria**:
- Unit test: Publisher sends "Hello" to "topic-A". Subscriber on "topic-A" receives it.
- Unit test: Subscriber on "topic-B" does NOT receive it.
- Latency is < 1ms for local messages.

## AGORA-102: Define Agent Communication Language (ACL) Schema
**Priority**: P1
**Context**:
Agents need a standardized way to speak. Raw text is ambiguous. We adopt FIPA-ACL standards adapted for LLMs.
**Problem Statement (The Why)**:
If Agent A sends "Do this", and Agent B expects "Request: Do this", the system breaks. We need a strict schema.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/core/acl.py`.
2. Define `AgoraMessage` dataclass.
3. Fields:
   - `message_id`: UUID
   - `timestamp`: ISO8601
   - `sender`: str (Agent ID)
   - `receiver`: str (Agent ID or "BROADCAST")
   - `performative`: Enum (REQUEST, PROPOSE, AGREE, REFUSE, INFORM, FAILURE)
   - `content`: Dict (The payload)
   - `protocol`: str (e.g., "contract-net")
4. Implement `to_json()` and `from_json()` methods.
**Acceptance Criteria**:
- Valid messages serialize/deserialize correctly.
- Invalid messages (missing fields) raise `ValidationError`.

## AGORA-103: Implement Agent Identity & Key Generation
**Priority**: P1
**Context**:
In a marketplace, identity is everything. We cannot rely on simple string names. We need cryptographic proof of identity.
**Problem Statement (The Why)**:
Any agent could claim to be "The Admin". We need Self-Sovereign Identity (SSI) principles.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/core/identity.py`.
2. Implement `IdentityManager` class.
3. Method `generate_identity()`: Creates an Ed25519 public/private key pair.
4. Method `save_identity(path)`: Saves encrypted private key to disk.
5. Method `load_identity(path)`: Loads it back.
**Acceptance Criteria**:
- Keys are generated using `cryptography` library.
- Private keys are never exposed in logs.
- Public key serves as the `agent_id`.

## AGORA-104: Implement Message Signing
**Priority**: P1
**Context**:
Trust requires verification. Every message in the Agora must be signed by the sender.
**Problem Statement (The Why)**:
To prevent "Man in the Middle" attacks or spoofing in the Town Square.
**Technical Requirements (The What)**:
1. Update `AgoraMessage` to include `signature` field.
2. Update `EventBus.publish`: Automatically sign the message hash with the sender's private key.
3. Update `EventBus` listeners: Automatically verify the signature against `sender` public key before processing.
**Acceptance Criteria**:
- A message with a valid signature is processed.
- A message with a tampered payload is rejected.

## AGORA-105: Create Agent Registry Service
**Priority**: P2
**Context**:
Agents need to find each other based on skills, not names.
**Problem Statement (The Why)**:
"I need a Python Coder." -> Who is that? The Registry answers this.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/core/registry.py`.
2. Implement `AgentRegistry` class (Singleton or Service).
3. Method `register(agent_profile)`: Stores agent metadata (ID, Guild, Skills, Price).
4. Method `find_agents(query)`: Returns list of matching agents.
**Acceptance Criteria**:
- Can register 3 agents (Coder, Reviewer, Tester).
- Query "Guild=Coder" returns only the Coder.
