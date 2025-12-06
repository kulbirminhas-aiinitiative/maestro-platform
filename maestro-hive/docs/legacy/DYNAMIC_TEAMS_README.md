# Dynamic Team Management System

A comprehensive system for managing dynamic software development teams with intelligent scaling, performance-based management, and real-world scenario handling.

## Overview

This system enables teams to:
- **Scale dynamically** from 2 to 11+ members based on needs
- **Manage performance** with automatic detection and replacement of underperformers
- **Optimize costs** by moving idle members to standby
- **Handle emergencies** by rapidly assembling specialized teams
- **Rotate members** based on SDLC phases
- **Share resources** across multiple projects

## Architecture

### Core Components

1. **DynamicTeamManager** (`dynamic_team_manager.py`)
   - Main orchestrator for all team operations
   - Handles adding, removing, replacing team members
   - Manages member lifecycle states
   - Integrates performance metrics and composition policies

2. **PerformanceMetricsAnalyzer** (`performance_metrics.py`)
   - Tracks individual agent performance (0-100 scores)
   - Monitors team health metrics
   - Detects underperformers automatically
   - Provides scaling recommendations

3. **TeamCompositionPolicy** (`team_composition_policies.py`)
   - Defines optimal team sizes for different project types
   - Phase-based team requirements
   - Progressive scaling plans
   - Minimum viable teams

4. **TeamScenarioHandler** (`team_scenarios.py`)
   - Implements 8 real-world scenarios
   - Reusable scenario patterns
   - Production-ready handlers

5. **Team Membership Model** (`persistence/models.py`)
   - Tracks member lifecycle (initializing → active → standby → retired)
   - Performance metrics storage
   - State transition history

## Member States

Members can be in one of 6 states:

| State | Description | When Used |
|-------|-------------|-----------|
| `INITIALIZING` | Member is being onboarded | Just added to team |
| `ACTIVE` | Actively working on tasks | Primary phase members |
| `ON_STANDBY` | Available but not actively working | Supporting roles, between phases |
| `RETIRED` | No longer needed | Phase complete, no longer required |
| `SUSPENDED` | Temporarily suspended | Performance issues |
| `REASSIGNED` | Moved to another team | Cross-project sharing |

## Project Types and Team Sizes

| Project Type | Min Team | Optimal Team | Duration | Example |
|--------------|----------|--------------|----------|---------|
| Bug Fix | 2 | 3 | 3 days | Simple backend bug |
| Simple Feature | 5 | 6 | 14 days | Add new API endpoint |
| Medium Feature | 7 | 9 | 30 days | User authentication |
| Complex Feature | 11 | 11 | 60 days | Payment integration |
| Full SDLC | 11 | 11 | 90 days | New product launch |
| Security Patch | 4 | 5 | 2 days | CVE fix |
| Emergency | 3 | 4 | 1 day | Production incident |

## Real-World Scenarios

### 1. Progressive Team Scaling (2→4+ members)

**Context**: Bug fix turns into a feature

```python
handler = TeamScenarioHandler(team_manager)
result = await handler.scenario_progressive_scaling()
```

**Flow**:
1. Start with 2 members (backend dev + QA)
2. Discover it needs UI changes
3. Add frontend dev + UI/UX designer
4. Scale to full team if complexity grows

### 2. Phase-Based Rotation

**Context**: Full SDLC with phase transitions

```python
result = await handler.scenario_phase_based_rotation()
```

**Flow**:
- **Requirements**: Analyst + UX (active), Architect (standby)
- **Design**: Architect (active), Analyst (standby)
- **Implementation**: Devs (active), Architect + QA (standby)
- **Testing**: QA (active), Devs (on-call)
- **Deployment**: DevOps + Deployment (active)

### 3. Performance-Based Removal

**Context**: Member consistently underperforming

```python
result = await handler.scenario_performance_based_removal()
```

**Actions**:
- Score 50-60: Monitor for improvement
- Score 30-50: Move to standby
- Score <30: Replace with new member

### 4. Emergency Escalation

**Context**: Critical security incident

```python
result = await handler.scenario_emergency_escalation()
```

**Actions**:
1. Immediately add security specialist + deployment specialist
2. Put feature work on hold
3. Reassign developers to security patch

### 5. Skill-Based Dynamic Composition

**Context**: Different projects need different teams

```python
result = await handler.scenario_skill_based_composition()
```

Demonstrates optimal team for:
- Bug fixes (2-3 people)
- Features (5-9 people)
- Security patches (4-5 people)

### 6. Workload-Based Auto-Scaling

**Context**: Task queue growing

```python
result = await handler.scenario_workload_autoscaling()
```

**Triggers**:
- Ready tasks > 10
- Capacity utilization > 90%

**Actions**:
- Activate standby members
- Add new members if needed

### 7. Cost Optimization During Idle

**Context**: Waiting for external dependency

```python
result = await handler.scenario_cost_optimization_idle()
```

**Actions**:
1. Move most members to standby
2. Keep 1 coordinator active to monitor
3. Reactivate when dependency resolved

### 8. Cross-Project Resource Sharing

**Context**: 1 specialist, 3 projects

```python
result = await handler.scenario_cross_project_sharing()
```

**Strategy**:
- Queue-based allocation
- Time-boxed assignments (2 hours per project)
- Priority-ordered rotation

## Performance Scoring

Individual agents are scored on 4 dimensions:

### 1. Task Completion (40% weight)
- Percentage of tasks completed
- Score = completion rate (0-100)

### 2. Speed (30% weight)
- Task duration vs team average
- Faster = higher score
- Slower = lower score

