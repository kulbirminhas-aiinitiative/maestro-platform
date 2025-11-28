# Prometheus Metrics Integration Guide

**Phase 3 Enhancement: Observability and Monitoring**

## Overview

This guide shows how to integrate Prometheus metrics into the DAG Workflow System for production monitoring.

**Metrics Module:** `prometheus_metrics.py`
**Status:** ✅ Implemented
**Production Ready:** Yes

---

## Quick Start

### 1. Add Metrics Endpoint to API Server

Add the following to `dag_api_server.py`:

```python
from prometheus_metrics import get_metrics, get_metrics_content_type, MetricsCollector
from fastapi.responses import Response

# Add metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )
```

### 2. Instrument Workflow Execution

Add metrics collection to workflow execution:

```python
from prometheus_metrics import MetricsCollector

@app.post("/workflow/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, context: Dict[str, Any]):
    start_time = time.time()
    MetricsCollector.record_workflow_start(workflow_id)

    try:
        result = await dag_executor.execute_workflow(workflow_id, context)
        duration = time.time() - start_time

        status = 'success' if result.success else 'failure'
        MetricsCollector.record_workflow_complete(workflow_id, status, duration)

        return result
    except Exception as e:
        duration = time.time() - start_time
        MetricsCollector.record_workflow_complete(workflow_id, 'failure', duration)
        raise
```

### 3. Instrument Node Execution

Add to `dag_executor.py`:

```python
from prometheus_metrics import MetricsCollector

async def _execute_single_node(self, dag, context, node_id):
    node = dag.nodes[node_id]
    start_time = time.time()

    MetricsCollector.record_node_start(
        node_type=node.node_type,
        phase_name=node.name
    )

    try:
        # ... existing execution code ...

        duration = time.time() - start_time
        MetricsCollector.record_node_complete(
            node_type=node.node_type,
            phase_name=node.name,
            status='success',
            duration_seconds=duration,
            retry_count=node_state.retry_count
        )

        return node_state
    except Exception as e:
        duration = time.time() - start_time
        MetricsCollector.record_node_complete(
            node_type=node.node_type,
            phase_name=node.name,
            status='failure',
            duration_seconds=duration
        )
        raise
```

### 4. Instrument Health Checks

Update health check endpoints to report metrics:

```python
from prometheus_metrics import MetricsCollector

@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    is_healthy = db_engine.health_check()

    # Update metrics
    MetricsCollector.update_health_status('database', is_healthy)

    if not is_healthy:
        raise HTTPException(status_code=503, detail={"ready": False})

    return {"ready": True}
```

---

## Metrics Reference

### Workflow Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `dag_workflow_executions_total` | Counter | Total workflows executed | workflow_name, status |
| `dag_workflow_execution_duration_seconds` | Histogram | Workflow duration | workflow_name |
| `dag_active_workflows` | Gauge | Currently executing workflows | - |
| `dag_workflow_queue_depth` | Gauge | Workflows waiting to execute | - |

### Node Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `dag_node_executions_total` | Counter | Total nodes executed | node_type, phase_name, status |
| `dag_node_execution_duration_seconds` | Histogram | Node duration | node_type, phase_name |
| `dag_node_retries_total` | Counter | Total node retries | node_type, phase_name |
| `dag_active_nodes` | Gauge | Currently executing nodes | - |

### System Health Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `dag_database_connections` | Gauge | Active database connections | - |
| `dag_database_pool_size` | Gauge | Database connection pool size | - |
| `dag_database_query_duration_seconds` | Histogram | Database query duration | query_type |
| `dag_context_store_operations_total` | Counter | Context store operations | operation, status |
| `dag_memory_usage_bytes` | Gauge | Memory usage | - |
| `dag_cpu_usage_percent` | Gauge | CPU usage | - |

