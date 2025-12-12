"""
Agent Registry - Agent Registration and Discovery Service

EPIC: MD-3107 - Agora Phase 2: Guilds & Registry
AC-2: Implement AgentRegistry class with register() and find_agents() methods
AC-4: Agents can check in at startup with their skills and availability

The AgentRegistry maintains a directory of available agents and their capabilities,
enabling dynamic discovery of agents for task assignment.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-105)
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from maestro_hive.agora.guilds import Guild, GuildType

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent availability status."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class AgentCapabilities:
    """
    Capabilities that an agent registers with.

    Attributes:
        guilds: Set of guilds the agent belongs to
        skills: Specific skills the agent has
        languages: Programming languages supported
        frameworks: Frameworks the agent is proficient in
        max_concurrent_tasks: How many tasks can run simultaneously
        cost_per_token: Agent's token cost rate
    """

    guilds: Set[GuildType] = field(default_factory=set)
    skills: Set[str] = field(default_factory=set)
    languages: Set[str] = field(default_factory=set)
    frameworks: Set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 1
    cost_per_token: float = 0.001

    def to_dict(self) -> Dict[str, Any]:
        """Serialize capabilities to dictionary."""
        return {
            "guilds": [g.value for g in self.guilds],
            "skills": list(self.skills),
            "languages": list(self.languages),
            "frameworks": list(self.frameworks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "cost_per_token": self.cost_per_token,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapabilities":
        """Deserialize capabilities from dictionary."""
        return cls(
            guilds={GuildType(g) for g in data.get("guilds", [])},
            skills=set(data.get("skills", [])),
            languages=set(data.get("languages", [])),
            frameworks=set(data.get("frameworks", [])),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 1),
            cost_per_token=data.get("cost_per_token", 0.001),
        )


@dataclass
class RegisteredAgent:
    """
    An agent registered in the Agora.

    Attributes:
        agent_id: Unique identifier for this agent
        name: Human-readable name
        capabilities: Agent's capabilities
        status: Current availability status
        current_tasks: Number of tasks currently assigned
        last_heartbeat: Last time agent checked in
        metadata: Additional agent metadata
    """

    agent_id: str
    name: str
    capabilities: AgentCapabilities
    status: AgentStatus = AgentStatus.AVAILABLE
    current_tasks: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return (
            self.status == AgentStatus.AVAILABLE
            and self.current_tasks < self.capabilities.max_concurrent_tasks
        )

    @property
    def available_capacity(self) -> int:
        """Get number of additional tasks agent can handle."""
        if self.status != AgentStatus.AVAILABLE:
            return 0
        return max(0, self.capabilities.max_concurrent_tasks - self.current_tasks)

    def has_skill(self, skill: str) -> bool:
        """Check if agent has a specific skill."""
        return skill.lower() in {s.lower() for s in self.capabilities.skills}

    def has_guild(self, guild_type: GuildType) -> bool:
        """Check if agent belongs to a guild."""
        return guild_type in self.capabilities.guilds

    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities.to_dict(),
            "status": self.status.value,
            "current_tasks": self.current_tasks,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "registered_at": self.registered_at.isoformat(),
            "metadata": self.metadata,
        }


class AgentRegistry:
    """
    Registry for agent registration and discovery.

    AC-2: Implements register() and find_agents() methods
    AC-4: Supports agent check-in with skills and availability

    This class is thread-safe and can be used as a singleton.
    """

    _instance: Optional["AgentRegistry"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, RegisteredAgent] = {}
        self._agents_lock = threading.RLock()
        self._heartbeat_timeout = timedelta(minutes=5)
        self._on_agent_registered: List[Callable[[RegisteredAgent], None]] = []
        self._on_agent_offline: List[Callable[[RegisteredAgent], None]] = []

        # Initialize Guild definitions
        Guild.initialize()

        logger.info("AgentRegistry initialized")

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def register(
        self,
        name: str,
        capabilities: AgentCapabilities,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RegisteredAgent:
        """
        Register an agent with the Agora.

        AC-2: register() method implementation
        AC-4: Agent check-in at startup with skills and availability

        Args:
            name: Human-readable name for the agent
            capabilities: Agent's capabilities (guilds, skills, etc.)
            agent_id: Optional specific ID (auto-generated if not provided)
            metadata: Additional metadata about the agent

        Returns:
            RegisteredAgent instance
        """
        with self._agents_lock:
            if agent_id is None:
                agent_id = str(uuid.uuid4())

            if agent_id in self._agents:
                # Update existing registration (re-registration)
                agent = self._agents[agent_id]
                agent.capabilities = capabilities
                agent.status = AgentStatus.AVAILABLE
                agent.last_heartbeat = datetime.utcnow()
                if metadata:
                    agent.metadata.update(metadata)
                logger.info(f"Agent re-registered: {name} ({agent_id})")
            else:
                # New registration
                agent = RegisteredAgent(
                    agent_id=agent_id,
                    name=name,
                    capabilities=capabilities,
                    metadata=metadata or {},
                )
                self._agents[agent_id] = agent
                logger.info(f"Agent registered: {name} ({agent_id})")

                # Notify listeners
                for callback in self._on_agent_registered:
                    try:
                        callback(agent)
                    except Exception as e:
                        logger.error(f"Error in registration callback: {e}")

            return agent

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent from the Agora.

        Args:
            agent_id: ID of agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        with self._agents_lock:
            if agent_id in self._agents:
                agent = self._agents.pop(agent_id)
                logger.info(f"Agent unregistered: {agent.name} ({agent_id})")
                return True
            return False

    def heartbeat(self, agent_id: str, status: Optional[AgentStatus] = None) -> bool:
        """
        Update agent's heartbeat timestamp.

        AC-4: Agent check-in mechanism

        Args:
            agent_id: ID of the agent
            status: Optional status update

        Returns:
            True if heartbeat recorded, False if agent not found
        """
        with self._agents_lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            agent.last_heartbeat = datetime.utcnow()
            if status is not None:
                agent.status = status

            return True

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update an agent's status.

        Args:
            agent_id: ID of the agent
            status: New status

        Returns:
            True if updated, False if agent not found
        """
        with self._agents_lock:
            if agent_id not in self._agents:
                return False

            self._agents[agent_id].status = status
            logger.debug(f"Agent {agent_id} status updated to {status.value}")
            return True

    def assign_task(self, agent_id: str) -> bool:
        """
        Increment task count for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            True if task assigned, False if agent not found or unavailable
        """
        with self._agents_lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            if not agent.is_available:
                return False

            agent.current_tasks += 1
            if agent.current_tasks >= agent.capabilities.max_concurrent_tasks:
                agent.status = AgentStatus.BUSY

            logger.debug(f"Task assigned to agent {agent_id}, tasks: {agent.current_tasks}")
            return True

    def complete_task(self, agent_id: str) -> bool:
        """
        Decrement task count for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            True if task completed, False if agent not found
        """
        with self._agents_lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            agent.current_tasks = max(0, agent.current_tasks - 1)

            if agent.status == AgentStatus.BUSY and agent.current_tasks < agent.capabilities.max_concurrent_tasks:
                agent.status = AgentStatus.AVAILABLE

            logger.debug(f"Task completed by agent {agent_id}, tasks: {agent.current_tasks}")
            return True

    def get_agent(self, agent_id: str) -> Optional[RegisteredAgent]:
        """Get an agent by ID."""
        with self._agents_lock:
            return self._agents.get(agent_id)

    def find_agents(
        self,
        guild: Optional[GuildType] = None,
        skill: Optional[str] = None,
        skills: Optional[Set[str]] = None,
        max_cost: Optional[float] = None,
        available_only: bool = True,
        min_capacity: int = 1,
    ) -> List[RegisteredAgent]:
        """
        Find agents matching criteria.

        AC-2: find_agents() method implementation

        Args:
            guild: Filter by guild membership
            skill: Filter by single skill
            skills: Filter by multiple skills (agent must have all)
            max_cost: Maximum cost per token
            available_only: Only return available agents
            min_capacity: Minimum available capacity required

        Returns:
            List of matching agents, sorted by cost (ascending)
        """
        with self._agents_lock:
            results = []

            for agent in self._agents.values():
                # Check availability
                if available_only and not agent.is_available:
                    continue

                # Check capacity
                if agent.available_capacity < min_capacity:
                    continue

                # Check guild membership
                if guild is not None and not agent.has_guild(guild):
                    continue

                # Check single skill
                if skill is not None and not agent.has_skill(skill):
                    continue

                # Check multiple skills
                if skills is not None:
                    agent_skills_lower = {s.lower() for s in agent.capabilities.skills}
                    required_skills_lower = {s.lower() for s in skills}
                    if not required_skills_lower.issubset(agent_skills_lower):
                        continue

                # Check cost constraint
                if max_cost is not None and agent.capabilities.cost_per_token > max_cost:
                    continue

                results.append(agent)

            # Sort by cost (ascending)
            results.sort(key=lambda a: a.capabilities.cost_per_token)

            return results

    def find_by_guilds(
        self,
        guilds: Set[GuildType],
        require_all: bool = False,
        available_only: bool = True,
    ) -> List[RegisteredAgent]:
        """
        Find agents by guild membership.

        Args:
            guilds: Set of guilds to search for
            require_all: If True, agent must belong to all guilds
            available_only: Only return available agents

        Returns:
            List of matching agents
        """
        with self._agents_lock:
            results = []

            for agent in self._agents.values():
                if available_only and not agent.is_available:
                    continue

                agent_guilds = agent.capabilities.guilds

                if require_all:
                    if guilds.issubset(agent_guilds):
                        results.append(agent)
                else:
                    if guilds & agent_guilds:  # Intersection
                        results.append(agent)

            return results

    def get_all_agents(self) -> List[RegisteredAgent]:
        """Get all registered agents."""
        with self._agents_lock:
            return list(self._agents.values())

    def get_available_agents(self) -> List[RegisteredAgent]:
        """Get all available agents."""
        with self._agents_lock:
            return [a for a in self._agents.values() if a.is_available]

    def get_agents_by_status(self, status: AgentStatus) -> List[RegisteredAgent]:
        """Get agents with a specific status."""
        with self._agents_lock:
            return [a for a in self._agents.values() if a.status == status]

    def cleanup_stale_agents(self) -> List[str]:
        """
        Mark agents as offline if they haven't sent a heartbeat recently.

        Returns:
            List of agent IDs that were marked offline
        """
        with self._agents_lock:
            now = datetime.utcnow()
            stale_agents = []

            for agent_id, agent in self._agents.items():
                if agent.status != AgentStatus.OFFLINE:
                    if now - agent.last_heartbeat > self._heartbeat_timeout:
                        agent.status = AgentStatus.OFFLINE
                        stale_agents.append(agent_id)
                        logger.warning(f"Agent {agent.name} ({agent_id}) marked offline (no heartbeat)")

                        # Notify listeners
                        for callback in self._on_agent_offline:
                            try:
                                callback(agent)
                            except Exception as e:
                                logger.error(f"Error in offline callback: {e}")

            return stale_agents

    def on_agent_registered(self, callback: Callable[[RegisteredAgent], None]) -> None:
        """Register a callback for when an agent is registered."""
        self._on_agent_registered.append(callback)

    def on_agent_offline(self, callback: Callable[[RegisteredAgent], None]) -> None:
        """Register a callback for when an agent goes offline."""
        self._on_agent_offline.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._agents_lock:
            total = len(self._agents)
            by_status = {}
            by_guild = {}

            for agent in self._agents.values():
                # Count by status
                status_name = agent.status.value
                by_status[status_name] = by_status.get(status_name, 0) + 1

                # Count by guild
                for guild in agent.capabilities.guilds:
                    guild_name = guild.value
                    by_guild[guild_name] = by_guild.get(guild_name, 0) + 1

            return {
                "total_agents": total,
                "by_status": by_status,
                "by_guild": by_guild,
                "available_count": len(self.get_available_agents()),
            }
