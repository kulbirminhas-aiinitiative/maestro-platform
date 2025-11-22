"""
Example of a Static Team with a Sequential Workflow.

Demonstrates a simple, fixed team where one agent's work is passed to the next.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from claude_team_sdk.agent_base import TeamAgent, AgentConfig, AgentRole
from claude_team_sdk.team_coordinator import TeamCoordinator, TeamConfig

class AnalystAgent(TeamAgent):
    """An agent that analyzes data and writes a report."""
    def __init__(self, agent_id, coord_server):
        super().__init__(
            config=AgentConfig(
                agent_id=agent_id,
                role=AgentRole.ANALYST,
                system_prompt="You are an analyst. Your job is to write a brief report on a topic."
            ),
            coordination_server=coord_server
        )

    async def write_report(self, topic: str) -> str:
        print(f"[{self.agent_id}] Writing a report on: {topic}")
        report = f"This is a brief report about {topic}. It concludes that the matter is important."
        # In a real scenario, this would involve an LLM call.
        await self.share_knowledge(key=f"report_{topic}", value=report)
        print(f"[{self.agent_id}] Report finished and shared.")
        return report

class ReviewerAgent(TeamAgent):
    """An agent that reviews a report."""
    def __init__(self, agent_id, coord_server):
        super().__init__(
            config=AgentConfig(
                agent_id=agent_id,
                role=AgentRole.REVIEWER,
                system_prompt="You are a reviewer. Your job is to review a report and provide feedback."
            ),
            coordination_server=coord_server
        )

    async def review_report(self, topic: str):
        print(f"[{self.agent_id}] Looking for report on '{topic}' to review.")
        report = await self.get_knowledge(f"report_{topic}")
        if report:
            print(f"[{self.agent_id}] Found report: '{report}'")
            print(f"[{self.agent_id}] Review complete. The report looks good.")
        else:
            print(f"[{self.agent_id}] Could not find a report for '{topic}'.")

async def main():
    """Main function to run the static team example."""
    print("🚀 Static Team (Sequential Workflow) Example 🚀")
    
    # 1. Setup coordinator
    coordinator = TeamCoordinator(TeamConfig(team_id="static_team"))
    coord_server = coordinator.create_coordination_server()

    # 2. Create a fixed team of agents
    analyst = AnalystAgent("analyst_andy", coord_server)
    reviewer = ReviewerAgent("reviewer_rita", coord_server)
    
    print("\\nTeam Members:")
    print(f"- {analyst.agent_id} ({analyst.config.role.value})")
    print(f"- {reviewer.agent_id} ({reviewer.config.role.value})")
    
    # 3. Execute workflow sequentially
    print("\\nStarting sequential workflow...")
    topic = "the importance of teamwork"
    
    # Analyst runs first
    await analyst.initialize()
    await analyst.write_report(topic)
    await analyst.shutdown()

    # Reviewer runs second
    await reviewer.initialize()
    await reviewer.review_report(topic)
    await reviewer.shutdown()
    
    print("\\n✅ Static team workflow complete!")

if __name__ == "__main__":
    asyncio.run(main())
