"""
Capability Registry Integration with team_execution_v2.py

JIRA: MD-2069 (part of MD-2042)
Description: Integration layer connecting CapabilityRegistry to the execution pipeline.

This module provides:
- RegistryEnhancedTeamComposer: Wrapper that uses CapabilityRegistry for agent selection
- ExecutionFeedbackHandler: Records quality scores and updates proficiency post-execution
- CapabilityAwareCoordinator: Coordinator that routes tasks based on capability scoring

Usage:
    from dde.capability_integration import (
        RegistryEnhancedTeamComposer,
        ExecutionFeedbackHandler,
        setup_capability_routing
    )

    # Enhance existing team composer
    composer = RegistryEnhancedTeamComposer(registry)

    # Record execution results
    feedback = ExecutionFeedbackHandler(registry)
    await feedback.on_execution_complete(result)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging

from .capability_registry import (
    CapabilityRegistry,
    AgentProfile,
    MatchScore,
    ScoringWeights,
    create_registry
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes for Integration
# ============================================================================

@dataclass
class ExecutionResult:
    """Result of a task execution for feedback processing."""
    agent_id: str
    task_id: str
    success: bool
    quality_score: float  # 0.0 - 1.0
    execution_time_ms: int
    primary_skill: Optional[str] = None
    skills_used: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class TeamAssignment:
    """Team assignment with agents mapped to roles."""
    team_id: str
    agents: List[AgentProfile]
    role_assignments: Dict[str, str]  # role -> agent_id
    match_scores: Dict[str, MatchScore]  # agent_id -> score
    total_coverage: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingDecision:
    """Decision for routing a task to an agent."""
    task_id: str
    selected_agent: AgentProfile
    match_score: MatchScore
    alternatives: List[tuple[AgentProfile, MatchScore]]
    reasoning: str
    routing_weights: ScoringWeights


# ============================================================================
# Registry-Enhanced Team Composer
# ============================================================================

class RegistryEnhancedTeamComposer:
    """
    Team composition enhanced with CapabilityRegistry lookup.

    JIRA: MD-2069 (part of MD-2042)

    Integrates with TeamComposerAgent from team_execution_v2.py by:
    1. Replacing hardcoded persona mapping with registry lookups
    2. Using real-time agent availability from registry
    3. Applying capability-based scoring for team selection
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        weights: Optional[ScoringWeights] = None
    ):
        """
        Initialize with capability registry.

        Args:
            registry: CapabilityRegistry instance
            weights: Scoring weights for agent selection
        """
        self.registry = registry
        self.weights = weights or ScoringWeights()

    def find_agents_for_expertise(
        self,
        required_expertise: List[str],
        min_proficiency: int = 2,
        availability_required: bool = True
    ) -> List[tuple[AgentProfile, MatchScore]]:
        """
        Find agents that match required expertise from requirement analysis.

        This replaces _extract_personas_for_requirement in team_execution_v2.py

        Args:
            required_expertise: Skills extracted from requirement analysis
            min_proficiency: Minimum proficiency level (default 2)
            availability_required: Only include available agents

        Returns:
            List of (agent, score) tuples sorted by match quality
        """
        # Map common expertise terms to capability taxonomy skills
        skill_mapping = self._map_expertise_to_skills(required_expertise)

        # Route task through registry
        results = self.registry.route_task(
            required_skills=skill_mapping,
            weights=self.weights,
            min_proficiency=min_proficiency,
            availability_required=availability_required,
            limit=10
        )

        logger.info(f"Found {len(results)} agents for expertise: {required_expertise}")
        return results

    def compose_team(
        self,
        required_expertise: List[str],
        team_size: int = 3,
        ensure_coverage: bool = True
    ) -> TeamAssignment:
        """
        Compose an optimal team for the required expertise.

        Args:
            required_expertise: Skills needed
            team_size: Maximum team size
            ensure_coverage: Try to cover all skills

        Returns:
            TeamAssignment with selected agents
        """
        from uuid import uuid4

        skill_mapping = self._map_expertise_to_skills(required_expertise)
        all_agents = self.registry.list_agents()

        selected_agents = []
        role_assignments = {}
        match_scores = {}
        skills_covered = set()

        # Greedy selection: pick agents that maximize coverage
        remaining_skills = set(skill_mapping)

        while len(selected_agents) < team_size and remaining_skills:
            best_agent = None
            best_score = None
            best_new_coverage = set()

            for agent in all_agents:
                if agent.agent_id in [a.agent_id for a in selected_agents]:
                    continue
                if agent.availability_status != "available":
                    continue

                # Calculate score for remaining skills
                score = self.registry.calculate_match_score(
                    agent, list(remaining_skills), self.weights
                )

                new_coverage = set(score.required_skills_matched) - skills_covered

                # Prefer agents that cover more uncovered skills
                if new_coverage and (best_agent is None or
                    len(new_coverage) > len(best_new_coverage) or
                    (len(new_coverage) == len(best_new_coverage) and
                     score.total > best_score.total)):
                    best_agent = agent
                    best_score = score
                    best_new_coverage = new_coverage

            if best_agent:
                selected_agents.append(best_agent)
                match_scores[best_agent.agent_id] = best_score
                skills_covered.update(best_new_coverage)
                remaining_skills -= best_new_coverage

                # Assign role based on primary skill
                primary_skill = best_score.required_skills_matched[0] if best_score.required_skills_matched else "general"
                role_assignments[primary_skill] = best_agent.agent_id
            else:
                break

        # Calculate total coverage
        total_coverage = len(skills_covered) / len(skill_mapping) if skill_mapping else 0

        return TeamAssignment(
            team_id=f"team-{uuid4().hex[:8]}",
            agents=selected_agents,
            role_assignments=role_assignments,
            match_scores=match_scores,
            total_coverage=total_coverage
        )

    def validate_team_coverage(
        self,
        required_expertise: List[str]
    ) -> Dict[str, Any]:
        """
        Validate if current agents can cover the required expertise.

        Args:
            required_expertise: Skills needed

        Returns:
            Coverage analysis with gaps
        """
        skill_mapping = self._map_expertise_to_skills(required_expertise)
        coverage = self.registry.get_capability_coverage()

        covered_skills = []
        uncovered_skills = []
        partial_skills = []

        for skill in skill_mapping:
            count = coverage.get(skill, 0)
            if count == 0:
                # Check parent skills
                parent_count = sum(
                    coverage.get(s, 0) for s in coverage.keys()
                    if skill.startswith(s) or s.startswith(skill)
                )
                if parent_count > 0:
                    partial_skills.append({"skill": skill, "parent_coverage": parent_count})
                else:
                    uncovered_skills.append(skill)
            else:
                covered_skills.append({"skill": skill, "agent_count": count})

        return {
            "total_skills_required": len(skill_mapping),
            "fully_covered": len(covered_skills),
            "partially_covered": len(partial_skills),
            "uncovered": len(uncovered_skills),
            "coverage_percentage": len(covered_skills) / len(skill_mapping) * 100 if skill_mapping else 100,
            "details": {
                "covered": covered_skills,
                "partial": partial_skills,
                "gaps": uncovered_skills
            }
        }

    def _map_expertise_to_skills(self, expertise: List[str]) -> List[str]:
        """Map generic expertise terms to capability taxonomy skills."""
        # Common mappings from requirement analysis to taxonomy
        mappings = {
            "python": "Backend:Python",
            "fastapi": "Backend:Python:FastAPI",
            "react": "Web:React",
            "typescript": "Web:TypeScript",
            "javascript": "Web:JavaScript",
            "nodejs": "Backend:Node",
            "node.js": "Backend:Node",
            "database": "Data:SQL",
            "postgresql": "Data:PostgreSQL",
            "postgres": "Data:PostgreSQL",
            "sql": "Data:SQL",
            "testing": "Testing:Unit",
            "unit testing": "Testing:Unit",
            "integration testing": "Testing:Integration",
            "e2e testing": "Testing:E2E",
            "docker": "DevOps:Docker",
            "kubernetes": "DevOps:Kubernetes",
            "ci/cd": "DevOps:CI/CD",
            "security": "Security:OWASP",
            "api": "Architecture:APIDesign",
            "rest api": "Architecture:APIDesign",
            "frontend": "Web:React",
            "backend": "Backend:Python",
            "fullstack": "Web:React",
            "devops": "DevOps:Docker",
            "mobile": "Mobile:ReactNative",
            "aws": "Cloud:AWS",
            "performance": "Testing:Performance",
            "documentation": "Documentation:Technical"
        }

        skills = []
        for exp in expertise:
            exp_lower = exp.lower()

            # Direct mapping
            if exp_lower in mappings:
                skills.append(mappings[exp_lower])
            # Partial matching
            elif any(key in exp_lower for key in mappings):
                for key, skill in mappings.items():
                    if key in exp_lower:
                        skills.append(skill)
                        break
            else:
                # Use as-is if it looks like a taxonomy skill
                if ":" in exp:
                    skills.append(exp)
                else:
                    # Default to Backend:Python for unknown
                    logger.warning(f"Unknown expertise term: {exp}")

        return list(set(skills)) if skills else ["Backend:Python"]


