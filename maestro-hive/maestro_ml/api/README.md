# Maestro ML Platform REST API

**Status**: ✅ Complete
**Quick Win**: #4
**Version**: 1.0.0

FastAPI-based REST API providing unified access to Maestro ML Platform services.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Start the Server

```bash
# Development mode (with auto-reload)
python -m api.main

# Or using uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 📚 API Endpoints

### System

- `GET /` - API information
- `GET /health` - Health check with service status

### Model Registry (`/api/v1/models`)

- `GET /api/v1/models` - List all models
- `GET /api/v1/models/{name}` - Get model details
- `POST /api/v1/models` - Create new model
- `PATCH /api/v1/models/{name}` - Update model metadata
- `DELETE /api/v1/models/{name}` - Delete model
- `GET /api/v1/models/{name}/versions` - Get model versions
- `GET /api/v1/models/{name}/versions/{version}` - Get specific version
- `POST /api/v1/models/{name}/versions/{version}/stage` - Transition stage
- `POST /api/v1/models/{name}/tags` - Set model tag
- `DELETE /api/v1/models/{name}/tags/{key}` - Delete model tag
- `POST /api/v1/models/{name}/versions/{version}/tags` - Set version tag
- `DELETE /api/v1/models/{name}/versions/{version}/tags/{key}` - Delete version tag

### Model Cards (`/api/v1/model-cards`)

- `GET /api/v1/model-cards/{name}/versions/{version}` - Get model card (JSON/Markdown)
- `POST /api/v1/model-cards/{name}/versions/{version}/generate` - Generate PDF model card
- `POST /api/v1/model-cards/{name}/versions/{version}/validate` - Validate model card

---

## 🔧 Configuration

All configuration via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server host |
| `API_PORT` | `8000` | Server port |
| `DEBUG` | `true` | Debug mode |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow tracking server |
| `PDF_SERVICE_URL` | `http://localhost:9550` | PDF generator service |
| `SECRET_KEY` | (required) | JWT secret key |

---

## 📖 Usage Examples

### Model Registry

**List Models**:
```bash
curl http://localhost:8000/api/v1/models
```

**Get Model**:
```bash
curl http://localhost:8000/api/v1/models/fraud-detector
```

**Create Model**:
```bash
curl -X POST http://localhost:8000/api/v1/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-model",
    "description": "My new model",
    "tags": {"team": "data-science"}
  }'
```

**Transition to Production**:
```bash
curl -X POST http://localhost:8000/api/v1/models/fraud-detector/versions/3/stage \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "Production",
    "archive_existing_versions": true
  }'
```

### Model Cards

**Get Model Card (JSON)**:
```bash
curl http://localhost:8000/api/v1/model-cards/fraud-detector/versions/3
```

**Get Model Card (Markdown)**:
```bash
curl http://localhost:8000/api/v1/model-cards/fraud-detector/versions/3?format=markdown \
  -o fraud-detector-v3.md
```

**Generate PDF Model Card**:
```bash
curl -X POST http://localhost:8000/api/v1/model-cards/fraud-detector/versions/3/generate \
  -H "Content-Type: application/json" \
  -d '{
    "overrides": {
      "intended_use": {
        "primary_uses": ["Fraud detection"],
        "out_of_scope": ["Credit scoring"]
      }
    }
  }' \
  -o fraud-detector-v3.pdf
```

---

## 🔒 Authentication

The API supports two authentication methods:

### 1. JWT Bearer Token (Future)

```bash
# Login to get token (endpoint to be implemented)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=user&password=pass"

# Use token
curl http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer <token>"
```

### 2. API Key

```bash
# Set API_KEY_ENABLED=true in .env
# Add keys to API_KEYS list

curl http://localhost:8000/api/v1/models \
  -H "X-API-Key: your-api-key"
```

**Note**: Authentication is currently optional for development. Enable in production by modifying `dependencies/auth.py`.

---

## 🏗️ Architecture

```
api/
├── main.py                 # FastAPI application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment file
├── v1/                     # API v1 routes
│   ├── models.py           # Model registry endpoints
│   └── model_cards.py      # Model cards endpoints
├── schemas/                # Pydantic schemas
│   ├── common.py           # Common schemas
│   └── models.py           # Model schemas
├── dependencies/           # FastAPI dependencies
│   └── auth.py             # Authentication
└── middleware/             # Middleware (rate limiting, etc.)
```

---

## 🧪 Testing

### Manual Testing

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/api/v1/models | jq

# Get specific model
curl http://localhost:8000/api/v1/models/fraud-detector | jq
```

### Integration Tests (Future)

```bash
pytest tests/test_api.py -v
```

---

## 📊 OpenAPI Schema

The API auto-generates OpenAPI 3.0 schema. Access at:

- JSON: http://localhost:8000/openapi.json
- Interactive docs: http://localhost:8000/docs

---

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maestro-api
  namespace: ml-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: maestro-api
  template:
    metadata:
      labels:
        app: maestro-api
    spec:
      containers:
      - name: api
        image: maestro-ml/api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-tracking:5000"
```

---

## 🔌 Client Integration

### Python

```python
import requests

# List models
response = requests.get("http://localhost:8000/api/v1/models")
models = response.json()

# Create model
response = requests.post(
    "http://localhost:8000/api/v1/models",
    json={"name": "new-model", "description": "My model"}
)
```

### JavaScript

```javascript
// List models
const response = await fetch('http://localhost:8000/api/v1/models');
const data = await response.json();

// Create model
const response = await fetch('http://localhost:8000/api/v1/models', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'new-model',
    description: 'My model'
  })
});
```

### Maestro ML SDK

```python
# Future: SDK integration
from maestro_ml import MaestroClient

client = MaestroClient(api_url="http://localhost:8000")
models = client.models.list()
```

---

## 🐛 Troubleshooting

### Issue: "Connection refused to MLflow"

**Solution**:
```bash
# Check MLflow is running
curl http://localhost:5000/health

# Update MLFLOW_TRACKING_URI in .env
```

### Issue: "PDF generation failed"

**Solution**:
```bash
# Start PDF service
cd ~/projects/utilities/services/pdf_generator
python app.py

# Verify it's running
curl http://localhost:9550/health
```

---

## 📝 License

Apache License 2.0

---

**Built for Maestro ML Platform**
**Version**: 1.0.0 | **Date**: 2025-10-04
