"""
Tests for Task Management Service (MD-2120)

Tests for:
- Auto-transition tasks to Done
- Close EPIC when all tasks complete
- Add completion comments with summary
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.task_management_service import (
    TaskManagementService,
    ClosureResult,
    EpicClosureResult,
    ClosureReason,
    get_task_management_service,
    reset_task_management_service
)
from services.integration.interfaces import (
    TaskStatus,
    TaskType,
    TaskData,
    AdapterResult
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_adapter():
    """Create a mock JiraAdapter"""
    adapter = AsyncMock()
    adapter.adapter_name = "jira"
    return adapter


@pytest.fixture
def service(mock_adapter):
    """Create a TaskManagementService with mock adapter"""
    return TaskManagementService(jira_adapter=mock_adapter)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test"""
    reset_task_management_service()
    yield
    reset_task_management_service()


def create_task_data(
    task_id: str,
    status: TaskStatus = TaskStatus.IN_PROGRESS,
    task_type: TaskType = TaskType.TASK,
    title: str = "Test Task"
) -> TaskData:
    """Helper to create TaskData objects"""
    return TaskData(
        id=f"jira-{task_id}",
        external_id=task_id,
        title=title,
        description="Test description",
        type=task_type,
        status=status
    )


# =============================================================================
# Test ClosureResult
# =============================================================================

class TestClosureResult:
    """Tests for ClosureResult dataclass"""

    def test_creation(self):
        """Test ClosureResult creation"""
        result = ClosureResult(
            task_id="MD-123",
            success=True,
            previous_status="in_progress",
            new_status="done",
            reason=ClosureReason.COMPLETED
        )
        assert result.task_id == "MD-123"
        assert result.success is True
        assert result.reason == ClosureReason.COMPLETED

    def test_to_dict(self):
        """Test serialization"""
        result = ClosureResult(
            task_id="MD-123",
            success=True,
            reason=ClosureReason.COMPLETED
        )
        data = result.to_dict()
        assert data['task_id'] == "MD-123"
        assert data['success'] is True
        assert data['reason'] == "completed"

    def test_failed_result(self):
        """Test failed result"""
        result = ClosureResult(
            task_id="MD-123",
            success=False,
            error="Transition failed"
        )
        assert result.success is False
        assert result.error == "Transition failed"


class TestEpicClosureResult:
    """Tests for EpicClosureResult dataclass"""

    def test_creation(self):
        """Test EpicClosureResult creation"""
        result = EpicClosureResult(
            epic_id="MD-100",
            success=True,
            total_children=5,
            children_done=5,
            children_pending=0
        )
        assert result.epic_id == "MD-100"
        assert result.total_children == 5
        assert result.children_pending == 0

    def test_to_dict(self):
        """Test serialization"""
        result = EpicClosureResult(
            epic_id="MD-100",
            success=False,
            total_children=5,
            children_done=3,
            children_pending=2,
            pending_task_ids=["MD-101", "MD-102"]
        )
        data = result.to_dict()
        assert data['epic_id'] == "MD-100"
        assert data['children_pending'] == 2
        assert len(data['pending_task_ids']) == 2


class TestClosureReason:
    """Tests for ClosureReason enum"""

    def test_values(self):
        """Test enum values"""
        assert ClosureReason.COMPLETED.value == "completed"
        assert ClosureReason.ALL_CHILDREN_DONE.value == "all_children_done"
        assert ClosureReason.MANUAL.value == "manual"
        assert ClosureReason.WORKFLOW_COMPLETE.value == "workflow_complete"


# =============================================================================
# Test TaskManagementService.complete_task
# =============================================================================

