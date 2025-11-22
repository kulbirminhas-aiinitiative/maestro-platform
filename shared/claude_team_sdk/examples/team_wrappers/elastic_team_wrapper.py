#!/usr/bin/env python3
"""
Production-Ready Elastic Team Wrapper

An advanced elastic team with:
- Role-based task assignment (tasks assigned to roles, not individuals)
- Onboarding briefings (new members get context)
- Knowledge handoffs (departing members transfer knowledge)
- Workload-based auto-scaling
- Seamless member substitution

Usage:
    python examples/team_wrappers/elastic_team_wrapper.py \\
        --project "Payment Gateway Integration" \\
        --workload high \\
        --output ./output/elastic

Features:
    - Role abstraction (roles != agents)
    - Context-aware onboarding
    - Knowledge preservation
    - Auto-scaling based on workload
    - Cost optimization
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Use new src structure
try:
    from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from src.claude_team_sdk.config import settings
    from src.claude_team_sdk.resilience import CircuitBreaker
except ImportError:
    from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from claude_team_sdk.config import settings
    from claude_team_sdk.resilience import CircuitBreaker


class WorkloadLevel(Enum):
    """Workload levels for auto-scaling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TeamRole(Enum):
    """Team roles (abstract from individuals)."""
    TECH_LEAD = "Tech Lead"
    BACKEND_LEAD = "Backend Lead"
    FRONTEND_LEAD = "Frontend Lead"
    QA_LEAD = "QA Lead"


class ElasticAgent(TeamAgent):
    """Enhanced agent with onboarding and knowledge handoff."""

    def __init__(self, agent_id: str, coord_server, role: TeamRole, briefing: Optional[Dict] = None):
        config = AgentConfig(
            agent_id=agent_id,
            role=self._map_role_to_agent_role(role),
            system_prompt=f"You are {role.value}. {self._get_role_prompt(role)}"
        )
        super().__init__(config, coord_server)
        self.team_role = role
        self.briefing = briefing or {}
        self.knowledge_items: List[str] = []

    @staticmethod
    def _map_role_to_agent_role(role: TeamRole) -> AgentRole:
        """Map team role to agent role."""
        mapping = {
            TeamRole.TECH_LEAD: AgentRole.ARCHITECT,
            TeamRole.BACKEND_LEAD: AgentRole.DEVELOPER,
            TeamRole.FRONTEND_LEAD: AgentRole.DEVELOPER,
            TeamRole.QA_LEAD: AgentRole.TESTER,
        }
        return mapping.get(role, AgentRole.DEVELOPER)

    @staticmethod
    def _get_role_prompt(role: TeamRole) -> str:
        """Get role-specific prompt."""
        prompts = {
            TeamRole.TECH_LEAD: "Lead technical decisions and architecture.",
            TeamRole.BACKEND_LEAD: "Lead backend development and API design.",
            TeamRole.FRONTEND_LEAD: "Lead frontend development and UX.",
            TeamRole.QA_LEAD: "Lead quality assurance and testing.",
        }
        return prompts.get(role, "Contribute to the team.")

    async def onboard(self):
        """Process onboarding briefing."""
        if self.briefing:
            print(f"\n[{self.agent_id}] 📚 Onboarding Briefing:")
            print(f"   Role: {self.team_role.value}")
            print(f"   Context: {self.briefing.get('context', 'No context provided')}")
            print(f"   Current Phase: {self.briefing.get('current_phase', 'unknown')}")
            print(f"   Key Points: {len(self.briefing.get('key_points', []))} items")
        await self.initialize()

    async def create_knowledge_handoff(self) -> Dict[str, Any]:
        """Create knowledge handoff for successor."""
        print(f"\n[{self.agent_id}] 📝 Creating knowledge handoff...")

        handoff = {
            "from_agent": self.agent_id,
            "role": self.team_role.value,
            "created_at": datetime.now().isoformat(),
            "knowledge_items": self.knowledge_items,
            "status": {
                "work_completed": "All assigned tasks completed",
                "pending_items": [],
                "recommendations": "Maintain current architecture approach"
            },
            "context": "Smooth transition - all documentation updated"
        }

        # Share handoff
        await self.share_knowledge(
            key=f"handoff_{self.team_role.value.replace(' ', '_')}",
            value=handoff
        )

        print(f"[{self.agent_id}] ✅ Knowledge handoff created")
        return handoff

    async def execute_role_task(self, task: str):
        """Execute a task for this role."""
        print(f"\n[{self.agent_id}] ⚙️  Executing: {task}")
        await asyncio.sleep(1)  # Simulate work

        result = {
            "task": task,
            "role": self.team_role.value,
            "agent": self.agent_id,
            "completed_at": datetime.now().isoformat(),
            "outcome": f"Successfully completed {task}"
        }

        # Track knowledge item
        self.knowledge_items.append(task)

        # Share result
        await self.share_knowledge(
            key=f"task_{task.replace(' ', '_').lower()}",
            value=result
        )

        print(f"[{self.agent_id}] ✅ Task complete: {task}")
        return result


