# SDK-Based Team Patterns

**Production-ready team patterns using Claude Team SDK properly**

Each pattern leverages the SDK's unique capabilities:
- TeamCoordinator with MCP server
- TeamAgent base class
- 12 coordination tools (messages, knowledge, voting, etc.)
- Autonomous agent behavior

---

## 🎯 Available Patterns

### 1. Autonomous Swarm 🐝

**Pattern**: Multiple similar agents autonomously claim tasks and share discoveries

**File**: `pattern_autonomous_swarm.py`

**Usage**:
```bash
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "Research authentication security for microservices" \
    --agents 5 \
    --output ./output/swarm
```

**How it works**:
1. Creates N research agents (all same role)
2. Breaks requirement into research subtasks
3. Agents autonomously claim tasks from queue
4. Each shares findings via `share_knowledge`
5. Synthesizer compiles collective intelligence

**SDK Features**:
- ✅ `claim_task` - Autonomous task claiming
- ✅ `share_knowledge` - Collective intelligence
- ✅ `get_knowledge` - Synthesis
- ✅ Parallel execution

**Output**:
- Individual research files
- `SWARM_SYNTHESIS.md` - Integrated findings
- Knowledge items shared by all agents

**Best For**:
- Parallel research
- Multi-topic exploration
- Collective intelligence tasks

---

### 2. Democratic Decision Making 🗳️

**Pattern**: Team proposes solutions, discusses, votes democratically

**File**: `pattern_democratic_decision.py`

**Usage**:
```bash
python examples/sdk_patterns/pattern_democratic_decision.py \
    --requirement "Choose database for high-traffic API" \
    --roles architect backend frontend qa \
    --output ./output/decision
```

**How it works**:
1. Each team member proposes solution from their perspective
2. Team discusses via messages
3. All members vote on all proposals
4. Winning proposal is implemented
5. Creates decision record

**SDK Features**:
- ✅ `propose_decision` - Democratic proposals
- ✅ `vote_decision` - Voting mechanism
- ✅ `post_message` / `get_messages` - Discussion
- ✅ Consensus building

**Output**:
- `DECISION_RECORD.md` - What was decided and why
- `IMPLEMENTATION_PLAN.md` - How to implement
- `VOTING_SUMMARY.md` - Full voting breakdown

**Best For**:
- Architecture decisions
- Technology choices
- Design alternatives
- Critical decisions requiring consensus

---

### 3. Knowledge Pipeline 🔄

**Pattern**: Sequential stages where each builds on previous knowledge

**File**: `pattern_knowledge_pipeline.py`

**Usage**:
```bash
python examples/sdk_patterns/pattern_knowledge_pipeline.py \
    --requirement "Build payment processing API" \
    --stages research design implement test \
    --output ./output/pipeline
```

**How it works**:
1. Stage 1 (Research): Creates research artifacts
2. Stage 2 (Design): Builds on research
3. Stage 3 (Implement): Uses design
4. Stage 4 (Test): Tests implementation
5. Each shares knowledge for next stage

**SDK Features**:
- ✅ `share_knowledge` - Knowledge accumulation
- ✅ `store_artifact` - Artifact pipeline
- ✅ `get_knowledge` / `get_artifacts` - Context building
- ✅ Sequential coordination

**Output**:
- Research findings
- Architecture design
- Implementation code
- Test suites
- Cumulative knowledge across stages

**Best For**:
- SDLC workflows
- Sequential value addition
- Context-dependent stages
- Knowledge accumulation

---

### 4. Ask-the-Expert 🎓

**Pattern**: Generalist consults specialists for complex questions

**File**: `pattern_ask_expert.py`

**Usage**:
```bash
python examples/sdk_patterns/pattern_ask_expert.py \
    --requirement "Build secure REST API with payment processing" \
    --experts security performance database \
    --output ./output/expert
```

**How it works**:
1. Generalist analyzes requirement
2. Identifies areas needing expertise
3. Asks specific questions to experts
4. Experts respond with detailed guidance
5. Generalist integrates advice

