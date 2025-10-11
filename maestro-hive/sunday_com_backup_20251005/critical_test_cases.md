# Critical Test Cases - Sunday.com MVP
*QA Engineer: Test Case Generation*
*Date: December 2024*
*Priority: Critical Features Only*

## Test Case Overview

This document contains detailed test cases for the most critical features of Sunday.com MVP. Each test case includes preconditions, test steps, expected results, and success criteria.

**Coverage**: Core functionality that must work for MVP release
**Total Test Cases**: 45 critical test cases
**Execution Priority**: High

---

## Test Case Categories

### 1. Authentication & User Management (8 test cases)
### 2. Board Management (12 test cases)
### 3. Item/Task Management (10 test cases)
### 4. Real-time Collaboration (8 test cases)
### 5. File Management (4 test cases)
### 6. Security & Permissions (3 test cases)

---

## 1. Authentication & User Management

### TC-AUTH-001: User Registration Flow
**Priority**: Critical
**Component**: Authentication Service
**Test Type**: End-to-End

**Preconditions**:
- Application is accessible
- Email service is configured
- Database is accessible

**Test Steps**:
1. Navigate to registration page `/register`
2. Enter valid email: `test@example.com`
3. Enter strong password: `TestPass123!`
4. Enter full name: `Test User`
5. Select organization role: `Member`
6. Click "Create Account" button
7. Verify email confirmation sent
8. Check redirect to dashboard

**Expected Results**:
- ✅ User account created in database
- ✅ Confirmation email sent
- ✅ JWT token generated
- ✅ User redirected to dashboard
- ✅ Welcome message displayed

**Success Criteria**: User can successfully register and access application

---

### TC-AUTH-002: User Login Flow
**Priority**: Critical
**Component**: Authentication Service
**Test Type**: End-to-End

**Preconditions**:
- User account exists in system
- User is not currently logged in

**Test Steps**:
1. Navigate to login page `/login`
2. Enter registered email
3. Enter correct password
4. Click "Sign In" button
5. Verify successful login
6. Check user session creation

**Expected Results**:
- ✅ JWT token generated and stored
- ✅ User redirected to dashboard
- ✅ Navigation shows user info
- ✅ Session persisted in localStorage

**Success Criteria**: Registered user can successfully log in

---

### TC-AUTH-003: Password Reset Flow
**Priority**: High
**Component**: Authentication Service
**Test Type**: Integration

**Preconditions**:
- User account exists
- Email service operational

**Test Steps**:
1. Navigate to login page
2. Click "Forgot Password" link
3. Enter registered email address
4. Click "Send Reset Link"
5. Check email for reset link
6. Click reset link from email
7. Enter new password
8. Confirm password change
9. Login with new password

**Expected Results**:
- ✅ Reset email sent successfully
- ✅ Reset token validates correctly
- ✅ Password updated in database
- ✅ Old password no longer works
- ✅ New password allows login

**Success Criteria**: User can reset password via email

---

### TC-AUTH-004: Session Persistence
**Priority**: Medium
**Component**: Authentication Service
**Test Type**: Unit

**Test Steps**:
1. Login successfully
2. Close browser tab
3. Reopen application
4. Verify user still logged in
5. Test token refresh mechanism

**Expected Results**:
- ✅ Session maintained across browser restarts
- ✅ Token auto-refreshed before expiry
- ✅ User remains authenticated

---

### TC-AUTH-005: Logout Functionality
**Priority**: Medium
**Component**: Authentication Service
**Test Type**: Unit

**Test Steps**:
1. Login to application
2. Click logout button
3. Verify session cleanup
4. Try accessing protected route

**Expected Results**:
- ✅ JWT token invalidated
- ✅ localStorage cleared
- ✅ Redirected to login page
- ✅ Cannot access protected routes

---

### TC-AUTH-006: Invalid Login Attempts
**Priority**: High
**Component**: Authentication Security
**Test Type**: Security

**Test Steps**:
1. Enter invalid email/password combinations
2. Attempt multiple failed logins
3. Verify rate limiting kicks in
4. Test account lockout mechanism

