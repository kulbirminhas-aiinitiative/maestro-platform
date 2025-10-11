# Airflow ML Workflow Orchestration

Apache Airflow orchestrates all ML workflows in the Maestro ML Platform, including feature materialization, model training, data validation, and deployment pipelines.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Airflow Components                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Webserver   │    │  Scheduler   │    │   Workers    │  │
│  │  (UI/API)    │    │  (DAG exec)  │    │  (Tasks)     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                    │           │
│         └───────────────────┴────────────────────┘           │
│                             │                                │
│                   ┌─────────▼─────────┐                      │
│                   │  PostgreSQL DB    │                      │
│                   │  (Metadata)       │                      │
│                   └───────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼───┐           ┌────▼────┐         ┌────▼────┐
    │ Feast │           │ MLflow  │         │  K8s    │
    │Feature│           │ Training│         │  Pods   │
    │ Store │           │ Tracking│         │         │
    └───────┘           └─────────┘         └─────────┘
```

## Production vs Minikube

| Component | Production | Minikube |
|-----------|------------|----------|
| **Executor** | CeleryExecutor | LocalExecutor |
| **Workers** | 3-20 (autoscaled) | 0 (built-in) |
| **Webserver** | 2 replicas (HA) | 1 replica |
| **Scheduler** | 2 replicas (HA) | 1 replica (with webserver) |
| **PostgreSQL** | StatefulSet (persistent) | StatefulSet (persistent) |
| **DAGs Storage** | ReadWriteMany PVC | EmptyDir |
| **Resources** | 8-16GB RAM total | 2-4GB RAM total |
| **Monitoring** | Integrated with Prometheus | Basic metrics |

## DAG Workflows

### 1. Feature Materialization (`feature_materialization.py`)

**Purpose**: Daily materialization of features from offline to online store

**Schedule**: Daily at 2 AM

**Tasks**:
1. Validate feature store configuration
2. Materialize features (last 7 days)
3. Validate online feature availability

**SLA**: 30 minutes

### 2. Model Training Pipeline (`model_training_pipeline.py`)

**Purpose**: Complete ML model training workflow

**Schedule**: Weekly on Sunday at 4 AM

**Tasks**:
1. Data validation
2. Feature engineering (get from Feast)
3. Model training (log to MLflow)
4. Model evaluation
5. Model registration (if metrics > threshold)

**Decision Logic**:
- If accuracy > 0.85: Register model to staging
- Else: Skip registration

**SLA**: 2 hours

### 3. Data Validation Pipeline (`data_validation_pipeline.py`)

**Purpose**: Automated data quality monitoring

**Schedule**: Every 6 hours

**Tasks**:
1. Schema validation
2. Data quality checks (missing, duplicates, ranges, freshness)
3. Drift detection (KS test)
4. Anomaly detection (Isolation Forest)
5. Generate quality report

**Alerts**:
- Data quality check failures
- Significant drift detected
- Anomaly rate > 10%

**SLA**: 15 minutes

## DAG Development

### Creating a New DAG

1. **Create DAG file** in `mlops/airflow/dags/`:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

default_args = {
    'owner': 'ml-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'my_ml_workflow',
    default_args=default_args,
    schedule_interval='0 0 * * *',  # Daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'custom'],
) as dag:

    task1 = KubernetesPodOperator(
        task_id='my_task',
        name='my-pod',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['python', '-c'],
        arguments=['print("Hello from Airflow")'],
    )
```

2. **Deploy DAG**:
   - Production: Copy to DAGs PVC
   - Minikube: Copy to `/opt/airflow/dags` in pod

3. **Test DAG**:
```bash
# Access Airflow pod
kubectl exec -it -n airflow <pod-name> -- bash

# Test DAG
airflow dags test my_ml_workflow 2025-01-01

# List DAGs
airflow dags list
```

## Deployment

### Production

```bash
# Apply manifests
kubectl apply -f infrastructure/kubernetes/airflow-deployment.yaml

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -n airflow -l app=airflow --timeout=5m

# Copy DAGs to PVC
kubectl cp mlops/airflow/dags/. airflow/<webserver-pod>:/opt/airflow/dags/

# Access webserver
kubectl port-forward -n airflow svc/airflow-webserver 8080:80
# → http://localhost:8080 (admin/admin)
```

### Minikube

```bash
# Apply minikube manifests
kubectl apply -f infrastructure/minikube/airflow.yaml

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -n airflow -l app=airflow --timeout=5m

# Copy DAGs
POD_NAME=$(kubectl get pod -n airflow -l app=airflow -o jsonpath='{.items[0].metadata.name}')
kubectl cp mlops/airflow/dags/. airflow/$POD_NAME:/opt/airflow/dags/

# Access webserver
kubectl port-forward -n airflow svc/airflow-webserver 8080:80
# → http://localhost:8080 (admin/admin)
```

