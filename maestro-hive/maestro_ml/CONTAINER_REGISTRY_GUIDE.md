# Container Registry Setup Guide

## Overview

The ML platform uses a container registry to store Docker images for:
- Custom training containers
- Inference serving containers
- Airflow custom operators
- Data pipeline jobs

## Deployment Options

### Production (Harbor)
- Location: `infrastructure/kubernetes/container-registry.yaml`
- Features: Vulnerability scanning, RBAC, replication, webhooks
- Components: PostgreSQL, Redis, Core, Registry, Portal
- Storage: 100Gi for images

### Minikube (Simple Docker Registry)
- Location: `infrastructure/minikube/container-registry.yaml`
- Features: Lightweight, simple, fast
- Components: Registry v2, Web UI
- Storage: 20Gi for images

## Ports

Via port registry manager:
- **Registry**: 30506 (push/pull images)
- **Registry UI**: 30507 (web interface)

## Deployment

### Minikube

```bash
# Deploy registry
kubectl apply -f infrastructure/minikube/container-registry.yaml

# Wait for registry to be ready
kubectl wait --for=condition=ready pod -l app=docker-registry -n registry --timeout=300s

# Get registry URL
MINIKUBE_IP=$(minikube ip)
echo "Registry: http://$MINIKUBE_IP:30506"
echo "UI: http://$MINIKUBE_IP:30507"
```

### Production

```bash
# Deploy Harbor
kubectl apply -f infrastructure/kubernetes/container-registry.yaml

# Wait for all components
kubectl wait --for=condition=ready pod -l app=harbor-core -n harbor-system --timeout=300s

# Access via ingress
echo "Registry: https://registry.maestro-ml.example.com"
```

## Configuration

### Configure Docker to Use Registry

```bash
# For minikube (insecure registry)
MINIKUBE_IP=$(minikube ip)

# Add to Docker daemon config (/etc/docker/daemon.json)
{
  "insecure-registries": ["$MINIKUBE_IP:30506"]
}

# Restart Docker
sudo systemctl restart docker
```

### Configure Kubernetes to Pull from Registry

```bash
# For minikube (already configured)
eval $(minikube docker-env)

# For production (create secret)
kubectl create secret docker-registry regcred \
  --docker-server=registry.maestro-ml.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --namespace=ml-platform
```

## Building and Pushing Images

### Example: Custom Training Container

```bash
# 1. Build image
docker build -t training-job:v1.0 -f docker/training.Dockerfile .

# 2. Tag for registry
MINIKUBE_IP=$(minikube ip)
docker tag training-job:v1.0 $MINIKUBE_IP:30506/ml-platform/training-job:v1.0

# 3. Push to registry
docker push $MINIKUBE_IP:30506/ml-platform/training-job:v1.0

# 4. Verify in UI
open http://$MINIKUBE_IP:30507
```

### Example: Airflow Custom Operator

```bash
# 1. Create Dockerfile
cat > docker/airflow-custom.Dockerfile <<EOF
FROM apache/airflow:2.7.3-python3.11
USER root
RUN apt-get update && apt-get install -y gcc python3-dev
USER airflow
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY dags/ /opt/airflow/dags/
COPY mlops/ /opt/airflow/mlops/
EOF

# 2. Build and push
docker build -t airflow-custom:v1.0 -f docker/airflow-custom.Dockerfile .
docker tag airflow-custom:v1.0 $MINIKUBE_IP:30506/ml-platform/airflow:v1.0
docker push $MINIKUBE_IP:30506/ml-platform/airflow:v1.0
```

### Example: Inference Server

```bash
# 1. Create Dockerfile
cat > docker/inference.Dockerfile <<EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY model_server/ .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# 2. Build and push
docker build -t inference-server:v1.0 -f docker/inference.Dockerfile .
docker tag inference-server:v1.0 $MINIKUBE_IP:30506/ml-platform/inference:v1.0
docker push $MINIKUBE_IP:30506/ml-platform/inference:v1.0
```

## Using Images in Kubernetes

### In Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: training-job
  namespace: ml-platform
spec:
  template:
    spec:
      containers:
      - name: trainer
        image: 192.168.49.2:30506/ml-platform/training-job:v1.0
        imagePullPolicy: Always
      # For production with authentication
      imagePullSecrets:
      - name: regcred
```

### In Airflow DAG

```python
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

train_model = KubernetesPodOperator(
    task_id='train_model',
    name='model-training',
    namespace='ml-platform',
    image='192.168.49.2:30506/ml-platform/training-job:v1.0',
    image_pull_policy='Always',
    get_logs=True,
)
```

## Registry Management

### List Images

```bash
# Via API
curl http://$MINIKUBE_IP:30506/v2/_catalog