class TestCompleteTask:
    """Tests for complete_task method"""

    @pytest.mark.asyncio
    async def test_complete_task_success(self, service, mock_adapter):
        """Test successful task completion"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)
        completed_task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_task)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.complete_task("MD-123")

        assert result.success is True
        assert result.previous_status == "in_progress"
        assert result.new_status == "done"
        assert result.comment_added is True
        mock_adapter.transition_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_task_already_done(self, service, mock_adapter):
        """Test completing task that's already done"""
        task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)

        result = await service.complete_task("MD-123")

        assert result.success is True
        assert result.previous_status == "done"
        mock_adapter.transition_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_task_get_fails(self, service, mock_adapter):
        """Test handling get_task failure"""
        mock_adapter.get_task.return_value = AdapterResult(
            success=False,
            error="Task not found"
        )

        result = await service.complete_task("MD-123")

        assert result.success is False
        assert "Failed to get task" in result.error

    @pytest.mark.asyncio
    async def test_complete_task_transition_fails(self, service, mock_adapter):
        """Test handling transition failure"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(
            success=False,
            error="Invalid transition"
        )

        result = await service.complete_task("MD-123")

        assert result.success is False
        assert "Failed to transition" in result.error

    @pytest.mark.asyncio
    async def test_complete_task_with_summary(self, service, mock_adapter):
        """Test task completion with summary"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)
        completed_task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_task)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.complete_task(
            "MD-123",
            summary="Implementation complete with 100% test coverage"
        )

        assert result.success is True
        # Verify comment was added with summary
        call_args = mock_adapter.add_comment.call_args
        comment = call_args[0][1]
        assert "Implementation complete" in comment

    @pytest.mark.asyncio
    async def test_complete_task_no_comment(self, service, mock_adapter):
        """Test task completion without comment"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)
        completed_task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_task)

        result = await service.complete_task("MD-123", add_comment=False)

        assert result.success is True
        assert result.comment_added is False
        mock_adapter.add_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_task_custom_reason(self, service, mock_adapter):
        """Test task completion with custom reason"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)
        completed_task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_task)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.complete_task(
            "MD-123",
            reason=ClosureReason.WORKFLOW_COMPLETE
        )

        assert result.success is True
        assert result.reason == ClosureReason.WORKFLOW_COMPLETE


# =============================================================================
# Test TaskManagementService.check_and_close_epic
# =============================================================================

