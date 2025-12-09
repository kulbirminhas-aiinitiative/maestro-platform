"""
Saturation Detector

Detects when the system has learned enough patterns and can
transition to reduced verbosity modes.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class VerbosityLevel(Enum):
    """Verbosity levels for the system."""
    LEARNING = "learning"
    OPTIMIZED = "optimized"
    PRODUCTION = "production"


@dataclass
class SaturationStatus:
    """Current saturation status."""
    score: float
    trend: str  # "increasing", "stable", "decreasing"
    is_saturated: bool
    recommended_level: VerbosityLevel
    events_since_last_check: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TransitionEvent:
    """Event triggered on level transition."""
    from_level: VerbosityLevel
    to_level: VerbosityLevel
    reason: str
    saturation_score: float
    timestamp: datetime = field(default_factory=datetime.now)


class SaturationDetector:
    """
    Detects pattern saturation to trigger verbosity transitions.
    
    Monitors novelty scores over time and triggers transitions when
    patterns stabilize (high saturation) or regress (low saturation).
    """
    
    # Transition thresholds
    LEARNING_TO_OPTIMIZED = 0.95
    OPTIMIZED_TO_PRODUCTION = 0.98
    REGRESSION_THRESHOLD = 0.7
    
    # Minimum events before transition
    MIN_LEARNING_EVENTS = 1000
    MIN_STABILITY_EVENTS = 100
    
    def __init__(
        self,
        window_size: int = 500,
        check_interval: int = 100,
        auto_transition: bool = True,
    ):
        """
        Initialize the saturation detector.
        
        Args:
            window_size: Number of scores to track for averaging
            check_interval: Check for transition every N events
            auto_transition: Whether to auto-transition levels
        """
        self.window_size = window_size
        self.check_interval = check_interval
        self.auto_transition = auto_transition
        
        self._current_level = VerbosityLevel.LEARNING
        self._novelty_scores: deque = deque(maxlen=window_size)
        self._events_count = 0
        self._last_transition = datetime.now()
        self._transition_history: List[TransitionEvent] = []
        self._callbacks: List[Callable[[TransitionEvent], None]] = []
        
        logger.info("SaturationDetector initialized")
    
    @property
    def current_level(self) -> VerbosityLevel:
        return self._current_level
    
    @current_level.setter
    def current_level(self, level: VerbosityLevel):
        if level != self._current_level:
            old_level = self._current_level
            self._current_level = level
            logger.info(f"Level changed: {old_level.value} -> {level.value}")
    
    def register_callback(self, callback: Callable[[TransitionEvent], None]):
        """Register callback for transition events."""
        self._callbacks.append(callback)
    
    def record_novelty(self, score: float):
        """
        Record a novelty score from the NoveltyScorer.
        
        Args:
            score: Novelty score (0.0 = familiar, 1.0 = novel)
        """
        self._novelty_scores.append((score, datetime.now()))
        self._events_count += 1
        
        # Periodic saturation check
        if self._events_count % self.check_interval == 0:
            self._check_saturation()
    
    def _calculate_saturation(self) -> float:
        """Calculate current saturation score."""
        if not self._novelty_scores:
            return 0.0
        
        # Saturation = 1 - average novelty
        avg_novelty = sum(s[0] for s in self._novelty_scores) / len(self._novelty_scores)
        return 1.0 - avg_novelty
    
    def _calculate_trend(self) -> str:
        """Calculate saturation trend."""
        if len(self._novelty_scores) < 100:
            return "insufficient_data"
        
        # Compare recent vs older scores
        scores = list(self._novelty_scores)
        mid = len(scores) // 2
        
        old_avg = sum(s[0] for s in scores[:mid]) / mid
        new_avg = sum(s[0] for s in scores[mid:]) / (len(scores) - mid)
        
        # Lower novelty = higher saturation
        if new_avg < old_avg - 0.05:
            return "increasing"
        elif new_avg > old_avg + 0.05:
            return "decreasing"
        return "stable"
    
    def _check_saturation(self):
        """Check if transition is needed."""
        if not self.auto_transition:
            return
        
        saturation = self._calculate_saturation()
        current = self._current_level
        
        # Check for progression
        if current == VerbosityLevel.LEARNING:
            if saturation >= self.LEARNING_TO_OPTIMIZED and self._events_count >= self.MIN_LEARNING_EVENTS:
                self._trigger_transition(
                    VerbosityLevel.OPTIMIZED,
                    f"Saturation {saturation:.2%} >= {self.LEARNING_TO_OPTIMIZED:.0%}",
                    saturation
                )
        
        elif current == VerbosityLevel.OPTIMIZED:
            if saturation >= self.OPTIMIZED_TO_PRODUCTION:
                stable_count = self._count_stable_scores()
                if stable_count >= self.MIN_STABILITY_EVENTS:
                    self._trigger_transition(
                        VerbosityLevel.PRODUCTION,
                        f"Saturation {saturation:.2%} >= {self.OPTIMIZED_TO_PRODUCTION:.0%}, stable for {stable_count} events",
                        saturation
                    )
        
        # Check for regression
        if current in [VerbosityLevel.OPTIMIZED, VerbosityLevel.PRODUCTION]:
            if saturation < self.REGRESSION_THRESHOLD:
                self._trigger_transition(
                    VerbosityLevel.LEARNING,
                    f"Regression detected: saturation {saturation:.2%} < {self.REGRESSION_THRESHOLD:.0%}",
                    saturation
                )
    
    def _count_stable_scores(self) -> int:
        """Count consecutive stable (low novelty) scores."""
        count = 0
        for score, _ in reversed(self._novelty_scores):
            if score < 0.1:  # Very low novelty = stable
                count += 1
            else:
                break
        return count
    
    def _trigger_transition(self, to_level: VerbosityLevel, reason: str, saturation: float):
        """Trigger a level transition."""
        event = TransitionEvent(
            from_level=self._current_level,
            to_level=to_level,
            reason=reason,
            saturation_score=saturation,
        )
        
        self._current_level = to_level
        self._last_transition = datetime.now()
        self._transition_history.append(event)
        
        logger.info(f"Transition: {event.from_level.value} -> {event.to_level.value}: {reason}")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_status(self) -> SaturationStatus:
        """Get current saturation status."""
        saturation = self._calculate_saturation()
        trend = self._calculate_trend()
        
        # Determine recommended level
        if saturation >= self.OPTIMIZED_TO_PRODUCTION:
            recommended = VerbosityLevel.PRODUCTION
        elif saturation >= self.LEARNING_TO_OPTIMIZED:
            recommended = VerbosityLevel.OPTIMIZED
        else:
            recommended = VerbosityLevel.LEARNING
        
        return SaturationStatus(
            score=saturation,
            trend=trend,
            is_saturated=saturation >= self.LEARNING_TO_OPTIMIZED,
            recommended_level=recommended,
            events_since_last_check=self._events_count % self.check_interval,
        )
    
    def force_level(self, level: VerbosityLevel, reason: str = "Manual override"):
        """Force a specific verbosity level."""
        if level != self._current_level:
            saturation = self._calculate_saturation()
            self._trigger_transition(level, reason, saturation)
    
    def get_transition_history(self, limit: int = 10) -> List[TransitionEvent]:
        """Get recent transition history."""
        return self._transition_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "current_level": self._current_level.value,
            "saturation_score": self._calculate_saturation(),
            "trend": self._calculate_trend(),
            "total_events": self._events_count,
            "transitions": len(self._transition_history),
            "auto_transition": self.auto_transition,
        }
