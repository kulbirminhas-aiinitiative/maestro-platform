"""
Tests for Workflow Orchestrator (MD-2108)

Validates:
- WorkflowOrchestrator execution
- EventBus pub/sub
- Health monitoring
- Checkpoint/resume
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowConfig,
    WorkflowPhase,
    WorkflowState,
    WorkflowResult,
    PhaseResult,
    create_orchestrator
)
from orchestrator.event_bus import (
    EventBus,
    Event,
    EventType,
    WebhookConfig,
    get_event_bus,
    emit_event
)
from orchestrator.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthReport,
    AlertConfig,
    get_health_monitor,
    check_health
)


class TestEventBus:
    """Tests for EventBus"""

    def test_create_event(self):
        """Test event creation"""
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="wf-123",
            payload={'key': 'value'}
        )
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == "wf-123"
        assert event.payload['key'] == 'value'
        assert event.id is not None

    def test_event_to_dict(self):
        """Test event serialization"""
        event = Event(
            type=EventType.PHASE_COMPLETED,
            workflow_id="wf-123",
            phase="design"
        )
        d = event.to_dict()
        assert d['type'] == 'phase_completed'
        assert d['workflow_id'] == 'wf-123'
        assert d['phase'] == 'design'

    def test_event_from_dict(self):
        """Test event deserialization"""
        data = {
            'type': 'workflow_started',
            'workflow_id': 'wf-123',
            'timestamp': datetime.utcnow().isoformat()
        }
        event = Event.from_dict(data)
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == 'wf-123'

    def test_subscribe_and_emit(self):
        """Test event subscription and emission"""
        bus = EventBus(persist_events=False)
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.WORKFLOW_STARTED, handler)
        event = Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1")
        bus.emit(event)

        assert len(received) == 1
        assert received[0].workflow_id == "wf-1"

    def test_subscribe_all(self):
        """Test global event subscription"""
        bus = EventBus(persist_events=False)
        received = []

        bus.subscribe_all(lambda e: received.append(e))

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))
        bus.emit(Event(type=EventType.PHASE_COMPLETED, workflow_id="wf-1"))

        assert len(received) == 2

    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        bus = EventBus(persist_events=False)
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.WORKFLOW_STARTED, handler)
        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))

        assert bus.unsubscribe(EventType.WORKFLOW_STARTED, handler) is True
        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-2"))

        assert len(received) == 1

    def test_event_history(self):
        """Test event history"""
        bus = EventBus(persist_events=True)
        bus.clear_history()

        for i in range(5):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"wf-{i}"))

        history = bus.get_history()
        assert len(history) == 5

    def test_event_history_filtering(self):
        """Test event history filtering"""
        bus = EventBus(persist_events=True)
        bus.clear_history()

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))
        bus.emit(Event(type=EventType.WORKFLOW_COMPLETED, workflow_id="wf-1"))
        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-2"))

        history = bus.get_history(workflow_id="wf-1")
        assert len(history) == 2

        history = bus.get_history(event_type=EventType.WORKFLOW_STARTED)
        assert len(history) == 2

    def test_pause_resume(self):
        """Test pausing and resuming event processing"""
        bus = EventBus(persist_events=False)
        received = []

        bus.subscribe_all(lambda e: received.append(e))
        bus.pause()

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))
        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-2"))

        assert len(received) == 0

        count = bus.resume()
        assert count == 2
        assert len(received) == 2

    def test_get_stats(self):
        """Test getting event bus statistics"""
        bus = EventBus(persist_events=True)
        bus.clear_history()

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))
        bus.emit(Event(type=EventType.WORKFLOW_COMPLETED, workflow_id="wf-1"))

        stats = bus.get_stats()
        assert stats['total_events'] == 2
        assert 'workflow_started' in stats['event_counts']


class TestWorkflowConfig:
    """Tests for WorkflowConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = WorkflowConfig(project_id="MD")
        assert config.project_id == "MD"
        assert config.checkpoint_enabled is True
        assert config.governance_enabled is True
        assert len(config.phases) == len(WorkflowPhase)

    def test_custom_config(self):
        """Test custom configuration"""
        config = WorkflowConfig(
            project_id="MD",
            epic_id="MD-123",
            parallel_tasks=8,
            phases=[WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN]
        )
        assert config.epic_id == "MD-123"
        assert config.parallel_tasks == 8
        assert len(config.phases) == 2

    def test_config_to_dict(self):
        """Test config serialization"""
        config = WorkflowConfig(project_id="MD")
        d = config.to_dict()
        assert d['project_id'] == "MD"
        assert 'phases' in d


class TestPhaseResult:
    """Tests for PhaseResult"""

    def test_phase_result_creation(self):
        """Test phase result creation"""
        result = PhaseResult(
            phase=WorkflowPhase.DESIGN,
            status='success',
            started_at=datetime.utcnow(),
            tasks_created=['T1', 'T2']
        )
        assert result.phase == WorkflowPhase.DESIGN
        assert result.status == 'success'
        assert len(result.tasks_created) == 2

    def test_phase_result_duration(self):
        """Test duration calculation"""
        start = datetime.utcnow()
        result = PhaseResult(
            phase=WorkflowPhase.DESIGN,
            status='success',
            started_at=start,
            completed_at=start + timedelta(seconds=30)
        )
        assert result.duration_seconds == 30.0


