# Testing Guide

## Overview

The platform includes comprehensive testing at multiple levels:
- Unit tests for services
- Integration tests for system flows
- Load testing for performance validation
- End-to-end testing for complete workflows

## Running Unit Tests

### Prerequisites

```bash
cd tests
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=../src --cov-report=html -v
```

View coverage report:
```bash
open htmlcov/index.html
```

### Run Specific Test Files

```bash
# Producer tests
pytest test_producer.py -v

# API tests
pytest test_api.py -v
```

## Integration Testing

### Local Environment Testing

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Wait for services to be ready**:
   ```bash
   # Check service health
   curl http://localhost:8080/health
   curl http://localhost:8081/health
   ```

3. **Run integration test script**:
   ```bash
   ./tests/integration_test.sh
   ```

### Test Scenarios

#### Scenario 1: Event Ingestion Flow

```bash
# Send single event
curl -X POST http://localhost:8080/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_action",
    "data": {"user_id": "test_user", "action": "test", "value": 100}
  }'

# Verify event in API
sleep 5
curl "http://localhost:8081/api/events?limit=1" | jq
```

#### Scenario 2: Batch Processing

```bash
# Send batch
curl -X POST http://localhost:8080/api/events/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"event_type": "transaction", "data": {"amount": 99.99}},
    {"event_type": "transaction", "data": {"amount": 149.99}},
    {"event_type": "transaction", "data": {"amount": 199.99}}
  ]'

# Check aggregations after window completes
sleep 300
curl "http://localhost:8081/api/aggregations?event_type=transaction" | jq
```

#### Scenario 3: Real-Time Metrics

```bash
# Generate traffic
curl -X POST http://localhost:8080/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"num_events": 1000, "event_type": "user_action"}'

# Check real-time metrics
curl "http://localhost:8081/api/metrics/realtime?event_type=user_action" | jq
```

#### Scenario 4: Anomaly Detection

```bash
# Send normal events
for i in {1..10}; do
  curl -X POST http://localhost:8080/api/events \
    -H "Content-Type: application/json" \
    -d '{"event_type": "transaction", "data": {"value": 100}}' &
done
wait

# Send anomalous event
curl -X POST http://localhost:8080/api/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "transaction", "data": {"value": 10000}}'

# Check anomalies
sleep 10
curl "http://localhost:8081/api/anomalies?event_type=transaction" | jq
```

## Load Testing

### Using Apache Bench

```bash
# Test producer endpoint
ab -n 10000 -c 100 -p event.json -T application/json http://localhost:8080/api/events
```

### Using Locust

1. **Install Locust**:
   ```bash
   pip install locust
   ```

2. **Create locustfile.py**:
   ```python
   from locust import HttpUser, task, between

   class AnalyticsUser(HttpUser):
       wait_time = between(1, 3)

       @task
       def send_event(self):
           self.client.post("/api/events", json={
               "event_type": "user_action",
               "data": {"user_id": "load_test", "value": 42}
           })
   ```

3. **Run load test**:
   ```bash
   locust -f locustfile.py --host=http://localhost:8080
   ```

4. **Access Locust UI**: http://localhost:8089

### Performance Targets

- **Throughput**: 10,000+ events/second
- **Latency (p99)**: < 100ms
- **Error Rate**: < 0.1%

## End-to-End Testing

### Kubernetes Environment

1. **Deploy to test cluster**:
   ```bash
   cd k8s
   ./deploy.sh
   ```

2. **Get service endpoints**:
   ```bash
   PRODUCER_IP=$(kubectl get svc producer -n analytics-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   API_IP=$(kubectl get svc api -n analytics-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   ```

3. **Run E2E tests**:
   ```bash
   export PRODUCER_URL="http://$PRODUCER_IP:8080"
   export API_URL="http://$API_IP:8081"
   pytest tests/e2e/ -v
   ```

## Monitoring Tests

### Prometheus Metrics

```bash
# Check if metrics are being collected
curl http://localhost:9090/api/v1/query?query=up

# Query producer metrics
curl "http://localhost:9090/api/v1/query?query=kafka_producer_record_send_total"
```

### Grafana Dashboards

1. Access Grafana: http://localhost:3000
2. Login: admin/admin
3. Verify dashboards load correctly
4. Check data is being displayed

## Database Testing

### PostgreSQL Queries

```bash
# Connect to database
docker exec -it postgres psql -U analytics_user -d analytics

# Check event count
SELECT COUNT(*) FROM raw_events;

# Check aggregations
SELECT event_type, COUNT(*) FROM aggregations GROUP BY event_type;

# Check anomalies
SELECT * FROM anomalies ORDER BY detected_at DESC LIMIT 10;
```

### Redis Cache

```bash
# Connect to Redis
docker exec -it redis redis-cli

# Check metrics
KEYS metrics:*
GET metrics:count:user_action
HGETALL metrics:region:user_action
```

## Chaos Testing

### Simulate Failures

1. **Kill producer**:
   ```bash
   docker stop producer
   # System should continue processing existing messages
   docker start producer
   ```

2. **Kill stream processor**:
   ```bash
   docker stop stream-processor
   # Messages should accumulate in Kafka
   docker start stream-processor
   # Processing should resume
   ```

3. **Network partition**:
   ```bash
   # Simulate network issues
   docker network disconnect analytics-network kafka
   # Wait 30 seconds
   docker network connect analytics-network kafka
   ```

## Test Data Cleanup

### Clean Docker Environment

```bash
docker-compose down -v
docker-compose up -d
```

### Clean Kubernetes Environment

```bash
kubectl delete namespace analytics-platform
cd k8s && ./deploy.sh
```

### Clean Database

```bash
docker exec -it postgres psql -U analytics_user -d analytics -c "TRUNCATE raw_events, aggregations, anomalies CASCADE;"
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          cd tests
          pip install -r requirements.txt
      - name: Run unit tests
        run: pytest -v --cov
      - name: Start services
        run: docker-compose up -d
      - name: Run integration tests
        run: ./tests/integration_test.sh
```

## Test Reporting

Generate test reports:

```bash
# HTML report
pytest --html=report.html --self-contained-html

# JUnit XML (for CI)
pytest --junitxml=report.xml

# Coverage report
pytest --cov=../src --cov-report=xml --cov-report=html
```