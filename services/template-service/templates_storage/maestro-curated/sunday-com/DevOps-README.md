# Sunday.com - DevOps Infrastructure

This document provides a comprehensive guide to the DevOps infrastructure for Sunday.com, including containerization, CI/CD pipelines, Kubernetes deployments, and Infrastructure as Code.

## 📁 Directory Structure

```
sunday_com/
├── .github/workflows/          # GitHub Actions CI/CD pipelines
│   ├── ci.yml                 # Continuous Integration
│   ├── cd.yml                 # Continuous Deployment
│   └── e2e.yml                # End-to-End Testing
├── k8s/                       # Kubernetes configurations
│   ├── base/                  # Base Kubernetes manifests
│   ├── staging/               # Staging environment overlays
│   ├── production/            # Production environment overlays
│   └── monitoring/            # Monitoring stack
├── terraform/                 # Infrastructure as Code
│   ├── modules/               # Reusable Terraform modules
│   ├── environments/          # Environment-specific configurations
│   └── main.tf               # Main Terraform configuration
├── scripts/                   # Automation scripts
│   ├── setup/                # Setup and installation scripts
│   ├── deployment/           # Deployment automation
│   └── monitoring/           # Health checks and monitoring
├── config/                    # Configuration files
│   ├── redis.conf            # Redis configuration
│   ├── prometheus.yml        # Prometheus configuration
│   └── grafana/              # Grafana dashboards
├── docker-compose.yml         # Local development environment
├── docker-compose.dev.yml     # Development overrides
└── docker-compose.prod.yml    # Production overrides
```

## 🐳 Docker Configuration

### Backend Dockerfile

The backend uses a multi-stage Docker build for optimal production images:

- **Base Stage**: Node.js 20 Alpine
- **Dependencies**: Installs production dependencies only
- **Builder**: Compiles TypeScript and generates Prisma client
- **Runner**: Final production image with non-root user

Key features:
- Multi-stage builds for smaller images
- Security-focused (non-root user)
- Health checks included
- Optimized for caching

### Frontend Dockerfile

The frontend uses Nginx for serving static assets:

- **Builder**: Node.js environment for building React app
- **Runner**: Nginx Alpine with custom configuration
- **Features**: Gzip compression, security headers, SPA routing

### Development vs Production

- **Development**: Hot reloading, debugging ports, verbose logging
- **Production**: Optimized builds, security hardening, monitoring

## 🐙 Docker Compose

### Local Development Stack

```bash
# Start full development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Services included:
# - PostgreSQL (primary database)
# - Redis (cache and sessions)
# - Elasticsearch (search engine)
# - ClickHouse (analytics)
# - MinIO (S3-compatible storage)
# - Prometheus (metrics)
# - Grafana (visualization)
# - Mailhog (email testing)
```

### Quick Start

```bash
# Setup local development environment
./scripts/setup/setup-local-dev.sh

# Start services
docker-compose up -d

# Check service health
./scripts/monitoring/health-check.sh -e local
```

## 🚀 CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Continuous Integration (`ci.yml`)

**Triggers**: Push to main/develop, Pull Requests

**Jobs**:
- **Backend Tests**: Unit tests, linting, type checking
- **Frontend Tests**: Component tests, linting, type checking
- **Security Scanning**: Trivy vulnerability scanner
- **Build Images**: Docker builds for backend and frontend

**Features**:
- Parallel execution for speed
- Test result reporting
- Security vulnerability scanning
- Multi-architecture builds (AMD64, ARM64)

#### 2. Continuous Deployment (`cd.yml`)

**Triggers**: Push to main, Version tags

**Environments**:
- **Staging**: Automatic deployment from main branch
- **Production**: Manual deployment from version tags

**Features**:
- Blue-green deployments
- Database backups before production deployment
- Smoke tests after deployment
- Automatic rollback on failure
- Slack notifications

#### 3. End-to-End Testing (`e2e.yml`)

**Triggers**: Push, Pull Requests, Scheduled (daily)

**Tests**:
- Playwright E2E tests
- Visual regression tests
- Performance tests (k6)

### Pipeline Security

