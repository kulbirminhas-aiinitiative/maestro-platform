# User Management REST API Documentation

## Version: 1.0.0
## Design Phase

---

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Versioning](#versioning)

---

## Overview

The User Management REST API provides a comprehensive set of CRUD (Create, Read, Update, Delete) operations for managing user data. This API follows RESTful design principles and returns JSON-formatted responses.

### Key Features
- Full CRUD operations for user entities
- Standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
- JSON request/response format
- Comprehensive error handling
- Input validation
- Pagination support for list operations

---

## Base URL

```
Production: https://api.example.com/v1
Development: http://localhost:8000/v1
```

---

## Authentication

All API endpoints require authentication using Bearer tokens.

### Request Header
```
Authorization: Bearer <your_access_token>
```

### Example
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     https://api.example.com/v1/users
```

---

## API Endpoints

### 1. Create User

**Endpoint:** `POST /users`

**Description:** Creates a new user in the system.

**Request Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePassword123!",
  "phone": "+1-555-0123",
  "role": "user"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-555-0123",
  "role": "user",
  "is_active": true,
  "created_at": "2025-10-12T13:41:12.263147Z",
  "updated_at": "2025-10-12T13:41:12.263147Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid input data
- `409 Conflict` - Username or email already exists
- `401 Unauthorized` - Missing or invalid authentication token

---

### 2. Get All Users

**Endpoint:** `GET /users`

**Description:** Retrieves a paginated list of all users.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number |
| page_size | integer | No | 20 | Items per page (max: 100) |
| sort_by | string | No | created_at | Sort field (username, email, created_at) |
| order | string | No | desc | Sort order (asc, desc) |
| is_active | boolean | No | - | Filter by active status |
| role | string | No | - | Filter by user role |

**Request Example:**
```
GET /users?page=1&page_size=20&sort_by=username&order=asc
```

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john_doe",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1-555-0123",
      "role": "user",
      "is_active": true,
      "created_at": "2025-10-12T13:41:12.263147Z",
      "updated_at": "2025-10-12T13:41:12.263147Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 20,
    "total_items": 145,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Missing or invalid authentication token

---

### 3. Get User by ID

**Endpoint:** `GET /users/{user_id}`

**Description:** Retrieves a specific user by their unique identifier.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string (UUID) | Yes | Unique user identifier |

**Request Example:**
```
GET /users/550e8400-e29b-41d4-a716-446655440000
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-555-0123",
  "role": "user",
  "is_active": true,
  "created_at": "2025-10-12T13:41:12.263147Z",
  "updated_at": "2025-10-12T13:41:12.263147Z",
  "last_login": "2025-10-12T14:30:00.000000Z"
}
```

**Error Responses:**
- `404 Not Found` - User does not exist
- `401 Unauthorized` - Missing or invalid authentication token
- `400 Bad Request` - Invalid user_id format

---

### 4. Update User (Full)

**Endpoint:** `PUT /users/{user_id}`

**Description:** Fully updates a user's information. All fields must be provided.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string (UUID) | Yes | Unique user identifier |

**Request Body:**
```json
{
  "username": "john_doe_updated",
  "email": "john.updated@example.com",
  "first_name": "John",
  "last_name": "Doe-Smith",
  "phone": "+1-555-9999",
  "role": "admin",
  "is_active": true
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe_updated",
  "email": "john.updated@example.com",
  "first_name": "John",
  "last_name": "Doe-Smith",
  "phone": "+1-555-9999",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-10-12T13:41:12.263147Z",
  "updated_at": "2025-10-12T15:20:00.000000Z"
}
```

**Error Responses:**
- `404 Not Found` - User does not exist
- `400 Bad Request` - Invalid input data or missing required fields
- `409 Conflict` - Username or email already exists
- `401 Unauthorized` - Missing or invalid authentication token

---

### 5. Update User (Partial)

**Endpoint:** `PATCH /users/{user_id}`

**Description:** Partially updates a user's information. Only provided fields will be updated.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string (UUID) | Yes | Unique user identifier |

**Request Body:**
```json
{
  "phone": "+1-555-7777",
  "is_active": false
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-555-7777",
  "role": "user",
  "is_active": false,
  "created_at": "2025-10-12T13:41:12.263147Z",
  "updated_at": "2025-10-12T15:25:00.000000Z"
}
```

**Error Responses:**
- `404 Not Found` - User does not exist
- `400 Bad Request` - Invalid input data
- `409 Conflict` - Updated username or email already exists
- `401 Unauthorized` - Missing or invalid authentication token

---

### 6. Delete User

**Endpoint:** `DELETE /users/{user_id}`

**Description:** Permanently deletes a user from the system.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string (UUID) | Yes | Unique user identifier |

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| soft_delete | boolean | No | false | Soft delete (deactivate) instead of permanent deletion |

**Request Example:**
```
DELETE /users/550e8400-e29b-41d4-a716-446655440000
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found` - User does not exist
- `401 Unauthorized` - Missing or invalid authentication token
- `403 Forbidden` - Insufficient permissions to delete user

---

## Data Models

### User Model

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| id | UUID | Auto-generated | Unique | User unique identifier |
| username | string | Yes | 3-50 chars, alphanumeric + underscore | Unique username |
| email | string | Yes | Valid email format | Unique email address |
| first_name | string | Yes | 1-100 chars | User's first name |
| last_name | string | Yes | 1-100 chars | User's last name |
| password | string | Yes | Min 8 chars, hashed | User password (hashed) |
| phone | string | No | Valid phone format | Contact phone number |
| role | string | Yes | Enum: user, admin, moderator | User role |
| is_active | boolean | No | Default: true | Account active status |
| created_at | datetime | Auto-generated | ISO 8601 | Creation timestamp |
| updated_at | datetime | Auto-generated | ISO 8601 | Last update timestamp |
| last_login | datetime | No | ISO 8601 | Last login timestamp |

### Password Requirements
- Minimum length: 8 characters
- Must contain at least one uppercase letter
- Must contain at least one lowercase letter
- Must contain at least one number
- Must contain at least one special character (!@#$%^&*)

---

## Error Handling

All error responses follow a consistent format:

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "email",
        "message": "Email address is already in use"
      }
    ],
    "timestamp": "2025-10-12T15:30:00.000000Z",
    "request_id": "req_abc123xyz"
  }
}
```