### 3. Quality (20% weight)
- Based on failure rate
- <5% failures = 100 points
- >30% failures = <50 points

### 4. Collaboration (10% weight)
- Message engagement
- Team participation
- 0-100 score

**Overall Score**: Weighted average of all 4 dimensions

### Performance Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Overall score | < 60 | Flag as underperformer |
| Completion rate | < 50% | Issue identified |
| Failure rate | > 30% | Quality concern |
| Collaboration | < 40 | Low engagement |
| Task duration | > 2x average | Speed concern |

## Usage Examples

### Basic Usage

```python
from dynamic_team_manager import DynamicTeamManager
from team_composition_policies import ProjectType

# Initialize
manager = DynamicTeamManager(
    team_id="my_team",
    state_manager=state_manager,
    project_type=ProjectType.MEDIUM_FEATURE
)

# Initialize team for project
await manager.initialize_team_for_project(
    ProjectType.MEDIUM_FEATURE,
    use_minimal_team=True  # Start with minimum viable team
)

# Add a member
await manager.add_member(
    persona_id="security_specialist",
    reason="Security review needed",
    auto_activate=True
)

# Evaluate performance
evaluation = await manager.evaluate_team_performance()

# Handle underperformers
result = await manager.handle_underperformers(auto_replace=True)

# Auto-scale based on workload
await manager.auto_scale_by_workload()
```

### Phase Transitions

```python
from team_organization import SDLCPhase

# Scale team for design phase
await manager.scale_team_for_phase(SDLCPhase.DESIGN)

# This will:
# - Activate architect and security specialist
# - Move requirement analyst to standby
# - Keep other members as needed
```

### Member Lifecycle Management

```python
# Add member
await manager.add_member("backend_developer", "New feature work")

# Activate member
await manager.activate_member(agent_id, "Phase started")

# Put on standby
await manager.put_on_standby(agent_id, "Phase complete")

# Retire member
await manager.retire_member(agent_id, "No longer needed")

# Replace underperformer
await manager.replace_member(agent_id, "Low performance")
```

## Running the Demo

### Interactive Demo (All Scenarios)

```bash
cd examples/sdlc_team
python demo_dynamic_teams.py
```

Choose from menu:
- 1-8: Run individual scenario
- all: Run all scenarios
- q: Quit

### Quick Demo (3 Key Scenarios)

```bash
python demo_dynamic_teams.py quick
```

Shows:
1. Progressive scaling
2. Phase-based rotation (2 phases)
3. Emergency escalation

### Comparison Demo

```bash
python demo_dynamic_teams.py compare
```

Compares team compositions for different project types.

## Integration with SDLC Coordinator

The DynamicTeamManager can be integrated with SDLCTeamCoordinator:

```python
from sdlc_coordinator import SDLCTeamCoordinator
from dynamic_team_manager import DynamicTeamManager

# Create coordinator
coordinator = await create_sdlc_team("My Project")

# Add dynamic team manager
dynamic_manager = DynamicTeamManager(
    team_id=coordinator.team_id,
    state_manager=coordinator.state,
    project_type=ProjectType.MEDIUM_FEATURE
)

# Use both together
await dynamic_manager.initialize_team_for_project(
    ProjectType.MEDIUM_FEATURE
)

# Start workflow
await coordinator.create_project_workflow(
    workflow_type="feature",
    feature_name="User Authentication"
)

# Handle team scaling as workflow progresses
await coordinator.start_phase(SDLCPhase.REQUIREMENTS)
await dynamic_manager.scale_team_for_phase(SDLCPhase.REQUIREMENTS)
```

## Key Design Principles

### 1. Just-in-Time Scaling
Don't start with full team. Add members as needed.

### 2. Performance-Driven
Automatically detect and handle underperformers.

### 3. Cost-Optimized
Minimize active members, maximize standby usage.

### 4. Phase-Aware
Different phases need different team compositions.

### 5. Emergency-Ready
Can rapidly assemble specialized teams.

### 6. Data-Driven
All decisions based on metrics, not gut feel.

## Future Enhancements

Potential areas for expansion:

1. **Machine Learning**: Predict optimal team size based on historical data
2. **Skill Matching**: Match tasks to members based on skill proficiency
3. **Workload Prediction**: Forecast scaling needs in advance
4. **Cost Modeling**: Actual dollar cost calculations
5. **Multi-Team Optimization**: Optimize resources across multiple teams
6. **External Resource Integration**: Hire contractors dynamically
7. **Performance Trends**: Track performance over time

## Files Created

| File | Purpose |
|------|---------|
| `persistence/models.py` | Added TeamMembership and MembershipState |
| `persistence/state_manager.py` | Added member management methods |
| `performance_metrics.py` | Performance scoring and analysis |
| `team_composition_policies.py` | Team size policies and templates |
| `dynamic_team_manager.py` | Main orchestrator |
| `team_scenarios.py` | 8 real-world scenario handlers |
| `demo_dynamic_teams.py` | Interactive demo |
| `DYNAMIC_TEAMS_README.md` | This file |

## Summary

This dynamic team management system provides:

✅ **8 Real-World Scenarios** - Production-ready patterns
✅ **Intelligent Auto-Scaling** - Workload and phase-based
✅ **Performance Management** - Automatic detection and replacement
✅ **Cost Optimization** - Minimize idle resources
✅ **Flexible Composition** - 2 to 11+ members
✅ **Complete Lifecycle** - From initialization to retirement
✅ **Production-Ready** - Persistent state, metrics, RBAC

Use this system to manage software development teams dynamically, efficiently, and intelligently.
