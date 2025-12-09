#!/usr/bin/env python3
"""
Persona Registry: Central registry for AI personas and their capabilities.

This module provides registration, discovery, and lifecycle management
for AI personas used in the Maestro orchestration system.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PersonaStatus(Enum):
    """Status of a registered persona."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


@dataclass
class ModelConfig:
    """Configuration for the AI model backing a persona."""
    model_id: str
    provider: str = "anthropic"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaDefinition:
    """
    Definition of an AI persona.

    A persona encapsulates the identity, capabilities, and configuration
    of an AI agent within the Maestro system.
    """
    id: str
    name: str
    description: str
    capabilities: List[str]
    system_prompt: str
    model_config: ModelConfig
    status: PersonaStatus = PersonaStatus.ACTIVE
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def has_capability(self, capability: str) -> bool:
        """Check if persona has a specific capability."""
        return capability.lower() in [c.lower() for c in self.capabilities]

    def has_any_capability(self, capabilities: List[str]) -> bool:
        """Check if persona has any of the given capabilities."""
        lower_caps = {c.lower() for c in self.capabilities}
        return any(c.lower() in lower_caps for c in capabilities)

    def has_all_capabilities(self, capabilities: List[str]) -> bool:
        """Check if persona has all of the given capabilities."""
        lower_caps = {c.lower() for c in self.capabilities}
        return all(c.lower() in lower_caps for c in capabilities)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['status'] = self.status.value
        data['model_config'] = asdict(self.model_config)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaDefinition':
        """Create PersonaDefinition from dictionary."""
        data = dict(data)  # Copy to avoid mutation
        if isinstance(data.get('status'), str):
            data['status'] = PersonaStatus(data['status'])
        if isinstance(data.get('model_config'), dict):
            data['model_config'] = ModelConfig(**data['model_config'])
        return cls(**data)


