"""
Unit Tests for Handoff System
Version: 1.0.0

Comprehensive tests for phase-to-phase handoff models.
"""

import pytest
from datetime import datetime
from typing import List

from contracts.handoff.models import HandoffStatus, HandoffTask, HandoffSpec
from contracts.models import AcceptanceCriterion
from contracts.artifacts.models import Artifact, ArtifactManifest


# ============================================================================
# Test HandoffStatus Enum
# ============================================================================

class TestHandoffStatus:
    """Tests for HandoffStatus enum"""

    def test_handoff_status_values(self):
        """Test HandoffStatus enum values"""
        assert HandoffStatus.DRAFT == "DRAFT"
        assert HandoffStatus.READY == "READY"
        assert HandoffStatus.IN_PROGRESS == "IN_PROGRESS"
        assert HandoffStatus.COMPLETED == "COMPLETED"
        assert HandoffStatus.REJECTED == "REJECTED"

    def test_handoff_status_membership(self):
        """Test HandoffStatus membership checks"""
        assert "DRAFT" in [status.value for status in HandoffStatus]
        assert "READY" in [status.value for status in HandoffStatus]
        assert "INVALID" not in [status.value for status in HandoffStatus]

    def test_handoff_status_iteration(self):
        """Test iterating over HandoffStatus"""
        statuses = list(HandoffStatus)
        assert len(statuses) == 5
        assert HandoffStatus.DRAFT in statuses
        assert HandoffStatus.COMPLETED in statuses


# ============================================================================
# Test HandoffTask
# ============================================================================

class TestHandoffTask:
    """Tests for HandoffTask dataclass"""

    def test_handoff_task_creation_minimal(self):
        """Test creating HandoffTask with minimal fields"""
        task = HandoffTask(
            task_id="task-001",
            description="Implement user authentication"
        )

        assert task.task_id == "task-001"
        assert task.description == "Implement user authentication"
        assert task.assigned_to is None
        assert task.completed is False
        assert task.priority == "medium"
        assert task.dependencies == []

    def test_handoff_task_creation_full(self):
        """Test creating HandoffTask with all fields"""
        task = HandoffTask(
            task_id="task-002",
            description="Write API tests",
            assigned_to="qa-agent",
            completed=True,
            priority="high",
            dependencies=["task-001"]
        )

        assert task.task_id == "task-002"
        assert task.description == "Write API tests"
        assert task.assigned_to == "qa-agent"
        assert task.completed is True
        assert task.priority == "high"
        assert task.dependencies == ["task-001"]

    def test_handoff_task_priority_levels(self):
        """Test different priority levels"""
        priorities = ["low", "medium", "high", "critical"]

        for priority in priorities:
            task = HandoffTask(
                task_id=f"task-{priority}",
                description=f"Task with {priority} priority",
                priority=priority
            )
            assert task.priority == priority

    def test_handoff_task_multiple_dependencies(self):
        """Test task with multiple dependencies"""
        task = HandoffTask(
            task_id="task-003",
            description="Integration testing",
            dependencies=["task-001", "task-002", "task-004"]
        )

        assert len(task.dependencies) == 3
        assert "task-001" in task.dependencies
        assert "task-004" in task.dependencies

    def test_handoff_task_completion_toggle(self):
        """Test toggling task completion status"""
        task = HandoffTask(
            task_id="task-005",
            description="Code review"
        )

        assert task.completed is False

        # Mark as completed
        task.completed = True
        assert task.completed is True

        # Mark as incomplete
        task.completed = False
        assert task.completed is False

    def test_handoff_task_reassignment(self):
        """Test reassigning task to different agent"""
        task = HandoffTask(
            task_id="task-006",
            description="Bug fix",
            assigned_to="backend-dev"
        )

        assert task.assigned_to == "backend-dev"

        # Reassign
        task.assigned_to = "senior-dev"
        assert task.assigned_to == "senior-dev"

    def test_handoff_task_empty_dependencies(self):
        """Test task with explicitly empty dependencies"""
        task = HandoffTask(
            task_id="task-007",
            description="Initial setup",
            dependencies=[]
        )

        assert task.dependencies == []
        assert len(task.dependencies) == 0


