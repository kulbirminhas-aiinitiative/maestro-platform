#!/usr/bin/env python3
"""
SDK Pattern: Autonomous Swarm

Multiple similar agents autonomously claim tasks, share discoveries,
and build collective intelligence through the SDK's knowledge sharing.

Usage:
    python examples/sdk_patterns/pattern_autonomous_swarm.py \
        --requirement "Research authentication security for microservices" \
        --agents 5 \
        --output ./output/swarm

How it works:
1. Creates N research agents (all same role)
2. Breaks requirement into research tasks
3. Agents autonomously claim tasks from queue
4. Each shares findings via share_knowledge
5. Final synthesizer compiles all knowledge into report

SDK Features Used:
- claim_task (autonomous task claiming)
- share_knowledge (collective intelligence)
- get_knowledge (synthesis)
- Parallel execution
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List
from datetime import datetime
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig
from src.claude_team_sdk.config import settings

logger = logging.getLogger(__name__)


class SwarmResearcher(TeamAgent):
    """Autonomous research agent for swarm pattern"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            auto_claim_tasks=True,
            system_prompt=f"""You are {agent_id}, an autonomous research agent in a swarm.

AUTONOMOUS WORKFLOW:
1. Claim unclaimed research tasks from queue (use claim_task)
2. Conduct thorough research using Claude Code tools
3. Create detailed research document (use Write tool)
4. Share ALL key findings via share_knowledge tool
5. Complete task (use complete_task)
6. Repeat until no tasks remain

CRITICAL - KNOWLEDGE SHARING:
- Share specific, actionable insights
- Use descriptive keys: "security_best_practices", "common_vulnerabilities", etc.
- Each finding should be substantial (not generic)
- Check what others discovered (use get_knowledge) to avoid duplication

RESEARCH OUTPUT:
- Create markdown file: research_<topic>.md
- Include: summary, detailed findings, best practices, recommendations
- Be specific and technical

Work independently but share generously."""
        )
        super().__init__(config, coordination_server)

    async def execute_task(self, task_description: str):
        """Execute research task"""
        await self._update_status(AgentStatus.WORKING, task_description)
        return {"success": True, "agent_id": self.agent_id}

    async def execute_role_specific_work(self):
        """Autonomous task loop"""
        await self._auto_task_loop()


class KnowledgeSynthesizer(TeamAgent):
    """Synthesizes swarm's collective knowledge"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, the Knowledge Synthesizer.

Your job: Compile swarm's collective intelligence into comprehensive report.

SYNTHESIS WORKFLOW:
1. Wait for all research tasks to complete
2. Check team messages to see what was researched
3. Retrieve ALL knowledge items (use get_knowledge for each)
4. Create comprehensive synthesis report combining all insights
5. Identify patterns and contradictions across findings
6. Generate actionable recommendations

OUTPUT:
- File: SWARM_SYNTHESIS.md
- Sections: Executive Summary, Integrated Findings, Patterns, Recommendations
- Reference all agent contributions

Make the synthesis more valuable than individual parts."""
        )
        super().__init__(config, coordination_server)

    async def synthesize(self, coordinator: TeamCoordinator):
        """Synthesize all swarm knowledge"""
        await self._update_status(AgentStatus.WORKING, "Synthesizing")

        logger.info(f"[{self.agent_id}] 🧩 Synthesizing swarm knowledge...")

        # Get all knowledge items
        knowledge_items = coordinator.shared_workspace["knowledge"]

        # Build context for synthesis
        knowledge_context = "\n".join([
            f"- {key}: {item['value'][:200]}... (from {item['from']})"
            for key, item in knowledge_items.items()
        ])

        await self.client.query(
            f"""Synthesize all research from the swarm:

AVAILABLE KNOWLEDGE:
{knowledge_context}

TASK:
1. Retrieve full details for each knowledge item (use get_knowledge)
2. Analyze all findings holistically
3. Identify common themes and patterns
4. Note contradictions or differing viewpoints
5. Create comprehensive synthesis report

CREATE FILE: SWARM_SYNTHESIS.md

Structure:
# Swarm Research Synthesis

## Executive Summary
[High-level overview of all findings]

## Integrated Findings
[Comprehensive integration of all research]

## Common Patterns
[Themes across multiple agents' findings]

## Contradictions & Trade-offs
[Where findings differ or conflict]

## Actionable Recommendations
[Specific next steps based on collective intelligence]

## Agent Contributions
[Credit each agent's key contributions]

Use Write tool to create this file."""
        )

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)
                        logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

        await self._update_status(AgentStatus.IDLE, "Synthesis complete")
        return files_created

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