**Expected Results**:
- ✅ Clear error messages displayed
- ✅ Rate limiting after 5 failed attempts
- ✅ Account temporarily locked
- ✅ No sensitive information leaked

---

### TC-AUTH-007: Token Validation
**Priority**: Critical
**Component**: JWT Service
**Test Type**: Security

**Test Steps**:
1. Generate valid JWT token
2. Test with expired token
3. Test with tampered token
4. Test with malformed token

**Expected Results**:
- ✅ Valid tokens accepted
- ✅ Expired tokens rejected
- ✅ Tampered tokens rejected
- ✅ Proper error responses

---

### TC-AUTH-008: Profile Update
**Priority**: Medium
**Component**: User Profile
**Test Type**: Integration

**Test Steps**:
1. Login as authenticated user
2. Navigate to profile settings
3. Update name and email
4. Save changes
5. Verify updates persisted

**Expected Results**:
- ✅ Profile updates saved
- ✅ Email validation if changed
- ✅ UI reflects changes
- ✅ Database updated correctly

---

## 2. Board Management

### TC-BOARD-001: Create New Board
**Priority**: Critical
**Component**: Board Service
**Test Type**: End-to-End

**Preconditions**:
- User is logged in
- User has workspace access

**Test Steps**:
1. Navigate to boards page
2. Click "Create Board" button
3. Enter board name: `Test Project Board`
4. Enter description: `Board for testing purposes`
5. Select workspace
6. Choose template: `Basic Kanban`
7. Click "Create Board"
8. Verify board creation

**Expected Results**:
- ✅ Board created with unique ID
- ✅ Default columns added (To Do, In Progress, Done)
- ✅ User added as board owner
- ✅ Board appears in workspace
- ✅ Redirected to board view

**Success Criteria**: User can create functional board with default structure

---

### TC-BOARD-002: Board View Rendering
**Priority**: Critical
**Component**: BoardView Component
**Test Type**: End-to-End

**Preconditions**:
- Board exists in system
- User has read access

**Test Steps**:
1. Navigate to board URL `/board/{boardId}`
2. Verify board header displays
3. Check column structure
4. Verify items are displayed
5. Test responsive layout

**Expected Results**:
- ✅ Board name and description shown
- ✅ All columns rendered correctly
- ✅ Items grouped by status
- ✅ Drag-and-drop indicators visible
- ✅ Mobile view adapts properly

**Success Criteria**: Board displays correctly with all components

---

### TC-BOARD-003: Kanban Drag and Drop
**Priority**: Critical
**Component**: Drag and Drop Service
**Test Type**: Integration

**Preconditions**:
- Board with multiple columns exists
- Items exist in different columns

**Test Steps**:
1. Open board in kanban view
2. Drag item from "To Do" to "In Progress"
3. Verify item position changes
4. Drag item to different position in same column
5. Test drag between multiple columns

**Expected Results**:
- ✅ Item moves to target column
- ✅ Item status updates automatically
- ✅ Position saved in database
- ✅ Real-time update to other users
- ✅ Visual feedback during drag

**Success Criteria**: Drag and drop works smoothly with persistence

---

### TC-BOARD-004: Column Management
**Priority**: High
**Component**: Board Service
**Test Type**: Integration

**Test Steps**:
1. Open board settings
2. Add new column "Review"
3. Rename existing column
4. Change column color
5. Delete unused column
6. Reorder columns

**Expected Results**:
- ✅ New column appears on board
- ✅ Column names update immediately
- ✅ Color changes reflected
- ✅ Column deletion removes items appropriately
- ✅ Column order persisted

---

### TC-BOARD-005: Board Permissions
**Priority**: High
**Component**: Authorization Service
**Test Type**: Security

**Test Steps**:
1. Create board as Owner
2. Invite user as Viewer
3. Test Viewer cannot edit
4. Promote user to Editor
5. Test Editor can modify items
6. Test Admin can manage permissions

**Expected Results**:
- ✅ Permissions enforced correctly
- ✅ UI adapts to user role
- ✅ API rejects unauthorized actions
- ✅ Permission changes take effect immediately

---

### TC-BOARD-006: Board Search and Filter
**Priority**: Medium
**Component**: Board Service
**Test Type**: Integration

