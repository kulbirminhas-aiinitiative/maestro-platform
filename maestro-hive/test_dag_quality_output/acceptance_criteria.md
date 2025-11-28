# Acceptance Criteria
## REST API for User Authentication with JWT Tokens

**Project ID:** 0bd5797e-2983-482a-bf5a-a025a8d44ac2
**Phase:** Requirement Analysis
**Date:** 2025-10-11

---

## Overview

This document provides detailed acceptance criteria for all user stories in the User Authentication REST API project. Each criterion follows the Given-When-Then format and includes test scenarios for validation.

---

## US-001: User Registration

### AC-001.1: Successful Registration with Valid Data
**Given** I am a new user
**When** I submit a POST request to `/api/auth/register` with:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```
**Then** the system responds with HTTP 201 Created
**And** the response includes:
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "timestamp"
  }
}
```
**And** the password is hashed and stored securely in the database
**And** the password is never returned in the response

### AC-001.2: Registration Fails with Duplicate Email
**Given** a user with email "user@example.com" already exists
**When** I try to register with the same email
**Then** the system responds with HTTP 409 Conflict
**And** the response includes:
```json
{
  "error": "Email already registered",
  "field": "email"
}
```

### AC-001.3: Registration Fails with Invalid Email Format
**Given** I submit registration data
**When** the email is in invalid format (e.g., "notanemail")
**Then** the system responds with HTTP 400 Bad Request
**And** the response includes:
```json
{
  "error": "Invalid email format",
  "field": "email"
}
```

### AC-001.4: Registration Fails with Weak Password
**Given** I submit registration data
**When** the password does not meet complexity requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
**Then** the system responds with HTTP 400 Bad Request
**And** the response includes specific password requirements

### AC-001.5: Registration with Missing Required Fields
**Given** I submit registration data
**When** required fields (email or password) are missing
**Then** the system responds with HTTP 400 Bad Request
**And** the response specifies which fields are missing

---

## US-002: User Login

### AC-002.1: Successful Login with Valid Credentials
**Given** I am a registered user with:
- Email: "user@example.com"
- Password: "SecurePass123!"
**When** I submit a POST request to `/api/auth/login` with valid credentials
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```
**And** the access token is a valid JWT
**And** the access token expires in 15 minutes
**And** the refresh token expires in 7 days

### AC-002.2: Login Fails with Incorrect Password
**Given** I am a registered user
**When** I submit login credentials with an incorrect password
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Invalid credentials"
}
```
**And** the failed attempt is logged

### AC-002.3: Login Fails with Non-Existent Email
**Given** I submit login credentials
**When** the email does not exist in the system
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Invalid credentials"
}
```
**And** the system does not reveal whether the email exists

### AC-002.4: Login Blocked After Multiple Failed Attempts
**Given** I have made 5 failed login attempts
**When** I try to login again within 15 minutes
**Then** the system responds with HTTP 429 Too Many Requests
**And** the response includes:
```json
{
  "error": "Too many login attempts. Please try again later.",
  "retry_after": 900
}
```

### AC-002.5: JWT Token Contains Required Claims
**Given** I successfully login
**When** I decode the access token
**Then** the token payload contains:
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234568790,
  "type": "access"
}
```

---

## US-003: Access Protected Resources

### AC-003.1: Successful Access with Valid Token
**Given** I have a valid access token
**When** I send a GET request to a protected endpoint with:
```
Authorization: Bearer <valid_access_token>
```
**Then** the system responds with HTTP 200 OK
**And** I receive the requested resource

### AC-003.2: Access Denied with Missing Token
**Given** I do not include an authorization header
**When** I try to access a protected endpoint
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Authentication required"
}
```

### AC-003.3: Access Denied with Invalid Token
**Given** I provide an invalid or malformed token
**When** I try to access a protected endpoint
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Invalid token"
}
```

### AC-003.4: Access Denied with Expired Token
**Given** my access token has expired
**When** I try to access a protected endpoint
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Token expired",
  "code": "TOKEN_EXPIRED"
}
```

### AC-003.5: Token Validation Performance
**Given** I have a valid access token
**When** the system validates my token
**Then** the validation process completes in less than 10ms
**And** the validation does not require database queries (stateless)

---

## US-004: Token Refresh

### AC-004.1: Successful Token Refresh
**Given** I have a valid refresh token
**When** I send a POST request to `/api/auth/refresh` with:
```json
{
  "refresh_token": "valid_refresh_token"
}
```
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "access_token": "new_jwt_access_token",
  "token_type": "Bearer",
  "expires_in": 900
}
```
**And** the new access token has a fresh expiration time

