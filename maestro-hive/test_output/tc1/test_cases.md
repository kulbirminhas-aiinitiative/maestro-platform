# Test Cases: Health Check API Endpoint

## Test Case Document Information
- **Project:** Simple Health Check API
- **Version:** 1.0
- **Date:** 2025-10-09
- **QA Engineer:** QA Engineer

---

## TC001: Verify Health Endpoint Returns 200 Status Code

**Priority:** High
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Observe the HTTP response status code

**Expected Result:**
- HTTP status code should be 200 (OK)

**Test Data:** None required

---

## TC002: Verify Health Endpoint Returns Valid JSON Response

**Priority:** High
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Parse the response body
3. Verify the response is valid JSON format

**Expected Result:**
- Response body is valid JSON
- Response can be successfully parsed

**Test Data:** None required

---

## TC003: Verify Response Contains Required Fields

**Priority:** High
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Parse the JSON response
3. Check for presence of "status" field
4. Check for presence of "timestamp" field

**Expected Result:**
- Response contains "status" field
- Response contains "timestamp" field
- No additional unexpected fields present

**Test Data:** None required

---

## TC004: Verify Status Field Value

**Priority:** High
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Parse the JSON response
3. Extract the value of "status" field
4. Verify the value

**Expected Result:**
- "status" field value equals "ok" (case-sensitive)

**Test Data:** None required

---

## TC005: Verify Timestamp Field Format

**Priority:** High
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Parse the JSON response
3. Extract the "timestamp" field value
4. Verify timestamp is in valid ISO 8601 format or timestamp string format

**Expected Result:**
- Timestamp field contains a valid timestamp string
- Timestamp represents current date/time (within reasonable margin)

**Test Data:** None required

---

## TC006: Verify Response Time Performance

**Priority:** Medium
**Type:** Performance
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Record start time
2. Send GET request to http://localhost:8000/health
3. Receive response
4. Record end time
5. Calculate response time

**Expected Result:**
- Response time should be less than 200ms under normal conditions

**Test Data:** None required

---

## TC007: Verify POST Method Not Allowed

**Priority:** Medium
**Type:** Negative
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send POST request to http://localhost:8000/health
2. Observe the HTTP response status code

**Expected Result:**
- HTTP status code should be 405 (Method Not Allowed) or 404 (Not Found)
- Endpoint should not accept POST method

**Test Data:** None required

---

## TC008: Verify PUT Method Not Allowed

**Priority:** Medium
**Type:** Negative
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send PUT request to http://localhost:8000/health
2. Observe the HTTP response status code

**Expected Result:**
- HTTP status code should be 405 (Method Not Allowed) or 404 (Not Found)
- Endpoint should not accept PUT method

**Test Data:** None required

---

## TC009: Verify DELETE Method Not Allowed

**Priority:** Medium
**Type:** Negative
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send DELETE request to http://localhost:8000/health
2. Observe the HTTP response status code

**Expected Result:**
- HTTP status code should be 405 (Method Not Allowed) or 404 (Not Found)
- Endpoint should not accept DELETE method

**Test Data:** None required

---

## TC010: Verify Multiple Concurrent Requests

**Priority:** Medium
**Type:** Performance
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send 10 concurrent GET requests to http://localhost:8000/health
2. Wait for all responses
3. Verify all responses

**Expected Result:**
- All 10 requests should return 200 status code
- All responses should contain valid JSON with correct structure
- No requests should fail or timeout

**Test Data:** None required

---

## TC011: Verify Content-Type Header

**Priority:** Low
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health
2. Examine response headers
3. Verify Content-Type header

**Expected Result:**
- Content-Type header should be "application/json"

**Test Data:** None required

---

## TC012: Verify Endpoint with Trailing Slash

**Priority:** Low
**Type:** Functional
**Preconditions:**
- FastAPI application is running
- Server accessible at http://localhost:8000

**Test Steps:**
1. Send GET request to http://localhost:8000/health/
2. Observe the HTTP response

**Expected Result:**
- Should return 200 status code OR redirect to /health
- Should return valid health check response

**Test Data:** None required

---

## Test Case Summary

| Priority | Total | Description |
|----------|-------|-------------|
| High | 5 | Critical functionality tests |
| Medium | 5 | Important validation and negative tests |
| Low | 2 | Nice-to-have validations |
| **Total** | **12** | **Complete test coverage** |

## Test Coverage Matrix

| Requirement | Test Cases | Coverage |
|-------------|------------|----------|
| GET /health endpoint | TC001, TC002, TC003 | ✓ |
| JSON response format | TC002, TC003, TC011 | ✓ |
| status: "ok" field | TC003, TC004 | ✓ |
| timestamp field | TC003, TC005 | ✓ |
| HTTP methods validation | TC007, TC008, TC009 | ✓ |
| Performance | TC006, TC010 | ✓ |
