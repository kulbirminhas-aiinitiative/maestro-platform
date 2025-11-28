"""
DDE Dynamic Routing Engine (MD-887)

Runtime task distribution with load balancing.
Routes tasks to optimal agents based on multiple factors.

Features:
- Capability-based routing
- Load balancing
- Real-time status updates
- Fallback strategies

ML Integration Points:
- Reinforcement learning for routing
- Context-aware routing (project type, urgency)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from dde.agent_registry import get_agent_registry, AgentProfile
from dde.task_matcher import get_task_matcher, TaskRequirements, MatchResult
from dde.agent_evaluator import get_agent_evaluator
from dde.performance_tracker import get_performance_tracker

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Routing strategies"""
    BEST_MATCH = "best_match"  # Highest scoring agent
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    LEAST_LOADED = "least_loaded"  # Agent with least WIP
    SPECIALIZED = "specialized"  # Best for task type
    FALLBACK = "fallback"  # Use fallback when primary unavailable


@dataclass
class RoutingDecision:
    """Result of a routing decision"""
    task_id: str
    agent_id: str
    agent_name: str
    strategy_used: str
    confidence: float
    match_score: float
    reasons: List[str]
    alternatives: List[str]
    routed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'strategy_used': self.strategy_used,
            'confidence': round(self.confidence, 4),
            'match_score': round(self.match_score, 4),
            'reasons': self.reasons,
            'alternatives': self.alternatives,
            'routed_at': self.routed_at.isoformat()
        }


