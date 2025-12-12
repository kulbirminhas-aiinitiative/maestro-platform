"""
Evolution Tracker for Persona Capability Growth.

This module provides functionality for tracking and recording persona capability
evolution over time, detecting milestones, and calculating growth velocity.

EPIC: MD-3021 - Persona Evolution & Learning
AC-2: Evolution tracker for capability growth
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class MilestoneType(Enum):
    """Types of evolution milestones."""
    SKILL_ACQUIRED = "skill_acquired"
    SKILL_MASTERY = "skill_mastery"
    LEVEL_UP = "level_up"
    STREAK_ACHIEVED = "streak_achieved"
    GROWTH_SPURT = "growth_spurt"
    EXPERTISE_THRESHOLD = "expertise_threshold"
    SPECIALIZATION = "specialization"
    CROSS_SKILL_SYNERGY = "cross_skill_synergy"


class EvolutionStage(Enum):
    """Stages of persona evolution."""
    NASCENT = "nascent"
    DEVELOPING = "developing"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class Milestone:
    """Represents an evolution milestone achievement."""
    id: str
    persona_id: str
    milestone_type: MilestoneType
    skill_id: Optional[str]
    achieved_at: datetime
    description: str
    previous_value: float
    new_value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary."""
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "milestone_type": self.milestone_type.value,
            "skill_id": self.skill_id,
            "achieved_at": self.achieved_at.isoformat(),
            "description": self.description,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
        }


@dataclass
class EvolutionSnapshot:
    """Point-in-time snapshot of persona evolution state."""
    id: str
    persona_id: str
    timestamp: datetime
    stage: EvolutionStage
    overall_level: float
    skill_levels: Dict[str, float]
    growth_velocity: float
    active_skills: int
    total_experiences: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "timestamp": self.timestamp.isoformat(),
            "stage": self.stage.value,
            "overall_level": self.overall_level,
            "skill_levels": self.skill_levels,
            "growth_velocity": self.growth_velocity,
            "active_skills": self.active_skills,
            "total_experiences": self.total_experiences,
            "metadata": self.metadata,
        }


@dataclass
class GrowthMetrics:
    """Metrics for persona growth analysis."""
    persona_id: str
    period_start: datetime
    period_end: datetime
    velocity: float
    acceleration: float
    skills_improved: int
    skills_declined: int
    milestones_achieved: int
    dominant_skill: Optional[str]
    growth_trend: str  # "accelerating", "steady", "decelerating", "stagnant"

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "persona_id": self.persona_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "skills_improved": self.skills_improved,
            "skills_declined": self.skills_declined,
            "milestones_achieved": self.milestones_achieved,
            "dominant_skill": self.dominant_skill,
            "growth_trend": self.growth_trend,
        }


@dataclass
class EvolutionConfig:
    """Configuration for evolution tracking."""
    snapshot_interval_seconds: int = 3600  # 1 hour
    milestone_threshold: float = 0.1  # 10% improvement triggers milestone
    mastery_threshold: float = 0.9  # 90% skill level = mastery
    expertise_threshold: float = 0.75  # 75% skill level = expertise
    growth_spurt_threshold: float = 0.2  # 20% growth in period = spurt
    stagnation_threshold_days: int = 7  # No improvement for 7 days = stagnant
    velocity_window_days: int = 7  # Window for velocity calculation
    max_snapshots_per_persona: int = 1000
    max_milestones_per_persona: int = 500


