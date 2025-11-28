# Maestro Platform - Infrastructure as Code & Automation Guide

**Complete automation stack for zero-manual-effort deployments**

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAESTRO PLATFORM IaC STACK                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Infrastructure Provisioning (Terraform)               │
│  ├── Network Module        → Docker networks                    │
│  ├── Database Module       → PostgreSQL + Redis                 │
│  ├── Monitoring Module     → Prometheus + Grafana              │
│  └── Compute Module        → Application containers            │
│                                                                 │
│  Layer 2: Configuration Management (Ansible)                    │
│  ├── OS Configuration      → Security, users, packages          │
│  ├── Service Configuration → Grafana orgs, Prometheus targets   │
│  ├── Secret Management     → Vault/AWS SSM integration         │
│  └── Post-Deploy Tasks     → Health checks, backups            │
│                                                                 │
│  Layer 3: Container Orchestration (Docker Compose)              │
│  ├── Service Discovery     → maestro-network                    │
│  ├── Health Checks         → Auto-restart policies             │
│  ├── Volume Management     → Persistent data                    │
│  └── Environment Configs   → Per-environment overrides          │
│                                                                 │
│  Layer 4: CI/CD Pipeline (GitHub Actions)                       │
│  ├── Validation            → terraform fmt, validate            │
│  ├── Planning              → terraform plan                     │
│  ├── Deployment            → terraform apply + ansible          │
│  └── Rollback              → Automated on failure              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start (Zero Manual Steps)

### Option 1: One-Command Deployment (Recommended)

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Deploy to demo environment
./maestro-deploy.sh demo

# Deploy to staging
./maestro-deploy.sh staging

# Deploy to production
./maestro-deploy.sh prod
```

**That's it!** The script:
- ✅ Checks prerequisites
- ✅ Loads configuration
- ✅ Creates directories
- ✅ Provisions infrastructure with Terraform
- ✅ Applies configuration with Ansible
- ✅ Runs health checks
- ✅ Displays access URLs

### Option 2: Terraform Only

```bash
cd terraform/environments/demo

# Load secrets
export TF_VAR_postgres_admin_password="your-password"
export TF_VAR_redis_password="your-password"
export TF_VAR_grafana_admin_password="your-password"

# Deploy
terraform init
terraform plan
terraform apply -auto-approve
```

### Option 3: Ansible Only (existing infrastructure)

```bash
cd ansible

# Deploy configuration
ansible-playbook \
  -i inventory/demo.ini \
  playbooks/deploy-infrastructure.yml \
  -e "deployment_environment=demo"
```

## Directory Structure

```
infrastructure/
├── maestro-deploy.sh              ← Master deployment script
├── deploy.sh                       ← Legacy script (being replaced)
│
├── terraform/                      ← Infrastructure as Code
│   ├── modules/                    ← Reusable modules
│   │   ├── network/                → Docker networks
│   │   ├── database/               → PostgreSQL + Redis
│   │   ├── monitoring/             → Prometheus + Grafana
│   │   └── compute/                → Application services
│   └── environments/               ← Environment-specific configs
│       ├── dev/
│       ├── demo/
│       ├── staging/
│       └── prod/
│
├── ansible/                        ← Configuration management
│   ├── playbooks/
│   │   ├── deploy-infrastructure.yml
│   │   ├── post-deploy-config.yml
│   │   └── backup-restore.yml
│   ├── roles/
│   │   ├── common/                 → Base OS config
│   │   ├── docker/                 → Docker installation
│   │   ├── security/               → Security hardening
│   │   └── monitoring/             → Monitoring agents
│   └── inventory/
│       ├── demo.ini
│       ├── staging.ini
│       └── prod.ini
│
├── k8s/                            ← Kubernetes manifests (production)
│   ├── base/                       → Base configurations
│   └── overlays/                   → Environment overlays
│       ├── dev/
│       ├── demo/
│       ├── staging/
│       └── prod/
│
├── ci-cd/                          ← CI/CD pipelines
│   ├── github-actions/
│   │   └── deploy-infrastructure.yml
│   └── gitlab-ci/
│       └── .gitlab-ci.yml
│
├── docker-compose.infrastructure.yml  ← Fallback compose file
├── .env.infrastructure             ← Environment variables
└── databases/                      ← Database init scripts
    └── postgres/
        └── init-scripts/
            └── 01-create-databases.sql
```

## Terraform Modules

### Network Module
Creates isolated Docker networks with proper CIDR allocation.

```hcl
module "network" {
  source = "../../modules/network"

  network_name = "maestro-network"
  environment  = "demo"
  subnet_cidr  = "172.28.0.0/16"
}
```

### Database Module
Provisions PostgreSQL with multi-database setup and Redis with namespace isolation.

```hcl
module "database" {
  source = "../../modules/database"

  environment         = "demo"
  network_name        = module.network.network_name
  admin_password      = var.postgres_admin_password
  redis_password      = var.redis_password
  external_port       = 25432
  redis_external_port = 27379
}
```

### Monitoring Module
Deploys Prometheus and Grafana with automatic configuration.

```hcl
module "monitoring" {
  source = "../../modules/monitoring"

  environment            = "demo"
  network_name           = module.network.network_name
  prometheus_port        = 29090
  grafana_port           = 23000
  grafana_admin_password = var.grafana_admin_password
}
```

## Ansible Roles

### Common Role
- Sets up base OS configuration
- Installs required packages
- Configures users and SSH

### Docker Role
- Installs Docker and Docker Compose
- Configures Docker daemon
- Sets up logging drivers

### Security Role
- Configures firewall rules
- Sets up fail2ban
- Hardens SSH configuration
- Manages SSL certificates

### Monitoring Role
- Installs node_exporter for Prometheus
- Configures log forwarding
- Sets up alerting rules

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy-infrastructure.yml
name: Deploy Maestro Infrastructure

on:
  push:
    branches: [main, demo, staging]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform apply -auto-approve
```

