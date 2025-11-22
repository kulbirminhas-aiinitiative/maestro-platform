#!/usr/bin/env python3
"""
Team Size Comparison - Different Team Compositions

Demonstrates communication patterns across different team sizes:
- Small (2 members): Doctor + Nurse consultation
- Medium (5 members): Software development team
- Large (10 members): Enterprise project team

Shows how communication complexity scales with team size
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import (
    TeamCoordinator, TeamConfig, TeamAgent,
    AgentConfig, AgentRole, DeveloperAgent
)


async def small_team_demo():
    """2-person team: Doctor + Nurse"""
    print("\n" + "=" * 70)
    print("SMALL TEAM (2 members): Doctor + Nurse Consultation")
    print("=" * 70 + "\n")

    config = TeamConfig(team_id="small_team")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    doctor = DeveloperAgent("dr_smith", coord_server)
    nurse = DeveloperAgent("nurse_jones", coord_server)

    await doctor.initialize()
    await nurse.initialize()

    # Simple 1:1 communication
    await doctor.send_message("nurse_jones", "Patient in Room 3 needs vitals check", "request")
    await asyncio.sleep(0.5)

    await nurse.send_message("dr_smith", "Vitals: BP 120/80, HR 72, Temp 98.6F - All normal", "response")
    await asyncio.sleep(0.5)

    await doctor.send_message("nurse_jones", "Thanks! Please prepare discharge paperwork", "request")

    state = await coordinator.get_workspace_state()
    print(f"📊 Small Team Stats:")
    print(f"   - Members: 2")
    print(f"   - Messages: {state['messages']}")
    print(f"   - Communication pattern: Direct 1:1")
    print(f"   - Coordination: Simple, fast\n")

    await doctor.shutdown()
    await nurse.shutdown()
    await coordinator.shutdown()


async def medium_team_demo():
    """5-person team: Dev team with specializations"""
    print("\n" + "=" * 70)
    print("MEDIUM TEAM (5 members): Software Development Team")
    print("=" * 70 + "\n")

    config = TeamConfig(team_id="medium_team")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    from claude_team_sdk import (ArchitectAgent, DeveloperAgent,
                                   ReviewerAgent, TesterAgent)

    architect = ArchitectAgent("alice", coord_server)
    dev1 = DeveloperAgent("bob", coord_server)
    dev2 = DeveloperAgent("carol", coord_server)
    reviewer = ReviewerAgent("dave", coord_server)
    tester = TesterAgent("eve", coord_server)

    for agent in [architect, dev1, dev2, reviewer, tester]:
        await agent.initialize()

    # More complex communication patterns
    await architect.send_message("all", "New feature: User authentication. Design: OAuth2 + JWT", "broadcast")
    await asyncio.sleep(0.5)

    await dev1.send_message("alice", "Implementing OAuth2 flow. Need security review?", "question")
    await dev2.send_message("alice", "I'll handle JWT token generation and validation", "info")
    await asyncio.sleep(0.5)

    await reviewer.send_message("bob", "Yes, send PR when ready. I'll review security", "response")
    await tester.send_message("all", "I'll create auth test suite once implementation ready", "info")
    await asyncio.sleep(0.5)

    state = await coordinator.get_workspace_state()
    print(f"📊 Medium Team Stats:")
    print(f"   - Members: 5")
    print(f"   - Messages: {state['messages']}")
    print(f"   - Communication pattern: Mix of broadcast + targeted")
    print(f"   - Coordination: Moderate complexity\n")

    for agent in [architect, dev1, dev2, reviewer, tester]:
        await agent.shutdown()
    await coordinator.shutdown()


async def large_team_demo():
    """10-person team: Enterprise project"""
    print("\n" + "=" * 70)
    print("LARGE TEAM (10 members): Enterprise Project Team")
    print("=" * 70 + "\n")

    config = TeamConfig(team_id="large_team")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create 10-member team
    agents = []
    for i in range(10):
        agent = DeveloperAgent(f"member_{i+1}", coord_server)
        agents.append(agent)
        await agent.initialize()

    # Complex multi-threaded communication
    # Leader broadcasts
    await agents[0].send_message("all", "Project kickoff: E-commerce platform redesign. 6-month timeline", "broadcast")
    await asyncio.sleep(0.3)

    # Sub-team formation
    await agents[1].send_message("member_2", "Let's form frontend sub-team. You, me, member_3?", "request")
    await agents[2].send_message("member_1", "Count me in for frontend!", "response")
    await asyncio.sleep(0.3)

    await agents[4].send_message("member_5", "Backend team: database design. Join me?", "request")
    await agents[5].send_message("member_6", "API team coordination - need 2 more devs", "broadcast")
    await asyncio.sleep(0.3)

    # Multiple parallel conversations
    await agents[3].send_message("member_7", "QA strategy discussion?", "request")
    await agents[6].send_message("member_8", "DevOps setup - cloud architecture decisions", "info")
    await agents[8].send_message("all", "Design system meeting tomorrow, all welcome", "broadcast")
    await asyncio.sleep(0.3)

    state = await coordinator.get_workspace_state()
    print(f"📊 Large Team Stats:")
    print(f"   - Members: 10")
    print(f"   - Messages: {state['messages']}")
    print(f"   - Communication pattern: Multiple parallel threads")
    print(f"   - Sub-teams: Formed organically (Frontend, Backend, API, QA, DevOps)")
    print(f"   - Coordination: Complex, requires sub-team structure\n")

    for agent in agents:
        await agent.shutdown()
    await coordinator.shutdown()


async def run_comparison():
    """Compare all team sizes"""

    print("\n" + "🔍 TEAM SIZE COMMUNICATION ANALYSIS")
    print("=" * 70)
    print("Comparing how communication patterns change with team size")
    print("=" * 70)

    # Run all demos
    await small_team_demo()
    await medium_team_demo()
    await large_team_demo()

    # Final analysis
    print("\n" + "=" * 70)
    print("📊 COMMUNICATION COMPLEXITY ANALYSIS")
    print("=" * 70 + "\n")

    print("🔹 SMALL TEAM (2 members):")
    print("   Pros:")
    print("     - Minimal coordination overhead")
    print("     - Direct, fast communication")
    print("     - Clear roles and responsibilities")
    print("   Cons:")
    print("     - Limited specialization")
    print("     - Single point of failure")
    print("   Best for: Simple tasks, quick decisions\n")

    print("🔹 MEDIUM TEAM (5 members):")
    print("   Pros:")
    print("     - Good specialization")
    print("     - Manageable communication")
    print("     - Balanced flexibility/structure")
    print("   Cons:")
    print("     - Requires some coordination")
    print("     - Potential for miscommunication")
    print("   Best for: Standard projects, balanced workload\n")

    print("🔹 LARGE TEAM (10+ members):")
    print("   Pros:")
    print("     - High specialization")
    print("     - Parallel workstreams")
    print("     - Diverse expertise")
    print("   Cons:")
    print("     - High communication overhead")
    print("     - Needs sub-team structure")
    print("     - Coordination complexity")
    print("   Best for: Large projects, complex requirements\n")

    print("💡 KEY INSIGHTS:")
    print("   1. Communication complexity grows exponentially with team size")
    print("   2. Teams > 7-8 members benefit from sub-team structure")
    print("   3. Shared MCP enables seamless scaling across all sizes")
    print("   4. Knowledge sharing becomes critical in larger teams")
    print("   5. Clear roles and responsibilities essential for all sizes\n")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_comparison())
