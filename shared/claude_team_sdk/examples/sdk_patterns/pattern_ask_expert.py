#!/usr/bin/env python3
"""
SDK Pattern: Ask-the-Expert

Generalist agents handle common tasks, consult specialists for complex questions.
Demonstrates direct agent-to-agent messaging and expertise routing.

Usage:
    python examples/sdk_patterns/pattern_ask_expert.py \
        --requirement "Build secure REST API with payment processing" \
        --experts security performance database \
        --output ./output/expert

How it works:
1. Generalist agent analyzes requirement
2. Identifies areas needing specialist expertise
3. Asks specific questions to expert agents
4. Experts respond with detailed guidance
5. Generalist integrates expert advice into final solution

SDK Features Used:
- post_message (with to_agent for direct messaging)
- get_messages (checking for questions and answers)
- Expert consultation pattern
- Async Q&A coordination
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig
from src.claude_team_sdk.config import settings

logger = logging.getLogger(__name__)


EXPERT_DOMAINS = {
    "security": "security vulnerabilities, authentication, authorization, encryption, and secure coding",
    "performance": "performance optimization, caching, load balancing, and scalability",
    "database": "database design, indexing, query optimization, and data modeling",
    "api": "API design, REST principles, GraphQL, and API best practices",
    "testing": "testing strategies, test automation, coverage, and quality assurance"
}


class ExpertAgent(TeamAgent):
    """Specialist agent that answers domain-specific questions"""

    def __init__(self, agent_id: str, coordination_server, domain: str):
        self.domain = domain
        self.expertise = EXPERT_DOMAINS.get(domain, "general software engineering")

        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.REVIEWER,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, a {domain.upper()} EXPERT.

Your expertise: {self.expertise}

WORKFLOW:
1. Monitor messages for questions directed to you (use get_messages)
2. When you receive a question:
   - Analyze it from your expert perspective
   - Provide detailed, actionable advice
   - Include best practices and anti-patterns
   - Reference industry standards
3. Respond using post_message directed to the questioner
4. Share your expert guidance via share_knowledge for team reference

RESPONSE QUALITY:
- Be specific and technical
- Provide code examples if relevant
- Explain trade-offs
- Cite sources or standards
- Don't give generic advice

You are THE expert in {domain}. Provide deep, valuable insights."""
        )
        super().__init__(config, coordination_server)

    async def monitor_and_respond(self, duration_seconds: int = 60):
        """Monitor for questions and respond"""
        await self._update_status(AgentStatus.WORKING, "Monitoring for questions")

        logger.info(f"[{self.agent_id}] 👂 Monitoring for {self.domain} questions...")

        end_time = asyncio.get_event_loop().time() + duration_seconds

        while asyncio.get_event_loop().time() < end_time:
            await self.client.query(
                f"""Check for questions directed to you:

1. Use get_messages to check for new questions
2. Look for messages addressed to you
3. For each question:
   - Analyze from your {self.domain} expertise
   - Provide detailed expert response
   - Use post_message to respond to questioner
   - Use share_knowledge to document your guidance

If no questions, wait briefly then check again."""
            )

            async for msg in self.client.receive_response():
                pass

            await asyncio.sleep(5)  # Check every 5 seconds

        await self._update_status(AgentStatus.IDLE, "Monitoring complete")

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


class GeneralistAgent(TeamAgent):
    """Generalist agent that consults experts"""

    def __init__(self, agent_id: str, coordination_server, expert_domains: List[str]):
        self.expert_domains = expert_domains

        expert_list = ", ".join([f"{d}_expert" for d in expert_domains])

        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.DEVELOPER,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, a Generalist Developer.

You handle most tasks but consult experts for complex questions.

AVAILABLE EXPERTS:
{expert_list}

WORKFLOW:
1. Analyze the requirement
2. Identify areas needing expert input
3. For each expert area:
   - Formulate specific, detailed question
   - Use post_message to ask the expert directly
   - Wait for their response (use get_messages)
4. Integrate expert advice into solution
5. Create comprehensive implementation plan

ASKING EXPERTS:
- Ask specific, technical questions
- Provide context
- Use post_message with to_agent={expert}_expert
- Example: "security_expert", "performance_expert"

INTEGRATION:
- Synthesize all expert advice
- Create holistic solution
- Reference expert contributions
- Create final deliverable

