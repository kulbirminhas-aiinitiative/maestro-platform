# Sunday.com Monitoring and Alerting Setup

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Architecture](#monitoring-architecture)
3. [Metrics Collection](#metrics-collection)
4. [Alerting Framework](#alerting-framework)
5. [Dashboard Configuration](#dashboard-configuration)
6. [Log Management](#log-management)
7. [Performance Monitoring](#performance-monitoring)
8. [Security Monitoring](#security-monitoring)
9. [Business Metrics](#business-metrics)
10. [Incident Response](#incident-response)

---

## Overview

This document outlines the comprehensive monitoring and alerting setup for Sunday.com, designed to provide full observability across the entire platform stack. The monitoring system ensures early detection of issues, performance optimization, and reliable incident response.

### Monitoring Objectives

- **Availability**: 99.9% uptime monitoring with <2 minute detection
- **Performance**: Sub-200ms response time tracking
- **Security**: Real-time threat detection and compliance monitoring
- **Business**: User engagement and revenue impact metrics
- **Infrastructure**: Resource utilization and capacity planning

### Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│  Collection Layer                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │   Prometheus    │ │   Filebeat      │ │   Jaeger        │  │
│  │   (Metrics)     │ │   (Logs)        │ │   (Traces)      │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│  Storage Layer                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │   Prometheus    │ │ Elasticsearch   │ │   Jaeger        │  │
│  │   (TSDB)        │ │   (Log Store)   │ │  (Trace Store)  │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│  Visualization Layer                                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │    Grafana      │ │     Kibana      │ │  Jaeger UI      │  │
│  │  (Dashboards)   │ │  (Log Analysis) │ │ (Trace Analysis)│  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│  Alerting Layer                                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │         AlertManager + PagerDuty + Slack                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Monitoring Architecture

### 1. Prometheus Configuration

```yaml
# k8s/monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
      external_labels:
        cluster: 'sunday-production'
        environment: 'production'

    rule_files:
      - "/etc/prometheus/rules/*.yml"

    scrape_configs:
    # Application metrics
    - job_name: 'sunday-backend'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - sunday-production
          - sunday-staging
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: backend
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

    # Infrastructure metrics
    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)

    # Database metrics
    - job_name: 'postgres-exporter'
      static_configs:
      - targets: ['postgres-exporter:9187']

    - job_name: 'redis-exporter'
      static_configs:
      - targets: ['redis-exporter:9121']

    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:v2.40.0
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config-volume
          mountPath: /etc/prometheus/
        - name: storage-volume
          mountPath: /prometheus/
        args:
        - '--config.file=/etc/prometheus/prometheus.yml'
        - '--storage.tsdb.path=/prometheus/'
        - '--web.console.libraries=/etc/prometheus/console_libraries'
        - '--web.console.templates=/etc/prometheus/consoles'
        - '--storage.tsdb.retention.time=30d'
        - '--web.enable-lifecycle'
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
      volumes:
      - name: config-volume
        configMap:
          name: prometheus-config
      - name: storage-volume
        persistentVolumeClaim:
          claimName: prometheus-storage
```

### 2. Grafana Setup

```yaml
# k8s/monitoring/grafana-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:9.3.0
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-secrets
              key: admin-password
        - name: GF_INSTALL_PLUGINS
          value: "grafana-piechart-panel,grafana-worldmap-panel"
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        - name: grafana-config
          mountPath: /etc/grafana/provisioning
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: grafana-storage
        persistentVolumeClaim:
          claimName: grafana-storage
      - name: grafana-config
        configMap:
          name: grafana-config

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
  namespace: monitoring
data:
  datasource.yml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      access: proxy
      url: http://prometheus:9090
      isDefault: true
    - name: Elasticsearch
      type: elasticsearch
      access: proxy
      url: http://elasticsearch:9200
      database: "logstash-*"
```

---

## Metrics Collection

### 1. Application Metrics

#### Backend Service Metrics

```javascript
// backend/src/middleware/metrics.js
const prometheus = require('prom-client');

// Create metrics registry
const register = new prometheus.Registry();

// Application metrics
const httpRequestDuration = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10]
});

const httpRequestTotal = new prometheus.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

const databaseConnectionPool = new prometheus.Gauge({
  name: 'database_connection_pool_size',
  help: 'Current database connection pool size',
  labelNames: ['database', 'state']
});

const activeUsers = new prometheus.Gauge({
  name: 'active_users_total',
  help: 'Number of currently active users',
  labelNames: ['workspace']
});

const redisOperations = new prometheus.Counter({
  name: 'redis_operations_total',
  help: 'Total Redis operations',
  labelNames: ['operation', 'status']
});

// Register metrics
register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestTotal);
register.registerMetric(databaseConnectionPool);
register.registerMetric(activeUsers);
register.registerMetric(redisOperations);

// Middleware to collect HTTP metrics
const metricsMiddleware = (req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const route = req.route ? req.route.path : req.path;

    httpRequestDuration
      .labels(req.method, route, res.statusCode)
      .observe(duration);

    httpRequestTotal
      .labels(req.method, route, res.statusCode)
      .inc();
  });

  next();
};

// Metrics endpoint
const metricsHandler = async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (err) {
    res.status(500).end(err);
  }
};

module.exports = {
  metricsMiddleware,
  metricsHandler,
  register,
  metrics: {
    httpRequestDuration,
    httpRequestTotal,
    databaseConnectionPool,
    activeUsers,
    redisOperations
  }
};
```

#### Database Metrics

```yaml
# k8s/monitoring/postgres-exporter.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
    spec:
      containers:
      - name: postgres-exporter
        image: prometheuscommunity/postgres-exporter:v0.11.1
        ports:
        - containerPort: 9187
        env:
        - name: DATA_SOURCE_NAME
          valueFrom:
            secretKeyRef:
              name: postgres-monitoring-secrets
              key: connection-string
        - name: PG_EXPORTER_EXTEND_QUERY_PATH
          value: "/etc/postgres_exporter/queries.yaml"
        volumeMounts:
        - name: queries
          mountPath: /etc/postgres_exporter
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      volumes:
      - name: queries
        configMap:
          name: postgres-exporter-queries

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-exporter-queries
  namespace: monitoring
data:
  queries.yaml: |
    pg_database:
      query: "SELECT pg_database.datname, pg_database_size(pg_database.datname) as size FROM pg_database"
      master: true
      metrics:
        - datname:
            usage: "LABEL"
            description: "Name of the database"
        - size:
            usage: "GAUGE"
            description: "Disk space used by the database"

    pg_stat_user_tables:
      query: "SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup FROM pg_stat_user_tables"
      master: true
      metrics:
        - schemaname:
            usage: "LABEL"
            description: "Name of the schema"
        - tablename:
            usage: "LABEL"
            description: "Name of the table"
        - n_tup_ins:
            usage: "COUNTER"
            description: "Number of rows inserted"
        - n_tup_upd:
            usage: "COUNTER"
            description: "Number of rows updated"
        - n_tup_del:
            usage: "COUNTER"
            description: "Number of rows deleted"
        - n_live_tup:
            usage: "GAUGE"
            description: "Number of live rows"
        - n_dead_tup:
            usage: "GAUGE"
            description: "Number of dead rows"
```

### 2. Infrastructure Metrics

#### Node Exporter Configuration

```yaml
# k8s/monitoring/node-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.5.0
        ports:
        - containerPort: 9100
        args:
        - '--path.rootfs=/host'
        - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
      tolerations:
      - operator: Exists
```

---

## Alerting Framework

### 1. AlertManager Configuration

```yaml
# k8s/monitoring/alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.sendgrid.net:587'
      smtp_from: 'alerts@sunday.com'
      smtp_auth_username: 'apikey'
      smtp_auth_password: '${SENDGRID_API_KEY}'

    templates:
    - '/etc/alertmanager/templates/*.tmpl'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'default'
      routes:
      # Critical alerts go to PagerDuty
      - match:
          severity: critical
        receiver: 'pagerduty-critical'
        group_wait: 0s
        group_interval: 5m
        repeat_interval: 1h

      # High severity alerts go to Slack
      - match:
          severity: warning
        receiver: 'slack-warnings'
        group_interval: 5m
        repeat_interval: 4h

    receivers:
    - name: 'default'
      email_configs:
      - to: 'devops@sunday.com'
        subject: 'Sunday.com Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Environment: {{ .Labels.environment }}
          Severity: {{ .Labels.severity }}
          {{ end }}

    - name: 'pagerduty-critical'
      pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        severity: '{{ .CommonLabels.severity }}'

    - name: 'slack-warnings'
      slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'
        title: 'Sunday.com Alert'
        text: |
          {{ range .Alerts }}
          *Alert:* {{ .Annotations.summary }}
          *Environment:* {{ .Labels.environment }}
          *Severity:* {{ .Labels.severity }}
          *Description:* {{ .Annotations.description }}
          {{ end }}

    inhibit_rules:
    - source_match:
        severity: 'critical'
      target_match:
        severity: 'warning'
      equal: ['alertname', 'instance']
```

### 2. Prometheus Alert Rules

```yaml
# k8s/monitoring/alert-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: monitoring
data:
  application.yml: |
    groups:
    - name: application.rules
      rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.instance }}"

      # High response time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s for {{ $labels.instance }}"

      # Database connection pool exhaustion
      - alert: DatabaseConnectionPoolHigh
        expr: database_connection_pool_size{state="active"} / database_connection_pool_size{state="total"} > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool usage high"
          description: "Connection pool usage is {{ $value | humanizePercentage }} for {{ $labels.database }}"

      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} service is down for {{ $labels.instance }}"

  infrastructure.yml: |
    groups:
    - name: infrastructure.rules
      rules:
      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}% for {{ $labels.instance }}"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}% for {{ $labels.instance }}"

      # Disk space low
      - alert: DiskSpaceLow
        expr: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low"
          description: "Disk space usage is {{ $value }}% for {{ $labels.instance }} on {{ $labels.mountpoint }}"

      # Pod crash looping
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod is crash looping"
          description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"

  database.yml: |
    groups:
    - name: database.rules
      rules:
      # Database is down
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
          description: "PostgreSQL database is down for {{ $labels.instance }}"

      # High database connections
      - alert: HighDatabaseConnections
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connections"
          description: "Database connection usage is {{ $value | humanizePercentage }} for {{ $labels.instance }}"

      # Slow queries
      - alert: SlowQueries
        expr: pg_stat_activity_max_tx_duration > 300
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "Longest running query is {{ $value }}s for {{ $labels.instance }}"

      # Replication lag
      - alert: ReplicationLag
        expr: pg_replication_lag > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database replication lag"
          description: "Replication lag is {{ $value }}s for {{ $labels.instance }}"
```

---

## Dashboard Configuration

### 1. Application Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "Sunday.com Application Dashboard",
    "description": "Main application metrics and performance indicators",
    "tags": ["sunday", "application"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{route}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests/sec",
            "min": 0
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "99th percentile"
          }
        ],
        "yAxes": [
          {
            "label": "Response Time (s)",
            "min": 0
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 0
        }
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 5}
              ]
            }
          }
        },
        "gridPos": {
          "h": 4,
          "w": 6,
          "x": 0,
          "y": 8
        }
      },
      {
        "id": 4,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(active_users_total)",
            "legendFormat": "Active Users"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "short"
          }
        },
        "gridPos": {
          "h": 4,
          "w": 6,
          "x": 6,
          "y": 8
        }
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### 2. Infrastructure Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "Sunday.com Infrastructure Dashboard",
    "description": "Infrastructure and Kubernetes metrics",
    "tags": ["sunday", "infrastructure", "kubernetes"],
    "panels": [
      {
        "id": 1,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{instance}}"
          }
        ],
        "yAxes": [
          {
            "label": "CPU Usage %",
            "min": 0,
            "max": 100
          }
        ]
      },
      {
        "id": 2,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "{{instance}}"
          }
        ],
        "yAxes": [
          {
            "label": "Memory Usage %",
            "min": 0,
            "max": 100
          }
        ]
      },
      {
        "id": 3,
        "title": "Pod Status",
        "type": "table",
        "targets": [
          {
            "expr": "kube_pod_status_phase",
            "legendFormat": "",
            "format": "table"
          }
        ],
        "transformations": [
          {
            "id": "organize",
            "options": {
              "excludeByName": {
                "__name__": true,
                "job": true
              }
            }
          }
        ]
      }
    ]
  }
}
```

---

## Log Management

### 1. Elasticsearch Configuration

```yaml
# k8s/monitoring/elasticsearch.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: monitoring
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        ports:
        - containerPort: 9200
        - containerPort: 9300
        env:
        - name: cluster.name
          value: "sunday-logs"
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch"
        - name: cluster.initial_master_nodes
          value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
        - name: ES_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
        - name: xpack.security.enabled
          value: "false"
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
        resources:
          requests:
            cpu: 1
            memory: 4Gi
          limits:
            cpu: 2
            memory: 4Gi
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