- **Secrets Management**: AWS Secrets Manager, GitHub secrets
- **OIDC Authentication**: Passwordless AWS access
- **Image Scanning**: Trivy security scans
- **Dependency Auditing**: npm audit, Snyk

## ☸️ Kubernetes Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                    │
├─────────────────────────────────────────────────────────────┤
│  Ingress (NGINX)                                           │
│  ├─── sunday.com → Frontend Service                        │
│  └─── api.sunday.com → Backend Service                     │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                         │
│  ├─── Frontend (React + Nginx)                            │
│  ├─── Backend (Node.js + TypeScript)                      │
│  └─── Workers (Background Jobs)                           │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                │
│  ├─── PostgreSQL (Primary Database)                       │
│  ├─── Redis (Cache + Sessions)                            │
│  ├─── Elasticsearch (Search)                              │
│  └─── ClickHouse (Analytics)                             │
├─────────────────────────────────────────────────────────────┤
│  Monitoring & Observability                               │
│  ├─── Prometheus (Metrics)                                │
│  ├─── Grafana (Dashboards)                               │
│  └─── Jaeger (Tracing)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Strategy

#### Kustomize Structure

- **Base**: Common Kubernetes manifests
- **Overlays**: Environment-specific customizations
- **Patches**: Targeted modifications for different environments

#### Key Features

- **Auto-scaling**: HPA for frontend and backend
- **Security**: Network policies, security contexts, RBAC
- **Monitoring**: Prometheus metrics, health checks
- **Persistence**: StatefulSets for databases
- **Secrets**: Encrypted secret management

### Environment Configuration

#### Staging
- **Replicas**: Backend (2), Frontend (1)
- **Resources**: Lower resource limits
- **Databases**: Smaller storage allocations
- **Access**: HTTP basic auth protection

#### Production
- **Replicas**: Backend (5), Frontend (3)
- **Resources**: Higher resource limits and requests
- **Databases**: High availability, larger storage
- **Security**: Enhanced security policies

## 🏗️ Infrastructure as Code (Terraform)

### AWS Resources

#### Core Infrastructure
- **VPC**: Multi-AZ with public, private, and database subnets
- **EKS**: Kubernetes cluster with managed node groups
- **RDS**: PostgreSQL with Multi-AZ deployment
- **ElastiCache**: Redis cluster for caching
- **S3**: Object storage for files and backups

#### Security
- **IAM**: Roles and policies for services
- **Secrets Manager**: Centralized secret management
- **VPC Endpoints**: Private connectivity to AWS services
- **Security Groups**: Network access control

#### Monitoring
- **CloudWatch**: Logs and metrics
- **AWS X-Ray**: Distributed tracing
- **CloudTrail**: API audit logs

### Terraform Modules

```
terraform/
├── modules/
│   ├── vpc/              # VPC and networking
│   ├── eks/              # Kubernetes cluster
│   ├── rds/              # Database infrastructure
│   ├── elasticache/      # Redis caching
│   ├── s3/               # Object storage
│   └── monitoring/       # Observability stack
└── environments/
    ├── staging/          # Staging configuration
    └── production/       # Production configuration
```

### Deployment

```bash
# Initialize Terraform
terraform init

# Plan changes
terraform plan -var-file="environments/production/terraform.tfvars"

# Apply infrastructure
terraform apply -var-file="environments/production/terraform.tfvars"

# Update kubectl config
aws eks update-kubeconfig --name sunday-production --region us-east-1
```

## 📊 Monitoring and Observability

### Metrics (Prometheus + Grafana)

**System Metrics**:
- CPU, memory, disk usage
- Network I/O and latency
- Kubernetes cluster health

**Application Metrics**:
- Request rate, error rate, duration
- Database connections and query performance
- Cache hit rates and memory usage

**Business Metrics**:
- User activity and engagement
- Feature usage statistics
- Performance indicators

### Logging (ELK Stack)

**Log Aggregation**:
- Structured JSON logging
- Centralized log collection
- Real-time log analysis

**Log Sources**:
- Application logs (Node.js)
- Access logs (Nginx)
- System logs (Kubernetes)
- Audit logs (AWS CloudTrail)

### Alerting

