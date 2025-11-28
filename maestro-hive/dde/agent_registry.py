"""
DDE Agent Profile Registry (MD-883)

Persistent storage for agent profiles with capabilities.
Integrates with PerformanceTracker for ML-ready scoring.

Features:
- CRUD operations for agent profiles
- Capability storage with proficiency levels
- WIP limit and load tracking
- Quality score history
- Integration with performance tracker
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from dde.performance_tracker import get_performance_tracker, AgentPerformanceSummary

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Agent capability with proficiency level"""
    skill_id: str  # e.g., "Backend:Python:FastAPI"
    proficiency: int  # 1-5 scale
    source: str = "manual"  # manual, inferred, historical
    confidence: float = 1.0  # For inferred capabilities
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'skill_id': self.skill_id,
            'proficiency': self.proficiency,
            'source': self.source,
            'confidence': self.confidence,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCapability':
        return cls(
            skill_id=data['skill_id'],
            proficiency=data['proficiency'],
            source=data.get('source', 'manual'),
            confidence=data.get('confidence', 1.0),
            last_used=datetime.fromisoformat(data['last_used']) if data.get('last_used') else None
        )


@dataclass
class AgentProfile:
    """Complete agent profile with capabilities and status"""
    agent_id: str
    name: str
    persona_type: str  # e.g., "requirement_analyst", "backend_developer"
    availability_status: str = "available"  # available, busy, offline
    wip_limit: int = 3
    current_wip: int = 0
    capabilities: List[AgentCapability] = field(default_factory=list)
    quality_score_history: List[float] = field(default_factory=list)  # Last N scores
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'persona_type': self.persona_type,
            'availability_status': self.availability_status,
            'wip_limit': self.wip_limit,
            'current_wip': self.current_wip,
            'capabilities': [c.to_dict() for c in self.capabilities],
            'quality_score_history': self.quality_score_history,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentProfile':
        return cls(
            agent_id=data['agent_id'],
            name=data['name'],
            persona_type=data['persona_type'],
            availability_status=data.get('availability_status', 'available'),
            wip_limit=data.get('wip_limit', 3),
            current_wip=data.get('current_wip', 0),
            capabilities=[AgentCapability.from_dict(c) for c in data.get('capabilities', [])],
            quality_score_history=data.get('quality_score_history', []),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )

    @property
    def recent_quality_score(self) -> float:
        """Get most recent quality score or default"""
        if self.quality_score_history:
            return sum(self.quality_score_history[-5:]) / min(5, len(self.quality_score_history))
        return 0.8  # Default

    @property
    def load_factor(self) -> float:
        """Current load as percentage of WIP limit"""
        if self.wip_limit <= 0:
            return 1.0
        return self.current_wip / self.wip_limit

    def has_capability(self, skill_id: str, min_proficiency: int = 1) -> bool:
        """Check if agent has a capability at minimum proficiency"""
        for cap in self.capabilities:
            if cap.skill_id == skill_id and cap.proficiency >= min_proficiency:
                return True
            # Check parent capabilities (e.g., Backend:Python for Backend:Python:FastAPI)
            if skill_id.startswith(cap.skill_id) and cap.proficiency >= min_proficiency:
                return True
        return False

    def get_proficiency(self, skill_id: str) -> int:
        """Get proficiency for a skill (0 if not found)"""
        for cap in self.capabilities:
            if cap.skill_id == skill_id:
                return cap.proficiency
            # Check hierarchy
            if skill_id.startswith(cap.skill_id):
                return cap.proficiency
        return 0

    def add_quality_score(self, score: float):
        """Add a quality score to history (keep last 20)"""
        self.quality_score_history.append(score)
        if len(self.quality_score_history) > 20:
            self.quality_score_history = self.quality_score_history[-20:]
        self.updated_at = datetime.now()


