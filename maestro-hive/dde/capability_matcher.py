"""
DDE Capability Matcher

Matches tasks to agents based on capability requirements and agent profiles.
Uses a scoring algorithm that considers proficiency, availability, quality, and load.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import yaml
from pathlib import Path


@dataclass
class AgentProfile:
    """Profile of an agent with capabilities and status"""
    agent_id: str
    name: str
    availability_status: str  # 'available', 'busy', 'offline'
    wip_limit: int
    current_wip: int
    recent_quality_score: float  # 0.0 to 1.0
    last_active: Optional[datetime]
    capabilities: Dict[str, int]  # skill_id -> proficiency (1-5)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'availability_status': self.availability_status,
            'wip_limit': self.wip_limit,
            'current_wip': self.current_wip,
            'recent_quality_score': self.recent_quality_score,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'capabilities': self.capabilities
        }


class CapabilityTaxonomy:
    """Manages capability taxonomy and skill hierarchy"""

    def __init__(self, taxonomy_file: str = "config/capability_taxonomy.yaml"):
        """Load capability taxonomy from YAML file"""
        self.taxonomy_file = Path(taxonomy_file)
        self.taxonomy = {}
        self.aliases = {}
        self.groups = {}
        self._load_taxonomy()

    def _load_taxonomy(self):
        """Load taxonomy from YAML file"""
        if not self.taxonomy_file.exists():
            raise FileNotFoundError(f"Taxonomy file not found: {self.taxonomy_file}")

        with open(self.taxonomy_file) as f:
            data = yaml.safe_load(f)

        self.taxonomy = data.get('taxonomy', {})
        self.aliases = data.get('aliases', {})
        self.groups = data.get('groups', {})

    def normalize_capability(self, capability: str) -> str:
        """
        Normalize capability string (e.g., resolve aliases).

        Args:
            capability: Capability string (e.g., "Backend:Python:FastAPI")

        Returns:
            Normalized capability string
        """
        # Check aliases
        if capability in self.aliases:
            return self.aliases[capability]

        return capability

    def expand_capability(self, capability: str) -> List[str]:
        """
        Expand capability to include parent capabilities.

        Example:
            "Backend:Python:FastAPI" expands to:
            ["Backend:Python:FastAPI", "Backend:Python", "Backend"]

        Args:
            capability: Capability string

        Returns:
            List of capability strings (most specific to least specific)
        """
        parts = capability.split(':')
        expanded = []

        for i in range(len(parts), 0, -1):
            expanded.append(':'.join(parts[:i]))

        return expanded

    def get_skills_in_group(self, group_name: str) -> List[str]:
        """
        Get all skills in a capability group.

        Args:
            group_name: Name of capability group

        Returns:
            List of skill IDs in the group
        """
        return self.groups.get(group_name, [])


class CapabilityMatcher:
    """
    Matches agents to required capabilities using a scoring algorithm.

    Score = (proficiency * 0.4) + (availability * 0.3) +
            (recent_quality * 0.2) + (low_load * 0.1)
    """

    def __init__(self, taxonomy: Optional[CapabilityTaxonomy] = None):
        """
        Initialize capability matcher.

        Args:
            taxonomy: CapabilityTaxonomy instance (optional)
        """
        self.taxonomy = taxonomy or CapabilityTaxonomy()
        self.agent_profiles: Dict[str, AgentProfile] = {}

    def register_agent(self, profile: AgentProfile):
        """
        Register an agent profile.

        Args:
            profile: AgentProfile to register
        """
        self.agent_profiles[profile.agent_id] = profile

    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent.

        Args:
            agent_id: ID of agent to unregister
        """
        if agent_id in self.agent_profiles:
            del self.agent_profiles[agent_id]

    def update_agent_status(
        self,
        agent_id: str,
        availability_status: Optional[str] = None,
        current_wip: Optional[int] = None,
        recent_quality_score: Optional[float] = None
    ):
        """
        Update agent status.

        Args:
            agent_id: ID of agent to update
            availability_status: New availability status (optional)
            current_wip: New current WIP count (optional)
            recent_quality_score: New quality score (optional)
        """
        if agent_id not in self.agent_profiles:
            raise ValueError(f"Agent not found: {agent_id}")

        profile = self.agent_profiles[agent_id]

        if availability_status is not None:
            profile.availability_status = availability_status
        if current_wip is not None:
            profile.current_wip = current_wip
        if recent_quality_score is not None:
            profile.recent_quality_score = recent_quality_score

        profile.last_active = datetime.now()

    def match(
        self,
        required_skills: List[str],
        min_proficiency: int = 3,
        max_results: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Match agents with required skills.

        Args:
            required_skills: List of required skill IDs
            min_proficiency: Minimum proficiency level (1-5)
            max_results: Maximum number of results to return

        Returns:
            List of (agent_id, match_score) tuples, sorted by score (descending)
        """
        candidates = []

        # Normalize skills
        normalized_skills = [
            self.taxonomy.normalize_capability(skill)
            for skill in required_skills
        ]

        for agent_id, profile in self.agent_profiles.items():
            # Check if agent has required skills
            if not self._has_required_skills(profile, normalized_skills, min_proficiency):
                continue

            # Calculate match score
            score = self._calculate_match_score(profile, normalized_skills)
            candidates.append((agent_id, score))

        # Sort by score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[:max_results]

    def _has_required_skills(
        self,
        profile: AgentProfile,
        required_skills: List[str],
        min_proficiency: int
    ) -> bool:
        """
        Check if agent has all required skills at minimum proficiency.

        Args:
            profile: AgentProfile to check
            required_skills: List of required skill IDs
            min_proficiency: Minimum proficiency level

        Returns:
            True if agent has all required skills, False otherwise
        """
        for skill in required_skills:
            # Expand skill to include parent capabilities
            expanded_skills = self.taxonomy.expand_capability(skill)

            # Check if agent has any of the expanded skills
            has_skill = False
            for expanded_skill in expanded_skills:
                if expanded_skill in profile.capabilities:
                    if profile.capabilities[expanded_skill] >= min_proficiency:
                        has_skill = True
                        break

            if not has_skill:
                return False

        return True

    def _calculate_match_score(
        self,
        profile: AgentProfile,
        required_skills: List[str]
    ) -> float:
        """
        Calculate match score for an agent.

        Score = (proficiency * 0.4) + (availability * 0.3) +
                (recent_quality * 0.2) + (low_load * 0.1)

        Args:
            profile: AgentProfile to score
            required_skills: List of required skill IDs

        Returns:
            Match score (0.0 to 1.0)
        """
        # Proficiency component (0.4 weight)
        avg_proficiency = self._get_avg_proficiency(profile, required_skills)
        proficiency_score = (avg_proficiency / 5.0) * 0.4

        # Availability component (0.3 weight)
        availability_score = 0.3 if profile.availability_status == 'available' else 0

        # Quality component (0.2 weight)
        quality_score = profile.recent_quality_score * 0.2

        # Load component (0.1 weight)
        load_factor = profile.current_wip / profile.wip_limit if profile.wip_limit > 0 else 1.0
        load_score = (1 - load_factor) * 0.1

        total_score = proficiency_score + availability_score + quality_score + load_score

        return total_score

    def _get_avg_proficiency(
        self,
        profile: AgentProfile,
        required_skills: List[str]
    ) -> float:
        """
        Get average proficiency across required skills.

        Args:
            profile: AgentProfile to check
            required_skills: List of required skill IDs

        Returns:
            Average proficiency (1.0 to 5.0)
        """
        proficiencies = []

        for skill in required_skills:
            # Expand skill to include parent capabilities
            expanded_skills = self.taxonomy.expand_capability(skill)

            # Find best matching proficiency
            best_proficiency = 0
            for expanded_skill in expanded_skills:
                if expanded_skill in profile.capabilities:
                    best_proficiency = max(
                        best_proficiency,
                        profile.capabilities[expanded_skill]
                    )

            proficiencies.append(best_proficiency)

        return sum(proficiencies) / len(proficiencies) if proficiencies else 0

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """
        Get agent profile by ID.

        Args:
            agent_id: Agent ID

        Returns:
            AgentProfile if found, None otherwise
        """
        return self.agent_profiles.get(agent_id)

    def list_agents(
        self,
        availability_status: Optional[str] = None
    ) -> List[AgentProfile]:
        """
        List all registered agents.

        Args:
            availability_status: Filter by availability status (optional)

        Returns:
            List of AgentProfile objects
        """
        agents = list(self.agent_profiles.values())

        if availability_status:
            agents = [a for a in agents if a.availability_status == availability_status]

        return agents


# Example usage
if __name__ == "__main__":
    # Create matcher
    matcher = CapabilityMatcher()

    # Register sample agents
    matcher.register_agent(AgentProfile(
        agent_id="agent-001",
        name="Backend Specialist",
        availability_status="available",
        wip_limit=3,
        current_wip=1,
        recent_quality_score=0.92,
        last_active=datetime.now(),
        capabilities={
            "Backend:Python:FastAPI": 5,
            "Backend:Python": 5,
            "Backend": 5,
            "Data:SQL:PostgreSQL": 4,
            "Testing:Unit": 4
        }
    ))

    matcher.register_agent(AgentProfile(
        agent_id="agent-002",
        name="Full Stack Developer",
        availability_status="available",
        wip_limit=3,
        current_wip=2,
        recent_quality_score=0.85,
        last_active=datetime.now(),
        capabilities={
            "Web:React": 4,
            "Backend:Node:Express": 4,
            "Data:SQL:PostgreSQL": 3,
            "Testing:E2E": 3
        }
    ))

    # Match agents for a backend task
    matches = matcher.match(
        required_skills=["Backend:Python:FastAPI", "Data:SQL:PostgreSQL"],
        min_proficiency=3
    )

    print("Matches for Backend:Python:FastAPI + PostgreSQL:")
    for agent_id, score in matches:
        profile = matcher.get_agent_profile(agent_id)
        print(f"  {profile.name} ({agent_id}): score={score:.3f}")
