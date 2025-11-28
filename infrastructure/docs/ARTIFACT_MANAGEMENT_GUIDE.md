# Maestro Platform - Artifact Management Guide

## Overview

The Maestro Platform uses an enterprise-grade, open-source artifact management stack to handle all types of artifacts across the development lifecycle:

- **Container Images** → Harbor (with security scanning)
- **Dependencies** (PyPI, npm, Maven) → Nexus OSS
- **ML Models & Experiments** → MLflow
- **ML Datasets** → DVC (Data Version Control)
- **Storage Backend** → MinIO (dev/test) / AWS S3 (production)

This architecture provides:
✅ **Unified artifact management** across all repos
✅ **Security scanning** for vulnerabilities
✅ **Reproducibility** for ML experiments and datasets
✅ **Dependency caching** for faster builds
✅ **RBAC** for team-based access control
✅ **Hybrid deployment** (Docker Compose + Kubernetes)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Maestro Platform Repos                       │
│  maestro-hive | maestro-frontend | maestro-engine | quality-   │
│  fabric | execution-platform                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
         ┌────────────┴─────────────┬─────────────┬──────────────┐
         │                          │             │              │
         ▼                          ▼             ▼              ▼
┌──────────────────┐    ┌─────────────────┐  ┌─────────┐  ┌──────────┐
│  Harbor Registry │    │   Nexus OSS     │  │ MLflow  │  │   DVC    │
│ - Docker images  │    │ - PyPI packages │  │ - Exps  │  │ - Data   │
│ - Helm charts    │    │ - npm packages  │  │ - Models│  │ versions │
│ - Trivy scanning │    │ - Maven jars    │  │ Registry│  │          │
└────────┬─────────┘    └────────┬────────┘  └────┬────┘  └────┬─────┘
         │                       │                 │            │
         └───────────────────────┴─────────────────┴────────────┘
                                  │
                         ┌────────▼─────────┐
                         │  MinIO / AWS S3  │
                         │  Object Storage  │
                         └──────────────────┘
```

---

## Quick Start

### 1. Start Infrastructure Services

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Set passwords in .env.infrastructure
nano .env.infrastructure

# Start all artifact management services
docker-compose -f docker-compose.infrastructure.yml up -d

# Check status
docker-compose -f docker-compose.infrastructure.yml ps
```

### 2. Access Web UIs

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Harbor** | http://localhost:28080 | admin / (see .env: HARBOR_ADMIN_PASSWORD) |
| **Nexus** | http://localhost:28081 | admin / admin123 (change on first login) |
| **MLflow** | http://localhost:25000 | No auth (dev mode) |
| **MinIO Console** | http://localhost:29001 | minioadmin / (see .env: MINIO_ROOT_PASSWORD) |

### 3. Configure Local Environment

```bash
# Configure Docker, npm, and pip to use registries
cd /home/ec2-user/projects/maestro-platform/infrastructure
./scripts/configure-registries.sh --all
```

---

## Component Details

### Harbor (Container Registry)

**Purpose**: Secure container registry with vulnerability scanning and RBAC.

**Key Features**:
- Trivy-based security scanning
- Project-based access control
- Replication to other registries
- Webhook notifications

#### Initial Setup

1. **Access Harbor UI**: http://localhost:28080
2. **Login**: admin / (from .env.infrastructure)
3. **Create Projects**:
   - maestro-hive (private)
   - maestro-frontend (private)
   - maestro-engine (private)
   - execution-platform (private)
   - quality-fabric (private)

#### Building and Pushing Images

```bash
# Tag image for Harbor
docker tag my-app:latest localhost:28080/maestro-hive/my-app:v1.0.0

# Login to Harbor
docker login localhost:28080
# Username: admin
# Password: <from .env>

# Push image
docker push localhost:28080/maestro-hive/my-app:v1.0.0

# Harbor will automatically scan for vulnerabilities
```

#### Security Scanning

Harbor automatically scans images on push using Trivy.

