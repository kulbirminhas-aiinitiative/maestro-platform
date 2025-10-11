# Maestro ML Python SDK

**Version**: 0.1.0
**Status**: Beta
**License**: Apache 2.0

Official Python SDK for the Maestro ML Platform - A unified, Pythonic interface for MLOps operations.

## 🚀 Quick Win #2 - Python SDK v0.1

This is **Quick Win #2** from the Path A roadmap, providing a clean Python API for common ML platform operations:

- ✅ Model Registry (browse, create, update, version models)
- ✅ Configuration management
- ✅ Type-safe interfaces with Pydantic
- ⏳ Experiment Tracking (coming soon)
- ⏳ Training Job Submission (coming soon)
- ⏳ Model Deployment (coming soon)

---

## 📦 Installation

### From Source (Development)

```bash
# Clone the repository
cd sdk/maestro-ml-sdk

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### From PyPI (When Published)

```bash
pip install maestro-ml
```

---

## 🎯 Quick Start

### 1. Configure Connection

```bash
# Set environment variables
export MAESTRO_ML_MLFLOW_URI=http://localhost:5000
export MAESTRO_ML_NAMESPACE=ml-platform
```

Or create a `.env` file:

```env
MAESTRO_ML_MLFLOW_URI=http://localhost:5000
MAESTRO_ML_NAMESPACE=ml-platform
MAESTRO_ML_VERBOSE=false
```

### 2. Basic Usage

```python
from maestro_ml import MaestroClient

# Initialize the client (auto-loads from environment)
client = MaestroClient()

# List all models
models = client.models.list()
for model in models:
    print(f"{model.name}: {len(model.latest_versions)} versions")

# Get a specific model
model = client.models.get("fraud-detector")
print(f"Latest version: {model.latest_version.version}")
print(f"Production version: {model.production_version}")

# Get a specific version
version = client.models.get_version("fraud-detector", "3")
print(f"Stage: {version.current_stage}")
print(f"Status: {version.status}")

# Transition to production
client.models.transition_version_stage(
    name="fraud-detector",
    version="3",
    stage="Production",
    archive_existing_versions=True
)
```

### 3. Run Example

```bash
cd examples
python quickstart.py
```

---

## 📚 Features

### Model Registry

Interact with the MLflow Model Registry through a clean, Pythonic API:

```python
# List models with filtering
models = client.models.list(max_results=100)
fraud_models = client.models.search("name LIKE '%fraud%'")

# Get model details
model = client.models.get("my-model")
print(f"Description: {model.description}")
print(f"Tags: {model.tags}")
print(f"Latest version: {model.latest_version.version}")

# Get latest versions by stage
prod_versions = client.models.get_latest_versions(
    "my-model",
    stages=["Production"]
)

# Create a new model
model = client.models.create(
    name="new-model",
    description="My new ML model",
    tags={"team": "data-science", "priority": "high"}
)

# Update model metadata
model = client.models.update(
    name="my-model",
    description="Updated description"
)

# Version management
version = client.models.transition_version_stage(
    name="my-model",
    version="5",
    stage="Production",
    archive_existing_versions=True
)

# Tagging
client.models.set_version_tag("my-model", "5", "validated", "true")
client.models.set_version_tag("my-model", "5", "accuracy", "0.95")

# Delete a model
client.models.delete("old-model")
```

### Configuration

Flexible configuration with multiple options:

```python
from maestro_ml import MaestroClient, Config

# Option 1: Auto-load from environment
client = MaestroClient()

# Option 2: Explicit parameters
client = MaestroClient(
    mlflow_uri="http://mlflow.example.com:5000",
    namespace="production"
)

# Option 3: Use Config object
config = Config.from_env()
config.verbose = True
client = MaestroClient(config=config)

