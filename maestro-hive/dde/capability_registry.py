"""
Capability Registry - Unified registry for agent capabilities with database persistence.

JIRA: MD-2065 (part of MD-2042)
Description: Central registry for dynamic agent capability management with:
- Agent CRUD operations
- Capability CRUD operations
- In-memory caching for performance (<100ms lookups)
- Integration with capability taxonomy

Author: AI Agent
Date: 2024-12
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import logging
import threading
from functools import lru_cache

# Database imports
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session, sessionmaker
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# Local imports
from .capability_matcher import CapabilityTaxonomy

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AgentCapability:
    """Represents a single capability of an agent."""
    skill_id: str
    proficiency: int  # 1-5 scale
    source: str = "manual"  # manual, inferred, historical, assessment
    confidence: float = 1.0
    last_used: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "proficiency": self.proficiency,
            "source": self.source,
            "confidence": self.confidence,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "version": self.version
        }


@dataclass
class AgentProfile:
    """Complete agent profile with capabilities."""
    agent_id: str
    name: str
    persona_type: str
    availability_status: str = "offline"  # available, busy, offline
    wip_limit: int = 3
    current_wip: int = 0
    capabilities: List[AgentCapability] = field(default_factory=list)
    quality_history: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "persona_type": self.persona_type,
            "availability_status": self.availability_status,
            "wip_limit": self.wip_limit,
            "current_wip": self.current_wip,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "quality_history": self.quality_history[-20:],  # Last 20 scores
            "metadata": self.metadata,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def get_proficiency(self, skill_id: str) -> int:
        """Get proficiency for a specific skill."""
        for cap in self.capabilities:
            if cap.skill_id == skill_id:
                return cap.proficiency
        return 0

    def has_capability(self, skill_id: str, min_proficiency: int = 1) -> bool:
        """Check if agent has a capability at minimum proficiency level."""
        return self.get_proficiency(skill_id) >= min_proficiency


@dataclass
class AgentFilters:
    """Filters for listing agents."""
    persona_type: Optional[str] = None
    availability_status: Optional[str] = None
    min_proficiency: int = 1
    required_skills: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0


@dataclass
class ScoringWeights:
    """
    Configurable weights for the agent match scoring algorithm.

    JIRA: MD-2067 (part of MD-2042)
    Default weights optimized for balanced routing:
    - Proficiency: 35% - skill level importance
    - Availability: 25% - agent availability
    - Quality: 25% - historical performance
    - Load: 10% - current workload consideration
    - Recency: 5% - prefer recently active agents
    """
    proficiency: float = 0.35
    availability: float = 0.25
    quality: float = 0.25
    load: float = 0.10
    recency: float = 0.05

    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = self.proficiency + self.availability + self.quality + self.load + self.recency
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    @classmethod
    def quality_focused(cls) -> "ScoringWeights":
        """Weights emphasizing quality over availability."""
        return cls(proficiency=0.30, availability=0.15, quality=0.40, load=0.10, recency=0.05)

    @classmethod
    def speed_focused(cls) -> "ScoringWeights":
        """Weights emphasizing availability for fast assignment."""
        return cls(proficiency=0.25, availability=0.40, quality=0.20, load=0.10, recency=0.05)

    @classmethod
    def load_balanced(cls) -> "ScoringWeights":
        """Weights for even workload distribution."""
        return cls(proficiency=0.25, availability=0.20, quality=0.20, load=0.30, recency=0.05)


@dataclass
class MatchScore:
    """
    Result of calculating agent match score.

    JIRA: MD-2067 (part of MD-2042)
    """
    total: float
    components: Dict[str, float]
    agent_id: str
    required_skills_matched: List[str]
    skills_missing: List[str]

    @property
    def is_full_match(self) -> bool:
        """Returns True if all required skills are matched."""
        return len(self.skills_missing) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": round(self.total, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "agent_id": self.agent_id,
            "required_skills_matched": self.required_skills_matched,
            "skills_missing": self.skills_missing,
            "is_full_match": self.is_full_match
        }


@dataclass
class CapabilityVersion:
    """Represents a capability version."""
    skill_id: str
    version: str
    effective_date: datetime = field(default_factory=datetime.now)
    deprecated: bool = False
    successor_skill_id: Optional[str] = None

    @staticmethod
    def parse(version_str: str) -> "CapabilityVersion":
        """Parse a SemVer string."""
        parts = version_str.split(".")
        return CapabilityVersion(
            skill_id="",
            version=version_str
        )

    @property
    def major(self) -> int:
        parts = self.version.split(".")
        return int(parts[0]) if parts else 0

    @property
    def minor(self) -> int:
        parts = self.version.split(".")
        return int(parts[1]) if len(parts) > 1 else 0

    @property
    def patch(self) -> int:
        parts = self.version.split(".")
        return int(parts[2]) if len(parts) > 2 else 0

    def is_compatible_with(self, other: "CapabilityVersion") -> bool:
        """Check if this version is compatible with another (same major version)."""
        return self.major == other.major and self.minor >= other.minor


# ============================================================================
# Capability Registry Class
# ============================================================================

class CapabilityRegistry:
    """
    Unified registry for agent capabilities with database persistence.

    Features:
    - Agent CRUD operations
    - Capability CRUD operations
    - In-memory caching for <100ms lookups
    - Hierarchical skill matching via taxonomy
    - Quality history tracking
    """

    def __init__(
        self,
        db_session: Optional[Any] = None,
        taxonomy_path: str = "config/capability_taxonomy.yaml",
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize the CapabilityRegistry.

        Args:
            db_session: SQLAlchemy session or database connection
            taxonomy_path: Path to capability taxonomy YAML file
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.db = db_session
        self.taxonomy = CapabilityTaxonomy(taxonomy_path)
        self.cache_ttl = cache_ttl_seconds

        # In-memory cache
        self._agent_cache: Dict[str, Tuple[AgentProfile, datetime]] = {}
        self._capability_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_lock = threading.RLock()

        logger.info("CapabilityRegistry initialized with taxonomy: %s", taxonomy_path)

    # =========================================================================
    # Agent CRUD Operations
    # =========================================================================

    def register_agent(
        self,
        agent_id: str,
        name: str,
        persona_type: str,
        capabilities: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentProfile:
        """
        Register a new agent with capabilities.

        Args:
            agent_id: Unique agent identifier
            name: Agent display name
            persona_type: Type of agent persona (e.g., backend_developer)
            capabilities: Dict of skill_id -> proficiency (1-5)
            metadata: Optional additional metadata

        Returns:
            Created AgentProfile
        """
        now = datetime.now()

        # Create agent in database
        if self.db:
            try:
                # Insert agent
                self.db.execute(text("""
                    INSERT INTO capability_agents (agent_id, name, persona_type, metadata, created_at, updated_at)
                    VALUES (:agent_id, :name, :persona_type, :metadata::jsonb, :now, :now)
                    ON CONFLICT (agent_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        persona_type = EXCLUDED.persona_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """), {
                    "agent_id": agent_id,
                    "name": name,
                    "persona_type": persona_type,
                    "metadata": str(metadata or {}),
                    "now": now
                })

                # Get agent's internal ID
                result = self.db.execute(text(
                    "SELECT id FROM capability_agents WHERE agent_id = :agent_id"
                ), {"agent_id": agent_id})
                internal_id = result.fetchone()[0]

                # Add capabilities
                for skill_id, proficiency in capabilities.items():
                    self._add_capability_to_db(internal_id, skill_id, proficiency)

                self.db.commit()
                logger.info("Registered agent: %s (%s)", agent_id, name)

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to register agent %s: %s", agent_id, e)
                raise

        # Create and cache profile
        agent_caps = [
            AgentCapability(skill_id=skill, proficiency=prof)
            for skill, prof in capabilities.items()
        ]

        profile = AgentProfile(
            agent_id=agent_id,
            name=name,
            persona_type=persona_type,
            capabilities=agent_caps,
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )

        self._cache_agent(profile)
        return profile

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.

        Args:
            agent_id: Agent to remove

        Returns:
            True if agent was removed
        """
        if self.db:
            try:
                result = self.db.execute(text(
                    "DELETE FROM capability_agents WHERE agent_id = :agent_id"
                ), {"agent_id": agent_id})
                self.db.commit()

                if result.rowcount > 0:
                    logger.info("Unregistered agent: %s", agent_id)
                    self.invalidate_agent_cache(agent_id)
                    return True
                return False

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to unregister agent %s: %s", agent_id, e)
                raise

        # Memory-only mode
        with self._cache_lock:
            if agent_id in self._agent_cache:
                del self._agent_cache[agent_id]
                return True
        return False

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """
        Get an agent profile by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentProfile or None if not found
        """
        # Check cache first
        cached = self._get_cached_agent(agent_id)
        if cached:
            return cached

        # Load from database
        if self.db:
            try:
                result = self.db.execute(text("""
                    SELECT
                        a.agent_id, a.name, a.persona_type, a.availability_status,
                        a.wip_limit, a.current_wip, a.metadata, a.last_active,
                        a.created_at, a.updated_at
                    FROM capability_agents a
                    WHERE a.agent_id = :agent_id
                """), {"agent_id": agent_id})

                row = result.fetchone()
                if not row:
                    return None

                # Load capabilities
                caps_result = self.db.execute(text("""
                    SELECT
                        c.skill_id, ac.proficiency, ac.source, ac.confidence,
                        ac.last_used, ac.execution_count, ac.success_count, c.version
                    FROM agent_capabilities ac
                    JOIN capabilities c ON ac.capability_id = c.id
                    JOIN capability_agents a ON ac.agent_id = a.id
                    WHERE a.agent_id = :agent_id
                """), {"agent_id": agent_id})

                capabilities = [
                    AgentCapability(
                        skill_id=cap_row[0],
                        proficiency=cap_row[1],
                        source=cap_row[2],
                        confidence=cap_row[3],
                        last_used=cap_row[4],
                        execution_count=cap_row[5],
                        success_count=cap_row[6],
                        version=cap_row[7] or "1.0.0"
                    )
                    for cap_row in caps_result.fetchall()
                ]

                # Load quality history
                history_result = self.db.execute(text("""
                    SELECT quality_score
                    FROM agent_quality_history
                    WHERE agent_id = (SELECT id FROM capability_agents WHERE agent_id = :agent_id)
                    ORDER BY recorded_at DESC
                    LIMIT 20
                """), {"agent_id": agent_id})
                quality_history = [r[0] for r in history_result.fetchall()]

                profile = AgentProfile(
                    agent_id=row[0],
                    name=row[1],
                    persona_type=row[2],
                    availability_status=row[3] or "offline",
                    wip_limit=row[4] or 3,
                    current_wip=row[5] or 0,
                    metadata=row[6] or {},
                    last_active=row[7],
                    created_at=row[8],
                    updated_at=row[9],
                    capabilities=capabilities,
                    quality_history=quality_history
                )

                self._cache_agent(profile)
                return profile

            except Exception as e:
                logger.error("Failed to get agent %s: %s", agent_id, e)
                return None

        return None

    def list_agents(self, filters: Optional[AgentFilters] = None) -> List[AgentProfile]:
        """
        List agents with optional filters.

        Args:
            filters: Optional AgentFilters

        Returns:
            List of matching AgentProfiles
        """
        filters = filters or AgentFilters()

        if self.db:
            try:
                query = """
                    SELECT agent_id
                    FROM capability_agents
                    WHERE 1=1
                """
                params = {}

                if filters.persona_type:
                    query += " AND persona_type = :persona_type"
                    params["persona_type"] = filters.persona_type

                if filters.availability_status:
                    query += " AND availability_status = :availability_status"
                    params["availability_status"] = filters.availability_status

                query += " LIMIT :limit OFFSET :offset"
                params["limit"] = filters.limit
                params["offset"] = filters.offset

                result = self.db.execute(text(query), params)
                agent_ids = [row[0] for row in result.fetchall()]

                return [
                    agent for agent_id in agent_ids
                    if (agent := self.get_agent(agent_id)) is not None
                ]

            except Exception as e:
                logger.error("Failed to list agents: %s", e)
                return []

        # Memory-only mode
        with self._cache_lock:
            agents = [
                profile for profile, _ in self._agent_cache.values()
            ]

        if filters.persona_type:
            agents = [a for a in agents if a.persona_type == filters.persona_type]
        if filters.availability_status:
            agents = [a for a in agents if a.availability_status == filters.availability_status]

        return agents[filters.offset:filters.offset + filters.limit]

    def update_agent_status(
        self,
        agent_id: str,
        status: Optional[str] = None,
        wip: Optional[int] = None,
        wip_delta: Optional[int] = None
    ) -> bool:
        """
        Update agent availability status and/or WIP count.

        Args:
            agent_id: Agent to update
            status: New availability status
            wip: New WIP count (absolute)
            wip_delta: WIP delta (positive or negative)

        Returns:
            True if update succeeded
        """
        if self.db:
            try:
                updates = ["last_active = NOW()", "updated_at = NOW()"]
                params = {"agent_id": agent_id}

                if status:
                    updates.append("availability_status = :status")
                    params["status"] = status

                if wip is not None:
                    updates.append("current_wip = :wip")
                    params["wip"] = wip
                elif wip_delta is not None:
                    updates.append("current_wip = GREATEST(0, current_wip + :wip_delta)")
                    params["wip_delta"] = wip_delta

                query = f"""
                    UPDATE capability_agents
                    SET {', '.join(updates)}
                    WHERE agent_id = :agent_id
                """

                result = self.db.execute(text(query), params)
                self.db.commit()

                if result.rowcount > 0:
                    self.invalidate_agent_cache(agent_id)
                    return True
                return False

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to update agent status %s: %s", agent_id, e)
                raise

        # Memory-only mode
        with self._cache_lock:
            if agent_id in self._agent_cache:
                profile, _ = self._agent_cache[agent_id]
                if status:
                    profile.availability_status = status
                if wip is not None:
                    profile.current_wip = wip
                elif wip_delta is not None:
                    profile.current_wip = max(0, profile.current_wip + wip_delta)
                profile.last_active = datetime.now()
                self._cache_agent(profile)
                return True
        return False

    # =========================================================================
    # Capability CRUD Operations
    # =========================================================================

    def add_capability(
        self,
        agent_id: str,
        skill_id: str,
        proficiency: int,
        source: str = "manual"
    ) -> bool:
        """
        Add a capability to an existing agent.

        Args:
            agent_id: Agent to update
            skill_id: Capability to add
            proficiency: Proficiency level (1-5)
            source: How proficiency was determined

        Returns:
            True if capability was added
        """
        if not 1 <= proficiency <= 5:
            raise ValueError("Proficiency must be between 1 and 5")

        if self.db:
            try:
                # Get agent internal ID
                result = self.db.execute(text(
                    "SELECT id FROM capability_agents WHERE agent_id = :agent_id"
                ), {"agent_id": agent_id})
                row = result.fetchone()
                if not row:
                    return False

                internal_id = row[0]
                self._add_capability_to_db(internal_id, skill_id, proficiency, source)
                self.db.commit()

                self.invalidate_agent_cache(agent_id)
                return True

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to add capability: %s", e)
                raise

        # Memory-only mode
        agent = self.get_agent(agent_id)
        if agent:
            agent.capabilities.append(
                AgentCapability(skill_id=skill_id, proficiency=proficiency, source=source)
            )
            self._cache_agent(agent)
            return True
        return False

    def update_capability(
        self,
        agent_id: str,
        skill_id: str,
        proficiency: int
    ) -> bool:
        """
        Update an existing capability's proficiency.

        Args:
            agent_id: Agent to update
            skill_id: Capability to update
            proficiency: New proficiency level

        Returns:
            True if capability was updated
        """
        if not 1 <= proficiency <= 5:
            raise ValueError("Proficiency must be between 1 and 5")

        if self.db:
            try:
                result = self.db.execute(text("""
                    UPDATE agent_capabilities ac
                    SET proficiency = :proficiency, updated_at = NOW()
                    FROM capability_agents a, capabilities c
                    WHERE ac.agent_id = a.id
                      AND ac.capability_id = c.id
                      AND a.agent_id = :agent_id
                      AND c.skill_id = :skill_id
                """), {
                    "agent_id": agent_id,
                    "skill_id": skill_id,
                    "proficiency": proficiency
                })
                self.db.commit()

                if result.rowcount > 0:
                    self.invalidate_agent_cache(agent_id)
                    return True
                return False

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to update capability: %s", e)
                raise

        # Memory-only mode
        agent = self.get_agent(agent_id)
        if agent:
            for cap in agent.capabilities:
                if cap.skill_id == skill_id:
                    cap.proficiency = proficiency
                    self._cache_agent(agent)
                    return True
        return False

    def remove_capability(self, agent_id: str, skill_id: str) -> bool:
        """
        Remove a capability from an agent.

        Args:
            agent_id: Agent to update
            skill_id: Capability to remove

        Returns:
            True if capability was removed
        """
        if self.db:
            try:
                result = self.db.execute(text("""
                    DELETE FROM agent_capabilities ac
                    USING capability_agents a, capabilities c
                    WHERE ac.agent_id = a.id
                      AND ac.capability_id = c.id
                      AND a.agent_id = :agent_id
                      AND c.skill_id = :skill_id
                """), {"agent_id": agent_id, "skill_id": skill_id})
                self.db.commit()

                if result.rowcount > 0:
                    self.invalidate_agent_cache(agent_id)
                    return True
                return False

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to remove capability: %s", e)
                raise

        # Memory-only mode
        agent = self.get_agent(agent_id)
        if agent:
            original_len = len(agent.capabilities)
            agent.capabilities = [c for c in agent.capabilities if c.skill_id != skill_id]
            if len(agent.capabilities) < original_len:
                self._cache_agent(agent)
                return True
        return False

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Get all capabilities for an agent."""
        agent = self.get_agent(agent_id)
        return agent.capabilities if agent else []

    # =========================================================================
    # Query Methods
    # =========================================================================

    def find_capable_agents(
        self,
        required_skills: List[str],
        min_proficiency: int = 1,
        availability_required: bool = False,
        include_parent_matches: bool = True,
        limit: int = 10
    ) -> List[AgentProfile]:
        """
        Find agents with specific capabilities.

        Args:
            required_skills: Skills the agents must have
            min_proficiency: Minimum proficiency level
            availability_required: Only return available agents
            include_parent_matches: Include agents with parent skills
            limit: Maximum agents to return

        Returns:
            List of matching agents sorted by match quality
        """
        # Expand skills if including parent matches
        search_skills = set(required_skills)
        if include_parent_matches:
            for skill in required_skills:
                # Add parent skills
                parents = self.taxonomy.expand_capability(skill)
                search_skills.update(parents)

        # Find matching agents
        agents = self.list_agents()
        matches = []

        for agent in agents:
            # Check availability
            if availability_required and agent.availability_status != "available":
                continue

            # Check capabilities
            agent_skills = {cap.skill_id for cap in agent.capabilities}
            skill_overlap = agent_skills.intersection(search_skills)

            if skill_overlap:
                # Check proficiency
                max_prof = max(
                    agent.get_proficiency(skill) for skill in skill_overlap
                )
                if max_prof >= min_proficiency:
                    matches.append((agent, max_prof, len(skill_overlap)))

        # Sort by proficiency (desc) then skill coverage (desc)
        matches.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return [agent for agent, _, _ in matches[:limit]]

    def get_capability_coverage(self) -> Dict[str, int]:
        """
        Get count of agents per capability.

        Returns:
            Dict mapping skill_id to agent count
        """
        if self.db:
            try:
                result = self.db.execute(text("""
                    SELECT c.skill_id, COUNT(DISTINCT ac.agent_id) as agent_count
                    FROM capabilities c
                    LEFT JOIN agent_capabilities ac ON c.id = ac.capability_id
                    GROUP BY c.skill_id
                """))
                return {row[0]: row[1] for row in result.fetchall()}
            except Exception as e:
                logger.error("Failed to get capability coverage: %s", e)
                return {}

        # Memory-only mode
        coverage = {}
        agents = self.list_agents()
        for agent in agents:
            for cap in agent.capabilities:
                coverage[cap.skill_id] = coverage.get(cap.skill_id, 0) + 1
        return coverage

    # =========================================================================
    # Enhanced Routing Algorithm (MD-2067)
    # =========================================================================

    def calculate_match_score(
        self,
        agent: AgentProfile,
        required_skills: List[str],
        weights: Optional[ScoringWeights] = None
    ) -> MatchScore:
        """
        Calculate comprehensive match score for an agent.

        JIRA: MD-2067 (part of MD-2042)

        Uses 5-factor weighted scoring:
        - Proficiency (35%): Average skill proficiency for required skills
        - Availability (25%): Agent availability status
        - Quality (25%): Historical quality performance (rolling 20)
        - Load (10%): Current WIP vs limit ratio
        - Recency (5%): Time since last activity

        Args:
            agent: Agent to score
            required_skills: Skills required for the task
            weights: Custom scoring weights (default: ScoringWeights())

        Returns:
            MatchScore with total and component breakdown
        """
        weights = weights or ScoringWeights()

        # Get matched and missing skills
        agent_skill_ids = {cap.skill_id for cap in agent.capabilities}

        # Expand skills to include parent matches
        expanded_skills = set()
        for skill in required_skills:
            expanded_skills.add(skill)
            parents = self.taxonomy.expand_capability(skill)
            expanded_skills.update(parents)

        matched_skills = []
        missing_skills = []

        for skill in required_skills:
            # Check direct match or parent match
            if skill in agent_skill_ids:
                matched_skills.append(skill)
            elif any(parent in agent_skill_ids for parent in self.taxonomy.expand_capability(skill)):
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)

        # 1. Proficiency Score (0-1)
        prof_scores = []
        for skill in matched_skills:
            if skill in agent_skill_ids:
                prof = agent.get_proficiency(skill)
            else:
                # Use parent skill proficiency
                for cap in agent.capabilities:
                    if skill.startswith(cap.skill_id):
                        prof = cap.proficiency
                        break
                else:
                    prof = 1
            prof_scores.append(prof / 5.0)  # Normalize to 0-1

        proficiency_score = sum(prof_scores) / len(prof_scores) if prof_scores else 0.0

        # 2. Availability Score (0-1)
        availability_map = {"available": 1.0, "busy": 0.3, "offline": 0.0}
        availability_score = availability_map.get(agent.availability_status, 0.0)

        # 3. Quality Score (0-1) - rolling 20 average
        if agent.quality_history:
            quality_score = sum(agent.quality_history[-20:]) / len(agent.quality_history[-20:])
        else:
            quality_score = 0.7  # Default for new agents

        # 4. Load Score (0-1) - inverse of current load
        if agent.wip_limit > 0:
            load_ratio = agent.current_wip / agent.wip_limit
            load_score = max(0, 1 - load_ratio)
        else:
            load_score = 0.0

        # 5. Recency Score (0-1) - based on last activity
        if agent.last_active:
            hours_since = (datetime.now() - agent.last_active).total_seconds() / 3600
            if hours_since < 1:
                recency_score = 1.0
            elif hours_since < 8:
                recency_score = 0.8
            elif hours_since < 24:
                recency_score = 0.5
            else:
                recency_score = 0.2
        else:
            recency_score = 0.5  # Default for agents without activity

        # Calculate weighted total
        total = (
            proficiency_score * weights.proficiency +
            availability_score * weights.availability +
            quality_score * weights.quality +
            load_score * weights.load +
            recency_score * weights.recency
        )

        return MatchScore(
            total=total,
            components={
                "proficiency": proficiency_score,
                "availability": availability_score,
                "quality": quality_score,
                "load": load_score,
                "recency": recency_score
            },
            agent_id=agent.agent_id,
            required_skills_matched=matched_skills,
            skills_missing=missing_skills
        )

    def route_task(
        self,
        required_skills: List[str],
        weights: Optional[ScoringWeights] = None,
        min_proficiency: int = 1,
        availability_required: bool = True,
        full_match_required: bool = False,
        limit: int = 5
    ) -> List[Tuple[AgentProfile, MatchScore]]:
        """
        Route a task to the best available agents.

        JIRA: MD-2067 (part of MD-2042)

        Args:
            required_skills: Skills needed for the task
            weights: Scoring weights (default, quality_focused, speed_focused, load_balanced)
            min_proficiency: Minimum skill proficiency required
            availability_required: Only consider available agents
            full_match_required: Require all skills to be matched
            limit: Maximum results to return

        Returns:
            List of (agent, score) tuples sorted by match score descending
        """
        candidates = []
        agents = self.list_agents()

        for agent in agents:
            # Quick availability filter
            if availability_required and agent.availability_status != "available":
                continue

            # Calculate match score
            score = self.calculate_match_score(agent, required_skills, weights)

            # Filter by match requirements
            if full_match_required and not score.is_full_match:
                continue

            # Check minimum proficiency
            if score.components["proficiency"] * 5 < min_proficiency:
                continue

            candidates.append((agent, score))

        # Sort by total score descending
        candidates.sort(key=lambda x: x[1].total, reverse=True)

        return candidates[:limit]

    def get_best_agent(
        self,
        required_skills: List[str],
        weights: Optional[ScoringWeights] = None
    ) -> Optional[Tuple[AgentProfile, MatchScore]]:
        """
        Get the single best agent for a task.

        Convenience wrapper around route_task.

        Args:
            required_skills: Skills needed for the task
            weights: Scoring weights

        Returns:
            Tuple of (best_agent, score) or None if no match
        """
        results = self.route_task(
            required_skills=required_skills,
            weights=weights,
            availability_required=True,
            limit=1
        )
        return results[0] if results else None

    # =========================================================================
    # Quality Tracking
    # =========================================================================

    def record_quality_score(
        self,
        agent_id: str,
        task_id: str,
        quality_score: float,
        execution_time_ms: Optional[int] = None,
        skill_id: Optional[str] = None
    ) -> bool:
        """
        Record a quality score for an agent execution.

        Args:
            agent_id: Agent who performed the task
            task_id: Task identifier
            quality_score: Quality score (0.0-1.0)
            execution_time_ms: Execution time in milliseconds
            skill_id: Primary skill used

        Returns:
            True if recorded successfully
        """
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")

        if self.db:
            try:
                self.db.execute(text("""
                    INSERT INTO agent_quality_history
                    (agent_id, task_id, quality_score, execution_time_ms, skill_id)
                    SELECT id, :task_id, :quality_score, :execution_time_ms, :skill_id
                    FROM capability_agents WHERE agent_id = :agent_id
                """), {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "quality_score": quality_score,
                    "execution_time_ms": execution_time_ms,
                    "skill_id": skill_id
                })
                self.db.commit()

                self.invalidate_agent_cache(agent_id)
                return True

            except Exception as e:
                self.db.rollback()
                logger.error("Failed to record quality score: %s", e)
                raise

        # Memory-only mode
        agent = self.get_agent(agent_id)
        if agent:
            agent.quality_history.append(quality_score)
            # Keep only last 20 scores
            agent.quality_history = agent.quality_history[-20:]
            self._cache_agent(agent)
            return True
        return False

    def boost_proficiency(
        self,
        agent_id: str,
        skill_id: str,
        boost: float = 0.1
    ) -> bool:
        """
        Boost an agent's proficiency for a skill (capped at 5).

        Args:
            agent_id: Agent to boost
            skill_id: Skill to boost
            boost: Amount to boost (default 0.1)

        Returns:
            True if boosted
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return False

        current_prof = agent.get_proficiency(skill_id)
        new_prof = min(5, int(current_prof + boost + 0.5))  # Round to nearest int

        if new_prof > current_prof:
            return self.update_capability(agent_id, skill_id, new_prof)
        return True

    # =========================================================================
    # Versioning Methods
    # =========================================================================

    def add_capability_version(
        self,
        skill_id: str,
        version: str,
        deprecated: bool = False,
        successor_skill_id: Optional[str] = None
    ) -> bool:
        """Add or update a capability version."""
        if self.db:
            try:
                self.db.execute(text("""
                    UPDATE capabilities
                    SET version = :version, deprecated = :deprecated,
                        successor_skill_id = :successor
                    WHERE skill_id = :skill_id
                """), {
                    "skill_id": skill_id,
                    "version": version,
                    "deprecated": deprecated,
                    "successor": successor_skill_id
                })
                self.db.commit()
                return True
            except Exception as e:
                self.db.rollback()
                logger.error("Failed to add capability version: %s", e)
                return False
        return False

    def migrate_capability(self, old_skill_id: str) -> str:
        """Migrate a deprecated capability to its successor."""
        if self.db:
            try:
                result = self.db.execute(text("""
                    SELECT successor_skill_id
                    FROM capabilities
                    WHERE skill_id = :skill_id AND deprecated = TRUE
                """), {"skill_id": old_skill_id})
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
            except Exception as e:
                logger.error("Failed to migrate capability: %s", e)
        return old_skill_id

    def is_capability_compatible(
        self,
        required_skill: str,
        required_version: str,
        agent_skill: str,
        agent_version: str
    ) -> bool:
        """
        Check if an agent's capability version satisfies a requirement.

        JIRA: MD-2068 (part of MD-2042)

        Compatibility rules:
        - Same major version required
        - Agent's minor version must be >= required minor version
        - Patch version is ignored

        Args:
            required_skill: Skill required by the task
            required_version: Minimum version required (SemVer)
            agent_skill: Agent's skill
            agent_version: Agent's version for this skill

        Returns:
            True if compatible
        """
        # First check skill compatibility
        if required_skill != agent_skill:
            # Check if agent skill is a parent of required skill
            if not required_skill.startswith(agent_skill):
                return False

        # Parse versions
        req_parts = required_version.split(".")
        agent_parts = agent_version.split(".")

        req_major = int(req_parts[0]) if req_parts else 0
        req_minor = int(req_parts[1]) if len(req_parts) > 1 else 0

        agent_major = int(agent_parts[0]) if agent_parts else 0
        agent_minor = int(agent_parts[1]) if len(agent_parts) > 1 else 0

        # Major version must match
        if req_major != agent_major:
            return False

        # Agent minor must be >= required minor
        return agent_minor >= req_minor

    def get_deprecated_capabilities(self) -> List[Dict[str, Any]]:
        """
        Get all deprecated capabilities with their successors.

        JIRA: MD-2068 (part of MD-2042)

        Returns:
            List of deprecated capability info with migration paths
        """
        deprecated = []

        if self.db:
            try:
                result = self.db.execute(text("""
                    SELECT skill_id, version, successor_skill_id
                    FROM capabilities
                    WHERE deprecated = TRUE
                """))
                for row in result.fetchall():
                    deprecated.append({
                        "skill_id": row[0],
                        "version": row[1],
                        "successor_skill_id": row[2],
                        "migration_available": row[2] is not None
                    })
            except Exception as e:
                logger.error("Failed to get deprecated capabilities: %s", e)

        return deprecated

    def deprecate_capability(
        self,
        skill_id: str,
        successor_skill_id: Optional[str] = None
    ) -> bool:
        """
        Mark a capability as deprecated.

        JIRA: MD-2068 (part of MD-2042)

        Args:
            skill_id: Capability to deprecate
            successor_skill_id: Replacement capability (if any)

        Returns:
            True if successful
        """
        if self.db:
            try:
                self.db.execute(text("""
                    UPDATE capabilities
                    SET deprecated = TRUE, successor_skill_id = :successor
                    WHERE skill_id = :skill_id
                """), {
                    "skill_id": skill_id,
                    "successor": successor_skill_id
                })
                self.db.commit()
                logger.info(f"Deprecated capability {skill_id} -> {successor_skill_id}")
                return True
            except Exception as e:
                self.db.rollback()
                logger.error("Failed to deprecate capability: %s", e)
                return False
        return False

    def migrate_agent_capabilities(self, agent_id: str) -> int:
        """
        Migrate all deprecated capabilities for an agent to their successors.

        JIRA: MD-2068 (part of MD-2042)

        Args:
            agent_id: Agent to migrate

        Returns:
            Number of capabilities migrated
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return 0

        migrated = 0
        for cap in agent.capabilities:
            successor = self.migrate_capability(cap.skill_id)
            if successor != cap.skill_id:
                # Add the new capability with same proficiency
                self.add_capability(
                    agent_id=agent_id,
                    skill_id=successor,
                    proficiency=cap.proficiency,
                    source="migrated"
                )
                # Remove the old capability
                self.remove_capability(agent_id, cap.skill_id)
                migrated += 1
                logger.info(f"Migrated {cap.skill_id} -> {successor} for agent {agent_id}")

        return migrated

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _cache_agent(self, agent: AgentProfile) -> None:
        """Cache an agent profile."""
        with self._cache_lock:
            self._agent_cache[agent.agent_id] = (agent, datetime.now())

    def _get_cached_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent from cache if valid."""
        with self._cache_lock:
            if agent_id in self._agent_cache:
                agent, cached_at = self._agent_cache[agent_id]
                if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                    return agent
                else:
                    del self._agent_cache[agent_id]
        return None

    def invalidate_agent_cache(self, agent_id: str) -> None:
        """Invalidate cached agent data."""
        with self._cache_lock:
            if agent_id in self._agent_cache:
                del self._agent_cache[agent_id]

    def refresh_cache(self) -> None:
        """Clear all cached data."""
        with self._cache_lock:
            self._agent_cache.clear()
            self._capability_cache.clear()

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _add_capability_to_db(
        self,
        agent_internal_id: str,
        skill_id: str,
        proficiency: int,
        source: str = "manual"
    ) -> None:
        """Add a capability to the database."""
        # Ensure capability exists in taxonomy
        self.db.execute(text("""
            INSERT INTO capabilities (skill_id, category, version)
            VALUES (:skill_id, :category, '1.0.0')
            ON CONFLICT (skill_id) DO NOTHING
        """), {
            "skill_id": skill_id,
            "category": skill_id.split(":")[0] if ":" in skill_id else skill_id
        })

        # Link agent to capability
        self.db.execute(text("""
            INSERT INTO agent_capabilities (agent_id, capability_id, proficiency, source)
            SELECT :agent_id, c.id, :proficiency, :source
            FROM capabilities c WHERE c.skill_id = :skill_id
            ON CONFLICT (agent_id, capability_id) DO UPDATE SET
                proficiency = EXCLUDED.proficiency,
                source = EXCLUDED.source,
                updated_at = NOW()
        """), {
            "agent_id": agent_internal_id,
            "skill_id": skill_id,
            "proficiency": proficiency,
            "source": source
        })


# ============================================================================
# Factory Function
# ============================================================================

def create_registry(
    database_url: Optional[str] = None,
    taxonomy_path: str = "config/capability_taxonomy.yaml"
) -> CapabilityRegistry:
    """
    Create a CapabilityRegistry instance.

    Args:
        database_url: PostgreSQL connection URL
        taxonomy_path: Path to capability taxonomy YAML

    Returns:
        Configured CapabilityRegistry
    """
    db_session = None

    if database_url and HAS_SQLALCHEMY:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        db_session = Session()

    return CapabilityRegistry(
        db_session=db_session,
        taxonomy_path=taxonomy_path
    )
