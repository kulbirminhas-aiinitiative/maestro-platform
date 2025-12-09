"""
Persona Evolution - Track and manage persona development over time

Implements:
- AC-2542-3: Track persona evolution with performance metrics
- AC-2542-2: Semantic versioning for evolution stages
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from .models import (
    Persona,
    PersonaCapability,
    PersonaVersion,
    CapabilityLevel,
)


logger = logging.getLogger(__name__)


class EvolutionTrigger(Enum):
    """What triggers an evolution event."""
    PERFORMANCE_THRESHOLD = "performance_threshold"
    CAPABILITY_ADDITION = "capability_addition"
    CAPABILITY_UPGRADE = "capability_upgrade"
    CONSTRAINT_CHANGE = "constraint_change"
    TONE_ADJUSTMENT = "tone_adjustment"
    MANUAL_UPGRADE = "manual_upgrade"
    A_B_TEST_WINNER = "a_b_test_winner"
    FEEDBACK_DRIVEN = "feedback_driven"


@dataclass
class PerformanceMetrics:
    """Performance metrics for evolution tracking."""
    success_rate: float = 0.0  # 0-1
    response_quality: float = 0.0  # 0-1
    task_completion_rate: float = 0.0  # 0-1
    user_satisfaction: float = 0.0  # 0-1
    constraint_compliance: float = 1.0  # 0-1 (1 = no violations)
    avg_response_time_ms: float = 0.0
    total_invocations: int = 0
    capability_usage: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "success_rate": self.success_rate,
            "response_quality": self.response_quality,
            "task_completion_rate": self.task_completion_rate,
            "user_satisfaction": self.user_satisfaction,
            "constraint_compliance": self.constraint_compliance,
            "avg_response_time_ms": self.avg_response_time_ms,
            "total_invocations": self.total_invocations,
            "capability_usage": self.capability_usage,
            "error_count": self.error_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """Deserialize metrics from dictionary."""
        return cls(
            success_rate=data.get("success_rate", 0.0),
            response_quality=data.get("response_quality", 0.0),
            task_completion_rate=data.get("task_completion_rate", 0.0),
            user_satisfaction=data.get("user_satisfaction", 0.0),
            constraint_compliance=data.get("constraint_compliance", 1.0),
            avg_response_time_ms=data.get("avg_response_time_ms", 0.0),
            total_invocations=data.get("total_invocations", 0),
            capability_usage=data.get("capability_usage", {}),
            error_count=data.get("error_count", 0),
        )
    
    def overall_score(self) -> float:
        """Calculate weighted overall performance score."""
        weights = {
            "success_rate": 0.25,
            "response_quality": 0.20,
            "task_completion_rate": 0.20,
            "user_satisfaction": 0.20,
            "constraint_compliance": 0.15,
        }
        
        score = (
            self.success_rate * weights["success_rate"] +
            self.response_quality * weights["response_quality"] +
            self.task_completion_rate * weights["task_completion_rate"] +
            self.user_satisfaction * weights["user_satisfaction"] +
            self.constraint_compliance * weights["constraint_compliance"]
        )
        
        return round(score, 4)


@dataclass
class EvolutionEvent:
    """Record of an evolution event."""
    id: UUID = field(default_factory=uuid4)
    persona_id: UUID = field(default_factory=uuid4)
    trigger: EvolutionTrigger = EvolutionTrigger.MANUAL_UPGRADE
    from_version: str = "1.0.0"
    to_version: str = "1.0.1"
    changes: Dict[str, Any] = field(default_factory=dict)
    metrics_before: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    metrics_after: Optional[PerformanceMetrics] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    initiated_by: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "id": str(self.id),
            "persona_id": str(self.persona_id),
            "trigger": self.trigger.value,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "changes": self.changes,
            "metrics_before": self.metrics_before.to_dict(),
            "metrics_after": self.metrics_after.to_dict() if self.metrics_after else None,
            "timestamp": self.timestamp.isoformat(),
            "initiated_by": self.initiated_by,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionEvent":
        """Deserialize event from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
            
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            persona_id=UUID(data["persona_id"]) if data.get("persona_id") else uuid4(),
            trigger=EvolutionTrigger(data.get("trigger", "manual_upgrade")),
            from_version=data.get("from_version", "1.0.0"),
            to_version=data.get("to_version", "1.0.1"),
            changes=data.get("changes", {}),
            metrics_before=PerformanceMetrics.from_dict(data.get("metrics_before", {})),
            metrics_after=PerformanceMetrics.from_dict(data["metrics_after"]) if data.get("metrics_after") else None,
            timestamp=timestamp,
            initiated_by=data.get("initiated_by"),
            notes=data.get("notes", ""),
        )


