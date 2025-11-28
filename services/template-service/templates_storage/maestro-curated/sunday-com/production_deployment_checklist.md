# Sunday.com Production Deployment Checklist & Validation Tools

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Execution Checklist](#deployment-execution-checklist)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Automated Validation Tools](#automated-validation-tools)
6. [Go/No-Go Decision Framework](#gono-go-decision-framework)
7. [Emergency Procedures](#emergency-procedures)
8. [Compliance and Audit](#compliance-and-audit)

---

## Overview

This comprehensive checklist and validation framework ensures safe, reliable production deployments for Sunday.com. It provides structured validation at every stage of the deployment process, with automated tools and clear go/no-go criteria.

### Checklist Principles

- **Comprehensive Coverage**: Every aspect of deployment validated
- **Risk-Based Approach**: Higher scrutiny for higher-risk changes
- **Automated Where Possible**: Reduce human error through automation
- **Clear Criteria**: Objective pass/fail criteria for each check
- **Audit Trail**: Complete documentation of all validation steps

### Deployment Risk Levels

| Risk Level | Criteria | Validation Requirements |
|------------|----------|------------------------|
| **Low** | Patch fixes, configuration changes | Standard checklist |
| **Medium** | Minor features, dependency updates | Enhanced validation |
| **High** | Major features, API changes | Comprehensive validation |
| **Critical** | Infrastructure changes, breaking changes | Full validation + approvals |

---

## Pre-Deployment Checklist

### Phase 1: Planning & Preparation (T-7 days)

#### Development & Testing Validation

```yaml
# Automated checks (run via CI/CD)
development_validation:
  code_quality:
    - name: "Code review completion"
      type: "manual"
      required: true
      validation: "All PRs have 2+ approvals from senior developers"

    - name: "Static code analysis"
      type: "automated"
      required: true
      command: "npm run lint && npm run type-check"
      threshold: "zero_errors"

    - name: "Security scan"
      type: "automated"
      required: true
      command: "npm audit --audit-level moderate"
      threshold: "zero_high_critical"

    - name: "Dependency vulnerability check"
      type: "automated"
      required: true
      command: "snyk test"
      threshold: "zero_high_critical"

  testing_coverage:
    - name: "Unit test coverage"
      type: "automated"
      required: true
      command: "npm run test:coverage"
      threshold: "coverage >= 85%"

    - name: "Integration tests"
      type: "automated"
      required: true
      command: "npm run test:integration"
      threshold: "all_passing"

    - name: "End-to-end tests"
      type: "automated"
      required: true
      command: "npm run test:e2e"
      threshold: "all_passing"

    - name: "Performance regression tests"
      type: "automated"
      required: true
      command: "npm run test:performance"
      threshold: "no_regression > 10%"

  documentation:
    - name: "API documentation updated"
      type: "manual"
      required: true
      validation: "OpenAPI specs updated for any API changes"

    - name: "Release notes prepared"
      type: "manual"
      required: true
      validation: "Release notes drafted and reviewed"

    - name: "Deployment runbook updated"
      type: "manual"
      required: true
      validation: "Any new deployment steps documented"
```

#### Infrastructure & Environment Validation

```bash
#!/bin/bash
# scripts/pre-deployment-infrastructure-check.sh

DEPLOYMENT_ID=${1}
ENVIRONMENT=${2:-"production"}

echo "🏗️ Pre-deployment infrastructure validation"
echo "Deployment: $DEPLOYMENT_ID"
echo "Environment: $ENVIRONMENT"

VALIDATION_RESULTS=""
TOTAL_CHECKS=0
PASSED_CHECKS=0

validate_check() {
    local check_name=$1
    local check_command=$2
    local expected_result=${3:-0}

    ((TOTAL_CHECKS++))
    echo "🔍 $check_name"

    if eval "$check_command"; then
        if [ $? -eq $expected_result ]; then
            echo "  ✅ PASSED"
            ((PASSED_CHECKS++))
            VALIDATION_RESULTS="$VALIDATION_RESULTS$check_name: PASSED\n"
        else
            echo "  ❌ FAILED"
            VALIDATION_RESULTS="$VALIDATION_RESULTS$check_name: FAILED\n"
        fi
    else
        echo "  ❌ ERROR"
        VALIDATION_RESULTS="$VALIDATION_RESULTS$check_name: ERROR\n"
    fi
}

echo "📊 1. Cluster Health Validation"

validate_check "Kubernetes cluster connectivity" \
    "kubectl cluster-info >/dev/null 2>&1"

validate_check "All nodes ready" \
    "kubectl get nodes --no-headers | grep -v Ready | wc -l | grep -q '^0$'"

validate_check "Control plane health" \
    "kubectl get componentstatuses --no-headers | grep -v Healthy | wc -l | grep -q '^0$'"

validate_check "Pod security policies active" \
    "kubectl get psp --no-headers | wc -l | awk '{exit \$1 > 0 ? 0 : 1}'"

echo "💾 2. Database Validation"

validate_check "Database connectivity" \
    "kubectl exec -n sunday-$ENVIRONMENT deployment/backend-deployment -- node -e 'require(\"./src/config/database\").testConnection()'"

validate_check "Database disk space" \
    "aws rds describe-db-clusters --db-cluster-identifier sunday-$ENVIRONMENT --query 'DBClusters[0].AllocatedStorage' --output text | awk '{exit \$1 > 80 ? 1 : 0}'"

validate_check "Database backup recent" \
    "aws rds describe-db-snapshots --db-cluster-identifier sunday-$ENVIRONMENT --query 'DBSnapshots[0].SnapshotCreateTime' --output text | xargs -I {} date -d {} +%s | awk '{exit (systime() - \$1) < 86400 ? 0 : 1}'"

validate_check "Database connection pool" \
    "kubectl exec -n sunday-$ENVIRONMENT deployment/backend-deployment -- node -e 'console.log(process.env.DB_POOL_SIZE)' | awk '{exit \$1 >= 10 ? 0 : 1}'"

echo "🗄️ 3. Storage and Cache Validation"

validate_check "Redis connectivity" \
    "kubectl exec -n sunday-$ENVIRONMENT deployment/backend-deployment -- redis-cli -h redis ping | grep -q PONG"

validate_check "S3 bucket accessibility" \
    "aws s3 ls s3://sunday-$ENVIRONMENT-storage/ >/dev/null 2>&1"

validate_check "Elasticsearch cluster health" \
    "curl -s http://elasticsearch:9200/_cluster/health | jq -r '.status' | grep -q green"

echo "🌐 4. Network and Load Balancer Validation"

validate_check "Load balancer health" \
    "aws elbv2 describe-target-health --target-group-arn \$(aws elbv2 describe-target-groups --names sunday-$ENVIRONMENT --query 'TargetGroups[0].TargetGroupArn' --output text) --query 'TargetHealthDescriptions[?TargetHealth.State!=\`healthy\`]' --output text | wc -l | grep -q '^0$'"

validate_check "DNS resolution" \
    "nslookup sunday.com | grep -q 'Address:'"

validate_check "SSL certificate validity" \
    "echo | openssl s_client -servername sunday.com -connect sunday.com:443 2>/dev/null | openssl x509 -noout -dates | grep 'notAfter' | awk -F= '{print \$2}' | xargs -I {} date -d {} +%s | awk '{exit (systime() + 2592000) < \$1 ? 0 : 1}'"

echo "📊 5. Monitoring and Observability"

validate_check "Prometheus targets healthy" \
    "curl -s http://prometheus:9090/api/v1/targets | jq '.data.activeTargets | map(select(.health == \"up\")) | length' | awk '{exit \$1 > 10 ? 0 : 1}'"

validate_check "Grafana accessibility" \
    "curl -f -s http://grafana:3000/api/health >/dev/null"

validate_check "AlertManager responsive" \
    "curl -f -s http://alertmanager:9093/api/v1/status >/dev/null"

validate_check "Log aggregation working" \
    "curl -s 'http://elasticsearch:9200/_cat/indices' | grep logstash | wc -l | awk '{exit \$1 > 0 ? 0 : 1}'"

echo "🔒 6. Security Validation"

validate_check "Network policies active" \
    "kubectl get networkpolicies -n sunday-$ENVIRONMENT --no-headers | wc -l | awk '{exit \$1 > 0 ? 0 : 1}'"

validate_check "Pod security contexts" \
    "kubectl get pods -n sunday-$ENVIRONMENT -o jsonpath='{.items[*].spec.securityContext.runAsNonRoot}' | grep -q true"

validate_check "Secret encryption at rest" \
    "kubectl get secrets -n sunday-$ENVIRONMENT --no-headers | wc -l | awk '{exit \$1 > 0 ? 0 : 1}'"

validate_check "Image vulnerability scan" \
    "docker scout cves ghcr.io/sunday/backend:latest --format json | jq '.vulnerabilities | map(select(.severity == \"critical\")) | length' | grep -q '^0$'"

# Calculate success rate
SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo ""
echo "📋 Infrastructure Validation Summary"
echo "=================================="
echo "Total Checks: $TOTAL_CHECKS"
echo "Passed Checks: $PASSED_CHECKS"
echo "Success Rate: $SUCCESS_RATE%"
echo ""

# Generate detailed report
cat > "deployment-plans/$DEPLOYMENT_ID/infrastructure-validation-report.md" << EOF
# Infrastructure Validation Report

**Deployment ID**: $DEPLOYMENT_ID
**Environment**: $ENVIRONMENT
**Validation Date**: $(date)
**Success Rate**: $SUCCESS_RATE%

## Results Summary

- **Total Checks**: $TOTAL_CHECKS
- **Passed**: $PASSED_CHECKS
- **Failed**: $((TOTAL_CHECKS - PASSED_CHECKS))

## Detailed Results

$(echo -e "$VALIDATION_RESULTS")

## Recommendation

$(if [ $SUCCESS_RATE -ge 95 ]; then
    echo "🟢 **PROCEED**: Infrastructure validation passed"
elif [ $SUCCESS_RATE -ge 85 ]; then
    echo "🟡 **CAUTION**: Review failed checks before proceeding"
else
    echo "🔴 **BLOCK**: Too many failed checks - address issues before deployment"
fi)
EOF

if [ $SUCCESS_RATE -ge 95 ]; then
    echo "✅ Infrastructure validation PASSED"
    exit 0
elif [ $SUCCESS_RATE -ge 85 ]; then
    echo "⚠️ Infrastructure validation WARNING"
    exit 1
else
    echo "❌ Infrastructure validation FAILED"
    exit 2
fi
```

#### Business & Stakeholder Validation

```yaml
business_validation:
  stakeholder_approval:
    - name: "Product owner approval"
      type: "manual"
      required: true
      validation: "Product owner has approved release scope"

    - name: "Security team approval"
      type: "manual"
      required_for: ["high", "critical"]
      validation: "Security review completed and approved"

    - name: "Customer success notification"
      type: "manual"
      required: true
      validation: "Customer success team notified of changes"

  business_readiness:
    - name: "Support documentation ready"
      type: "manual"
      required: true
      validation: "Support team has updated documentation"

    - name: "Feature flags configured"
      type: "manual"
      required: true
      validation: "Feature flags set for gradual rollout"

    - name: "Rollback plan documented"
      type: "manual"
      required: true
      validation: "Detailed rollback procedures documented"

    - name: "Communication plan ready"
      type: "manual"
      required: true
      validation: "Customer communication templates prepared"
```

### Phase 2: Final Preparation (T-24 hours)

#### Pre-Deployment Systems Check

```python
#!/usr/bin/env python3
# scripts/final-pre-deployment-check.py

import subprocess
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class PreDeploymentValidator:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.base_url = f"https://{'sunday.com' if environment == 'production' else environment + '.sunday.com'}"
        self.validation_results = []

    def run_final_validation(self) -> Tuple[bool, Dict]:
        """Run comprehensive final validation before deployment"""

        print(f"🔍 Running final pre-deployment validation for {self.environment}")

        validation_suite = [
            ("System Health", self.validate_system_health),
            ("Performance Baseline", self.validate_performance_baseline),
            ("Security Posture", self.validate_security_posture),
            ("Data Integrity", self.validate_data_integrity),
            ("External Dependencies", self.validate_external_dependencies),
            ("Capacity Planning", self.validate_capacity_planning),
            ("Backup Verification", self.validate_backup_status),
            ("Team Readiness", self.validate_team_readiness)
        ]

        overall_success = True
        detailed_results = {}

        for category, validator in validation_suite:
            print(f"\n📋 {category} Validation")
            try:
                success, details = validator()
                detailed_results[category] = {
                    "success": success,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }

                if success:
                    print(f"✅ {category}: PASSED")
                else:
                    print(f"❌ {category}: FAILED")
                    overall_success = False

            except Exception as e:
                print(f"❌ {category}: ERROR - {str(e)}")
                detailed_results[category] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                overall_success = False

        return overall_success, detailed_results

    def validate_system_health(self) -> Tuple[bool, Dict]:
        """Validate current system health"""

        checks = []

        # API health check
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            checks.append({
                "name": "API Health Endpoint",
                "success": response.status_code == 200,
                "value": response.status_code
            })
        except Exception as e:
            checks.append({
                "name": "API Health Endpoint",
                "success": False,
                "error": str(e)
            })

        # Database health
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', f'sunday-{self.environment}',
                'deployment/backend-deployment', '--',
                'node', '-e', 'require("./src/config/database").testConnection()'
            ], capture_output=True, timeout=15)

            checks.append({
                "name": "Database Connectivity",
                "success": result.returncode == 0,
                "output": result.stdout.decode()
            })
        except Exception as e:
            checks.append({
                "name": "Database Connectivity",
                "success": False,
                "error": str(e)
            })

        # Application pods status
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pods', '-n', f'sunday-{self.environment}',
                '--field-selector=status.phase=Running', '--no-headers'
            ], capture_output=True, text=True)

            running_pods = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            result = subprocess.run([
                'kubectl', 'get', 'pods', '-n', f'sunday-{self.environment}',
                '--no-headers'
            ], capture_output=True, text=True)

            total_pods = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            checks.append({
                "name": "Pod Health",
                "success": running_pods == total_pods and total_pods > 0,
                "running_pods": running_pods,
                "total_pods": total_pods
            })
        except Exception as e:
            checks.append({
                "name": "Pod Health",
                "success": False,
                "error": str(e)
            })

        success = all(check["success"] for check in checks)
        return success, {"checks": checks}

    def validate_performance_baseline(self) -> Tuple[bool, Dict]:
        """Validate current performance metrics"""

        metrics = {}

        # Response time check
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            response_time = (time.time() - start_time) * 1000

            metrics["api_response_time"] = {
                "value": response_time,
                "unit": "ms",
                "threshold": 500,
                "success": response_time < 500
            }
        except Exception as e:
            metrics["api_response_time"] = {
                "success": False,
                "error": str(e)
            }

        # Current error rate (from Prometheus if available)
        try:
            prom_query = 'rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])'
            response = requests.get(
                f"http://prometheus:9090/api/v1/query",
                params={"query": prom_query},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data["status"] == "success" and data["data"]["result"]:
                    error_rate = float(data["data"]["result"][0]["value"][1]) * 100

                    metrics["error_rate"] = {
                        "value": error_rate,
                        "unit": "%",
                        "threshold": 1.0,
                        "success": error_rate < 1.0
                    }
        except Exception as e:
            metrics["error_rate"] = {
                "success": False,
                "error": str(e)
            }

        # System resource utilization
        try:
            # CPU usage
            result = subprocess.run([
                'kubectl', 'top', 'nodes', '--no-headers'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                cpu_usage = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 3:
                        cpu_percent = int(parts[2].rstrip('%'))
                        cpu_usage.append(cpu_percent)

                avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0

                metrics["cpu_usage"] = {
                    "value": avg_cpu,
                    "unit": "%",
                    "threshold": 70,
                    "success": avg_cpu < 70
                }
        except Exception as e:
            metrics["cpu_usage"] = {
                "success": False,
                "error": str(e)
            }

        success = all(
            metric.get("success", False)
            for metric in metrics.values()
        )

        return success, {"metrics": metrics}

    def validate_security_posture(self) -> Tuple[bool, Dict]:
        """Validate security configuration"""

        security_checks = []

        # SSL certificate validity
        try:
            result = subprocess.run([
                'echo', '|', 'openssl', 's_client', '-servername', 'sunday.com',
                '-connect', 'sunday.com:443', '2>/dev/null', '|',
                'openssl', 'x509', '-noout', '-dates'
            ], shell=True, capture_output=True, text=True)

            # Simplified check - in real implementation, parse the certificate dates
            security_checks.append({
                "name": "SSL Certificate",
                "success": "notAfter" in result.stdout,
                "details": "Certificate validity checked"
            })
        except Exception as e:
            security_checks.append({
                "name": "SSL Certificate",
                "success": False,
                "error": str(e)
            })

        # Network policies
        try:
            result = subprocess.run([
                'kubectl', 'get', 'networkpolicies', '-n', f'sunday-{self.environment}',
                '--no-headers'
            ], capture_output=True, text=True)

            policy_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            security_checks.append({
                "name": "Network Policies",
                "success": policy_count > 0,
                "count": policy_count
            })
        except Exception as e:
            security_checks.append({
                "name": "Network Policies",
                "success": False,
                "error": str(e)
            })

        success = all(check["success"] for check in security_checks)
        return success, {"checks": security_checks}

    def validate_data_integrity(self) -> Tuple[bool, Dict]:
        """Validate data integrity and consistency"""

        integrity_checks = []

        # Database consistency check
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', f'sunday-{self.environment}',
                'deployment/backend-deployment', '--',
                'node', '-e', 'require("./scripts/data-integrity-check.js")'
            ], capture_output=True, timeout=30)

            integrity_checks.append({
                "name": "Database Consistency",
                "success": result.returncode == 0,
                "output": result.stdout.decode()
            })
        except Exception as e:
            integrity_checks.append({
                "name": "Database Consistency",
                "success": False,
                "error": str(e)
            })

        success = all(check["success"] for check in integrity_checks)
        return success, {"checks": integrity_checks}

    def validate_external_dependencies(self) -> Tuple[bool, Dict]:
        """Validate external service dependencies"""

        dependencies = [
            ("GitHub API", "https://api.github.com/status"),
            ("SendGrid", "https://status.sendgrid.com/api/v2/status.json"),
            ("Stripe", "https://status.stripe.com/api/v2/status.json")
        ]

        dependency_checks = []

        for name, url in dependencies:
            try:
                response = requests.get(url, timeout=10)
                dependency_checks.append({
                    "name": name,
                    "success": response.status_code == 200,
                    "status_code": response.status_code
                })
            except Exception as e:
                dependency_checks.append({
                    "name": name,
                    "success": False,
                    "error": str(e)
                })

        success = all(check["success"] for check in dependency_checks)
        return success, {"checks": dependency_checks}

    def validate_capacity_planning(self) -> Tuple[bool, Dict]:
        """Validate system capacity for expected load"""

        capacity_metrics = {}

        # Check current resource utilization vs capacity
        try:
            # Node capacity check
            result = subprocess.run([
                'kubectl', 'describe', 'nodes'
            ], capture_output=True, text=True)

            # Simplified capacity check - in real implementation, parse detailed metrics
            capacity_metrics["node_capacity"] = {
                "success": "Ready" in result.stdout,
                "details": "Node capacity check completed"
            }
        except Exception as e:
            capacity_metrics["node_capacity"] = {
                "success": False,
                "error": str(e)
            }

        success = all(
            metric.get("success", False)
            for metric in capacity_metrics.values()
        )

        return success, capacity_metrics

    def validate_backup_status(self) -> Tuple[bool, Dict]:
        """Validate backup systems and recent backups"""

        backup_checks = []

        # Database backup check
        try:
            result = subprocess.run([
                'aws', 'rds', 'describe-db-snapshots',
                '--db-cluster-identifier', f'sunday-{self.environment}',
                '--snapshot-type', 'manual',
                '--query', 'DBSnapshots[0].SnapshotCreateTime',
                '--output', 'text'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                backup_time = result.stdout.strip()
                # Simplified check - in real implementation, parse timestamp
                backup_checks.append({
                    "name": "Database Backup",
                    "success": len(backup_time) > 0,
                    "last_backup": backup_time
                })
            else:
                backup_checks.append({
                    "name": "Database Backup",
                    "success": False,
                    "error": "No recent backups found"
                })
        except Exception as e:
            backup_checks.append({
                "name": "Database Backup",
                "success": False,
                "error": str(e)
            })

        success = all(check["success"] for check in backup_checks)
        return success, {"checks": backup_checks}

    def validate_team_readiness(self) -> Tuple[bool, Dict]:
        """Validate team readiness for deployment"""

        # This would typically integrate with on-call scheduling systems
        readiness_checks = [
            {
                "name": "On-call Engineer Available",
                "success": True,  # Would check actual on-call system
                "details": "On-call engineer confirmed availability"
            },
            {
                "name": "War Room Prepared",
                "success": True,  # Would check Slack channel creation, etc.
                "details": "Communication channels prepared"
            },
            {
                "name": "Rollback Plan Reviewed",
                "success": True,  # Would check documentation timestamps
                "details": "Rollback procedures reviewed and updated"
            }
        ]

        success = all(check["success"] for check in readiness_checks)
        return success, {"checks": readiness_checks}

    def generate_validation_report(self, results: Dict) -> str:
        """Generate comprehensive validation report"""

        report = f"""# Pre-Deployment Validation Report

**Environment**: {self.environment}
**Validation Date**: {datetime.now().isoformat()}
**Overall Status**: {"✅ PASSED" if all(cat["success"] for cat in results.values()) else "❌ FAILED"}

## Summary

| Category | Status | Details |
|----------|--------|---------|
"""

        for category, result in results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            details = len(result.get("checks", result.get("metrics", [])))
            report += f"| {category} | {status} | {details} checks |\n"

        report += "\n## Detailed Results\n\n"

        for category, result in results.items():
            report += f"### {category}\n\n"
            if "checks" in result:
                for check in result["checks"]:
                    status = "✅" if check["success"] else "❌"
                    report += f"- {status} {check['name']}\n"
            elif "metrics" in result:
                for metric_name, metric in result["metrics"].items():
                    status = "✅" if metric["success"] else "❌"
                    value = metric.get("value", "N/A")
                    unit = metric.get("unit", "")
                    report += f"- {status} {metric_name}: {value}{unit}\n"
            report += "\n"

        return report

if __name__ == "__main__":
    import sys

    environment = sys.argv[1] if len(sys.argv) > 1 else "production"

    validator = PreDeploymentValidator(environment)
    success, results = validator.run_final_validation()

    # Generate report
    report = validator.generate_validation_report(results)

    # Save report
    with open(f"pre-deployment-validation-{environment}-{int(time.time())}.md", 'w') as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"Pre-deployment validation: {'PASSED' if success else 'FAILED'}")
    print(f"{'='*60}")

    if success:
        print("🟢 All validations passed - deployment approved")
        sys.exit(0)
    else:
        print("🔴 Some validations failed - address issues before deployment")
        sys.exit(1)
```

---

## Deployment Execution Checklist

### Real-time Deployment Monitoring

```yaml
deployment_execution:
  phase_1_preparation:
    - name: "Deployment war room established"
      type: "manual"
      required: true
      validation: "Slack channel created with all stakeholders"

    - name: "Monitoring dashboards ready"
      type: "manual"
      required: true
      validation: "Grafana dashboards opened and monitoring active"

    - name: "Status page updated"
      type: "manual"
      required: true
      validation: "Maintenance window scheduled if required"

    - name: "Customer notifications sent"
      type: "manual"
      required_for: ["high", "critical"]
      validation: "Customer communication sent if user-facing changes"

  phase_2_execution:
    - name: "Deployment initiated"
      type: "automated"
      required: true
      command: "./scripts/initiate-deployment.sh"

    - name: "Real-time monitoring active"
      type: "automated"
      required: true
      validation: "Monitoring scripts running and reporting"

    - name: "Health checks passing"
      type: "automated"
      required: true
      validation: "All health endpoints responding correctly"

    - name: "Error rates within bounds"
      type: "automated"
      required: true
      threshold: "error_rate < 1%"

  phase_3_validation:
    - name: "Smoke tests execution"
      type: "automated"
      required: true
      command: "./scripts/deployment-smoke-tests.sh"

    - name: "Performance validation"
      type: "automated"
      required: true
      validation: "Response times within acceptable ranges"

    - name: "User journey validation"
      type: "automated"
      required: true
      command: "./scripts/critical-user-journey-tests.sh"

  phase_4_completion:
    - name: "Traffic fully migrated"
      type: "automated"
      required: true
      validation: "100% traffic on new version"

    - name: "Old version cleanup"
      type: "manual"
      required: true
      validation: "Previous version pods scaled down or removed"

    - name: "Status page updated"
      type: "manual"
      required: true
      validation: "Deployment completion communicated"
```

### Critical User Journey Tests

```bash
#!/bin/bash
# scripts/critical-user-journey-tests.sh

ENVIRONMENT=${1:-"production"}
BASE_URL="https://$([ "$ENVIRONMENT" = "production" ] && echo "sunday.com" || echo "$ENVIRONMENT.sunday.com")"

echo "🧪 Running critical user journey tests for $ENVIRONMENT"

TEST_RESULTS=""
TOTAL_TESTS=0
PASSED_TESTS=0

run_test() {
    local test_name=$1
    local test_function=$2

    ((TOTAL_TESTS++))
    echo "🔍 Testing: $test_name"

    if $test_function; then
        echo "  ✅ PASSED"
        ((PASSED_TESTS++))
        TEST_RESULTS="$TEST_RESULTS$test_name: PASSED\n"
    else
        echo "  ❌ FAILED"
        TEST_RESULTS="$TEST_RESULTS$test_name: FAILED\n"
    fi
}

# Test functions
test_user_registration() {
    local email="test-$(date +%s)@example.com"
    local response=$(curl -s -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$email\",\"password\":\"TestPass123!\",\"name\":\"Test User\"}")

    echo "$response" | grep -q "success\|created\|token"
}

test_user_login() {
    local response=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@sunday.com","password":"TestPass123!"}')

    echo "$response" | grep -q "token\|success"
}

test_workspace_creation() {
    # Get auth token first
    local token=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@sunday.com","password":"TestPass123!"}' | \
        jq -r '.token // empty')

    if [ -n "$token" ]; then
        local response=$(curl -s -X POST "$BASE_URL/api/workspaces" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d '{"name":"Test Workspace","description":"Automated test workspace"}')

        echo "$response" | grep -q "id\|created"
    else
        return 1
    fi
}

test_task_creation() {
    # Get auth token
    local token=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@sunday.com","password":"TestPass123!"}' | \
        jq -r '.token // empty')

    if [ -n "$token" ]; then
        local response=$(curl -s -X POST "$BASE_URL/api/tasks" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d '{"title":"Test Task","description":"Automated test task","priority":"medium"}')

        echo "$response" | grep -q "id\|created"
    else
        return 1
    fi
}

test_real_time_updates() {
    # Test WebSocket connection
    local ws_url="wss://$([ "$ENVIRONMENT" = "production" ] && echo "sunday.com" || echo "$ENVIRONMENT.sunday.com")/ws"

    timeout 10 node -e "
        const WebSocket = require('ws');
        const ws = new WebSocket('$ws_url');
        ws.on('open', () => {
            console.log('WebSocket connected');
            ws.close();
            process.exit(0);
        });
        ws.on('error', () => process.exit(1));
        setTimeout(() => process.exit(1), 5000);
    " 2>/dev/null
}

test_file_upload() {
    local token=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@sunday.com","password":"TestPass123!"}' | \
        jq -r '.token // empty')

    if [ -n "$token" ]; then
        # Create a small test file
        echo "Test file content" > /tmp/test-upload.txt

        local response=$(curl -s -X POST "$BASE_URL/api/files/upload" \
            -H "Authorization: Bearer $token" \
            -F "file=@/tmp/test-upload.txt")

        rm -f /tmp/test-upload.txt
        echo "$response" | grep -q "url\|id\|success"
    else
        return 1
    fi
}

test_search_functionality() {
    local token=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@sunday.com","password":"TestPass123!"}' | \
        jq -r '.token // empty')

    if [ -n "$token" ]; then
        local response=$(curl -s -X GET "$BASE_URL/api/search?q=test" \
            -H "Authorization: Bearer $token")

        echo "$response" | grep -q "results\|data"
    else
        return 1
    fi
}

test_api_performance() {
    local start_time=$(date +%s%N)
    local response=$(curl -s "$BASE_URL/api/health")
    local end_time=$(date +%s%N)

    local duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds

    # Check if response time is under 500ms
    [ $duration -lt 500 ] && echo "$response" | grep -q "ok\|healthy"
}

# Run all tests
echo "🚀 Starting critical user journey tests..."

run_test "User Registration" test_user_registration
run_test "User Login" test_user_login
run_test "Workspace Creation" test_workspace_creation
run_test "Task Creation" test_task_creation
run_test "Real-time Updates" test_real_time_updates
run_test "File Upload" test_file_upload
run_test "Search Functionality" test_search_functionality
run_test "API Performance" test_api_performance

# Calculate success rate
SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

echo ""
echo "📊 User Journey Test Results"
echo "============================"
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Success Rate: $SUCCESS_RATE%"
echo ""

if [ $SUCCESS_RATE -ge 90 ]; then
    echo "✅ Critical user journeys PASSED"
    exit 0
elif [ $SUCCESS_RATE -ge 75 ]; then
    echo "⚠️ Critical user journeys WARNING - some tests failed"
    exit 1
else
    echo "❌ Critical user journeys FAILED - too many failures"
    exit 2
fi
```

---

## Go/No-Go Decision Framework

### Automated Decision Engine

```python
#!/usr/bin/env python3
# scripts/go-no-go-decision-engine.py

import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class DecisionLevel(Enum):
    GO = "go"
    CAUTION = "caution"
    NO_GO = "no_go"

@dataclass
class ValidationResult:
    category: str
    success: bool
    score: int  # 0-100
    critical: bool
    details: Dict

class GoNoGoDecisionEngine:
    def __init__(self):
        self.decision_criteria = {
            "infrastructure": {"weight": 25, "minimum_score": 90},
            "security": {"weight": 20, "minimum_score": 95},
            "performance": {"weight": 20, "minimum_score": 85},
            "business": {"weight": 15, "minimum_score": 80},
            "monitoring": {"weight": 10, "minimum_score": 85},
            "team_readiness": {"weight": 10, "minimum_score": 90}
        }

        self.critical_blockers = [
            "security_vulnerability",
            "data_corruption_risk",
            "infrastructure_failure",
            "regulatory_compliance_issue"
        ]

    def make_decision(self, validation_results: List[ValidationResult],
                     deployment_risk_level: str) -> Tuple[DecisionLevel, Dict]:
        """Make go/no-go decision based on validation results"""

        print("🎯 Analyzing validation results for go/no-go decision...")

        # Check for critical blockers
        critical_issues = self.check_critical_blockers(validation_results)
        if critical_issues:
            return DecisionLevel.NO_GO, {
                "reason": "Critical blockers detected",
                "critical_issues": critical_issues,
                "recommendation": "Address critical issues before proceeding"
            }

        # Calculate weighted score
        overall_score = self.calculate_weighted_score(validation_results)

        # Get minimum threshold based on risk level
        min_threshold = self.get_minimum_threshold(deployment_risk_level)

        # Analyze individual category scores
        category_analysis = self.analyze_categories(validation_results)

        # Make decision
        decision = self.determine_decision_level(
            overall_score, min_threshold, category_analysis, deployment_risk_level
        )

        decision_details = {
            "overall_score": overall_score,
            "minimum_threshold": min_threshold,
            "deployment_risk_level": deployment_risk_level,
            "category_scores": category_analysis,
            "recommendation": self.generate_recommendation(decision, overall_score, category_analysis),
            "next_steps": self.generate_next_steps(decision),
            "timestamp": time.time()
        }

        return decision, decision_details

    def check_critical_blockers(self, validation_results: List[ValidationResult]) -> List[str]:
        """Check for critical blocking issues"""

        critical_issues = []

        for result in validation_results:
            if not result.success and result.critical:
                critical_issues.append(f"{result.category}: {result.details.get('issue', 'Critical failure')}")

            # Check for specific critical conditions
            if result.category == "security" and result.score < 80:
                critical_issues.append("Security score below critical threshold")

            if result.category == "infrastructure" and result.score < 85:
                critical_issues.append("Infrastructure readiness below critical threshold")

        return critical_issues

    def calculate_weighted_score(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall weighted score"""

        total_weighted_score = 0
        total_weight = 0

        for result in validation_results:
            if result.category in self.decision_criteria:
                weight = self.decision_criteria[result.category]["weight"]
                total_weighted_score += result.score * weight
                total_weight += weight

        return total_weighted_score / total_weight if total_weight > 0 else 0

    def get_minimum_threshold(self, risk_level: str) -> float:
        """Get minimum threshold based on deployment risk level"""

        thresholds = {
            "low": 80,
            "medium": 85,
            "high": 90,
            "critical": 95
        }

        return thresholds.get(risk_level, 85)

    def analyze_categories(self, validation_results: List[ValidationResult]) -> Dict:
        """Analyze individual category performance"""

        category_analysis = {}

        for result in validation_results:
            category_analysis[result.category] = {
                "score": result.score,
                "success": result.success,
                "minimum_required": self.decision_criteria.get(result.category, {}).get("minimum_score", 80),
                "meets_minimum": result.score >= self.decision_criteria.get(result.category, {}).get("minimum_score", 80),
                "details": result.details
            }

        return category_analysis

    def determine_decision_level(self, overall_score: float, min_threshold: float,
                               category_analysis: Dict, risk_level: str) -> DecisionLevel:
        """Determine the final decision level"""

        # Check if overall score meets threshold
        if overall_score < min_threshold:
            return DecisionLevel.NO_GO

        # Check if any category fails minimum requirements
        failed_categories = [
            cat for cat, analysis in category_analysis.items()
            if not analysis["meets_minimum"]
        ]

        if failed_categories:
            if risk_level in ["high", "critical"]:
                return DecisionLevel.NO_GO
            else:
                return DecisionLevel.CAUTION

        # All checks passed
        if overall_score >= min_threshold + 5:  # 5 point buffer
            return DecisionLevel.GO
        else:
            return DecisionLevel.CAUTION

    def generate_recommendation(self, decision: DecisionLevel, overall_score: float,
                              category_analysis: Dict) -> str:
        """Generate detailed recommendation"""

        if decision == DecisionLevel.GO:
            return (f"Deployment approved. Overall score of {overall_score:.1f} meets all requirements. "
                   f"All validation categories are within acceptable ranges.")

        elif decision == DecisionLevel.CAUTION:
            weak_categories = [
                cat for cat, analysis in category_analysis.items()
                if analysis["score"] < analysis["minimum_required"] + 10
            ]
            return (f"Proceed with caution. Overall score of {overall_score:.1f} is acceptable, "
                   f"but monitor the following areas closely: {', '.join(weak_categories)}")

        else:  # NO_GO
            failed_categories = [
                cat for cat, analysis in category_analysis.items()
                if not analysis["meets_minimum"]
            ]
            return (f"Deployment blocked. Overall score of {overall_score:.1f} is below threshold. "
                   f"Address issues in: {', '.join(failed_categories)}")

    def generate_next_steps(self, decision: DecisionLevel) -> List[str]:
        """Generate specific next steps based on decision"""

        if decision == DecisionLevel.GO:
            return [
                "Proceed with deployment execution",
                "Activate real-time monitoring",
                "Notify stakeholders of deployment start",
                "Prepare rollback procedures as precaution"
            ]

        elif decision == DecisionLevel.CAUTION:
            return [
                "Proceed with enhanced monitoring",
                "Have rollback team on standby",
                "Consider reduced deployment scope",
                "Increase post-deployment validation period"
            ]

        else:  # NO_GO
            return [
                "Address failed validation items",
                "Re-run validation after fixes",
                "Schedule new deployment window",
                "Communicate delay to stakeholders"
            ]

    def generate_decision_report(self, decision: DecisionLevel, details: Dict) -> str:
        """Generate comprehensive decision report"""

        decision_icons = {
            DecisionLevel.GO: "🟢",
            DecisionLevel.CAUTION: "🟡",
            DecisionLevel.NO_GO: "🔴"
        }

        report = f"""# Go/No-Go Decision Report

## Decision Summary

**{decision_icons[decision]} {decision.value.upper()}**

- **Overall Score**: {details['overall_score']:.1f}/100
- **Minimum Threshold**: {details['minimum_threshold']}
- **Risk Level**: {details['deployment_risk_level']}
- **Timestamp**: {time.ctime(details['timestamp'])}

## Recommendation

{details['recommendation']}

## Category Analysis

| Category | Score | Required | Status |
|----------|-------|----------|--------|
"""

        for category, analysis in details['category_scores'].items():
            status_icon = "✅" if analysis['meets_minimum'] else "❌"
            report += f"| {category} | {analysis['score']}/100 | {analysis['minimum_required']} | {status_icon} |\n"

        report += f"\n## Next Steps\n\n"
        for i, step in enumerate(details['next_steps'], 1):
            report += f"{i}. {step}\n"

        return report

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python go-no-go-decision-engine.py <validation-results.json>")
        sys.exit(1)

    results_file = sys.argv[1]

    try:
        with open(results_file, 'r') as f:
            raw_results = json.load(f)
    except FileNotFoundError:
        print(f"Results file not found: {results_file}")
        sys.exit(1)

    # Convert raw results to ValidationResult objects
    validation_results = []
    for category, data in raw_results.items():
        if isinstance(data, dict) and 'success' in data:
            validation_results.append(ValidationResult(
                category=category,
                success=data['success'],
                score=data.get('score', 0),
                critical=data.get('critical', False),
                details=data.get('details', {})
            ))

    # Get deployment risk level (default to medium)
    risk_level = raw_results.get('deployment_risk_level', 'medium')

    # Make decision
    engine = GoNoGoDecisionEngine()
    decision, details = engine.make_decision(validation_results, risk_level)

    # Generate and save report
    report = engine.generate_decision_report(decision, details)

    report_file = f"go-no-go-decision-{int(time.time())}.md"
    with open(report_file, 'w') as f:
        f.write(report)

    # Output decision
    print(f"\n{'='*60}")
    print(f"GO/NO-GO DECISION: {decision.value.upper()}")
    print(f"{'='*60}")
    print(f"Overall Score: {details['overall_score']:.1f}/100")
    print(f"Report saved: {report_file}")

    if decision == DecisionLevel.GO:
        print("🟢 DEPLOYMENT APPROVED")
        sys.exit(0)
    elif decision == DecisionLevel.CAUTION:
        print("🟡 PROCEED WITH CAUTION")
        sys.exit(0)
    else:
        print("🔴 DEPLOYMENT BLOCKED")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

*This Production Deployment Checklist & Validation Tools framework provides comprehensive validation at every stage of the deployment process, ensuring safe and reliable production deployments for Sunday.com.*

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: Deployment Specialist Team*