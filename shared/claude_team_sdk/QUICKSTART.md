# Claude Team SDK - Quick Start Guide

## Installation

### Prerequisites
1. Python 3.10+
2. Node.js (for Claude Code CLI)
3. Claude API key

### Install Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code
```

### Install Claude Team SDK
```bash
cd /home/ec2-user/projects/shared/claude_team_sdk
pip install -e .
```

Or install from requirements:
```bash
pip install -r requirements.txt
```

## 5-Minute Quick Start

### 1. Create a Simple Team (30 seconds)

```python
import asyncio
from claude_team_sdk import TeamCoordinator, TeamConfig, DeveloperAgent

async def quick_demo():
    # Create coordinator
    coordinator = TeamCoordinator(TeamConfig())

    # Create shared MCP server
    coord_server = coordinator.create_coordination_server()

    # Create agent
    dev = DeveloperAgent("dev_1", coord_server)

    # Add task
    await coordinator.add_task("Build hello world API", "developer")

    # Run agent for 10 seconds
    task = asyncio.create_task(dev.run())
    await asyncio.sleep(10)
    task.cancel()

    # Show results
    state = await coordinator.get_workspace_state()
    print(f"Tasks completed: {state['tasks']['completed']}")

asyncio.run(quick_demo())
```

### 2. Multi-Agent Team (2 minutes)

```python
import asyncio
from claude_team_sdk import (
    TeamCoordinator, TeamConfig,
    ArchitectAgent, DeveloperAgent, ReviewerAgent
)

async def multi_agent_demo():
    # Setup
    coordinator = TeamCoordinator(TeamConfig(team_id="my_team"))
    coord_server = coordinator.create_coordination_server()

    # Create team
    architect = ArchitectAgent("architect", coord_server)
    developer = DeveloperAgent("developer", coord_server)
    reviewer = ReviewerAgent("reviewer", coord_server)

    # Add workflow tasks
    await coordinator.add_task("Design REST API", "architect", priority=10)
    await coordinator.add_task("Implement endpoints", "developer", priority=8)
    await coordinator.add_task("Review implementation", "reviewer", priority=5)

    # Run team for 30 seconds
    agents = [
        asyncio.create_task(architect.run()),
        asyncio.create_task(developer.run()),
        asyncio.create_task(reviewer.run())
    ]

    await asyncio.sleep(30)

    for agent in agents:
        agent.cancel()

    # Results
    state = await coordinator.get_workspace_state()
    print(f"Team: {state['active_agents']} agents")
    print(f"Messages: {state['messages']}")
    print(f"Tasks: {state['tasks']}")

asyncio.run(multi_agent_demo())
```

### 3. Custom Communication (3 minutes)

```python
import asyncio
from claude_team_sdk import TeamCoordinator, TeamConfig, TeamAgent, AgentConfig, AgentRole

async def custom_workflow():
    coordinator = TeamCoordinator(TeamConfig())
    coord_server = coordinator.create_coordination_server()

    # Create agents
    agent_a = TeamAgent(
        AgentConfig(agent_id="agent_a", role=AgentRole.ARCHITECT),
        coord_server
    )
    agent_b = TeamAgent(
        AgentConfig(agent_id="agent_b", role=AgentRole.DEVELOPER),
        coord_server
    )

    # Initialize
    await agent_a.initialize()
    await agent_b.initialize()

    # Agent A shares knowledge
    await agent_a.share_knowledge(
        "api_design",
        "Use RESTful pattern with layered architecture",
        "architecture"
    )

    # Agent A messages Agent B
    await agent_a.send_message(
        "agent_b",
        "Please check knowledge base for API design",
        "request"
    )

    await asyncio.sleep(2)

    # Agent B retrieves knowledge
    design = await agent_b.get_knowledge("api_design")
    print(f"Agent B retrieved: {design}")

    # Agent B responds
    await agent_b.send_message(
        "agent_a",
        "Design received, starting implementation",
        "response"
    )

    # Cleanup
    await agent_a.shutdown()
    await agent_b.shutdown()

asyncio.run(custom_workflow())
```

## Key Concepts

### 1. Team Coordinator
Central orchestrator that creates the shared MCP server

```python
coordinator = TeamCoordinator(TeamConfig(
    team_id="my_team",
    workspace_path=Path("./workspace"),
    max_agents=10
))

# Create shared server
coord_server = coordinator.create_coordination_server()
```

### 2. Shared MCP Server
All agents connect to the same MCP server for coordination

```python
# All agents use the SAME coord_server
agent_1 = DeveloperAgent("dev_1", coord_server)
agent_2 = DeveloperAgent("dev_2", coord_server)
agent_3 = ReviewerAgent("reviewer", coord_server)
```

### 3. Agent Communication
Agents communicate via MCP tools

```python
# Send message
await agent.send_message("other_agent", "Hello!", "info")

