# Sunday.com Blue-Green Deployment Automation

## Table of Contents

1. [Overview](#overview)
2. [Blue-Green Architecture](#blue-green-architecture)
3. [Automated Deployment Pipeline](#automated-deployment-pipeline)
4. [Traffic Management](#traffic-management)
5. [Health Checks and Validation](#health-checks-and-validation)
6. [Rollback Procedures](#rollback-procedures)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Implementation Scripts](#implementation-scripts)

---

## Overview

Blue-Green deployment is Sunday.com's primary zero-downtime deployment strategy for production environments. This automation framework ensures safe, reliable deployments with instant rollback capabilities while maintaining continuous service availability.

### Blue-Green Benefits

- **Zero Downtime**: Instant traffic switching between environments
- **Instant Rollback**: Immediate reversion to previous version if issues arise
- **Safe Testing**: Production-like environment for final validation
- **Reduced Risk**: Complete environment isolation during deployment
- **Data Integrity**: No impact on live user sessions or data

### Architecture Principles

- **Environment Isolation**: Complete separation between blue and green environments
- **Automated Validation**: Comprehensive health checks before traffic switching
- **Traffic Orchestration**: Intelligent load balancer management
- **State Management**: Consistent environment state tracking
- **Observability**: Full visibility into deployment process

---

## Blue-Green Architecture

### Infrastructure Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    Blue-Green Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                     Load Balancer (ALB)                        │
│                           │                                     │
│           ┌───────────────┼───────────────┐                     │
│           │               │               │                     │
│    ┌─────────────┐        │        ┌─────────────┐             │
│    │    BLUE     │◄───────┼───────►│    GREEN    │             │
│    │ Environment │        │        │ Environment │             │
│    └─────────────┘        │        └─────────────┘             │
│           │               │               │                     │
│    ┌─────────────┐        │        ┌─────────────┐             │
│    │   Backend   │        │        │   Backend   │             │
│    │   Services  │        │        │   Services  │             │
│    └─────────────┘        │        └─────────────┘             │
│           │               │               │                     │
│    ┌─────────────┐        │        ┌─────────────┐             │
│    │  Frontend   │        │        │  Frontend   │             │
│    │   Services  │        │        │   Services  │             │
│    └─────────────┘        │        └─────────────┘             │
│                           │                                     │
│           Shared Database & Storage Layer                       │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │  PostgreSQL  │  Redis  │  Elasticsearch  │  S3 Storage │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Kubernetes Deployment Structure

```yaml
# k8s/blue-green/blue-green-setup.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sunday-blue
---
apiVersion: v1
kind: Namespace
metadata:
  name: sunday-green
---
# Blue Environment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
  namespace: sunday-blue
  labels:
    app: backend
    version: blue
    environment: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: blue
  template:
    metadata:
      labels:
        app: backend
        version: blue
        environment: production
    spec:
      containers:
      - name: backend
        image: ghcr.io/sunday/backend:latest
        ports:
        - containerPort: 3000
        env:
        - name: ENVIRONMENT_COLOR
          value: "blue"
        - name: NODE_ENV
          value: "production"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# Green Environment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
  namespace: sunday-green
  labels:
    app: backend
    version: green
    environment: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: green
  template:
    metadata:
      labels:
        app: backend
        version: green
        environment: production
    spec:
      containers:
      - name: backend
        image: ghcr.io/sunday/backend:latest
        ports:
        - containerPort: 3000
        env:
        - name: ENVIRONMENT_COLOR
          value: "green"
        - name: NODE_ENV
          value: "production"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# Traffic Management Service
apiVersion: v1
kind: Service
metadata:
  name: backend-service-active
  namespace: sunday-production
  labels:
    app: backend
    role: active
spec:
  selector:
    app: backend
    version: blue  # Initially points to blue
  ports:
  - port: 80
    targetPort: 3000
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service-inactive
  namespace: sunday-production
  labels:
    app: backend
    role: inactive
spec:
  selector:
    app: backend
    version: green  # Initially points to green
  ports:
  - port: 80
    targetPort: 3000
    name: http
  type: ClusterIP
```

---

## Automated Deployment Pipeline

### Main Blue-Green Deployment Script

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh

set -e

# Configuration
DEPLOYMENT_ID=${1}
NEW_VERSION=${2}
DEPLOYMENT_CONFIG=${3:-"deployment-config.json"}

if [ -z "$DEPLOYMENT_ID" ] || [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <deployment-id> <new-version> [config-file]"
    exit 1
fi

# Load configuration
source "deployment-plans/${DEPLOYMENT_ID}/config.sh"

# Logging setup
LOG_FILE="deployment-plans/${DEPLOYMENT_ID}/deployment.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo "🚀 Starting Blue-Green Deployment: $DEPLOYMENT_ID"
echo "Version: $NEW_VERSION"
echo "Timestamp: $(date)"

# Initialize deployment tracking
DEPLOYMENT_STATE_FILE="deployment-plans/${DEPLOYMENT_ID}/state.json"
create_deployment_state() {
    cat > "$DEPLOYMENT_STATE_FILE" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "version": "$NEW_VERSION",
  "start_time": "$(date -Iseconds)",
  "current_phase": "initialization",
  "active_environment": "$(get_active_environment)",
  "target_environment": "$(get_inactive_environment)",
  "status": "in_progress",
  "rollback_available": false
}
EOF
}

update_deployment_state() {
    local phase=$1
    local status=$2
    jq --arg phase "$phase" --arg status "$status" --arg time "$(date -Iseconds)" \
        '.current_phase = $phase | .status = $status | .last_update = $time' \
        "$DEPLOYMENT_STATE_FILE" > "${DEPLOYMENT_STATE_FILE}.tmp" && \
        mv "${DEPLOYMENT_STATE_FILE}.tmp" "$DEPLOYMENT_STATE_FILE"
}

# Utility functions
get_active_environment() {
    kubectl get service backend-service-active -n sunday-production \
        -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "blue"
}

get_inactive_environment() {
    local active=$(get_active_environment)
    if [ "$active" = "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

wait_for_deployment_ready() {
    local namespace=$1
    local max_wait=${2:-600}  # 10 minutes default
    local start_time=$(date +%s)

    echo "⏳ Waiting for deployment to be ready in $namespace..."

    while true; do
        if kubectl rollout status deployment/backend-deployment -n "$namespace" --timeout=60s >/dev/null 2>&1; then
            echo "✅ Deployment ready in $namespace"
            return 0
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -gt $max_wait ]; then
            echo "❌ Timeout waiting for deployment in $namespace"
            return 1
        fi

        echo "⏳ Still waiting... (${elapsed}s elapsed)"
        sleep 30
    done
}

# Phase 1: Pre-deployment validation
echo "📋 Phase 1: Pre-deployment validation"
update_deployment_state "pre_validation" "running"

# Check current system health
if ! ./scripts/pre-deployment-validation.sh "$DEPLOYMENT_ID" "production" "blue_green"; then
    echo "❌ Pre-deployment validation failed"
    update_deployment_state "pre_validation" "failed"
    exit 1
fi

echo "✅ Pre-deployment validation passed"
update_deployment_state "pre_validation" "completed"

# Phase 2: Prepare inactive environment
ACTIVE_ENV=$(get_active_environment)
INACTIVE_ENV=$(get_inactive_environment)

echo "📦 Phase 2: Preparing $INACTIVE_ENV environment"
echo "Active environment: $ACTIVE_ENV"
echo "Target environment: $INACTIVE_ENV"

update_deployment_state "environment_preparation" "running"
create_deployment_state

# Update inactive environment with new version
echo "🔄 Deploying version $NEW_VERSION to $INACTIVE_ENV environment..."

kubectl set image deployment/backend-deployment \
    backend=ghcr.io/sunday/backend:$NEW_VERSION \
    -n sunday-$INACTIVE_ENV

kubectl set image deployment/frontend-deployment \
    frontend=ghcr.io/sunday/frontend:$NEW_VERSION \
    -n sunday-$INACTIVE_ENV

# Wait for rollout to complete
if ! wait_for_deployment_ready "sunday-$INACTIVE_ENV"; then
    echo "❌ Failed to deploy to $INACTIVE_ENV environment"
    update_deployment_state "environment_preparation" "failed"
    exit 1
fi

echo "✅ $INACTIVE_ENV environment ready with version $NEW_VERSION"
update_deployment_state "environment_preparation" "completed"

# Phase 3: Health checks and validation
echo "🏥 Phase 3: Health checks and validation"
update_deployment_state "health_validation" "running"

# Run comprehensive health checks on inactive environment
if ! ./scripts/blue-green-health-check.sh "$INACTIVE_ENV" "$NEW_VERSION"; then
    echo "❌ Health checks failed for $INACTIVE_ENV environment"
    update_deployment_state "health_validation" "failed"
    echo "🔄 Rolling back $INACTIVE_ENV environment..."
    kubectl rollout undo deployment/backend-deployment -n sunday-$INACTIVE_ENV
    kubectl rollout undo deployment/frontend-deployment -n sunday-$INACTIVE_ENV
    exit 1
fi

echo "✅ Health checks passed for $INACTIVE_ENV environment"
update_deployment_state "health_validation" "completed"

# Phase 4: Traffic switching
echo "🔀 Phase 4: Traffic switching"
update_deployment_state "traffic_switching" "running"

# Create backup of current service configuration
kubectl get service backend-service-active -n sunday-production -o yaml > \
    "deployment-plans/${DEPLOYMENT_ID}/active-service-backup.yaml"

kubectl get service backend-service-inactive -n sunday-production -o yaml > \
    "deployment-plans/${DEPLOYMENT_ID}/inactive-service-backup.yaml"

# Switch traffic to inactive environment (making it active)
echo "🚦 Switching traffic from $ACTIVE_ENV to $INACTIVE_ENV..."

# Update service selectors
kubectl patch service backend-service-active -n sunday-production \
    -p "{\"spec\":{\"selector\":{\"version\":\"$INACTIVE_ENV\"}}}"

kubectl patch service frontend-service-active -n sunday-production \
    -p "{\"spec\":{\"selector\":{\"version\":\"$INACTIVE_ENV\"}}}"

# Update inactive service to point to old active environment
kubectl patch service backend-service-inactive -n sunday-production \
    -p "{\"spec\":{\"selector\":{\"version\":\"$ACTIVE_ENV\"}}}"

kubectl patch service frontend-service-inactive -n sunday-production \
    -p "{\"spec\":{\"selector\":{\"version\":\"$ACTIVE_ENV\"}}}"

# Brief wait for traffic to stabilize
sleep 30

echo "✅ Traffic switched to $INACTIVE_ENV environment"
update_deployment_state "traffic_switching" "completed"

# Update state to reflect new active environment
jq --arg active "$INACTIVE_ENV" --arg inactive "$ACTIVE_ENV" \
    '.active_environment = $active | .previous_environment = $inactive | .rollback_available = true' \
    "$DEPLOYMENT_STATE_FILE" > "${DEPLOYMENT_STATE_FILE}.tmp" && \
    mv "${DEPLOYMENT_STATE_FILE}.tmp" "$DEPLOYMENT_STATE_FILE"

# Phase 5: Post-deployment validation
echo "🔍 Phase 5: Post-deployment validation"
update_deployment_state "post_validation" "running"

# Monitor for issues for specified duration
MONITORING_DURATION=${MONITORING_DURATION:-300}  # 5 minutes default
echo "📊 Monitoring deployment for $MONITORING_DURATION seconds..."

if ! ./scripts/post-deployment-monitoring.sh "$NEW_VERSION" "$MONITORING_DURATION"; then
    echo "❌ Post-deployment monitoring detected issues"
    echo "🔄 Initiating automatic rollback..."

    if ./scripts/blue-green-rollback.sh "$DEPLOYMENT_ID" "automatic"; then
        echo "✅ Automatic rollback completed successfully"
        update_deployment_state "post_validation" "failed_rolled_back"
    else
        echo "❌ Automatic rollback failed - manual intervention required"
        update_deployment_state "post_validation" "failed_rollback_failed"
    fi
    exit 1
fi

echo "✅ Post-deployment monitoring passed"
update_deployment_state "post_validation" "completed"

# Phase 6: Cleanup and finalization
echo "🧹 Phase 6: Cleanup and finalization"
update_deployment_state "cleanup" "running"

# Optional: Scale down old environment to save resources
if [ "${SCALE_DOWN_OLD_ENV:-true}" = "true" ]; then
    echo "📉 Scaling down old $ACTIVE_ENV environment..."
    kubectl scale deployment backend-deployment --replicas=1 -n sunday-$ACTIVE_ENV
    kubectl scale deployment frontend-deployment --replicas=1 -n sunday-$ACTIVE_ENV
fi

# Update deployment tracking
jq --arg status "completed" --arg end_time "$(date -Iseconds)" \
    '.status = $status | .end_time = $end_time | .current_phase = "completed"' \
    "$DEPLOYMENT_STATE_FILE" > "${DEPLOYMENT_STATE_FILE}.tmp" && \
    mv "${DEPLOYMENT_STATE_FILE}.tmp" "$DEPLOYMENT_STATE_FILE"

# Send notifications
./scripts/send-deployment-notification.sh "$DEPLOYMENT_ID" "success" \
    "Blue-Green deployment completed successfully. Version $NEW_VERSION is now live."

echo "🎉 Blue-Green deployment completed successfully!"
echo "🔄 Active environment: $INACTIVE_ENV (version $NEW_VERSION)"
echo "💾 Rollback environment: $ACTIVE_ENV (previous version)"
echo "📊 Deployment duration: $(($(date +%s) - $(date -d "$(jq -r '.start_time' "$DEPLOYMENT_STATE_FILE")" +%s))) seconds"

update_deployment_state "cleanup" "completed"

echo "✅ Deployment $DEPLOYMENT_ID completed at $(date)"
```

### Blue-Green Health Check Script

```bash
#!/bin/bash
# scripts/blue-green-health-check.sh

ENVIRONMENT=${1}
VERSION=${2}
TIMEOUT=${3:-300}

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <environment> <version> [timeout]"
    exit 1
fi

echo "🏥 Running health checks for $ENVIRONMENT environment (version $VERSION)"

NAMESPACE="sunday-$ENVIRONMENT"
BASE_URL="https://${ENVIRONMENT}.sunday.com"
CHECK_COUNT=0
PASSED_CHECKS=0

run_check() {
    local check_name=$1
    local check_command=$2
    local expected_result=${3:-0}

    ((CHECK_COUNT++))
    echo "🔍 Running: $check_name"

    if eval "$check_command"; then
        if [ $? -eq $expected_result ]; then
            echo "✅ $check_name: PASSED"
            ((PASSED_CHECKS++))
            return 0
        fi
    fi

    echo "❌ $check_name: FAILED"
    return 1
}

# Basic service health checks
run_check "Pod readiness" \
    "kubectl get pods -n $NAMESPACE --no-headers | grep -v Running | wc -l | grep -q '^0$'"

run_check "Service endpoints" \
    "kubectl get endpoints -n $NAMESPACE backend-service -o jsonpath='{.subsets[0].addresses[0].ip}' | grep -q '.'"

# Application health checks
run_check "Backend health endpoint" \
    "curl -f -s --max-time 10 $BASE_URL/api/health"

run_check "Frontend accessibility" \
    "curl -f -s --max-time 10 $BASE_URL/ | grep -q 'Sunday.com'"

run_check "API authentication" \
    "curl -f -s --max-time 10 $BASE_URL/api/auth/status | jq -e '.status == \"ok\"'"

# Database connectivity
run_check "Database connectivity" \
    "kubectl exec -n $NAMESPACE deployment/backend-deployment -- node -e 'require(\"./src/config/database\").testConnection()'"

# Performance benchmarks
run_check "API response time" \
    "curl -o /dev/null -s -w '%{time_total}' $BASE_URL/api/health | awk '{exit \$1 > 1 ? 1 : 0}'"

# Integration checks
run_check "Redis connectivity" \
    "kubectl exec -n $NAMESPACE deployment/backend-deployment -- redis-cli -h redis ping | grep -q 'PONG'"

run_check "Search service" \
    "curl -f -s --max-time 10 $BASE_URL/api/search/health"

# Load testing
run_check "Basic load test" \
    "ab -n 100 -c 10 -t 30 $BASE_URL/api/health | grep -q 'Complete requests.*100'"

# Calculate success rate
SUCCESS_RATE=$((PASSED_CHECKS * 100 / CHECK_COUNT))

echo ""
echo "📊 Health Check Summary:"
echo "  Total checks: $CHECK_COUNT"
echo "  Passed: $PASSED_CHECKS"
echo "  Success rate: $SUCCESS_RATE%"

if [ $SUCCESS_RATE -ge 90 ]; then
    echo "✅ Health checks PASSED ($SUCCESS_RATE% success rate)"
    exit 0
else
    echo "❌ Health checks FAILED ($SUCCESS_RATE% success rate)"
    exit 1
fi
```

---

## Traffic Management

### Intelligent Traffic Switching

```bash
#!/bin/bash
# scripts/intelligent-traffic-switch.sh

DEPLOYMENT_ID=${1}
STRATEGY=${2:-"instant"}  # instant, gradual, canary

echo "🚦 Starting intelligent traffic switch for deployment: $DEPLOYMENT_ID"
echo "Strategy: $STRATEGY"

case $STRATEGY in
    "instant")
        perform_instant_switch
        ;;
    "gradual")
        perform_gradual_switch
        ;;
    "canary")
        perform_canary_switch
        ;;
    *)
        echo "Unknown strategy: $STRATEGY"
        exit 1
        ;;
esac

perform_instant_switch() {
    echo "⚡ Performing instant traffic switch..."

    ACTIVE_ENV=$(get_active_environment)
    INACTIVE_ENV=$(get_inactive_environment)

    # Switch 100% of traffic instantly
    kubectl patch service backend-service-active -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$INACTIVE_ENV\"}}}"

    echo "✅ Instant switch completed: 100% traffic to $INACTIVE_ENV"
}

perform_gradual_switch() {
    echo "📈 Performing gradual traffic switch..."

    # Implement weighted routing using ingress controller
    local phases=(10 25 50 75 100)

    for phase in "${phases[@]}"; do
        echo "🔄 Switching ${phase}% of traffic..."

        # Update ingress weights
        kubectl annotate ingress sunday-ingress -n sunday-production \
            nginx.ingress.kubernetes.io/canary-weight="$phase" --overwrite

        # Monitor for 2 minutes
        sleep 120

        # Check health metrics
        if ! check_traffic_health "$phase"; then
            echo "❌ Health check failed at ${phase}% traffic"
            rollback_traffic_switch
            return 1
        fi

        echo "✅ ${phase}% traffic switch successful"
    done

    echo "✅ Gradual switch completed: 100% traffic switched"
}

perform_canary_switch() {
    echo "🐦 Performing canary traffic switch..."

    # Start with 5% canary traffic
    local canary_weights=(5 10 25 50 100)

    for weight in "${canary_weights[@]}"; do
        echo "🔄 Setting canary weight to ${weight}%..."

        # Update canary ingress
        kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sunday-canary
  namespace: sunday-production
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "$weight"
spec:
  rules:
  - host: sunday.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service-inactive
            port:
              number: 80
EOF

        # Monitor canary metrics
        monitor_canary_metrics "$weight"

        if [ $? -ne 0 ]; then
            echo "❌ Canary metrics failed at ${weight}%"
            rollback_canary_switch
            return 1
        fi
    done

    # Remove canary and switch main traffic
    kubectl delete ingress sunday-canary -n sunday-production
    perform_instant_switch

    echo "✅ Canary switch completed successfully"
}

check_traffic_health() {
    local traffic_percentage=$1

    # Check error rates
    local error_rate=$(get_current_error_rate)
    if [ "${error_rate%.*}" -gt 5 ]; then
        echo "❌ High error rate detected: ${error_rate}%"
        return 1
    fi

    # Check response times
    local response_time=$(get_average_response_time)
    if [ "${response_time%.*}" -gt 2000 ]; then
        echo "❌ High response time detected: ${response_time}ms"
        return 1
    fi

    echo "✅ Traffic health check passed (${traffic_percentage}%)"
    return 0
}

monitor_canary_metrics() {
    local weight=$1
    local duration=180  # 3 minutes

    echo "📊 Monitoring canary metrics for ${duration}s at ${weight}% weight..."

    local start_time=$(date +%s)
    while [ $(($(date +%s) - start_time)) -lt $duration ]; do
        # Check canary error rate vs main traffic
        local canary_errors=$(get_canary_error_rate)
        local main_errors=$(get_main_error_rate)

        if [ "${canary_errors%.*}" -gt $((${main_errors%.*} * 2)) ]; then
            echo "❌ Canary error rate too high: ${canary_errors}% vs ${main_errors}%"
            return 1
        fi

        sleep 30
    done

    echo "✅ Canary monitoring passed"
    return 0
}

rollback_traffic_switch() {
    echo "🔄 Rolling back traffic switch..."

    # Restore original traffic routing
    kubectl apply -f "deployment-plans/${DEPLOYMENT_ID}/active-service-backup.yaml"
    kubectl apply -f "deployment-plans/${DEPLOYMENT_ID}/inactive-service-backup.yaml"

    echo "✅ Traffic rollback completed"
}
```

---

## Health Checks and Validation

### Comprehensive Validation Framework

```python
#!/usr/bin/env python3
# scripts/blue-green-validator.py

import requests
import json
import time
import subprocess
import sys
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

class BlueGreenValidator:
    def __init__(self, environment: str, version: str):
        self.environment = environment
        self.version = version
        self.base_url = f"https://{environment}.sunday.com"
        self.namespace = f"sunday-{environment}"
        self.validation_results = []

    def run_validation_suite(self) -> bool:
        """Run complete validation suite for blue-green deployment"""

        print(f"🔍 Starting validation suite for {self.environment} environment")
        print(f"Version: {self.version}")
        print(f"Base URL: {self.base_url}")

        validation_groups = [
            ("Infrastructure", self.validate_infrastructure),
            ("Application Health", self.validate_application_health),
            ("API Functionality", self.validate_api_functionality),
            ("Database Operations", self.validate_database_operations),
            ("Performance", self.validate_performance),
            ("Security", self.validate_security),
            ("Integration", self.validate_integrations)
        ]

        overall_success = True

        for group_name, validation_func in validation_groups:
            print(f"\n📋 Running {group_name} validations...")

            try:
                success = validation_func()
                if success:
                    print(f"✅ {group_name}: PASSED")
                else:
                    print(f"❌ {group_name}: FAILED")
                    overall_success = False
            except Exception as e:
                print(f"❌ {group_name}: ERROR - {str(e)}")
                overall_success = False

        self.generate_validation_report()

        return overall_success

    def validate_infrastructure(self) -> bool:
        """Validate infrastructure readiness"""
        checks = [
            ("Pod Status", self.check_pod_status),
            ("Service Endpoints", self.check_service_endpoints),
            ("Resource Usage", self.check_resource_usage),
            ("Network Connectivity", self.check_network_connectivity)
        ]

        return self.run_check_group(checks)

    def validate_application_health(self) -> bool:
        """Validate application health and readiness"""
        checks = [
            ("Health Endpoint", self.check_health_endpoint),
            ("Readiness Endpoint", self.check_readiness_endpoint),
            ("Version Endpoint", self.check_version_endpoint),
            ("Dependency Status", self.check_dependency_status)
        ]

        return self.run_check_group(checks)

    def validate_api_functionality(self) -> bool:
        """Validate core API functionality"""
        checks = [
            ("Authentication", self.check_authentication),
            ("User Operations", self.check_user_operations),
            ("Workspace Operations", self.check_workspace_operations),
            ("Task Operations", self.check_task_operations),
            ("Real-time Features", self.check_realtime_features)
        ]

        return self.run_check_group(checks)

    def validate_database_operations(self) -> bool:
        """Validate database connectivity and operations"""
        checks = [
            ("Database Connection", self.check_database_connection),
            ("Read Operations", self.check_database_reads),
            ("Write Operations", self.check_database_writes),
            ("Transaction Integrity", self.check_transaction_integrity)
        ]

        return self.run_check_group(checks)

    def validate_performance(self) -> bool:
        """Validate performance benchmarks"""
        checks = [
            ("Response Times", self.check_response_times),
            ("Throughput", self.check_throughput),
            ("Resource Efficiency", self.check_resource_efficiency),
            ("Load Handling", self.check_load_handling)
        ]

        return self.run_check_group(checks)

    def validate_security(self) -> bool:
        """Validate security configurations"""
        checks = [
            ("TLS Configuration", self.check_tls_config),
            ("Authentication Security", self.check_auth_security),
            ("Authorization Checks", self.check_authorization),
            ("Input Validation", self.check_input_validation)
        ]

        return self.run_check_group(checks)

    def validate_integrations(self) -> bool:
        """Validate external integrations"""
        checks = [
            ("Third-party APIs", self.check_third_party_apis),
            ("Webhook Delivery", self.check_webhook_delivery),
            ("Email Services", self.check_email_services),
            ("File Storage", self.check_file_storage)
        ]

        return self.run_check_group(checks)

    def run_check_group(self, checks: List[Tuple[str, callable]]) -> bool:
        """Run a group of validation checks"""
        results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_check = {
                executor.submit(check_func): check_name
                for check_name, check_func in checks
            }

            for future in as_completed(future_to_check):
                check_name = future_to_check[future]
                try:
                    result = future.result(timeout=30)
                    results.append((check_name, result))
                    status = "✅" if result else "❌"
                    print(f"  {status} {check_name}")
                except Exception as e:
                    results.append((check_name, False))
                    print(f"  ❌ {check_name}: {str(e)}")

        return all(result for _, result in results)

    # Individual check implementations
    def check_pod_status(self) -> bool:
        """Check if all pods are running and ready"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pods', '-n', self.namespace,
                '--no-headers'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return False

            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line:
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] != 'Running':
                        return False

            return True
        except Exception:
            return False

    def check_health_endpoint(self) -> bool:
        """Check application health endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def check_readiness_endpoint(self) -> bool:
        """Check application readiness endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/api/ready",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def check_version_endpoint(self) -> bool:
        """Check version endpoint returns expected version"""
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('version') == self.version
            return False
        except Exception:
            return False

    def check_authentication(self) -> bool:
        """Test authentication flow"""
        try:
            # Test login endpoint
            response = requests.post(
                f"{self.base_url}/api/auth/test-login",
                json={"test": True},
                timeout=10
            )
            return response.status_code in [200, 401]  # Either works or properly rejects
        except Exception:
            return False

    def check_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', self.namespace,
                'deployment/backend-deployment', '--',
                'node', '-e', 'require("./src/config/database").testConnection()'
            ], capture_output=True, timeout=15)

            return result.returncode == 0
        except Exception:
            return False

    def check_response_times(self) -> bool:
        """Check API response times meet requirements"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            response_time = (time.time() - start_time) * 1000

            return response.status_code == 200 and response_time < 500  # 500ms threshold
        except Exception:
            return False

    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        report = {
            "environment": self.environment,
            "version": self.version,
            "timestamp": time.time(),
            "results": self.validation_results
        }

        with open(f"validation-report-{self.environment}-{self.version}.json", 'w') as f:
            json.dump(report, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python blue-green-validator.py <environment> <version>")
        sys.exit(1)

    environment = sys.argv[1]
    version = sys.argv[2]

    validator = BlueGreenValidator(environment, version)
    success = validator.run_validation_suite()

    if success:
        print(f"\n✅ All validations passed for {environment} environment")
        sys.exit(0)
    else:
        print(f"\n❌ Some validations failed for {environment} environment")
        sys.exit(1)
```

---

## Rollback Procedures

### Automated Rollback System

```bash
#!/bin/bash
# scripts/blue-green-rollback.sh

DEPLOYMENT_ID=${1}
ROLLBACK_TYPE=${2:-"manual"}  # manual, automatic, emergency

if [ -z "$DEPLOYMENT_ID" ]; then
    echo "Usage: $0 <deployment-id> [rollback-type]"
    exit 1
fi

echo "🔄 Starting Blue-Green rollback for deployment: $DEPLOYMENT_ID"
echo "Rollback type: $ROLLBACK_TYPE"
echo "Timestamp: $(date)"

# Load deployment state
DEPLOYMENT_STATE_FILE="deployment-plans/${DEPLOYMENT_ID}/state.json"

if [ ! -f "$DEPLOYMENT_STATE_FILE" ]; then
    echo "❌ Deployment state file not found: $DEPLOYMENT_STATE_FILE"
    exit 1
fi

# Extract current state
CURRENT_ACTIVE=$(jq -r '.active_environment' "$DEPLOYMENT_STATE_FILE")
PREVIOUS_ENV=$(jq -r '.previous_environment' "$DEPLOYMENT_STATE_FILE")
ROLLBACK_AVAILABLE=$(jq -r '.rollback_available' "$DEPLOYMENT_STATE_FILE")

echo "Current active environment: $CURRENT_ACTIVE"
echo "Target rollback environment: $PREVIOUS_ENV"

if [ "$ROLLBACK_AVAILABLE" != "true" ]; then
    echo "❌ Rollback not available for this deployment"
    exit 1
fi

# Update deployment state
update_rollback_state() {
    local phase=$1
    local status=$2
    jq --arg phase "$phase" --arg status "$status" --arg time "$(date -Iseconds)" \
        '.rollback_phase = $phase | .rollback_status = $status | .rollback_time = $time' \
        "$DEPLOYMENT_STATE_FILE" > "${DEPLOYMENT_STATE_FILE}.tmp" && \
        mv "${DEPLOYMENT_STATE_FILE}.tmp" "$DEPLOYMENT_STATE_FILE"
}

# Rollback execution
execute_rollback() {
    echo "⚡ Executing traffic rollback..."
    update_rollback_state "traffic_switch" "running"

    # Immediate traffic switch back to previous environment
    kubectl patch service backend-service-active -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$PREVIOUS_ENV\"}}}"

    kubectl patch service frontend-service-active -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$PREVIOUS_ENV\"}}}"

    # Update inactive service
    kubectl patch service backend-service-inactive -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$CURRENT_ACTIVE\"}}}"

    kubectl patch service frontend-service-inactive -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$CURRENT_ACTIVE\"}}}"

    echo "✅ Traffic switched back to $PREVIOUS_ENV environment"
    update_rollback_state "traffic_switch" "completed"

    # Brief stabilization period
    sleep 30

    # Validate rollback success
    echo "🔍 Validating rollback success..."
    update_rollback_state "validation" "running"

    if validate_rollback_success; then
        echo "✅ Rollback validation successful"
        update_rollback_state "validation" "completed"

        # Update deployment state
        jq --arg active "$PREVIOUS_ENV" --arg previous "$CURRENT_ACTIVE" \
            '.active_environment = $active | .previous_environment = $previous | .rollback_completed = true' \
            "$DEPLOYMENT_STATE_FILE" > "${DEPLOYMENT_STATE_FILE}.tmp" && \
            mv "${DEPLOYMENT_STATE_FILE}.tmp" "$DEPLOYMENT_STATE_FILE"

        return 0
    else
        echo "❌ Rollback validation failed"
        update_rollback_state "validation" "failed"
        return 1
    fi
}

validate_rollback_success() {
    local max_attempts=6  # 3 minutes total
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "🔍 Validation attempt $attempt/$max_attempts"

        # Check health endpoint
        if curl -f -s --max-time 10 "https://sunday.com/api/health" >/dev/null; then
            # Check error rates
            local error_rate=$(get_current_error_rate)
            if [ "${error_rate%.*}" -lt 5 ]; then
                echo "✅ Rollback validation successful"
                return 0
            fi
        fi

        echo "⏳ Waiting 30s before next validation attempt..."
        sleep 30
        ((attempt++))
    done

    return 1
}

# Emergency procedures
emergency_rollback() {
    echo "🚨 EMERGENCY ROLLBACK INITIATED"

    # Immediate traffic switch without validation
    kubectl patch service backend-service-active -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$PREVIOUS_ENV\"}}}" || true

    kubectl patch service frontend-service-active -n sunday-production \
        -p "{\"spec\":{\"selector\":{\"version\":\"$PREVIOUS_ENV\"}}}" || true

    # Scale down problematic environment
    kubectl scale deployment backend-deployment --replicas=0 -n sunday-$CURRENT_ACTIVE || true
    kubectl scale deployment frontend-deployment --replicas=0 -n sunday-$CURRENT_ACTIVE || true

    echo "🚨 Emergency rollback completed"
}

# Execute rollback based on type
case $ROLLBACK_TYPE in
    "emergency")
        emergency_rollback
        ;;
    "automatic"|"manual")
        if execute_rollback; then
            echo "✅ Rollback completed successfully"

            # Send notifications
            ./scripts/send-deployment-notification.sh "$DEPLOYMENT_ID" "rollback_success" \
                "Blue-Green deployment rolled back successfully to $PREVIOUS_ENV environment"

            exit 0
        else
            echo "❌ Rollback failed"

            # Send failure notifications
            ./scripts/send-deployment-notification.sh "$DEPLOYMENT_ID" "rollback_failed" \
                "Blue-Green rollback failed - manual intervention required"

            exit 1
        fi
        ;;
    *)
        echo "Unknown rollback type: $ROLLBACK_TYPE"
        exit 1
        ;;
esac
```

---

*This Blue-Green deployment automation framework provides zero-downtime deployments with instant rollback capabilities for Sunday.com's production environment. The system ensures reliability through comprehensive validation and monitoring throughout the deployment process.*

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: Deployment Specialist Team*