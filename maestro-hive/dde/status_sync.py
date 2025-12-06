"""
DDE ↔ JIRA Bidirectional Status Synchronization Module (MD-2119)

Implements bidirectional status sync between DDE execution nodes and JIRA tasks.
- DDE node completion updates JIRA task status
- JIRA status changes can trigger DDE state changes (via webhooks)
- Status mapping between DDE (PENDING, RUNNING, COMPLETED) and JIRA (To Do, In Progress, Done)

Author: AI Agent
Created: 2025-12-02
Parent: MD-2106 (Task Management Integration)
"""

import logging
import asyncio
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import aiohttp

logger = logging.getLogger(__name__)


class DDEStatus(Enum):
    """DDE Node execution statuses"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class JIRAStatus(Enum):
    """JIRA task statuses"""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DEMO = "Demo"
    UAT = "UAT"
    DONE = "Done"


# Bidirectional status mapping
DDE_TO_JIRA_STATUS: Dict[DDEStatus, JIRAStatus] = {
    DDEStatus.PENDING: JIRAStatus.TODO,
    DDEStatus.READY: JIRAStatus.TODO,
    DDEStatus.RUNNING: JIRAStatus.IN_PROGRESS,
    DDEStatus.COMPLETED: JIRAStatus.DONE,
    DDEStatus.FAILED: JIRAStatus.IN_PROGRESS,  # Keep in progress, add failure comment
    DDEStatus.SKIPPED: JIRAStatus.DONE,  # Mark as done with skip note
    DDEStatus.BLOCKED: JIRAStatus.TODO,  # Back to todo with blocked note
}

JIRA_TO_DDE_STATUS: Dict[JIRAStatus, DDEStatus] = {
    JIRAStatus.TODO: DDEStatus.PENDING,
    JIRAStatus.IN_PROGRESS: DDEStatus.RUNNING,
    JIRAStatus.DEMO: DDEStatus.RUNNING,  # Still in progress
    JIRAStatus.UAT: DDEStatus.RUNNING,  # Still in progress
    JIRAStatus.DONE: DDEStatus.COMPLETED,
}


@dataclass
class StatusSyncEvent:
    """Event representing a status change"""
    source: str  # 'dde' or 'jira'
    entity_id: str  # Node ID or JIRA key
    old_status: str
    new_status: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    synced: bool = False
    sync_error: Optional[str] = None


@dataclass
class SyncBinding:
    """Binding between DDE node and JIRA task"""
    node_id: str
    jira_key: str
    last_dde_status: Optional[DDEStatus] = None
    last_jira_status: Optional[JIRAStatus] = None
    created_at: datetime = field(default_factory=datetime.now)
    sync_enabled: bool = True


class StatusSyncService:
    """
    Bidirectional status synchronization service.

    Handles:
    - DDE → JIRA: When a DDE node status changes, update corresponding JIRA task
    - JIRA → DDE: When a JIRA task status changes (webhook), update DDE node state
    """

    def __init__(
        self,
        jira_api_url: str = "http://localhost:14100/api/integrations/tasks",
        token: Optional[str] = None,
        auto_sync: bool = True
    ):
        """
        Initialize status sync service.

        Args:
            jira_api_url: Base URL for JIRA adapter API
            token: JWT token for authentication
            auto_sync: Enable automatic bidirectional sync
        """
        self.jira_api_url = jira_api_url
        self.token = token
        self.auto_sync = auto_sync

        # Bindings between DDE nodes and JIRA tasks
        self.bindings: Dict[str, SyncBinding] = {}  # node_id -> binding
        self.jira_to_node: Dict[str, str] = {}  # jira_key -> node_id

        # Event log for audit trail
        self.event_log: List[StatusSyncEvent] = []

        # Callbacks for status changes
        self._dde_status_callbacks: List[Callable] = []
        self._jira_status_callbacks: List[Callable] = []

        logger.info(f"StatusSyncService initialized (auto_sync={auto_sync})")

    def set_token(self, token: str):
        """Set or update JWT token"""
        self.token = token

    def bind(self, node_id: str, jira_key: str) -> SyncBinding:
        """
        Create a binding between a DDE node and a JIRA task.

        Args:
            node_id: DDE node identifier
            jira_key: JIRA task key (e.g., MD-2119)

        Returns:
            SyncBinding object
        """
        binding = SyncBinding(node_id=node_id, jira_key=jira_key)
        self.bindings[node_id] = binding
        self.jira_to_node[jira_key] = node_id

        logger.info(f"Created sync binding: {node_id} ↔ {jira_key}")
        return binding

    def unbind(self, node_id: str):
        """Remove binding for a node"""
        if node_id in self.bindings:
            binding = self.bindings[node_id]
            del self.jira_to_node[binding.jira_key]
            del self.bindings[node_id]
            logger.info(f"Removed sync binding for node: {node_id}")

    def get_binding(self, node_id: str) -> Optional[SyncBinding]:
        """Get binding for a node"""
        return self.bindings.get(node_id)

    def get_binding_by_jira(self, jira_key: str) -> Optional[SyncBinding]:
        """Get binding for a JIRA task"""
        node_id = self.jira_to_node.get(jira_key)
        return self.bindings.get(node_id) if node_id else None

    # ========== DDE → JIRA Sync ==========

    async def on_dde_status_change(
        self,
        node_id: str,
        old_status: DDEStatus,
        new_status: DDEStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Handle DDE node status change and sync to JIRA.

        Args:
            node_id: DDE node identifier
            old_status: Previous status
            new_status: New status
            error_message: Optional error message for failures

        Returns:
            True if sync successful, False otherwise
        """
        event = StatusSyncEvent(
            source='dde',
            entity_id=node_id,
            old_status=old_status.value,
            new_status=new_status.value,
            metadata={'error_message': error_message} if error_message else {}
        )
        self.event_log.append(event)

        # Check if we have a binding for this node
        binding = self.get_binding(node_id)
        if not binding or not binding.sync_enabled:
            logger.debug(f"No sync binding for node {node_id}, skipping JIRA update")
            return True

        binding.last_dde_status = new_status

        if not self.auto_sync:
            logger.debug(f"Auto-sync disabled, skipping JIRA update for {node_id}")
            return True

        # Map DDE status to JIRA status
        target_jira_status = DDE_TO_JIRA_STATUS.get(new_status)
        if not target_jira_status:
            logger.warning(f"No JIRA mapping for DDE status: {new_status}")
            return False

        # Build comment based on status
        comment = self._build_sync_comment(node_id, old_status, new_status, error_message)

        # Sync to JIRA
        try:
            success = await self._update_jira_status(
                binding.jira_key,
                target_jira_status.value,
                comment
            )
            event.synced = success
            if success:
                binding.last_jira_status = target_jira_status
                logger.info(f"Synced DDE {node_id} ({new_status.value}) → JIRA {binding.jira_key} ({target_jira_status.value})")
            return success
        except Exception as e:
            event.sync_error = str(e)
            logger.error(f"Failed to sync DDE → JIRA: {e}")
            return False

    def _build_sync_comment(
        self,
        node_id: str,
        old_status: DDEStatus,
        new_status: DDEStatus,
        error_message: Optional[str]
    ) -> str:
        """Build comment for JIRA update"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if new_status == DDEStatus.COMPLETED:
            return f"[DDE Sync {timestamp}] Node {node_id} completed successfully."
        elif new_status == DDEStatus.FAILED:
            return f"[DDE Sync {timestamp}] Node {node_id} failed: {error_message or 'Unknown error'}"
        elif new_status == DDEStatus.RUNNING:
            return f"[DDE Sync {timestamp}] Node {node_id} started execution."
        elif new_status == DDEStatus.BLOCKED:
            return f"[DDE Sync {timestamp}] Node {node_id} is blocked."
        elif new_status == DDEStatus.SKIPPED:
            return f"[DDE Sync {timestamp}] Node {node_id} was skipped."
        else:
            return f"[DDE Sync {timestamp}] Node {node_id} status: {new_status.value}"

    async def _update_jira_status(
        self,
        jira_key: str,
        target_status: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Update JIRA task status via adapter API.

        Args:
            jira_key: JIRA task key
            target_status: Target status name
            comment: Optional comment

        Returns:
            True if successful
        """
        if not self.token:
            logger.error("No JWT token configured for JIRA API")
            return False

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            # Transition the task
            transition_url = f"{self.jira_api_url}/{jira_key}/transition"
            transition_data = {
                "targetStatus": target_status,
                "comment": comment
            }

            async with session.post(transition_url, headers=headers, json=transition_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get('status') == 'success'
                else:
                    error_text = await resp.text()
                    logger.error(f"JIRA transition failed ({resp.status}): {error_text}")
                    return False

    # ========== JIRA → DDE Sync ==========

    async def on_jira_status_change(
        self,
        jira_key: str,
        old_status: str,
        new_status: str
    ) -> Optional[DDEStatus]:
        """
        Handle JIRA task status change (from webhook) and return corresponding DDE status.

        Args:
            jira_key: JIRA task key
            old_status: Previous status
            new_status: New status

        Returns:
            DDEStatus if binding exists, None otherwise
        """
        event = StatusSyncEvent(
            source='jira',
            entity_id=jira_key,
            old_status=old_status,
            new_status=new_status
        )
        self.event_log.append(event)

        # Check if we have a binding for this JIRA task
        binding = self.get_binding_by_jira(jira_key)
        if not binding or not binding.sync_enabled:
            logger.debug(f"No sync binding for JIRA {jira_key}")
            return None

        # Map JIRA status to DDE status
        try:
            jira_status = JIRAStatus(new_status)
            dde_status = JIRA_TO_DDE_STATUS.get(jira_status)

            if dde_status:
                binding.last_jira_status = jira_status
                binding.last_dde_status = dde_status
                event.synced = True

                logger.info(f"JIRA {jira_key} ({new_status}) → DDE {binding.node_id} ({dde_status.value})")

                # Notify callbacks
                for callback in self._dde_status_callbacks:
                    try:
                        callback(binding.node_id, dde_status)
                    except Exception as e:
                        logger.error(f"Status callback error: {e}")

                return dde_status
            else:
                logger.warning(f"No DDE mapping for JIRA status: {new_status}")
                return None

        except ValueError:
            logger.warning(f"Unknown JIRA status: {new_status}")
            return None

    # ========== Callbacks ==========

    def on_dde_status_update(self, callback: Callable[[str, DDEStatus], None]):
        """Register callback for DDE status updates (from JIRA changes)"""
        self._dde_status_callbacks.append(callback)

    def on_jira_status_update(self, callback: Callable[[str, JIRAStatus], None]):
        """Register callback for JIRA status updates (from DDE changes)"""
        self._jira_status_callbacks.append(callback)

    # ========== Batch Operations ==========

    async def sync_all_bindings_to_jira(self) -> Dict[str, bool]:
        """Sync all DDE node statuses to their bound JIRA tasks"""
        results = {}
        for node_id, binding in self.bindings.items():
            if binding.last_dde_status:
                success = await self.on_dde_status_change(
                    node_id,
                    DDEStatus.PENDING,
                    binding.last_dde_status
                )
                results[node_id] = success
        return results

    # ========== Audit & Reporting ==========

    def get_sync_history(self, limit: int = 100) -> List[Dict]:
        """Get recent sync events"""
        events = sorted(self.event_log, key=lambda e: e.timestamp, reverse=True)[:limit]
        return [
            {
                'source': e.source,
                'entity_id': e.entity_id,
                'old_status': e.old_status,
                'new_status': e.new_status,
                'timestamp': e.timestamp.isoformat(),
                'synced': e.synced,
                'error': e.sync_error
            }
            for e in events
        ]

    def get_binding_status(self) -> List[Dict]:
        """Get status of all bindings"""
        return [
            {
                'node_id': b.node_id,
                'jira_key': b.jira_key,
                'last_dde_status': b.last_dde_status.value if b.last_dde_status else None,
                'last_jira_status': b.last_jira_status.value if b.last_jira_status else None,
                'sync_enabled': b.sync_enabled
            }
            for b in self.bindings.values()
        ]


# Utility functions for integration
def map_dde_to_jira(dde_status: str) -> str:
    """Map DDE status string to JIRA status string"""
    try:
        dde = DDEStatus(dde_status)
        jira = DDE_TO_JIRA_STATUS.get(dde)
        return jira.value if jira else "To Do"
    except ValueError:
        return "To Do"


def map_jira_to_dde(jira_status: str) -> str:
    """Map JIRA status string to DDE status string"""
    try:
        jira = JIRAStatus(jira_status)
        dde = JIRA_TO_DDE_STATUS.get(jira)
        return dde.value if dde else "pending"
    except ValueError:
        return "pending"


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_sync():
        # Initialize service
        sync = StatusSyncService(
            jira_api_url="http://localhost:14100/api/integrations/tasks",
            auto_sync=False  # Disable for testing
        )

        # Create binding
        sync.bind("node_requirements", "MD-2119")

        # Test DDE → JIRA status mapping
        print("\n=== Status Mappings ===")
        for dde_status in DDEStatus:
            jira_status = DDE_TO_JIRA_STATUS.get(dde_status)
            print(f"DDE {dde_status.value:12} → JIRA {jira_status.value if jira_status else 'N/A'}")

        print("\n=== Reverse Mappings ===")
        for jira_status in JIRAStatus:
            dde_status = JIRA_TO_DDE_STATUS.get(jira_status)
            print(f"JIRA {jira_status.value:12} → DDE {dde_status.value if dde_status else 'N/A'}")

        # Test JIRA → DDE update
        print("\n=== Test JIRA → DDE ===")
        result = await sync.on_jira_status_change("MD-2119", "To Do", "In Progress")
        print(f"JIRA 'In Progress' maps to DDE: {result}")

        # Show bindings
        print("\n=== Bindings ===")
        print(json.dumps(sync.get_binding_status(), indent=2))

        # Show history
        print("\n=== Sync History ===")
        print(json.dumps(sync.get_sync_history(), indent=2))

    asyncio.run(test_sync())
