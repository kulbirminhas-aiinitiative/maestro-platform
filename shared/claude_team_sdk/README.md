# Claude Team SDK

**True Multi-Agent Collaboration Framework using Claude Code SDK**

Build teams of AI agents that collaborate in real-time through shared MCP (Model Context Protocol) servers.

## Features

✅ **True Multi-Agent Architecture**
- Multiple separate agent processes
- Each agent runs independently
- Concurrent execution

✅ **Direct Communication**
- Agents call each other's tools via shared MCP
- Real-time bidirectional messaging
- Request/response patterns

✅ **In-Memory Shared State**
- Shared Python objects across agents
- Thread-safe coordination
- Zero latency communication

✅ **Real-time Collaboration**
- Agents interact dynamically
- Event-driven coordination
- Asynchronous workflows

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Team Coordinator                        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │     Shared MCP Coordination Server             │    │
│  │                                                 │    │
│  │  Tools:                                        │    │
│  │  - post_message / get_messages                │    │
│  │  - claim_task / complete_task                 │    │
│  │  - share_knowledge / get_knowledge            │    │
│  │  - update_status / get_team_status           │    │
│  │  - store_artifact / get_artifacts            │    │
│  │  - propose_decision / vote_decision          │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │          Shared In-Memory Workspace             │    │
│  │                                                 │    │
│  │  - Messages (inter-agent communication)        │    │
│  │  - Tasks (distributed queue)                   │    │
│  │  - Knowledge Base (shared learning)            │    │
│  │  - Artifacts (work products)                   │    │
│  │  - Decisions (collaborative choices)           │    │
│  │  - Agent Status (real-time tracking)          │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                   ↓                   ↓
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │ Agent 1 │        │ Agent 2 │        │ Agent 3 │
   │         │        │         │        │         │
   │ Claude  │        │ Claude  │        │ Claude  │
   │ Client  │        │ Client  │        │ Client  │
   └─────────┘        └─────────┘        └─────────┘
        ↓                   ↓                   ↓
    (All agents share the same MCP server instance)
```

## Installation

```bash
# Install dependencies
pip install claude-code-sdk

# Install Claude Code CLI (required)
npm install -g @anthropic-ai/claude-code

# Install team SDK
pip install -e ./claude_team_sdk
```

## Quick Start

### 1. Basic Team Setup

```python
import asyncio
from claude_team_sdk import (
    TeamCoordinator,
    TeamConfig,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent
)

async def main():
    # Create coordinator
    coordinator = TeamCoordinator(TeamConfig())

    # Create shared MCP server
    coord_server = coordinator.create_coordination_server()

    # Create agents (all share the same server!)
    architect = ArchitectAgent("architect_1", coord_server)
    developer = DeveloperAgent("developer_1", coord_server)
    reviewer = ReviewerAgent("reviewer_1", coord_server)

    # Add tasks
    await coordinator.add_task(
        "Design API architecture",
        required_role="architect"
    )

    await coordinator.add_task(
        "Implement endpoints",
        required_role="developer"
    )

    # Run agents concurrently
    await asyncio.gather(
        architect.run(),
        developer.run(),
        reviewer.run()
    )

asyncio.run(main())
```

### 2. Agent Communication

```python
# Agent A sends message to Agent B
await agent_a.send_message(
    to_agent="agent_b",
    message="Please review the API design",
    message_type="request"
)

# Agent B checks messages
messages = await agent_b.check_messages(limit=5)
```

### 3. Knowledge Sharing

```python
# Share knowledge
await architect.share_knowledge(
    key="api_pattern",
    value="RESTful with layered architecture",
    category="architecture"
)

# Retrieve knowledge
pattern = await developer.get_knowledge("api_pattern")
```

### 4. Task Coordination

```python
# Coordinator adds tasks
await coordinator.add_task(
    description="Build user service",
    required_role="developer",
    priority=10
)

# Agents auto-claim tasks matching their role
# (happens automatically in agent.run())
```

## Specialized Agents

### ArchitectAgent
- Designs system architecture
- Makes technical decisions
- Creates design documents
- Guides implementation

### DeveloperAgent
- Implements features
- Writes code
- Follows architecture
- Collaborates with team

### ReviewerAgent
- Reviews code quality
- Ensures standards
- Provides feedback
- Approves changes

### TesterAgent
- Creates test plans
- Writes tests
- Executes tests
- Reports issues

### CoordinatorAgent
- Manages workflow
- Distributes tasks
- Tracks progress
- Facilitates collaboration

## Key Components

### TeamCoordinator
Main orchestration class for multi-agent teams.

```python
coordinator = TeamCoordinator(TeamConfig(
    team_id="my_team",
    workspace_path=Path("./workspace"),
    max_agents=10
))

# Create shared coordination server
coord_server = coordinator.create_coordination_server()

# Add tasks
await coordinator.add_task(description, required_role, priority)

