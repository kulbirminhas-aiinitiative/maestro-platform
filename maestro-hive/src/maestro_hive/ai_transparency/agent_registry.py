"""
Agent Registry Module - MD-2792

Manages AI agent configurations, registration, and lifecycle.
Provides centralized agent tracking for transparency and compliance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of an AI agent."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class AgentCapability(Enum):
    """Capabilities that an AI agent can have."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DATA_ANALYSIS = "data_analysis"
    DECISION_SUPPORT = "decision_support"
    AUTOMATION = "automation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


@dataclass
class AgentConfig:
    """
    Configuration for an AI agent.

    Contains all metadata and settings for agent transparency compliance.
    """
    # Identity
    agent_id: str
    name: str
    display_name: str
    description: str

    # Provider information
    provider: str = "Anthropic"
    model_name: str = "Claude"
    model_version: Optional[str] = None

    # Status and capabilities
    status: AgentStatus = AgentStatus.ACTIVE
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Visual identity
    avatar_url: Optional[str] = None
    badge_color: str = "#6366f1"  # Indigo

    # Transparency settings
    disclosure_text: str = "AI-generated content"
    show_confidence: bool = True
    show_reasoning: bool = False

    # Compliance
    eu_ai_act_category: str = "general_purpose"
    risk_level: str = "limited"
    human_oversight_required: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent config to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "avatar_url": self.avatar_url,
            "badge_color": self.badge_color,
            "disclosure_text": self.disclosure_text,
            "show_confidence": self.show_confidence,
            "show_reasoning": self.show_reasoning,
            "eu_ai_act_category": self.eu_ai_act_category,
            "risk_level": self.risk_level,
            "human_oversight_required": self.human_oversight_required,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create agent config from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description", ""),
            provider=data.get("provider", "Anthropic"),
            model_name=data.get("model_name", "Claude"),
            model_version=data.get("model_version"),
            status=AgentStatus(data.get("status", "active")),
            capabilities=[AgentCapability(c) for c in data.get("capabilities", [])],
            avatar_url=data.get("avatar_url"),
            badge_color=data.get("badge_color", "#6366f1"),
            disclosure_text=data.get("disclosure_text", "AI-generated content"),
            show_confidence=data.get("show_confidence", True),
            show_reasoning=data.get("show_reasoning", False),
            eu_ai_act_category=data.get("eu_ai_act_category", "general_purpose"),
            risk_level=data.get("risk_level", "limited"),
            human_oversight_required=data.get("human_oversight_required", True),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class AgentRegistry:
    """
    Central registry for AI agents.

    Manages agent registration, lookup, and lifecycle with full
    transparency and compliance tracking.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the agent registry.

        Args:
            storage_path: Optional path to persist registry state
        """
        self._agents: Dict[str, AgentConfig] = {}
        self._storage_path = storage_path
        self._event_listeners: List[callable] = []

        # Load persisted state if available
        if storage_path:
            self._load_state()

    def register(self, config: AgentConfig) -> str:
        """
        Register a new agent.

        Args:
            config: Agent configuration

        Returns:
            Agent ID

        Raises:
            ValueError: If agent with same ID already exists
        """
        if config.agent_id in self._agents:
            raise ValueError(f"Agent with ID {config.agent_id} already registered")

        self._agents[config.agent_id] = config
        self._notify_listeners("registered", config)
        self._save_state()

        logger.info(f"Registered agent: {config.name} ({config.agent_id})")
        return config.agent_id

    def register_new(
        self,
        name: str,
        display_name: str,
        description: str,
        **kwargs: Any
    ) -> AgentConfig:
        """
        Create and register a new agent with auto-generated ID.

        Args:
            name: Agent name (internal)
            display_name: Display name for UI
            description: Agent description
            **kwargs: Additional agent configuration

        Returns:
            Created AgentConfig
        """
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        config = AgentConfig(
            agent_id=agent_id,
            name=name,
            display_name=display_name,
            description=description,
            **kwargs
        )
        self.register(config)
        return config

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id in self._agents:
            config = self._agents.pop(agent_id)
            self._notify_listeners("unregistered", config)
            self._save_state()
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False

    def get(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Get agent configuration by ID.

        Args:
            agent_id: Agent ID

        Returns:
            AgentConfig if found, None otherwise
        """
        return self._agents.get(agent_id)

    def get_by_name(self, name: str) -> Optional[AgentConfig]:
        """
        Get agent configuration by name.

        Args:
            name: Agent name

        Returns:
            AgentConfig if found, None otherwise
        """
        for config in self._agents.values():
            if config.name == name:
                return config
        return None

    def list_all(self) -> List[AgentConfig]:
        """Get all registered agents."""
        return list(self._agents.values())

    def list_active(self) -> List[AgentConfig]:
        """Get all active agents."""
        return [a for a in self._agents.values() if a.status == AgentStatus.ACTIVE]

    def list_by_capability(self, capability: AgentCapability) -> List[AgentConfig]:
        """
        Get agents with a specific capability.

        Args:
            capability: Required capability

        Returns:
            List of agents with the capability
        """
        return [
            a for a in self._agents.values()
            if capability in a.capabilities and a.status == AgentStatus.ACTIVE
        ]

    def list_by_tag(self, tag: str) -> List[AgentConfig]:
        """
        Get agents with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of agents with the tag
        """
        return [a for a in self._agents.values() if tag in a.tags]

    def update(self, agent_id: str, **kwargs: Any) -> Optional[AgentConfig]:
        """
        Update agent configuration.

        Args:
            agent_id: Agent ID
            **kwargs: Fields to update

        Returns:
            Updated AgentConfig if found, None otherwise
        """
        if agent_id not in self._agents:
            return None

        config = self._agents[agent_id]

        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()
        self._notify_listeners("updated", config)
        self._save_state()

        logger.info(f"Updated agent: {agent_id}")
        return config

    def set_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update agent status.

        Args:
            agent_id: Agent ID
            status: New status

        Returns:
            True if updated, False if not found
        """
        result = self.update(agent_id, status=status)
        return result is not None

    def add_listener(self, listener: callable) -> None:
        """Add event listener for registry changes."""
        self._event_listeners.append(listener)

    def remove_listener(self, listener: callable) -> None:
        """Remove event listener."""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    def _notify_listeners(self, event: str, config: AgentConfig) -> None:
        """Notify all listeners of an event."""
        for listener in self._event_listeners:
            try:
                listener(event, config)
            except Exception as e:
                logger.error(f"Error in registry listener: {e}")

    def _save_state(self) -> None:
        """Save registry state to storage."""
        if not self._storage_path:
            return

        try:
            data = {
                "version": "1.0.0",
                "agents": {
                    aid: config.to_dict()
                    for aid, config in self._agents.items()
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            with open(self._storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry state: {e}")

    def _load_state(self) -> None:
        """Load registry state from storage."""
        if not self._storage_path:
            return

        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)

            for agent_id, agent_data in data.get("agents", {}).items():
                self._agents[agent_id] = AgentConfig.from_dict(agent_data)

            logger.info(f"Loaded {len(self._agents)} agents from storage")
        except FileNotFoundError:
            logger.debug("No existing registry state found")
        except Exception as e:
            logger.error(f"Failed to load registry state: {e}")

    def export_registry(self) -> Dict[str, Any]:
        """
        Export full registry for backup or audit.

        Returns:
            Complete registry data as dictionary
        """
        return {
            "version": "1.0.0",
            "export_time": datetime.utcnow().isoformat(),
            "agent_count": len(self._agents),
            "agents": {
                aid: config.to_dict()
                for aid, config in self._agents.items()
            }
        }

    def import_registry(self, data: Dict[str, Any], merge: bool = False) -> int:
        """
        Import registry data.

        Args:
            data: Registry data to import
            merge: If True, merge with existing. If False, replace.

        Returns:
            Number of agents imported
        """
        if not merge:
            self._agents.clear()

        imported = 0
        for agent_id, agent_data in data.get("agents", {}).items():
            if agent_id not in self._agents or not merge:
                self._agents[agent_id] = AgentConfig.from_dict(agent_data)
                imported += 1

        self._save_state()
        logger.info(f"Imported {imported} agents")
        return imported

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        status_counts = {}
        capability_counts = {}

        for config in self._agents.values():
            # Count by status
            status = config.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            # Count by capability
            for cap in config.capabilities:
                capability_counts[cap.value] = capability_counts.get(cap.value, 0) + 1

        return {
            "total_agents": len(self._agents),
            "by_status": status_counts,
            "by_capability": capability_counts,
            "unique_providers": len(set(a.provider for a in self._agents.values())),
        }


# Default registry instance
_default_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get the default agent registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry


def set_registry(registry: AgentRegistry) -> None:
    """Set the default agent registry instance."""
    global _default_registry
    _default_registry = registry