### AC-004.2: Refresh Fails with Expired Refresh Token
**Given** my refresh token has expired
**When** I try to refresh my access token
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Refresh token expired. Please login again."
}
```

### AC-004.3: Refresh Fails with Invalid Refresh Token
**Given** I provide an invalid refresh token
**When** I try to refresh my access token
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Invalid refresh token"
}
```

### AC-004.4: Refresh Fails with Blacklisted Token
**Given** my refresh token has been blacklisted (after logout)
**When** I try to use it to refresh my access token
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Token has been revoked"
}
```

---

## US-005: User Logout

### AC-005.1: Successful Logout
**Given** I am authenticated with a valid access token
**When** I send a POST request to `/api/auth/logout` with:
```
Authorization: Bearer <access_token>
```
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "message": "Logged out successfully"
}
```
**And** my token is added to the blacklist

### AC-005.2: Token Cannot Be Used After Logout
**Given** I have logged out
**When** I try to use my old access token to access protected resources
**Then** the system responds with HTTP 401 Unauthorized
**And** the response includes:
```json
{
  "error": "Token has been revoked"
}
```

### AC-005.3: Logout with Both Access and Refresh Tokens
**Given** I am authenticated
**When** I logout with my access token
**Then** both my access token and refresh token are invalidated
**And** neither can be used for subsequent requests

---

## US-006: Request Password Reset

### AC-006.1: Successful Password Reset Request
**Given** I have forgotten my password
**When** I send a POST request to `/api/auth/forgot-password` with:
```json
{
  "email": "user@example.com"
}
```
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```
**And** an email is sent to the user with a reset link
**And** the reset token expires in 1 hour

### AC-006.2: Password Reset Request for Non-Existent Email
**Given** I submit a password reset request
**When** the email does not exist in the system
**Then** the system responds with HTTP 200 OK
**And** the response is identical to a successful request (security)
**And** no email is sent

### AC-006.3: Password Reset Email Contains Valid Link
**Given** I requested a password reset
**When** I receive the email
**Then** the email contains a link in format:
```
https://app.example.com/reset-password?token=<secure_token>
```
**And** the token is cryptographically secure (minimum 32 bytes)
**And** the token is hashed before storing in database

### AC-006.4: Rate Limiting on Password Reset Requests
**Given** I have requested password reset 3 times
**When** I try to request again within 1 hour
**Then** the system responds with HTTP 429 Too Many Requests
**And** subsequent reset requests are blocked

---

## US-007: Reset Password

### AC-007.1: Successful Password Reset
**Given** I have a valid password reset token
**When** I send a POST request to `/api/auth/reset-password` with:
```json
{
  "token": "valid_reset_token",
  "new_password": "NewSecurePass456!"
}
```
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "message": "Password reset successfully"
}
```
**And** my password is updated in the database
**And** the reset token is invalidated
**And** all existing sessions/tokens are terminated

### AC-007.2: Password Reset Fails with Expired Token
**Given** my reset token has expired (>1 hour old)
**When** I try to reset my password
**Then** the system responds with HTTP 400 Bad Request
**And** the response includes:
```json
{
  "error": "Reset token has expired"
}
```

### AC-007.3: Password Reset Fails with Invalid Token
**Given** I provide an invalid reset token
**When** I try to reset my password
**Then** the system responds with HTTP 400 Bad Request
**And** the response includes:
```json
{
  "error": "Invalid reset token"
}
```

### AC-007.4: Password Reset Fails with Weak Password
**Given** I have a valid reset token
**When** I try to set a password that doesn't meet requirements
**Then** the system responds with HTTP 400 Bad Request
**And** the response specifies password requirements

### AC-007.5: Token is Single-Use Only
**Given** I successfully reset my password using a token
**When** I try to use the same token again
**Then** the system responds with HTTP 400 Bad Request
**And** the response includes:
```json
{
  "error": "Reset token has already been used"
}
```

---

## US-008: View User Profile

