"""Behavior Reinforcer - Reinforce successful behaviors."""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from .models import LearningPattern, PatternType
from .analyzer import PatternAnalyzer

logger = logging.getLogger(__name__)


class BehaviorReinforcer:
    """Reinforces successful behaviors based on patterns."""
    
    def __init__(self, analyzer: PatternAnalyzer):
        self.analyzer = analyzer
        self._reinforcements: Dict[str, float] = {}  # action -> reinforcement score
        self._history: List[Dict] = []
    
    def reinforce(self, action: str, reward: float) -> None:
        """Apply reinforcement to an action."""
        current = self._reinforcements.get(action, 0.0)
        # Simple moving average reinforcement
        alpha = 0.1
        self._reinforcements[action] = current + alpha * (reward - current)
        
        self._history.append({
            "action": action,
            "reward": reward,
            "new_score": self._reinforcements[action]
        })
        
        logger.debug("Reinforced %s: %.3f -> %.3f", action, current, self._reinforcements[action])
    
    def get_reinforcement(self, action: str) -> float:
        """Get current reinforcement score for an action."""
        return self._reinforcements.get(action, 0.0)
    
    def suggest_action(self, possible_actions: List[str]) -> Optional[str]:
        """Suggest best action based on reinforcement scores."""
        if not possible_actions:
            return None
        
        scored = [(a, self.get_reinforcement(a)) for a in possible_actions]
        # Also consider patterns
        for action in possible_actions:
            pattern = self.analyzer.get_pattern(action)
            if pattern and pattern.pattern_type == PatternType.SUCCESS:
                for i, (a, s) in enumerate(scored):
                    if a == action:
                        scored[i] = (a, s + pattern.confidence * 0.5)
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None
    
    def get_stats(self) -> Dict:
        return {
            "reinforced_actions": len(self._reinforcements),
            "history_length": len(self._history),
            "top_actions": sorted(self._reinforcements.items(), key=lambda x: x[1], reverse=True)[:5]
        }