### Standard Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | VALIDATION_ERROR | Invalid input data |
| 401 | UNAUTHORIZED | Authentication required or failed |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 422 | UNPROCESSABLE_ENTITY | Semantic error in request |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_SERVER_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable |

---

## Rate Limiting

API endpoints are rate-limited to ensure fair usage.

### Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1696857600
```

### Default Limits
- **Authenticated requests:** 1000 requests per hour
- **Unauthenticated requests:** 100 requests per hour

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 3600 seconds.",
    "timestamp": "2025-10-12T15:30:00.000000Z",
    "request_id": "req_abc123xyz"
  }
}
```

---

## Versioning

The API uses URL versioning. The current version is `v1`.

### Version Format
```
https://api.example.com/v1/users
```

### Version Deprecation Policy
- New versions will be announced 90 days in advance
- Deprecated versions will be supported for 12 months after deprecation notice
- Version sunset dates will be communicated via API headers and documentation

---

## Best Practices

### Pagination
- Always use pagination for list endpoints
- Default page size is 20 items
- Maximum page size is 100 items

### Caching
- Use ETags for conditional requests
- Implement client-side caching where appropriate

### Security
- Always use HTTPS in production
- Store access tokens securely
- Never log or expose sensitive data (passwords, tokens)
- Implement proper input validation on client side

### Performance
- Request only the fields you need
- Use appropriate page sizes
- Implement request timeout handling

---

## Support

For API support and questions:
- Documentation: https://docs.example.com
- Support Email: api-support@example.com
- Issue Tracker: https://github.com/example/api/issues

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-12
**Phase:** Design
**Status:** Draft
