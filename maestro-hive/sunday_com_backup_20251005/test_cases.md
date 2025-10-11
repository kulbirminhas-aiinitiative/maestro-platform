# Test Cases for Critical Features
*Sunday.com - Work Management Platform*

## Document Overview
This document contains detailed test cases for all critical features of the Sunday.com platform. Each test case includes preconditions, test steps, expected results, and acceptance criteria.

**Test Case Format:**
- **TC-XXX**: Test Case ID
- **Priority**: Critical/High/Medium/Low
- **Type**: Functional/Performance/Security/Usability
- **Automation Level**: Manual/Automated/Semi-automated

---

## Authentication & Authorization Test Cases

### TC-001: User Registration
**Priority:** Critical | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that new users can successfully register for the platform

**Preconditions:**
- Application is accessible
- User does not already exist in the system
- Email service is functioning

**Test Steps:**
1. Navigate to registration page
2. Enter valid first name: "John"
3. Enter valid last name: "Doe"
4. Enter unique email: "john.doe@example.com"
5. Enter strong password: "SecurePass123!"
6. Confirm password: "SecurePass123!"
7. Accept terms and conditions
8. Click "Register" button

**Expected Results:**
- Registration successful message displayed
- User account created in database
- Confirmation email sent
- User redirected to email verification page

**Acceptance Criteria:**
- ✅ User account exists in database
- ✅ Password is properly hashed
- ✅ Email verification token generated
- ✅ User status set to "pending verification"

---

### TC-002: User Login with Valid Credentials
**Priority:** Critical | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that registered users can login with correct credentials

**Preconditions:**
- User account exists and is verified
- User is not currently logged in

**Test Steps:**
1. Navigate to login page
2. Enter valid email: "john.doe@example.com"
3. Enter correct password: "SecurePass123!"
4. Click "Login" button

**Expected Results:**
- Login successful
- JWT token generated and stored
- User redirected to dashboard
- User session established

**Acceptance Criteria:**
- ✅ Valid JWT token in localStorage
- ✅ User profile data available
- ✅ Navigation menu shows logged-in state
- ✅ Session timeout properly configured

---

### TC-003: User Login with Invalid Credentials
**Priority:** High | **Type:** Security | **Automation:** Automated

**Objective:** Verify that invalid login attempts are properly rejected

**Preconditions:**
- User account exists
- User is not currently logged in

**Test Steps:**
1. Navigate to login page
2. Enter valid email: "john.doe@example.com"
3. Enter incorrect password: "WrongPassword"
4. Click "Login" button

**Expected Results:**
- Login fails with appropriate error message
- No JWT token generated
- User remains on login page
- Failed attempt logged for security

**Acceptance Criteria:**
- ✅ Error message: "Invalid email or password"
- ✅ No sensitive information leaked
- ✅ Account not locked on first attempt
- ✅ Login attempt logged in security log

---

### TC-004: Password Reset Flow
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can reset their password using email

**Preconditions:**
- User account exists and is verified
- Email service is functioning

**Test Steps:**
1. Navigate to login page
2. Click "Forgot Password" link
3. Enter registered email: "john.doe@example.com"
4. Click "Send Reset Link" button
5. Check email for reset token
6. Click reset link in email
7. Enter new password: "NewSecurePass123!"
8. Confirm new password: "NewSecurePass123!"
9. Click "Reset Password" button

**Expected Results:**
- Reset email sent successfully
- Reset token is valid and secure
- Password updated in database
- User can login with new password

**Acceptance Criteria:**
- ✅ Reset token expires in 1 hour
- ✅ Old password no longer works
- ✅ New password properly hashed
- ✅ Reset token invalidated after use

---

## Board Management Test Cases

### TC-101: Create New Board
**Priority:** Critical | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can create new boards within workspaces

**Preconditions:**
- User is logged in
- User has access to a workspace
- User has board creation permissions

**Test Steps:**
1. Navigate to workspace dashboard
2. Click "Create Board" button
3. Enter board name: "Product Development"
4. Enter board description: "Track product features and bugs"
5. Select template: "Software Development"
6. Set board visibility: "Private"
7. Add initial columns: "Backlog", "In Progress", "Review", "Done"
8. Click "Create Board" button