**Test Steps**:
1. Create board with multiple items
2. Search for specific item name
3. Filter by assignee
4. Filter by status
5. Clear filters

**Expected Results**:
- ✅ Search returns matching items
- ✅ Filters work independently
- ✅ Combined filters work correctly
- ✅ Clear filters restores all items

---

### TC-BOARD-007: Board Templates
**Priority**: Medium
**Component**: Template Service
**Test Type**: Integration

**Test Steps**:
1. Access board creation
2. Select different templates
3. Verify template structure applied
4. Customize template columns
5. Save as custom template

**Expected Results**:
- ✅ Templates create correct structure
- ✅ Customizations preserved
- ✅ Custom templates saveable

---

### TC-BOARD-008: Board Duplication
**Priority**: Low
**Component**: Board Service
**Test Type**: Integration

**Test Steps**:
1. Select existing board
2. Click "Duplicate Board"
3. Modify duplicate name
4. Verify content copied
5. Test permissions inherited

**Expected Results**:
- ✅ Board structure duplicated
- ✅ Items copied correctly
- ✅ Permissions copied appropriately

---

### TC-BOARD-009: Board Archiving
**Priority**: Medium
**Component**: Board Service
**Test Type**: Integration

**Test Steps**:
1. Navigate to board settings
2. Click "Archive Board"
3. Confirm archive action
4. Verify board hidden from workspace
5. Test board restoration

**Expected Results**:
- ✅ Board marked as archived
- ✅ Hidden from active boards
- ✅ Data preserved
- ✅ Restoration works correctly

---

### TC-BOARD-010: Board Sharing
**Priority**: High
**Component**: Sharing Service
**Test Type**: Integration

**Test Steps**:
1. Open board sharing dialog
2. Generate shareable link
3. Set link permissions
4. Test anonymous access
5. Revoke link access

**Expected Results**:
- ✅ Shareable link generated
- ✅ Permissions enforced
- ✅ Anonymous users see correct view
- ✅ Link revocation works

---

### TC-BOARD-011: Board Export
**Priority**: Low
**Component**: Export Service
**Test Type**: Integration

**Test Steps**:
1. Navigate to board options
2. Select export format (CSV)
3. Choose export data scope
4. Download export file
5. Verify data completeness

**Expected Results**:
- ✅ Export file generated
- ✅ Data format correct
- ✅ All selected data included

---

### TC-BOARD-012: Board Performance
**Priority**: High
**Component**: Board Rendering
**Test Type**: Performance

**Test Steps**:
1. Create board with 100+ items
2. Measure initial load time
3. Test scroll performance
4. Measure drag-and-drop responsiveness
5. Test concurrent user performance

**Expected Results**:
- ✅ Load time < 2 seconds
- ✅ Smooth scrolling
- ✅ Responsive drag operations
- ✅ No performance degradation with multiple users

---

## 3. Item/Task Management

### TC-ITEM-001: Create New Item
**Priority**: Critical
**Component**: Item Service
**Test Type**: End-to-End

**Preconditions**:
- User is logged in
- Board exists and is accessible

**Test Steps**:
1. Navigate to board view
2. Click "Add Item" in a column
3. Enter item name: `Test Task`
4. Enter description: `This is a test task`
5. Select assignee from dropdown
6. Set due date
7. Add labels/tags
8. Click "Create Item"

**Expected Results**:
- ✅ Item created with unique ID
- ✅ Item appears in correct column
- ✅ All properties saved correctly
- ✅ Assignee receives notification
- ✅ Item position set correctly

**Success Criteria**: User can create item with all required properties

---

### TC-ITEM-002: Edit Item Details
**Priority**: Critical
**Component**: Item Form Component
**Test Type**: Integration

**Preconditions**:
- Item exists on board
- User has edit permissions

**Test Steps**:
1. Click on existing item
2. Open item details modal
3. Edit item name
4. Update description
5. Change assignee
6. Modify due date
7. Add/remove labels
8. Save changes

**Expected Results**:
- ✅ All changes saved to database
- ✅ UI updates immediately
- ✅ Other users see updates real-time
- ✅ Change history tracked
- ✅ Notifications sent for relevant changes

