#!/usr/bin/env python3
"""
Team Composer: Assembles optimal AI teams based on task requirements.

This module handles team composition, including:
- Skill matching between tasks and personas
- Dynamic scaling of team size
- Role assignment based on task complexity
- Context sharing between team members
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels affecting team size."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PersonaRole(Enum):
    """Standard persona roles in a team."""
    LEAD = "lead"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    QA = "qa"
    ARCHITECT = "architect"
    DOCUMENTOR = "documentor"


@dataclass
class Skill:
    """Represents a skill with proficiency level."""
    name: str
    proficiency: float = 1.0  # 0.0 to 1.0

    def matches(self, required_skill: str, min_proficiency: float = 0.5) -> bool:
        """Check if this skill matches a required skill."""
        return (
            self.name.lower() == required_skill.lower()
            and self.proficiency >= min_proficiency
        )


@dataclass
class PersonaInstance:
    """Represents an available persona that can be assigned to a team."""
    persona_id: str
    name: str
    skills: List[Skill]
    current_load: float = 0.0  # 0.0 to 1.0
    max_concurrent_tasks: int = 3

    def available_capacity(self) -> float:
        """Calculate available capacity."""
        return max(0.0, 1.0 - self.current_load)

    def has_skill(self, skill_name: str, min_proficiency: float = 0.5) -> bool:
        """Check if persona has a specific skill."""
        return any(s.matches(skill_name, min_proficiency) for s in self.skills)

    def skill_score(self, required_skills: List[str]) -> float:
        """Calculate skill match score for required skills."""
        if not required_skills:
            return 1.0
        matches = sum(1 for rs in required_skills if self.has_skill(rs))
        return matches / len(required_skills)


@dataclass
class TaskRequirements:
    """Requirements for a task that needs team assignment."""
    task_id: str
    title: str
    complexity: TaskComplexity
    required_skills: List[str]
    estimated_effort_hours: float
    priority: int = 5  # 1-10, higher is more urgent
    dependencies: List[str] = field(default_factory=list)

    def min_team_size(self) -> int:
        """Get minimum team size based on complexity."""
        complexity_to_size = {
            TaskComplexity.LOW: 1,
            TaskComplexity.MEDIUM: 2,
            TaskComplexity.HIGH: 3,
            TaskComplexity.CRITICAL: 4
        }
        return complexity_to_size.get(self.complexity, 2)


@dataclass
class TeamConstraints:
    """Constraints on team composition."""
    max_team_size: int = 5
    min_team_size: int = 1
    required_roles: List[PersonaRole] = field(default_factory=list)
    budget_limit: Optional[float] = None
    deadline: Optional[datetime] = None


@dataclass
class TeamMember:
    """A persona assigned to a team with a specific role."""
    persona: PersonaInstance
    role: PersonaRole
    allocated_capacity: float
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class TeamComposition:
    """The composed team for a task."""
    team_id: str
    task_id: str
    members: List[TeamMember]
    created_at: datetime
    task_mapping: Dict[str, str] = field(default_factory=dict)
    shared_context: Dict[str, Any] = field(default_factory=dict)

    def add_member(self, member: TeamMember) -> None:
        """Add a member to the team."""
        self.members.append(member)

    def get_lead(self) -> Optional[TeamMember]:
        """Get the team lead."""
        for member in self.members:
            if member.role == PersonaRole.LEAD:
                return member
        return None

    def total_skill_coverage(self, required_skills: List[str]) -> float:
        """Calculate total skill coverage across team."""
        if not required_skills:
            return 1.0
        covered = set()
        for member in self.members:
            for skill in required_skills:
                if member.persona.has_skill(skill):
                    covered.add(skill)
        return len(covered) / len(required_skills)

    def share_context(self, key: str, value: Any) -> None:
        """Share context across team members."""
        self.shared_context[key] = value
        logger.info(f"Team {self.team_id}: Shared context '{key}' with {len(self.members)} members")


class TeamComposer:
    """
    Composes optimal teams for tasks based on requirements and constraints.

    Implements:
    - skill_matching: Match personas to required skills
    - dynamic_scaling: Adjust team size based on complexity
    - role_assignment: Assign appropriate roles to team members
    - context_sharing: Enable context propagation across team
    """

    def __init__(self, persona_pool: List[PersonaInstance]):
        """Initialize with available persona pool."""
        self.persona_pool = persona_pool
        self._active_teams: Dict[str, TeamComposition] = {}

    async def compose_team(
        self,
        task_requirements: TaskRequirements,
        constraints: Optional[TeamConstraints] = None
    ) -> TeamComposition:
        """
        Compose an optimal team for the given task.

        Args:
            task_requirements: The task that needs a team
            constraints: Optional constraints on team composition

        Returns:
            TeamComposition with assigned personas and roles
        """
        constraints = constraints or TeamConstraints()

        # Calculate target team size
        target_size = self._calculate_team_size(task_requirements, constraints)
        logger.info(f"Target team size for {task_requirements.task_id}: {target_size}")

        # Find matching personas using skill_matching
        candidates = self._skill_matching(
            task_requirements.required_skills,
            min_match_score=0.3
        )
        logger.info(f"Found {len(candidates)} skill-matched candidates")

        # Apply dynamic_scaling based on complexity
        scaled_candidates = self._dynamic_scaling(
            candidates,
            task_requirements.complexity,
            target_size
        )

        # Create team composition
        team = TeamComposition(
            team_id=str(uuid.uuid4()),
            task_id=task_requirements.task_id,
            members=[],
            created_at=datetime.utcnow()
        )

        # Apply role_assignment
        assigned = self._role_assignment(
            scaled_candidates[:target_size],
            task_requirements,
            constraints.required_roles
        )

        for persona, role, capacity in assigned:
            member = TeamMember(
                persona=persona,
                role=role,
                allocated_capacity=capacity
            )
            team.add_member(member)

            # Update persona load
            persona.current_load += capacity

        # Setup context_sharing
        team.share_context("task_requirements", {
            "id": task_requirements.task_id,
            "title": task_requirements.title,
            "complexity": task_requirements.complexity.value,
            "required_skills": task_requirements.required_skills
        })

        # Store active team
        self._active_teams[team.team_id] = team

        logger.info(
            f"Composed team {team.team_id} with {len(team.members)} members "
            f"for task {task_requirements.task_id}"
        )

        return team

    def _calculate_team_size(
        self,
        requirements: TaskRequirements,
        constraints: TeamConstraints
    ) -> int:
        """Calculate optimal team size."""
        base_size = requirements.min_team_size()

        # Adjust for required roles
        if constraints.required_roles:
            base_size = max(base_size, len(constraints.required_roles))

        # Apply constraints
        return max(
            constraints.min_team_size,
            min(constraints.max_team_size, base_size)
        )

    def _skill_matching(
        self,
        required_skills: List[str],
        min_match_score: float = 0.3
    ) -> List[PersonaInstance]:
        """
        Match personas to required skills.

        Returns personas sorted by skill match score.
        """
        scored_personas = []

        for persona in self.persona_pool:
            if persona.available_capacity() <= 0:
                continue

            score = persona.skill_score(required_skills)
            if score >= min_match_score:
                scored_personas.append((persona, score))

        # Sort by score descending
        scored_personas.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in scored_personas]

    def _dynamic_scaling(
        self,
        candidates: List[PersonaInstance],
        complexity: TaskComplexity,
        target_size: int
    ) -> List[PersonaInstance]:
        """
        Apply dynamic scaling based on task complexity.

        For higher complexity, prefer personas with more available capacity.
        """
        if complexity in (TaskComplexity.HIGH, TaskComplexity.CRITICAL):
            # For complex tasks, sort by available capacity
            candidates = sorted(
                candidates,
                key=lambda p: p.available_capacity(),
                reverse=True
            )

        return candidates[:target_size * 2]  # Return extra for flexibility

    def _role_assignment(
        self,
        personas: List[PersonaInstance],
        requirements: TaskRequirements,
        required_roles: List[PersonaRole]
    ) -> List[tuple]:
        """
        Assign roles to personas based on skills and requirements.

        Returns list of (persona, role, capacity) tuples.
        """
        assignments = []
        assigned_personas: Set[str] = set()

        # First, assign required roles
        roles_to_assign = list(required_roles) if required_roles else [PersonaRole.LEAD]

        for role in roles_to_assign:
            for persona in personas:
                if persona.persona_id in assigned_personas:
                    continue

                # Check if persona fits role
                if self._fits_role(persona, role):
                    capacity = min(0.5, persona.available_capacity())
                    assignments.append((persona, role, capacity))
                    assigned_personas.add(persona.persona_id)
                    break

        # Assign remaining personas as developers
        for persona in personas:
            if persona.persona_id not in assigned_personas:
                capacity = min(0.3, persona.available_capacity())
                assignments.append((persona, PersonaRole.DEVELOPER, capacity))
                assigned_personas.add(persona.persona_id)

        return assignments

    def _fits_role(self, persona: PersonaInstance, role: PersonaRole) -> bool:
        """Check if a persona fits a specific role."""
        role_skills = {
            PersonaRole.LEAD: ["leadership", "architecture", "planning"],
            PersonaRole.DEVELOPER: ["coding", "implementation", "python"],
            PersonaRole.REVIEWER: ["review", "quality", "standards"],
            PersonaRole.QA: ["testing", "automation", "quality"],
            PersonaRole.ARCHITECT: ["architecture", "design", "system"],
            PersonaRole.DOCUMENTOR: ["documentation", "writing", "technical"]
        }

        required = role_skills.get(role, [])
        return any(persona.has_skill(s) for s in required)

    def release_team(self, team_id: str) -> None:
        """Release a team and free up persona capacity."""
        team = self._active_teams.get(team_id)
        if not team:
            return

        for member in team.members:
            member.persona.current_load -= member.allocated_capacity
            member.persona.current_load = max(0, member.persona.current_load)

        del self._active_teams[team_id]
        logger.info(f"Released team {team_id}")

    def get_active_teams(self) -> Dict[str, TeamComposition]:
        """Get all active teams."""
        return self._active_teams.copy()

    def performance_tracking(self, team_id: str) -> Dict[str, Any]:
        """
        Track team performance metrics.

        Returns metrics about team utilization and skill coverage.
        """
        team = self._active_teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        return {
            "team_id": team_id,
            "member_count": len(team.members),
            "total_capacity_used": sum(m.allocated_capacity for m in team.members),
            "skill_coverage": team.total_skill_coverage(
                team.shared_context.get("task_requirements", {}).get("required_skills", [])
            ),
            "roles_filled": [m.role.value for m in team.members]
        }


# Factory function for creating default team composer
def create_team_composer(config: Optional[Dict[str, Any]] = None) -> TeamComposer:
    """Create a TeamComposer with default persona pool."""
    config = config or {}

    # Default personas
    default_personas = [
        PersonaInstance(
            persona_id="backend-1",
            name="Backend Engineer",
            skills=[
                Skill("python", 0.9),
                Skill("api", 0.85),
                Skill("database", 0.8),
                Skill("coding", 0.9),
                Skill("implementation", 0.85)
            ]
        ),
        PersonaInstance(
            persona_id="devops-1",
            name="DevOps Engineer",
            skills=[
                Skill("infrastructure", 0.9),
                Skill("ci/cd", 0.85),
                Skill("kubernetes", 0.8),
                Skill("architecture", 0.7)
            ]
        ),
        PersonaInstance(
            persona_id="qa-1",
            name="QA Engineer",
            skills=[
                Skill("testing", 0.9),
                Skill("automation", 0.85),
                Skill("quality", 0.9),
                Skill("review", 0.7)
            ]
        ),
        PersonaInstance(
            persona_id="architect-1",
            name="Solutions Architect",
            skills=[
                Skill("architecture", 0.95),
                Skill("design", 0.9),
                Skill("system", 0.85),
                Skill("leadership", 0.8),
                Skill("planning", 0.85)
            ]
        ),
        PersonaInstance(
            persona_id="tech-writer-1",
            name="Technical Writer",
            skills=[
                Skill("documentation", 0.95),
                Skill("writing", 0.9),
                Skill("technical", 0.85)
            ]
        )
    ]

    return TeamComposer(default_personas)
