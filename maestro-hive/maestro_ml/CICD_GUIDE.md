# CI/CD Pipeline Guide

## Overview

The ML platform uses **GitHub Actions** for continuous integration and deployment with dedicated pipelines for:
1. **ML Training** - Automated model training and evaluation
2. **Model Deployment** - Deploying models to staging/production
3. **Infrastructure** - Managing Kubernetes and cloud resources
4. **Data Pipelines** - Testing and deploying data workflows

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  CI/CD Pipeline Flow                      │
└──────────────────────────────────────────────────────────┘

Developer Workflow:
┌──────────┐
│   Code   │
│  Change  │
└────┬─────┘
     │
     ▼
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│   Push   │────▶│  GitHub      │────▶│  CI Checks  │
│ to Repo  │     │  Actions     │     │  • Lint     │
└──────────┘     └──────────────┘     │  • Test     │
                                       │  • Build    │
                                       └──────┬──────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                         ▼                    ▼                    ▼
                  ┌──────────┐        ┌──────────┐        ┌──────────┐
                  │  Train   │        │  Deploy  │        │ Infra    │
                  │  Model   │        │  Model   │        │ Deploy   │
                  └────┬─────┘        └────┬─────┘        └────┬─────┘
                       │                   │                   │
                       ▼                   ▼                   ▼
                  ┌──────────┐        ┌──────────┐        ┌──────────┐
                  │ MLflow   │        │ K8s      │        │ Terraform│
                  │ Registry │        │ Cluster  │        │ & K8s    │
                  └──────────┘        └──────────┘        └──────────┘
