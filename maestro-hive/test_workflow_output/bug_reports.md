# Bug Report Template & Tracking

## Bug Report Template

### Bug ID: BUG-XXX
**Date Reported:** YYYY-MM-DD
**Reported By:** QA Engineer Name
**Priority:** Critical / High / Medium / Low
**Severity:** Blocker / Critical / Major / Minor / Trivial
**Status:** New / In Progress / Fixed / Closed / Reopened

---

#### Summary
[Brief one-line description of the bug]

#### Environment
- API Version:
- Environment: Development / Staging / Production
- OS:
- Browser (if applicable):
- Database:

#### Preconditions
- [List any setup or state required before bug can be reproduced]

#### Steps to Reproduce
1. [First step]
2. [Second step]
3. [Continue...]

#### Expected Result
[What should happen]

#### Actual Result
[What actually happened]

#### Test Data Used
```json
{
  "example": "data"
}
```

#### Screenshots/Logs
[Attach relevant screenshots, error logs, or API responses]

#### API Request/Response
**Request:**
```http
POST /api/users HTTP/1.1
Content-Type: application/json

{
  "name": "Test User",
  "email": "test@example.com"
}
```

**Response:**
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": "Internal Server Error"
}
```

#### Additional Information
- Test Case Reference: TC-XXX
- Related Bugs: BUG-YYY
- Notes: [Any additional context]

#### Suggested Fix
[Optional: QA engineer's suggestion for resolution]

---

## Sample Bug Reports

### BUG-001: API Returns 500 Error When Creating User with Missing Email
**Date Reported:** 2025-10-12
**Reported By:** QA Team
**Priority:** High
**Severity:** Major
**Status:** New

#### Summary
API returns 500 Internal Server Error instead of 400 Bad Request when attempting to create user without email field.

#### Environment
- API Version: 1.0
- Environment: Development
- Database: PostgreSQL 14

#### Preconditions
- API server is running
- Database is accessible

#### Steps to Reproduce
1. Send POST request to `/api/users`
2. Include request body with name but without email field
3. Observe response

#### Expected Result
- Status Code: 400 Bad Request
- Response body contains validation error message indicating email is required
- User is not created

#### Actual Result
- Status Code: 500 Internal Server Error
- Response body contains generic error message
- Server logs show unhandled exception

#### Test Data Used
```json
{
  "name": "John Doe",
  "age": 30
}
```

#### API Request/Response
**Request:**
```http
POST /api/users HTTP/1.1
Content-Type: application/json

{
  "name": "John Doe",
  "age": 30
}
```

**Response:**
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

#### Additional Information
- Test Case Reference: TC-003
- Impact: Poor user experience, unclear error messaging
- Notes: This affects input validation for all required fields

#### Suggested Fix
Add proper validation middleware to check required fields before processing request. Return 400 status with descriptive error message.

---

### BUG-002: Duplicate Email Allowed During User Creation
**Date Reported:** 2025-10-12
**Reported By:** QA Team
**Priority:** Critical
**Severity:** Critical
**Status:** New

#### Summary
System allows creation of multiple users with the same email address, violating uniqueness constraint.

#### Environment
- API Version: 1.0
- Environment: Development
- Database: PostgreSQL 14

#### Preconditions
- One user exists with email "test@example.com"

#### Steps to Reproduce
1. Create first user with email "test@example.com"
2. Attempt to create second user with same email "test@example.com"
3. Check database for duplicate entries

#### Expected Result
- First user: 201 Created
- Second user: 409 Conflict or 400 Bad Request
- Error message: "Email already exists"
- Only one user with that email in database

#### Actual Result
- Both requests: 201 Created
- No error returned
- Database contains two users with identical email addresses

#### Test Data Used
```json
{
  "name": "User One",
  "email": "test@example.com",
  "age": 25
}
```

```json
{
  "name": "User Two",
  "email": "test@example.com",
  "age": 30
}
```

#### Additional Information
- Test Case Reference: TC-002
- Impact: Data integrity violation, authentication issues
- Related Bugs: None
- Notes: This is a critical data integrity issue

#### Suggested Fix
1. Add unique constraint on email field in database schema
2. Add validation check before user creation
3. Return 409 Conflict status with appropriate error message

---

### BUG-003: GET Request Returns Users Without Created Timestamp
**Date Reported:** 2025-10-12
**Reported By:** QA Team
**Priority:** Medium
**Severity:** Minor
**Status:** New

#### Summary
User objects returned by GET endpoints are missing created_at and updated_at timestamp fields.

#### Environment
- API Version: 1.0
- Environment: Development

#### Preconditions
- At least one user exists in database

#### Steps to Reproduce
1. Create a new user via POST /api/users
2. Retrieve user via GET /api/users/{id}
3. Examine response payload

#### Expected Result
User object contains:
- id
- name
- email
- age
- role
- created_at (ISO 8601 timestamp)
- updated_at (ISO 8601 timestamp)

#### Actual Result
User object contains:
- id
- name
- email
- age
- role

Missing: created_at, updated_at fields

#### API Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30,
  "role": "user"
}
```

#### Additional Information
- Test Case Reference: TC-007
- Impact: Cannot track when users were created or last modified
- Notes: Audit trail is incomplete

#### Suggested Fix
Include created_at and updated_at fields in API response serialization.

---

## Bug Tracking Summary

### Bug Statistics

**Total Bugs Reported:** 3 (Sample)

**By Priority:**
- Critical: 1
- High: 1
- Medium: 1
- Low: 0

**By Severity:**
- Critical: 1
- Major: 1
- Minor: 1
- Trivial: 0

**By Status:**
- New: 3
- In Progress: 0
- Fixed: 0
- Closed: 0
- Reopened: 0

**By Category:**
- Validation: 1
- Data Integrity: 1
- API Response: 1
- Error Handling: 1

---

## Bug Priority Guidelines

### Critical
- Complete system failure
- Data loss or corruption
- Security vulnerabilities
- No workaround available

### High
- Major functionality broken
- Significant user impact
- Workaround is difficult

### Medium
- Minor functionality issue
- Moderate user impact
- Workaround available

### Low
- Cosmetic issues
- Minimal user impact
- Easy workaround

---

## Bug Severity Guidelines

### Blocker
- Prevents testing from continuing
- Complete feature failure

### Critical
- Major functionality unusable
- Data integrity issues

### Major
- Significant functionality impaired
- Clear violation of requirements

### Minor
- Small functionality issue
- Minor inconvenience

### Trivial
- Cosmetic issues
- Typos, formatting
