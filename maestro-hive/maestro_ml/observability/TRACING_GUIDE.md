# Distributed Tracing with OpenTelemetry

Complete guide to distributed tracing in Maestro ML Platform using OpenTelemetry and Jaeger.

## 📊 Overview

Distributed tracing helps you:
- **Track requests** across multiple services
- **Identify bottlenecks** in your ML pipeline
- **Debug production issues** with detailed trace data
- **Monitor performance** at the operation level
- **Understand dependencies** between services

### Architecture

```
┌─────────────┐
│   API       │
│  Request    │
└──────┬──────┘
       │ Creates trace
       ▼
┌─────────────────────────────┐
│  OpenTelemetry              │
│  - Auto-instrument FastAPI  │
│  - Capture spans            │
│  - Add context              │
└──────┬──────────────────────┘
       │ Export spans
       ▼
┌─────────────┐
│   Jaeger    │
│   Agent     │
└──────┬──────┘
       │ Forward traces
       ▼
┌─────────────────────┐
│  Jaeger Collector   │
│  & Storage          │
└──────┬──────────────┘
       │
       ▼
┌─────────────┐
│  Jaeger UI  │
│  Visualize  │
└─────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using Poetry (recommended)
poetry add opentelemetry-api opentelemetry-sdk \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-sqlalchemy \
  opentelemetry-instrumentation-httpx \
  opentelemetry-exporter-jaeger-thrift

# Or using pip
pip install opentelemetry-api opentelemetry-sdk \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-sqlalchemy \
  opentelemetry-instrumentation-httpx \
  opentelemetry-exporter-jaeger-thrift
```

### 2. Deploy Jaeger (Local Development)

```bash
# Using Docker Compose
docker-compose -f observability/docker-compose.tracing.yaml up -d

# Access Jaeger UI
open http://localhost:16686
```

### 3. Configure Tracing in Your API

```python
from fastapi import FastAPI
from observability import configure_tracing, add_tracing_middleware

app = FastAPI(title="Maestro ML")

# Configure tracing
tracing_manager = configure_tracing(
    app=app,
    service_name="maestro-ml-api"
)

# Add middleware
add_tracing_middleware(app)
```

### 4. Environment Variables

```bash
# .env
TRACING_ENABLED=true
JAEGER_AGENT_HOST=localhost  # or jaeger.observability.svc.cluster.local in K8s
JAEGER_AGENT_PORT=6831
```

---

## 🔧 Configuration

### Basic Configuration

```python
from observability import TracingManager

tracing_manager = TracingManager(
    service_name="maestro-ml-api",
    service_version="1.0.0",
    jaeger_host="jaeger.observability.svc.cluster.local",
    jaeger_port=6831,
    enabled=True
)

# Setup tracing
tracing_manager.setup_tracing()

# Instrument FastAPI
tracing_manager.instrument_fastapi(app)
```

### Advanced Configuration

```python
# Custom resource attributes
from opentelemetry.sdk.resources import Resource

resource = Resource(attributes={
    "service.name": "maestro-ml-api",
    "service.version": "1.0.0",
    "deployment.environment": "production",
    "service.namespace": "ml-platform",
    "cloud.provider": "aws",
    "cloud.region": "us-west-2"
})
```

### Instrumentation Options

```python
# Instrument SQLAlchemy
tracing_manager.instrument_sqlalchemy(engine)

# Instrument HTTPX (HTTP clients)
tracing_manager.instrument_httpx()

# Instrument Redis
tracing_manager.instrument_redis()
```

---

## 📝 Usage Patterns

### Pattern 1: Automatic Tracing (Recommended)

All FastAPI endpoints are automatically traced:

```python
@app.get("/models")
async def list_models():
    # Automatically creates span: "GET /models"
    return {"models": []}
```

### Pattern 2: Custom Spans with Context Manager

```python
from observability import trace_span

@app.post("/models")
async def create_model(model_data: dict):
    # Custom span for validation
    with trace_span("validate_model", attributes={"model_type": model_data["type"]}):
        validate(model_data)

    # Custom span for database save
    with trace_span("save_to_database", attributes={"table": "models"}):
        await db.save(model_data)

    return {"status": "created"}
```

### Pattern 3: Function Decorator

```python
from observability import traced

@traced("train_model_job")
async def train_model(model_id: str, config: dict):
    # Entire function is traced as single span
    # Nested operations create child spans

    with trace_span("load_data"):
        data = await load_data()

    with trace_span("training", attributes={"epochs": config["epochs"]}):
        model = train(data, config)

    return model
```

### Pattern 4: Manual Span Control

```python
from opentelemetry import trace

@app.post("/training/jobs")
async def submit_job(config: dict):
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("submit_training_job") as span:
        # Set attributes
        span.set_attribute("job.type", config["type"])
        span.set_attribute("job.priority", config.get("priority", "normal"))

        # Add event
        span.add_event("job_queued", attributes={"queue": "training"})

        # Process job
        job_id = await process_job(config)

        # Add another event
        span.add_event("job_started", attributes={"job_id": job_id})

        return {"job_id": job_id}
```

