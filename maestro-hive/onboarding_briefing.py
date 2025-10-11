#!/usr/bin/env python3
"""
AI-Powered Onboarding Briefing Generator

Generates tailored "State of the Union" briefings for new team members,
providing just-in-time context to accelerate productivity.

Briefings include:
- Executive summary of project status
- Key decisions relevant to the role
- Immediate tasks assigned
- Key contacts and stakeholders
- Resources and artifacts to review
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from persistence.state_manager import StateManager
from persistence.models import TaskStatus
import team_organization

SDLCPhase = team_organization.SDLCPhase


@dataclass
class KeyDecision:
    """A key decision made during the project"""
    decision_id: str
    decision: str
    rationale: str
    decided_by: str
    decided_at: str
    impact: str  # "high", "medium", "low"
    relevance_to_role: str


@dataclass
class ImmediateTask:
    """A task immediately relevant to the new member"""
    task_id: str
    title: str
    description: str
    priority: int
    estimated_hours: int
    dependencies: List[str] = field(default_factory=list)


@dataclass
class KeyContact:
    """A key contact for the new member"""
    role: str
    agent_id: str
    persona_id: str
    responsibility: str
    when_to_contact: str


@dataclass
class ResourceLink:
    """A resource to review"""
    title: str
    type: str  # "artifact", "decision", "knowledge", "documentation"
    link: str
    priority: str  # "must_read", "recommended", "optional"
    estimated_read_time_minutes: int


@dataclass
class OnboardingBriefing:
    """Complete onboarding briefing for a new team member"""
    # Metadata
    generated_at: str
    generated_for_agent: str
    generated_for_persona: str
    generated_for_role: Optional[str]
    project_name: str
    team_id: str
    current_phase: str

    # Executive summary
    executive_summary: str

    # Key information
    key_decisions: List[KeyDecision] = field(default_factory=list)
    immediate_tasks: List[ImmediateTask] = field(default_factory=list)
    key_contacts: List[KeyContact] = field(default_factory=list)
    resources: List[ResourceLink] = field(default_factory=list)

    # Context
    project_timeline: Dict[str, Any] = field(default_factory=dict)
    recent_accomplishments: List[str] = field(default_factory=list)
    current_challenges: List[str] = field(default_factory=list)
    your_focus_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "metadata": {
                "generated_at": self.generated_at,
                "generated_for_agent": self.generated_for_agent,
                "generated_for_persona": self.generated_for_persona,
                "generated_for_role": self.generated_for_role,
                "project_name": self.project_name,
                "team_id": self.team_id,
                "current_phase": self.current_phase
            },
            "executive_summary": self.executive_summary,
            "key_decisions": [
                {
                    "decision_id": d.decision_id,
                    "decision": d.decision,
                    "rationale": d.rationale,
                    "decided_by": d.decided_by,
                    "decided_at": d.decided_at,
                    "impact": d.impact,
                    "relevance": d.relevance_to_role
                }
                for d in self.key_decisions
            ],
            "immediate_tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "description": t.description,
                    "priority": t.priority,
                    "estimated_hours": t.estimated_hours,
                    "dependencies": t.dependencies
                }
                for t in self.immediate_tasks
            ],
            "key_contacts": [
                {
                    "role": c.role,
                    "agent_id": c.agent_id,
                    "persona_id": c.persona_id,
                    "responsibility": c.responsibility,
                    "when_to_contact": c.when_to_contact
                }
                for c in self.key_contacts
            ],
            "resources": [
                {
                    "title": r.title,
                    "type": r.type,
                    "link": r.link,
                    "priority": r.priority,
                    "read_time_minutes": r.estimated_read_time_minutes
                }
                for r in self.resources
            ],
            "context": {
                "project_timeline": self.project_timeline,
                "recent_accomplishments": self.recent_accomplishments,
                "current_challenges": self.current_challenges,
                "your_focus_areas": self.your_focus_areas
            }
        }


class OnboardingBriefingGenerator:
    """
    Generates contextual onboarding briefings

    Uses project history, decisions, tasks, and artifacts to create
    tailored briefings for new team members.
    """

    def __init__(
        self,
        state_manager: StateManager,
        project_name: str = "Unnamed Project"
    ):
        self.state = state_manager
        self.project_name = project_name

    async def generate_briefing(
        self,
        team_id: str,
        agent_id: str,
        persona_id: str,
        current_phase: SDLCPhase,
        role_id: Optional[str] = None
    ) -> OnboardingBriefing:
        """
        Generate complete onboarding briefing

        Args:
            team_id: Team identifier
            agent_id: New agent joining
            persona_id: Persona type (e.g., "security_specialist")
            current_phase: Current SDLC phase
            role_id: Optional role being filled (e.g., "Security Auditor")

        Returns:
            Complete OnboardingBriefing
        """
        print(f"\n  Generating onboarding briefing for {persona_id}...")

        # Gather all information
        decisions = await self._get_relevant_decisions(team_id, persona_id, current_phase)
        tasks = await self._get_immediate_tasks(team_id, persona_id, current_phase)
        contacts = await self._get_key_contacts(team_id, persona_id)
        resources = await self._get_key_resources(team_id, persona_id, current_phase)
        timeline = await self._get_project_timeline(team_id)
        accomplishments = await self._get_recent_accomplishments(team_id)
        challenges = await self._get_current_challenges(team_id)
        focus_areas = self._get_focus_areas_for_persona(persona_id, current_phase)

        # Generate executive summary
        summary = await self._generate_executive_summary(
            persona_id=persona_id,
            current_phase=current_phase,
            role_id=role_id,
            decisions=decisions,
            tasks=tasks
        )

        briefing = OnboardingBriefing(
            generated_at=datetime.utcnow().isoformat(),
            generated_for_agent=agent_id,
            generated_for_persona=persona_id,
            generated_for_role=role_id,
            project_name=self.project_name,
            team_id=team_id,
            current_phase=current_phase.value,
            executive_summary=summary,
            key_decisions=decisions,
            immediate_tasks=tasks,
            key_contacts=contacts,
            resources=resources,
            project_timeline=timeline,
            recent_accomplishments=accomplishments,
            current_challenges=challenges,
            your_focus_areas=focus_areas
        )

        print(f"  ✓ Briefing generated with:")
        print(f"     - {len(decisions)} key decisions")
        print(f"     - {len(tasks)} immediate tasks")
        print(f"     - {len(contacts)} key contacts")
        print(f"     - {len(resources)} resources")

        return briefing

    # =========================================================================
    # Information Gathering
    # =========================================================================

    async def _get_relevant_decisions(
        self,
        team_id: str,
        persona_id: str,
        current_phase: SDLCPhase
    ) -> List[KeyDecision]:
        """Get key decisions relevant to this persona"""
        # Get recent decisions from decision log
        from persistence.models import Decision

        async with self.state.db.session() as session:
            from sqlalchemy import select, desc

            result = await session.execute(
                select(Decision).where(
                    Decision.team_id == team_id
                ).order_by(desc(Decision.proposed_at)).limit(20)
            )
            all_decisions = result.scalars().all()

        # Filter to relevant decisions based on persona
        relevant_decisions = []
        for decision in all_decisions:
            relevance = self._assess_decision_relevance(decision, persona_id, current_phase)
            if relevance != "not_relevant":
                relevant_decisions.append(KeyDecision(
                    decision_id=decision.id,
                    decision=decision.decision,
                    rationale=decision.rationale or "No rationale provided",
                    decided_by=decision.proposed_by,
                    decided_at=decision.proposed_at.isoformat(),
                    impact="high" if decision.status == "approved" else "medium",
                    relevance_to_role=relevance
                ))

        # Sort by relevance and return top 5
        return sorted(
            relevant_decisions,
            key=lambda d: {"critical": 0, "high": 1, "medium": 2}.get(d.relevance_to_role, 3)
        )[:5]

    async def _get_immediate_tasks(
        self,
        team_id: str,
        persona_id: str,
        current_phase: SDLCPhase
    ) -> List[ImmediateTask]:
        """Get tasks immediately assigned or relevant to this persona"""
        from persistence.models import Task

        async with self.state.db.session() as session:
            from sqlalchemy import select

            # Get ready tasks for this persona's role
            persona_role_map = {
                "backend_developer": "developer",
                "frontend_developer": "developer",
                "security_specialist": "security",
                "qa_engineer": "tester",
                "solution_architect": "architect",
                "devops_engineer": "devops"
            }

            role = persona_role_map.get(persona_id, "any")

            result = await session.execute(
                select(Task).where(
                    Task.team_id == team_id,
                    Task.status.in_([TaskStatus.READY, TaskStatus.PENDING]),
                    Task.required_role.in_([role, "any", None])
                ).limit(10)
            )
            tasks = result.scalars().all()

        immediate_tasks = []
        for task in tasks:
            immediate_tasks.append(ImmediateTask(
                task_id=task.id,
                title=task.title,
                description=task.description or "No description",
                priority=task.priority,
                estimated_hours=4,  # Default estimate
                dependencies=[dep.id for dep in task.dependencies] if task.dependencies else []
            ))

        return sorted(immediate_tasks, key=lambda t: t.priority, reverse=True)[:5]

    async def _get_key_contacts(
        self,
        team_id: str,
        persona_id: str
    ) -> List[KeyContact]:
        """Get key contacts for this persona"""
        # Get active team members
        from persistence.models import MembershipState

        members = await self.state.get_team_members(team_id, state=MembershipState.ACTIVE)

        # Define key roles to contact based on persona
        contact_mapping = {
            "backend_developer": ["solution_architect", "devops_engineer", "qa_engineer"],
            "frontend_developer": ["ui_ux_designer", "solution_architect", "backend_developer"],
            "security_specialist": ["solution_architect", "devops_engineer", "backend_developer"],
            "qa_engineer": ["backend_developer", "frontend_developer", "requirement_analyst"],
            "solution_architect": ["requirement_analyst", "security_specialist", "devops_engineer"],
            "devops_engineer": ["solution_architect", "backend_developer", "deployment_specialist"]
        }

        relevant_personas = contact_mapping.get(persona_id, ["solution_architect"])

        key_contacts = []
        for member in members:
            if member['persona_id'] in relevant_personas:
                contact = KeyContact(
                    role=member['persona_id'].replace('_', ' ').title(),
                    agent_id=member['agent_id'],
                    persona_id=member['persona_id'],
                    responsibility=self._get_persona_responsibility(member['persona_id']),
                    when_to_contact=self._get_contact_guidance(persona_id, member['persona_id'])
                )
                key_contacts.append(contact)

        return key_contacts[:5]

    async def _get_key_resources(
        self,
        team_id: str,
        persona_id: str,
        current_phase: SDLCPhase
    ) -> List[ResourceLink]:
        """Get key resources to review"""
        # Get recent knowledge items
        knowledge_items = await self.state.get_knowledge(team_id)

        resources = []

        # Add knowledge items as resources
        for item in knowledge_items[:5]:
            resources.append(ResourceLink(
                title=item['key'],
                type="knowledge",
                link=f"knowledge/{item['id']}",
                priority="recommended" if item['category'] == "critical" else "optional",
                estimated_read_time_minutes=5
            ))

        # Add phase-specific resources
        phase_resources = self._get_phase_resources(persona_id, current_phase)
        resources.extend(phase_resources)

        return resources

    async def _get_project_timeline(self, team_id: str) -> Dict[str, Any]:
        """Get project timeline summary"""
        workspace = await self.state.get_workspace_state(team_id)

        return {
            "tasks_total": sum(workspace['tasks'].values()) if workspace['tasks'] else 0,
            "tasks_completed": workspace['tasks'].get('success', 0) if workspace['tasks'] else 0,
            "messages_exchanged": workspace.get('messages', 0),
            "knowledge_items": workspace.get('knowledge_items', 0)
        }

    async def _get_recent_accomplishments(self, team_id: str) -> List[str]:
        """Get recent project accomplishments"""
        from persistence.models import Task

        async with self.state.db.session() as session:
            from sqlalchemy import select, desc

            # Get recently completed tasks
            result = await session.execute(
                select(Task).where(
                    Task.team_id == team_id,
                    Task.status == TaskStatus.SUCCESS
                ).order_by(desc(Task.completed_at)).limit(5)
            )
            completed_tasks = result.scalars().all()

        accomplishments = []
        for task in completed_tasks:
            if task.completed_at:
                days_ago = (datetime.utcnow() - task.completed_at).days
                accomplishments.append(f"Completed: {task.title} ({days_ago} days ago)")

        return accomplishments

    async def _get_current_challenges(self, team_id: str) -> List[str]:
        """Get current project challenges"""
        from persistence.models import Task

        async with self.state.db.session() as session:
            from sqlalchemy import select

            # Get blocked or failed tasks
            result = await session.execute(
                select(Task).where(
                    Task.team_id == team_id,
                    Task.status.in_([TaskStatus.BLOCKED, TaskStatus.FAILED])
                ).limit(5)
            )
            problem_tasks = result.scalars().all()

        challenges = []
        for task in problem_tasks:
            status = "blocked" if task.status == TaskStatus.BLOCKED else "failed"
            challenges.append(f"{task.title} is {status}")

        if not challenges:
            challenges.append("No major blockers identified")

        return challenges

    def _get_focus_areas_for_persona(
        self,
        persona_id: str,
        current_phase: SDLCPhase
    ) -> List[str]:
        """Get focus areas for this persona in this phase"""
        focus_map = {
            ("backend_developer", "implementation"): [
                "API implementation according to contracts",
                "Database schema implementation",
                "Unit test coverage (target: 80%+)",
                "Code review compliance"
            ],
            ("frontend_developer", "implementation"): [
                "UI component implementation",
                "API integration",
                "Responsive design validation",
                "Accessibility compliance"
            ],
            ("security_specialist", "design"): [
                "Security architecture review",
                "Threat modeling",
                "Security controls design",
                "Compliance requirements"
            ],
            ("security_specialist", "testing"): [
                "Penetration testing",
                "Security vulnerability scanning",
                "Security regression testing",
                "Compliance validation"
            ],
            ("qa_engineer", "testing"): [
                "Test plan execution",
                "Bug reporting and tracking",
                "Regression testing",
                "UAT coordination"
            ]
        }

        key = (persona_id, current_phase.value)
        return focus_map.get(key, [
            "Collaborate with team on current phase",
            "Complete assigned tasks",
            "Maintain code/artifact quality"
        ])

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _generate_executive_summary(
        self,
        persona_id: str,
        current_phase: SDLCPhase,
        role_id: Optional[str],
        decisions: List[KeyDecision],
        tasks: List[ImmediateTask]
    ) -> str:
        """Generate executive summary (could use LLM here)"""
        role_text = f" to fill the role of {role_id}" if role_id else ""
        phase_text = current_phase.value.replace('_', ' ').title()

        summary = f"""You are joining {self.project_name} at the {phase_text} phase{role_text}.