**View scan results**:
1. Navigate to project → Repositories
2. Click on image
3. View "Vulnerabilities" tab

**Configure policies**:
- Settings → Configuration → System Settings → Deployment Security
- Enable "Prevent vulnerable images from running"
- Set CVE allowlist if needed

#### Using Harbor in Dockerfile

```dockerfile
# Before (Docker Hub)
FROM node:18-alpine

# After (Harbor proxy)
FROM localhost:28080/library/node:18-alpine
```

---

### Nexus OSS (Universal Repository)

**Purpose**: Multi-format artifact repository for dependencies and packages.

**Supported Formats**:
- PyPI (Python packages)
- npm (JavaScript/TypeScript)
- Docker (proxy to Docker Hub)
- Maven (Java/Kotlin)
- Raw (generic artifacts)

#### Initial Setup

1. **Access Nexus**: http://localhost:28081
2. **First login**: admin / admin123
3. **Change password** when prompted
4. **Create Repositories**:

##### PyPI Repository (Python)

Create these repositories:
- **pypi-proxy**: Proxy to pypi.org
- **pypi-hosted**: For internal Python packages
- **pypi-group**: Combines proxy + hosted

Configuration:
```
Name: pypi-group
Type: group
Members: pypi-proxy, pypi-hosted
```

##### npm Repository (Node.js)

Create these repositories:
- **npm-proxy**: Proxy to npmjs.com
- **npm-hosted**: For internal npm packages
- **npm-group**: Combines proxy + hosted

#### Using Nexus Repositories

##### PyPI (Python)

**Install packages**:
```bash
# Configure pip (done via configure-registries.sh)
pip install requests

# Or use directly
pip install --index-url http://localhost:28083/repository/pypi-group/simple requests
```

**Publish packages**:
```bash
# Build package
python setup.py sdist bdist_wheel

# Upload to Nexus
twine upload --repository-url http://localhost:28083/repository/pypi-hosted/ \
  --username <nexus-user> \
  --password <nexus-password> \
  dist/*
```

##### npm (Node.js)

**Install packages**:
```bash
# Configure npm (done via configure-registries.sh)
npm install express

# Or use .npmrc in project
echo "registry=http://localhost:28084/repository/npm-group/" > .npmrc
npm install
```

**Publish packages**:
```bash
# Login
npm login --registry=http://localhost:28084/repository/npm-hosted/

# Publish
npm publish --registry=http://localhost:28084/repository/npm-hosted/
```

---

### MLflow (ML Experiment Tracking)

**Purpose**: Track ML experiments, parameters, metrics, and models.

**Backend**: PostgreSQL (mlflow database)
**Artifact Storage**: MinIO (mlflow-artifacts bucket)

#### Using MLflow in Python

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:25000")

# Create experiment
mlflow.set_experiment("customer-churn-prediction")

# Start run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)

    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X_train, y_train)

    # Log metrics
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("f1_score", f1_score(y_test, model.predict(X_test)))

    # Log model
    mlflow.sklearn.log_model(model, "model")

    # Log artifacts (plots, etc.)
    fig = plot_confusion_matrix(model, X_test, y_test)
    mlflow.log_figure(fig, "confusion_matrix.png")

    print(f"Run ID: {mlflow.active_run().info.run_id}")
```

#### Model Registry

**Register a model**:
```python
# In your training script
mlflow.sklearn.log_model(model, "model", registered_model_name="churn-predictor")

# Or register an existing run
model_uri = f"runs:/{run_id}/model"
mlflow.register_model(model_uri, "churn-predictor")
```

**Promote model to production**:
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Transition to Production
client.transition_model_version_stage(
    name="churn-predictor",
    version=3,
    stage="Production"
)
```

**Load production model**:
```python
import mlflow.pyfunc

# Load latest production model
model = mlflow.pyfunc.load_model("models:/churn-predictor/Production")

# Make predictions
predictions = model.predict(new_data)
```

---

### DVC (Data Version Control)

**Purpose**: Git-like version control for large datasets.

