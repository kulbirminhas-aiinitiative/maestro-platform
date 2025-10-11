# Centralized Logging Setup Guide

## Overview

The ML platform uses **Loki + Promtail** for centralized log aggregation and analysis. This is a lightweight, cost-effective alternative to ELK stack, with native Grafana integration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Logging Architecture                   │
└─────────────────────────────────────────────────────────┘

┌──────────────┐
│   Pods       │
│ (ML Platform)│
│              │
│ • MLflow     │
│ • Airflow    │
│ • Feast      │
│ • Training   │
└──────┬───────┘
       │ logs to stdout/stderr
       ▼
┌──────────────────┐
│    Promtail      │
│  (DaemonSet)     │
│                  │
│ Runs on every    │
│ node, collects   │
│ container logs   │
└──────┬───────────┘
       │ ship logs
       ▼
┌──────────────────┐
│      Loki        │
│  (StatefulSet)   │
│                  │
│ • Index logs     │
│ • Store chunks   │
│ • Query API      │
└──────┬───────────┘
       │ query logs
       ▼
┌──────────────────┐
│     Grafana      │
│   (Dashboard)    │
│                  │
│ • Explore logs   │
│ • Build queries  │
│ • Create alerts  │
└──────────────────┘
```

## Components

### 1. Loki (Log Aggregator)
- **Purpose**: Index and store logs efficiently
- **Storage**: Filesystem-based (BoltDB for index, filesystem for chunks)
- **Retention**: 30 days (production), 7 days (minikube)
- **Replicas**: 2 (production), 1 (minikube)

### 2. Promtail (Log Collector)
- **Purpose**: Collect logs from Kubernetes pods
- **Deployment**: DaemonSet (runs on every node)
- **Method**: Reads container logs from /var/log/pods
- **Processing**: Adds labels (namespace, pod, container, app)

### 3. Grafana Integration
- **DataSource**: Pre-configured Loki datasource
- **Query Language**: LogQL (similar to PromQL)
- **Features**: Log streaming, filtering, aggregation

## Ports

Via port registry:
- **Loki API**: 30508 (minikube NodePort)

## Deployment

### Minikube

```bash
# 1. Deploy logging stack
kubectl apply -f infrastructure/minikube/logging-stack.yaml

# 2. Wait for Loki to be ready
kubectl wait --for=condition=ready pod -l app=loki -n logging --timeout=300s

# 3. Verify Promtail DaemonSet
kubectl get daemonset -n logging
kubectl get pods -n logging

# 4. Get Loki URL
MINIKUBE_IP=$(minikube ip)
echo "Loki API: http://$MINIKUBE_IP:30508"

# 5. Configure Grafana datasource (if not auto-configured)
kubectl apply -f infrastructure/minikube/logging-stack.yaml

# 6. Restart Grafana to load datasource
kubectl rollout restart deployment grafana -n monitoring
```

### Production

```bash
# 1. Deploy logging stack
kubectl apply -f infrastructure/kubernetes/logging-stack.yaml

# 2. Wait for Loki to be ready
kubectl wait --for=condition=ready pod -l app=loki -n logging --timeout=300s

# 3. Verify all components
kubectl get all -n logging

# 4. Check Promtail is collecting logs
kubectl logs -n logging daemonset/promtail --tail=50
```

## Verification

### Check Loki is Running

```bash
# Check Loki pods
kubectl get pods -n logging -l app=loki

# Check Loki logs
kubectl logs -n logging -l app=loki --tail=50

# Test Loki API
kubectl exec -it -n logging loki-0 -- wget -O- http://localhost:3100/ready
```

### Check Promtail is Collecting Logs

```bash
# Check Promtail DaemonSet
kubectl get daemonset -n logging promtail

# Check Promtail logs
kubectl logs -n logging daemonset/promtail --tail=50

# Should see lines like:
# level=info ts=... caller=filetargetmanager.go msg="Adding target" key="/var/log/pods/..."
```

### Query Logs via Loki API

```bash
MINIKUBE_IP=$(minikube ip)

# Query all logs from last hour
curl -G -s "http://$MINIKUBE_IP:30508/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="airflow"}' \
  --data-urlencode "start=$(date -u -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date -u +%s)000000000" | jq

# Query error logs
curl -G -s "http://$MINIKUBE_IP:30508/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="airflow"} |= "ERROR"' \
  --data-urlencode "start=$(date -u -d '1 hour ago' +%s)000000000" | jq