**SDK Features**:
- ✅ `post_message` with `to_agent` - Direct messaging
- ✅ `get_messages` - Q&A coordination
- ✅ Expert consultation pattern
- ✅ Async communication

**Output**:
- `SOLUTION_DESIGN.md` - Integrated solution
- `EXPERT_CONSULTATIONS.md` - Q&A summary
- `IMPLEMENTATION_PLAN.md` - Actionable steps
- Expert conversation log

**Best For**:
- Complex requirements needing multiple expertise
- Mixed skill requirements
- Consultation workflows
- Expert guidance integration

---

## 📊 Pattern Comparison

| Pattern | Coordination | Parallelism | Complexity | Output Type |
|---------|-------------|-------------|------------|-------------|
| **Autonomous Swarm** | Low (task queue) | High | Low | Research reports |
| **Democratic Decision** | High (discussion+voting) | Low | Medium | Decision records |
| **Knowledge Pipeline** | Medium (sequential) | None | Medium | Multi-stage deliverables |
| **Ask-the-Expert** | Medium (Q&A) | Medium | Low | Expert-guided solution |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install SDK
pip install -e ".[all]"

# Set API key
export ANTHROPIC_API_KEY="your-key"
```

### Run a Pattern

```bash
# Swarm pattern
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "Research JWT authentication" \
    --agents 3 \
    --output ./test_swarm

# Decision pattern
python examples/sdk_patterns/pattern_democratic_decision.py \
    --requirement "Choose CI/CD platform" \
    --roles architect devops \
    --output ./test_decision

# Pipeline pattern
python examples/sdk_patterns/pattern_knowledge_pipeline.py \
    --requirement "Build user management API" \
    --stages research design implement \
    --output ./test_pipeline

# Expert pattern
python examples/sdk_patterns/pattern_ask_expert.py \
    --requirement "Optimize database queries" \
    --experts database performance \
    --output ./test_expert
```

---

## 🎭 When to Use Each Pattern

### Use Autonomous Swarm when:
- ✅ You have multiple independent research tasks
- ✅ Speed through parallelism is important
- ✅ You want collective intelligence
- ✅ Tasks can be done independently

### Use Democratic Decision when:
- ✅ Multiple valid solutions exist
- ✅ Team consensus is critical
- ✅ Diverse perspectives needed
- ✅ Decision requires buy-in

### Use Knowledge Pipeline when:
- ✅ Work flows through distinct stages
- ✅ Later stages depend on earlier ones
- ✅ Context accumulates through process
- ✅ Following SDLC or similar workflow

### Use Ask-the-Expert when:
- ✅ Requirement needs multiple specialties
- ✅ Some areas require deep expertise
- ✅ Generalist can handle most, but not all
- ✅ Expert consultation adds value

---

## 🔍 SDK Features Used by Each Pattern

### Autonomous Swarm
```python
# Agents autonomously claim tasks
await coordinator.add_task("Research topic X", required_role="researcher")

# Agents auto-claim in their loop
# (handled by TeamAgent base class with auto_claim_tasks=True)

# Share discoveries
await agent.share_knowledge("finding_name", "finding_value", "category")

# Synthesize collective knowledge
all_knowledge = coordinator.shared_workspace["knowledge"]
```

### Democratic Decision
```python
# Propose solution
await agent.propose_decision(
    decision="Use PostgreSQL",
    rationale="Detailed reasoning..."
)

# Discuss
await agent.post_message("all", "My thoughts on proposal X...")

# Vote
await agent.vote_decision(decision_id, "approve")

# Implement consensus
winning = max(decisions, key=lambda d: approval_count(d))
```

### Knowledge Pipeline
```python
# Stage 1: Research
await research_agent.share_knowledge("requirements", findings)

# Stage 2: Design (uses Stage 1)
requirements = await design_agent.get_knowledge("requirements")
await design_agent.share_knowledge("architecture", design)

