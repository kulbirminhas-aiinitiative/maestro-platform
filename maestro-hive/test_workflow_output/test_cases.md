# Test Cases - User Management REST API
## Design Phase - Version 1.0

**Project:** User Management REST API
**Workflow ID:** workflow-20251012-130125
**Date:** 2025-10-12
**Prepared By:** QA Engineer

---

## Test Case Template

Each test case includes:
- **Test ID:** Unique identifier
- **Test Name:** Descriptive name
- **Priority:** High/Medium/Low
- **Category:** Test category
- **Preconditions:** Setup requirements
- **Test Steps:** Step-by-step procedure
- **Test Data:** Input data
- **Expected Result:** Expected outcome
- **Actual Result:** To be filled during execution
- **Status:** Not Executed/Pass/Fail

---

# 1. CREATE USER TESTS (POST /api/users)

## TC-001: Create User with Valid Complete Data
**Priority:** High
**Category:** Functional - Create

**Preconditions:**
- API endpoint `/api/users` is accessible
- Database is available and initialized
- No user exists with email "john.doe@example.com"

**Test Steps:**
1. Send POST request to `/api/users`
2. Include valid user data in request body
3. Verify HTTP status code
4. Verify response body structure
5. Verify user ID is generated
6. Query database to confirm user exists

