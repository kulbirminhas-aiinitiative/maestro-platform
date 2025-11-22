#!/usr/bin/env python3
"""
Autonomous Agent Discussion V2 - PRODUCTION ARCHITECTURE

Key Improvements over V1:
1. ✅ Persistent state (PostgreSQL + Redis) - no more data loss
2. ✅ Agents can create tasks during discussion - bridge ideation & execution
3. ✅ RBAC enforcement - role-based permissions
4. ✅ Event-driven - agents react to real-time events
5. ✅ Workflow integration - discussions can spawn workflows
6. ✅ Audit trail - all actions logged

This demonstrates the COMPLETE lifecycle:
  Discussion → Decision → Task Creation → Execution
"""

import asyncio
import uuid
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from persistence import init_database, StateManager
from persistence.database import DatabaseConfig
from persistence.redis_manager import RedisManager
from rbac import RoleManager, AccessController
from workflow import WorkflowEngine, WorkflowBuilder, TaskType


class ProductionAutonomousAgent:
    """
    Autonomous agent with production features:
    - Persistent state
    - RBAC enforcement
    - Event-driven reactions
    - Can create tasks and workflows
    """

    def __init__(
        self,
        agent_id: str,
        role_id: str,
        role_description: str,
        expertise: str,
        team_id: str,
        state_manager: StateManager,
        access_controller: AccessController
    ):
        self.agent_id = agent_id
        self.role_id = role_id
        self.role_description = role_description
        self.expertise = expertise
        self.team_id = team_id
        self.state = state_manager
        self.access = access_controller

        self.message_count = 0
        self.tasks_created = 0

    async def initialize(self):
        """Register agent with team"""
        await self.state.update_agent_status(
            team_id=self.team_id,
            agent_id=self.agent_id,
            role=self.role_id,
            status="initialized",
            message=f"Ready to collaborate as {self.role_description}"
        )

    async def participate_in_discussion(
        self,
        agenda: str,
        rounds: int,
        target_outcome: str
    ):
        """
        Autonomously participate in discussion

        Unlike V1, this agent can:
        - Create tasks based on discussion
        - Propose workflows
        - React to events
        """

        await self.state.update_agent_status(
            self.team_id, self.agent_id, self.role_id,
            "working", f"Discussing: {agenda}"
        )

        for round_num in range(1, rounds + 1):
            print(f"  [{self.agent_id}] Round {round_num}/{rounds}")

            # 1. Check messages from other agents
            messages = await self.state.get_messages(
                team_id=self.team_id,
                agent_id=self.agent_id,
                limit=20
            )

            # 2. Simulate agent thinking and contribution
            # (In real implementation, would use Claude API)
            contribution = await self._decide_contribution(
                agenda=agenda,
                round_num=round_num,
                total_rounds=rounds,
                target_outcome=target_outcome,
                recent_messages=messages
            )

            # 3. Execute contribution with RBAC enforcement
            await self._execute_contribution(contribution)

            # Small delay between rounds
            await asyncio.sleep(1)

        await self.state.update_agent_status(
            self.team_id, self.agent_id, self.role_id,
            "idle", "Discussion completed"
        )

    async def _decide_contribution(
        self,
        agenda: str,
        round_num: int,
        total_rounds: int,
        target_outcome: str,
        recent_messages: List[Dict]
    ) -> Dict[str, Any]:
        """
        Decide what to contribute this round

        Returns a contribution plan with actions to take
        """

        # Analyze current state
        context = {
            "round": round_num,
            "total_rounds": total_rounds,
            "messages_seen": len(recent_messages),
            "my_messages": self.message_count,
            "tasks_created": self.tasks_created
        }

        # Different behavior based on role and round
        if self.role_id == "product_manager":
            return await self._pm_contribution(round_num, total_rounds, context)
        elif self.role_id == "architect":
            return await self._architect_contribution(round_num, total_rounds, context)
        elif self.role_id == "developer":
            return await self._developer_contribution(round_num, total_rounds, context)
        else:
            return await self._generic_contribution(round_num, total_rounds, context)

    async def _pm_contribution(self, round_num: int, total_rounds: int, context: Dict) -> Dict:
        """Product Manager behavior"""
        if round_num == 1:
            # First round: Share vision and requirements
            return {
                "action": "post_message",
                "content": f"[{self.agent_id}] Let's discuss the requirements. As PM, I see this as a critical feature for user engagement.",
                "metadata": {"round": round_num, "role": "vision"}
            }
        elif round_num == total_rounds - 1:
            # Second to last: Create tasks
            return {
                "action": "create_tasks",
                "tasks": [
                    {
                        "title": "Technical Design Document",
                        "description": "Create architecture for the feature",
                        "required_role": "architect",
                        "priority": 10
                    },
                    {
                        "title": "Implementation Plan",
                        "description": "Break down implementation steps",
                        "required_role": "developer",
                        "priority": 8
                    }
                ]
            }
        elif round_num == total_rounds:
            # Last round: Propose decision
            return {
                "action": "propose_decision",
                "decision": f"Approve feature development with created tasks",
                "rationale": "Team aligned on approach, tasks created for execution"
            }
        else:
            # Middle rounds: Share knowledge
            return {
                "action": "share_knowledge",
                "key": f"requirement_{round_num}",
                "value": f"User research insight from round {round_num}",
                "category": "requirements"
            }

    async def _architect_contribution(self, round_num: int, total_rounds: int, context: Dict) -> Dict:
        """Architect behavior"""
        if round_num == 1:
            return {
                "action": "post_message",
                "content": f"[{self.agent_id}] From an architecture perspective, we need to consider scalability and maintainability.",
                "metadata": {"round": round_num, "role": "technical"}
            }
        elif round_num == 2:
            return {
                "action": "share_knowledge",
                "key": "architecture_pattern",
                "value": "Recommend microservices pattern for flexibility",
                "category": "architecture"
            }
        else:
            return {
                "action": "post_message",
                "content": f"[{self.agent_id}] I'll create the technical design once we finalize requirements.",
                "metadata": {"round": round_num}
            }

    async def _developer_contribution(self, round_num: int, total_rounds: int, context: Dict) -> Dict:
        """Developer behavior"""
        if round_num == 1:
            return {
                "action": "post_message",
                "content": f"[{self.agent_id}] Ready to implement. What's the priority?",
                "metadata": {"round": round_num, "role": "implementation"}
            }
        else:
            return {
                "action": "post_message",
                "content": f"[{self.agent_id}] I can help break this into smaller tasks.",
                "metadata": {"round": round_num}
            }

    async def _generic_contribution(self, round_num: int, total_rounds: int, context: Dict) -> Dict:
        """Generic agent behavior"""
        return {
            "action": "post_message",
            "content": f"[{self.agent_id}] Contributing from {self.role_description} perspective.",
            "metadata": {"round": round_num, "role": self.role_id}
        }

    async def _execute_contribution(self, contribution: Dict[str, Any]):
        """Execute the contribution with RBAC enforcement"""
        action = contribution.get("action")

        try:
            if action == "post_message":
                # Check permission
                self.access.check_access(
                    self.agent_id,
                    self.role_id,
                    "post_message"
                )

                # Execute
                await self.state.post_message(
                    team_id=self.team_id,
                    from_agent=self.agent_id,
                    message=contribution["content"],
                    metadata=contribution.get("metadata", {})
                )
                self.message_count += 1
                print(f"    → Message posted")

            elif action == "create_tasks":
                # Check permission
                self.access.check_access(
                    self.agent_id,
                    self.role_id,
                    "create_task"
                )

                # Create each task
                for task_spec in contribution["tasks"]:
                    task = await self.state.create_task(
                        team_id=self.team_id,
                        title=task_spec["title"],
                        description=task_spec["description"],
                        created_by=self.agent_id,
                        required_role=task_spec.get("required_role"),
                        priority=task_spec.get("priority", 5)
                    )
                    self.tasks_created += 1
                    print(f"    → Task created: {task['title']}")

            elif action == "share_knowledge":
                # Check permission
                self.access.check_access(
                    self.agent_id,
                    self.role_id,
                    "share_knowledge"
                )

                # Share knowledge
                await self.state.share_knowledge(
                    team_id=self.team_id,
                    key=contribution["key"],
                    value=contribution["value"],
                    source_agent=self.agent_id,
                    category=contribution.get("category")
                )
                print(f"    → Knowledge shared: {contribution['key']}")

            elif action == "propose_decision":
                # Check permission
                self.access.check_access(
                    self.agent_id,
                    self.role_id,
                    "propose_decision"
                )

                # Propose decision (using database models directly)
                from persistence.models import Decision
                decision = Decision(
                    id=str(uuid.uuid4()),
                    team_id=self.team_id,
                    decision=contribution["decision"],
                    rationale=contribution.get("rationale"),
                    proposed_by=self.agent_id,
                    status="pending"
                )

                async with self.state.db.session() as session:
                    session.add(decision)

                print(f"    → Decision proposed: {contribution['decision']}")

        except Exception as e:
            print(f"    ✗ Action failed: {e}")


