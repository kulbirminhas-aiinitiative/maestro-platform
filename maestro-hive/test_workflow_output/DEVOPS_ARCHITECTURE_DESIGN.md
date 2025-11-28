# DevOps Architecture Design Document
## User Management REST API - Design Phase

**Project**: User Management REST API
**Phase**: Design
**Role**: DevOps Engineer
**Date**: 2025-10-12
**Status**: Complete ✓

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Infrastructure Architecture](#infrastructure-architecture)
3. [Container Strategy](#container-strategy)
4. [Kubernetes Architecture](#kubernetes-architecture)
5. [CI/CD Pipeline Design](#cicd-pipeline-design)
6. [Monitoring & Observability](#monitoring--observability)
7. [Infrastructure as Code](#infrastructure-as-code)
8. [Security Architecture](#security-architecture)
9. [Disaster Recovery](#disaster-recovery)
10. [Deployment Strategy](#deployment-strategy)
11. [Runbooks](#runbooks)

---

## Executive Summary

This document outlines the complete DevOps architecture for the User Management REST API. The design focuses on:

- **Scalability**: Auto-scaling infrastructure to handle varying loads
- **Reliability**: High availability with 99.9% uptime target
- **Security**: Defense-in-depth approach with multiple security layers
- **Observability**: Comprehensive monitoring and alerting
- **Automation**: Fully automated CI/CD pipeline
- **Cost Optimization**: Efficient resource utilization

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Kubernetes (EKS) | Industry-standard orchestration, managed service reduces operational overhead |
| Docker Containers | Consistent environments, efficient resource usage, portable |
| GitHub Actions | Integrated with GitHub, extensive marketplace, cost-effective |
| Terraform | Infrastructure as Code, multi-cloud support, large community |
| Prometheus + Grafana | Open-source, Kubernetes-native, rich ecosystem |
| AWS Cloud | Mature services, global presence, strong security features |

---

## Infrastructure Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS Cloud                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                VPC (10.0.0.0/16)                      │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │          Public Subnets                        │  │  │
│  │  │  ┌──────────────┐    ┌──────────────┐         │  │  │
│  │  │  │ NAT Gateway  │    │  ALB/Ingress │         │  │  │
│  │  │  └──────────────┘    └──────────────┘         │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │          Private Subnets (Apps)                │  │  │
│  │  │  ┌──────────────────────────────────────┐     │  │  │
│  │  │  │  EKS Cluster                         │     │  │  │
│  │  │  │  ┌────────────┐  ┌────────────┐     │     │  │  │
│  │  │  │  │  API Pods  │  │  API Pods  │ ... │     │  │  │
│  │  │  │  └────────────┘  └────────────┘     │     │  │  │
│  │  │  └──────────────────────────────────────┘     │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │          Private Subnets (Data)                │  │  │
│  │  │  ┌────────────┐    ┌──────────────┐           │  │  │
│  │  │  │ RDS        │    │ ElastiCache  │           │  │  │
│  │  │  │ PostgreSQL │    │ Redis        │           │  │  │
│  │  │  └────────────┘    └──────────────┘           │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┐  │
└─────────────────────────────────────────────────────────────┘
```

### Infrastructure Components

#### 1. Networking Layer
- **VPC**: Isolated virtual network (10.0.0.0/16)
- **Subnets**: Multi-AZ deployment across 3 availability zones
  - Public Subnets: Internet-facing resources (ALB, NAT)
  - Private Subnets (App): Application workloads (EKS)
  - Private Subnets (Data): Databases and caches
- **Security Groups**: Firewall rules for each component
- **Network ACLs**: Additional subnet-level security

#### 2. Compute Layer
- **EKS Cluster**: Managed Kubernetes service
  - Version: 1.28
  - Node Groups: Auto-scaling (min: 3, max: 10)
  - Instance Types: t3.medium (dev), t3.large (prod)
- **Pod Specifications**:
  - CPU Request: 250m, Limit: 1000m
  - Memory Request: 256Mi, Limit: 1Gi
  - Replicas: 3 (min), 10 (max with HPA)

#### 3. Data Layer
- **RDS PostgreSQL**:
  - Version: 15.4
  - Instance: db.t3.medium (dev), db.r6g.large (prod)
  - Storage: 100GB, auto-scaling to 500GB
  - Backup: 7 days (dev), 30 days (prod)
  - Multi-AZ: Enabled in production
- **ElastiCache Redis**:
  - Version: 7.0
  - Node Type: cache.t3.micro (dev), cache.r6g.large (prod)
  - Cluster Mode: Enabled in production
  - Replication: 3 nodes in production

#### 4. Storage Layer
- **EBS Volumes**: Persistent storage for pods (if needed)
- **S3 Buckets**:
  - Application assets
  - Terraform state (with versioning)
  - Backup storage
  - Log archives

---

## Container Strategy

### Docker Architecture

#### Multi-Stage Build Strategy

Our Dockerfile uses multi-stage builds for:
- Smaller final image size
- Improved security (fewer dependencies)
- Faster build times (layer caching)

```dockerfile
# Stage 1: Builder (dependencies + build)
FROM node:18-alpine AS builder
# ... build steps ...

# Stage 2: Production (minimal runtime)
FROM node:18-alpine
# ... production setup ...
```

#### Security Hardening

1. **Non-root User**: Application runs as user ID 1001
2. **Read-only Root Filesystem**: Prevents tampering
3. **No Privileged Escalation**: Security context prevents privilege escalation
4. **Minimal Base Image**: Alpine Linux (5MB base)
5. **Security Scanning**: Trivy scans for vulnerabilities

#### Image Tagging Strategy

```
ghcr.io/org/user-api:latest           # Latest build from main
ghcr.io/org/user-api:v1.2.3           # Semantic version
ghcr.io/org/user-api:main-abc123      # Branch + commit SHA
ghcr.io/org/user-api:pr-456           # Pull request builds
```

### Container Registry

- **Registry**: GitHub Container Registry (ghcr.io)
- **Access**: Token-based authentication
- **Scanning**: Automated vulnerability scanning
- **Retention**: 30-day retention for development tags

---

## Kubernetes Architecture

### Cluster Design

#### Namespace Strategy

| Namespace | Purpose | Resource Quotas |
|-----------|---------|-----------------|
| production | Production workloads | CPU: 10 cores, Memory: 20Gi |
| staging | Staging environment | CPU: 5 cores, Memory: 10Gi |
| development | Development testing | CPU: 3 cores, Memory: 6Gi |
| monitoring | Monitoring stack | CPU: 4 cores, Memory: 8Gi |

#### Resource Management

**Deployment Configuration**:
```yaml
resources:
  requests:
    cpu: 250m        # Guaranteed CPU
    memory: 256Mi    # Guaranteed memory
  limits:
    cpu: 1000m       # Maximum CPU
    memory: 1Gi      # Maximum memory
```

**Horizontal Pod Autoscaler**:
- Min Replicas: 3
- Max Replicas: 10
- CPU Target: 70%
- Memory Target: 80%
- Scale-up: Aggressive (2 pods per 30s)
- Scale-down: Conservative (50% reduction per 60s, 5min stabilization)

### High Availability

#### Pod Distribution
- **Anti-Affinity**: Pods spread across nodes
- **Pod Disruption Budget**: Minimum 2 pods available during updates
- **Multiple Replicas**: Always at least 3 pods running

#### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 15
  periodSeconds: 5
  failureThreshold: 3
```

### Service Mesh (Optional Enhancement)

Consider implementing Istio for:
- Advanced traffic management
- Service-to-service authentication
- Observability and tracing
- Circuit breaking and retries

---

## CI/CD Pipeline Design

### Pipeline Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Commit    │─────▶│   Quality    │─────▶│     Build    │
│   & Push    │      │   Checks     │      │    & Test    │
└─────────────┘      └──────────────┘      └──────────────┘
                                                    │
                                                    ▼
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Deploy    │◀─────│   Security   │◀─────│   Container  │
│  Production │      │    Scan      │      │    Build     │
└─────────────┘      └──────────────┘      └──────────────┘
```

### Pipeline Stages

#### 1. Quality Checks (3-5 minutes)
- **Linting**: ESLint for code quality
- **Formatting**: Prettier check
- **Dependency Audit**: npm audit for known vulnerabilities
- **Security Scan**: Snyk for security issues

**Success Criteria**: All checks pass, no high severity issues

#### 2. Testing (5-10 minutes)
- **Unit Tests**: Jest for component testing
- **Integration Tests**: API endpoint testing
- **Coverage**: Minimum 80% code coverage
- **Database Tests**: Test with PostgreSQL service container

**Success Criteria**: All tests pass, coverage threshold met

#### 3. Container Build (5-10 minutes)
- **Multi-arch Build**: linux/amd64, linux/arm64
- **Image Optimization**: Layer caching, multi-stage builds
- **Tagging**: Automatic semantic versioning
- **Registry Push**: Push to GitHub Container Registry

**Success Criteria**: Image built and pushed successfully

#### 4. Security Scanning (3-5 minutes)
- **Container Scan**: Trivy vulnerability scanner
- **Severity Threshold**: Block on HIGH/CRITICAL
- **SARIF Upload**: Results to GitHub Security tab
- **Compliance Check**: CIS Docker Benchmark

**Success Criteria**: No critical vulnerabilities, compliance passed

#### 5. Deployment (5-15 minutes)

**Development** (auto-deploy):
- Trigger: Push to `develop` branch
- Strategy: Rolling update
- Smoke tests: Health check only

**Staging** (auto-deploy):
- Trigger: Push to `staging` branch
- Strategy: Blue-Green deployment
- Tests: Full E2E test suite

**Production** (manual approval):
- Trigger: Release creation or manual workflow
- Strategy: Blue-Green with canary
- Tests: Smoke tests + manual validation
- Approval: Required from DevOps team

### Deployment Strategies

#### Rolling Update (Development)
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1          # 1 extra pod during update
    maxUnavailable: 0    # No downtime
```

#### Blue-Green (Staging/Production)
1. Deploy new version (green)
2. Run health checks
3. Run smoke tests
4. Switch traffic to green
5. Monitor for issues
6. Decommission blue (after stabilization period)

#### Canary (Production - Advanced)
1. Deploy new version to 10% of pods
2. Monitor metrics for 10 minutes
3. If successful, increase to 50%
4. Monitor for another 10 minutes
5. If successful, complete rollout to 100%

### Rollback Strategy

**Automatic Rollback Triggers**:
- Health check failures
- Smoke test failures
- Error rate spike (>5% over 5 minutes)
- Deployment timeout (10 minutes)

**Manual Rollback**:
```bash
kubectl rollout undo deployment/user-api -n production
# or
./scripts/deploy.sh rollback production
```

---

## Monitoring & Observability

### Monitoring Stack

#### Components

1. **Prometheus** (Metrics Collection)
   - Scrape interval: 15 seconds
   - Retention: 30 days
   - Storage: 100GB

2. **Grafana** (Visualization)
   - Dashboards: Pre-configured for API, Database, Redis
   - Alerts: Integrated with Alertmanager
   - Users: Team access with RBAC

3. **Alertmanager** (Alert Routing)
   - Routes: Severity-based routing
   - Integrations: Slack, PagerDuty, Email
   - Inhibition: Prevent alert storms

4. **Loki** (Log Aggregation) - Optional
   - Centralized logging
   - Retention: 7 days
   - Query language: LogQL

### Metrics Collection

#### Application Metrics

**Custom Metrics to Implement**:
```javascript
// Request metrics
http_requests_total{method, path, status}
http_request_duration_seconds{method, path}

// Business metrics
users_created_total
users_deleted_total
authentication_attempts_total{status}

// Database metrics
db_queries_total{operation, table}
db_query_duration_seconds{operation, table}
db_connection_pool_active
db_connection_pool_idle

// Cache metrics
redis_cache_hits_total
redis_cache_misses_total
redis_operations_total{operation}
```

#### Infrastructure Metrics

**Automatically Collected**:
- Container CPU/Memory usage
- Pod restart count
- Network I/O
- Disk I/O
- Database connections
- Redis operations

### Alerting Rules

#### Critical Alerts (PagerDuty)

| Alert | Condition | Action |
|-------|-----------|--------|
| Pod Down | Pod unavailable >2min | Page on-call engineer |
| High Error Rate | 5xx errors >5% for 5min | Page on-call engineer |
| Database Down | RDS unavailable >1min | Page on-call + DBA |
| Out of Memory | Memory >95% for 5min | Auto-restart + Page |

#### Warning Alerts (Slack)

| Alert | Condition | Action |
|-------|-----------|--------|
| High CPU | CPU >70% for 10min | Notify team channel |
| High Response Time | P95 >1s for 5min | Notify team channel |
| High Cache Miss Rate | Miss rate >50% for 10min | Notify team channel |
| Deployment Stuck | Rollout >15min | Notify team channel |

### Dashboards

#### 1. Application Dashboard
- Request rate (req/s)
- Error rate (%)
- Response time (P50, P95, P99)
- Active connections
- Pod status and health

#### 2. Database Dashboard
- Query performance
- Connection pool utilization
- Replication lag (if applicable)
- Storage usage
- Top slow queries

#### 3. Infrastructure Dashboard
- Cluster resource utilization
- Node health status
- Pod distribution
- Network traffic
- Cost metrics

### Logging Strategy

#### Log Levels

| Environment | Level | Retention |
|-------------|-------|-----------|
| Development | DEBUG | 1 day |
| Staging | INFO | 7 days |
| Production | INFO | 30 days |

#### Structured Logging Format

```json
{
  "timestamp": "2025-10-12T14:30:00Z",
  "level": "INFO",
  "service": "user-api",
  "pod": "user-api-abc123",
  "trace_id": "xyz789",
  "message": "User created successfully",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "duration_ms": 45
}
```

---

## Infrastructure as Code

### Terraform Structure

```
terraform/
├── main.tf                 # Main configuration
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── versions.tf             # Provider versions
├── backend.tf              # State backend config
├── environments/
│   ├── dev/
│   │   ├── terraform.tfvars
│   │   └── backend.tfvars
│   ├── staging/
│   │   ├── terraform.tfvars
│   │   └── backend.tfvars
│   └── production/
│       ├── terraform.tfvars
│       └── backend.tfvars
└── modules/
    ├── vpc/
    ├── eks/
    ├── rds/
    └── redis/
```

### State Management

- **Backend**: S3 + DynamoDB for state locking
- **Encryption**: State files encrypted at rest
- **Versioning**: S3 versioning enabled
- **Access**: IAM-based access control

### Terraform Workflow

```bash
# Initialize
terraform init -backend-config=environments/production/backend.tfvars

# Plan
terraform plan -var-file=environments/production/terraform.tfvars

# Apply (with approval)
terraform apply -var-file=environments/production/terraform.tfvars

# Destroy (with confirmation)
terraform destroy -var-file=environments/production/terraform.tfvars
```

---

## Security Architecture

### Defense in Depth

#### 1. Network Security
- VPC isolation
- Private subnets for workloads
- Security groups with least privilege
- Network policies in Kubernetes

#### 2. Container Security
- Non-root user
- Read-only root filesystem
- Security context constraints
- Vulnerability scanning

#### 3. Application Security
- JWT authentication
- Rate limiting
- Input validation
- SQL injection prevention (ORM)

#### 4. Secrets Management
- AWS Secrets Manager for sensitive data
- Kubernetes secrets for service credentials
- Encrypted at rest and in transit
- Rotation policies

#### 5. Access Control
- RBAC in Kubernetes
- IAM roles for service accounts
- MFA for administrative access
- Audit logging enabled

### Compliance

- **GDPR**: Data encryption, right to deletion
- **SOC 2**: Audit logs, access controls
- **HIPAA**: Encryption, access logs (if applicable)

---

## Disaster Recovery

### Backup Strategy

#### Database Backups
- **Automated Snapshots**: Daily at 3:00 AM UTC
- **Retention**: 30 days (production), 7 days (dev)
- **Point-in-time Recovery**: 5-minute granularity
- **Cross-region Replication**: Enabled for production

#### Application State
- **Configuration**: Stored in Git (version controlled)
- **Secrets**: Backed up in Secrets Manager
- **Logs**: Archived to S3 after 7 days

### Recovery Procedures

#### RTO (Recovery Time Objective)
- **Critical**: 1 hour
- **High**: 4 hours
- **Medium**: 24 hours

#### RPO (Recovery Point Objective)
- **Database**: 5 minutes
- **Application**: 0 (stateless)
- **Logs**: 1 hour

### Disaster Scenarios

#### 1. Complete AZ Failure
- **Impact**: Degraded performance
- **Recovery**: Auto-failover to healthy AZ
- **Time**: < 5 minutes

#### 2. Region Failure
- **Impact**: Service unavailable
- **Recovery**: Manual failover to DR region
- **Time**: < 1 hour (requires runbook execution)

#### 3. Database Corruption
- **Impact**: Potential data loss
- **Recovery**: Restore from latest snapshot
- **Time**: < 30 minutes

---

## Deployment Strategy

### Environment Promotion Flow

```
develop → dev environment
   ↓ (automated)
   ↓
staging → staging environment
   ↓ (manual approval)
   ↓
main → production environment
```

### Pre-deployment Checklist

- [ ] All tests passing
- [ ] Security scans completed
- [ ] No critical vulnerabilities
- [ ] Database migrations tested
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured
- [ ] Team notified of deployment
- [ ] Approval obtained (production)

### Post-deployment Verification

1. **Smoke Tests** (2 minutes)
   - Health endpoint responding
   - Basic API operations working

2. **Monitoring Check** (5 minutes)
   - Error rates normal
   - Response times acceptable
   - No alerts firing

3. **Rollback Decision** (10 minutes)
   - If issues detected, rollback immediately
   - If stable, continue monitoring

---

## Runbooks

### Common Operations

#### 1. Scale Application

```bash
# Manual scaling
kubectl scale deployment/user-api --replicas=5 -n production

# Adjust HPA
kubectl edit hpa/user-api-hpa -n production
```

#### 2. Restart Application

```bash
# Rolling restart
kubectl rollout restart deployment/user-api -n production
```

#### 3. View Logs

```bash
# Recent logs
kubectl logs -f deployment/user-api -n production

# Logs from specific pod
kubectl logs user-api-abc123 -n production

# Previous container logs
kubectl logs user-api-abc123 -n production --previous
```

#### 4. Execute Database Migration

```bash
# Run migration job
kubectl apply -f k8s/migrations/job.yaml -n production

# Check migration status
kubectl logs job/db-migration -n production
```

#### 5. Emergency Rollback

```bash
# Quick rollback
kubectl rollout undo deployment/user-api -n production

# Rollback to specific revision
kubectl rollout undo deployment/user-api --to-revision=3 -n production

# Check rollout status
kubectl rollout status deployment/user-api -n production
```

### Troubleshooting Guide

#### Pod CrashLoopBackOff

1. Check logs: `kubectl logs <pod> -n production`
2. Check events: `kubectl describe pod <pod> -n production`
3. Verify configuration: `kubectl get configmap -n production`
4. Check secrets: `kubectl get secrets -n production`

#### High Memory Usage

1. Check metrics: Grafana → Infrastructure Dashboard
2. Identify memory leak: `kubectl top pods -n production`
3. Restart pod: `kubectl delete pod <pod> -n production`
4. Review application code for memory leaks

#### Database Connection Issues

1. Check RDS status: AWS Console → RDS
2. Verify security groups: Allow traffic from EKS
3. Test connection: `kubectl run -it --rm debug --image=postgres:15 -- psql`
4. Check connection pool: Grafana → Database Dashboard

---

## Appendix

### Tool Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Kubernetes | 1.28 | Container orchestration |
| Docker | 24.0 | Containerization |
| Terraform | 1.5+ | Infrastructure as Code |
| Helm | 3.12+ | Package management |
| kubectl | 1.28 | Kubernetes CLI |

### Useful Commands

```bash
# Get cluster info
kubectl cluster-info

# Get all resources
kubectl get all -n production

# Describe resource
kubectl describe <resource> <name> -n production

# Port forward
kubectl port-forward svc/user-api 8080:80 -n production

# Execute command in pod
kubectl exec -it <pod> -n production -- /bin/sh

# Copy files to/from pod
kubectl cp <pod>:/path/to/file ./local-file -n production
```

### Support Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| DevOps Team | devops@company.com | Slack: #devops |
| On-Call Engineer | PagerDuty | +1-555-0100 |
| Database Team | dba@company.com | Slack: #database |
| Security Team | security@company.com | Slack: #security |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-12 | DevOps Engineer | Initial design document |

---

**END OF DOCUMENT**