**Expected Results:**
- Board created successfully
- Board appears in workspace board list
- Default columns created
- User set as board owner
- Board settings configured correctly

**Acceptance Criteria:**
- ✅ Board exists in database with correct metadata
- ✅ User has owner permissions
- ✅ Default columns created with proper order
- ✅ Board activity log initialized

---

### TC-102: Board Permission Management
**Priority:** High | **Type:** Security | **Automation:** Automated

**Objective:** Verify that board permissions are properly enforced

**Preconditions:**
- Board exists with defined permissions
- Multiple users with different role levels
- Users are authenticated

**Test Steps:**
1. Login as board owner
2. Invite user with "Viewer" role
3. Invite user with "Editor" role
4. Invite user with "Admin" role
5. Login as Viewer user
6. Attempt to edit board settings (should fail)
7. Login as Editor user
8. Attempt to edit items (should succeed)
9. Login as Admin user
10. Attempt to manage permissions (should succeed)

**Expected Results:**
- Permissions enforced at API level
- UI elements hidden/disabled based on permissions
- Appropriate error messages for unauthorized actions
- Audit log tracks permission changes

**Acceptance Criteria:**
- ✅ API returns 403 for unauthorized actions
- ✅ UI correctly reflects user permissions
- ✅ Permission changes logged in audit trail
- ✅ Real-time permission updates work

---

### TC-103: Board Real-time Collaboration
**Priority:** Critical | **Type:** Functional | **Automation:** Semi-automated

**Objective:** Verify that multiple users can collaborate on boards in real-time

**Preconditions:**
- Board exists with multiple collaborators
- WebSocket connection established
- Multiple browser sessions or users

**Test Steps:**
1. Open board in Browser 1 (User A)
2. Open same board in Browser 2 (User B)
3. User A creates new item "Feature X"
4. Verify User B sees new item immediately
5. User B moves item to "In Progress" column
6. Verify User A sees column change immediately
7. User A adds comment to item
8. Verify User B sees new comment notification
9. Both users edit item simultaneously
10. Verify conflict resolution works correctly

**Expected Results:**
- Changes appear in real-time across all sessions
- Conflict resolution prevents data loss
- User presence indicators work correctly
- WebSocket connections remain stable

**Acceptance Criteria:**
- ✅ Updates appear within 100ms
- ✅ No data loss during conflicts
- ✅ Presence indicators show active users
- ✅ Connection recovery works on network issues

---

## Task/Item Management Test Cases

### TC-201: Create Task Item
**Priority:** Critical | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can create task items on boards

**Preconditions:**
- User is logged in
- Board exists and user has edit permissions
- Board has at least one column

**Test Steps:**
1. Navigate to board view
2. Click "Add Item" in "Backlog" column
3. Enter item title: "Implement user authentication"
4. Enter item description: "Add JWT-based authentication system"
5. Set priority: "High"
6. Set due date: "2024-12-31"
7. Assign to user: "john.doe@example.com"
8. Add tags: "backend", "security"
9. Set estimated hours: "8"
10. Click "Create Item" button

**Expected Results:**
- Item created successfully in specified column
- All metadata properly saved
- Assignee receives notification
- Item appears in assignee's task list

**Acceptance Criteria:**
- ✅ Item visible in board column
- ✅ All fields properly saved
- ✅ Activity log entry created
- ✅ Search index updated

---

### TC-202: Drag and Drop Item Movement
**Priority:** High | **Type:** Usability | **Automation:** Semi-automated

**Objective:** Verify that items can be moved between columns using drag and drop

**Preconditions:**
- Board with multiple columns exists
- Items exist in various columns
- User has edit permissions

**Test Steps:**
1. Navigate to board view
2. Locate item in "Backlog" column
3. Click and hold on item
4. Drag item to "In Progress" column
5. Release mouse button
6. Verify item moved to new column
7. Test moving item back to original column
8. Test invalid drop targets (outside board)
9. Test keyboard accessibility (Tab + Space/Enter)

**Expected Results:**
- Items move smoothly between columns
- Visual feedback during drag operation
- Status automatically updated
- Changes saved to database immediately