### 2. Filebeat Configuration

```yaml
# k8s/monitoring/filebeat.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: monitoring
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*sunday*.log
      processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/log/containers/"

    - type: log
      paths:
        - /var/log/nginx/access.log
        - /var/log/nginx/error.log
      fields:
        service: nginx
        environment: production

    processors:
    - add_host_metadata:
        when.not.contains.tags: forwarded
    - add_docker_metadata: ~
    - add_kubernetes_metadata: ~

    output.elasticsearch:
      hosts: ["elasticsearch:9200"]
      index: "filebeat-sunday-%{+yyyy.MM.dd}"

    logging.level: info
    logging.to_files: true
    logging.files:
      path: /var/log/filebeat
      name: filebeat
      keepfiles: 7
      permissions: 0644

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
    spec:
      serviceAccount: filebeat
      terminationGracePeriodSeconds: 30
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:8.5.0
        args: [
          "-c", "/etc/filebeat.yml",
          "-e",
        ]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - name: config
          mountPath: /etc/filebeat.yml
          readOnly: true
          subPath: filebeat.yml
        - name: data
          mountPath: /usr/share/filebeat/data
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 200Mi
          limits:
            cpu: 200m
            memory: 400Mi
      volumes:
      - name: config
        configMap:
          defaultMode: 0600
          name: filebeat-config
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
      - name: data
        hostPath:
          path: /var/lib/filebeat-data
          type: DirectoryOrCreate
```

