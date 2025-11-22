#!/usr/bin/env python3
"""
EXPERIMENT 2: Democratic Architecture Team

Tests the SDK's decision proposal and voting capabilities.

Hypothesis:
- Agents can propose different architectural solutions
- Team can discuss via messages
- Democratic voting produces consensus
- Voted decision is actually adopted

Setup:
- 1 ArchitectAgent (proposes option A)
- 1 BackendDeveloper (proposes option B)
- 1 FrontendDeveloper (proposes option C)
- 1 QAEngineer (proposes option D)
- All agents discuss and vote
- Final implementation follows majority

Metrics:
- Number of proposals
- Number of votes per decision
- Discussion quality (messages exchanged)
- Consensus achievement
- Implementation alignment with vote
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


class ProposingAgent(TeamAgent):
    """Agent that proposes solutions and participates in voting"""

    def __init__(self, agent_id: str, coordination_server, role: AgentRole, perspective: str):
        self.perspective = perspective

        config = AgentConfig(
            agent_id=agent_id,
            role=role,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, a {role.value} with expertise in {perspective}.

DECISION-MAKING WORKFLOW:
1. **Propose** your solution using propose_decision tool
   - Include detailed rationale from your {perspective} perspective
   - Explain trade-offs and benefits

2. **Discuss** via messages
   - Read others' proposals (check messages)
   - Post thoughtful questions and concerns
   - Engage in technical debate

3. **Vote** on all proposals (including your own)
   - Use vote_decision tool
   - Vote based on merit, not ego
   - Consider team's collective needs

4. **Implement** the winning decision
   - Check which decision won
   - Implement according to consensus

Be thoughtful, collaborative, and evidence-based in your decision making."""
        )
        super().__init__(config, coordination_server)

    async def propose_solution(self, problem: str):
        """Propose a solution from this agent's perspective"""
        await self._update_status(AgentStatus.WORKING, "Proposing solution")

        logger.info(f"[{self.agent_id}] 💡 Proposing solution for: {problem}")

        await self.client.query(
            f"""The team needs to decide on: {problem}

From your {self.perspective} perspective, propose a solution:

1. Analyze the problem from your expertise area
2. Develop a specific proposal
3. Use propose_decision tool with:
   - decision: Clear, specific proposal
   - rationale: Detailed explanation from {self.perspective} viewpoint
   - Include pros/cons, risks, benefits

4. Post a message to team explaining your proposal
5. Store your proposal details as knowledge for reference

Be specific and technical. Don't propose generic solutions."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Proposal submitted")

    async def discuss_proposals(self):
        """Engage in discussion about all proposals"""
        await self._update_status(AgentStatus.WORKING, "Discussing proposals")

        logger.info(f"[{self.agent_id}] 💬 Engaging in discussion...")

        await self.client.query(
            """Participate in team discussion:

1. Check messages to see all proposals
2. Analyze each proposal from your expertise perspective
3. Post thoughtful responses:
   - Ask clarifying questions
   - Raise concerns from your domain
   - Suggest improvements
   - Challenge assumptions (respectfully)

4. Engage in back-and-forth discussion
5. Use post_message to communicate

Focus on finding the best technical solution, not winning arguments."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Discussion participation complete")

    async def vote_on_proposals(self):
        """Vote on all proposals"""
        await self._update_status(AgentStatus.WORKING, "Voting")

        logger.info(f"[{self.agent_id}] 🗳️  Voting on proposals...")

        await self.client.query(
            """Cast your votes:

1. Review all messages and proposals
2. Evaluate each proposal based on:
   - Technical merit
   - Feasibility
   - Alignment with requirements
   - Risk level

3. Vote on EACH proposal using vote_decision:
   - "approve" if you support it
   - "reject" if you oppose it
   - "abstain" if uncertain

4. Post message explaining your voting rationale

Vote based on technical merit, not personal preference."""
        )

        async for msg in self.client.receive_response():
            pass

        await self._update_status(AgentStatus.IDLE, "Voting complete")

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


