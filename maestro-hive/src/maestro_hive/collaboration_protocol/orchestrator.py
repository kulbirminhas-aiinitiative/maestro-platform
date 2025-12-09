"""Task Orchestrator - Orchestrate complex multi-agent workflows."""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from .models import TaskAssignment, TaskStatus, CollaborationSession
from .coordinator import CollaborationCoordinator

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """Orchestrates complex workflows across agents."""
    
    def __init__(self, coordinator: CollaborationCoordinator):
        self.coordinator = coordinator
        self._workflows: Dict[UUID, List[Dict]] = {}
    
    def create_workflow(self, session_id: UUID, tasks: List[Dict]) -> UUID:
        """Create a workflow from task definitions."""
        from uuid import uuid4
        workflow_id = uuid4()
        self._workflows[workflow_id] = tasks
        logger.info("Created workflow %s with %d tasks", workflow_id, len(tasks))
        return workflow_id
    
    def execute_workflow(self, session_id: UUID, workflow_id: UUID) -> List[TaskAssignment]:
        """Execute a workflow, respecting dependencies."""
        tasks = self._workflows.get(workflow_id, [])
        assignments = []
        
        for task_def in tasks:
            agent_id = task_def.get("agent_id")
            if agent_id:
                assignment = self.coordinator.assign_task(session_id, UUID(agent_id), task_def)
                if assignment:
                    assignments.append(assignment)
        
        return assignments
    
    def get_ready_tasks(self, session: CollaborationSession) -> List[TaskAssignment]:
        """Get tasks that are ready to execute (dependencies met)."""
        completed_ids = {t.id for t in session.tasks if t.status == TaskStatus.COMPLETED}
        ready = []
        
        for task in session.tasks:
            if task.status == TaskStatus.ASSIGNED:
                if all(dep in completed_ids for dep in task.dependencies):
                    ready.append(task)
        
        return ready
    
    def handoff_task(self, session_id: UUID, task_id: UUID, from_agent: UUID, to_agent: UUID, context: Dict) -> bool:
        """Hand off task from one agent to another."""
        session = self.coordinator._sessions.get(session_id)
        if not session:
            return False
        
        for task in session.tasks:
            if task.id == task_id and task.agent_id == from_agent:
                task.agent_id = to_agent
                task.input_data.update(context)
                logger.info("Handed off task %s from %s to %s", task_id, from_agent, to_agent)
                return True
        return False
    
    def get_workflow_status(self, workflow_id: UUID) -> Dict:
        """Get workflow execution status."""
        tasks = self._workflows.get(workflow_id, [])
        return {
            "workflow_id": str(workflow_id),
            "total_tasks": len(tasks),
            "status": "active" if tasks else "unknown"
        }
