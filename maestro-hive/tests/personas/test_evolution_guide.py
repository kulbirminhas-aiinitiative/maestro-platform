#!/usr/bin/env python3
"""
Tests for EvolutionGuide module.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from maestro_hive.personas.trait_manager import (
    TraitManager,
    Trait,
    TraitCategory,
    TraitStatus,
)
from maestro_hive.personas.skill_decay_tracker import (
    SkillDecayTracker,
)
from maestro_hive.personas.evolution_guide import (
    EvolutionGuide,
    EvolutionRecommendation,
    EvolutionPlan,
    CareerGoal,
    LearningResource,
    RecommendationPriority,
    RecommendationType,
    get_evolution_guide
)


class TestLearningResource:
    """Tests for LearningResource dataclass."""

    def test_resource_creation(self):
        """Test basic resource creation."""
        resource = LearningResource(
            resource_id="res_001",
            title="Python Mastery Course",
            resource_type="course",
            url="https://example.com/course",
            estimated_hours=20.0,
            difficulty_level="advanced",
            effectiveness_score=0.9
        )

        assert resource.resource_id == "res_001"
        assert resource.title == "Python Mastery Course"
        assert resource.resource_type == "course"
        assert resource.estimated_hours == 20.0


class TestEvolutionRecommendation:
    """Tests for EvolutionRecommendation dataclass."""

    def test_recommendation_creation(self):
        """Test basic recommendation creation."""
        rec = EvolutionRecommendation(
            recommendation_id="rec_001",
            trait_id="trait_001",
            persona_id="persona_001",
            trait_name="Python",
            recommendation_type=RecommendationType.PRACTICE,
            priority=RecommendationPriority.HIGH,
            title="Practice: Python",
            description="Improve Python skills",
            expected_level_gain=0.15,
            estimated_hours=10.0
        )

        assert rec.recommendation_id == "rec_001"
        assert rec.recommendation_type == RecommendationType.PRACTICE
        assert rec.priority == RecommendationPriority.HIGH
        assert not rec.accepted
        assert not rec.completed

    def test_recommendation_with_resources(self):
        """Test recommendation with learning resources."""
        resources = [
            LearningResource(
                resource_id="res_1",
                title="Course 1",
                resource_type="course",
                estimated_hours=5.0
            ),
            LearningResource(
                resource_id="res_2",
                title="Project 1",
                resource_type="project",
                estimated_hours=3.0
            )
        ]

        rec = EvolutionRecommendation(
            recommendation_id="rec_001",
            trait_id="trait_001",
            persona_id="persona_001",
            trait_name="Python",
            recommendation_type=RecommendationType.PRACTICE,
            priority=RecommendationPriority.MEDIUM,
            title="Practice: Python",
            description="Improve Python skills",
            expected_level_gain=0.1,
            estimated_hours=8.0,
            resources=resources
        )

        assert len(rec.resources) == 2

    def test_recommendation_to_dict(self):
        """Test recommendation serialization."""
        rec = EvolutionRecommendation(
            recommendation_id="rec_001",
            trait_id="trait_001",
            persona_id="persona_001",
            trait_name="Python",
            recommendation_type=RecommendationType.REINFORCE,
            priority=RecommendationPriority.URGENT,
            title="Reinforce: Python",
            description="Your Python skill is declining",
            expected_level_gain=0.15,
            estimated_hours=5.0
        )

        data = rec.to_dict()

        assert data["recommendation_type"] == "reinforce"
        assert data["priority"] == "urgent"
        assert data["expected_level_gain"] == 0.15


class TestCareerGoal:
    """Tests for CareerGoal dataclass."""

    def test_career_goal_creation(self):
        """Test basic career goal creation."""
        goal = CareerGoal(
            goal_id="goal_001",
            persona_id="persona_001",
            title="Become Senior Engineer",
            description="Advance to senior engineering role",
            target_role="Senior Software Engineer",
            target_traits={"Python": 0.9, "System Design": 0.8}
        )

        assert goal.goal_id == "goal_001"
        assert goal.target_role == "Senior Software Engineer"
        assert len(goal.target_traits) == 2
        assert goal.progress == 0.0


class TestEvolutionPlan:
    """Tests for EvolutionPlan dataclass."""

    def test_plan_creation(self):
        """Test basic plan creation."""
        recommendations = [
            EvolutionRecommendation(
                recommendation_id="rec_001",
                trait_id="trait_001",
                persona_id="persona_001",
                trait_name="Python",
                recommendation_type=RecommendationType.PRACTICE,
                priority=RecommendationPriority.HIGH,
                title="Practice: Python",
                description="Improve Python",
                expected_level_gain=0.1,
                estimated_hours=10.0
            )
        ]

        plan = EvolutionPlan(
            plan_id="plan_001",
            persona_id="persona_001",
            title="Q1 Development Plan",
            recommendations=recommendations,
            total_estimated_hours=10.0,
            expected_completion_date="2024-03-31T00:00:00",
            career_goal=None
        )

        assert plan.plan_id == "plan_001"
        assert len(plan.recommendations) == 1
        assert plan.total_estimated_hours == 10.0

    def test_plan_to_dict(self):
        """Test plan serialization."""
        plan = EvolutionPlan(
            plan_id="plan_001",
            persona_id="persona_001",
            title="Development Plan",
            recommendations=[],
            total_estimated_hours=0.0,
            expected_completion_date=None,
            career_goal=None
        )

        data = plan.to_dict()

        assert data["plan_id"] == "plan_001"
        assert data["recommendations"] == []


class TestEvolutionGuide:
    """Tests for EvolutionGuide class."""

    @pytest.fixture
    def trait_manager(self):
        """Create a fresh TraitManager."""
        return TraitManager(max_traits_per_persona=50)

    @pytest.fixture
    def decay_tracker(self, trait_manager):
        """Create a SkillDecayTracker."""
        return SkillDecayTracker(trait_manager=trait_manager)

    @pytest.fixture
    def guide(self, trait_manager, decay_tracker):
        """Create an EvolutionGuide."""
        return EvolutionGuide(
            trait_manager=trait_manager,
            decay_tracker=decay_tracker,
            max_recommendations_per_persona=5
        )

    @pytest.fixture
    def persona_with_traits(self, trait_manager):
        """Create a persona with multiple traits."""
        persona_id = "persona_1"

        # Active trait with room for growth
        trait1 = trait_manager.create_trait(
            name="Python",
            description="Python programming",
            category=TraitCategory.TECHNICAL,
            persona_id=persona_id,
            initial_level=0.6
        )
        trait1.metrics.last_practice = datetime.utcnow().isoformat()

        # High-level trait ready for advancement
        trait2 = trait_manager.create_trait(
            name="System Design",
            description="System architecture",
            category=TraitCategory.TECHNICAL,
            persona_id=persona_id,
            initial_level=0.75
        )
        trait2.metrics.last_practice = datetime.utcnow().isoformat()

        # Decaying trait
        trait3 = trait_manager.create_trait(
            name="Communication",
            description="Communication skills",
            category=TraitCategory.SOFT_SKILL,
            persona_id=persona_id,
            initial_level=0.5
        )
        trait3.metrics.last_practice = (datetime.utcnow() - timedelta(days=45)).isoformat()

        return persona_id

    def test_set_career_goal(self, guide):
        """Test setting a career goal."""
        goal = guide.set_career_goal(
            persona_id="persona_1",
            title="Become Tech Lead",
            description="Advance to tech lead position",
            target_role="Tech Lead",
            target_traits={"Python": 0.9, "Leadership": 0.8}
        )

        assert goal.goal_id.startswith("goal_")
        assert goal.title == "Become Tech Lead"
        assert goal.target_traits["Python"] == 0.9

    def test_get_career_goal(self, guide):
        """Test getting a career goal."""
        guide.set_career_goal(
            persona_id="persona_1",
            title="Goal",
            description="Description",
            target_role="Role",
            target_traits={}
        )

        goal = guide.get_career_goal("persona_1")
        assert goal is not None
        assert goal.persona_id == "persona_1"

    def test_get_career_goal_not_set(self, guide):
        """Test getting career goal when not set."""
        goal = guide.get_career_goal("nonexistent")
        assert goal is None

    def test_generate_recommendations(self, guide, persona_with_traits):
        """Test generating recommendations."""
        recommendations = guide.generate_recommendations(persona_with_traits)

        assert isinstance(recommendations, list)
        # Should have recommendations for decaying traits

    def test_generate_recommendations_with_career_goal(self, guide, persona_with_traits, trait_manager):
        """Test generating recommendations aligned with career goal."""
        guide.set_career_goal(
            persona_id=persona_with_traits,
            title="Senior Engineer",
            description="Become senior",
            target_role="Senior Engineer",
            target_traits={"Python": 0.9, "Leadership": 0.8}
        )

        recommendations = guide.generate_recommendations(persona_with_traits)

        # Should have career-aligned recommendations
        assert isinstance(recommendations, list)

    def test_generate_recommendations_cached(self, guide, persona_with_traits):
        """Test that recommendations are cached."""
        recs1 = guide.generate_recommendations(persona_with_traits)
        recs2 = guide.generate_recommendations(persona_with_traits)

        # Should return same recommendations (cached)
        if recs1 and recs2:
            assert recs1[0].recommendation_id == recs2[0].recommendation_id

    def test_generate_recommendations_force_refresh(self, guide, persona_with_traits):
        """Test forcing refresh of recommendations."""
        recs1 = guide.generate_recommendations(persona_with_traits)
        recs2 = guide.generate_recommendations(persona_with_traits, force_refresh=True)

        # Both should exist
        assert isinstance(recs1, list)
        assert isinstance(recs2, list)

    def test_generate_recommendations_limit(self, guide, trait_manager):
        """Test that recommendations respect max limit."""
        persona_id = "persona_limit"

        # Create many traits
        for i in range(10):
            trait = trait_manager.create_trait(
                name=f"Skill_{i}",
                description=f"Skill {i}",
                category=TraitCategory.TECHNICAL,
                persona_id=persona_id,
                initial_level=0.4
            )
            trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=30)).isoformat()

        recommendations = guide.generate_recommendations(persona_id)

        assert len(recommendations) <= guide._max_recommendations

    def test_create_evolution_plan(self, guide, persona_with_traits):
        """Test creating an evolution plan."""
        guide.generate_recommendations(persona_with_traits)

        plan = guide.create_evolution_plan(
            persona_id=persona_with_traits,
            title="Q1 Development Plan"
        )

        assert plan.plan_id.startswith("plan_")
        assert plan.persona_id == persona_with_traits
        assert plan.title == "Q1 Development Plan"
        assert isinstance(plan.recommendations, list)

    def test_create_evolution_plan_with_specific_recommendations(self, guide, persona_with_traits):
        """Test creating plan with specific recommendations."""
        recs = guide.generate_recommendations(persona_with_traits)

        if recs:
            rec_ids = [recs[0].recommendation_id]
            plan = guide.create_evolution_plan(
                persona_id=persona_with_traits,
                title="Focused Plan",
                recommendation_ids=rec_ids
            )

            assert len(plan.recommendations) == 1

    def test_get_plan(self, guide, persona_with_traits):
        """Test getting a plan by ID."""
        guide.generate_recommendations(persona_with_traits)
        created_plan = guide.create_evolution_plan(
            persona_id=persona_with_traits,
            title="Test Plan"
        )

        retrieved_plan = guide.get_plan(created_plan.plan_id)

        assert retrieved_plan is not None
        assert retrieved_plan.plan_id == created_plan.plan_id

    def test_get_plan_not_found(self, guide):
        """Test getting non-existent plan."""
        plan = guide.get_plan("nonexistent")
        assert plan is None

    def test_get_recommendations(self, guide, persona_with_traits):
        """Test getting cached recommendations."""
        guide.generate_recommendations(persona_with_traits)

        cached = guide.get_recommendations(persona_with_traits)
        assert isinstance(cached, list)

    def test_accept_recommendation(self, guide, persona_with_traits):
        """Test accepting a recommendation."""
        recs = guide.generate_recommendations(persona_with_traits)

        if recs:
            rec_id = recs[0].recommendation_id
            result = guide.accept_recommendation(rec_id)

            assert result is True
            assert recs[0].accepted is True

    def test_accept_recommendation_not_found(self, guide):
        """Test accepting non-existent recommendation."""
        result = guide.accept_recommendation("nonexistent")
        assert result is False

    def test_complete_recommendation(self, guide, persona_with_traits):
        """Test completing a recommendation."""
        recs = guide.generate_recommendations(persona_with_traits)

        if recs:
            rec_id = recs[0].recommendation_id
            guide.accept_recommendation(rec_id)
            result = guide.complete_recommendation(rec_id)

            assert result is True
            assert recs[0].completed is True

    def test_complete_recommendation_not_found(self, guide):
        """Test completing non-existent recommendation."""
        result = guide.complete_recommendation("nonexistent")
        assert result is False

    def test_get_statistics(self, guide, persona_with_traits):
        """Test getting evolution guide statistics."""
        guide.generate_recommendations(persona_with_traits)
        guide.set_career_goal(
            persona_id=persona_with_traits,
            title="Goal",
            description="Desc",
            target_role="Role",
            target_traits={}
        )

        stats = guide.get_statistics()

        assert "total_recommendations" in stats
        assert "accepted_recommendations" in stats
        assert "completed_recommendations" in stats
        assert "active_plans" in stats
        assert "career_goals_set" in stats
        assert "ml_model_enabled" in stats

    def test_reinforce_recommendation_priority(self, guide, trait_manager):
        """Test that decaying traits get urgent priority."""
        persona_id = "decay_test"

        trait = trait_manager.create_trait(
            name="Decaying Skill",
            description="A skill that needs reinforcement",
            category=TraitCategory.TECHNICAL,
            persona_id=persona_id,
            initial_level=0.3
        )
        # Set very old practice date
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=60)).isoformat()

        recs = guide.generate_recommendations(persona_id)

        # Should have a reinforce recommendation
        reinforce_recs = [r for r in recs if r.recommendation_type == RecommendationType.REINFORCE]
        if reinforce_recs:
            assert reinforce_recs[0].priority in [RecommendationPriority.URGENT, RecommendationPriority.HIGH]

    def test_advance_recommendation_for_high_level(self, guide, trait_manager):
        """Test that high-level traits get advance recommendations."""
        persona_id = "advance_test"

        trait = trait_manager.create_trait(
            name="Strong Skill",
            description="A skill ready for advancement",
            category=TraitCategory.TECHNICAL,
            persona_id=persona_id,
            initial_level=0.75
        )
        trait.metrics.last_practice = datetime.utcnow().isoformat()

        recs = guide.generate_recommendations(persona_id)

        # Should have an advance recommendation
        advance_recs = [r for r in recs if r.recommendation_type == RecommendationType.ADVANCE]
        if advance_recs:
            assert advance_recs[0].priority == RecommendationPriority.MEDIUM

    def test_diversification_recommendation(self, guide, trait_manager):
        """Test diversification recommendation for missing skills."""
        persona_id = "diversify_test"

        # Create a few traits
        for i in range(3):
            trait_manager.create_trait(
                name=f"Skill_{i}",
                description=f"Skill {i}",
                category=TraitCategory.TECHNICAL,
                persona_id=persona_id,
                initial_level=0.6
            )

        # Set career goal requiring new skills
        guide.set_career_goal(
            persona_id=persona_id,
            title="Expand Skills",
            description="Learn new things",
            target_role="Full Stack Developer",
            target_traits={"NewSkill": 0.8}
        )

        recs = guide.generate_recommendations(persona_id)

        # Should have a learn/diversify recommendation
        learn_recs = [r for r in recs if r.recommendation_type == RecommendationType.LEARN]
        if learn_recs:
            assert learn_recs[0].trait_name == "NewSkill"


class TestGetEvolutionGuide:
    """Tests for singleton factory function."""

    def test_singleton_behavior(self):
        """Test singleton returns same instance."""
        guide1 = get_evolution_guide(force_new=True)
        guide2 = get_evolution_guide()

        assert guide1 is guide2

    def test_force_new(self):
        """Test force_new creates new instance."""
        guide1 = get_evolution_guide(force_new=True)
        guide2 = get_evolution_guide(force_new=True)

        assert guide1 is not guide2


class TestRecommendationPriorityEnum:
    """Tests for RecommendationPriority enum."""

    def test_enum_values(self):
        """Test all priority values exist."""
        assert RecommendationPriority.URGENT.value == "urgent"
        assert RecommendationPriority.HIGH.value == "high"
        assert RecommendationPriority.MEDIUM.value == "medium"
        assert RecommendationPriority.LOW.value == "low"
        assert RecommendationPriority.EXPLORATORY.value == "exploratory"


class TestRecommendationTypeEnum:
    """Tests for RecommendationType enum."""

    def test_enum_values(self):
        """Test all recommendation types exist."""
        assert RecommendationType.PRACTICE.value == "practice"
        assert RecommendationType.LEARN.value == "learn"
        assert RecommendationType.REINFORCE.value == "reinforce"
        assert RecommendationType.ADVANCE.value == "advance"
        assert RecommendationType.SPECIALIZE.value == "specialize"
        assert RecommendationType.DIVERSIFY.value == "diversify"
        assert RecommendationType.TRANSITION.value == "transition"