class TestCheckAndCloseEpic:
    """Tests for check_and_close_epic method"""

    @pytest.mark.asyncio
    async def test_close_epic_all_done(self, service, mock_adapter):
        """Test closing epic when all children are done"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.DONE),
            create_task_data("MD-103", status=TaskStatus.DONE)
        ]
        completed_epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_epic)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.check_and_close_epic("MD-100")

        assert result.success is True
        assert result.total_children == 3
        assert result.children_done == 3
        assert result.children_pending == 0
        assert result.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_epic_pending_children(self, service, mock_adapter):
        """Test epic not closed when children pending"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.IN_PROGRESS),
            create_task_data("MD-103", status=TaskStatus.TODO)
        ]

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)

        result = await service.check_and_close_epic("MD-100")

        assert result.success is False
        assert result.children_pending == 2
        assert "MD-102" in result.pending_task_ids
        assert "MD-103" in result.pending_task_ids

    @pytest.mark.asyncio
    async def test_close_epic_force(self, service, mock_adapter):
        """Test force closing epic with pending children"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.TODO)
        ]
        completed_epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_epic)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.check_and_close_epic("MD-100", force=True)

        assert result.success is True
        mock_adapter.transition_task.assert_called()

    @pytest.mark.asyncio
    async def test_close_epic_already_done(self, service, mock_adapter):
        """Test epic already done"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.DONE)
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE)
        ]

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)

        result = await service.check_and_close_epic("MD-100")

        assert result.success is True
        mock_adapter.transition_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_epic_no_children(self, service, mock_adapter):
        """Test closing epic with no children"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)
        completed_epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=[])
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=completed_epic)
        mock_adapter.add_comment.return_value = AdapterResult(success=True)

        result = await service.check_and_close_epic("MD-100")

        assert result.success is True
        assert result.total_children == 0


# =============================================================================
# Test TaskManagementService.complete_workflow
# =============================================================================

class TestCompleteWorkflow:
    """Tests for complete_workflow method"""

    @pytest.mark.asyncio
    async def test_complete_workflow_success(self, service, mock_adapter):
        """Test completing entire workflow"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)
        task1 = create_task_data("MD-101", status=TaskStatus.IN_PROGRESS)
        task2 = create_task_data("MD-102", status=TaskStatus.IN_PROGRESS)
        completed_task1 = create_task_data("MD-101", status=TaskStatus.DONE)
        completed_task2 = create_task_data("MD-102", status=TaskStatus.DONE)
        completed_epic = create_task_data("MD-100", status=TaskStatus.DONE, task_type=TaskType.EPIC)

        # Need to provide enough returns: task1, task2, epic (for check_and_close_epic), epic (for complete_task inside close)
        mock_adapter.get_task.side_effect = [
            AdapterResult(success=True, data=task1),
            AdapterResult(success=True, data=task2),
            AdapterResult(success=True, data=epic),
            AdapterResult(success=True, data=epic)
        ]
        mock_adapter.transition_task.side_effect = [
            AdapterResult(success=True, data=completed_task1),
            AdapterResult(success=True, data=completed_task2),
            AdapterResult(success=True, data=completed_epic)
        ]
        mock_adapter.add_comment.return_value = AdapterResult(success=True)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=[
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.DONE)
        ])

        result = await service.complete_workflow(
            epic_id="MD-100",
            task_ids=["MD-101", "MD-102"],
            summary="Workflow completed"
        )

        assert result['success'] is True
        assert len(result['tasks']) == 2
        assert result['epic_result'] is not None

    @pytest.mark.asyncio
    async def test_complete_workflow_partial_failure(self, service, mock_adapter):
        """Test workflow with partial task failures"""
        task1 = create_task_data("MD-101", status=TaskStatus.IN_PROGRESS)
        task2 = create_task_data("MD-102", status=TaskStatus.IN_PROGRESS)
        completed_task = create_task_data("MD-101", status=TaskStatus.DONE)
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, status=TaskStatus.IN_PROGRESS)

        mock_adapter.get_task.side_effect = [
            AdapterResult(success=True, data=task1),
            AdapterResult(success=True, data=task2),
            AdapterResult(success=True, data=epic)
        ]
        mock_adapter.transition_task.side_effect = [
            AdapterResult(success=True, data=completed_task),
            AdapterResult(success=False, error="Transition blocked")
        ]
        mock_adapter.add_comment.return_value = AdapterResult(success=True)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=[
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.IN_PROGRESS)
        ])

        result = await service.complete_workflow(
            epic_id="MD-100",
            task_ids=["MD-101", "MD-102"]
        )

        assert result['success'] is False
        assert len(result['tasks']) == 2


# =============================================================================
# Test TaskManagementService.get_epic_completion_status
# =============================================================================

class TestGetEpicCompletionStatus:
    """Tests for get_epic_completion_status method"""

    @pytest.mark.asyncio
    async def test_get_status_mixed(self, service, mock_adapter):
        """Test getting status with mixed task states"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC, title="Test Epic")
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.DONE),
            create_task_data("MD-103", status=TaskStatus.IN_PROGRESS),
            create_task_data("MD-104", status=TaskStatus.TODO),
            create_task_data("MD-105", status=TaskStatus.BLOCKED)
        ]

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)

        result = await service.get_epic_completion_status("MD-100")

        assert result['epic_id'] == "MD-100"
        assert result['total_children'] == 5
        assert result['done'] == 2
        assert result['in_progress'] == 1
        assert result['todo'] == 1
        assert result['blocked'] == 1
        assert result['completion_percentage'] == 40.0
        assert result['ready_to_close'] is False

    @pytest.mark.asyncio
    async def test_get_status_all_done(self, service, mock_adapter):
        """Test status when all tasks done"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC)
        children = [
            create_task_data("MD-101", status=TaskStatus.DONE),
            create_task_data("MD-102", status=TaskStatus.DONE)
        ]

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=children)

        result = await service.get_epic_completion_status("MD-100")

        assert result['completion_percentage'] == 100.0
        assert result['ready_to_close'] is True

    @pytest.mark.asyncio
    async def test_get_status_no_children(self, service, mock_adapter):
        """Test status with no children"""
        epic = create_task_data("MD-100", task_type=TaskType.EPIC)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=epic)
        mock_adapter.get_epic_children.return_value = AdapterResult(success=True, data=[])

        result = await service.get_epic_completion_status("MD-100")

        assert result['total_children'] == 0
        assert result['completion_percentage'] == 100.0
        assert result['ready_to_close'] is True


