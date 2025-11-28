# API Guide

## Base URL
```
https://api.eventsourcing.example.com/api/v1
```

## Authentication

All requests require a valid JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

All requests must include the tenant ID:
```
X-Tenant-ID: <tenant-uuid>
```

## Endpoints

### Health Check
```
GET /health
```

Returns API health status.

### Tenant Management

#### Create Tenant
```
POST /tenants
Content-Type: application/json

{
  "tenant_name": "Acme Corp",
  "subscription_tier": "enterprise",
  "settings": {
    "max_users": 100
  }
}
```

#### Get Tenant
```
GET /tenants/{tenant_id}
```

#### Update Tenant
```
PUT /tenants/{tenant_id}
Content-Type: application/json

{
  "tenant_name": "Acme Corporation",
  "subscription_tier": "enterprise"
}
```

#### Delete Tenant
```
DELETE /tenants/{tenant_id}
```

### Commands

#### Execute Command
```
POST /commands/execute
Content-Type: application/json
X-Tenant-ID: <tenant-uuid>

{
  "command_type": "CreateOrder",
  "command_id": "uuid",
  "data": {
    "order_id": "uuid",
    "items": []
  }
}
```

Response:
```json
{
  "success": true,
  "aggregate_id": "uuid",
  "message": "Command executed successfully"
}
```

### Queries

#### Execute Query
```
POST /queries/execute
Content-Type: application/json
X-Tenant-ID: <tenant-uuid>

{
  "query_type": "GetOrderById",
  "order_id": "uuid"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "status": "pending",
    "items": []
  },
  "total_count": 1
}
```

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Invalid request",
  "errors": {
    "field": "error message"
  }
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "message": "Tenant is not active"
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Resource not found"
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Concurrency conflict",
  "errors": {
    "version": "Expected version 5 but found 6"
  }
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Internal server error",
  "error": "Error details"
}
```

## Rate Limiting

- 100 requests per minute per tenant
- 429 Too Many Requests response when exceeded

## Pagination

Queries support pagination:
```json
{
  "page": 1,
  "page_size": 20
}
```

Response includes pagination metadata:
```json
{
  "success": true,
  "data": [],
  "total_count": 100,
  "page": 1,
  "page_size": 20
}
```

## Webhooks

Tenants can configure webhooks to receive event notifications:

```
POST /tenants/{tenant_id}/webhooks
Content-Type: application/json

{
  "url": "https://example.com/webhook",
  "event_types": ["OrderCreated", "OrderUpdated"],
  "secret": "webhook-secret"
}
```

Webhook payload:
```json
{
  "event_id": "uuid",
  "event_type": "OrderCreated",
  "tenant_id": "uuid",
  "occurred_at": "2025-09-30T02:41:46Z",
  "data": {}
}
```