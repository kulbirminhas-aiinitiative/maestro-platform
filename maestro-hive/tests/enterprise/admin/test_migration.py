"""Tests for migration runner module."""

import pytest
from datetime import datetime

from maestro_hive.enterprise.admin.config import AdminConfig
from maestro_hive.enterprise.admin.migration import (
    MigrationRunner,
    MigrationPlan,
    MigrationStep,
    MigrationStatus,
)


class TestMigrationStatus:
    """Tests for MigrationStatus enum."""

    def test_migration_statuses_exist(self):
        """Test all migration statuses are defined."""
        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.IN_PROGRESS.value == "in_progress"
        assert MigrationStatus.VERIFYING.value == "verifying"
        assert MigrationStatus.COMPLETED.value == "completed"
        assert MigrationStatus.FAILED.value == "failed"
        assert MigrationStatus.ROLLED_BACK.value == "rolled_back"


class TestMigrationStep:
    """Tests for MigrationStep dataclass."""

    def test_create_migration_step(self):
        """Test creating a migration step."""
        step = MigrationStep(
            step_id="step-1",
            name="Migrate repo",
            description="Migrate repository",
            source="user/repo",
            target="org/repo",
        )

        assert step.step_id == "step-1"
        assert step.source == "user/repo"
        assert step.target == "org/repo"
        assert step.status == MigrationStatus.PENDING

    def test_migration_step_to_dict(self):
        """Test converting migration step to dict."""
        step = MigrationStep(
            step_id="step-1",
            name="Migrate repo",
            description="Migrate repository",
            source="user/repo",
            target="org/repo",
            status=MigrationStatus.COMPLETED,
        )

        data = step.to_dict()

        assert data["step_id"] == "step-1"
        assert data["status"] == "completed"


class TestMigrationPlan:
    """Tests for MigrationPlan dataclass."""

    def test_create_migration_plan(self):
        """Test creating a migration plan."""
        steps = [
            MigrationStep(
                step_id="step-1",
                name="Migrate repo 1",
                description="Migrate first repo",
                source="user/repo1",
                target="org/repo1",
            ),
            MigrationStep(
                step_id="step-2",
                name="Migrate repo 2",
                description="Migrate second repo",
                source="user/repo2",
                target="org/repo2",
            ),
        ]

        plan = MigrationPlan(
            plan_id="plan-123",
            name="Test Migration",
            description="Test migration plan",
            steps=steps,
            created_at=datetime.utcnow(),
            created_by="test_user",
        )

        assert plan.plan_id == "plan-123"
        assert len(plan.steps) == 2
        assert plan.status == MigrationStatus.PENDING

    def test_get_progress_initial(self):
        """Test getting initial progress."""
        steps = [
            MigrationStep(
                step_id="step-1",
                name="Step 1",
                description="First step",
                source="a",
                target="b",
            ),
            MigrationStep(
                step_id="step-2",
                name="Step 2",
                description="Second step",
                source="c",
                target="d",
            ),
        ]

        plan = MigrationPlan(
            plan_id="plan-123",
            name="Test",
            description="Test",
            steps=steps,
            created_at=datetime.utcnow(),
            created_by="test",
        )

        progress = plan.get_progress()

        assert progress["total_steps"] == 2
        assert progress["completed"] == 0
        assert progress["pending"] == 2
        assert progress["percentage"] == 0

    def test_get_progress_partial(self):
        """Test getting partial progress."""
        steps = [
            MigrationStep(
                step_id="step-1",
                name="Step 1",
                description="First step",
                source="a",
                target="b",
                status=MigrationStatus.COMPLETED,
            ),
            MigrationStep(
                step_id="step-2",
                name="Step 2",
                description="Second step",
                source="c",
                target="d",
                status=MigrationStatus.IN_PROGRESS,
            ),
            MigrationStep(
                step_id="step-3",
                name="Step 3",
                description="Third step",
                source="e",
                target="f",
            ),
        ]

        plan = MigrationPlan(
            plan_id="plan-123",
            name="Test",
            description="Test",
            steps=steps,
            created_at=datetime.utcnow(),
            created_by="test",
        )

        progress = plan.get_progress()

        assert progress["total_steps"] == 3
        assert progress["completed"] == 1
        assert progress["in_progress"] == 1
        assert progress["pending"] == 1
        assert progress["percentage"] == pytest.approx(33.33, rel=0.1)


