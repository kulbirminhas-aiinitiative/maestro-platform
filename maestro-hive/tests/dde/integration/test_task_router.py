"""
DDE Integration Tests: Task Router (JIT Assignment)
Test IDs: DDE-401 to DDE-430 (30 tests)

Tests for just-in-time task assignment:
- Assign task to best available agent
- Top 3 candidate fallback strategy
- Task queueing when all agents busy
- FIFO queue ordering
- WIP limit enforcement (max 3 tasks per agent)
- Task timeout and reassignment
- Task priority scheduling
- Concurrent task assignments
- Queue backpressure alerts

These tests ensure the system can:
1. Route tasks to optimal agents in real-time
2. Handle fallback scenarios gracefully
3. Queue tasks when capacity is exhausted
4. Enforce WIP limits to prevent overload
5. Scale to handle concurrent assignments
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Task to be assigned"""
    task_id: str
    node_id: str
    required_capability: str
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    timeout_seconds: int = 300
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Assignment:
    """Task assignment record"""
    task_id: str
    agent_id: str
    assigned_at: datetime
    capability: str


class NoAgentAvailableError(Exception):
    """No agent available for task"""
    pass


class TaskQueuedError(Exception):
    """Task queued for later processing"""
    pass


class WIPLimitExceededError(Exception):
    """Agent has reached WIP limit"""
    pass


class TaskQueue:
    """FIFO queue for tasks waiting for agents"""

    def __init__(self):
        self._queues: Dict[str, deque] = {}  # capability -> queue
        self._task_index: Dict[str, str] = {}  # task_id -> capability

    def enqueue(self, task: Task, capability: str):
        """Add task to queue for specific capability"""
        if capability not in self._queues:
            self._queues[capability] = deque()

        self._queues[capability].append(task)
        self._task_index[task.task_id] = capability
        task.status = TaskStatus.QUEUED

    def dequeue(self, capability: str) -> Optional[Task]:
        """Remove and return next task from queue (FIFO)"""
        if capability not in self._queues or not self._queues[capability]:
            return None

        task = self._queues[capability].popleft()
        if task.task_id in self._task_index:
            del self._task_index[task.task_id]

        return task

    def peek(self, capability: str) -> Optional[Task]:
        """Peek at next task without removing"""
        if capability not in self._queues or not self._queues[capability]:
            return None
        return self._queues[capability][0]

    def size(self, capability: Optional[str] = None) -> int:
        """Get queue size (total or for specific capability)"""
        if capability:
            return len(self._queues.get(capability, []))
        return sum(len(q) for q in self._queues.values())

    def get_all_tasks(self, capability: Optional[str] = None) -> List[Task]:
        """Get all queued tasks"""
        if capability:
            return list(self._queues.get(capability, []))

        all_tasks = []
        for queue in self._queues.values():
            all_tasks.extend(queue)
        return all_tasks

    def clear(self):
        """Clear all queues"""
        self._queues.clear()
        self._task_index.clear()


