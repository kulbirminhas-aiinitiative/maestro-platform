#!/usr/bin/env python3
"""Tests for TeamComposer module."""

import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.personas.team_composer import (
    TeamComposer,
    TeamComposition,
    TaskRequirements,
    TaskComplexity,
    PersonaInstance,
    PersonaRole,
    TeamMember,
    TeamConstraints,
    Skill,
    create_team_composer
)


class TestSkill:
    """Tests for Skill dataclass."""

    def test_skill_creation(self):
        """Test creating a Skill."""
        skill = Skill(name="Python", proficiency=0.8)
        assert skill.name == "Python"
        assert skill.proficiency == 0.8

    def test_skill_matches(self):
        """Test skill matching with proficiency threshold."""
        skill = Skill(name="Python", proficiency=0.8)

        assert skill.matches("python") is True  # Case insensitive
        assert skill.matches("Python", min_proficiency=0.7) is True
        assert skill.matches("Python", min_proficiency=0.9) is False
        assert skill.matches("Java") is False


class TestPersonaInstance:
    """Tests for PersonaInstance dataclass."""

    def test_persona_instance_creation(self):
        """Test creating a PersonaInstance."""
        skills = [Skill(name="Python", proficiency=0.9)]
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=skills
        )

        assert persona.persona_id == "dev_001"
        assert persona.name == "Developer"
        assert len(persona.skills) == 1

    def test_available_capacity(self):
        """Test capacity calculation."""
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=[],
            current_load=0.3
        )

        assert persona.available_capacity() == 0.7

    def test_has_skill(self):
        """Test skill checking."""
        skills = [
            Skill(name="Python", proficiency=0.9),
            Skill(name="JavaScript", proficiency=0.6)
        ]
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=skills
        )

        assert persona.has_skill("Python") is True
        assert persona.has_skill("Python", min_proficiency=0.8) is True
        assert persona.has_skill("Python", min_proficiency=0.95) is False
        assert persona.has_skill("Java") is False

    def test_skill_score(self):
        """Test skill score calculation."""
        skills = [
            Skill(name="Python", proficiency=0.8),
            Skill(name="JavaScript", proficiency=0.6)
        ]
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=skills
        )

        # Score for skills we have (both match)
        score = persona.skill_score(["Python", "JavaScript"])
        assert score == 1.0

        # Score includes missing skill
        score_with_missing = persona.skill_score(["Python", "Java"])
        assert score_with_missing == 0.5


class TestTeamMember:
    """Tests for TeamMember dataclass."""

    def test_team_member_creation(self):
        """Test creating a TeamMember."""
        skills = [Skill(name="Python", proficiency=0.9)]
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=skills
        )
        member = TeamMember(
            persona=persona,
            role=PersonaRole.DEVELOPER,
            allocated_capacity=0.5
        )

        assert member.persona.persona_id == "dev_001"
        assert member.role == PersonaRole.DEVELOPER
        assert member.allocated_capacity == 0.5


class TestTaskRequirements:
    """Tests for TaskRequirements dataclass."""

    def test_task_requirements_creation(self):
        """Test creating TaskRequirements."""
        req = TaskRequirements(
            task_id="task_001",
            title="Build API",
            complexity=TaskComplexity.HIGH,
            required_skills=["Python", "Docker"],
            estimated_effort_hours=40.0,
            priority=8
        )

        assert len(req.required_skills) == 2
        assert req.complexity == TaskComplexity.HIGH
        assert req.priority == 8

    def test_min_team_size(self):
        """Test minimum team size calculation."""
        # Low complexity = smaller team
        req_low = TaskRequirements(
            task_id="task_001",
            title="Simple Fix",
            complexity=TaskComplexity.LOW,
            required_skills=["Python"],
            estimated_effort_hours=4.0
        )
        assert req_low.min_team_size() == 1

        # High complexity = larger team
        req_high = TaskRequirements(
            task_id="task_002",
            title="Major Feature",
            complexity=TaskComplexity.HIGH,
            required_skills=["Python", "Docker", "Kubernetes", "AWS"],
            estimated_effort_hours=80.0
        )
        assert req_high.min_team_size() == 3


class TestTeamConstraints:
    """Tests for TeamConstraints dataclass."""

    def test_team_constraints_creation(self):
        """Test creating TeamConstraints."""
        constraints = TeamConstraints(
            max_team_size=5,
            min_team_size=2,
            required_roles=[PersonaRole.LEAD, PersonaRole.DEVELOPER]
        )

        assert constraints.max_team_size == 5
        assert constraints.min_team_size == 2
        assert len(constraints.required_roles) == 2


class TestTeamComposition:
    """Tests for TeamComposition dataclass."""

    def test_team_composition_creation(self):
        """Test creating a TeamComposition."""
        team = TeamComposition(
            team_id="team_001",
            task_id="task_001",
            members=[],
            created_at=datetime.now()
        )

        assert team.team_id == "team_001"
        assert team.task_id == "task_001"
        assert len(team.members) == 0

    def test_add_member(self):
        """Test adding members to team."""
        team = TeamComposition(
            team_id="team_001",
            task_id="task_001",
            members=[],
            created_at=datetime.now()
        )

        skills = [Skill(name="Python", proficiency=0.9)]
        persona = PersonaInstance(
            persona_id="dev_001",
            name="Developer",
            skills=skills
        )
        member = TeamMember(
            persona=persona,
            role=PersonaRole.DEVELOPER,
            allocated_capacity=0.5
        )

        team.add_member(member)
        assert len(team.members) == 1

    def test_share_context(self):
        """Test context sharing."""
        team = TeamComposition(
            team_id="team_001",
            task_id="task_001",
            members=[],
            created_at=datetime.now()
        )

        team.share_context("project", "MaestroHive")
        assert team.shared_context["project"] == "MaestroHive"


