"""
Example of a Parallel Team.

Demonstrates multiple agents working on independent tasks concurrently.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from claude_team_sdk.agent_base import TeamAgent, AgentConfig, AgentRole
from claude_team_sdk.team_coordinator import TeamCoordinator, TeamConfig

class ResearchAgent(TeamAgent):
    """An agent that performs 'research' on a topic."""
    def __init__(self, agent_id, coord_server):
        super().__init__(
            config=AgentConfig(
                agent_id=agent_id,
                role=AgentRole.RESEARCHER,
                system_prompt="You are a research agent. You investigate topics."
            ),
            coordination_server=coord_server
        )

    async def research(self, topic: str):
        """Simulates the research process."""
        print(f"[{self.agent_id}] Starting research on: {topic}")
        # Simulate a network call or long-running task
        await asyncio.sleep(2)
        result = f"Findings on {topic}: It is a complex subject with many facets."
        await self.share_knowledge(key=f"research_{topic}", value=result)
        print(f"[{self.agent_id}] Research complete for: {topic}")

async def main():
    """Main function to run the parallel team example."""
    print("🚀 Parallel Team Example 🚀")

    # 1. Setup coordinator
    coordinator = TeamCoordinator(TeamConfig(team_id="parallel_team"))
    coord_server = coordinator.create_coordination_server()

    # 2. Create multiple agents of the same type
    researcher1 = ResearchAgent("researcher_rob", coord_server)
    researcher2 = ResearchAgent("researcher_rachel", coord_server)
    
    print("\\nTeam Members:")
    print(f"- {researcher1.agent_id} ({researcher1.config.role.value})")
    print(f"- {researcher2.agent_id} ({researcher2.config.role.value})")

    # 3. Define tasks for the agents to run in parallel
    topic1 = "quantum_computing"
    topic2 = "neural_networks"
    
    print(f"\\nStarting parallel research on '{topic1}' and '{topic2}'...")

    # 4. Initialize agents and run their tasks concurrently using asyncio.gather
    await researcher1.initialize()
    await researcher2.initialize()
    
    await asyncio.gather(
        researcher1.research(topic1),
        researcher2.research(topic2)
    )

    # 5. Verify that the knowledge was shared
    print("\\nVerifying results...")
    result1 = await coordinator.shared_workspace['knowledge'].get(f"research_{topic1}")
    result2 = await coordinator.shared_workspace['knowledge'].get(f"research_{topic2}")

    if result1:
        print(f"- Result for '{topic1}' found.")
    if result2:
        print(f"- Result for '{topic2}' found.")

    await researcher1.shutdown()
    await researcher2.shutdown()

    print("\\n✅ Parallel team workflow complete!")

if __name__ == "__main__":
    asyncio.run(main())
