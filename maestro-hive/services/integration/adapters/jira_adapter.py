"""
JIRA Adapter Implementation

Implements ITaskAdapter for JIRA via the internal adapter API.
Uses localhost:14100 as the internal API endpoint.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..interfaces import (
    ITaskAdapter,
    TaskData,
    TaskStatus,
    TaskPriority,
    TaskType,
    SearchQuery,
    AdapterResult
)

logger = logging.getLogger(__name__)


# Status mapping: internal -> JIRA
STATUS_TO_JIRA = {
    TaskStatus.TODO: "To Do",
    TaskStatus.IN_PROGRESS: "In Progress",
    TaskStatus.DONE: "Done",
    TaskStatus.BLOCKED: "Blocked",
    TaskStatus.CANCELLED: "Cancelled"
}

# Status mapping: JIRA -> internal
JIRA_TO_STATUS = {
    "to do": TaskStatus.TODO,
    "in progress": TaskStatus.IN_PROGRESS,
    "done": TaskStatus.DONE,
    "blocked": TaskStatus.BLOCKED,
    "cancelled": TaskStatus.CANCELLED
}

# Priority mapping
PRIORITY_TO_JIRA = {
    TaskPriority.HIGHEST: "Highest",
    TaskPriority.HIGH: "High",
    TaskPriority.MEDIUM: "Medium",
    TaskPriority.LOW: "Low",
    TaskPriority.LOWEST: "Lowest"
}

JIRA_TO_PRIORITY = {
    "highest": TaskPriority.HIGHEST,
    "high": TaskPriority.HIGH,
    "medium": TaskPriority.MEDIUM,
    "low": TaskPriority.LOW,
    "lowest": TaskPriority.LOWEST
}

# Type mapping
TYPE_TO_JIRA = {
    TaskType.EPIC: "Epic",
    TaskType.STORY: "Story",
    TaskType.TASK: "Task",
    TaskType.SUBTASK: "Sub-task",
    TaskType.BUG: "Bug"
}

JIRA_TO_TYPE = {
    "epic": TaskType.EPIC,
    "story": TaskType.STORY,
    "task": TaskType.TASK,
    "sub-task": TaskType.SUBTASK,
    "subtask": TaskType.SUBTASK,
    "bug": TaskType.BUG
}


class JiraAdapter(ITaskAdapter):
    """
    JIRA adapter using internal API at localhost:14100.

    Configuration:
        base_url: Internal API URL (default: http://localhost:14100)
        token: JWT authentication token
        default_project: Default JIRA project ID
    """

    def __init__(
        self,
        base_url: str = "http://localhost:14100",
        token: Optional[str] = None,
        default_project: str = "MD"
    ):
        """
        Initialize JIRA adapter.

        Args:
            base_url: Internal API base URL
            token: JWT token for authentication
            default_project: Default project ID
        """
        self._base_url = base_url.rstrip('/')
        self._token = token
        self._default_project = default_project
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"JiraAdapter initialized with base_url={base_url}")

    @property
    def adapter_name(self) -> str:
        return "jira"

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _parse_task(self, data: Dict[str, Any]) -> TaskData:
        """Parse JIRA API response to TaskData"""
        status_name = data.get('status', {}).get('name', 'To Do').lower()
        priority_name = data.get('priority', 'medium').lower()
        type_name = data.get('type', 'task').lower()

        return TaskData(
            id=data.get('id', ''),
            external_id=data.get('externalId', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            type=JIRA_TO_TYPE.get(type_name, TaskType.TASK),
            status=JIRA_TO_STATUS.get(status_name, TaskStatus.TODO),
            priority=JIRA_TO_PRIORITY.get(priority_name, TaskPriority.MEDIUM),
            assignee=data.get('assignee', {}).get('name') if data.get('assignee') else None,
            reporter=data.get('reporter', {}).get('name') if data.get('reporter') else None,
            parent_id=data.get('parentId'),
            project_id=data.get('project', {}).get('externalId'),
            labels=data.get('labels', []),
            story_points=data.get('storyPoints'),
            created_at=datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00')) if data.get('createdAt') else None,
            updated_at=datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00')) if data.get('updatedAt') else None,
            deep_link=data.get('deepLink'),
            custom_fields=data.get('customFields', {})
        )

    async def create_task(
        self,
        title: str,
        description: str = "",
        project_id: Optional[str] = None,
        task_type: TaskType = TaskType.TASK,
        priority: TaskPriority = TaskPriority.MEDIUM,
        parent_id: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """Create a new task in JIRA"""
        try:
            client = await self._get_client()
            payload = {
                "title": title,
                "description": description,
                "projectId": project_id or self._default_project,
                "type": TYPE_TO_JIRA.get(task_type, "Task"),
                "priority": PRIORITY_TO_JIRA.get(priority, "Medium")
            }

            if parent_id:
                payload["parentId"] = parent_id
            if assignee:
                payload["assignee"] = assignee
            if labels:
                payload["labels"] = labels

            response = await client.post(
                f"{self._base_url}/api/integrations/tasks",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                task = self._parse_task(result.get('output', {}))
                return AdapterResult(success=True, data=task)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            return AdapterResult(success=False, error=str(e))

    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """Update an existing task"""
        try:
            client = await self._get_client()
            payload = {}

            if title is not None:
                payload["title"] = title
            if description is not None:
                payload["description"] = description
            if priority is not None:
                payload["priority"] = PRIORITY_TO_JIRA.get(priority, "Medium")
            if assignee is not None:
                payload["assignee"] = assignee
            if labels is not None:
                payload["labels"] = labels

            response = await client.patch(
                f"{self._base_url}/api/integrations/tasks/{task_id}",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                task = self._parse_task(result.get('output', {}))
                return AdapterResult(success=True, data=task)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to update task: {e}")
            return AdapterResult(success=False, error=str(e))

    async def transition_task(
        self,
        task_id: str,
        target_status: TaskStatus
    ) -> AdapterResult:
        """Transition task to a new status"""
        try:
            client = await self._get_client()
            payload = {
                "targetStatus": STATUS_TO_JIRA.get(target_status, "To Do")
            }

            response = await client.post(
                f"{self._base_url}/api/integrations/tasks/{task_id}/transition",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                task = self._parse_task(result.get('output', {}))
                return AdapterResult(success=True, data=task)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to transition task: {e}")
            return AdapterResult(success=False, error=str(e))

    async def get_task(self, task_id: str) -> AdapterResult:
        """Get a task by ID"""
        try:
            client = await self._get_client()

            response = await client.get(
                f"{self._base_url}/api/integrations/tasks/{task_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                task = self._parse_task(result.get('output', {}))
                return AdapterResult(success=True, data=task)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to get task: {e}")
            return AdapterResult(success=False, error=str(e))

    async def search_tasks(self, query: SearchQuery) -> AdapterResult:
        """Search for tasks"""
        try:
            client = await self._get_client()

            params = {}
            if query.project_id:
                params["projectId"] = query.project_id
            if query.text:
                params["jql"] = f'text ~ "{query.text}"'

            response = await client.get(
                f"{self._base_url}/api/integrations/tasks",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tasks = [
                    self._parse_task(item)
                    for item in result.get('output', {}).get('result', [])
                ]
                return AdapterResult(success=True, data=tasks)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to search tasks: {e}")
            return AdapterResult(success=False, error=str(e))

    async def create_epic(
        self,
        title: str,
        description: str = "",
        project_id: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> AdapterResult:
        """Create a new epic"""
        return await self.create_task(
            title=title,
            description=description,
            project_id=project_id,
            task_type=TaskType.EPIC,
            labels=labels
        )

    async def delete_task(self, task_id: str) -> AdapterResult:
        """Delete a task"""
        try:
            client = await self._get_client()

            response = await client.delete(
                f"{self._base_url}/api/integrations/tasks/{task_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                return AdapterResult(success=True)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to delete task: {e}")
            return AdapterResult(success=False, error=str(e))

    async def health_check(self) -> AdapterResult:
        """Check adapter health"""
        try:
            client = await self._get_client()

            response = await client.get(
                f"{self._base_url}/health",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return AdapterResult(
                    success=True,
                    data={'status': 'healthy', 'adapter': 'jira'}
                )
            else:
                return AdapterResult(
                    success=False,
                    error=f"Health check failed: {response.status_code}"
                )

        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    async def add_comment(
        self,
        task_id: str,
        comment: str
    ) -> AdapterResult:
        """Add a comment to a task"""
        try:
            client = await self._get_client()
            payload = {"body": comment}

            response = await client.post(
                f"{self._base_url}/api/integrations/tasks/{task_id}/comments",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                return AdapterResult(success=True, data=result.get('output', {}))
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to add comment: {e}")
            return AdapterResult(success=False, error=str(e))

    async def get_epic_children(
        self,
        epic_id: str,
        project_id: Optional[str] = None
    ) -> AdapterResult:
        """Get all children (stories/tasks) of an epic"""
        try:
            client = await self._get_client()

            # Search for tasks with this epic as parent
            proj = project_id or self._default_project
            params = {"jql": f"project={proj}"}

            response = await client.get(
                f"{self._base_url}/api/integrations/tasks",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                # Filter tasks where parentId or epicId matches
                items = result.get('output', {}).get('items', [])
                children = [
                    self._parse_task(item)
                    for item in items
                    if item.get('parentId') == epic_id or item.get('epicId') == epic_id
                ]
                return AdapterResult(success=True, data=children)
            else:
                return AdapterResult(
                    success=False,
                    error=result.get('error', {}).get('message', 'Unknown error')
                )

        except Exception as e:
            logger.exception(f"Failed to get epic children: {e}")
            return AdapterResult(success=False, error=str(e))

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