**Storage**: MinIO (dev) / AWS S3 (production)

See detailed guide: [DVC_QUICKSTART.md](./DVC_QUICKSTART.md)

#### Quick Example

```bash
# Initialize DVC in your ML project
cd /home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml
dvc init

# Copy DVC config template
cp /home/ec2-user/projects/maestro-platform/infrastructure/templates/dvc/.dvc/config .dvc/config

# Track a dataset
dvc add data/raw/train.parquet

# Commit to Git
git add data/raw/train.parquet.dvc .gitignore
git commit -m "Track training dataset"

# Push data to remote storage
dvc push
```

---

### MinIO (Object Storage)

**Purpose**: S3-compatible storage for development and testing.

**Access**: http://localhost:29001

**Buckets** (auto-created):
- `mlflow-artifacts`: MLflow experiment artifacts
- `dvc-storage`: DVC datasets
- `nexus-blobs`: Nexus blob storage
- `harbor-registry`: Harbor container images
- `backups`: Infrastructure backups

#### Using MinIO from Python

```python
import boto3

# Configure S3 client for MinIO
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:29000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='<minio-password>',
    region_name='us-east-1'
)

# Upload file
s3.upload_file('local-file.txt', 'dvc-storage', 'remote-file.txt')

# Download file
s3.download_file('dvc-storage', 'remote-file.txt', 'downloaded-file.txt')
```

---

## Multi-Repository Workflows

### Sharing Datasets Across Repos

Use DVC import to share datasets:

```bash
# In maestro-frontend project
dvc import https://github.com/your-org/maestro-data datasets/customer_segmentation.parquet

# Or use dvc.api in Python
import dvc.api

with dvc.api.open(
    'datasets/customer_segmentation.parquet',
    repo='https://github.com/your-org/maestro-data',
    rev='v1.0'
) as f:
    df = pd.read_parquet(f)
```

### Sharing Docker Base Images

Create shared base images in Harbor:

```dockerfile
# In maestro-base-images repo
FROM python:3.11-slim
RUN pip install mlflow dvc[s3] pandas numpy
# Build and push
docker build -t localhost:28080/maestro-platform/python-ml-base:1.0 .
docker push localhost:28080/maestro-platform/python-ml-base:1.0
```

Use in other repos:
```dockerfile
# In maestro-hive Dockerfile
FROM localhost:28080/maestro-platform/python-ml-base:1.0
COPY . /app
```

### Sharing Python Packages

Publish shared utilities to Nexus:

```bash
# In shared/ repo
python setup.py sdist bdist_wheel
twine upload --repository-url http://localhost:28083/repository/pypi-hosted/ dist/*
```

Install in other repos:
```bash
# requirements.txt
maestro-shared-utils==1.0.0
```

---

## Production Deployment

### Switch to AWS S3

Update `.env.infrastructure`:

```bash
# Change from MinIO to S3
ARTIFACT_STORAGE_TYPE=s3
ARTIFACT_STORAGE_ENDPOINT=https://s3.amazonaws.com
ARTIFACT_STORAGE_REGION=us-east-1
# Use IAM roles or set:
# ARTIFACT_STORAGE_ACCESS_KEY=<AWS_ACCESS_KEY>
# ARTIFACT_STORAGE_SECRET_KEY=<AWS_SECRET_KEY>
```

Update DVC config:
```bash
dvc remote default s3-prod
dvc push
```

Update MLflow:
```python
os.environ['MLFLOW_S3_ENDPOINT_URL'] = 'https://s3.amazonaws.com'
```

### Kubernetes Deployment

See [K8s deployment guide](./K8S_DEPLOYMENT.md) for deploying to Kubernetes.

---

## Security Best Practices

### 1. Vulnerability Scanning

- Harbor automatically scans all images
- Review scan reports before deploying
- Set up policies to block critical CVEs

### 2. Access Control

**Harbor**:
- Use project-level RBAC
- Create robot accounts for CI/CD
- Enable content trust (Docker Content Trust)