# Get workspace state
state = await coordinator.get_workspace_state()

# Shutdown
await coordinator.shutdown()
```

### Shared MCP Tools

All agents have access to these coordination tools:

- **post_message** - Send message to agent(s)
- **get_messages** - Retrieve messages
- **claim_task** - Claim task from queue
- **complete_task** - Mark task complete
- **share_knowledge** - Share knowledge item
- **get_knowledge** - Retrieve knowledge
- **update_status** - Update agent status
- **get_team_status** - Get all agent statuses
- **store_artifact** - Store work artifact
- **get_artifacts** - Retrieve artifacts
- **propose_decision** - Propose team decision
- **vote_decision** - Vote on decision

### Communication Patterns

```python
from claude_team_sdk import CommunicationProtocol

# Request/Response
request = CommunicationProtocol.create_request(
    from_agent="agent_a",
    to_agent="agent_b",
    request_type="help",
    content="Need architecture review"
)

# Broadcast
broadcast = CommunicationProtocol.create_broadcast(
    from_agent="coordinator",
    content="Team meeting in 5 minutes"
)

# Direct message
message = CommunicationProtocol.create_direct_message(
    from_agent="developer",
    to_agent="reviewer",
    content="PR ready for review"
)
```

### Shared Workspace

```python
from claude_team_sdk import SharedWorkspace

workspace = SharedWorkspace()

# Store artifact
await workspace.store_artifact(
    artifact_id="code_123",
    name="api.py",
    artifact_type="code",
    content=code_content,
    agent_id="developer_1"
)

# Get workspace stats
stats = await workspace.get_workspace_stats()
```

## Examples

### Example 1: Basic Team
See `examples/basic_team.py` for a complete example of:
- Creating a team
- Adding tasks
- Running multiple agents
- Monitoring progress

### Example 2: Advanced Collaboration
See `examples/advanced_collaboration.py` for:
- Custom agent workflows
- Direct messaging
- Knowledge sharing
- Collaborative decisions

### Example 3: Custom Agent

```python
from claude_team_sdk import TeamAgent, AgentConfig, AgentRole

class CustomAgent(TeamAgent):
    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            system_prompt="Custom agent prompt..."
        )
        super().__init__(config, coordination_server)

    async def execute_task(self, task_description: str):
        # Custom task execution logic
        await self._update_status(AgentStatus.WORKING, task_description)

        # Use Claude to process task
        await self.client.query(f"Execute: {task_description}")

        async for msg in self.client.receive_response():
            # Process results
            pass

        return {"success": True}

    async def execute_role_specific_work(self):
        # Custom workflow
        await self._auto_task_loop()
```

## Key Benefits

### vs Single Agent
- **Parallel execution** - Multiple tasks simultaneously
- **Specialization** - Each agent focuses on their role
- **Scalability** - Add agents as needed

### vs Sequential Workflow
- **Real-time collaboration** - Agents interact dynamically
- **Faster completion** - Concurrent task processing
- **Better decisions** - Collaborative problem solving

### vs Event-based Systems
- **Direct communication** - No message broker needed
- **Low latency** - In-memory state sharing
- **Type safety** - Shared Python objects

## Configuration

```python
from claude_team_sdk import TeamConfig

config = TeamConfig(
    team_id="production_team",
    workspace_path=Path("./prod_workspace"),
    max_agents=20,
    enable_logging=True,
    coordination_interval=0.5  # Status check interval
)
```

## Monitoring

```python
# Get real-time workspace state
state = await coordinator.get_workspace_state()

print(f"Active Agents: {state['active_agents']}")
print(f"Tasks: {state['tasks']}")
print(f"Messages: {state['messages']}")
print(f"Knowledge Items: {state['knowledge_items']}")
print(f"Artifacts: {state['artifacts']}")
```

## Best Practices

1. **Agent Initialization**
   - Always initialize agents before use
   - Ensure coordination server is created first

2. **Task Design**
   - Make tasks atomic and role-specific
   - Set appropriate priorities
   - Use dependencies for task ordering

3. **Communication**
   - Use message types appropriately
   - Check messages regularly
   - Respond to requests promptly

4. **Knowledge Sharing**
   - Categorize knowledge items
   - Use descriptive keys
   - Update rather than duplicate

5. **Resource Management**
   - Always shutdown agents properly
   - Use async context managers when possible
   - Clean up coordination resources

## Troubleshooting

### Agents not claiming tasks
- Check role matching between task and agent
- Verify coordination server is shared correctly
- Ensure agents are running (await agent.run())

### Messages not received
- Check message routing (to_agent field)
- Verify agents are calling check_messages()
- Ensure coordination server is connected

### Knowledge not found
- Verify key matches exactly
- Check if knowledge was stored successfully
- Ensure using same coordination server

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please see CONTRIBUTING.md

## Support

- Documentation: `./docs`
- Examples: `./examples`
- Issues: GitHub Issues
- Discussions: GitHub Discussions
