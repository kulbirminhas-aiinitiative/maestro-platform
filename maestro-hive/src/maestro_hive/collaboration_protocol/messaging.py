"""Message Bus - Inter-agent messaging system."""
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional
from uuid import UUID
from .models import CollaborationMessage, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    """Message bus for agent communication."""
    
    def __init__(self):
        self._subscribers: Dict[UUID, List[Callable]] = defaultdict(list)
        self._broadcast_subscribers: List[Callable] = []
        self._message_history: List[CollaborationMessage] = []
        self._max_history = 1000
    
    def subscribe(self, agent_id: UUID, callback: Callable):
        """Subscribe to messages for an agent."""
        self._subscribers[agent_id].append(callback)
        logger.debug("Agent %s subscribed to messages", agent_id)
    
    def subscribe_broadcast(self, callback: Callable):
        """Subscribe to broadcast messages."""
        self._broadcast_subscribers.append(callback)
    
    def publish(self, message: CollaborationMessage) -> bool:
        """Publish a message."""
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]
        
        if message.message_type == MessageType.BROADCAST:
            for callback in self._broadcast_subscribers:
                try:
                    callback(message)
                except Exception as e:
                    logger.error("Broadcast callback failed: %s", e)
        elif message.recipient_id:
            for callback in self._subscribers.get(message.recipient_id, []):
                try:
                    callback(message)
                except Exception as e:
                    logger.error("Message callback failed: %s", e)
        
        logger.debug("Published message %s from %s", message.id, message.sender_id)
        return True
    
    def request_response(self, message: CollaborationMessage, timeout_ms: int = 5000) -> Optional[CollaborationMessage]:
        """Send request and wait for response (simplified sync version)."""
        message.message_type = MessageType.REQUEST
        self.publish(message)
        
        # In real impl, would wait for correlated response
        # Here we just simulate
        response = CollaborationMessage(
            sender_id=message.recipient_id or UUID(int=0),
            recipient_id=message.sender_id,
            message_type=MessageType.RESPONSE,
            content={"ack": True},
            correlation_id=message.id
        )
        return response
    
    def get_history(self, agent_id: Optional[UUID] = None, limit: int = 100) -> List[CollaborationMessage]:
        """Get message history."""
        messages = self._message_history
        if agent_id:
            messages = [m for m in messages if m.sender_id == agent_id or m.recipient_id == agent_id]
        return messages[-limit:]