# Option 4: Custom .env file
config = Config.from_env(env_file=Path(".env.production"))
client = MaestroClient(config=config)
```

---

## 🔧 Configuration Options

All configuration can be set via environment variables (prefix: `MAESTRO_ML_`) or in code:

| Parameter | Env Variable | Default | Description |
|-----------|--------------|---------|-------------|
| `mlflow_uri` | `MAESTRO_ML_MLFLOW_URI` | `http://localhost:5000` | MLflow tracking server |
| `mlflow_registry_uri` | `MAESTRO_ML_MLFLOW_REGISTRY_URI` | Same as mlflow_uri | Model registry URI |
| `namespace` | `MAESTRO_ML_NAMESPACE` | `ml-platform` | Kubernetes namespace |
| `kube_context` | `MAESTRO_ML_KUBE_CONTEXT` | None | Kubernetes context |
| `kube_config_path` | `MAESTRO_ML_KUBE_CONFIG_PATH` | `~/.kube/config` | Path to kubeconfig |
| `api_url` | `MAESTRO_ML_API_URL` | None | Platform API URL |
| `api_key` | `MAESTRO_ML_API_KEY` | None | API authentication key |
| `request_timeout` | `MAESTRO_ML_REQUEST_TIMEOUT` | `30` | Request timeout (seconds) |
| `verify_ssl` | `MAESTRO_ML_VERIFY_SSL` | `true` | Verify SSL certificates |
| `verbose` | `MAESTRO_ML_VERBOSE` | `false` | Enable verbose logging |

---

## 🏗️ Architecture

```
maestro-ml-sdk/
├── maestro_ml/
│   ├── __init__.py          # Public API
│   ├── client.py            # MaestroClient (main entry point)
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exceptions
│   ├── models/              # Model registry
│   │   ├── __init__.py
│   │   ├── model.py         # Model data classes
│   │   └── registry_client.py  # MLflow wrapper
│   ├── experiments/         # Experiment tracking (coming soon)
│   ├── training/            # Training jobs (coming soon)
│   ├── deployment/          # Model deployment (coming soon)
│   └── utils/               # Shared utilities
├── tests/                   # Unit and integration tests
├── examples/                # Usage examples
├── docs/                    # Documentation
├── pyproject.toml           # Package configuration
└── README.md                # This file
```

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=maestro_ml --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

---

## 📖 Examples

### Example 1: Model Lifecycle

```python
from maestro_ml import MaestroClient

client = MaestroClient()

# Create a new model
model = client.models.create(
    name="customer-churn",
    description="Predicts customer churn probability",
    tags={"team": "growth", "business_unit": "retail"}
)

# Register version 1 (usually done during training)
# ... training happens here ...

# Get the latest version
version = client.models.get_latest_versions("customer-churn")[0]

# Transition to staging
client.models.transition_version_stage(
    name="customer-churn",
    version=version.version,
    stage="Staging"
)

# After validation, promote to production
client.models.transition_version_stage(
    name="customer-churn",
    version=version.version,
    stage="Production",
    archive_existing_versions=True  # Archive old production version
)
```

### Example 2: Model Comparison

```python
# Compare all versions of a model
model = client.models.get("fraud-detector")

print(f"Model: {model.name}")
print(f"Total versions: {len(model.latest_versions)}")
print()

for version in model.latest_versions:
    print(f"Version {version.version}:")
    print(f"  Stage: {version.current_stage}")
    print(f"  Status: {version.status}")
    print(f"  Created: {version.creation_timestamp}")
    print(f"  Tags: {version.tags}")
    print()
```

### Example 3: Batch Operations

```python
# Get all production models
models = client.models.list()
production_models = [
    model for model in models
    if model.production_version is not None
]

print(f"Found {len(production_models)} models in production:")
for model in production_models:
    prod = model.production_version
    print(f"  {model.name} v{prod.version}")
```

---

## 🚧 Roadmap

### v0.1.0 (Current) - Model Registry
- ✅ MLflow model registry wrapper
- ✅ Configuration management
- ✅ Pydantic data models
- ✅ Basic examples
- ✅ Unit tests