**Test Data:**
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "age": 30,
  "role": "user"
}
```

**Expected Result:**
- HTTP Status: `201 Created`
- Response contains:
  - `id`: auto-generated unique identifier
  - `name`: "John Doe"
  - `email`: "john.doe@example.com"
  - `age`: 30
  - `role`: "user"
  - `created_at`: timestamp
  - `updated_at`: timestamp
- User exists in database
- `Location` header with user resource URL

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-002: Create User with Minimum Required Fields
**Priority:** High
**Category:** Functional - Create

**Preconditions:**
- API endpoint is accessible

**Test Steps:**
1. Send POST request with only required fields
2. Verify status code
3. Verify optional fields have default values

**Test Data:**
```json
{
  "name": "Jane Smith",
  "email": "jane.smith@example.com"
}
```

**Expected Result:**
- HTTP Status: `201 Created`
- Response contains user with defaults for optional fields
- User created successfully

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-003: Create User with Duplicate Email
**Priority:** High
**Category:** Negative - Create

**Preconditions:**
- User with email "existing@example.com" already exists

**Test Steps:**
1. Attempt to create user with existing email
2. Verify error response

**Test Data:**
```json
{
  "name": "Duplicate User",
  "email": "existing@example.com",
  "age": 25
}
```

**Expected Result:**
- HTTP Status: `409 Conflict` or `400 Bad Request`
- Response body:
```json
{
  "error": "Email already exists",
  "code": "DUPLICATE_EMAIL",
  "field": "email"
}
```
- No new user created

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-004: Create User with Missing Required Field (Email)
**Priority:** High
**Category:** Negative - Data Validation

**Preconditions:**
- API endpoint is accessible

**Test Steps:**
1. Send POST request without required email field
2. Verify validation error

**Test Data:**
```json
{
  "name": "No Email User",
  "age": 30
}
```

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Response indicates missing email field
```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "email",
      "message": "Email is required"
    }
  ]
}
```

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-005: Create User with Invalid Email Format
**Priority:** High
**Category:** Negative - Data Validation

**Test Steps:**
1. Send POST request with invalid email format
2. Verify validation error

**Test Data:**
```json
{
  "name": "Invalid Email",
  "email": "not-an-email"
}
```

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error message: "Invalid email format"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-006: Create User with Invalid Data Type
**Priority:** Medium
**Category:** Negative - Data Validation

**Test Steps:**
1. Send POST request with wrong data type for age
2. Verify type validation

**Test Data:**
```json
{
  "name": "Type Error",
  "email": "type@example.com",
  "age": "thirty"
}
```

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error indicates type mismatch for age field

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-007: Create User with Special Characters in Name
**Priority:** Medium
**Category:** Boundary - Create

**Test Steps:**
1. Create user with special characters in name
2. Verify proper handling

**Test Data:**
```json
{
  "name": "O'Brien-Smith Jr.",
  "email": "obrien@example.com",
  "age": 35
}
```

**Expected Result:**
- HTTP Status: `201 Created`
- Name stored correctly with special characters
- No data corruption

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-008: Create User with Maximum Field Lengths
**Priority:** Medium
**Category:** Boundary - Create

**Test Steps:**
1. Create user with maximum allowed field lengths
2. Verify acceptance or appropriate error

**Test Data:**
```json
{
  "name": "[255 character string]",
  "email": "max@example.com",
  "age": 150
}
```

**Expected Result:**
- Either accepted if within limits
- Or `400 Bad Request` if exceeds limits

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-009: Create User with Empty String Values
**Priority:** Medium
**Category:** Negative - Data Validation

**Test Data:**
```json
{
  "name": "",
  "email": "empty@example.com"
}
```

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error: "Name cannot be empty"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-010: Create User with SQL Injection Attempt
**Priority:** High
**Category:** Security - Create

**Test Data:**
```json
{
  "name": "'; DROP TABLE users; --",
  "email": "hacker@example.com"
}
```

**Expected Result:**
- HTTP Status: `201 Created` or `400 Bad Request`
- No SQL injection executed
- Input sanitized properly
- Database integrity maintained

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 2. READ USER TESTS (GET /api/users)

## TC-011: Get All Users - Success
**Priority:** High
**Category:** Functional - Read

**Preconditions:**
- At least 3 users exist in database

**Test Steps:**
1. Send GET request to `/api/users`
2. Verify response status
3. Verify response is array
4. Verify each user has required fields

**Expected Result:**
- HTTP Status: `200 OK`
- Response is JSON array
- Each user object contains: id, name, email, created_at, updated_at
- Array length matches database count

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-012: Get All Users - Empty Database
**Priority:** Medium
**Category:** Edge Case - Read

**Preconditions:**
- Database has no users

**Test Steps:**
1. Send GET request to `/api/users`
2. Verify empty array response

**Expected Result:**
- HTTP Status: `200 OK`
- Response: `[]` (empty array)

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-013: Get User by Valid ID
**Priority:** High
**Category:** Functional - Read

**Preconditions:**
- User with ID=1 exists

**Test Steps:**
1. Send GET request to `/api/users/1`
2. Verify response contains correct user

**Expected Result:**
- HTTP Status: `200 OK`
- Response contains user with ID=1
- All fields present and correct

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-014: Get User by Non-Existent ID
**Priority:** High
**Category:** Negative - Read

**Test Steps:**
1. Send GET request to `/api/users/99999`
2. Verify 404 error

**Expected Result:**
- HTTP Status: `404 Not Found`
- Error message: "User not found"
```json
{
  "error": "User not found",
  "code": "USER_NOT_FOUND",
  "id": 99999
}
```

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-015: Get User by Invalid ID Format
**Priority:** Medium
**Category:** Negative - Read

**Test Steps:**
1. Send GET request to `/api/users/abc`
2. Verify error response

**Expected Result:**
- HTTP Status: `400 Bad Request` or `404 Not Found`
- Error: "Invalid user ID format"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-016: Get Users with Pagination (if supported)
**Priority:** Medium
**Category:** Functional - Read

**Test Steps:**
1. Send GET request with pagination parameters
2. Verify correct subset returned

**Request:** `GET /api/users?page=1&limit=10`

**Expected Result:**
- HTTP Status: `200 OK`
- Response contains max 10 users
- Pagination metadata included

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 3. UPDATE USER TESTS (PUT /api/users/{id})

## TC-017: Update User - Full Update (PUT)
**Priority:** High
**Category:** Functional - Update

**Preconditions:**
- User with ID=1 exists

**Test Steps:**
1. Send PUT request to `/api/users/1`
2. Include complete updated user data
3. Verify update successful
4. Verify all fields updated

**Test Data:**
```json
{
  "name": "John Updated",
  "email": "john.updated@example.com",
  "age": 31,
  "role": "admin"
}
```

**Expected Result:**
- HTTP Status: `200 OK`
- Response contains updated user
- `updated_at` timestamp changed
- All fields reflect new values

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-018: Update User - Partial Update (PATCH)
**Priority:** High
**Category:** Functional - Update

**Preconditions:**
- User with ID=1 exists with name="John" and email="john@example.com"

**Test Steps:**
1. Send PATCH request to `/api/users/1`
2. Include only name field
3. Verify only name updated

**Test Data:**
```json
{
  "name": "John Modified"
}
```

**Expected Result:**
- HTTP Status: `200 OK`
- Name field updated to "John Modified"
- Email and other fields unchanged
- `updated_at` timestamp changed

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-019: Update Non-Existent User
**Priority:** High
**Category:** Negative - Update

**Test Steps:**
1. Send PUT request to `/api/users/99999`
2. Verify 404 error

**Expected Result:**
- HTTP Status: `404 Not Found`
- Error: "User not found"
- No data created or modified

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-020: Update User with Duplicate Email
**Priority:** High
**Category:** Negative - Update

**Preconditions:**
- User1 (ID=1) has email "user1@example.com"
- User2 (ID=2) has email "user2@example.com"

**Test Steps:**
1. Attempt to update User1's email to User2's email
2. Verify constraint violation

**Test Data:**
```json
{
  "email": "user2@example.com"
}
```

**Expected Result:**
- HTTP Status: `409 Conflict` or `400 Bad Request`
- Error: "Email already exists"
- User1's email unchanged

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-021: Update User with Invalid Email
**Priority:** Medium
**Category:** Negative - Update

**Test Steps:**
1. Send PATCH with invalid email format
2. Verify validation error

**Test Data:**
```json
{
  "email": "invalid-email"
}
```

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error: "Invalid email format"
- User data unchanged

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-022: Update User with Empty Body
**Priority:** Medium
**Category:** Negative - Update

**Test Steps:**
1. Send PUT/PATCH with empty request body
2. Verify error

**Test Data:** `{}`

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error: "No update data provided"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 4. DELETE USER TESTS (DELETE /api/users/{id})

## TC-023: Delete User by Valid ID
**Priority:** High
**Category:** Functional - Delete

**Preconditions:**
- User with ID=1 exists

**Test Steps:**
1. Send DELETE request to `/api/users/1`
2. Verify successful deletion
3. Verify user removed from database
4. Attempt GET on deleted user

**Expected Result:**
- HTTP Status: `200 OK` or `204 No Content`
- Response may contain deleted user data or be empty
- User no longer in database
- Subsequent GET returns 404

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-024: Delete Non-Existent User
**Priority:** High
**Category:** Negative - Delete

**Test Steps:**
1. Send DELETE request to `/api/users/99999`
2. Verify 404 error

**Expected Result:**
- HTTP Status: `404 Not Found`
- Error: "User not found"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-025: Delete User with Invalid ID
**Priority:** Medium
**Category:** Negative - Delete

**Test Steps:**
1. Send DELETE request to `/api/users/abc`
2. Verify error response

**Expected Result:**
- HTTP Status: `400 Bad Request` or `404 Not Found`
- Error: "Invalid user ID"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-026: Delete Same User Twice (Idempotency)
**Priority:** Medium
**Category:** Edge Case - Delete

**Test Steps:**
1. Delete user with ID=1 (first time)
2. Delete same user again (second time)
3. Verify behavior

**Expected Result:**
- First delete: `200 OK` or `204 No Content`
- Second delete: `404 Not Found`

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 5. INTEGRATION & END-TO-END TESTS

## TC-027: Complete User Lifecycle
**Priority:** High
**Category:** Integration - E2E

**Test Steps:**
1. Create new user (POST)
2. Verify user in list (GET all)
3. Get user by ID (GET by ID)
4. Update user (PUT/PATCH)
5. Verify update (GET by ID)
6. Delete user (DELETE)
7. Verify deletion (GET by ID returns 404)

**Expected Result:**
- All operations succeed
- Data consistency maintained
- Final GET returns 404

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-028: Multiple Users Management
**Priority:** High
**Category:** Integration

**Test Steps:**
1. Create 5 users with different data
2. Get all users - verify count is 5
3. Update 2 users
4. Delete 1 user
5. Get all users - verify count is 4
6. Verify updated data correct

**Expected Result:**
- All operations succeed
- Final count: 4 users
- Data matches expectations

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-029: Concurrent User Creation
**Priority:** Medium
**Category:** Concurrency

**Test Steps:**
1. Send 10 POST requests simultaneously
2. Verify all succeed with unique IDs
3. Verify no data corruption

**Expected Result:**
- All 10 users created
- Each has unique ID
- No race conditions or corruption

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-030: Concurrent Duplicate Email Creation
**Priority:** Medium
**Category:** Concurrency

**Test Steps:**
1. Send 2+ POST requests simultaneously with same email
2. Verify only one succeeds

**Expected Result:**
- One request: `201 Created`
- Others: `409 Conflict`
- Only one user with that email exists

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 6. ERROR HANDLING TESTS

## TC-031: Invalid JSON in Request Body
**Priority:** High
**Category:** Error Handling

**Test Steps:**
1. Send POST with malformed JSON
2. Verify error response

**Test Data:** `{ invalid json }`

**Expected Result:**
- HTTP Status: `400 Bad Request`
- Error: "Invalid JSON format"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-032: Missing Content-Type Header
**Priority:** Medium
**Category:** Error Handling

**Test Steps:**
1. Send POST without Content-Type header
2. Verify handling

**Expected Result:**
- HTTP Status: `415 Unsupported Media Type` or `400 Bad Request`
- Error indicates missing/invalid Content-Type

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-033: Invalid HTTP Method
**Priority:** Low
**Category:** Error Handling

**Test Steps:**
1. Send unsupported method (e.g., TRACE) to `/api/users`
2. Verify error

**Expected Result:**
- HTTP Status: `405 Method Not Allowed`
- `Allow` header lists supported methods

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

# 7. SECURITY TESTS

## TC-034: XSS Attack Prevention
**Priority:** High
**Category:** Security

**Test Data:**
```json
{
  "name": "<script>alert('XSS')</script>",
  "email": "xss@example.com"
}
```

**Expected Result:**
- Input sanitized or escaped
- No script execution on retrieval
- Data stored safely

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

## TC-035: Authentication Required (if applicable)
**Priority:** High
**Category:** Security

**Test Steps:**
1. Send requests without authentication token
2. Verify access denied

**Expected Result:**
- HTTP Status: `401 Unauthorized`
- Error: "Authentication required"

**Actual Result:** [Pending execution]
**Status:** Not Executed

---

---

## Test Summary

**Total Test Cases:** 35

### By Priority:
- **High:** 24 test cases
- **Medium:** 10 test cases
- **Low:** 1 test case

### By Category:
- **Functional:** 8 test cases
- **Negative Testing:** 14 test cases
- **Data Validation:** 6 test cases
- **Security:** 3 test cases
- **Integration:** 2 test cases
- **Edge Cases:** 2 test cases

### Coverage by Operation:
- **CREATE (POST):** 10 test cases
- **READ (GET):** 6 test cases
- **UPDATE (PUT/PATCH):** 6 test cases
- **DELETE:** 4 test cases
- **Integration/E2E:** 4 test cases
- **Error Handling:** 3 test cases
- **Security:** 2 test cases

---

## Traceability Matrix

| Requirement | Test Cases |
|-------------|-----------|
| Create User | TC-001 to TC-010 |
| Read Users | TC-011 to TC-016 |
| Update User | TC-017 to TC-022 |
| Delete User | TC-023 to TC-026 |
| Data Validation | TC-004, TC-005, TC-006, TC-009, TC-021 |
| Error Handling | TC-031, TC-032, TC-033 |
| Security | TC-010, TC-034, TC-035 |
| Integration | TC-027, TC-028, TC-029, TC-030 |

---

## Execution Notes

- All test cases marked "Not Executed" - ready for implementation phase
- Each test case should be executed independently
- Test data should be reset between test runs
- Failed tests should be documented with actual results
- Retesting required after bug fixes

**Document Version:** 1.0
**Last Updated:** 2025-10-12
**Next Review:** Implementation Phase
