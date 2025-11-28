# Bug Report Template
## User Management REST API

**Project:** User Management REST API
**Workflow ID:** workflow-20251012-130125
**Version:** 1.0
**Date:** 2025-10-12

---

## Bug Report Format

Use this template for all bug reports during testing.

---

## BUG-[ID]: [Short Description]

### Bug Information
- **Bug ID:** BUG-[Sequential Number]
- **Reported By:** [QA Engineer Name]
- **Date Reported:** [YYYY-MM-DD]
- **Environment:** [Development/Staging/Production]
- **Build/Version:** [Version Number]
- **Test Case Reference:** [TC-XXX]

### Classification
- **Priority:** [Critical/High/Medium/Low]
- **Severity:** [Critical/Major/Minor/Trivial]
- **Type:** [Functional/UI/Performance/Security/Data/Integration]
- **Status:** [New/In Progress/Fixed/Retest/Closed/Won't Fix]

### Description
[Detailed description of the bug]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]
...

### Test Data Used
```json
{
  "example": "data"
}
```

### Expected Result
[What should happen]

### Actual Result
[What actually happens]

### Visual Evidence
- Screenshots: [Attach if applicable]
- Logs: [Include relevant log excerpts]
- Response Body:
```json
{
  "error": "example"
}
```

### Environment Details
- **API Endpoint:** [e.g., POST /api/users]
- **HTTP Method:** [GET/POST/PUT/PATCH/DELETE]
- **Request Headers:**
```
Content-Type: application/json
Authorization: Bearer [token]
```

### Impact
[Describe the impact on functionality, users, or system]

### Workaround
[Describe any temporary workaround, if available]

### Suggested Fix
[Optional: Suggestions for fixing the bug]

### Related Bugs
- Related to: BUG-XXX
- Blocks: BUG-XXX
- Blocked by: BUG-XXX

### Attachments
- [ ] Screenshots
- [ ] Log files
- [ ] Test data
- [ ] API response dumps

---

## Priority and Severity Guidelines

### Priority Levels
- **Critical:** System down, no workaround, affects all users
- **High:** Major functionality broken, limited workaround
- **Medium:** Moderate impact, workaround available
- **Low:** Minor issue, cosmetic, minimal impact

### Severity Levels
- **Critical:** Complete loss of functionality, data corruption
- **Major:** Significant functionality loss, incorrect results
- **Minor:** Small functionality issue, minor inconvenience
- **Trivial:** Cosmetic issues, typos

---

## Example Bug Reports

### Example 1: Critical Bug

## BUG-001: User Creation Fails with Valid Data

### Bug Information
- **Bug ID:** BUG-001
- **Reported By:** QA Engineer
- **Date Reported:** 2025-10-12
- **Environment:** Staging
- **Build/Version:** v1.0.0
- **Test Case Reference:** TC-001

### Classification
- **Priority:** Critical
- **Severity:** Critical
- **Type:** Functional
- **Status:** New

### Description
User creation fails with HTTP 500 Internal Server Error when submitting valid user data. This affects the core functionality of the API.

### Steps to Reproduce
1. Send POST request to `/api/users`
2. Include valid user data in request body
3. Observe response