**Success Criteria**: Item properties can be updated successfully

---

### TC-ITEM-003: Item Status Workflow
**Priority**: Critical
**Component**: Workflow Engine
**Test Type**: Integration

**Test Steps**:
1. Create item in "To Do" status
2. Move to "In Progress"
3. Verify status change
4. Move to "Done"
5. Test status restrictions
6. Verify automated actions

**Expected Results**:
- ✅ Status transitions work correctly
- ✅ Position updates automatically
- ✅ Automated rules trigger
- ✅ History recorded
- ✅ Notifications sent

---

### TC-ITEM-004: Item Assignment
**Priority**: High
**Component**: Assignment Service
**Test Type**: Integration

**Test Steps**:
1. Open item details
2. Assign to team member
3. Verify assignee notification
4. Change assignee
5. Test multiple assignees
6. Remove assignment

**Expected Results**:
- ✅ Assignment saved correctly
- ✅ Notifications sent appropriately
- ✅ UI shows assigned users
- ✅ Assignment changes tracked

---

### TC-ITEM-005: Item Comments
**Priority**: Medium
**Component**: Comment Service
**Test Type**: Integration

**Test Steps**:
1. Open item details
2. Add comment with text
3. Mention another user (@username)
4. Edit existing comment
5. Delete comment
6. Verify comment threading

**Expected Results**:
- ✅ Comments saved and displayed
- ✅ Mentions trigger notifications
- ✅ Edit/delete permissions enforced
- ✅ Threading works correctly

---

### TC-ITEM-006: Item Attachments
**Priority**: Medium
**Component**: File Service
**Test Type**: Integration

**Test Steps**:
1. Open item details
2. Upload file attachment
3. Verify file preview
4. Download attachment
5. Delete attachment
6. Test multiple file types

**Expected Results**:
- ✅ Files upload successfully
- ✅ Previews generated correctly
- ✅ Downloads work properly
- ✅ File permissions enforced

---

### TC-ITEM-007: Item Dependencies
**Priority**: Medium
**Component**: Dependency Service
**Test Type**: Integration

**Test Steps**:
1. Create two items
2. Set dependency relationship
3. Test blocking behavior
4. Remove dependency
5. Verify workflow rules

**Expected Results**:
- ✅ Dependencies tracked correctly
- ✅ Blocking rules enforced
- ✅ Visual indicators shown

---

### TC-ITEM-008: Item Search
**Priority**: Medium
**Component**: Search Service
**Test Type**: Integration

**Test Steps**:
1. Create items with various properties
2. Search by item name
3. Search by assignee
4. Search by labels
5. Use advanced filters

**Expected Results**:
- ✅ Search returns accurate results
- ✅ Filters work correctly
- ✅ Performance acceptable

---

### TC-ITEM-009: Bulk Item Operations
**Priority**: High
**Component**: Bulk Operations
**Test Type**: Integration

**Test Steps**:
1. Select multiple items
2. Bulk edit assignees
3. Bulk change status
4. Bulk delete items
5. Verify undo functionality

**Expected Results**:
- ✅ Bulk operations complete successfully
- ✅ All selected items updated
- ✅ Undo works correctly

---

### TC-ITEM-010: Item Performance
**Priority**: High
**Component**: Item Rendering
**Test Type**: Performance

**Test Steps**:
1. Create board with 500+ items
2. Measure load performance
3. Test filtering performance
4. Test update responsiveness

**Expected Results**:
- ✅ Load time acceptable
- ✅ Smooth interactions
- ✅ No memory leaks

---

## 4. Real-time Collaboration

### TC-REALTIME-001: WebSocket Connection
**Priority**: Critical
**Component**: WebSocket Service
**Test Type**: Integration

**Test Steps**:
1. Login to application
2. Navigate to board
3. Verify WebSocket connection established
4. Test connection persistence
5. Test reconnection on failure

**Expected Results**:
- ✅ WebSocket connects successfully
- ✅ Connection maintained during session
- ✅ Auto-reconnect on disconnect
- ✅ No duplicate connections

---

