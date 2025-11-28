# REST API Endpoints Specification - User Management API

## Project Information
**Workflow ID:** workflow-20251012-130125
**Phase:** Requirements
**Document Version:** 1.0
**API Version:** v1
**Date:** 2025-10-12
**Prepared by:** Backend Developer

---

## 1. API Overview

### Base URL
```
Development: http://localhost:3000/api/v1
Staging: https://staging-api.example.com/api/v1
Production: https://api.example.com/api/v1
```

### API Design Principles
- **RESTful Architecture:** Resource-based URLs with appropriate HTTP methods
- **JSON Format:** All requests and responses use JSON
- **Versioning:** API version in URL path (/api/v1/)
- **Stateless:** No server-side session state
- **HATEOAS:** Hypermedia links in responses (where applicable)

### Global Headers

#### Request Headers
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <JWT_TOKEN>  # For authenticated endpoints
X-Request-ID: <UUID>  # Optional, for request tracing
```

#### Response Headers
```http
Content-Type: application/json
X-Request-ID: <UUID>
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1697123456
```

---

## 2. Authentication

### 2.1 Login

**Endpoint:** `POST /api/v1/auth/login`

**Description:** Authenticate user and receive JWT access token

**Authentication Required:** No

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Validation Rules:**
- `email`: Required, valid email format
- `password`: Required, minimum 8 characters

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600
    }
  },
  "message": "Login successful",
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

**Error Responses:**

*401 Unauthorized:*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

*400 Bad Request:*
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

---

### 2.2 Logout

**Endpoint:** `POST /api/v1/auth/logout`

**Description:** Invalidate current access token

**Authentication Required:** Yes

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Logout successful",
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

---

### 2.3 Refresh Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Description:** Get new access token using refresh token

**Authentication Required:** Yes (Refresh Token)

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  },
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

---

## 3. User Management Endpoints

### 3.1 Create User

**Endpoint:** `POST /api/v1/users`

**Description:** Register a new user account

**Authentication Required:** No

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "date_of_birth": "1990-01-15"
}
```

**Field Specifications:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| username | string | Yes | 3-50 chars, alphanumeric + underscore, unique |
| email | string | Yes | Valid email format, unique |
| password | string | Yes | Min 8 chars, 1 upper, 1 lower, 1 digit, 1 special |
| first_name | string | No | 1-100 chars |
| last_name | string | No | 1-100 chars |
| phone_number | string | No | Valid E.164 format |
| date_of_birth | string | No | ISO 8601 date (YYYY-MM-DD), must be past |

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+1234567890",
      "date_of_birth": "1990-01-15",
      "profile_picture_url": null,
      "bio": null,
      "status": "active",
      "email_verified": false,
      "created_at": "2025-10-12T13:01:25.000Z",
      "updated_at": "2025-10-12T13:01:25.000Z"
    }
  },
  "message": "User created successfully",
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

**Error Responses:**

