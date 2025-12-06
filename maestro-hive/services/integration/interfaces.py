"""
Integration Adapter Interfaces (MD-2109, MD-2110)

Defines abstract interfaces for external tool adapters:
- ITaskAdapter: JIRA, Monday.com, Asana task management
- IDocumentAdapter: Confluence, Notion, Google Docs

These interfaces enable the orchestrator to work with any external
tool through a consistent API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class TaskStatus(Enum):
    """Standard task status mapping"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Standard priority levels"""
    HIGHEST = "highest"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    LOWEST = "lowest"


class TaskType(Enum):
    """Standard task types"""
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"
    BUG = "bug"


@dataclass
class TaskData:
    """
    Normalized task data structure.

    Maps to/from external systems like JIRA, Monday.com, etc.
    """
    id: str
    external_id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.TASK
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    story_points: Optional[float] = None
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deep_link: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'external_id': self.external_id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'status': self.status.value,
            'priority': self.priority.value,
            'assignee': self.assignee,
            'reporter': self.reporter,
            'parent_id': self.parent_id,
            'project_id': self.project_id,
            'labels': self.labels,
            'story_points': self.story_points,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deep_link': self.deep_link,
            'custom_fields': self.custom_fields
        }


@dataclass
class DocumentData:
    """
    Normalized document data structure.

    Maps to/from external systems like Confluence, Notion, etc.
    """
    id: str
    external_id: str
    title: str
    content: str = ""
    space_id: Optional[str] = None
    parent_id: Optional[str] = None
    version: int = 1
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deep_link: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'external_id': self.external_id,
            'title': self.title,
            'content': self.content,
            'space_id': self.space_id,
            'parent_id': self.parent_id,
            'version': self.version,
            'author': self.author,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deep_link': self.deep_link,
            'labels': self.labels,
            'metadata': self.metadata
        }


@dataclass
class SearchQuery:
    """Query parameters for searching tasks/documents"""
    project_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    type: Optional[TaskType] = None
    assignee: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    text: Optional[str] = None
    parent_id: Optional[str] = None
    limit: int = 50
    offset: int = 0
    custom_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Standard result wrapper for adapter operations"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ITaskAdapter(ABC):
    """
    Interface for task management adapters (MD-2109).

    Implementations:
    - JiraAdapter: JIRA integration via internal API
    - MondayAdapter: Monday.com integration
    - AsanaAdapter: Asana integration

    All methods return AdapterResult for consistent error handling.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Unique identifier for this adapter (e.g., 'jira', 'monday')"""
        pass

    @abstractmethod
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
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            project_id: Target project
            task_type: Type of task (epic, story, task, etc.)
            priority: Priority level
            parent_id: Parent task/epic ID
            assignee: Assigned user
            labels: Task labels
            custom_fields: Additional fields

        Returns:
            AdapterResult with TaskData on success
        """
        pass

    @abstractmethod
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
        """
        Update an existing task.

        Args:
            task_id: Task ID to update
            title: New title (optional)
            description: New description (optional)
            priority: New priority (optional)
            assignee: New assignee (optional)
            labels: New labels (optional)
            custom_fields: Additional fields to update

        Returns:
            AdapterResult with updated TaskData on success
        """
        pass

    @abstractmethod
    async def transition_task(
        self,
        task_id: str,
        target_status: TaskStatus
    ) -> AdapterResult:
        """
        Transition task to a new status.

        Args:
            task_id: Task ID to transition
            target_status: Target status

        Returns:
            AdapterResult with updated TaskData on success
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> AdapterResult:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            AdapterResult with TaskData on success
        """
        pass

    @abstractmethod
    async def search_tasks(self, query: SearchQuery) -> AdapterResult:
        """
        Search for tasks.

        Args:
            query: Search parameters

        Returns:
            AdapterResult with List[TaskData] on success
        """
        pass

    @abstractmethod
    async def create_epic(
        self,
        title: str,
        description: str = "",
        project_id: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> AdapterResult:
        """
        Create a new epic.

        Args:
            title: Epic title
            description: Epic description
            project_id: Target project
            labels: Epic labels

        Returns:
            AdapterResult with TaskData on success
        """
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> AdapterResult:
        """
        Delete a task.

        Args:
            task_id: Task ID to delete

        Returns:
            AdapterResult with success status
        """
        pass

    async def health_check(self) -> AdapterResult:
        """
        Check adapter health/connectivity.

        Returns:
            AdapterResult with health status
        """
        return AdapterResult(success=True, data={'status': 'healthy'})


class IDocumentAdapter(ABC):
    """
    Interface for document management adapters (MD-2110).

    Implementations:
    - ConfluenceAdapter: Atlassian Confluence
    - NotionAdapter: Notion pages
    - GoogleDocsAdapter: Google Docs

    All methods return AdapterResult for consistent error handling.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Unique identifier for this adapter (e.g., 'confluence', 'notion')"""
        pass

    @abstractmethod
    async def create_page(
        self,
        title: str,
        content: str,
        space_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        Create a new document page.

        Args:
            title: Page title
            content: Page content (HTML/Markdown depending on adapter)
            space_id: Target space/workspace
            parent_id: Parent page ID
            labels: Page labels
            metadata: Additional metadata

        Returns:
            AdapterResult with DocumentData on success
        """
        pass

    @abstractmethod
    async def update_page(
        self,
        page_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        Update an existing page.

        Args:
            page_id: Page ID to update
            title: New title (optional)
            content: New content (optional)
            labels: New labels (optional)
            metadata: Additional metadata to update

        Returns:
            AdapterResult with updated DocumentData on success
        """
        pass

    @abstractmethod
    async def get_page(self, page_id: str) -> AdapterResult:
        """
        Get a page by ID.

        Args:
            page_id: Page ID

        Returns:
            AdapterResult with DocumentData on success
        """
        pass

    @abstractmethod
    async def delete_page(self, page_id: str) -> AdapterResult:
        """
        Delete a page.

        Args:
            page_id: Page ID to delete

        Returns:
            AdapterResult with success status
        """
        pass

    @abstractmethod
    async def search_pages(
        self,
        query: str,
        space_id: Optional[str] = None,
        limit: int = 50
    ) -> AdapterResult:
        """
        Search for pages.

        Args:
            query: Search text
            space_id: Limit to specific space
            limit: Maximum results

        Returns:
            AdapterResult with List[DocumentData] on success
        """
        pass

    @abstractmethod
    async def get_page_children(
        self,
        page_id: str,
        limit: int = 50
    ) -> AdapterResult:
        """
        Get child pages of a parent page.

        Args:
            page_id: Parent page ID
            limit: Maximum results

        Returns:
            AdapterResult with List[DocumentData] on success
        """
        pass

    async def health_check(self) -> AdapterResult:
        """
        Check adapter health/connectivity.

        Returns:
            AdapterResult with health status
        """
        return AdapterResult(success=True, data={'status': 'healthy'})
