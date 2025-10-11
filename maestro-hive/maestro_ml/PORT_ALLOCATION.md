# Maestro ML Platform - Port Allocation

**Registry Managed**: Yes
**Registry Location**: `/home/ec2-user/projects/shared/services_registry.json`
**Manager**: `/home/ec2-user/projects/shared/tools/port_registry_manager.py`

## Allocated Ports

All ports are dynamically allocated via the shared Port Registry Manager to avoid conflicts with other projects on this server.

### Minikube NodePorts

| Service | Internal Port | NodePort | Allocated | Description |
|---------|--------------|----------|-----------|-------------|
| **MLflow** | 5000 | 30500 | ✅ | ML experiment tracking |
| **Feast** | 6566 | 30501 | ✅ | Feature store server |
| **Airflow** | 8080 | 30502 | ✅ | Workflow orchestration |
| **Prometheus** | 9090 | 30503 | ✅ | Metrics collection |
| **Grafana** | 3000 | 30504 | ✅ | Monitoring dashboards |
| **MinIO Console** | 9001 | 30505 | ✅ | S3-compatible storage UI |

### Internal Services (ClusterIP only)

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** (storage) | 5432 | Database for MLflow & Feast |
| **PostgreSQL** (airflow) | 5432 | Database for Airflow metadata |
| **Redis** | 6379 | Feast online store |
| **MinIO API** | 9000 | S3-compatible object storage |
| **Airflow Flower** | 5555 | Celery task monitoring |

## Port Management

### Check Current Allocation

```bash
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"
```

### Re-allocate Ports

If you need to change port allocations:

```bash
# 1. Release current ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"

# 2. Allocate new ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "maestro-ml-platform" \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml" \
  --count 6 \
  --start-range 30500 \
  --end-range 30999

# 3. Update manifests with new ports
```

### Access Services (Minikube)

Once minikube is running, access services via NodePorts:

```bash
MINIKUBE_IP=$(minikube ip)

# MLflow
echo "http://$MINIKUBE_IP:30500"

# Feast
echo "http://$MINIKUBE_IP:30501"

# Airflow
echo "http://$MINIKUBE_IP:30502"

# Prometheus
echo "http://$MINIKUBE_IP:30503"

# Grafana
echo "http://$MINIKUBE_IP:30504"

# MinIO Console
echo "http://$MINIKUBE_IP:30505"
```

Or use port-forward (recommended):

```bash
# MLflow
kubectl port-forward -n mlflow svc/mlflow-service 5000:80

# Feast
kubectl port-forward -n feast svc/feast-feature-server 6566:80

# Airflow
kubectl port-forward -n airflow svc/airflow-webserver 8080:80

# Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090

# Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

# MinIO Console
kubectl port-forward -n storage svc/minio 9001:9001
```

## Production Deployment

In production, services use:
- **LoadBalancer** type for external access
- **Ingress** controllers with domain names
- **ClusterIP** for internal services

Port allocation is not needed for production as LoadBalancers and Ingress handle external access.

### Production URLs (Example)

- MLflow: https://mlflow.maestro-ml.example.com
- Feast: https://feast.maestro-ml.example.com
- Airflow: https://airflow.maestro-ml.example.com
- Prometheus: https://prometheus.maestro-ml.example.com
- Grafana: https://grafana.maestro-ml.example.com

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

```bash
# Check what's using a port
sudo netstat -tulpn | grep 30500

# Or with ss
ss -tulpn | grep 30500

# Check registry
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status
```

### Re-registration

If services were deployed outside the registry:

```python
from port_registry_manager import PortRegistryManager

manager = PortRegistryManager()

# Register existing service
manager.register_service(
    service_name="mlflow",
    service_type="ml-tracking",
    port=30500,
    project_path="/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml",
    health_endpoint="/health",
    namespace="mlflow"
)
```

## CI/CD Integration

The port registry is automatically used by deployment scripts:

```bash
# In scripts/setup-minikube-test.sh
# Ports are pre-allocated and configured in manifests

# Verify allocation
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status
```

---

**Last Updated**: 2025-10-04
**Managed By**: Shared Port Registry
**Project**: Maestro ML Platform
