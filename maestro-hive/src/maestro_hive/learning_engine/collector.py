"""Experience Collector - Collect and store learning experiences."""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from .models import LearningEvent, FeedbackSignal, FeedbackType

logger = logging.getLogger(__name__)


class ExperienceCollector:
    """Collects experiences for learning."""
    
    def __init__(self, max_events: int = 10000):
        self._events: List[LearningEvent] = []
        self._by_agent: Dict[UUID, List[UUID]] = {}
        self._by_action: Dict[str, List[UUID]] = {}
        self.max_events = max_events
    
    def record(self, agent_id: UUID, action: str, input_data: Dict, output_data: Dict,
               context: Optional[Dict] = None) -> LearningEvent:
        """Record a learning event."""
        event = LearningEvent(
            agent_id=agent_id,
            action=action,
            input_data=input_data,
            output_data=output_data,
            context=context or {}
        )
        
        self._events.append(event)
        
        if agent_id not in self._by_agent:
            self._by_agent[agent_id] = []
        self._by_agent[agent_id].append(event.id)
        
        if action not in self._by_action:
            self._by_action[action] = []
        self._by_action[action].append(event.id)
        
        # Trim if exceeds max
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        
        logger.debug("Recorded event %s for agent %s", event.id, agent_id)
        return event
    
    def add_feedback(self, event_id: UUID, feedback_type: FeedbackType, score: float,
                     source: str = "user", context: Optional[Dict] = None) -> bool:
        """Add feedback to an event."""
        for event in self._events:
            if event.id == event_id:
                event.feedback = FeedbackSignal(
                    feedback_type=feedback_type,
                    source=source,
                    score=score,
                    context=context or {}
                )
                logger.debug("Added feedback to event %s", event_id)
                return True
        return False
    
    def get_events(self, agent_id: Optional[UUID] = None, action: Optional[str] = None,
                   limit: int = 100) -> List[LearningEvent]:
        """Get events with optional filters."""
        events = self._events
        
        if agent_id:
            event_ids = set(self._by_agent.get(agent_id, []))
            events = [e for e in events if e.id in event_ids]
        
        if action:
            event_ids = set(self._by_action.get(action, []))
            events = [e for e in events if e.id in event_ids]
        
        return events[-limit:]
    
    def get_feedback_events(self, feedback_type: Optional[FeedbackType] = None) -> List[LearningEvent]:
        """Get events with feedback."""
        events = [e for e in self._events if e.feedback is not None]
        if feedback_type:
            events = [e for e in events if e.feedback.feedback_type == feedback_type]
        return events
    
    def get_stats(self) -> Dict:
        return {"total_events": len(self._events), "unique_agents": len(self._by_agent),
                "unique_actions": len(self._by_action),
                "events_with_feedback": len([e for e in self._events if e.feedback])}