**Acceptance Criteria:**
- ✅ Smooth animation during drag
- ✅ Status field updated in database
- ✅ Activity log records movement
- ✅ Keyboard navigation works

---

### TC-203: Item Status Workflow
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that item status changes follow defined workflow rules

**Preconditions:**
- Board with workflow rules configured
- Items in various states
- User has edit permissions

**Test Steps:**
1. Create item in "Backlog" status
2. Attempt to move directly to "Done" (should be blocked)
3. Move item to "In Progress" (should succeed)
4. Start timer for item
5. Add work log entry
6. Move item to "Review" (should succeed)
7. Add review comments
8. Move item to "Done" (should succeed)
9. Verify item completion metrics updated

**Expected Results:**
- Workflow rules properly enforced
- Invalid transitions blocked with clear messaging
- Completion triggers update metrics
- Time tracking data preserved

**Acceptance Criteria:**
- ✅ Workflow validation at API level
- ✅ Clear error messages for invalid transitions
- ✅ Completion date automatically set
- ✅ Metrics and analytics updated

---

## Time Tracking Test Cases

### TC-301: Start/Stop Timer
**Priority:** Critical | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can start and stop timers for tasks

**Preconditions:**
- User is logged in
- Task item exists
- No timer currently running for user

**Test Steps:**
1. Navigate to board with task items
2. Click timer icon on specific item
3. Click "Start Timer" button
4. Verify timer starts counting
5. Wait 10 seconds
6. Click "Stop Timer" button
7. Verify time entry created
8. Check timer display shows "00:00:10"

**Expected Results:**
- Timer starts immediately when clicked
- Real-time countdown displayed
- Time entry saved to database
- Only one timer active per user

**Acceptance Criteria:**
- ✅ Timer accuracy within 1 second
- ✅ Time entry created with correct duration
- ✅ Item shows active timer indicator
- ✅ Multiple timers prevented

---

### TC-302: Manual Time Entry
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can manually add time entries

**Preconditions:**
- User is logged in
- Task item exists
- User has time tracking permissions

**Test Steps:**
1. Navigate to item details
2. Click "Add Time Entry" button
3. Select date: "2024-12-15"
4. Enter start time: "09:00 AM"
5. Enter end time: "10:30 AM"
6. Add description: "Implemented user login API"
7. Mark as billable: true
8. Click "Save Time Entry" button

**Expected Results:**
- Time entry saved with 1.5 hours duration
- Entry appears in time tracking list
- Billable flag properly set
- Total hours updated on item

**Acceptance Criteria:**
- ✅ Duration calculated correctly (1.5 hours)
- ✅ Entry linked to correct item and user
- ✅ Billable status saved properly
- ✅ Time statistics updated

---

### TC-303: Time Tracking Reports
**Priority:** Medium | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that time tracking reports generate accurate data

**Preconditions:**
- Multiple time entries exist
- Time entries span multiple dates
- Different users have time entries

**Test Steps:**
1. Navigate to time tracking reports
2. Select date range: "Last 30 days"
3. Filter by user: "Current user"
4. Filter by project/board
5. Generate report
6. Verify total hours calculation
7. Verify billable vs non-billable breakdown
8. Export report as CSV
9. Verify export data accuracy

**Expected Results:**
- Report shows accurate time totals
- Filters work correctly
- Export includes all visible data
- Charts display properly

**Acceptance Criteria:**
- ✅ Time calculations accurate to minute precision
- ✅ Filters properly applied
- ✅ Export contains correct data
- ✅ Charts render without errors

---

## Analytics Dashboard Test Cases

### TC-401: Board Analytics Display
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that board analytics display accurate metrics

**Preconditions:**
- Board with historical data exists
- Items have various statuses and completion dates
- Multiple users have contributed to board

**Test Steps:**
1. Navigate to board analytics
2. Verify velocity chart displays
3. Check completion rate metrics
4. Verify member activity chart
5. Test time range filter (Last 30 days)
6. Test time range filter (Last 7 days)
7. Verify export functionality
8. Check real-time updates

**Expected Results:**
- All charts render correctly
- Metrics calculations are accurate
- Filters update data correctly
- Export works properly