class TestMigrationRunner:
    """Tests for MigrationRunner class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        runner = MigrationRunner()
        assert runner.config.dry_run is True

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = AdminConfig(dry_run=True)
        runner = MigrationRunner(config)
        assert runner.config.dry_run is True

    def test_create_plan(self):
        """Test creating a migration plan."""
        runner = MigrationRunner()

        plan = runner.create_plan(
            name="Test Migration",
            description="Test migration plan",
            migrations=[
                {"source": "user/repo1", "target": "org/repo1"},
                {"source": "user/repo2", "target": "org/repo2"},
            ],
            created_by="test_user",
        )

        assert plan.name == "Test Migration"
        assert len(plan.steps) == 2
        assert plan.created_by == "test_user"
        assert plan.dry_run is True

    def test_get_plan(self):
        """Test getting a plan by ID."""
        runner = MigrationRunner()

        plan = runner.create_plan(
            name="Test",
            description="Test",
            migrations=[{"source": "a", "target": "b"}],
        )

        retrieved = runner.get_plan(plan.plan_id)
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id

    def test_get_plan_not_found(self):
        """Test getting a non-existent plan."""
        runner = MigrationRunner()
        assert runner.get_plan("nonexistent") is None

    def test_list_plans(self):
        """Test listing all plans."""
        runner = MigrationRunner()

        runner.create_plan(
            name="Plan 1",
            description="First plan",
            migrations=[{"source": "a", "target": "b"}],
        )
        runner.create_plan(
            name="Plan 2",
            description="Second plan",
            migrations=[{"source": "c", "target": "d"}],
        )

        plans = runner.list_plans()
        assert len(plans) == 2

    def test_list_plans_filtered(self):
        """Test listing plans with status filter."""
        runner = MigrationRunner()

        plan1 = runner.create_plan(
            name="Plan 1",
            description="First plan",
            migrations=[{"source": "a", "target": "b"}],
        )
        plan1.status = MigrationStatus.COMPLETED

        runner.create_plan(
            name="Plan 2",
            description="Second plan",
            migrations=[{"source": "c", "target": "d"}],
        )

        pending_plans = runner.list_plans(status=MigrationStatus.PENDING)
        assert len(pending_plans) == 1

    @pytest.mark.asyncio
    async def test_execute_plan_dry_run(self):
        """Test executing a plan in dry run mode."""
        config = AdminConfig(dry_run=True)
        runner = MigrationRunner(config)

        plan = runner.create_plan(
            name="Test Migration",
            description="Test migration",
            migrations=[
                {"source": "user/repo", "target": "org/repo"},
            ],
        )

        result = await runner.execute_plan(plan.plan_id)

        assert result.status == MigrationStatus.COMPLETED
        assert result.steps[0].status == MigrationStatus.COMPLETED
        assert result.steps[0].result is not None
        assert result.steps[0].result.dry_run is True

    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self):
        """Test executing a non-existent plan."""
        runner = MigrationRunner()

        with pytest.raises(ValueError, match="Plan not found"):
            await runner.execute_plan("nonexistent")

    def test_register_progress_callback(self):
        """Test registering a progress callback."""
        runner = MigrationRunner()
        callback_called = []

        def callback(plan):
            callback_called.append(plan.plan_id)

        runner.register_progress_callback(callback)
        assert len(runner._progress_callbacks) == 1

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """Test that progress callback is called during execution."""
        config = AdminConfig(dry_run=True)
        runner = MigrationRunner(config)
        progress_updates = []

        def callback(plan):
            progress_updates.append(plan.get_progress())

        runner.register_progress_callback(callback)

        plan = runner.create_plan(
            name="Test",
            description="Test",
            migrations=[{"source": "a", "target": "b"}],
        )

        await runner.execute_plan(plan.plan_id)

        # Should have progress updates
        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_rollback_plan(self):
        """Test rolling back a plan."""
        config = AdminConfig(dry_run=True)
        runner = MigrationRunner(config)

        plan = runner.create_plan(
            name="Test",
            description="Test",
            migrations=[{"source": "a", "target": "b"}],
        )

        # Execute first
        await runner.execute_plan(plan.plan_id)

        # Then rollback
        result = await runner.rollback_plan(plan.plan_id)

        assert result.status == MigrationStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_plan_not_found(self):
        """Test rolling back a non-existent plan."""
        runner = MigrationRunner()

        with pytest.raises(ValueError, match="Plan not found"):
            await runner.rollback_plan("nonexistent")

    def test_get_operations_history(self):
        """Test getting operations history."""
        runner = MigrationRunner()
        history = runner.get_operations_history()
        assert isinstance(history, list)
