"""
DDE Task-Agent Matching Service (MD-884)

Matches tasks to agents using a scoring algorithm.
Rule-based now, ML-ready for future enhancement.

Scoring Algorithm:
- Capability match (40%)
- Availability (30%)
- Recent quality (20%)
- Load factor (10%)

ML Integration Points:
- Replace static weights with learned weights
- Add task complexity prediction
- Historical success rate by task type
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from dde.agent_registry import get_agent_registry, AgentProfile
from dde.performance_tracker import get_performance_tracker

logger = logging.getLogger(__name__)


@dataclass
class TaskRequirements:
    """Requirements for a task"""
    task_id: str
    task_type: str
    required_skills: List[str]
    min_proficiency: int = 3
    complexity: str = "moderate"  # simple, moderate, complex
    priority: str = "normal"  # low, normal, high, critical
    estimated_effort_hours: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MatchResult:
    """Result of matching an agent to a task"""
    agent_id: str
    agent_name: str
    score: float  # 0.0 to 1.0
    capability_score: float
    availability_score: float
    quality_score: float
    load_score: float
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'score': round(self.score, 4),
            'capability_score': round(self.capability_score, 4),
            'availability_score': round(self.availability_score, 4),
            'quality_score': round(self.quality_score, 4),
            'load_score': round(self.load_score, 4),
            'reasons': self.reasons
        }


class TaskMatcher:
    """
    Task-Agent Matching Service

    Matches tasks to agents using a multi-factor scoring algorithm.
    Integrates with AgentRegistry and PerformanceTracker.
    """

    # Default weights (ML will learn optimal weights)
    DEFAULT_WEIGHTS = {
        'capability': 0.40,
        'availability': 0.30,
        'quality': 0.20,
        'load': 0.10
    }

    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize task matcher.

        Args:
            weights: Custom scoring weights (optional)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.registry = get_agent_registry()
        self.tracker = get_performance_tracker()

        logger.info(f"✅ TaskMatcher initialized")
        logger.info(f"   Weights: capability={self.weights['capability']}, "
                   f"availability={self.weights['availability']}, "
                   f"quality={self.weights['quality']}, "
                   f"load={self.weights['load']}")

    def match(
        self,
        requirements: TaskRequirements,
        max_results: int = 5,
        only_available: bool = True
    ) -> List[MatchResult]:
        """
        Match agents to task requirements.

        Args:
            requirements: Task requirements
            max_results: Maximum number of results
            only_available: Only consider available agents

        Returns:
            List of MatchResult sorted by score (descending)
        """
        candidates = []

        # Get all agents
        agents = self.registry.list_agents(
            availability_status="available" if only_available else None
        )

        for agent in agents:
            # Check if agent has required capabilities
            if not self._has_required_capabilities(agent, requirements):
                continue

            # Calculate match score
            result = self._calculate_match_score(agent, requirements)
            candidates.append(result)

        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)

        return candidates[:max_results]

    def get_best_match(
        self,
        requirements: TaskRequirements
    ) -> Optional[MatchResult]:
        """
        Get the single best matching agent.

        Args:
            requirements: Task requirements

        Returns:
            Best MatchResult or None
        """
        matches = self.match(requirements, max_results=1)
        return matches[0] if matches else None

    def match_by_persona_type(
        self,
        persona_type: str,
        task_type: str = None
    ) -> Optional[MatchResult]:
        """
        Get match for a specific persona type.

        Useful when the persona is already determined by workflow
        but we want to score and validate the assignment.

        Args:
            persona_type: Required persona type
            task_type: Optional task type for scoring

        Returns:
            MatchResult or None
        """
        agent = self.registry.get_agent_by_persona(persona_type)
        if not agent:
            logger.warning(f"No agent found for persona: {persona_type}")
            return None

        # Create minimal requirements
        requirements = TaskRequirements(
            task_id=f"persona-{persona_type}",
            task_type=task_type or persona_type,
            required_skills=[]  # No specific requirements
        )

        return self._calculate_match_score(agent, requirements)

    def _has_required_capabilities(
        self,
        agent: AgentProfile,
        requirements: TaskRequirements
    ) -> bool:
        """Check if agent has all required capabilities"""
        for skill in requirements.required_skills:
            if not agent.has_capability(skill, requirements.min_proficiency):
                return False
        return True

    def _calculate_match_score(
        self,
        agent: AgentProfile,
        requirements: TaskRequirements
    ) -> MatchResult:
        """
        Calculate match score for an agent.

        This is the core scoring algorithm that ML will enhance.

        Args:
            agent: Agent to score
            requirements: Task requirements

        Returns:
            MatchResult with detailed scores
        """
        reasons = []

        # 1. Capability score (0.0 to 1.0)
        capability_score = self._calculate_capability_score(agent, requirements)
        if capability_score > 0.8:
            reasons.append(f"Strong skill match ({capability_score:.0%})")
        elif capability_score < 0.5:
            reasons.append(f"Weak skill match ({capability_score:.0%})")

        # 2. Availability score (0.0 to 1.0)
        availability_score = self._calculate_availability_score(agent)
        if agent.availability_status == "available":
            reasons.append("Currently available")
        else:
            reasons.append(f"Status: {agent.availability_status}")

        # 3. Quality score (0.0 to 1.0)
        quality_score = self._calculate_quality_score(agent, requirements.task_type)
        if quality_score > 0.9:
            reasons.append(f"Excellent quality history ({quality_score:.0%})")
        elif quality_score < 0.7:
            reasons.append(f"Quality needs improvement ({quality_score:.0%})")

        # 4. Load score (0.0 to 1.0, higher is better = less load)
        load_score = self._calculate_load_score(agent)
        if load_score < 0.3:
            reasons.append(f"High workload ({agent.current_wip}/{agent.wip_limit} WIP)")
        elif load_score > 0.8:
            reasons.append("Low workload")

        # Calculate weighted total
        total_score = (
            capability_score * self.weights['capability'] +
            availability_score * self.weights['availability'] +
            quality_score * self.weights['quality'] +
            load_score * self.weights['load']
        )

        return MatchResult(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            score=total_score,
            capability_score=capability_score,
            availability_score=availability_score,
            quality_score=quality_score,
            load_score=load_score,
            reasons=reasons
        )

    def _calculate_capability_score(
        self,
        agent: AgentProfile,
        requirements: TaskRequirements
    ) -> float:
        """Calculate capability match score"""
        if not requirements.required_skills:
            # No specific requirements, use default score
            return 0.8

        total_proficiency = 0
        max_proficiency = len(requirements.required_skills) * 5

        for skill in requirements.required_skills:
            proficiency = agent.get_proficiency(skill)
            total_proficiency += proficiency

        if max_proficiency == 0:
            return 1.0

        return total_proficiency / max_proficiency

    def _calculate_availability_score(self, agent: AgentProfile) -> float:
        """Calculate availability score"""
        status_scores = {
            'available': 1.0,
            'busy': 0.3,
            'offline': 0.0
        }
        return status_scores.get(agent.availability_status, 0.5)

    def _calculate_quality_score(
        self,
        agent: AgentProfile,
        task_type: str
    ) -> float:
        """
        Calculate quality score based on history.

        Uses both agent profile history and performance tracker.
        """
        # Get from agent profile
        profile_score = agent.recent_quality_score

        # Get from performance tracker
        performance = self.tracker.get_agent_summary(agent.agent_id)
        if performance:
            # Weight recent performance more
            tracker_score = performance.avg_quality_score

            # Check if agent has experience with this task type
            if task_type in performance.executions_by_task_type:
                # Has experience - trust performance score more
                return tracker_score * 0.7 + profile_score * 0.3
            else:
                # No experience with this task type
                return profile_score * 0.6 + tracker_score * 0.4

        return profile_score

    def _calculate_load_score(self, agent: AgentProfile) -> float:
        """Calculate load score (higher = less loaded)"""
        load_factor = agent.load_factor
        # Invert: 0 load = 1.0 score, full load = 0.0 score
        return max(0.0, 1.0 - load_factor)

    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update scoring weights.

        ML model will call this with learned optimal weights.

        Args:
            new_weights: New weight values
        """
        # Validate weights sum to 1.0
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0: {total}")
            # Normalize
            new_weights = {k: v / total for k, v in new_weights.items()}

        self.weights.update(new_weights)
        logger.info(f"📊 Updated matching weights: {self.weights}")

    def get_match_explanation(
        self,
        requirements: TaskRequirements,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed explanation of match score for an agent.

        Useful for debugging and ML model interpretation.

        Args:
            requirements: Task requirements
            agent_id: Agent to explain

        Returns:
            Detailed explanation dictionary
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return {'error': f'Agent not found: {agent_id}'}

        result = self._calculate_match_score(agent, requirements)

        return {
            'agent_id': agent_id,
            'agent_name': agent.name,
            'requirements': {
                'task_type': requirements.task_type,
                'required_skills': requirements.required_skills,
                'min_proficiency': requirements.min_proficiency
            },
            'scores': {
                'total': result.score,
                'capability': {
                    'score': result.capability_score,
                    'weight': self.weights['capability'],
                    'weighted': result.capability_score * self.weights['capability']
                },
                'availability': {
                    'score': result.availability_score,
                    'weight': self.weights['availability'],
                    'weighted': result.availability_score * self.weights['availability']
                },
                'quality': {
                    'score': result.quality_score,
                    'weight': self.weights['quality'],
                    'weighted': result.quality_score * self.weights['quality']
                },
                'load': {
                    'score': result.load_score,
                    'weight': self.weights['load'],
                    'weighted': result.load_score * self.weights['load']
                }
            },
            'agent_details': {
                'status': agent.availability_status,
                'wip': f"{agent.current_wip}/{agent.wip_limit}",
                'capabilities': [
                    {'skill': c.skill_id, 'proficiency': c.proficiency}
                    for c in agent.capabilities
                ]
            },
            'reasons': result.reasons
        }


# Global instance
_matcher: Optional[TaskMatcher] = None


def get_task_matcher() -> TaskMatcher:
    """Get or create global task matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = TaskMatcher()
    return _matcher


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize registry with defaults
    registry = get_agent_registry()
    registry.initialize_default_agents()

    # Create matcher
    matcher = get_task_matcher()

    # Create task requirements
    requirements = TaskRequirements(
        task_id="task-001",
        task_type="backend_development",
        required_skills=["Backend:Python:FastAPI", "Data:SQL:PostgreSQL"],
        min_proficiency=3,
        complexity="moderate"
    )

    # Find matches
    print("\n=== Task Matching Results ===")
    print(f"Task: {requirements.task_type}")
    print(f"Required: {requirements.required_skills}")
    print()

    matches = matcher.match(requirements)

    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.agent_name} ({match.agent_id})")
        print(f"   Total Score: {match.score:.3f}")
        print(f"   - Capability: {match.capability_score:.3f}")
        print(f"   - Availability: {match.availability_score:.3f}")
        print(f"   - Quality: {match.quality_score:.3f}")
        print(f"   - Load: {match.load_score:.3f}")
        print(f"   Reasons: {', '.join(match.reasons)}")
        print()

    # Get detailed explanation
    if matches:
        best_match = matches[0]
        print("\n=== Detailed Explanation ===")
        explanation = matcher.get_match_explanation(requirements, best_match.agent_id)
        import json
        print(json.dumps(explanation, indent=2))