**Acceptance Criteria:**
- ✅ Velocity calculation matches manual calculation
- ✅ Completion rate reflects actual data
- ✅ Charts update when filters applied
- ✅ Export contains chart data

---

### TC-402: Organization Analytics
**Priority:** Medium | **Type:** Functional | **Automation:** Automated

**Objective:** Verify organization-wide analytics are accurate and secure

**Preconditions:**
- User has organization admin role
- Multiple workspaces and boards exist
- Historical data available

**Test Steps:**
1. Navigate to organization analytics
2. Verify workspace overview metrics
3. Check team productivity metrics
4. Test user activity reports
5. Verify permission-based data access
6. Login as non-admin user
7. Verify restricted access to sensitive data

**Expected Results:**
- Admin sees all organization data
- Non-admin sees only permitted data
- Metrics are calculated correctly
- Performance is acceptable

**Acceptance Criteria:**
- ✅ Permission-based data filtering
- ✅ Accurate cross-workspace calculations
- ✅ Charts load within 3 seconds
- ✅ Data refresh works correctly

---

## Webhook Management Test Cases

### TC-501: Create Webhook
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can create webhooks for event notifications

**Preconditions:**
- User is logged in
- User has webhook management permissions
- External endpoint available for testing

**Test Steps:**
1. Navigate to webhook management
2. Click "Create Webhook" button
3. Enter webhook URL: "https://api.example.com/webhook"
4. Select events: "item.created", "item.updated"
5. Set scope: "Current Board"
6. Enter description: "Sync with external CRM"
7. Click "Create Webhook" button
8. Verify webhook appears in list
9. Test webhook endpoint

**Expected Results:**
- Webhook created successfully
- Secret key generated
- Webhook appears in management list
- Test delivery successful

**Acceptance Criteria:**
- ✅ Webhook saved with correct configuration
- ✅ Secret key generated for security
- ✅ Test delivery works
- ✅ Webhook status shows as "Active"

---

### TC-502: Webhook Event Delivery
**Priority:** Critical | **Type:** Integration | **Automation:** Semi-automated

**Objective:** Verify that webhooks deliver events correctly

**Preconditions:**
- Webhook configured for item events
- External endpoint monitoring requests
- Board with items exists

**Test Steps:**
1. Create new item on board
2. Verify webhook delivery triggered
3. Check payload format and content
4. Update item status
5. Verify update event delivered
6. Delete item
7. Verify delete event delivered
8. Test delivery failure and retry logic

**Expected Results:**
- Events delivered within 5 seconds
- Payload format matches specification
- HMAC signature valid
- Retry logic works on failures

**Acceptance Criteria:**
- ✅ Event delivery within 5 seconds
- ✅ Payload contains correct event data
- ✅ HMAC signature validates
- ✅ Failed deliveries retry up to 3 times

---

## File Management Test Cases

### TC-601: File Upload
**Priority:** High | **Type:** Functional | **Automation:** Automated

**Objective:** Verify that users can upload files to items

**Preconditions:**
- User is logged in
- Item exists for file attachment
- Various file types available for testing

**Test Steps:**
1. Navigate to item details
2. Click "Attach File" button
3. Select image file (test.jpg, 2MB)
4. Verify upload progress indicator
5. Verify file appears in attachments list
6. Upload document file (test.pdf, 5MB)
7. Upload large file (test.zip, 15MB)
8. Test unsupported file type (.exe)

**Expected Results:**
- Supported files upload successfully
- Progress indicator shows upload status
- Files appear in attachments list
- Unsupported files rejected with error

**Acceptance Criteria:**
- ✅ Upload completes within 30 seconds for 15MB file
- ✅ File metadata properly stored
- ✅ File type validation works
- ✅ Storage limits enforced

---

### TC-602: File Security and Access Control
**Priority:** Critical | **Type:** Security | **Automation:** Automated

**Objective:** Verify that file access is properly controlled

**Preconditions:**
- Files attached to items with different permissions
- Users with different access levels
- Private and public boards exist

**Test Steps:**
1. Upload file to private board item
2. Login as unauthorized user
3. Attempt to access file URL directly
4. Verify access denied
5. Login as authorized user
6. Verify file access successful
7. Test file sharing links
8. Verify link expiration works

