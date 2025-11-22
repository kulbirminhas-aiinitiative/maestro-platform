#!/usr/bin/env python3
"""
Autonomous Agent Discussion - NO HARDCODED CONVERSATIONS

Agents are given:
- An agenda/objective
- Number of discussion rounds
- Their roles

They autonomously:
- Use Claude to decide what to say
- Call MCP tools to communicate
- Share knowledge and make decisions
- Collaborate without scripted interactions

This demonstrates TRUE multi-agent collaboration!
"""

import asyncio
from pathlib import Path
import sys
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_team_sdk import (
    TeamCoordinator,
    TeamConfig,
    TeamAgent,
    AgentConfig,
    AgentRole,
    AgentStatus
)


class AutonomousAgent(TeamAgent):
    """Agent that autonomously participates in discussions"""

    def __init__(self, agent_id: str, role: str, expertise: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.DEVELOPER,  # Generic role
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, participating in a team discussion.

YOUR ROLE: {role}
YOUR EXPERTISE: {expertise}

OBJECTIVE: Actively participate in the team discussion using the coordination tools.

AVAILABLE TOOLS (use them proactively):
1. post_message - Send messages to team members or broadcast to all
2. get_messages - Check messages from other team members
3. share_knowledge - Share important insights, data, or decisions
4. get_knowledge - Retrieve knowledge shared by others
5. propose_decision - Propose decisions for the team
6. vote_decision - Vote on proposed decisions
7. update_status - Update your current status

PARTICIPATION GUIDELINES:
1. Start by checking messages from other team members
2. Contribute your expertise to the discussion
3. Ask questions when you need clarification
4. Share knowledge when you have valuable insights
5. Build on others' ideas
6. Propose decisions when appropriate
7. Vote on proposals thoughtfully

IMPORTANT:
- Use the MCP tools actively to communicate
- Don't just think - actually post messages and share knowledge
- Respond to messages from other agents
- Keep the discussion moving forward
- Be collaborative and constructive

Remember: You're having a REAL conversation with other agents through the shared MCP server.
Use the tools to actually communicate!"""
        )
        super().__init__(config, coordination_server)
        self.role_description = role
        self.expertise = expertise

    async def execute_task(self, task_description: str):
        """Execute a specific task - not used in autonomous discussion"""
        return {"status": "completed", "result": "Task executed"}

    async def execute_role_specific_work(self):
        """Role-specific work - handled by participate_in_discussion"""
        pass

    async def participate_in_discussion(self, agenda: str, rounds: int):
        """Autonomously participate in discussion for N rounds"""

        await self._update_status(AgentStatus.WORKING, f"Discussing: {agenda}")

        for round_num in range(1, rounds + 1):
            # Agent autonomously decides what to do using Claude
            prompt = f"""DISCUSSION ROUND {round_num}/{rounds}

AGENDA: {agenda}

YOUR ROLE: {self.role_description}
YOUR EXPERTISE: {self.expertise}

INSTRUCTIONS:
1. First, check messages from other team members (use get_messages)
2. Read and consider what others have said
3. Contribute your perspective based on your expertise
4. You can:
   - Post messages to share ideas (post_message)
   - Share important knowledge (share_knowledge)
   - Propose decisions if appropriate (propose_decision)
   - Vote on decisions if any were proposed (vote_decision)
   - Ask questions to other team members

5. Be specific and actionable in your contributions
6. Build on what others have shared

IMPORTANT: Actually USE the coordination tools to communicate. This is round {round_num} of {rounds}.
"""

            if self.client:
                await self.client.query(prompt)

                # Let Claude process and use MCP tools
                async for msg in self.client.receive_response():
                    # Agent is autonomously using tools during this iteration
                    pass

            # Small delay between rounds
            await asyncio.sleep(2)

        await self._update_status(AgentStatus.COMPLETED, "Discussion complete")


async def run_autonomous_discussion(
    agenda: str,
    discussion_rounds: int = 3,
    target_outcome: str = None,
    team_composition: List[dict] = None
):
    """
    Run autonomous agent discussion.

    Args:
        agenda: What the team should discuss
        discussion_rounds: Number of discussion iterations
        target_outcome: Optional desired outcome (agents will work toward this)
        team_composition: List of dicts with 'id', 'role', 'expertise'
    """

    print("🤖 AUTONOMOUS AGENT DISCUSSION")
    print("=" * 70)
    print(f"\n📋 AGENDA: {agenda}")
    print(f"🔄 ROUNDS: {discussion_rounds}")
    if target_outcome:
        print(f"🎯 TARGET: {target_outcome}")
    print("\n" + "=" * 70 + "\n")

    # Setup
    config = TeamConfig(team_id="autonomous_discussion")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create agents
    agents = []
    print("👥 TEAM MEMBERS:\n")

    for member in team_composition:
        agent = AutonomousAgent(
            agent_id=member['id'],
            role=member['role'],
            expertise=member['expertise'],
            coordination_server=coord_server
        )
        agents.append(agent)
        await agent.initialize()
        print(f"   ✓ {member['id']}: {member['role']} ({member['expertise']})")

    print("\n" + "=" * 70)
    print("\n🎬 STARTING AUTONOMOUS DISCUSSION...\n")
    print("(Agents will autonomously use MCP tools to communicate)\n")
    print("=" * 70 + "\n")

    # Give context to all agents
    context_prompt = f"""TEAM DISCUSSION STARTING

AGENDA: {agenda}

{f'TARGET OUTCOME: {target_outcome}' if target_outcome else ''}

You are working with {len(agents)} team members (including yourself).
Each member has different expertise. Collaborate effectively!

The discussion will run for {discussion_rounds} rounds.
Make your contributions count!"""

    for agent in agents:
        if agent.client:
            await agent.client.query(context_prompt)
            async for _ in agent.client.receive_response():
                pass

    # Run autonomous discussion
    await asyncio.gather(*[
        agent.participate_in_discussion(agenda, discussion_rounds)
        for agent in agents
    ])

    # Summary
    print("\n" + "=" * 70)
    print("\n📊 DISCUSSION SUMMARY:\n")

    state = await coordinator.get_workspace_state()

    print(f"Team Participation:")
    print(f"  - Total messages: {state['messages']}")
    print(f"  - Knowledge shared: {state['knowledge_items']}")
    print(f"  - Decisions proposed: {state['decisions']}")
    print(f"  - Discussion rounds: {discussion_rounds}")

    print(f"\n💬 Message Activity:")
    print(f"  - Average per round: {state['messages'] / discussion_rounds:.1f}")
    print(f"  - Average per agent: {state['messages'] / len(agents):.1f}")

    print(f"\n🧠 Knowledge Sharing:")
    if state['knowledge_items'] > 0:
        print(f"  - Items shared: {state['knowledge_items']}")
        print(f"  - Collaboration level: {'High' if state['knowledge_items'] > 5 else 'Moderate' if state['knowledge_items'] > 2 else 'Low'}")
    else:
        print(f"  - No knowledge items shared")

    print(f"\n🗳️ Decision Making:")
    if state['decisions'] > 0:
        print(f"  - Decisions proposed: {state['decisions']}")
        print(f"  - Team reached conclusions: Yes")
    else:
        print(f"  - No formal decisions proposed")

    print("\n" + "=" * 70 + "\n")

    # Cleanup
    for agent in agents:
        await agent.shutdown()
    await coordinator.shutdown()

    print("✅ Autonomous discussion completed!\n")


async def example_1_product_feature():
    """Example: Product team discussing new feature"""

    await run_autonomous_discussion(
        agenda="Design a new real-time collaboration feature for our product",
        discussion_rounds=4,
        target_outcome="Agree on feature design, technical approach, and timeline",
        team_composition=[
            {
                'id': 'product_manager',
                'role': 'Product Manager',
                'expertise': 'User needs, market requirements, prioritization'
            },
            {
                'id': 'tech_lead',
                'role': 'Technical Lead',
                'expertise': 'System architecture, feasibility, technical constraints'
            },
            {
                'id': 'ux_designer',
                'role': 'UX Designer',
                'expertise': 'User experience, interaction design, usability'
            },
            {
                'id': 'engineer',
                'role': 'Senior Engineer',
                'expertise': 'Implementation, performance, scalability'
            }
        ]
    )


async def example_2_research_problem():
    """Example: Research team discussing approach"""

    await run_autonomous_discussion(
        agenda="How can we improve the accuracy of our ML model for disease prediction?",
        discussion_rounds=3,
        target_outcome="Define research hypothesis and experimental approach",
        team_composition=[
            {
                'id': 'pi',
                'role': 'Principal Investigator',
                'expertise': 'Research direction, methodology, funding'
            },
            {
                'id': 'ml_expert',
                'role': 'ML Researcher',
                'expertise': 'Machine learning algorithms, model optimization'
            },
            {
                'id': 'domain_expert',
                'role': 'Medical Doctor',
                'expertise': 'Disease mechanisms, clinical relevance'
            }
        ]
    )


async def example_3_crisis_response():
    """Example: Emergency team coordinating response"""

    await run_autonomous_discussion(
        agenda="Coordinate response to chemical spill at industrial facility",
        discussion_rounds=5,
        target_outcome="Action plan with clear responsibilities and timeline",
        team_composition=[
            {
                'id': 'incident_commander',
                'role': 'Incident Commander',
                'expertise': 'Overall coordination, resource allocation, priorities'
            },
            {
                'id': 'hazmat_specialist',
                'role': 'Hazmat Specialist',
                'expertise': 'Chemical identification, containment, safety protocols'
            },
            {
                'id': 'fire_chief',
                'role': 'Fire Chief',
                'expertise': 'Fire suppression, evacuation, scene safety'
            },
            {
                'id': 'ems_coordinator',
                'role': 'EMS Coordinator',
                'expertise': 'Medical treatment, triage, patient transport'
            },
            {
                'id': 'public_info',
                'role': 'Public Information Officer',
                'expertise': 'Media relations, public communication, alerts'
            }
        ]
    )


async def example_4_small_team():
    """Example: Small 2-person team"""

    await run_autonomous_discussion(
        agenda="Review patient treatment plan and adjust medications",
        discussion_rounds=3,
        target_outcome="Updated treatment plan with medication adjustments",
        team_composition=[
            {
                'id': 'doctor',
                'role': 'Attending Physician',
                'expertise': 'Diagnosis, treatment planning, medical decisions'
            },
            {
                'id': 'pharmacist',
                'role': 'Clinical Pharmacist',
                'expertise': 'Drug interactions, dosing, medication safety'
            }
        ]
    )


async def main():
    """Run examples"""

    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1]

        examples = {
            '1': ('Product Feature Discussion', example_1_product_feature),
            '2': ('Research Problem Discussion', example_2_research_problem),
            '3': ('Crisis Response Coordination', example_3_crisis_response),
            '4': ('Small Team Consultation', example_4_small_team),
        }

        if example in examples:
            name, func = examples[example]
            print(f"\n🎯 Running: {name}\n")
            await func()
        else:
            print(f"Unknown example: {example}")
            print(f"Available: {', '.join(examples.keys())}")
    else:
        # Run product feature example by default
        print("\n🎯 Running: Product Feature Discussion (default)\n")
        print("Tip: Run with argument 1-4 to choose example:")
        print("  python autonomous_discussion.py 1  # Product feature")
        print("  python autonomous_discussion.py 2  # Research problem")
        print("  python autonomous_discussion.py 3  # Crisis response")
        print("  python autonomous_discussion.py 4  # Small team\n")

        await example_1_product_feature()


if __name__ == "__main__":
    asyncio.run(main())