---

## Performance Monitoring

### 1. Application Performance Monitoring

```javascript
// backend/src/middleware/apm.js
const apm = require('elastic-apm-node');

// Initialize APM
const apmAgent = apm.start({
  serviceName: 'sunday-backend',
  serviceVersion: process.env.APP_VERSION || 'unknown',
  environment: process.env.NODE_ENV || 'development',
  serverUrl: process.env.ELASTIC_APM_SERVER_URL,
  secretToken: process.env.ELASTIC_APM_SECRET_TOKEN,
  captureBody: 'errors',
  errorOnAbortedRequests: false,
  captureErrorLogStackTraces: 'always'
});

// Custom performance metrics
class PerformanceMonitor {
  static trackDatabaseQuery(operation, duration, success) {
    apm.setCustomContext({
      database: {
        operation,
        duration,
        success
      }
    });
  }

  static trackExternalAPI(service, endpoint, duration, statusCode) {
    apm.setCustomContext({
      external_api: {
        service,
        endpoint,
        duration,
        status_code: statusCode
      }
    });
  }

  static trackBusinessMetric(metric, value, labels = {}) {
    apm.setCustomContext({
      business_metrics: {
        metric,
        value,
        labels
      }
    });
  }
}

module.exports = { apmAgent, PerformanceMonitor };
```

