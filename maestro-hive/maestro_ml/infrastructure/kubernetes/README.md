# Kubernetes Deployment

Kubernetes manifests for deploying Maestro ML Platform to a production cluster.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Container registry access
- Ingress controller (nginx)
- cert-manager (for TLS)
- Metrics server (for HPA)

## Quick Deploy

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (update values first!)
kubectl apply -f secrets.yaml

# Create config
kubectl apply -f configmap.yaml

# Deploy persistent volumes
kubectl apply -f pvc.yaml

# Deploy services
kubectl apply -f service.yaml

# Deploy applications
kubectl apply -f deployment.yaml

# Setup ingress
kubectl apply -f ingress.yaml

# Enable autoscaling
kubectl apply -f hpa.yaml
```

## Configuration

### 1. Update Secrets

Edit `secrets.yaml` and replace all `CHANGE_ME` values:

```bash
# Generate a secure secret key
openssl rand -hex 32

# Update DATABASE_URL with your PostgreSQL connection
# Update AWS credentials if using S3
```

### 2. Update Ingress

Edit `ingress.yaml` and replace `api.maestro-ml.example.com` with your domain.

### 3. Configure Storage Class

Edit `pvc.yaml` and update `storageClassName` to match your cluster's storage class:

```bash
kubectl get storageclass
```

## Verify Deployment

```bash
# Check all resources
kubectl get all -n maestro-ml

# Check pods
kubectl get pods -n maestro-ml

# View logs
kubectl logs -f -n maestro-ml deployment/maestro-api

# Check HPA status
kubectl get hpa -n maestro-ml
```

## Scaling

### Manual Scaling

```bash
# Scale API replicas
kubectl scale deployment/maestro-api -n maestro-ml --replicas=5

# Scale workers
kubectl scale deployment/maestro-worker -n maestro-ml --replicas=3
```

### Auto-scaling (HPA)

The HPA is configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Min replicas: 2
- Max replicas: 10

## Monitoring

```bash
# CPU and memory usage
kubectl top pods -n maestro-ml

# Resource requests/limits
kubectl describe deployment/maestro-api -n maestro-ml
```

## Troubleshooting

### Pods not starting

```bash
# Check events
kubectl describe pod <pod-name> -n maestro-ml

# View logs
kubectl logs <pod-name> -n maestro-ml

# Check secrets
kubectl get secret maestro-secrets -n maestro-ml -o yaml
```

### Database connection issues

```bash
# Test PostgreSQL connection
kubectl run -it --rm debug --image=postgres:14 --restart=Never -n maestro-ml -- \
  psql postgresql://maestro:password@maestro-postgres:5432/maestro_ml
```

### Ingress not working

```bash
# Check ingress
kubectl describe ingress maestro-ingress -n maestro-ml

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Database Migrations

```bash
# Run migrations
kubectl exec -it deployment/maestro-api -n maestro-ml -- \
  alembic upgrade head
```

## Backup and Restore

### PostgreSQL Backup

```bash
# Backup database
kubectl exec deployment/maestro-postgres -n maestro-ml -- \
  pg_dump -U maestro maestro_ml > backup.sql

# Restore database
kubectl exec -i deployment/maestro-postgres -n maestro-ml -- \
  psql -U maestro maestro_ml < backup.sql
```

## Production Checklist

- [ ] Update all secrets in `secrets.yaml`
- [ ] Configure proper ingress hostname
- [ ] Setup TLS certificates
- [ ] Configure resource limits
- [ ] Enable pod disruption budgets
- [ ] Setup monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Setup database backups
- [ ] Configure network policies
- [ ] Enable pod security policies
- [ ] Setup external secret management

## Clean Up

```bash
# Delete all resources
kubectl delete namespace maestro-ml
```
