# Grafana Dashboards for Maestro ML Platform

This directory contains Grafana dashboard definitions for monitoring the Maestro ML Platform.

## Dashboards

### 1. Maestro ML Platform - Overview
**File:** `maestro-ml-overview.json`

Comprehensive platform health and activity overview.

**Panels:**
- HTTP Request Rate
- HTTP Request Latency (p95)
- Total Models
- Total Experiments (24h)
- API Error Rate
- Rate Limit Exceeded Events
- Model Operations by Type
- Feature Discovery Duration
- Tenant Quota Usage (with alert)

**Key Metrics:**
- Overall platform health
- Traffic patterns
- Error rates and availability
- Resource usage warnings

---

### 2. ML Operations
**File:** `ml-operations.json`

Detailed view of machine learning operations and model lifecycle.

**Panels:**
- Model Operations Rate (create, update, delete, deploy)
- Models by Tenant
- Model Size Distribution (p50, p95)
- Experiments by Status
- Training Job Duration (p95)
- Model Card Generations
- Model Operations Summary Table

**Key Metrics:**
- Model creation and deployment activity
- Training performance
- Model size trends
- Experiment success rates

---

### 3. Tenant Management
**File:** `tenant-management.json`

Multi-tenancy monitoring and quota management.

**Panels:**
- Quota Usage by Resource Type
- Active Users (total)
- Total Tenants
- Active Users by Tenant
- Tenant Resource Usage Table
- Models per Tenant
- API Requests by Tenant

**Key Metrics:**
- Quota utilization warnings (80% threshold)
- Tenant activity levels
- Resource consumption patterns
- Fair usage monitoring

**Features:**
- Tenant variable for filtering
- Quota usage alerts

---

### 4. API Performance
**File:** `api-performance.json`

API performance, latency, and error tracking.

**Panels:**
- Request Rate by Endpoint
- Request Latency by Percentile (p50, p95, p99)
- Error Rate by Endpoint (with alert)
- Requests in Progress
- Status Code Distribution
- Rate Limit Events
- Endpoint Performance Summary Table

**Key Metrics:**
- API responsiveness (p95, p99 latency)
- Error rates and types
- Rate limiting effectiveness
- Endpoint-level performance

**Alerts:**
- High error rate (>0.1 errors/sec)

---

## Installation

### Option 1: Grafana UI

1. Open Grafana (http://localhost:3000)
2. Navigate to **Dashboards** → **Import**
3. Upload JSON file or paste JSON content
4. Select Prometheus data source
5. Click **Import**

### Option 2: Provisioning (Recommended)

Add to Grafana provisioning configuration:

```yaml
# /etc/grafana/provisioning/dashboards/maestro-ml.yaml
apiVersion: 1

providers:
  - name: 'Maestro ML'
    orgId: 1
    folder: 'Maestro ML Platform'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /path/to/maestro_ml/monitoring/grafana/dashboards
```

### Option 3: Kubernetes ConfigMap

```bash
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/ \
  --namespace=monitoring
```

---

## Data Source Configuration

All dashboards require a Prometheus data source named **"Prometheus"**.

**Prometheus Configuration:**
- URL: http://prometheus:9090 (Kubernetes service)
- Access: Server (default)
- Scrape Interval: 15s

**Metrics Endpoint:**
```
http://maestro-api:8000/metrics
```

---

## Alert Configuration

### Configured Alerts

1. **Tenant Quota Warning** (Overview dashboard)
   - Condition: Quota usage > 80%
   - Evaluates: maestro_tenant_quota_usage_ratio

2. **High Error Rate Alert** (API Performance dashboard)
   - Condition: Error rate > 0.1 errors/sec
   - Evaluates: maestro_api_errors_total

### Setting Up Notifications

1. Configure notification channel in Grafana
2. Edit dashboard alert rules
3. Add notification channel to alert

Example notification channels:
- Email
- Slack
- PagerDuty
- Webhook

---

## Metrics Reference

### HTTP Metrics
- `maestro_http_requests_total` - Total HTTP requests
- `maestro_http_request_duration_seconds` - Request latency histogram
- `maestro_http_requests_in_progress` - In-flight requests
- `maestro_api_errors_total` - API errors by type

### ML Metrics
- `maestro_ml_models_total` - Total registered models
- `maestro_ml_model_operations_total` - Model operations counter
- `maestro_ml_model_size_bytes` - Model size histogram
- `maestro_ml_experiments_total` - Total experiments
- `maestro_ml_training_duration_seconds` - Training duration

### Feature Discovery
- `maestro_feature_discovery_operations_total` - Discovery operations
- `maestro_feature_discovery_duration_seconds` - Discovery duration

### Model Cards
- `maestro_model_card_generations_total` - Card generations

### Tenant Metrics
- `maestro_tenant_quota_usage_ratio` - Quota usage (0-1)
- `maestro_tenant_active_users` - Active user count

### Rate Limiting
- `maestro_rate_limit_exceeded_total` - Rate limit violations

---

## Dashboard Maintenance

### Updating Dashboards

1. Edit dashboard in Grafana UI
2. Export JSON (Share → Export → Save to file)
3. Copy JSON to appropriate file in this directory
4. Commit to version control

### Best Practices

- Use template variables for tenant filtering
- Set appropriate refresh intervals (30s-1m)
- Configure alerts with reasonable thresholds
- Include both high-level and detailed views
- Use appropriate time ranges (Last 1h, Last 24h)
- Group related panels logically

---

## Troubleshooting

### No Data in Panels

1. Verify Prometheus is scraping metrics endpoint:
   ```bash
   curl http://maestro-api:8000/metrics
   ```

2. Check Prometheus targets:
   ```
   http://prometheus:9090/targets
   ```

3. Verify metric names match:
   ```promql
   {__name__=~"maestro.*"}
   ```

### High Cardinality Warnings

Some metrics use labels like `tenant_id` and `endpoint`. Monitor cardinality:

```promql
count({__name__=~"maestro.*"}) by (__name__)
```

Limit to active tenants if needed.

### Performance Issues

- Reduce refresh rate for complex dashboards
- Use recording rules for expensive queries
- Limit time range for high-resolution data
- Use `$__interval` variable in queries

---

## Recording Rules (Optional)

For better performance, create Prometheus recording rules:

```yaml
# prometheus-rules.yaml
groups:
  - name: maestro_ml
    interval: 30s
    rules:
      - record: maestro:http_request_rate:5m
        expr: sum by (endpoint) (rate(maestro_http_requests_total[5m]))

      - record: maestro:http_request_latency_p95:5m
        expr: histogram_quantile(0.95, sum(rate(maestro_http_request_duration_seconds_bucket[5m])) by (le, endpoint))
```

---

## Additional Resources

- [Prometheus Query Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