### AC-008.1: Successful Profile Retrieval
**Given** I am authenticated with a valid access token
**When** I send a GET request to `/api/auth/me` with:
```
Authorization: Bearer <access_token>
```
**Then** the system responds with HTTP 200 OK
**And** the response includes:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "timestamp",
  "last_login": "timestamp"
}
```
**And** the response does NOT include password hash or sensitive data

### AC-008.2: Profile Access Denied Without Authentication
**Given** I do not have a valid access token
**When** I try to access the profile endpoint
**Then** the system responds with HTTP 401 Unauthorized

---

## US-009: Handle Invalid Authentication

### AC-009.1: Clear Error Messages for Various Failures
**Given** an authentication operation fails
**When** the failure occurs
**Then** the system returns appropriate HTTP status codes:
- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication failed)
- 403: Forbidden (insufficient permissions)
- 429: Too Many Requests (rate limited)

### AC-009.2: Error Response Format Consistency
**Given** any error occurs
**When** the system responds
**Then** the response follows the format:
```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "field": "field_name (optional)"
}
```

### AC-009.3: No Sensitive Data in Error Messages
**Given** any error occurs
**When** the error response is generated
**Then** the response does not include:
- Password values
- Token values (except generic "invalid token" messages)
- Internal system paths or stack traces
- Database error details

---

## US-010: Rate Limiting Protection

### AC-010.1: Rate Limit on Login Endpoint
**Given** I make multiple login attempts
**When** I exceed 5 attempts in 15 minutes
**Then** subsequent requests receive HTTP 429
**And** the response includes:
```json
{
  "error": "Too many login attempts",
  "retry_after": 900
}
```
**And** I can retry after the specified time

### AC-010.2: Rate Limit on Registration Endpoint
**Given** I make multiple registration attempts from same IP
**When** I exceed 3 attempts in 1 hour
**Then** subsequent requests are rate limited

### AC-010.3: Rate Limit on Password Reset Endpoint
**Given** I request password reset multiple times
**When** I exceed 3 attempts in 1 hour
**Then** subsequent requests are rate limited

### AC-010.4: Rate Limit Headers in Response
**Given** rate limiting is active
**When** I make a request
**Then** the response includes headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1234567890
```

---

## Non-Functional Acceptance Criteria

### Performance Criteria

#### AC-NF-001: Response Time
**Given** the system is under normal load
**When** any authentication endpoint is called
**Then** the response time is < 200ms for 95% of requests

#### AC-NF-002: Concurrent Users
**Given** the system has 1000 concurrent authenticated users
**When** they make API requests
**Then** the system maintains stable performance
**And** no degradation in response times occurs

#### AC-NF-003: Token Validation Performance
**Given** a protected endpoint is called
**When** token validation occurs
**Then** validation completes in < 10ms
**And** does not require database queries

### Security Criteria

#### AC-NF-004: Password Hashing
**Given** a user registers or changes password
**When** the password is stored
**Then** it is hashed using bcrypt with minimum 10 rounds
**And** the plain text password is never stored

#### AC-NF-005: HTTPS Enforcement
**Given** any API endpoint is called over HTTP
**When** the request reaches the server
**Then** it is automatically redirected to HTTPS
**Or** rejected with appropriate error

#### AC-NF-006: Token Security
**Given** JWT tokens are generated
**When** tokens are signed
**Then** HS256 or RS256 algorithm is used
**And** secret keys are stored in environment variables
**And** secret keys are minimum 256 bits

#### AC-NF-007: Input Validation
**Given** any endpoint receives input
**When** the input is processed
**Then** all input is validated and sanitized
**And** protection against SQL injection is enforced
**And** protection against XSS is enforced

### Reliability Criteria

#### AC-NF-008: Error Handling
**Given** an unexpected error occurs
**When** the system handles the error
**Then** a graceful error response is returned
**And** the error is logged with full context
**And** the system continues to operate normally

#### AC-NF-009: Database Transactions
**Given** a database operation fails
**When** the operation is part of a transaction
**Then** the transaction is rolled back
**And** data consistency is maintained

---

## Testing Requirements

### Unit Testing
- Minimum 80% code coverage
- All functions have corresponding unit tests
- Edge cases and error conditions tested
- Mock external dependencies

### Integration Testing
- All API endpoints tested end-to-end
- Database operations verified
- Token generation and validation tested
- Email sending tested (with mock service)

### Security Testing
- OWASP Top 10 vulnerabilities checked
- Penetration testing conducted
- Token security validated
- Rate limiting effectiveness verified

### Performance Testing
- Load testing with 1000 concurrent users
- Response time benchmarks verified
- Database query performance tested
- Token validation performance measured

---

## Sign-Off Criteria

All acceptance criteria must be:
- Implemented according to specifications
- Verified through automated tests
- Validated by QA team
- Approved by Product Owner
- Security reviewed and approved
- Performance benchmarks met
- Documentation completed

**Document Version:** 1.0
**Status:** Approved for Development
**Next Review:** Upon completion of Phase 1