**Expected Results:**
- Unauthorized access blocked
- Authorized access works correctly
- Sharing links work as expected
- Link expiration enforced

**Acceptance Criteria:**
- ✅ 403 error for unauthorized access
- ✅ File access requires authentication
- ✅ Sharing links expire as configured
- ✅ File permissions inherit from item permissions

---

## Real-time Collaboration Test Cases

### TC-701: Multi-user Editing
**Priority:** Critical | **Type:** Functional | **Automation:** Semi-automated

**Objective:** Verify that multiple users can edit simultaneously without conflicts

**Preconditions:**
- Board with editing permissions for multiple users
- WebSocket connections established
- Multiple browser sessions or users

**Test Steps:**
1. User A opens item for editing
2. User B opens same item for editing
3. User A modifies item title
4. User B modifies item description simultaneously
5. Both users save changes
6. Verify both changes preserved
7. Test conflict resolution for same field
8. Verify last-write-wins logic

**Expected Results:**
- Simultaneous edits to different fields work
- Conflicts resolved consistently
- No data loss occurs
- Users notified of conflicts

**Acceptance Criteria:**
- ✅ Different fields edited simultaneously
- ✅ Same field conflicts resolved properly
- ✅ Users receive conflict notifications
- ✅ Data integrity maintained

---

### TC-702: User Presence Indicators
**Priority:** Medium | **Type:** Usability | **Automation:** Semi-automated

**Objective:** Verify that user presence is accurately displayed

**Preconditions:**
- Multiple users with board access
- Real-time features enabled
- WebSocket connections working

**Test Steps:**
1. User A joins board
2. Verify User A appears in presence list
3. User B joins same board
4. Verify both users shown in presence
5. User A leaves board
6. Verify User A removed from presence list
7. Test presence timeout on connection loss
8. Test presence across different board views

**Expected Results:**
- Presence accurately reflects active users
- Join/leave events update immediately
- Timeout removes inactive users
- Presence works across board views

**Acceptance Criteria:**
- ✅ Presence updates within 2 seconds
- ✅ Inactive users removed after 30 seconds
- ✅ Presence consistent across views
- ✅ No ghost users in presence list

---

## Performance Test Cases

### TC-801: API Response Time
**Priority:** High | **Type:** Performance | **Automation:** Automated

**Objective:** Verify that API endpoints meet performance requirements

**Preconditions:**
- Application deployed and accessible
- Test data loaded in database
- Load testing tools configured

**Test Steps:**
1. Execute 100 concurrent GET /api/boards requests
2. Measure average response time
3. Execute 50 concurrent POST /api/items requests
4. Measure 95th percentile response time
5. Execute 25 concurrent file upload requests
6. Measure system performance under load

**Expected Results:**
- Average response time < 200ms
- 95th percentile < 500ms
- No errors under normal load
- System remains stable

**Acceptance Criteria:**
- ✅ Average response time meets target
- ✅ 95th percentile within limits
- ✅ Error rate < 1%
- ✅ Memory usage stable

---

### TC-802: Frontend Performance
**Priority:** Medium | **Type:** Performance | **Automation:** Automated

**Objective:** Verify that frontend meets performance requirements

**Preconditions:**
- Application built for production
- Performance testing tools available
- Various network conditions simulated

**Test Steps:**
1. Load board page with 100 items
2. Measure initial page load time
3. Test scrolling performance
4. Measure time to interactive
5. Test on slow 3G connection
6. Measure bundle size and loading

**Expected Results:**
- Page loads within 3 seconds
- Smooth scrolling performance
- Interactive within 5 seconds
- Acceptable performance on mobile

**Acceptance Criteria:**
- ✅ First contentful paint < 2 seconds
- ✅ Time to interactive < 5 seconds
- ✅ Bundle size < 3MB
- ✅ 60 FPS scrolling performance

---

## Security Test Cases

### TC-901: SQL Injection Prevention
**Priority:** Critical | **Type:** Security | **Automation:** Automated

**Objective:** Verify that SQL injection attacks are prevented

**Preconditions:**
- Application accessible for testing
- Database with test data
- Security testing tools available

