"""
Shared State Management for Multi-Agent Teams
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """Shared task definition"""
    task_id: str
    description: str
    required_role: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    priority: int = 5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_be_claimed(self) -> bool:
        """Check if task can be claimed"""
        return self.status == TaskStatus.PENDING and not self.assigned_to

    def is_blocked(self) -> bool:
        """Check if task is blocked by dependencies"""
        return self.status == TaskStatus.BLOCKED or bool(self.dependencies)


class TaskQueue:
    """
    Shared task queue for multi-agent coordination.

    Features:
    - Priority-based task ordering
    - Role-based task filtering
    - Dependency management
    - Concurrent task claiming (thread-safe)
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def add_task(
        self,
        task_id: str,
        description: str,
        required_role: str = "any",
        priority: int = 5,
        dependencies: List[str] = None
    ) -> Task:
        """Add task to queue"""
        async with self._lock:
            task = Task(
                task_id=task_id,
                description=description,
                required_role=required_role,
                priority=priority,
                dependencies=dependencies or []
            )
            self.tasks[task_id] = task
            return task

    async def claim_task(self, agent_id: str, agent_role: str) -> Optional[Task]:
        """Claim next available task for agent role"""
        async with self._lock:
            # Find highest priority unclaimed task for role
            available_tasks = [
                t for t in self.tasks.values()
                if t.can_be_claimed() and
                (t.required_role == agent_role or t.required_role == "any") and
                not t.is_blocked()
            ]

            if not available_tasks:
                return None

            # Sort by priority (higher first)
            available_tasks.sort(key=lambda t: t.priority, reverse=True)
            task = available_tasks[0]

            # Claim task
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_to = agent_id
            task.claimed_at = datetime.now().isoformat()

            return task

    async def complete_task(self, task_id: str, result: str = "") -> bool:
        """Mark task as completed"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now().isoformat()

                # Unblock dependent tasks
                await self._unblock_dependents(task_id)
                return True

            return False

    async def _unblock_dependents(self, completed_task_id: str):
        """Unblock tasks that depend on completed task"""
        for task in self.tasks.values():
            if completed_task_id in task.dependencies:
                task.dependencies.remove(completed_task_id)

                # If no more dependencies, unblock
                if not task.dependencies and task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.PENDING

    async def get_task_stats(self) -> Dict[str, int]:
        """Get task queue statistics"""
        async with self._lock:
            return {
                "total": len(self.tasks),
                "pending": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
                "in_progress": sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
                "blocked": sum(1 for t in self.tasks.values() if t.status == TaskStatus.BLOCKED),
            }


@dataclass
class KnowledgeItem:
    """Shared knowledge item"""
    key: str
    value: Any
    category: str
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1
    tags: List[str] = field(default_factory=list)


class KnowledgeBase:
    """
    Shared knowledge base for team collaboration.

    Features:
    - Categorized knowledge storage
    - Version tracking
    - Tag-based search
    - Concurrent access (thread-safe)
    """

    def __init__(self):
        self.knowledge: Dict[str, KnowledgeItem] = {}
        self._lock = asyncio.Lock()

    async def store(
        self,
        key: str,
        value: Any,
        category: str,
        agent_id: str,
        tags: List[str] = None
    ) -> KnowledgeItem:
        """Store knowledge item"""
        async with self._lock:
            if key in self.knowledge:
                # Update existing
                item = self.knowledge[key]
                item.value = value
                item.updated_at = datetime.now().isoformat()
                item.version += 1
                if tags:
                    item.tags = list(set(item.tags + tags))
            else:
                # Create new
                item = KnowledgeItem(
                    key=key,
                    value=value,
                    category=category,
                    created_by=agent_id,
                    tags=tags or []
                )
                self.knowledge[key] = item

            return item

    async def retrieve(self, key: str) -> Optional[KnowledgeItem]:
        """Retrieve knowledge item"""
        async with self._lock:
            return self.knowledge.get(key)

    async def search_by_category(self, category: str) -> List[KnowledgeItem]:
        """Search knowledge by category"""
        async with self._lock:
            return [
                item for item in self.knowledge.values()
                if item.category == category
            ]

    async def search_by_tag(self, tag: str) -> List[KnowledgeItem]:
        """Search knowledge by tag"""
        async with self._lock:
            return [
                item for item in self.knowledge.values()
                if tag in item.tags
            ]

    async def get_all_categories(self) -> List[str]:
        """Get all knowledge categories"""
        async with self._lock:
            return list(set(item.category for item in self.knowledge.values()))


@dataclass
class Artifact:
    """Shared work artifact"""
    artifact_id: str
    name: str
    artifact_type: str  # "code", "document", "diagram", "test", etc.
    content: Any
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class SharedWorkspace:
    """
    Shared workspace for team artifacts and state.

    Features:
    - Artifact storage and retrieval
    - Versioned content
    - Metadata and tagging
    - Concurrent access (thread-safe)
    """

    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}
        self.task_queue = TaskQueue()
        self.knowledge_base = KnowledgeBase()
        self._lock = asyncio.Lock()

    async def store_artifact(
        self,
        artifact_id: str,
        name: str,
        artifact_type: str,
        content: Any,
        agent_id: str,
        metadata: Dict[str, Any] = None
    ) -> Artifact:
        """Store artifact in workspace"""
        async with self._lock:
            artifact = Artifact(
                artifact_id=artifact_id,
                name=name,
                artifact_type=artifact_type,
                content=content,
                created_by=agent_id,
                metadata=metadata or {}
            )
            self.artifacts[artifact_id] = artifact
            return artifact

    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Retrieve artifact"""
        async with self._lock:
            return self.artifacts.get(artifact_id)

    async def get_artifacts_by_type(self, artifact_type: str) -> List[Artifact]:
        """Get all artifacts of specific type"""
        async with self._lock:
            return [
                a for a in self.artifacts.values()
                if a.artifact_type == artifact_type
            ]

    async def get_workspace_stats(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        task_stats = await self.task_queue.get_task_stats()

        async with self._lock:
            return {
                "artifacts": {
                    "total": len(self.artifacts),
                    "by_type": self._count_by_type()
                },
                "tasks": task_stats,
                "knowledge": {
                    "total": len(self.knowledge_base.knowledge),
                    "categories": await self.knowledge_base.get_all_categories()
                }
            }

    def _count_by_type(self) -> Dict[str, int]:
        """Count artifacts by type"""
        counts = {}
        for artifact in self.artifacts.values():
            counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1
        return counts