*409 Conflict (Duplicate Email/Username):*
```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_RESOURCE",
    "message": "Email already exists",
    "details": {
      "field": "email",
      "value": "john.doe@example.com"
    },
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

*400 Bad Request (Validation Error):*
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "password",
        "message": "Password must contain at least one uppercase letter"
      },
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

---

### 3.2 Get User by ID

**Endpoint:** `GET /api/v1/users/:id`

**Description:** Retrieve a single user by their ID

**Authentication Required:** Yes

**Path Parameters:**
- `id` (UUID): User's unique identifier

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+1234567890",
      "date_of_birth": "1990-01-15",
      "profile_picture_url": "https://example.com/avatars/johndoe.jpg",
      "bio": "Software developer passionate about clean code",
      "status": "active",
      "email_verified": true,
      "created_at": "2025-10-12T13:01:25.000Z",
      "updated_at": "2025-10-12T13:01:25.000Z",
      "last_login": "2025-10-12T13:00:00.000Z"
    }
  },
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

**Error Responses:**

*404 Not Found:*
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User not found",
    "details": {
      "resource": "user",
      "id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

*400 Bad Request (Invalid UUID):*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid user ID format",
    "details": {
      "field": "id",
      "expected": "UUID"
    },
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

---

### 3.3 List Users

**Endpoint:** `GET /api/v1/users`

**Description:** Retrieve a paginated list of users with optional filtering and sorting

**Authentication Required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description | Validation |
|-----------|------|---------|-------------|------------|
| page | integer | 1 | Page number | Min: 1 |
| limit | integer | 20 | Items per page | Min: 1, Max: 100 |
| search | string | - | Search in name and email | Min: 2 chars |
| status | string | - | Filter by status | Enum: active, inactive, suspended |
| sort_by | string | created_at | Sort field | Enum: created_at, email, username, last_name |
| sort_order | string | desc | Sort direction | Enum: asc, desc |
| email_verified | boolean | - | Filter by verification status | true/false |

**Example Request:**
```
GET /api/v1/users?page=1&limit=20&search=john&status=active&sort_by=last_name&sort_order=asc
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "johndoe",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "status": "active",
        "email_verified": true,
        "created_at": "2025-10-12T13:01:25.000Z"
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "username": "johnsmith",
        "email": "john.smith@example.com",
        "first_name": "John",
        "last_name": "Smith",
        "status": "active",
        "email_verified": true,
        "created_at": "2025-10-11T10:30:00.000Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_items": 95,
      "has_next": true,
      "has_previous": false
    }
  },
  "timestamp": "2025-10-12T13:01:25.000Z"
}
```

**Error Responses:**

*400 Bad Request (Invalid Query Parameters):*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_QUERY_PARAMETER",
    "message": "Invalid query parameters",
    "details": [
      {
        "parameter": "limit",
        "message": "Limit must be between 1 and 100"
      }
    ],
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

---

### 3.4 Update User

**Endpoint:** `PUT /api/v1/users/:id`

**Description:** Update an existing user's information (full update)

**Authentication Required:** Yes (User must own the account or be admin)

**Path Parameters:**
- `id` (UUID): User's unique identifier

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "first_name": "Jonathan",
  "last_name": "Doe",
  "phone_number": "+1987654321",
  "date_of_birth": "1990-01-15",
  "profile_picture_url": "https://example.com/new-avatar.jpg",
  "bio": "Updated bio text"
}
```

**Note:** Password updates should use the separate password update endpoint

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "email": "newemail@example.com",
      "first_name": "Jonathan",
      "last_name": "Doe",
      "phone_number": "+1987654321",
      "date_of_birth": "1990-01-15",
      "profile_picture_url": "https://example.com/new-avatar.jpg",
      "bio": "Updated bio text",
      "status": "active",
      "email_verified": false,
      "created_at": "2025-10-12T13:01:25.000Z",
      "updated_at": "2025-10-12T14:30:00.000Z",
      "last_login": "2025-10-12T13:00:00.000Z"
    }
  },
  "message": "User updated successfully",
  "timestamp": "2025-10-12T14:30:00.000Z"
}
```

**Error Responses:**

*403 Forbidden:*
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to update this user",
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

*409 Conflict (Email Already Exists):*
```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_RESOURCE",
    "message": "Email already in use by another user",
    "details": {
      "field": "email"
    },
    "timestamp": "2025-10-12T13:01:25.000Z"
  }
}
```

---

### 3.5 Partial Update User

**Endpoint:** `PATCH /api/v1/users/:id`

**Description:** Partially update user information (only specified fields)

**Authentication Required:** Yes (User must own the account or be admin)

**Path Parameters:**
- `id` (UUID): User's unique identifier

**Request Body (example - only include fields to update):**
```json
{
  "first_name": "Jonathan",
  "bio": "Updated bio"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "email": "john.doe@example.com",
      "first_name": "Jonathan",
      "last_name": "Doe",
      "phone_number": "+1234567890",
      "date_of_birth": "1990-01-15",
      "profile_picture_url": "https://example.com/avatar.jpg",
      "bio": "Updated bio",
      "status": "active",
      "email_verified": true,
      "created_at": "2025-10-12T13:01:25.000Z",
      "updated_at": "2025-10-12T14:45:00.000Z",
      "last_login": "2025-10-12T13:00:00.000Z"
    }
  },
  "message": "User updated successfully",
  "timestamp": "2025-10-12T14:45:00.000Z"
}
```

---

### 3.6 Delete User

**Endpoint:** `DELETE /api/v1/users/:id`

**Description:** Soft delete a user account (marks as deleted, doesn't remove data)

**Authentication Required:** Yes (User must own the account or be admin)

**Path Parameters:**
- `id` (UUID): User's unique identifier

**Success Response (204 No Content):**
```
(Empty response body)
```

**Alternative Response (200 OK):**
```json
{
  "success": true,
  "message": "User deleted successfully",
  "timestamp": "2025-10-12T15:00:00.000Z"
}
```

**Error Responses:**

*404 Not Found:*
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User not found",
    "timestamp": "2025-10-12T15:00:00.000Z"
  }
}
```

