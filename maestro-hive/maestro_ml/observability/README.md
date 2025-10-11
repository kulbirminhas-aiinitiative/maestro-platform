# Observability & Distributed Tracing

Comprehensive observability stack for Maestro ML Platform with distributed tracing, monitoring, and performance analysis.

## 🎯 Components

### 1. Distributed Tracing (OpenTelemetry + Jaeger)
- **Full request tracing** across services
- **Performance analysis** with span timing
- **Error tracking** and debugging
- **Service dependency mapping**

### 2. Metrics (Prometheus)
- API performance metrics
- Business metrics (models, experiments)
- Resource utilization
- Custom application metrics

### 3. Visualization (Grafana + Jaeger UI)
- Pre-built dashboards
- Real-time monitoring
- Trace visualization
- Alert management

---

## 🚀 Quick Start

### Local Development

```bash
# 1. Start Jaeger and dependencies
docker-compose -f observability/docker-compose.tracing.yaml up -d

# 2. Install tracing dependencies
poetry add opentelemetry-api opentelemetry-sdk \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-exporter-jaeger-thrift

# 3. Enable tracing in your app
export TRACING_ENABLED=true
export JAEGER_AGENT_HOST=localhost

# 4. Run your application
uvicorn maestro_ml.api.main:app

# 5. Access Jaeger UI
open http://localhost:16686
```

### Kubernetes Production

```bash
# 1. Deploy Jaeger
kubectl apply -f observability/jaeger-deployment.yaml

# 2. Verify deployment
kubectl get pods -n observability

# 3. Configure application
kubectl set env deployment/maestro-api \
  TRACING_ENABLED=true \
  JAEGER_AGENT_HOST=jaeger.observability.svc.cluster.local

# 4. Port-forward Jaeger UI
kubectl port-forward -n observability svc/jaeger 16686:16686

# 5. Access UI
open http://localhost:16686
```

---

## 📁 Directory Structure

```
observability/
├── README.md                          # This file
├── TRACING_GUIDE.md                   # Complete tracing guide
├── tracing.py                         # OpenTelemetry configuration
├── middleware.py                      # Tracing middleware
├── __init__.py                        # Package exports
├── api_integration_example.py         # Integration examples
├── jaeger-deployment.yaml             # Kubernetes deployment
└── docker-compose.tracing.yaml        # Local development setup
```

---

## 🔧 Configuration Files

### 1. Tracing Setup (`tracing.py`)

Core OpenTelemetry configuration:
- TracerProvider setup
- Jaeger exporter configuration
- Auto-instrumentation for FastAPI, SQLAlchemy, HTTPX, Redis
- Custom span context manager
- Tracing decorator for functions

```python
from observability import configure_tracing

# Auto-configure tracing
tracing_manager = configure_tracing(
    app=app,
    service_name="maestro-ml-api"
)
```

### 2. Middleware (`middleware.py`)

HTTP request enrichment:
- `TracingMiddleware` - Adds HTTP metadata to spans
- `TenantContextMiddleware` - Propagates tenant context
- `PerformanceTrackingMiddleware` - Tracks slow requests

```python
from observability import add_tracing_middleware

# Add all middleware
add_tracing_middleware(app)
```

### 3. Jaeger Deployment (`jaeger-deployment.yaml`)

Production-ready Kubernetes deployment:
- All-in-one Jaeger instance
- Security contexts applied
- Resource limits configured
- Persistent storage (Badger)
- Ingress for UI access

---

## 📊 Usage Examples

### Example 1: Automatic Tracing

```python
from fastapi import FastAPI
from observability import configure_tracing, add_tracing_middleware

app = FastAPI()

# Setup tracing - all endpoints automatically traced
configure_tracing(app, service_name="my-service")
add_tracing_middleware(app)

@app.get("/models")  # Automatically traced!
async def list_models():
    return {"models": []}
```

### Example 2: Custom Spans

```python
from observability import trace_span

@app.post("/models/train")
async def train_model(config: dict):
    # Custom span for data loading
    with trace_span("load_training_data", {"dataset": config["dataset"]}):
        data = await load_data(config["dataset"])

    # Custom span for training
    with trace_span("train_model", {"epochs": config["epochs"]}):
        model = await train(data, config)

    return {"model_id": model.id}
```

### Example 3: Function Decorator

```python
from observability import traced

@traced("ml_pipeline")
async def run_ml_pipeline(config: dict):
    # Entire function is traced
    data = await load_data()
    model = await train_model(data)
    results = await evaluate_model(model)
    return results
```

### Example 4: Error Tracking

```python
@app.get("/models/{model_id}")
async def get_model(model_id: str):
    try:
        model = await fetch_model(model_id)
        return model
    except ModelNotFoundError as e:
        # Exception automatically recorded in trace
        raise HTTPException(status_code=404, detail=str(e))
```

---

## 🔍 Viewing Traces

### Jaeger UI Access

**Local Development:**
```bash
open http://localhost:16686
```

**Kubernetes:**
```bash
kubectl port-forward -n observability svc/jaeger 16686:16686
open http://localhost:16686
```

### Finding Traces

1. **Select Service**: `maestro-ml-api`
2. **Set Time Range**: Last 1 hour, Last 24 hours
3. **Filter**:
   - By operation: `GET /models`, `POST /training/jobs`
   - By tags: `http.status_code=500`, `tenant.id=abc123`
   - By duration: `> 1s`
