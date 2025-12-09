"""Agent Executor - Execute agent tasks (AC-2544-1, AC-2544-3)."""
import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import AgentState, AgentSession, AgentContext

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTask:
    """Task to be executed by an agent."""
    id: UUID
    session_id: UUID
    input_data: Dict[str, Any]
    callback: Optional[Callable] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ExecutionResult:
    """Result from agent execution."""
    task_id: UUID
    success: bool
    output: Any = None
    error: Optional[str] = None
    tokens_used: int = 0
    execution_time_ms: float = 0.0


class AgentExecutor:
    """Executes agent tasks with concurrency support (AC-2544-3)."""
    
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_queue: Dict[UUID, List[ExecutionTask]] = {}
        self._lock = threading.RLock()
        self._handlers: Dict[str, Callable] = {}
        logger.info("AgentExecutor initialized with %d workers", max_workers)
    
    def register_handler(self, name: str, handler: Callable):
        """Register execution handler."""
        self._handlers[name] = handler
    
    def submit_task(self, session: AgentSession, input_data: Dict[str, Any], callback: Optional[Callable] = None) -> ExecutionTask:
        """Submit task for execution."""
        from uuid import uuid4
        task = ExecutionTask(
            id=uuid4(),
            session_id=session.id,
            input_data=input_data,
            callback=callback,
        )
        
        with self._lock:
            if session.id not in self._task_queue:
                self._task_queue[session.id] = []
            self._task_queue[session.id].append(task)
        
        # Submit to executor
        self._executor.submit(self._execute_task, session, task)
        logger.debug("Submitted task %s for session %s", task.id, session.id)
        return task
    
    def _execute_task(self, session: AgentSession, task: ExecutionTask) -> ExecutionResult:
        """Execute a task."""
        start_time = time.time()
        
        try:
            if session.state != AgentState.RUNNING:
                raise RuntimeError(f"Session not running: {session.state.value}")
            
            # Simulate execution (in real impl, would call LLM/tools)
            output = self._process_input(session, task.input_data)
            tokens = len(str(output)) // 4  # Rough token estimate
            
            result = ExecutionResult(
                task_id=task.id,
                success=True,
                output=output,
                tokens_used=tokens,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
            
            # Update metrics
            session.metrics.record_request(True, tokens, result.execution_time_ms)
            
            # Add to context
            session.context.add_message("user", str(task.input_data.get("message", "")))
            session.context.add_message("assistant", str(output))
            
        except Exception as e:
            result = ExecutionResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
            session.metrics.record_request(False, 0, result.execution_time_ms)
            logger.error("Task %s failed: %s", task.id, e)
        
        # Run callback
        if task.callback:
            try:
                task.callback(result)
            except Exception as e:
                logger.error("Task callback failed: %s", e)
        
        return result
    
    def _process_input(self, session: AgentSession, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and generate output."""
        message = input_data.get("message", "")
        handler_name = input_data.get("handler", "default")
        
        if handler_name in self._handlers:
            return self._handlers[handler_name](session, input_data)
        
        # Default echo response
        return {
            "response": f"Processed: {message}",
            "session_id": str(session.id),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_pending_tasks(self, session_id: UUID) -> List[ExecutionTask]:
        """Get pending tasks for a session."""
        with self._lock:
            return list(self._task_queue.get(session_id, []))
    
    def shutdown(self):
        """Shutdown executor."""
        self._executor.shutdown(wait=True)
        logger.info("AgentExecutor shutdown")
