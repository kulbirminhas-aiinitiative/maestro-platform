#!/usr/bin/env python3
"""
Advanced Team Collaboration Example

Demonstrates:
- Custom agent interactions
- Direct messaging between agents
- Knowledge sharing
- Collaborative decision making
- Artifact creation and sharing
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_team_sdk import (
    TeamCoordinator,
    TeamConfig,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
)


async def architect_workflow(architect, developer_id):
    """Architect creates design and shares with developer"""

    # Initialize
    await architect.initialize()

    # Create architecture
    print(f"\n[{architect.agent_id}] Creating architecture...\n")

    await architect.send_message(
        "all",
        "Starting architecture design for user service",
        "info"
    )

    # Share architectural decision
    await architect.share_knowledge(
        key="api_pattern",
        value="RESTful API with layered architecture: Controller -> Service -> Repository",
        category="architecture"
    )

    await architect.share_knowledge(
        key="auth_method",
        value="JWT-based authentication with refresh tokens",
        category="security"
    )

    # Send guidance to developer
    await architect.send_message(
        developer_id,
        "Architecture complete. Please implement based on RESTful pattern. Check knowledge base for details.",
        "request"
    )

    print(f"[{architect.agent_id}] Architecture shared with team\n")

    await asyncio.sleep(5)


async def developer_workflow(developer, architect_id):
    """Developer gets architecture and implements"""

    # Initialize
    await developer.initialize()

    # Wait for architecture
    await asyncio.sleep(3)

    # Check messages from architect
    print(f"\n[{developer.agent_id}] Checking messages...\n")
    messages = await developer.check_messages(limit=5)
    for msg in messages:
        print(f"  📨 {msg}")

    # Get architectural decisions
    api_pattern = await developer.get_knowledge("api_pattern")
    auth_method = await developer.get_knowledge("auth_method")

    print(f"\n[{developer.agent_id}] Retrieved architecture:")
    print(f"  - API Pattern: {api_pattern}")
    print(f"  - Auth Method: {auth_method}\n")

    # Implement (simulated)
    await developer.send_message(
        "all",
        "Implementation in progress following architecture guidelines",
        "info"
    )

    # Ask question
    await developer.send_message(
        architect_id,
        "Should we use async endpoints for all operations?",
        "question"
    )

    await asyncio.sleep(3)

    # Store artifact
    if developer.client:
        await developer.client.query(
            "Store an artifact named 'user_endpoints.py' with type 'code' containing the implementation"
        )
        async for _ in developer.client.receive_response():
            pass

    print(f"[{developer.agent_id}] Implementation complete, artifact stored\n")

    # Request review
    await developer.send_message(
        "reviewer_rex",
        "Please review user_endpoints.py artifact",
        "request"
    )

    await asyncio.sleep(2)


async def reviewer_workflow(reviewer):
    """Reviewer checks code and provides feedback"""

    # Initialize
    await reviewer.initialize()

    # Wait for review request
    await asyncio.sleep(8)

    print(f"\n[{reviewer.agent_id}] Checking for review requests...\n")

    # Check messages
    messages = await reviewer.check_messages(limit=5)
    for msg in messages:
        print(f"  📨 {msg}")

    # Get artifact
    if reviewer.client:
        await reviewer.client.query(
            "Get the artifact 'user_endpoints.py' and review it for quality, security, and best practices"
        )

        async for _ in reviewer.client.receive_response():
            pass

    print(f"\n[{reviewer.agent_id}] Review complete\n")

    # Send feedback
    await reviewer.send_message(
        "dev_danny",
        "Code review complete. Good structure, but please add input validation and error handling.",
        "response"
    )

    # Propose decision
    if reviewer.client:
        await reviewer.client.query(
            "Propose a decision: 'Approve user service implementation with minor changes' with rationale 'Code follows architecture but needs validation'"
        )
        async for _ in reviewer.client.receive_response():
            pass

    print(f"[{reviewer.agent_id}] Proposed team decision\n")


async def main():
    """Advanced collaboration example"""

    print("🚀 Advanced Multi-Agent Collaboration Demo\n")
    print("=" * 60)

    # Setup
    config = TeamConfig(team_id="advanced_team")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create agents
    architect = ArchitectAgent("architect_amy", coord_server)
    developer = DeveloperAgent("dev_danny", coord_server)
    reviewer = ReviewerAgent("reviewer_rex", coord_server)

    print("\n👥 Team Members:")
    print("   - architect_amy (Solution Architect)")
    print("   - dev_danny (Developer)")
    print("   - reviewer_rex (Code Reviewer)\n")

    print("=" * 60)

    # Run workflows
    await asyncio.gather(
        architect_workflow(architect, "dev_danny"),
        developer_workflow(developer, "architect_amy"),
        reviewer_workflow(reviewer)
    )

    print("=" * 60)
    print("\n📊 Final Team State:\n")

    state = await coordinator.get_workspace_state()
    print(f"Messages: {state['messages']}")
    print(f"Knowledge Items: {state['knowledge_items']}")
    print(f"Artifacts: {state['artifacts']}")
    print(f"Decisions: {state['decisions']}")

    # Cleanup
    await architect.shutdown()
    await developer.shutdown()
    await reviewer.shutdown()
    await coordinator.shutdown()

    print("\n✅ Collaboration complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
