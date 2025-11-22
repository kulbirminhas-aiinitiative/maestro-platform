#!/usr/bin/env python3
"""
EXPERIMENT 1: Autonomous Swarm Research Team

Tests the SDK's autonomous task claiming and knowledge sharing capabilities.

Hypothesis:
- Multiple similar agents can self-organize around a task queue
- Agents share discoveries via knowledge base
- Final synthesis benefits from all findings

Setup:
- 5 ResearchAgent instances (all same role)
- 5 research tasks added to queue
- NO orchestration - agents autonomously claim
- Knowledge sharing enabled
- Final synthesizer compiles all knowledge

Metrics:
- Task completion time
- Knowledge items shared
- Quality of final synthesis
- Agent utilization (how many actually worked)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig

logger = logging.getLogger(__name__)


class SwarmResearchAgent(TeamAgent):
    """Research agent that autonomously claims tasks and shares findings"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.RESEARCHER,
            auto_claim_tasks=True,  # KEY: Autonomous claiming
            system_prompt=f"""You are {agent_id}, a Research Agent in a swarm intelligence team.

AUTONOMOUS BEHAVIOR:
- Continuously check for unclaimed research tasks
- Claim tasks matching your role
- Conduct thorough research
- **CRITICAL**: Share ALL findings via share_knowledge tool
- Check what others have discovered via get_knowledge
- Build upon team's collective knowledge

RESEARCH WORKFLOW:
1. Claim a research task from the queue
2. Conduct research on the topic
3. Share key findings: use share_knowledge with descriptive keys
4. Check team knowledge: use get_knowledge to see others' findings
5. Complete the task with summary
6. Repeat until no tasks remain

KNOWLEDGE SHARING:
- Share specific insights (not generic summaries)
- Use descriptive keys: "auth_security_best_practices", "jwt_vulnerabilities", etc.
- Include actionable recommendations
- Reference what others have found

You work independently but benefit from the swarm's collective intelligence."""
        )
        super().__init__(config, coordination_server)

    async def execute_task(self, task_description: str):
        """Execute research task with knowledge sharing"""
        await self._update_status(AgentStatus.WORKING, task_description)

        logger.info(f"[{self.agent_id}] 🔬 Researching: {task_description}")

        # The actual research happens in the auto_claim loop
        # This gets called by the TeamAgent's _auto_task_loop
        return {"success": True, "agent_id": self.agent_id}

    async def execute_role_specific_work(self):
        """This is called when auto_claim_tasks=True"""
        # Let the base class handle autonomous task claiming
        await self._auto_task_loop()


class SynthesizerAgent(TeamAgent):
    """Synthesizes all knowledge from swarm into final report"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            auto_claim_tasks=False,  # Manual control
            system_prompt=f"""You are {agent_id}, the Knowledge Synthesizer.

YOUR TASK:
- Wait for swarm to complete all research tasks
- Retrieve ALL knowledge shared by the team
- Synthesize into comprehensive final report
- Create actionable recommendations

SYNTHESIS WORKFLOW:
1. Check team messages to see what was researched
2. Use get_knowledge to retrieve ALL findings
3. Analyze patterns across all discoveries
4. Create synthesis report combining all insights
5. Share final synthesis via share_knowledge("final_synthesis", ...)

Focus on integrating diverse findings into coherent whole."""
        )
        super().__init__(config, coordination_server)

    async def synthesize_knowledge(self, output_dir: Path):
        """Synthesize all team knowledge"""
        await self._update_status(AgentStatus.WORKING, "Synthesizing team knowledge")

        logger.info(f"[{self.agent_id}] 🧩 Synthesizing all team knowledge...")

        await self.client.query(
            """Synthesize all research completed by the swarm:

1. Check messages (use get_messages) to see what topics were researched
2. Retrieve knowledge items (use get_knowledge for each topic)
3. Create comprehensive synthesis report:

**File**: synthesis_report.md

Include:
- Executive Summary: Key themes across all research
- Integrated Findings: Synthesize all discoveries
- Patterns Identified: Common themes
- Contradictions: Where findings differ
- Final Recommendations: Actionable next steps

4. Share synthesis via share_knowledge("final_synthesis", summary)
5. Post message that synthesis is complete