### Test Data Used
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "age": 30,
  "role": "user"
}
```

### Expected Result
- HTTP Status: 201 Created
- Response contains user object with generated ID
- User stored in database

### Actual Result
- HTTP Status: 500 Internal Server Error
- Response body:
```json
{
  "error": "Internal Server Error"
}
```
- User not created in database

### Visual Evidence
**Server Logs:**
```
[2025-10-12 14:30:15] ERROR: Database connection failed
[2025-10-12 14:30:15] ERROR: Unable to insert user record
```

### Environment Details
- **API Endpoint:** POST /api/users
- **HTTP Method:** POST
- **Request Headers:**
```
Content-Type: application/json
```

### Impact
Complete loss of user creation functionality. No users can be created. Blocks all dependent functionality (read, update, delete require existing users).

### Workaround
None available.

### Suggested Fix
Check database connection configuration. Verify database schema matches application models.

### Related Bugs
None

### Attachments
- [x] Log files
- [x] Test data
- [x] API response dumps

---

### Example 2: High Priority Bug

## BUG-002: Email Validation Accepts Invalid Format

### Bug Information
- **Bug ID:** BUG-002
- **Reported By:** QA Engineer
- **Date Reported:** 2025-10-12
- **Environment:** Staging
- **Build/Version:** v1.0.0
- **Test Case Reference:** TC-005

### Classification
- **Priority:** High
- **Severity:** Major
- **Type:** Data Validation
- **Status:** New

### Description
API accepts invalid email formats during user creation, violating data integrity requirements.

### Steps to Reproduce
1. Send POST request to `/api/users`
2. Include invalid email format (e.g., "not-an-email")
3. Observe that request succeeds

### Test Data Used
```json
{
  "name": "Invalid Email User",
  "email": "not-an-email"
}
```

### Expected Result
- HTTP Status: 400 Bad Request
- Error message: "Invalid email format"
- User not created

### Actual Result
- HTTP Status: 201 Created
- User created with invalid email
- Database contains invalid email

### Environment Details
- **API Endpoint:** POST /api/users
- **HTTP Method:** POST

### Impact
Data integrity compromised. Invalid emails stored in database. Email notifications will fail. Duplicate detection via email may not work correctly.

### Workaround
Perform manual email validation before API call.

### Suggested Fix
Implement email format validation using regex or email validator library. Add validation before database insert.

### Related Bugs
None

---

### Example 3: Medium Priority Bug

## BUG-003: GET All Users Returns Unsorted List

### Bug Information
- **Bug ID:** BUG-003
- **Reported By:** QA Engineer
- **Date Reported:** 2025-10-12
- **Environment:** Staging
- **Build/Version:** v1.0.0
- **Test Case Reference:** TC-011

### Classification
- **Priority:** Medium
- **Severity:** Minor
- **Type:** Functional
- **Status:** New

### Description
GET /api/users returns users in random order instead of consistent sorting (e.g., by ID or creation date).

### Steps to Reproduce
1. Create 5 users
2. Send GET request to `/api/users`
3. Note the order
4. Send GET request again
5. Observe different order

### Expected Result
Users returned in consistent order (e.g., sorted by ID ascending or creation date)

### Actual Result
Users returned in inconsistent/random order across multiple requests

### Impact
Inconsistent user experience. Makes pagination difficult. Frontend cannot rely on order.

### Workaround
Sort results on client side.

### Suggested Fix
Add ORDER BY clause to database query. Default to sorting by ID ascending.

---

## Bug Tracking Workflow

### Status Workflow
1. **New** → Bug reported by QA
2. **In Progress** → Developer working on fix
3. **Fixed** → Developer completed fix
4. **Retest** → QA retesting the fix
5. **Closed** → Bug verified as fixed
6. **Reopened** → Bug still exists after fix attempt
7. **Won't Fix** → Bug will not be addressed

### Responsibilities
- **QA Engineer:** Report bugs, verify fixes, update status
- **Developer:** Fix bugs, update status, provide fix details
- **Project Manager:** Prioritize bugs, assign resources

---

## Bug Report Best Practices

### DO:
- Be specific and detailed
- Include exact steps to reproduce
- Provide actual test data used
- Include screenshots and logs
- Verify bug is reproducible
- Check for duplicates before reporting
- Use clear, concise language

### DON'T:
- Report multiple bugs in one report
- Include assumptions without verification
- Skip steps to reproduce
- Use vague descriptions like "doesn't work"
- Report bugs without testing first
- Forget to include environment details

---

## Bug Metrics

Track the following metrics:
- **Total Bugs Reported:** Count of all bugs
- **Bugs by Priority:** Count per priority level
- **Bugs by Severity:** Count per severity level
- **Bugs by Type:** Functional, Security, Performance, etc.
- **Bugs by Status:** New, In Progress, Fixed, Closed
- **Resolution Time:** Average time to fix bugs
- **Reopen Rate:** % of bugs reopened after initial fix

---

## Document Version
- **Version:** 1.0
- **Last Updated:** 2025-10-12
- **Next Review:** Implementation Phase
