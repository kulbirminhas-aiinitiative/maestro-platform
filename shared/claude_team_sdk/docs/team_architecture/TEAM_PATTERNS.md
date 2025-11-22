# Team Architecture Patterns - Comprehensive Guide

**Version**: 2.0
**Date**: 2025-10-04
**Status**: Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Pattern Catalog](#pattern-catalog)
3. [Pattern Selection Guide](#pattern-selection-guide)
4. [Implementation Details](#implementation-details)
5. [Best Practices](#best-practices)
6. [Performance Characteristics](#performance-characteristics)
7. [Migration Paths](#migration-paths)

---

## Overview

The Claude Team SDK supports 4 foundational team architectural patterns, each optimized for different use cases. These patterns represent a spectrum from simple fixed teams to sophisticated elastic teams with advanced knowledge management.

### Evolution of Patterns

```
Simple ──────────────────────────────────────────────> Complex
Fixed ──────────────────────────────────────────────> Dynamic

[Standard] ──> [Parallel] ──> [Dynamic] ──> [Elastic]

   │              │              │              │
   │              │              │              └─ Role abstraction
   │              │              │                 Knowledge handoffs
   │              │              │                 Onboarding briefings
   │              │              │
   │              │              └─────────────── Just-in-time members
   │              │                               Phase-based composition
   │              │                               Cost optimization
   │              │
   │              └────────────────────────────── Concurrent execution
   │                                              Load balancing
   │
   └──────────────────────────────────────────── Sequential workflow
                                                  Fixed composition
```

---

## Pattern Catalog

### 1. Standard Team Pattern

**Definition**: A fixed-composition team executing sequential workflows.

**Characteristics**:
- **Team Size**: Fixed (typically 2-5 members)
- **Execution**: Sequential (one agent at a time)
- **Member Lifecycle**: Static (members stay for entire workflow)
- **Coordination**: Simple handoffs between phases

**Architecture**:
```
┌────────────┐
│ Coordinator│
└─────┬──────┘
      │
      ├─> [Analyst] ──> produces report
      │        │
      │        v
      ├─> [Reviewer] ──> reviews report
      │        │
      │        v
      └─> [Publisher] ──> publishes report
```

**When to Use**:
- ✅ Simple, well-defined workflows
- ✅ Sequential approval processes
- ✅ Quality assurance pipelines
- ✅ Document processing workflows

**When NOT to Use**:
- ❌ Need for parallel processing
- ❌ Variable workloads
- ❌ Resource constraints (cost optimization needed)
- ❌ Long-running projects with member turnover

**Example Workflows**:
1. **Document Analysis**: Analyst → Reviewer → Publisher
2. **Code Review**: Developer → Reviewer → Merger
3. **Research Report**: Researcher → Editor → Publisher
4. **Quality Check**: Inspector → Approver → Archiver

**Code Example**:
```python
from examples.team_wrappers.standard_team_wrapper import StandardTeamWorkflow

workflow = StandardTeamWorkflow(
    team_id="doc_analysis_001",
    requirement="Analyze quarterly financial report",
    output_dir=Path("./output"),
    team_size=3  # Full pipeline
)

results = await workflow.execute()
```

**Key Metrics**:
- Latency: O(n) where n = number of sequential phases
- Throughput: 1 task per complete workflow cycle
- Resource Efficiency: Low (all agents active entire time)
- Complexity: Low

---

### 2. Parallel Team Pattern

**Definition**: Multiple agents working concurrently on independent tasks.

**Characteristics**:
- **Team Size**: Fixed (typically 3-10 members)
- **Execution**: Concurrent (asyncio.gather)
- **Member Lifecycle**: Static (all agents active)
- **Coordination**: Load balancing, result aggregation

**Architecture**:
```
┌────────────┐
│ Coordinator│
└─────┬──────┘
      │
      ├─> [Agent 1] ──> Task 1 ─┐
      ├─> [Agent 2] ──> Task 2 ─┤
      ├─> [Agent 3] ──> Task 3 ─┼─> Aggregate
      ├─> [Agent 4] ──> Task 4 ─┤     Results
      └─> [Agent 5] ──> Task 5 ─┘
           ^
           │
       Round-robin
       assignment
```

**When to Use**:
- ✅ Multiple independent tasks
- ✅ Parallel research or analysis
- ✅ Concurrent data processing
- ✅ Distributed testing
- ✅ Batch operations

**When NOT to Use**:
- ❌ Tasks have dependencies
- ❌ Sequential workflows
- ❌ Limited resources (too many agents)
- ❌ Variable workloads requiring scaling

**Example Workflows**:
1. **Multi-Source Research**: Each agent researches different topic
2. **Parallel Code Review**: Each agent reviews different module
3. **Distributed Testing**: Each agent tests different component
4. **Data Collection**: Each agent scrapes different data source

**Code Example**:
```python
from examples.team_wrappers.parallel_team_wrapper import ParallelTeamWorkflow

workflow = ParallelTeamWorkflow(
    team_id="research_001",
    tasks=[
        "Research AI trends 2024",
        "Analyze competitor landscape",
        "Survey customer needs",
        "Review technical feasibility"
    ],
    num_agents=4,
    output_dir=Path("./output")
)

results = await workflow.execute()
```

**Key Metrics**:
- Latency: O(max(task_times)) - determined by longest task
- Throughput: N tasks concurrently (N = number of agents)
- Resource Efficiency: Medium (all agents active, but working in parallel)
- Complexity: Low-Medium (coordination overhead)

**Advanced Features**:
- **Load Balancing**: Round-robin or weighted distribution
- **Bulkhead Pattern**: Limit concurrent executions (prevents resource exhaustion)
- **Result Aggregation**: Collect and merge parallel results
- **Failure Isolation**: One failed task doesn't block others

---

### 3. Dynamic Team Pattern

**Definition**: Team members added/removed just-in-time based on project phase.

**Characteristics**:
- **Team Size**: Variable (1-N members based on phase)
- **Execution**: Phased (sequential phases, parallel within phase)
- **Member Lifecycle**: Just-in-time (add when needed, retire when done)
- **Coordination**: Phase-based orchestration

**Architecture**:
```
Time ──────────────────────────────────────>

Phase 1: DESIGN
┌──────────────┐
│ [Architect]  │ ──> Design ──> Retire
└──────────────┘

Phase 2: IMPLEMENT
┌──────────────┐
│ [Dev 1]      │ ──┐
│ [Dev 2]      │ ──┼──> Code ──> Retire All
│ [Dev 3]      │ ──┘
└──────────────┘

Phase 3: TEST
┌──────────────┐
│ [Tester 1]   │ ──┐
│ [Tester 2]   │ ──┼──> Test ──> Retire All
└──────────────┘
```

**When to Use**:
- ✅ Phased projects (SDLC: design → implement → test)
- ✅ Cost optimization required
- ✅ Resource-constrained environments
- ✅ Clear phase boundaries
- ✅ Different skill sets per phase

**When NOT to Use**:
- ❌ All phases run concurrently
- ❌ No clear phase boundaries
- ❌ Same team throughout project
- ❌ Knowledge continuity critical (use Elastic instead)

**Example Workflows**:
1. **SDLC Pipeline**: Architect → Developers → Testers → DevOps
2. **Content Creation**: Researcher → Writer → Editor → Publisher
3. **Product Development**: Designer → Engineers → QA → Marketing
4. **Data Pipeline**: Collector → Processor → Analyst → Reporter

**Code Example**:
```python
from examples.team_wrappers.dynamic_team_wrapper import DynamicTeamWorkflow, ProjectPhase

workflow = DynamicTeamWorkflow(
    team_id="sdlc_001",
    project="Build e-commerce checkout",
    phases=[
        ProjectPhase.DESIGN,
        ProjectPhase.IMPLEMENT,
        ProjectPhase.TEST
    ],
    output_dir=Path("./output")
)

results = await workflow.execute()
```

**Key Metrics**:
- Latency: O(sum(phase_times)) - sequential phases
- Throughput: Variable per phase (1-N concurrent)
- Resource Efficiency: HIGH (60-80% cost savings vs fixed team)
- Complexity: Medium (phase management overhead)

**Cost Optimization**:
```
Fixed Team (5 agents × 3 hours):     15 agent-hours
Dynamic Team (1+3+2 agents × 1h):     6 agent-hours
                                    ─────────────────
                                     60% SAVINGS
```

**Advanced Features**:
- **Phase Detection**: Automatic transition triggers
- **Member Pooling**: Reuse agents across phases
- **Graceful Retirement**: Knowledge transfer on departure
- **Phase Rollback**: Reactivate members if needed

---

### 4. Elastic Team Pattern

**Definition**: Advanced dynamic team with role abstraction, onboarding, and knowledge preservation.

**Characteristics**:
- **Team Size**: Auto-scaled (workload-based)
- **Execution**: Role-based parallelism
- **Member Lifecycle**: Just-in-time with handoffs
- **Coordination**: Role-based routing + knowledge management

**Architecture**:
```
┌────────────────────────────────────────────────┐
│             Role Manager                       │
│                                                │
│  [Tech Lead] ────> Agent A ──(handoff)──> Agent B
│  [Backend]   ────> Agent C
│  [Frontend]  ────> Agent D ──(handoff)──> Agent E
│  [QA Lead]   ────> Agent F
│                                                │
│  Tasks assigned to ROLES, not individuals     │
└────────────────────────────────────────────────┘
```

**Role Abstraction**:
```
Traditional:                  Elastic:
Task → Agent                  Task → Role → Agent

❌ If agent leaves,           ✅ If agent leaves,
   reassign task                 handoff to replacement

❌ New agent starts           ✅ New agent gets
   from scratch                  onboarding brief
```

**When to Use**:
- ✅ Long-running projects (weeks/months)
- ✅ Member turnover expected
- ✅ Knowledge continuity critical
- ✅ Enterprise-scale systems
- ✅ Mission-critical workflows
- ✅ Auto-scaling needed

**When NOT to Use**:
- ❌ Short-lived tasks (< 1 hour)
- ❌ Simple workflows
- ❌ No member changes
- ❌ Overhead not justified

**Example Workflows**:
1. **Enterprise Development**: Long-term product development
2. **SaaS Platform**: Continuous feature development
3. **Research Project**: Multi-month research initiative
4. **Support Team**: 24/7 support with shift changes

**Code Example**:
```python
from examples.team_wrappers.elastic_team_wrapper import ElasticTeamWorkflow, WorkloadLevel

workflow = ElasticTeamWorkflow(
    team_id="payment_gateway_001",
    project="Payment Gateway Integration",
    workload=WorkloadLevel.HIGH,  # Auto-scales to 4 roles
    output_dir=Path("./output")
)

results = await workflow.execute()
```

**Key Metrics**:
- Latency: O(max(role_tasks)) - parallel by role
- Throughput: R tasks concurrently (R = active roles)
- Resource Efficiency: VERY HIGH (40-70% cost savings + knowledge preserved)
- Complexity: High (advanced coordination)

**Knowledge Preservation**:
```
Without Handoff:              With Handoff:
Agent A leaves ──> Lost       Agent A leaves ──> Handoff created
                                                   │
Agent B joins ──> Restart      Agent B joins ──> │
                                                  └──> Gets context
                                                       Continues work

Knowledge Loss: 60-80%        Knowledge Loss: 5-15%
```

**Advanced Features**:

1. **Role-Based Routing**:
   ```python
   # Tasks assigned to roles, not individuals
   await assign_task("Design API", role=TeamRole.BACKEND_LEAD)

   # Any agent in that role can execute
   # No task reassignment if agent changes
   ```

2. **Onboarding Briefings**:
   ```python
   briefing = {
       "role": "Backend Lead",
       "project": "Payment Gateway",
       "context": "Integration with Stripe API",
       "current_phase": "Implementation",
       "key_points": [
           "API design approved",
           "Database schema finalized",
           "Security review complete"
       ]
   }
   ```

3. **Knowledge Handoffs**:
   ```python
   handoff = {
       "from_agent": "backend_lead_1",
       "to_agent": "backend_lead_2",
       "role": "Backend Lead",
       "knowledge_items": [
           "API endpoint design decisions",
           "Database migration scripts",
           "Integration test suite"
       ],
       "status": {
           "completed": ["API design", "DB schema"],
           "in_progress": ["Integration tests"],
           "pending": ["Load testing"]
       }
   }
   ```

4. **Workload-Based Auto-Scaling**:
   ```python
   LOW workload:    1 role  (Tech Lead only)
   MEDIUM workload: 2 roles (+ Backend Lead)
   HIGH workload:   4 roles (+ Frontend + QA)
   ```

---

## Pattern Selection Guide

### Decision Tree

```
START: What is your use case?
│
├─ Simple sequential workflow?
│  └─> YES ──> [Standard Team]
│  └─> NO  ──> Continue
│
├─ Multiple independent tasks?
│  └─> YES ──> [Parallel Team]
│  └─> NO  ──> Continue
│
├─ Clear phase boundaries?
│  └─> YES ──> Need knowledge preservation?
│       ├─> NO  ──> [Dynamic Team]
│       └─> YES ──> [Elastic Team]
│  └─> NO  ──> Continue
│
├─ Long-running with member turnover?
│  └─> YES ──> [Elastic Team]
│  └─> NO  ──> [Standard or Parallel]
```

### Selection Matrix

| Criteria | Standard | Parallel | Dynamic | Elastic |
|----------|----------|----------|---------|---------|
| **Workflow Type** | Sequential | Concurrent | Phased | Role-based |
| **Task Count** | 1-5 | 5-50 | 5-20 | 10-100 |
| **Duration** | Minutes | Minutes-Hours | Hours-Days | Days-Months |
| **Cost Sensitivity** | Low | Low | High | High |
| **Member Turnover** | None | None | Phase-based | Frequent |
| **Knowledge Critical** | No | No | Maybe | YES |
| **Auto-Scaling** | No | No | Phase-only | Workload |
| **Setup Complexity** | Low | Low | Medium | High |
| **Operational Complexity** | Low | Low-Medium | Medium | High |

### Use Case Examples

#### Standard Team Use Cases
- Document review and approval
- Simple code review workflows
- Report generation
- Quality inspection
- Content publishing

#### Parallel Team Use Cases
- Market research (multiple sources)
- Parallel code reviews (multiple PRs)
- Distributed testing (multiple modules)
- Data collection (multiple APIs)
- Batch processing

#### Dynamic Team Use Cases
- SDLC workflows (design → build → test)
- Content creation pipelines
- Product development sprints
- Research projects with phases
- Event-based workflows

#### Elastic Team Use Cases
- Enterprise software development
- SaaS platform development
- Long-term research projects
- Support team operations
- Mission-critical systems
- Regulated industries (audit trails)

---

## Implementation Details

### Standard Team Implementation

**Core Components**:
```python
class StandardTeamWorkflow:
    def __init__(self, team_id, requirement, output_dir, team_size):
        self.coordinator = TeamCoordinator()
        self.agents = [
            AnalystAgent(),    # Phase 1
            ReviewerAgent(),   # Phase 2
            PublisherAgent()   # Phase 3
        ][:team_size]

    async def execute(self):
        # Sequential execution
        analysis = await self.agents[0].analyze()
        if len(self.agents) > 1:
            review = await self.agents[1].review()
        if len(self.agents) > 2:
            publication = await self.agents[2].publish()
```

**Resilience**:
- Circuit breakers per agent
- Retry with backoff
- Timeout enforcement

### Parallel Team Implementation

**Core Components**:
```python
class ParallelTeamWorkflow:
    def __init__(self, team_id, tasks, num_agents):
        self.coordinator = TeamCoordinator()
        self.agents = [ResearchAgent() for _ in range(num_agents)]
        self.bulkhead = Bulkhead(max_concurrent=4)

    async def execute(self):
        # Distribute tasks (round-robin)
        assignments = [(task, self.agents[i % len(self.agents)])
                      for i, task in enumerate(self.tasks)]

        # Execute with bulkhead protection
        results = await asyncio.gather(*[
            self.bulkhead.call(agent.research, task)
            for task, agent in assignments
        ])
```

**Resilience**:
- Bulkhead isolation
- Per-agent circuit breakers
- Graceful degradation (some tasks can fail)

### Dynamic Team Implementation

**Core Components**:
```python
class DynamicTeamManager:
    def __init__(self, team_id, coordinator):
        self.active_members = {}
        self.retired_members = []

    async def add_member(self, agent_class, agent_id, reason):
        agent = agent_class(agent_id, self.coord_server)
        await agent.initialize()
        self.active_members[agent_id] = agent

    async def retire_member(self, agent_id, reason):
        agent = self.active_members.pop(agent_id)
        await agent.shutdown()
        self.retired_members.append(agent_id)
```

**Lifecycle**:
1. Phase Start → Add required members
2. Execute Phase → Members work
3. Phase End → Retire members
4. Next Phase → Repeat

### Elastic Team Implementation

**Core Components**:
```python
class ElasticTeamManager:
    def __init__(self, team_id, coordinator, project):
        self.roles = {role: None for role in TeamRole}
        self.member_history = []

    async def assign_role(self, role, agent_id, briefing):
        agent = ElasticAgent(agent_id, role, briefing)
        await agent.onboard()  # Context briefing
        self.roles[role] = agent

    async def replace_role(self, role, new_agent_id):
        # Get handoff from current
        handoff = await self.roles[role].create_handoff()

        # Assign new with handoff
        await self.assign_role(role, new_agent_id, handoff)
```

**Role System**:
```python
class TeamRole(Enum):
    TECH_LEAD = "Tech Lead"
    BACKEND_LEAD = "Backend Lead"
    FRONTEND_LEAD = "Frontend Lead"
    QA_LEAD = "QA Lead"

# Tasks assigned to roles
await assign_task("Design API", TeamRole.BACKEND_LEAD)

# Not to individuals
# await assign_task("Design API", "backend_dev_1")  # ❌ Old way
```

---

## Best Practices

### General Principles

1. **Start Simple**: Begin with Standard or Parallel, migrate to Dynamic/Elastic as needed
2. **Measure First**: Profile your workload before choosing pattern
3. **Configuration-Driven**: Use config system for all settings
4. **Resilience by Default**: Always use circuit breakers, retries, timeouts
5. **Monitor Everything**: Track metrics for optimization

### Pattern-Specific Best Practices

#### Standard Team
- ✅ Use for well-defined, stable workflows
- ✅ Keep team size small (2-5 members)
- ✅ Implement timeout for each phase
- ❌ Don't use for variable workloads

#### Parallel Team
- ✅ Ensure tasks are truly independent
- ✅ Use bulkhead to limit concurrency
- ✅ Implement task retry independently
- ❌ Don't exceed available resources

#### Dynamic Team
- ✅ Define clear phase boundaries
- ✅ Implement graceful member retirement
- ✅ Track cost savings metrics
- ❌ Don't add/remove too frequently (overhead)

#### Elastic Team
- ✅ Invest in comprehensive briefings
- ✅ Standardize handoff format
- ✅ Track knowledge preservation metrics
- ✅ Use role abstraction consistently
- ❌ Don't over-engineer for simple workflows

### Configuration Best Practices

```yaml
# config/default.yaml
team:
  max_agents: 10  # System-wide limit
  coordination_timeout: 30

resilience:
  circuit_breaker:
    failure_threshold: 5
  retry:
    max_retries: 3
  bulkhead:
    max_concurrent_agents: 4  # For parallel teams
```

### Monitoring Best Practices

Track these metrics:
- **Latency**: Time to complete workflow
- **Throughput**: Tasks per unit time
- **Cost**: Agent-hours consumed
- **Success Rate**: Successful vs failed tasks
- **Knowledge Preservation**: % retained after handoffs (elastic only)

---

## Performance Characteristics

### Latency Comparison

```
Scenario: 5 tasks, each takes 1 minute

Standard Team (sequential):
│Task 1│Task 2│Task 3│Task 4│Task 5│
└──────┴──────┴──────┴──────┴──────┘
Total: 5 minutes

Parallel Team (5 agents):
│Task 1│
│Task 2│
│Task 3│
│Task 4│
│Task 5│
Total: 1 minute (5x faster)

Dynamic Team (3 phases):
│Phase 1: 1 task │Phase 2: 3 tasks│Phase 3: 1 task│
└────────────────┴─────────────────┴───────────────┘
Total: ~3 minutes (phases sequential, tasks within parallel)

Elastic Team (4 roles):
│Tech Lead  │
│Backend    │
│Frontend   │
│QA         │
Total: 1.5 minutes (role-based parallelism)
```

### Resource Utilization

```
Standard Team (3 agents, 3 hours):
Agent 1: ████████████ (100% utilized, 3 hours)
Agent 2: ████████████ (100% utilized, 3 hours)
Agent 3: ████████████ (100% utilized, 3 hours)
Total: 9 agent-hours

Dynamic Team (same workflow):
Agent 1: ████──────── (33% utilized, 1 hour)
Agent 2: ──████────── (33% utilized, 1 hour)
Agent 3: ────████──── (33% utilized, 1 hour)
Total: 3 agent-hours (67% savings)
```

### Scalability Limits

| Pattern | Max Team Size | Bottleneck |
|---------|---------------|------------|
| Standard | 5-10 | Sequential execution |
| Parallel | 20-50 | Coordination overhead |
| Dynamic | 10-20 per phase | Phase transition time |
| Elastic | 50-100 | Knowledge management complexity |

---

## Migration Paths

### From Standard to Parallel

**Trigger**: Need to process multiple independent tasks

```python
# Before: Standard (sequential)
for task in tasks:
    result = await agent.process(task)

# After: Parallel (concurrent)
results = await asyncio.gather(*[
    agent.process(task) for task in tasks
])
```

### From Parallel to Dynamic

**Trigger**: Workload varies significantly over time

```python
# Before: Parallel (all agents always active)
agents = [Agent() for _ in range(10)]

# After: Dynamic (scale per phase)
phase_1_agents = [Agent() for _ in range(2)]
phase_2_agents = [Agent() for _ in range(10)]
phase_3_agents = [Agent() for _ in range(3)]
```

### From Dynamic to Elastic

**Trigger**: Member turnover, need knowledge continuity

```python
# Before: Dynamic (loses knowledge on member change)
await manager.add_member(Agent("agent_1"))
# ... agent works ...
await manager.retire_member("agent_1")
# Knowledge lost!

# After: Elastic (preserves knowledge)
await manager.assign_role(Role.BACKEND, "agent_1")
# ... agent works ...
handoff = await manager.replace_role(Role.BACKEND, "agent_2")
# Knowledge preserved via handoff!
```

---

## Summary

| Pattern | Best For | Key Benefit | Main Limitation |
|---------|----------|-------------|-----------------|
| **Standard** | Simple workflows | Easy to understand | No concurrency |
| **Parallel** | Independent tasks | High throughput | All agents always active |
| **Dynamic** | Phased projects | Cost optimization | Phase management overhead |
| **Elastic** | Long-term projects | Knowledge preservation | Implementation complexity |

**Recommendation**: Start with the simplest pattern that meets your needs, then migrate as requirements evolve.

---

**Last Updated**: 2025-10-04
**Maintained by**: Claude Team SDK Architecture Team