### v0.2.0 (Week 2) - Training & Deployment
- ⏳ Training job submission (Kubeflow)
- ⏳ Model deployment (KServe)
- ⏳ Job monitoring
- ⏳ Deployment management

### v0.3.0 (Week 3) - Experiments & Features
- ⏳ Experiment tracking
- ⏳ Feature store integration (Feast)
- ⏳ Run comparison
- ⏳ Metrics visualization

### v1.0.0 (Week 4) - Production Ready
- ⏳ Complete API coverage
- ⏳ CLI tool (`maestro-ml`)
- ⏳ Comprehensive documentation
- ⏳ PyPI publication
- ⏳ Integration tests

---

## 🤝 Contributing

```bash
# Setup development environment
git clone <repo>
cd sdk/maestro-ml-sdk
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests before committing
pytest
black maestro_ml tests
isort maestro_ml tests
mypy maestro_ml
```

---

## 📝 API Reference

### MaestroClient

Main entry point for the SDK.

**Initialization:**
```python
client = MaestroClient(
    mlflow_uri="http://localhost:5000",  # Optional
    namespace="ml-platform",              # Optional
    config=None                            # Or provide Config object
)
```

**Properties:**
- `client.models` - ModelRegistryClient
- `client.experiments` - ExperimentsClient (coming soon)
- `client.training` - TrainingClient (coming soon)
- `client.deployment` - DeploymentClient (coming soon)

### ModelRegistryClient

Interface to MLflow Model Registry.

**Methods:**
- `list(max_results=100, filter_string=None)` - List models
- `get(name)` - Get model by name
- `get_version(name, version)` - Get specific version
- `get_latest_versions(name, stages=None)` - Get latest versions
- `create(name, description=None, tags=None)` - Create model
- `update(name, description)` - Update model
- `delete(name)` - Delete model
- `transition_version_stage(name, version, stage, archive_existing_versions=False)` - Change stage
- `set_version_tag(name, version, key, value)` - Add tag
- `delete_version_tag(name, version, key)` - Remove tag
- `search(filter_string, max_results=100)` - Search models

---

## 🆘 Troubleshooting

### Issue: Cannot connect to MLflow

**Error:** `MLflowException: Failed to connect to MLflow`

**Solution:**
```bash
# Check MLflow is running
curl http://localhost:5000/health

# Verify environment variable
echo $MAESTRO_ML_MLFLOW_URI

# Or use port-forwarding
kubectl port-forward -n ml-platform svc/mlflow-tracking 5000:5000
```

### Issue: Model not found

**Error:** `ModelNotFoundException: Model 'xyz' not found`

**Solution:**
```python
# List all models to check name
models = client.models.list()
for model in models:
    print(model.name)
```

### Issue: Authentication errors

**Error:** `AuthenticationException`

**Solution:**
```bash
# Set API key (if required)
export MAESTRO_ML_API_KEY=your-api-key
```

---

## 📄 License

Apache License 2.0 - See LICENSE file for details

---

## 🔗 Links

- **Documentation**: https://docs.maestro-ml.io
- **GitHub**: https://github.com/maestro-ml/maestro-ml-sdk
- **Issue Tracker**: https://github.com/maestro-ml/maestro-ml-sdk/issues
- **PyPI**: https://pypi.org/project/maestro-ml/ (coming soon)

---

## ✅ Quick Win Status

**Current Progress**: 60% (Week 1 of 2)

- [x] Package structure
- [x] Configuration management
- [x] Model registry client
- [x] Pydantic data models
- [x] Exception handling
- [x] Examples
- [x] Basic documentation
- [ ] Training job submission (Week 2)
- [ ] Deployment operations (Week 2)
- [ ] PyPI package (Week 2)
- [ ] Complete documentation (Week 2)

**Estimated Completion**: End of Week 2 (Q1 2025)

---

**Built with ❤️ by the Maestro ML Team**
**Version**: 0.1.0 | **Status**: Beta | **Date**: 2025-10-04
