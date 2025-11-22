# Claude Team SDK - Critical Capabilities Analysis

**Date**: 2025-10-04
**Purpose**: Understand what the SDK actually provides and what team patterns it enables

---

## 🔍 Core SDK Capabilities

### 1. Team Coordination Infrastructure

**TeamCoordinator** provides:
- ✅ In-memory shared workspace
- ✅ MCP coordination server with 12 tools
- ✅ Async locking for thread-safe operations
- ✅ Event queue for broadcasts
- ✅ Agent lifecycle tracking

### 2. MCP Coordination Tools (12 Total)

| Tool | Purpose | Key Capability |
|------|---------|----------------|
| **post_message** | Send message to agent/all | Async inter-agent communication |
| **get_messages** | Read messages for agent | Message inbox with filtering |
| **claim_task** | Claim task from queue | Role-based task claiming |
| **complete_task** | Mark task complete | Task lifecycle management |
| **share_knowledge** | Add knowledge item | Persistent key-value knowledge base |
| **get_knowledge** | Retrieve knowledge | Knowledge retrieval with metadata |
| **update_status** | Update agent status | Real-time status tracking |
| **get_team_status** | View all statuses | Team visibility |
| **store_artifact** | Store work product | Artifact versioning |
| **get_artifacts** | List artifacts | Artifact discovery |
| **propose_decision** | Propose team decision | Democratic decision making |
| **vote_decision** | Vote on decision | Voting mechanism |

### 3. Shared Workspace State

```python
shared_workspace = {
    "messages": [],      # All inter-agent messages
    "tasks": {},         # Task queue with status
    "knowledge": {},     # Shared knowledge base
    "agent_status": {},  # Real-time agent status
    "artifacts": {},     # Work products
    "decisions": []      # Team decisions with votes
}
```

### 4. TeamAgent Base Class

Provides:
- ✅ ClaudeSDKClient integration (real Claude API)
- ✅ MCP coordination server connection
- ✅ Built-in message/knowledge/status helpers
- ✅ Abstract `execute_task` method
- ✅ Auto-task claiming loop

---

## 🎯 What Team Patterns Are ACTUALLY Enabled?

### Pattern 1: **Autonomous Task Queue** ⭐

**Description**: Coordinator adds tasks to queue, agents autonomously claim and execute based on their role

**Enabled by**:
- `add_task()` - Coordinator adds tasks
- `claim_task()` - Agents auto-claim by role
- `complete_task()` - Agents mark complete
- `_auto_task_loop()` - Built into TeamAgent

**Key Insight**: Agents are truly autonomous - they decide what to work on

**Use Cases**:
- Bug triage (different severity → different roles)
- Code review queue
- Ticket processing
- Multi-priority workloads

**Example Flow**:
```python
# Coordinator adds tasks
await coordinator.add_task("Design API", required_role="architect")
await coordinator.add_task("Implement endpoint", required_role="developer")
await coordinator.add_task("Write tests", required_role="tester")

# Agents autonomously claim and execute
# Architect claims design task
# Developer waits for design, then claims implementation
# Tester waits for implementation, then claims test task
```

---

### Pattern 2: **Collaborative Knowledge Building** ⭐

**Description**: Agents share discoveries, others build upon them

**Enabled by**:
- `share_knowledge()` - Persistent knowledge store
- `get_knowledge()` - Other agents retrieve and build on it
- Knowledge has `category` for organization
- Knowledge includes `from` agent and `timestamp`

**Key Insight**: Knowledge persists across agent lifecycles and can be referenced by any agent

**Use Cases**:
- Research compilation (each agent researches subtopic, shares findings)
- Architecture documentation (architect shares decisions, developers reference)
- Testing insights (tester shares edge cases, others learn)

**Example Flow**:
```python
# Agent 1 shares discovery
await agent1.share_knowledge("api_pattern", "REST with OpenAPI", "architecture")

# Agent 2 retrieves and builds on it
knowledge = await agent2.get_knowledge("api_pattern")
# Agent 2 now implements based on this knowledge
```

---

### Pattern 3: **Democratic Decision Making** ⭐

**Description**: Agents propose solutions, team votes, majority wins

**Enabled by**:
- `propose_decision()` - Any agent proposes
- `vote_decision()` - All agents vote
- Votes tracked: approve/reject/abstain
- Decision status: pending/approved/rejected

**Key Insight**: No single agent is in control - team reaches consensus