class RoutingEngine:
    """
    Dynamic Routing Engine

    Routes tasks to optimal agents with load balancing.
    """

    def __init__(self):
        """Initialize routing engine"""
        self.registry = get_agent_registry()
        self.matcher = get_task_matcher()
        self.evaluator = get_agent_evaluator()
        self.tracker = get_performance_tracker()

        # Round-robin state
        self._round_robin_index: Dict[str, int] = {}

        # Routing statistics
        self._routing_stats: Dict[str, int] = {}

        logger.info("✅ RoutingEngine initialized")

    def route_task(
        self,
        requirements: TaskRequirements,
        strategy: RoutingStrategy = RoutingStrategy.BEST_MATCH,
        exclude_agents: List[str] = None
    ) -> Optional[RoutingDecision]:
        """
        Route a task to an agent.

        Args:
            requirements: Task requirements
            strategy: Routing strategy
            exclude_agents: Agents to exclude

        Returns:
            RoutingDecision or None
        """
        exclude = set(exclude_agents or [])

        # Get matches from task matcher
        matches = self.matcher.match(requirements, max_results=10)

        # Filter excluded agents
        matches = [m for m in matches if m.agent_id not in exclude]

        if not matches:
            logger.warning(f"No available agents for task {requirements.task_id}")
            return None

        # Apply routing strategy
        if strategy == RoutingStrategy.BEST_MATCH:
            decision = self._route_best_match(requirements, matches)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            decision = self._route_round_robin(requirements, matches)
        elif strategy == RoutingStrategy.LEAST_LOADED:
            decision = self._route_least_loaded(requirements, matches)
        elif strategy == RoutingStrategy.SPECIALIZED:
            decision = self._route_specialized(requirements, matches)
        else:
            decision = self._route_best_match(requirements, matches)

        if decision:
            # Update routing stats
            self._routing_stats[decision.agent_id] = \
                self._routing_stats.get(decision.agent_id, 0) + 1

            # Update agent WIP
            self.registry.update_agent_status(
                decision.agent_id,
                current_wip=self.registry.get_agent(decision.agent_id).current_wip + 1
            )

            logger.info(f"🔀 Routed {requirements.task_id} to {decision.agent_name} "
                       f"(strategy: {strategy.value}, score: {decision.match_score:.3f})")

        return decision

    def _route_best_match(
        self,
        requirements: TaskRequirements,
        matches: List[MatchResult]
    ) -> RoutingDecision:
        """Route to highest scoring agent"""
        best = matches[0]

        return RoutingDecision(
            task_id=requirements.task_id,
            agent_id=best.agent_id,
            agent_name=best.agent_name,
            strategy_used=RoutingStrategy.BEST_MATCH.value,
            confidence=best.score,
            match_score=best.score,
            reasons=best.reasons + ["Selected as best overall match"],
            alternatives=[m.agent_id for m in matches[1:3]]
        )

    def _route_round_robin(
        self,
        requirements: TaskRequirements,
        matches: List[MatchResult]
    ) -> RoutingDecision:
        """Distribute tasks evenly"""
        task_type = requirements.task_type

        # Get current index
        idx = self._round_robin_index.get(task_type, 0)

        # Select agent
        selected_idx = idx % len(matches)
        selected = matches[selected_idx]

        # Update index
        self._round_robin_index[task_type] = idx + 1

        return RoutingDecision(
            task_id=requirements.task_id,
            agent_id=selected.agent_id,
            agent_name=selected.agent_name,
            strategy_used=RoutingStrategy.ROUND_ROBIN.value,
            confidence=0.8,  # Lower confidence for round-robin
            match_score=selected.score,
            reasons=selected.reasons + [f"Round-robin selection (index {selected_idx})"],
            alternatives=[m.agent_id for m in matches if m.agent_id != selected.agent_id][:2]
        )

    def _route_least_loaded(
        self,
        requirements: TaskRequirements,
        matches: List[MatchResult]
    ) -> RoutingDecision:
        """Route to agent with least workload"""
        # Sort by load factor
        agent_loads = []
        for match in matches:
            agent = self.registry.get_agent(match.agent_id)
            if agent:
                agent_loads.append((match, agent.load_factor))

        # Sort by load (ascending) then by match score (descending)
        agent_loads.sort(key=lambda x: (x[1], -x[0].score))

        if not agent_loads:
            return self._route_best_match(requirements, matches)

        selected_match, load = agent_loads[0]
        agent = self.registry.get_agent(selected_match.agent_id)

        return RoutingDecision(
            task_id=requirements.task_id,
            agent_id=selected_match.agent_id,
            agent_name=selected_match.agent_name,
            strategy_used=RoutingStrategy.LEAST_LOADED.value,
            confidence=selected_match.score * (1 - load),
            match_score=selected_match.score,
            reasons=selected_match.reasons + [
                f"Lowest workload ({agent.current_wip}/{agent.wip_limit} WIP)"
            ],
            alternatives=[m.agent_id for m, _ in agent_loads[1:3]]
        )

    def _route_specialized(
        self,
        requirements: TaskRequirements,
        matches: List[MatchResult]
    ) -> RoutingDecision:
        """Route to agent best specialized for task type"""
        # Get best agent for this task type from evaluator
        best_for_type = self.evaluator.get_best_agent_for_task_type(
            requirements.task_type
        )

        if best_for_type:
            # Find this agent in matches
            for match in matches:
                if match.agent_id == best_for_type:
                    return RoutingDecision(
                        task_id=requirements.task_id,
                        agent_id=match.agent_id,
                        agent_name=match.agent_name,
                        strategy_used=RoutingStrategy.SPECIALIZED.value,
                        confidence=0.9,
                        match_score=match.score,
                        reasons=match.reasons + [
                            f"Specialized for {requirements.task_type}"
                        ],
                        alternatives=[m.agent_id for m in matches if m.agent_id != match.agent_id][:2]
                    )

        # Fallback to best match
        return self._route_best_match(requirements, matches)

    def release_agent(self, agent_id: str):
        """
        Release an agent after task completion.

        Args:
            agent_id: Agent to release
        """
        agent = self.registry.get_agent(agent_id)
        if agent and agent.current_wip > 0:
            self.registry.update_agent_status(
                agent_id,
                current_wip=agent.current_wip - 1
            )
            logger.info(f"📤 Released {agent.name} "
                       f"(WIP: {agent.current_wip - 1}/{agent.wip_limit})")

    def get_available_agents(
        self,
        required_skills: List[str] = None
    ) -> List[AgentProfile]:
        """
        Get list of available agents.

        Args:
            required_skills: Optional skill filter

        Returns:
            List of available agents
        """
        agents = self.registry.list_agents(availability_status="available")

        # Filter by skills if specified
        if required_skills:
            agents = [
                a for a in agents
                if all(a.has_capability(skill) for skill in required_skills)
            ]

        # Filter by WIP limit
        agents = [a for a in agents if a.current_wip < a.wip_limit]

        return agents

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            'total_routed': sum(self._routing_stats.values()),
            'by_agent': self._routing_stats.copy(),
            'round_robin_state': self._round_robin_index.copy()
        }

    def reset_stats(self):
        """Reset routing statistics"""
        self._routing_stats = {}
        self._round_robin_index = {}

    def route_batch(
        self,
        tasks: List[TaskRequirements],
        strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED
    ) -> List[RoutingDecision]:
        """
        Route multiple tasks optimally.

        Args:
            tasks: List of task requirements
            strategy: Routing strategy

        Returns:
            List of routing decisions
        """
        decisions = []

        for task in tasks:
            # Get already assigned agents for this batch
            assigned = [d.agent_id for d in decisions]

            # Try to route with load balancing
            decision = self.route_task(
                task,
                strategy=strategy,
                exclude_agents=[]  # Don't exclude, but prefer less loaded
            )

            if decision:
                decisions.append(decision)

        return decisions

    def suggest_optimal_strategy(
        self,
        requirements: TaskRequirements
    ) -> RoutingStrategy:
        """
        Suggest optimal routing strategy for a task.

        Args:
            requirements: Task requirements

        Returns:
            Recommended strategy
        """
        # High priority tasks -> best match
        if requirements.priority in ["high", "critical"]:
            return RoutingStrategy.BEST_MATCH

        # Complex tasks -> specialized
        if requirements.complexity == "complex":
            return RoutingStrategy.SPECIALIZED

        # Simple tasks -> round robin for distribution
        if requirements.complexity == "simple":
            return RoutingStrategy.ROUND_ROBIN

        # Default -> least loaded for efficiency
        return RoutingStrategy.LEAST_LOADED


