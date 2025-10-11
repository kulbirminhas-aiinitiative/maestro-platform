# Bug Report Template: Health Check API

## Bug Report Information
Use this template to report any defects found during testing of the Health Check API endpoint.

---

## Bug Report #[ID]

### Basic Information
- **Bug ID:** [Unique identifier, e.g., BUG-001]
- **Reported By:** [QA Engineer name]
- **Date Reported:** [YYYY-MM-DD]
- **Project:** Simple Health Check API
- **Version:** 1.0
- **Environment:** [Development/Testing/Staging]

### Classification
- **Severity:** [Critical/High/Medium/Low]
  - **Critical:** System crash, data loss, security vulnerability
  - **High:** Major functionality broken, no workaround
  - **Medium:** Functionality impaired, workaround exists
  - **Low:** Minor issue, cosmetic problem

- **Priority:** [P1/P2/P3/P4]
  - **P1:** Fix immediately
  - **P2:** Fix before release
  - **P3:** Fix if time permits
  - **P4:** Future release

- **Status:** [New/Assigned/In Progress/Fixed/Closed/Reopened]

### Bug Details

#### Summary
[One-line description of the issue]

#### Description
[Detailed description of the bug, including what went wrong]

#### Steps to Reproduce
1. [First step]
2. [Second step]
3. [Third step]
4. [Continue as needed]

#### Expected Result
[What should happen according to requirements]

#### Actual Result
[What actually happened]

#### Test Case Reference
- **Related Test Case:** [e.g., TC001]
- **Test Type:** [Functional/Performance/Negative/etc.]

### Technical Details

#### Request Information
```http
[HTTP method] [URL]
Headers:
[Any relevant headers]

Body:
[Request body if applicable]
```

#### Response Information
```http
Status Code: [e.g., 500]
Headers:
[Response headers]

Body:
[Response body or error message]
```

#### Error Messages/Logs
```
[Paste error messages, stack traces, or log entries]
```

### Environment Details
- **OS:** [e.g., Ubuntu 22.04]
- **Python Version:** [e.g., 3.10.0]
- **FastAPI Version:** [e.g., 0.104.1]
- **Uvicorn Version:** [e.g., 0.24.0]
- **Browser (if applicable):** [N/A for API]
- **Other Dependencies:** [List any relevant packages]

### Evidence
- **Screenshots:** [Attach or reference screenshots]
- **Videos:** [If screen recording available]
- **Log Files:** [Attach or reference log files]
- **Test Output:** [Pytest output or other test results]

### Impact Assessment
- **Affected Users:** [Who is impacted]
- **Frequency:** [How often does this occur]
- **Workaround Available:** [Yes/No - describe if yes]
- **Business Impact:** [Description of impact on business/users]

### Additional Information
- **First Observed:** [When was this first noticed]
- **Reproducibility:** [Always/Sometimes/Once - X% reproduction rate]
- **Related Bugs:** [Reference to related bug reports]
- **Regression:** [Is this a regression? Yes/No]

### Developer Notes
[Space for developer comments, root cause analysis, fix description]

### Resolution
- **Assigned To:** [Developer name]
- **Fixed In Version:** [Version number]
- **Resolution Date:** [YYYY-MM-DD]
- **Resolution Summary:** [How the bug was fixed]

### Verification
- **Verified By:** [QA Engineer name]
- **Verification Date:** [YYYY-MM-DD]
- **Verification Status:** [Pass/Fail]
- **Verification Notes:** [Any notes from verification testing]

---

## Sample Bug Report

### Bug Report #BUG-001

#### Basic Information
- **Bug ID:** BUG-001
- **Reported By:** QA Engineer
- **Date Reported:** 2025-10-09
- **Project:** Simple Health Check API
- **Version:** 1.0
- **Environment:** Development

#### Classification
- **Severity:** High
- **Priority:** P2
- **Status:** New

#### Bug Details

##### Summary
/health endpoint returns 500 Internal Server Error instead of 200 OK

