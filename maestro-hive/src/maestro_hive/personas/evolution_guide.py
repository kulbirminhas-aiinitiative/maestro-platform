#!/usr/bin/env python3
"""
Evolution Guide: Intelligent trait improvement recommendations.

This module provides ML-powered and rule-based recommendations for
persona trait evolution, suggesting optimal learning paths and
prioritizing skill development based on career goals and decay urgency.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
"""

import json
import logging
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import random

from .trait_manager import (
    TraitManager,
    Trait,
    TraitCategory,
    TraitStatus,
    get_trait_manager
)
from .skill_decay_tracker import (
    SkillDecayTracker,
    DecayCalculationResult,
    get_skill_decay_tracker
)

logger = logging.getLogger(__name__)


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""
    URGENT = "urgent"      # Address immediately (decay critical)
    HIGH = "high"          # Address soon (career impact)
    MEDIUM = "medium"      # Scheduled improvement
    LOW = "low"            # Nice to have
    EXPLORATORY = "exploratory"  # New skill exploration


class RecommendationType(Enum):
    """Types of evolution recommendations."""
    PRACTICE = "practice"           # Practice existing skill
    LEARN = "learn"                 # Learn new skill
    REINFORCE = "reinforce"         # Reinforce decaying skill
    ADVANCE = "advance"             # Advance to next level
    SPECIALIZE = "specialize"       # Deep specialization
    DIVERSIFY = "diversify"         # Broaden skill set
    TRANSITION = "transition"       # Career transition support


@dataclass
class LearningResource:
    """A learning resource for skill development."""
    resource_id: str
    title: str
    resource_type: str  # "course", "book", "project", "mentorship"
    url: Optional[str] = None
    estimated_hours: float = 0.0
    difficulty_level: str = "intermediate"
    effectiveness_score: float = 0.7


@dataclass
class EvolutionRecommendation:
    """A recommendation for trait evolution."""
    recommendation_id: str
    trait_id: str
    persona_id: Optional[str]
    trait_name: str
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    expected_level_gain: float
    estimated_hours: float
    resources: List[LearningResource] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)  # trait_ids
    rationale: str = ""
    confidence_score: float = 0.8  # ML model confidence
    generated_by: str = "rules"  # "ml" or "rules"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    accepted: bool = False
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            **asdict(self),
            "recommendation_type": self.recommendation_type.value,
            "priority": self.priority.value,
            "resources": [asdict(r) for r in self.resources]
        }


@dataclass
class CareerGoal:
    """A career goal for guiding recommendations."""
    goal_id: str
    persona_id: str
    title: str
    description: str
    target_role: str
    target_traits: Dict[str, float]  # trait_name -> target_level
    deadline: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0


@dataclass
class EvolutionPlan:
    """A comprehensive evolution plan for a persona."""
    plan_id: str
    persona_id: str
    title: str
    recommendations: List[EvolutionRecommendation]
    total_estimated_hours: float
    expected_completion_date: Optional[str]
    career_goal: Optional[CareerGoal]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "plan_id": self.plan_id,
            "persona_id": self.persona_id,
            "title": self.title,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_estimated_hours": self.total_estimated_hours,
            "expected_completion_date": self.expected_completion_date,
            "career_goal": asdict(self.career_goal) if self.career_goal else None,
            "created_at": self.created_at
        }