class EvolutionTracker:
    """
    Tracks and records persona capability evolution over time.

    Features:
    - Automatic milestone detection
    - Growth velocity calculation
    - Evolution stage determination
    - Historical snapshot management
    - Growth trend analysis
    """

    _instance: Optional["EvolutionTracker"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, config: Optional[EvolutionConfig] = None):
        """Initialize evolution tracker."""
        self._config = config or EvolutionConfig()
        self._snapshots: Dict[str, List[EvolutionSnapshot]] = {}
        self._milestones: Dict[str, List[Milestone]] = {}
        self._current_stages: Dict[str, EvolutionStage] = {}
        self._skill_levels: Dict[str, Dict[str, float]] = {}
        self._experience_counts: Dict[str, int] = {}
        self._last_snapshot_times: Dict[str, datetime] = {}
        self._data_lock = threading.RLock()
        self._initialized = True
        logger.info("EvolutionTracker initialized with config: %s", self._config)

    @classmethod
    def get_instance(cls, config: Optional[EvolutionConfig] = None) -> "EvolutionTracker":
        """Get singleton instance of EvolutionTracker."""
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

    def record_skill_update(
        self,
        persona_id: str,
        skill_id: str,
        new_level: float,
        experience_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Milestone]:
        """
        Record a skill level update and detect milestones.

        Args:
            persona_id: ID of the persona
            skill_id: ID of the skill
            new_level: New skill level (0.0 to 1.0)
            experience_count: Total experience count for persona
            metadata: Optional additional metadata

        Returns:
            List of milestones achieved from this update
        """
        with self._data_lock:
            achieved_milestones: List[Milestone] = []
            now = datetime.utcnow()

            # Initialize persona data if needed
            if persona_id not in self._skill_levels:
                self._skill_levels[persona_id] = {}
                self._milestones[persona_id] = []
                self._snapshots[persona_id] = []
                self._current_stages[persona_id] = EvolutionStage.NASCENT

            # Get previous level
            previous_level = self._skill_levels[persona_id].get(skill_id, 0.0)

            # Update skill level
            self._skill_levels[persona_id][skill_id] = new_level
            self._experience_counts[persona_id] = experience_count

            # Check for milestones
            achieved_milestones.extend(
                self._detect_milestones(
                    persona_id, skill_id, previous_level, new_level, now, metadata
                )
            )

            # Update evolution stage
            self._update_evolution_stage(persona_id)

            # Check if snapshot needed
            self._maybe_create_snapshot(persona_id, now)

            logger.debug(
                "Recorded skill update for %s/%s: %.3f -> %.3f, milestones: %d",
                persona_id, skill_id, previous_level, new_level, len(achieved_milestones)
            )

            return achieved_milestones

    def _detect_milestones(
        self,
        persona_id: str,
        skill_id: str,
        previous_level: float,
        new_level: float,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]],
    ) -> List[Milestone]:
        """Detect milestones from a skill level change."""
        milestones: List[Milestone] = []

        # Skip if no improvement
        if new_level <= previous_level:
            return milestones

        improvement = new_level - previous_level

        # Skill Acquired - first time skill appears
        if previous_level == 0.0 and new_level > 0.0:
            milestone = Milestone(
                id=str(uuid4()),
                persona_id=persona_id,
                milestone_type=MilestoneType.SKILL_ACQUIRED,
                skill_id=skill_id,
                achieved_at=timestamp,
                description=f"Acquired skill: {skill_id}",
                previous_value=previous_level,
                new_value=new_level,
                metadata=metadata or {},
            )
            milestones.append(milestone)
            self._milestones[persona_id].append(milestone)

        # Expertise Threshold crossed
        if previous_level < self._config.expertise_threshold <= new_level:
            milestone = Milestone(
                id=str(uuid4()),
                persona_id=persona_id,
                milestone_type=MilestoneType.EXPERTISE_THRESHOLD,
                skill_id=skill_id,
                achieved_at=timestamp,
                description=f"Reached expertise level in: {skill_id}",
                previous_value=previous_level,
                new_value=new_level,
                metadata=metadata or {},
            )
            milestones.append(milestone)
            self._milestones[persona_id].append(milestone)

        # Skill Mastery
        if previous_level < self._config.mastery_threshold <= new_level:
            milestone = Milestone(
                id=str(uuid4()),
                persona_id=persona_id,
                milestone_type=MilestoneType.SKILL_MASTERY,
                skill_id=skill_id,
                achieved_at=timestamp,
                description=f"Achieved mastery in: {skill_id}",
                previous_value=previous_level,
                new_value=new_level,
                metadata=metadata or {},
            )
            milestones.append(milestone)
            self._milestones[persona_id].append(milestone)

        # Growth Spurt
        if improvement >= self._config.growth_spurt_threshold:
            milestone = Milestone(
                id=str(uuid4()),
                persona_id=persona_id,
                milestone_type=MilestoneType.GROWTH_SPURT,
                skill_id=skill_id,
                achieved_at=timestamp,
                description=f"Growth spurt in: {skill_id} (+{improvement:.1%})",
                previous_value=previous_level,
                new_value=new_level,
                metadata=metadata or {},
            )
            milestones.append(milestone)
            self._milestones[persona_id].append(milestone)

        # Level Up (every 0.1 increment)
        prev_level_int = int(previous_level * 10)
        new_level_int = int(new_level * 10)
        if new_level_int > prev_level_int:
            milestone = Milestone(
                id=str(uuid4()),
                persona_id=persona_id,
                milestone_type=MilestoneType.LEVEL_UP,
                skill_id=skill_id,
                achieved_at=timestamp,
                description=f"Level up in {skill_id}: Level {new_level_int}",
                previous_value=previous_level,
                new_value=new_level,
                metadata=metadata or {},
            )
            milestones.append(milestone)
            self._milestones[persona_id].append(milestone)

        # Enforce max milestones limit
        if len(self._milestones[persona_id]) > self._config.max_milestones_per_persona:
            self._milestones[persona_id] = self._milestones[persona_id][
                -self._config.max_milestones_per_persona:
            ]

        return milestones

    def _update_evolution_stage(self, persona_id: str) -> None:
        """Update the evolution stage for a persona."""
        skill_levels = self._skill_levels.get(persona_id, {})

        if not skill_levels:
            self._current_stages[persona_id] = EvolutionStage.NASCENT
            return

        avg_level = sum(skill_levels.values()) / len(skill_levels)
        max_level = max(skill_levels.values())
        num_skills = len(skill_levels)

        # Determine stage based on average level and skill count
        if avg_level >= 0.9 and num_skills >= 5 and max_level >= 0.95:
            self._current_stages[persona_id] = EvolutionStage.MASTER
        elif avg_level >= 0.75 and num_skills >= 4:
            self._current_stages[persona_id] = EvolutionStage.EXPERT
        elif avg_level >= 0.6 and num_skills >= 3:
            self._current_stages[persona_id] = EvolutionStage.PROFICIENT
        elif avg_level >= 0.4 and num_skills >= 2:
            self._current_stages[persona_id] = EvolutionStage.COMPETENT
        elif avg_level >= 0.2:
            self._current_stages[persona_id] = EvolutionStage.DEVELOPING
        else:
            self._current_stages[persona_id] = EvolutionStage.NASCENT

    def _maybe_create_snapshot(self, persona_id: str, now: datetime) -> Optional[EvolutionSnapshot]:
        """Create a snapshot if enough time has passed."""
        last_snapshot = self._last_snapshot_times.get(persona_id)

        if last_snapshot is not None:
            elapsed = (now - last_snapshot).total_seconds()
            if elapsed < self._config.snapshot_interval_seconds:
                return None

        return self.create_snapshot(persona_id)

    def create_snapshot(self, persona_id: str) -> Optional[EvolutionSnapshot]:
        """
        Create an evolution snapshot for a persona.

        Args:
            persona_id: ID of the persona

        Returns:
            Created snapshot or None if persona not found
        """
        with self._data_lock:
            skill_levels = self._skill_levels.get(persona_id)
            if skill_levels is None:
                return None

            now = datetime.utcnow()

            # Calculate overall level
            overall_level = 0.0
            if skill_levels:
                overall_level = sum(skill_levels.values()) / len(skill_levels)

            # Calculate growth velocity
            velocity = self.calculate_growth_velocity(persona_id)

            snapshot = EvolutionSnapshot(
                id=str(uuid4()),
                persona_id=persona_id,
                timestamp=now,
                stage=self._current_stages.get(persona_id, EvolutionStage.NASCENT),
                overall_level=overall_level,
                skill_levels=dict(skill_levels),
                growth_velocity=velocity,
                active_skills=len(skill_levels),
                total_experiences=self._experience_counts.get(persona_id, 0),
            )

            # Store snapshot
            if persona_id not in self._snapshots:
                self._snapshots[persona_id] = []
            self._snapshots[persona_id].append(snapshot)
            self._last_snapshot_times[persona_id] = now

            # Enforce max snapshots limit
            if len(self._snapshots[persona_id]) > self._config.max_snapshots_per_persona:
                self._snapshots[persona_id] = self._snapshots[persona_id][
                    -self._config.max_snapshots_per_persona:
                ]

            logger.debug(
                "Created snapshot for %s: stage=%s, level=%.3f, velocity=%.4f",
                persona_id, snapshot.stage.value, overall_level, velocity
            )

            return snapshot

    def calculate_growth_velocity(
        self,
        persona_id: str,
        window_days: Optional[int] = None,
    ) -> float:
        """
        Calculate growth velocity for a persona.

        Args:
            persona_id: ID of the persona
            window_days: Window for velocity calculation (default from config)

        Returns:
            Growth velocity (change in overall level per day)
        """
        with self._data_lock:
            if window_days is None:
                window_days = self._config.velocity_window_days

            snapshots = self._snapshots.get(persona_id, [])
            if len(snapshots) < 2:
                return 0.0

            # Get snapshots within window
            now = datetime.utcnow()
            window_start = now - timedelta(days=window_days)

            window_snapshots = [
                s for s in snapshots if s.timestamp >= window_start
            ]

            if len(window_snapshots) < 2:
                # Use oldest and newest if not enough in window
                window_snapshots = [snapshots[0], snapshots[-1]]

            if len(window_snapshots) < 2:
                return 0.0

            # Calculate velocity
            first = window_snapshots[0]
            last = window_snapshots[-1]

            level_change = last.overall_level - first.overall_level
            time_delta = (last.timestamp - first.timestamp).total_seconds()

            if time_delta <= 0:
                return 0.0

            # Convert to per-day velocity
            days = time_delta / 86400
            if days < 0.01:  # Less than ~15 minutes
                return 0.0

            return level_change / days

    def get_growth_metrics(
        self,
        persona_id: str,
        period_days: int = 7,
    ) -> Optional[GrowthMetrics]:
        """
        Get comprehensive growth metrics for a persona.

        Args:
            persona_id: ID of the persona
            period_days: Period for metrics calculation

        Returns:
            Growth metrics or None if insufficient data
        """
        with self._data_lock:
            snapshots = self._snapshots.get(persona_id, [])
            if len(snapshots) < 2:
                return None

            now = datetime.utcnow()
            period_start = now - timedelta(days=period_days)

            # Get snapshots in period
            period_snapshots = [s for s in snapshots if s.timestamp >= period_start]

            if len(period_snapshots) < 2:
                period_snapshots = [snapshots[0], snapshots[-1]]

            first = period_snapshots[0]
            last = period_snapshots[-1]

            # Calculate velocity
            velocity = self.calculate_growth_velocity(persona_id, period_days)

            # Calculate acceleration (change in velocity)
            acceleration = 0.0
            if len(period_snapshots) >= 3:
                mid_idx = len(period_snapshots) // 2
                mid = period_snapshots[mid_idx]

                # First half velocity
                time_delta1 = (mid.timestamp - first.timestamp).total_seconds() / 86400
                if time_delta1 > 0:
                    v1 = (mid.overall_level - first.overall_level) / time_delta1
                else:
                    v1 = 0.0

                # Second half velocity
                time_delta2 = (last.timestamp - mid.timestamp).total_seconds() / 86400
                if time_delta2 > 0:
                    v2 = (last.overall_level - mid.overall_level) / time_delta2
                else:
                    v2 = 0.0

                total_time = time_delta1 + time_delta2
                if total_time > 0:
                    acceleration = (v2 - v1) / total_time

            # Count improved/declined skills
            skills_improved = 0
            skills_declined = 0
            for skill_id in last.skill_levels:
                first_level = first.skill_levels.get(skill_id, 0.0)
                last_level = last.skill_levels.get(skill_id, 0.0)
                if last_level > first_level + 0.01:
                    skills_improved += 1
                elif last_level < first_level - 0.01:
                    skills_declined += 1

            # Count milestones in period
            milestones = self._milestones.get(persona_id, [])
            milestones_achieved = sum(
                1 for m in milestones if m.achieved_at >= period_start
            )

            # Find dominant skill
            dominant_skill = None
            if last.skill_levels:
                dominant_skill = max(last.skill_levels, key=last.skill_levels.get)

            # Determine growth trend
            if acceleration > 0.01:
                growth_trend = "accelerating"
            elif acceleration < -0.01:
                growth_trend = "decelerating"
            elif velocity > 0.001:
                growth_trend = "steady"
            else:
                growth_trend = "stagnant"

            return GrowthMetrics(
                persona_id=persona_id,
                period_start=first.timestamp,
                period_end=last.timestamp,
                velocity=velocity,
                acceleration=acceleration,
                skills_improved=skills_improved,
                skills_declined=skills_declined,
                milestones_achieved=milestones_achieved,
                dominant_skill=dominant_skill,
                growth_trend=growth_trend,
            )

    def get_evolution_stage(self, persona_id: str) -> EvolutionStage:
        """
        Get current evolution stage for a persona.

        Args:
            persona_id: ID of the persona

        Returns:
            Current evolution stage
        """
        with self._data_lock:
            return self._current_stages.get(persona_id, EvolutionStage.NASCENT)

    def get_milestones(
        self,
        persona_id: str,
        milestone_type: Optional[MilestoneType] = None,
        skill_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Milestone]:
        """
        Get milestones for a persona with optional filtering.

        Args:
            persona_id: ID of the persona
            milestone_type: Filter by milestone type
            skill_id: Filter by skill ID
            since: Filter milestones after this time
            limit: Maximum number of milestones to return

        Returns:
            List of milestones
        """
        with self._data_lock:
            milestones = self._milestones.get(persona_id, [])

            # Apply filters
            filtered = milestones

            if milestone_type is not None:
                filtered = [m for m in filtered if m.milestone_type == milestone_type]

            if skill_id is not None:
                filtered = [m for m in filtered if m.skill_id == skill_id]

            if since is not None:
                filtered = [m for m in filtered if m.achieved_at >= since]

            # Return most recent first, limited
            return sorted(filtered, key=lambda m: m.achieved_at, reverse=True)[:limit]

    def get_snapshots(
        self,
        persona_id: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[EvolutionSnapshot]:
        """
        Get evolution snapshots for a persona.

        Args:
            persona_id: ID of the persona
            since: Filter snapshots after this time
            limit: Maximum number of snapshots to return

        Returns:
            List of snapshots
        """
        with self._data_lock:
            snapshots = self._snapshots.get(persona_id, [])

            if since is not None:
                snapshots = [s for s in snapshots if s.timestamp >= since]

            # Return most recent first, limited
            return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[:limit]

    def get_evolution_summary(self, persona_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive evolution summary for a persona.

        Args:
            persona_id: ID of the persona

        Returns:
            Dictionary containing evolution summary
        """
        with self._data_lock:
            stage = self.get_evolution_stage(persona_id)
            skill_levels = self._skill_levels.get(persona_id, {})
            milestones = self._milestones.get(persona_id, [])
            snapshots = self._snapshots.get(persona_id, [])

            # Calculate overall level
            overall_level = 0.0
            if skill_levels:
                overall_level = sum(skill_levels.values()) / len(skill_levels)

            # Get recent milestones
            recent_milestones = sorted(
                milestones, key=lambda m: m.achieved_at, reverse=True
            )[:5]

            # Get growth metrics
            metrics = self.get_growth_metrics(persona_id)

            return {
                "persona_id": persona_id,
                "stage": stage.value,
                "overall_level": overall_level,
                "skill_count": len(skill_levels),
                "skill_levels": skill_levels,
                "total_milestones": len(milestones),
                "total_snapshots": len(snapshots),
                "recent_milestones": [m.to_dict() for m in recent_milestones],
                "growth_metrics": metrics.to_dict() if metrics else None,
                "experience_count": self._experience_counts.get(persona_id, 0),
            }

    def compare_personas(
        self,
        persona_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare evolution progress across multiple personas.

        Args:
            persona_ids: List of persona IDs to compare

        Returns:
            Comparison data
        """
        with self._data_lock:
            comparisons = []

            for persona_id in persona_ids:
                skill_levels = self._skill_levels.get(persona_id, {})
                overall_level = 0.0
                if skill_levels:
                    overall_level = sum(skill_levels.values()) / len(skill_levels)

                comparisons.append({
                    "persona_id": persona_id,
                    "stage": self.get_evolution_stage(persona_id).value,
                    "overall_level": overall_level,
                    "skill_count": len(skill_levels),
                    "milestone_count": len(self._milestones.get(persona_id, [])),
                    "velocity": self.calculate_growth_velocity(persona_id),
                })

            # Sort by overall level
            comparisons.sort(key=lambda x: x["overall_level"], reverse=True)

            return {
                "personas": comparisons,
                "comparison_time": datetime.utcnow().isoformat(),
                "total_compared": len(comparisons),
            }


# Module-level convenience functions
def get_tracker(config: Optional[EvolutionConfig] = None) -> EvolutionTracker:
    """Get the singleton EvolutionTracker instance."""
    return EvolutionTracker.get_instance(config)


def record_skill_update(
    persona_id: str,
    skill_id: str,
    new_level: float,
    experience_count: int = 0,
) -> List[Milestone]:
    """Record a skill update and return any achieved milestones."""
    return get_tracker().record_skill_update(
        persona_id, skill_id, new_level, experience_count
    )


def get_evolution_summary(persona_id: str) -> Dict[str, Any]:
    """Get evolution summary for a persona."""
    return get_tracker().get_evolution_summary(persona_id)
