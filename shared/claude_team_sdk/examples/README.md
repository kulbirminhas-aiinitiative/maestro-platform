# Examples - Claude Team SDK

This directory contains examples demonstrating the Claude Team SDK's multi-agent collaboration capabilities.

## 🚀 Quick Start

### Installation

```bash
# Install the SDK
pip install -e .

# Or with all dependencies
pip install -e ".[all]"

# Setup configuration
cp .env.example .env
# Edit .env with your values
```

### Running Examples

```bash
# Basic team collaboration
python examples/basic_team.py

# Advanced collaboration patterns
python examples/advanced_collaboration.py

# Autonomous discussion
python examples/autonomous_discussion.py
```

## 📁 Example Structure

### Core Examples

#### `basic_team.py`
**Demonstrates**: Basic multi-agent collaboration

```python
from claude_team_sdk import TeamCoordinator, DeveloperAgent, ReviewerAgent

# Create team
coordinator = TeamCoordinator(config)
coord_server = coordinator.create_coordination_server()

# Add agents
developer = DeveloperAgent("dev1", coord_server)
reviewer = ReviewerAgent("rev1", coord_server)

# Execute tasks
await developer.execute()
await reviewer.execute()
```

**Key Concepts**:
- Team coordinator setup
- Shared MCP coordination
- Task distribution
- Inter-agent communication

#### `advanced_collaboration.py`
**Demonstrates**: Complex collaboration patterns

- Leader-worker pattern
- Pipeline execution
- Peer-to-peer collaboration
- Decision voting

#### `autonomous_discussion.py`
**Demonstrates**: Autonomous agent discussions

- Self-organizing teams
- Emergent behavior
- Continuous collaboration
- Dynamic task creation

### Domain-Specific Examples

#### `domain_teams/`

- `medical_team.py` - Medical diagnosis team
- `research_team.py` - Research collaboration
- `business_team.py` - Business analysis
- `educational_team.py` - Teaching assistance
- `emergency_response_team.py` - Emergency coordination

### SDLC Examples

#### `sdlc_team/`

Full software development lifecycle examples:

- `sdlc_code_generator.py` - Code generation wrapper
- `autonomous_sdlc_engine.py` - Autonomous SDLC execution
- `sdlc_workflow.py` - Complete SDLC workflow
- `team_organization.py` - Team structure patterns

**Generated Projects**: Examples generate full projects in `generated_*/` directories

## 🔧 Configuration

### Using the New Config System

```python
# Import configuration
from claude_team_sdk.config import settings

# Access values
database_url = settings.database.url
max_agents = settings.team.max_agents
api_url = settings.api.base_url

# Environment-specific
if settings.service.environment == "production":
    # Production logic
    pass
```

### Environment Variables

```bash
# Core settings
export CLAUDE_TEAM_DATABASE_URL=postgresql://...
export CLAUDE_TEAM_REDIS_URL=redis://...
export CLAUDE_TEAM_MAX_AGENTS=10

# API keys
export ANTHROPIC_API_KEY=your_key_here
```

## 📊 Example Output

### Basic Team Example

```
🚀 Starting Multi-Agent Team Collaboration

✅ Team Coordinator created: demo_team
✅ Shared MCP Coordination Server created

📋 Adding tasks to queue...

Task 1: Design authentication system
Task 2: Implement user login
Task 3: Write unit tests

👥 Spawning agents...

✅ Architect (arch1) spawned
✅ Developer (dev1) spawned
✅ Reviewer (rev1) spawned
✅ Tester (test1) spawned

🔄 Agents executing tasks...

[Architect] Claimed task: Design authentication system
[Architect] Completed task: Design authentication system
[Architect] Shared knowledge: auth_design

[Developer] Claimed task: Implement user login
[Developer] Retrieved knowledge: auth_design
[Developer] Completed task: Implement user login

✅ All tasks completed!

📈 Team Statistics:
   - Total tasks: 3
   - Completed: 3
   - Messages exchanged: 12
   - Knowledge items: 5
```

