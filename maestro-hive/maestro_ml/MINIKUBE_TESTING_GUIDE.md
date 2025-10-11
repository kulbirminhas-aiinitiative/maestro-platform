# Maestro ML Platform - Minikube Local Testing Guide

**Purpose**: Test the complete ML platform locally before production deployment
**Environment**: Minikube on your laptop/workstation
**Duration**: ~30 minutes setup, unlimited testing
**Cost**: $0 (runs locally)

---

## Prerequisites

### Required Software
- **Minikube** >= 1.30.0 - [Install Guide](https://minikube.sigs.k8s.io/docs/start/)
- **kubectl** >= 1.28.0 - [Install Guide](https://kubernetes.io/docs/tasks/tools/)
- **Docker** or **Podman** - Container runtime
- **Helm** (optional) - For monitoring stack

### System Requirements
- **CPU**: 4+ cores (recommended 8)
- **Memory**: 8GB+ RAM (recommended 16GB)
- **Disk**: 40GB+ free space
- **OS**: Linux, macOS, or Windows with WSL2

### Quick Install (macOS)
```bash
# Install minikube
brew install minikube kubectl helm

# Verify installation
minikube version
kubectl version --client
```

### Quick Install (Linux)
```bash
# Install minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

---

## Quick Start (5 minutes)

### 1. Start Minikube Test Environment
```bash
cd maestro_ml
./scripts/setup-minikube-test.sh
```

**This script will**:
- ✅ Start minikube cluster (4 CPUs, 8GB RAM)
- ✅ Enable required addons (metrics, ingress, storage)
- ✅ Install Prometheus + Grafana monitoring (via Helm)
- ✅ Deploy PostgreSQL (for MLflow + Feast + Airflow)
- ✅ Deploy Redis (for Feast online store)
- ✅ Deploy MinIO (S3-compatible storage)
- ✅ Deploy MLflow tracking server
- ✅ Deploy Feast feature server
- ✅ Deploy Airflow orchestration
- ✅ Configure monitoring (ServiceMonitors, Alerts)

**Duration**: ~5-10 minutes

### 2. Validate Deployment
```bash
./scripts/validate-minikube.sh
```

**Tests**:
- Cluster connectivity
- All pods running
- Service connectivity
- MLflow health
- Feast health
- MinIO buckets
- Monitoring stack

### 3. Access Services

**MLflow** (Experiment Tracking):
```bash
kubectl port-forward -n mlflow svc/mlflow-service 5000:80
```
→ http://localhost:5000

**Feast** (Feature Store):
```bash
kubectl port-forward -n feast svc/feast-feature-server 6566:80
```
→ http://localhost:6566

**MinIO Console** (S3 Storage):
```bash
kubectl port-forward -n storage svc/minio 9001:9001
```
→ http://localhost:9001 (admin/minioadmin)

**Grafana** (Monitoring):
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```
→ http://localhost:3000 (admin/admin)

**Prometheus**:
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
```
→ http://localhost:9090

**Airflow** (Workflow Orchestration):
```bash
kubectl port-forward -n airflow svc/airflow-webserver 8080:80
```
→ http://localhost:8080 (admin/admin)

---

## Architecture

### Local Stack vs Production

| Component | Production | Minikube | Notes |
|-----------|------------|----------|-------|
| **K8s Cluster** | AWS EKS | Minikube | Single-node vs multi-node |
| **PostgreSQL** | RDS | StatefulSet | Persistent volume |
| **Redis** | ElastiCache | StatefulSet | Persistent volume |
| **S3 Storage** | AWS S3 | MinIO | S3-compatible API |
| **Monitoring** | Managed | kube-prometheus-stack | Full Prometheus + Grafana |
| **GPU Nodes** | g4dn.xlarge | N/A | CPU-only in minikube |
| **Load Balancer** | AWS ALB | NodePort | Local access only |

### Resource Allocation

**Minikube Cluster**:
- CPUs: 4 (configurable: `MINIKUBE_CPUS=8`)
- Memory: 8GB (configurable: `MINIKUBE_MEMORY=16384`)
- Disk: 40GB (configurable: `MINIKUBE_DISK=80g`)

**Per-Service Resources**:
| Service | Requests | Limits | Storage |
|---------|----------|--------|---------|
| PostgreSQL | 256Mi/100m | 512Mi/500m | 5Gi |
| Redis | 256Mi/100m | 512Mi/500m | 2Gi |
| MinIO | 256Mi/100m | 1Gi/500m | 10Gi |
| MLflow | 256Mi/100m | 512Mi/500m | - |
| Feast | 256Mi/100m | 512Mi/500m | - |
| Airflow | 1Gi/500m | 2Gi/1000m | 2Gi |
| Airflow DB | 256Mi/100m | 512Mi/500m | 2Gi |

**Total**: ~3GB RAM, ~24GB disk

---

## Testing Workflows

### Test 1: MLflow Experiment Tracking

**1. Create a test experiment**:
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("minikube-test")

with mlflow.start_run():
    mlflow.log_param("test_param", "value")
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_artifact("model.pkl")
```

**2. Verify in UI**: http://localhost:5000

**3. Check artifact storage in MinIO**: http://localhost:9001

### Test 2: Feast Feature Store

**1. Apply feature definitions**:
```bash
cd mlops/feast/feature_repo

# Update feature_store.yaml to use minikube services
cat > feature_store.yaml <<EOF
project: maestro_ml
provider: local
registry:
  registry_type: sql
  path: postgresql://maestro:maestro123@localhost:5432/feast_registry
online_store:
  type: redis
  connection_string: "localhost:6379"
offline_store:
  type: file
  path: /tmp/feast/offline
EOF

# Port-forward services first
kubectl port-forward -n storage svc/postgresql 5432:5432 &
kubectl port-forward -n storage svc/redis 6379:6379 &

# Apply features
feast apply
```

**2. Test feature retrieval**:
```python
from feast import FeatureStore

store = FeatureStore(repo_path=".")

# Get online features
features = store.get_online_features(
    features=["user_profile_features:skill_score_backend"],
    entity_rows=[{"user_id": "user_123"}]
).to_dict()

print(features)
```

### Test 3: Monitoring & Alerts

**1. View Grafana dashboards**:
- Access Grafana: http://localhost:3000
- Navigate to: Dashboards → ML Platform
- View: ML Platform Overview, GPU Monitoring

**2. Test Prometheus queries**:
- Access Prometheus: http://localhost:9090
- Query: `up{job="mlflow-metrics"}`
- Query: `feast_feature_request_duration_seconds`

**3. Trigger an alert**:
```bash
# Simulate MLflow being down
kubectl scale deployment -n mlflow mlflow-server --replicas=0

# Wait 5 minutes, then check alerts in Prometheus
# Go to: Alerts tab in Prometheus UI

# Restore
kubectl scale deployment -n mlflow mlflow-server --replicas=1
```

### Test 4: Airflow Workflows

**1. Access Airflow UI**:
```bash
kubectl port-forward -n airflow svc/airflow-webserver 8080:80
```
→ http://localhost:8080 (admin/admin)

**2. View DAGs**:
- Navigate to DAGs page
- You should see 3 DAGs:
  - `feast_feature_materialization` - Daily feature updates
  - `ml_model_training_pipeline` - Weekly model training
  - `data_validation_pipeline` - Every 6 hours data quality checks

**3. Manually trigger a DAG**:
```bash
# In the Airflow UI:
# 1. Click on a DAG name
# 2. Click the "Play" button (▶) in the top right
# 3. Click "Trigger DAG"
# 4. Monitor progress in Graph view
```

**4. Check DAG logs**:
```bash
# View scheduler logs
kubectl logs -n airflow -l app=airflow -f

# Or use the UI:
# DAGs → [DAG name] → Graph → [Task] → Logs
```

**5. Test feature materialization DAG**:
```bash
# Trigger the DAG via CLI
AIRFLOW_POD=$(kubectl get pod -n airflow -l app=airflow -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n airflow $AIRFLOW_POD -- airflow dags trigger feast_feature_materialization

# Check run status
kubectl exec -n airflow $AIRFLOW_POD -- airflow dags list-runs -d feast_feature_materialization
```

### Test 5: Data Pipeline

**1. Create sample feature data**:
```python
import pandas as pd
from datetime import datetime

# Sample user features
user_features = pd.DataFrame({
    "user_id": ["user_1", "user_2", "user_3"],
    "skill_score_backend": [0.8, 0.6, 0.9],
    "skill_score_frontend": [0.5, 0.9, 0.7],
    "event_timestamp": [datetime.now()] * 3
})

# Save to parquet
user_features.to_parquet("user_features.parquet")
```

**2. Upload to MinIO**:
```bash
# Port-forward MinIO
kubectl port-forward -n storage svc/minio 9000:9000

# Upload using mc client or MinIO console
mc alias set local http://localhost:9000 admin minioadmin
mc cp user_features.parquet local/feast/data/
```

**3. Materialize features**:
```bash
cd mlops/feast/feature_repo
feast materialize-incremental $(date +%Y-%m-%d)
```

---

## Debugging

### View Logs
```bash
# MLflow
kubectl logs -n mlflow -l app=mlflow -f

# Feast
kubectl logs -n feast -l app=feast -f

# PostgreSQL
kubectl logs -n storage -l app=postgresql -f

# All pods in a namespace
kubectl logs -n mlflow --all-containers -f
```

### Exec into Pods
```bash
# PostgreSQL
kubectl exec -it -n storage postgresql-0 -- psql -U maestro -d mlflow

# Redis
kubectl exec -it -n storage redis-0 -- redis-cli

# MLflow
kubectl exec -it -n mlflow <pod-name> -- /bin/bash
```

### Check Resources
```bash
# Node resources
kubectl top node

# Pod resources
kubectl top pods -n storage
kubectl top pods -n mlflow
kubectl top pods -n feast

# Describe pod (events, status)
kubectl describe pod -n mlflow <pod-name>
```

### Common Issues

**Issue**: Pods stuck in Pending
```bash
# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Usually means not enough resources
# Solution: Increase minikube resources or scale down replicas
```

**Issue**: MLflow can't connect to PostgreSQL
```bash
# Check service DNS
kubectl exec -n mlflow <pod> -- nslookup postgresql.storage.svc.cluster.local

# Check PostgreSQL is accepting connections
kubectl exec -n storage postgresql-0 -- pg_isready
```

**Issue**: Feast can't connect to Redis
```bash
# Test Redis connection from Feast pod
kubectl exec -n feast <pod> -- redis-cli -h redis.storage.svc.cluster.local ping
```

**Issue**: MinIO buckets not created
```bash
# Check MinIO init job
kubectl logs -n storage job/minio-init

# Manually create buckets
kubectl exec -n storage <minio-pod> -- mc mb local/mlflow
```

---

## Performance Testing

### Stress Test MLflow
```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Port-forward MLflow
kubectl port-forward -n mlflow svc/mlflow-service 5000:80

# Run load test
hey -n 1000 -c 10 http://localhost:5000/health

# Monitor resources
kubectl top pods -n mlflow
```

### Stress Test Feast
```python
import concurrent.futures
from feast import FeatureStore

store = FeatureStore(repo_path=".")

def get_features(user_id):
    return store.get_online_features(
        features=["user_profile_features:skill_score_backend"],
        entity_rows=[{"user_id": user_id}]
    ).to_dict()

# Concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(get_features, f"user_{i}") for i in range(100)]
    results = [f.result() for f in futures]
```

---

## Cleanup

### Stop (Preserve State)
```bash
minikube stop
```
Resume later with `minikube start`

### Delete Everything
```bash
minikube delete
```

### Delete Only ML Platform
```bash
kubectl delete namespace mlflow feast airflow storage ml-monitoring
```

### Delete Monitoring Stack
```bash
helm uninstall kube-prometheus-stack -n monitoring
kubectl delete namespace monitoring
```

---

## Comparing to Production

### What Works the Same
✅ All Kubernetes manifests (portable)
✅ MLflow API and functionality
✅ Feast feature definitions and serving
✅ Prometheus metrics collection
✅ Grafana dashboards
✅ Service discovery (DNS)
✅ ConfigMaps and Secrets

### What's Different
⚠️ Storage: MinIO instead of S3
⚠️ Database: Pod-based PostgreSQL instead of RDS
⚠️ Cache: Pod-based Redis instead of ElastiCache
⚠️ Networking: NodePort instead of LoadBalancer/Ingress
⚠️ No GPU nodes
⚠️ Single-node cluster (no HA)
⚠️ Limited resources

### Migration to Production
When ready for production:
1. Update manifests: `infrastructure/kubernetes/` (use production versions)
2. Deploy Terraform: `cd infrastructure/terraform && terraform apply`
3. Update DNS: Point domains to production ingresses
4. Migrate data: Export from MinIO/PostgreSQL, import to S3/RDS
5. Update monitoring: Deploy to production Prometheus/Grafana

---

## Next Steps After Testing

1. ✅ Validate all services work locally
2. ✅ Test Airflow DAG orchestration
3. ✅ Test ML training workflows
4. ✅ Test feature materialization
5. ✅ Review monitoring dashboards
6. ✅ Document any issues or improvements
7. ➡️ Deploy to production AWS environment
8. ➡️ Set up production CI/CD pipelines
9. ➡️ Implement production data pipelines

---

## FAQ

**Q: Can I run this in CI/CD?**
A: Yes! GitHub Actions, GitLab CI, etc. support minikube. Useful for integration tests.

**Q: How do I increase resources?**
A: Set environment variables before running setup:
```bash
export MINIKUBE_CPUS=8
export MINIKUBE_MEMORY=16384
./scripts/setup-minikube-test.sh
```

**Q: Can I test GPU workloads?**
A: No, minikube doesn't support GPU passthrough. Test GPU code on production or cloud GPU instance.

**Q: How do I persist data between minikube restarts?**
A: Data in PersistentVolumes survives `minikube stop`. Only `minikube delete` removes it.

**Q: Can multiple people share a minikube environment?**
A: Not recommended. Each developer should have their own local minikube.

**Q: What about Windows?**
A: Use WSL2 with minikube. Follow Windows-specific installation guides.

---

**Last Updated**: 2025-10-04
**Version**: 1.0
**Status**: Ready for testing ✅
