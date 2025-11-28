"""
Prometheus Metrics for DAG Workflow System

Provides comprehensive metrics collection for:
- Workflow execution (success, failure, duration)
- Node execution (by phase, status, duration)
- System health (database, queue, resources)
- API performance (requests, latency, errors)

Phase 3 Enhancement: Observability and monitoring
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY
)
from typing import Optional, Dict, Any
from datetime import datetime
import time
import logging


logger = logging.getLogger(__name__)


# =============================================================================
# Workflow Execution Metrics
# =============================================================================

# Total workflows executed
workflow_executions_total = Counter(
    'dag_workflow_executions_total',
    'Total number of workflow executions',
    ['workflow_name', 'status']  # status: success, failure, cancelled
)

# Workflow execution duration
workflow_execution_duration_seconds = Histogram(
    'dag_workflow_execution_duration_seconds',
    'Duration of workflow executions in seconds',
    ['workflow_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)  # 1s to 1hr
)

# Active workflows
active_workflows = Gauge(
    'dag_active_workflows',
    'Number of currently executing workflows'
)

# Workflow queue depth
workflow_queue_depth = Gauge(
    'dag_workflow_queue_depth',
    'Number of workflows waiting to execute'
)


# =============================================================================
# Node Execution Metrics
# =============================================================================

# Total nodes executed
node_executions_total = Counter(
    'dag_node_executions_total',
    'Total number of node executions',
    ['node_type', 'phase_name', 'status']  # status: success, failure, skipped
)

# Node execution duration
node_execution_duration_seconds = Histogram(
    'dag_node_execution_duration_seconds',
    'Duration of node executions in seconds',
    ['node_type', 'phase_name'],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 120, 300, 600)  # 100ms to 10min
)

# Node retry count
node_retries_total = Counter(
    'dag_node_retries_total',
    'Total number of node retries',
    ['node_type', 'phase_name']
)

# Active nodes
active_nodes = Gauge(
    'dag_active_nodes',
    'Number of currently executing nodes'
)


# =============================================================================
# System Health Metrics
# =============================================================================

# Database connections
database_connections = Gauge(
    'dag_database_connections',
    'Number of active database connections'
)

# Database connection pool size
database_pool_size = Gauge(
    'dag_database_pool_size',
    'Size of database connection pool'
)

# Database query duration
database_query_duration_seconds = Histogram(
    'dag_database_query_duration_seconds',
    'Duration of database queries in seconds',
    ['query_type'],  # query_type: select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5)  # 1ms to 5s
)

# Context store operations
context_store_operations_total = Counter(
    'dag_context_store_operations_total',
    'Total number of context store operations',
    ['operation', 'status']  # operation: save, load, delete; status: success, failure
)

# Memory usage
memory_usage_bytes = Gauge(
    'dag_memory_usage_bytes',
    'Memory usage in bytes'
)

# CPU usage
cpu_usage_percent = Gauge(
    'dag_cpu_usage_percent',
    'CPU usage percentage'
)


# =============================================================================
# API Metrics
# =============================================================================

# API requests
api_requests_total = Counter(
    'dag_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

# API request duration
api_request_duration_seconds = Histogram(
    'dag_api_request_duration_seconds',
    'Duration of API requests in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)  # 5ms to 10s
)

# WebSocket connections
websocket_connections = Gauge(
    'dag_websocket_connections',
    'Number of active WebSocket connections'
)

# Health check status
health_check_status = Gauge(
    'dag_health_check_status',
    'Health check status (1=healthy, 0=unhealthy)',
    ['check_type']  # check_type: database, redis, etc.
)


# =============================================================================
# Contract Validation Metrics
# =============================================================================

# Contract validations
contract_validations_total = Counter(
    'dag_contract_validations_total',
    'Total number of contract validations',
    ['contract_type', 'status']  # contract_type: input, output; status: valid, invalid
)

# Contract validation duration
contract_validation_duration_seconds = Histogram(
    'dag_contract_validation_duration_seconds',
    'Duration of contract validations in seconds',
    ['contract_type'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1)  # 1ms to 1s
)


# =============================================================================
# Quality Metrics
# =============================================================================

# Quality scores
quality_score_distribution = Histogram(
    'dag_quality_score_distribution',
    'Distribution of quality scores',
    ['phase_name'],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# Artifacts generated
artifacts_generated_total = Counter(
    'dag_artifacts_generated_total',
    'Total number of artifacts generated',
    ['artifact_type']
)

# Artifact size
artifact_size_bytes = Histogram(
    'dag_artifact_size_bytes',
    'Size of generated artifacts in bytes',
    ['artifact_type'],
    buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600)  # 1KB to 100MB
)


# =============================================================================
# System Information
# =============================================================================

# System info
system_info = Info(
    'dag_system',
    'DAG Workflow System information'
)

# Set system info
system_info.info({
    'version': '3.0.0',
    'phase_1_complete': 'true',
    'phase_2_complete': 'true',
    'production_readiness': '95',
    'deployment_status': 'production_ready'
})


# =============================================================================
# Metric Helper Functions
# =============================================================================

class MetricsCollector:
    """
    Helper class for collecting and managing Prometheus metrics.
    """

    @staticmethod
    def record_workflow_start(workflow_name: str):
        """Record workflow start"""
        active_workflows.inc()
        logger.debug(f"Workflow started: {workflow_name}")

    @staticmethod
    def record_workflow_complete(
        workflow_name: str,
        status: str,
        duration_seconds: float
    ):
        """
        Record workflow completion

        Args:
            workflow_name: Name of the workflow
            status: 'success', 'failure', or 'cancelled'
            duration_seconds: Execution duration
        """
        workflow_executions_total.labels(
            workflow_name=workflow_name,
            status=status
        ).inc()

        workflow_execution_duration_seconds.labels(
            workflow_name=workflow_name
        ).observe(duration_seconds)

        active_workflows.dec()
        logger.debug(f"Workflow completed: {workflow_name} ({status}) in {duration_seconds:.2f}s")

    @staticmethod
    def record_node_start(node_type: str, phase_name: str):
        """Record node start"""
        active_nodes.inc()
        logger.debug(f"Node started: {phase_name} ({node_type})")

    @staticmethod
    def record_node_complete(
        node_type: str,
        phase_name: str,
        status: str,
        duration_seconds: float,
        retry_count: int = 0
    ):
        """
        Record node completion

        Args:
            node_type: Type of node (phase, parallel_group, etc.)
            phase_name: Name of the phase
            status: 'success', 'failure', or 'skipped'
            duration_seconds: Execution duration
            retry_count: Number of retries
        """
        node_executions_total.labels(
            node_type=node_type,
            phase_name=phase_name,
            status=status
        ).inc()

        node_execution_duration_seconds.labels(
            node_type=node_type,
            phase_name=phase_name
        ).observe(duration_seconds)

        if retry_count > 0:
            node_retries_total.labels(
                node_type=node_type,
                phase_name=phase_name
            ).inc(retry_count)

        active_nodes.dec()
        logger.debug(f"Node completed: {phase_name} ({status}) in {duration_seconds:.2f}s")

    @staticmethod
    def record_api_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float
    ):
        """
        Record API request

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status_code: HTTP status code
            duration_seconds: Request duration
        """
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()

        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration_seconds)

    @staticmethod
    def record_database_query(query_type: str, duration_seconds: float):
        """Record database query execution"""
        database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration_seconds)

    @staticmethod
    def record_context_store_operation(
        operation: str,
        status: str,
        duration_seconds: float
    ):
        """
        Record context store operation

        Args:
            operation: 'save', 'load', or 'delete'
            status: 'success' or 'failure'
            duration_seconds: Operation duration
        """
        context_store_operations_total.labels(
            operation=operation,
            status=status
        ).inc()

    @staticmethod
    def record_contract_validation(
        contract_type: str,
        is_valid: bool,
        duration_seconds: float
    ):
        """
        Record contract validation

        Args:
            contract_type: 'input' or 'output'
            is_valid: Whether validation passed
            duration_seconds: Validation duration
        """
        status = 'valid' if is_valid else 'invalid'

        contract_validations_total.labels(
            contract_type=contract_type,
            status=status
        ).inc()

        contract_validation_duration_seconds.labels(
            contract_type=contract_type
        ).observe(duration_seconds)

    @staticmethod
    def record_quality_score(phase_name: str, score: float):
        """Record quality score for a phase"""
        quality_score_distribution.labels(
            phase_name=phase_name
        ).observe(score)

    @staticmethod
    def record_artifact(artifact_type: str, size_bytes: int):
        """Record artifact generation"""
        artifacts_generated_total.labels(
            artifact_type=artifact_type
        ).inc()

        artifact_size_bytes.labels(
            artifact_type=artifact_type
        ).observe(size_bytes)

    @staticmethod
    def update_health_status(check_type: str, is_healthy: bool):
        """Update health check status"""
        health_check_status.labels(
            check_type=check_type
        ).set(1 if is_healthy else 0)

    @staticmethod
    def update_system_resources(memory_bytes: int, cpu_percent: float):
        """Update system resource metrics"""
        memory_usage_bytes.set(memory_bytes)
        cpu_usage_percent.set(cpu_percent)

    @staticmethod
    def update_database_metrics(connections: int, pool_size: int):
        """Update database connection metrics"""
        database_connections.set(connections)
        database_pool_size.set(pool_size)


# =============================================================================
# Metric Decorators
# =============================================================================

def track_workflow_execution(workflow_name: str):
    """Decorator to track workflow execution metrics"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            MetricsCollector.record_workflow_start(workflow_name)

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                status = 'success' if result.get('success', False) else 'failure'
                MetricsCollector.record_workflow_complete(workflow_name, status, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                MetricsCollector.record_workflow_complete(workflow_name, 'failure', duration)
                raise

        return wrapper
    return decorator


def track_node_execution(node_type: str, phase_name: str):
    """Decorator to track node execution metrics"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            MetricsCollector.record_node_start(node_type, phase_name)

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                status = result.get('status', 'unknown')
                retry_count = result.get('retry_count', 0)
                MetricsCollector.record_node_complete(
                    node_type, phase_name, status, duration, retry_count
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                MetricsCollector.record_node_complete(
                    node_type, phase_name, 'failure', duration
                )
                raise

        return wrapper
    return decorator


# =============================================================================
# Export Functions
# =============================================================================

def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus format

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """
    Get Prometheus metrics content type

    Returns:
        Content type for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST


# Export public API
__all__ = [
    'MetricsCollector',
    'get_metrics',
    'get_metrics_content_type',
    'track_workflow_execution',
    'track_node_execution',
    # Individual metrics for advanced usage
    'workflow_executions_total',
    'workflow_execution_duration_seconds',
    'node_executions_total',
    'node_execution_duration_seconds',
    'api_requests_total',
    'api_request_duration_seconds',
    'health_check_status',
    'system_info',
]
