# Health Check API Documentation

## Overview
Simple REST API providing a health check endpoint for service monitoring and availability verification.

## Base Information
- **Framework**: FastAPI 0.104.1
- **Python Version**: 3.8+
- **Server**: Uvicorn

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### GET /health

Returns the current health status of the service.

**Endpoint**: `/health`

**Method**: `GET`

**Authentication**: Not required

**Request Parameters**: None

**Response**:
- **Status Code**: `200 OK`
- **Content-Type**: `application/json`

**Response Schema**:
```json
{
  "status": "string",
  "timestamp": "string (ISO 8601 format)"
}
```

**Example Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-10-09T12:34:56.789012"
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/health"
```

**Python Example**:
```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
```

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Examples

### Starting the Server

Default (development):
```bash
uvicorn main:app
```

With auto-reload for development:
```bash
uvicorn main:app --reload
```

Production configuration:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing the Endpoint

Using curl:
```bash
curl http://localhost:8000/health
```

Using httpie:
```bash
http GET http://localhost:8000/health
```

Using Python requests:
```python
import requests
response = requests.get("http://localhost:8000/health")
assert response.status_code == 200
assert response.json()["status"] == "ok"
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| status | string | Health status of the service (always "ok" when service is running) |
| timestamp | string | Current UTC timestamp in ISO 8601 format |

## Error Handling

This endpoint does not return error responses under normal circumstances. If the endpoint is unreachable, the service may be down or experiencing network issues.

## Monitoring & Health Checks

This endpoint is designed for:
- Container orchestration health checks (Kubernetes, Docker)
- Load balancer health monitoring
- Uptime monitoring services
- CI/CD pipeline verification

## Performance

- **Response Time**: < 10ms typical
- **Rate Limiting**: None
- **Caching**: Not applicable

## Version History

- **v1.0.0** (2025-10-09): Initial release with basic health check endpoint