4. **Click "Find Traces"**

### Analyzing Traces

**Trace List:**
- Request duration
- Number of spans
- Error status

**Trace Detail:**
- Timeline visualization
- Span hierarchy (parent → child)
- Duration breakdown
- Attributes and events
- Exception details

**Example Trace:**
```
POST /models/train (5.2s)
├── validate_config (0.1s)
├── load_training_data (2.1s)
│   ├── fetch_from_s3 (1.8s)
│   └── deserialize (0.3s)
├── train_model (2.8s)
│   ├── epoch_1 (0.3s)
│   ├── epoch_2 (0.3s)
│   └── ... (0.3s each)
└── save_model (0.2s)
```

---

## 🎨 Trace Attributes

### Automatic Attributes

Added by middleware:
- `http.method` - GET, POST, etc.
- `http.url` - Full URL
- `http.status_code` - 200, 404, 500
- `http.client_ip` - Client IP
- `http.response_time_ms` - Duration
- `tenant.id` - From x-tenant-id header
- `user.id` - From x-user-id header

### Custom Attributes

Add business context:

```python
from opentelemetry import trace

span = trace.get_current_span()
span.set_attribute("model.id", model_id)
span.set_attribute("model.type", "pytorch")
span.set_attribute("training.epochs", 100)
span.set_attribute("gpu.count", 4)
```

### Span Events

Mark important milestones:

```python
span.add_event("checkpoint_saved", {
    "epoch": 50,
    "loss": 0.23,
    "path": "s3://bucket/checkpoint-50.pt"
})
```

---

## 📈 Performance

### Sampling

Configure sampling to reduce overhead:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of requests in production
tracer_provider = TracerProvider(
    sampler=TraceIdRatioBased(0.1)
)
```

### Batch Export

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000  # Export every 5s
)
```

### Exclude Endpoints

```python
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="health,metrics,readiness"  # Don't trace
)
```

---

## 🔐 Security

### Jaeger Hardening

Already applied in `jaeger-deployment.yaml`:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 3000
  fsGroup: 2000
  capabilities:
    drop: ["ALL"]
```

### Network Policies

Restrict access to Jaeger:

```yaml
# Only allow ML platform services
ingress:
- from:
  - namespaceSelector:
      matchLabels:
        app: ml-platform
```

### Resource Limits

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1"
    memory: "2Gi"
```

---

## 🧪 Testing

### Unit Tests

```python
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

@pytest.fixture
def trace_exporter():
    exporter = InMemorySpanExporter()
    # Setup tracer with exporter
    yield exporter
    exporter.clear()

def test_creates_spans(trace_exporter):
    # Make request
    response = client.post("/models", json={...})

    # Verify spans
    spans = trace_exporter.get_finished_spans()
    assert len(spans) > 0
    assert spans[0].name == "POST /models"
```

### Integration Tests

```bash
# Start Jaeger
docker-compose -f observability/docker-compose.tracing.yaml up -d

# Run tests with tracing enabled
TRACING_ENABLED=true pytest tests/

# View traces in Jaeger
open http://localhost:16686
```

---

## 📚 Documentation

- **[TRACING_GUIDE.md](./TRACING_GUIDE.md)** - Complete tracing guide
  - Configuration options
  - Usage patterns
  - Best practices
  - Troubleshooting
  - Advanced features

- **[api_integration_example.py](./api_integration_example.py)** - Code examples
  - 8 different usage patterns
  - Real-world scenarios
  - Error handling
  - Performance optimization

---

## 🛠️ Troubleshooting

### No traces appearing

1. Check `TRACING_ENABLED=true`
2. Verify Jaeger is running: `docker ps | grep jaeger`
3. Test connectivity: `telnet jaeger.observability.svc.cluster.local 6831`
4. Enable debug logging

### High memory usage

1. Reduce sampling rate
2. Increase batch interval
3. Exclude high-volume endpoints

### Spans not nested

1. Ensure context propagation:
   ```python
   from opentelemetry import context
   ctx = context.get_current()
   with context.attach(ctx):
       await operation()
   ```

---

## 🎯 Common Use Cases

### 1. Debug Slow Requests

Find slow traces → Examine span breakdown → Identify bottleneck → Optimize

### 2. Track ML Pipeline

Trace entire training pipeline from data load to model save

### 3. Multi-Service Tracing

Track requests across API → MLflow → S3 → Database

### 4. Error Investigation

Filter by error status → Examine exception details → Root cause analysis

---

## 📞 Support

- **Documentation**: [TRACING_GUIDE.md](./TRACING_GUIDE.md)
- **Examples**: [api_integration_example.py](./api_integration_example.py)
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **Jaeger Docs**: https://www.jaegertracing.io/docs/

---

## ✅ Checklist

### Development
- [x] OpenTelemetry configured
- [x] Middleware implemented
- [x] Auto-instrumentation working
- [x] Custom spans added
- [x] Error tracking enabled
- [x] Local testing setup

### Production
- [x] Jaeger deployed to Kubernetes
- [x] Security contexts applied
- [x] Resource limits configured
- [x] Network policies created
- [x] Sampling configured
- [x] Documentation complete

---

**Version**: 1.0
**Last Updated**: 2025-10-05
**Status**: ✅ Production Ready
**Phase**: 2 Week 2 Complete