# Check messages
messages = await agent.check_messages(limit=5)

# Share knowledge
await agent.share_knowledge("key", "value", "category")

# Get knowledge
value = await agent.get_knowledge("key")
```

### 4. Task Distribution
Coordinator distributes tasks, agents claim based on role

```python
# Add task
await coordinator.add_task(
    "Build feature X",
    required_role="developer",
    priority=10
)

# Agents auto-claim matching tasks when running
await agent.run()  # Will claim and execute tasks
```

## Architecture Patterns

### Pattern 1: Pipeline
```
Architect → Developer → Reviewer → Tester
```

### Pattern 2: Swarm
```
Multiple developers working in parallel
```

### Pattern 3: Hierarchical
```
Coordinator
    ├── Team A (Architect + Developers)
    └── Team B (Reviewers + Testers)
```

## Running Examples

### Basic Team Example
```bash
cd /home/ec2-user/projects/shared/claude_team_sdk
python examples/basic_team.py
```

### Advanced Collaboration Example
```bash
python examples/advanced_collaboration.py
```

## Common Patterns

### Pattern: Architect → Developer Flow
```python
async def architect_developer_flow():
    coordinator = TeamCoordinator(TeamConfig())
    server = coordinator.create_coordination_server()

    architect = ArchitectAgent("arch", server)
    developer = DeveloperAgent("dev", server)

    await architect.initialize()
    await developer.initialize()

    # Architect shares design
    await architect.share_knowledge(
        "architecture",
        "Microservices with API gateway",
        "design"
    )

    # Developer gets design
    arch = await developer.get_knowledge("architecture")

    # Developer implements
    # ... implementation logic

    await architect.shutdown()
    await developer.shutdown()
```

### Pattern: Request/Response
```python
# Agent A requests help
await agent_a.send_message(
    "agent_b",
    "Please review my code",
    "request"
)

# Agent B responds
await agent_b.send_message(
    "agent_a",
    "Review complete, looks good",
    "response"
)
```

### Pattern: Broadcast
```python
# Send to all agents
await coordinator_agent.send_message(
    "all",  # Broadcast to everyone
    "Team meeting in 5 minutes",
    "broadcast"
)
```

## Troubleshooting

### Issue: Agents not communicating
**Solution:** Ensure all agents share the same coord_server instance

```python
# ✅ Correct
server = coordinator.create_coordination_server()
agent1 = DeveloperAgent("a", server)
agent2 = DeveloperAgent("b", server)  # Same server

# ❌ Wrong
agent1 = DeveloperAgent("a", coordinator.create_coordination_server())
agent2 = DeveloperAgent("b", coordinator.create_coordination_server())  # Different servers!
```

### Issue: Tasks not being claimed
**Solution:** Check role matching

```python
# Task requires "developer" role
await coordinator.add_task("Build API", required_role="developer")

# Agent must have matching role
agent = DeveloperAgent("dev", server)  # Role is "developer" ✅
```

### Issue: Knowledge not found
**Solution:** Use exact key matching

```python
# Store
await agent.share_knowledge("api_design", "value", "cat")

# Retrieve - key must match exactly
value = await agent.get_knowledge("api_design")  # ✅
value = await agent.get_knowledge("API_design")  # ❌ Case sensitive
```

## Next Steps

1. **Read Full Documentation**: See `README.md`
2. **Explore Examples**: Check `examples/` directory
3. **Build Custom Agents**: Extend `TeamAgent` class
4. **Create Workflows**: Combine agents for complex tasks

## API Reference

### TeamCoordinator
- `create_coordination_server()` - Create shared MCP server
- `add_task(desc, role, priority)` - Add task to queue
- `get_workspace_state()` - Get current state
- `shutdown()` - Clean shutdown

### TeamAgent
- `initialize()` - Connect to coordination server
- `send_message(to, msg, type)` - Send message
- `check_messages(limit)` - Get messages
- `share_knowledge(key, value, cat)` - Share knowledge
- `get_knowledge(key)` - Get knowledge
- `run()` - Start agent execution
- `shutdown()` - Stop agent

### Specialized Agents
- `ArchitectAgent(id, server)` - Solution architect
- `DeveloperAgent(id, server, lang)` - Developer
- `ReviewerAgent(id, server)` - Code reviewer
- `TesterAgent(id, server)` - QA tester
- `CoordinatorAgent(id, server)` - Team coordinator

## Support

- Documentation: `README.md`
- Examples: `examples/`
- Issues: GitHub Issues