*403 Forbidden:*
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to delete this user",
    "timestamp": "2025-10-12T15:00:00.000Z"
  }
}
```

---

### 3.7 Update Password

**Endpoint:** `PATCH /api/v1/users/:id/password`

**Description:** Update user password with verification

**Authentication Required:** Yes (User must own the account)

**Path Parameters:**
- `id` (UUID): User's unique identifier

**Request Body:**
```json
{
  "current_password": "OldSecurePass123!",
  "new_password": "NewSecurePass456!",
  "confirm_password": "NewSecurePass456!"
}
```

**Validation Rules:**
- `current_password`: Required, must match existing password
- `new_password`: Required, must meet password complexity requirements
- `confirm_password`: Required, must match new_password

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Password updated successfully",
  "timestamp": "2025-10-12T15:15:00.000Z"
}
```

**Error Responses:**

*401 Unauthorized (Wrong Current Password):*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PASSWORD",
    "message": "Current password is incorrect",
    "timestamp": "2025-10-12T15:15:00.000Z"
  }
}
```

*400 Bad Request (Password Mismatch):*
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Password confirmation does not match",
    "details": {
      "field": "confirm_password"
    },
    "timestamp": "2025-10-12T15:15:00.000Z"
  }
}
```

---

## 4. Utility Endpoints

### 4.1 Health Check

**Endpoint:** `GET /api/v1/health`

**Description:** Check API health status

**Authentication Required:** No

**Success Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-12T15:30:00.000Z",
  "services": {
    "database": "connected",
    "cache": "connected"
  }
}
```

---

### 4.2 API Information

**Endpoint:** `GET /api/v1/info`

**Description:** Get API version and information

**Authentication Required:** No

**Success Response (200 OK):**
```json
{
  "api_name": "User Management API",
  "version": "1.0.0",
  "description": "REST API for user management with CRUD operations",
  "documentation_url": "https://api.example.com/docs",
  "timestamp": "2025-10-12T15:30:00.000Z"
}
```

---

## 5. Error Response Format

### Standard Error Structure

All error responses follow this consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "timestamp": "2025-10-12T15:30:00.000Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|-----------|-------------|
| 400 | VALIDATION_ERROR | Request validation failed |
| 400 | INVALID_PARAMETER | Invalid parameter value or format |
| 400 | INVALID_QUERY_PARAMETER | Invalid query string parameter |
| 401 | UNAUTHORIZED | Authentication required |
| 401 | INVALID_CREDENTIALS | Invalid email/password combination |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | JWT token is invalid |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | RESOURCE_NOT_FOUND | Requested resource not found |
| 409 | DUPLICATE_RESOURCE | Resource already exists (email/username) |
| 422 | BUSINESS_LOGIC_ERROR | Request violates business rules |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_SERVER_ERROR | Unexpected server error |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable |

---

## 6. Rate Limiting

### Rate Limit Policy

- **Limit:** 100 requests per minute per IP address
- **Window:** Rolling 60-second window
- **Headers:** Rate limit info included in response headers

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1697123456
```

