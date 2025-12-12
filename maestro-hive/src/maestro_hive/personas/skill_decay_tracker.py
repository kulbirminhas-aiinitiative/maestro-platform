#!/usr/bin/env python3
"""
Skill Decay Tracker: Monitor and calculate skill degradation over time.

This module implements exponential decay modeling for persona traits,
alerting when skills fall below configured thresholds and need reinforcement.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
ADR Reference: ADR-001 Exponential Decay Model
"""

import math
import threading
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from .trait_manager import (
    TraitManager,
    Trait,
    TraitStatus,
    TraitCategory,
    TraitEvent,
    get_trait_manager
)

logger = logging.getLogger(__name__)


class DecayAlertLevel(Enum):
    """Alert levels for skill decay notifications."""
    INFO = "info"          # Informational, no action needed
    WARNING = "warning"    # Skill at risk, practice recommended
    CRITICAL = "critical"  # Skill severely degraded, urgent action
    EMERGENCY = "emergency"  # Skill about to be lost


@dataclass
class DecayParameters:
    """
    Parameters controlling decay calculation for a trait category.

    The exponential decay formula is:
    level(t) = level_0 * e^(-decay_rate * t)

    where t is time since last practice in days.
    """
    decay_rate: float = 0.02  # Daily decay rate (lambda)
    warning_threshold: float = 0.3  # Level at which warning is triggered
    critical_threshold: float = 0.1  # Level at which critical alert is triggered
    min_decay_level: float = 0.05  # Minimum level a skill can decay to
    recovery_bonus: float = 1.5  # Multiplier for recovery after practice

    def validate(self) -> None:
        """Validate decay parameters."""
        if not 0.0 < self.decay_rate < 1.0:
            raise ValueError(f"decay_rate must be between 0 and 1, got {self.decay_rate}")
        if self.warning_threshold <= self.critical_threshold:
            raise ValueError("warning_threshold must be > critical_threshold")


@dataclass
class DecayAlert:
    """Alert generated when a skill decays below threshold."""
    alert_id: str
    trait_id: str
    persona_id: Optional[str]
    trait_name: str
    current_level: float
    previous_level: float
    alert_level: DecayAlertLevel
    message: str
    recommendation: str
    days_since_practice: float
    projected_decay_30d: float  # Projected level in 30 days
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            **asdict(self),
            "alert_level": self.alert_level.value
        }


@dataclass
class DecayCalculationResult:
    """Result of a decay calculation for a trait."""
    trait_id: str
    original_level: float
    decayed_level: float
    decay_amount: float
    days_since_practice: float
    decay_rate_used: float
    alert_generated: Optional[DecayAlert] = None
    calculation_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# Type alias for alert handlers
DecayAlertHandler = Callable[[DecayAlert], None]


