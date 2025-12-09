"""Agent Runtime Engine - Main entry point for agent execution (AC-2544-1)."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import AgentState, AgentSession, AgentContext, ExecutionMetrics
from .lifecycle import AgentLifecycle
from .executor import AgentExecutor, ExecutionResult
from .context_manager import ContextManager

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Main runtime engine for executing AI agents (AC-2544-1)."""
    
    def __init__(self, storage_path: Optional[Path] = None, max_workers: int = 4):
        self.lifecycle = AgentLifecycle()
        self.executor = AgentExecutor(max_workers=max_workers)
        self.context_manager = ContextManager(storage_path)
        self._agents: Dict[UUID, Dict[str, Any]] = {}
        logger.info("AgentRuntime initialized")
    
    def register_agent(self, agent_id: UUID, persona_id: Optional[UUID] = None, knowledge_ids: Optional[List[UUID]] = None) -> bool:
        """Register an agent with the runtime."""
        self._agents[agent_id] = {
            "persona_id": persona_id,
            "knowledge_ids": knowledge_ids or [],
            "registered_at": datetime.utcnow(),
        }
        logger.info("Registered agent %s", agent_id)
        return True
    
    def create_session(self, agent_id: UUID, resume_context_id: Optional[UUID] = None) -> AgentSession:
        """Create execution session for an agent (AC-2544-1)."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
        
        session = self.lifecycle.create_session(agent_id)
        agent_info = self._agents[agent_id]
        
        # Load or create context
        if resume_context_id:
            context = self.context_manager.load_context(resume_context_id)
            if context:
                session.context = context
                logger.info("Resumed context %s for session %s", resume_context_id, session.id)
        
        # Set persona and knowledge
        session.context.persona_id = agent_info["persona_id"]
        session.context.loaded_knowledge = agent_info["knowledge_ids"]
        
        return session
    
    def start_session(self, session_id: UUID) -> bool:
        """Start agent session (AC-2544-2)."""
        return self.lifecycle.start(session_id)
    
    def pause_session(self, session_id: UUID) -> bool:
        """Pause agent session (AC-2544-2)."""
        session = self.lifecycle.get_session(session_id)
        if session:
            self.context_manager.save_context(session.context)
        return self.lifecycle.pause(session_id)
    
    def resume_session(self, session_id: UUID) -> bool:
        """Resume agent session (AC-2544-2)."""
        return self.lifecycle.resume(session_id)
    
    def stop_session(self, session_id: UUID) -> bool:
        """Stop agent session (AC-2544-2)."""
        session = self.lifecycle.get_session(session_id)
        if session:
            self.context_manager.save_context(session.context)
        return self.lifecycle.stop(session_id)
    
    def execute(self, session_id: UUID, message: str, callback: Optional[Callable] = None) -> Optional[UUID]:
        """Execute a message in agent session (AC-2544-1)."""
        session = self.lifecycle.get_session(session_id)
        if not session or session.state != AgentState.RUNNING:
            return None
        
        task = self.executor.submit_task(session, {"message": message}, callback)
        return task.id
    
    def get_metrics(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get execution metrics (AC-2544-4)."""
        session = self.lifecycle.get_session(session_id)
        return session.metrics.to_dict() if session else None
    
    def get_session_state(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get session state."""
        session = self.lifecycle.get_session(session_id)
        return session.to_dict() if session else None
    
    def save_session_context(self, session_id: UUID) -> bool:
        """Save session context for persistence (AC-2544-5)."""
        session = self.lifecycle.get_session(session_id)
        if session:
            return self.context_manager.save_context(session.context)
        return False
    
    def shutdown(self):
        """Shutdown runtime."""
        self.executor.shutdown()
        logger.info("AgentRuntime shutdown")
