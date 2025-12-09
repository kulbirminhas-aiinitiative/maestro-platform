"""Collaboration Coordinator - Coordinate multi-agent activities."""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from .models import CollaborationSession, CollaborationMessage, TaskAssignment, TaskStatus, MessageType
from .messaging import MessageBus

logger = logging.getLogger(__name__)


class CollaborationCoordinator:
    """Coordinates collaboration between agents."""
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self._sessions: Dict[UUID, CollaborationSession] = {}
    
    def create_session(self, coordinator_id: UUID) -> CollaborationSession:
        """Create new collaboration session."""
        session = CollaborationSession(coordinator_id=coordinator_id)
        session.add_participant(coordinator_id)
        self._sessions[session.id] = session
        logger.info("Created collaboration session %s", session.id)
        return session
    
    def join_session(self, session_id: UUID, agent_id: UUID) -> bool:
        """Add agent to session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.add_participant(agent_id)
        
        # Broadcast join
        self.message_bus.publish(CollaborationMessage(
            sender_id=agent_id,
            message_type=MessageType.BROADCAST,
            content={"event": "agent_joined", "session_id": str(session_id)}
        ))
        return True
    
    def assign_task(self, session_id: UUID, agent_id: UUID, task_data: Dict) -> Optional[TaskAssignment]:
        """Assign task to agent in session."""
        session = self._sessions.get(session_id)
        if not session or agent_id not in session.participants:
            return None
        
        task = TaskAssignment(
            agent_id=agent_id,
            status=TaskStatus.ASSIGNED,
            priority=task_data.get("priority", 5),
            input_data=task_data.get("input", {}),
            dependencies=[UUID(d) for d in task_data.get("dependencies", [])]
        )
        session.add_task(task)
        
        # Notify agent
        self.message_bus.publish(CollaborationMessage(
            sender_id=session.coordinator_id or UUID(int=0),
            recipient_id=agent_id,
            message_type=MessageType.REQUEST,
            content={"task_id": str(task.id), "input": task.input_data}
        ))
        
        return task
    
    def complete_task(self, session_id: UUID, task_id: UUID, output: Dict) -> bool:
        """Mark task as completed."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        for task in session.tasks:
            if task.id == task_id:
                task.complete(output)
                logger.info("Task %s completed", task_id)
                return True
        return False
    
    def get_session_status(self, session_id: UUID) -> Optional[Dict]:
        """Get session status."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        completed = sum(1 for t in session.tasks if t.status == TaskStatus.COMPLETED)
        return {
            "session_id": str(session_id),
            "participants": len(session.participants),
            "total_tasks": len(session.tasks),
            "completed_tasks": completed,
            "pending_tasks": len(session.tasks) - completed
        }
    
    def end_session(self, session_id: UUID) -> bool:
        """End collaboration session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Ended session %s", session_id)
            return True
        return False