class TaskRouter:
    """
    Routes tasks to agents using JIT assignment strategy.

    Strategy:
    1. Match task capability to agents
    2. Try assigning to top 3 candidates
    3. If all busy, queue task
    4. Enforce WIP limits
    """

    def __init__(self, capability_matcher, registry):
        self.matcher = capability_matcher
        self.registry = registry
        self.queue = TaskQueue()
        self.assignments: Dict[str, Assignment] = {}  # task_id -> assignment
        self.agent_assignments: Dict[str, List[str]] = {}  # agent_id -> [task_ids]
        self.backpressure_threshold = 10  # Queue size threshold

    async def assign_task(
        self,
        task: Task,
        max_candidates: int = 3
    ) -> str:
        """
        Assign task to best available agent.

        Returns agent_id or raises error if assignment failed.
        """
        # Match capabilities
        candidates = await self.matcher.match(
            [task.required_capability],
            min_proficiency=3
        )

        if not candidates:
            # No agents with required capability
            await self._enqueue_task(task)
            raise NoAgentAvailableError(
                f"No agent available for {task.required_capability}"
            )

        # Try top N candidates
        for i, candidate in enumerate(candidates[:max_candidates]):
            agent_id = candidate.agent_id

            try:
                # Check WIP limit
                if not self._can_assign(agent_id):
                    continue

                # Assign task
                await self._assign(task, agent_id)
                return agent_id

            except WIPLimitExceededError:
                continue

        # All candidates busy - queue task
        await self._enqueue_task(task)
        raise TaskQueuedError(
            f"All agents busy, task queued for {task.required_capability}"
        )

    async def _assign(self, task: Task, agent_id: str):
        """Perform task assignment"""
        agent = self.registry.get_agent(agent_id)

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Check WIP limit
        if agent.current_wip >= agent.wip_limit:
            raise WIPLimitExceededError(
                f"Agent {agent_id} at WIP limit ({agent.wip_limit})"
            )

        # Create assignment
        assignment = Assignment(
            task_id=task.task_id,
            agent_id=agent_id,
            assigned_at=datetime.now(),
            capability=task.required_capability
        )

        # Update state
        self.assignments[task.task_id] = assignment
        task.assigned_agent = agent_id
        task.status = TaskStatus.ASSIGNED

        # Track agent assignments
        if agent_id not in self.agent_assignments:
            self.agent_assignments[agent_id] = []
        self.agent_assignments[agent_id].append(task.task_id)

        # Increment WIP
        self.registry.increment_wip(agent_id)

    async def _enqueue_task(self, task: Task):
        """Add task to queue"""
        self.queue.enqueue(task, task.required_capability)

        # Check backpressure
        if self.queue.size() >= self.backpressure_threshold:
            # Alert condition - could emit metrics/alerts here
            pass

    def _can_assign(self, agent_id: str) -> bool:
        """Check if agent can accept more tasks"""
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return False

        return agent.current_wip < agent.wip_limit

    async def complete_task(self, task_id: str):
        """Mark task as complete and free up agent capacity"""
        if task_id not in self.assignments:
            return

        assignment = self.assignments[task_id]
        agent_id = assignment.agent_id

        # Decrement WIP
        self.registry.decrement_wip(agent_id)

        # Remove from agent assignments
        if agent_id in self.agent_assignments:
            if task_id in self.agent_assignments[agent_id]:
                self.agent_assignments[agent_id].remove(task_id)

        # Try to assign queued task
        await self._process_queue(assignment.capability)

    async def _process_queue(self, capability: str):
        """Process queued tasks for capability"""
        while self.queue.size(capability) > 0:
            task = self.queue.peek(capability)
            if not task:
                break

            try:
                # Try to assign
                await self.assign_task(task)
                # Remove from queue on success
                self.queue.dequeue(capability)
            except (NoAgentAvailableError, TaskQueuedError):
                # Still no capacity, stop processing
                break

    async def reassign_task(self, task_id: str, exclude_agent: Optional[str] = None) -> str:
        """Reassign task to different agent"""
        if task_id not in self.assignments:
            raise ValueError(f"Task {task_id} not assigned")

        old_assignment = self.assignments[task_id]
        old_agent_id = old_assignment.agent_id
        capability = old_assignment.capability

        # Remove old assignment first
        del self.assignments[task_id]

        # Free up old agent
        self.registry.decrement_wip(old_agent_id)
        if old_agent_id in self.agent_assignments:
            if task_id in self.agent_assignments[old_agent_id]:
                self.agent_assignments[old_agent_id].remove(task_id)

        # Get candidates excluding old agent
        candidates = await self.matcher.match(
            [capability],
            min_proficiency=3
        )

        # Filter out old agent if not specified as exclude
        exclude = exclude_agent if exclude_agent else old_agent_id
        candidates = [c for c in candidates if c.agent_id != exclude]

        if not candidates:
            raise NoAgentAvailableError(
                f"No other agent available for {capability}"
            )

        # Try to assign to best available new agent
        for candidate in candidates[:3]:
            agent_id = candidate.agent_id
            try:
                if self._can_assign(agent_id):
                    task = Task(
                        task_id=task_id,
                        node_id="",
                        required_capability=capability,
                        status=TaskStatus.PENDING
                    )
                    await self._assign(task, agent_id)
                    return agent_id
            except WIPLimitExceededError:
                continue

        raise TaskQueuedError("All other agents at capacity")

    def get_agent_tasks(self, agent_id: str) -> List[str]:
        """Get all tasks assigned to agent"""
        return self.agent_assignments.get(agent_id, [])

    def get_queue_depth(self, capability: Optional[str] = None) -> int:
        """Get queue depth"""
        return self.queue.size(capability)

    def is_backpressure_active(self) -> bool:
        """Check if backpressure threshold exceeded"""
        return self.queue.size() >= self.backpressure_threshold