**Use Cases**:
- Architecture decisions (multiple approaches, team votes)
- Code review approval (multiple reviewers vote)
- Priority decisions (which task to tackle first)
- Design choices (UI/UX alternatives)

**Example Flow**:
```python
# Architect proposes approach
decision_id = await architect.propose_decision(
    "Use microservices architecture",
    "Better scalability and team independence"
)

# Other agents vote
await backend_dev.vote_decision(decision_id, "approve")
await frontend_dev.vote_decision(decision_id, "approve")
await tester.vote_decision(decision_id, "reject")  # Complexity concerns

# 2 approve, 1 reject → Decision approved
```

---

### Pattern 4: **Swarm Intelligence** ⭐

**Description**: Multiple similar agents working independently, sharing discoveries

**Enabled by**:
- Multiple agents with same role
- Shared knowledge base
- Independent task claiming
- Artifact sharing

**Key Insight**: Like ants finding food - each explores independently, all benefit from discoveries

**Use Cases**:
- Parallel research (5 researchers, each explores different sources)
- Bug hunting (multiple testers, share findings)
- Code review (multiple reviewers, catch different issues)

**Example Flow**:
```python
# Spawn 5 research agents
researchers = [ResearchAgent(f"researcher_{i}", coord_server) for i in range(5)]

# Each claims research tasks independently
# As they find insights, they share via share_knowledge()
# Other researchers benefit from shared discoveries
# Final compilation benefits from all findings
```

---

### Pattern 5: **Assembly Line (Pipeline)** ⭐

**Description**: Sequential processing where each agent adds value, uses artifacts from previous

**Enabled by**:
- `store_artifact()` - Each agent stores their work
- `get_artifacts()` - Next agent retrieves previous work
- Messages for handoffs
- Status tracking for pipeline visibility

**Key Insight**: Work flows through stages, artifacts accumulate value

**Use Cases**:
- SDLC pipeline (requirements → design → code → test → deploy)
- Document creation (research → draft → review → edit → publish)
- Data processing (collect → clean → analyze → visualize)

**Example Flow**:
```python
# Stage 1: Architect stores design
await architect.store_artifact("design_doc", design_content, "design")
await architect.post_message("all", "Design complete, stored as artifact")

# Stage 2: Developer retrieves and implements
artifacts = await developer.get_artifacts("design")
# Implements based on design
await developer.store_artifact("code", code_content, "implementation")

# Stage 3: Tester retrieves and tests
code_artifacts = await tester.get_artifacts("implementation")
# Tests and reports
```

---

### Pattern 6: **Ask-the-Expert** ⭐

**Description**: Generalist agents ask specialist agents for specific expertise

**Enabled by**:
- Direct messaging (`to_agent` parameter)
- `get_team_status()` to find who's available
- Async message exchange

**Key Insight**: Agents can consult each other, not just work independently

**Use Cases**:
- Security review (developer asks security expert)
- Performance optimization (team asks performance specialist)
- Domain expertise (general agent asks domain expert)

**Example Flow**:
```python
# Developer needs security advice
await developer.post_message(
    "security_expert",
    "What's the best approach for JWT validation?",
    "question"
)

# Security expert responds
await security_expert.post_message(
    "developer_1",
    "Use RS256 with public key verification. Here's why...",
    "answer"
)
```

---

### Pattern 7: **Hierarchical Coordination** ⭐

**Description**: Coordinator orchestrates, assigns tasks, monitors progress

**Enabled by**:
- Coordinator has external control (add_task, get_workspace_state)
- Agents report status
- `get_team_status()` for monitoring
- Tasks can be added dynamically

**Key Insight**: Mix of top-down (coordinator) and bottom-up (agent autonomy)

**Use Cases**:
- Project management (PM coordinates, agents execute)
- Event-driven workflows (coordinator adds tasks based on events)
- Adaptive systems (coordinator adjusts based on team status)

**Example Flow**:
```python
# Coordinator monitors progress
state = await coordinator.get_workspace_state()

if state["tasks"]["completed"] > 5:
    # Add integration task
    await coordinator.add_task("Integration testing", "tester")

# Agents autonomously claim and execute
```

---

## 🚫 What the SDK Does NOT Enable

### ❌ Agent Spawning/Termination
- **Missing**: Dynamic agent lifecycle (add/remove agents at runtime)
- **Workaround**: Pre-create all agents, use status to "deactivate"

