# Sunday.com Deployment Quick Reference Guide
## DevOps Operations - Enhanced Infrastructure

**Last Updated**: December 19, 2024
**DevOps Engineer**: Senior DevOps Specialist

---

## 🚀 Quick Deployment Commands

### 1. Enhanced Deployment Script
```bash
# Full production deployment
DEPLOY_ENV=production DEPLOY_STRATEGY=rolling ./scripts/deployment/enhanced-deploy.sh deploy

# Validation only
./scripts/deployment/enhanced-deploy.sh validate

# Emergency rollback
./scripts/deployment/enhanced-deploy.sh rollback
```

### 2. Docker Compose (Development/Testing)
```bash
# Start all services
docker-compose -f docker-compose.yml up -d

# Production environment
docker-compose -f docker-compose.production.yml up -d

# Stop and cleanup
docker-compose down --volumes --remove-orphans
```

### 3. Kubernetes Deployment
```bash
# Deploy to production
kubectl apply -f k8s/production/enhanced-deployment.yaml

# Check deployment status
kubectl get pods -n sunday-com-prod
kubectl get services -n sunday-com-prod

# Scale deployment
kubectl scale deployment sunday-backend --replicas=5 -n sunday-com-prod
```

### 4. Infrastructure Provisioning (Terraform)
```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars"

# Apply infrastructure
terraform apply -var-file="production.tfvars"

# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name sunday-com-production-eks
```

---

## 🔍 Health Check Commands

### System Health
```bash
# Check all Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check Kubernetes pods
kubectl get pods --all-namespaces

# Check service endpoints
curl -f http://localhost:3000/health  # Backend
curl -f http://localhost:80/health    # Frontend
```

### Database Health
```bash
# PostgreSQL connection test
docker exec sunday-postgres pg_isready -U sunday_user

# Redis connection test
docker exec sunday-redis redis-cli ping
```

### Monitoring Access
```bash
# Grafana Dashboard
open http://localhost:3001  # Username: admin, Password: admin123

# Prometheus Metrics
open http://localhost:9090

# Application Logs
docker logs sunday-backend -f
docker logs sunday-frontend -f
```

---

## 🛠️ Troubleshooting Commands

### Container Issues
```bash
# View container logs
docker logs <container-name> --tail 100 -f

# Execute into container
docker exec -it <container-name> /bin/bash

# Restart specific service
docker-compose restart <service-name>

# Check resource usage
docker stats
```

### Kubernetes Issues
```bash
# Describe pod issues
kubectl describe pod <pod-name> -n sunday-com-prod

# View pod logs
kubectl logs <pod-name> -n sunday-com-prod -f

# Check events
kubectl get events -n sunday-com-prod --sort-by='.lastTimestamp'

# Pod shell access
kubectl exec -it <pod-name> -n sunday-com-prod -- /bin/bash
```

### Database Issues
```bash
# PostgreSQL shell
docker exec -it sunday-postgres psql -U sunday_user -d sunday_db

# Check database connections
docker exec sunday-postgres psql -U sunday_user -d sunday_db -c "SELECT count(*) FROM pg_stat_activity;"

# Redis CLI
docker exec -it sunday-redis redis-cli

# Check Redis memory usage
docker exec sunday-redis redis-cli info memory
```

---

## 📊 Monitoring & Metrics

### Key Metrics URLs
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Application Health**: http://localhost:3000/health
- **Frontend Health**: http://localhost:80/health

### Important Metrics to Monitor
```bash
# CPU Usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Memory Usage
free -h

# Disk Usage
df -h

# Network Connections
netstat -tlnp | grep -E '(3000|80|5432|6379)'
```

### Log Locations
```bash
# Application Logs
tail -f logs/deployment/deploy_*.log

# Docker Logs
docker logs sunday-backend --tail 100 -f
docker logs sunday-frontend --tail 100 -f

# System Logs
tail -f /var/log/syslog
```

---

## 🔧 Common Operations

### Scaling Operations
```bash
# Scale backend horizontally
docker-compose up -d --scale backend=3

# Kubernetes scaling
kubectl scale deployment sunday-backend --replicas=5 -n sunday-com-prod

# Auto-scaling status
kubectl get hpa -n sunday-com-prod
```