# Via UI
open http://$MINIKUBE_IP:30507
```

### Delete Image

```bash
# Get digest
curl -I -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  http://$MINIKUBE_IP:30506/v2/ml-platform/training-job/manifests/v1.0

# Delete by digest
curl -X DELETE http://$MINIKUBE_IP:30506/v2/ml-platform/training-job/manifests/sha256:...

# Run garbage collection
kubectl exec -it docker-registry-0 -n registry -- \
  registry garbage-collect /etc/docker/registry/config.yml
```

### View Image Tags

```bash
curl http://$MINIKUBE_IP:30506/v2/ml-platform/training-job/tags/list
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push ML Image

on:
  push:
    branches: [main]
    paths:
      - 'docker/**'
      - 'mlops/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: |
          docker build -t training-job:${{ github.sha }} -f docker/training.Dockerfile .

      - name: Push to registry
        run: |
          docker tag training-job:${{ github.sha }} \
            registry.maestro-ml.example.com/ml-platform/training-job:${{ github.sha }}
          docker push registry.maestro-ml.example.com/ml-platform/training-job:${{ github.sha }}
          docker tag training-job:${{ github.sha }} \
            registry.maestro-ml.example.com/ml-platform/training-job:latest
          docker push registry.maestro-ml.example.com/ml-platform/training-job:latest
```

## Common ML Images

### Training Images

```bash
# PyTorch training
docker build -t $REGISTRY/ml-platform/pytorch-train:v1.0 -f docker/pytorch.Dockerfile .

# TensorFlow training
docker build -t $REGISTRY/ml-platform/tensorflow-train:v1.0 -f docker/tensorflow.Dockerfile .

# Scikit-learn training
docker build -t $REGISTRY/ml-platform/sklearn-train:v1.0 -f docker/sklearn.Dockerfile .
```

### Serving Images

```bash
# MLflow serving
docker build -t $REGISTRY/ml-platform/mlflow-serve:v1.0 -f docker/mlflow-serve.Dockerfile .

# TorchServe
docker build -t $REGISTRY/ml-platform/torchserve:v1.0 -f docker/torchserve.Dockerfile .

# TensorFlow Serving
docker build -t $REGISTRY/ml-platform/tf-serving:v1.0 -f docker/tf-serving.Dockerfile .
```

## Troubleshooting

### Cannot Push to Registry

```bash
# Check registry is running
kubectl get pods -n registry

# Check service
kubectl get svc -n registry

# Test connectivity
curl http://$MINIKUBE_IP:30506/v2/
# Should return: {}
```

### Image Pull Errors in Kubernetes

```bash
# Check image exists
curl http://$MINIKUBE_IP:30506/v2/ml-platform/training-job/tags/list

# Check pod events
kubectl describe pod <pod-name> -n ml-platform

# For production: check secret
kubectl get secret regcred -n ml-platform -o yaml
```

### Registry Storage Full

```bash
# Check storage usage
kubectl exec -it docker-registry-0 -n registry -- df -h /var/lib/registry

# Run garbage collection
kubectl exec -it docker-registry-0 -n registry -- \
  registry garbage-collect /etc/docker/registry/config.yml --delete-untagged
```

## Security Best Practices

### For Production

1. **Enable HTTPS**: Use cert-manager for TLS
2. **Enable Authentication**: Configure Harbor RBAC
3. **Scan Images**: Enable Trivy vulnerability scanning
4. **Content Trust**: Enable Docker Content Trust
5. **Network Policies**: Restrict registry access
6. **Backup**: Regular backup of registry data

### For Development

1. **Use Insecure Registry**: Only for local minikube
2. **No Authentication**: Simplify development
3. **Limited Storage**: 20Gi for testing
4. **No Replication**: Single instance

## Monitoring

### Registry Metrics (Prometheus)

```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: docker-registry
  namespace: registry
spec:
  selector:
    matchLabels:
      app: docker-registry
  endpoints:
  - port: registry
    path: /metrics
```

### Key Metrics

- `registry_http_requests_total`: Total HTTP requests
- `registry_storage_bytes`: Storage usage
- `registry_http_request_duration_seconds`: Request latency

## Next Steps

1. ✅ Deploy registry to minikube
2. ✅ Build custom training image
3. ➡️ Integrate with CI/CD pipeline
4. ➡️ Set up image scanning
5. ➡️ Configure backup strategy

---

**Last Updated**: 2025-10-04
**Status**: Production Ready ✅