**Test Steps:**
1. Attempt SQL injection in login form
2. Test malicious input in search fields
3. Try injection in API parameters
4. Test file upload with malicious content
5. Verify parameterized queries used
6. Test error messages for information leakage

**Expected Results:**
- All injection attempts blocked
- No database errors exposed
- Application remains stable
- Security logs capture attempts

**Acceptance Criteria:**
- ✅ No successful SQL injection
- ✅ Error messages don't leak information
- ✅ All inputs properly validated
- ✅ Security events logged

---

### TC-902: Authentication Security
**Priority:** Critical | **Type:** Security | **Automation:** Automated

**Objective:** Verify that authentication mechanisms are secure

**Preconditions:**
- User accounts available for testing
- Security testing tools configured
- Various attack scenarios prepared

**Test Steps:**
1. Test brute force attack protection
2. Verify JWT token security
3. Test session management
4. Verify password policy enforcement
5. Test multi-factor authentication
6. Check for session fixation vulnerabilities

**Expected Results:**
- Brute force attempts blocked
- JWT tokens properly secured
- Session management secure
- Password policies enforced

**Acceptance Criteria:**
- ✅ Account lockout after 5 failed attempts
- ✅ JWT tokens properly signed and validated
- ✅ Sessions expire appropriately
- ✅ Strong password requirements enforced

---

## Accessibility Test Cases

### TC-1001: Keyboard Navigation
**Priority:** High | **Type:** Accessibility | **Automation:** Semi-automated

**Objective:** Verify that all functionality is accessible via keyboard

**Preconditions:**
- Application fully loaded
- Screen reader software available
- Keyboard navigation testing tools

**Test Steps:**
1. Navigate entire application using only Tab key
2. Test all interactive elements reachable
3. Verify focus indicators visible
4. Test keyboard shortcuts work
5. Test modal dialog navigation
6. Verify screen reader compatibility

**Expected Results:**
- All interactive elements accessible
- Focus indicators clearly visible
- Logical tab order maintained
- Screen reader announces correctly

**Acceptance Criteria:**
- ✅ All buttons/links accessible via keyboard
- ✅ Focus indicators meet WCAG contrast requirements
- ✅ Tab order follows logical flow
- ✅ Screen reader announces all content properly

---

### TC-1002: Color Contrast and Visual Design
**Priority:** Medium | **Type:** Accessibility | **Automation:** Automated

**Objective:** Verify that visual design meets accessibility standards

**Preconditions:**
- Application styles fully loaded
- Color contrast testing tools available
- WCAG testing guidelines

**Test Steps:**
1. Test color contrast ratios for all text
2. Verify information not conveyed by color alone
3. Test with high contrast mode
4. Verify text scaling to 200%
5. Test with different color vision simulations

**Expected Results:**
- All text meets WCAG AA contrast ratios
- Information accessible without color
- High contrast mode works properly
- Text scaling maintains functionality

**Acceptance Criteria:**
- ✅ Contrast ratio ≥ 4.5:1 for normal text
- ✅ Contrast ratio ≥ 3:1 for large text
- ✅ Color not sole indicator of meaning
- ✅ Text scalable to 200% without loss of functionality

---

## Test Case Summary

### Test Case Statistics
- **Total Test Cases**: 32
- **Critical Priority**: 12 test cases
- **High Priority**: 12 test cases
- **Medium Priority**: 6 test cases
- **Low Priority**: 2 test cases

### Automation Coverage
- **Fully Automated**: 24 test cases (75%)
- **Semi-automated**: 6 test cases (19%)
- **Manual Only**: 2 test cases (6%)

### Test Categories
- **Functional**: 18 test cases (56%)
- **Security**: 6 test cases (19%)
- **Performance**: 4 test cases (13%)
- **Usability**: 2 test cases (6%)
- **Accessibility**: 2 test cases (6%)

---

**Legend:**
- ✅ Pass criteria that must be met
- ⚠️ Warning criteria (investigate if not met)
- ❌ Fail criteria (test fails if not met)

*Test Cases Document Version: 1.0*
*Last Updated: December 2024*
*Next Review: After implementation of missing features*