class TestTeamComposer:
    """Tests for TeamComposer class."""

    @pytest.fixture
    def persona_pool(self):
        """Create a test persona pool."""
        return [
            PersonaInstance(
                persona_id="architect_001",
                name="Architect",
                skills=[
                    Skill(name="system_design", proficiency=0.95),
                    Skill(name="python", proficiency=0.8)
                ]
            ),
            PersonaInstance(
                persona_id="dev_001",
                name="Senior Developer",
                skills=[
                    Skill(name="python", proficiency=0.9),
                    Skill(name="testing", proficiency=0.8)
                ]
            ),
            PersonaInstance(
                persona_id="dev_002",
                name="Junior Developer",
                skills=[
                    Skill(name="python", proficiency=0.6),
                    Skill(name="javascript", proficiency=0.7)
                ]
            ),
            PersonaInstance(
                persona_id="qa_001",
                name="QA Engineer",
                skills=[
                    Skill(name="testing", proficiency=0.95),
                    Skill(name="automation", proficiency=0.8)
                ]
            )
        ]

    @pytest.fixture
    def composer(self, persona_pool):
        """Create a TeamComposer with test pool."""
        return TeamComposer(persona_pool)

    @pytest.mark.asyncio
    async def test_compose_team(self, composer):
        """Test composing a team for requirements."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.MEDIUM,
            required_skills=["python", "testing"],
            estimated_effort_hours=24.0
        )

        team = await composer.compose_team(requirements)

        assert team is not None
        assert len(team.members) >= 1
        assert team.team_id is not None
        assert team.task_id == "task_001"

    @pytest.mark.asyncio
    async def test_compose_team_with_constraints(self, composer):
        """Test composing team with constraints."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.HIGH,
            required_skills=["python"],
            estimated_effort_hours=40.0
        )
        constraints = TeamConstraints(
            max_team_size=3,
            min_team_size=2
        )

        team = await composer.compose_team(requirements, constraints)

        assert team is not None
        assert len(team.members) >= constraints.min_team_size
        assert len(team.members) <= constraints.max_team_size

    def test_skill_matching(self, composer):
        """Test skill matching."""
        matches = composer._skill_matching(
            required_skills=["python"],
            min_match_score=0.5
        )

        # Should find personas with python skill
        assert len(matches) >= 2

    def test_calculate_team_size(self, composer):
        """Test team size calculation."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.HIGH,
            required_skills=["python", "testing", "docker"],
            estimated_effort_hours=60.0
        )
        constraints = TeamConstraints(max_team_size=5, min_team_size=1)

        size = composer._calculate_team_size(requirements, constraints)
        assert size >= requirements.min_team_size()
        assert size <= constraints.max_team_size

    def test_role_assignment(self, composer, persona_pool):
        """Test role assignment to personas."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.MEDIUM,
            required_skills=["python"],
            estimated_effort_hours=24.0
        )

        assignments = composer._role_assignment(
            persona_pool[:2],
            requirements,
            [PersonaRole.LEAD]
        )
        assert len(assignments) >= 1

    @pytest.mark.asyncio
    async def test_team_stored_in_active_teams(self, composer):
        """Test that composed team is stored in active teams."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.LOW,
            required_skills=["python"],
            estimated_effort_hours=8.0
        )

        team = await composer.compose_team(requirements)
        active_teams = composer.get_active_teams()

        assert team.team_id in active_teams
        assert active_teams[team.team_id].team_id == team.team_id

    @pytest.mark.asyncio
    async def test_release_team(self, composer):
        """Test releasing a team."""
        requirements = TaskRequirements(
            task_id="task_001",
            title="Build Feature",
            complexity=TaskComplexity.LOW,
            required_skills=["python"],
            estimated_effort_hours=8.0
        )

        team = await composer.compose_team(requirements)
        composer.release_team(team.team_id)

        # Team should be released - no longer in active teams
        active_teams = composer.get_active_teams()
        assert team.team_id not in active_teams

    @pytest.mark.asyncio
    async def test_get_active_teams(self, composer):
        """Test getting all active teams."""
        # Create a couple teams
        for i in range(2):
            requirements = TaskRequirements(
                task_id=f"task_{i}",
                title=f"Feature {i}",
                complexity=TaskComplexity.LOW,
                required_skills=["python"],
                estimated_effort_hours=8.0
            )
            await composer.compose_team(requirements)

        active = composer.get_active_teams()
        assert len(active) >= 2

    def test_dynamic_scaling(self, composer, persona_pool):
        """Test dynamic scaling of candidates."""
        scaled = composer._dynamic_scaling(
            persona_pool,
            TaskComplexity.HIGH,
            target_size=2
        )

        # Should return scaled list
        assert len(scaled) <= len(persona_pool) * 2


class TestCreateTeamComposer:
    """Tests for factory function."""

    def test_create_team_composer_default(self):
        """Test creating composer with defaults."""
        composer = create_team_composer()

        assert composer is not None
        assert isinstance(composer, TeamComposer)

    def test_create_team_composer_with_config(self):
        """Test creating composer with config."""
        config = {
            "max_team_size": 10,
            "min_proficiency": 0.6
        }

        composer = create_team_composer(config)

        assert composer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