**Alert Channels**:
- Slack notifications
- Email alerts
- PagerDuty integration

**Alert Rules**:
- High error rates
- Performance degradation
- Infrastructure issues
- Security events

## 🚨 Incident Response

### Health Monitoring

```bash
# Check overall system health
./scripts/monitoring/health-check.sh -e production

# Check specific services
kubectl get pods -n sunday-production
kubectl logs -f deployment/backend-deployment -n sunday-production
```

### Emergency Procedures

#### Rollback Deployment

```bash
# Emergency rollback
./scripts/deployment/rollback.sh -e production --force

# Rollback to specific revision
./scripts/deployment/rollback.sh -e production -r 3
```

#### Scale Services

```bash
# Scale backend pods
kubectl scale deployment backend-deployment --replicas=10 -n sunday-production

# Scale frontend pods
kubectl scale deployment frontend-deployment --replicas=5 -n sunday-production
```

#### Database Emergency

```bash
# Create immediate backup
kubectl create job emergency-backup --from=cronjob/database-backup -n sunday-production

# Access database directly
kubectl exec -it postgres-statefulset-0 -n sunday-production -- psql -U sunday_user -d sunday_db
```

## 🔧 Development Workflow

### Local Development

1. **Setup Environment**:
   ```bash
   ./scripts/setup/setup-local-dev.sh
   ```

2. **Start Development**:
   ```bash
   # Start services
   docker-compose up -d

   # Start backend
   cd backend && npm run dev

   # Start frontend
   cd frontend && npm run dev
   ```

3. **Run Tests**:
   ```bash
   # Backend tests
   cd backend && npm test

   # Frontend tests
   cd frontend && npm test

   # E2E tests
   cd e2e && npm test
   ```

### Deployment Process

1. **Feature Development**:
   - Create feature branch
   - Develop and test locally
   - Push to GitHub (triggers CI)

2. **Staging Deployment**:
   - Merge to main branch
   - Automatic deployment to staging
   - Run E2E tests

3. **Production Deployment**:
   - Create version tag
   - Manual approval required
   - Blue-green deployment
   - Smoke tests and verification

## 🔐 Security

### Container Security
- Non-root user execution
- Minimal base images (Alpine)
- Regular security scanning
- Read-only root filesystems

### Kubernetes Security
- Network policies
- Pod security contexts
- RBAC authorization
- Secret encryption at rest

### Infrastructure Security
- VPC isolation
- Security groups
- IAM least privilege
- Encryption in transit and at rest

### Application Security
- JWT authentication
- Rate limiting
- CORS protection
- Input validation

## 📈 Performance Optimization

### Application Performance
- Redis caching
- Database connection pooling
- CDN for static assets
- Gzip compression

### Infrastructure Performance
- Auto-scaling groups
- Load balancing
- Multi-AZ deployment
- SSD storage

### Monitoring Performance
- APM tools (Datadog)
- Real user monitoring
- Synthetic monitoring
- Performance budgets

## 🚀 Deployment Commands

### Local Development
```bash
# Setup everything
./scripts/setup/setup-local-dev.sh

# Health check
./scripts/monitoring/health-check.sh -e local
```

### Staging Deployment
```bash
# Deploy to staging
./scripts/deployment/deploy.sh -e staging -v main

# Health check
./scripts/monitoring/health-check.sh -e staging
```

### Production Deployment
```bash
# Deploy to production
./scripts/deployment/deploy.sh -e production -v v1.2.3

# Health check
./scripts/monitoring/health-check.sh -e production
```

### Emergency Operations
```bash
# Rollback production
./scripts/deployment/rollback.sh -e production --force

# Scale services
kubectl scale deployment backend-deployment --replicas=10 -n sunday-production
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🤝 Contributing

1. Follow the GitOps workflow
2. Test changes locally first
3. Use feature branches for development
4. Ensure all CI checks pass
5. Request review for infrastructure changes

## 📞 Support

For DevOps support and incident response:
- Slack: #devops-support
- Email: devops@sunday.com
- PagerDuty: Critical incidents only

---

*This infrastructure is designed for scale, security, and reliability. For questions or improvements, please reach out to the DevOps team.*