# Import matcher from previous test file
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from test_capability_matcher import (
    AgentProfile,
    AgentCapability,
    AgentStatus,
    CapabilityRegistry,
    CapabilityMatcher
)


@pytest.mark.integration
@pytest.mark.dde
class TestBasicAssignment:
    """Test suite for basic task assignment"""

    @pytest.fixture
    def registry(self):
        """Create fresh registry"""
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        """Create matcher"""
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        """Create router"""
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_401_assign_task_to_best_agent(self, router, registry):
        """DDE-401: Assign task to best available agent"""
        # Register agent
        agent = AgentProfile(
            agent_id="agent-1",
            name="React Dev",
            status=AgentStatus.AVAILABLE
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=4)
        )

        # Create task
        task = Task(
            task_id="task-1",
            node_id="FE.Login",
            required_capability="Web:React"
        )

        # Assign
        agent_id = await router.assign_task(task)

        assert agent_id == "agent-1"
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_agent == "agent-1"

    @pytest.mark.asyncio
    async def test_dde_402_assignment_increments_wip(self, router, registry):
        """DDE-402: Assignment increments agent WIP"""
        agent = AgentProfile(agent_id="agent-1", name="Dev")
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        assert agent.current_wip == 0

        await router.assign_task(task)

        assert registry.get_agent("agent-1").current_wip == 1

    @pytest.mark.asyncio
    async def test_dde_403_no_agent_available_raises_error(self, router, registry):
        """DDE-403: No agent available raises NoAgentAvailableError"""
        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        with pytest.raises(NoAgentAvailableError):
            await router.assign_task(task)

    @pytest.mark.asyncio
    async def test_dde_404_assignment_tracked_in_registry(self, router, registry):
        """DDE-404: Assignment is tracked in router"""
        agent = AgentProfile(agent_id="agent-1", name="Dev")
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        await router.assign_task(task)

        assert "task-1" in router.assignments
        assert router.assignments["task-1"].agent_id == "agent-1"