## 🧪 Testing Examples

```bash
# Run example tests
pytest examples/tests/ -v

# Test specific example
python examples/basic_team.py --test

# Dry run (no actual API calls)
python examples/basic_team.py --dry-run
```

## 🎯 Learning Path

### 1. Start Here: Basic Concepts

1. **basic_team.py** - Understand core concepts
2. **advanced_collaboration.py** - Learn patterns
3. **autonomous_discussion.py** - See autonomy in action

### 2. Domain Applications

Explore `domain_teams/` for specific use cases:

- Medical diagnosis
- Research collaboration
- Business analysis
- Education
- Emergency response

### 3. Real-World: SDLC

Study `sdlc_team/` for production-ready examples:

- Full project generation
- Multi-phase workflows
- Quality assurance
- Deployment automation

## 🔍 Key Patterns Demonstrated

### Pattern 1: Leader-Worker

```python
coordinator = CoordinatorAgent("coordinator", coord_server)
workers = [DeveloperAgent(f"dev{i}", coord_server) for i in range(3)]

# Coordinator distributes work
await coordinator.distribute_tasks(tasks)

# Workers execute in parallel
await asyncio.gather(*[w.execute() for w in workers])
```

### Pattern 2: Pipeline

```python
# Sequential hand-offs
architect = ArchitectAgent("arch", coord_server)
developer = DeveloperAgent("dev", coord_server)
tester = TesterAgent("test", coord_server)

# Each stage builds on previous
await architect.design()
await developer.implement()
await tester.validate()
```

### Pattern 3: Peer-to-Peer

```python
# Equal peers collaborating
agents = [Agent(f"agent{i}", coord_server) for i in range(5)]

# Democratic decisions
await asyncio.gather(*[a.propose_and_vote() for a in agents])
```

## 🛠️ Customization

### Creating Custom Agents

```python
from claude_team_sdk import TeamAgent, AgentConfig, AgentRole

class CustomAgent(TeamAgent):
    def __init__(self, agent_id, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.CUSTOM,
            capabilities=["custom_skill"]
        )
        super().__init__(config, coord_server)

    async def execute_role_specific_work(self):
        # Your custom logic
        task = await self.claim_task()
        result = await self.process(task)
        await self.complete_task(task, result)
```

### Custom Workflows

```python
async def custom_workflow(requirement: str):
    """Custom workflow implementation."""
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Your custom agent composition
    agents = [
        CustomAgent("custom1", coord_server),
        DeveloperAgent("dev1", coord_server),
    ]

    # Your custom orchestration
    for agent in agents:
        await agent.execute()

    return coordinator.get_workspace_state()
```

## 📚 Additional Resources

- [Architecture Documentation](../ARCHITECTURE.md)
- [Configuration Guide](../config/README.md)
- [Migration Guide](../MIGRATION_GUIDE.md)
- [API Reference](../docs/api/)

## 🐛 Troubleshooting

### Common Issues

**Import errors**:
```bash
# Ensure package is installed
pip install -e .

# Check Python path
python -c "import claude_team_sdk; print(claude_team_sdk.__file__)"
```

**Configuration errors**:
```bash
# Check config loading
python -c "from claude_team_sdk.config import settings; print(settings.as_dict())"

# Validate port allocation
python scripts/validate_port_allocation.py
```

**Agent execution errors**:
```bash
# Enable debug logging
export CLAUDE_TEAM_LOG_LEVEL=DEBUG
python examples/basic_team.py
```

## 🤝 Contributing Examples

To contribute a new example:

1. Create file in appropriate directory
2. Follow naming convention: `{purpose}_{type}.py`
3. Include docstring with:
   - Purpose
   - Key concepts demonstrated
   - Usage instructions
4. Add to this README
5. Add tests in `examples/tests/`

## 📝 License

All examples are provided under the same license as the main project (MIT).

---

**Need help?** Check the [main documentation](../README.md) or create an issue.