You're competent in general development but know when to ask for help."""
        )
        super().__init__(config, coordination_server)

    async def solve_with_experts(self, requirement: str, coordinator: TeamCoordinator):
        """Solve requirement by consulting experts"""
        await self._update_status(AgentStatus.WORKING, "Consulting experts")

        logger.info(f"[{self.agent_id}] 🤔 Analyzing requirement and consulting experts...")

        expert_list = ", ".join([f"{d}_expert" for d in self.expert_domains])

        await self.client.query(
            f"""Solve this requirement with expert help:

REQUIREMENT: {requirement}

AVAILABLE EXPERTS: {expert_list}

PROCESS:
1. Analyze the requirement
2. Identify specific questions for each expert
3. Ask each expert using post_message:
   - Use to_agent parameter: "security_expert", "performance_expert", etc.
   - Ask specific, detailed questions
4. Wait and check for responses (use get_messages)
5. Integrate all expert advice
6. Create comprehensive solution

CREATE FILES:
- SOLUTION_DESIGN.md: Your solution integrating expert advice
- EXPERT_CONSULTATIONS.md: Summary of expert Q&A
- IMPLEMENTATION_PLAN.md: Actionable steps

Use Write tool for files. Reference expert contributions."""
        )

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)
                        logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

        await self._update_status(AgentStatus.IDLE, "Solution complete")
        return files_created

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


async def run_expert_pattern(requirement: str, expert_domains: List[str], output_dir: Path):
    """Execute ask-the-expert pattern"""

    print("=" * 80)
    print("🎓 ASK-THE-EXPERT PATTERN")
    print("=" * 80)
    print(f"Requirement: {requirement}")
    print(f"Experts Available: {', '.join(expert_domains)}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    print()

    start_time = datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create coordinator
    team_config = TeamConfig(
        team_id=f"expert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        workspace_path=output_dir,
        max_agents=len(expert_domains) + 1
    )
    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    print(f"🎓 Creating expert panel ({len(expert_domains)} experts)...")

    # Create experts
    experts = []
    for domain in expert_domains:
        expert = ExpertAgent(f"{domain}_expert", coord_server, domain)
        await expert.initialize()
        experts.append(expert)
        print(f"  ✓ {expert.agent_id} ({domain} specialist)")

    print()
    print("👨‍💻 Creating generalist agent...")

    # Create generalist
    generalist = GeneralistAgent("generalist", coord_server, expert_domains)
    await generalist.initialize()
    print(f"  ✓ {generalist.agent_id}")

    print()
    print("=" * 60)
    print("CONSULTATION PHASE")
    print("=" * 60)

    # Start experts monitoring
    print("Experts monitoring for questions...")
    expert_tasks = [
        asyncio.create_task(expert.monitor_and_respond(60))
        for expert in experts
    ]

    # Generalist consults experts
    print("Generalist consulting experts...")
    files = await generalist.solve_with_experts(requirement, coordinator)

    # Wait for expert responses
    await asyncio.sleep(10)  # Give experts time to respond

    # Stop experts
    for task in expert_tasks:
        task.cancel()
    await asyncio.gather(*expert_tasks, return_exceptions=True)

    # Shutdown
    for expert in experts:
        await expert.shutdown()
    await generalist.shutdown()

    # Results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    final_state = await coordinator.get_workspace_state()

    result = {
        "pattern": "ask_the_expert",
        "requirement": requirement,
        "experts": expert_domains,
        "duration_seconds": duration,
        "files_created": files,
        "messages_exchanged": final_state['messages'],
        "knowledge_shared": final_state['knowledge_items'],
        "output_dir": str(output_dir)
    }

    with open(output_dir / "expert_results.json", 'w') as f:
        json.dump(result, f, indent=2, default=str)

    # Save conversation
    messages = coordinator.shared_workspace["messages"]
    with open(output_dir / "expert_conversations.json", 'w') as f:
        json.dump(messages, f, indent=2, default=str)

    print()
    print("=" * 80)
    print("✅ ASK-THE-EXPERT PATTERN COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.2f}s")
    print(f"Experts Consulted: {len(expert_domains)}")
    print(f"Messages: {result['messages_exchanged']}")
    print(f"Files Created: {len(files)}")
    print(f"Output: {output_dir}")
    print("=" * 80)

    return result


async def main():
    parser = argparse.ArgumentParser(description="Ask-the-Expert Pattern")
    parser.add_argument("--requirement", required=True, help="Problem to solve")
    parser.add_argument("--experts", nargs="+",
                       choices=list(EXPERT_DOMAINS.keys()),
                       default=["security", "performance"],
                       help="Expert domains to consult")
    parser.add_argument("--output", type=Path,
                       default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "expert",
                       help="Output directory")

    args = parser.parse_args()

    result = await run_expert_pattern(args.requirement, args.experts, args.output)

    if len(result['files_created']) > 0:
        print(f"\n✅ Success! Check {result['output_dir']} for solution")
    else:
        print(f"\n❌ No files created")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    asyncio.run(main())
