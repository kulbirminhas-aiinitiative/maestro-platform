"""
Task Management Service (MD-2117, MD-2120)

Provides task lifecycle management including:
- Auto-transition tasks to Done when nodes complete
- Close EPIC when all tasks complete
- Add completion comments with summary
- Create epics from workflow definitions (MD-2117)
- Create tasks from manifest (MD-2117)
- Sync task status from external systems (MD-2117)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .integration.interfaces import TaskStatus, TaskType, AdapterResult
from .integration.adapters.jira_adapter import JiraAdapter

logger = logging.getLogger(__name__)


class ClosureReason(Enum):
    """Reason for task closure"""
    COMPLETED = "completed"
    ALL_CHILDREN_DONE = "all_children_done"
    MANUAL = "manual"
    WORKFLOW_COMPLETE = "workflow_complete"


@dataclass
class ClosureResult:
    """Result of a closure operation"""
    task_id: str
    success: bool
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    reason: Optional[ClosureReason] = None
    comment_added: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'task_id': self.task_id,
            'success': self.success,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'reason': self.reason.value if self.reason else None,
            'comment_added': self.comment_added,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class EpicClosureResult:
    """Result of an epic closure operation"""
    epic_id: str
    success: bool
    total_children: int = 0
    children_done: int = 0
    children_pending: int = 0
    pending_task_ids: List[str] = field(default_factory=list)
    closed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'epic_id': self.epic_id,
            'success': self.success,
            'total_children': self.total_children,
            'children_done': self.children_done,
            'children_pending': self.children_pending,
            'pending_task_ids': self.pending_task_ids,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'error': self.error
        }


class TaskManagementService:
    """
    Service for managing task lifecycle and closure workflows.

    Features:
    - Auto-transition tasks to Done
    - Check and close epics when all children are done
    - Add completion comments with summary
    """

    def __init__(
        self,
        jira_adapter: Optional[JiraAdapter] = None,
        base_url: str = "http://localhost:14100",
        token: Optional[str] = None
    ):
        """
        Initialize the task management service.

        Args:
            jira_adapter: Optional pre-configured JiraAdapter
            base_url: Base URL for JIRA API (if adapter not provided)
            token: JWT token for authentication (if adapter not provided)
        """
        if jira_adapter:
            self._adapter = jira_adapter
        else:
            self._adapter = JiraAdapter(base_url=base_url, token=token)

        logger.info("TaskManagementService initialized")

    async def complete_task(
        self,
        task_id: str,
        summary: Optional[str] = None,
        reason: ClosureReason = ClosureReason.COMPLETED,
        add_comment: bool = True
    ) -> ClosureResult:
        """
        Transition a task to Done with optional completion comment.

        Args:
            task_id: Task ID to complete
            summary: Optional summary to include in comment
            reason: Reason for closure
            add_comment: Whether to add a completion comment

        Returns:
            ClosureResult with operation details
        """
        try:
            # Get current task state
            get_result = await self._adapter.get_task(task_id)
            if not get_result.success:
                return ClosureResult(
                    task_id=task_id,
                    success=False,
                    error=f"Failed to get task: {get_result.error}"
                )

            task = get_result.data
            previous_status = task.status.value if task.status else "unknown"

            # Skip if already done
            if task.status == TaskStatus.DONE:
                return ClosureResult(
                    task_id=task_id,
                    success=True,
                    previous_status=previous_status,
                    new_status="done",
                    reason=reason
                )

            # Transition to Done
            transition_result = await self._adapter.transition_task(
                task_id=task_id,
                target_status=TaskStatus.DONE
            )

            if not transition_result.success:
                return ClosureResult(
                    task_id=task_id,
                    success=False,
                    previous_status=previous_status,
                    error=f"Failed to transition: {transition_result.error}"
                )

            comment_added = False
            if add_comment:
                comment_text = self._build_completion_comment(
                    task_id=task_id,
                    reason=reason,
                    summary=summary
                )
                comment_result = await self._adapter.add_comment(task_id, comment_text)
                comment_added = comment_result.success

            logger.info(f"Task {task_id} completed: {previous_status} -> Done")

            return ClosureResult(
                task_id=task_id,
                success=True,
                previous_status=previous_status,
                new_status="done",
                reason=reason,
                comment_added=comment_added
            )

        except Exception as e:
            logger.exception(f"Error completing task {task_id}: {e}")
            return ClosureResult(
                task_id=task_id,
                success=False,
                error=str(e)
            )

    async def check_and_close_epic(
        self,
        epic_id: str,
        force: bool = False
    ) -> EpicClosureResult:
        """
        Check if all children of an epic are done and close it if so.

        Args:
            epic_id: Epic ID to check
            force: If True, close epic even if children are not all done

        Returns:
            EpicClosureResult with status details
        """
        try:
            # Get epic details
            epic_result = await self._adapter.get_task(epic_id)
            if not epic_result.success:
                return EpicClosureResult(
                    epic_id=epic_id,
                    success=False,
                    error=f"Failed to get epic: {epic_result.error}"
                )

            epic = epic_result.data

            # Get all children
            children_result = await self._adapter.get_epic_children(epic_id)
            if not children_result.success:
                return EpicClosureResult(
                    epic_id=epic_id,
                    success=False,
                    error=f"Failed to get children: {children_result.error}"
                )

            children = children_result.data or []
            total = len(children)
            done = [c for c in children if c.status == TaskStatus.DONE]
            pending = [c for c in children if c.status != TaskStatus.DONE]

            result = EpicClosureResult(
                epic_id=epic_id,
                success=False,
                total_children=total,
                children_done=len(done),
                children_pending=len(pending),
                pending_task_ids=[c.external_id for c in pending]
            )

            # Check if we can close
            if len(pending) > 0 and not force:
                result.error = f"Epic has {len(pending)} pending tasks"
                return result

            # Epic already done
            if epic.status == TaskStatus.DONE:
                result.success = True
                result.closed_at = datetime.utcnow()
                return result

            # Close the epic
            close_result = await self.complete_task(
                task_id=epic_id,
                summary=f"All {total} child tasks completed",
                reason=ClosureReason.ALL_CHILDREN_DONE
            )

            if close_result.success:
                result.success = True
                result.closed_at = datetime.utcnow()
            else:
                result.error = close_result.error

            return result

        except Exception as e:
            logger.exception(f"Error checking epic {epic_id}: {e}")
            return EpicClosureResult(
                epic_id=epic_id,
                success=False,
                error=str(e)
            )

    async def complete_workflow(
        self,
        epic_id: str,
        task_ids: List[str],
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete all tasks in a workflow and close the epic.

        Args:
            epic_id: Epic ID for the workflow
            task_ids: List of task IDs to complete
            summary: Optional workflow summary

        Returns:
            Dict with completion results
        """
        results = {
            'epic_id': epic_id,
            'tasks': [],
            'epic_result': None,
            'success': True
        }

        # Complete all tasks
        for task_id in task_ids:
            task_result = await self.complete_task(
                task_id=task_id,
                summary=summary,
                reason=ClosureReason.WORKFLOW_COMPLETE
            )
            results['tasks'].append(task_result.to_dict())
            if not task_result.success:
                results['success'] = False

        # Close the epic
        epic_result = await self.check_and_close_epic(epic_id)
        results['epic_result'] = epic_result.to_dict()
        if not epic_result.success:
            results['success'] = False

        return results

    async def get_epic_completion_status(
        self,
        epic_id: str
    ) -> Dict[str, Any]:
        """
        Get completion status of an epic and its children.

        Args:
            epic_id: Epic ID to check

        Returns:
            Dict with status information
        """
        try:
            # Get epic
            epic_result = await self._adapter.get_task(epic_id)
            if not epic_result.success:
                return {
                    'epic_id': epic_id,
                    'error': epic_result.error
                }

            epic = epic_result.data

            # Get children
            children_result = await self._adapter.get_epic_children(epic_id)
            children = children_result.data or [] if children_result.success else []

            # Calculate stats
            done = [c for c in children if c.status == TaskStatus.DONE]
            in_progress = [c for c in children if c.status == TaskStatus.IN_PROGRESS]
            todo = [c for c in children if c.status == TaskStatus.TODO]
            blocked = [c for c in children if c.status == TaskStatus.BLOCKED]

            completion_pct = (len(done) / len(children) * 100) if children else 100

            return {
                'epic_id': epic_id,
                'epic_status': epic.status.value if epic.status else 'unknown',
                'epic_title': epic.title,
                'total_children': len(children),
                'done': len(done),
                'in_progress': len(in_progress),
                'todo': len(todo),
                'blocked': len(blocked),
                'completion_percentage': round(completion_pct, 1),
                'ready_to_close': len(todo) == 0 and len(in_progress) == 0 and len(blocked) == 0,
                'children': [
                    {
                        'id': c.external_id,
                        'title': c.title,
                        'status': c.status.value if c.status else 'unknown'
                    }
                    for c in children
                ]
            }

        except Exception as e:
            logger.exception(f"Error getting epic status: {e}")
            return {
                'epic_id': epic_id,
                'error': str(e)
            }

    async def create_epic_from_workflow(
        self,
        workflow_name: str,
        workflow_description: str,
        project_id: str = "MD",
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        Create an epic from a DDE workflow definition.

        Args:
            workflow_name: Name/title for the epic
            workflow_description: Description of the workflow
            project_id: JIRA project ID (default: MD)
            labels: Optional labels to apply
            custom_fields: Optional custom field values

        Returns:
            AdapterResult with created epic data
        """
        try:
            title = f"[EPIC] {workflow_name}"
            description = f"{workflow_description}\n\n---\nCreated by TaskManagementService from workflow"

            result = await self._adapter.create_epic(
                title=title,
                description=description,
                project_id=project_id,
                labels=labels or []
            )

            if result.success:
                logger.info(f"Created epic from workflow: {result.data.external_id}")
            else:
                logger.error(f"Failed to create epic: {result.error}")

            return result

        except Exception as e:
            logger.exception(f"Error creating epic from workflow: {e}")
            return AdapterResult(success=False, error=str(e))

    async def create_tasks_from_manifest(
        self,
        manifest: List[Dict[str, Any]],
        epic_id: str,
        project_id: str = "MD"
    ) -> Dict[str, Any]:
        """
        Create tasks from a manifest definition.

        Args:
            manifest: List of task definitions with keys:
                - title: Task title (required)
                - description: Task description
                - type: Task type (task/story/subtask)
                - priority: Priority level
                - labels: List of labels
            epic_id: Parent epic ID
            project_id: JIRA project ID

        Returns:
            Dict with created tasks and any errors
        """
        results = {
            'epic_id': epic_id,
            'created': [],
            'failed': [],
            'total': len(manifest),
            'success_count': 0,
            'error_count': 0
        }

        for idx, task_def in enumerate(manifest):
            try:
                title = task_def.get('title', f'Task {idx + 1}')
                description = task_def.get('description', '')
                task_type_str = task_def.get('type', 'task').lower()
                priority_str = task_def.get('priority', 'medium').lower()
                labels = task_def.get('labels', [])

                # Map string to enum
                from .integration.interfaces import TaskType, TaskPriority
                type_map = {
                    'epic': TaskType.EPIC,
                    'story': TaskType.STORY,
                    'task': TaskType.TASK,
                    'subtask': TaskType.SUBTASK,
                    'bug': TaskType.BUG
                }
                priority_map = {
                    'highest': TaskPriority.HIGHEST,
                    'high': TaskPriority.HIGH,
                    'medium': TaskPriority.MEDIUM,
                    'low': TaskPriority.LOW,
                    'lowest': TaskPriority.LOWEST
                }

                task_type = type_map.get(task_type_str, TaskType.TASK)
                priority = priority_map.get(priority_str, TaskPriority.MEDIUM)

                result = await self._adapter.create_task(
                    title=title,
                    description=description,
                    project_id=project_id,
                    task_type=task_type,
                    priority=priority,
                    parent_id=epic_id,
                    labels=labels
                )

                if result.success:
                    results['created'].append({
                        'id': result.data.external_id,
                        'title': title,
                        'type': task_type_str
                    })
                    results['success_count'] += 1
                else:
                    results['failed'].append({
                        'title': title,
                        'error': result.error
                    })
                    results['error_count'] += 1

            except Exception as e:
                results['failed'].append({
                    'title': task_def.get('title', f'Task {idx + 1}'),
                    'error': str(e)
                })
                results['error_count'] += 1

        logger.info(f"Created {results['success_count']}/{results['total']} tasks from manifest")
        return results

    async def sync_task_status(
        self,
        task_id: str,
        external_status: str,
        source: str = "workflow"
    ) -> Dict[str, Any]:
        """
        Sync task status from an external system.

        Args:
            task_id: JIRA task ID
            external_status: Status from external system
            source: Source system name

        Returns:
            Dict with sync result
        """
        result = {
            'task_id': task_id,
            'external_status': external_status,
            'source': source,
            'synced': False,
            'previous_status': None,
            'new_status': None,
            'error': None
        }

        try:
            # Map external status to JIRA status
            status_map = {
                # Common workflow statuses
                'pending': TaskStatus.TODO,
                'queued': TaskStatus.TODO,
                'waiting': TaskStatus.TODO,
                'ready': TaskStatus.TODO,
                'running': TaskStatus.IN_PROGRESS,
                'executing': TaskStatus.IN_PROGRESS,
                'active': TaskStatus.IN_PROGRESS,
                'processing': TaskStatus.IN_PROGRESS,
                'completed': TaskStatus.DONE,
                'finished': TaskStatus.DONE,
                'success': TaskStatus.DONE,
                'passed': TaskStatus.DONE,
                'failed': TaskStatus.BLOCKED,
                'error': TaskStatus.BLOCKED,
                'blocked': TaskStatus.BLOCKED,
                'cancelled': TaskStatus.CANCELLED,
                'skipped': TaskStatus.CANCELLED,
                # Direct mappings
                'todo': TaskStatus.TODO,
                'to do': TaskStatus.TODO,
                'in progress': TaskStatus.IN_PROGRESS,
                'in_progress': TaskStatus.IN_PROGRESS,
                'done': TaskStatus.DONE
            }

            target_status = status_map.get(external_status.lower())
            if not target_status:
                result['error'] = f"Unknown external status: {external_status}"
                return result

            # Get current status
            get_result = await self._adapter.get_task(task_id)
            if not get_result.success:
                result['error'] = f"Failed to get task: {get_result.error}"
                return result

            current_status = get_result.data.status
            result['previous_status'] = current_status.value if current_status else 'unknown'

            # Skip if already at target status
            if current_status == target_status:
                result['synced'] = True
                result['new_status'] = target_status.value
                return result

            # Transition to new status
            transition_result = await self._adapter.transition_task(
                task_id=task_id,
                target_status=target_status
            )

            if transition_result.success:
                result['synced'] = True
                result['new_status'] = target_status.value
                logger.info(f"Synced {task_id}: {result['previous_status']} -> {target_status.value} (from {source})")
            else:
                result['error'] = f"Failed to transition: {transition_result.error}"

            return result

        except Exception as e:
            logger.exception(f"Error syncing task status: {e}")
            result['error'] = str(e)
            return result

    def _build_completion_comment(
        self,
        task_id: str,
        reason: ClosureReason,
        summary: Optional[str] = None
    ) -> str:
        """Build a completion comment for a task"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        comment_parts = [
            f"Task completed at {timestamp}",
            f"Reason: {reason.value}"
        ]

        if summary:
            comment_parts.append(f"\nSummary:\n{summary}")

        comment_parts.append("\n---\nAutomatically closed by TaskManagementService")

        return "\n".join(comment_parts)

    async def close(self) -> None:
        """Close the service and underlying adapter"""
        await self._adapter.close()


# Singleton instance
_service: Optional[TaskManagementService] = None


def get_task_management_service(
    token: Optional[str] = None
) -> TaskManagementService:
    """Get the default task management service instance"""
    global _service
    if _service is None:
        _service = TaskManagementService(token=token)
    return _service


def reset_task_management_service() -> None:
    """Reset the task management service (for testing)"""
    global _service
    _service = None