# ============================================================================
# Test HandoffSpec
# ============================================================================

class TestHandoffSpec:
    """Tests for HandoffSpec dataclass"""

    def test_handoff_spec_creation_minimal(self):
        """Test creating HandoffSpec with minimal fields"""
        spec = HandoffSpec(
            handoff_id="handoff-001",
            from_phase="design",
            to_phase="development"
        )

        assert spec.handoff_id == "handoff-001"
        assert spec.from_phase == "design"
        assert spec.to_phase == "development"
        assert spec.tasks == []
        assert spec.input_artifacts is None
        assert spec.acceptance_criteria == []
        assert spec.status == HandoffStatus.DRAFT
        assert isinstance(spec.created_at, datetime)
        assert spec.completed_at is None
        assert spec.context == {}

    def test_handoff_spec_creation_full(self):
        """Test creating HandoffSpec with all fields"""
        tasks = [
            HandoffTask(
                task_id="task-001",
                description="Implement feature",
                assigned_to="dev-agent",
                priority="high"
            )
        ]

        criteria = [
            AcceptanceCriterion(
                criterion_id="ac-001",
                description="All tests pass",
                validator_type="pytest",
                validation_config={"min_coverage": 80}
            )
        ]

        manifest = ArtifactManifest(
            manifest_id="manifest-001",
            contract_id="contract-001",
            artifacts=[]
        )

        completed_time = datetime.utcnow()

        spec = HandoffSpec(
            handoff_id="handoff-002",
            from_phase="development",
            to_phase="testing",
            tasks=tasks,
            input_artifacts=manifest,
            acceptance_criteria=criteria,
            status=HandoffStatus.READY,
            completed_at=completed_time,
            context={"notes": "Ready for testing"}
        )

        assert spec.handoff_id == "handoff-002"
        assert spec.from_phase == "development"
        assert spec.to_phase == "testing"
        assert len(spec.tasks) == 1
        assert spec.input_artifacts == manifest
        assert len(spec.acceptance_criteria) == 1
        assert spec.status == HandoffStatus.READY
        assert spec.completed_at == completed_time
        assert spec.context["notes"] == "Ready for testing"

    def test_handoff_spec_status_progression(self):
        """Test handoff status progression through lifecycle"""
        spec = HandoffSpec(
            handoff_id="handoff-003",
            from_phase="design",
            to_phase="development"
        )

        # Draft -> Ready
        assert spec.status == HandoffStatus.DRAFT
        spec.status = HandoffStatus.READY
        assert spec.status == HandoffStatus.READY

        # Ready -> In Progress
        spec.status = HandoffStatus.IN_PROGRESS
        assert spec.status == HandoffStatus.IN_PROGRESS

        # In Progress -> Completed
        spec.status = HandoffStatus.COMPLETED
        spec.completed_at = datetime.utcnow()
        assert spec.status == HandoffStatus.COMPLETED
        assert spec.completed_at is not None

    def test_handoff_spec_status_rejection(self):
        """Test handoff rejection flow"""
        spec = HandoffSpec(
            handoff_id="handoff-004",
            from_phase="development",
            to_phase="testing",
            status=HandoffStatus.IN_PROGRESS
        )

        # Reject handoff
        spec.status = HandoffStatus.REJECTED
        spec.context["rejection_reason"] = "Incomplete implementation"

        assert spec.status == HandoffStatus.REJECTED
        assert spec.context["rejection_reason"] == "Incomplete implementation"

    def test_handoff_spec_multiple_tasks(self):
        """Test handoff with multiple tasks"""
        tasks = [
            HandoffTask(task_id="t1", description="Task 1", priority="high"),
            HandoffTask(task_id="t2", description="Task 2", priority="medium"),
            HandoffTask(task_id="t3", description="Task 3", priority="low")
        ]

        spec = HandoffSpec(
            handoff_id="handoff-005",
            from_phase="analysis",
            to_phase="design",
            tasks=tasks
        )

        assert len(spec.tasks) == 3
        assert spec.tasks[0].task_id == "t1"
        assert spec.tasks[1].priority == "medium"
        assert spec.tasks[2].description == "Task 3"

    def test_handoff_spec_task_dependencies(self):
        """Test handoff with tasks that have dependencies"""
        tasks = [
            HandoffTask(task_id="t1", description="Foundation", dependencies=[]),
            HandoffTask(task_id="t2", description="Feature A", dependencies=["t1"]),
            HandoffTask(task_id="t3", description="Feature B", dependencies=["t1"]),
            HandoffTask(task_id="t4", description="Integration", dependencies=["t2", "t3"])
        ]

        spec = HandoffSpec(
            handoff_id="handoff-006",
            from_phase="design",
            to_phase="implementation",
            tasks=tasks
        )

        # Check dependencies
        assert spec.tasks[0].dependencies == []
        assert spec.tasks[1].dependencies == ["t1"]
        assert spec.tasks[3].dependencies == ["t2", "t3"]

    def test_handoff_spec_task_completion_tracking(self):
        """Test tracking task completion in handoff"""
        tasks = [
            HandoffTask(task_id="t1", description="Task 1", completed=True),
            HandoffTask(task_id="t2", description="Task 2", completed=True),
            HandoffTask(task_id="t3", description="Task 3", completed=False)
        ]

        spec = HandoffSpec(
            handoff_id="handoff-007",
            from_phase="development",
            to_phase="testing",
            tasks=tasks
        )

        completed_count = sum(1 for task in spec.tasks if task.completed)
        total_count = len(spec.tasks)

        assert completed_count == 2
        assert total_count == 3
        assert completed_count / total_count == pytest.approx(0.666, 0.01)

    def test_handoff_spec_with_artifacts(self):
        """Test handoff with artifact manifest"""
        artifacts = [
            Artifact(
                artifact_id="art-001",
                path="designs/mockup.png",
                digest="abc123",
                size_bytes=1024,
                media_type="image/png",
                role="evidence"
            )
        ]

        manifest = ArtifactManifest(
            manifest_id="manifest-001",
            contract_id="contract-001",
            artifacts=artifacts
        )

        spec = HandoffSpec(
            handoff_id="handoff-008",
            from_phase="design",
            to_phase="development",
            input_artifacts=manifest
        )

        assert spec.input_artifacts is not None
        assert len(spec.input_artifacts.artifacts) == 1
        assert spec.input_artifacts.artifacts[0].artifact_id == "art-001"

    def test_handoff_spec_with_acceptance_criteria(self):
        """Test handoff with acceptance criteria"""
        criteria = [
            AcceptanceCriterion(
                criterion_id="ac-001",
                description="UI matches design",
                validator_type="screenshot_diff",
                validation_config={"threshold": 0.95}
            ),
            AcceptanceCriterion(
                criterion_id="ac-002",
                description="All tests pass",
                validator_type="pytest",
                validation_config={"min_coverage": 80}
            )
        ]

        spec = HandoffSpec(
            handoff_id="handoff-009",
            from_phase="development",
            to_phase="qa",
            acceptance_criteria=criteria
        )

        assert len(spec.acceptance_criteria) == 2
        assert spec.acceptance_criteria[0].validator_type == "screenshot_diff"
        assert spec.acceptance_criteria[1].description == "All tests pass"

    def test_handoff_spec_context_metadata(self):
        """Test handoff context for additional metadata"""
        spec = HandoffSpec(
            handoff_id="handoff-010",
            from_phase="development",
            to_phase="staging",
            context={
                "deployment_type": "blue-green",
                "rollback_strategy": "immediate",
                "monitoring_enabled": True,
                "estimated_duration_hours": 2
            }
        )

        assert spec.context["deployment_type"] == "blue-green"
        assert spec.context["rollback_strategy"] == "immediate"
        assert spec.context["monitoring_enabled"] is True
        assert spec.context["estimated_duration_hours"] == 2

    def test_handoff_spec_to_dict_minimal(self):
        """Test serializing minimal HandoffSpec to dict"""
        spec = HandoffSpec(
            handoff_id="handoff-011",
            from_phase="phase1",
            to_phase="phase2"
        )

        data = spec.to_dict()

        assert data["handoff_id"] == "handoff-011"
        assert data["from_phase"] == "phase1"
        assert data["to_phase"] == "phase2"
        assert data["tasks"] == []
        assert data["status"] == "DRAFT"
        assert "created_at" in data
        assert data["completed_at"] is None
        assert data["context"] == {}

    def test_handoff_spec_to_dict_with_tasks(self):
        """Test serializing HandoffSpec with tasks to dict"""
        tasks = [
            HandoffTask(
                task_id="t1",
                description="Task 1",
                assigned_to="agent1",
                completed=True,
                priority="high",
                dependencies=["t0"]
            )
        ]

        spec = HandoffSpec(
            handoff_id="handoff-012",
            from_phase="dev",
            to_phase="qa",
            tasks=tasks,
            status=HandoffStatus.COMPLETED
        )

        data = spec.to_dict()

        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "t1"
        assert data["tasks"][0]["description"] == "Task 1"
        assert data["tasks"][0]["assigned_to"] == "agent1"
        assert data["tasks"][0]["completed"] is True
        assert data["tasks"][0]["priority"] == "high"
        assert data["tasks"][0]["dependencies"] == ["t0"]
        assert data["status"] == "COMPLETED"

    def test_handoff_spec_to_dict_completed(self):
        """Test serializing completed HandoffSpec to dict"""
        completed_time = datetime(2024, 1, 15, 10, 30, 0)

        spec = HandoffSpec(
            handoff_id="handoff-013",
            from_phase="qa",
            to_phase="production",
            status=HandoffStatus.COMPLETED,
            completed_at=completed_time
        )

        data = spec.to_dict()

        assert data["status"] == "COMPLETED"
        assert data["completed_at"] == completed_time.isoformat()

    def test_handoff_spec_timestamps(self):
        """Test HandoffSpec timestamp handling"""
        before = datetime.utcnow()

        spec = HandoffSpec(
            handoff_id="handoff-014",
            from_phase="design",
            to_phase="dev"
        )

        after = datetime.utcnow()

        assert before <= spec.created_at <= after
        assert spec.completed_at is None

        # Complete the handoff
        completion_time = datetime.utcnow()
        spec.completed_at = completion_time
        spec.status = HandoffStatus.COMPLETED

        assert spec.completed_at == completion_time


