"""
Guild Router - Capability-Based Agent Routing

EPIC: MD-3107 - Agora Phase 2: Guilds & Registry
AC-3: Implement GuildRouter to find agents by capability and cost constraints

The GuildRouter provides intelligent routing of tasks to appropriate agents
based on required capabilities, cost constraints, and availability.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-105)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from maestro_hive.agora.guilds import Guild, GuildType
from maestro_hive.agora.registry import AgentRegistry, RegisteredAgent, AgentStatus

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Strategies for selecting agents."""

    CHEAPEST = "cheapest"  # Select cheapest available agent
    BEST_QUALITY = "best_quality"  # Select highest quality tier agent
    ROUND_ROBIN = "round_robin"  # Distribute work evenly
    LEAST_LOADED = "least_loaded"  # Select agent with most available capacity
    FIRST_AVAILABLE = "first_available"  # Select first matching agent


@dataclass
class RoutingRequest:
    """
    Request for routing a task to an agent.

    Attributes:
        required_guilds: Guilds the agent must belong to (any of these)
        required_skills: Skills the agent must have (all of these)
        preferred_guilds: Preferred guilds (used for ranking)
        max_cost_per_token: Maximum acceptable cost
        min_quality_tier: Minimum quality tier required
        strategy: Routing strategy to use
        exclude_agents: Agent IDs to exclude from consideration
    """

    required_guilds: Set[GuildType] = field(default_factory=set)
    required_skills: Set[str] = field(default_factory=set)
    preferred_guilds: Set[GuildType] = field(default_factory=set)
    max_cost_per_token: Optional[float] = None
    min_quality_tier: int = 1
    strategy: RoutingStrategy = RoutingStrategy.CHEAPEST
    exclude_agents: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize request to dictionary."""
        return {
            "required_guilds": [g.value for g in self.required_guilds],
            "required_skills": list(self.required_skills),
            "preferred_guilds": [g.value for g in self.preferred_guilds],
            "max_cost_per_token": self.max_cost_per_token,
            "min_quality_tier": self.min_quality_tier,
            "strategy": self.strategy.value,
            "exclude_agents": list(self.exclude_agents),
            "metadata": self.metadata,
        }


@dataclass
class RoutingResult:
    """
    Result of a routing request.

    Attributes:
        success: Whether routing was successful
        agent: The selected agent (if successful)
        candidates: All candidate agents considered
        reason: Reason for failure (if unsuccessful)
        scores: Scoring details for each candidate
    """

    success: bool
    agent: Optional[RegisteredAgent] = None
    candidates: List[RegisteredAgent] = field(default_factory=list)
    reason: Optional[str] = None
    scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "success": self.success,
            "agent": self.agent.to_dict() if self.agent else None,
            "candidates_count": len(self.candidates),
            "reason": self.reason,
            "scores": self.scores,
        }


class GuildRouter:
    """
    Router for finding and selecting agents based on capabilities.

    AC-3: Find agents by capability and cost constraints

    The router uses Guild profiles and agent capabilities to intelligently
    match tasks to appropriate agents.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize the router.

        Args:
            registry: Agent registry to use (defaults to singleton)
        """
        self._registry = registry or AgentRegistry.get_instance()
        self._round_robin_index: Dict[str, int] = {}

        # Ensure guilds are initialized
        Guild.initialize()

        logger.info("GuildRouter initialized")

    def route(self, request: RoutingRequest) -> RoutingResult:
        """
        Route a request to an appropriate agent.

        AC-3: Find agents by capability and cost constraints

        Args:
            request: Routing request with requirements

        Returns:
            RoutingResult with selected agent or failure reason
        """
        # Find candidate agents
        candidates = self._find_candidates(request)

        if not candidates:
            return RoutingResult(
                success=False,
                candidates=[],
                reason="No agents match the routing criteria",
            )

        # Score and rank candidates
        scored_candidates = self._score_candidates(candidates, request)

        # Select agent based on strategy
        selected = self._select_agent(scored_candidates, request)

        if selected is None:
            return RoutingResult(
                success=False,
                candidates=candidates,
                reason="No agent could be selected with the given strategy",
                scores={agent_id: score for agent_id, score, _ in scored_candidates},
            )

        return RoutingResult(
            success=True,
            agent=selected,
            candidates=candidates,
            scores={agent_id: score for agent_id, score, _ in scored_candidates},
        )

    def _find_candidates(self, request: RoutingRequest) -> List[RegisteredAgent]:
        """Find all agents matching the basic criteria."""
        # Start with all available agents
        if request.required_guilds:
            # Find agents in any of the required guilds
            candidates = self._registry.find_by_guilds(
                request.required_guilds,
                require_all=False,
                available_only=True,
            )
        else:
            candidates = self._registry.get_available_agents()

        # Filter by skills
        if request.required_skills:
            candidates = [
                agent for agent in candidates
                if all(agent.has_skill(skill) for skill in request.required_skills)
            ]

        # Filter by cost
        if request.max_cost_per_token is not None:
            candidates = [
                agent for agent in candidates
                if agent.capabilities.cost_per_token <= request.max_cost_per_token
            ]

        # Filter by quality tier
        if request.min_quality_tier > 1:
            candidates = [
                agent for agent in candidates
                if self._get_agent_quality_tier(agent) >= request.min_quality_tier
            ]

        # Exclude specific agents
        if request.exclude_agents:
            candidates = [
                agent for agent in candidates
                if agent.agent_id not in request.exclude_agents
            ]

        return candidates

    def _score_candidates(
        self,
        candidates: List[RegisteredAgent],
        request: RoutingRequest,
    ) -> List[tuple[str, float, RegisteredAgent]]:
        """
        Score candidates based on how well they match the request.

        Returns list of (agent_id, score, agent) tuples, sorted by score descending.
        """
        scored = []

        for agent in candidates:
            score = self._calculate_score(agent, request)
            scored.append((agent.agent_id, score, agent))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _calculate_score(self, agent: RegisteredAgent, request: RoutingRequest) -> float:
        """Calculate a score for an agent based on the request."""
        score = 100.0

        # Preferred guild bonus (+20 per matching preferred guild)
        if request.preferred_guilds:
            matching_preferred = agent.capabilities.guilds & request.preferred_guilds
            score += len(matching_preferred) * 20

        # Quality tier bonus (+10 per tier above minimum)
        quality_tier = self._get_agent_quality_tier(agent)
        score += (quality_tier - request.min_quality_tier) * 10

        # Cost efficiency (lower cost = higher score)
        # Normalize to 0-50 range based on typical cost range 0.001-0.02
        max_expected_cost = 0.02
        cost_score = max(0, (max_expected_cost - agent.capabilities.cost_per_token) / max_expected_cost * 50)
        score += cost_score

        # Available capacity bonus
        capacity_bonus = agent.available_capacity * 5
        score += capacity_bonus

        # Skill match bonus (+5 per matching skill beyond required)
        if request.required_skills:
            extra_skills = len(agent.capabilities.skills) - len(request.required_skills)
            score += max(0, extra_skills) * 2

        return score

    def _get_agent_quality_tier(self, agent: RegisteredAgent) -> int:
        """Get the quality tier for an agent based on their guilds."""
        max_tier = 1
        for guild_type in agent.capabilities.guilds:
            try:
                profile = Guild.get_profile(guild_type)
                max_tier = max(max_tier, profile.quality_tier)
            except ValueError:
                pass
        return max_tier

    def _select_agent(
        self,
        scored_candidates: List[tuple[str, float, RegisteredAgent]],
        request: RoutingRequest,
    ) -> Optional[RegisteredAgent]:
        """Select an agent based on the routing strategy."""
        if not scored_candidates:
            return None

        strategy = request.strategy

        if strategy == RoutingStrategy.CHEAPEST:
            # Sort by cost and return cheapest
            sorted_by_cost = sorted(
                scored_candidates,
                key=lambda x: x[2].capabilities.cost_per_token
            )
            return sorted_by_cost[0][2]

        elif strategy == RoutingStrategy.BEST_QUALITY:
            # Sort by quality tier and return best
            sorted_by_quality = sorted(
                scored_candidates,
                key=lambda x: self._get_agent_quality_tier(x[2]),
                reverse=True
            )
            return sorted_by_quality[0][2]

        elif strategy == RoutingStrategy.LEAST_LOADED:
            # Sort by available capacity and return most available
            sorted_by_capacity = sorted(
                scored_candidates,
                key=lambda x: x[2].available_capacity,
                reverse=True
            )
            return sorted_by_capacity[0][2]

        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # Distribute work evenly using round-robin
            key = self._get_round_robin_key(request)
            index = self._round_robin_index.get(key, 0)

            # Sort by agent_id for consistent ordering
            sorted_by_id = sorted(scored_candidates, key=lambda x: x[0])
            selected = sorted_by_id[index % len(sorted_by_id)][2]

            self._round_robin_index[key] = index + 1
            return selected

        elif strategy == RoutingStrategy.FIRST_AVAILABLE:
            # Return first candidate (already sorted by score)
            return scored_candidates[0][2]

        # Default: return highest scored
        return scored_candidates[0][2]

    def _get_round_robin_key(self, request: RoutingRequest) -> str:
        """Generate a key for round-robin tracking."""
        guilds = sorted(g.value for g in request.required_guilds)
        skills = sorted(request.required_skills)
        return f"{','.join(guilds)}:{','.join(skills)}"

    def find_agents_for_task(
        self,
        task_type: str,
        max_cost: Optional[float] = None,
        count: int = 1,
    ) -> List[RegisteredAgent]:
        """
        Find agents suitable for a specific task type.

        AC-3: Find agents by capability and cost constraints

        Args:
            task_type: Type of task (maps to guild)
            max_cost: Maximum cost per token
            count: Number of agents needed

        Returns:
            List of suitable agents
        """
        # Map task types to guilds
        task_to_guild = {
            "code": GuildType.CODER,
            "coding": GuildType.CODER,
            "review": GuildType.REVIEWER,
            "code_review": GuildType.REVIEWER,
            "test": GuildType.TESTER,
            "testing": GuildType.TESTER,
            "architecture": GuildType.ARCHITECT,
            "design": GuildType.ARCHITECT,
            "frontend": GuildType.FRONTEND_DEVELOPER,
            "backend": GuildType.BACKEND_DEVELOPER,
            "api": GuildType.API_DEVELOPER,
            "database": GuildType.DATABASE_ENGINEER,
            "security": GuildType.SECURITY_ANALYST,
            "docs": GuildType.TECHNICAL_WRITER,
            "documentation": GuildType.TECHNICAL_WRITER,
            "ux": GuildType.UX_DESIGNER,
            "requirements": GuildType.REQUIREMENTS_ANALYST,
            "devops": GuildType.DEVOPS_ENGINEER,
            "sre": GuildType.SRE,
            "project": GuildType.PROJECT_MANAGER,
            "scrum": GuildType.SCRUM_MASTER,
        }

        guild = task_to_guild.get(task_type.lower(), GuildType.GENERALIST)

        request = RoutingRequest(
            required_guilds={guild},
            max_cost_per_token=max_cost,
            strategy=RoutingStrategy.CHEAPEST,
        )

        # Find multiple agents if needed
        results = []
        exclude_set: Set[str] = set()

        for _ in range(count):
            request.exclude_agents = exclude_set
            result = self.route(request)

            if result.success and result.agent:
                results.append(result.agent)
                exclude_set.add(result.agent.agent_id)
            else:
                break

        return results

    def get_guild_availability(self) -> Dict[str, Dict[str, int]]:
        """
        Get availability statistics by guild.

        Returns:
            Dict mapping guild names to availability stats
        """
        stats: Dict[str, Dict[str, int]] = {}

        for guild_type in GuildType:
            agents = self._registry.find_by_guilds({guild_type}, available_only=False)
            available = [a for a in agents if a.is_available]

            stats[guild_type.value] = {
                "total": len(agents),
                "available": len(available),
                "busy": len([a for a in agents if a.status == AgentStatus.BUSY]),
                "offline": len([a for a in agents if a.status == AgentStatus.OFFLINE]),
            }

        return stats

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        registry_stats = self._registry.get_stats()
        guild_availability = self.get_guild_availability()

        return {
            "registry": registry_stats,
            "guild_availability": guild_availability,
            "round_robin_keys": list(self._round_robin_index.keys()),
        }