**Nexus**:
- Create service accounts per project
- Use roles for team-based access
- Enable LDAP/AD integration for enterprise

### 3. Secrets Management

Never commit credentials:
```bash
# .gitignore
.env
.env.infrastructure
.dvc/config.local
```

Use environment variables or secret managers:
```python
# Bad
mlflow.set_tracking_uri("http://admin:password@mlflow:5000")

# Good
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
```

---

## Monitoring and Observability

### Metrics Exported

All services export Prometheus metrics:

- **Harbor**: http://localhost:28080/metrics
- **Nexus**: http://localhost:28081/service/metrics/prometheus
- **MinIO**: http://localhost:29000/minio/v2/metrics/cluster
- **MLflow**: Custom exporter (see monitoring guide)

### Grafana Dashboards

Pre-configured dashboards in Grafana (http://localhost:23000):

- Artifact Registry Usage
- MLflow Experiment Metrics
- Storage Capacity & Growth
- Security Scan Results

---

## Troubleshooting

### Harbor issues

**Cannot push images**:
```bash
# Check Harbor is running
docker ps | grep harbor

# Check logs
docker logs maestro-harbor-core

# Verify DNS resolution
ping localhost

# Re-login
docker logout localhost:28080
docker login localhost:28080
```

### Nexus issues

**Cannot pull packages**:
```bash
# Check Nexus status
curl http://localhost:28081/service/rest/v1/status

# Clear pip cache
pip cache purge

# Clear npm cache
npm cache clean --force
```

### MLflow issues

**Cannot connect**:
```bash
# Check MLflow is running
curl http://localhost:25000/health

# Check database connection
docker exec maestro-postgres psql -U maestro_admin -c "\\l" | grep mlflow

# Check MinIO bucket
docker exec maestro-minio-init mc ls maestro/mlflow-artifacts
```

### DVC issues

**Cannot push/pull data**:
```bash
# Verify remote
dvc remote list

# Test connection to MinIO
curl http://localhost:29000/minio/health/live

# Force push
dvc push --force
```

---

## Backup and Disaster Recovery

### Automated Backups

See [backup guide](./BACKUP_DISASTER_RECOVERY.md) for automated backup procedures.

### Manual Backup

```bash
# PostgreSQL databases
docker exec maestro-postgres pg_dumpall -U maestro_admin > backup_$(date +%Y%m%d).sql

# MinIO data
docker exec maestro-minio-init mc mirror maestro/ /backups/

# Harbor images
# Use Harbor's built-in replication to backup registry

# Nexus blobs
docker cp maestro-nexus:/nexus-data nexus_backup_$(date +%Y%m%d)
```

---

## Migration from Old Systems

### Migrating from pypiserver to Nexus

See [PYPI_MIGRATION_GUIDE.md](./PYPI_MIGRATION_GUIDE.md)

### Migrating from Docker Hub

Update Dockerfiles:
```dockerfile
# Old
FROM python:3.11

# New
FROM localhost:28080/library/python:3.11
```

### Migrating existing MLflow experiments

```python
# Export from old MLflow
mlflow experiments csv --experiment-id 1 > exp1.csv

# Import to new MLflow
mlflow.set_tracking_uri("http://localhost:25000")
# Re-run experiments or manually import
```

---

## Support and Resources

- **Documentation**: /infrastructure/docs/
- **Slack**: #maestro-infrastructure
- **Issues**: GitHub Issues in maestro-platform repo

### External Resources

- [Harbor Documentation](https://goharbor.io/docs/)
- [Nexus OSS Documentation](https://help.sonatype.com/repomanager3)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [DVC Documentation](https://dvc.org/doc)
- [MinIO Documentation](https://min.io/docs/)

---

## Changelog

- **2025-10-24**: Initial implementation
  - Added Harbor, Nexus, MLflow (enhanced), MinIO
  - DVC integration with template configs
  - Multi-repo support
  - Hybrid Docker Compose + Kubernetes deployment
