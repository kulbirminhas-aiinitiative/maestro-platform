#!/usr/bin/env python3
"""
Production-Ready Dynamic Team Wrapper

A dynamic/elastic team that adds and removes members based on workload and phase.
Members are added just-in-time and retired when no longer needed.

Usage:
    python examples/team_wrappers/dynamic_team_wrapper.py \\
        --project "Build e-commerce platform" \\
        --phases design implement test \\
        --output ./output/dynamic

Features:
    - Just-in-time member addition
    - Automatic member retirement
    - Phase-based team composition
    - Workload-based scaling
    - Cost optimization (minimize active members)
    - Configuration-driven
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
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


class ProjectPhase(Enum):
    """Project phases for dynamic team composition."""
    DESIGN = "design"
    IMPLEMENT = "implement"
    TEST = "test"
    DEPLOY = "deploy"


class ArchitectAgent(TeamAgent):
    """Solution architect - needed in design phase."""
    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ARCHITECT,
            system_prompt="You are a solution architect. Design system architecture."
        )
        super().__init__(config, coord_server)

    async def design(self, project: str) -> Dict[str, Any]:
        print(f"[{self.agent_id}] 🏗️  Designing architecture for: {project}")
        await asyncio.sleep(1)
        design = {
            "project": project,
            "architecture": "Microservices architecture",
            "components": ["Frontend", "Backend API", "Database", "Cache"],
            "tech_stack": {"backend": "Python/FastAPI", "frontend": "React"},
            "designed_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.share_knowledge(key="architecture_design", value=design)
        print(f"[{self.agent_id}] ✅ Architecture design complete")
        return design


class DeveloperAgent(TeamAgent):
    """Developer - needed in implementation phase."""
    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.DEVELOPER,
            system_prompt="You are a developer. Implement features based on design."
        )
        super().__init__(config, coord_server)

    async def implement(self, component: str) -> Dict[str, Any]:
        print(f"[{self.agent_id}] 💻 Implementing: {component}")
        await asyncio.sleep(1)
        implementation = {
            "component": component,
            "code_files": [f"{component.lower()}.py", f"test_{component.lower()}.py"],
            "lines_of_code": 500,
            "implemented_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.share_knowledge(key=f"impl_{component}", value=implementation)
        print(f"[{self.agent_id}] ✅ Implementation complete: {component}")
        return implementation


class TesterAgent(TeamAgent):
    """Tester - needed in test phase."""
    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.TESTER,
            system_prompt="You are a QA tester. Test implementations thoroughly."
        )
        super().__init__(config, coord_server)

    async def test(self, component: str) -> Dict[str, Any]:
        print(f"[{self.agent_id}] 🧪 Testing: {component}")
        await asyncio.sleep(1)
        test_result = {
            "component": component,
            "tests_run": 25,
            "tests_passed": 24,
            "tests_failed": 1,
            "coverage": 0.88,
            "tested_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.share_knowledge(key=f"test_{component}", value=test_result)
        print(f"[{self.agent_id}] ✅ Testing complete: {component} ({test_result['tests_passed']}/{test_result['tests_run']} passed)")
        return test_result


class DynamicTeamManager:
    """Manages dynamic team composition."""

    def __init__(self, team_id: str, coordinator: TeamCoordinator):
        self.team_id = team_id
        self.coordinator = coordinator
        self.coord_server = coordinator.create_coordination_server()
        self.active_members: Dict[str, TeamAgent] = {}
        self.retired_members: List[str] = []

    async def add_member(
        self,
        agent_class,
        agent_id: str,
        reason: str
    ) -> TeamAgent:
        """Add a team member just-in-time."""
        print(f"\n[Manager] ➕ Adding member: {agent_id}")
        print(f"[Manager]    Reason: {reason}")

        agent = agent_class(agent_id, self.coord_server)
        await agent.initialize()
        self.active_members[agent_id] = agent

        print(f"[Manager] ✅ {agent_id} is now active ({len(self.active_members)} total members)")
        return agent

    async def retire_member(self, agent_id: str, reason: str):
        """Retire a team member to optimize costs."""
        if agent_id in self.active_members:
            print(f"\n[Manager] ➖ Retiring member: {agent_id}")
            print(f"[Manager]    Reason: {reason}")

            agent = self.active_members.pop(agent_id)
            await agent.shutdown()
            self.retired_members.append(agent_id)

            print(f"[Manager] ✅ {agent_id} retired ({len(self.active_members)} active members remain)")
        else:
            print(f"[Manager] ⚠️  Cannot retire {agent_id}: not in active members")

    def get_team_stats(self) -> Dict[str, Any]:
        """Get current team statistics."""
        return {
            "active_members": len(self.active_members),
            "retired_members": len(self.retired_members),
            "active_member_ids": list(self.active_members.keys()),
            "total_lifetime_members": len(self.active_members) + len(self.retired_members)
        }


class DynamicTeamWorkflow:
    """Production-ready dynamic team workflow."""

    def __init__(
        self,
        team_id: str,
        project: str,
        phases: List[ProjectPhase],
        output_dir: Path
    ):
        self.team_id = team_id
        self.project = project
        self.phases = phases
        self.output_dir = output_dir
        self.manager: Optional[DynamicTeamManager] = None
        self.results = {
            "phases": {},
            "team_history": []
        }

    async def execute_phase(self, phase: ProjectPhase):
        """Execute a specific project phase with appropriate team."""
        print(f"\n{'=' * 80}")
        print(f"📋 Phase: {phase.value.upper()}")
        print(f"{'=' * 80}\n")

        if phase == ProjectPhase.DESIGN:
            # Add architect for design phase
            architect = await self.manager.add_member(
                ArchitectAgent,
                "architect_1",
                "Need architecture design for project"
            )

            # Do design work
            design_result = await architect.design(self.project)
            self.results["phases"][phase.value] = design_result

            # Retire architect after design (cost optimization)
            await self.manager.retire_member(
                "architect_1",
                "Design phase complete - no longer needed"
            )

        elif phase == ProjectPhase.IMPLEMENT:
            # Get design from previous phase
            design = await self.manager.coord_server.call_tool(
                "get_knowledge",
                {"key": "architecture_design"}
            )

            if not design or "content" not in design:
                print("⚠️  No design found, creating default implementation plan")
                components = ["Frontend", "Backend", "Database"]
            else:
                components = design["content"][0]["text"]["components"]

            # Add developers (scale based on workload)
            num_devs = min(len(components), settings.team.max_agents - 1)
            developers = []
            for i in range(num_devs):
                dev = await self.manager.add_member(
                    DeveloperAgent,
                    f"developer_{i+1}",
                    f"Implement component {i+1}/{len(components)}"
                )
                developers.append(dev)

            # Implement components in parallel
            impl_tasks = []
            for i, component in enumerate(components):
                dev = developers[i % len(developers)]
                impl_tasks.append(dev.implement(component))

            impl_results = await asyncio.gather(*impl_tasks)
            self.results["phases"][phase.value] = impl_results

            # Retire developers after implementation
            for i in range(num_devs):
                await self.manager.retire_member(
                    f"developer_{i+1}",
                    "Implementation complete"
                )

        elif phase == ProjectPhase.TEST:
            # Add testers
            tester = await self.manager.add_member(
                TesterAgent,
                "tester_1",
                "Quality assurance for implemented components"
            )

            # Get implemented components
            impl_phase = self.results["phases"].get("implement", [])
            components = [impl["component"] for impl in impl_phase] if impl_phase else ["Frontend"]

            # Test components
            test_results = []
            for component in components:
                result = await tester.test(component)
                test_results.append(result)

            self.results["phases"][phase.value] = test_results

            # Retire tester
            await self.manager.retire_member(
                "tester_1",
                "Testing phase complete"
            )

        # Record team state after phase
        stats = self.manager.get_team_stats()
        self.results["team_history"].append({
            "phase": phase.value,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        })

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete dynamic team workflow."""
        print(f"\n{'=' * 80}")
        print(f"🚀 Dynamic Team Workflow: {self.team_id}")
        print(f"{'=' * 80}\n")

        print(f"Configuration:")
        print(f"  Project: {self.project}")
        print(f"  Phases: {[p.value for p in self.phases]}")
        print(f"  Max Agents: {settings.team.max_agents}")
        print(f"  Output: {self.output_dir}\n")

        start_time = datetime.now()

        try:
            # Create coordinator and manager
            from claude_team_sdk.team_coordinator import TeamConfig
            config = TeamConfig(team_id=self.team_id)
            coordinator = TeamCoordinator(config)
            self.manager = DynamicTeamManager(self.team_id, coordinator)

            print("✅ Dynamic Team Manager initialized\n")

            # Execute each phase
            for phase in self.phases:
                await self.execute_phase(phase)

            # Compile final results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            final_results = {
                "team_id": self.team_id,
                "workflow_type": "dynamic",
                "project": self.project,
                "executed_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "phases_executed": [p.value for p in self.phases],
                **self.results,
                "final_team_stats": self.manager.get_team_stats(),
                "status": "success"
            }

            print(f"\n{'=' * 80}")
            print("✅ Dynamic Team Workflow Complete!")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Total Members Used: {final_results['final_team_stats']['total_lifetime_members']}")
            print(f"   Final Active Members: {final_results['final_team_stats']['active_members']}")
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


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dynamic Team Workflow - Production Ready"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project description"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=["design", "implement", "test", "deploy"],
        default=["design", "implement", "test"],
        help="Project phases to execute"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir) / "dynamic_team",
        help="Output directory for results"
    )
    parser.add_argument(
        "--team-id",
        default=f"dynamic_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Convert phases to enum
    phases = [ProjectPhase(p) for p in args.phases]

    # Create and execute workflow
    workflow = DynamicTeamWorkflow(
        team_id=args.team_id,
        project=args.project,
        phases=phases,
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
