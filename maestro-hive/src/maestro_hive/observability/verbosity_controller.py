"""
VerbosityController - Manages adaptive verbosity levels for the visibility system.

This controller determines whether events should be:
- Logged to JIRA
- Published to Confluence
- Stored in learning stores

Based on the current verbosity level and event type.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Set
from datetime import datetime
import json
import logging
import os

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)


class VerbosityLevel(Enum):
    """
    Verbosity levels for the visibility system.
    
    LEARNING: Maximum capture - log everything for training (first ~1000 events)
    OPTIMIZED: Reduced capture - log major events and novel patterns
    PRODUCTION: Minimal capture - log errors and exceptions only
    """
    LEARNING = "learning"
    OPTIMIZED = "optimized"
    PRODUCTION = "production"
    
    @property
    def numeric_value(self) -> int:
        """Return numeric value for comparison."""
        return {"learning": 1, "optimized": 2, "production": 3}[self.value]


@dataclass
class VerbosityConfig:
    """Configuration for the verbosity controller."""
    current_level: VerbosityLevel = VerbosityLevel.LEARNING
    saturation_threshold: float = 0.95
    min_learning_events: int = 1000
    auto_transition: bool = True
    persist_to_db: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "current_level": self.current_level.value,
            "saturation_threshold": self.saturation_threshold,
            "min_learning_events": self.min_learning_events,
            "auto_transition": self.auto_transition,
            "persist_to_db": self.persist_to_db,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerbosityConfig":
        """Create from dictionary."""
        return cls(
            current_level=VerbosityLevel(data.get("current_level", "learning")),
            saturation_threshold=data.get("saturation_threshold", 0.95),
            min_learning_events=data.get("min_learning_events", 1000),
            auto_transition=data.get("auto_transition", True),
            persist_to_db=data.get("persist_to_db", True),
        )


class VerbosityController:
    """
    Controls verbosity levels for the visibility system.
    
    Determines what events should be logged based on:
    - Current verbosity level
    - Event type
    - Saturation state
    
    Supports persistence to database for distributed deployments.
    """
    
    # Event types that are ALWAYS logged (even in PRODUCTION)
    CRITICAL_EVENTS: Set[str] = {
        "error_recovered",
        "quality_gate_failed",
        "security_issue",
        "critical_failure",
    }
    
    # Event types logged in OPTIMIZED and LEARNING modes
    MAJOR_EVENTS: Set[str] = {
        "blueprint_selected",
        "persona_completed",
        "quality_gate_evaluated",
        "artifact_generated",
    }
    
    # Event types logged only in LEARNING mode
    DETAILED_EVENTS: Set[str] = {
        "contract_negotiated",
        "persona_started",
        "template_applied",
        "dependency_resolved",
        "retry_attempted",
    }
    
    def __init__(
        self,
        config: Optional[VerbosityConfig] = None,
        redis_url: Optional[str] = None,
        db_connection: Optional[Any] = None,
    ):
        self._config = config or VerbosityConfig()
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._db = db_connection
        self._redis = None
        self._event_count = 0
        self._saturation_score = 0.0
        self._last_check = datetime.utcnow()
        
    @property
    def current_level(self) -> VerbosityLevel:
        """Get current verbosity level."""
        return self._config.current_level
    
    @property
    def config(self) -> VerbosityConfig:
        """Get current configuration."""
        return self._config
    
    def set_level(self, level: VerbosityLevel) -> None:
        """
        Set verbosity level.
        
        Args:
            level: New verbosity level
        """
        old_level = self._config.current_level
        self._config.current_level = level
        
        logger.info(f"Verbosity level changed: {old_level.value} -> {level.value}")
        
        if self._config.persist_to_db and self._db:
            self._persist_config()
    
    def should_log_to_jira(self, event_type: str) -> bool:
        """
        Determine if an event should create a JIRA subtask.
        
        Args:
            event_type: Type of decision event
            
        Returns:
            True if event should be logged to JIRA
        """
        level = self._config.current_level
        
        # Critical events always logged
        if event_type in self.CRITICAL_EVENTS:
            return True
        
        # Production mode: only critical events
        if level == VerbosityLevel.PRODUCTION:
            return False
        
        # Optimized mode: major events only
        if level == VerbosityLevel.OPTIMIZED:
            return event_type in self.MAJOR_EVENTS
        
        # Learning mode: all events
        return True
    
    def should_create_confluence_page(self, page_type: str) -> bool:
        """
        Determine if a Confluence page should be created.
        
        Args:
            page_type: Type of page (summary, detail, artifact)
            
        Returns:
            True if page should be created
        """
        level = self._config.current_level
        
        if level == VerbosityLevel.PRODUCTION:
            return page_type == "error_report"
        
        if level == VerbosityLevel.OPTIMIZED:
            return page_type in {"summary", "milestone", "error_report"}
        
        # Learning mode: all pages
        return True
    
    def should_store_learning(self, entry_type: str) -> bool:
        """
        Determine if an entry should be stored in learning stores.
        
        Args:
            entry_type: Type of learning entry
            
        Returns:
            True if entry should be stored
        """
        level = self._config.current_level
        
        if level == VerbosityLevel.PRODUCTION:
            return entry_type == "exception"
        
        if level == VerbosityLevel.OPTIMIZED:
            return entry_type in {"novel_pattern", "quality_issue", "exception"}
        
        return True
    
    def filter_event(self, event_type: str, verbosity_required: VerbosityLevel) -> bool:
        """
        Filter an event based on current verbosity level.
        
        Args:
            event_type: Type of event
            verbosity_required: Minimum verbosity required for this event
            
        Returns:
            True if event should be processed
        """
        current_numeric = self._config.current_level.numeric_value
        required_numeric = verbosity_required.numeric_value
        
        # Event passes if current level is at or below required level
        # (lower numeric = more verbose)
        return current_numeric <= required_numeric
    
    def check_saturation(self) -> bool:
        """
        Check if saturation threshold has been reached.
        
        Returns:
            True if saturation threshold exceeded
        """
        return self._saturation_score >= self._config.saturation_threshold
    
    def update_saturation(self, score: float) -> None:
        """
        Update saturation score.
        
        Args:
            score: New saturation score (0-1)
        """
        self._saturation_score = min(1.0, max(0.0, score))
        
        # Check for auto-transition
        if self._config.auto_transition and self.check_saturation():
            self._auto_transition()
    
    def _auto_transition(self) -> None:
        """Auto-transition to next verbosity level if saturated."""
        current = self._config.current_level
        
        if current == VerbosityLevel.LEARNING:
            if self._event_count >= self._config.min_learning_events:
                self.set_level(VerbosityLevel.OPTIMIZED)
                logger.info(
                    f"Auto-transitioned to OPTIMIZED "
                    f"(events: {self._event_count}, saturation: {self._saturation_score:.2%})"
                )
        elif current == VerbosityLevel.OPTIMIZED:
            self.set_level(VerbosityLevel.PRODUCTION)
            logger.info(
                f"Auto-transitioned to PRODUCTION "
                f"(saturation: {self._saturation_score:.2%})"
            )
    
    def record_event(self) -> None:
        """Record that an event was processed."""
        self._event_count += 1
    
    def _persist_config(self) -> None:
        """Persist configuration to database."""
        if not self._db:
            return
        
        try:
            # Implementation depends on DB type
            # For SQLAlchemy:
            # self._db.execute(
            #     "INSERT INTO verbosity_config (...) VALUES (...) ON CONFLICT DO UPDATE ..."
            # )
            pass
        except Exception as e:
            logger.error(f"Failed to persist verbosity config: {e}")
    
    async def load_config_from_db(self) -> None:
        """Load configuration from database."""
        if not self._db:
            return
        
        try:
            # Implementation depends on DB type
            pass
        except Exception as e:
            logger.error(f"Failed to load verbosity config: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status summary."""
        return {
            "level": self._config.current_level.value,
            "saturation_score": self._saturation_score,
            "event_count": self._event_count,
            "saturation_threshold": self._config.saturation_threshold,
            "is_saturated": self.check_saturation(),
            "auto_transition": self._config.auto_transition,
        }
