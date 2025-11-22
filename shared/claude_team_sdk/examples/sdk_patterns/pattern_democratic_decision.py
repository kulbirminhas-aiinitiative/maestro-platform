#!/usr/bin/env python3
"""
SDK Pattern: Democratic Decision Making

Team proposes multiple solutions, discusses, votes democratically,
and implements consensus decision.

Usage:
    python examples/sdk_patterns/pattern_democratic_decision.py \
        --requirement "Choose database for high-traffic API" \
        --roles architect backend frontend qa \
        --output ./output/decision

How it works:
1. Each team member proposes a solution from their perspective
2. Team discusses proposals via messages
3. All members vote on all proposals
4. Winning proposal is implemented
5. Creates decision record and implementation plan

SDK Features Used:
- propose_decision (democratic proposals)
- vote_decision (voting mechanism)
- post_message / get_messages (discussion)
- Consensus building
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig
from src.claude_team_sdk.config import settings

logger = logging.getLogger(__name__)


ROLE_PERSPECTIVES = {
    "architect": "system architecture, scalability, and long-term maintainability",
    "backend": "implementation complexity, performance, and backend integration",
    "frontend": "developer experience, API usability, and frontend integration",
    "qa": "testing complexity, reliability, and quality assurance",
    "security": "security implications, vulnerabilities, and risk mitigation",
    "devops": "deployment, operations, and infrastructure management"
}


class DecisionMaker(TeamAgent):
    """Agent that proposes, discusses, and votes on decisions"""

    def __init__(self, agent_id: str, coordination_server, role: str):
        self.perspective = ROLE_PERSPECTIVES.get(role, "general engineering")

        # Map role string to AgentRole enum
        role_map = {
            "architect": AgentRole.ARCHITECT,
            "backend": AgentRole.DEVELOPER,
            "frontend": AgentRole.DEVELOPER,
            "qa": AgentRole.TESTER,
            "security": AgentRole.REVIEWER,
            "devops": AgentRole.DEPLOYER
        }

        config = AgentConfig(
            agent_id=agent_id,
            role=role_map.get(role, AgentRole.DEVELOPER),
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, a {role} expert focused on {self.perspective}.

DEMOCRATIC DECISION PROCESS:

PHASE 1 - PROPOSE:
1. Analyze requirement from your expertise perspective
2. Develop a specific, detailed proposal
3. Use propose_decision tool with:
   - decision: Clear, actionable proposal
   - rationale: Detailed explanation from {self.perspective} viewpoint
4. Post message explaining your proposal to team

PHASE 2 - DISCUSS:
1. Read all proposals (check messages)
2. Analyze each from your expertise perspective
3. Post thoughtful questions and concerns
4. Engage in technical debate
5. Challenge assumptions respectfully
6. Build on others' ideas

PHASE 3 - VOTE:
1. Review all proposals and discussion
2. Evaluate based on technical merit, not ego
3. Vote on EACH proposal using vote_decision:
   - "approve" if technically sound
   - "reject" if concerns outweigh benefits
   - "abstain" if insufficient expertise
4. Post message explaining your votes

Be specific, technical, and focused on best solution for the team."""
        )
        super().__init__(config, coordination_server)
        self.role_name = role

    async def propose_solution(self, requirement: str):
        """Propose solution from this agent's perspective"""
        await self._update_status(AgentStatus.WORKING, "Proposing solution")

        logger.info(f"[{self.agent_id}] 💡 Proposing solution ({self.role_name})...")

        await self.client.query(
            f"""The team must decide: {requirement}

From your {self.perspective} perspective:

1. Analyze the requirement deeply
2. Develop a specific, detailed proposal
3. Use propose_decision tool:
   - decision: Your specific recommendation
   - rationale: Why this is best from {self.perspective} viewpoint
4. Use post_message to explain proposal to team
5. Use share_knowledge to document your analysis

Be specific with technical details, not generic."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Proposal submitted")
        logger.info(f"[{self.agent_id}] ✅ Proposal submitted")

    async def participate_discussion(self):
        """Engage in team discussion"""
        await self._update_status(AgentStatus.WORKING, "Discussing")

        logger.info(f"[{self.agent_id}] 💬 Participating in discussion...")

        await self.client.query(
            f"""Participate in team discussion:

1. Use get_messages to read all proposals
2. Analyze each from your {self.perspective} perspective
3. Use post_message to:
   - Ask clarifying questions
   - Raise concerns from your domain
   - Challenge weak assumptions
   - Suggest improvements
4. Engage in back-and-forth dialogue

Focus on finding the best technical solution through collaborative debate."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Discussion complete")

    async def cast_votes(self, coordinator: TeamCoordinator):
        """Vote on all proposals"""
        await self._update_status(AgentStatus.WORKING, "Voting")

        logger.info(f"[{self.agent_id}] 🗳️  Casting votes...")

        decisions = coordinator.shared_workspace["decisions"]
        decision_info = "\n".join([
            f"- {d['id']}: {d['decision']} (by {d['proposed_by']})"
            for d in decisions
        ])

        await self.client.query(
            f"""Cast your votes on all proposals:

PROPOSALS TO VOTE ON:
{decision_info}

VOTING PROCESS:
1. Review all proposals and discussion (use get_messages)
2. Evaluate each based on:
   - Technical merit
   - Feasibility
   - Alignment with requirement
   - Risks and benefits
3. For EACH proposal, use vote_decision:
   - "approve" if you support it
   - "reject" if concerns outweigh benefits
   - "abstain" if uncertain/insufficient expertise
4. Use post_message to explain your voting rationale

Vote based on what's best for the project, not personal preference."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Voting complete")
        logger.info(f"[{self.agent_id}] ✅ Votes cast")

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


class DecisionImplementer(TeamAgent):
    """Implements the winning decision"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.DEVELOPER,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, the Decision Implementer.

Your job: Implement the team's democratically chosen decision.

IMPLEMENTATION WORKFLOW:
1. Identify winning proposal (most approvals)
2. Review all discussion and votes
3. Create implementation plan based on consensus
4. Document the decision and rationale
5. Create actionable next steps

OUTPUT FILES:
- DECISION_RECORD.md: What was decided and why
- IMPLEMENTATION_PLAN.md: How to implement the decision
- VOTING_SUMMARY.md: Full voting breakdown

Reference all team input and document consensus."""
        )
        super().__init__(config, coordination_server)

    async def implement_decision(self, coordinator: TeamCoordinator):
        """Create decision record and implementation plan"""
        await self._update_status(AgentStatus.WORKING, "Implementing")

        logger.info(f"[{self.agent_id}] 📋 Creating decision record...")

        decisions = coordinator.shared_workspace["decisions"]

        # Determine winner
        winner = None
        max_approvals = -1

        for decision in decisions:
            approvals = sum(1 for v in decision['votes'].values() if v == "approve")
            if approvals > max_approvals:
                max_approvals = approvals
                winner = decision

        decision_context = json.dumps(decisions, indent=2, default=str)
        messages = coordinator.shared_workspace["messages"]
        messages_context = "\n".join([
            f"[{m['from']}]: {m['message'][:100]}..."
            for m in messages[-20:]  # Last 20 messages
        ])

        await self.client.query(
            f"""Implement the team's democratic decision:

VOTING RESULTS:
{decision_context}

RECENT DISCUSSION:
{messages_context}

WINNING DECISION:
{json.dumps(winner, indent=2, default=str) if winner else "No clear winner"}

CREATE THREE FILES:

1. **DECISION_RECORD.md**:
   - Decision made
   - Winning proposal details
   - Voting breakdown (who voted what)
   - Key discussion points
   - Rationale for consensus

2. **IMPLEMENTATION_PLAN.md**:
   - Actionable steps to implement decision
   - Timeline and milestones
   - Responsibilities
   - Success criteria
   - Risk mitigation

3. **VOTING_SUMMARY.md**:
   - All proposals submitted
   - Vote tallies for each
   - Participation rate
   - Consensus strength

Use Write tool to create these files."""
        )

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)
                        logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

        await self._update_status(AgentStatus.IDLE, "Implementation complete")
        return files_created, winner

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


async def run_democratic_pattern(requirement: str, roles: List[str], output_dir: Path):
    """Execute democratic decision pattern"""

    print("=" * 80)
    print("🗳️  DEMOCRATIC DECISION MAKING PATTERN")
    print("=" * 80)
    print(f"Decision: {requirement}")
    print(f"Team Roles: {', '.join(roles)}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    print()

    start_time = datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create coordinator
    team_config = TeamConfig(
        team_id=f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        workspace_path=output_dir,
        max_agents=len(roles) + 1
    )
    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    print(f"👥 Creating decision-making team ({len(roles)} members)...")

    # Create team
    team = []
    for role in roles:
        agent = DecisionMaker(f"{role}_lead", coord_server, role)
        await agent.initialize()
        team.append(agent)
        print(f"  ✓ {agent.agent_id} ({role})")

    print()
    print("=" * 60)
    print("PHASE 1: PROPOSAL SUBMISSION")
    print("=" * 60)

    # Phase 1: Proposals
    print("Each member proposing solution from their perspective...")
    await asyncio.gather(*[agent.propose_solution(requirement) for agent in team])

    state = await coordinator.get_workspace_state()
    print(f"  ✅ {state['decisions']} proposals submitted")
    print()

    print("=" * 60)
    print("PHASE 2: TEAM DISCUSSION")
    print("=" * 60)

    # Phase 2: Discussion
    print("Team members discussing proposals...")
    await asyncio.gather(*[agent.participate_discussion() for agent in team])

    state = await coordinator.get_workspace_state()
    print(f"  ✅ {state['messages']} messages exchanged")
    print()

    print("=" * 60)
    print("PHASE 3: VOTING")
    print("=" * 60)

    # Phase 3: Voting
    print("Team members casting votes...")
    await asyncio.gather(*[agent.cast_votes(coordinator) for agent in team])

    decisions = coordinator.shared_workspace["decisions"]
    total_votes = sum(len(d['votes']) for d in decisions)
    print(f"  ✅ {total_votes} votes cast across {len(decisions)} proposals")
    print()

    # Shutdown team
    for agent in team:
        await agent.shutdown()

    print("=" * 60)
    print("PHASE 4: IMPLEMENTATION")
    print("=" * 60)

    # Phase 4: Implementation
    print("Creating decision record and implementation plan...")
    implementer = DecisionImplementer("implementer", coord_server)
    await implementer.initialize()
    impl_files, winner = await implementer.implement_decision(coordinator)
    await implementer.shutdown()

    # Results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    result = {
        "pattern": "democratic_decision",
        "requirement": requirement,
        "team_roles": roles,
        "duration_seconds": duration,
        "proposals": len(decisions),
        "votes_cast": total_votes,
        "messages": state['messages'],
        "winning_decision": winner['decision'] if winner else None,
        "implementation_files": impl_files,
        "output_dir": str(output_dir)
    }

    with open(output_dir / "decision_results.json", 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 80)
    print("✅ DEMOCRATIC DECISION COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.2f}s")
    print(f"Proposals: {result['proposals']}")
    print(f"Votes Cast: {result['votes_cast']}")
    print(f"Winning Decision: {result['winning_decision']}")
    print(f"Output: {output_dir}")
    print("=" * 80)

    return result


async def main():
    parser = argparse.ArgumentParser(description="Democratic Decision Pattern")
    parser.add_argument("--requirement", required=True, help="Decision to make")
    parser.add_argument("--roles", nargs="+",
                       choices=list(ROLE_PERSPECTIVES.keys()),
                       default=["architect", "backend", "qa"],
                       help="Team member roles")
    parser.add_argument("--output", type=Path,
                       default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "decision",
                       help="Output directory")

    args = parser.parse_args()

    result = await run_democratic_pattern(args.requirement, args.roles, args.output)

    if result['proposals'] > 0:
        print(f"\n✅ Success! Check {result['output_dir']} for decision record")
    else:
        print(f"\n❌ No proposals submitted")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    asyncio.run(main())