class ElasticTeamManager:
    """Manages elastic team with role-based composition."""

    def __init__(self, team_id: str, coordinator: TeamCoordinator, project: str):
        self.team_id = team_id
        self.coordinator = coordinator
        self.coord_server = coordinator.create_coordination_server()
        self.project = project

        # Role-based tracking (role -> agent mapping)
        self.roles: Dict[TeamRole, Optional[ElasticAgent]] = {
            role: None for role in TeamRole
        }

        # History
        self.member_history: List[Dict] = []

    async def assign_role(
        self,
        role: TeamRole,
        agent_id: str,
        reason: str,
        previous_handoff: Optional[Dict] = None
    ) -> ElasticAgent:
        """Assign an agent to a role with onboarding."""
        print(f"\n[Manager] 🎭 Assigning role: {role.value}")
        print(f"[Manager]    Agent: {agent_id}")
        print(f"[Manager]    Reason: {reason}")

        # Create briefing
        briefing = {
            "role": role.value,
            "project": self.project,
            "context": reason,
            "current_phase": "active",
            "key_points": [
                f"You are taking over as {role.value}",
                "Review shared knowledge for context",
                "Coordinate with other team members"
            ]
        }

        # If there's a handoff from previous agent, include it
        if previous_handoff:
            briefing["handoff"] = previous_handoff
            briefing["key_points"].append("Knowledge handoff from previous member available")

        # Create and onboard agent
        agent = ElasticAgent(agent_id, self.coord_server, role, briefing)
        await agent.onboard()

        # Assign to role
        self.roles[role] = agent

        # Record history
        self.member_history.append({
            "action": "assigned",
            "role": role.value,
            "agent_id": agent_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

        print(f"[Manager] ✅ {agent_id} assigned to {role.value}")
        return agent

    async def replace_role(
        self,
        role: TeamRole,
        new_agent_id: str,
        reason: str
    ):
        """Replace an agent in a role with knowledge handoff."""
        print(f"\n[Manager] 🔄 Replacing {role.value}")

        current_agent = self.roles.get(role)
        handoff = None

        # Get handoff from current agent
        if current_agent:
            print(f"[Manager]    Current: {current_agent.agent_id}")
            handoff = await current_agent.create_knowledge_handoff()
            await current_agent.shutdown()

            self.member_history.append({
                "action": "retired",
                "role": role.value,
                "agent_id": current_agent.agent_id,
                "reason": "Replacement",
                "timestamp": datetime.now().isoformat()
            })

        # Assign new agent with handoff
        await self.assign_role(role, new_agent_id, reason, handoff)

    async def scale_team(self, workload: WorkloadLevel):
        """Auto-scale team based on workload."""
        print(f"\n[Manager] 📊 Auto-scaling for {workload.value} workload...")

        if workload == WorkloadLevel.LOW:
            # Minimal team
            roles_needed = [TeamRole.TECH_LEAD]
        elif workload == WorkloadLevel.MEDIUM:
            # Standard team
            roles_needed = [TeamRole.TECH_LEAD, TeamRole.BACKEND_LEAD]
        else:  # HIGH
            # Full team
            roles_needed = [TeamRole.TECH_LEAD, TeamRole.BACKEND_LEAD,
                          TeamRole.FRONTEND_LEAD, TeamRole.QA_LEAD]

        # Assign needed roles
        for i, role in enumerate(roles_needed):
            if not self.roles.get(role):
                await self.assign_role(
                    role,
                    f"{role.value.lower().replace(' ', '_')}_{i+1}",
                    f"Required for {workload.value} workload"
                )

        active_roles = [r.value for r, a in self.roles.items() if a is not None]
        print(f"[Manager] ✅ Team scaled: {len(active_roles)} active roles")

    def get_team_composition(self) -> Dict[str, Any]:
        """Get current team composition."""
        return {
            "roles": {
                role.value: agent.agent_id if agent else None
                for role, agent in self.roles.items()
            },
            "active_members": sum(1 for a in self.roles.values() if a),
            "total_history": len(self.member_history)
        }


class ElasticTeamWorkflow:
    """Production-ready elastic team workflow."""

    def __init__(
        self,
        team_id: str,
        project: str,
        workload: WorkloadLevel,
        output_dir: Path
    ):
        self.team_id = team_id
        self.project = project
        self.workload = workload
        self.output_dir = output_dir
        self.manager: Optional[ElasticTeamManager] = None

    async def execute(self) -> Dict[str, Any]:
        """Execute elastic team workflow."""
        print(f"\n{'=' * 80}")
        print(f"🚀 Elastic Team Workflow: {self.team_id}")
        print(f"{'=' * 80}\n")

        print(f"Configuration:")
        print(f"  Project: {self.project}")
        print(f"  Workload: {self.workload.value}")
        print(f"  Max Agents: {settings.team.max_agents}")
        print(f"  Output: {self.output_dir}\n")

        start_time = datetime.now()

        try:
            # Create coordinator and manager
            from claude_team_sdk.team_coordinator import TeamConfig
            config = TeamConfig(team_id=self.team_id)
            coordinator = TeamCoordinator(config)
            self.manager = ElasticTeamManager(self.team_id, coordinator, self.project)

            print("✅ Elastic Team Manager initialized\n")

            # Phase 1: Initial team scaling
            print(f"{'=' * 80}")
            print("Phase 1: Team Scaling")
            print(f"{'=' * 80}")
            await self.manager.scale_team(self.workload)

            # Phase 2: Execute tasks with role-based assignment
            print(f"\n{'=' * 80}")
            print("Phase 2: Task Execution")
            print(f"{'=' * 80}")

            tasks = {
                TeamRole.TECH_LEAD: "Define system architecture",
                TeamRole.BACKEND_LEAD: "Design API endpoints",
                TeamRole.FRONTEND_LEAD: "Design UI components",
                TeamRole.QA_LEAD: "Create test strategy"
            }

            results = []
            for role, task in tasks.items():
                agent = self.manager.roles.get(role)
                if agent:
                    result = await agent.execute_role_task(task)
                    results.append(result)

            # Phase 3: Demonstrate role replacement (with knowledge handoff)
            print(f"\n{'=' * 80}")
            print("Phase 3: Role Replacement (Knowledge Handoff)")
            print(f"{'=' * 80}")

            if self.manager.roles.get(TeamRole.BACKEND_LEAD):
                await self.manager.replace_role(
                    TeamRole.BACKEND_LEAD,
                    "backend_lead_2",
                    "Original member completed tenure - seamless transition"
                )

            # Compile results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            final_results = {
                "team_id": self.team_id,
                "workflow_type": "elastic",
                "project": self.project,
                "workload": self.workload.value,
                "executed_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "team_composition": self.manager.get_team_composition(),
                "tasks_completed": len(results),
                "member_history": self.manager.member_history,
                "status": "success"
            }

            print(f"\n{'=' * 80}")
            print("✅ Elastic Team Workflow Complete!")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Active Roles: {final_results['team_composition']['active_members']}")
            print(f"   Total Members Used: {final_results['team_composition']['total_history']}")
            print(f"   Tasks Completed: {len(results)}")
            print(f"{'=' * 80}\n")

            return final_results

        except Exception as e:
            print(f"\n❌ Error in workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "team_id": self.team_id
            }

        finally:
            # Cleanup all active agents
            if self.manager:
                print("🧹 Cleaning up...")
                for role, agent in self.manager.roles.items():
                    if agent:
                        await agent.shutdown()
                print("✅ Cleanup complete\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Elastic Team Workflow - Production Ready"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project description"
    )
    parser.add_argument(
        "--workload",
        choices=["low", "medium", "high"],
        default="medium",
        help="Workload level (affects team size)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir) / "elastic_team",
        help="Output directory for results"
    )
    parser.add_argument(
        "--team-id",
        default=f"elastic_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Create and execute workflow
    workflow = ElasticTeamWorkflow(
        team_id=args.team_id,
        project=args.project,
        workload=WorkloadLevel(args.workload),
        output_dir=args.output
    )

    results = await workflow.execute()

    # Save results
    args.output.mkdir(parents=True, exist_ok=True)
    results_file = args.output / "workflow_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 Results saved to: {results_file}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