@pytest.mark.integration
@pytest.mark.dde
class TestFallbackStrategy:
    """Test suite for top-3 fallback strategy"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_405_try_top_3_candidates(self, router, registry):
        """DDE-405: Router tries top 3 candidates before queueing"""
        # Register 3 agents, all at WIP limit
        for i in range(3):
            agent = AgentProfile(
                agent_id=f"agent-{i}",
                name=f"Dev {i}",
                current_wip=3,
                wip_limit=3,
                quality_score=0.8 - (i * 0.1)
            )
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=4
                )
            )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        # Should try all 3, then queue
        with pytest.raises(TaskQueuedError):
            await router.assign_task(task)

        assert task.status == TaskStatus.QUEUED

    @pytest.mark.asyncio
    async def test_dde_406_fallback_to_second_candidate(self, router, registry):
        """DDE-406: Falls back to second candidate if first busy"""
        # Agent 1: At limit
        agent1 = AgentProfile(
            agent_id="agent-1",
            name="Busy Dev",
            current_wip=3,
            wip_limit=3,
            quality_score=0.9
        )
        registry.register_agent(agent1)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=5)
        )

        # Agent 2: Available
        agent2 = AgentProfile(
            agent_id="agent-2",
            name="Available Dev",
            current_wip=0,
            wip_limit=3,
            quality_score=0.8
        )
        registry.register_agent(agent2)
        registry.add_capability(
            AgentCapability(agent_id="agent-2", skill_id="Web:React", proficiency=4)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        agent_id = await router.assign_task(task)

        # Should assign to agent-2 (agent-1 at limit)
        assert agent_id == "agent-2"

    @pytest.mark.asyncio
    async def test_dde_407_fallback_to_third_candidate(self, router, registry):
        """DDE-407: Falls back to third candidate if first two busy"""
        # Agents 1 & 2: At limit
        for i in range(2):
            agent = AgentProfile(
                agent_id=f"agent-{i}",
                name=f"Busy Dev {i}",
                current_wip=3,
                wip_limit=3,
                quality_score=0.9 - (i * 0.05)
            )
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=5
                )
            )

        # Agent 3: Available
        agent3 = AgentProfile(
            agent_id="agent-3",
            name="Available Dev",
            current_wip=0,
            wip_limit=3,
            quality_score=0.7
        )
        registry.register_agent(agent3)
        registry.add_capability(
            AgentCapability(agent_id="agent-3", skill_id="Web:React", proficiency=4)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        agent_id = await router.assign_task(task)

        assert agent_id == "agent-3"


@pytest.mark.integration
@pytest.mark.dde
class TestTaskQueueing:
    """Test suite for task queueing"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_408_task_queued_when_all_busy(self, router, registry):
        """DDE-408: Task queued when all agents busy"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        with pytest.raises(TaskQueuedError):
            await router.assign_task(task)

        assert router.get_queue_depth() == 1
        assert task.status == TaskStatus.QUEUED

    @pytest.mark.asyncio
    async def test_dde_409_fifo_queue_ordering(self, router, registry):
        """DDE-409: Queue maintains FIFO ordering"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue 3 tasks
        tasks = []
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            tasks.append(task)

            with pytest.raises(TaskQueuedError):
                await router.assign_task(task)

        # Check FIFO order
        queued_tasks = router.queue.get_all_tasks("Web:React")
        assert len(queued_tasks) == 3
        assert queued_tasks[0].task_id == "task-0"
        assert queued_tasks[1].task_id == "task-1"
        assert queued_tasks[2].task_id == "task-2"

    @pytest.mark.asyncio
    async def test_dde_410_queue_per_capability(self, router, registry):
        """DDE-410: Separate queues per capability"""
        agent = AgentProfile(agent_id="agent-1", name="Dev", current_wip=3, wip_limit=3)
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue tasks for different capabilities
        task1 = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")
        task2 = Task(task_id="task-2", node_id="node-2", required_capability="Backend:Python")

        with pytest.raises(TaskQueuedError):
            await router.assign_task(task1)

        with pytest.raises(NoAgentAvailableError):
            await router.assign_task(task2)

        # Check separate queues
        assert router.get_queue_depth("Web:React") == 1
        assert router.get_queue_depth("Backend:Python") == 1
        assert router.get_queue_depth() == 2

    @pytest.mark.asyncio
    async def test_dde_411_queue_processed_on_completion(self, router, registry):
        """DDE-411: Queue processed when agent becomes available"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue a task
        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        with pytest.raises(TaskQueuedError):
            await router.assign_task(task)

        assert router.get_queue_depth() == 1

        # Simulate task completion (free up capacity)
        # First need to assign a dummy task to have something to complete
        registry.agents["agent-1"].current_wip = 1
        router.assignments["dummy"] = Assignment(
            task_id="dummy",
            agent_id="agent-1",
            assigned_at=datetime.now(),
            capability="Web:React"
        )
        router.agent_assignments["agent-1"] = ["dummy"]

        # Complete task (this should process queue)
        await router.complete_task("dummy")

        # Queue should now be empty (task assigned)
        assert router.get_queue_depth() == 0


@pytest.mark.integration
@pytest.mark.dde
class TestWIPLimitEnforcement:
    """Test suite for WIP limit enforcement"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_412_wip_limit_enforced(self, router, registry):
        """DDE-412: WIP limit is enforced (default 3)"""
        agent = AgentProfile(agent_id="agent-1", name="Dev", wip_limit=3)
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Assign 3 tasks (should succeed)
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            agent_id = await router.assign_task(task)
            assert agent_id == "agent-1"

        # 4th task should queue
        task4 = Task(task_id="task-4", node_id="node-4", required_capability="Web:React")

        with pytest.raises(TaskQueuedError):
            await router.assign_task(task4)

    @pytest.mark.asyncio
    async def test_dde_413_custom_wip_limit_respected(self, router, registry):
        """DDE-413: Custom WIP limits are respected"""
        agent = AgentProfile(agent_id="agent-1", name="Dev", wip_limit=5)
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Assign 5 tasks (should succeed with custom limit)
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            await router.assign_task(task)

        assert registry.get_agent("agent-1").current_wip == 5

    @pytest.mark.asyncio
    async def test_dde_414_completion_frees_wip_slot(self, router, registry):
        """DDE-414: Task completion frees WIP slot"""
        agent = AgentProfile(agent_id="agent-1", name="Dev", wip_limit=3)
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Fill WIP
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            await router.assign_task(task)

        assert registry.get_agent("agent-1").current_wip == 3

        # Complete one task
        await router.complete_task("task-0")

        assert registry.get_agent("agent-1").current_wip == 2

        # Should be able to assign another
        task4 = Task(task_id="task-4", node_id="node-4", required_capability="Web:React")
        agent_id = await router.assign_task(task4)
        assert agent_id == "agent-1"