### ❌ Agent-to-Agent Direct Delegation
- **Missing**: Agent A cannot assign task directly to Agent B
- **Workaround**: Use messages to request, then add task to queue

### ❌ Persistent Storage
- **Missing**: Workspace is in-memory only
- **Impact**: Team state lost on restart
- **Workaround**: Manually serialize shared_workspace

### ❌ Priority Queue
- **Missing**: Tasks have `priority` field but no priority-based claiming
- **Impact**: FIFO task claiming only
- **Workaround**: Custom claim_task logic

### ❌ Sub-Teams
- **Missing**: No nested coordination servers
- **Impact**: Cannot create sub-teams within team
- **Workaround**: Use agent naming conventions and message filtering

---

## 🎭 Recommended Team Patterns

Based on SDK capabilities, these patterns are **well-supported**:

### 1. **Autonomous Swarm** (Highest Recommendation)
- 5-10 similar agents
- Each claims tasks independently
- Share discoveries via knowledge base
- Emergent coordination through shared knowledge

### 2. **Knowledge Pipeline**
- Sequential specialist agents
- Each adds knowledge/artifacts
- Next agent builds on previous
- Final output is synthesis of all

### 3. **Collaborative Research**
- Multiple researchers
- Each explores different angles
- Share findings in real-time
- Vote on conclusions

### 4. **Democratic Decision Making**
- Agents propose solutions
- Team discusses via messages
- Vote on best approach
- Implement consensus

### 5. **Expert Network**
- Generalist agents + specialists
- Generalists handle common tasks
- Consult specialists for complex questions
- Specialists share expertise via knowledge base

---

## 🔬 Patterns to Test/Explore

### Experiment 1: Pure Autonomous Team
- Add 10 tasks to queue
- Spawn 3 agents (architect, developer, tester)
- **NO orchestration code**
- Let agents auto-claim and execute
- **Question**: Do they self-organize effectively?

### Experiment 2: Knowledge Accumulation
- 5 research agents
- Each researches different topic
- Share all findings
- Final agent synthesizes all knowledge
- **Question**: Can knowledge base scale to complex synthesis?

### Experiment 3: Debate and Vote
- 3 agents propose different solutions
- Each explains rationale
- Team votes
- **Question**: Do agents actually vote meaningfully?

### Experiment 4: Swarm Optimization
- 10 agents, 20 simple tasks
- Measure completion time vs sequential
- **Question**: Does parallelism actually work?

### Experiment 5: Pipeline with Handoffs
- 5 agents in pipeline
- Each depends on previous artifact
- **Question**: Can artifacts effectively transfer context?

---

## 📊 Pattern Comparison Matrix

| Pattern | Coordination | Scalability | Complexity | Best For |
|---------|-------------|-------------|------------|----------|
| **Autonomous Queue** | Low (task queue) | High (add agents) | Low | Parallel workloads |
| **Knowledge Building** | Medium (knowledge) | Medium | Medium | Research, learning |
| **Democratic Voting** | High (messages+votes) | Low (all must vote) | High | Critical decisions |
| **Swarm** | Low (shared knowledge) | Very High | Low | Exploration |
| **Assembly Line** | Medium (artifacts) | Medium | Medium | SDLC, pipelines |
| **Ask Expert** | High (direct messages) | Medium | Medium | Mixed expertise |
| **Hierarchical** | High (coordinator) | Low (bottleneck) | Low | Managed projects |

---

## 🎯 Conclusion: What Should We Build?

### Top 3 Patterns to Implement & Test:

1. **Autonomous Swarm Research Team**
   - Tests: task claiming, knowledge sharing, parallel execution
   - Most aligned with SDK strengths
   - Real-world valuable (parallel research)

2. **Democratic Architecture Team**
   - Tests: proposals, voting, discussion via messages
   - Unique capability (voting)
   - Real-world valuable (architectural decisions)

3. **Knowledge Pipeline**
   - Tests: artifacts, sequential knowledge building, handoffs
   - Tests integration of multiple capabilities
   - Real-world valuable (SDLC workflows)

### What NOT to Build:

- ❌ Simple sequential teams (doesn't leverage SDK)
- ❌ Single-agent with coordination (overhead without benefit)
- ❌ Fixed workflows (agents aren't autonomous)

---

**Next Steps**: Implement test harness for these 3 patterns and measure their effectiveness.
