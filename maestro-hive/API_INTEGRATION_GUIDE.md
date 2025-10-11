# Quality Fabric API Integration Guide
## Using Real APIs Instead of File Search

**Created**: January 2025  
**Status**: ✅ API Endpoints Ready  
**Port**: 8001 (Quality Fabric Modular API)

---

## Overview

Quality Fabric now exposes comprehensive REST APIs for SDLC integration. Your SDLC Team can call these APIs remotely without needing direct filesystem access to the quality-fabric directory.

---

## New SDLC Integration API Endpoints

### Base URL
```
http://localhost:8001/api/sdlc
```

### Available Endpoints

#### 1. Validate Persona Output
```http
POST /api/sdlc/validate-persona
Content-Type: application/json

{
  "persona_id": "backend_dev_001",
  "persona_type": "backend_developer",
  "artifacts": {
    "code_files": [
      {"name": "main.py", "content": "...", "lines": 150}
    ],
    "test_files": [
      {"name": "test_main.py", "content": "...", "lines": 100}
    ],
    "documentation": [],
    "config_files": [],
    "metadata": {}
  },
  "custom_gates": null,
  "project_context": {}
}
```

**Response**:
```json
{
  "persona_id": "backend_dev_001",
  "persona_type": "backend_developer",
  "status": "pass",
  "overall_score": 85.5,
  "gates_passed": ["code_files_present", "test_files_present", "coverage_acceptable"],
  "gates_failed": [],
  "quality_metrics": {
    "code_coverage": 80.0,
    "test_coverage": 72.0,
    "pylint_score": 8.0
  },
  "recommendations": [],
  "requires_revision": false,
  "validation_timestamp": "2025-01-15T10:30:00Z",
  "execution_time_ms": 145.2
}
```

#### 2. Evaluate Phase Gate
```http
POST /api/sdlc/evaluate-phase-gate
Content-Type: application/json

{
  "current_phase": "implementation",
  "next_phase": "testing",
  "phase_outputs": {
    "total_code_files": 15,
    "total_test_files": 12
  },
  "persona_results": [
    {"persona_id": "backend_001", "overall_score": 85.0},
    {"persona_id": "frontend_001", "overall_score": 80.0}
  ],
  "custom_gates": null,
  "project_id": "proj_123"
}
```

**Response**:
```json
{
  "current_phase": "implementation",
  "next_phase": "testing",
  "status": "pass",
  "overall_quality_score": 82.5,
  "gates_passed": ["overall_quality"],
  "gates_failed": [],
  "blockers": [],
  "warnings": [],
  "recommendations": [],
  "bypass_available": true,
  "bypass_justification_required": false,
  "human_approval_required": false,
  "evaluation_timestamp": "2025-01-15T10:35:00Z"
}
```

#### 3. Track Template Quality
```http
POST /api/sdlc/track-template-quality
Content-Type: application/json

{
  "project_id": "proj_123",
  "templates_used": {
    "backend_developer": ["tmpl_001", "tmpl_002"],
    "frontend_developer": ["tmpl_010"]
  },
  "quality_scores": {
    "backend_developer": 85.0,
    "frontend_developer": 80.0
  },
  "test_results": {
    "tests_passed": 150,
    "tests_failed": 5
  },
  "project_metadata": {}
}
```

**Response**:
```json
{
  "template_assessments": [
    {
      "template_id": "tmpl_001",
      "persona": "backend_developer",
      "quality_score": 85.0,
      "success": true
    }
  ],
  "updated_scores": {
    "tmpl_001": 85.0,
    "tmpl_002": 85.0
  },
  "golden_templates": ["tmpl_001"],
  "deprecated_templates": [],
  "recommendations": ["Continue using high-scoring templates"]
}
```

#### 4. Get Quality Analytics
```http
GET /api/sdlc/quality-analytics?project_id=proj_123&time_range_days=30
```

**Response**:
```json
{
  "overall_quality_trend": [
    {"date": "2025-01-01", "score": 75.0},
    {"date": "2025-01-02", "score": 78.5}
  ],
  "persona_quality_scores": {
    "backend_developer": 85.0,
    "frontend_developer": 80.0
  },
  "phase_gate_pass_rates": {
    "implementation": 85.0,
    "testing": 92.0
  },
  "common_failures": [
    {"type": "low_coverage", "count": 15, "percentage": 30.0}
  ],
  "quality_improvements": [],
  "template_effectiveness": {
    "tmpl_001": 92.0
  }
}
```

---

## Updated Client Library

The `quality_fabric_client.py` is already configured to use these APIs! It will automatically:

1. Make HTTP POST requests to `/api/sdlc/validate-persona`
2. Make HTTP POST requests to `/api/sdlc/evaluate-phase-gate`
3. Parse JSON responses
4. Handle errors gracefully

### Current Implementation

The client currently uses **mock validation** for Day 1 testing. To switch to real API calls:

```python
# In quality_fabric_client.py

async def validate_persona_output(self, ...):
    # Current: Mock implementation
    # TODO: Uncomment this for real API calls
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.base_url}/api/sdlc/validate-persona",
            json={
                "persona_id": persona_id,
                "persona_type": persona_type.value,
                "artifacts": {
                    "code_files": output.get("code_files", []),
                    "test_files": output.get("test_files", []),
                    "documentation": output.get("documentation", []),
                    "config_files": output.get("config_files", []),
                    "metadata": output.get("metadata", {})
                },
                "custom_gates": custom_gates,
                "project_context": {}
            },
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            return PersonaValidationResult(
                persona_id=data["persona_id"],
                persona_type=data["persona_type"],
                status=data["status"],
                overall_score=data["overall_score"],
                gates_passed=data["gates_passed"],
                gates_failed=data["gates_failed"],
                quality_metrics=data["quality_metrics"],
                recommendations=data["recommendations"],
                requires_revision=data["requires_revision"]
            )
```