```

## Pipelines

### 1. ML Training Pipeline

**File**: `.github/workflows/ml-training-pipeline.yml`

**Triggers**:
- Push to `main`/`develop` (changes in `mlops/training/**`)
- Pull requests to `main`
- Manual workflow dispatch

**Jobs**:
1. **Code Quality** - Black, Flake8, MyPy, unit tests
2. **Data Validation** - Validate training data, check drift
3. **Build Image** - Build training container, scan for vulnerabilities
4. **Train Model** - Trigger Airflow DAG, run training
5. **Evaluate** - Check metrics against quality gates
6. **Register** - Register model in MLflow if quality gates pass
7. **Deploy Staging** - Optional deployment to staging
8. **Notify** - Send Slack notifications

**Quality Gates**:
- Code coverage > 80%
- Model accuracy > 0.85
- Model F1 score > 0.80
- No critical vulnerabilities in container

**Example Usage**:
```bash
# Automatic trigger on push
git push origin main

# Manual trigger
gh workflow run ml-training-pipeline.yml \
  -f experiment_name=my-experiment \
  -f model_type=random_forest
```

### 2. Model Deployment Pipeline

**File**: `.github/workflows/model-deployment.yml`

**Triggers**:
- Manual workflow dispatch (production deployments)
- Push tags `model-v*`

**Jobs**:
1. **Build Inference** - Build inference container with model
2. **Test Inference** - Container tests, load tests
3. **Deploy Staging** - Deploy to staging environment
4. **Deploy Production** - Deploy with selected strategy:
   - **Rolling**: Gradual pod replacement
   - **Blue-Green**: Deploy to new environment, switch traffic
   - **Canary**: Deploy to subset (10%), monitor, promote
5. **Monitor** - Check metrics, SLOs after deployment
6. **Update Registry** - Transition model stage to Production
7. **Notify** - Send deployment notifications

**Deployment Strategies**:

**Rolling** (default):
```yaml
# Gradual update, no downtime
maxSurge: 1
maxUnavailable: 0
```

**Blue-Green**:
```bash
# Deploy green, test, switch traffic
helm install model-server-green ...
kubectl patch service ... selector=green
helm uninstall model-server-blue
```

**Canary**:
```bash
# 10% traffic to new version
# Monitor for 10 minutes
# Promote to 100% if healthy
```

**Example Usage**:
```bash
# Deploy model v5 to production with canary
gh workflow run model-deployment.yml \
  -f model_name=ml-platform-model \
  -f model_version=5 \
  -f environment=production \
  -f deployment_strategy=canary
```

### 3. Infrastructure Deployment Pipeline

**File**: `.github/workflows/infrastructure-deployment.yml`

**Triggers**:
- Push to `main` (changes in `infrastructure/**`, `terraform/**`)
- Pull requests (shows Terraform plan)
- Manual workflow dispatch

**Jobs**:
1. **Validate** - Terraform format, validate, kubeval
2. **Security Scan** - tfsec, checkov, Trivy
3. **Terraform Plan** - Show plan in PR comments
4. **Deploy Staging** - Apply Terraform, deploy K8s resources
5. **Deploy Production** - Production deployment (manual approval)
6. **Integration Tests** - Run end-to-end tests
7. **Backup** - Backup Terraform state, K8s configs
8. **Notify** - Send deployment notifications

**Example Usage**:
```bash
# Deploy specific component to staging
gh workflow run infrastructure-deployment.yml \
  -f environment=staging \
  -f component=airflow

# Deploy all components to production
gh workflow run infrastructure-deployment.yml \
  -f environment=production \
  -f component=all
```

## Setup Instructions

### 1. GitHub Secrets

Configure these secrets in GitHub repository settings:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# Container Registry
CONTAINER_REGISTRY=registry.example.com
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=<password>

# MLflow
MLFLOW_TRACKING_URI=https://mlflow.example.com

# Airflow
AIRFLOW_API_URL=https://airflow.example.com
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=<password>

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: External services
OPENAI_API_KEY=sk-...
HUGGINGFACE_TOKEN=hf_...
```

### 2. GitHub Environments

Create environments with protection rules:

**Staging**:
```yaml
# No approvals needed
deployment_branch_policy:
  protected_branches: true
```

**Production**:
```yaml
# Require manual approval
protection_rules:
  - type: required_reviewers
    reviewers: 2
  - type: wait_timer
    wait_timer: 300  # 5 minutes
deployment_branch_policy:
  protected_branches: true
  custom_branch_policies:
    - name: main
```

### 3. Required Files

Create these helper scripts:

**`scripts/wait-for-dag-completion.sh`**:
```bash
#!/bin/bash
DAG_ID=$1
TIMEOUT=$2

# Poll Airflow API for DAG run status
# Wait until success or timeout
```

**`scripts/get-mlflow-metrics.py`**:
```python
import mlflow
import argparse

# Get metrics from latest MLflow run
# Output to stdout or file
```

**`scripts/check-quality-gate.py`**:
```python
import json
import sys

# Check if metrics meet quality gates
# Exit 1 if failed, 0 if passed
```

**`scripts/monitor-canary.py`**:
```python
# Monitor canary deployment metrics
# Compare with baseline
# Return success/failure
```

**`scripts/health-check.sh`**:
```bash
#!/bin/bash
ENV=$1

# Check all service health endpoints
# Verify readiness
```

## Workflow Patterns

### Pattern 1: Feature Branch Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-model

# 2. Make changes, push
git push origin feature/new-model

# 3. Create PR (triggers CI checks)
gh pr create

# 4. CI runs:
#    - Code quality checks
#    - Unit tests
#    - Data validation
#    - Terraform plan (if infra changed)

# 5. Review and merge (triggers deployment)
gh pr merge

# 6. Main branch CI runs:
#    - Train model
#    - Deploy to staging
```

### Pattern 2: Model Release Workflow

```bash
# 1. Train model (via PR merge or manual trigger)
gh workflow run ml-training-pipeline.yml

# 2. Model passes quality gates, registered in MLflow

# 3. Test in staging (automatic or manual)

# 4. Deploy to production (manual, requires approval)
gh workflow run model-deployment.yml \
  -f model_name=ml-platform-model \
  -f model_version=7 \
  -f environment=production \
  -f deployment_strategy=canary

# 5. Monitor deployment

# 6. Model transitioned to Production stage in MLflow
```

### Pattern 3: Hotfix Workflow

```bash
# 1. Create hotfix branch from main
git checkout -b hotfix/fix-inference

# 2. Fix issue, test locally

# 3. Push and create PR
git push origin hotfix/fix-inference
gh pr create --base main

# 4. CI validates changes

# 5. Emergency merge (bypass some approvals if configured)
gh pr merge --admin

# 6. Deploy to production immediately
gh workflow run model-deployment.yml \
  -f environment=production \
  -f deployment_strategy=rolling
```

## Best Practices

### Code Quality

1. **Use pre-commit hooks**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
```

2. **Enforce coverage thresholds**:
```yaml
- name: Check coverage
  run: |
    pytest --cov=mlops --cov-fail-under=80
```

### Security

1. **Scan all images**:
```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    severity: 'CRITICAL,HIGH'
    exit-code: 1  # Fail on findings
```

2. **Use secrets scanner**:
```yaml
- name: Scan for secrets
  uses: trufflesecurity/trufflehog@main
```

### Performance

1. **Cache dependencies**:
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
```

2. **Parallel jobs**:
```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
```

### Monitoring

1. **Track deployment metrics**:
```python
# In deployment script
import mlflow

mlflow.log_metrics({
    "deployment_duration": duration,
    "deployment_status": 1 if success else 0
})
```

2. **Set up alerts**:
```yaml
# In Prometheus
- alert: DeploymentFailed
  expr: deployment_status == 0
  for: 5m
```

## Troubleshooting

### Workflow Fails at Build Step

```bash
# Check build logs
gh run view <run-id> --log

# Common issues:
# - Dockerfile not found: check path
# - Build context too large: add .dockerignore
# - Registry auth failed: check secrets
```

### Model Training Timeout

```bash
# Increase timeout in workflow
timeout-minutes: 120  # 2 hours

# Or split into separate jobs
# - Job 1: Trigger training
# - Job 2: Wait and monitor (with longer timeout)
```

### Deployment Rollback

```bash
# Automatic rollback on failure (in workflow)
- name: Rollback if failed
  if: failure()
  run: helm rollback model-server

# Manual rollback
helm rollback model-server -n ml-platform
kubectl rollout undo deployment/model-server -n ml-platform
```

### Secrets Not Available

```bash
# Verify secret exists
gh secret list

# Set secret
gh secret set AWS_ACCESS_KEY_ID

# Check environment secrets
gh secret list --env production
```

## Metrics and Reporting

### Deployment Frequency

Track via GitHub Actions metrics:
```bash
gh run list --workflow=model-deployment.yml \
  --json status,conclusion,createdAt \
  --jq '.[] | select(.conclusion=="success")' | wc -l
```

### Lead Time for Changes

```bash
# Time from commit to production
gh run list --workflow=ml-training-pipeline.yml \
  --json databaseId,createdAt,updatedAt,conclusion
```

### Mean Time to Recovery (MTTR)

```bash
# Track rollback frequency and duration
gh run list --workflow=model-deployment.yml \
  --json status,name | grep -i rollback
```

## Next Steps

1. ✅ Set up GitHub secrets
2. ✅ Create GitHub environments
3. ✅ Add helper scripts
4. ➡️ Test workflows in staging
5. ➡️ Configure Slack notifications
6. ➡️ Set up deployment dashboards
7. ➡️ Document runbooks

---

**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