## Configuration

### Connections

Airflow connections for external services:

```bash
# MLflow connection
airflow connections add mlflow_default \
  --conn-type http \
  --conn-host mlflow-service.mlflow.svc.cluster.local \
  --conn-port 80

# AWS S3 (MinIO) connection
airflow connections add aws_default \
  --conn-type aws \
  --conn-login admin \
  --conn-password minioadmin \
  --conn-extra '{"endpoint_url": "http://minio.storage.svc.cluster.local:9000"}'

# Feast connection
airflow connections add feast_default \
  --conn-type http \
  --conn-host feast-feature-server.feast.svc.cluster.local \
  --conn-port 80
```

### Variables

Set Airflow variables for DAG configuration:

```bash
# Model quality thresholds
airflow variables set model_accuracy_threshold 0.85
airflow variables set model_f1_threshold 0.80

# Feature materialization settings
airflow variables set feature_materialization_days 7
airflow variables set feature_offline_store s3://feast/

# Alert settings
airflow variables set alert_email ml-team@example.com
airflow variables set slack_webhook_url https://hooks.slack.com/...
```

## Monitoring

### Metrics

Airflow exports metrics to Prometheus via StatsD:

- `airflow_dag_run_duration` - DAG execution time
- `airflow_task_duration` - Task execution time
- `airflow_dag_run_success` - Successful DAG runs
- `airflow_dag_run_failed` - Failed DAG runs
- `airflow_scheduler_heartbeat` - Scheduler health

### Alerts

Prometheus alerts for Airflow:

- DAG run failures
- Long-running tasks (> SLA)
- Scheduler not responding
- High worker memory usage

### Logs

```bash
# View DAG logs
kubectl logs -n airflow -l app=airflow,component=scheduler -f

# View task logs (from UI)
# → http://localhost:8080 → DAGs → [DAG name] → Graph → [Task] → Logs

# Check PostgreSQL
kubectl exec -it -n airflow airflow-postgresql-0 -- psql -U maestro -d airflow
```

## Troubleshooting

### DAG Not Appearing in UI

```bash
# Check DAG is in dags folder
kubectl exec -n airflow <pod> -- ls -la /opt/airflow/dags/

# Check for syntax errors
kubectl exec -n airflow <pod> -- python /opt/airflow/dags/my_dag.py

# Check scheduler logs
kubectl logs -n airflow -l component=scheduler -f
```

### Task Failing

```bash
# View task logs in UI
# → DAGs → [DAG] → Graph → [Task] → Logs

# Re-run task
# → Task Instance → Clear → Confirm

# Check worker resources
kubectl top pods -n airflow -l component=worker
```

### Connection Issues

```bash
# Test connection from Airflow pod
kubectl exec -it -n airflow <pod> -- bash

# Test MLflow
curl http://mlflow-service.mlflow.svc.cluster.local/health

# Test Feast
curl http://feast-feature-server.feast.svc.cluster.local/health

# Test PostgreSQL
psql postgresql://maestro:maestro123@airflow-postgresql.airflow.svc.cluster.local:5432/airflow
```

## Best Practices

### DAG Design

1. **Idempotency**: Tasks should be re-runnable
2. **Atomicity**: Tasks should be self-contained
3. **Proper dependencies**: Use `>>` for task order
4. **Resource requests**: Set appropriate CPU/memory
5. **Timeouts**: Set execution timeouts
6. **Retries**: Configure retry logic
7. **Alerts**: Set up failure notifications

### Resource Management

```python
resources = k8s.V1ResourceRequirements(
    requests={'memory': '1Gi', 'cpu': '500m'},  # Minimum
    limits={'memory': '2Gi', 'cpu': '1000m'}    # Maximum
)
```

### Cleanup

```python
# Delete pods after completion
is_delete_operator_pod=True

# Get logs before deletion
get_logs=True
```

## Next Steps

1. ✅ Airflow deployed to production/minikube
2. ✅ 3 sample DAGs created
3. ➡️ Add more ML-specific DAGs:
   - Model deployment pipeline
   - A/B test management
   - Feature monitoring
   - Model retraining triggers
4. ➡️ Integrate with CI/CD for DAG deployment
5. ➡️ Set up Airflow monitoring dashboards
6. ➡️ Configure production alerts and SLAs

---

**Documentation Version**: 1.0
**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