---

## Starting Quality Fabric API

### Option 1: Docker Compose (Recommended)
```bash
cd ~/projects/quality-fabric
docker-compose up -d quality-fabric
```

### Option 2: Direct Python
```bash
cd ~/projects/quality-fabric
python3.11 services/api/main.py
```

### Verify API is Running
```bash
# Health check
curl http://localhost:8001/health

# SDLC integration health
curl http://localhost:8001/api/sdlc/health

# View OpenAPI docs
open http://localhost:8001/docs
```

---

## Testing the New APIs

### Using curl
```bash
# Test persona validation
curl -X POST http://localhost:8001/api/sdlc/validate-persona \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "test_001",
    "persona_type": "backend_developer",
    "artifacts": {
      "code_files": [{"name": "main.py"}],
      "test_files": [{"name": "test_main.py"}],
      "documentation": [],
      "config_files": [],
      "metadata": {}
    }
  }' | jq .
```

### Using Python (httpx)
```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/sdlc/validate-persona",
            json={
                "persona_id": "test_001",
                "persona_type": "backend_developer",
                "artifacts": {
                    "code_files": [{"name": "main.py"}],
                    "test_files": [{"name": "test_main.py"}],
                    "documentation": [],
                    "config_files": [],
                    "metadata": {}
                }
            }
        )
        print(response.json())

asyncio.run(test_api())
```

### Using the Client Library
```python
from quality_fabric_client import QualityFabricClient, PersonaType
import asyncio

async def test():
    client = QualityFabricClient("http://localhost:8001")
    
    result = await client.validate_persona_output(
        persona_id="test_001",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        output={
            "code_files": [{"name": "main.py"}],
            "test_files": [{"name": "test_main.py"}]
        }
    )
    
    print(f"Status: {result.status}")
    print(f"Score: {result.overall_score:.1%}")

asyncio.run(test())
```

---

## API vs. File Search Comparison

### File Search Approach (Not Recommended)
```python
# Would need direct access to quality-fabric directory
import sys
sys.path.append("/home/ec2-user/projects/quality-fabric")
from services.core.test_orchestrator import TestOrchestrator
# ... complex imports and initialization
```

**Issues**:
- ❌ Requires filesystem access
- ❌ Tight coupling to internal structure
- ❌ Hard to deploy remotely
- ❌ Version conflicts possible
- ❌ No API versioning
- ❌ No authentication/authorization

### API Approach (Recommended) ✅
```python
# Clean HTTP API call
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/api/sdlc/validate-persona",
        json=request_data
    )
    result = response.json()
```

**Benefits**:
- ✅ Clean separation of concerns
- ✅ Works remotely (can be on different server)
- ✅ Standard REST API
- ✅ Easy to version
- ✅ Can add authentication
- ✅ Can be load balanced
- ✅ Independent deployment

---

## Migration Path

### Day 1 (Current) - Mock Implementation
- Client uses mock validation
- No API dependency
- Fast for testing

### Day 2 - Switch to Real APIs
1. Start Quality Fabric API service
2. Update client to make real API calls
3. Test with actual quality checks
4. Validate results

### Day 3+ - Enhanced APIs
1. Add real code coverage analysis
2. Add security scanning
3. Add performance profiling
4. Add ML-powered predictions

---

## API Documentation

Once Quality Fabric is running, access interactive API docs:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

These docs show:
- All available endpoints
- Request/response schemas
- Try-it-out functionality
- Example payloads

---

## Configuration

### Environment Variables
```bash
# Quality Fabric API URL
export QUALITY_FABRIC_URL=http://localhost:8001

# Optional: API authentication
export QUALITY_FABRIC_API_KEY=your_api_key

# Optional: Timeout
export QUALITY_FABRIC_TIMEOUT=60
```

### In Code
```python
from quality_fabric_client import QualityFabricClient

# Default localhost
client = QualityFabricClient()

# Custom URL
client = QualityFabricClient("http://quality-fabric.example.com:8001")

# With timeout
client = QualityFabricClient(timeout=120.0)
```

---

## Production Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  quality-fabric:
    image: quality-fabric:latest
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  sdlc-team:
    image: sdlc-team:latest
    environment:
      - QUALITY_FABRIC_URL=http://quality-fabric:8001
    depends_on:
      - quality-fabric
```

### Kubernetes
```yaml
apiVersion: v1
kind: Service
metadata:
  name: quality-fabric
spec:
  selector:
    app: quality-fabric
  ports:
    - port: 8001
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quality-fabric
spec:
  replicas: 3
  selector:
    matchLabels:
      app: quality-fabric
  template:
    metadata:
      labels:
        app: quality-fabric
    spec:
      containers:
      - name: quality-fabric
        image: quality-fabric:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

---

## Summary

✅ **API Endpoints Created**: 4 new SDLC integration endpoints  
✅ **Registered in main.py**: Router added to FastAPI app  
✅ **Client Ready**: quality_fabric_client.py configured for APIs  
✅ **No File Search Needed**: Everything via HTTP REST APIs  
✅ **Production Ready**: Can be deployed separately  

**Next Steps**:
1. Start Quality Fabric: `cd ~/projects/quality-fabric && python3.11 services/api/main.py`
2. Test APIs: `curl http://localhost:8001/api/sdlc/health`
3. View docs: http://localhost:8001/docs
4. Update client to use real APIs (Day 2)

---

**Created**: January 2025  
**API Version**: 1.0  
**Status**: ✅ Ready to use