### Secrets Configuration

Required GitHub Secrets:
```
POSTGRES_ADMIN_PASSWORD
REDIS_PASSWORD
GRAFANA_ADMIN_PASSWORD
```

## Environment Configuration

### Demo Environment
```bash
# terraform/environments/demo/terraform.tfvars
postgres_port   = 25432
redis_port      = 27379
prometheus_port = 29090
grafana_port    = 23000
```

### Staging Environment
```bash
# terraform/environments/staging/terraform.tfvars
postgres_port   = 35432
redis_port      = 36379
prometheus_port = 39090
grafana_port    = 33000
```

### Production Environment
```bash
# terraform/environments/prod/terraform.tfvars
postgres_port   = 5432
redis_port      = 6379
prometheus_port = 9090
grafana_port    = 3000
```

## Deployment Workflows

### New Environment Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd maestro-platform/infrastructure

# 2. Create environment file
cp .env.infrastructure.template .env.infrastructure
# Edit passwords

# 3. Deploy
./maestro-deploy.sh demo
```

### Update Existing Infrastructure

```bash
# 1. Pull latest code
git pull

# 2. Plan changes
cd terraform/environments/demo
terraform plan

# 3. Apply changes
terraform apply -auto-approve
```

### Destroy Infrastructure

```bash
cd terraform/environments/demo
terraform destroy -auto-approve
```

## Port Management Strategy

### Problem: Port Conflicts
Manual port assignment leads to conflicts across environments.

### Solution: Service Discovery + Dynamic Ports

**Internal Communication** (via Docker network):
```bash
# Services communicate using container names
postgresql://maestro-postgres-demo:5432/quality_fabric
redis://maestro-redis-demo:6379/0
```

**External Access** (host ports):
```bash
# Only for admin/debugging - dynamically assigned
MAESTRO_POSTGRES_PORT=25432  # Can be auto-detected if conflict
```

### Port Auto-Detection
The `maestro-deploy.sh` script automatically finds available ports:

```bash
find_available_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo $port
}
```

## Secret Management

### Local Development
```bash
# .env.infrastructure
MAESTRO_POSTGRES_ADMIN_PASSWORD=local_password
```

### Demo/Staging (AWS SSM)
```bash
# Ansible loads from AWS Systems Manager
ansible-playbook playbooks/deploy.yml \
  -e "secrets_backend=aws_ssm"
```

### Production (HashiCorp Vault)
```bash
# Ansible loads from Vault
ansible-playbook playbooks/deploy.yml \
  -e "secrets_backend=vault" \
  -e "vault_addr=https://vault.example.com"
```

## Monitoring & Observability

### Infrastructure Monitoring
- **Prometheus**: Scrapes all infrastructure components
- **Grafana**: Visualizes metrics with pre-configured dashboards
- **Health Checks**: Automated health monitoring for all services

### Service Monitoring
Services auto-register with Prometheus via labels:

```yaml
labels:
  - maestro.service=quality-fabric
  - maestro.team=quality
  - maestro.layer=application
```

Query in Prometheus:
```promql
http_requests_total{maestro_service="quality-fabric"}
```

## Backup & Disaster Recovery

### Automated Backups

```bash
# PostgreSQL backup (automated via cron)
ansible-playbook playbooks/backup-postgres.yml

# Manual backup
docker exec maestro-postgres-demo pg_dumpall -U maestro_admin > backup.sql
```

### Restore from Backup

```bash
ansible-playbook playbooks/restore-postgres.yml \
  -e "backup_file=/path/to/backup.sql"
```

## Troubleshooting

### Terraform Issues

```bash
# Refresh state
terraform refresh

# Force unlock if stuck
terraform force-unlock <lock-id>

# Re-initialize
rm -rf .terraform
terraform init
```

### Ansible Issues

```bash
# Verbose output
ansible-playbook -vvv playbooks/deploy.yml

# Check connectivity
ansible all -i inventory/demo.ini -m ping

# Dry run
ansible-playbook playbooks/deploy.yml --check
```

### Container Issues

```bash
# View logs
docker logs -f maestro-postgres-demo

# Restart service
docker restart maestro-grafana-demo

# Inspect network
docker network inspect maestro-network
```

## Best Practices

1. **Never commit secrets** - Use environment variables or secret managers
2. **Always plan before apply** - Run `terraform plan` first
3. **Use workspaces** - Isolate state per environment
4. **Tag resources** - Use consistent labeling
5. **Automate everything** - No manual steps in deployment
6. **Test in demo first** - Always validate in lower environments
7. **Monitor deployments** - Watch health checks during deployment
8. **Have rollback plan** - Test `terraform destroy` regularly

## Next Steps

- [ ] Set up GitHub Actions secrets
- [ ] Configure AWS SSM for staging
- [ ] Set up Vault for production
- [ ] Create Kubernetes manifests
- [ ] Configure auto-scaling policies
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Implement blue-green deployments

## Support

For issues or questions:
- Infrastructure: [infrastructure-team@maestro.com](mailto:infrastructure-team@maestro.com)
- Documentation: `/maestro-platform/infrastructure/README.md`
- Runbooks: `/maestro-platform/infrastructure/docs/runbooks/`
