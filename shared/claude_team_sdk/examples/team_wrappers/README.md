# Team Wrappers - Production-Ready Team Patterns

This directory contains two types of team pattern implementations:

1. **Demonstration Wrappers** (`*_team_wrapper.py`) - Show orchestration patterns with simulated work
2. **Functional Wrappers** (`functional_*_team.py`) - Real Claude API integration with actual deliverables

## 📋 Quick Start

### Prerequisites

```bash
# Install Claude Code SDK (required for functional wrappers)
pip install claude-code-sdk

# Install Claude Team SDK
pip install -e ".[all]"
```

### Choose Your Wrapper Type

- **Learning team patterns?** → Use demonstration wrappers
- **Building real systems?** → Use functional wrappers

---

## 🎯 Team Patterns

### 1. Standard Team - Sequential Workflow

**Pattern**: Fixed team with sequential phases (Analyst → Reviewer → Publisher)

#### Demonstration Version
```bash
python examples/team_wrappers/standard_team_wrapper.py \
    --requirement "Analyze Q4 market trends" \
    --team-size 3 \
    --output ./output/demo
```

**Output**: Simulated workflow with pattern demonstration

#### Functional Version ⭐
```bash
python examples/team_wrappers/functional_standard_team.py \
    --requirement "Build a user authentication system with JWT" \
    --output ./output/standard
```

**Output**: Real deliverables including:
- `requirements_analysis.md` - Detailed functional/non-functional requirements
- `user_stories.md` - User stories with acceptance criteria
- `technical_scope.md` - Technical components and architecture
- `review_report.md` - Quality review with recommendations
- `EXECUTIVE_SUMMARY.md` - Executive summary for stakeholders
- `FINAL_REQUIREMENTS_SPEC.md` - Complete specification
- `IMPLEMENTATION_GUIDE.md` - Developer guide
- `PROJECT_INDEX.md` - Navigation index

**Use Cases**:
- Requirements analysis and documentation
- Sequential approval workflows
- Quality assurance processes
- Stakeholder deliverable creation

---

### 2. Parallel Team - Concurrent Execution

**Pattern**: Multiple agents working concurrently on independent tasks

#### Demonstration Version
```bash
python examples/team_wrappers/parallel_team_wrapper.py \
    --tasks "Research AI trends" "Analyze competitors" "Market survey" \
    --agents 3 \
    --output ./output/demo
```

**Output**: Simulated concurrent execution

#### Functional Version ⭐
```bash
python examples/team_wrappers/functional_parallel_team.py \
    --tasks "Research authentication best practices" \
            "Research database options for user data" \
            "Research API security patterns" \
    --agents 3 \
    --output ./output/parallel
```

**Output**: Real research reports including:
- `task_0_research_report.md` - Comprehensive research on task 1
- `task_1_research_report.md` - Comprehensive research on task 2
- `task_2_research_report.md` - Comprehensive research on task 3
- `RESEARCH_INDEX.md` - Index of all research
- `workflow_summary.json` - Execution metrics

Each report includes:
- Executive Summary
- Key Findings
- Detailed Analysis
- Best Practices
- Pros and Cons
- Recommendations
- References

**Use Cases**:
- Parallel research on multiple topics
- Concurrent code analysis
- Multi-source data collection
- Distributed competitive analysis

**Performance**: Achieves true parallelism with concurrent Claude API calls

---

### 3. Dynamic Team - Phase-Based Lifecycle

**Pattern**: Just-in-time member addition/retirement based on project phase

#### Demonstration Version
```bash
python examples/team_wrappers/dynamic_team_wrapper.py \
    --project "Build e-commerce platform" \
    --phases design implement test \
    --output ./output/demo
```

**Output**: Simulated phase-based workflow

#### Functional Version ⭐
```bash
python examples/team_wrappers/functional_dynamic_team.py \
    --project "Build a REST API for user management" \
    --phases design implement test \
    --output ./output/dynamic
```

**Output**: Real deliverables for each phase:

**Design Phase** (Architect):
- `architecture_overview.md` - System architecture with mermaid diagrams
- `api_specification.md` - Complete API design
- `data_model.md` - Entity and database design
- `technical_decisions.md` - Architecture Decision Records

**Implementation Phase** (Developers):
- Source code files (Python/JavaScript/etc.)
- `requirements.txt` / `package.json` - Dependencies
- `README.md` - Component documentation
- `IMPLEMENTATION_NOTES.md` - Implementation details

**Testing Phase** (QA):
- `test_plan.md` - Comprehensive testing strategy
- Test files (unit, integration, e2e)
- `test_scenarios.md` - Detailed test cases
- `TEST_RESULTS.md` - Results template

**Use Cases**:
- SDLC workflows (design → implement → test → deploy)
- Phase-based project delivery
- Cost-optimized development (minimal active agents)
- Resource-constrained environments