class PersonaRegistry:
    """
    Central registry for AI personas.

    Provides registration, discovery, and lifecycle management with
    support for capability-based matching and persistence.
    """

    _instance: Optional['PersonaRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the persona registry.

        Args:
            persistence_path: Path to JSON file for persistence
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._personas: Dict[str, PersonaDefinition] = {}
        self._registry_lock = threading.RLock()
        self._persistence_path = Path(persistence_path) if persistence_path else None
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> persona_ids
        self._initialized = True

        # Load persisted personas
        if self._persistence_path and self._persistence_path.exists():
            self._load_from_file()

        # Register default personas
        self._register_defaults()

        logger.info("PersonaRegistry initialized")

    def register(self, persona: PersonaDefinition, overwrite: bool = False) -> bool:
        """
        Register a new persona.

        Args:
            persona: PersonaDefinition to register
            overwrite: Allow overwriting existing persona

        Returns:
            True if registration successful
        """
        with self._registry_lock:
            if persona.id in self._personas and not overwrite:
                logger.warning(f"Persona already registered: {persona.id}")
                return False

            # Update timestamp if overwriting
            if persona.id in self._personas:
                persona.updated_at = datetime.utcnow().isoformat()

            self._personas[persona.id] = persona
            self._update_capability_index(persona)
            self._persist()

            logger.info(f"Persona registered: {persona.id} ({persona.name})")
            return True

    def unregister(self, persona_id: str) -> bool:
        """
        Remove a persona from the registry.

        Args:
            persona_id: ID of persona to remove

        Returns:
            True if persona was found and removed
        """
        with self._registry_lock:
            if persona_id not in self._personas:
                return False

            persona = self._personas.pop(persona_id)
            self._remove_from_capability_index(persona)
            self._persist()

            logger.info(f"Persona unregistered: {persona_id}")
            return True

    def get(self, persona_id: str) -> Optional[PersonaDefinition]:
        """
        Get a persona by ID.

        Args:
            persona_id: ID of persona to retrieve

        Returns:
            PersonaDefinition or None if not found
        """
        with self._registry_lock:
            return self._personas.get(persona_id)

    def list_all(self, status: Optional[PersonaStatus] = None) -> List[PersonaDefinition]:
        """
        List all registered personas.

        Args:
            status: Filter by status (optional)

        Returns:
            List of PersonaDefinitions
        """
        with self._registry_lock:
            personas = list(self._personas.values())
            if status:
                personas = [p for p in personas if p.status == status]
            return personas

    def find_by_capability(self, capability: str) -> List[PersonaDefinition]:
        """
        Find personas that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching PersonaDefinitions
        """
        with self._registry_lock:
            cap_lower = capability.lower()
            persona_ids = self._capability_index.get(cap_lower, set())
            return [self._personas[pid] for pid in persona_ids if pid in self._personas]

    def find_by_capabilities(
        self,
        capabilities: List[str],
        match_all: bool = True
    ) -> List[PersonaDefinition]:
        """
        Find personas by multiple capabilities.

        Args:
            capabilities: List of capabilities to match
            match_all: If True, persona must have all capabilities

        Returns:
            List of matching PersonaDefinitions
        """
        with self._registry_lock:
            if match_all:
                # Intersection of all capability sets
                persona_sets = [
                    self._capability_index.get(c.lower(), set())
                    for c in capabilities
                ]
                if not persona_sets:
                    return []
                matching_ids = set.intersection(*persona_sets)
            else:
                # Union of all capability sets
                matching_ids: Set[str] = set()
                for cap in capabilities:
                    matching_ids.update(self._capability_index.get(cap.lower(), set()))

            return [self._personas[pid] for pid in matching_ids if pid in self._personas]

    def find_by_tag(self, tag: str) -> List[PersonaDefinition]:
        """
        Find personas by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching PersonaDefinitions
        """
        with self._registry_lock:
            tag_lower = tag.lower()
            return [p for p in self._personas.values() if tag_lower in [t.lower() for t in p.tags]]

    def update_status(self, persona_id: str, status: PersonaStatus) -> bool:
        """
        Update persona status.

        Args:
            persona_id: ID of persona to update
            status: New status

        Returns:
            True if update successful
        """
        with self._registry_lock:
            if persona_id not in self._personas:
                return False

            self._personas[persona_id].status = status
            self._personas[persona_id].updated_at = datetime.utcnow().isoformat()
            self._persist()

            logger.info(f"Persona {persona_id} status updated to {status.value}")
            return True

    def get_all_capabilities(self) -> List[str]:
        """Get list of all unique capabilities across all personas."""
        with self._registry_lock:
            return list(self._capability_index.keys())

    def _update_capability_index(self, persona: PersonaDefinition) -> None:
        """Update capability index for a persona."""
        for cap in persona.capabilities:
            cap_lower = cap.lower()
            if cap_lower not in self._capability_index:
                self._capability_index[cap_lower] = set()
            self._capability_index[cap_lower].add(persona.id)

    def _remove_from_capability_index(self, persona: PersonaDefinition) -> None:
        """Remove persona from capability index."""
        for cap in persona.capabilities:
            cap_lower = cap.lower()
            if cap_lower in self._capability_index:
                self._capability_index[cap_lower].discard(persona.id)
                if not self._capability_index[cap_lower]:
                    del self._capability_index[cap_lower]

    def _persist(self) -> None:
        """Persist registry to file."""
        if not self._persistence_path:
            return

        data = {
            'personas': [p.to_dict() for p in self._personas.values()],
            'updated_at': datetime.utcnow().isoformat()
        }

        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persistence_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_file(self) -> None:
        """Load registry from file."""
        try:
            with open(self._persistence_path, 'r') as f:
                data = json.load(f)

            for persona_data in data.get('personas', []):
                persona = PersonaDefinition.from_dict(persona_data)
                self._personas[persona.id] = persona
                self._update_capability_index(persona)

            logger.info(f"Loaded {len(self._personas)} personas from {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load personas: {e}")

    def _register_defaults(self) -> None:
        """Register default system personas."""
        defaults = [
            PersonaDefinition(
                id="architect",
                name="Software Architect",
                description="Designs system architecture and makes high-level technical decisions",
                capabilities=["architecture", "design", "review", "planning"],
                system_prompt="You are a senior software architect...",
                model_config=ModelConfig(model_id="claude-3-opus-20240229"),
                tags=["system", "default"]
            ),
            PersonaDefinition(
                id="developer",
                name="Software Developer",
                description="Implements features and writes production code",
                capabilities=["coding", "implementation", "debugging", "refactoring"],
                system_prompt="You are an experienced software developer...",
                model_config=ModelConfig(model_id="claude-3-sonnet-20240229"),
                tags=["system", "default"]
            ),
            PersonaDefinition(
                id="qa_engineer",
                name="QA Engineer",
                description="Tests software and ensures quality standards",
                capabilities=["testing", "qa", "validation", "bug-finding"],
                system_prompt="You are a QA engineer focused on quality...",
                model_config=ModelConfig(model_id="claude-3-sonnet-20240229"),
                tags=["system", "default"]
            ),
            PersonaDefinition(
                id="tech_writer",
                name="Technical Writer",
                description="Creates documentation and technical content",
                capabilities=["documentation", "writing", "explanation"],
                system_prompt="You are a technical writer creating clear documentation...",
                model_config=ModelConfig(model_id="claude-3-haiku-20240307"),
                tags=["system", "default"]
            )
        ]

        for persona in defaults:
            if persona.id not in self._personas:
                self._personas[persona.id] = persona
                self._update_capability_index(persona)


# Convenience function to get singleton instance
def get_persona_registry(**kwargs) -> PersonaRegistry:
    """Get the singleton PersonaRegistry instance."""
    return PersonaRegistry(**kwargs)
