"""
DAG Execution Engine for workflow orchestration
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict, deque
import networkx as nx

from .models import TaskStatus, ExecutionResult, TaskConfig

logger = logging.getLogger(__name__)


class DAGNode:
    """Node in the DAG representing a task"""

    def __init__(self, task_config: TaskConfig):
        self.task_config = task_config
        self.task_id = task_config.task_id
        self.status = TaskStatus.PENDING
        self.result: Optional[ExecutionResult] = None
        self.dependencies: Set[str] = set(task_config.dependencies)
        self.dependents: Set[str] = set()

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are completed"""
        return self.dependencies.issubset(completed_tasks)

    def __repr__(self):
        return f"DAGNode(id={self.task_id}, status={self.status})"


class DAGEngine:
    """Core DAG engine for dependency resolution and execution planning"""

    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
        self.graph = nx.DiGraph()

    def add_task(self, task_config: TaskConfig) -> None:
        """Add a task to the DAG"""
        node = DAGNode(task_config)
        self.nodes[node.task_id] = node
        self.graph.add_node(node.task_id, node=node)

        # Add edges for dependencies
        for dep_id in task_config.dependencies:
            if dep_id not in self.nodes:
                raise ValueError(f"Dependency {dep_id} not found for task {node.task_id}")
            self.graph.add_edge(dep_id, node.task_id)
            self.nodes[dep_id].dependents.add(node.task_id)

    def validate(self) -> bool:
        """Validate DAG structure (check for cycles)"""
        try:
            if not nx.is_directed_acyclic_graph(self.graph):
                raise ValueError("Graph contains cycles")
            return True
        except Exception as e:
            logger.error(f"DAG validation failed: {e}")
            raise

    def get_execution_order(self) -> List[List[str]]:
        """Get topologically sorted execution order (levels for parallel execution)"""
        if not self.validate():
            raise ValueError("Invalid DAG structure")

        levels = []
        in_degree = {node: self.graph.in_degree(node) for node in self.graph.nodes()}
        queue = deque([node for node, degree in in_degree.items() if degree == 0])

        while queue:
            level = []
            level_size = len(queue)

            for _ in range(level_size):
                node = queue.popleft()
                level.append(node)

                # Reduce in-degree for dependent nodes
                for successor in self.graph.successors(node):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)

            levels.append(level)

        return levels

    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[DAGNode]:
        """Get tasks that are ready to execute"""
        ready = []
        for node in self.nodes.values():
            if node.status == TaskStatus.PENDING and node.is_ready(completed_tasks):
                ready.append(node)
        return ready

    def get_critical_path(self) -> List[str]:
        """Calculate critical path through the DAG"""
        if not self.nodes:
            return []

        # Add weights based on estimated execution time
        weighted_graph = self.graph.copy()
        for node_id, node in self.nodes.items():
            weight = node.task_config.resources.timeout_seconds
            weighted_graph.nodes[node_id]['weight'] = weight

        # Find longest path
        try:
            critical_path = nx.dag_longest_path(weighted_graph, weight='weight')
            return critical_path
        except Exception as e:
            logger.error(f"Error calculating critical path: {e}")
            return []

    def visualize(self) -> Dict[str, Any]:
        """Generate visualization data for the DAG"""
        return {
            "nodes": [
                {
                    "id": node_id,
                    "name": node.task_config.name,
                    "status": node.status.value,
                    "type": node.task_config.task_type
                }
                for node_id, node in self.nodes.items()
            ],
            "edges": [
                {"source": u, "target": v}
                for u, v in self.graph.edges()
            ]
        }


class DAGExecutor:
    """Executes DAG with parallel task execution and error handling"""

    def __init__(
        self,
        dag_engine: DAGEngine,
        task_executor: Callable,
        max_parallel_tasks: int = 10
    ):
        self.dag_engine = dag_engine
        self.task_executor = task_executor
        self.max_parallel_tasks = max_parallel_tasks
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()
        self.semaphore = asyncio.Semaphore(max_parallel_tasks)

    async def execute_task(self, node: DAGNode) -> ExecutionResult:
        """Execute a single task with retry logic"""
        task_config = node.task_config
        retry_count = 0
        max_retries = task_config.retry_policy.get("max_retries", 3)
        retry_delay = task_config.retry_policy.get("retry_delay", 60)
        exponential_backoff = task_config.retry_policy.get("exponential_backoff", True)

        async with self.semaphore:
            while retry_count <= max_retries:
                try:
                    node.status = TaskStatus.RUNNING
                    self.running_tasks.add(node.task_id)

                    logger.info(f"Executing task {node.task_id} (attempt {retry_count + 1})")
                    start_time = datetime.utcnow()

                    # Execute the task
                    output = await self.task_executor(task_config)

                    end_time = datetime.utcnow()
                    result = ExecutionResult(
                        task_id=node.task_id,
                        status=TaskStatus.SUCCESS,
                        output=output,
                        start_time=start_time,
                        end_time=end_time,
                        retry_count=retry_count
                    )

                    node.status = TaskStatus.SUCCESS
                    node.result = result
                    self.completed_tasks.add(node.task_id)
                    self.running_tasks.remove(node.task_id)

                    logger.info(f"Task {node.task_id} completed successfully")
                    return result

                except Exception as e:
                    logger.error(f"Task {node.task_id} failed (attempt {retry_count + 1}): {e}")
                    retry_count += 1

                    if retry_count > max_retries:
                        end_time = datetime.utcnow()
                        result = ExecutionResult(
                            task_id=node.task_id,
                            status=TaskStatus.FAILED,
                            error=str(e),
                            start_time=start_time,
                            end_time=end_time,
                            retry_count=retry_count - 1
                        )

                        node.status = TaskStatus.FAILED
                        node.result = result
                        self.failed_tasks.add(node.task_id)
                        self.running_tasks.discard(node.task_id)
                        return result

                    # Wait before retry
                    node.status = TaskStatus.RETRYING
                    delay = retry_delay * (2 ** (retry_count - 1)) if exponential_backoff else retry_delay
                    await asyncio.sleep(delay)

    async def execute(self, failure_strategy: str = "fail_fast") -> List[ExecutionResult]:
        """Execute the entire DAG"""
        logger.info("Starting DAG execution")

        # Validate DAG
        self.dag_engine.validate()

        results = []
        pending_tasks = set(self.dag_engine.nodes.keys())

        while pending_tasks or self.running_tasks:
            # Get ready tasks
            ready_tasks = [
                node for node in self.dag_engine.nodes.values()
                if node.task_id in pending_tasks and node.is_ready(self.completed_tasks)
            ]

            if not ready_tasks and not self.running_tasks:
                # Deadlock detected
                logger.error("Deadlock detected: no tasks ready and none running")
                break

            # Execute ready tasks in parallel
            if ready_tasks:
                tasks = []
                for node in ready_tasks:
                    pending_tasks.remove(node.task_id)
                    tasks.append(self.execute_task(node))

                # Wait for at least one task to complete
                if tasks:
                    completed = await asyncio.gather(*tasks, return_exceptions=True)
                    results.extend([r for r in completed if isinstance(r, ExecutionResult)])

                    # Check failure strategy
                    if failure_strategy == "fail_fast" and self.failed_tasks:
                        logger.warning("Fail-fast strategy triggered, stopping execution")
                        break
            else:
                # Wait a bit for running tasks
                await asyncio.sleep(1)

        logger.info(f"DAG execution completed: {len(self.completed_tasks)} succeeded, {len(self.failed_tasks)} failed")
        return results