async def run_swarm_pattern(requirement: str, num_agents: int, output_dir: Path):
    """Execute autonomous swarm pattern"""

    print("=" * 80)
    print("🐝 AUTONOMOUS SWARM PATTERN")
    print("=" * 80)
    print(f"Requirement: {requirement}")
    print(f"Swarm Size: {num_agents} agents")
    print(f"Output: {output_dir}")
    print("=" * 80)
    print()

    start_time = datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create team coordinator
    team_config = TeamConfig(
        team_id=f"swarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        workspace_path=output_dir,
        max_agents=num_agents + 1  # swarm + synthesizer
    )
    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    print("📋 Breaking requirement into research tasks...")

    # Break requirement into subtasks
    subtasks = [
        f"Research: {requirement} - Best practices and industry standards",
        f"Research: {requirement} - Common pitfalls and anti-patterns",
        f"Research: {requirement} - Implementation strategies",
        f"Research: {requirement} - Security considerations",
        f"Research: {requirement} - Performance optimization"
    ]

    for task in subtasks[:num_agents]:  # Limit to swarm size
        task_id = await coordinator.add_task(task, required_role="researcher")
        print(f"  ✓ Added: {task_id}")

    print()
    print(f"🐝 Spawning swarm of {num_agents} autonomous researchers...")

    # Create swarm
    swarm = []
    for i in range(num_agents):
        agent = SwarmResearcher(f"researcher_{i+1}", coord_server)
        await agent.initialize()
        swarm.append(agent)
        print(f"  ✓ {agent.agent_id} ready")

    print()
    print("🚀 Releasing swarm (agents will self-organize)...")
    print()

    # Start swarm autonomously
    swarm_tasks = [asyncio.create_task(agent.run()) for agent in swarm]

    # Monitor progress
    while True:
        await asyncio.sleep(3)
        state = await coordinator.get_workspace_state()

        print(f"  Progress: {state['tasks']['completed']}/{state['tasks']['total']} tasks | "
              f"Knowledge: {state['knowledge_items']} items | "
              f"Messages: {state['messages']}")

        if state['tasks']['completed'] == state['tasks']['total']:
            print()
            print("✅ All research complete!")
            break

    # Stop swarm
    for task in swarm_tasks:
        task.cancel()
    await asyncio.gather(*swarm_tasks, return_exceptions=True)

    for agent in swarm:
        await agent.shutdown()

    print()
    print("🧩 Synthesizing collective intelligence...")

    # Synthesize
    synthesizer = KnowledgeSynthesizer("synthesizer", coord_server)
    await synthesizer.initialize()
    synthesis_files = await synthesizer.synthesize(coordinator)
    await synthesizer.shutdown()

    # Results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    final_state = await coordinator.get_workspace_state()

    result = {
        "pattern": "autonomous_swarm",
        "requirement": requirement,
        "swarm_size": num_agents,
        "duration_seconds": duration,
        "tasks_completed": final_state['tasks']['completed'],
        "knowledge_items": final_state['knowledge_items'],
        "messages": final_state['messages'],
        "synthesis_files": synthesis_files,
        "output_dir": str(output_dir)
    }

    # Save
    with open(output_dir / "swarm_results.json", 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 80)
    print("✅ SWARM PATTERN COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.2f}s")
    print(f"Tasks: {result['tasks_completed']}")
    print(f"Knowledge Shared: {result['knowledge_items']} items")
    print(f"Synthesis: {len(synthesis_files)} file(s)")
    print(f"Output: {output_dir}")
    print("=" * 80)

    return result


async def main():
    parser = argparse.ArgumentParser(description="Autonomous Swarm Pattern")
    parser.add_argument("--requirement", required=True, help="Research requirement")
    parser.add_argument("--agents", type=int, default=3, help="Number of swarm agents")
    parser.add_argument("--output", type=Path,
                       default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "swarm",
                       help="Output directory")

    args = parser.parse_args()

    if args.agents > 10:
        print("⚠️  Warning: Limiting swarm to 10 agents (you requested {args.agents})")
        args.agents = 10

    result = await run_swarm_pattern(args.requirement, args.agents, args.output)

    if result['tasks_completed'] > 0:
        print(f"\n✅ Success! Check {result['output_dir']} for results")
    else:
        print(f"\n❌ No tasks completed")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    asyncio.run(main())