@pytest.mark.integration
@pytest.mark.dde
class TestTaskReassignment:
    """Test suite for task reassignment"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_415_reassign_task_to_different_agent(self, router, registry):
        """DDE-415: Task can be reassigned to different agent"""
        # Two agents
        for i in range(2):
            agent = AgentProfile(
                agent_id=f"agent-{i}",
                name=f"Dev {i}",
                quality_score=0.8 - (i * 0.1)
            )
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=3
                )
            )

        # Assign to agent-0
        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")
        agent_id = await router.assign_task(task)
        assert agent_id == "agent-0"

        # Reassign
        new_agent_id = await router.reassign_task("task-1")

        # Should be assigned to agent-1
        assert new_agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_dde_416_reassignment_frees_original_agent(self, router, registry):
        """DDE-416: Reassignment frees original agent's WIP"""
        for i in range(2):
            agent = AgentProfile(agent_id=f"agent-{i}", name=f"Dev {i}")
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=3
                )
            )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")
        await router.assign_task(task)

        assert registry.get_agent("agent-0").current_wip == 1

        # Reassign
        await router.reassign_task("task-1")

        # Original agent should be freed
        assert registry.get_agent("agent-0").current_wip == 0
        assert registry.get_agent("agent-1").current_wip == 1


@pytest.mark.integration
@pytest.mark.dde
class TestConcurrentAssignments:
    """Test suite for concurrent task assignments"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_417_concurrent_assignments_safe(self, router, registry):
        """DDE-417: Concurrent task assignments are safe"""
        # Register 5 agents
        for i in range(5):
            agent = AgentProfile(agent_id=f"agent-{i}", name=f"Dev {i}")
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=3
                )
            )

        # Assign 10 tasks concurrently
        tasks = [
            Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            for i in range(10)
        ]

        # Assign concurrently
        results = await asyncio.gather(
            *[router.assign_task(task) for task in tasks],
            return_exceptions=True
        )

        # Count successful assignments
        successful = sum(1 for r in results if isinstance(r, str))

        # At least 5 should succeed (one per agent)
        assert successful >= 5

    @pytest.mark.asyncio
    async def test_dde_418_10_tasks_per_second_throughput(self, router, registry):
        """DDE-418: Can handle 10 task assignments per second"""
        # Register 10 agents
        for i in range(10):
            agent = AgentProfile(agent_id=f"agent-{i}", name=f"Dev {i}")
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=3
                )
            )

        # Assign 10 tasks
        tasks = [
            Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            for i in range(10)
        ]

        start = time.time()
        results = await asyncio.gather(
            *[router.assign_task(task) for task in tasks],
            return_exceptions=True
        )
        elapsed = time.time() - start

        # Should complete in less than 1 second
        assert elapsed < 1.0
        assert sum(1 for r in results if isinstance(r, str)) == 10


@pytest.mark.integration
@pytest.mark.dde
class TestBackpressureAlerts:
    """Test suite for queue backpressure detection"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_419_backpressure_threshold_10(self, router, registry):
        """DDE-419: Backpressure threshold is 10 tasks"""
        assert router.backpressure_threshold == 10

    @pytest.mark.asyncio
    async def test_dde_420_backpressure_inactive_below_threshold(self, router, registry):
        """DDE-420: Backpressure inactive below threshold"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue 5 tasks (below threshold)
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            with pytest.raises(TaskQueuedError):
                await router.assign_task(task)

        assert not router.is_backpressure_active()

    @pytest.mark.asyncio
    async def test_dde_421_backpressure_active_above_threshold(self, router, registry):
        """DDE-421: Backpressure active when queue exceeds threshold"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue 10 tasks (at threshold)
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            with pytest.raises(TaskQueuedError):
                await router.assign_task(task)

        assert router.is_backpressure_active()

    @pytest.mark.asyncio
    async def test_dde_422_queue_depth_tracked_per_capability(self, router, registry):
        """DDE-422: Queue depth tracked per capability"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Queue tasks for React
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            with pytest.raises(TaskQueuedError):
                await router.assign_task(task)

        # Queue tasks for Python
        for i in range(5):
            task = Task(
                task_id=f"task-py-{i}",
                node_id=f"node-{i}",
                required_capability="Backend:Python"
            )
            with pytest.raises(NoAgentAvailableError):
                await router.assign_task(task)

        assert router.get_queue_depth("Web:React") == 3
        assert router.get_queue_depth("Backend:Python") == 5
        assert router.get_queue_depth() == 8


@pytest.mark.integration
@pytest.mark.dde
class TestAgentTaskTracking:
    """Test suite for tracking agent's assigned tasks"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_423_get_agent_tasks(self, router, registry):
        """DDE-423: Can retrieve all tasks assigned to agent"""
        agent = AgentProfile(agent_id="agent-1", name="Dev")
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        # Assign 3 tasks
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            await router.assign_task(task)

        tasks = router.get_agent_tasks("agent-1")

        assert len(tasks) == 3
        assert "task-0" in tasks
        assert "task-1" in tasks
        assert "task-2" in tasks

    @pytest.mark.asyncio
    async def test_dde_424_agent_tasks_updated_on_completion(self, router, registry):
        """DDE-424: Agent's task list updated on completion"""
        agent = AgentProfile(agent_id="agent-1", name="Dev")
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")
        await router.assign_task(task)

        assert len(router.get_agent_tasks("agent-1")) == 1

        await router.complete_task("task-1")

        assert len(router.get_agent_tasks("agent-1")) == 0

    @pytest.mark.asyncio
    async def test_dde_425_multiple_agents_tracked_independently(self, router, registry):
        """DDE-425: Multiple agents tracked independently"""
        # Register 3 agents
        for i in range(3):
            agent = AgentProfile(agent_id=f"agent-{i}", name=f"Dev {i}")
            registry.register_agent(agent)
            registry.add_capability(
                AgentCapability(
                    agent_id=f"agent-{i}",
                    skill_id="Web:React",
                    proficiency=3
                )
            )

        # Assign tasks to different agents
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                node_id=f"node-{i}",
                required_capability="Web:React"
            )
            await router.assign_task(task)

        # Each agent should have 1 task
        for i in range(3):
            tasks = router.get_agent_tasks(f"agent-{i}")
            assert len(tasks) == 1