# Get log streams
curl -s "http://$MINIKUBE_IP:30508/loki/api/v1/labels" | jq
```

## Using Grafana Explore

### Access Grafana

```bash
# Minikube
MINIKUBE_IP=$(minikube ip)
open http://$MINIKUBE_IP:30504  # Grafana port

# Login: admin / admin (default)
```

### Navigate to Loki

1. Click **Explore** (compass icon in left sidebar)
2. Select **Loki** from datasource dropdown
3. Start querying logs

### Example LogQL Queries

```logql
# All logs from Airflow namespace
{namespace="airflow"}

# All logs from MLflow pods
{namespace="ml-platform", app="mlflow"}

# Error logs from all namespaces
{namespace=~".*"} |= "ERROR"

# Airflow task failures
{namespace="airflow"} |= "Task failed"

# MLflow experiment logs
{namespace="ml-platform", app="mlflow"} |~ "experiment_id=\\d+"

# Count errors per minute
sum(count_over_time({namespace="airflow"} |= "ERROR" [1m]))

# Top 10 pods by log volume
topk(10, sum by (pod) (count_over_time({namespace=~".*"}[5m])))

# Training job logs
{namespace="ml-platform", job=~"training-.*"}

# Filter by time range (last 5 minutes)
{namespace="airflow"} [5m]

# Multiple filters (AND)
{namespace="airflow", pod=~"scheduler-.*"} |= "INFO" != "heartbeat"

# Parse JSON logs
{app="mlflow"} | json | level="error"

# Extract and filter fields
{app="airflow"} | logfmt | duration > 10s
```

### Building Log Dashboards

Create Grafana dashboard panels with LogQL queries:

```json
{
  "title": "Airflow Error Rate",
  "targets": [
    {
      "expr": "sum(rate({namespace=\"airflow\"} |= \"ERROR\" [5m]))"
    }
  ],
  "type": "graph"
}
```

## Log Labels

Promtail automatically adds these labels:

- `namespace`: Kubernetes namespace
- `pod`: Pod name
- `container`: Container name
- `app`: Application label from pod
- `job`: Combination of namespace/pod

### Custom Labels

Add custom labels in application logs:

```python
# Python example
import logging
import json

logger = logging.getLogger(__name__)

# Structured logging (Loki can parse)
logger.info(json.dumps({
    "message": "Training started",
    "experiment_id": "exp_123",
    "model_type": "random_forest",
    "level": "info"
}))
```

Promtail can extract these with pipeline stages:

```yaml
pipeline_stages:
  - json:
      expressions:
        experiment_id: experiment_id
        model_type: model_type
  - labels:
      experiment_id:
      model_type:
```

## Alerts

### Configure Loki Alerts in Prometheus

```yaml
# PrometheusRule example (already included in logging-stack.yaml)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: loki-alerts
  namespace: logging
spec:
  groups:
  - name: loki
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate({namespace="airflow"} |= "ERROR" [5m])) > 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate in Airflow"
        description: "Airflow error rate is {{ $value }} errors/sec"
```

### ML Platform Specific Alerts

```yaml
- alert: MLflowExperimentFailed
  expr: |
    count_over_time({namespace="ml-platform", app="mlflow"} |= "experiment failed" [5m]) > 0
  labels:
    severity: critical

- alert: AirflowDAGFailure
  expr: |
    count_over_time({namespace="airflow"} |= "DAG.*failed" [10m]) > 0
  labels:
    severity: critical

- alert: TrainingJobOOM
  expr: |
    count_over_time({namespace="ml-platform"} |= "OOMKilled" [5m]) > 0
  labels:
    severity: warning
```

## Performance Tuning

### Loki Configuration

```yaml
# Adjust ingestion limits
limits_config:
  ingestion_rate_mb: 10  # MB/sec per tenant
  ingestion_burst_size_mb: 20  # Burst size
  max_streams_per_user: 10000  # Max active streams

# Adjust retention
limits_config:
  retention_period: 720h  # 30 days
```

### Promtail Configuration

```yaml
# Limit CPU/memory usage
resources:
  requests:
    memory: "64Mi"
    cpu: "25m"
  limits:
    memory: "128Mi"
    cpu: "100m"
```

### Storage Sizing

**Production**:
- Loki storage: 50Gi (30 day retention, ~1.7Gi/day)
- Assumes ~10MB/sec average ingestion

**Minikube**:
- Loki storage: 10Gi (7 day retention, ~1.4Gi/day)
- Assumes ~2MB/sec average ingestion

### Retention Calculation

```bash
# Estimate storage needs
daily_log_volume_mb = ingestion_rate_mb * 86400
storage_needed_gb = (daily_log_volume_mb / 1024) * retention_days

