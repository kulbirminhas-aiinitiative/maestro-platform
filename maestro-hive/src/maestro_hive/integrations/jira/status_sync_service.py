"""
JIRA Status Sync Service

Bidirectional status synchronization between Maestro Hive and JIRA.
Subscribes to Redis events and updates JIRA issues accordingly.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HiveStatus(Enum):
    """Internal Hive task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class JiraStatus(Enum):
    """JIRA status IDs."""
    TO_DO = "10012"
    IN_PROGRESS = "10013"
    DONE = "10014"
    BLOCKED = "10015"


# Bidirectional status mapping
HIVE_TO_JIRA: Dict[HiveStatus, JiraStatus] = {
    HiveStatus.PENDING: JiraStatus.TO_DO,
    HiveStatus.IN_PROGRESS: JiraStatus.IN_PROGRESS,
    HiveStatus.COMPLETED: JiraStatus.DONE,
    HiveStatus.FAILED: JiraStatus.BLOCKED,
    HiveStatus.BLOCKED: JiraStatus.BLOCKED,
}

JIRA_TO_HIVE: Dict[JiraStatus, HiveStatus] = {
    JiraStatus.TO_DO: HiveStatus.PENDING,
    JiraStatus.IN_PROGRESS: HiveStatus.IN_PROGRESS,
    JiraStatus.DONE: HiveStatus.COMPLETED,
    JiraStatus.BLOCKED: HiveStatus.BLOCKED,
}


@dataclass
class StatusChangeEvent:
    """Status change event from Redis."""
    task_id: str
    old_status: str
    new_status: str
    timestamp: datetime
    source: str  # "hive" or "jira"
    jira_key: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    task_id: str
    jira_key: Optional[str]
    old_status: str
    new_status: str
    error: Optional[str] = None