@pytest.mark.integration
@pytest.mark.dde
class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    @pytest.fixture
    def registry(self):
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        return CapabilityMatcher(registry)

    @pytest.fixture
    def router(self, matcher, registry):
        return TaskRouter(matcher, registry)

    @pytest.mark.asyncio
    async def test_dde_426_empty_queue_returns_zero_depth(self, router, registry):
        """DDE-426: Empty queue returns zero depth"""
        assert router.get_queue_depth() == 0
        assert router.get_queue_depth("Web:React") == 0

    @pytest.mark.asyncio
    async def test_dde_427_complete_nonexistent_task_safe(self, router, registry):
        """DDE-427: Completing non-existent task is safe"""
        # Should not raise error
        await router.complete_task("nonexistent-task-id")

    @pytest.mark.asyncio
    async def test_dde_428_reassign_unassigned_task_raises_error(self, router, registry):
        """DDE-428: Reassigning unassigned task raises ValueError"""
        with pytest.raises(ValueError):
            await router.reassign_task("nonexistent-task-id")

    @pytest.mark.asyncio
    async def test_dde_429_get_tasks_for_unknown_agent_returns_empty(self, router, registry):
        """DDE-429: Getting tasks for unknown agent returns empty list"""
        tasks = router.get_agent_tasks("unknown-agent")

        assert tasks == []
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_dde_430_queue_peek_doesnt_remove_task(self, router, registry):
        """DDE-430: Queue peek doesn't remove task"""
        agent = AgentProfile(
            agent_id="agent-1",
            name="Dev",
            current_wip=3,
            wip_limit=3
        )
        registry.register_agent(agent)
        registry.add_capability(
            AgentCapability(agent_id="agent-1", skill_id="Web:React", proficiency=3)
        )

        task = Task(task_id="task-1", node_id="node-1", required_capability="Web:React")

        with pytest.raises(TaskQueuedError):
            await router.assign_task(task)

        # Peek at task
        peeked = router.queue.peek("Web:React")
        assert peeked.task_id == "task-1"

        # Queue size unchanged
        assert router.get_queue_depth("Web:React") == 1

        # Peek again - same task
        peeked2 = router.queue.peek("Web:React")
        assert peeked2.task_id == "task-1"