The project is currently active with {len(decisions)} key decisions made and {len(tasks)} immediate tasks ready for work.

Your focus will be on {persona_id.replace('_', ' ')} responsibilities during this phase. """

        if decisions:
            summary += f"The most recent critical decision was: {decisions[0].decision}. "

        if tasks:
            summary += f"Your immediate priority is: {tasks[0].title}."

        return summary

    def _assess_decision_relevance(
        self,
        decision: Any,
        persona_id: str,
        current_phase: SDLCPhase
    ) -> str:
        """Assess how relevant a decision is to a persona (critical/high/medium/not_relevant)"""
        decision_text = decision.decision.lower()

        # Keyword matching for relevance (in real implementation, could use LLM)
        persona_keywords = {
            "security_specialist": ["security", "auth", "encryption", "compliance", "vulnerability"],
            "backend_developer": ["api", "database", "backend", "server", "performance"],
            "frontend_developer": ["ui", "frontend", "user interface", "react", "component"],
            "devops_engineer": ["infrastructure", "deployment", "docker", "kubernetes", "ci/cd"],
            "qa_engineer": ["testing", "quality", "test", "bug", "validation"]
        }

        keywords = persona_keywords.get(persona_id, [])

        if any(keyword in decision_text for keyword in keywords):
            return "high"

        return "medium"  # Everything is somewhat relevant

    def _get_persona_responsibility(self, persona_id: str) -> str:
        """Get responsibility description for persona"""
        responsibilities = {
            "solution_architect": "Architecture decisions and technical leadership",
            "backend_developer": "Backend implementation and API development",
            "frontend_developer": "Frontend implementation and UI development",
            "security_specialist": "Security reviews and compliance",
            "devops_engineer": "Infrastructure and deployment",
            "qa_engineer": "Quality assurance and testing",
            "ui_ux_designer": "User experience and interface design"
        }
        return responsibilities.get(persona_id, "Team contribution")

    def _get_contact_guidance(self, your_persona: str, contact_persona: str) -> str:
        """Get guidance on when to contact someone"""
        guidance_map = {
            ("backend_developer", "solution_architect"): "For architecture questions or design decisions",
            ("backend_developer", "devops_engineer"): "For deployment or infrastructure questions",
            ("frontend_developer", "ui_ux_designer"): "For design clarifications or UI/UX questions",
            ("security_specialist", "solution_architect"): "For architecture security reviews",
            ("qa_engineer", "backend_developer"): "For bug reports and testing questions"
        }

        key = (your_persona, contact_persona)
        return guidance_map.get(key, "For collaboration and questions")

    def _get_phase_resources(self, persona_id: str, current_phase: SDLCPhase) -> List[ResourceLink]:
        """Get phase-specific resources"""
        # In real implementation, this would query actual artifacts
        return [
            ResourceLink(
                title=f"{current_phase.value.title()} Phase Documentation",
                type="documentation",
                link=f"/docs/{current_phase.value}",
                priority="must_read",
                estimated_read_time_minutes=15
            ),
            ResourceLink(
                title="Project Architecture Overview",
                type="artifact",
                link="/artifacts/architecture",
                priority="must_read",
                estimated_read_time_minutes=20
            )
        ]

    # =========================================================================
    # Formatting and Output
    # =========================================================================

    def print_briefing(self, briefing: OnboardingBriefing):
        """Print formatted briefing"""
        print(f"\n{'=' * 80}")
        print(f"ONBOARDING BRIEFING: {briefing.project_name}")
        print(f"{'=' * 80}\n")

        print(f"Generated for: {briefing.generated_for_persona}")
        if briefing.generated_for_role:
            print(f"Role: {briefing.generated_for_role}")
        print(f"Current Phase: {briefing.current_phase}")
        print(f"Generated: {briefing.generated_at}\n")

        print(f"{'─' * 80}")
        print("EXECUTIVE SUMMARY")
        print(f"{'─' * 80}\n")
        print(briefing.executive_summary)

        if briefing.key_decisions:
            print(f"\n{'─' * 80}")
            print("KEY DECISIONS")
            print(f"{'─' * 80}\n")
            for i, decision in enumerate(briefing.key_decisions, 1):
                print(f"{i}. {decision.decision}")
                print(f"   Rationale: {decision.rationale}")
                print(f"   Decided by: {decision.decided_by}")
                print(f"   Relevance: {decision.relevance_to_role}\n")

        if briefing.immediate_tasks:
            print(f"{'─' * 80}")
            print("YOUR IMMEDIATE TASKS")
            print(f"{'─' * 80}\n")
            for i, task in enumerate(briefing.immediate_tasks, 1):
                print(f"{i}. [{task.priority}] {task.title}")
                print(f"   {task.description}")
                print(f"   Estimated: {task.estimated_hours}h\n")

        if briefing.key_contacts:
            print(f"{'─' * 80}")
            print("KEY CONTACTS")
            print(f"{'─' * 80}\n")
            for contact in briefing.key_contacts:
                print(f"• {contact.role}: {contact.agent_id}")
                print(f"  Responsibility: {contact.responsibility}")
                print(f"  When to contact: {contact.when_to_contact}\n")

        if briefing.resources:
            print(f"{'─' * 80}")
            print("RESOURCES TO REVIEW")
            print(f"{'─' * 80}\n")
            for resource in briefing.resources:
                priority_icon = "🔴" if resource.priority == "must_read" else "🟡" if resource.priority == "recommended" else "⚪"
                print(f"{priority_icon} {resource.title} ({resource.estimated_read_time_minutes}min)")
                print(f"   Type: {resource.type} | Link: {resource.link}\n")

        print(f"{'=' * 80}\n")


if __name__ == "__main__":
    print("Onboarding Briefing Generator")
    print("=" * 80)
    print("\nGenerates tailored 'State of the Union' briefings for new team members.")
    print("Includes: decisions, tasks, contacts, resources, and context.")