### Pattern 5: Error Tracking

```python
@app.get("/models/{model_id}")
async def get_model(model_id: str):
    try:
        model = await fetch_model(model_id)
        return model
    except ModelNotFoundError as e:
        # Exception automatically recorded in span
        # Span marked with error status
        raise HTTPException(status_code=404, detail=str(e))
```

---

## 🎨 Trace Attributes

### Automatic Attributes (from middleware)

- `http.method` - HTTP method (GET, POST, etc.)
- `http.url` - Full request URL
- `http.status_code` - Response status code
- `http.client_ip` - Client IP address
- `http.user_agent` - User agent string
- `http.response_time_ms` - Response time in milliseconds

### Custom Business Attributes

```python
span = trace.get_current_span()

# Model attributes
span.set_attribute("model.id", model_id)
span.set_attribute("model.type", "pytorch")
span.set_attribute("model.version", "v1.2.3")

# Training attributes
span.set_attribute("training.epochs", 100)
span.set_attribute("training.batch_size", 32)
span.set_attribute("training.learning_rate", 0.001)

# Tenant attributes
span.set_attribute("tenant.id", tenant_id)
span.set_attribute("tenant.quota_usage", 0.75)

# Resource attributes
span.set_attribute("resource.gpu_count", 4)
span.set_attribute("resource.instance_type", "p3.8xlarge")
```

### Span Events

```python
span.add_event(
    "model_checkpoint_saved",
    attributes={
        "epoch": 50,
        "loss": 0.23,
        "checkpoint_path": "s3://models/checkpoint-50.pt"
    }
)

span.add_event(
    "dataset_loaded",
    attributes={
        "dataset_size": 1000000,
        "load_time_ms": 5234
    }
)
```

---

## 🔍 Viewing Traces in Jaeger

### 1. Access Jaeger UI

**Local Development:**
```bash
# Docker Compose
open http://localhost:16686

# Kubernetes Port Forward
kubectl port-forward -n observability svc/jaeger 16686:16686
open http://localhost:16686
```

### 2. Finding Traces

1. **Select Service**: Choose `maestro-ml-api` from dropdown
2. **Set Time Range**: Last 1 hour, Last 24 hours, etc.
3. **Filter by Operation**: Select specific endpoints
4. **Filter by Tags**:
   - `http.status_code=500` (errors only)
   - `tenant.id=tenant-123`
   - `model.type=pytorch`
5. **Click "Find Traces"**

### 3. Analyzing Traces

**Trace List View:**
- Duration of each request
- Number of spans
- Service involvement
- Error status

**Trace Detail View:**
- Timeline visualization
- Span hierarchy (parent-child)
- Span duration and % of total
- Tags and logs for each span
- Error details

**Trace Comparison:**
- Compare slow vs fast requests
- Identify bottlenecks
- Analyze performance patterns

---

## 📊 Common Use Cases

### Use Case 1: Debug Slow API Requests

**Problem**: `/models/{id}/deploy` endpoint is slow

**Solution**:
1. Find traces for the endpoint in Jaeger
2. Sort by duration (longest first)
3. Examine span breakdown:
   - `validate_deployment_config` - 50ms
   - `fetch_model_from_registry` - 2000ms ← **Bottleneck!**
   - `create_k8s_deployment` - 500ms
   - `update_database` - 100ms

4. Optimize model fetching (add caching)

### Use Case 2: Track ML Training Pipeline

```python
@traced("ml_training_pipeline")
async def train_model_pipeline(config: dict):
    with trace_span("data_preprocessing", attributes={"rows": 1000000}):
        data = await preprocess_data(config["dataset"])

    with trace_span("feature_engineering", attributes={"features": 50}):
        features = await engineer_features(data)

    with trace_span("model_training", attributes={"epochs": 100}):
        model = await train_model(features, config)

    with trace_span("model_evaluation", attributes={"metrics": ["accuracy", "f1"]}):
        metrics = await evaluate_model(model)

    return {"model_id": "...", "metrics": metrics}
```

**View in Jaeger:**
- Total pipeline duration
- Time spent in each phase
- Identify optimization opportunities

### Use Case 3: Multi-Service Request Tracking

**Scenario**: Request flows through multiple services:
1. API Gateway → 2. ML API → 3. MLflow → 4. S3

**Tracing shows:**
```
HTTP POST /models/deploy (5.2s total)
├── validate_request (0.1s)
├── fetch_model_metadata (0.3s)
│   └── mlflow.get_model (0.2s)
├── download_model_artifacts (4.5s)  ← Slow!
│   └── s3.download (4.4s)
└── create_deployment (0.3s)
```

**Solution**: Implement model artifact caching

### Use Case 4: Error Investigation

**Problem**: Intermittent 500 errors on `/predictions` endpoint

**Solution**:
1. Filter traces: `http.status_code=500`
2. Examine error traces
3. Check span with error status
4. View exception details:
   ```
   ValueError: Model version v2.0 not found in registry
   at line 45 in model_loader.py
   ```
5. Root cause: Deployment using wrong version

