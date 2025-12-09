"""Agent Lifecycle Manager - Manage agent lifecycle states (AC-2544-2)."""
import logging
from datetime import datetime
from typing import Callable, Dict, Optional
from uuid import UUID

from .models import AgentState, AgentSession, ExecutionMetrics

logger = logging.getLogger(__name__)


class AgentLifecycle:
    """Manages agent lifecycle transitions (AC-2544-2)."""
    
    VALID_TRANSITIONS = {
        AgentState.CREATED: {AgentState.INITIALIZING},
        AgentState.INITIALIZING: {AgentState.RUNNING, AgentState.ERROR},
        AgentState.RUNNING: {AgentState.PAUSED, AgentState.STOPPING, AgentState.ERROR},
        AgentState.PAUSED: {AgentState.RUNNING, AgentState.STOPPING},
        AgentState.STOPPING: {AgentState.STOPPED},
        AgentState.STOPPED: {AgentState.CREATED},
        AgentState.ERROR: {AgentState.CREATED, AgentState.STOPPED},
    }
    
    def __init__(self):
        self._sessions: Dict[UUID, AgentSession] = {}
        self._hooks: Dict[str, list] = {"on_start": [], "on_stop": [], "on_pause": [], "on_resume": [], "on_error": []}
    
    def create_session(self, agent_id: UUID) -> AgentSession:
        """Create new agent session."""
        session = AgentSession(agent_id=agent_id)
        session.metrics.start_time = datetime.utcnow()
        self._sessions[session.id] = session
        logger.info("Created session %s for agent %s", session.id, agent_id)
        return session
    
    def start(self, session_id: UUID) -> bool:
        """Start agent (CREATED -> INITIALIZING -> RUNNING)."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if not self._can_transition(session.state, AgentState.INITIALIZING):
            return False
        
        session.state = AgentState.INITIALIZING
        self._run_hooks("on_start", session)
        session.state = AgentState.RUNNING
        logger.info("Started session %s", session_id)
        return True
    
    def pause(self, session_id: UUID) -> bool:
        """Pause agent (RUNNING -> PAUSED)."""
        session = self._sessions.get(session_id)
        if not session or not self._can_transition(session.state, AgentState.PAUSED):
            return False
        
        session.state = AgentState.PAUSED
        self._run_hooks("on_pause", session)
        logger.info("Paused session %s", session_id)
        return True
    
    def resume(self, session_id: UUID) -> bool:
        """Resume agent (PAUSED -> RUNNING)."""
        session = self._sessions.get(session_id)
        if not session or not self._can_transition(session.state, AgentState.RUNNING):
            return False
        
        session.state = AgentState.RUNNING
        self._run_hooks("on_resume", session)
        logger.info("Resumed session %s", session_id)
        return True
    
    def stop(self, session_id: UUID) -> bool:
        """Stop agent (RUNNING/PAUSED -> STOPPING -> STOPPED)."""
        session = self._sessions.get(session_id)
        if not session or not self._can_transition(session.state, AgentState.STOPPING):
            return False
        
        session.state = AgentState.STOPPING
        self._run_hooks("on_stop", session)
        session.state = AgentState.STOPPED
        logger.info("Stopped session %s", session_id)
        return True
    
    def error(self, session_id: UUID, error_msg: str) -> None:
        """Set agent to error state."""
        session = self._sessions.get(session_id)
        if session:
            session.state = AgentState.ERROR
            session.context.metadata["last_error"] = error_msg
            self._run_hooks("on_error", session)
            logger.error("Session %s error: %s", session_id, error_msg)
    
    def get_session(self, session_id: UUID) -> Optional[AgentSession]:
        return self._sessions.get(session_id)
    
    def get_state(self, session_id: UUID) -> Optional[AgentState]:
        session = self._sessions.get(session_id)
        return session.state if session else None
    
    def _can_transition(self, current: AgentState, target: AgentState) -> bool:
        return target in self.VALID_TRANSITIONS.get(current, set())
    
    def _run_hooks(self, hook_name: str, session: AgentSession):
        for hook in self._hooks.get(hook_name, []):
            try:
                hook(session)
            except Exception as e:
                logger.error("Hook %s failed: %s", hook_name, e)
    
    def register_hook(self, hook_name: str, callback: Callable):
        if hook_name in self._hooks:
            self._hooks[hook_name].append(callback)