class MLModelInterface:
    """
    Interface for ML model integration.

    This is a placeholder that can be replaced with actual ML model
    when available. Currently uses rule-based fallback.
    """

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path
        self.model_loaded = False
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load ML model."""
        if self.model_path and self.model_path.exists():
            try:
                # Placeholder for actual model loading
                # In production: self.model = joblib.load(model_path)
                logger.info(f"ML model loaded from {self.model_path}")
                self.model_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}")
                self.model_loaded = False
        else:
            logger.info("No ML model path configured, using rule-based recommendations")

    def predict_recommendations(
        self,
        traits: List[Trait],
        decay_results: List[DecayCalculationResult],
        career_goal: Optional[CareerGoal]
    ) -> List[Dict[str, Any]]:
        """
        Predict recommendations using ML model.

        Returns empty list if model not loaded (falls back to rules).
        """
        if not self.model_loaded:
            return []

        # Placeholder for actual ML inference
        # In production: return self.model.predict(features)
        return []


class EvolutionGuide:
    """
    Provides intelligent recommendations for trait evolution.

    Combines ML predictions with rule-based logic to suggest
    optimal learning paths for persona development.
    """

    # Priority weights for recommendation scoring
    DEFAULT_WEIGHTS = {
        "decay_urgency": 0.4,
        "career_alignment": 0.3,
        "effort_efficiency": 0.3
    }

    def __init__(
        self,
        trait_manager: Optional[TraitManager] = None,
        decay_tracker: Optional[SkillDecayTracker] = None,
        ml_model_path: Optional[Path] = None,
        max_recommendations_per_persona: int = 5,
        priority_weights: Optional[Dict[str, float]] = None,
        persistence_path: Optional[Path] = None
    ):
        """
        Initialize the EvolutionGuide.

        Args:
            trait_manager: TraitManager instance
            decay_tracker: SkillDecayTracker instance
            ml_model_path: Path to ML model file
            max_recommendations_per_persona: Max recommendations to generate
            priority_weights: Weights for priority scoring
            persistence_path: Path for persistence
        """
        self._trait_manager = trait_manager or get_trait_manager()
        self._decay_tracker = decay_tracker or get_skill_decay_tracker()
        self._ml_model = MLModelInterface(ml_model_path)
        self._max_recommendations = max_recommendations_per_persona
        self._weights = priority_weights or self.DEFAULT_WEIGHTS.copy()
        self._persistence_path = persistence_path

        self._recommendations: Dict[str, List[EvolutionRecommendation]] = {}  # persona_id -> recs
        self._career_goals: Dict[str, CareerGoal] = {}  # persona_id -> goal
        self._plans: Dict[str, EvolutionPlan] = {}  # plan_id -> plan
        self._lock = threading.RLock()
        self._recommendation_counter = 0

        # Load persisted state
        if persistence_path and persistence_path.exists():
            self._load_state()

        logger.info(
            f"EvolutionGuide initialized: max_recs={max_recommendations_per_persona}, "
            f"ml_enabled={self._ml_model.model_loaded}"
        )

    def set_career_goal(
        self,
        persona_id: str,
        title: str,
        description: str,
        target_role: str,
        target_traits: Dict[str, float],
        deadline: Optional[str] = None
    ) -> CareerGoal:
        """Set a career goal for a persona."""
        goal_id = f"goal_{hashlib.md5(f'{persona_id}_{title}'.encode()).hexdigest()[:12]}"

        goal = CareerGoal(
            goal_id=goal_id,
            persona_id=persona_id,
            title=title,
            description=description,
            target_role=target_role,
            target_traits=target_traits,
            deadline=deadline,
            progress=0.0
        )

        self._career_goals[persona_id] = goal
        self._save_state()

        logger.info(f"Career goal set for persona {persona_id}: {title}")
        return goal

    def get_career_goal(self, persona_id: str) -> Optional[CareerGoal]:
        """Get the career goal for a persona."""
        return self._career_goals.get(persona_id)

    def generate_recommendations(
        self,
        persona_id: str,
        force_refresh: bool = False
    ) -> List[EvolutionRecommendation]:
        """
        Generate evolution recommendations for a persona.

        Args:
            persona_id: The persona to generate recommendations for
            force_refresh: Force regeneration of recommendations

        Returns:
            List of EvolutionRecommendation objects
        """
        with self._lock:
            # Check if we have cached recommendations
            if not force_refresh and persona_id in self._recommendations:
                cached = self._recommendations[persona_id]
                # Return if not expired
                if cached and cached[0].expires_at:
                    expiry = datetime.fromisoformat(cached[0].expires_at)
                    if datetime.utcnow() < expiry:
                        return cached

            # Get persona traits and decay information
            traits = self._trait_manager.get_traits_by_persona(persona_id)
            if not traits:
                return []

            # Run decay calculation
            decay_results = self._decay_tracker.run_decay_calculation(persona_id)
            decay_map = {r.trait_id: r for r in decay_results}

            # Get career goal
            career_goal = self._career_goals.get(persona_id)

            # Try ML model first
            ml_recs = self._ml_model.predict_recommendations(
                traits, decay_results, career_goal
            )

            if ml_recs:
                recommendations = self._process_ml_recommendations(ml_recs, persona_id)
            else:
                # Fall back to rule-based recommendations
                recommendations = self._generate_rule_based_recommendations(
                    persona_id, traits, decay_map, career_goal
                )

            # Limit and cache
            recommendations = recommendations[:self._max_recommendations]
            self._recommendations[persona_id] = recommendations
            self._save_state()

            logger.info(
                f"Generated {len(recommendations)} recommendations for persona {persona_id} "
                f"(method: {'ml' if ml_recs else 'rules'})"
            )

            return recommendations

    def _generate_rule_based_recommendations(
        self,
        persona_id: str,
        traits: List[Trait],
        decay_map: Dict[str, DecayCalculationResult],
        career_goal: Optional[CareerGoal]
    ) -> List[EvolutionRecommendation]:
        """Generate recommendations using rule-based logic."""
        recommendations = []

        for trait in traits:
            rec = self._evaluate_trait_for_recommendation(
                trait, decay_map.get(trait.id), career_goal
            )
            if rec:
                recommendations.append(rec)

        # Add diversification recommendations if needed
        if len(traits) < 10 and career_goal:
            div_rec = self._generate_diversification_recommendation(
                persona_id, traits, career_goal
            )
            if div_rec:
                recommendations.append(div_rec)

        # Sort by priority score
        recommendations.sort(
            key=lambda r: self._calculate_priority_score(r),
            reverse=True
        )

        return recommendations

    def _evaluate_trait_for_recommendation(
        self,
        trait: Trait,
        decay_result: Optional[DecayCalculationResult],
        career_goal: Optional[CareerGoal]
    ) -> Optional[EvolutionRecommendation]:
        """Evaluate a single trait for recommendation."""
        self._recommendation_counter += 1
        rec_id = f"rec_{self._recommendation_counter}"

        # Check for decay urgency
        if decay_result and decay_result.alert_generated:
            return self._create_reinforce_recommendation(
                rec_id, trait, decay_result, career_goal
            )

        # Check for advancement opportunity
        if trait.level >= 0.7 and trait.status == TraitStatus.ACTIVE:
            return self._create_advance_recommendation(
                rec_id, trait, career_goal
            )

        # Check for career alignment
        if career_goal and trait.name in career_goal.target_traits:
            target = career_goal.target_traits[trait.name]
            if trait.level < target:
                return self._create_career_aligned_recommendation(
                    rec_id, trait, target, career_goal
                )

        return None

    def _create_reinforce_recommendation(
        self,
        rec_id: str,
        trait: Trait,
        decay_result: DecayCalculationResult,
        career_goal: Optional[CareerGoal]
    ) -> EvolutionRecommendation:
        """Create a reinforcement recommendation for decaying skill."""
        priority = RecommendationPriority.URGENT if decay_result.decayed_level < 0.2 else RecommendationPriority.HIGH

        return EvolutionRecommendation(
            recommendation_id=rec_id,
            trait_id=trait.id,
            persona_id=trait.persona_id,
            trait_name=trait.name,
            recommendation_type=RecommendationType.REINFORCE,
            priority=priority,
            title=f"Reinforce: {trait.name}",
            description=f"Your {trait.name} skill is declining. Practice to maintain proficiency.",
            expected_level_gain=0.15,
            estimated_hours=5.0,
            rationale=f"Skill has decayed by {decay_result.decay_amount:.1%} over {decay_result.days_since_practice:.0f} days",
            confidence_score=0.9,
            generated_by="rules",
            expires_at=(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) +
                       __import__('datetime').timedelta(days=7)).isoformat(),
            resources=[
                LearningResource(
                    resource_id=f"res_{rec_id}_1",
                    title=f"{trait.name} Practice Exercises",
                    resource_type="project",
                    estimated_hours=3.0
                ),
                LearningResource(
                    resource_id=f"res_{rec_id}_2",
                    title=f"{trait.name} Review Course",
                    resource_type="course",
                    estimated_hours=2.0
                )
            ]
        )

    def _create_advance_recommendation(
        self,
        rec_id: str,
        trait: Trait,
        career_goal: Optional[CareerGoal]
    ) -> EvolutionRecommendation:
        """Create an advancement recommendation."""
        return EvolutionRecommendation(
            recommendation_id=rec_id,
            trait_id=trait.id,
            persona_id=trait.persona_id,
            trait_name=trait.name,
            recommendation_type=RecommendationType.ADVANCE,
            priority=RecommendationPriority.MEDIUM,
            title=f"Advance: {trait.name}",
            description=f"You're ready to advance your {trait.name} skill to expert level.",
            expected_level_gain=0.2,
            estimated_hours=15.0,
            rationale="Strong foundation in place, ready for advanced concepts",
            confidence_score=0.85,
            generated_by="rules",
            expires_at=(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) +
                       __import__('datetime').timedelta(days=14)).isoformat(),
            resources=[
                LearningResource(
                    resource_id=f"res_{rec_id}_1",
                    title=f"Advanced {trait.name} Mastery",
                    resource_type="course",
                    estimated_hours=10.0,
                    difficulty_level="advanced"
                )
            ]
        )

    def _create_career_aligned_recommendation(
        self,
        rec_id: str,
        trait: Trait,
        target_level: float,
        career_goal: CareerGoal
    ) -> EvolutionRecommendation:
        """Create a career-aligned recommendation."""
        gap = target_level - trait.level
        hours_estimate = gap * 50  # Rough estimate: 50 hours per 1.0 level

        return EvolutionRecommendation(
            recommendation_id=rec_id,
            trait_id=trait.id,
            persona_id=trait.persona_id,
            trait_name=trait.name,
            recommendation_type=RecommendationType.PRACTICE,
            priority=RecommendationPriority.HIGH,
            title=f"Career Goal: {trait.name}",
            description=f"Improve {trait.name} to support your goal of becoming a {career_goal.target_role}.",
            expected_level_gain=min(gap, 0.3),
            estimated_hours=hours_estimate,
            rationale=f"Needed for career goal: {career_goal.title}",
            confidence_score=0.85,
            generated_by="rules",
            expires_at=(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) +
                       __import__('datetime').timedelta(days=7)).isoformat()
        )

    def _generate_diversification_recommendation(
        self,
        persona_id: str,
        traits: List[Trait],
        career_goal: CareerGoal
    ) -> Optional[EvolutionRecommendation]:
        """Generate recommendation to diversify skills."""
        existing_names = {t.name.lower() for t in traits}

        for target_name in career_goal.target_traits:
            if target_name.lower() not in existing_names:
                self._recommendation_counter += 1
                rec_id = f"rec_{self._recommendation_counter}"

                return EvolutionRecommendation(
                    recommendation_id=rec_id,
                    trait_id="",  # New trait
                    persona_id=persona_id,
                    trait_name=target_name,
                    recommendation_type=RecommendationType.LEARN,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"New Skill: {target_name}",
                    description=f"Learn {target_name} to support your career goals.",
                    expected_level_gain=0.5,
                    estimated_hours=20.0,
                    rationale=f"Required for career goal: {career_goal.title}",
                    confidence_score=0.75,
                    generated_by="rules"
                )

        return None

    def _calculate_priority_score(self, rec: EvolutionRecommendation) -> float:
        """Calculate priority score for sorting."""
        score = 0.0

        # Priority weight
        priority_scores = {
            RecommendationPriority.URGENT: 1.0,
            RecommendationPriority.HIGH: 0.8,
            RecommendationPriority.MEDIUM: 0.6,
            RecommendationPriority.LOW: 0.4,
            RecommendationPriority.EXPLORATORY: 0.2
        }
        score += priority_scores.get(rec.priority, 0.5) * self._weights["decay_urgency"]

        # Efficiency (level gain / hours)
        if rec.estimated_hours > 0:
            efficiency = rec.expected_level_gain / rec.estimated_hours
            score += min(efficiency * 10, 1.0) * self._weights["effort_efficiency"]

        # Confidence
        score += rec.confidence_score * self._weights["career_alignment"]

        return score

    def _process_ml_recommendations(
        self,
        ml_recs: List[Dict[str, Any]],
        persona_id: str
    ) -> List[EvolutionRecommendation]:
        """Process ML model output into recommendations."""
        # Placeholder for processing ML model output
        return []

    def create_evolution_plan(
        self,
        persona_id: str,
        title: str,
        recommendation_ids: Optional[List[str]] = None
    ) -> EvolutionPlan:
        """Create a comprehensive evolution plan."""
        with self._lock:
            # Generate recommendations if needed
            if persona_id not in self._recommendations:
                self.generate_recommendations(persona_id)

            all_recs = self._recommendations.get(persona_id, [])

            # Filter by IDs if provided
            if recommendation_ids:
                selected_recs = [r for r in all_recs if r.recommendation_id in recommendation_ids]
            else:
                selected_recs = all_recs[:self._max_recommendations]

            # Calculate total hours
            total_hours = sum(r.estimated_hours for r in selected_recs)

            # Estimate completion date
            hours_per_week = 10  # Assume 10 hours/week
            weeks = total_hours / hours_per_week
            completion_date = (datetime.utcnow() +
                             __import__('datetime').timedelta(weeks=weeks)).isoformat()

            plan_id = f"plan_{hashlib.md5(f'{persona_id}_{title}'.encode()).hexdigest()[:12]}"

            plan = EvolutionPlan(
                plan_id=plan_id,
                persona_id=persona_id,
                title=title,
                recommendations=selected_recs,
                total_estimated_hours=total_hours,
                expected_completion_date=completion_date,
                career_goal=self._career_goals.get(persona_id)
            )

            self._plans[plan_id] = plan
            self._save_state()

            logger.info(f"Created evolution plan {plan_id} for persona {persona_id}")
            return plan

    def get_plan(self, plan_id: str) -> Optional[EvolutionPlan]:
        """Get an evolution plan by ID."""
        return self._plans.get(plan_id)

    def get_recommendations(self, persona_id: str) -> List[EvolutionRecommendation]:
        """Get cached recommendations for a persona."""
        return self._recommendations.get(persona_id, [])

    def accept_recommendation(self, recommendation_id: str) -> bool:
        """Mark a recommendation as accepted."""
        for recs in self._recommendations.values():
            for rec in recs:
                if rec.recommendation_id == recommendation_id:
                    rec.accepted = True
                    self._save_state()
                    return True
        return False

    def complete_recommendation(self, recommendation_id: str) -> bool:
        """Mark a recommendation as completed."""
        for recs in self._recommendations.values():
            for rec in recs:
                if rec.recommendation_id == recommendation_id:
                    rec.completed = True
                    self._save_state()
                    return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get evolution guide statistics."""
        total_recs = sum(len(recs) for recs in self._recommendations.values())
        accepted = sum(
            sum(1 for r in recs if r.accepted)
            for recs in self._recommendations.values()
        )
        completed = sum(
            sum(1 for r in recs if r.completed)
            for recs in self._recommendations.values()
        )

        return {
            "total_recommendations": total_recs,
            "accepted_recommendations": accepted,
            "completed_recommendations": completed,
            "active_plans": len(self._plans),
            "career_goals_set": len(self._career_goals),
            "ml_model_enabled": self._ml_model.model_loaded
        }

    def _save_state(self) -> None:
        """Save guide state to disk."""
        if not self._persistence_path:
            return

        try:
            data = {
                "recommendations": {
                    pid: [r.to_dict() for r in recs]
                    for pid, recs in self._recommendations.items()
                },
                "career_goals": {
                    pid: asdict(goal)
                    for pid, goal in self._career_goals.items()
                },
                "plans": {
                    pid: plan.to_dict()
                    for pid, plan in self._plans.items()
                },
                "recommendation_counter": self._recommendation_counter,
                "saved_at": datetime.utcnow().isoformat()
            }

            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save evolution guide state: {e}")

    def _load_state(self) -> None:
        """Load guide state from disk."""
        try:
            with open(self._persistence_path, "r") as f:
                data = json.load(f)

            self._recommendation_counter = data.get("recommendation_counter", 0)

            # Restore career goals
            for pid, goal_data in data.get("career_goals", {}).items():
                self._career_goals[pid] = CareerGoal(**goal_data)

            logger.info(f"Loaded evolution guide state: {len(self._career_goals)} career goals")
        except Exception as e:
            logger.error(f"Failed to load evolution guide state: {e}")


# Singleton instance
_evolution_guide: Optional[EvolutionGuide] = None
_evolution_guide_lock = threading.Lock()


def get_evolution_guide(
    trait_manager: Optional[TraitManager] = None,
    force_new: bool = False
) -> EvolutionGuide:
    """
    Get the singleton EvolutionGuide instance.

    Args:
        trait_manager: Optional TraitManager instance
        force_new: Force creation of new instance

    Returns:
        EvolutionGuide instance
    """
    global _evolution_guide

    with _evolution_guide_lock:
        if _evolution_guide is None or force_new:
            _evolution_guide = EvolutionGuide(trait_manager=trait_manager)
        return _evolution_guide
