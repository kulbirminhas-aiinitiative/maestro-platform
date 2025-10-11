# Sunday.com Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Strategies](#deployment-strategies)
5. [Step-by-Step Deployment Process](#step-by-step-deployment-process)
6. [Production Deployment](#production-deployment)
7. [Post-Deployment Validation](#post-deployment-validation)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide provides comprehensive instructions for deploying Sunday.com across different environments (development, staging, production). The platform uses a cloud-native architecture with Kubernetes orchestration, supporting both automated CI/CD deployments and manual deployment procedures.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Deployment Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│  Developer → Git Push → GitHub Actions → Docker Build →        │
│  Security Scan → Container Registry → Kubernetes Deploy →      │
│  Smoke Tests → Production Verification                         │
└─────────────────────────────────────────────────────────────────┘
```

### Supported Deployment Strategies

- **Rolling Deployments**: For regular updates with minimal downtime
- **Blue-Green Deployments**: For major releases requiring zero downtime
- **Canary Deployments**: For gradual rollout with risk mitigation
- **Hotfix Deployments**: For emergency patches and critical fixes

---

## Prerequisites

### Required Tools

```bash
# Install required tools
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Access Requirements

- **AWS Account**: Access to EKS clusters, RDS, ElastiCache
- **GitHub Access**: Repository read/write permissions
- **Container Registry**: GHCR or ECR push/pull permissions
- **Kubernetes RBAC**: Deployment permissions for target namespaces

### Environment Access

| Environment | EKS Cluster | Region | Purpose |
|-------------|-------------|--------|---------|
| Development | sunday-dev | us-east-1 | Local development testing |
| Staging | sunday-staging | us-east-1 | Pre-production validation |
| Production | sunday-production | us-east-1 | Live application |
| DR | sunday-dr | us-west-2 | Disaster recovery |

---

## Environment Configuration

### 1. AWS Configuration

```bash
# Configure AWS credentials
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set default.region us-east-1

# Update kubeconfig for EKS access
aws eks update-kubeconfig --name sunday-staging --region us-east-1
aws eks update-kubeconfig --name sunday-production --region us-east-1
```

### 2. Environment Variables

Create environment-specific configuration files:

```bash
# .env.staging
NODE_ENV=staging
DATABASE_URL=postgresql://user:pass@staging-db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/sunday_staging
REDIS_URL=redis://staging-cache.xxx.cache.amazonaws.com:6379
JWT_SECRET=staging-jwt-secret-here
LOG_LEVEL=info
ENABLE_METRICS=true

# .env.production
NODE_ENV=production
DATABASE_URL=postgresql://user:pass@production-db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/sunday_production
REDIS_URL=redis://production-cache.xxx.cache.amazonaws.com:6379
JWT_SECRET=production-jwt-secret-here
LOG_LEVEL=warn
ENABLE_METRICS=true
```

### 3. Kubernetes Secrets

```bash
# Create secrets for each environment
kubectl create secret generic app-secrets \
  --from-env-file=.env.staging \
  --namespace=sunday-staging

kubectl create secret generic app-secrets \
  --from-env-file=.env.production \
  --namespace=sunday-production
```

---

## Deployment Strategies

### 1. Rolling Deployment (Default)

**Use Case**: Regular updates, minor feature releases
**Downtime**: Minimal (rolling update)
**Risk**: Low

```yaml
# k8s/rolling-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    spec:
      containers:
      - name: backend
        image: ghcr.io/sunday/backend:{{VERSION}}
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### 2. Blue-Green Deployment

**Use Case**: Major releases, database migrations
**Downtime**: Zero (instant switch)
**Risk**: Medium

```bash
# Deploy to green environment
kubectl apply -f k8s/production/ -l environment=green

# Wait for readiness
kubectl rollout status deployment/backend-deployment-green

# Switch traffic
kubectl patch service backend-service -p '{"spec":{"selector":{"version":"green"}}}'

# Cleanup blue environment
kubectl delete deployment backend-deployment-blue
```

### 3. Canary Deployment

**Use Case**: High-risk changes, new features
**Downtime**: None
**Risk**: Low (gradual rollout)

```yaml
# Deploy canary version (10% traffic)
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: backend-rollout
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10
      - pause: {duration: 5m}
      - setWeight: 50
      - pause: {duration: 10m}
      - setWeight: 100
```

---

## Step-by-Step Deployment Process

### 1. Pre-Deployment Checklist

```bash
#!/bin/bash
# scripts/pre-deployment-checklist.sh

echo "🔍 Pre-deployment checklist..."

# Check cluster connectivity
kubectl cluster-info || exit 1

# Verify namespace exists
kubectl get namespace sunday-production || exit 1

# Check resource availability
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources"

# Verify secrets exist
kubectl get secrets -n sunday-production | grep app-secrets || exit 1

# Check database connectivity
kubectl exec -it deployment/backend-deployment -n sunday-production -- \
  node -e "require('./src/config/database').testConnection()"

# Verify external dependencies
curl -f https://api.github.com/status
curl -f https://registry.npmjs.org/

echo "✅ Pre-deployment checks passed"
```

### 2. Build and Push Images

```bash
#!/bin/bash
# scripts/build-and-push.sh

VERSION=${1:-$(git rev-parse --short HEAD)}
REGISTRY="ghcr.io/sunday"

echo "🏗️ Building images for version: $VERSION"

# Build backend image
docker build -t $REGISTRY/backend:$VERSION ./backend
docker build -t $REGISTRY/backend:latest ./backend

# Build frontend image
docker build -t $REGISTRY/frontend:$VERSION ./frontend
docker build -t $REGISTRY/frontend:latest ./frontend

# Push images
docker push $REGISTRY/backend:$VERSION
docker push $REGISTRY/backend:latest
docker push $REGISTRY/frontend:$VERSION
docker push $REGISTRY/frontend:latest

echo "✅ Images built and pushed successfully"
```

### 3. Database Migration

```bash
#!/bin/bash
# scripts/migrate-database.sh

ENVIRONMENT=${1:-staging}
NAMESPACE="sunday-$ENVIRONMENT"

echo "🗃️ Running database migrations for $ENVIRONMENT..."

# Create migration job
kubectl create job migrate-$(date +%s) \
  --from=cronjob/database-migration \
  --namespace=$NAMESPACE

# Wait for migration to complete
kubectl wait --for=condition=complete job/migrate-$(date +%s) \
  --namespace=$NAMESPACE \
  --timeout=300s

# Check migration status
kubectl logs job/migrate-$(date +%s) --namespace=$NAMESPACE

echo "✅ Database migration completed"
```

### 4. Deploy Application

```bash
#!/bin/bash
# scripts/deploy-application.sh

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="sunday-$ENVIRONMENT"

echo "🚀 Deploying Sunday.com version $VERSION to $ENVIRONMENT..."

# Update image tags
find k8s/$ENVIRONMENT -name "*.yaml" -exec \
  sed -i "s|{{VERSION}}|$VERSION|g" {} \;

# Apply Kubernetes manifests
kubectl apply -f k8s/$ENVIRONMENT/ --namespace=$NAMESPACE

# Wait for rollout
kubectl rollout status deployment/backend-deployment --namespace=$NAMESPACE
kubectl rollout status deployment/frontend-deployment --namespace=$NAMESPACE

echo "✅ Application deployed successfully"
```

---

## Production Deployment

### Production Deployment Process

#### 1. Create Release Tag

```bash
# Create and push release tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

#### 2. Automated Production Deployment

The GitHub Actions CD pipeline automatically triggers production deployment when a release tag is pushed:

```yaml
# .github/workflows/cd.yml (excerpt)
deploy-production:
  if: startsWith(github.ref, 'refs/tags/v')
  steps:
    - name: Create backup
    - name: Deploy to production (Blue-Green)
    - name: Run smoke tests
    - name: Switch traffic
    - name: Verify deployment
    - name: Cleanup old version
```

#### 3. Manual Production Deployment

For emergency deployments or when automated pipeline is unavailable:

```bash
#!/bin/bash
# scripts/manual-production-deploy.sh

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

echo "🚨 Manual production deployment: $VERSION"

# 1. Create backup
echo "📦 Creating backup..."
kubectl create job backup-$(date +%s) \
  --from=cronjob/database-backup \
  --namespace=sunday-production

# 2. Deploy to green environment
echo "🟢 Deploying to green environment..."
./scripts/deploy-application.sh production $VERSION

# 3. Run production smoke tests
echo "🧪 Running smoke tests..."
./scripts/production-smoke-tests.sh green

# 4. Switch traffic (Blue-Green)
echo "🔄 Switching traffic to green..."
kubectl patch service backend-service -n sunday-production \
  -p '{"spec":{"selector":{"version":"green"}}}'
kubectl patch service frontend-service -n sunday-production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Final verification
echo "✅ Final verification..."
sleep 30
./scripts/production-smoke-tests.sh production

# 6. Cleanup blue environment
echo "🧹 Cleaning up blue environment..."
kubectl delete deployment backend-deployment-blue \
  frontend-deployment-blue -n sunday-production

echo "🎉 Production deployment completed successfully!"
```

---

## Post-Deployment Validation

### 1. Health Checks

```bash
#!/bin/bash
# scripts/health-checks.sh

ENVIRONMENT=${1:-staging}
BASE_URL="https://${ENVIRONMENT}.sunday.com"

if [ "$ENVIRONMENT" = "production" ]; then
  BASE_URL="https://sunday.com"
fi

echo "🏥 Running health checks for $ENVIRONMENT..."

# API health check
curl -f "$BASE_URL/api/health" || exit 1

# Database connectivity
curl -f "$BASE_URL/api/health/database" || exit 1

# Redis connectivity
curl -f "$BASE_URL/api/health/redis" || exit 1

# Authentication service
curl -f "$BASE_URL/api/health/auth" || exit 1

# Search service
curl -f "$BASE_URL/api/health/search" || exit 1

echo "✅ All health checks passed"
```

### 2. Smoke Tests

```bash
#!/bin/bash
# scripts/smoke-tests.sh

ENVIRONMENT=${1:-staging}
BASE_URL="https://${ENVIRONMENT}.sunday.com"

echo "🧪 Running smoke tests for $ENVIRONMENT..."

# Test user registration
RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}')

# Test login
RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}')

TOKEN=$(echo $RESPONSE | jq -r '.token')

# Test authenticated endpoints
curl -f -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/workspaces" || exit 1

# Test real-time features
WEBSOCKET_URL="wss://${ENVIRONMENT}.sunday.com/ws"
node -e "
  const WebSocket = require('ws');
  const ws = new WebSocket('$WEBSOCKET_URL', {
    headers: { Authorization: 'Bearer $TOKEN' }
  });
  ws.on('open', () => { ws.close(); process.exit(0); });
  ws.on('error', () => process.exit(1));
"

echo "✅ Smoke tests passed"
```

### 3. Performance Validation

```bash
#!/bin/bash
# scripts/performance-tests.sh

ENVIRONMENT=${1:-staging}
BASE_URL="https://${ENVIRONMENT}.sunday.com"

echo "⚡ Running performance tests for $ENVIRONMENT..."

# Load test with k6
k6 run --vus 100 --duration 60s \
  --env BASE_URL=$BASE_URL \
  testing/performance/load-test.js

# Response time check
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" "$BASE_URL/api/health")
if (( $(echo "$RESPONSE_TIME > 2.0" | bc -l) )); then
  echo "❌ Response time too slow: ${RESPONSE_TIME}s"
  exit 1
fi

echo "✅ Performance tests passed"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n sunday-production

# View pod logs
kubectl logs deployment/backend-deployment -n sunday-production

# Describe pod for events
kubectl describe pod <pod-name> -n sunday-production

# Check resource constraints
kubectl top pods -n sunday-production
```

#### 2. Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it deployment/backend-deployment -n sunday-production -- \
  pg_isready -h $DB_HOST -p $DB_PORT

# Check database secrets
kubectl get secret app-secrets -n sunday-production -o yaml

# Verify RDS instance status
aws rds describe-db-clusters --db-cluster-identifier sunday-production
```

#### 3. Load Balancer Issues

```bash
# Check service endpoints
kubectl get endpoints -n sunday-production

# Verify ingress configuration
kubectl describe ingress -n sunday-production

# Check AWS Load Balancer status
aws elbv2 describe-load-balancers
```

#### 4. Performance Issues

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n sunday-production

# Review metrics in Grafana
curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "https://grafana.sunday.com/api/datasources/proxy/1/api/v1/query?query=container_memory_usage_bytes"

# Scale horizontally if needed
kubectl scale deployment backend-deployment --replicas=5 -n sunday-production
```

### Emergency Procedures

#### 1. Emergency Scale Down

```bash
# Scale down problematic services
kubectl scale deployment backend-deployment --replicas=0 -n sunday-production
kubectl scale deployment frontend-deployment --replicas=1 -n sunday-production
```

#### 2. Emergency Rollback

```bash
# Quick rollback to previous version
kubectl rollout undo deployment/backend-deployment -n sunday-production
kubectl rollout undo deployment/frontend-deployment -n sunday-production
```

#### 3. Circuit Breaker Activation

```bash
# Enable maintenance mode
kubectl patch configmap app-config -n sunday-production \
  -p '{"data":{"maintenance_mode":"true"}}'

# Restart pods to pick up config
kubectl rollout restart deployment/backend-deployment -n sunday-production
```

---

## Rollback Procedures

### Automated Rollback

The CD pipeline includes automated rollback capabilities:

```yaml
# .github/workflows/cd.yml
rollback-production:
  if: github.event_name == 'workflow_dispatch'
  steps:
    - name: Rollback deployment
    - name: Verify rollback
    - name: Notify teams
```

### Manual Rollback Process

#### 1. Quick Rollback (Kubernetes)

```bash
#!/bin/bash
# scripts/quick-rollback.sh

NAMESPACE=${1:-sunday-production}

echo "🔄 Performing quick rollback for $NAMESPACE..."

# Rollback to previous version
kubectl rollout undo deployment/backend-deployment -n $NAMESPACE
kubectl rollout undo deployment/frontend-deployment -n $NAMESPACE

# Wait for rollback to complete
kubectl rollout status deployment/backend-deployment -n $NAMESPACE
kubectl rollout status deployment/frontend-deployment -n $NAMESPACE

# Verify rollback
./scripts/smoke-tests.sh ${NAMESPACE/sunday-/}

echo "✅ Rollback completed successfully"
```

#### 2. Database Rollback

```bash
#!/bin/bash
# scripts/database-rollback.sh

BACKUP_ID=${1}
ENVIRONMENT=${2:-staging}

if [ -z "$BACKUP_ID" ]; then
  echo "Usage: $0 <backup-id> [environment]"
  echo "Available backups:"
  aws rds describe-db-snapshots --db-cluster-identifier sunday-$ENVIRONMENT
  exit 1
fi

echo "🗃️ Rolling back database to backup: $BACKUP_ID"

# Create new cluster from snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier sunday-$ENVIRONMENT-rollback \
  --snapshot-identifier $BACKUP_ID

# Wait for cluster to be available
aws rds wait db-cluster-available \
  --db-cluster-identifier sunday-$ENVIRONMENT-rollback

echo "✅ Database rollback completed"
```

#### 3. Full Environment Rollback

```bash
#!/bin/bash
# scripts/full-rollback.sh

TARGET_VERSION=${1}
ENVIRONMENT=${2:-production}

if [ -z "$TARGET_VERSION" ]; then
  echo "Usage: $0 <target-version> [environment]"
  exit 1
fi

echo "🚨 Full environment rollback to version: $TARGET_VERSION"

# 1. Create current state backup
./scripts/create-backup.sh $ENVIRONMENT

# 2. Rollback application
./scripts/deploy-application.sh $ENVIRONMENT $TARGET_VERSION

# 3. Verify deployment
./scripts/smoke-tests.sh $ENVIRONMENT

# 4. Update monitoring
curl -X POST -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "https://grafana.sunday.com/api/annotations" \
  -d "{\"text\":\"Rollback to $TARGET_VERSION\",\"tags\":[\"rollback\"]}"

echo "✅ Full rollback completed successfully"
```

---

## Monitoring and Alerts

### Key Metrics to Monitor

- **Application Health**: Response times, error rates, throughput
- **Infrastructure**: CPU, memory, disk usage, network
- **Database**: Connection pool, query performance, replication lag
- **User Experience**: Page load times, API latency, error rates

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|---------|
| API Response Time | >500ms | >2s | Scale up/investigate |
| Error Rate | >1% | >5% | Immediate investigation |
| CPU Usage | >70% | >90% | Scale horizontally |
| Memory Usage | >80% | >95% | Scale vertically |
| Database Connections | >80% | >95% | Optimize queries |

### Grafana Dashboards

- **Overview Dashboard**: High-level system health
- **Application Dashboard**: Service-specific metrics
- **Infrastructure Dashboard**: Kubernetes and AWS resources
- **User Experience Dashboard**: Frontend performance metrics

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: DevOps Team*