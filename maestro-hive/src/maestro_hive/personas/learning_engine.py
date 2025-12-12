#!/usr/bin/env python3
"""
Learning Engine: Persona Experience Accumulation & Skill Growth.

This module provides the core learning infrastructure for AI personas,
enabling experience recording, pattern recognition, and skill level
calculation based on accumulated experiences.

Related EPIC: MD-3021 - Persona Evolution & Learning
"""

import json
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class ExperienceType(Enum):
    """Types of learning experiences."""
    PRACTICE = "practice"         # Skill practice session
    SUCCESS = "success"           # Successful task completion
    FAILURE = "failure"           # Failed attempt (learning opportunity)
    FEEDBACK = "feedback"         # External feedback received
    OBSERVATION = "observation"   # Learning from observing others
    COLLABORATION = "collaboration"  # Learning through collaboration
    INSTRUCTION = "instruction"   # Direct instruction/training


class LearningOutcome(Enum):
    """Outcomes of learning experiences."""
    EXCELLENT = "excellent"   # Exceeds expectations
    GOOD = "good"            # Meets expectations
    ADEQUATE = "adequate"    # Minimum acceptable
    POOR = "poor"            # Below expectations
    FAILED = "failed"        # Complete failure


@dataclass
class LearningEngineConfig:
    """Configuration for the learning engine."""
    batch_size: int = 100
    process_interval: int = 60  # seconds
    max_history: int = 10000
    decay_factor: float = 0.95
    min_experiences: int = 5
    growth_base_rate: float = 0.01
    experience_weight_recent: float = 0.7
    experience_weight_historical: float = 0.3
    storage_path: Optional[Path] = None