---

## 🛠️ Kubernetes Deployment

### Deploy Jaeger

```bash
# Apply Jaeger deployment
kubectl apply -f observability/jaeger-deployment.yaml

# Verify
kubectl get pods -n observability
kubectl get svc -n observability

# Port forward UI
kubectl port-forward -n observability svc/jaeger 16686:16686
```

### Configure Applications

```yaml
# deployment.yaml
env:
- name: TRACING_ENABLED
  value: "true"
- name: JAEGER_AGENT_HOST
  value: "jaeger.observability.svc.cluster.local"
- name: JAEGER_AGENT_PORT
  value: "6831"
```

### Service Mesh Integration (Optional)

If using Istio/Linkerd, tracing is automatic at the mesh level.

---

## 🔐 Security Hardening

### Jaeger with Security Context

Already applied in `jaeger-deployment.yaml`:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: false  # Badger needs write access
```

### Network Policies

Restrict Jaeger access:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: jaeger-ingress
  namespace: observability
spec:
  podSelector:
    matchLabels:
      app: jaeger
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          app: ml-platform
    ports:
    - port: 6831
      protocol: UDP
    - port: 14268
      protocol: TCP
```

---

## 📈 Performance Considerations

### Sampling Strategies

```python
# Production: Sample 10% of traces
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

tracer_provider = TracerProvider(
    sampler=TraceIdRatioBased(0.1)  # 10% sampling
)
```

### Batch Export Configuration

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    jaeger_exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000,  # Export every 5 seconds
    max_export_batch_size=512
)
```

### Exclude High-Volume Endpoints

```python
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="health,metrics,readiness,liveness"
)
```

---

## 🧪 Testing

### Local Testing

```bash
# Start Jaeger
docker-compose -f observability/docker-compose.tracing.yaml up -d

# Run application with tracing
TRACING_ENABLED=true uvicorn maestro_ml.api.main:app

# Generate test traces
curl http://localhost:8000/models
curl http://localhost:8000/experiments

# View in Jaeger
open http://localhost:16686
```

### Integration Tests

```python
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

@pytest.fixture
def trace_exporter():
    """Fixture for capturing traces in tests."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    exporter.clear()

def test_model_creation_creates_spans(trace_exporter):
    """Test that model creation creates appropriate spans."""
    # Make API call
    response = client.post("/models", json={"name": "test-model"})

    # Get captured spans
    spans = trace_exporter.get_finished_spans()

    # Assert spans exist
    assert len(spans) > 0

    # Find specific spans
    validation_span = next(s for s in spans if s.name == "validate_model")
    assert validation_span.attributes["model_type"] == "pytorch"

    db_span = next(s for s in spans if s.name == "save_to_database")
    assert db_span.status.is_ok
```

---

## 📚 Best Practices

### 1. Meaningful Span Names

✅ **Good:**
```python
trace_span("load_training_dataset", {"dataset": "imagenet"})
trace_span("train_resnet50_model", {"epochs": 100})
```

❌ **Bad:**
```python
trace_span("step1")
trace_span("process_data")
```

### 2. Add Relevant Attributes

```python
# Include business context
span.set_attribute("model.id", model_id)
span.set_attribute("user.id", user_id)
span.set_attribute("tenant.id", tenant_id)

# Include technical context
span.set_attribute("db.statement", query)
span.set_attribute("db.rows_affected", row_count)
```

### 3. Use Events for Important Milestones

```python
span.add_event("model_checkpoint_saved", {"epoch": 50})
span.add_event("validation_accuracy_improved", {"accuracy": 0.95})
span.add_event("early_stopping_triggered", {"epoch": 75})
```

### 4. Keep Spans Focused

Each span should represent a single operation:

```python
# Good: Separate spans
with trace_span("load_data"):
    data = load()

with trace_span("train_model"):
    model = train(data)

# Bad: Single large span
with trace_span("train"):
    data = load()  # Should be separate span
    model = train(data)
```

### 5. Handle Errors Properly

```python
try:
    result = await risky_operation()
except Exception as e:
    span = trace.get_current_span()
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    raise
```

---

## 🔧 Troubleshooting

### Problem: No traces in Jaeger

**Solutions:**
1. Check `TRACING_ENABLED=true` in environment
2. Verify Jaeger is running: `docker ps | grep jaeger`
3. Check Jaeger agent connectivity:
   ```bash
   telnet jaeger.observability.svc.cluster.local 6831
   ```
4. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Problem: High memory usage

**Solutions:**
1. Reduce sampling rate
2. Increase batch export interval
3. Exclude high-volume endpoints
4. Reduce span attribute size

### Problem: Spans not nested correctly

**Solutions:**
1. Ensure context propagation:
   ```python
   from opentelemetry import context

   # Save context
   ctx = context.get_current()

   # Restore in async task
   with context.attach(ctx):
       await async_operation()
   ```

---

## 📖 Additional Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [FastAPI OpenTelemetry Guide](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/signals/traces/)

---

**Last Updated**: 2025-10-05
**Version**: 1.0
**Status**: ✅ Production Ready
