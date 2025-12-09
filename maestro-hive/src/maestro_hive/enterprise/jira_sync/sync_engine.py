"""
JIRA Bidirectional Sync Engine.

Implements full synchronization between Maestro workflows and JIRA issues.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import asyncio
import hashlib
import json


class SyncDirection(Enum):
    """Sync direction."""
    TO_JIRA = "to_jira"
    FROM_JIRA = "from_jira"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(Enum):
    """Sync operation status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FieldChange:
    """Record of a field change."""
    field_name: str
    old_value: Any
    new_value: Any
    source: str  # "maestro" or "jira"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SyncResult:
    """Result of sync operation."""
    workflow_id: str
    jira_issue_key: str
    direction: SyncDirection
    status: SyncStatus
    changes: List[FieldChange] = field(default_factory=list)
    conflicts: List["SyncConflict"] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0


@dataclass
class SyncState:
    """Sync state for a workflow-issue pair."""
    workflow_id: str
    jira_issue_key: str
    last_sync_at: Optional[datetime] = None
    maestro_hash: str = ""
    jira_hash: str = ""
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    is_linked: bool = True


class JIRASyncEngine:
    """
    Bidirectional sync engine between Maestro and JIRA.

    Supports:
    - Push Maestro changes to JIRA
    - Pull JIRA changes to Maestro
    - Bidirectional sync with conflict detection
    - Change tracking and history
    """

    def __init__(
        self,
        jira_client=None,
        maestro_db=None,
        field_mapper=None,
        conflict_resolver=None,
    ):
        """
        Initialize sync engine.

        Args:
            jira_client: JIRA API client
            maestro_db: Maestro database connection
            field_mapper: Field mapping configuration
            conflict_resolver: Conflict resolution handler
        """
        self.jira = jira_client
        self.db = maestro_db
        self.mapper = field_mapper
        self.resolver = conflict_resolver
        self._sync_states: Dict[str, SyncState] = {}
        self._sync_history: List[SyncResult] = []

    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash of data for change detection."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def link_workflow_to_issue(
        self,
        workflow_id: str,
        jira_issue_key: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
    ) -> SyncState:
        """
        Link Maestro workflow to JIRA issue.

        Args:
            workflow_id: Maestro workflow ID
            jira_issue_key: JIRA issue key
            direction: Sync direction

        Returns:
            SyncState for the link
        """
        state = SyncState(
            workflow_id=workflow_id,
            jira_issue_key=jira_issue_key,
            sync_direction=direction,
            last_sync_at=datetime.utcnow(),
        )

        self._sync_states[workflow_id] = state
        return state

    async def unlink_workflow(self, workflow_id: str) -> bool:
        """
        Unlink workflow from JIRA issue.

        Args:
            workflow_id: Workflow ID to unlink

        Returns:
            True if unlinked
        """
        if workflow_id in self._sync_states:
            self._sync_states[workflow_id].is_linked = False
            return True
        return False

    async def sync_to_jira(
        self,
        workflow_id: str,
        force: bool = False,
    ) -> SyncResult:
        """
        Push Maestro workflow changes to JIRA.

        Args:
            workflow_id: Workflow to sync
            force: Force sync even if no changes detected

        Returns:
            SyncResult with sync details
        """
        start_time = datetime.utcnow()

        state = self._sync_states.get(workflow_id)
        if not state or not state.is_linked:
            return SyncResult(
                workflow_id=workflow_id,
                jira_issue_key="",
                direction=SyncDirection.TO_JIRA,
                status=SyncStatus.FAILED,
                error="Workflow not linked to JIRA issue",
            )

        try:
            # Get current Maestro data
            maestro_data = await self._get_maestro_workflow(workflow_id)
            maestro_hash = self._compute_hash(maestro_data)

            # Check for changes
            if not force and maestro_hash == state.maestro_hash:
                return SyncResult(
                    workflow_id=workflow_id,
                    jira_issue_key=state.jira_issue_key,
                    direction=SyncDirection.TO_JIRA,
                    status=SyncStatus.SKIPPED,
                )

            # Map fields to JIRA format
            jira_fields = self._map_to_jira(maestro_data)

            # Update JIRA issue
            changes = await self._update_jira_issue(
                state.jira_issue_key,
                jira_fields,
                maestro_data,
            )

            # Update sync state
            state.maestro_hash = maestro_hash
            state.last_sync_at = datetime.utcnow()

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = SyncResult(
                workflow_id=workflow_id,
                jira_issue_key=state.jira_issue_key,
                direction=SyncDirection.TO_JIRA,
                status=SyncStatus.SUCCESS,
                changes=changes,
                duration_ms=int(duration),
            )

            self._sync_history.append(result)
            return result

        except Exception as e:
            return SyncResult(
                workflow_id=workflow_id,
                jira_issue_key=state.jira_issue_key if state else "",
                direction=SyncDirection.TO_JIRA,
                status=SyncStatus.FAILED,
                error=str(e),
            )

    async def sync_from_jira(
        self,
        jira_issue_key: str,
        force: bool = False,
    ) -> SyncResult:
        """
        Pull JIRA issue changes to Maestro.

        Args:
            jira_issue_key: JIRA issue to sync from
            force: Force sync even if no changes

        Returns:
            SyncResult with sync details
        """
        start_time = datetime.utcnow()

        # Find linked workflow
        workflow_id = None
        state = None
        for wf_id, s in self._sync_states.items():
            if s.jira_issue_key == jira_issue_key and s.is_linked:
                workflow_id = wf_id
                state = s
                break

        if not state:
            return SyncResult(
                workflow_id="",
                jira_issue_key=jira_issue_key,
                direction=SyncDirection.FROM_JIRA,
                status=SyncStatus.FAILED,
                error="No workflow linked to this JIRA issue",
            )

        try:
            # Get current JIRA data
            jira_data = await self._get_jira_issue(jira_issue_key)
            jira_hash = self._compute_hash(jira_data)

            # Check for changes
            if not force and jira_hash == state.jira_hash:
                return SyncResult(
                    workflow_id=workflow_id,
                    jira_issue_key=jira_issue_key,
                    direction=SyncDirection.FROM_JIRA,
                    status=SyncStatus.SKIPPED,
                )

            # Map fields to Maestro format
            maestro_fields = self._map_from_jira(jira_data)

            # Update Maestro workflow
            changes = await self._update_maestro_workflow(
                workflow_id,
                maestro_fields,
                jira_data,
            )

            # Update sync state
            state.jira_hash = jira_hash
            state.last_sync_at = datetime.utcnow()

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = SyncResult(
                workflow_id=workflow_id,
                jira_issue_key=jira_issue_key,
                direction=SyncDirection.FROM_JIRA,
                status=SyncStatus.SUCCESS,
                changes=changes,
                duration_ms=int(duration),
            )

            self._sync_history.append(result)
            return result

        except Exception as e:
            return SyncResult(
                workflow_id=workflow_id or "",
                jira_issue_key=jira_issue_key,
                direction=SyncDirection.FROM_JIRA,
                status=SyncStatus.FAILED,
                error=str(e),
            )

    async def sync_bidirectional(
        self,
        workflow_id: str,
    ) -> SyncResult:
        """
        Perform bidirectional sync with conflict detection.

        Args:
            workflow_id: Workflow to sync

        Returns:
            SyncResult with sync details and any conflicts
        """
        start_time = datetime.utcnow()

        state = self._sync_states.get(workflow_id)
        if not state or not state.is_linked:
            return SyncResult(
                workflow_id=workflow_id,
                jira_issue_key="",
                direction=SyncDirection.BIDIRECTIONAL,
                status=SyncStatus.FAILED,
                error="Workflow not linked",
            )

        try:
            # Get both sides
            maestro_data = await self._get_maestro_workflow(workflow_id)
            jira_data = await self._get_jira_issue(state.jira_issue_key)

            maestro_hash = self._compute_hash(maestro_data)
            jira_hash = self._compute_hash(jira_data)

            # Check for changes on both sides
            maestro_changed = maestro_hash != state.maestro_hash
            jira_changed = jira_hash != state.jira_hash

            changes = []
            conflicts = []

            if maestro_changed and jira_changed:
                # Both changed - detect conflicts
                conflicts = self._detect_conflicts(maestro_data, jira_data)

                if conflicts and self.resolver:
                    # Attempt automatic resolution
                    resolved_data, unresolved = await self.resolver.resolve_all(conflicts)
                    conflicts = unresolved

                    if resolved_data:
                        # Apply resolved changes
                        await self._update_jira_issue(
                            state.jira_issue_key,
                            self._map_to_jira(resolved_data),
                            resolved_data,
                        )
                        await self._update_maestro_workflow(
                            workflow_id,
                            resolved_data,
                            jira_data,
                        )

            elif maestro_changed:
                # Only Maestro changed - push to JIRA
                jira_fields = self._map_to_jira(maestro_data)
                changes = await self._update_jira_issue(
                    state.jira_issue_key,
                    jira_fields,
                    maestro_data,
                )

            elif jira_changed:
                # Only JIRA changed - pull to Maestro
                maestro_fields = self._map_from_jira(jira_data)
                changes = await self._update_maestro_workflow(
                    workflow_id,
                    maestro_fields,
                    jira_data,
                )

            # Update sync state
            state.maestro_hash = maestro_hash
            state.jira_hash = jira_hash
            state.last_sync_at = datetime.utcnow()

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            status = SyncStatus.SUCCESS
            if conflicts:
                status = SyncStatus.CONFLICT
            elif not changes:
                status = SyncStatus.SKIPPED

            result = SyncResult(
                workflow_id=workflow_id,
                jira_issue_key=state.jira_issue_key,
                direction=SyncDirection.BIDIRECTIONAL,
                status=status,
                changes=changes,
                conflicts=conflicts,
                duration_ms=int(duration),
            )

            self._sync_history.append(result)
            return result

        except Exception as e:
            return SyncResult(
                workflow_id=workflow_id,
                jira_issue_key=state.jira_issue_key,
                direction=SyncDirection.BIDIRECTIONAL,
                status=SyncStatus.FAILED,
                error=str(e),
            )

    async def _get_maestro_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get Maestro workflow data."""
        # Implementation would fetch from database
        return {
            "id": workflow_id,
            "summary": "Sample workflow",
            "description": "Workflow description",
            "status": "in_progress",
            "assignee": "user@example.com",
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def _get_jira_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get JIRA issue data."""
        # Implementation would call JIRA API
        return {
            "key": issue_key,
            "fields": {
                "summary": "Sample issue",
                "description": "Issue description",
                "status": {"name": "In Progress"},
                "assignee": {"emailAddress": "user@example.com"},
                "updated": datetime.utcnow().isoformat(),
            }
        }

    def _map_to_jira(self, maestro_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Maestro fields to JIRA format."""
        if self.mapper:
            return self.mapper.to_jira(maestro_data)

        # Default mapping
        return {
            "summary": maestro_data.get("summary"),
            "description": maestro_data.get("description"),
        }

    def _map_from_jira(self, jira_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map JIRA fields to Maestro format."""
        if self.mapper:
            return self.mapper.from_jira(jira_data)

        # Default mapping
        fields = jira_data.get("fields", {})
        return {
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "status": fields.get("status", {}).get("name"),
        }

    async def _update_jira_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
        source_data: Dict[str, Any],
    ) -> List[FieldChange]:
        """Update JIRA issue with changes."""
        # Implementation would call JIRA API
        changes = []
        for field_name, new_value in fields.items():
            if new_value is not None:
                changes.append(FieldChange(
                    field_name=field_name,
                    old_value=None,  # Would get from JIRA
                    new_value=new_value,
                    source="maestro",
                ))
        return changes

    async def _update_maestro_workflow(
        self,
        workflow_id: str,
        fields: Dict[str, Any],
        source_data: Dict[str, Any],
    ) -> List[FieldChange]:
        """Update Maestro workflow with changes."""
        # Implementation would update database
        changes = []
        for field_name, new_value in fields.items():
            if new_value is not None:
                changes.append(FieldChange(
                    field_name=field_name,
                    old_value=None,  # Would get from DB
                    new_value=new_value,
                    source="jira",
                ))
        return changes

    def _detect_conflicts(
        self,
        maestro_data: Dict[str, Any],
        jira_data: Dict[str, Any],
    ) -> List["SyncConflict"]:
        """Detect conflicts between Maestro and JIRA data."""
        from .conflict import SyncConflict

        conflicts = []
        jira_fields = jira_data.get("fields", {})

        # Compare common fields
        field_pairs = [
            ("summary", "summary"),
            ("description", "description"),
        ]

        for maestro_field, jira_field in field_pairs:
            maestro_val = maestro_data.get(maestro_field)
            jira_val = jira_fields.get(jira_field)

            if maestro_val != jira_val and maestro_val and jira_val:
                conflicts.append(SyncConflict(
                    field_name=maestro_field,
                    maestro_value=maestro_val,
                    jira_value=jira_val,
                    detected_at=datetime.utcnow(),
                ))

        return conflicts

    def get_sync_history(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SyncResult]:
        """
        Get sync history.

        Args:
            workflow_id: Filter by workflow
            limit: Max results

        Returns:
            List of sync results
        """
        history = self._sync_history
        if workflow_id:
            history = [r for r in history if r.workflow_id == workflow_id]
        return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]

    def get_sync_state(self, workflow_id: str) -> Optional[SyncState]:
        """Get sync state for workflow."""
        return self._sync_states.get(workflow_id)
