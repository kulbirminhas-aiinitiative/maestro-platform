# API Documentation

## Producer Service API (Port 8080)

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "producer",
  "timestamp": "2025-09-30T12:00:00.000000"
}
```

### Ingest Single Event

```http
POST /api/events
Content-Type: application/json
```

**Request Body**:
```json
{
  "event_id": "evt_123",
  "event_type": "user_action",
  "timestamp": "2025-09-30T12:00:00.000000",
  "data": {
    "user_id": "user_123",
    "action": "click",
    "value": 42,
    "region": "us-east"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "event_id": "evt_123",
  "topic": "events.user_action",
  "partition": 0,
  "offset": 12345
}
```

### Ingest Batch Events

```http
POST /api/events/batch
Content-Type: application/json
```

**Request Body**:
```json
[
  {
    "event_type": "transaction",
    "data": {
      "amount": 99.99,
      "currency": "USD"
    }
  },
  {
    "event_type": "page_view",
    "data": {
      "page": "/home",
      "user_id": "user_456"
    }
  }
]
```

**Response**:
```json
{
  "status": "success",
  "count": 2,
  "results": [
    {"event_id": "evt_1001", "status": "submitted"},
    {"event_id": "evt_1002", "status": "submitted"}
  ]
}
```

### Simulate Traffic

```http
POST /api/simulate
Content-Type: application/json
```

**Request Body**:
```json
{
  "num_events": 1000,
  "event_type": "random"
}
```

**Response**:
```json
{
  "status": "success",
  "events_generated": 1000
}
```

### Get Metrics

```http
GET /metrics
```

**Response**:
```json
{
  "producer_metrics": {
    "record_send_rate": 1234.56,
    "record_error_rate": 0.12,
    "request_latency_avg": 45.3
  }
}
```

## API Service (Port 8081)

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "api",
  "timestamp": "2025-09-30T12:00:00.000000",
  "dependencies": {
    "postgres": "connected",
    "redis": "connected"
  }
}
```

### Query Events

```http
GET /api/events?event_type=user_action&start_time=2025-09-30T00:00:00&limit=100&offset=0
```

**Query Parameters**:
- `event_type` (optional): Filter by event type
- `start_time` (optional): Start timestamp (ISO 8601)
- `end_time` (optional): End timestamp (ISO 8601)
- `limit` (optional): Maximum results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
  "events": [
    {
      "event_id": "evt_123",
      "event_type": "user_action",
      "timestamp": "2025-09-30T12:00:00",
      "data": {
        "user_id": "user_123",
        "action": "click",
        "value": 42
      },
      "metadata": {
        "source": "producer-service",
        "ingestion_time": "2025-09-30T12:00:00.123"
      }
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0
}
```

### Query Aggregations

```http
GET /api/aggregations?event_type=transaction&start_time=2025-09-30T00:00:00&limit=50
```

**Query Parameters**:
- `event_type` (optional): Filter by event type
- `start_time` (optional): Start timestamp
- `end_time` (optional): End timestamp
- `limit` (optional): Maximum results (default: 100)

**Response**:
```json
{
  "aggregations": [
    {
      "event_type": "transaction",
      "window_start": "2025-09-30T12:00:00",
      "count": 1523,
      "metrics": {
        "total_value": 152345.67,
        "avg_value": 100.03,
        "max_value": 999.99,
        "min_value": 0.99
      },
      "computed_at": "2025-09-30T12:05:00"
    }
  ],
  "count": 1
}
```

### Get Real-Time Metrics

```http
GET /api/metrics/realtime?event_type=user_action
```

**Query Parameters**:
- `event_type`: Event type to query (default: user_action)

**Response**:
```json
{
  "event_type": "user_action",
  "total_count": 45678,
  "region_distribution": {
    "us-east": "12345",
    "us-west": "11234",
    "eu-west": "10123",
    "ap-south": "11976"
  },
  "recent_events": [
    {
      "user_id": "user_789",
      "value": 55,
      "metric": "clicks",
      "region": "us-east"
    }
  ],
  "timestamp": "2025-09-30T12:00:00.000000"
}
```

### Query Anomalies

```http
GET /api/anomalies?event_type=transaction&limit=50
```

**Query Parameters**:
- `event_type` (optional): Filter by event type
- `limit` (optional): Maximum results (default: 50)

**Response**:
```json
{
  "anomalies": [
    {
      "event_type": "transaction",
      "detected_at": "2025-09-30T12:15:00",
      "details": {
        "current_value": 9999.99,
        "expected_value": 100.00,
        "deviation": 99.0
      }
    }
  ],
  "count": 1
}
```

### Get Dashboard Summary

```http
GET /api/dashboard/summary
```

**Response**:
```json
{
  "summary": {
    "event_counts_24h": {
      "user_action": 125643,
      "transaction": 45231,
      "page_view": 234567,
      "error": 123,
      "system_metric": 89012
    },
    "recent_aggregations_1h": {
      "user_action": 5234,
      "transaction": 1876
    },
    "anomalies_24h": 15,
    "realtime_counts": {
      "user_action": 345,
      "transaction": 123
    }
  },
  "timestamp": "2025-09-30T12:00:00.000000"
}
```

### Get System Statistics

```http
GET /api/stats
```

**Response**:
```json
{
  "stats": {
    "total_events": 5234567,
    "total_aggregations": 12345,
    "total_anomalies": 234,
    "database_size_bytes": 1234567890
  },
  "timestamp": "2025-09-30T12:00:00.000000"
}
```

## Event Types

The system supports the following event types:

- `user_action`: User interactions (clicks, views, etc.)
- `transaction`: Financial transactions
- `page_view`: Page view events
- `error`: Error events
- `system_metric`: System performance metrics

Each event type is published to a separate Kafka topic: `events.<event_type>`

## Error Responses

All endpoints may return error responses:

**400 Bad Request**:
```json
{
  "error": "Invalid request",
  "details": "Missing required field: event_type"
}
```

**500 Internal Server Error**:
```json
{
  "error": "Internal server error",
  "details": "Database connection failed"
}
```

**503 Service Unavailable**:
```json
{
  "error": "Service unavailable",
  "details": "Kafka producer not initialized"
}
```

## Rate Limiting

Production deployments should implement rate limiting:

- Recommended: 1000 requests/minute per client
- Batch endpoints: 100 requests/minute
- Simulation endpoint: 10 requests/minute

## Authentication

For production use, implement authentication:

- API Key authentication
- OAuth 2.0
- JWT tokens

Add authentication headers:
```http
Authorization: Bearer <token>
X-API-Key: <api-key>
```