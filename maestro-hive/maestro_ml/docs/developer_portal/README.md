# Maestro ML Platform - Developer Portal

Welcome to the Maestro ML Platform Developer Documentation. This guide will help you get started with building ML applications on our platform.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Core Concepts](#core-concepts)
4. [API Reference](#api-reference)
5. [SDKs](#sdks)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

Get up and running with Maestro ML in 5 minutes.

### Installation

```bash
# Install Python SDK
pip install maestro-ml

# Or use the CLI
pip install maestro-ml-cli
```

### Hello World Example

```python
from maestro_ml import MaestroClient

# Initialize client
client = MaestroClient(
    api_url="https://api.maestro-ml.com",
    api_key="your-api-key"
)

# Create a project
project = client.projects.create(
    name="My First Project",
    description="Getting started with Maestro ML"
)

# Train a model
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

# Load data
X, y = load_iris(return_X_y=True)

# Train model
model = RandomForestClassifier()
model.fit(X, y)

# Register model
registered_model = client.models.register(
    project_id=project.id,
    model=model,
    name="iris_classifier",
    framework="sklearn"
)

print(f"Model registered: {registered_model.id}")
```

---

## Authentication

### API Keys

Generate an API key from your dashboard:

```python
client = MaestroClient(api_key="mml_abc123...")
```

### Service Accounts

For production deployments:

```python
from maestro_ml.auth import ServiceAccount

sa = ServiceAccount.from_file("service-account.json")
client = MaestroClient(auth=sa)
```

### Environment Variables

```bash
export MAESTRO_ML_API_KEY=mml_abc123...
export MAESTRO_ML_API_URL=https://api.maestro-ml.com
```

```python
# Auto-loads from environment
client = MaestroClient()
```

---

## Core Concepts

### Projects

Projects are the top-level organizational unit.

```python
# Create project
project = client.projects.create(
    name="Customer Churn Prediction",
    description="Predict customer churn using historical data"
)

# List projects
projects = client.projects.list()

# Get project
project = client.projects.get("project-id")

# Update project
project.update(
    success_metrics={
        "accuracy": 0.95,
        "f1_score": 0.92
    }
)
```

### Models

Models represent trained ML models.

```python
# Register model
model = client.models.register(
    project_id=project.id,
    model=trained_model,
    name="churn_predictor_v1",
    framework="pytorch",
    metadata={
        "training_data": "customers_2024.csv",
        "features": ["age", "tenure", "monthly_charges"]
    }
)

# List models
models = client.models.list(project_id=project.id)

# Get model
model = client.models.get("model-id")

# Load model for inference
loaded_model = client.models.load("model-id")
predictions = loaded_model.predict(X_test)
```

### Experiments

Track and compare different model training runs.

```python
# Start experiment
with client.experiments.run(
    project_id=project.id,
    name="hyperparameter_tuning"
) as experiment:
    # Log parameters
    experiment.log_params({
        "learning_rate": 0.01,
        "epochs": 100,
        "batch_size": 32
    })

    # Train model
    for epoch in range(100):
        loss = train_epoch(model, data)

        # Log metrics
        experiment.log_metrics({
            "loss": loss,
            "epoch": epoch
        })

    # Log model
    experiment.log_model(model, "final_model")
```

### Artifacts

Store and retrieve any file (datasets, configs, reports).

```python
# Upload artifact
artifact = client.artifacts.upload(
    project_id=project.id,
    file_path="data/training_data.csv",
    artifact_type="dataset",
    tags=["training", "v2"]
)

# Download artifact
client.artifacts.download(
    artifact_id=artifact.id,
    destination="local_data.csv"
)

# Search artifacts
artifacts = client.artifacts.search(
    project_id=project.id,
    tags=["dataset"],
    artifact_type="dataset"
)
```

---

## API Reference

### REST API

Base URL: `https://api.maestro-ml.com/api/v1`

#### Projects

**Create Project**
```http
POST /projects
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "My Project",
  "description": "Project description"
}
```

**Get Projects**
```http
GET /projects?limit=10&offset=0
Authorization: Bearer <api_key>
```

**Get Project**
```http
GET /projects/{project_id}
Authorization: Bearer <api_key>
```

**Update Project**
```http
PUT /projects/{project_id}
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "success_metrics": {
    "accuracy": 0.95
  }
}
```

#### Models

**Register Model**
```http
POST /models
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "project_id": "proj_123",
  "name": "my_model",
  "framework": "pytorch",
  "version": "1.0.0"
}
```

**Deploy Model**
```http
POST /models/{model_id}/deploy
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "environment": "production",
  "replicas": 3
}
```

#### Experiments

**Create Experiment**
```http
POST /experiments
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "project_id": "proj_123",
  "name": "experiment_1",
  "parameters": {
    "lr": 0.01
  }
}
```

**Log Metrics**
```http
POST /experiments/{experiment_id}/metrics
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "metrics": {
    "accuracy": 0.95,
    "loss": 0.05
  },
  "step": 100
}
```

### GraphQL API

Available at: `https://api.maestro-ml.com/graphql`

```graphql
query GetProject($id: ID!) {
  project(id: $id) {
    id
    name
    description
    models {
      id
      name
      version
      status
    }
    experiments {
      id
      name
      status
      metrics {
        accuracy
        loss
      }
    }
  }
}
```

---

## SDKs

### Python SDK

```bash
pip install maestro-ml
```

**Documentation**: [Python SDK Docs](./sdk/python.md)

### JavaScript/TypeScript SDK

```bash
npm install @maestro-ml/sdk
```

```typescript
import { MaestroClient } from '@maestro-ml/sdk'

const client = new MaestroClient({
  apiKey: process.env.MAESTRO_ML_API_KEY
})

// Create project
const project = await client.projects.create({
  name: 'My Project'
})
```

### CLI

```bash
pip install maestro-ml-cli
```

```bash
# Login
maestro login

# Create project
maestro projects create "My Project"

# List models
maestro models list --project-id proj_123

# Deploy model
maestro models deploy model_456 --env production
```

---

## Examples

### Complete ML Pipeline

```python
from maestro_ml import MaestroClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pandas as pd

# Initialize
client = MaestroClient()

# Create project
project = client.projects.create(name="Customer Churn")

# Load and prepare data
df = pd.read_csv("customers.csv")
X = df.drop("churn", axis=1)
y = df["churn"]
X_train, X_test, y_train, y_test = train_test_split(X, y)

# Upload dataset as artifact
client.artifacts.upload(
    project_id=project.id,
    file_path="customers.csv",
    artifact_type="dataset"
)

# Start experiment
with client.experiments.run(
    project_id=project.id,
    name="random_forest_baseline"
) as experiment:
    # Log parameters
    experiment.log_params({
        "n_estimators": 100,
        "max_depth": 10
    })

    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X_train, y_train)

    # Evaluate
    accuracy = model.score(X_test, y_test)

    # Log metrics
    experiment.log_metrics({"accuracy": accuracy})

    # Register model
    registered_model = experiment.log_model(
        model,
        name="churn_predictor"
    )

# Deploy model
client.models.deploy(
    registered_model.id,
    environment="production"
)

print(f"Model deployed: {registered_model.id}")
```

### Real-time Inference

```python
# Load deployed model
model = client.models.load("model_123")

# Make predictions
predictions = model.predict({
    "age": 35,
    "tenure": 24,
    "monthly_charges": 79.99
})

print(f"Churn probability: {predictions['churn_probability']}")
```

### Batch Predictions

```python
# Submit batch job
job = client.batch.submit(
    model_id="model_123",
    input_data="s3://my-bucket/input.csv",
    output_location="s3://my-bucket/predictions/"
)

# Monitor job
while job.status != "completed":
    time.sleep(10)
    job.refresh()
    print(f"Progress: {job.progress}%")

# Download results
client.batch.download_results(job.id, "predictions.csv")
```

---

## Best Practices

### 1. Project Organization

- Use descriptive project names
- Add comprehensive descriptions
- Tag related projects
- Track success metrics

### 2. Model Versioning

```python
# Use semantic versioning
client.models.register(
    model=model,
    name="churn_predictor",
    version="1.2.0",  # major.minor.patch
    changelog="Improved feature engineering"
)
```

### 3. Experiment Tracking

```python
# Track everything
experiment.log_params(hyperparameters)
experiment.log_metrics(validation_metrics)
experiment.log_artifacts(["config.yaml", "plots/"])
experiment.log_model(model)
```

### 4. Error Handling

```python
from maestro_ml.exceptions import MaestroMLError

try:
    model = client.models.load("model_123")
except MaestroMLError as e:
    logger.error(f"Failed to load model: {e}")
    # Fallback to previous version
    model = client.models.load("model_122")
```

### 5. Resource Cleanup

```python
# Use context managers
with client.experiments.run(...) as experiment:
    # Experiment is auto-completed/failed
    train_model()

# Or explicit cleanup
experiment = client.experiments.create(...)
try:
    train_model()
    experiment.complete()
except Exception as e:
    experiment.fail(error=str(e))
```

---

## Troubleshooting

### Authentication Issues

**Problem**: `401 Unauthorized`

**Solution**:
```python
# Verify API key
print(client.auth.verify())

# Refresh token
client.auth.refresh()
```

### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solution**:
```python
from maestro_ml.retry import with_retry

@with_retry(max_attempts=3, backoff=2.0)
def upload_artifact():
    return client.artifacts.upload(...)
```

### Large File Uploads

**Problem**: Upload timeout

**Solution**:
```python
# Use multipart upload for files > 100MB
client.artifacts.upload_multipart(
    file_path="large_dataset.parquet",
    chunk_size=10 * 1024 * 1024  # 10MB chunks
)
```

### Model Loading Issues

**Problem**: Model not loading

**Solution**:
```python
# Check model status
model = client.models.get("model_123")
print(f"Status: {model.status}")

# Verify framework compatibility
print(f"Framework: {model.framework} {model.framework_version}")

# Load with specific version
model = client.models.load("model_123", framework_version="2.0.0")
```

---

## Support

- **Documentation**: https://docs.maestro-ml.com
- **API Reference**: https://api.maestro-ml.com/docs
- **Community Forum**: https://community.maestro-ml.com
- **GitHub**: https://github.com/maestro-ml/platform
- **Email**: support@maestro-ml.com

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.

## License

See [LICENSE](./LICENSE) for details.
