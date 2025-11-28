# User Management REST API Documentation

**API Version:** 1.0
**Base URL:** `https://api.example.com/api/v1`
**Documentation Date:** 2025-10-12
**Status:** Design Phase - Complete

---

## Table of Contents

1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Request/Response Format](#request-response-format)
4. [API Endpoints](#api-endpoints)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)
8. [SDKs and Libraries](#sdks-and-libraries)

---

## 1. Introduction

The User Management REST API provides a comprehensive set of endpoints for managing user accounts in your application. This API follows REST principles and uses standard HTTP methods and status codes.

### Key Features
- Full CRUD operations for user management
- Secure authentication and authorization
- Input validation and error handling
- Pagination support for list operations
- Rate limiting for API protection
- JSON request/response format

### API Versioning
The API uses URL-based versioning. The current version is `v1` and is included in the base URL: `/api/v1`

---

## 2. Authentication

### Authentication Method
The API uses **JWT (JSON Web Token)** based authentication. Include the access token in the Authorization header of your requests.

### Header Format
```
Authorization: Bearer <access_token>
```

### Obtaining an Access Token

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "8e7a9f6b5c4d3e2a1b0c9d8e7f6a5b4c..."
}
```

### Token Expiration
- Access tokens expire after 1 hour (3600 seconds)
- Refresh tokens expire after 30 days
- Use the refresh endpoint to obtain a new access token

### Refreshing Tokens

**Endpoint:** `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "8e7a9f6b5c4d3e2a1b0c9d8e7f6a5b4c..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

## 3. Request/Response Format

### Content Type
All requests and responses use JSON format.

**Required Headers:**
```
Content-Type: application/json
Accept: application/json
```

### Standard Response Structure

**Success Response:**
```json
{
  "data": { /* resource data */ },
  "meta": {
    "timestamp": "2025-10-12T13:01:25Z",
    "version": "1.0"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "email": "Email format is invalid"
    },
    "timestamp": "2025-10-12T13:01:25Z",
    "path": "/api/v1/users"
  }
}
```

---

## 4. API Endpoints

### 4.1 Create User

**Endpoint:** `POST /users`
**Authentication:** Not required (public registration)
**Description:** Create a new user account

#### Request Body

```json
{
  "username": "john_doe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1-555-0123",
  "date_of_birth": "1990-01-15"
}
```

#### Request Fields

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| username | string | Yes | 3-50 chars, alphanumeric, underscore, hyphen | Unique username |
| email | string | Yes | Valid email format | Unique email address |
| password | string | Yes | Min 8 chars, complexity rules | User password |
| first_name | string | No | 1-100 chars | First name |
| last_name | string | No | 1-100 chars | Last name |
| phone_number | string | No | Valid phone format | Contact number |
| date_of_birth | date | No | ISO 8601 format | Date of birth |

#### Success Response (201 Created)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1-555-0123",
    "date_of_birth": "1990-01-15",
    "status": "active",
    "created_at": "2025-10-12T13:01:25Z",
    "updated_at": "2025-10-12T13:01:25Z"
  }
}
```

#### Error Responses

**400 Bad Request** - Invalid input data
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "username": "Username must be at least 3 characters",
      "email": "Email format is invalid"
    }
  }
}
```

**409 Conflict** - Duplicate username or email
```json
{
  "error": {
    "code": "DUPLICATE_RESOURCE",
    "message": "Username or email already exists",
    "details": {
      "field": "username",
      "value": "john_doe"
    }
  }
}
```

---

### 4.2 Get All Users

**Endpoint:** `GET /users`
**Authentication:** Required
**Description:** Retrieve a paginated list of users

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 20 | Items per page (max: 100) |
| sort | string | created_at | Sort field (created_at, username, email) |
| order | string | desc | Sort order (asc, desc) |
| status | string | - | Filter by status (active, inactive, suspended) |
| search | string | - | Search in username, email, name |

#### Request Example

```
GET /users?page=1&limit=20&sort=created_at&order=desc&status=active
Authorization: Bearer <access_token>
```

#### Success Response (200 OK)

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john_doe",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "status": "active",
      "created_at": "2025-10-12T13:01:25Z",
      "updated_at": "2025-10-12T13:01:25Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "username": "jane_smith",
      "email": "jane.smith@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "status": "active",
      "created_at": "2025-10-12T12:30:00Z",
      "updated_at": "2025-10-12T12:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### 4.3 Get User by ID

**Endpoint:** `GET /users/{id}`
**Authentication:** Required
**Description:** Retrieve a specific user by ID

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | User identifier |

#### Request Example

```
GET /users/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>
```

#### Success Response (200 OK)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1-555-0123",
    "date_of_birth": "1990-01-15",
    "bio": "Software developer and tech enthusiast",
    "profile_picture_url": "https://cdn.example.com/avatars/john_doe.jpg",
    "status": "active",
    "created_at": "2025-10-12T13:01:25Z",
    "updated_at": "2025-10-12T13:01:25Z",
    "last_login": "2025-10-12T15:30:00Z"
  }
}
```

#### Error Response (404 Not Found)

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User not found",
    "details": {
      "id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

---

### 4.4 Update User (Full Update)

**Endpoint:** `PUT /users/{id}`
**Authentication:** Required
**Description:** Completely replace a user's data

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | User identifier |

#### Request Body

```json
{
  "email": "john.newemail@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1-555-9999",
  "date_of_birth": "1990-01-15",
  "bio": "Updated bio text"
}
```

#### Success Response (200 OK)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john.newemail@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1-555-9999",
    "date_of_birth": "1990-01-15",
    "bio": "Updated bio text",
    "status": "active",
    "created_at": "2025-10-12T13:01:25Z",
    "updated_at": "2025-10-12T16:45:00Z"
  }
}
```

