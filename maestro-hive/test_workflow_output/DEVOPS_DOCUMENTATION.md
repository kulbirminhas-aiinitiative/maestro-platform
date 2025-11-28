# DevOps Documentation - User Management REST API

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Infrastructure Components](#infrastructure-components)
4. [Deployment Guide](#deployment-guide)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security](#security)
8. [Operations](#operations)
9. [Troubleshooting](#troubleshooting)

## Overview

This documentation covers the complete DevOps infrastructure and deployment processes for the User Management REST API system.

### Project Stack
- **Application**: Python REST API (FastAPI/Flask)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Container Runtime**: Docker
- **Orchestration**: Kubernetes (EKS)
- **Cloud Provider**: AWS
- **Infrastructure as Code**: Terraform
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

## Architecture

### High-Level Architecture
```
Internet → ALB/Ingress → Kubernetes Cluster
                         ├── API Pods (3+ replicas)
                         ├── PostgreSQL StatefulSet
                         └── Redis StatefulSet
```

### Components
- **Load Balancer**: AWS ALB via Kubernetes Ingress
- **API Layer**: Python REST API (Uvicorn/Gunicorn)
- **Data Layer**: PostgreSQL with persistent volumes
- **Cache Layer**: Redis for session/cache management
- **Monitoring**: Prometheus metrics, Grafana dashboards
- **Logging**: CloudWatch Logs

## Infrastructure Components

### 1. Containerization (Docker)

#### Dockerfile
- Multi-stage build for optimized image size
- Non-root user for security
- Health checks built-in
- Location: `Dockerfile`

#### Build Command
```bash
docker build -t user-mgmt-api:latest .
```

#### Run Locally
```bash
docker-compose up -d
```

### 2. Kubernetes Manifests

All Kubernetes resources are in the `k8s/` directory:

- **namespace.yaml**: Isolated namespace for the application
- **configmap.yaml**: Non-sensitive configuration
- **secrets.yaml**: Sensitive data (use external secrets in production)
- **postgres-deployment.yaml**: PostgreSQL database with PVC
- **redis-deployment.yaml**: Redis cache with PVC
- **api-deployment.yaml**: Main API application with 3 replicas
- **ingress.yaml**: External access configuration
- **hpa.yaml**: Horizontal Pod Autoscaler (3-10 replicas)
- **network-policy.yaml**: Network segmentation rules

#### Apply Kubernetes Resources
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/
```

### 3. Infrastructure as Code (Terraform)

Terraform modules provision AWS infrastructure:

#### Modules Structure
```
terraform/
├── main.tf                 # Root configuration
├── variables.tf            # Input variables
├── outputs.tf             # Output values
├── modules/
│   ├── vpc/              # VPC, subnets, NAT
│   ├── eks/              # EKS cluster
│   ├── rds/              # PostgreSQL RDS
│   └── redis/            # ElastiCache Redis
└── environments/
    ├── dev/              # Dev environment vars
    └── prod/             # Prod environment vars
```

#### Provision Infrastructure
```bash
cd terraform
terraform init
terraform plan -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars
```

## Deployment Guide

### Prerequisites
- AWS CLI configured
- kubectl installed
- Docker installed
- Access to EKS cluster

### Automated Deployment

Use the deployment script:
```bash
./scripts/deploy.sh dev v1.0.0
```

### Manual Deployment Steps

1. **Configure kubectl**
```bash
aws eks update-kubeconfig --name dev-cluster --region us-east-1
```

2. **Apply Secrets**
```bash
kubectl create secret generic user-mgmt-secrets \
  --from-literal=DATABASE_PASSWORD=your-password \
  --from-literal=SECRET_KEY=your-secret-key \
  -n user-management
```

3. **Deploy Application**
```bash
kubectl apply -f k8s/
```

4. **Verify Deployment**
```bash
kubectl get pods -n user-management
kubectl get svc -n user-management
```

5. **Check Application Health**
```bash
kubectl port-forward svc/user-mgmt-api-service 8000:80 -n user-management
curl http://localhost:8000/health
```

## CI/CD Pipeline

### GitHub Actions Workflow

The pipeline (`.github/workflows/ci-cd.yml`) includes:

#### 1. Code Quality Checks
- Black formatting
- Flake8 linting
- Pylint analysis
- MyPy type checking
- Bandit security scanning
- Safety dependency checking

#### 2. Testing
- Unit tests with pytest
- Integration tests
- Coverage reporting to Codecov
- Test database via Docker services

#### 3. Build & Push
- Multi-arch Docker build (amd64, arm64)
- Push to GitHub Container Registry
- Trivy security scanning
- SARIF upload to GitHub Security

#### 4. Deploy
- **Development**: Auto-deploy on push to `develop`
- **Production**: Deploy on release creation
- Smoke tests after deployment
- Automatic rollback on failure

### Pipeline Triggers
- Push to `main` or `develop` branches
- Pull requests
- Release creation

### Secrets Required
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SLACK_WEBHOOK` (optional)

## Monitoring & Observability

### Prometheus Metrics

Exposed metrics at `/metrics` endpoint:
- HTTP request duration
- Request count by endpoint
- Active connections
- Database connection pool stats
- Redis cache hit/miss rates

### Grafana Dashboards

Access: `http://grafana:3000` (via port-forward or ingress)

Default dashboards include:
- API Performance Overview
- Database Metrics
- Pod Resource Usage
- Request Rate & Latency

### CloudWatch Logs

Application logs are sent to CloudWatch:
```bash
aws logs tail /aws/eks/user-management-dev --follow
```

### Kubernetes Monitoring

```bash
# Watch pods
kubectl get pods -n user-management -w

# View logs
kubectl logs -f deployment/user-mgmt-api -n user-management

# Resource usage
kubectl top pods -n user-management
```

## Security

### Security Measures Implemented

1. **Container Security**
   - Non-root user in containers
   - Read-only root filesystem
   - Dropped all capabilities
   - Security context constraints

2. **Network Security**
   - Network policies for pod-to-pod communication
   - TLS/SSL on ingress
   - Private subnets for workloads

3. **Secrets Management**
   - AWS Secrets Manager for sensitive data
   - Kubernetes secrets for cluster data
   - No hardcoded credentials

4. **Image Security**
   - Trivy scanning in CI/CD
   - Regular base image updates
   - Minimal base images (Alpine)

5. **Access Control**
   - RBAC for Kubernetes
   - IAM roles for service accounts
   - Least privilege principle

### Security Best Practices

- Rotate secrets regularly (every 90 days)
- Keep base images updated
- Monitor CVE databases
- Use network policies
- Enable audit logging

## Operations

### Common Operations

#### Scale Application
```bash
kubectl scale deployment/user-mgmt-api --replicas=5 -n user-management
```

#### Update Image
```bash
kubectl set image deployment/user-mgmt-api \
  api=ghcr.io/your-org/user-mgmt-api:v1.1.0 \
  -n user-management
```

#### Rollback Deployment
```bash
./scripts/rollback.sh prod
```

#### Database Backup
```bash
./scripts/backup-db.sh prod
```

#### View Logs
```bash
kubectl logs -f deployment/user-mgmt-api -n user-management --tail=100
```

#### Execute Command in Pod
```bash
kubectl exec -it deployment/user-mgmt-api -n user-management -- /bin/bash
```

### Disaster Recovery

#### Database Restore
```bash
# Download backup from S3
aws s3 cp s3://user-management-prod-backups/backup_20241012.sql.gz .

# Restore to database
gunzip backup_20241012.sql.gz
kubectl exec -i deployment/postgres -n user-management -- \
  psql -U dbuser -d usermanagement < backup_20241012.sql
```

#### Cluster Recovery
```bash
# Recreate cluster from Terraform
cd terraform
terraform apply -var-file=environments/prod/terraform.tfvars

# Restore applications
kubectl apply -f k8s/
```

## Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n user-management

# Check events
kubectl get events -n user-management --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n user-management
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl run psql-test --rm -it --restart=Never \
  --image=postgres:15-alpine \
  --namespace=user-management \
  -- psql postgresql://dbuser:password@postgres-service:5432/usermanagement
```

#### High Memory/CPU Usage
```bash
# Check resource usage
kubectl top pods -n user-management

# Check HPA status
kubectl get hpa -n user-management

# Review metrics
kubectl describe hpa user-mgmt-api-hpa -n user-management
```

#### Service Not Accessible
```bash
# Check service endpoints
kubectl get endpoints -n user-management

# Check ingress
kubectl describe ingress user-mgmt-ingress -n user-management

# Port forward for testing
kubectl port-forward svc/user-mgmt-api-service 8000:80 -n user-management
```

### Debug Mode

Enable debug logging:
```bash
kubectl set env deployment/user-mgmt-api LOG_LEVEL=DEBUG -n user-management
```

### Performance Issues

1. Check database query performance
2. Review cache hit rates
3. Analyze request patterns
4. Check network latency
5. Review resource limits

## Contact & Support

- **DevOps Team**: devops@company.com
- **On-Call**: PagerDuty rotation
- **Documentation**: Internal wiki
- **Runbooks**: `/docs` directory

---

**Last Updated**: 2024-10-12
**Version**: 1.0.0
**Maintained By**: DevOps Team