Use Write tool to create the synthesis_report.md file."""
        )

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)

        await self._update_status(AgentStatus.IDLE, "Synthesis complete")
        logger.info(f"[{self.agent_id}] ✅ Synthesis complete")

        return files_created

    async def execute_task(self, task_description: str):
        return await self.synthesize_knowledge(Path("."))

    async def execute_role_specific_work(self):
        pass


async def run_experiment():
    """Run autonomous swarm experiment"""

    print("=" * 80)
    print("🧪 EXPERIMENT 1: AUTONOMOUS SWARM RESEARCH TEAM")
    print("=" * 80)
    print()
    print("Testing:")
    print("  ✓ Autonomous task claiming")
    print("  ✓ Knowledge sharing across swarm")
    print("  ✓ Parallel execution")
    print("  ✓ Knowledge synthesis")
    print()
    print("=" * 80)
    print()

    start_time = datetime.now()

    # Setup
    output_dir = Path("./experiments/swarm_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    team_config = TeamConfig(
        team_id="swarm_experiment",
        workspace_path=output_dir,
        max_agents=6  # 5 researchers + 1 synthesizer
    )

    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    print("📋 Adding research tasks to queue...")

    # Add research tasks
    research_topics = [
        "JWT authentication security best practices",
        "OAuth 2.0 vs OpenID Connect comparison",
        "API rate limiting strategies",
        "Database connection pooling patterns",
        "Microservices communication patterns"
    ]

    for topic in research_topics:
        task_id = await coordinator.add_task(
            description=f"Research: {topic}",
            required_role="researcher"
        )
        print(f"  ✓ Added task: {task_id} - {topic[:50]}...")

    print()
    print(f"👥 Spawning {len(research_topics)} autonomous research agents...")
    print()

    # Create swarm of research agents
    swarm = []
    for i in range(len(research_topics)):
        agent = SwarmResearchAgent(f"researcher_{i+1}", coord_server)
        await agent.initialize()
        swarm.append(agent)
        print(f"  ✓ {agent.agent_id} initialized and ready")

    print()
    print("🚀 Releasing swarm (autonomous operation)...")
    print("   Agents will self-organize and claim tasks")
    print()

    # Start all agents autonomously
    agent_tasks = [
        asyncio.create_task(agent.run())
        for agent in swarm
    ]

    # Monitor progress
    print("📊 Monitoring swarm activity...")
    print()

    # Wait for all tasks to complete
    while True:
        await asyncio.sleep(5)  # Check every 5 seconds

        state = await coordinator.get_workspace_state()

        print(f"  Status: {state['tasks']['completed']}/{state['tasks']['total']} tasks complete")
        print(f"  Knowledge items: {state['knowledge_items']}")
        print(f"  Messages: {state['messages']}")

        if state['tasks']['completed'] == state['tasks']['total']:
            print()
            print("✅ All research tasks completed!")
            break

    # Cancel agent tasks
    for task in agent_tasks:
        task.cancel()

    await asyncio.gather(*agent_tasks, return_exceptions=True)

    # Shutdown research agents
    for agent in swarm:
        await agent.shutdown()

    print()
    print("🧩 Starting knowledge synthesis...")
    print()

    # Create synthesizer
    synthesizer = SynthesizerAgent("synthesizer", coord_server)
    await synthesizer.initialize()

    # Synthesize all knowledge
    synthesis_files = await synthesizer.synthesize_knowledge(output_dir)

    await synthesizer.shutdown()

    # Final metrics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    final_state = await coordinator.get_workspace_state()

    results = {
        "experiment": "autonomous_swarm",
        "duration_seconds": duration,
        "tasks_completed": final_state['tasks']['completed'],
        "knowledge_items_shared": final_state['knowledge_items'],
        "messages_exchanged": final_state['messages'],
        "artifacts_created": final_state['artifacts'],
        "synthesis_files": synthesis_files,
        "workspace_state": final_state
    }

    # Save results
    results_file = output_dir / "experiment_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print()
    print("=" * 80)
    print("🎯 EXPERIMENT RESULTS")
    print("=" * 80)
    print(f"  Duration: {duration:.2f}s")
    print(f"  Tasks Completed: {results['tasks_completed']}")
    print(f"  Knowledge Shared: {results['knowledge_items_shared']} items")
    print(f"  Messages: {results['messages_exchanged']}")
    print(f"  Synthesis Files: {len(synthesis_files)}")
    print()
    print(f"  Throughput: {results['tasks_completed'] / duration:.2f} tasks/second")
    print(f"  Avg Knowledge/Task: {results['knowledge_items_shared'] / max(results['tasks_completed'], 1):.2f}")
    print()
    print(f"📁 Results saved to: {results_file}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    asyncio.run(run_experiment())