# ============================================================================
# Execution Feedback Handler
# ============================================================================

class ExecutionFeedbackHandler:
    """
    Handles post-execution feedback to update capability scores.

    JIRA: MD-2069 (part of MD-2042)

    Called after task completion to:
    1. Record quality scores in history
    2. Update capability proficiency based on performance
    3. Update agent availability status
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        auto_boost_threshold: float = 0.9,
        auto_demote_threshold: float = 0.3
    ):
        """
        Initialize feedback handler.

        Args:
            registry: CapabilityRegistry instance
            auto_boost_threshold: Quality threshold for auto-boosting proficiency
            auto_demote_threshold: Quality threshold for considering demotion
        """
        self.registry = registry
        self.auto_boost_threshold = auto_boost_threshold
        self.auto_demote_threshold = auto_demote_threshold

    async def on_execution_complete(self, result: ExecutionResult) -> Dict[str, Any]:
        """
        Process execution completion and update registry.

        Args:
            result: ExecutionResult from task execution

        Returns:
            Summary of updates made
        """
        updates = {
            "quality_recorded": False,
            "proficiency_updated": False,
            "status_updated": False,
            "details": []
        }

        try:
            # 1. Record quality score
            self.registry.record_quality_score(
                agent_id=result.agent_id,
                task_id=result.task_id,
                quality_score=result.quality_score,
                execution_time_ms=result.execution_time_ms,
                skill_id=result.primary_skill
            )
            updates["quality_recorded"] = True
            updates["details"].append(f"Recorded quality: {result.quality_score:.2f}")

            # 2. Update proficiency based on performance
            if result.success and result.quality_score > self.auto_boost_threshold:
                # Boost proficiency for high-quality work
                if result.primary_skill:
                    boosted = self.registry.boost_proficiency(
                        agent_id=result.agent_id,
                        skill_id=result.primary_skill,
                        boost=0.1
                    )
                    if boosted:
                        updates["proficiency_updated"] = True
                        updates["details"].append(
                            f"Boosted {result.primary_skill} proficiency"
                        )

            # 3. Update agent availability (task complete = freed up)
            self.registry.update_agent_status(
                agent_id=result.agent_id,
                status="available",
                wip=-1  # Decrement WIP
            )
            updates["status_updated"] = True
            updates["details"].append("Agent status updated to available")

            logger.info(
                f"Processed feedback for {result.agent_id}: "
                f"quality={result.quality_score:.2f}, success={result.success}"
            )

        except Exception as e:
            logger.error(f"Failed to process execution feedback: {e}")
            updates["error"] = str(e)

        return updates

    async def on_execution_start(self, agent_id: str, task_id: str) -> bool:
        """
        Mark agent as busy when execution starts.

        Args:
            agent_id: Agent starting work
            task_id: Task being started

        Returns:
            True if status updated
        """
        try:
            self.registry.update_agent_status(
                agent_id=agent_id,
                status="busy",
                wip=1  # Increment WIP
            )
            logger.info(f"Agent {agent_id} marked busy for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            return False

    def get_agent_performance_summary(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance summary for an agent.

        Args:
            agent_id: Agent to summarize

        Returns:
            Performance metrics
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        quality_history = agent.quality_history[-20:]

        return {
            "agent_id": agent_id,
            "name": agent.name,
            "current_status": agent.availability_status,
            "wip": f"{agent.current_wip}/{agent.wip_limit}",
            "quality_stats": {
                "total_scores": len(quality_history),
                "average": sum(quality_history) / len(quality_history) if quality_history else 0,
                "min": min(quality_history) if quality_history else 0,
                "max": max(quality_history) if quality_history else 0,
                "recent_trend": self._calculate_trend(quality_history)
            },
            "capabilities_count": len(agent.capabilities),
            "top_capabilities": [
                {"skill": c.skill_id, "proficiency": c.proficiency}
                for c in sorted(agent.capabilities, key=lambda x: x.proficiency, reverse=True)[:5]
            ]
        }

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate recent performance trend."""
        if len(scores) < 4:
            return "insufficient_data"

        recent = sum(scores[-4:]) / 4
        older = sum(scores[:-4]) / (len(scores) - 4)

        diff = recent - older
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"