# =============================================================================
# Test Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_service(self):
        """Test singleton getter"""
        service1 = get_task_management_service()
        service2 = get_task_management_service()
        assert service1 is service2

    def test_reset_service(self):
        """Test singleton reset"""
        service1 = get_task_management_service()
        reset_task_management_service()
        service2 = get_task_management_service()
        assert service1 is not service2


# =============================================================================
# Test Comment Building
# =============================================================================

class TestCommentBuilding:
    """Tests for _build_completion_comment"""

    def test_basic_comment(self, service):
        """Test basic comment generation"""
        comment = service._build_completion_comment(
            task_id="MD-123",
            reason=ClosureReason.COMPLETED
        )
        assert "completed" in comment
        assert "TaskManagementService" in comment

    def test_comment_with_summary(self, service):
        """Test comment with summary"""
        comment = service._build_completion_comment(
            task_id="MD-123",
            reason=ClosureReason.WORKFLOW_COMPLETE,
            summary="All tests passed with 100% coverage"
        )
        assert "Summary:" in comment
        assert "All tests passed" in comment
        assert "workflow_complete" in comment


# =============================================================================
# Test create_epic_from_workflow (MD-2117)
# =============================================================================

class TestCreateEpicFromWorkflow:
    """Tests for create_epic_from_workflow method"""

    @pytest.mark.asyncio
    async def test_create_epic_success(self, service, mock_adapter):
        """Test successful epic creation from workflow"""
        epic = create_task_data("MD-200", task_type=TaskType.EPIC)

        mock_adapter.create_epic.return_value = AdapterResult(success=True, data=epic)

        result = await service.create_epic_from_workflow(
            workflow_name="User Authentication Flow",
            workflow_description="Implement user authentication workflow"
        )

        assert result.success is True
        mock_adapter.create_epic.assert_called_once()
        call_args = mock_adapter.create_epic.call_args
        assert "[EPIC] User Authentication Flow" in call_args.kwargs.get('title', call_args[1].get('title', ''))

    @pytest.mark.asyncio
    async def test_create_epic_with_labels(self, service, mock_adapter):
        """Test epic creation with labels"""
        epic = create_task_data("MD-200", task_type=TaskType.EPIC)

        mock_adapter.create_epic.return_value = AdapterResult(success=True, data=epic)

        result = await service.create_epic_from_workflow(
            workflow_name="Test Workflow",
            workflow_description="Description",
            labels=["phase-1", "sprint-5"]
        )

        assert result.success is True
        call_args = mock_adapter.create_epic.call_args
        assert call_args.kwargs.get('labels') == ["phase-1", "sprint-5"]

    @pytest.mark.asyncio
    async def test_create_epic_failure(self, service, mock_adapter):
        """Test epic creation failure"""
        mock_adapter.create_epic.return_value = AdapterResult(
            success=False,
            error="Project not found"
        )

        result = await service.create_epic_from_workflow(
            workflow_name="Test Workflow",
            workflow_description="Description"
        )

        assert result.success is False
        assert result.error == "Project not found"


# =============================================================================
# Test create_tasks_from_manifest (MD-2117)
# =============================================================================

