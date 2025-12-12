#!/usr/bin/env python3
"""
Trait Manager: Central manager for persona trait attributes.

This module provides CRUD operations, validation, and event handling for
persona traits in the Maestro orchestration system. Traits represent
learnable characteristics that can evolve over time.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, TypeVar, Generic
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class TraitCategory(Enum):
    """Categories of traits that can be assigned to personas."""
    TECHNICAL = "technical"  # Programming languages, frameworks, tools
    SOFT_SKILL = "soft_skill"  # Communication, leadership, collaboration
    DOMAIN = "domain"  # Industry/domain knowledge
    LEADERSHIP = "leadership"  # Management and leadership capabilities
    ANALYTICAL = "analytical"  # Problem-solving, data analysis
    CREATIVE = "creative"  # Design, innovation, ideation
    CUSTOM = "custom"  # User-defined traits


class TraitStatus(Enum):
    """Status of a trait assignment."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EVOLVING = "evolving"  # Currently being improved
    DECAYING = "decaying"  # Not practiced recently
    MASTERED = "mastered"  # Reached maximum level


class TraitValidationError(Exception):
    """Raised when trait validation fails."""
    pass


class TraitNotFoundError(Exception):
    """Raised when a trait is not found."""
    pass


@dataclass
class TraitMetrics:
    """Metrics tracking for trait usage and evolution."""
    practice_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_practice_time_hours: float = 0.0
    last_practice: Optional[str] = None
    level_history: List[Dict[str, Any]] = field(default_factory=list)

    def record_practice(
        self,
        success: bool,
        duration_hours: float,
        new_level: float
    ) -> None:
        """Record a practice event for this trait."""
        self.practice_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.total_practice_time_hours += duration_hours
        self.last_practice = datetime.utcnow().isoformat()

        # Track level history
        self.level_history.append({
            "level": new_level,
            "timestamp": self.last_practice,
            "practice_hours": duration_hours
        })

        # Keep only last 100 history entries
        if len(self.level_history) > 100:
            self.level_history = self.level_history[-100:]

    @property
    def success_rate(self) -> float:
        """Calculate the success rate for this trait."""
        if self.practice_count == 0:
            return 0.0
        return self.success_count / self.practice_count