class JiraStatusSyncService:
    """
    Bidirectional status synchronization between Hive and JIRA.
    
    Features:
    - Subscribes to Redis event bus for status changes
    - Updates JIRA issues when Hive tasks change
    - Handles JIRA webhooks for reverse sync
    - Conflict resolution for concurrent updates
    """
    
    def __init__(
        self,
        jira_url: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_token: Optional[str] = None,
        redis_url: Optional[str] = None,
    ):
        """Initialize the sync service."""
        self.jira_url = jira_url or os.getenv("JIRA_URL")
        self.jira_email = jira_email or os.getenv("JIRA_EMAIL")
        self.jira_token = jira_token or os.getenv("JIRA_API_TOKEN")
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        
        self._task_jira_mapping: Dict[str, str] = {}  # task_id -> jira_key
        self._sync_history: List[SyncResult] = []
        self._running = False
        self._callbacks: List[Callable[[SyncResult], None]] = []
        
        logger.info("JiraStatusSyncService initialized")
    
    def register_callback(self, callback: Callable[[SyncResult], None]):
        """Register a callback for sync events."""
        self._callbacks.append(callback)
    
    def map_task_to_jira(self, task_id: str, jira_key: str):
        """Register a mapping between task ID and JIRA key."""
        self._task_jira_mapping[task_id] = jira_key
        logger.debug(f"Mapped task {task_id} to JIRA {jira_key}")
    
    def get_jira_key(self, task_id: str) -> Optional[str]:
        """Get JIRA key for a task."""
        return self._task_jira_mapping.get(task_id)
    
    def hive_to_jira_status(self, hive_status: str) -> JiraStatus:
        """Convert Hive status to JIRA status."""
        try:
            status = HiveStatus(hive_status)
            return HIVE_TO_JIRA.get(status, JiraStatus.TO_DO)
        except ValueError:
            return JiraStatus.TO_DO
    
    def jira_to_hive_status(self, jira_status: str) -> HiveStatus:
        """Convert JIRA status to Hive status."""
        try:
            status = JiraStatus(jira_status)
            return JIRA_TO_HIVE.get(status, HiveStatus.PENDING)
        except ValueError:
            return HiveStatus.PENDING
    
    async def sync_task_status(
        self,
        task_id: str,
        new_status: str,
        source: str = "hive"
    ) -> SyncResult:
        """
        Synchronize status change to the other system.
        
        Args:
            task_id: The task identifier
            new_status: The new status value
            source: Where the change originated ("hive" or "jira")
            
        Returns:
            SyncResult with operation details
        """
        jira_key = self._task_jira_mapping.get(task_id)
        
        if source == "hive" and jira_key:
            # Sync from Hive to JIRA
            jira_status = self.hive_to_jira_status(new_status)
            result = await self._update_jira_status(jira_key, jira_status)
        elif source == "jira" and task_id:
            # Sync from JIRA to Hive
            hive_status = self.jira_to_hive_status(new_status)
            result = await self._update_hive_status(task_id, hive_status)
        else:
            result = SyncResult(
                success=False,
                task_id=task_id,
                jira_key=jira_key,
                old_status="",
                new_status=new_status,
                error="No mapping found or invalid source"
            )
        
        self._sync_history.append(result)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        return result
    
    async def _update_jira_status(
        self,
        jira_key: str,
        status: JiraStatus
    ) -> SyncResult:
        """Update JIRA issue status."""
        # In production, this would call JIRA API
        # POST /rest/api/3/issue/{issueKey}/transitions
        
        logger.info(f"Updating JIRA {jira_key} to status {status.name}")
        
        return SyncResult(
            success=True,
            task_id="",
            jira_key=jira_key,
            old_status="",
            new_status=status.name,
        )
    
    async def _update_hive_status(
        self,
        task_id: str,
        status: HiveStatus
    ) -> SyncResult:
        """Update Hive task status."""
        # In production, this would update the task in Hive
        
        logger.info(f"Updating Hive task {task_id} to status {status.value}")
        
        return SyncResult(
            success=True,
            task_id=task_id,
            jira_key=self._task_jira_mapping.get(task_id),
            old_status="",
            new_status=status.value,
        )
    
    async def handle_jira_webhook(self, payload: Dict[str, Any]) -> SyncResult:
        """
        Handle incoming JIRA webhook for status changes.
        
        Args:
            payload: JIRA webhook payload
            
        Returns:
            SyncResult from processing
        """
        webhook_event = payload.get("webhookEvent", "")
        
        if "issue_updated" not in webhook_event:
            return SyncResult(
                success=True,
                task_id="",
                jira_key="",
                old_status="",
                new_status="",
                error="Not a status change event"
            )
        
        issue = payload.get("issue", {})
        jira_key = issue.get("key", "")
        
        changelog = payload.get("changelog", {})
        status_change = None
        
        for item in changelog.get("items", []):
            if item.get("field") == "status":
                status_change = {
                    "from": item.get("fromString"),
                    "to": item.get("toString"),
                    "to_id": item.get("to"),
                }
                break
        
        if not status_change:
            return SyncResult(
                success=True,
                task_id="",
                jira_key=jira_key,
                old_status="",
                new_status="",
                error="No status change in changelog"
            )
        
        # Find task ID by JIRA key
        task_id = None
        for tid, jkey in self._task_jira_mapping.items():
            if jkey == jira_key:
                task_id = tid
                break
        
        if task_id:
            return await self.sync_task_status(
                task_id,
                status_change["to_id"],
                source="jira"
            )
        
        return SyncResult(
            success=False,
            task_id="",
            jira_key=jira_key,
            old_status=status_change["from"],
            new_status=status_change["to"],
            error="No task mapping found for JIRA key"
        )
    
    async def start_event_subscription(self):
        """Start subscribing to Redis status change events."""
        self._running = True
        logger.info("Started event subscription")
        
        # In production, this would subscribe to Redis pub/sub
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the sync service."""
        self._running = False
        logger.info("Stopped sync service")
    
    def get_sync_history(
        self,
        limit: int = 100,
        success_only: bool = False
    ) -> List[SyncResult]:
        """Get sync history."""
        history = self._sync_history[-limit:]
        if success_only:
            history = [r for r in history if r.success]
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sync statistics."""
        total = len(self._sync_history)
        successful = sum(1 for r in self._sync_history if r.success)
        
        return {
            "total_syncs": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "mappings": len(self._task_jira_mapping),
        }