### TC-REALTIME-002: Live Presence Indicators
**Priority**: High
**Component**: Presence Service
**Test Type**: Integration

**Preconditions**:
- Multiple users have board access
- WebSocket connections active

**Test Steps**:
1. User A opens board
2. User B opens same board
3. Verify both users see each other online
4. User A leaves board
5. Verify User B sees User A offline

**Expected Results**:
- ✅ Online users displayed correctly
- ✅ Offline detection works
- ✅ User avatars shown
- ✅ Real-time updates smooth

---

### TC-REALTIME-003: Live Item Updates
**Priority**: Critical
**Component**: Real-time Sync
**Test Type**: Integration

**Test Steps**:
1. User A and B view same board
2. User A creates new item
3. Verify User B sees new item immediately
4. User B edits item
5. Verify User A sees changes real-time

**Expected Results**:
- ✅ Changes propagate < 500ms
- ✅ No conflicts or overwrites
- ✅ UI updates smoothly
- ✅ Change attribution shown

---

### TC-REALTIME-004: Collaborative Editing
**Priority**: High
**Component**: Conflict Resolution
**Test Type**: Integration

**Test Steps**:
1. Two users edit same item simultaneously
2. Test conflict resolution
3. Verify last-writer-wins behavior
4. Test optimistic updates
5. Verify rollback on conflicts

**Expected Results**:
- ✅ Conflicts handled gracefully
- ✅ No data loss
- ✅ Clear conflict indication
- ✅ Proper resolution algorithm

---

### TC-REALTIME-005: Live Cursors
**Priority**: Medium
**Component**: Cursor Tracking
**Test Type**: Integration

**Test Steps**:
1. Multiple users on same board
2. Verify cursor positions shown
3. Test cursor movement tracking
4. Verify cursor disappears when user leaves

**Expected Results**:
- ✅ Cursors displayed accurately
- ✅ Smooth movement tracking
- ✅ Proper cleanup on disconnect

---

### TC-REALTIME-006: Broadcasting Performance
**Priority**: High
**Component**: Message Broadcasting
**Test Type**: Performance

**Test Steps**:
1. Simulate 50 concurrent users
2. Generate frequent updates
3. Measure broadcast latency
4. Test bandwidth usage
5. Verify no message loss

**Expected Results**:
- ✅ Latency < 100ms
- ✅ Reasonable bandwidth usage
- ✅ No message drops
- ✅ Performance scales well

---

### TC-REALTIME-007: Connection Recovery
**Priority**: High
**Component**: Resilience Testing
**Test Type**: Integration

**Test Steps**:
1. Establish connection
2. Simulate network interruption
3. Verify automatic reconnection
4. Test data synchronization
5. Verify no data loss

**Expected Results**:
- ✅ Reconnection automatic
- ✅ Data resynchronized
- ✅ No duplicate messages
- ✅ User experience smooth

---

### TC-REALTIME-008: Notification System
**Priority**: Medium
**Component**: Notification Service
**Test Type**: Integration

**Test Steps**:
1. User A assigns item to User B
2. Verify User B receives notification
3. Test in-app notifications
4. Test browser notifications
5. Verify notification preferences

**Expected Results**:
- ✅ Notifications delivered correctly
- ✅ Proper notification content
- ✅ Preferences respected
- ✅ No spam/duplicate notifications

---

## 5. File Management

### TC-FILE-001: File Upload
**Priority**: High
**Component**: File Service
**Test Type**: Integration

**Test Steps**:
1. Navigate to item details
2. Click file upload area
3. Select multiple files
4. Verify upload progress
5. Test upload cancellation

**Expected Results**:
- ✅ Files upload successfully
- ✅ Progress indicator works
- ✅ Cancellation works
- ✅ File metadata stored

---

### TC-FILE-002: File Security
**Priority**: Critical
**Component**: File Security
**Test Type**: Security

**Test Steps**:
1. Upload various file types
2. Test malicious file upload
3. Verify file type restrictions
4. Test file size limits
5. Verify virus scanning

**Expected Results**:
- ✅ Malicious files rejected
- ✅ File type validation works
- ✅ Size limits enforced
- ✅ Security scanning active

---

