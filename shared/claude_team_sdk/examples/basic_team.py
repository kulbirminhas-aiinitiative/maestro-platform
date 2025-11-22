#!/usr/bin/env python3
"""
Basic Team Collaboration Example

Demonstrates:
- Creating a team coordinator
- Spawning multiple agents
- Shared MCP coordination
- Task distribution
- Inter-agent communication
"""

import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_team_sdk import (
    TeamCoordinator,
    TeamConfig,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    TesterAgent
)


async def main():
    """Basic team collaboration example"""

    print("🚀 Starting Multi-Agent Team Collaboration\n")

    # 1. Create team coordinator
    config = TeamConfig(
        team_id="demo_team",
        workspace_path=Path("./demo_workspace"),
        max_agents=5
    )

    coordinator = TeamCoordinator(config)
    print(f"✅ Team Coordinator created: {coordinator.team_id}\n")

    # 2. Create shared coordination server
    coord_server = coordinator.create_coordination_server()
    print("✅ Shared MCP Coordination Server created\n")

    # 3. Add tasks to the queue
    print("📋 Adding tasks to queue...\n")

    await coordinator.add_task(
        "Design REST API architecture for user service",
        required_role="architect",
        priority=10
    )

    await coordinator.add_task(
        "Implement user registration endpoint",
        required_role="developer",
        priority=8
    )

    await coordinator.add_task(
        "Implement user login endpoint",
        required_role="developer",
        priority=8
    )

    await coordinator.add_task(
        "Review user service implementation",
        required_role="reviewer",
        priority=6
    )

    await coordinator.add_task(
        "Create test suite for user endpoints",
        required_role="tester",
        priority=5
    )

    print("✅ Tasks added\n")

    # 4. Create agents (all share the same MCP server!)
    print("👥 Creating agents...\n")

    architect = ArchitectAgent("architect_alice", coord_server)
    developer1 = DeveloperAgent("dev_bob", coord_server, language="Python")
    developer2 = DeveloperAgent("dev_carol", coord_server, language="Python")
    reviewer = ReviewerAgent("reviewer_dave", coord_server)
    tester = TesterAgent("tester_eve", coord_server)

    print("✅ Agents created:\n")
    print("   - architect_alice (Architect)")
    print("   - dev_bob (Python Developer)")
    print("   - dev_carol (Python Developer)")
    print("   - reviewer_dave (Code Reviewer)")
    print("   - tester_eve (QA Tester)\n")

    # 5. Run agents concurrently
    print("🏃 Starting agent execution...\n")
    print("=" * 60)

    # Run for 30 seconds
    agent_tasks = [
        asyncio.create_task(architect.run()),
        asyncio.create_task(developer1.run()),
        asyncio.create_task(developer2.run()),
        asyncio.create_task(reviewer.run()),
        asyncio.create_task(tester.run())
    ]

    # Monitor progress
    try:
        # Let agents work for 30 seconds
        await asyncio.sleep(30)

        # Show workspace state
        print("\n" + "=" * 60)
        print("\n📊 Workspace State:\n")

        state = await coordinator.get_workspace_state()
        print(f"Team ID: {state['team_id']}")
        print(f"Active Agents: {state['active_agents']}")
        print(f"Messages Exchanged: {state['messages']}")
        print(f"\nTasks:")
        print(f"  - Total: {state['tasks']['total']}")
        print(f"  - Pending: {state['tasks']['pending']}")
        print(f"  - In Progress: {state['tasks']['in_progress']}")
        print(f"  - Completed: {state['tasks']['completed']}")
        print(f"\nKnowledge Items: {state['knowledge_items']}")
        print(f"Artifacts: {state['artifacts']}")
        print(f"Decisions: {state['decisions']}")

    finally:
        # Cleanup
        print("\n\n🛑 Shutting down team...\n")
        for task in agent_tasks:
            task.cancel()

        await coordinator.shutdown()
        print("✅ Team shutdown complete\n")


if __name__ == "__main__":
    asyncio.run(main())