@dataclass
class Trait:
    """
    Definition of a persona trait.

    A trait represents a specific characteristic or capability that
    can be assigned to personas and evolves over time through practice.
    """
    id: str
    name: str
    description: str
    category: TraitCategory
    level: float = 0.5  # 0.0 to 1.0
    min_level: float = 0.0
    max_level: float = 1.0
    status: TraitStatus = TraitStatus.ACTIVE
    persona_id: Optional[str] = None
    parent_trait_id: Optional[str] = None  # For trait hierarchies
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: TraitMetrics = field(default_factory=TraitMetrics)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        """Validate trait after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate trait fields."""
        if not self.id:
            raise TraitValidationError("Trait ID cannot be empty")
        if not self.name:
            raise TraitValidationError("Trait name cannot be empty")
        if not 0.0 <= self.level <= 1.0:
            raise TraitValidationError(f"Trait level must be between 0.0 and 1.0, got {self.level}")
        if self.min_level > self.max_level:
            raise TraitValidationError("min_level cannot be greater than max_level")

    def update_level(self, new_level: float, reason: str = "") -> None:
        """Update the trait level with validation."""
        if not 0.0 <= new_level <= 1.0:
            raise TraitValidationError(f"New level must be between 0.0 and 1.0, got {new_level}")

        clamped_level = max(self.min_level, min(self.max_level, new_level))

        old_level = self.level
        self.level = clamped_level
        self.updated_at = datetime.utcnow().isoformat()

        # Update status based on level
        if clamped_level >= 0.95:
            self.status = TraitStatus.MASTERED
        elif clamped_level < old_level:
            self.status = TraitStatus.DECAYING
        elif clamped_level > old_level:
            self.status = TraitStatus.EVOLVING

        logger.info(
            f"Trait {self.id} level updated: {old_level:.2f} -> {clamped_level:.2f} "
            f"(reason: {reason})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert trait to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "level": self.level,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "status": self.status.value,
            "persona_id": self.persona_id,
            "parent_trait_id": self.parent_trait_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "metrics": asdict(self.metrics),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trait":
        """Create a Trait from dictionary representation."""
        # Handle enums
        if isinstance(data.get("category"), str):
            data["category"] = TraitCategory(data["category"])
        if isinstance(data.get("status"), str):
            data["status"] = TraitStatus(data["status"])

        # Handle metrics
        if isinstance(data.get("metrics"), dict):
            data["metrics"] = TraitMetrics(**data["metrics"])

        return cls(**data)


# Type alias for event handlers
TraitEventHandler = Callable[["TraitEvent"], None]


@dataclass
class TraitEvent:
    """Event emitted when trait state changes."""
    event_type: str  # "created", "updated", "deleted", "level_changed"
    trait_id: str
    persona_id: Optional[str]
    old_value: Optional[Any]
    new_value: Optional[Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TraitManager:
    """
    Central manager for persona traits.

    Provides CRUD operations, validation, event handling, and persistence
    for traits assigned to personas.
    """

    def __init__(
        self,
        persistence_path: Optional[Path] = None,
        max_traits_per_persona: int = 50,
        strict_validation: bool = True
    ):
        """
        Initialize the TraitManager.

        Args:
            persistence_path: Path for trait storage (JSON file)
            max_traits_per_persona: Maximum traits allowed per persona
            strict_validation: Enable strict validation mode
        """
        self._traits: Dict[str, Trait] = {}
        self._persona_traits: Dict[str, Set[str]] = {}  # persona_id -> trait_ids
        self._event_handlers: List[TraitEventHandler] = []
        self._lock = threading.RLock()
        self._persistence_path = persistence_path
        self._max_traits_per_persona = max_traits_per_persona
        self._strict_validation = strict_validation

        # Load existing traits if persistence path exists
        if persistence_path and persistence_path.exists():
            self._load_from_disk()

        logger.info(
            f"TraitManager initialized: persistence={persistence_path}, "
            f"max_traits={max_traits_per_persona}, strict={strict_validation}"
        )

    def register_event_handler(self, handler: TraitEventHandler) -> None:
        """Register an event handler for trait events."""
        self._event_handlers.append(handler)
        logger.debug(f"Registered event handler: {handler}")

    def _emit_event(self, event: TraitEvent) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def create_trait(
        self,
        name: str,
        description: str,
        category: TraitCategory,
        persona_id: Optional[str] = None,
        initial_level: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Trait:
        """
        Create a new trait.

        Args:
            name: Name of the trait
            description: Description of the trait
            category: Category of the trait
            persona_id: Optional persona to assign to
            initial_level: Initial trait level (0.0 to 1.0)
            tags: Optional tags for categorization
            metadata: Optional metadata dictionary

        Returns:
            The created Trait object

        Raises:
            TraitValidationError: If validation fails
        """
        with self._lock:
            # Check persona trait limit
            if persona_id and persona_id in self._persona_traits:
                if len(self._persona_traits[persona_id]) >= self._max_traits_per_persona:
                    raise TraitValidationError(
                        f"Persona {persona_id} has reached max traits limit "
                        f"({self._max_traits_per_persona})"
                    )

            # Generate unique ID
            trait_id = f"trait_{uuid.uuid4().hex[:12]}"

            # Create trait
            trait = Trait(
                id=trait_id,
                name=name,
                description=description,
                category=category,
                level=initial_level,
                persona_id=persona_id,
                tags=tags or [],
                metadata=metadata or {}
            )

            # Store trait
            self._traits[trait_id] = trait

            # Track persona association
            if persona_id:
                if persona_id not in self._persona_traits:
                    self._persona_traits[persona_id] = set()
                self._persona_traits[persona_id].add(trait_id)

            # Emit event
            self._emit_event(TraitEvent(
                event_type="created",
                trait_id=trait_id,
                persona_id=persona_id,
                old_value=None,
                new_value=trait.to_dict()
            ))

            # Persist
            self._save_to_disk()

            logger.info(f"Created trait: {trait_id} ({name}) for persona {persona_id}")
            return trait

    def get_trait(self, trait_id: str) -> Trait:
        """
        Get a trait by ID.

        Args:
            trait_id: The trait ID

        Returns:
            The Trait object

        Raises:
            TraitNotFoundError: If trait not found
        """
        with self._lock:
            if trait_id not in self._traits:
                raise TraitNotFoundError(f"Trait {trait_id} not found")
            return self._traits[trait_id]

    def get_traits_by_persona(self, persona_id: str) -> List[Trait]:
        """
        Get all traits for a persona.

        Args:
            persona_id: The persona ID

        Returns:
            List of Trait objects
        """
        with self._lock:
            trait_ids = self._persona_traits.get(persona_id, set())
            return [self._traits[tid] for tid in trait_ids if tid in self._traits]

    def get_traits_by_category(self, category: TraitCategory) -> List[Trait]:
        """
        Get all traits in a category.

        Args:
            category: The trait category

        Returns:
            List of Trait objects
        """
        with self._lock:
            return [t for t in self._traits.values() if t.category == category]

    def update_trait(
        self,
        trait_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[float] = None,
        status: Optional[TraitStatus] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Trait:
        """
        Update an existing trait.

        Args:
            trait_id: The trait ID to update
            name: New name (optional)
            description: New description (optional)
            level: New level (optional)
            status: New status (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)

        Returns:
            The updated Trait object

        Raises:
            TraitNotFoundError: If trait not found
        """
        with self._lock:
            if trait_id not in self._traits:
                raise TraitNotFoundError(f"Trait {trait_id} not found")

            trait = self._traits[trait_id]
            old_value = trait.to_dict()

            # Apply updates
            if name is not None:
                trait.name = name
            if description is not None:
                trait.description = description
            if level is not None:
                trait.update_level(level, reason="manual_update")
            if status is not None:
                trait.status = status
            if tags is not None:
                trait.tags = tags
            if metadata is not None:
                trait.metadata.update(metadata)

            trait.updated_at = datetime.utcnow().isoformat()

            # Emit event
            self._emit_event(TraitEvent(
                event_type="updated",
                trait_id=trait_id,
                persona_id=trait.persona_id,
                old_value=old_value,
                new_value=trait.to_dict()
            ))

            # Persist
            self._save_to_disk()

            logger.info(f"Updated trait: {trait_id}")
            return trait

    def delete_trait(self, trait_id: str) -> None:
        """
        Delete a trait.

        Args:
            trait_id: The trait ID to delete

        Raises:
            TraitNotFoundError: If trait not found
        """
        with self._lock:
            if trait_id not in self._traits:
                raise TraitNotFoundError(f"Trait {trait_id} not found")

            trait = self._traits[trait_id]
            old_value = trait.to_dict()

            # Remove from persona tracking
            if trait.persona_id and trait.persona_id in self._persona_traits:
                self._persona_traits[trait.persona_id].discard(trait_id)

            # Delete trait
            del self._traits[trait_id]

            # Emit event
            self._emit_event(TraitEvent(
                event_type="deleted",
                trait_id=trait_id,
                persona_id=trait.persona_id,
                old_value=old_value,
                new_value=None
            ))

            # Persist
            self._save_to_disk()

            logger.info(f"Deleted trait: {trait_id}")

    def record_practice(
        self,
        trait_id: str,
        success: bool,
        duration_hours: float,
        level_change: float = 0.0
    ) -> Trait:
        """
        Record a practice event for a trait.

        Args:
            trait_id: The trait ID
            success: Whether the practice was successful
            duration_hours: Duration of practice in hours
            level_change: Change in level from practice

        Returns:
            The updated Trait object
        """
        with self._lock:
            trait = self.get_trait(trait_id)
            old_level = trait.level

            # Calculate new level
            new_level = max(0.0, min(1.0, trait.level + level_change))

            # Record metrics
            trait.metrics.record_practice(success, duration_hours, new_level)

            # Update level
            if level_change != 0:
                trait.update_level(new_level, reason="practice")

            # Emit level change event
            if old_level != trait.level:
                self._emit_event(TraitEvent(
                    event_type="level_changed",
                    trait_id=trait_id,
                    persona_id=trait.persona_id,
                    old_value=old_level,
                    new_value=trait.level
                ))

            # Persist
            self._save_to_disk()

            return trait

    def get_trait_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics about all traits."""
        with self._lock:
            total = len(self._traits)
            by_category = {}
            by_status = {}
            avg_level = 0.0

            for trait in self._traits.values():
                # By category
                cat = trait.category.value
                by_category[cat] = by_category.get(cat, 0) + 1

                # By status
                status = trait.status.value
                by_status[status] = by_status.get(status, 0) + 1

                # Average level
                avg_level += trait.level

            if total > 0:
                avg_level /= total

            return {
                "total_traits": total,
                "by_category": by_category,
                "by_status": by_status,
                "average_level": avg_level,
                "personas_with_traits": len(self._persona_traits)
            }

    def _save_to_disk(self) -> None:
        """Save traits to disk if persistence is enabled."""
        if not self._persistence_path:
            return

        try:
            data = {
                "traits": {tid: t.to_dict() for tid, t in self._traits.items()},
                "persona_traits": {
                    pid: list(tids) for pid, tids in self._persona_traits.items()
                },
                "saved_at": datetime.utcnow().isoformat()
            }

            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._traits)} traits to {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save traits: {e}")

    def _load_from_disk(self) -> None:
        """Load traits from disk."""
        try:
            with open(self._persistence_path, "r") as f:
                data = json.load(f)

            # Load traits
            for tid, tdata in data.get("traits", {}).items():
                self._traits[tid] = Trait.from_dict(tdata)

            # Load persona mappings
            for pid, tids in data.get("persona_traits", {}).items():
                self._persona_traits[pid] = set(tids)

            logger.info(f"Loaded {len(self._traits)} traits from {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load traits: {e}")


# Singleton instance
_trait_manager: Optional[TraitManager] = None
_trait_manager_lock = threading.Lock()


def get_trait_manager(
    persistence_path: Optional[Path] = None,
    force_new: bool = False
) -> TraitManager:
    """
    Get the singleton TraitManager instance.

    Args:
        persistence_path: Path for trait storage
        force_new: Force creation of new instance

    Returns:
        TraitManager instance
    """
    global _trait_manager

    with _trait_manager_lock:
        if _trait_manager is None or force_new:
            _trait_manager = TraitManager(persistence_path=persistence_path)
        return _trait_manager
