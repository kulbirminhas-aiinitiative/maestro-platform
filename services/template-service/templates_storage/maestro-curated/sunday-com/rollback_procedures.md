# Sunday.com Rollback Procedures

## Table of Contents

1. [Overview](#overview)
2. [Rollback Strategy](#rollback-strategy)
3. [Rollback Types](#rollback-types)
4. [Automated Rollback Systems](#automated-rollback-systems)
5. [Manual Rollback Procedures](#manual-rollback-procedures)
6. [Database Rollback](#database-rollback)
7. [Infrastructure Rollback](#infrastructure-rollback)
8. [Verification and Validation](#verification-and-validation)
9. [Post-Rollback Actions](#post-rollback-actions)
10. [Emergency Procedures](#emergency-procedures)

---

## Overview

This document outlines comprehensive rollback procedures for Sunday.com to ensure rapid recovery from deployment issues, system failures, or critical bugs. The rollback strategy is designed to minimize downtime and maintain system integrity across all environments.

### Rollback Principles

- **Speed**: Complete rollback within 15 minutes for critical issues
- **Safety**: Preserve data integrity during all rollback operations
- **Automation**: Prefer automated rollback over manual intervention
- **Monitoring**: Continuous monitoring during rollback process
- **Communication**: Clear communication to all stakeholders

### Rollback Triggers

- **Performance Degradation**: Response times >5x baseline
- **Critical Bugs**: System-breaking functionality issues
- **Security Vulnerabilities**: Newly discovered security flaws
- **Data Integrity Issues**: Corruption or loss of user data
- **Failed Health Checks**: Multiple service health check failures

---

## Rollback Strategy

### Decision Matrix

| Issue Severity | Response Time | Rollback Type | Authority Required |
|----------------|---------------|---------------|-------------------|
| **P0 - Critical** | <5 minutes | Automated | On-call Engineer |
| **P1 - High** | <15 minutes | Semi-automated | Engineering Lead |
| **P2 - Medium** | <1 hour | Manual | Engineering Manager |
| **P3 - Low** | Next release | Scheduled | Product Team |

### Rollback Workflow

```
Issue Detection → Assessment → Decision → Execution → Verification → Communication
     ↓              ↓           ↓          ↓            ↓              ↓
  Monitoring    Impact Analysis  Go/No-Go   Rollback   Health Check   Stakeholder
   Alerts       Risk Assessment  Decision   Process    Validation     Notification
```

---

## Rollback Types

### 1. Application Rollback

**Scope**: Application code and configuration
**Impact**: Service functionality
**Downtime**: 2-5 minutes

```bash
# Quick application rollback
kubectl rollout undo deployment/backend-deployment -n sunday-production
kubectl rollout undo deployment/frontend-deployment -n sunday-production
```

### 2. Database Rollback

**Scope**: Database schema and data
**Impact**: Data state and structure
**Downtime**: 15-60 minutes (depending on data size)

```bash
# Database rollback from backup
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier sunday-production-rollback \
  --snapshot-identifier backup-20241201-120000
```

### 3. Infrastructure Rollback

**Scope**: Kubernetes manifests, networking, security
**Impact**: System configuration
**Downtime**: 5-15 minutes

```bash
# Infrastructure rollback using GitOps
git revert HEAD --no-edit
argocd app sync sunday-production
```

### 4. Full Environment Rollback

**Scope**: Complete environment state
**Impact**: Entire system
**Downtime**: 30-120 minutes

```bash
# Complete environment restoration
./scripts/full-environment-rollback.sh v1.2.3 production
```

---

## Automated Rollback Systems

### 1. Circuit Breaker Pattern

Automatic service isolation when failure thresholds are exceeded:

```javascript
// Circuit breaker configuration
const circuitBreakerConfig = {
  errorThreshold: 50,      // 50% error rate
  timeout: 60000,          // 60 second timeout
  resetTimeout: 30000,     // 30 second reset period
  monitoringPeriod: 10000  // 10 second monitoring window
};
```

### 2. Health Check Based Rollback

Automated rollback triggered by failed health checks:

```yaml
# k8s/health-check-monitor.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: health-check-monitor
spec:
  schedule: "*/2 * * * *"  # Every 2 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: monitor
            image: ghcr.io/sunday/health-monitor:latest
            env:
            - name: ROLLBACK_THRESHOLD
              value: "3"  # 3 consecutive failures trigger rollback
```

### 3. Performance-Based Rollback

Automatic rollback when performance degrades:

```python
# monitoring/performance_monitor.py
def check_performance_metrics():
    avg_response_time = get_average_response_time(300)  # 5 minutes
    error_rate = get_error_rate(300)

    if avg_response_time > RESPONSE_TIME_THRESHOLD or error_rate > ERROR_RATE_THRESHOLD:
        trigger_automatic_rollback()
```

### 4. Canary Analysis Rollback

Automated rollback during canary deployments:

```yaml
# argo-rollouts/canary-config.yaml
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: backend-service
      steps:
      - setWeight: 10
      - pause: {duration: 5m}
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: backend-canary
```

---

## Manual Rollback Procedures

### 1. Emergency Application Rollback

Use when automated systems fail or manual intervention is required:

```bash
#!/bin/bash
# scripts/emergency-rollback.sh

set -e

ENVIRONMENT=${1:-production}
NAMESPACE="sunday-$ENVIRONMENT"

echo "🚨 EMERGENCY ROLLBACK INITIATED for $ENVIRONMENT"
echo "Time: $(date)"

# Step 1: Enable maintenance mode
echo "🔧 Enabling maintenance mode..."
kubectl patch configmap app-config -n $NAMESPACE \
  -p '{"data":{"maintenance_mode":"true","maintenance_message":"System under maintenance - will be back shortly"}}'

# Step 2: Scale down problematic services
echo "📉 Scaling down services..."
kubectl scale deployment backend-deployment --replicas=1 -n $NAMESPACE
kubectl scale deployment frontend-deployment --replicas=1 -n $NAMESPACE

# Step 3: Rollback application
echo "🔄 Rolling back application..."
kubectl rollout undo deployment/backend-deployment -n $NAMESPACE
kubectl rollout undo deployment/frontend-deployment -n $NAMESPACE

# Step 4: Wait for rollback completion
echo "⏳ Waiting for rollback to complete..."
kubectl rollout status deployment/backend-deployment -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/frontend-deployment -n $NAMESPACE --timeout=300s

# Step 5: Disable maintenance mode
echo "✅ Disabling maintenance mode..."
kubectl patch configmap app-config -n $NAMESPACE \
  -p '{"data":{"maintenance_mode":"false"}}'

# Step 6: Scale back up
echo "📈 Scaling services back up..."
if [ "$ENVIRONMENT" = "production" ]; then
  kubectl scale deployment backend-deployment --replicas=3 -n $NAMESPACE
  kubectl scale deployment frontend-deployment --replicas=2 -n $NAMESPACE
else
  kubectl scale deployment backend-deployment --replicas=2 -n $NAMESPACE
  kubectl scale deployment frontend-deployment --replicas=1 -n $NAMESPACE
fi

# Step 7: Verify rollback
echo "🧪 Verifying rollback..."
sleep 30
./scripts/smoke-tests.sh $ENVIRONMENT

echo "✅ EMERGENCY ROLLBACK COMPLETED"
echo "Current version: $(kubectl get deployment backend-deployment -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')"
```

### 2. Blue-Green Rollback

For environments using blue-green deployment strategy:

```bash
#!/bin/bash
# scripts/blue-green-rollback.sh

ENVIRONMENT=${1:-production}
NAMESPACE="sunday-$ENVIRONMENT"

echo "🔄 Blue-Green rollback for $ENVIRONMENT"

# Identify current active environment
CURRENT_SELECTOR=$(kubectl get service backend-service -n $NAMESPACE -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT_SELECTOR" = "green" ]; then
  ROLLBACK_TO="blue"
else
  ROLLBACK_TO="green"
fi

echo "Current active: $CURRENT_SELECTOR"
echo "Rolling back to: $ROLLBACK_TO"

# Check if rollback target exists and is healthy
if ! kubectl get deployment backend-deployment-$ROLLBACK_TO -n $NAMESPACE >/dev/null 2>&1; then
  echo "❌ Rollback target deployment not found: backend-deployment-$ROLLBACK_TO"
  exit 1
fi

# Verify rollback target health
kubectl rollout status deployment/backend-deployment-$ROLLBACK_TO -n $NAMESPACE

# Switch traffic to rollback target
echo "🔀 Switching traffic to $ROLLBACK_TO environment..."
kubectl patch service backend-service -n $NAMESPACE \
  -p "{\"spec\":{\"selector\":{\"version\":\"$ROLLBACK_TO\"}}}"
kubectl patch service frontend-service -n $NAMESPACE \
  -p "{\"spec\":{\"selector\":{\"version\":\"$ROLLBACK_TO\"}}}"

# Wait and verify
sleep 30
./scripts/smoke-tests.sh $ENVIRONMENT

echo "✅ Blue-Green rollback completed"
```

### 3. Version-Specific Rollback

Rollback to a specific version:

```bash
#!/bin/bash
# scripts/version-rollback.sh

TARGET_VERSION=${1}
ENVIRONMENT=${2:-staging}
NAMESPACE="sunday-$ENVIRONMENT"

if [ -z "$TARGET_VERSION" ]; then
  echo "Usage: $0 <version> [environment]"
  echo "Available versions:"
  kubectl rollout history deployment/backend-deployment -n $NAMESPACE
  exit 1
fi

echo "🔄 Rolling back to version: $TARGET_VERSION"

# Update deployment with target version
kubectl set image deployment/backend-deployment \
  backend=ghcr.io/sunday/backend:$TARGET_VERSION \
  -n $NAMESPACE

kubectl set image deployment/frontend-deployment \
  frontend=ghcr.io/sunday/frontend:$TARGET_VERSION \
  -n $NAMESPACE

# Wait for rollout
kubectl rollout status deployment/backend-deployment -n $NAMESPACE
kubectl rollout status deployment/frontend-deployment -n $NAMESPACE

# Verify rollback
./scripts/smoke-tests.sh $ENVIRONMENT

echo "✅ Version rollback completed"
```

---

## Database Rollback

### 1. Point-in-Time Recovery

For minor data issues or recent changes:

```bash
#!/bin/bash
# scripts/database-point-in-time-recovery.sh

TARGET_TIME=${1}
ENVIRONMENT=${2:-staging}

if [ -z "$TARGET_TIME" ]; then
  echo "Usage: $0 <YYYY-MM-DDTHH:MM:SS> [environment]"
  echo "Example: $0 2024-12-01T14:30:00"
  exit 1
fi

echo "🕒 Point-in-time recovery to: $TARGET_TIME"

# Create new cluster from point-in-time
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier sunday-$ENVIRONMENT-recovery \
  --source-db-cluster-identifier sunday-$ENVIRONMENT \
  --restore-to-time $TARGET_TIME \
  --restore-type full-copy

# Wait for cluster to be available
echo "⏳ Waiting for recovery cluster to be available..."
aws rds wait db-cluster-available \
  --db-cluster-identifier sunday-$ENVIRONMENT-recovery

echo "✅ Point-in-time recovery completed"
echo "New cluster: sunday-$ENVIRONMENT-recovery"
```

### 2. Snapshot Restoration

For major issues or planned rollbacks:

```bash
#!/bin/bash
# scripts/database-snapshot-restore.sh

SNAPSHOT_ID=${1}
ENVIRONMENT=${2:-staging}

if [ -z "$SNAPSHOT_ID" ]; then
  echo "Usage: $0 <snapshot-id> [environment]"
  echo "Available snapshots:"
  aws rds describe-db-snapshots \
    --db-cluster-identifier sunday-$ENVIRONMENT \
    --snapshot-type manual \
    --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
    --output table
  exit 1
fi

echo "📦 Restoring from snapshot: $SNAPSHOT_ID"

# Restore cluster from snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier sunday-$ENVIRONMENT-restored \
  --snapshot-identifier $SNAPSHOT_ID

# Wait for restoration
echo "⏳ Waiting for restoration to complete..."
aws rds wait db-cluster-available \
  --db-cluster-identifier sunday-$ENVIRONMENT-restored

echo "✅ Snapshot restoration completed"
```

### 3. Schema Rollback

For database schema changes:

```bash
#!/bin/bash
# scripts/schema-rollback.sh

MIGRATION_VERSION=${1}
ENVIRONMENT=${2:-staging}

if [ -z "$MIGRATION_VERSION" ]; then
  echo "Usage: $0 <migration-version> [environment]"
  exit 1
fi

echo "🗃️ Rolling back schema to migration: $MIGRATION_VERSION"

# Run rollback migration
kubectl exec -it deployment/backend-deployment -n sunday-$ENVIRONMENT -- \
  npm run migrate:rollback -- --to $MIGRATION_VERSION

echo "✅ Schema rollback completed"
```

---

## Infrastructure Rollback

### 1. Kubernetes Configuration Rollback

```bash
#!/bin/bash
# scripts/k8s-config-rollback.sh

COMMIT_HASH=${1}
ENVIRONMENT=${2:-staging}

if [ -z "$COMMIT_HASH" ]; then
  echo "Usage: $0 <git-commit-hash> [environment]"
  exit 1
fi

echo "⚙️ Rolling back Kubernetes configuration to: $COMMIT_HASH"

# Checkout specific commit
git checkout $COMMIT_HASH k8s/$ENVIRONMENT/

# Apply previous configuration
kubectl apply -f k8s/$ENVIRONMENT/ --namespace=sunday-$ENVIRONMENT

echo "✅ Kubernetes configuration rollback completed"
```

### 2. Network Policy Rollback

```bash
#!/bin/bash
# scripts/network-rollback.sh

ENVIRONMENT=${1:-staging}
NAMESPACE="sunday-$ENVIRONMENT"

echo "🌐 Rolling back network policies for $ENVIRONMENT"

# Remove current network policies
kubectl delete networkpolicy --all -n $NAMESPACE

# Apply backup network policies
kubectl apply -f k8s/backup/network-policies/ -n $NAMESPACE

echo "✅ Network policy rollback completed"
```

### 3. Service Mesh Rollback

```bash
#!/bin/bash
# scripts/service-mesh-rollback.sh

ENVIRONMENT=${1:-staging}

echo "🕸️ Rolling back service mesh configuration for $ENVIRONMENT"

# Rollback Istio virtual services
kubectl rollout undo deployment/istio-proxy -n istio-system

# Reset traffic routing
kubectl apply -f k8s/service-mesh/backup/ -n sunday-$ENVIRONMENT

echo "✅ Service mesh rollback completed"
```

---

## Verification and Validation

### 1. Rollback Verification Script

```bash
#!/bin/bash
# scripts/verify-rollback.sh

ENVIRONMENT=${1:-staging}
BASE_URL="https://${ENVIRONMENT}.sunday.com"

if [ "$ENVIRONMENT" = "production" ]; then
  BASE_URL="https://sunday.com"
fi

echo "🔍 Verifying rollback for $ENVIRONMENT..."

# Check application version
BACKEND_VERSION=$(kubectl get deployment backend-deployment -n sunday-$ENVIRONMENT \
  -o jsonpath='{.spec.template.spec.containers[0].image}' | cut -d':' -f2)
echo "Backend version: $BACKEND_VERSION"

# Health checks
echo "🏥 Running health checks..."
curl -f "$BASE_URL/api/health" || exit 1
curl -f "$BASE_URL/api/health/database" || exit 1
curl -f "$BASE_URL/api/health/redis" || exit 1

# Functional tests
echo "🧪 Running functional tests..."
./scripts/smoke-tests.sh $ENVIRONMENT

# Performance baseline check
echo "⚡ Checking performance baseline..."
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" "$BASE_URL/api/health")
if (( $(echo "$RESPONSE_TIME > 2.0" | bc -l) )); then
  echo "⚠️ Warning: Response time slower than expected: ${RESPONSE_TIME}s"
fi

# Check error rates
echo "📊 Checking error rates..."
ERROR_RATE=$(curl -s "$BASE_URL/api/metrics/errors" | jq -r '.rate')
if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
  echo "⚠️ Warning: Error rate higher than expected: ${ERROR_RATE}%"
fi

echo "✅ Rollback verification completed successfully"
```

### 2. Database Integrity Check

```bash
#!/bin/bash
# scripts/verify-database-integrity.sh

ENVIRONMENT=${1:-staging}

echo "🗃️ Verifying database integrity for $ENVIRONMENT..."

# Run database consistency checks
kubectl exec -it deployment/backend-deployment -n sunday-$ENVIRONMENT -- \
  node scripts/database-integrity-check.js

# Check foreign key constraints
kubectl exec -it deployment/backend-deployment -n sunday-$ENVIRONMENT -- \
  psql $DATABASE_URL -c "
    SELECT conname, conrelid::regclass
    FROM pg_constraint
    WHERE contype = 'f' AND NOT pg_constraint_check(oid);"

# Verify critical data counts
kubectl exec -it deployment/backend-deployment -n sunday-$ENVIRONMENT -- \
  node scripts/verify-data-counts.js

echo "✅ Database integrity verification completed"
```

---

## Post-Rollback Actions

### 1. Incident Documentation

```bash
#!/bin/bash
# scripts/document-rollback.sh

INCIDENT_ID=${1}
ROLLBACK_REASON=${2}
ENVIRONMENT=${3:-production}

if [ -z "$INCIDENT_ID" ] || [ -z "$ROLLBACK_REASON" ]; then
  echo "Usage: $0 <incident-id> <rollback-reason> [environment]"
  exit 1
fi

echo "📝 Documenting rollback incident: $INCIDENT_ID"

# Create incident report
cat > "incidents/rollback-$INCIDENT_ID.md" << EOF
# Rollback Incident Report

**Incident ID**: $INCIDENT_ID
**Date**: $(date)
**Environment**: $ENVIRONMENT
**Rollback Reason**: $ROLLBACK_REASON

## Timeline
- **Detection**: $(date)
- **Decision**: $(date)
- **Rollback Start**: $(date)
- **Rollback Complete**: $(date)
- **Verification**: $(date)

## Impact
- **Affected Users**: TBD
- **Downtime**: TBD
- **Data Loss**: None

## Root Cause
TBD - Investigation in progress

## Action Items
- [ ] Root cause analysis
- [ ] Process improvements
- [ ] Preventive measures

## Lessons Learned
TBD
EOF

echo "✅ Incident documentation created: incidents/rollback-$INCIDENT_ID.md"
```

### 2. Stakeholder Communication

```bash
#!/bin/bash
# scripts/notify-rollback.sh

ENVIRONMENT=${1:-production}
ROLLBACK_REASON=${2:-"Critical issue detected"}

echo "📢 Notifying stakeholders of rollback..."

# Slack notification
curl -X POST -H 'Content-type: application/json' \
  --data "{
    \"text\":\"🔄 Rollback completed for $ENVIRONMENT\",
    \"attachments\":[{
      \"color\":\"warning\",
      \"fields\":[{
        \"title\":\"Environment\",
        \"value\":\"$ENVIRONMENT\",
        \"short\":true
      },{
        \"title\":\"Reason\",
        \"value\":\"$ROLLBACK_REASON\",
        \"short\":true
      },{
        \"title\":\"Status\",
        \"value\":\"System restored and operational\",
        \"short\":false
      }]
    }]
  }" \
  $SLACK_WEBHOOK_URL

# Status page update
curl -X POST \
  -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.statuspage.io/v1/pages/$STATUS_PAGE_ID/incidents \
  -d "{
    \"incident\": {
      \"name\": \"System Rollback - $ENVIRONMENT\",
      \"status\": \"resolved\",
      \"impact_override\": \"minor\",
      \"body\": \"We have successfully rolled back a recent deployment due to: $ROLLBACK_REASON. All systems are now operational.\"
    }
  }"

echo "✅ Stakeholder notifications sent"
```

### 3. Monitoring Reset

```bash
#!/bin/bash
# scripts/reset-monitoring.sh

ENVIRONMENT=${1:-staging}

echo "📊 Resetting monitoring baselines for $ENVIRONMENT..."

# Reset Grafana alerts
curl -X POST \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  https://grafana.sunday.com/api/annotations \
  -d "{
    \"text\": \"Rollback completed - monitoring baseline reset\",
    \"time\": $(date +%s)000,
    \"tags\": [\"rollback\", \"$ENVIRONMENT\"]
  }"

# Clear accumulated metrics
kubectl delete pod -l app=prometheus-node-exporter -n monitoring

# Restart monitoring services
kubectl rollout restart deployment/prometheus -n monitoring
kubectl rollout restart deployment/grafana -n monitoring

echo "✅ Monitoring reset completed"
```

---

## Emergency Procedures

### 1. Complete System Shutdown

For catastrophic failures requiring immediate shutdown:

```bash
#!/bin/bash
# scripts/emergency-shutdown.sh

ENVIRONMENT=${1:-production}
REASON=${2:-"Emergency shutdown"}

echo "🚨 EMERGENCY SHUTDOWN INITIATED"
echo "Environment: $ENVIRONMENT"
echo "Reason: $REASON"
echo "Time: $(date)"

# Enable global maintenance mode
kubectl patch configmap app-config -n sunday-$ENVIRONMENT \
  -p '{"data":{"maintenance_mode":"true","maintenance_message":"System temporarily unavailable due to emergency maintenance"}}'

# Scale down all services
kubectl scale deployment --all --replicas=0 -n sunday-$ENVIRONMENT

# Update status page
curl -X POST \
  -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
  https://api.statuspage.io/v1/pages/$STATUS_PAGE_ID/incidents \
  -d "{
    \"incident\": {
      \"name\": \"Emergency Maintenance\",
      \"status\": \"investigating\",
      \"impact_override\": \"major\",
      \"body\": \"We are currently experiencing technical difficulties and have temporarily taken the system offline for emergency maintenance.\"
    }
  }"

echo "🚨 EMERGENCY SHUTDOWN COMPLETED"
```

### 2. Data Corruption Recovery

For severe data corruption issues:

```bash
#!/bin/bash
# scripts/data-corruption-recovery.sh

ENVIRONMENT=${1:-staging}
BACKUP_TIME=${2}

echo "🔥 Data corruption recovery for $ENVIRONMENT"

if [ -z "$BACKUP_TIME" ]; then
  echo "Available backups:"
  aws rds describe-db-snapshots \
    --db-cluster-identifier sunday-$ENVIRONMENT \
    --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
    --output table
  exit 1
fi

# Immediate system shutdown
./scripts/emergency-shutdown.sh $ENVIRONMENT "Data corruption detected"

# Create forensic snapshot of corrupted database
aws rds create-db-snapshot \
  --db-cluster-identifier sunday-$ENVIRONMENT \
  --db-snapshot-identifier sunday-$ENVIRONMENT-corrupted-$(date +%s)

# Restore from clean backup
./scripts/database-snapshot-restore.sh $BACKUP_TIME $ENVIRONMENT

echo "🔥 Data corruption recovery initiated"
echo "Manual intervention required to complete recovery"
```

### 3. Security Breach Response

For security incidents requiring immediate isolation:

```bash
#!/bin/bash
# scripts/security-breach-response.sh

ENVIRONMENT=${1:-production}
BREACH_TYPE=${2:-"Unknown"}

echo "🛡️ SECURITY BREACH RESPONSE"
echo "Environment: $ENVIRONMENT"
echo "Breach Type: $BREACH_TYPE"

# Immediate isolation
kubectl patch networkpolicy deny-all -n sunday-$ENVIRONMENT \
  -p '{"spec":{"podSelector":{},"policyTypes":["Ingress","Egress"]}}'

# Revoke all API tokens
kubectl delete secret --all -l type=api-token -n sunday-$ENVIRONMENT

# Enable audit logging
kubectl patch configmap app-config -n sunday-$ENVIRONMENT \
  -p '{"data":{"audit_level":"debug","security_mode":"lockdown"}}'

# Notify security team
curl -X POST -H 'Content-type: application/json' \
  --data "{
    \"text\":\"🚨 SECURITY BREACH DETECTED\",
    \"channel\":\"#security-alerts\",
    \"attachments\":[{
      \"color\":\"danger\",
      \"fields\":[{
        \"title\":\"Environment\",
        \"value\":\"$ENVIRONMENT\"
      },{
        \"title\":\"Breach Type\",
        \"value\":\"$BREACH_TYPE\"
      },{
        \"title\":\"Action\",
        \"value\":\"System isolated - manual investigation required\"
      }]
    }]
  }" \
  $SECURITY_SLACK_WEBHOOK

echo "🛡️ SECURITY BREACH RESPONSE COMPLETED"
echo "System isolated - security team notified"
```

---

## Rollback Testing

### 1. Regular Rollback Drills

```bash
#!/bin/bash
# scripts/rollback-drill.sh

ENVIRONMENT="staging"
DRILL_ID="drill-$(date +%s)"

echo "🎯 Rollback drill: $DRILL_ID"

# Deploy a test version
kubectl set image deployment/backend-deployment \
  backend=ghcr.io/sunday/backend:test-rollback \
  -n sunday-$ENVIRONMENT

# Wait for deployment
kubectl rollout status deployment/backend-deployment -n sunday-$ENVIRONMENT

# Simulate issue detection
sleep 60

# Execute rollback
./scripts/emergency-rollback.sh $ENVIRONMENT

# Verify rollback success
./scripts/verify-rollback.sh $ENVIRONMENT

echo "✅ Rollback drill completed: $DRILL_ID"
```

### 2. Chaos Engineering

```yaml
# chaos/rollback-chaos.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: rollback-test
spec:
  action: pod-failure
  mode: one
  selector:
    namespaces:
      - sunday-staging
    labelSelectors:
      app: backend
  scheduler:
    cron: "0 2 * * 1"  # Every Monday at 2 AM
```

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Emergency Contact: devops-oncall@sunday.com*