class TestCreateTasksFromManifest:
    """Tests for create_tasks_from_manifest method"""

    @pytest.mark.asyncio
    async def test_create_tasks_success(self, service, mock_adapter):
        """Test successful task creation from manifest"""
        task1 = create_task_data("MD-301")
        task2 = create_task_data("MD-302")

        mock_adapter.create_task.side_effect = [
            AdapterResult(success=True, data=task1),
            AdapterResult(success=True, data=task2)
        ]

        manifest = [
            {"title": "Task 1", "description": "First task", "type": "task"},
            {"title": "Task 2", "description": "Second task", "type": "story", "priority": "high"}
        ]

        result = await service.create_tasks_from_manifest(
            manifest=manifest,
            epic_id="MD-200"
        )

        assert result['success_count'] == 2
        assert result['error_count'] == 0
        assert len(result['created']) == 2

    @pytest.mark.asyncio
    async def test_create_tasks_partial_failure(self, service, mock_adapter):
        """Test manifest with partial failures"""
        task1 = create_task_data("MD-301")

        mock_adapter.create_task.side_effect = [
            AdapterResult(success=True, data=task1),
            AdapterResult(success=False, error="Invalid type")
        ]

        manifest = [
            {"title": "Task 1", "type": "task"},
            {"title": "Task 2", "type": "invalid"}
        ]

        result = await service.create_tasks_from_manifest(
            manifest=manifest,
            epic_id="MD-200"
        )

        assert result['success_count'] == 1
        assert result['error_count'] == 1
        assert len(result['failed']) == 1

    @pytest.mark.asyncio
    async def test_create_tasks_empty_manifest(self, service, mock_adapter):
        """Test with empty manifest"""
        result = await service.create_tasks_from_manifest(
            manifest=[],
            epic_id="MD-200"
        )

        assert result['total'] == 0
        assert result['success_count'] == 0
        mock_adapter.create_task.assert_not_called()


# =============================================================================
# Test sync_task_status (MD-2117)
# =============================================================================

class TestSyncTaskStatus:
    """Tests for sync_task_status method"""

    @pytest.mark.asyncio
    async def test_sync_status_success(self, service, mock_adapter):
        """Test successful status sync"""
        task = create_task_data("MD-123", status=TaskStatus.TODO)
        updated_task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=updated_task)

        result = await service.sync_task_status(
            task_id="MD-123",
            external_status="running",
            source="workflow-engine"
        )

        assert result['synced'] is True
        assert result['previous_status'] == "todo"
        assert result['new_status'] == "in_progress"

    @pytest.mark.asyncio
    async def test_sync_status_already_synced(self, service, mock_adapter):
        """Test sync when status already matches"""
        task = create_task_data("MD-123", status=TaskStatus.IN_PROGRESS)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)

        result = await service.sync_task_status(
            task_id="MD-123",
            external_status="running"
        )

        assert result['synced'] is True
        mock_adapter.transition_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_status_unknown_status(self, service, mock_adapter):
        """Test sync with unknown external status"""
        task = create_task_data("MD-123", status=TaskStatus.TODO)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)

        result = await service.sync_task_status(
            task_id="MD-123",
            external_status="unknown_status"
        )

        assert result['synced'] is False
        assert "Unknown external status" in result['error']

    @pytest.mark.asyncio
    async def test_sync_status_mapping(self, service, mock_adapter):
        """Test various status mappings"""
        task = create_task_data("MD-123", status=TaskStatus.TODO)
        updated_task = create_task_data("MD-123", status=TaskStatus.DONE)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(success=True, data=updated_task)

        # Test 'completed' maps to DONE
        result = await service.sync_task_status("MD-123", "completed")
        assert result['new_status'] == "done"

        # Reset
        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)

        # Test 'success' maps to DONE
        result = await service.sync_task_status("MD-123", "success")
        assert result['new_status'] == "done"

    @pytest.mark.asyncio
    async def test_sync_status_transition_failure(self, service, mock_adapter):
        """Test handling transition failure"""
        task = create_task_data("MD-123", status=TaskStatus.TODO)

        mock_adapter.get_task.return_value = AdapterResult(success=True, data=task)
        mock_adapter.transition_task.return_value = AdapterResult(
            success=False,
            error="Invalid transition"
        )

        result = await service.sync_task_status("MD-123", "running")

        assert result['synced'] is False
        assert "Failed to transition" in result['error']