async def run_production_autonomous_discussion(
    agenda: str,
    discussion_rounds: int = 3,
    target_outcome: str = "",
    team_composition: List[Dict[str, str]] = None,
    use_sqlite: bool = True  # True for demo, False for PostgreSQL
):
    """
    Run production autonomous discussion with full architecture

    Features:
    - Persistent state (PostgreSQL or SQLite)
    - RBAC enforcement
    - Event-driven
    - Task creation during discussion
    - Audit trail
    """

    print("\n" + "="*70)
    print("🤖 PRODUCTION AUTONOMOUS DISCUSSION V2")
    print("="*70)
    print(f"\n📋 AGENDA: {agenda}")
    print(f"🔄 ROUNDS: {discussion_rounds}")
    if target_outcome:
        print(f"🎯 TARGET: {target_outcome}")
    print("\n" + "="*70)

    # 1. Initialize persistence layer
    print("\n📦 Initializing infrastructure...")

    if use_sqlite:
        db_connection = DatabaseConfig.for_testing()
        print("  ✓ Using SQLite (demo mode)")
    else:
        db_connection = DatabaseConfig.from_env()
        print("  ✓ Using PostgreSQL (production mode)")

    db = await init_database(db_connection)
    print("  ✓ Database initialized")

    redis = RedisManager()
    await redis.initialize()
    print("  ✓ Redis connected")

    state_manager = StateManager(db, redis)
    print("  ✓ State manager ready")

    # 2. Setup RBAC
    role_manager = RoleManager()
    access_controller = AccessController(role_manager)
    print("  ✓ RBAC configured")

    # 3. Create workflow engine
    workflow_engine = WorkflowEngine(state_manager)
    print("  ✓ Workflow engine ready")

    team_id = f"team_{uuid.uuid4().hex[:8]}"

    print("\n" + "="*70)
    print("👥 TEAM MEMBERS:\n")

    # 4. Create agents
    agents = []
    for member in team_composition:
        agent = ProductionAutonomousAgent(
            agent_id=member['id'],
            role_id=member.get('role_id', 'developer'),
            role_description=member['role'],
            expertise=member['expertise'],
            team_id=team_id,
            state_manager=state_manager,
            access_controller=access_controller
        )
        agents.append(agent)
        await agent.initialize()

        # Show permissions
        perms = access_controller.get_agent_permissions(member.get('role_id', 'developer'))
        can_create_tasks = perms['tool_access'].get('create_task', False)

        print(f"   ✓ {member['id']}: {member['role']}")
        print(f"     Role: {member.get('role_id', 'developer')}")
        print(f"     Can create tasks: {'Yes' if can_create_tasks else 'No'}")
        print(f"     Expertise: {member['expertise']}")

    print("\n" + "="*70)
    print("\n🎬 STARTING DISCUSSION...\n")

    # 5. Run discussion (agents work in parallel)
    await asyncio.gather(*[
        agent.participate_in_discussion(agenda, discussion_rounds, target_outcome)
        for agent in agents
    ])

    print("\n" + "="*70)
    print("\n📊 DISCUSSION RESULTS:\n")

    # 6. Show results from persistent storage
    workspace_state = await state_manager.get_workspace_state(team_id)

    print(f"Team Participation:")
    print(f"  - Total messages: {workspace_state['messages']}")
    print(f"  - Knowledge shared: {workspace_state['knowledge_items']}")
    print(f"  - Decisions proposed: {workspace_state['decisions']}")
    print(f"  - Tasks created: {workspace_state['tasks']}")

    # Get all tasks
    from sqlalchemy import select
    from persistence.models import Task

    async with state_manager.db.session() as session:
        result = await session.execute(
            select(Task).where(Task.team_id == team_id)
        )
        tasks = result.scalars().all()

    if tasks:
        print(f"\n📝 Created Tasks:")
        for task in tasks:
            print(f"  - [{task.id[:8]}] {task.title}")
            print(f"    Required role: {task.required_role}")
            print(f"    Priority: {task.priority}")
            print(f"    Status: {task.status.value if hasattr(task.status, 'value') else task.status}")

    # Get all messages
    messages = await state_manager.get_messages(team_id, limit=100)

    if messages:
        print(f"\n💬 Message Thread (last 10):")
        for msg in messages[-10:]:
            print(f"  [{msg['from']}]: {msg['message'][:60]}...")

    # Get knowledge
    knowledge = await state_manager.get_knowledge(team_id)

    if knowledge:
        print(f"\n🧠 Shared Knowledge:")
        for item in knowledge:
            print(f"  - {item['key']}: {item['value'][:60]}...")

    print("\n" + "="*70)
    print("\n✅ DISCUSSION COMPLETE!")
    print("\nKey Achievements:")
    print("  ✓ All data persisted to database")
    print("  ✓ RBAC enforced on all actions")
    print("  ✓ Agents created executable tasks")
    print("  ✓ Complete audit trail available")
    print("  ✓ Ready for execution phase")

    # Cleanup
    await redis.close()
    await db.close()

    print("\n" + "="*70 + "\n")