### Rate Limit Exceeded Response (429)

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "retry_after": 45
    },
    "timestamp": "2025-10-12T15:45:00.000Z"
  }
}
```

---

## 7. Pagination

### Pagination Parameters

All list endpoints support pagination:

- `page`: Current page number (default: 1, min: 1)
- `limit`: Items per page (default: 20, min: 1, max: 100)

### Pagination Response Format

```json
{
  "pagination": {
    "current_page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 95,
    "has_next": true,
    "has_previous": false,
    "links": {
      "first": "/api/v1/users?page=1&limit=20",
      "last": "/api/v1/users?page=5&limit=20",
      "next": "/api/v1/users?page=2&limit=20",
      "prev": null
    }
  }
}
```

---

## 8. Filtering and Sorting

### Supported Filter Operations

**Equality:**
```
GET /api/v1/users?status=active
```

**Search (partial match):**
```
GET /api/v1/users?search=john
```

**Boolean filters:**
```
GET /api/v1/users?email_verified=true
```

### Supported Sort Operations

**Single field sort:**
```
GET /api/v1/users?sort_by=created_at&sort_order=desc
```

**Sort options:**
- Fields: `created_at`, `email`, `username`, `last_name`
- Order: `asc` (ascending), `desc` (descending)

---

## 9. API Testing Examples

### cURL Examples

**Create User:**
```bash
curl -X POST https://api.example.com/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john.doe@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Login:**
```bash
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
  }'
```

**Get User (Authenticated):**
```bash
curl -X GET https://api.example.com/api/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**List Users with Filters:**
```bash
curl -X GET "https://api.example.com/api/v1/users?page=1&limit=20&status=active&sort_by=created_at" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Update User:**
```bash
curl -X PATCH https://api.example.com/api/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jonathan",
    "bio": "Updated bio"
  }'
```

**Delete User:**
```bash
curl -X DELETE https://api.example.com/api/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 10. OpenAPI/Swagger Documentation

### Swagger UI Endpoint
```
Development: http://localhost:3000/api/docs
Production: https://api.example.com/api/docs
```

### OpenAPI Specification
```
OpenAPI Spec (JSON): /api/v1/openapi.json
OpenAPI Spec (YAML): /api/v1/openapi.yaml
```

---

## 11. Security Considerations

### Authentication
- JWT tokens with 1-hour expiration
- Refresh tokens with 7-day expiration
- Secure token storage (httpOnly cookies recommended for web)

### Authorization
- Role-based access control (user can only modify own data)
- Admin role for elevated permissions

### Data Protection
- Passwords never returned in responses
- Password fields excluded from all user objects
- Sensitive data encrypted in transit (HTTPS)

### Input Validation
- All inputs validated and sanitized
- SQL injection prevention via parameterized queries
- XSS protection via output encoding

---

## 12. API Versioning Strategy

### Current Version
- **Version:** v1
- **Release Date:** 2025-10-12
- **Status:** Active

### Future Versions
- Breaking changes will increment version (v2, v3, etc.)
- Non-breaking changes will not change version
- Old versions maintained for 6 months after new version release

### Deprecation Policy
- 3-month notice before deprecation
- Deprecation warnings in response headers
- Documentation of migration path

---

## 13. Performance Considerations

### Response Time Targets
- 95th percentile: < 200ms
- 99th percentile: < 500ms
- Average: < 100ms

### Caching Strategy
- User objects cached for 5 minutes
- Cache invalidation on updates
- ETag support for conditional requests

### Database Query Optimization
- All queries use indexed fields
- N+1 query prevention
- Connection pooling enabled

---

## 14. Monitoring and Observability

### Metrics Exposed
- Request count by endpoint
- Response time percentiles
- Error rate by type
- Active user sessions

### Logging
- All requests logged with request ID
- Error stack traces captured
- Audit log for data modifications

### Health Monitoring
- Health check endpoint: `/api/v1/health`
- Database connectivity check
- Memory and CPU usage monitoring

---

## Appendix A: HTTP Status Code Reference

| Status Code | Meaning | Usage |
|-------------|---------|-------|
| 200 | OK | Successful GET, PATCH, PUT |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid request syntax or validation error |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Authenticated but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict (duplicate email/username) |
| 422 | Unprocessable Entity | Business logic validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily down |

---

## Appendix B: Response Time Benchmarks

| Endpoint | Target (p95) | Typical |
|----------|--------------|---------|
| POST /auth/login | 150ms | 80ms |
| POST /users | 200ms | 100ms |
| GET /users/:id | 100ms | 50ms |
| GET /users (list) | 200ms | 120ms |
| PATCH /users/:id | 150ms | 80ms |
| DELETE /users/:id | 100ms | 60ms |

---

**Document Status:** Final
**Quality Review:** Passed
**Ready for Implementation:** Yes
**OpenAPI Spec:** To be generated from this documentation
