# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Kubernetes cluster (for production)
- PostgreSQL 16+
- Redis 7+

## Local Development

### 1. Clone Repository
```bash
git clone <repository-url>
cd eventsourcing-saas
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Run Migrations
```bash
docker-compose exec postgres psql -U postgres -d eventsourcing -f /docker-entrypoint-initdb.d/001_initial_schema.sql
docker-compose exec postgres psql -U postgres -d eventsourcing -f /docker-entrypoint-initdb.d/002_add_indexes.sql
```

### 5. Verify Installation
```bash
curl http://localhost:8000/health
```

## Production Deployment (Kubernetes)

### 1. Create Namespace
```bash
kubectl apply -f kubernetes/namespace.yaml
```

### 2. Configure Secrets
```bash
# Create secrets from environment variables
kubectl create secret generic eventsourcing-secrets \
  --from-literal=db_user=<DB_USER> \
  --from-literal=db_password=<DB_PASSWORD> \
  --from-literal=secret_key=<SECRET_KEY> \
  -n eventsourcing
```

### 3. Deploy Database
```bash
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl apply -f kubernetes/redis-deployment.yaml
```

### 4. Wait for Database
```bash
kubectl wait --for=condition=ready pod -l app=postgres -n eventsourcing --timeout=300s
```

### 5. Run Migrations
```bash
kubectl exec -it postgres-0 -n eventsourcing -- psql -U postgres -d eventsourcing < database/migrations/001_initial_schema.sql
kubectl exec -it postgres-0 -n eventsourcing -- psql -U postgres -d eventsourcing < database/migrations/002_add_indexes.sql
```

### 6. Deploy Application
```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/ingress.yaml
```

### 7. Verify Deployment
```bash
kubectl get pods -n eventsourcing
kubectl get svc -n eventsourcing
kubectl get ingress -n eventsourcing
```

## Monitoring Setup

### 1. Deploy Prometheus
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus -n eventsourcing
```

### 2. Deploy Grafana
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana -n eventsourcing
```

### 3. Access Dashboards
```bash
# Grafana
kubectl port-forward svc/grafana 3000:80 -n eventsourcing
# Visit http://localhost:3000

# Prometheus
kubectl port-forward svc/prometheus-server 9090:80 -n eventsourcing
# Visit http://localhost:9090
```

## Scaling

### Manual Scaling
```bash
kubectl scale deployment eventsourcing-api --replicas=5 -n eventsourcing
```

### Auto-scaling
HPA is configured in `kubernetes/hpa.yaml`:
- Min replicas: 3
- Max replicas: 10
- Target CPU: 70%
- Target Memory: 80%

## Backup and Recovery

### Database Backup
```bash
# Backup
kubectl exec -it postgres-0 -n eventsourcing -- pg_dump -U postgres eventsourcing > backup.sql

# Restore
kubectl exec -i postgres-0 -n eventsourcing -- psql -U postgres eventsourcing < backup.sql
```

### Event Store Backup
Since events are immutable, regular backups are critical:
```bash
# Automated backup script
kubectl exec -it postgres-0 -n eventsourcing -- pg_dump -U postgres -t events -t snapshots eventsourcing | gzip > events_backup_$(date +%Y%m%d).sql.gz
```

## Security Hardening

### 1. TLS/SSL
- Configure cert-manager for automatic certificate management
- Update ingress.yaml with proper domain

### 2. Network Policies
```bash
kubectl apply -f kubernetes/network-policies.yaml
```

### 3. Pod Security Policies
- Run containers as non-root
- Read-only root filesystem
- Drop unnecessary capabilities

### 4. Secrets Management
- Use external secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Rotate secrets regularly
- Never commit secrets to version control

## Troubleshooting

### Check Logs
```bash
kubectl logs -f deployment/eventsourcing-api -n eventsourcing
```

### Database Connection Issues
```bash
kubectl exec -it postgres-0 -n eventsourcing -- psql -U postgres -d eventsourcing -c "SELECT COUNT(*) FROM events;"
```

### Performance Issues
```bash
# Check HPA status
kubectl get hpa -n eventsourcing

# Check resource usage
kubectl top pods -n eventsourcing
kubectl top nodes
```

## Rollback

```bash
kubectl rollout undo deployment/eventsourcing-api -n eventsourcing
kubectl rollout status deployment/eventsourcing-api -n eventsourcing
```

## Maintenance

### Update Application
```bash
# Build new image
docker build -t eventsourcing-api:v2.0.0 .

# Push to registry
docker push eventsourcing-api:v2.0.0

# Update deployment
kubectl set image deployment/eventsourcing-api api=eventsourcing-api:v2.0.0 -n eventsourcing

# Monitor rollout
kubectl rollout status deployment/eventsourcing-api -n eventsourcing
```

### Database Maintenance
```bash
# Vacuum and analyze
kubectl exec -it postgres-0 -n eventsourcing -- psql -U postgres -d eventsourcing -c "VACUUM ANALYZE;"

# Reindex
kubectl exec -it postgres-0 -n eventsourcing -- psql -U postgres -d eventsourcing -c "REINDEX DATABASE eventsourcing;"
```