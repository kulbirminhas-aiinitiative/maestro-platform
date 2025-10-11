# Bug Report Template - Sunday.com

## Bug Information

**Bug ID:** SUNDAY-[NUMBER]
**Date Reported:** [DATE]
**Reported By:** [REPORTER_NAME]
**Assigned To:** [ASSIGNEE_NAME]
**Sprint/Release:** [SPRINT_NUMBER] / [RELEASE_VERSION]

## Bug Classification

**Priority:**
- [ ] P0 - Critical (System down, data loss, security breach)
- [ ] P1 - High (Major feature broken, significant user impact)
- [ ] P2 - Medium (Feature partially working, moderate impact)
- [ ] P3 - Low (Minor issue, cosmetic, nice-to-have)

**Severity:**
- [ ] Critical - System unusable, data corruption
- [ ] High - Major functionality impacted
- [ ] Medium - Minor functionality impacted
- [ ] Low - Cosmetic or documentation issue

**Bug Type:**
- [ ] Functional
- [ ] Performance
- [ ] UI/UX
- [ ] Security
- [ ] Accessibility
- [ ] Integration
- [ ] Data/Database
- [ ] API
- [ ] Mobile-specific
- [ ] Browser-specific

**Component/Epic:**
- [ ] Core Work Management
- [ ] AI-Powered Automation
- [ ] Real-Time Collaboration
- [ ] Customization & Configuration
- [ ] Analytics & Reporting
- [ ] Integration Ecosystem
- [ ] Mobile Experience
- [ ] Security & Compliance
- [ ] Infrastructure
- [ ] Other: [SPECIFY]

## Environment Information

**Environment:**
- [ ] Development
- [ ] Test
- [ ] Staging
- [ ] Production

**Browser/Platform:**
- **Browser:** [BROWSER_NAME] [VERSION]
- **Operating System:** [OS] [VERSION]
- **Device:** [DEVICE_TYPE] (if mobile)
- **Screen Resolution:** [RESOLUTION]

**Application Version:**
- **Frontend Version:** [VERSION]
- **Backend Version:** [VERSION]
- **Database Version:** [VERSION]

**User Account:**
- **User Role:** [ADMIN/MANAGER/MEMBER/VIEWER]
- **Organization:** [ORGANIZATION_NAME]
- **Permissions:** [PERMISSION_DETAILS]

## Bug Summary

**Title:** [CONCISE_BUG_DESCRIPTION]

**Description:**
[DETAILED_DESCRIPTION_OF_THE_ISSUE]

**Expected Behavior:**
[WHAT_SHOULD_HAPPEN]

**Actual Behavior:**
[WHAT_ACTUALLY_HAPPENS]

**Impact on Users:**
[HOW_THIS_AFFECTS_END_USERS]

## Reproduction Information

**Reproducibility:**
- [ ] Always (100% of the time)
- [ ] Often (70-99% of the time)
- [ ] Sometimes (30-69% of the time)
- [ ] Rarely (1-29% of the time)
- [ ] Unable to reproduce

**Prerequisites:**
[CONDITIONS_NEEDED_BEFORE_REPRODUCING]

**Steps to Reproduce:**
1. [STEP_1]
2. [STEP_2]
3. [STEP_3]
4. [CONTINUE_AS_NEEDED]

**Test Data Required:**
[SPECIFIC_DATA_NEEDED_TO_REPRODUCE]

## Evidence

**Screenshots:**
- [ ] Before state: [ATTACH_SCREENSHOT]
- [ ] Error state: [ATTACH_SCREENSHOT]
- [ ] Expected state: [ATTACH_SCREENSHOT]

**Videos:**
- [ ] Screen recording: [ATTACH_VIDEO]

**Error Messages:**
```
[PASTE_ERROR_MESSAGES_HERE]
```

**Console Errors:**
```javascript
[PASTE_CONSOLE_ERRORS_HERE]
```

**Network Errors:**
```
[PASTE_NETWORK_ERRORS_HERE]
```

**Server Logs:**
```
[PASTE_RELEVANT_SERVER_LOGS]
```

## Technical Details

**API Endpoints Affected:**
- [ENDPOINT_1]
- [ENDPOINT_2]

**Database Tables Affected:**
- [TABLE_1]
- [TABLE_2]

**Components Affected:**
- [COMPONENT_1]
- [COMPONENT_2]

**Related Test Cases:**
- [TEST_CASE_ID_1]: [TEST_CASE_NAME]
- [TEST_CASE_ID_2]: [TEST_CASE_NAME]

## Business Impact

**User Impact:**
- [ ] All users affected
- [ ] Specific user roles affected: [SPECIFY_ROLES]
- [ ] Specific organizations affected: [SPECIFY_ORGS]
- [ ] Limited to specific browsers/devices

**Feature Impact:**
- [ ] Feature completely broken
- [ ] Feature partially working
- [ ] Workaround available
- [ ] Cosmetic issue only

