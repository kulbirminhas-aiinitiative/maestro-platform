"""
Example: Integrating OpenTelemetry Tracing with FastAPI

This file demonstrates how to add distributed tracing to the Maestro ML API.
"""

from fastapi import FastAPI, Depends
from observability import configure_tracing, add_tracing_middleware, traced, trace_span

# Create FastAPI app
app = FastAPI(
    title="Maestro ML Platform",
    version="1.0.0"
)

# Configure distributed tracing
tracing_manager = configure_tracing(
    app=app,
    service_name="maestro-ml-api"
)

# Add tracing middleware
add_tracing_middleware(app)


# Example 1: Automatic tracing (all endpoints are auto-traced)
@app.get("/models")
async def list_models():
    """All FastAPI endpoints are automatically traced."""
    # Tracing is automatic - no code changes needed
    return {"models": []}


# Example 2: Manual span for specific operations
@app.post("/models")
async def create_model(model_data: dict):
    """Create a model with custom span for validation."""

    # Create custom span for validation
    with trace_span("validate_model_data", attributes={"model_type": model_data.get("type")}):
        # Validation logic here
        if not model_data.get("name"):
            raise ValueError("Model name required")

    # Create custom span for database save
    with trace_span("save_model_to_db", attributes={"model_id": "123"}):
        # Database save logic here
        pass

    return {"model_id": "123"}


# Example 3: Using decorator for function tracing
@traced("training_job_execution")
async def execute_training_job(job_id: str, config: dict):
    """Execute training job with automatic tracing."""

    # This entire function is traced
    with trace_span("load_dataset"):
        # Load dataset
        pass

    with trace_span("train_model", attributes={"epochs": config.get("epochs", 10)}):
        # Training logic
        pass

    return {"status": "completed"}


@app.post("/training/jobs")
async def submit_training_job(job_config: dict):
    """Submit training job endpoint."""
    job_id = "job-123"

    # Call traced function
    result = await execute_training_job(job_id, job_config)

    return result


# Example 4: Tracing database queries
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends()):
    """Get project - database queries are automatically traced."""

    # SQLAlchemy queries are automatically traced
    # with trace_span("database.query") already applied
    with trace_span("fetch_project", attributes={"project_id": project_id}):
        # query = select(Project).where(Project.id == project_id)
        # result = await db.execute(query)
        # project = result.scalar_one_or_none()
        pass

    return {"project_id": project_id}


# Example 5: Tracing external HTTP calls
import httpx

@app.get("/external/data")
async def fetch_external_data():
    """Fetch data from external service - HTTP calls are traced."""

    # HTTPX client calls are automatically traced
    async with httpx.AsyncClient() as client:
        # This call will appear in traces
        response = await client.get("https://api.example.com/data")

    return response.json()


# Example 6: Adding custom events to spans
from opentelemetry import trace

@app.post("/models/{model_id}/deploy")
async def deploy_model(model_id: str, config: dict):
    """Deploy model with trace events."""

    span = trace.get_current_span()

    # Add event to current span
    span.add_event(
        "deployment_started",
        attributes={
            "model_id": model_id,
            "target_environment": config.get("environment", "production"),
            "replicas": config.get("replicas", 1)
        }
    )

    # Deployment logic here
    with trace_span("create_k8s_deployment"):
        pass

    # Add completion event
    span.add_event(
        "deployment_completed",
        attributes={"deployment_id": "deploy-123"}
    )

    return {"deployment_id": "deploy-123", "status": "running"}


# Example 7: Error tracking in traces
@app.get("/models/{model_id}/metrics")
async def get_model_metrics(model_id: str):
    """Get model metrics - errors are automatically recorded in traces."""

    try:
        # Simulated error
        if model_id == "invalid":
            raise ValueError("Invalid model ID")

        with trace_span("fetch_metrics", attributes={"model_id": model_id}):
            # Metrics fetching logic
            metrics = {"accuracy": 0.95}

        return metrics

    except Exception as e:
        # Exception is automatically recorded in the span
        # and marked as error status
        raise


# Example 8: Tenant-specific tracing
@app.get("/tenant/resources")
async def get_tenant_resources(tenant_id: str):
    """Get tenant resources - tenant context is automatically added to traces."""

    # Tenant ID from header (x-tenant-id) is automatically added to trace
    span = trace.get_current_span()

    # Additional tenant attributes
    span.set_attribute("tenant.resource_count", 10)
    span.set_attribute("tenant.quota_usage", 0.75)

    with trace_span("fetch_tenant_resources", attributes={"tenant_id": tenant_id}):
        # Resource fetching logic
        pass

    return {"resources": []}


# Environment configuration
# Set these in your .env file:
# TRACING_ENABLED=true
# JAEGER_AGENT_HOST=jaeger.observability.svc.cluster.local
# JAEGER_AGENT_PORT=6831

"""
Viewing Traces in Jaeger:

1. Port-forward Jaeger UI:
   kubectl port-forward -n observability svc/jaeger 16686:16686

2. Open browser:
   http://localhost:16686

3. Select service:
   - Service: maestro-ml-api
   - Find traces

4. View trace details:
   - Click on trace to see span tree
   - View timing information
   - See custom attributes and events
   - Inspect errors and exceptions

Trace Structure:
- HTTP Request (root span)
  ├── validate_model_data
  ├── save_model_to_db
  │   └── database.query
  └── external_api_call
      └── http.request

Custom Attributes in Traces:
- http.method, http.url, http.status_code
- tenant.id (from x-tenant-id header)
- user.id (from x-user-id header)
- model_id, project_id (custom business logic)
- performance.duration_ms
- performance.slow_request (if > 1 second)
"""
