#!/usr/bin/env python3
"""
Production-Ready Parallel Team Wrapper

A parallel team where multiple agents work concurrently on independent tasks.
Uses configuration system and resilience patterns.

Usage:
    python examples/team_wrappers/parallel_team_wrapper.py \\
        --tasks "Research AI trends" "Analyze competitors" "Market survey" \\
        --agents 3 \\
        --output ./output/research

Features:
    - Concurrent execution (asyncio.gather)
    - Configuration-driven
    - Resilience patterns
    - Load balancing across agents
    - Progress tracking
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Use new src structure
try:
    from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from src.claude_team_sdk.config import settings
    from src.claude_team_sdk.resilience import CircuitBreaker, retry_with_backoff, Bulkhead
except ImportError:
    from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from claude_team_sdk.config import settings
    from claude_team_sdk.resilience import CircuitBreaker, retry_with_backoff, Bulkhead


class ResearchAgent(TeamAgent):
    """Agent that performs parallel research on topics."""

    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.RESEARCHER,
            system_prompt="You are a research agent. Conduct thorough research on assigned topics."
        )
        super().__init__(config, coord_server)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.resilience.circuit_breaker.failure_threshold,
            name=f"{agent_id}_circuit"
        )

    async def research(self, task: str, task_id: int) -> Dict[str, Any]:
        """Research a specific task."""
        print(f"[{self.agent_id}] 🔍 Starting research: {task}")

        async def do_research():
            # Simulate research time (in production, this would call Claude API)
            await asyncio.sleep(2)  # Simulates API call

            research_result = {
                "task_id": task_id,
                "task": task,
                "agent_id": self.agent_id,
                "started_at": datetime.now().isoformat(),
                "findings": {
                    "summary": f"Comprehensive research on {task}",
                    "key_points": [
                        f"Finding 1 for {task}",
                        f"Finding 2 for {task}",
                        f"Finding 3 for {task}"
                    ],
                    "sources": ["Source A", "Source B", "Source C"],
                    "confidence": 0.85
                },
                "completed_at": datetime.now().isoformat()
            }
            return research_result

        # Execute with resilience
        result = await self.circuit_breaker.call(
            retry_with_backoff,
            do_research,
            max_retries=settings.resilience.retry.max_retries,
            name=f"{self.agent_id}_research_{task_id}"
        )

        # Share findings with team
        await self.share_knowledge(
            key=f"research_{task_id}",
            value=result
        )

        print(f"[{self.agent_id}] ✅ Completed: {task}")
        return result


class ParallelTeamWorkflow:
    """Production-ready parallel team workflow."""

    def __init__(
        self,
        team_id: str,
        tasks: List[str],
        num_agents: int,
        output_dir: Path
    ):
        self.team_id = team_id
        self.tasks = tasks
        self.num_agents = num_agents
        self.output_dir = output_dir
        self.coordinator = None
        self.agents: List[ResearchAgent] = []

        # Bulkhead to limit concurrent operations
        self.bulkhead = Bulkhead(
            max_concurrent=settings.resilience.bulkhead.max_concurrent_agents,
            name="parallel_team_bulkhead"
        )

    async def distribute_tasks(self) -> List[Dict[str, Any]]:
        """Distribute tasks across agents and execute in parallel."""
        print(f"\n📊 Task Distribution:")
        print(f"  Total Tasks: {len(self.tasks)}")
        print(f"  Available Agents: {self.num_agents}")
        print(f"  Max Concurrent: {settings.resilience.bulkhead.max_concurrent_agents}\n")

        # Create task assignments (round-robin)
        assignments = []
        for task_id, task in enumerate(self.tasks):
            agent_idx = task_id % self.num_agents
            agent = self.agents[agent_idx]
            assignments.append({
                "task_id": task_id,
                "task": task,
                "agent": agent,
                "agent_id": agent.agent_id
            })
            print(f"  Task {task_id}: '{task}' → {agent.agent_id}")

        print("\n⚙️  Executing tasks in parallel...\n")

        # Execute all tasks concurrently with bulkhead protection
        async def execute_with_bulkhead(assignment):
            return await self.bulkhead.call(
                assignment["agent"].research,
                assignment["task"],
                assignment["task_id"]
            )

        results = await asyncio.gather(
            *[execute_with_bulkhead(a) for a in assignments],
            return_exceptions=True
        )

        # Process results
        successful_results = []
        failed_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "task_id": i,
                    "task": self.tasks[i],
                    "error": str(result),
                    "status": "failed"
                })
                print(f"  ❌ Task {i} failed: {str(result)}")
            else:
                successful_results.append(result)

        print(f"\n📈 Execution Summary:")
        print(f"  Successful: {len(successful_results)}/{len(self.tasks)}")
        print(f"  Failed: {len(failed_results)}/{len(self.tasks)}")

        return successful_results, failed_results

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete parallel team workflow."""
        print(f"\n{'=' * 80}")
        print(f"🚀 Parallel Team Workflow: {self.team_id}")
        print(f"{'=' * 80}\n")

        print(f"Configuration:")
        print(f"  Environment: {settings.service.environment}")
        print(f"  Max Agents: {settings.team.max_agents}")
        print(f"  Bulkhead Limit: {settings.resilience.bulkhead.max_concurrent_agents}")
        print(f"  Circuit Breaker Threshold: {settings.resilience.circuit_breaker.failure_threshold}")
        print(f"  Output Directory: {self.output_dir}\n")

        start_time = datetime.now()

        try:
            # Create team coordinator
            print("📋 Setting up team coordinator...")
            from claude_team_sdk.team_coordinator import TeamConfig
            config = TeamConfig(
                team_id=self.team_id,
                max_agents=self.num_agents
            )
            self.coordinator = TeamCoordinator(config)
            coord_server = self.coordinator.create_coordination_server()
            print("✅ Coordinator ready\n")

            # Create agents
            print(f"👥 Creating {self.num_agents} research agents...")
            for i in range(self.num_agents):
                agent = ResearchAgent(f"researcher_{i+1}", coord_server)
                await agent.initialize()
                self.agents.append(agent)
                print(f"  ✅ {agent.agent_id} initialized")
            print()

            # Distribute and execute tasks
            successful_results, failed_results = await self.distribute_tasks()

            # Calculate metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Compile final results
            results = {
                "team_id": self.team_id,
                "workflow_type": "parallel",
                "num_agents": self.num_agents,
                "num_tasks": len(self.tasks),
                "executed_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "tasks_per_second": len(self.tasks) / duration if duration > 0 else 0,
                "results": {
                    "successful": successful_results,
                    "failed": failed_results
                },
                "success_rate": len(successful_results) / len(self.tasks) if self.tasks else 0,
                "status": "success" if not failed_results else "partial_success"
            }

            # Save individual research results
            self.output_dir.mkdir(parents=True, exist_ok=True)
            for result in successful_results:
                result_file = self.output_dir / f"research_{result['task_id']}.json"
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)

            print(f"\n{'=' * 80}")
            print("✅ Parallel Workflow Complete!")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Throughput: {results['tasks_per_second']:.2f} tasks/second")
            print(f"   Success Rate: {results['success_rate']*100:.1f}%")
            print(f"{'=' * 80}\n")

            return results

        except Exception as e:
            print(f"\n❌ Error in workflow: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "team_id": self.team_id
            }

        finally:
            # Cleanup
            print("🧹 Cleaning up...")
            for agent in self.agents:
                await agent.shutdown()
            print("✅ Cleanup complete\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parallel Team Workflow - Production Ready"
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        required=True,
        help="List of research tasks to execute in parallel"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=3,
        help="Number of research agents to create"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir) / "parallel_team",
        help="Output directory for results"
    )
    parser.add_argument(
        "--team-id",
        default=f"parallel_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Validate
    if args.agents > settings.team.max_agents:
        print(f"⚠️  Warning: Requested {args.agents} agents but max is {settings.team.max_agents}")
        args.agents = settings.team.max_agents

    # Create and execute workflow
    workflow = ParallelTeamWorkflow(
        team_id=args.team_id,
        tasks=args.tasks,
        num_agents=args.agents,
        output_dir=args.output
    )

    results = await workflow.execute()

    # Save summary
    summary_file = args.output / "workflow_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 Summary saved to: {summary_file}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
