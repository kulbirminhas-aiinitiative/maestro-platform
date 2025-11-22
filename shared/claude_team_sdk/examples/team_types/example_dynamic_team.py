"""
Example of a Dynamic/Elastic Team.

Demonstrates a team that changes its composition based on project needs.
It uses a simplified, in-memory version of the DynamicTeamManager for clarity.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from claude_team_sdk.agent_base import TeamAgent, AgentConfig, AgentRole
from claude_team_sdk.team_coordinator import TeamCoordinator, TeamConfig

class ProjectManagerAgent(TeamAgent):
    """A simplified Project Manager agent."""
    def __init__(self, agent_id, coord_server):
        super().__init__(
            config=AgentConfig(
                agent_id=agent_id,
                role=AgentRole.COORDINATOR,
                system_prompt="You are a project manager. You define tasks."
            ),
            coordination_server=coord_server
        )

    async def define_task(self, task_description: str):
        print(f"[{self.agent_id}] Defining task: {task_description}")
        await self.post_message("all", f"New task available: {task_description}")

class DeveloperAgent(TeamAgent):
    """A simplified Developer agent."""
    def __init__(self, agent_id, coord_server):
        super().__init__(
            config=AgentConfig(
                agent_id=agent_id,
                role=AgentRole.DEVELOPER,
                system_prompt="You are a developer. You write code."
            ),
            coordination_server=coord_server
        )

    async def implement_task(self, task_description: str):
        print(f"[{self.agent_id}] Implementing task: {task_description}")
        await asyncio.sleep(1) # Simulate coding
        code = "print('Hello, World!')"
        await self.share_knowledge(key="final_code", value=code)
        print(f"[{self.agent_id}] Implementation complete.")

class SimpleDynamicTeamManager:
    """A simplified, in-memory manager for dynamic teams."""
    def __init__(self, coordinator: TeamCoordinator):
        self.coordinator = coordinator
        self.team: Dict[str, TeamAgent] = {}
        print("[Manager] Dynamic Team Manager initialized.")

    async def add_agent(self, agent_class, agent_id: str) -> TeamAgent:
        """Adds an agent to the team just-in-time."""
        print(f"[Manager] Adding '{agent_id}' to the team.")
        agent = agent_class(agent_id, self.coordinator.create_coordination_server())
        await agent.initialize()
        self.team[agent_id] = agent
        print(f"[Manager] '{agent_id}' is now active.")
        return agent

    async def retire_agent(self, agent_id: str):
        """Retires an agent when their task is done."""
        if agent_id in self.team:
            print(f"[Manager] Retiring '{agent_id}' from the team.")
            agent = self.team.pop(agent_id)
            await agent.shutdown()
            print(f"[Manager] '{agent_id}' is now retired.")
        else:
            print(f"[Manager] Agent '{agent_id}' not found in team.")

async def main():
    """Main function to run the dynamic team example."""
    print("🚀 Dynamic/Elastic Team Example 🚀")

    # 1. Setup coordinator and dynamic manager
    coordinator = TeamCoordinator(TeamConfig(team_id="dynamic_team"))
    manager = SimpleDynamicTeamManager(coordinator)

    # 2. Start with a single agent: the Project Manager
    print("\\n--- Phase 1: Project Inception ---")
    pm = await manager.add_agent(ProjectManagerAgent, "pm_paula")
    
    # PM defines the work
    task = "Create a simple Python script."
    await pm.define_task(task)

    # 3. Manager decides a developer is needed and adds one to the team
    print("\\n--- Phase 2: Development ---")
    dev = await manager.add_agent(DeveloperAgent, "dev_dave")
    
    # Developer implements the task
    await dev.implement_task(task)

    # 4. The developer's work is done, so the manager retires them to save 'costs'
    print("\\n--- Phase 3: Task Completion ---")
    await manager.retire_agent("dev_dave")

    # 5. Final state check
    print("\\nFinal team composition:", list(manager.team.keys()))
    final_code = await coordinator.shared_workspace['knowledge'].get("final_code")
    print(f"Final artifact 'final_code': {final_code}")

    # Clean up remaining agents
    await manager.retire_agent("pm_paula")
    
    print("\\n✅ Dynamic team workflow complete!")

if __name__ == "__main__":
    asyncio.run(main())