async def run_experiment():
    """Run democratic voting experiment"""

    print("=" * 80)
    print("🧪 EXPERIMENT 2: DEMOCRATIC ARCHITECTURE TEAM")
    print("=" * 80)
    print()
    print("Testing:")
    print("  ✓ Multiple proposal submission")
    print("  ✓ Team discussion via messages")
    print("  ✓ Democratic voting")
    print("  ✓ Consensus achievement")
    print()
    print("=" * 80)
    print()

    start_time = datetime.now()

    # Setup
    output_dir = Path("./experiments/voting_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    team_config = TeamConfig(
        team_id="voting_experiment",
        workspace_path=output_dir,
        max_agents=4
    )

    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    # The problem to decide on
    problem = "Choose authentication architecture for multi-tenant SaaS platform"

    print(f"🎯 Decision Problem: {problem}")
    print()
    print("👥 Creating decision-making team...")
    print()

    # Create team with different perspectives
    team = [
        ProposingAgent("architect", coord_server, AgentRole.ARCHITECT, "system architecture and scalability"),
        ProposingAgent("backend_dev", coord_server, AgentRole.DEVELOPER, "backend implementation and maintainability"),
        ProposingAgent("frontend_dev", coord_server, AgentRole.DEVELOPER, "frontend UX and integration"),
        ProposingAgent("qa_lead", coord_server, AgentRole.TESTER, "security and testing complexity"),
    ]

    for agent in team:
        await agent.initialize()
        print(f"  ✓ {agent.agent_id} initialized ({agent.perspective})")

    print()
    print("=" * 80)
    print("PHASE 1: PROPOSAL SUBMISSION")
    print("=" * 80)
    print()

    # Phase 1: Each agent proposes a solution
    print("Each agent proposing solution from their perspective...")
    print()

    proposal_tasks = [agent.propose_solution(problem) for agent in team]
    await asyncio.gather(*proposal_tasks)

    await asyncio.sleep(2)  # Let proposals settle

    state1 = await coordinator.get_workspace_state()
    print(f"  ✅ Proposals submitted: {state1['decisions']}")
    print(f"  Messages: {state1['messages']}")
    print()

    print("=" * 80)
    print("PHASE 2: TEAM DISCUSSION")
    print("=" * 80)
    print()

    # Phase 2: Discussion
    print("Agents discussing proposals...")
    print()

    discussion_tasks = [agent.discuss_proposals() for agent in team]
    await asyncio.gather(*discussion_tasks)

    await asyncio.sleep(2)

    state2 = await coordinator.get_workspace_state()
    print(f"  ✅ Discussion messages: {state2['messages']}")
    print()

    print("=" * 80)
    print("PHASE 3: VOTING")
    print("=" * 80)
    print()

    # Phase 3: Voting
    print("Agents casting votes...")
    print()

    voting_tasks = [agent.vote_on_proposals() for agent in team]
    await asyncio.gather(*voting_tasks)

    await asyncio.sleep(2)

    # Analyze results
    decisions = coordinator.shared_workspace["decisions"]

    print()
    print("=" * 80)
    print("VOTING RESULTS")
    print("=" * 80)
    print()

    for i, decision in enumerate(decisions, 1):
        print(f"Proposal {i}: {decision['decision']}")
        print(f"  Proposed by: {decision['proposed_by']}")
        print(f"  Rationale: {decision['rationale'][:100]}...")
        print(f"  Votes: {decision['votes']}")

        # Count votes
        approve = sum(1 for v in decision['votes'].values() if v == "approve")
        reject = sum(1 for v in decision['votes'].values() if v == "reject")
        abstain = sum(1 for v in decision['votes'].values() if v == "abstain")

        print(f"  Results: {approve} approve, {reject} reject, {abstain} abstain")

        if approve > reject:
            print(f"  ✅ APPROVED by majority")
        else:
            print(f"  ❌ REJECTED by majority")
        print()

    # Shutdown
    for agent in team:
        await agent.shutdown()

    # Final metrics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    final_state = await coordinator.get_workspace_state()

    results = {
        "experiment": "democratic_voting",
        "problem": problem,
        "duration_seconds": duration,
        "proposals_submitted": len(decisions),
        "votes_cast": sum(len(d['votes']) for d in decisions),
        "messages_exchanged": final_state['messages'],
        "decisions": decisions,
        "workspace_state": final_state
    }

    # Save results
    results_file = output_dir / "experiment_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Save messages log
    messages_file = output_dir / "team_discussion.json"
    with open(messages_file, 'w') as f:
        json.dump(coordinator.shared_workspace["messages"], f, indent=2, default=str)

    print("=" * 80)
    print("🎯 EXPERIMENT RESULTS")
    print("=" * 80)
    print(f"  Duration: {duration:.2f}s")
    print(f"  Proposals: {results['proposals_submitted']}")
    print(f"  Total Votes: {results['votes_cast']}")
    print(f"  Messages: {results['messages_exchanged']}")
    print()
    print(f"  Avg Votes/Proposal: {results['votes_cast'] / max(results['proposals_submitted'], 1):.2f}")
    print(f"  Discussion Intensity: {results['messages_exchanged'] / max(duration, 1):.2f} messages/sec")
    print()
    print(f"📁 Results saved to: {results_file}")
    print(f"📁 Discussion saved to: {messages_file}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    asyncio.run(run_experiment())