### 2. Frontend Performance Monitoring

```javascript
// frontend/src/utils/performance.js
class FrontendPerformanceMonitor {
  constructor() {
    this.apiUrl = process.env.REACT_APP_API_URL;
    this.sessionId = this.generateSessionId();
  }

  // Track page load performance
  trackPageLoad(pageName) {
    if (window.performance && window.performance.timing) {
      const timing = window.performance.timing;
      const loadTime = timing.loadEventEnd - timing.navigationStart;
      const domContentLoaded = timing.domContentLoadedEventEnd - timing.navigationStart;

      this.sendMetric('page_load', {
        page: pageName,
        load_time: loadTime,
        dom_content_loaded: domContentLoaded,
        session_id: this.sessionId
      });
    }
  }

  // Track user interactions
  trackUserInteraction(action, component, duration = null) {
    this.sendMetric('user_interaction', {
      action,
      component,
      duration,
      timestamp: Date.now(),
      session_id: this.sessionId
    });
  }

  // Track API call performance
  trackAPICall(endpoint, method, duration, statusCode) {
    this.sendMetric('api_call', {
      endpoint,
      method,
      duration,
      status_code: statusCode,
      session_id: this.sessionId
    });
  }

  // Send metrics to backend
  async sendMetric(type, data) {
    try {
      await fetch(`${this.apiUrl}/metrics/frontend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          type,
          data,
          timestamp: Date.now(),
          user_agent: navigator.userAgent,
          url: window.location.href
        })
      });
    } catch (error) {
      console.warn('Failed to send performance metric:', error);
    }
  }

  generateSessionId() {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
  }
}

