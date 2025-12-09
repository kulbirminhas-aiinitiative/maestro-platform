"""Pattern Analyzer - Analyze experiences to discover patterns."""
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from uuid import UUID
from .models import LearningEvent, LearningPattern, PatternType, FeedbackType
from .collector import ExperienceCollector

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Analyzes experiences to discover learning patterns."""
    
    def __init__(self, collector: ExperienceCollector, min_occurrences: int = 3):
        self.collector = collector
        self.min_occurrences = min_occurrences
        self._patterns: Dict[str, LearningPattern] = {}
    
    def analyze(self, agent_id: Optional[UUID] = None) -> List[LearningPattern]:
        """Analyze events to discover patterns."""
        events = self.collector.get_events(agent_id=agent_id, limit=1000)
        
        # Group by action
        action_events = defaultdict(list)
        for event in events:
            action_events[event.action].append(event)
        
        patterns = []
        for action, action_events_list in action_events.items():
            if len(action_events_list) < self.min_occurrences:
                continue
            
            # Calculate success rate from feedback
            with_feedback = [e for e in action_events_list if e.feedback]
            if with_feedback:
                success_count = sum(1 for e in with_feedback 
                                   if e.feedback.feedback_type == FeedbackType.POSITIVE)
                success_rate = success_count / len(with_feedback)
                
                pattern_type = PatternType.SUCCESS if success_rate > 0.7 else PatternType.FAILURE
                
                pattern = LearningPattern(
                    pattern_type=pattern_type,
                    trigger=action,
                    action=action,
                    confidence=min(0.95, 0.5 + len(with_feedback) * 0.05),
                    occurrence_count=len(action_events_list),
                    success_rate=success_rate,
                    examples=[e.id for e in action_events_list[:5]]
                )
                
                pattern_key = f"{action}:{pattern_type.value}"
                self._patterns[pattern_key] = pattern
                patterns.append(pattern)
        
        logger.info("Discovered %d patterns", len(patterns))
        return patterns
    
    def get_pattern(self, trigger: str) -> Optional[LearningPattern]:
        """Get pattern for a trigger."""
        for key, pattern in self._patterns.items():
            if pattern.trigger == trigger:
                return pattern
        return None
    
    def get_recommendations(self, context: Dict) -> List[LearningPattern]:
        """Get recommended patterns based on context."""
        action = context.get("action", "")
        return [p for p in self._patterns.values() 
                if p.trigger == action and p.confidence > 0.6]
    
    def get_all_patterns(self) -> List[LearningPattern]:
        return list(self._patterns.values())