class PersonaEvolution:
    """
    Manages persona evolution and improvement over time.
    
    Features:
    - Performance tracking
    - Automatic evolution suggestions
    - A/B testing support
    - Evolution history
    - Rollback capabilities
    """
    
    # Thresholds for automatic evolution suggestions
    DEFAULT_THRESHOLDS = {
        "min_invocations": 100,  # Minimum invocations before suggesting evolution
        "success_rate_target": 0.90,
        "satisfaction_target": 0.85,
        "capability_upgrade_threshold": 0.95,  # Usage rate to suggest upgrade
    }
    
    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize evolution manager.
        
        Args:
            thresholds: Custom thresholds for evolution triggers
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._metrics: Dict[UUID, PerformanceMetrics] = {}
        self._history: Dict[UUID, List[EvolutionEvent]] = {}
        self._active_experiments: Dict[UUID, Dict[str, Any]] = {}
        
        logger.info("PersonaEvolution initialized")
    
    def record_metric(
        self,
        persona_id: UUID,
        metric_name: str,
        value: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a performance metric for a persona.
        
        Args:
            persona_id: ID of persona
            metric_name: Name of metric
            value: Metric value
            context: Additional context
        """
        if persona_id not in self._metrics:
            self._metrics[persona_id] = PerformanceMetrics()
        
        metrics = self._metrics[persona_id]
        metrics.total_invocations += 1
        
        # Update appropriate metric with rolling average
        if metric_name == "success":
            n = metrics.total_invocations
            metrics.success_rate = ((n - 1) * metrics.success_rate + value) / n
        elif metric_name == "quality":
            n = metrics.total_invocations
            metrics.response_quality = ((n - 1) * metrics.response_quality + value) / n
        elif metric_name == "completion":
            n = metrics.total_invocations
            metrics.task_completion_rate = ((n - 1) * metrics.task_completion_rate + value) / n
        elif metric_name == "satisfaction":
            n = metrics.total_invocations
            metrics.user_satisfaction = ((n - 1) * metrics.user_satisfaction + value) / n
        elif metric_name == "response_time":
            n = metrics.total_invocations
            metrics.avg_response_time_ms = ((n - 1) * metrics.avg_response_time_ms + value) / n
        elif metric_name == "error":
            metrics.error_count += 1
            metrics.constraint_compliance = 1 - (metrics.error_count / metrics.total_invocations)
        elif metric_name == "capability_used":
            cap_name = context.get("capability") if context else "unknown"
            metrics.capability_usage[cap_name] = metrics.capability_usage.get(cap_name, 0) + 1
    
    def get_metrics(self, persona_id: UUID) -> Optional[PerformanceMetrics]:
        """Get current metrics for a persona."""
        return self._metrics.get(persona_id)
    
    def analyze_evolution_readiness(
        self,
        persona: Persona,
    ) -> Dict[str, Any]:
        """
        Analyze if a persona is ready for evolution.
        
        Args:
            persona: Persona to analyze
        
        Returns:
            Analysis results with suggestions
        """
        metrics = self._metrics.get(persona.id)
        if not metrics:
            return {
                "ready": False,
                "reason": "No metrics available",
                "suggestions": [],
            }
        
        if metrics.total_invocations < self.thresholds["min_invocations"]:
            return {
                "ready": False,
                "reason": f"Insufficient data ({metrics.total_invocations}/{self.thresholds['min_invocations']} invocations)",
                "suggestions": [],
            }
        
        suggestions = []
        
        # Check success rate
        if metrics.success_rate < self.thresholds["success_rate_target"]:
            suggestions.append({
                "type": "improve_success",
                "current": metrics.success_rate,
                "target": self.thresholds["success_rate_target"],
                "recommendation": "Review error patterns and add targeted capabilities",
            })
        
        # Check satisfaction
        if metrics.user_satisfaction < self.thresholds["satisfaction_target"]:
            suggestions.append({
                "type": "improve_satisfaction",
                "current": metrics.user_satisfaction,
                "target": self.thresholds["satisfaction_target"],
                "recommendation": "Adjust tone profile or add empathy-focused training",
            })
        
        # Check capability usage for upgrade candidates
        for cap_name, usage_count in metrics.capability_usage.items():
            usage_rate = usage_count / metrics.total_invocations
            if usage_rate > self.thresholds["capability_upgrade_threshold"]:
                cap = persona.get_capability(cap_name)
                if cap and cap.level != CapabilityLevel.MASTER:
                    suggestions.append({
                        "type": "upgrade_capability",
                        "capability": cap_name,
                        "current_level": cap.level.value,
                        "usage_rate": usage_rate,
                        "recommendation": f"Consider upgrading {cap_name} to next level",
                    })
        
        # Check constraint compliance
        if metrics.constraint_compliance < 0.95:
            suggestions.append({
                "type": "review_constraints",
                "compliance_rate": metrics.constraint_compliance,
                "recommendation": "Review and potentially relax overly strict constraints",
            })
        
        ready = len(suggestions) > 0 and metrics.overall_score() > 0.7
        
        return {
            "ready": ready,
            "overall_score": metrics.overall_score(),
            "metrics": metrics.to_dict(),
            "suggestions": suggestions,
        }
    
    def evolve_persona(
        self,
        persona: Persona,
        changes: Dict[str, Any],
        trigger: EvolutionTrigger = EvolutionTrigger.MANUAL_UPGRADE,
        initiated_by: Optional[str] = None,
        notes: str = "",
    ) -> Tuple[Persona, EvolutionEvent]:
        """
        Evolve a persona with specified changes.
        
        Args:
            persona: Persona to evolve
            changes: Dictionary of changes to apply
            trigger: What triggered this evolution
            initiated_by: Who initiated the evolution
            notes: Evolution notes
        
        Returns:
            Tuple of (evolved persona, evolution event)
        """
        metrics_before = self._metrics.get(persona.id, PerformanceMetrics())
        from_version = str(persona.version)
        
        # Determine version bump type based on changes
        bump_type = "patch"
        if "capabilities" in changes and any(
            c.get("action") == "add" for c in changes.get("capabilities", [])
        ):
            bump_type = "minor"
        if "breaking_changes" in changes and changes["breaking_changes"]:
            bump_type = "major"
        
        # Apply changes
        evolved = self._apply_changes(persona, changes)
        
        # Bump version
        if bump_type == "major":
            evolved.version = evolved.version.bump_major()
        elif bump_type == "minor":
            evolved.version = evolved.version.bump_minor()
        else:
            evolved.version = evolved.version.bump_patch()
        
        evolved.version.changelog = notes or f"Evolution triggered by {trigger.value}"
        evolved.version.checksum = evolved.compute_checksum()
        evolved.version_history.append(PersonaVersion.from_dict(persona.version.to_dict()))
        evolved.updated_at = datetime.utcnow()
        
        # Create evolution event
        event = EvolutionEvent(
            persona_id=persona.id,
            trigger=trigger,
            from_version=from_version,
            to_version=str(evolved.version),
            changes=changes,
            metrics_before=metrics_before,
            initiated_by=initiated_by,
            notes=notes,
        )
        
        # Record in history
        if persona.id not in self._history:
            self._history[persona.id] = []
        self._history[persona.id].append(event)
        
        # Reset metrics for new version
        self._metrics[persona.id] = PerformanceMetrics()
        
        logger.info(
            "Evolved persona %s: v%s -> v%s (%s)",
            persona.id,
            from_version,
            evolved.version,
            trigger.value,
        )
        
        return evolved, event
    
    def _apply_changes(
        self,
        persona: Persona,
        changes: Dict[str, Any],
    ) -> Persona:
        """Apply evolution changes to create new persona."""
        # Create a copy
        evolved = Persona.from_dict(persona.to_dict())
        
        # Apply capability changes
        for cap_change in changes.get("capabilities", []):
            action = cap_change.get("action")
            if action == "add":
                evolved.add_capability(PersonaCapability(
                    name=cap_change["name"],
                    description=cap_change.get("description", ""),
                    level=CapabilityLevel(cap_change.get("level", "intermediate")),
                    domain=cap_change.get("domain"),
                    tools=cap_change.get("tools", []),
                ))
            elif action == "remove":
                evolved.remove_capability(cap_change["name"])
            elif action == "upgrade":
                cap = evolved.get_capability(cap_change["name"])
                if cap:
                    cap.level = CapabilityLevel(cap_change.get("level", cap.level.value))
        
        # Apply tone changes
        if "tone" in changes:
            tone_updates = changes["tone"]
            if "formality" in tone_updates:
                evolved.tone.formality = tone_updates["formality"]
            if "verbosity" in tone_updates:
                evolved.tone.verbosity = tone_updates["verbosity"]
            if "empathy" in tone_updates:
                evolved.tone.empathy = tone_updates["empathy"]
            if "humor" in tone_updates:
                evolved.tone.humor = tone_updates["humor"]
            if "technical_depth" in tone_updates:
                evolved.tone.technical_depth = tone_updates["technical_depth"]
        
        # Apply config changes
        if "config" in changes:
            for key, value in changes["config"].items():
                if hasattr(evolved.config, key):
                    setattr(evolved.config, key, value)
        
        return evolved
    
    def get_evolution_history(
        self,
        persona_id: UUID,
        limit: int = 50,
    ) -> List[EvolutionEvent]:
        """Get evolution history for a persona."""
        history = self._history.get(persona_id, [])
        return sorted(history, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def start_ab_test(
        self,
        persona_a: Persona,
        persona_b: Persona,
        test_name: str,
        duration_hours: int = 24,
        traffic_split: float = 0.5,
    ) -> str:
        """
        Start an A/B test between two persona variants.
        
        Args:
            persona_a: Control persona
            persona_b: Variant persona
            test_name: Name for the test
            duration_hours: Test duration
            traffic_split: Traffic allocation to variant B
        
        Returns:
            Test ID
        """
        test_id = str(uuid4())
        
        self._active_experiments[UUID(test_id)] = {
            "name": test_name,
            "persona_a": str(persona_a.id),
            "persona_b": str(persona_b.id),
            "started_at": datetime.utcnow().isoformat(),
            "ends_at": (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat(),
            "traffic_split": traffic_split,
            "metrics_a": PerformanceMetrics().to_dict(),
            "metrics_b": PerformanceMetrics().to_dict(),
            "status": "running",
        }
        
        logger.info("Started A/B test %s: %s vs %s", test_name, persona_a.id, persona_b.id)
        return test_id
    
    def conclude_ab_test(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """
        Conclude an A/B test and return results.
        
        Args:
            test_id: ID of the test
        
        Returns:
            Test results with winner recommendation
        """
        experiment = self._active_experiments.get(UUID(test_id))
        if not experiment:
            return {"error": "Test not found"}
        
        metrics_a = PerformanceMetrics.from_dict(experiment["metrics_a"])
        metrics_b = PerformanceMetrics.from_dict(experiment["metrics_b"])
        
        score_a = metrics_a.overall_score()
        score_b = metrics_b.overall_score()
        
        winner = "A" if score_a >= score_b else "B"
        confidence = abs(score_a - score_b) / max(score_a, score_b, 0.01)
        
        experiment["status"] = "completed"
        experiment["completed_at"] = datetime.utcnow().isoformat()
        experiment["winner"] = winner
        experiment["confidence"] = confidence
        
        logger.info("A/B test %s concluded: %s wins with %.2f confidence", test_id, winner, confidence)
        
        return {
            "test_id": test_id,
            "winner": winner,
            "score_a": score_a,
            "score_b": score_b,
            "confidence": confidence,
            "recommendation": f"Adopt Persona {winner}" if confidence > 0.1 else "No significant difference",
        }