export default new FrontendPerformanceMonitor();
```

---

## Security Monitoring

### 1. Security Event Detection

```yaml
# k8s/monitoring/security-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-alert-rules
  namespace: monitoring
data:
  security.yml: |
    groups:
    - name: security.rules
      rules:
      # Failed login attempts
      - alert: HighFailedLoginAttempts
        expr: rate(auth_login_attempts_total{status="failed"}[5m]) > 10
        for: 2m
        labels:
          severity: warning
          category: security
        annotations:
          summary: "High number of failed login attempts"
          description: "{{ $value }} failed login attempts per second from {{ $labels.source_ip }}"

      # Suspicious API activity
      - alert: SuspiciousAPIActivity
        expr: rate(http_requests_total{status_code=~"4.."}[5m]) > 50
        for: 5m
        labels:
          severity: warning
          category: security
        annotations:
          summary: "Suspicious API activity detected"
          description: "High rate of 4xx responses: {{ $value }} requests/sec"

      # Unauthorized access attempts
      - alert: UnauthorizedAccess
        expr: rate(auth_authorization_failures_total[5m]) > 5
        for: 2m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Unauthorized access attempts"
          description: "{{ $value }} authorization failures per second"

      # Data export anomaly
      - alert: DataExportAnomaly
        expr: rate(data_export_requests_total[5m]) > rate(data_export_requests_total[1h]) * 5
        for: 1m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Unusual data export activity"
          description: "Data export rate is 5x higher than usual"
```

### 2. Compliance Monitoring

```javascript
// backend/src/monitoring/compliance.js
const { metrics } = require('../middleware/metrics');

class ComplianceMonitor {
  constructor() {
    this.auditEvents = new metrics.Counter({
      name: 'audit_events_total',
      help: 'Total audit events',
      labelNames: ['event_type', 'user_id', 'resource_type', 'action']
    });

    this.dataAccess = new metrics.Counter({
      name: 'data_access_total',
      help: 'Total data access events',
      labelNames: ['user_id', 'resource_id', 'access_type']
    });

    this.privacyRequests = new metrics.Counter({
      name: 'privacy_requests_total',
      help: 'Total privacy-related requests',
      labelNames: ['request_type', 'status']
    });
  }