# Global instance
_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    """Get or create global routing engine instance."""
    global _engine
    if _engine is None:
        _engine = RoutingEngine()
    return _engine


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize
    registry = get_agent_registry()
    registry.initialize_default_agents()

    engine = get_routing_engine()

    # Create task requirements
    tasks = [
        TaskRequirements(
            task_id="task-001",
            task_type="backend_development",
            required_skills=["Backend:Python"],
            complexity="moderate",
            priority="normal"
        ),
        TaskRequirements(
            task_id="task-002",
            task_type="testing",
            required_skills=["Testing:Unit"],
            complexity="simple",
            priority="normal"
        ),
        TaskRequirements(
            task_id="task-003",
            task_type="deployment",
            required_skills=["DevOps:Docker"],
            complexity="moderate",
            priority="high"
        )
    ]

    print("\n=== Routing Tasks ===")

    for task in tasks:
        # Get suggested strategy
        strategy = engine.suggest_optimal_strategy(task)
        print(f"\nTask: {task.task_id} ({task.task_type})")
        print(f"  Strategy: {strategy.value}")

        # Route task
        decision = engine.route_task(task, strategy)

        if decision:
            print(f"  Routed to: {decision.agent_name}")
            print(f"  Score: {decision.match_score:.3f}")
            print(f"  Confidence: {decision.confidence:.3f}")
            print(f"  Reasons: {', '.join(decision.reasons[:2])}")

    # Show stats
    print("\n=== Routing Stats ===")
    stats = engine.get_routing_stats()
    print(f"Total routed: {stats['total_routed']}")
    for agent_id, count in stats['by_agent'].items():
        print(f"  {agent_id}: {count} tasks")

    # Release agents
    print("\n=== Releasing Agents ===")
    for agent_id in stats['by_agent'].keys():
        engine.release_agent(agent_id)