# Stage 3: Implementation (uses Stage 2)
architecture = await dev_agent.get_knowledge("architecture")
# ... and so on
```

### Ask-the-Expert
```python
# Ask expert
await generalist.post_message(
    to_agent="security_expert",
    message="What's the best approach for JWT validation?"
)

# Expert responds
await expert.post_message(
    to_agent="generalist",
    message="Use RS256 with public key verification because..."
)

# Generalist integrates
responses = await generalist.get_messages()
```

---

## 📈 Expected Outputs

### Autonomous Swarm
```
output/
├── research_topic1.md          # Individual research
├── research_topic2.md
├── research_topic3.md
├── SWARM_SYNTHESIS.md          # Collective intelligence
└── swarm_results.json          # Metrics
```

### Democratic Decision
```
output/
├── DECISION_RECORD.md          # What was decided
├── IMPLEMENTATION_PLAN.md      # How to implement
├── VOTING_SUMMARY.md           # Vote breakdown
└── decision_results.json       # Metrics
```

### Knowledge Pipeline
```
output/
├── research_findings.md        # Stage 1
├── architecture_design.md      # Stage 2
├── implementation/             # Stage 3
│   ├── src/
│   └── config/
├── tests/                      # Stage 4
└── pipeline_results.json       # Metrics
```

### Ask-the-Expert
```
output/
├── SOLUTION_DESIGN.md          # Integrated solution
├── EXPERT_CONSULTATIONS.md     # Q&A summary
├── IMPLEMENTATION_PLAN.md      # Action items
├── expert_conversations.json   # Full Q&A log
└── expert_results.json         # Metrics
```

---

## 🧪 Testing Patterns

### Test All Patterns
```bash
# Run each pattern with simple test case
./test_all_patterns.sh
```

### Individual Pattern Testing
```bash
# Test with small scope
python pattern_autonomous_swarm.py \
    --requirement "Research Python async patterns" \
    --agents 2 \
    --output /tmp/test

# Verify output
ls /tmp/test/
cat /tmp/test/SWARM_SYNTHESIS.md
```

---

## 🔧 Customization

### Add New Pattern

1. Create `pattern_your_name.py`
2. Use TeamCoordinator + TeamAgent
3. Leverage SDK coordination tools
4. Follow pattern template:

```python
from src.claude_team_sdk import TeamAgent, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig

class YourAgent(TeamAgent):
    def __init__(self, agent_id, coordination_server):
        config = AgentConfig(...)
        super().__init__(config, coordination_server)

    async def execute_task(self, task_description):
        # Your logic using SDK tools
        pass

async def run_your_pattern(requirement, output_dir):
    coordinator = TeamCoordinator(TeamConfig(...))
    coord_server = coordinator.create_coordination_server()

    # Create agents
    # Execute pattern
    # Return results
```

---

## 📚 Related Documentation

- [SDK Capabilities Analysis](../../docs/team_architecture/SDK_CAPABILITIES_ANALYSIS.md)
- [Team Coordinator Source](../../src/claude_team_sdk/coordination/team_coordinator.py)
- [Pattern Experiments](../pattern_experiments/) - Experimental versions

---

## 🐛 Troubleshooting

### "No tasks claimed"
- Check `required_role` matches agent role
- Ensure `auto_claim_tasks=True` for autonomous agents
- Verify tasks added before agents start

### "No messages received"
- Check `to_agent` parameter is correct agent ID
- Use `get_messages` with sufficient limit
- Verify agents initialized before messaging

### "Knowledge not found"
- Ensure `share_knowledge` called before `get_knowledge`
- Check key name spelling
- Knowledge persists in coordinator's shared_workspace

### "Votes not recorded"
- Verify decision_id is correct
- Ensure `propose_decision` was called first
- Check decision exists in coordinator.shared_workspace["decisions"]

---

**Last Updated**: 2025-10-04
**Status**: All 4 core patterns implemented and tested
