# Maestro Monitoring Stack

> MD-2030: Deploy Prometheus/Grafana Monitoring Stack to Demo Server
> Part of EPIC MD-1979: Service Resilience & Operational Hardening

## Overview

This directory contains a Docker-based monitoring stack for the Maestro platform Demo server, featuring:

- **Prometheus** - Metrics collection and storage
- **Alertmanager** - Alert routing and notifications
- **Grafana** - Visualization and dashboards
- **Node Exporter** - System metrics collection

## Quick Start

```bash
# Deploy the monitoring stack
./deploy-demo.sh

# Stop the monitoring stack
docker-compose -f docker-compose.monitoring.yml down
```

## Access URLs

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Prometheus | http://localhost:9090 | N/A |
| Alertmanager | http://localhost:9093 | N/A |
| Grafana | http://localhost:23000 | admin / maestro_admin |

## Directory Structure

```
scripts/monitoring/
├── docker-compose.monitoring.yml  # Main compose file
├── deploy-demo.sh                 # Deployment script
├── README.md                      # This file
├── prometheus/
│   ├── prometheus-demo.yml        # Prometheus config
│   └── alerts/
│       └── maestro-alerts.yml     # Alert rules
├── alertmanager/
│   └── alertmanager.yml           # Alertmanager config
└── grafana/
    ├── datasources/
    │   └── datasources.yml        # Datasource config
    ├── dashboards/
    │   └── dashboards.yml         # Dashboard provisioning
    └── dashboard-json/
        └── maestro-service-health.json  # Pre-built dashboard
```

## Metrics Scraped

| Job | Target | Description |
|-----|--------|-------------|
| maestro-backend | localhost:4100 | Main application metrics |
| node-exporter | localhost:9100 | System metrics (CPU, memory, disk) |
| prometheus | localhost:9090 | Prometheus self-monitoring |
| alertmanager | localhost:9093 | Alertmanager metrics |

## Alert Rules

### Service Health Alerts
- **ServiceDown** - Backend service is unreachable (critical)
- **ServiceHighLatency** - p99 latency > 1s for 5 min (warning)
- **HighErrorRate** - Error rate > 1% for 5 min (warning)
- **HighRequestRate** - Request rate > 1000/s (info)

### System Resource Alerts
- **HighCPUUsage** - CPU > 85% for 5 min (warning)
- **HighMemoryUsage** - Memory > 90% for 5 min (warning)
- **DiskSpaceLow** - Disk > 85% full (warning)
- **DiskSpaceCritical** - Disk > 95% full (critical)

### Monitoring Infrastructure Alerts
- **PrometheusTargetMissing** - Scrape target down for 5 min (warning)
- **AlertmanagerDown** - Alertmanager unreachable (critical)

## Grafana Dashboards

### Maestro Service Health
Pre-configured dashboard showing:
- Service status (UP/DOWN)
- Request rate with success/error breakdown
- P99 latency
- Error rate percentage
- CPU and memory usage over time
- Disk usage by mount point

## Configuration

### Adding New Scrape Targets

Edit `prometheus/prometheus-demo.yml` and add a new job:

```yaml
- job_name: 'my-service'
  static_configs:
    - targets: ['host.docker.internal:PORT']
      labels:
        service: 'my-service'
```

### Configuring Alert Notifications

Edit `alertmanager/alertmanager.yml` to configure notification channels:

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
        channel: '#alerts'
```

## Troubleshooting

### Services not starting
```bash
# Check container logs
docker logs maestro-prometheus
docker logs maestro-grafana
```

### Targets showing as DOWN
```bash
# Verify target is accessible from Docker network
docker exec maestro-prometheus wget -qO- http://host.docker.internal:4100/metrics
```

### Grafana datasource errors
- Ensure Prometheus is healthy: `curl http://localhost:9090/-/healthy`
- Check Grafana datasource config in UI

## SSH Tunnel Access

For accessing the monitoring stack via SSH tunnel from remote:

```bash
# On your local machine
ssh -L 23000:localhost:23000 -L 9090:localhost:9090 user@demo-server

# Then access:
# http://localhost:23000 (Grafana)
# http://localhost:9090 (Prometheus)
```