@dataclass
class Experience:
    """A recorded learning experience for a persona."""
    experience_id: str
    persona_id: str
    skill_id: str
    experience_type: ExperienceType
    outcome: LearningOutcome
    outcome_score: float  # 0.0 to 1.0
    context: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    difficulty_level: float = 0.5  # 0.0 (easy) to 1.0 (hard)
    feedback: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert experience to dictionary."""
        return {
            **asdict(self),
            "experience_type": self.experience_type.value,
            "outcome": self.outcome.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experience":
        """Create experience from dictionary."""
        data = data.copy()
        data["experience_type"] = ExperienceType(data["experience_type"])
        data["outcome"] = LearningOutcome(data["outcome"])
        return cls(**data)


@dataclass
class ExperienceResult:
    """Result of recording an experience."""
    success: bool
    experience_id: str
    skill_level_before: float
    skill_level_after: float
    growth_amount: float
    message: str = ""


@dataclass
class SkillLevelData:
    """Skill level data for a persona."""
    persona_id: str
    skill_id: str
    level: float  # 0.0 to 1.0
    experience_count: int
    total_practice_hours: float
    last_experience: str
    growth_rate: float  # Recent growth velocity
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class LearningStats:
    """Statistics about learning progress."""
    persona_id: str
    total_experiences: int
    total_skills: int
    average_skill_level: float
    total_practice_hours: float
    experience_breakdown: Dict[str, int]  # By type
    outcome_distribution: Dict[str, int]  # By outcome
    most_practiced_skill: Optional[str]
    fastest_growing_skill: Optional[str]


class LearningEngine:
    """
    Core engine for persona experience accumulation and learning.

    Handles:
    - Experience event processing and storage
    - Pattern recognition from accumulated experiences
    - Skill level calculation based on experience
    - Learning rate optimization
    """

    _instance: Optional["LearningEngine"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[LearningEngineConfig] = None):
        """Initialize the learning engine."""
        self.config = config or LearningEngineConfig()
        self._experiences: Dict[str, List[Experience]] = defaultdict(list)
        self._skill_levels: Dict[str, Dict[str, SkillLevelData]] = defaultdict(dict)
        self._experience_lock = threading.Lock()
        self._callbacks: List[Callable[[Experience, ExperienceResult], None]] = []
        self._initialized = False

        if self.config.storage_path:
            self._load_state()

        self._initialized = True
        logger.info("LearningEngine initialized with config: %s", self.config)

    @classmethod
    def get_instance(cls, config: Optional[LearningEngineConfig] = None) -> "LearningEngine":
        """Get singleton instance of learning engine."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def record_experience(self, experience: Experience) -> ExperienceResult:
        """
        Record a learning experience for a persona.

        Args:
            experience: The experience to record

        Returns:
            ExperienceResult with success status and skill level changes
        """
        with self._experience_lock:
            # Get current skill level
            skill_level_before = self.get_skill_level(
                experience.persona_id,
                experience.skill_id
            )

            # Store experience
            key = f"{experience.persona_id}:{experience.skill_id}"
            self._experiences[key].append(experience)

            # Trim history if needed
            if len(self._experiences[key]) > self.config.max_history:
                self._experiences[key] = self._experiences[key][-self.config.max_history:]

            # Calculate new skill level
            skill_level_after = self._calculate_skill_level(
                experience.persona_id,
                experience.skill_id
            )

            # Update skill level data
            self._update_skill_level_data(
                experience.persona_id,
                experience.skill_id,
                skill_level_after,
                experience
            )

            growth = skill_level_after - skill_level_before

            result = ExperienceResult(
                success=True,
                experience_id=experience.experience_id,
                skill_level_before=skill_level_before,
                skill_level_after=skill_level_after,
                growth_amount=growth,
                message=f"Experience recorded. Growth: {growth:+.4f}"
            )

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(experience, result)
                except Exception as e:
                    logger.error("Callback error: %s", e)

            logger.debug(
                "Recorded experience %s for persona %s skill %s: %.4f -> %.4f",
                experience.experience_id,
                experience.persona_id,
                experience.skill_id,
                skill_level_before,
                skill_level_after
            )

            return result

    def get_skill_level(self, persona_id: str, skill_id: str) -> float:
        """
        Get current skill level based on accumulated experience.

        Args:
            persona_id: The persona ID
            skill_id: The skill ID

        Returns:
            Current skill level (0.0 to 1.0)
        """
        if persona_id in self._skill_levels:
            if skill_id in self._skill_levels[persona_id]:
                return self._skill_levels[persona_id][skill_id].level

        # Calculate from experiences if not cached
        return self._calculate_skill_level(persona_id, skill_id)

    def _calculate_skill_level(self, persona_id: str, skill_id: str) -> float:
        """Calculate skill level from accumulated experiences."""
        key = f"{persona_id}:{skill_id}"
        experiences = self._experiences.get(key, [])

        if not experiences:
            return 0.0

        if len(experiences) < self.config.min_experiences:
            # Not enough data, use simple average
            return sum(e.outcome_score for e in experiences) / len(experiences) * 0.5

        # Use exponential decay weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        now = datetime.utcnow()

        for i, exp in enumerate(reversed(experiences)):
            # Time decay
            exp_time = datetime.fromisoformat(exp.timestamp.replace("Z", "+00:00"))
            days_ago = (now - exp_time.replace(tzinfo=None)).days
            time_weight = self.config.decay_factor ** days_ago

            # Recency weight (more recent = higher weight)
            recency_weight = self.config.experience_weight_recent if i < 10 else self.config.experience_weight_historical

            # Difficulty adjustment (harder tasks contribute more)
            difficulty_weight = 0.5 + exp.difficulty_level * 0.5

            # Experience type weight
            type_weight = self._get_experience_type_weight(exp.experience_type)

            weight = time_weight * recency_weight * difficulty_weight * type_weight
            weighted_sum += exp.outcome_score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # Calculate base level
        base_level = weighted_sum / total_weight

        # Apply growth curve (diminishing returns at higher levels)
        # Uses logistic curve to smooth growth
        adjusted_level = self._apply_growth_curve(base_level, len(experiences))

        return min(1.0, max(0.0, adjusted_level))

    def _get_experience_type_weight(self, exp_type: ExperienceType) -> float:
        """Get weight multiplier for experience type."""
        weights = {
            ExperienceType.PRACTICE: 1.0,
            ExperienceType.SUCCESS: 1.5,
            ExperienceType.FAILURE: 0.8,
            ExperienceType.FEEDBACK: 1.2,
            ExperienceType.OBSERVATION: 0.6,
            ExperienceType.COLLABORATION: 1.3,
            ExperienceType.INSTRUCTION: 1.4,
        }
        return weights.get(exp_type, 1.0)

    def _apply_growth_curve(self, base_level: float, experience_count: int) -> float:
        """Apply growth curve with diminishing returns."""
        # Logistic growth curve
        # L / (1 + e^(-k*(x-x0)))
        L = 1.0  # Maximum level
        k = 0.1  # Steepness
        x0 = 50  # Midpoint (experiences needed for 0.5 level)

        experience_factor = L / (1 + math.exp(-k * (experience_count - x0)))

        return base_level * (0.3 + 0.7 * experience_factor)

    def _update_skill_level_data(
        self,
        persona_id: str,
        skill_id: str,
        new_level: float,
        experience: Experience
    ):
        """Update cached skill level data."""
        if persona_id not in self._skill_levels:
            self._skill_levels[persona_id] = {}

        key = f"{persona_id}:{skill_id}"
        experiences = self._experiences.get(key, [])

        total_hours = sum(e.duration_seconds for e in experiences) / 3600.0

        old_data = self._skill_levels[persona_id].get(skill_id)
        old_level = old_data.level if old_data else 0.0
        growth_rate = new_level - old_level

        self._skill_levels[persona_id][skill_id] = SkillLevelData(
            persona_id=persona_id,
            skill_id=skill_id,
            level=new_level,
            experience_count=len(experiences),
            total_practice_hours=total_hours,
            last_experience=experience.timestamp,
            growth_rate=growth_rate,
            created_at=old_data.created_at if old_data else experience.timestamp,
            updated_at=datetime.utcnow().isoformat()
        )

    def get_learning_history(
        self,
        persona_id: str,
        skill_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Experience]:
        """
        Get learning history for a persona.

        Args:
            persona_id: The persona ID
            skill_id: Optional skill filter
            limit: Maximum number of experiences to return

        Returns:
            List of experiences, most recent first
        """
        if skill_id:
            key = f"{persona_id}:{skill_id}"
            experiences = self._experiences.get(key, [])
        else:
            # Get all experiences for persona
            experiences = []
            for key, exps in self._experiences.items():
                if key.startswith(f"{persona_id}:"):
                    experiences.extend(exps)
            experiences.sort(key=lambda e: e.timestamp, reverse=True)

        return experiences[-limit:][::-1]  # Return in chronological order

    def calculate_growth_rate(
        self,
        persona_id: str,
        skill_id: str,
        window_days: int = 7
    ) -> float:
        """
        Calculate learning growth rate for a skill.

        Args:
            persona_id: The persona ID
            skill_id: The skill ID
            window_days: Number of days to calculate rate over

        Returns:
            Growth rate (change per day)
        """
        key = f"{persona_id}:{skill_id}"
        experiences = self._experiences.get(key, [])

        if len(experiences) < 2:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=window_days)
        cutoff_iso = cutoff.isoformat()

        recent_experiences = [
            e for e in experiences
            if e.timestamp >= cutoff_iso
        ]

        if len(recent_experiences) < 2:
            return 0.0

        # Calculate level at start and end of window
        first_exp = recent_experiences[0]
        last_exp = recent_experiences[-1]

        first_score = first_exp.outcome_score
        last_score = last_exp.outcome_score

        first_time = datetime.fromisoformat(first_exp.timestamp.replace("Z", "+00:00"))
        last_time = datetime.fromisoformat(last_exp.timestamp.replace("Z", "+00:00"))

        days_elapsed = (last_time - first_time).total_seconds() / 86400

        if days_elapsed < 0.1:
            return 0.0

        return (last_score - first_score) / days_elapsed

    def get_learning_stats(self, persona_id: str) -> LearningStats:
        """
        Get comprehensive learning statistics for a persona.

        Args:
            persona_id: The persona ID

        Returns:
            LearningStats with comprehensive statistics
        """
        all_experiences: List[Experience] = []
        skills: Dict[str, List[Experience]] = defaultdict(list)

        for key, exps in self._experiences.items():
            if key.startswith(f"{persona_id}:"):
                skill_id = key.split(":")[1]
                all_experiences.extend(exps)
                skills[skill_id].extend(exps)

        if not all_experiences:
            return LearningStats(
                persona_id=persona_id,
                total_experiences=0,
                total_skills=0,
                average_skill_level=0.0,
                total_practice_hours=0.0,
                experience_breakdown={},
                outcome_distribution={},
                most_practiced_skill=None,
                fastest_growing_skill=None
            )

        # Calculate breakdowns
        exp_breakdown: Dict[str, int] = defaultdict(int)
        outcome_dist: Dict[str, int] = defaultdict(int)

        for exp in all_experiences:
            exp_breakdown[exp.experience_type.value] += 1
            outcome_dist[exp.outcome.value] += 1

        total_hours = sum(e.duration_seconds for e in all_experiences) / 3600.0

        # Find most practiced and fastest growing
        skill_counts = {s: len(exps) for s, exps in skills.items()}
        most_practiced = max(skill_counts, key=skill_counts.get) if skill_counts else None

        growth_rates = {
            s: self.calculate_growth_rate(persona_id, s)
            for s in skills
        }
        fastest_growing = max(growth_rates, key=growth_rates.get) if growth_rates else None

        # Average skill level
        skill_levels = [
            self.get_skill_level(persona_id, s) for s in skills
        ]
        avg_level = sum(skill_levels) / len(skill_levels) if skill_levels else 0.0

        return LearningStats(
            persona_id=persona_id,
            total_experiences=len(all_experiences),
            total_skills=len(skills),
            average_skill_level=avg_level,
            total_practice_hours=total_hours,
            experience_breakdown=dict(exp_breakdown),
            outcome_distribution=dict(outcome_dist),
            most_practiced_skill=most_practiced,
            fastest_growing_skill=fastest_growing
        )

    def get_all_skill_levels(self, persona_id: str) -> Dict[str, SkillLevelData]:
        """Get all skill levels for a persona."""
        return dict(self._skill_levels.get(persona_id, {}))

    def register_callback(
        self,
        callback: Callable[[Experience, ExperienceResult], None]
    ):
        """Register a callback to be called after each experience is recorded."""
        self._callbacks.append(callback)

    def _load_state(self):
        """Load state from storage."""
        if not self.config.storage_path:
            return

        storage_file = self.config.storage_path / "learning_engine_state.json"
        if not storage_file.exists():
            return

        try:
            with open(storage_file, "r") as f:
                data = json.load(f)

            for key, exps in data.get("experiences", {}).items():
                self._experiences[key] = [
                    Experience.from_dict(e) for e in exps
                ]

            logger.info("Loaded learning engine state from %s", storage_file)
        except Exception as e:
            logger.error("Failed to load learning engine state: %s", e)

    def save_state(self):
        """Save state to storage."""
        if not self.config.storage_path:
            return

        self.config.storage_path.mkdir(parents=True, exist_ok=True)
        storage_file = self.config.storage_path / "learning_engine_state.json"

        try:
            data = {
                "experiences": {
                    key: [e.to_dict() for e in exps]
                    for key, exps in self._experiences.items()
                },
                "saved_at": datetime.utcnow().isoformat()
            }

            with open(storage_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved learning engine state to %s", storage_file)
        except Exception as e:
            logger.error("Failed to save learning engine state: %s", e)


# Module-level singleton accessor
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine(config: Optional[LearningEngineConfig] = None) -> LearningEngine:
    """Get the global learning engine instance."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine(config)
    return _learning_engine


def record_experience(
    persona_id: str,
    skill_id: str,
    experience_type: ExperienceType,
    outcome: LearningOutcome,
    outcome_score: float,
    **kwargs
) -> ExperienceResult:
    """
    Convenience function to record an experience.

    Args:
        persona_id: The persona ID
        skill_id: The skill ID
        experience_type: Type of experience
        outcome: Outcome of the experience
        outcome_score: Score from 0.0 to 1.0
        **kwargs: Additional experience fields

    Returns:
        ExperienceResult
    """
    experience = Experience(
        experience_id=hashlib.sha256(
            f"{persona_id}:{skill_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16],
        persona_id=persona_id,
        skill_id=skill_id,
        experience_type=experience_type,
        outcome=outcome,
        outcome_score=outcome_score,
        **kwargs
    )

    engine = get_learning_engine()
    return engine.record_experience(experience)
