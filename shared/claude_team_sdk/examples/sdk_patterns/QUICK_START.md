# Quick Start Guide - SDK Team Patterns

**Get started in 5 minutes with production-ready team patterns**

---

## ⚡ Fastest Start

```bash
# 1. Install
pip install -e ".[all]"

# 2. Set API key
export ANTHROPIC_API_KEY="your-key-here"

# 3. Run a pattern
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "Research GraphQL vs REST APIs" \
    --agents 3 \
    --output ./my_first_swarm

# 4. Check results
cat ./my_first_swarm/SWARM_SYNTHESIS.md
```

---

## 📋 Pattern Examples

### 1. Research Multiple Topics (Swarm)

**Use Case**: Need to research 3-5 related topics quickly

```bash
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "Research authentication methods for microservices" \
    --agents 4 \
    --output ./auth_research
```

**What happens**:
- 4 agents autonomously research different aspects
- Each shares findings
- Final synthesis combines all insights

**Check output**:
```bash
ls ./auth_research/
# research_*.md files (individual research)
# SWARM_SYNTHESIS.md (collective intelligence)
# swarm_results.json (metrics)
```

---

### 2. Make Team Decision (Democratic)

**Use Case**: Need to choose between options with team consensus

```bash
python examples/sdk_patterns/pattern_democratic_decision.py \
    --requirement "Choose database for high-traffic e-commerce platform" \
    --roles architect backend qa devops \
    --output ./db_decision
```

**What happens**:
- Each role proposes solution from their perspective
- Team discusses pros/cons via messages
- Everyone votes
- Winning solution documented

**Check output**:
```bash
cat ./db_decision/DECISION_RECORD.md
cat ./db_decision/IMPLEMENTATION_PLAN.md
cat ./db_decision/VOTING_SUMMARY.md
```

---

### 3. Build Complete Project (Pipeline)

**Use Case**: Need end-to-end project from research to tests

```bash
python examples/sdk_patterns/pattern_knowledge_pipeline.py \
    --requirement "Build user authentication API with JWT" \
    --stages research design implement test \
    --output ./auth_api_project
```

**What happens**:
- Stage 1: Research authentication approaches
- Stage 2: Design architecture based on research
- Stage 3: Implement based on design
- Stage 4: Create test suite for implementation

**Check output**:
```bash
tree ./auth_api_project/
# research_findings.md
# architecture_design.md
# implementation files
# test files
```

---

### 4. Get Expert Advice (Ask-Expert)

**Use Case**: Need specialist input on complex requirement

```bash
python examples/sdk_patterns/pattern_ask_expert.py \
    --requirement "Build payment processing system with PCI compliance" \
    --experts security database api \
    --output ./payment_system
```

**What happens**:
- Generalist analyzes requirement
- Asks security expert about PCI compliance
- Asks database expert about sensitive data storage
- Asks API expert about integration patterns
- Integrates all advice into solution

**Check output**:
```bash
cat ./payment_system/SOLUTION_DESIGN.md
cat ./payment_system/EXPERT_CONSULTATIONS.md
```

---

## 🎯 Real-World Examples

### Example 1: Technical Research Sprint

**Scenario**: CTO wants research on adopting GraphQL

```bash
# Swarm researches different angles
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "GraphQL adoption for enterprise - performance, security, migration strategy, tooling, and team training" \
    --agents 5 \
    --output ./graphql_research

# Get consolidated report
cat ./graphql_research/SWARM_SYNTHESIS.md
```

**Result**: Comprehensive research report covering all aspects

---

### Example 2: Architecture Decision

**Scenario**: Team needs to choose microservices communication pattern

```bash
# Democratic decision with full team
python examples/sdk_patterns/pattern_democratic_decision.py \
    --requirement "Choose inter-service communication: REST, gRPC, or message queue" \
    --roles architect backend frontend devops \
    --output ./communication_decision

# Review consensus
cat ./communication_decision/DECISION_RECORD.md
```

**Result**: Documented decision with team buy-in

---

### Example 3: New Feature Development

**Scenario**: Build complete feature from scratch