# ============================================================================
# Integration Setup Function
# ============================================================================

def setup_capability_routing(
    database_url: Optional[str] = None,
    taxonomy_path: str = "config/capability_taxonomy.yaml",
    weights: Optional[ScoringWeights] = None
) -> tuple[CapabilityRegistry, RegistryEnhancedTeamComposer, ExecutionFeedbackHandler]:
    """
    Set up complete capability routing integration.

    JIRA: MD-2069 (part of MD-2042)

    Usage:
        registry, composer, feedback = setup_capability_routing(
            database_url="postgresql://...",
            weights=ScoringWeights.quality_focused()
        )

        # In team_execution_v2.py
        agents = composer.find_agents_for_expertise(classification.required_expertise)
        team = composer.compose_team(classification.required_expertise)

        # After execution
        await feedback.on_execution_complete(result)

    Args:
        database_url: PostgreSQL connection string (None for in-memory)
        taxonomy_path: Path to capability taxonomy YAML
        weights: Scoring weights for routing

    Returns:
        Tuple of (registry, composer, feedback_handler)
    """
    # Create registry
    registry = create_registry(
        database_url=database_url,
        taxonomy_path=taxonomy_path
    )

    # Create composer with registry
    composer = RegistryEnhancedTeamComposer(
        registry=registry,
        weights=weights
    )

    # Create feedback handler
    feedback = ExecutionFeedbackHandler(registry=registry)

    logger.info("Capability routing integration initialized")

    return registry, composer, feedback


