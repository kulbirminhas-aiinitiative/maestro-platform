# DAG Studio Frontend-Backend Integration Test Plan

**Date:** October 19, 2025
**Purpose:** Comprehensive testing of Phase 1 & 2 improvements

---

## Test Environment

### **Service Status:**
- Frontend: http://3.10.213.208:4300
- API Gateway: http://3.10.213.208:8080
- Backend: http://3.10.213.208:5001 (via gateway)

### **URLs to Test:**
- DAG Studio: http://3.10.213.208:4300/orchestration (or /dag-studio)
- Login: http://3.10.213.208:4300/login
- Workflow API: http://3.10.213.208:8080/api/workflow/*
- WebSocket: ws://3.10.213.208:8080/ws/workflow/{workflow_id}?token={JWT}

---

## Pre-Test Checklist

- [ ] All services running (frontend, backend, gateway)
- [ ] Valid authentication token available
- [ ] Browser console open (F12) for debugging
- [ ] Network tab open to monitor requests
- [ ] Clear localStorage before starting

---

## Test Suite 1: Authentication & Authorization

### **Test 1.1: Login and Token Storage**

**Steps:**
1. Navigate to http://3.10.213.208:4300/login
2. Enter credentials and log in
3. Open browser DevTools → Application → Local Storage
4. Verify `maestro_access_token` exists

**Expected:**
- ✅ Login successful
- ✅ Token stored in localStorage
- ✅ Redirected to dashboard

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 1.2: WebSocket JWT Authentication**

**Steps:**
1. Navigate to DAG Studio
2. Create a simple workflow (1-2 phases)
3. Click "Execute"
4. Open browser Network tab → WS (WebSocket)
5. Check WebSocket connection URL

**Expected:**
- ✅ WebSocket URL includes `?token=...`
- ✅ Connection status: "101 Switching Protocols"
- ✅ No authentication errors in console

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 1.3: Invalid Token Rejection**

**Steps:**
1. Open browser DevTools → Application → Local Storage
2. Change `maestro_access_token` to "invalid_token_123"
3. Try to execute a workflow
4. Check console and Network tab

**Expected:**
- ✅ WebSocket connection rejected
- ✅ Close code: 4001
- ✅ Toast notification: "🔒 Session expired or invalid. Please log in again."

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 2: Toast Notifications (Phase 2)

### **Test 2.1: Workflow Execution Started**

**Steps:**
1. Create a workflow with 2 phases
2. Click "Execute"

**Expected:**
- ✅ Toast appears in top-right corner
- ✅ Message: "🚀 Workflow execution started! Total phases: 2"
- ✅ Auto-dismisses after 4 seconds
- ✅ NO browser alert() dialog

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 2.2: Workflow Save**

**Steps:**
1. Create a workflow
2. Click "Save"

**Expected:**
- ✅ Toast: "💾 Workflow saved successfully!"
- ✅ No blocking alert

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 2.3: Export Workflow**

**Steps:**
1. Click "Export"
2. Save JSON file

**Expected:**
- ✅ Toast: "📥 Workflow exported successfully!"
- ✅ File downloads automatically

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 2.4: Import Workflow**

**Steps:**
1. Click "Import"
2. Select a valid workflow JSON file

**Expected:**
- ✅ Toast: "📤 Workflow imported successfully!"
- ✅ Workflow loads in canvas

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 2.5: Validation Errors**

**Steps:**
1. Try to execute an empty workflow (0 phases)

**Expected:**
- ✅ Toast: "Please add at least one phase to the workflow before executing."
- ✅ Error toast (red background)

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 2.6: Workflow Completion**

**Steps:**
1. Execute a simple 1-phase workflow
2. Wait for completion

**Expected:**
- ✅ Toast: "🎉 Workflow completed successfully!"
- ✅ Duration: 5 seconds

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 3: State Re-sync on Browser Refresh (Phase 2)