```bash
# Pipeline from research to code
python examples/sdk_patterns/pattern_knowledge_pipeline.py \
    --requirement "Real-time notification system with WebSockets" \
    --stages research design implement test \
    --output ./notification_system

# Review implementation
ls ./notification_system/
```

**Result**: Complete implementation with tests

---

### Example 4: Complex Problem Solving

**Scenario**: Optimize slow database queries

```bash
# Consult experts for guidance
python examples/sdk_patterns/pattern_ask_expert.py \
    --requirement "Database queries taking 5+ seconds on million-row table" \
    --experts database performance \
    --output ./query_optimization

# Review expert recommendations
cat ./query_optimization/SOLUTION_DESIGN.md
```

**Result**: Expert-guided optimization plan

---

## 🔧 Common Customizations

### More Agents
```bash
# Larger swarm for more coverage
python pattern_autonomous_swarm.py --requirement "..." --agents 8
```

### Different Roles
```bash
# Custom team composition
python pattern_democratic_decision.py \
    --requirement "..." \
    --roles architect security performance
```

### Fewer Stages
```bash
# Just research and design
python pattern_knowledge_pipeline.py \
    --requirement "..." \
    --stages research design
```

### More Experts
```bash
# All available experts
python pattern_ask_expert.py \
    --requirement "..." \
    --experts security performance database api testing
```

---

## 📊 Output Structure

### Every Pattern Creates:
- `*_results.json` - Metrics and summary
- Deliverable files (markdown, code, etc.)
- Pattern-specific outputs

### Swarm Output:
```
output/
├── research_*.md         # Individual research
├── SWARM_SYNTHESIS.md    # Collective report
└── swarm_results.json    # Metrics
```

### Decision Output:
```
output/
├── DECISION_RECORD.md       # What was decided
├── IMPLEMENTATION_PLAN.md   # How to implement
├── VOTING_SUMMARY.md        # Vote breakdown
└── decision_results.json    # Metrics
```

### Pipeline Output:
```
output/
├── [stage 1 files]
├── [stage 2 files]
├── [stage 3 files]
├── [stage 4 files]
└── pipeline_results.json
```

### Expert Output:
```
output/
├── SOLUTION_DESIGN.md           # Integrated solution
├── EXPERT_CONSULTATIONS.md      # Q&A summary
├── expert_conversations.json    # Full conversation
└── expert_results.json          # Metrics
```

---

## 🚨 Troubleshooting

### "ModuleNotFoundError: No module named 'claude_code_sdk'"
```bash
pip install claude-code-sdk
```

### "No API key found"
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "No files created"
- Check API key is valid
- Ensure output directory is writable
- Review console output for errors

### "Agents not claiming tasks"
- Verify `--agents` matches number of tasks
- Check role matches task requirements
- Ensure coordinator is running

---

## 🎓 Next Steps

1. **Run all patterns** - Try each with simple requirements
2. **Check outputs** - Review generated files
3. **Customize** - Adjust agents, roles, stages for your needs
4. **Read details** - See [README.md](README.md) for deep dive
5. **Create patterns** - Build your own patterns

---

## 💡 Pro Tips

**Tip 1**: Start small
```bash
# 2 agents, simple requirement
python pattern_autonomous_swarm.py \
    --requirement "Research Redis caching" \
    --agents 2
```

**Tip 2**: Use descriptive requirements
```bash
# Good: Specific and actionable
--requirement "Compare PostgreSQL vs MongoDB for user analytics with 10M records/day"

# Bad: Too vague
--requirement "Database stuff"
```

**Tip 3**: Match pattern to problem
- Independent tasks → Swarm
- Need consensus → Democratic
- Sequential flow → Pipeline
- Need expertise → Ask-Expert

**Tip 4**: Check results.json for metrics
```bash
cat output/swarm_results.json | jq
```

---

**Ready to build?** Pick a pattern and run it!

```bash
# Your first team
python examples/sdk_patterns/pattern_autonomous_swarm.py \
    --requirement "Your requirement here" \
    --agents 3 \
    --output ./my_output
```