# Example: 10MB/s for 30 days
# = 10 * 86400 / 1024 * 30 = ~25GB
```

## Troubleshooting

### Loki Not Receiving Logs

```bash
# Check Promtail is running on all nodes
kubectl get daemonset -n logging promtail

# Check Promtail logs for errors
kubectl logs -n logging daemonset/promtail --tail=100

# Verify Promtail can reach Loki
kubectl exec -it -n logging $(kubectl get pod -n logging -l app=promtail -o name | head -1) -- \
  wget -O- http://loki:3100/ready
```

### Loki Query Timeout

```bash
# Increase query timeout in Grafana datasource
# Or reduce time range / add more filters to query
```

### Loki Storage Full

```bash
# Check storage usage
kubectl exec -it -n logging loki-0 -- df -h /loki

# Reduce retention period
kubectl edit configmap -n logging loki-config
# Change retention_period to smaller value

# Restart Loki
kubectl rollout restart statefulset -n logging loki
```

### Missing Logs from Specific Pods

```bash
# Check pod labels
kubectl get pod <pod-name> -n <namespace> --show-labels

# Verify Promtail relabel config matches the labels
kubectl get configmap -n logging promtail-config -o yaml

# Check Promtail discovered the pod
kubectl exec -it -n logging $(kubectl get pod -n logging -l app=promtail -o name | head -1) -- \
  wget -O- http://localhost:9080/targets
```

## Integration with ML Workflows

### Airflow DAG Logging

```python
# In Airflow DAG
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging

def training_task():
    logger = logging.getLogger(__name__)
    logger.info("Starting training job")
    # Training logic...
    logger.info("Training completed", extra={
        "experiment_id": "exp_123",
        "accuracy": 0.95
    })

with DAG('ml_training') as dag:
    train = PythonOperator(
        task_id='train_model',
        python_callable=training_task
    )
```

Query in Grafana:
```logql
{namespace="airflow", job=~".*ml_training.*"} |= "experiment_id"
```

### MLflow Experiment Tracking

```python
# In MLflow experiment
import mlflow
import logging

logger = logging.getLogger(__name__)

with mlflow.start_run():
    logger.info(f"Starting experiment: {mlflow.active_run().info.run_id}")
    # Training...
    logger.info(f"Experiment completed: accuracy={accuracy}")
```

Query in Grafana:
```logql
{namespace="ml-platform", app="mlflow"} |= "Starting experiment"
```

### Custom Training Jobs

```python
# In Kubernetes training job
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","extra":%(extra)s}'
)

logger = logging.getLogger(__name__)

logger.info("Training started", extra=json.dumps({
    "model_type": "random_forest",
    "dataset_size": 10000
}))
```

Query in Grafana:
```logql
{namespace="ml-platform", job=~"training-.*"} | json
```

## Best Practices

### Log Formatting

1. **Use structured logging** (JSON) for easy parsing
2. **Include context** (experiment_id, run_id, user_id)
3. **Use consistent log levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. **Add timestamps** to all logs

### Query Optimization

1. **Use specific labels** to narrow down searches
2. **Add time ranges** to limit query scope
3. **Use filters** (|=, |~) before parsing (| json)
4. **Avoid regex** when possible (slower than string matching)

### Retention Strategy

1. **Production**: 30 days (compliance, debugging)
2. **Development**: 7 days (cost savings)
3. **Archive**: Export to S3 for long-term storage

### Cost Optimization

1. **Filter noisy logs** at Promtail level
2. **Sample high-volume logs** (e.g., keep 10%)
3. **Use appropriate retention** periods
4. **Enable compression** (automatic in Loki)

## Monitoring Loki

### Key Metrics

```promql
# Ingestion rate
rate(loki_ingester_bytes_received_total[5m])

# Query latency
histogram_quantile(0.99, rate(loki_request_duration_seconds_bucket[5m]))

# Active streams
loki_ingester_streams

# Storage usage
loki_storage_bytes_used / loki_storage_bytes_total
```

### Grafana Dashboards

Import official Loki dashboards:
- Dashboard ID: 13639 (Loki Stack Monitoring)
- Dashboard ID: 12611 (Loki Logs)

## Next Steps

1. ✅ Deploy Loki + Promtail
2. ✅ Configure Grafana datasource
3. ➡️ Create log dashboards for ML workflows
4. ➡️ Set up log-based alerts
5. ➡️ Configure log archival to S3
6. ➡️ Add structured logging to all services

---

**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
