# Team Pattern Experiments

**Purpose**: Explore what team patterns the Claude Team SDK actually enables and test their effectiveness.

## 📊 Critical Analysis

See [SDK_CAPABILITIES_ANALYSIS.md](../../docs/team_architecture/SDK_CAPABILITIES_ANALYSIS.md) for complete analysis of:
- What the SDK provides (12 MCP coordination tools)
- What patterns are enabled
- What patterns are NOT supported
- Recommended patterns to implement

## 🧪 Experiments

### Experiment 1: Autonomous Swarm Research ⭐

**File**: `experiment_autonomous_swarm.py`

**Tests**:
- ✅ Autonomous task claiming from queue
- ✅ Parallel execution with multiple similar agents
- ✅ Knowledge sharing via SDK tools
- ✅ Synthesis of collective intelligence

**Run**:
```bash
python examples/pattern_experiments/experiment_autonomous_swarm.py
```

**Expected Output**:
- 5 research agents autonomously claim 5 tasks
- Each shares findings via `share_knowledge`
- Synthesizer compiles all knowledge into final report
- Metrics: completion time, knowledge items, throughput

**Success Criteria**:
- All tasks completed automatically
- Knowledge items > number of tasks (agents share multiple findings)
- Synthesis report integrates all discoveries

---

### Experiment 2: Democratic Architecture Team ⭐

**File**: `experiment_democratic_voting.py`

**Tests**:
- ✅ Multiple proposal submission
- ✅ Team discussion via messages
- ✅ Democratic voting mechanism
- ✅ Consensus achievement

**Run**:
```bash
python examples/pattern_experiments/experiment_democratic_voting.py
```

**Expected Output**:
- 4 agents each propose different architecture
- Discussion via inter-agent messages
- All agents vote on all proposals
- Winning solution identified

**Success Criteria**:
- 4 unique proposals submitted
- Active discussion (10+ messages exchanged)
- All agents vote on all proposals
- Clear winner emerges

---

### Experiment 3: Knowledge Pipeline (TODO)

**File**: `experiment_knowledge_pipeline.py`

**Tests**:
- ✅ Sequential knowledge building
- ✅ Artifact-based handoffs
- ✅ Context preservation across stages
- ✅ Value accumulation through pipeline

**Stages**:
1. Research → creates research artifacts
2. Design → builds on research
3. Implementation → uses design artifacts
4. Testing → validates implementation

---

## 🔑 Key Insights from Analysis

### What Makes SDK Teams Different

Unlike typical frameworks, the SDK enables:

1. **True Autonomy**: Agents claim tasks themselves, not assigned
2. **Persistent Knowledge**: Knowledge base survives across agent lifecycles
3. **Democratic Coordination**: No central controller - team decides via voting
4. **Emergent Behavior**: Swarm intelligence through knowledge sharing

### What the SDK is NOT

- ❌ NOT a workflow engine (no fixed DAGs)
- ❌ NOT hierarchical (no manager assigns tasks)
- ❌ NOT sequential (supports full parallelism)
- ❌ NOT stateless (knowledge persists in workspace)

### Recommended Patterns

Based on SDK strengths:

| Pattern | SDK Alignment | Complexity | Real-World Value |
|---------|---------------|------------|------------------|
| **Autonomous Swarm** | ⭐⭐⭐⭐⭐ | Low | High (parallel research) |
| **Democratic Voting** | ⭐⭐⭐⭐⭐ | Medium | High (architecture decisions) |
| **Knowledge Pipeline** | ⭐⭐⭐⭐ | Medium | High (SDLC) |
| **Ask-the-Expert** | ⭐⭐⭐⭐ | Low | High (specialized consultation) |
| **Assembly Line** | ⭐⭐⭐ | High | Medium (depends on artifacts) |

### Anti-Patterns (Don't Build These)

- ❌ Simple sequential workflows (doesn't leverage SDK)
- ❌ Single agent with coordination overhead
- ❌ Fixed orchestration (defeats autonomous design)
- ❌ Manager-assigns-tasks pattern (use task queue instead)

---

## 📈 Experiment Metrics

### Autonomous Swarm Metrics
- **Completion Time**: Total time from start to all tasks done
- **Throughput**: Tasks completed per second
- **Knowledge Density**: Knowledge items shared per task
- **Utilization**: % of agents that claimed at least one task
- **Synthesis Quality**: Coverage of all agent findings

### Democratic Voting Metrics
- **Proposal Diversity**: How different are the proposals?
- **Discussion Quality**: Messages per proposal
- **Voting Participation**: % of agents who voted
- **Consensus Strength**: Margin of winning vote
- **Implementation Alignment**: Does implementation match vote?

---

## 🚀 Running All Experiments

```bash
# Create output directories
mkdir -p experiments/{swarm_output,voting_output,pipeline_output}

# Run experiments
python examples/pattern_experiments/experiment_autonomous_swarm.py
python examples/pattern_experiments/experiment_democratic_voting.py

# Review results
cat experiments/swarm_output/experiment_results.json
cat experiments/voting_output/experiment_results.json
cat experiments/voting_output/team_discussion.json
```

---

## 🔬 Experiment Design Principles

### 1. Test ONE Capability at a Time
- Swarm → tests autonomous claiming + knowledge sharing
- Voting → tests proposals + voting + discussion
- Pipeline → tests artifacts + sequential building

### 2. Use SDK Tools Correctly
- ✅ Use `claim_task` for autonomous claiming
- ✅ Use `share_knowledge` for persistence
- ✅ Use `propose_decision` + `vote_decision` for consensus
- ✅ Use `post_message` for communication
- ❌ Don't bypass SDK and orchestrate externally

### 3. Measure SDK-Specific Metrics
- Not just "did it work?"
- But "did agents coordinate effectively?"
- Track messages, knowledge, votes, artifacts

### 4. Let Agents be Autonomous
- Minimal external orchestration
- Let agents discover, communicate, decide
- Measure emergent behavior

---

## 🎯 Next Steps

### After Running Experiments

1. **Analyze Results**:
   - Did agents self-organize effectively?
   - Was knowledge sharing meaningful?
   - Did voting produce good decisions?

2. **Identify Improvements**:
   - SDK missing capabilities
   - Agent system prompt improvements
   - Coordination efficiency

3. **Build Real Patterns**:
   - Take successful experiments
   - Create production wrappers
   - Add error handling, resilience
   - Document learnings

---

## 📚 Related Documentation

- [SDK Capabilities Analysis](../../docs/team_architecture/SDK_CAPABILITIES_ANALYSIS.md) - Detailed capability review
- [Team Patterns](../../docs/team_architecture/TEAM_PATTERNS.md) - Pattern documentation
- [TeamCoordinator Source](../../src/claude_team_sdk/coordination/team_coordinator.py) - Implementation details

---

**Last Updated**: 2025-10-04
**Status**: Experiments 1 & 2 ready to run, Experiment 3 TODO