### **Test 3.1: Refresh During Execution**

**Steps:**
1. Execute a workflow with 3 phases
2. Wait for Phase 1 to complete
3. **Refresh browser (F5 or Ctrl+R)**
4. Check node statuses and console

**Expected:**
- ✅ Phase 1 shows "completed" status (green)
- ✅ Phase 2/3 show correct status
- ✅ WebSocket reconnects automatically
- ✅ Toast: "🔄 Reconnected to running workflow"
- ✅ Continues receiving phase updates

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 3.2: Return After Workflow Completion**

**Steps:**
1. Execute a workflow and wait for completion
2. **Close browser tab**
3. **Open new tab** and navigate to DAG Studio
4. Open the same workflow

**Expected:**
- ✅ All nodes show "completed" status
- ✅ Toast: "✅ Workflow previously completed"
- ✅ localStorage cleared for this workflow
- ✅ No WebSocket connection attempted

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 3.3: Return After Workflow Failure**

**Steps:**
1. Execute a workflow that will fail (if possible)
2. Wait for failure
3. Refresh browser

**Expected:**
- ✅ Nodes show correct failure status
- ✅ Toast: "❌ Workflow failed: {error message}"
- ✅ localStorage cleared

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 4: Real-Time WebSocket Updates

### **Test 4.1: Phase Status Updates**

**Steps:**
1. Execute a workflow with 3 phases
2. Watch the node status changes in real-time
3. Check browser console for WebSocket messages

**Expected:**
- ✅ Phase 1: pending → running → completed
- ✅ Phase 2: pending → running → completed
- ✅ Phase 3: pending → running → completed
- ✅ Console shows WebSocket messages: "phase_started", "phase_completed"

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 4.2: WebSocket Reconnection**

**Steps:**
1. Execute a workflow
2. Open browser DevTools → Network → WS tab
3. Right-click WebSocket connection → "Close connection"
4. Wait 5 seconds

**Expected:**
- ✅ WebSocket automatically reconnects
- ✅ Console: "WebSocket disconnected, reconnecting in 5s..."
- ✅ Console: "WebSocket connected"
- ✅ Continues receiving updates

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 5: Error Handling

### **Test 5.1: Backend Not Responding**

**Steps:**
1. Stop backend: `kill {backend_pid}`
2. Try to execute a workflow

**Expected:**
- ✅ Toast: "Cannot connect to workflow engine. Please ensure the backend is running."
- ✅ Duration: 6 seconds

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 5.2: Session Expiration During Execution**

**Steps:**
1. Execute a workflow
2. While running, delete `maestro_access_token` from localStorage
3. WebSocket should close

**Expected:**
- ✅ WebSocket closes with code 4001
- ✅ Toast: "🔒 Session expired. Please log in again."

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 6: Complete End-to-End Flow

### **Test 6.1: Full Workflow Lifecycle**

**Steps:**
1. Login to application
2. Navigate to DAG Studio
3. Create workflow: Requirements → Architecture → Implementation
4. Assign teams to each phase
5. Save workflow
6. Execute workflow
7. Watch real-time updates
8. Refresh browser during execution
9. Wait for completion
10. Export completed workflow

**Expected:**
- ✅ Each step shows appropriate toast notification
- ✅ No alert() dialogs appear
- ✅ State persists across refresh
- ✅ WebSocket reconnects seamlessly
- ✅ All phase statuses update correctly
- ✅ Completion toast appears
- ✅ Export succeeds

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Test Suite 7: Performance & UX

### **Test 7.1: Toast Notification Stacking**

**Steps:**
1. Rapidly perform multiple actions:
   - Save workflow
   - Execute workflow
   - Export workflow

**Expected:**
- ✅ All toasts appear
- ✅ Toasts stack vertically (no overlap)
- ✅ Each auto-dismisses after duration
- ✅ No performance degradation

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