---

### 4.5 Update User (Partial Update)

**Endpoint:** `PATCH /users/{id}`
**Authentication:** Required
**Description:** Update specific fields of a user

#### Request Body

```json
{
  "first_name": "Jonathan",
  "bio": "Passionate developer"
}
```

#### Success Response (200 OK)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john.doe@example.com",
    "first_name": "Jonathan",
    "last_name": "Doe",
    "bio": "Passionate developer",
    "status": "active",
    "updated_at": "2025-10-12T17:00:00Z"
  }
}
```

---

### 4.6 Delete User

**Endpoint:** `DELETE /users/{id}`
**Authentication:** Required
**Description:** Delete a user account (soft delete)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | User identifier |

#### Request Example

```
DELETE /users/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>
```

#### Success Response (204 No Content)

No response body. The user is marked as deleted.

#### Error Response (404 Not Found)

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User not found"
  }
}
```

---

## 5. Error Codes

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Input validation failed |
| AUTHENTICATION_REQUIRED | 401 | Missing or invalid authentication |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required permissions |
| RESOURCE_NOT_FOUND | 404 | Requested resource does not exist |
| DUPLICATE_RESOURCE | 409 | Resource already exists (duplicate) |
| UNPROCESSABLE_ENTITY | 422 | Request understood but cannot be processed |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_SERVER_ERROR | 500 | Server encountered an error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

---

## 6. Rate Limiting

### Limits
- **Anonymous requests:** 20 requests per minute
- **Authenticated requests:** 100 requests per minute
- **Burst limit:** 10 requests per second

### Rate Limit Headers

The API returns rate limit information in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1697123456
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "retry_after": 45
    }
  }
}
```

---

## 7. Examples

### Example 1: User Registration Flow

```bash
# Step 1: Create a new user
curl -X POST https://api.example.com/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_wonder",
    "email": "alice@example.com",
    "password": "SecurePass123!",
    "first_name": "Alice",
    "last_name": "Wonder"
  }'

# Response:
# {
#   "data": {
#     "id": "770e8400-e29b-41d4-a716-446655440002",
#     "username": "alice_wonder",
#     "email": "alice@example.com",
#     ...
#   }
# }

# Step 2: Login to get access token
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_wonder",
    "password": "SecurePass123!"
  }'

# Response:
# {
#   "access_token": "eyJhbGc...",
#   "refresh_token": "8e7a9f6b..."
# }
```

### Example 2: Retrieve and Update User

```bash
# Step 1: Get user details
curl -X GET https://api.example.com/api/v1/users/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer eyJhbGc..."

# Step 2: Update user profile
curl -X PATCH https://api.example.com/api/v1/users/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Exploring wonderland and technology",
    "phone_number": "+1-555-1234"
  }'
```

### Example 3: List Users with Filtering

```bash
# Get active users, sorted by creation date
curl -X GET "https://api.example.com/api/v1/users?status=active&sort=created_at&order=desc&limit=10" \
  -H "Authorization: Bearer eyJhbGc..."

# Search for users
curl -X GET "https://api.example.com/api/v1/users?search=alice" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## 8. SDKs and Libraries

### Official SDKs

Client libraries are planned for:
- JavaScript/TypeScript (Node.js and Browser)
- Python
- Java
- Ruby
- PHP
- Go

### Sample Code (JavaScript)

```javascript
// Installation: npm install user-management-api-client

import UserManagementClient from 'user-management-api-client';

const client = new UserManagementClient({
  baseURL: 'https://api.example.com/api/v1',
  apiKey: 'your-api-key'
});

// Create a user
async function createUser() {
  try {
    const user = await client.users.create({
      username: 'bob_builder',
      email: 'bob@example.com',
      password: 'SecurePass123!',
      first_name: 'Bob',
      last_name: 'Builder'
    });
    console.log('User created:', user.id);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Get user by ID
async function getUser(userId) {
  const user = await client.users.get(userId);
  console.log('User:', user);
}

// Update user
async function updateUser(userId, updates) {
  const user = await client.users.update(userId, updates);
  console.log('User updated:', user);
}

// List users
async function listUsers() {
  const response = await client.users.list({
    page: 1,
    limit: 20,
    status: 'active'
  });
  console.log('Total users:', response.pagination.total);
  console.log('Users:', response.data);
}
```

---

## Support and Resources

### Additional Documentation
- [Getting Started Guide](./user_guide.md)
- [Authentication Guide](./authentication.md)
- [Best Practices](./best_practices.md)
- [Changelog](./changelog.md)

### Support Channels
- **API Status:** https://status.example.com
- **Support Email:** api-support@example.com
- **Developer Forum:** https://forum.example.com
- **GitHub Issues:** https://github.com/example/user-api/issues

### API Status
Check real-time API status and scheduled maintenance at: https://status.example.com

---

**Last Updated:** 2025-10-12
**Document Version:** 1.0
**API Version:** 1.0