# ============================================================================
# Integration Tests
# ============================================================================

class TestHandoffIntegration:
    """Integration tests for handoff workflow"""

    def test_complete_handoff_workflow(self):
        """Test complete handoff lifecycle from draft to completion"""
        # Create handoff in DRAFT
        spec = HandoffSpec(
            handoff_id="handoff-wf-001",
            from_phase="requirements",
            to_phase="design"
        )

        assert spec.status == HandoffStatus.DRAFT

        # Add tasks
        spec.tasks.append(
            HandoffTask(
                task_id="t1",
                description="Create wireframes",
                assigned_to="designer"
            )
        )
        spec.tasks.append(
            HandoffTask(
                task_id="t2",
                description="Define user flows",
                assigned_to="ux-designer"
            )
        )

        assert len(spec.tasks) == 2

        # Mark as READY
        spec.status = HandoffStatus.READY

        # Start work (IN_PROGRESS)
        spec.status = HandoffStatus.IN_PROGRESS

        # Complete tasks
        spec.tasks[0].completed = True
        spec.tasks[1].completed = True

        # All tasks done, mark as COMPLETED
        all_completed = all(task.completed for task in spec.tasks)
        assert all_completed is True

        spec.status = HandoffStatus.COMPLETED
        spec.completed_at = datetime.utcnow()

        assert spec.status == HandoffStatus.COMPLETED
        assert spec.completed_at is not None

    def test_handoff_with_dependent_tasks(self):
        """Test handoff with task dependency chain"""
        tasks = [
            HandoffTask(task_id="setup", description="Setup environment"),
            HandoffTask(task_id="backend", description="Backend API", dependencies=["setup"]),
            HandoffTask(task_id="frontend", description="Frontend UI", dependencies=["setup"]),
            HandoffTask(task_id="integration", description="Integration", dependencies=["backend", "frontend"])
        ]

        spec = HandoffSpec(
            handoff_id="handoff-dep-001",
            from_phase="planning",
            to_phase="implementation",
            tasks=tasks
        )

        # Verify dependency structure
        assert spec.tasks[0].dependencies == []  # setup has no deps
        assert "setup" in spec.tasks[1].dependencies  # backend depends on setup
        assert "setup" in spec.tasks[2].dependencies  # frontend depends on setup
        assert len(spec.tasks[3].dependencies) == 2  # integration depends on both

    def test_handoff_serialization_roundtrip(self):
        """Test serializing and inspecting HandoffSpec"""
        tasks = [
            HandoffTask(
                task_id="t1",
                description="Task 1",
                completed=True,
                priority="high"
            )
        ]

        original = HandoffSpec(
            handoff_id="handoff-rt-001",
            from_phase="dev",
            to_phase="qa",
            tasks=tasks,
            status=HandoffStatus.IN_PROGRESS,
            context={"version": "1.0.0"}
        )

        # Serialize
        data = original.to_dict()

        # Verify serialized data
        assert data["handoff_id"] == original.handoff_id
        assert data["from_phase"] == original.from_phase
        assert data["to_phase"] == original.to_phase
        assert len(data["tasks"]) == len(original.tasks)
        assert data["tasks"][0]["task_id"] == "t1"
        assert data["tasks"][0]["completed"] is True
        assert data["status"] == "IN_PROGRESS"
        assert data["context"]["version"] == "1.0.0"

    def test_multi_phase_handoff_chain(self):
        """Test chain of handoffs across multiple phases"""
        handoffs = [
            HandoffSpec(
                handoff_id="h1",
                from_phase="requirements",
                to_phase="design",
                status=HandoffStatus.COMPLETED,
                completed_at=datetime.utcnow()
            ),
            HandoffSpec(
                handoff_id="h2",
                from_phase="design",
                to_phase="development",
                status=HandoffStatus.COMPLETED,
                completed_at=datetime.utcnow()
            ),
            HandoffSpec(
                handoff_id="h3",
                from_phase="development",
                to_phase="testing",
                status=HandoffStatus.IN_PROGRESS
            ),
            HandoffSpec(
                handoff_id="h4",
                from_phase="testing",
                to_phase="deployment",
                status=HandoffStatus.DRAFT
            )
        ]

        # Verify chain
        assert handoffs[0].to_phase == handoffs[1].from_phase
        assert handoffs[1].to_phase == handoffs[2].from_phase
        assert handoffs[2].to_phase == handoffs[3].from_phase

        # Check completion status
        completed_handoffs = [h for h in handoffs if h.status == HandoffStatus.COMPLETED]
        assert len(completed_handoffs) == 2

        in_progress = [h for h in handoffs if h.status == HandoffStatus.IN_PROGRESS]
        assert len(in_progress) == 1

    def test_handoff_rejection_and_retry(self):
        """Test rejecting and retrying a handoff"""
        spec = HandoffSpec(
            handoff_id="handoff-retry-001",
            from_phase="development",
            to_phase="qa",
            status=HandoffStatus.READY
        )

        # Start work
        spec.status = HandoffStatus.IN_PROGRESS

        # Reject due to issues
        spec.status = HandoffStatus.REJECTED
        spec.context["rejection_reason"] = "Incomplete test coverage"
        spec.context["rejected_at"] = datetime.utcnow().isoformat()

        assert spec.status == HandoffStatus.REJECTED

        # Fix issues and reset to DRAFT for retry
        spec.status = HandoffStatus.DRAFT
        spec.context["retry_count"] = 1
        spec.context["fixes_applied"] = "Added missing unit tests"

        # Ready for retry
        spec.status = HandoffStatus.READY

        # Complete successfully
        spec.status = HandoffStatus.IN_PROGRESS
        spec.status = HandoffStatus.COMPLETED
        spec.completed_at = datetime.utcnow()

        assert spec.status == HandoffStatus.COMPLETED
        assert spec.context["retry_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