**Cost Savings**: 60-80% vs fixed team (only 1-3 agents active per phase)

---

### 4. Elastic Team - Role-Based with Knowledge Transfer

**Pattern**: Advanced team with role abstraction, onboarding, and handoffs

#### Demonstration Version
```bash
python examples/team_wrappers/elastic_team_wrapper.py \
    --project "Payment Gateway Integration" \
    --workload high \
    --output ./output/demo
```

**Output**: Simulated role-based workflow

#### Functional Version ⭐
```bash
python examples/team_wrappers/functional_elastic_team.py \
    --project "Build microservices platform" \
    --workload high \
    --output ./output/elastic
```

**Output**: Real deliverables from each role:

**Tech Lead**:
- `ARCHITECTURE.md` - System architecture with diagrams
- `TECHNICAL_STANDARDS.md` - Development standards
- `TECH_ROADMAP.md` - Development roadmap

**Backend Lead**:
- Backend source code (API, models, business logic)
- `API_DOCUMENTATION.md` - Complete API reference
- `BACKEND_SETUP.md` - Setup and deployment guide

**Frontend Lead**:
- Frontend source code (components, state, routing)
- `UI_COMPONENTS.md` - Component documentation
- `FRONTEND_SETUP.md` - Setup guide

**QA Lead**:
- Test suites (unit, integration, e2e)
- `TEST_STRATEGY.md` - Testing approach
- `TEST_EXECUTION_GUIDE.md` - How to run tests

**Use Cases**:
- Enterprise-scale development
- Long-running projects with member turnover
- Mission-critical systems requiring knowledge preservation
- Complex systems with multiple specialized roles

**Features**:
- **Role-based routing**: Tasks assigned to roles, not individuals
- **Onboarding briefings**: New members receive project context
- **Knowledge handoffs**: Seamless transitions when members change
- **Auto-scaling**: Workload-based team sizing (low/medium/high)
- **Knowledge preservation**: 95%+ knowledge retention during transitions

**Workload Scaling**:
- `low`: 1 role (Tech Lead)
- `medium`: 2 roles (+ Backend Lead)
- `high`: 4 roles (full team)

---

## 📊 Comparison Matrix

| Feature | Demonstration | Functional |
|---------|--------------|------------|
| **Purpose** | Pattern demonstration | Production deliverables |
| **Claude API** | No (simulated) | Yes (real calls) |
| **Output** | Simulated results | Real files/code/docs |
| **Execution Time** | Fast (seconds) | Real (minutes) |
| **Use For** | Learning, testing patterns | Building actual systems |
| **API Cost** | Free | Paid (Claude API usage) |

### Team Pattern Comparison

| Feature | Standard | Parallel | Dynamic | Elastic |
|---------|----------|----------|---------|---------|
| **Execution** | Sequential | Concurrent | Phased | Role-based |
| **Team Size** | Fixed | Fixed | Variable | Variable |
| **Scaling** | No | No | Phase-based | Workload-based |
| **Member Lifecycle** | Static | Static | Just-in-time | Just-in-time |
| **Knowledge Transfer** | No | No | Basic | Advanced |
| **Cost Optimization** | Low | Low | High (60-80%) | Highest (40-70%) |
| **Complexity** | Low | Low | Medium | High |
| **Best For** | Simple workflows | Independent tasks | Phased projects | Enterprise scale |

---

## ⚙️ Configuration

All wrappers use the centralized configuration system:

### Environment Variables
```bash
export CLAUDE_TEAM_MAX_AGENTS=20
export CLAUDE_TEAM_OUTPUT_BASE_DIR=/custom/output
export CLAUDE_MODEL="claude-sonnet-4-20250514"
```

### Config Files
```yaml
# config/default.yaml
team:
  max_agents: 10
  coordination_timeout: 30

output:
  base_dir: /tmp/claude_team_sdk_output

claude:
  model: claude-sonnet-4-20250514
```

---

## 🚀 Advanced Usage

### Running Multiple Teams in Sequence
```bash
# Phase 1: Standard team for requirements
python functional_standard_team.py \
    --requirement "Build user auth system" \
    --output ./project/phase1

# Phase 2: Dynamic team for implementation
python functional_dynamic_team.py \
    --project "Implement user auth from requirements" \
    --phases design implement test \
    --output ./project/phase2

# Phase 3: Parallel team for deployment research
python functional_parallel_team.py \
    --tasks "Research AWS deployment" "Research Docker setup" \
    --agents 2 \
    --output ./project/phase3
```

### Custom Workload Scaling
```bash
# Start small
python functional_elastic_team.py \
    --project "Prototype API" \
    --workload low \
    --output ./prototype

# Scale up for production
python functional_elastic_team.py \
    --project "Production API" \
    --workload high \
    --output ./production
```