### **Test 7.2: Multiple Tab Behavior**

**Steps:**
1. Open DAG Studio in 2 browser tabs
2. Execute workflow in Tab 1
3. Switch to Tab 2

**Expected:**
- ✅ Both tabs can view workflow
- ✅ Real-time updates in both tabs (if same workflow)
- ✅ No conflicts or race conditions

**Actual:**
- [ ] Pass / [ ] Fail
- Notes: ___________

---

## Browser Compatibility Tests

Test in the following browsers:

- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

**Expected:**
- ✅ Toasts render correctly in all browsers
- ✅ WebSocket connections work
- ✅ localStorage persists

---

## Automated Test Script

```bash
#!/bin/bash
# Quick smoke test for DAG Studio integration

BASE_URL="http://3.10.213.208:8080"
FRONTEND_URL="http://3.10.213.208:4300"

echo "🧪 DAG Studio Integration Smoke Test"
echo "===================================="

# Test 1: Frontend accessible
echo -n "✓ Frontend accessible... "
if curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL | grep -q "200"; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

# Test 2: Backend health
echo -n "✓ Backend health... "
if curl -s $BASE_URL/health | grep -q "ok"; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

# Test 3: Status endpoint exists
echo -n "✓ Status endpoint... "
if curl -s -o /dev/null -w "%{http_code}" $BASE_URL/api/workflow/status/test | grep -q "404"; then
  echo "✅ PASS (404 expected for non-existent execution)"
else
  echo "⚠️  Check manually"
fi

echo ""
echo "📋 Manual tests required:"
echo "  1. Open $FRONTEND_URL/orchestration"
echo "  2. Test workflow execution with toasts"
echo "  3. Test browser refresh during execution"
echo "  4. Verify WebSocket JWT authentication"
```

---

## Common Issues & Troubleshooting

### **Issue: Toast notifications don't appear**

**Possible Causes:**
- react-hot-toast not imported in App.tsx
- Toaster component not rendered
- Z-index conflict with other UI elements

**Solution:**
- Check browser console for errors
- Verify `<Toaster />` in App.tsx
- Check package.json for react-hot-toast dependency

---

### **Issue: State not restored after refresh**

**Possible Causes:**
- localStorage cleared by browser
- execution_id not saved correctly
- Status endpoint returns 404

**Solution:**
- Check browser console for errors
- Verify localStorage contains `workflow_execution_{workflow_id}`
- Test status endpoint: `curl http://3.10.213.208:8080/api/workflow/status/{execution_id}`

---

### **Issue: WebSocket not reconnecting**

**Possible Causes:**
- JWT token expired or invalid
- Backend not running
- Gateway routing issue

**Solution:**
- Check token in localStorage
- Verify backend is running: `ps aux | grep workflow_api_v2`
- Check WebSocket URL in Network tab includes `?token=`

---

## Test Results Summary

**Tester:** ___________
**Date:** ___________
**Environment:** Production / Staging / Development

| Test Suite | Pass | Fail | Skip | Notes |
|-----------|------|------|------|-------|
| 1. Authentication | __ / __ | __ / __ | __ / __ | ______ |
| 2. Toast Notifications | __ / __ | __ / __ | __ / __ | ______ |
| 3. State Re-sync | __ / __ | __ / __ | __ / __ | ______ |
| 4. WebSocket Updates | __ / __ | __ / __ | __ / __ | ______ |
| 5. Error Handling | __ / __ | __ / __ | __ / __ | ______ |
| 6. E2E Flow | __ / __ | __ / __ | __ / __ | ______ |
| 7. Performance | __ / __ | __ / __ | __ / __ | ______ |

**Overall Status:** 🟢 Ready / 🟡 Minor Issues / 🔴 Critical Issues

---

## Sign-off

**Developer:** ___________  **Date:** ___________
**QA:** ___________  **Date:** ___________
**Product Owner:** ___________  **Date:** ___________