  trackAuditEvent(eventType, userId, resourceType, action, details = {}) {
    this.auditEvents.labels(eventType, userId, resourceType, action).inc();

    // Log detailed audit event
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      event_type: eventType,
      user_id: userId,
      resource_type: resourceType,
      action: action,
      details: details,
      level: 'audit'
    }));
  }

  trackDataAccess(userId, resourceId, accessType) {
    this.dataAccess.labels(userId, resourceId, accessType).inc();
  }

  trackPrivacyRequest(requestType, status) {
    this.privacyRequests.labels(requestType, status).inc();
  }

  // GDPR compliance tracking
  trackGDPREvent(userId, eventType, details) {
    this.trackAuditEvent('gdpr', userId, 'personal_data', eventType, {
      ...details,
      regulation: 'GDPR',
      compliance_framework: 'EU'
    });
  }
}

module.exports = new ComplianceMonitor();
```

---

## Business Metrics

### 1. User Engagement Metrics

```javascript
// backend/src/monitoring/business.js
const { metrics } = require('../middleware/metrics');

class BusinessMetrics {
  constructor() {
    this.userRegistrations = new metrics.Counter({
      name: 'user_registrations_total',
      help: 'Total user registrations',
      labelNames: ['source', 'plan_type']
    });

    this.workspaceActivity = new metrics.Gauge({
      name: 'workspace_activity_score',
      help: 'Workspace activity score',
      labelNames: ['workspace_id']
    });

    this.featureUsage = new metrics.Counter({
      name: 'feature_usage_total',
      help: 'Feature usage counter',
      labelNames: ['feature', 'user_type']
    });

    this.revenueMetrics = new metrics.Gauge({
      name: 'revenue_metrics',
      help: 'Revenue-related metrics',
      labelNames: ['metric_type', 'period']
    });
  }

  trackUserRegistration(source, planType) {
    this.userRegistrations.labels(source, planType).inc();
  }

  updateWorkspaceActivity(workspaceId, score) {
    this.workspaceActivity.labels(workspaceId).set(score);
  }

  trackFeatureUsage(feature, userType) {
    this.featureUsage.labels(feature, userType).inc();
  }

  updateRevenueMetric(metricType, period, value) {
    this.revenueMetrics.labels(metricType, period).set(value);
  }

  // Track conversion funnel
  trackConversionEvent(userId, event, metadata = {}) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      user_id: userId,
      event_type: 'conversion',
      event: event,
      metadata: metadata,
      level: 'business'
    }));
  }
}

module.exports = new BusinessMetrics();
```

---

## Incident Response

### 1. Incident Response Workflow

```bash
#!/bin/bash
# scripts/incident-response.sh

SEVERITY=${1:-"unknown"}
DESCRIPTION=${2:-"Incident detected by monitoring"}
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"

echo "🚨 INCIDENT RESPONSE INITIATED"
echo "Incident ID: $INCIDENT_ID"
echo "Severity: $SEVERITY"
echo "Description: $DESCRIPTION"

# Create incident in PagerDuty
curl -X POST \
  -H "Authorization: Token token=$PAGERDUTY_API_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.pagerduty.com/incidents \
  -d "{
    \"incident\": {
      \"type\": \"incident\",
      \"title\": \"$DESCRIPTION\",
      \"service\": {
        \"id\": \"$PAGERDUTY_SERVICE_ID\",
        \"type\": \"service_reference\"
      },
      \"priority\": {
        \"id\": \"$PAGERDUTY_PRIORITY_ID\",
        \"type\": \"priority_reference\"
      },
      \"urgency\": \"high\",
      \"incident_key\": \"$INCIDENT_ID\"
    }
  }"