### TC-FILE-003: File Access Control
**Priority**: High
**Component**: File Permissions
**Test Type**: Security

**Test Steps**:
1. Upload file to private item
2. Test unauthorized access
3. Verify permission inheritance
4. Test file sharing
5. Test download permissions

**Expected Results**:
- ✅ Unauthorized access blocked
- ✅ Permissions inherited correctly
- ✅ Sharing works securely

---

### TC-FILE-004: File Performance
**Priority**: Medium
**Component**: File Handling
**Test Type**: Performance

**Test Steps**:
1. Upload large files (100MB+)
2. Test multiple concurrent uploads
3. Measure download speeds
4. Test thumbnail generation

**Expected Results**:
- ✅ Large files handled correctly
- ✅ Concurrent uploads work
- ✅ Download speeds acceptable
- ✅ Thumbnails generated quickly

---

## 6. Security & Permissions

### TC-SEC-001: SQL Injection Prevention
**Priority**: Critical
**Component**: Database Security
**Test Type**: Security

**Test Steps**:
1. Attempt SQL injection in form fields
2. Test API endpoint parameters
3. Verify parameterized queries
4. Test search functionality
5. Verify input sanitization

**Expected Results**:
- ✅ SQL injection attempts blocked
- ✅ Parameterized queries used
- ✅ Input properly sanitized
- ✅ No data exposure

---

### TC-SEC-002: XSS Protection
**Priority**: Critical
**Component**: Input Validation
**Test Type**: Security

**Test Steps**:
1. Input script tags in text fields
2. Test HTML injection
3. Verify output encoding
4. Test rich text editors
5. Verify CSP headers

**Expected Results**:
- ✅ Script execution blocked
- ✅ HTML properly escaped
- ✅ CSP headers present
- ✅ No XSS vulnerabilities

---

### TC-SEC-003: Authorization Enforcement
**Priority**: Critical
**Component**: Access Control
**Test Type**: Security

**Test Steps**:
1. Test role-based access
2. Attempt privilege escalation
3. Test resource ownership
4. Verify API endpoint protection
5. Test session management

**Expected Results**:
- ✅ Roles enforced correctly
- ✅ Privilege escalation blocked
- ✅ Resource access controlled
- ✅ API protection works

---

## Test Execution Matrix

| Test Case | Priority | Status | Automation | Dependencies |
|-----------|----------|--------|------------|--------------|
| TC-AUTH-001 | Critical | ✅ | ✅ | Email service |
| TC-AUTH-002 | Critical | ✅ | ✅ | Database |
| TC-BOARD-001 | Critical | ✅ | ✅ | Workspace |
| TC-BOARD-002 | Critical | ✅ | ✅ | Board exists |
| TC-BOARD-003 | Critical | ✅ | ⚠️ | WebSocket |
| TC-ITEM-001 | Critical | ✅ | ✅ | Board access |
| TC-REALTIME-001 | Critical | ✅ | ⚠️ | WebSocket |
| TC-FILE-001 | High | ✅ | ✅ | Storage |
| TC-SEC-001 | Critical | ✅ | ✅ | None |

**Legend**:
- ✅ Ready for execution
- ⚠️ Partial automation/dependencies
- ❌ Blocked by missing features

---

## Execution Priority

### Phase 1 (Immediate): Authentication & Core Features
- All TC-AUTH test cases
- TC-BOARD-001, TC-BOARD-002
- TC-ITEM-001, TC-ITEM-002
- All TC-SEC test cases

### Phase 2 (High Priority): Advanced Features
- Remaining TC-BOARD test cases
- Remaining TC-ITEM test cases
- TC-FILE test cases

### Phase 3 (System Integration): Real-time Features
- All TC-REALTIME test cases
- Performance test cases
- Cross-browser validation

---

## Success Metrics

- **Critical Test Cases**: 100% pass rate required
- **High Priority**: 95% pass rate required
- **Medium Priority**: 90% pass rate required
- **Automation Coverage**: 80% of test cases automated
- **Performance**: All response times within SLA

---

*Test Cases Generated: December 2024*
*QA Engineer: Critical Feature Testing*
*Total: 45 test cases covering core MVP functionality*