# ============================================================================
# Monkey-patch helper for team_execution_v2.py (optional)
# ============================================================================

def patch_team_composer(
    team_composer_instance: Any,
    registry: CapabilityRegistry,
    weights: Optional[ScoringWeights] = None
) -> None:
    """
    Monkey-patch an existing TeamComposerAgent to use CapabilityRegistry.

    This allows gradual migration without modifying team_execution_v2.py directly.

    Args:
        team_composer_instance: Instance of TeamComposerAgent
        registry: CapabilityRegistry instance
        weights: Scoring weights
    """
    enhanced_composer = RegistryEnhancedTeamComposer(registry, weights)

    # Store original method
    original_extract = team_composer_instance._extract_personas_for_requirement

    def enhanced_extract(classification, *args, **kwargs):
        """Enhanced persona extraction using capability registry."""
        required_expertise = getattr(classification, 'required_expertise', [])

        if required_expertise:
            # Use registry-based lookup
            results = enhanced_composer.find_agents_for_expertise(
                required_expertise,
                availability_required=False
            )

            if results:
                # Map to persona format expected by team_execution_v2
                personas = []
                for agent, score in results[:5]:
                    personas.append({
                        "agent_id": agent.agent_id,
                        "persona_type": agent.persona_type,
                        "name": agent.name,
                        "match_score": score.total,
                        "capabilities": [c.skill_id for c in agent.capabilities]
                    })
                return personas

        # Fall back to original if no registry results
        return original_extract(classification, *args, **kwargs)

    # Apply patch
    team_composer_instance._extract_personas_for_requirement = enhanced_extract
    logger.info("TeamComposerAgent patched with CapabilityRegistry integration")


# Export all public classes
__all__ = [
    "ExecutionResult",
    "TeamAssignment",
    "RoutingDecision",
    "RegistryEnhancedTeamComposer",
    "ExecutionFeedbackHandler",
    "setup_capability_routing",
    "patch_team_composer"
]