# Notify Slack
curl -X POST -H 'Content-type: application/json' \
  --data "{
    \"text\":\"🚨 INCIDENT: $INCIDENT_ID\",
    \"attachments\":[{
      \"color\":\"danger\",
      \"fields\":[{
        \"title\":\"Severity\",
        \"value\":\"$SEVERITY\",
        \"short\":true
      },{
        \"title\":\"Description\",
        \"value\":\"$DESCRIPTION\",
        \"short\":false
      },{
        \"title\":\"Time\",
        \"value\":\"$(date)\",
        \"short\":true
      }]
    }]
  }" \
  $SLACK_INCIDENT_WEBHOOK

# Create incident directory and initial report
mkdir -p "incidents/$INCIDENT_ID"
cat > "incidents/$INCIDENT_ID/incident-report.md" << EOF
# Incident Report: $INCIDENT_ID

**Severity**: $SEVERITY
**Start Time**: $(date)
**Description**: $DESCRIPTION

## Timeline
- $(date): Incident detected

## Impact Assessment
- **Affected Services**: TBD
- **User Impact**: TBD
- **Business Impact**: TBD

## Actions Taken
- Incident response initiated
- On-call team notified

## Next Steps
- [ ] Root cause analysis
- [ ] Implement fix
- [ ] Monitor resolution
- [ ] Post-incident review

## Communication
- PagerDuty incident created
- Slack notification sent
- Status page updated (if needed)
EOF

echo "✅ Incident response initiated: $INCIDENT_ID"
```

### 2. Automated Recovery Actions

```yaml
# k8s/monitoring/auto-recovery.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: auto-recovery-monitor
  namespace: monitoring
spec:
  schedule: "*/1 * * * *"  # Every minute
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: auto-recovery
            image: ghcr.io/sunday/auto-recovery:latest
            env:
            - name: PROMETHEUS_URL
              value: "http://prometheus:9090"
            - name: KUBECTL_CONFIG
              value: "/etc/kubeconfig/config"
            command:
            - /bin/bash
            - -c
            - |
              # Check for unhealthy pods
              UNHEALTHY_PODS=$(kubectl get pods -A --field-selector=status.phase!=Running --no-headers | wc -l)

              if [ $UNHEALTHY_PODS -gt 5 ]; then
                echo "High number of unhealthy pods detected: $UNHEALTHY_PODS"

                # Restart deployments with failing pods
                kubectl get pods -A --field-selector=status.phase=Failed -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.labels.app}{"\n"}{end}' | \
                while read namespace app; do
                  if [ ! -z "$app" ]; then
                    echo "Restarting deployment $app in namespace $namespace"
                    kubectl rollout restart deployment/$app -n $namespace
                  fi
                done
              fi

              # Check memory usage and scale if needed
              HIGH_MEMORY_DEPLOYMENTS=$(kubectl top pods -A --no-headers | awk '$4 > 80 {print $1, $2}')

              if [ ! -z "$HIGH_MEMORY_DEPLOYMENTS" ]; then
                echo "$HIGH_MEMORY_DEPLOYMENTS" | while read namespace pod; do
                  APP=$(kubectl get pod $pod -n $namespace -o jsonpath='{.metadata.labels.app}')
                  CURRENT_REPLICAS=$(kubectl get deployment $APP -n $namespace -o jsonpath='{.spec.replicas}')
                  NEW_REPLICAS=$((CURRENT_REPLICAS + 1))

                  if [ $NEW_REPLICAS -le 10 ]; then
                    echo "Scaling up $APP in $namespace from $CURRENT_REPLICAS to $NEW_REPLICAS"
                    kubectl scale deployment $APP --replicas=$NEW_REPLICAS -n $namespace
                  fi
                done
              fi
          restartPolicy: OnFailure
```

---

*Last Updated: December 2024*
*Next Review: Q1 2025*
*Maintained by: DevOps and Monitoring Team*