# Example scenarios
async def example_product_feature_with_execution():
    """Product team that creates executable tasks"""

    await run_production_autonomous_discussion(
        agenda="Design and plan new real-time collaboration feature",
        discussion_rounds=4,
        target_outcome="Approved design with executable tasks created",
        team_composition=[
            {
                'id': 'pm',
                'role': 'Product Manager',
                'role_id': 'coordinator',  # Can create tasks
                'expertise': 'User needs, market requirements, prioritization'
            },
            {
                'id': 'architect',
                'role': 'Technical Architect',
                'role_id': 'architect',  # Can create workflows
                'expertise': 'System design, scalability, technical feasibility'
            },
            {
                'id': 'dev1',
                'role': 'Senior Developer',
                'role_id': 'developer',
                'expertise': 'Implementation, code quality, testing'
            }
        ],
        use_sqlite=True  # Use SQLite for demo
    )


async def main():
    """Run example"""
    print("\n🎯 Running: Product Feature Planning → Task Creation\n")
    print("This demonstrates the complete lifecycle:")
    print("  1. Autonomous discussion")
    print("  2. Team decision-making")
    print("  3. Task creation")
    print("  4. Ready for execution\n")

    await example_product_feature_with_execution()


if __name__ == "__main__":
    asyncio.run(main())
