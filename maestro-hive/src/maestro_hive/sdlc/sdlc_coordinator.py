#!/usr/bin/env python3
"""
SDLC Team Coordinator

Orchestrates the complete SDLC team with:
- 11 specialized personas
- Phase-based workflow execution
- RBAC enforcement
- Persistent state
- Event-driven coordination
- Progress monitoring

This is the main entry point for running SDLC teams with the production architecture.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import personas
import team_organization
import sdlc_workflow

SDLCPersonas = personas.SDLCPersonas
TeamOrganization = team_organization.TeamOrganization
SDLCPhase = team_organization.SDLCPhase
get_personas_for_phase = team_organization.get_personas_for_phase
get_next_phase = team_organization.get_next_phase
validate_phase_exit_criteria = team_organization.validate_phase_exit_criteria
SDLCWorkflowTemplates = sdlc_workflow.SDLCWorkflowTemplates

# Production architecture imports
from persistence import init_database, StateManager
from persistence.database import DatabaseConfig
from persistence.redis_manager import RedisManager
from rbac import RoleManager, AccessController
from workflow import WorkflowEngine
from workflow.dag import DAG

# Claude Code SDK imports (if using autonomous agents)
try:
    from claude_code_sdk import ClaudeCodeClient, ClaudeCodeConfig
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    print("Warning: claude_code_sdk not available. Autonomous agents disabled.")


class SDLCTeamCoordinator:
    """
    Main coordinator for SDLC teams

    Manages:
    - Team initialization with all 11 personas
    - Workflow creation and execution
    - Phase transitions
    - RBAC enforcement
    - Progress monitoring
    - Event-driven coordination
    """

    def __init__(
        self,
        team_id: str,
        project_name: str,
        state_manager: StateManager,
        workflow_engine: WorkflowEngine,
        access_controller: AccessController,
        use_autonomous_agents: bool = False
    ):
        self.team_id = team_id
        self.project_name = project_name
        self.state = state_manager
        self.workflow_engine = workflow_engine
        self.access = access_controller
        self.use_autonomous = use_autonomous_agents and CLAUDE_SDK_AVAILABLE

        self.personas = SDLCPersonas()
        self.organization = TeamOrganization()

        # Track team members
        self.team_members: Dict[str, Dict[str, Any]] = {}
        self.current_phase: Optional[SDLCPhase] = None
        self.current_workflow_id: Optional[str] = None

        # Autonomous agents (if enabled)
        self.agents: Dict[str, Any] = {}

    async def initialize_team(self):
        """
        Initialize the complete SDLC team with all 11 personas
        """
        print(f"\n{'=' * 80}")
        print(f"🚀 INITIALIZING SDLC TEAM: {self.project_name}")
        print(f"{'=' * 80}\n")

        # Get all persona definitions
        all_personas = [
            self.personas.requirement_analyst(),
            self.personas.solution_architect(),
            self.personas.frontend_developer(),
            self.personas.backend_developer(),
            self.personas.devops_engineer(),
            self.personas.qa_engineer(),
            self.personas.security_specialist(),
            self.personas.ui_ux_designer(),
            self.personas.technical_writer(),
            self.personas.deployment_specialist(),
            self.personas.deployment_integration_tester()
        ]

        print("👥 Team Members:\n")

        # Initialize each team member
        for persona in all_personas:
            agent_id = f"{persona['id']}_{self.team_id}"

            # Register with state manager
            await self.state.update_agent_status(
                team_id=self.team_id,
                agent_id=agent_id,
                role=persona['role_id'],
                status="initialized",
                message=f"Ready as {persona['name']}"
            )

            # Store team member info
            self.team_members[persona['id']] = {
                "agent_id": agent_id,
                "persona": persona,
                "role_id": persona['role_id'],
                "phase": persona['phase']
            }

            # Get RBAC permissions
            perms = self.access.get_agent_permissions(persona['role_id'])

            print(f"  ✓ {persona['name']} ({persona['id']})")
            print(f"    Role: {persona['role_id']} | Phase: {persona['phase']}")
            print(f"    Tools: {len(persona['tools_allowed'])} | Permissions: {len(perms['permissions'])}")

            # Initialize autonomous agent if enabled
            if self.use_autonomous:
                # This would initialize Claude agents with personas
                # Implementation depends on Claude Code SDK integration
                pass

        print(f"\n✅ Team initialized: {len(self.team_members)} members")
        print(f"{'=' * 80}\n")

    async def create_project_workflow(
        self,
        workflow_type: str,
        **workflow_params
    ) -> str:
        """
        Create a project workflow using templates

        Args:
            workflow_type: Type of workflow (feature, bugfix, security_patch, sprint)
            **workflow_params: Parameters for the workflow template
        """
        print(f"\n{'=' * 80}")
        print(f"📋 CREATING {workflow_type.upper()} WORKFLOW")
        print(f"{'=' * 80}\n")

        # Create DAG using templates
        if workflow_type == "feature":
            dag = SDLCWorkflowTemplates.create_feature_development_workflow(
                team_id=self.team_id,
                **workflow_params
            )
        elif workflow_type == "bugfix":
            dag = SDLCWorkflowTemplates.create_bug_fix_workflow(**workflow_params)
        elif workflow_type == "security_patch":
            dag = SDLCWorkflowTemplates.create_security_patch_workflow(**workflow_params)
        elif workflow_type == "sprint":
            dag = SDLCWorkflowTemplates.create_sprint_workflow(**workflow_params)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Create workflow in workflow engine
        workflow_id = await self.workflow_engine.create_workflow(
            team_id=self.team_id,
            dag=dag,
            created_by=f"coordinator_{self.team_id}"
        )

        self.current_workflow_id = workflow_id

        # Print workflow summary
        total_tasks = len(dag.nodes)
        total_hours = sum(n.estimated_hours for n in dag.nodes.values())
        critical_path = dag.get_critical_path()

        print(f"  ✓ Workflow created: {workflow_id}")
        print(f"  📊 Statistics:")
        print(f"     - Total tasks: {total_tasks}")
        print(f"     - Estimated hours: {total_hours}")
        print(f"     - Critical path: {len(critical_path)} tasks")
        print(f"  🎯 Ready for execution!")

        print(f"\n{'=' * 80}\n")

        return workflow_id

    async def start_phase(self, phase: SDLCPhase):
        """
        Start a specific SDLC phase

        This:
        1. Sets current phase
        2. Notifies relevant personas
        3. Makes phase tasks ready
        """
        print(f"\n{'=' * 80}")
        print(f"🚦 STARTING PHASE: {phase.value.upper()}")
        print(f"{'=' * 80}\n")

        self.current_phase = phase

        # Get phase info
        phase_structure = self.organization.get_phase_structure()
        phase_info = phase_structure.get(phase, {})

        # Get personas for this phase
        primary_personas = phase_info.get('primary_personas', [])
        supporting_personas = phase_info.get('supporting_personas', [])

        print(f"  📋 {phase_info.get('name', phase.value)}")
        print(f"  👥 Primary: {', '.join(primary_personas)}")
        if supporting_personas:
            print(f"  🤝 Supporting: {', '.join(supporting_personas)}")

        print(f"\n  📝 Deliverables:")
        for deliverable in phase_info.get('deliverables', []):
            print(f"     - {deliverable}")

        # Notify team members
        for persona_id in primary_personas + supporting_personas:
            if persona_id in self.team_members:
                member = self.team_members[persona_id]
                await self.state.post_message(
                    team_id=self.team_id,
                    from_agent="coordinator",
                    to_agent=member['agent_id'],
                    message=f"Phase {phase.value} has started. Your expertise is needed.",
                    metadata={"phase": phase.value, "role": "primary" if persona_id in primary_personas else "supporting"}
                )

        print(f"\n  ✅ Phase started. Team notified.")
        print(f"{'=' * 80}\n")

    async def get_ready_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks that are ready to be claimed

        Returns tasks where all dependencies are complete
        """
        if not self.current_workflow_id:
            return []

        # Get workflow status from engine
        workflow_status = await self.workflow_engine.get_workflow_status(
            team_id=self.team_id,
            workflow_id=self.current_workflow_id
        )

        ready_tasks = []
        for task in workflow_status.get('tasks', []):
            if task['status'] == 'ready':
                ready_tasks.append(task)

        return ready_tasks

    async def assign_task_to_persona(self, task_id: str, persona_id: str):
        """
        Assign a task to a specific persona

        Enforces RBAC - persona must have permission and required role
        """
        if persona_id not in self.team_members:
            raise ValueError(f"Unknown persona: {persona_id}")

        member = self.team_members[persona_id]

        # Check RBAC permission
        try:
            self.access.check_access(
                agent_id=member['agent_id'],
                role_id=member['role_id'],
                tool_name="claim_task",
                context={"task_id": task_id}
            )
        except Exception as e:
            print(f"  ✗ RBAC denied: {e}")
            return False

        # Claim task
        result = await self.state.claim_task(
            task_id=task_id,
            agent_id=member['agent_id']
        )

        if result['status'] == 'success':
            print(f"  ✓ Task {task_id[:8]} assigned to {member['persona']['name']}")
            return True
        else:
            print(f"  ✗ Failed to assign task: {result.get('message')}")
            return False

    async def auto_assign_tasks(self):
        """
        Automatically assign ready tasks to appropriate personas

        Matches task required_role with persona roles
        """
        ready_tasks = await self.get_ready_tasks()

        if not ready_tasks:
            return 0

        print(f"\n📋 Auto-assigning {len(ready_tasks)} ready tasks...\n")

        assigned_count = 0
        for task in ready_tasks:
            required_role = task.get('required_role')

            # Find persona with matching role
            for persona_id, member in self.team_members.items():
                if member['role_id'] == required_role:
                    success = await self.assign_task_to_persona(task['id'], persona_id)
                    if success:
                        assigned_count += 1
                    break

        print(f"\n✅ Assigned {assigned_count} tasks")
        return assigned_count

    async def complete_task(
        self,
        task_id: str,
        persona_id: str,
        result: Dict[str, Any]
    ):
        """
        Complete a task and update workflow state
        """
        if persona_id not in self.team_members:
            raise ValueError(f"Unknown persona: {persona_id}")

        member = self.team_members[persona_id]

        # Check RBAC
        try:
            self.access.check_access(
                agent_id=member['agent_id'],
                role_id=member['role_id'],
                tool_name="complete_task",
                context={"task_id": task_id}
            )
        except Exception as e:
            print(f"  ✗ RBAC denied: {e}")
            return False

        # Complete task
        completion_result = await self.state.complete_task(
            task_id=task_id,
            result=result
        )

        if completion_result['status'] == 'success':
            print(f"  ✓ Task {task_id[:8]} completed by {member['persona']['name']}")

            # Check if this unlocks new tasks
            await self.auto_assign_tasks()

            return True
        else:
            print(f"  ✗ Failed to complete task: {completion_result.get('message')}")
            return False

    async def check_phase_completion(self, phase: SDLCPhase) -> Dict[str, Any]:
        """
        Check if a phase can be completed based on exit criteria
        """
        phase_structure = self.organization.get_phase_structure()
        phase_info = phase_structure.get(phase, {})

        # Get all deliverables from completed tasks
        from sqlalchemy import select
        from persistence.models import Task, TaskStatus

        completed_deliverables = set()

        async with self.state.db.session() as session:
            result = await session.execute(
                select(Task).where(
                    Task.team_id == self.team_id,
                    Task.workflow_id == self.current_workflow_id,
                    Task.status == TaskStatus.SUCCESS
                )
            )
            tasks = result.scalars().all()

            for task in tasks:
                # Extract deliverable from task title/description
                if task.result and isinstance(task.result, dict):
                    deliverable = task.result.get('deliverable')
                    if deliverable:
                        completed_deliverables.add(deliverable)

        # Validate exit criteria
        validation = validate_phase_exit_criteria(phase, completed_deliverables)

        return {
            "phase": phase.value,
            "can_complete": validation['can_exit'],
            "completion_percentage": validation['completion_percentage'],
            "missing_criteria": validation['missing_criteria'],
            "completed_deliverables": list(completed_deliverables)
        }

    async def transition_to_next_phase(self):
        """
        Transition to the next SDLC phase

        Checks current phase completion and moves to next phase
        """
        if not self.current_phase:
            print("  ✗ No current phase set")
            return False

        # Check if current phase can be completed
        completion_status = await self.check_phase_completion(self.current_phase)

        if not completion_status['can_complete']:
            print(f"\n  ✗ Cannot complete {self.current_phase.value} phase")
            print(f"    Missing criteria:")
            for criterion in completion_status['missing_criteria']:
                print(f"      - {criterion}")
            return False

        # Get next phase
        next_phase = get_next_phase(self.current_phase)

        if not next_phase:
            print(f"\n  ✅ {self.current_phase.value} was the final phase!")
            return True

        # Transition
        print(f"\n  ✅ {self.current_phase.value} phase complete!")
        print(f"  🚀 Transitioning to {next_phase.value} phase...")

        await self.start_phase(next_phase)

        return True

    async def get_project_status(self) -> Dict[str, Any]:
        """
        Get comprehensive project status
        """
        workspace_state = await self.state.get_workspace_state(self.team_id)

        # Get workflow status
        workflow_status = None
        if self.current_workflow_id:
            workflow_status = await self.workflow_engine.get_workflow_status(
                team_id=self.team_id,
                workflow_id=self.current_workflow_id
            )

        # Get phase completion
        phase_completion = None
        if self.current_phase:
            phase_completion = await self.check_phase_completion(self.current_phase)

        return {
            "team_id": self.team_id,
            "project_name": self.project_name,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "workflow_id": self.current_workflow_id,
            "team_size": len(self.team_members),
            "workspace_state": workspace_state,
            "workflow_status": workflow_status,
            "phase_completion": phase_completion,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def print_status(self):
        """
        Print a formatted status report
        """
        status = await self.get_project_status()

        print(f"\n{'=' * 80}")
        print(f"📊 PROJECT STATUS: {self.project_name}")
        print(f"{'=' * 80}\n")

        print(f"🏷️  Team ID: {status['team_id']}")
        print(f"👥 Team Size: {status['team_size']} members")
        print(f"📋 Current Phase: {status['current_phase'] or 'Not started'}")
        print(f"🔄 Workflow: {status['workflow_id'] or 'Not created'}")

        if status['workspace_state']:
            ws = status['workspace_state']
            print(f"\n📈 Activity:")
            print(f"   - Messages: {ws['messages']}")
            print(f"   - Tasks: {ws['tasks']}")
            print(f"   - Knowledge Items: {ws['knowledge_items']}")
            print(f"   - Decisions: {ws['decisions']}")

        if status['workflow_status']:
            wf = status['workflow_status']
            print(f"\n🎯 Workflow Progress:")
            print(f"   - Status: {wf['status']}")
            print(f"   - Total Tasks: {wf.get('total_tasks', 0)}")
            print(f"   - Completed: {wf.get('completed_tasks', 0)}")
            print(f"   - In Progress: {wf.get('running_tasks', 0)}")
            print(f"   - Ready: {wf.get('ready_tasks', 0)}")

        if status['phase_completion']:
            pc = status['phase_completion']
            print(f"\n✅ Phase Completion:")
            print(f"   - Progress: {pc['completion_percentage']:.1f}%")
            print(f"   - Can Complete: {'Yes' if pc['can_complete'] else 'No'}")
            if pc['missing_criteria']:
                print(f"   - Missing: {len(pc['missing_criteria'])} criteria")

        print(f"\n{'=' * 80}\n")

    async def run_simulation(self, max_iterations: int = 100):
        """
        Run a simulation of the SDLC workflow

        This simulates task execution by auto-assigning and auto-completing tasks
        """
        print(f"\n{'=' * 80}")
        print(f"🎬 RUNNING SDLC SIMULATION")
        print(f"{'=' * 80}\n")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            print(f"\n--- Iteration {iteration} ---")

            # Auto-assign ready tasks
            assigned = await self.auto_assign_tasks()

            if assigned == 0:
                # Check if we can move to next phase
                if self.current_phase:
                    can_transition = await self.transition_to_next_phase()
                    if not can_transition:
                        print("  ℹ️  No tasks ready and cannot transition. Workflow may be complete or blocked.")
                        break
                else:
                    print("  ℹ️  No tasks ready. Workflow may be complete.")
                    break

            # Simulate task completion (in real scenario, agents would work on tasks)
            # For simulation, we'll mark assigned tasks as complete
            from sqlalchemy import select
            from persistence.models import Task, TaskStatus

            async with self.state.db.session() as session:
                result = await session.execute(
                    select(Task).where(
                        Task.team_id == self.team_id,
                        Task.workflow_id == self.current_workflow_id,
                        Task.status == TaskStatus.RUNNING
                    ).limit(5)  # Complete up to 5 tasks per iteration
                )
                running_tasks = result.scalars().all()

                for task in running_tasks:
                    # Simulate task completion
                    persona_id = task.assigned_to.split('_')[0]  # Extract persona_id from agent_id
                    if persona_id in self.team_members:
                        await self.complete_task(
                            task_id=task.id,
                            persona_id=persona_id,
                            result={
                                "status": "success",
                                "deliverable": task.title,
                                "simulated": True
                            }
                        )

            await asyncio.sleep(0.5)  # Small delay between iterations

        print(f"\n{'=' * 80}")
        print(f"✅ SIMULATION COMPLETE")
        print(f"{'=' * 80}\n")

        await self.print_status()


# Helper function to create and initialize SDLC coordinator
async def create_sdlc_team(
    project_name: str,
    use_sqlite: bool = True,
    use_autonomous_agents: bool = False
) -> SDLCTeamCoordinator:
    """
    Create and initialize a complete SDLC team with production architecture

    Args:
        project_name: Name of the project
        use_sqlite: Use SQLite (True) or PostgreSQL (False)
        use_autonomous_agents: Enable autonomous Claude agents

    Returns:
        Initialized SDLCTeamCoordinator
    """
    # Initialize infrastructure
    if use_sqlite:
        db_config = DatabaseConfig.for_testing()
    else:
        db_config = DatabaseConfig.from_env()

    db = await init_database(db_config)
    redis = RedisManager()
    await redis.initialize()

    state_manager = StateManager(db, redis)

    # Setup RBAC
    role_manager = RoleManager()
    access_controller = AccessController(role_manager)

    # Create workflow engine
    workflow_engine = WorkflowEngine(state_manager)

    # Create coordinator
    team_id = f"sdlc_{uuid.uuid4().hex[:8]}"

    coordinator = SDLCTeamCoordinator(
        team_id=team_id,
        project_name=project_name,
        state_manager=state_manager,
        workflow_engine=workflow_engine,
        access_controller=access_controller,
        use_autonomous_agents=use_autonomous_agents
    )

    # Initialize team
    await coordinator.initialize_team()

    return coordinator


if __name__ == "__main__":
    async def demo():
        """Demo: Create SDLC team and run feature development"""

        # Create team
        coordinator = await create_sdlc_team(
            project_name="E-Commerce Platform",
            use_sqlite=True,
            use_autonomous_agents=False
        )

        # Create feature workflow
        await coordinator.create_project_workflow(
            workflow_type="feature",
            feature_name="User Authentication",
            complexity="medium",
            include_security_review=True,
            include_performance_testing=True
        )

        # Start requirements phase
        await coordinator.start_phase(SDLCPhase.REQUIREMENTS)

        # Run simulation
        await coordinator.run_simulation(max_iterations=50)

        # Final status
        await coordinator.print_status()

        # Cleanup
        await coordinator.state.redis.close()
        await coordinator.state.db.close()

    asyncio.run(demo())