**Revenue Impact:**
- [ ] Potential revenue loss
- [ ] Customer satisfaction impact
- [ ] No business impact

## Workaround

**Is there a workaround?**
- [ ] Yes - [DESCRIBE_WORKAROUND]
- [ ] No
- [ ] Unknown

**Workaround Instructions:**
1. [STEP_1]
2. [STEP_2]
3. [CONTINUE_AS_NEEDED]

## Root Cause Analysis (Dev Team)

**Root Cause:**
[TO_BE_FILLED_BY_DEVELOPER]

**Code Areas Affected:**
[TO_BE_FILLED_BY_DEVELOPER]

**Why Was This Not Caught?**
[TO_BE_FILLED_BY_DEVELOPER]

## Fix Information (Dev Team)

**Fix Approach:**
[TO_BE_FILLED_BY_DEVELOPER]

**Code Changes Required:**
- [ ] Frontend changes
- [ ] Backend changes
- [ ] Database changes
- [ ] Infrastructure changes
- [ ] Configuration changes

**Testing Required:**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Regression testing
- [ ] Performance testing
- [ ] Security testing

**Risk Assessment:**
- [ ] Low risk - Isolated change
- [ ] Medium risk - Multiple components affected
- [ ] High risk - Core functionality change

## Verification Criteria

**Definition of Done:**
- [ ] Bug no longer reproduces
- [ ] All related functionality works correctly
- [ ] No new regressions introduced
- [ ] Performance not degraded
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Documentation updated (if needed)

**Test Cases to Execute:**
- [TEST_CASE_1]
- [TEST_CASE_2]
- [REGRESSION_TEST_SUITE]

**Environments to Test:**
- [ ] Development
- [ ] Test
- [ ] Staging
- [ ] Production (if applicable)

## Status Tracking

**Current Status:**
- [ ] New
- [ ] Assigned
- [ ] In Progress
- [ ] Code Review
- [ ] Testing
- [ ] Ready for Deploy
- [ ] Deployed
- [ ] Verified
- [ ] Closed

**Status History:**
| Date | Status | Updated By | Notes |
|------|--------|------------|-------|
| [DATE] | New | [NAME] | Initial report |
| [DATE] | [STATUS] | [NAME] | [NOTES] |

## Related Issues

**Duplicate Issues:**
- [ISSUE_ID]: [BRIEF_DESCRIPTION]

**Related Bugs:**
- [BUG_ID]: [BRIEF_DESCRIPTION]

**Blocked By:**
- [ISSUE_ID]: [BRIEF_DESCRIPTION]

**Blocking:**
- [ISSUE_ID]: [BRIEF_DESCRIPTION]

## Communication

**Stakeholders to Notify:**
- [ ] Product Manager
- [ ] Engineering Manager
- [ ] Customer Support
- [ ] Sales Team
- [ ] Specific customers: [LIST_CUSTOMERS]

**Customer Impact Communication:**
[COMMUNICATION_PLAN_IF_CUSTOMER_FACING]

## Additional Notes

**Special Considerations:**
[ANY_ADDITIONAL_CONTEXT_OR_CONSIDERATIONS]

**References:**
- [LINK_TO_REQUIREMENTS]
- [LINK_TO_DESIGN_DOCS]
- [LINK_TO_RELATED_DOCUMENTATION]

---

## Internal Use (QA Team)

**Testing Notes:**
[INTERNAL_TESTING_OBSERVATIONS]

**Automation Impact:**
- [ ] New test case needed
- [ ] Existing test case needs update
- [ ] No automation changes required

**Regression Impact:**
[AREAS_TO_FOCUS_ON_FOR_REGRESSION_TESTING]

---

## Review and Approval

**QA Review:**
- **Reviewer:** [QA_REVIEWER_NAME]
- **Date:** [DATE]
- **Comments:** [REVIEW_COMMENTS]
- **Approved:** [ ] Yes [ ] No

**Dev Review:**
- **Reviewer:** [DEV_REVIEWER_NAME]
- **Date:** [DATE]
- **Comments:** [REVIEW_COMMENTS]
- **Approved:** [ ] Yes [ ] No

**Product Review:**
- **Reviewer:** [PRODUCT_REVIEWER_NAME]
- **Date:** [DATE]
- **Comments:** [REVIEW_COMMENTS]
- **Approved:** [ ] Yes [ ] No

---

## Bug Report Metrics

**Time Metrics:**
- **Time to Assign:** [TIME]
- **Time to Start:** [TIME]
- **Time to Fix:** [TIME]
- **Time to Verify:** [TIME]
- **Total Resolution Time:** [TIME]

**Quality Metrics:**
- **False Positive:** [ ] Yes [ ] No
- **Returned from Dev:** [ ] Yes [ ] No (Reason: [REASON])
- **Escaped to Production:** [ ] Yes [ ] No

---

*Bug Report Template Version: 1.0*
*Last Updated: December 2024*
*Template Owner: QA Team*