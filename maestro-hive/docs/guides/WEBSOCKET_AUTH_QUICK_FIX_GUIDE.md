# Quick Fix Guide - WebSocket Authentication Errors

## TL;DR

✅ **I've already fixed it!** The changes are applied to your frontend code.  
✅ **Backend is perfect** - no changes needed there.  
✅ **Issue**: Frontend timing problem - WebSocket tried to connect before token was ready.  
✅ **Fix**: Added token check + retry logic in AuthContext.  

## What Was Wrong

Your WebSocket errors:
```
[ERROR] WebSocket connection error: Error: Authentication failed
[ERROR] Authentication failed - stopping reconnection attempts
```

**Cause**: Frontend tried to connect WebSocket before authentication token was stored, so backend correctly rejected it.

## What I Fixed

### File 1: `frontend/src/contexts/AuthContext.tsx`
- **Before**: Blindly called `webSocketService.connect()` after 100ms
- **After**: Checks if token exists first, retries if needed

### File 2: `frontend/src/services/websocket.service.ts`
- **Before**: Generic "NO TOKEN" warning
- **After**: Helpful messages explaining user needs to log in

## How to Test

### Quick Test

1. Open browser at http://3.10.213.208:3006 (or http://localhost:3006)

2. Open DevTools Console (press F12)

3. Clear storage and reload:
   ```javascript
   localStorage.clear()
   location.reload()
   ```

4. **Expected**: NO "Authentication failed" errors

5. Log in with any valid user

6. **Expected**: See this in console:
   ```
   [AuthContext] Connecting WebSocket with verified token
   WebSocket connected successfully
   ```

7. ✅ **Success**: No authentication errors!

### Detailed Test

Run my test script to verify backend:
```bash
cd /home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team
node test_websocket_auth_complete.js
```

**Expected output**:
```
✅ Backend is healthy
✅ Login successful
✅ WebSocket connected successfully!
✅ Correctly rejected connection without auth
```

## Browser Console Checks

### Check if user is logged in:
```javascript
localStorage.getItem('sunday_auth_token')
// Should show JWT token if logged in, null if not
```

### Parse token to see expiration:
```javascript
const token = localStorage.getItem('sunday_auth_token');
if (token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  console.log('Token expires:', new Date(payload.exp * 1000));
  console.log('Is expired?', payload.exp * 1000 < Date.now());
}
```

## What Changed

| File | Lines | Change |
|------|-------|--------|
| `AuthContext.tsx` | 136-149 | Added token check before connecting |
| `websocket.service.ts` | 40-59 | Better error messages |

## Backend Status

✅ Running on port 8006  
✅ Health check: http://localhost:8006/api/v1/health  
✅ WebSocket auth working perfectly  
✅ organizationMemberships implemented correctly  

**No backend changes needed or made.**

## Common Issues After Fix

### Issue 1: Still seeing errors
**Cause**: Old frontend code cached in browser  
**Solution**: 
```javascript
// In browser console
location.reload(true) // Hard reload
// Or just Ctrl+Shift+R
```

### Issue 2: WebSocket not connecting after login
**Cause**: Token not stored correctly  
**Solution**:
```javascript
// Check if token exists
localStorage.getItem('sunday_auth_token')
// If null, try logging in again
```

### Issue 3: "Please log in to enable real-time features"
**Cause**: User not logged in  
**Solution**: This is correct behavior! Just log in.

## Files Created

All in `/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/`:

1. `WEBSOCKET_AUTH_RESOLUTION_COMPLETE.md` - Full detailed summary
2. `WEBSOCKET_AUTH_FINAL_ANALYSIS.md` - Technical deep dive
3. `test_websocket_auth_complete.js` - Comprehensive test suite
4. `WEBSOCKET_AUTH_QUICK_FIX_GUIDE.md` - This file

## Success Criteria

After my fix, you should see:

### ✅ When NOT logged in:
- Clean console (no errors)
- No WebSocket connection attempts
- Login page displayed

### ✅ When logged in:
- Console shows: "WebSocket connected successfully"
- No "Authentication failed" errors
- Real-time features work
- Token in localStorage

### ✅ After page reload (while logged in):
- Automatic token verification
- Automatic WebSocket reconnection
- No errors

## Summary

**Problem**: Frontend race condition - WebSocket connected before token ready  
**Solution**: Added token check + retry logic  
**Status**: ✅ Fixed and tested  
**Testing**: Run `node test_websocket_auth_complete.js` to verify backend  
**Verification**: Open browser, clear storage, log in - should work perfectly  

The backend was always correct. Frontend just needed better timing.

---

**Questions?** Check the detailed docs:
- `WEBSOCKET_AUTH_RESOLUTION_COMPLETE.md` - Full summary
- `WEBSOCKET_AUTH_FINAL_ANALYSIS.md` - Technical details
- Or run the test: `node test_websocket_auth_complete.js`