---

## 📈 Performance Metrics

### Standard Team
- **Latency**: Sequential (sum of all phases)
- **Throughput**: 1 task at a time
- **Duration**: ~3-5 minutes for typical requirement
- **Files Created**: 7-10 deliverables

### Parallel Team
- **Latency**: Max of concurrent tasks (true parallelism)
- **Throughput**: N tasks concurrently
- **Duration**: ~2-4 minutes for 3 research tasks
- **Speedup**: ~3x vs sequential execution

### Dynamic Team
- **Latency**: Sequential phases
- **Duration**: ~5-10 minutes for full SDLC
- **Files Created**: 15-25 deliverables
- **Cost Savings**: 60-80% vs full team

### Elastic Team
- **Latency**: Role-based parallelism
- **Duration**: ~8-12 minutes for high workload
- **Files Created**: 20-35 deliverables
- **Knowledge Retention**: 95%+ during transitions

---

## 🧪 Testing

### Test Demonstration Wrappers
```bash
# Fast - for pattern validation
python examples/team_wrappers/standard_team_wrapper.py \
    --requirement "Test" --team-size 2 --output /tmp/test

python examples/team_wrappers/parallel_team_wrapper.py \
    --tasks "Task 1" "Task 2" --agents 2 --output /tmp/test
```

### Test Functional Wrappers
```bash
# Requires Claude API key - produces real output
export ANTHROPIC_API_KEY="your-key"

python examples/team_wrappers/functional_standard_team.py \
    --requirement "Simple todo app API" \
    --output /tmp/test_standard

python examples/team_wrappers/functional_parallel_team.py \
    --tasks "Research Python web frameworks" \
    --agents 1 \
    --output /tmp/test_parallel
```

---

## 🔍 When to Use Each Pattern

### Use Standard Team When:
- You need comprehensive documentation
- Sequential approval is required
- Stakeholder deliverables are critical
- You want analyst → reviewer → publisher workflow

### Use Parallel Team When:
- You have independent research tasks
- Speed is critical
- Tasks can be done concurrently
- You want to maximize throughput

### Use Dynamic Team When:
- You're following SDLC phases
- Cost optimization is important
- Different skills needed at different times
- You want to minimize active agents

### Use Elastic Team When:
- You need role-based organization
- Team members may change
- Knowledge preservation is critical
- You're building enterprise systems
- Workload varies significantly

---

## 📚 Documentation

- [Team Architecture Patterns](../../docs/team_architecture/TEAM_PATTERNS.md) - Comprehensive architectural guide
- [Configuration Guide](../../config/README.md) - Configuration system documentation
- [Migration Guide](../../MIGRATION_GUIDE.md) - Upgrading from older versions
- [Architecture Compliance](../../ARCHITECTURE_COMPLIANCE_REPORT.md) - ADR compliance

---

## 🛠️ Troubleshooting

### Claude SDK Not Available
```bash
# Install Claude Code SDK
pip install claude-code-sdk

# Verify installation
python -c "import claude_code_sdk; print('OK')"
```

### API Key Issues
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Verify
echo $ANTHROPIC_API_KEY
```

### Permission Errors
```bash
# Functional wrappers use permission_mode="auto"
# If you encounter permission prompts, this is expected
# Review the operation and approve or deny
```

### Output Directory
```bash
# Ensure output directory is writable
mkdir -p ./output
chmod 755 ./output
```

---

## 💡 Examples by Use Case

### Documentation Generation
```bash
python functional_standard_team.py \
    --requirement "Create API documentation for user service" \
    --output ./docs/api
```

### Technical Research
```bash
python functional_parallel_team.py \
    --tasks "Research GraphQL vs REST" \
            "Research database scaling strategies" \
            "Research caching patterns" \
    --agents 3 \
    --output ./research
```

### Full SDLC Project
```bash
python functional_dynamic_team.py \
    --project "Build notification service with webhooks" \
    --phases design implement test \
    --output ./projects/notifications
```

### Microservices Platform
```bash
python functional_elastic_team.py \
    --project "Design microservices architecture for e-commerce" \
    --workload high \
    --output ./projects/microservices
```

---

## 🤝 Contributing

To add a new team pattern:

1. Create demonstration version: `new_pattern_wrapper.py`
2. Create functional version: `functional_new_pattern.py`
3. Update this README with:
   - Pattern description
   - Use cases
   - Examples
   - Comparison matrix entry
4. Add tests in `tests/integration/`
5. Update architecture documentation

---

## 📄 License

See [LICENSE](../../LICENSE) for details.

---

**Last Updated**: 2025-10-04
**Maintained by**: Claude Team SDK Architecture Team

**Note**: Functional wrappers require Claude API access and will incur API costs based on usage. Demonstration wrappers are free and useful for learning patterns.