##### Description
When sending a GET request to the /health endpoint, the server returns a 500 Internal Server Error instead of the expected 200 OK status with JSON response. This completely breaks the health check functionality.

##### Steps to Reproduce
1. Start the FastAPI application using: `uvicorn main:app --reload`
2. Send GET request to http://localhost:8000/health
3. Observe the response

##### Expected Result
- HTTP Status Code: 200
- Response Body: `{"status": "ok", "timestamp": "<current_timestamp>"}`
- Content-Type: application/json

##### Actual Result
- HTTP Status Code: 500
- Response Body: `{"detail": "Internal Server Error"}`
- Error in server logs

##### Test Case Reference
- **Related Test Case:** TC001 - Verify Health Endpoint Returns 200 Status Code
- **Test Type:** Functional

#### Technical Details

##### Request Information
```http
GET http://localhost:8000/health
Headers:
Accept: */*
```

##### Response Information
```http
Status Code: 500
Headers:
Content-Type: application/json

Body:
{"detail": "Internal Server Error"}
```

##### Error Messages/Logs
```
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/path/to/file.py", line 123, in handler
    [Stack trace details]
AttributeError: 'NoneType' object has no attribute 'timestamp'
```

#### Environment Details
- **OS:** Ubuntu 22.04
- **Python Version:** 3.10.0
- **FastAPI Version:** 0.104.1
- **Uvicorn Version:** 0.24.0
- **Browser (if applicable):** N/A
- **Other Dependencies:** None

#### Evidence
- Test output showing failure
- Server logs with error trace

#### Impact Assessment
- **Affected Users:** All users attempting health checks
- **Frequency:** 100% - occurs on every request
- **Workaround Available:** No
- **Business Impact:** Critical - health checks are essential for monitoring and deployment

#### Additional Information
- **First Observed:** 2025-10-09 14:30:00
- **Reproducibility:** Always (100%)
- **Related Bugs:** None
- **Regression:** No - new feature

#### Developer Notes
[To be filled by developer]

#### Resolution
- **Assigned To:** [Developer name]
- **Fixed In Version:** [TBD]
- **Resolution Date:** [TBD]
- **Resolution Summary:** [TBD]

#### Verification
- **Verified By:** [TBD]
- **Verification Date:** [TBD]
- **Verification Status:** [TBD]
- **Verification Notes:** [TBD]

---

## Bug Tracking Guidelines

### When to Report a Bug
- Functionality doesn't match requirements
- Unexpected errors or crashes occur
- Performance is significantly degraded
- Security vulnerabilities discovered
- Data integrity issues

### Bug Report Best Practices
1. **One bug per report** - Don't combine multiple issues
2. **Be specific** - Provide exact steps, not general descriptions
3. **Include evidence** - Screenshots, logs, error messages
4. **Test thoroughly** - Verify the bug is reproducible
5. **Check for duplicates** - Search existing bug reports first
6. **Update status** - Keep the report current as bug progresses

### Severity Guidelines

**Critical**
- Application crashes or becomes unusable
- Data loss or corruption
- Security vulnerabilities
- Complete feature failure

**High**
- Major functionality broken
- No workaround available
- Significant performance degradation
- Affects multiple users

**Medium**
- Functionality impaired but usable
- Workaround exists
- Isolated to specific scenarios
- Minor performance issues

**Low**
- Cosmetic issues
- Minor inconveniences
- Rare edge cases
- Documentation errors

---

## Quick Reference

### Bug Lifecycle
1. **New** - Bug reported and awaiting review
2. **Assigned** - Bug assigned to developer
3. **In Progress** - Developer working on fix
4. **Fixed** - Fix implemented and ready for testing
5. **Closed** - Bug verified as fixed
6. **Reopened** - Bug verification failed, needs more work

### Required Fields
- Bug ID
- Summary
- Steps to Reproduce
- Expected vs Actual Result
- Severity and Priority
- Environment Details

### Optional but Recommended
- Screenshots/Evidence
- Error logs
- Performance metrics
- Related test cases