### Configuration Updates
```bash
# Update environment variables
docker-compose down
# Edit .env file
docker-compose up -d

# Kubernetes config update
kubectl create configmap sunday-config --from-file=config/ -n sunday-com-prod --dry-run=client -o yaml | kubectl apply -f -
```

### Backup Operations
```bash
# Database backup
docker exec sunday-postgres pg_dump -U sunday_user sunday_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis backup
docker exec sunday-redis redis-cli --rdb dump.rdb

# Application data backup
tar -czf app_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/
```

---

## 🚨 Emergency Procedures

### Emergency Rollback
```bash
# Using enhanced deployment script
./scripts/deployment/enhanced-deploy.sh rollback

# Docker Compose rollback
docker-compose down
git checkout <previous-commit>
docker-compose up -d

# Kubernetes rollback
kubectl rollout undo deployment/sunday-backend -n sunday-com-prod
kubectl rollout undo deployment/sunday-frontend -n sunday-com-prod
```

### Emergency Scale Down
```bash
# Stop non-essential services
docker-compose stop minio prometheus grafana jaeger

# Scale down to minimal resources
kubectl scale deployment sunday-backend --replicas=1 -n sunday-com-prod
kubectl scale deployment sunday-frontend --replicas=1 -n sunday-com-prod
```

### Emergency Database Recovery
```bash
# Restore from backup
docker exec -i sunday-postgres psql -U sunday_user -d sunday_db < backup_file.sql

# Check database integrity
docker exec sunday-postgres psql -U sunday_user -d sunday_db -c "SELECT version();"
```

---

## 📋 Pre-Deployment Checklist

### Before Deployment
- [ ] Run `./scripts/deployment/enhanced-deploy.sh validate`
- [ ] Check disk space: `df -h`
- [ ] Check memory usage: `free -h`
- [ ] Verify network connectivity: `ping 8.8.8.8`
- [ ] Check Docker daemon: `docker info`
- [ ] Verify environment variables: `cat .env`

### During Deployment
- [ ] Monitor deployment logs: `tail -f logs/deployment/deploy_*.log`
- [ ] Watch container status: `docker ps`
- [ ] Monitor resource usage: `docker stats`
- [ ] Check health endpoints: `curl http://localhost:3000/health`

### After Deployment
- [ ] Run smoke tests: `./scripts/deployment/enhanced-deploy.sh validate`
- [ ] Check application functionality
- [ ] Verify monitoring dashboards
- [ ] Confirm backup operations
- [ ] Update deployment documentation

---

## 🔐 Security Operations

### SSL/TLS Certificate Management
```bash
# Check certificate expiry
openssl x509 -in certificate.crt -text -noout | grep "Not After"

# Renew Let's Encrypt certificates
certbot renew --dry-run

# Update Kubernetes TLS secrets
kubectl create secret tls sunday-com-tls --cert=cert.pem --key=key.pem -n sunday-com-prod
```

### Security Scanning
```bash
# Container vulnerability scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image sunday-backend:latest

# Network security check
nmap -sS -p 80,443,3000,5432,6379 localhost

# Log analysis
grep -i "error\|fail\|attack" /var/log/nginx/error.log
```

---

## 📞 Support & Escalation

### Contact Information
- **DevOps Team**: devops@sunday.com
- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Infrastructure Provider**: AWS Support
- **Monitoring Alerts**: Slack #ops-alerts

### Escalation Matrix
1. **Level 1**: Application Issues → Development Team
2. **Level 2**: Infrastructure Issues → DevOps Team
3. **Level 3**: Critical System Failure → Senior Engineering Manager
4. **Level 4**: Security Incident → CISO & Legal Team

### Useful Documentation
- [Sunday.com Architecture Documentation](./architecture_document.md)
- [API Documentation](./API_DOCUMENTATION_COMPLETE.md)
- [Security Review](./security_review.md)
- [Deployment Guide](./deployment_guide.md)

---

**Quick Reference Guide Created by**: Senior DevOps Specialist
**Infrastructure Status**: Production Ready
**Last Validation**: December 19, 2024
**Next Review**: January 19, 2025