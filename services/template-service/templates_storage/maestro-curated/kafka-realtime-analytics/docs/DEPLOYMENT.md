# Deployment Guide

## Prerequisites

- Docker and Docker Compose (for local development)
- Kubernetes cluster (for production)
- kubectl configured
- Minimum 16GB RAM, 4 CPU cores

## Local Development Deployment

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd real-time-analytics-platform
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running**:
   ```bash
   docker-compose ps
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Wait for initialization** (approximately 2-3 minutes):
   - Kafka and Zookeeper need time to start
   - Database schema will be initialized automatically

### Test the System

1. **Send a test event**:
   ```bash
   curl -X POST http://localhost:8080/api/events \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "user_action",
       "data": {
         "user_id": "user_123",
         "action": "click",
         "value": 42,
         "region": "us-east"
       }
     }'
   ```

2. **Simulate traffic**:
   ```bash
   curl -X POST http://localhost:8080/api/simulate \
     -H "Content-Type: application/json" \
     -d '{"num_events": 1000, "event_type": "random"}'
   ```

3. **Query events**:
   ```bash
   curl http://localhost:8081/api/events?limit=10
   ```

4. **Get real-time metrics**:
   ```bash
   curl http://localhost:8081/api/metrics/realtime?event_type=user_action
   ```

5. **Dashboard summary**:
   ```bash
   curl http://localhost:8081/api/dashboard/summary
   ```

### Access Monitoring

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

- **Prometheus**: http://localhost:9090

### Stop Services

```bash
docker-compose down

# To remove volumes (data will be lost)
docker-compose down -v
```

## Production Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl access to cluster
- Sufficient cluster resources:
  - 8 nodes minimum
  - 32GB RAM per node
  - 100GB+ storage

### Build and Push Docker Images

1. **Build images**:
   ```bash
   # Producer
   docker build -t your-registry/analytics-producer:latest src/producer
   docker push your-registry/analytics-producer:latest

   # Stream Processor
   docker build -t your-registry/analytics-stream-processor:latest src/stream-processor
   docker push your-registry/analytics-stream-processor:latest

   # API
   docker build -t your-registry/analytics-api:latest src/api
   docker push your-registry/analytics-api:latest
   ```

2. **Update image references** in Kubernetes manifests:
   - `k8s/producer-deployment.yaml`
   - `k8s/stream-processor-deployment.yaml`
   - `k8s/api-deployment.yaml`

### Deploy to Kubernetes

1. **Navigate to k8s directory**:
   ```bash
   cd k8s
   ```

2. **Run deployment script**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Or deploy manually**:
   ```bash
   # Create namespace
   kubectl apply -f namespace.yaml

   # Deploy infrastructure
   kubectl apply -f kafka-deployment.yaml
   kubectl apply -f postgres-deployment.yaml
   kubectl apply -f redis-deployment.yaml

   # Wait for infrastructure to be ready
   kubectl wait --for=condition=ready pod -l app=kafka -n analytics-platform --timeout=300s

   # Deploy applications
   kubectl apply -f producer-deployment.yaml
   kubectl apply -f stream-processor-deployment.yaml
   kubectl apply -f api-deployment.yaml

   # Deploy monitoring
   kubectl apply -f monitoring-deployment.yaml
   ```

### Verify Deployment

1. **Check pod status**:
   ```bash
   kubectl get pods -n analytics-platform
   ```

2. **Check services**:
   ```bash
   kubectl get svc -n analytics-platform
   ```

3. **Get LoadBalancer IPs**:
   ```bash
   kubectl get svc producer -n analytics-platform
   kubectl get svc api -n analytics-platform
   kubectl get svc grafana -n analytics-platform
   ```

4. **Check logs**:
   ```bash
   kubectl logs -f deployment/producer -n analytics-platform
   kubectl logs -f deployment/stream-processor -n analytics-platform
   kubectl logs -f deployment/api -n analytics-platform
   ```

### Access Services

Get external IPs:
```bash
PRODUCER_IP=$(kubectl get svc producer -n analytics-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
API_IP=$(kubectl get svc api -n analytics-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
GRAFANA_IP=$(kubectl get svc grafana -n analytics-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Producer: http://$PRODUCER_IP:8080"
echo "API: http://$API_IP:8081"
echo "Grafana: http://$GRAFANA_IP:3000"
```

## Configuration

### Environment Variables

**Producer Service**:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `SERVICE_PORT`: Service port (default: 8080)

**Stream Processor**:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `POSTGRES_HOST`: PostgreSQL hostname
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port

**API Service**:
- `SERVICE_PORT`: Service port (default: 8081)
- `POSTGRES_HOST`: PostgreSQL hostname
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port

### Scaling

**Scale Producer**:
```bash
kubectl scale deployment producer -n analytics-platform --replicas=5
```

**Scale Stream Processor**:
```bash
kubectl scale deployment stream-processor -n analytics-platform --replicas=5
```

**Scale API**:
```bash
kubectl scale deployment api -n analytics-platform --replicas=5
```

**Scale Kafka**:
```bash
kubectl scale statefulset kafka -n analytics-platform --replicas=5
```

## Monitoring

### Grafana Dashboards

1. Access Grafana at http://\<GRAFANA_IP\>:3000
2. Login with admin/admin
3. Add Prometheus datasource (http://prometheus:9090)
4. Import dashboards from `infrastructure/monitoring/grafana/dashboards/`

### Prometheus Queries

- Event ingestion rate: `rate(kafka_producer_record_send_total[5m])`
- Processing lag: `kafka_consumer_lag`
- API response time: `http_request_duration_seconds`

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka logs
kubectl logs -f statefulset/kafka -n analytics-platform

# Verify Zookeeper
kubectl exec -it zookeeper-0 -n analytics-platform -- bash
echo stat | nc localhost 2181
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
kubectl logs -f statefulset/postgres -n analytics-platform

# Connect to database
kubectl exec -it postgres-0 -n analytics-platform -- psql -U analytics_user -d analytics
```

### Stream Processor Not Processing

```bash
# Check consumer group
kubectl exec -it kafka-0 -n analytics-platform -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group stream-processor-group
```

## Backup and Restore

### PostgreSQL Backup

```bash
kubectl exec -it postgres-0 -n analytics-platform -- pg_dump -U analytics_user analytics > backup.sql
```

### PostgreSQL Restore

```bash
kubectl exec -i postgres-0 -n analytics-platform -- psql -U analytics_user analytics < backup.sql
```

## Security Hardening

1. **Enable TLS for Kafka**:
   - Generate certificates
   - Update Kafka configuration
   - Update client configurations

2. **Enable PostgreSQL SSL**:
   - Configure SSL in postgres-deployment.yaml
   - Update connection strings

3. **Network Policies**:
   ```bash
   kubectl apply -f network-policies.yaml
   ```

4. **Pod Security Policies**:
   - Enable PSP admission controller
   - Apply restrictive policies

## Performance Tuning

### Kafka Tuning

- Adjust `num.partitions` for higher parallelism
- Increase `replica.lag.time.max.ms` if needed
- Tune `log.segment.bytes` and `log.retention.bytes`

### PostgreSQL Tuning

```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '4GB';

-- Increase work memory
ALTER SYSTEM SET work_mem = '64MB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Application Tuning

- Adjust worker/thread counts
- Tune batch sizes
- Configure connection pools