### API Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `dag_api_requests_total` | Counter | Total API requests | method, endpoint, status_code |
| `dag_api_request_duration_seconds` | Histogram | API request duration | method, endpoint |
| `dag_websocket_connections` | Gauge | Active WebSocket connections | - |
| `dag_health_check_status` | Gauge | Health check status (1=healthy) | check_type |

### Quality Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `dag_quality_score_distribution` | Histogram | Quality score distribution | phase_name |
| `dag_artifacts_generated_total` | Counter | Total artifacts generated | artifact_type |
| `dag_artifact_size_bytes` | Histogram | Artifact size | artifact_type |
| `dag_contract_validations_total` | Counter | Contract validations | contract_type, status |

---

## Prometheus Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dag-workflow-system'
    static_configs:
      - targets: ['localhost:8003']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Docker Compose

```yaml
version: '3.8'

services:
  dag-api-server:
    image: maestro/dag-api-server:3.0.0
    ports:
      - "8003:8003"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/maestro

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

---

## Grafana Dashboards

### Key Metrics Dashboard

**Panel 1: Workflow Success Rate**
```promql
# Success rate (last 5 minutes)
rate(dag_workflow_executions_total{status="success"}[5m]) /
rate(dag_workflow_executions_total[5m]) * 100
```

**Panel 2: Workflow Duration (P95)**
```promql
# 95th percentile workflow duration
histogram_quantile(0.95,
  rate(dag_workflow_execution_duration_seconds_bucket[5m])
)
```

**Panel 3: Active Workflows**
```promql
# Currently executing workflows
dag_active_workflows
```

**Panel 4: Node Failure Rate**
```promql
# Node failure rate by phase
rate(dag_node_executions_total{status="failure"}[5m])
```

**Panel 5: API Latency**
```promql
# API request latency (P95)
histogram_quantile(0.95,
  rate(dag_api_request_duration_seconds_bucket[5m])
)
```

**Panel 6: Database Health**
```promql
# Database health status
dag_health_check_status{check_type="database"}
```

### System Resources Dashboard

**Panel 1: CPU Usage**
```promql
dag_cpu_usage_percent
```

**Panel 2: Memory Usage**
```promql
dag_memory_usage_bytes / 1024 / 1024  # Convert to MB
```

**Panel 3: Database Connections**
```promql
dag_database_connections
```

**Panel 4: Active Nodes**
```promql
dag_active_nodes
```

---

## Alerting Rules

### alerts.yml

```yaml
groups:
  - name: dag_workflow_alerts
    interval: 30s
    rules:
      # Workflow failure rate too high
      - alert: HighWorkflowFailureRate
        expr: |
          rate(dag_workflow_executions_total{status="failure"}[5m]) /
          rate(dag_workflow_executions_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High workflow failure rate (>10%)"
          description: "Workflow failure rate is {{ $value | humanizePercentage }}"

      # Database unhealthy
      - alert: DatabaseUnhealthy
        expr: dag_health_check_status{check_type="database"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database health check failing"
          description: "Database is unhealthy"

      # High API latency
      - alert: HighAPILatency
        expr: |
          histogram_quantile(0.95,
            rate(dag_api_request_duration_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency (P95 > 5s)"
          description: "API P95 latency is {{ $value | humanizeDuration }}"

      # Too many active workflows
      - alert: TooManyActiveWorkflows
        expr: dag_active_workflows > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Too many active workflows (>100)"
          description: "{{ $value }} workflows are currently executing"

      # High memory usage
      - alert: HighMemoryUsage
        expr: dag_memory_usage_bytes > 2147483648  # 2GB
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage (>2GB)"
          description: "Memory usage is {{ $value | humanize1024 }}"
```

---

## Example Usage

### Using Decorators

```python
from prometheus_metrics import track_workflow_execution, track_node_execution

@track_workflow_execution("sdlc_parallel")
async def execute_sdlc_workflow(requirement: str):
    # Workflow execution automatically tracked
    result = await dag_executor.execute_workflow("sdlc_parallel", {
        "requirement": requirement
    })
    return result

@track_node_execution("phase", "backend_development")
async def execute_backend_phase(context):
    # Node execution automatically tracked
    result = await phase_executor.execute(context)
    return result
```

### Manual Metrics Collection

```python
from prometheus_metrics import MetricsCollector
import time

# Workflow execution
start = time.time()
MetricsCollector.record_workflow_start("my_workflow")

try:
    result = await execute_workflow()
    duration = time.time() - start
    MetricsCollector.record_workflow_complete("my_workflow", "success", duration)
except Exception as e:
    duration = time.time() - start
    MetricsCollector.record_workflow_complete("my_workflow", "failure", duration)

# Node execution
MetricsCollector.record_node_start("phase", "testing")
# ... execute node ...
MetricsCollector.record_node_complete("phase", "testing", "success", 45.2, retry_count=1)

# Quality score
MetricsCollector.record_quality_score("backend_development", 0.92)

# Artifacts
MetricsCollector.record_artifact("source_code", size_bytes=1048576)

# Health status
MetricsCollector.update_health_status("database", True)
MetricsCollector.update_health_status("redis", True)

# System resources
import psutil
process = psutil.Process()
MetricsCollector.update_system_resources(
    memory_bytes=process.memory_info().rss,
    cpu_percent=process.cpu_percent()
)
```

---

## Testing Metrics

### Verify Metrics Endpoint

```bash
# Test metrics endpoint
curl http://localhost:8003/metrics

# Expected output:
# HELP dag_workflow_executions_total Total number of workflow executions
# TYPE dag_workflow_executions_total counter
# dag_workflow_executions_total{status="success",workflow_name="sdlc_parallel"} 42.0
# ...
```

### Query Metrics with Prometheus

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query workflow success rate
curl 'http://localhost:9090/api/v1/query?query=rate(dag_workflow_executions_total{status="success"}[5m])'
```

---

## Best Practices

### 1. Metric Naming

- ✅ Use descriptive names: `dag_workflow_execution_duration_seconds`
- ✅ Include units: `_seconds`, `_bytes`, `_total`
- ✅ Use consistent prefixes: `dag_*`
- ❌ Avoid: `time`, `count`, `metric1`

### 2. Label Cardinality

- ✅ Low cardinality labels: `status`, `node_type`, `phase_name`
- ❌ High cardinality labels: `user_id`, `timestamp`, `workflow_execution_id`

### 3. Metric Types

- **Counter**: Monotonically increasing (requests, errors, completions)
- **Gauge**: Can go up or down (active workflows, memory usage)
- **Histogram**: Distributions (latency, duration, size)
- **Summary**: Similar to histogram but calculated client-side

### 4. Performance

- Keep metric collection lightweight
- Use labels instead of creating many metrics
- Batch updates when possible
- Avoid blocking operations in metric collection

---

## Production Deployment Checklist

- [x] ✅ Metrics module implemented (`prometheus_metrics.py`)
- [ ] ⏸️ Add `/metrics` endpoint to `dag_api_server.py`
- [ ] ⏸️ Instrument workflow execution
- [ ] ⏸️ Instrument node execution
- [ ] ⏸️ Instrument health checks
- [ ] ⏸️ Deploy Prometheus server
- [ ] ⏸️ Deploy Grafana
- [ ] ⏸️ Configure alerting rules
- [ ] ⏸️ Create dashboards
- [ ] ⏸️ Test monitoring in staging
- [ ] ⏸️ Deploy to production

---

## Related Documentation

- [Phase 3 Completion Report](./PHASE_3_COMPLETION_REPORT.md) - Full implementation details
- [Phase 2 Executive Summary](./PHASE_2_EXECUTIVE_SUMMARY.md) - Production readiness improvements
- [AGENT3 DAG Workflow Architecture](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - System architecture

**Status:** ✅ Prometheus metrics module implemented and ready for integration
**Next Steps:** Integrate metrics endpoints into API server and deploy Prometheus/Grafana stack