class SkillDecayTracker:
    """
    Tracks and calculates skill decay for persona traits.

    Uses exponential decay model to simulate natural skill degradation
    when traits are not practiced. Generates alerts when skills fall
    below configured thresholds.
    """

    # Default decay parameters by category
    DEFAULT_CATEGORY_RATES: Dict[TraitCategory, DecayParameters] = {
        TraitCategory.TECHNICAL: DecayParameters(decay_rate=0.03, warning_threshold=0.4),
        TraitCategory.SOFT_SKILL: DecayParameters(decay_rate=0.01, warning_threshold=0.25),
        TraitCategory.DOMAIN: DecayParameters(decay_rate=0.02, warning_threshold=0.3),
        TraitCategory.LEADERSHIP: DecayParameters(decay_rate=0.015, warning_threshold=0.35),
        TraitCategory.ANALYTICAL: DecayParameters(decay_rate=0.025, warning_threshold=0.35),
        TraitCategory.CREATIVE: DecayParameters(decay_rate=0.02, warning_threshold=0.3),
        TraitCategory.CUSTOM: DecayParameters(decay_rate=0.02, warning_threshold=0.3),
    }

    def __init__(
        self,
        trait_manager: Optional[TraitManager] = None,
        category_parameters: Optional[Dict[TraitCategory, DecayParameters]] = None,
        calculation_interval_hours: int = 24,
        persistence_path: Optional[Path] = None
    ):
        """
        Initialize the SkillDecayTracker.

        Args:
            trait_manager: TraitManager instance (uses singleton if not provided)
            category_parameters: Custom decay parameters by category
            calculation_interval_hours: How often to run decay calculations
            persistence_path: Path to persist decay state and alerts
        """
        self._trait_manager = trait_manager or get_trait_manager()
        self._category_params = category_parameters or self.DEFAULT_CATEGORY_RATES.copy()
        self._calculation_interval = timedelta(hours=calculation_interval_hours)
        self._persistence_path = persistence_path

        self._alert_handlers: List[DecayAlertHandler] = []
        self._active_alerts: Dict[str, DecayAlert] = {}  # trait_id -> alert
        self._calculation_history: List[DecayCalculationResult] = []
        self._last_calculation: Optional[datetime] = None
        self._lock = threading.RLock()
        self._alert_counter = 0

        # Register for trait events
        self._trait_manager.register_event_handler(self._on_trait_event)

        # Load persisted state
        if persistence_path and persistence_path.exists():
            self._load_state()

        logger.info(
            f"SkillDecayTracker initialized: interval={calculation_interval_hours}h, "
            f"categories={len(self._category_params)}"
        )

    def register_alert_handler(self, handler: DecayAlertHandler) -> None:
        """Register a handler for decay alerts."""
        self._alert_handlers.append(handler)
        logger.debug(f"Registered alert handler: {handler}")

    def _emit_alert(self, alert: DecayAlert) -> None:
        """Emit an alert to all registered handlers."""
        self._active_alerts[alert.trait_id] = alert

        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        logger.info(
            f"Decay alert emitted: {alert.alert_level.value} for trait {alert.trait_id} "
            f"(level: {alert.current_level:.2f})"
        )

    def _on_trait_event(self, event: TraitEvent) -> None:
        """Handle trait events from TraitManager."""
        # Clear alerts for traits that were practiced
        if event.event_type in ("level_changed", "updated"):
            if event.trait_id in self._active_alerts:
                # Check if level increased (practice occurred)
                if event.new_value and event.old_value:
                    new_level = event.new_value if isinstance(event.new_value, float) else 0
                    old_level = event.old_value if isinstance(event.old_value, float) else 0
                    if new_level > old_level:
                        del self._active_alerts[event.trait_id]
                        logger.info(f"Cleared decay alert for trait {event.trait_id} after practice")

    def get_decay_parameters(self, category: TraitCategory) -> DecayParameters:
        """Get decay parameters for a category."""
        return self._category_params.get(category, DecayParameters())

    def set_decay_parameters(
        self,
        category: TraitCategory,
        parameters: DecayParameters
    ) -> None:
        """Set custom decay parameters for a category."""
        parameters.validate()
        self._category_params[category] = parameters
        logger.info(f"Updated decay parameters for {category.value}")

    def calculate_decay(
        self,
        trait: Trait,
        as_of: Optional[datetime] = None
    ) -> DecayCalculationResult:
        """
        Calculate decay for a single trait.

        Args:
            trait: The trait to calculate decay for
            as_of: Calculate decay as of this time (default: now)

        Returns:
            DecayCalculationResult with decay information
        """
        as_of = as_of or datetime.utcnow()
        params = self.get_decay_parameters(trait.category)

        # Calculate days since last practice
        if trait.metrics.last_practice:
            last_practice = datetime.fromisoformat(trait.metrics.last_practice)
            days_since = (as_of - last_practice).total_seconds() / 86400.0
        else:
            # Use trait creation date if never practiced
            created = datetime.fromisoformat(trait.created_at)
            days_since = (as_of - created).total_seconds() / 86400.0

        # Apply exponential decay: L(t) = L0 * e^(-λt)
        original_level = trait.level
        decayed_level = original_level * math.exp(-params.decay_rate * days_since)

        # Enforce minimum level
        decayed_level = max(params.min_decay_level, decayed_level)

        decay_amount = original_level - decayed_level

        # Calculate projected level in 30 days
        projected_30d = decayed_level * math.exp(-params.decay_rate * 30)

        # Generate alert if needed
        alert = None
        if decayed_level <= params.critical_threshold:
            alert = self._create_alert(
                trait, decayed_level, original_level,
                DecayAlertLevel.CRITICAL, days_since, projected_30d
            )
        elif decayed_level <= params.warning_threshold:
            alert = self._create_alert(
                trait, decayed_level, original_level,
                DecayAlertLevel.WARNING, days_since, projected_30d
            )

        result = DecayCalculationResult(
            trait_id=trait.id,
            original_level=original_level,
            decayed_level=decayed_level,
            decay_amount=decay_amount,
            days_since_practice=days_since,
            decay_rate_used=params.decay_rate,
            alert_generated=alert
        )

        return result

    def _create_alert(
        self,
        trait: Trait,
        current_level: float,
        previous_level: float,
        alert_level: DecayAlertLevel,
        days_since: float,
        projected_30d: float
    ) -> DecayAlert:
        """Create a decay alert."""
        self._alert_counter += 1
        alert_id = f"decay_alert_{self._alert_counter}"

        if alert_level == DecayAlertLevel.CRITICAL:
            message = f"CRITICAL: Skill '{trait.name}' has degraded to {current_level:.1%}"
            recommendation = "Immediate practice session recommended to prevent skill loss"
        else:
            message = f"WARNING: Skill '{trait.name}' is declining ({current_level:.1%})"
            recommendation = "Schedule practice session within the next week"

        return DecayAlert(
            alert_id=alert_id,
            trait_id=trait.id,
            persona_id=trait.persona_id,
            trait_name=trait.name,
            current_level=current_level,
            previous_level=previous_level,
            alert_level=alert_level,
            message=message,
            recommendation=recommendation,
            days_since_practice=days_since,
            projected_decay_30d=projected_30d
        )

    def run_decay_calculation(
        self,
        persona_id: Optional[str] = None,
        apply_decay: bool = False
    ) -> List[DecayCalculationResult]:
        """
        Run decay calculation for traits.

        Args:
            persona_id: Calculate for specific persona (all if None)
            apply_decay: If True, actually update trait levels

        Returns:
            List of DecayCalculationResult objects
        """
        with self._lock:
            results = []

            if persona_id:
                traits = self._trait_manager.get_traits_by_persona(persona_id)
            else:
                traits = list(self._trait_manager._traits.values())

            for trait in traits:
                # Skip mastered or inactive traits
                if trait.status in (TraitStatus.MASTERED, TraitStatus.INACTIVE):
                    continue

                result = self.calculate_decay(trait)
                results.append(result)

                # Emit alert if generated
                if result.alert_generated:
                    self._emit_alert(result.alert_generated)

                # Apply decay if requested
                if apply_decay and result.decay_amount > 0.001:
                    trait.update_level(result.decayed_level, reason="decay")
                    trait.status = TraitStatus.DECAYING

            # Update calculation history
            self._calculation_history.extend(results)
            if len(self._calculation_history) > 1000:
                self._calculation_history = self._calculation_history[-1000:]

            self._last_calculation = datetime.utcnow()
            self._save_state()

            logger.info(
                f"Decay calculation complete: {len(results)} traits processed, "
                f"{sum(1 for r in results if r.alert_generated)} alerts generated"
            )

            return results

    def get_at_risk_traits(
        self,
        persona_id: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> List[Tuple[Trait, DecayCalculationResult]]:
        """
        Get traits at risk of decay.

        Args:
            persona_id: Filter by persona (all if None)
            threshold: Custom threshold (uses warning threshold if None)

        Returns:
            List of (Trait, DecayCalculationResult) tuples
        """
        at_risk = []

        if persona_id:
            traits = self._trait_manager.get_traits_by_persona(persona_id)
        else:
            traits = list(self._trait_manager._traits.values())

        for trait in traits:
            if trait.status in (TraitStatus.MASTERED, TraitStatus.INACTIVE):
                continue

            result = self.calculate_decay(trait)
            params = self.get_decay_parameters(trait.category)
            check_threshold = threshold or params.warning_threshold

            if result.decayed_level <= check_threshold:
                at_risk.append((trait, result))

        # Sort by decay level (most at risk first)
        at_risk.sort(key=lambda x: x[1].decayed_level)

        return at_risk

    def get_decay_statistics(self) -> Dict[str, Any]:
        """Get aggregate decay statistics."""
        with self._lock:
            return {
                "total_calculations": len(self._calculation_history),
                "active_alerts": len(self._active_alerts),
                "alerts_by_level": {
                    level.value: sum(
                        1 for a in self._active_alerts.values()
                        if a.alert_level == level
                    )
                    for level in DecayAlertLevel
                },
                "last_calculation": self._last_calculation.isoformat() if self._last_calculation else None,
                "calculation_interval_hours": self._calculation_interval.total_seconds() / 3600
            }

    def get_active_alerts(
        self,
        persona_id: Optional[str] = None,
        min_level: Optional[DecayAlertLevel] = None
    ) -> List[DecayAlert]:
        """Get active decay alerts."""
        alerts = list(self._active_alerts.values())

        if persona_id:
            alerts = [a for a in alerts if a.persona_id == persona_id]

        if min_level:
            level_order = [
                DecayAlertLevel.INFO,
                DecayAlertLevel.WARNING,
                DecayAlertLevel.CRITICAL,
                DecayAlertLevel.EMERGENCY
            ]
            min_idx = level_order.index(min_level)
            alerts = [
                a for a in alerts
                if level_order.index(a.alert_level) >= min_idx
            ]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for trait_id, alert in self._active_alerts.items():
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow().isoformat()
                self._save_state()
                return True
        return False

    def _save_state(self) -> None:
        """Save tracker state to disk."""
        if not self._persistence_path:
            return

        try:
            data = {
                "active_alerts": {
                    tid: alert.to_dict()
                    for tid, alert in self._active_alerts.items()
                },
                "last_calculation": self._last_calculation.isoformat() if self._last_calculation else None,
                "alert_counter": self._alert_counter,
                "saved_at": datetime.utcnow().isoformat()
            }

            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save decay tracker state: {e}")

    def _load_state(self) -> None:
        """Load tracker state from disk."""
        try:
            with open(self._persistence_path, "r") as f:
                data = json.load(f)

            self._alert_counter = data.get("alert_counter", 0)

            if data.get("last_calculation"):
                self._last_calculation = datetime.fromisoformat(data["last_calculation"])

            # Restore alerts
            for tid, alert_data in data.get("active_alerts", {}).items():
                alert_data["alert_level"] = DecayAlertLevel(alert_data["alert_level"])
                self._active_alerts[tid] = DecayAlert(**alert_data)

            logger.info(f"Loaded decay tracker state: {len(self._active_alerts)} alerts")
        except Exception as e:
            logger.error(f"Failed to load decay tracker state: {e}")


# Singleton instance
_decay_tracker: Optional[SkillDecayTracker] = None
_decay_tracker_lock = threading.Lock()


def get_skill_decay_tracker(
    trait_manager: Optional[TraitManager] = None,
    force_new: bool = False
) -> SkillDecayTracker:
    """
    Get the singleton SkillDecayTracker instance.

    Args:
        trait_manager: Optional TraitManager instance
        force_new: Force creation of new instance

    Returns:
        SkillDecayTracker instance
    """
    global _decay_tracker

    with _decay_tracker_lock:
        if _decay_tracker is None or force_new:
            _decay_tracker = SkillDecayTracker(trait_manager=trait_manager)
        return _decay_tracker