class AgentRegistry:
    """
    Agent Profile Registry

    Manages agent profiles with persistent storage.
    Integrates with PerformanceTracker for metrics.
    """

    def __init__(self, storage_path: str = "data/agents"):
        """
        Initialize agent registry.

        Args:
            storage_path: Path to store agent data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._profiles: Dict[str, AgentProfile] = {}
        self._load_profiles()

        logger.info(f"✅ AgentRegistry initialized")
        logger.info(f"   Storage: {self.storage_path}")
        logger.info(f"   Agents registered: {len(self._profiles)}")

    def _load_profiles(self):
        """Load profiles from storage"""
        profiles_file = self.storage_path / "profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file) as f:
                    data = json.load(f)
                    for profile_data in data:
                        profile = AgentProfile.from_dict(profile_data)
                        self._profiles[profile.agent_id] = profile
            except Exception as e:
                logger.warning(f"   Failed to load profiles: {e}")

    def _save_profiles(self):
        """Save profiles to storage"""
        profiles_file = self.storage_path / "profiles.json"
        try:
            data = [p.to_dict() for p in self._profiles.values()]
            with open(profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def register_agent(self, profile: AgentProfile) -> AgentProfile:
        """
        Register a new agent or update existing.

        Args:
            profile: AgentProfile to register

        Returns:
            Registered profile
        """
        self._profiles[profile.agent_id] = profile
        self._save_profiles()
        logger.info(f"📝 Registered agent: {profile.name} ({profile.agent_id})")
        return profile

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent profile by ID"""
        return self._profiles.get(agent_id)

    def get_agent_by_persona(self, persona_type: str) -> Optional[AgentProfile]:
        """Get agent profile by persona type"""
        for profile in self._profiles.values():
            if profile.persona_type == persona_type:
                return profile
        return None

    def list_agents(
        self,
        availability_status: Optional[str] = None,
        persona_type: Optional[str] = None
    ) -> List[AgentProfile]:
        """
        List agents with optional filters.

        Args:
            availability_status: Filter by status
            persona_type: Filter by persona type

        Returns:
            List of matching profiles
        """
        agents = list(self._profiles.values())

        if availability_status:
            agents = [a for a in agents if a.availability_status == availability_status]

        if persona_type:
            agents = [a for a in agents if a.persona_type == persona_type]

        return agents

    def update_agent_status(
        self,
        agent_id: str,
        availability_status: Optional[str] = None,
        current_wip: Optional[int] = None
    ):
        """
        Update agent status.

        Args:
            agent_id: Agent to update
            availability_status: New status
            current_wip: New WIP count
        """
        if agent_id not in self._profiles:
            raise ValueError(f"Agent not found: {agent_id}")

        profile = self._profiles[agent_id]

        if availability_status is not None:
            profile.availability_status = availability_status

        if current_wip is not None:
            profile.current_wip = current_wip

        profile.updated_at = datetime.now()
        self._save_profiles()

    def update_capability(
        self,
        agent_id: str,
        skill_id: str,
        proficiency: int,
        source: str = "manual"
    ):
        """
        Update or add agent capability.

        Args:
            agent_id: Agent to update
            skill_id: Skill identifier
            proficiency: Proficiency level (1-5)
            source: How capability was determined
        """
        if agent_id not in self._profiles:
            raise ValueError(f"Agent not found: {agent_id}")

        profile = self._profiles[agent_id]

        # Find existing capability
        for cap in profile.capabilities:
            if cap.skill_id == skill_id:
                cap.proficiency = proficiency
                cap.source = source
                cap.last_used = datetime.now()
                break
        else:
            # Add new capability
            profile.capabilities.append(AgentCapability(
                skill_id=skill_id,
                proficiency=proficiency,
                source=source
            ))

        profile.updated_at = datetime.now()
        self._save_profiles()

    def record_quality_score(self, agent_id: str, score: float):
        """
        Record a quality score for an agent.

        Args:
            agent_id: Agent ID
            score: Quality score (0.0 to 1.0)
        """
        if agent_id not in self._profiles:
            # Auto-create profile for unknown agents
            logger.warning(f"Agent {agent_id} not found, skipping quality score")
            return

        profile = self._profiles[agent_id]
        profile.add_quality_score(score)
        self._save_profiles()

    def get_agents_with_capability(
        self,
        skill_id: str,
        min_proficiency: int = 1
    ) -> List[AgentProfile]:
        """
        Get all agents with a specific capability.

        Args:
            skill_id: Required skill
            min_proficiency: Minimum proficiency level

        Returns:
            List of capable agents
        """
        capable = []
        for profile in self._profiles.values():
            if profile.has_capability(skill_id, min_proficiency):
                capable.append(profile)

        # Sort by proficiency descending
        capable.sort(
            key=lambda p: p.get_proficiency(skill_id),
            reverse=True
        )

        return capable

    def get_agent_with_performance(
        self,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get agent profile enriched with performance metrics.

        Args:
            agent_id: Agent ID

        Returns:
            Combined profile and performance data
        """
        profile = self.get_agent(agent_id)
        if not profile:
            return None

        # Get performance from tracker
        tracker = get_performance_tracker()
        performance = tracker.get_agent_summary(agent_id)

        result = profile.to_dict()
        if performance:
            result['performance'] = performance.to_dict()

        return result

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent profile.

        Args:
            agent_id: Agent to delete

        Returns:
            True if deleted, False if not found
        """
        if agent_id in self._profiles:
            del self._profiles[agent_id]
            self._save_profiles()
            logger.info(f"🗑️ Deleted agent: {agent_id}")
            return True
        return False

    def initialize_default_agents(self):
        """
        Initialize default SDLC agents from persona definitions.

        This creates profiles for standard personas if they don't exist.
        """
        default_agents = [
            {
                'agent_id': 'requirement_analyst',
                'name': 'Requirement Analyst',
                'persona_type': 'requirement_analyst',
                'capabilities': [
                    ('Analysis:Requirements', 5),
                    ('Documentation:Technical', 4),
                    ('Communication:Stakeholder', 4),
                ]
            },
            {
                'agent_id': 'backend_developer',
                'name': 'Marcus (Backend Developer)',
                'persona_type': 'backend_developer',
                'capabilities': [
                    ('Backend:Python:FastAPI', 5),
                    ('Backend:Python', 5),
                    ('Data:SQL:PostgreSQL', 4),
                    ('Testing:Unit', 4),
                    ('DevOps:Docker', 3),
                ]
            },
            {
                'agent_id': 'qa_engineer',
                'name': 'Rachel (QA Engineer)',
                'persona_type': 'qa_engineer',
                'capabilities': [
                    ('Testing:Unit', 5),
                    ('Testing:Integration', 5),
                    ('Testing:E2E', 5),
                    ('Testing:Performance', 4),
                    ('Quality:CodeReview', 4),
                ]
            },
            {
                'agent_id': 'devops_engineer',
                'name': 'David (DevOps Engineer)',
                'persona_type': 'devops_engineer',
                'capabilities': [
                    ('DevOps:Docker', 5),
                    ('DevOps:Kubernetes', 5),
                    ('DevOps:CI/CD', 5),
                    ('Cloud:AWS', 4),
                    ('Cloud:GCP', 3),
                    ('Monitoring:Observability', 4),
                ]
            },
            {
                'agent_id': 'frontend_developer',
                'name': 'Frontend Developer',
                'persona_type': 'frontend_developer',
                'capabilities': [
                    ('Frontend:React', 5),
                    ('Frontend:TypeScript', 5),
                    ('Frontend:CSS', 4),
                    ('Testing:Unit', 3),
                ]
            },
        ]

        created = 0
        for agent_def in default_agents:
            if agent_def['agent_id'] not in self._profiles:
                capabilities = [
                    AgentCapability(skill_id=skill, proficiency=prof)
                    for skill, prof in agent_def['capabilities']
                ]

                profile = AgentProfile(
                    agent_id=agent_def['agent_id'],
                    name=agent_def['name'],
                    persona_type=agent_def['persona_type'],
                    capabilities=capabilities
                )

                self.register_agent(profile)
                created += 1

        if created > 0:
            logger.info(f"✅ Initialized {created} default agents")


# Global instance
_registry: Optional[AgentRegistry] = None


def get_agent_registry(storage_path: str = "data/agents") -> AgentRegistry:
    """Get or create global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry(storage_path)
    return _registry


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create registry
    registry = get_agent_registry()

    # Initialize defaults
    registry.initialize_default_agents()

    # List all agents
    print("\n=== Registered Agents ===")
    for agent in registry.list_agents():
        print(f"\n{agent.name} ({agent.agent_id})")
        print(f"  Status: {agent.availability_status}")
        print(f"  WIP: {agent.current_wip}/{agent.wip_limit}")
        print(f"  Quality: {agent.recent_quality_score:.2f}")
        print(f"  Capabilities: {len(agent.capabilities)}")
        for cap in agent.capabilities[:3]:
            print(f"    - {cap.skill_id}: {cap.proficiency}/5")

    # Find agents with specific capability
    print("\n=== Agents with Python Capability ===")
    python_agents = registry.get_agents_with_capability("Backend:Python", min_proficiency=4)
    for agent in python_agents:
        print(f"  {agent.name}: proficiency {agent.get_proficiency('Backend:Python')}")
