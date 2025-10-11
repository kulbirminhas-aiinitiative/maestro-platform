# Sunday.com Canary Deployment Framework

## Table of Contents

1. [Overview](#overview)
2. [Canary Deployment Architecture](#canary-deployment-architecture)
3. [Traffic Splitting Strategy](#traffic-splitting-strategy)
4. [Automated Analysis](#automated-analysis)
5. [Progressive Rollout Stages](#progressive-rollout-stages)
6. [Real-time Monitoring](#real-time-monitoring)
7. [Automated Decision Making](#automated-decision-making)
8. [Implementation Scripts](#implementation-scripts)

---

## Overview

Canary deployment is Sunday.com's safest deployment strategy for high-risk changes, allowing gradual traffic migration with real-time analysis and automatic rollback capabilities. This framework implements intelligent, data-driven canary deployments with comprehensive monitoring and automated decision-making.

### Canary Deployment Benefits

- **Risk Mitigation**: Gradual exposure limits blast radius of issues
- **Real-time Validation**: Continuous monitoring during rollout
- **Automated Decisions**: Data-driven promotion or rollback
- **User Impact Minimization**: Affects only small percentage initially
- **Performance Comparison**: Side-by-side version comparison

### Framework Features

- **Progressive Traffic Splitting**: 1% → 5% → 10% → 25% → 50% → 100%
- **Multi-metric Analysis**: Error rates, latency, business metrics
- **Intelligent Automation**: ML-powered anomaly detection
- **Flexible Controls**: Manual override and custom thresholds
- **Comprehensive Reporting**: Detailed analysis and recommendations

---

## Canary Deployment Architecture

### Traffic Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Canary Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                       Load Balancer                            │
│                     (Intelligent Routing)                      │
│                           │                                     │
│          ┌────────────────┼────────────────┐                    │
│          │                │                │                    │
│    ┌─────────────┐        │        ┌─────────────┐             │
│    │   STABLE    │        │        │   CANARY    │             │
│    │ Version N   │◄───────┼───────►│ Version N+1 │             │
│    │             │        │        │             │             │
│    │ 95% Traffic │        │        │ 5% Traffic  │             │
│    └─────────────┘        │        └─────────────┘             │
│          │                │                │                    │
│    ┌─────────────┐        │        ┌─────────────┐             │
│    │ Monitoring  │        │        │ Monitoring  │             │
│    │ & Metrics   │        │        │ & Metrics   │             │
│    └─────────────┘        │        └─────────────┘             │
│                           │                                     │
│          ┌────────────────────────────────┐                     │
│          │      Analysis Engine          │                     │
│          │  • Metric Comparison          │                     │
│          │  • Anomaly Detection         │                     │
│          │  • Decision Automation       │                     │
│          └────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### Kubernetes Implementation

```yaml
# k8s/canary/canary-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: sunday-backend-rollout
  namespace: sunday-production
spec:
  replicas: 10
  strategy:
    canary:
      # Canary service for routing canary traffic
      canaryService: backend-service-canary
      # Stable service for routing stable traffic
      stableService: backend-service-stable
      # Traffic routing via ingress
      trafficRouting:
        nginx:
          stableIngress: sunday-ingress
          annotationPrefix: nginx.ingress.kubernetes.io
          additionalIngressAnnotations:
            canary-by-header: X-Canary
            canary-by-header-value: "true"
      # Progressive rollout steps
      steps:
      - setWeight: 1    # Start with 1% traffic
      - pause:
          duration: 5m   # Monitor for 5 minutes
      - analysis:
          templates:
          - templateName: canary-success-rate
          - templateName: canary-latency
          args:
          - name: service-name
            value: backend-service-canary
      - setWeight: 5    # Increase to 5%
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: canary-success-rate
          - templateName: canary-latency
          - templateName: canary-business-metrics
          args:
          - name: service-name
            value: backend-service-canary
      - setWeight: 10   # Increase to 10%
      - pause:
          duration: 15m
      - analysis:
          templates:
          - templateName: comprehensive-canary-analysis
          args:
          - name: service-name
            value: backend-service-canary
      - setWeight: 25   # Increase to 25%
      - pause:
          duration: 20m
      - analysis:
          templates:
          - templateName: comprehensive-canary-analysis
          args:
          - name: service-name
            value: backend-service-canary
      - setWeight: 50   # Increase to 50%
      - pause:
          duration: 30m
      - analysis:
          templates:
          - templateName: comprehensive-canary-analysis
          args:
          - name: service-name
            value: backend-service-canary
      # Final validation before 100%
      - pause: {}       # Manual approval gate
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/sunday/backend:latest
        ports:
        - containerPort: 3000
        env:
        - name: DEPLOYMENT_TYPE
          value: "canary"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
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
# Analysis Templates
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: canary-success-rate
  namespace: sunday-production
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 10
    successCondition: result[0] >= 0.95
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[5m])) /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: canary-latency
  namespace: sunday-production
spec:
  metrics:
  - name: latency-p95
    interval: 30s
    count: 10
    successCondition: result[0] <= 2000
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[5m])) by (le)
          ) * 1000

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: canary-business-metrics
  namespace: sunday-production
spec:
  metrics:
  - name: conversion-rate
    interval: 60s
    count: 5
    successCondition: result[0] >= 0.85
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(user_conversions_total{service="{{args.service-name}}"}[10m])) /
          sum(rate(user_sessions_total{service="{{args.service-name}}"}[10m]))
  - name: error-budget-burn
    interval: 30s
    count: 10
    successCondition: result[0] <= 5
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          (1 - (sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[5m])) /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m])))) * 10000

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-canary-analysis
  namespace: sunday-production
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 20
    successCondition: result[0] >= 0.95
    failureLimit: 5
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[5m])) /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
  - name: latency-comparison
    interval: 30s
    count: 20
    successCondition: result[0] <= 1.2  # Max 20% increase
    failureLimit: 5
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          (histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[5m])) by (le)
          )) /
          (histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket{service="backend-service-stable"}[5m])) by (le)
          ))
  - name: memory-usage
    interval: 30s
    count: 10
    successCondition: result[0] <= 0.8  # Max 80% memory usage
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          avg(container_memory_usage_bytes{pod=~"{{args.service-name}}-.*"}) /
          avg(container_spec_memory_limit_bytes{pod=~"{{args.service-name}}-.*"})
```

---

## Traffic Splitting Strategy

### Progressive Traffic Allocation

```python
#!/usr/bin/env python3
# scripts/canary-traffic-controller.py

import time
import json
import requests
import subprocess
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class CanaryTrafficController:
    def __init__(self, rollout_name: str, namespace: str = "sunday-production"):
        self.rollout_name = rollout_name
        self.namespace = namespace
        self.prometheus_url = "http://prometheus:9090"
        self.traffic_stages = [1, 5, 10, 25, 50, 100]
        self.analysis_duration = {
            1: 300,   # 5 minutes
            5: 600,   # 10 minutes
            10: 900,  # 15 minutes
            25: 1200, # 20 minutes
            50: 1800, # 30 minutes
            100: 0    # No wait for 100%
        }

    def execute_canary_rollout(self, target_version: str) -> bool:
        """Execute progressive canary rollout"""

        print(f"🐦 Starting canary rollout for {self.rollout_name}")
        print(f"Target version: {target_version}")
        print(f"Traffic stages: {self.traffic_stages}")

        rollout_state = {
            "rollout_name": self.rollout_name,
            "target_version": target_version,
            "start_time": datetime.now().isoformat(),
            "current_stage": 0,
            "status": "in_progress",
            "stages": []
        }

        try:
            for i, traffic_weight in enumerate(self.traffic_stages[:-1]):  # Exclude 100%
                stage_result = self.execute_traffic_stage(
                    traffic_weight,
                    self.analysis_duration[traffic_weight]
                )

                rollout_state["stages"].append(stage_result)
                rollout_state["current_stage"] = i + 1

                if not stage_result["success"]:
                    print(f"❌ Stage {traffic_weight}% failed: {stage_result['reason']}")
                    self.rollback_canary()
                    rollout_state["status"] = "failed"
                    rollout_state["failure_stage"] = traffic_weight
                    return False

                print(f"✅ Stage {traffic_weight}% completed successfully")

            # Final promotion to 100%
            if self.promote_to_full_traffic():
                print("🎉 Canary rollout completed successfully - 100% traffic")
                rollout_state["status"] = "completed"
                rollout_state["completion_time"] = datetime.now().isoformat()
                return True
            else:
                print("❌ Final promotion failed")
                self.rollback_canary()
                rollout_state["status"] = "failed"
                return False

        except Exception as e:
            print(f"❌ Canary rollout failed with exception: {str(e)}")
            self.rollback_canary()
            rollout_state["status"] = "error"
            rollout_state["error"] = str(e)
            return False

        finally:
            self.save_rollout_state(rollout_state)

    def execute_traffic_stage(self, weight: int, duration: int) -> Dict:
        """Execute a single traffic stage"""

        stage_start = datetime.now()
        print(f"🔄 Setting traffic weight to {weight}%")

        # Set traffic weight
        if not self.set_traffic_weight(weight):
            return {
                "weight": weight,
                "success": False,
                "reason": "Failed to set traffic weight",
                "duration": 0
            }

        print(f"📊 Analyzing metrics for {duration} seconds...")
        time.sleep(30)  # Initial stabilization

        # Analyze metrics during the stage
        analysis_result = self.analyze_canary_metrics(weight, duration - 30)

        stage_duration = (datetime.now() - stage_start).total_seconds()

        return {
            "weight": weight,
            "success": analysis_result["success"],
            "reason": analysis_result.get("reason", ""),
            "duration": stage_duration,
            "metrics": analysis_result["metrics"],
            "timestamp": stage_start.isoformat()
        }

    def set_traffic_weight(self, weight: int) -> bool:
        """Set canary traffic weight"""
        try:
            cmd = [
                "kubectl", "argo", "rollouts", "set", "image",
                self.rollout_name, f"backend=ghcr.io/sunday/backend:latest",
                "-n", self.namespace
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"Failed to update rollout: {result.stderr}")
                return False

            # Set the traffic weight
            weight_cmd = [
                "kubectl", "argo", "rollouts", "set", "canary-weight",
                self.rollout_name, str(weight),
                "-n", self.namespace
            ]

            result = subprocess.run(weight_cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            print(f"Error setting traffic weight: {str(e)}")
            return False

    def analyze_canary_metrics(self, weight: int, duration: int) -> Dict:
        """Analyze canary metrics during traffic stage"""

        analysis_start = time.time()
        metrics_history = []

        while time.time() - analysis_start < duration:
            current_metrics = self.collect_current_metrics()
            metrics_history.append({
                "timestamp": time.time(),
                "metrics": current_metrics
            })

            # Real-time anomaly detection
            if self.detect_immediate_issues(current_metrics):
                return {
                    "success": False,
                    "reason": "Immediate issue detected",
                    "metrics": current_metrics
                }

            time.sleep(30)  # Collect metrics every 30 seconds

        # Comprehensive analysis
        analysis_result = self.comprehensive_analysis(metrics_history, weight)

        return analysis_result

    def collect_current_metrics(self) -> Dict:
        """Collect current canary and stable metrics"""

        metrics = {}

        # Success rate
        metrics["canary_success_rate"] = self.query_prometheus(
            'sum(rate(http_requests_total{service="backend-service-canary",status!~"5.."}[2m])) / '
            'sum(rate(http_requests_total{service="backend-service-canary"}[2m]))'
        )

        metrics["stable_success_rate"] = self.query_prometheus(
            'sum(rate(http_requests_total{service="backend-service-stable",status!~"5.."}[2m])) / '
            'sum(rate(http_requests_total{service="backend-service-stable"}[2m]))'
        )

        # Latency (95th percentile)
        metrics["canary_latency_p95"] = self.query_prometheus(
            'histogram_quantile(0.95, '
            'sum(rate(http_request_duration_seconds_bucket{service="backend-service-canary"}[2m])) by (le))'
        ) * 1000

        metrics["stable_latency_p95"] = self.query_prometheus(
            'histogram_quantile(0.95, '
            'sum(rate(http_request_duration_seconds_bucket{service="backend-service-stable"}[2m])) by (le))'
        ) * 1000

        # Memory usage
        metrics["canary_memory_usage"] = self.query_prometheus(
            'avg(container_memory_usage_bytes{pod=~".*canary.*"}) / '
            'avg(container_spec_memory_limit_bytes{pod=~".*canary.*"})'
        )

        # CPU usage
        metrics["canary_cpu_usage"] = self.query_prometheus(
            'avg(rate(container_cpu_usage_seconds_total{pod=~".*canary.*"}[2m])) / '
            'avg(container_spec_cpu_quota{pod=~".*canary.*"}/container_spec_cpu_period{pod=~".*canary.*"})'
        )

        # Business metrics
        metrics["canary_conversion_rate"] = self.query_prometheus(
            'sum(rate(user_conversions_total{service="backend-service-canary"}[5m])) / '
            'sum(rate(user_sessions_total{service="backend-service-canary"}[5m]))'
        )

        metrics["stable_conversion_rate"] = self.query_prometheus(
            'sum(rate(user_conversions_total{service="backend-service-stable"}[5m])) / '
            'sum(rate(user_sessions_total{service="backend-service-stable"}[5m]))'
        )

        return metrics

    def query_prometheus(self, query: str) -> float:
        """Query Prometheus and return numeric result"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data["status"] == "success" and data["data"]["result"]:
                    return float(data["data"]["result"][0]["value"][1])

            return 0.0
        except Exception:
            return 0.0

    def detect_immediate_issues(self, metrics: Dict) -> bool:
        """Detect immediate issues that require rollback"""

        # Critical thresholds
        if metrics.get("canary_success_rate", 1.0) < 0.9:  # Less than 90% success rate
            print(f"❌ Critical: Low success rate {metrics['canary_success_rate']:.3f}")
            return True

        if metrics.get("canary_latency_p95", 0) > 5000:  # More than 5s latency
            print(f"❌ Critical: High latency {metrics['canary_latency_p95']:.0f}ms")
            return True

        if metrics.get("canary_memory_usage", 0) > 0.95:  # More than 95% memory
            print(f"❌ Critical: High memory usage {metrics['canary_memory_usage']:.3f}")
            return True

        return False

    def comprehensive_analysis(self, metrics_history: List[Dict], weight: int) -> Dict:
        """Perform comprehensive analysis of metrics"""

        if not metrics_history:
            return {"success": False, "reason": "No metrics collected"}

        # Calculate averages
        avg_metrics = self.calculate_average_metrics(metrics_history)

        # Performance comparison
        performance_ratio = self.compare_performance(avg_metrics)

        # Trend analysis
        trend_analysis = self.analyze_trends(metrics_history)

        # Business impact assessment
        business_impact = self.assess_business_impact(avg_metrics)

        # Decision logic
        decision = self.make_stage_decision(
            avg_metrics, performance_ratio, trend_analysis, business_impact, weight
        )

        return {
            "success": decision["proceed"],
            "reason": decision["reason"],
            "metrics": avg_metrics,
            "performance_ratio": performance_ratio,
            "trend_analysis": trend_analysis,
            "business_impact": business_impact,
            "confidence_score": decision["confidence"]
        }

    def calculate_average_metrics(self, metrics_history: List[Dict]) -> Dict:
        """Calculate average metrics from history"""
        if not metrics_history:
            return {}

        all_metrics = [entry["metrics"] for entry in metrics_history]
        avg_metrics = {}

        for key in all_metrics[0].keys():
            values = [m.get(key, 0) for m in all_metrics if m.get(key) is not None]
            avg_metrics[key] = sum(values) / len(values) if values else 0

        return avg_metrics

    def compare_performance(self, avg_metrics: Dict) -> Dict:
        """Compare canary vs stable performance"""
        comparison = {}

        # Success rate comparison
        canary_success = avg_metrics.get("canary_success_rate", 0)
        stable_success = avg_metrics.get("stable_success_rate", 0)
        comparison["success_rate_ratio"] = canary_success / stable_success if stable_success > 0 else 0

        # Latency comparison
        canary_latency = avg_metrics.get("canary_latency_p95", 0)
        stable_latency = avg_metrics.get("stable_latency_p95", 0)
        comparison["latency_ratio"] = canary_latency / stable_latency if stable_latency > 0 else 0

        # Conversion rate comparison
        canary_conversion = avg_metrics.get("canary_conversion_rate", 0)
        stable_conversion = avg_metrics.get("stable_conversion_rate", 0)
        comparison["conversion_ratio"] = canary_conversion / stable_conversion if stable_conversion > 0 else 0

        return comparison

    def make_stage_decision(self, metrics: Dict, performance: Dict, trends: Dict,
                           business: Dict, weight: int) -> Dict:
        """Make decision whether to proceed to next stage"""

        confidence = 100
        issues = []

        # Success rate criteria
        if metrics.get("canary_success_rate", 0) < 0.95:
            issues.append("Low success rate")
            confidence -= 30

        if performance.get("success_rate_ratio", 0) < 0.98:  # 2% degradation threshold
            issues.append("Success rate degradation vs stable")
            confidence -= 25

        # Latency criteria
        if performance.get("latency_ratio", 0) > 1.5:  # 50% increase threshold
            issues.append("Significant latency increase")
            confidence -= 20

        # Business metrics
        if performance.get("conversion_ratio", 0) < 0.95:  # 5% conversion drop
            issues.append("Business conversion impact")
            confidence -= 25

        # Trend analysis
        if trends.get("error_rate_trending_up", False):
            issues.append("Error rate trending upward")
            confidence -= 15

        # Resource usage
        if metrics.get("canary_memory_usage", 0) > 0.85:
            issues.append("High memory usage")
            confidence -= 10

        # Decision threshold based on traffic weight
        threshold = 70 - (weight * 0.5)  # Lower threshold for higher traffic

        proceed = confidence >= threshold and len(issues) == 0

        return {
            "proceed": proceed,
            "confidence": confidence,
            "threshold": threshold,
            "reason": "; ".join(issues) if issues else "All metrics within acceptable ranges",
            "issues": issues
        }

    def rollback_canary(self) -> bool:
        """Rollback canary deployment"""
        print("🔄 Rolling back canary deployment...")

        try:
            cmd = [
                "kubectl", "argo", "rollouts", "abort",
                self.rollout_name, "-n", self.namespace
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ Canary rollback completed")
                return True
            else:
                print(f"❌ Rollback failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Rollback error: {str(e)}")
            return False

    def promote_to_full_traffic(self) -> bool:
        """Promote canary to 100% traffic"""
        print("🚀 Promoting canary to 100% traffic...")

        try:
            cmd = [
                "kubectl", "argo", "rollouts", "promote",
                self.rollout_name, "-n", self.namespace
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            print(f"❌ Promotion error: {str(e)}")
            return False

    def save_rollout_state(self, state: Dict):
        """Save rollout state for analysis"""
        filename = f"canary-rollout-{self.rollout_name}-{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"📄 Rollout state saved: {filename}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python canary-traffic-controller.py <rollout-name> <target-version>")
        sys.exit(1)

    rollout_name = sys.argv[1]
    target_version = sys.argv[2]

    controller = CanaryTrafficController(rollout_name)
    success = controller.execute_canary_rollout(target_version)

    if success:
        print("🎉 Canary rollout completed successfully")
        sys.exit(0)
    else:
        print("❌ Canary rollout failed")
        sys.exit(1)
```

---

## Automated Analysis

### Comprehensive Metric Analysis Engine

```python
#!/usr/bin/env python3
# scripts/canary-analysis-engine.py

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional
import time
import json

class CanaryAnalysisEngine:
    def __init__(self):
        self.analysis_window = 300  # 5 minutes
        self.significance_level = 0.05
        self.min_sample_size = 100

        # Metric thresholds
        self.thresholds = {
            "success_rate": {"min": 0.95, "degradation": 0.02},
            "latency_p95": {"max": 2000, "increase": 0.5},  # 50% increase
            "latency_p99": {"max": 5000, "increase": 0.3},  # 30% increase
            "memory_usage": {"max": 0.85},
            "cpu_usage": {"max": 0.8},
            "conversion_rate": {"degradation": 0.05}  # 5% drop
        }

    def perform_comprehensive_analysis(self, canary_data: Dict, stable_data: Dict,
                                     duration: int) -> Dict:
        """Perform comprehensive statistical analysis"""

        print(f"🔬 Performing comprehensive analysis...")

        analysis_result = {
            "timestamp": time.time(),
            "duration": duration,
            "statistical_tests": {},
            "anomaly_detection": {},
            "performance_comparison": {},
            "business_impact": {},
            "recommendation": {},
            "confidence": 0
        }

        # Statistical significance tests
        analysis_result["statistical_tests"] = self.run_statistical_tests(
            canary_data, stable_data
        )

        # Anomaly detection
        analysis_result["anomaly_detection"] = self.detect_anomalies(
            canary_data, stable_data
        )

        # Performance comparison
        analysis_result["performance_comparison"] = self.compare_performance_metrics(
            canary_data, stable_data
        )

        # Business impact assessment
        analysis_result["business_impact"] = self.assess_business_impact(
            canary_data, stable_data
        )

        # Generate recommendation
        analysis_result["recommendation"] = self.generate_recommendation(
            analysis_result
        )

        return analysis_result

    def run_statistical_tests(self, canary_data: Dict, stable_data: Dict) -> Dict:
        """Run statistical significance tests"""

        tests = {}

        # Success rate comparison (proportion test)
        if "success_rate" in canary_data and "success_rate" in stable_data:
            tests["success_rate"] = self.proportion_test(
                canary_data["success_rate"], stable_data["success_rate"]
            )

        # Latency comparison (Mann-Whitney U test)
        if "latency_samples" in canary_data and "latency_samples" in stable_data:
            tests["latency"] = self.mann_whitney_test(
                canary_data["latency_samples"], stable_data["latency_samples"]
            )

        # Error rate comparison
        if "error_rate" in canary_data and "error_rate" in stable_data:
            tests["error_rate"] = self.proportion_test(
                canary_data["error_rate"], stable_data["error_rate"],
                test_type="error_rate"
            )

        return tests

    def proportion_test(self, canary_prop: float, stable_prop: float,
                       test_type: str = "success_rate") -> Dict:
        """Perform two-proportion z-test"""

        # Simulate sample sizes (in real implementation, use actual sample sizes)
        n_canary = 1000
        n_stable = 10000

        x_canary = int(canary_prop * n_canary)
        x_stable = int(stable_prop * n_stable)

        # Combined proportion
        p_combined = (x_canary + x_stable) / (n_canary + n_stable)

        # Standard error
        se = np.sqrt(p_combined * (1 - p_combined) * (1/n_canary + 1/n_stable))

        # Z-statistic
        z_stat = (canary_prop - stable_prop) / se if se > 0 else 0

        # P-value (two-tailed)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

        # Effect size (Cohen's h)
        effect_size = 2 * (np.arcsin(np.sqrt(canary_prop)) - np.arcsin(np.sqrt(stable_prop)))

        significant = p_value < self.significance_level

        return {
            "test_type": "two_proportion_z_test",
            "canary_proportion": canary_prop,
            "stable_proportion": stable_prop,
            "z_statistic": z_stat,
            "p_value": p_value,
            "effect_size": effect_size,
            "significant": significant,
            "interpretation": self.interpret_proportion_test(
                canary_prop, stable_prop, significant, test_type
            )
        }

    def mann_whitney_test(self, canary_samples: List[float],
                         stable_samples: List[float]) -> Dict:
        """Perform Mann-Whitney U test for latency comparison"""

        if len(canary_samples) < self.min_sample_size or len(stable_samples) < self.min_sample_size:
            return {
                "test_type": "mann_whitney_u",
                "error": "Insufficient sample size",
                "significant": False
            }

        statistic, p_value = stats.mannwhitneyu(
            canary_samples, stable_samples, alternative='two-sided'
        )

        # Effect size (rank-biserial correlation)
        n1, n2 = len(canary_samples), len(stable_samples)
        effect_size = 1 - (2 * statistic) / (n1 * n2)

        significant = p_value < self.significance_level

        canary_median = np.median(canary_samples)
        stable_median = np.median(stable_samples)

        return {
            "test_type": "mann_whitney_u",
            "canary_median": canary_median,
            "stable_median": stable_median,
            "u_statistic": statistic,
            "p_value": p_value,
            "effect_size": effect_size,
            "significant": significant,
            "interpretation": self.interpret_latency_test(
                canary_median, stable_median, significant
            )
        }

    def detect_anomalies(self, canary_data: Dict, stable_data: Dict) -> Dict:
        """Detect anomalies using multiple methods"""

        anomalies = {}

        # Threshold-based anomaly detection
        anomalies["threshold_based"] = self.threshold_anomaly_detection(canary_data)

        # Statistical anomaly detection
        anomalies["statistical"] = self.statistical_anomaly_detection(
            canary_data, stable_data
        )

        # Trend-based anomaly detection
        anomalies["trend_based"] = self.trend_anomaly_detection(canary_data)

        return anomalies

    def threshold_anomaly_detection(self, data: Dict) -> Dict:
        """Detect threshold-based anomalies"""

        anomalies = {}

        for metric, value in data.items():
            if metric in self.thresholds:
                threshold_config = self.thresholds[metric]

                if "min" in threshold_config and value < threshold_config["min"]:
                    anomalies[metric] = {
                        "type": "below_minimum",
                        "value": value,
                        "threshold": threshold_config["min"],
                        "severity": "high"
                    }

                if "max" in threshold_config and value > threshold_config["max"]:
                    anomalies[metric] = {
                        "type": "above_maximum",
                        "value": value,
                        "threshold": threshold_config["max"],
                        "severity": "high"
                    }

        return anomalies

    def compare_performance_metrics(self, canary_data: Dict, stable_data: Dict) -> Dict:
        """Compare performance metrics between canary and stable"""

        comparison = {}

        for metric in ["success_rate", "latency_p95", "latency_p99", "conversion_rate"]:
            if metric in canary_data and metric in stable_data:
                canary_val = canary_data[metric]
                stable_val = stable_data[metric]

                if stable_val > 0:
                    ratio = canary_val / stable_val
                    percentage_change = ((canary_val - stable_val) / stable_val) * 100
                else:
                    ratio = float('inf') if canary_val > 0 else 1
                    percentage_change = 0

                comparison[metric] = {
                    "canary_value": canary_val,
                    "stable_value": stable_val,
                    "ratio": ratio,
                    "percentage_change": percentage_change,
                    "assessment": self.assess_metric_change(metric, ratio, percentage_change)
                }

        return comparison

    def assess_metric_change(self, metric: str, ratio: float,
                           percentage_change: float) -> Dict:
        """Assess the significance of a metric change"""

        assessment = {"severity": "none", "description": ""}

        if metric == "success_rate":
            if ratio < 0.95:  # 5% degradation
                assessment = {"severity": "critical", "description": "Significant success rate degradation"}
            elif ratio < 0.98:  # 2% degradation
                assessment = {"severity": "warning", "description": "Moderate success rate degradation"}
            else:
                assessment = {"severity": "none", "description": "Success rate within acceptable range"}

        elif metric in ["latency_p95", "latency_p99"]:
            if ratio > 2.0:  # 100% increase
                assessment = {"severity": "critical", "description": "Severe latency increase"}
            elif ratio > 1.5:  # 50% increase
                assessment = {"severity": "warning", "description": "Significant latency increase"}
            elif ratio > 1.2:  # 20% increase
                assessment = {"severity": "info", "description": "Moderate latency increase"}
            else:
                assessment = {"severity": "none", "description": "Latency within acceptable range"}

        elif metric == "conversion_rate":
            if ratio < 0.9:  # 10% drop
                assessment = {"severity": "critical", "description": "Severe conversion rate drop"}
            elif ratio < 0.95:  # 5% drop
                assessment = {"severity": "warning", "description": "Significant conversion rate drop"}
            else:
                assessment = {"severity": "none", "description": "Conversion rate acceptable"}

        return assessment

    def generate_recommendation(self, analysis_result: Dict) -> Dict:
        """Generate deployment recommendation based on analysis"""

        confidence = 100
        issues = []
        critical_issues = []

        # Check statistical tests
        for test_name, test_result in analysis_result["statistical_tests"].items():
            if test_result.get("significant", False):
                interpretation = test_result.get("interpretation", {})
                if interpretation.get("recommendation") == "rollback":
                    critical_issues.append(f"Statistical significance in {test_name}")
                    confidence -= 30

        # Check anomalies
        threshold_anomalies = analysis_result["anomaly_detection"].get("threshold_based", {})
        for metric, anomaly in threshold_anomalies.items():
            if anomaly.get("severity") == "high":
                critical_issues.append(f"Threshold anomaly: {metric}")
                confidence -= 25

        # Check performance comparisons
        for metric, comparison in analysis_result["performance_comparison"].items():
            assessment = comparison.get("assessment", {})
            if assessment.get("severity") == "critical":
                critical_issues.append(f"Critical performance issue: {metric}")
                confidence -= 20
            elif assessment.get("severity") == "warning":
                issues.append(f"Performance warning: {metric}")
                confidence -= 10

        # Generate recommendation
        if critical_issues:
            recommendation = "rollback"
            reason = f"Critical issues detected: {'; '.join(critical_issues)}"
        elif confidence < 70:
            recommendation = "hold"
            reason = f"Multiple concerns: {'; '.join(issues)}"
        else:
            recommendation = "proceed"
            reason = "All metrics within acceptable ranges"

        return {
            "action": recommendation,
            "confidence": max(0, confidence),
            "reason": reason,
            "critical_issues": critical_issues,
            "warnings": issues
        }

    def interpret_proportion_test(self, canary_prop: float, stable_prop: float,
                                significant: bool, test_type: str) -> Dict:
        """Interpret proportion test results"""

        interpretation = {}

        if test_type == "success_rate":
            if significant and canary_prop < stable_prop:
                interpretation = {
                    "result": "canary_worse",
                    "description": "Canary has significantly lower success rate",
                    "recommendation": "rollback"
                }
            elif significant and canary_prop > stable_prop:
                interpretation = {
                    "result": "canary_better",
                    "description": "Canary has significantly higher success rate",
                    "recommendation": "proceed"
                }
            else:
                interpretation = {
                    "result": "no_difference",
                    "description": "No significant difference in success rates",
                    "recommendation": "proceed"
                }

        return interpretation

    def interpret_latency_test(self, canary_median: float, stable_median: float,
                             significant: bool) -> Dict:
        """Interpret latency test results"""

        if significant and canary_median > stable_median:
            return {
                "result": "canary_slower",
                "description": f"Canary significantly slower ({canary_median:.0f}ms vs {stable_median:.0f}ms)",
                "recommendation": "investigate" if canary_median / stable_median < 1.5 else "rollback"
            }
        elif significant and canary_median < stable_median:
            return {
                "result": "canary_faster",
                "description": f"Canary significantly faster ({canary_median:.0f}ms vs {stable_median:.0f}ms)",
                "recommendation": "proceed"
            }
        else:
            return {
                "result": "no_difference",
                "description": "No significant difference in latency",
                "recommendation": "proceed"
            }

if __name__ == "__main__":
    # Example usage
    engine = CanaryAnalysisEngine()

    # Mock data for testing
    canary_data = {
        "success_rate": 0.94,
        "latency_p95": 1500,
        "conversion_rate": 0.12
    }

    stable_data = {
        "success_rate": 0.96,
        "latency_p95": 1200,
        "conversion_rate": 0.13
    }

    result = engine.perform_comprehensive_analysis(canary_data, stable_data, 300)
    print(json.dumps(result, indent=2))
```

---

*This Canary Deployment Framework provides intelligent, data-driven progressive rollouts with comprehensive analysis and automated decision-making for Sunday.com's high-risk deployments.*

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: Deployment Specialist Team*