class TestWorkflowResult:
    """Tests for WorkflowResult"""

    def test_workflow_result_success(self):
        """Test successful workflow result"""
        config = WorkflowConfig(project_id="MD")
        result = WorkflowResult(
            workflow_id="wf-123",
            state=WorkflowState.COMPLETED,
            config=config
        )
        assert result.is_success is True

    def test_workflow_result_failed(self):
        """Test failed workflow result"""
        config = WorkflowConfig(project_id="MD")
        result = WorkflowResult(
            workflow_id="wf-123",
            state=WorkflowState.FAILED,
            config=config,
            error_message="Test error"
        )
        assert result.is_success is False
        assert result.error_message == "Test error"


class TestWorkflowOrchestrator:
    """Tests for WorkflowOrchestrator"""

    def test_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = WorkflowOrchestrator()
        assert orchestrator.config.project_id == "MD"

    def test_initialization_with_config(self):
        """Test orchestrator with custom config"""
        config = WorkflowConfig(project_id="TEST", epic_id="TEST-1")
        orchestrator = WorkflowOrchestrator(config)
        assert orchestrator.config.project_id == "TEST"
        assert orchestrator.config.epic_id == "TEST-1"

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test basic workflow execution"""
        config = WorkflowConfig(
            project_id="MD",
            phases=[WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN]
        )
        orchestrator = WorkflowOrchestrator(config, event_bus=EventBus(persist_events=False))

        result = await orchestrator.execute({
            'title': 'Test Feature',
            'description': 'Test description'
        })

        assert result.state == WorkflowState.COMPLETED
        assert result.is_success is True
        assert len(result.phases) == 2

    @pytest.mark.asyncio
    async def test_execute_all_phases(self):
        """Test executing all phases"""
        config = WorkflowConfig(project_id="MD")
        orchestrator = WorkflowOrchestrator(config, event_bus=EventBus(persist_events=False))

        result = await orchestrator.execute({'title': 'Full Workflow'})

        assert result.state == WorkflowState.COMPLETED
        assert len(result.phases) == 5  # All phases except COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_events(self):
        """Test that events are emitted during execution"""
        bus = EventBus(persist_events=True)
        bus.clear_history()

        config = WorkflowConfig(
            project_id="MD",
            phases=[WorkflowPhase.REQUIREMENTS]
        )
        orchestrator = WorkflowOrchestrator(config, event_bus=bus)

        await orchestrator.execute({'title': 'Test'})

        history = bus.get_history()
        event_types = [e.type for e in history]

        assert EventType.WORKFLOW_STARTED in event_types
        assert EventType.PHASE_STARTED in event_types
        assert EventType.PHASE_COMPLETED in event_types
        assert EventType.WORKFLOW_COMPLETED in event_types

    def test_register_phase_handler(self):
        """Test registering custom phase handler"""
        orchestrator = WorkflowOrchestrator()

        custom_called = []

        def custom_handler(wf_id, config, context):
            custom_called.append(wf_id)
            return PhaseResult(
                phase=WorkflowPhase.REQUIREMENTS,
                status='success',
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

        orchestrator.register_phase_handler(WorkflowPhase.REQUIREMENTS, custom_handler)

        # Verify handler is registered
        assert WorkflowPhase.REQUIREMENTS in orchestrator._phase_handlers

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self):
        """Test checkpoint creation"""
        config = WorkflowConfig(
            project_id="MD",
            checkpoint_enabled=True,
            phases=[WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN]
        )
        orchestrator = WorkflowOrchestrator(config, event_bus=EventBus(persist_events=False))

        result = await orchestrator.execute({'title': 'Checkpoint Test'})

        assert result.state == WorkflowState.COMPLETED
        # Checkpoints should be created for each phase

    def test_pause_workflow(self):
        """Test pausing a workflow"""
        orchestrator = WorkflowOrchestrator()
        # Would need to mock an active workflow
        result = orchestrator.pause("nonexistent")
        assert result is False

    def test_cancel_workflow(self):
        """Test canceling a workflow"""
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.cancel("nonexistent")
        assert result is False

    def test_get_active_workflows(self):
        """Test getting active workflows"""
        orchestrator = WorkflowOrchestrator()
        active = orchestrator.get_active_workflows()
        assert isinstance(active, list)

    def test_factory_function(self):
        """Test create_orchestrator factory"""
        orchestrator = create_orchestrator(
            project_id="TEST",
            epic_id="TEST-1",
            parallel_tasks=8
        )
        assert orchestrator.config.project_id == "TEST"
        assert orchestrator.config.epic_id == "TEST-1"
        assert orchestrator.config.parallel_tasks == 8


class TestHealthMonitor:
    """Tests for HealthMonitor"""

    def test_initialization(self):
        """Test health monitor initialization"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        assert monitor is not None

    def test_check_health_initial(self):
        """Test initial health check"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        monitor.reset_metrics()

        report = monitor.check_health()

        assert report.status == HealthStatus.HEALTHY
        assert report.active_workflows == 0
        assert report.failure_rate == 0.0

    def test_health_after_workflow_events(self):
        """Test health after workflow events"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        monitor.reset_metrics()

        # Emit workflow started
        bus.emit(Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="wf-1"
        ))

        report = monitor.check_health()
        assert report.active_workflows == 1

        # Emit workflow completed
        bus.emit(Event(
            type=EventType.WORKFLOW_COMPLETED,
            workflow_id="wf-1"
        ))

        report = monitor.check_health()
        assert report.active_workflows == 0
        assert report.total_completed == 1

    def test_failure_rate_calculation(self):
        """Test failure rate calculation"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        monitor.reset_metrics()

        # Start and complete some workflows
        for i in range(8):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"wf-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_COMPLETED, workflow_id=f"wf-{i}"))

        # Start and fail some workflows
        for i in range(2):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"fail-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_FAILED, workflow_id=f"fail-{i}"))

        report = monitor.check_health()
        assert report.total_completed == 8
        assert report.total_failed == 2
        assert report.failure_rate == 0.2

    def test_degraded_status(self):
        """Test degraded health status"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(
            event_bus=bus,
            degraded_threshold=0.05,
            failure_threshold=0.2
        )
        monitor.reset_metrics()

        # 10 completed, 1 failed = 10% failure rate
        for i in range(10):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"wf-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_COMPLETED, workflow_id=f"wf-{i}"))

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="fail-1"))
        bus.emit(Event(type=EventType.WORKFLOW_FAILED, workflow_id="fail-1"))

        report = monitor.check_health()
        assert report.status == HealthStatus.DEGRADED

    def test_unhealthy_status(self):
        """Test unhealthy status"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(
            event_bus=bus,
            failure_threshold=0.2
        )
        monitor.reset_metrics()

        # 3 completed, 2 failed = 40% failure rate
        for i in range(3):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"wf-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_COMPLETED, workflow_id=f"wf-{i}"))

        for i in range(2):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"fail-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_FAILED, workflow_id=f"fail-{i}"))

        report = monitor.check_health()
        assert report.status == HealthStatus.UNHEALTHY

    def test_set_component_health(self):
        """Test setting component health"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)

        monitor.set_component_health('governance', HealthStatus.UNHEALTHY)

        report = monitor.check_health()
        assert report.components['governance'] == HealthStatus.UNHEALTHY

    def test_get_metrics(self):
        """Test getting detailed metrics"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        monitor.reset_metrics()

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1"))

        metrics = monitor.get_metrics()
        assert 'active_workflows' in metrics
        assert len(metrics['active_workflows']) == 1

    def test_alert_configuration(self):
        """Test alert configuration"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)

        alerts_fired = []

        def alert_handler(name, severity, data):
            alerts_fired.append(name)

        monitor.add_alert_handler(alert_handler)

        # Create high failure scenario
        monitor.reset_metrics()
        for i in range(5):
            bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id=f"fail-{i}"))
            bus.emit(Event(type=EventType.WORKFLOW_FAILED, workflow_id=f"fail-{i}"))

        report = monitor.check_health()
        assert 'high_failure_rate' in alerts_fired

    def test_get_workflow_status(self):
        """Test getting specific workflow status"""
        bus = EventBus(persist_events=False)
        monitor = HealthMonitor(event_bus=bus)
        monitor.reset_metrics()

        bus.emit(Event(type=EventType.WORKFLOW_STARTED, workflow_id="wf-test"))

        status = monitor.get_workflow_status("wf-test")
        assert status is not None
        assert status['workflow_id'] == "wf-test"

        status = monitor.get_workflow_status("nonexistent")
        assert status is None

    def test_health_report_to_dict(self):
        """Test health report serialization"""
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            active_workflows=5,
            failure_rate=0.1
        )
        d = report.to_dict()
        assert d['status'] == 'healthy'
        assert d['active_workflows'] == 5


class TestWorkflowPhase:
    """Tests for WorkflowPhase enum"""

    def test_phase_values(self):
        """Test phase enum values"""
        assert WorkflowPhase.REQUIREMENTS.value == "requirements"
        assert WorkflowPhase.DESIGN.value == "design"
        assert WorkflowPhase.IMPLEMENTATION.value == "implementation"
        assert WorkflowPhase.TESTING.value == "testing"
        assert WorkflowPhase.DEPLOYMENT.value == "deployment"


class TestWorkflowState:
    """Tests for WorkflowState enum"""

    def test_state_values(self):
        """Test state enum values"""
        assert WorkflowState.PENDING.value == "pending"
        assert WorkflowState.RUNNING.value == "running"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.FAILED.value == "failed"


class TestHealthStatus:
    """Tests for HealthStatus enum"""

    def test_status_values(self):
        """Test health status values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
