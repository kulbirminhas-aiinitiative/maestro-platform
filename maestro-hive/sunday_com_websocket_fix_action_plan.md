# Sunday.com WebSocket Authentication Fix - Action Plan

## Executive Summary

The Sunday.com frontend is experiencing WebSocket authentication failures. After thorough analysis, the root cause is clear: **the WebSocket is attempting to connect without a valid JWT authentication token**.

## Current Status

### ✅ What's Working
1. **Backend API** - Running on port 8006, healthy and responding
2. **Authentication System** - Login/register endpoints working
3. **WebSocket Service** - Properly configured with JWT authentication middleware
4. **Frontend Auth Flow** - Well-structured AuthContext and auth store

### ❌ What's Failing
1. **WebSocket Connection** - Failing with "Authentication failed" error
2. **Token Availability** - WebSocket attempting connection before token is available/valid

## Root Cause

The error occurs in the authentication middleware at:
**Location**: `sunday_com/backend/src/services/websocket.service.ts:42-88`

The backend WebSocket service expects a valid JWT token:
```typescript
const token = socket.handshake.auth.token || socket.handshake.headers.authorization?.replace('Bearer ', '');
if (!token) {
  return next(new Error('Authentication token required'));
}
const decoded = jwt.verify(token, config.jwt.secret) as JwtPayload;
```

The most likely causes:
1. **User Not Logged In** - No token exists in localStorage
2. **Token Expired** - Token exists but has expired (24h default lifetime)
3. **Timing Issue** - WebSocket connects before token is properly set

## Solution - Immediate Action

### Option 1: Quick Fix (5 minutes)

**For the other agent to try:**

1. **Check if logged in** - Open browser console on the frontend (port 3006):
   ```javascript
   // Check for token
   localStorage.getItem('sunday_auth_token')
   ```

2. **If no token exists, log in:**
   - Navigate to the login page
   - Create a test account or log in with existing credentials
   - Password must be at least 8 characters

3. **After login, verify token:**
   ```javascript
   // Should return a JWT token
   localStorage.getItem('sunday_auth_token')
   ```

4. **WebSocket should auto-connect** - The AuthContext should automatically connect the WebSocket after successful login

### Option 2: Use Debug Tool (10 minutes)

A debugging tool has been created at:
**Path**: `sunday_com/websocket_debug.html`

**To use it:**

1. Open the file in a browser:
   ```bash
   # From the project directory
   open sunday_com/websocket_debug.html
   # Or navigate to it in your browser
   ```

2. Follow the step-by-step process:
   - **Step 1**: Check backend health
   - **Step 2**: Login with credentials (email + password 8+ chars)
   - **Step 3**: Analyze token validity
   - **Step 4**: Connect WebSocket

3. The tool will show exactly where the issue is and provide detailed logs

## Detailed Fix Steps

### Step 1: Verify Backend is Running

```bash
cd /home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/sunday_com/backend
npm run dev
# Should start on port 8006
```

**Test**:
```bash
curl http://3.10.213.208:8006/api/v1/health
# Should return 200 OK
```

### Step 2: Create Test User (if needed)

```bash
curl -X POST http://3.10.213.208:8006/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpass123",
    "firstName": "Test",
    "lastName": "User"
  }'
```

### Step 3: Login and Get Token

```bash
curl -X POST http://3.10.213.208:8006/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpass123"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "user": { ... },
    "tokens": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "..."
    }
  }
}
```

### Step 4: Test WebSocket with Token

Use the debugging tool (websocket_debug.html) or test manually in browser console:

```javascript
// In browser console on frontend
const io = require('socket.io-client');
const token = localStorage.getItem('sunday_auth_token');

const socket = io('ws://3.10.213.208:8006', {
  auth: { token },
  transports: ['websocket', 'polling']
});

socket.on('connect', () => console.log('✅ Connected!'));
socket.on('connect_error', (err) => console.error('❌ Error:', err));
```

## Common Issues and Solutions

### Issue 1: "No token - aborting connection"

**Cause**: User not logged in

**Solution**:
```javascript
// 1. Check frontend at http://localhost:3006 or port 3006
// 2. Navigate to /auth/login
// 3. Login with valid credentials
// 4. Verify token is stored:
localStorage.getItem('sunday_auth_token')
```

### Issue 2: "Authentication failed" with token present

**Cause**: Token expired or invalid

**Solution**:
```javascript
// Check token expiration
function checkToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = new Date(payload.exp * 1000);
    const now = new Date();
    
    console.log('Token expires:', exp);
    console.log('Current time:', now);
    console.log('Is expired?', exp < now);
    
    if (exp < now) {
      console.log('❌ Token is expired - please login again');
    } else {
      console.log('✅ Token is valid');
    }
  } catch (e) {
    console.error('❌ Invalid token format');
  }
}

checkToken(localStorage.getItem('sunday_auth_token'));
```

**If expired**:
- Log out and log in again
- Or trigger token refresh:
  ```javascript
  // The auth store has a refresh method
  // Should be called automatically by AuthContext
  ```

### Issue 3: WebSocket connects too early

**Cause**: Timing issue in auth flow

**Current Protection** (already implemented):
- AuthContext waits for token verification before allowing WebSocket
- See: `sunday_com/frontend/src/contexts/AuthContext.tsx:136-149`

**Verification**:
```javascript
// Check auth state in browser console
const authStore = require('@/store/auth');
console.log('Is authenticated?', authStore.useAuthStore.getState().isAuthenticated);
console.log('User:', authStore.useAuthStore.getState().user);
```

### Issue 4: CORS or network issues

**Check backend logs**:
```bash
cd sunday_com/backend
# Look for WebSocket connection attempts in logs
```

**Verify CORS** in backend configuration:
```typescript
// Should allow frontend origin
// Check server.ts or main.ts for Socket.IO CORS config
```

## Monitoring and Verification

### Frontend Checks

**In browser console**:
```javascript
// 1. Check authentication status
localStorage.getItem('sunday_auth_token')
localStorage.getItem('sunday_refresh_token')

// 2. Check WebSocket service
webSocketService.isConnected()

// 3. Watch for connection events
window.addEventListener('websocket_connected', () => {
  console.log('✅ WebSocket connected');
});
```

### Backend Checks

**Add temporary logging** in `sunday_com/backend/src/services/websocket.service.ts`:
```typescript
// Line 42-50
this.io.use(async (socket: AuthenticatedSocket, next) => {
  try {
    const token = socket.handshake.auth.token ||
      socket.handshake.headers.authorization?.replace('Bearer ', '');

    console.log('[WS Auth] Connection attempt');
    console.log('[WS Auth] Has token?', !!token);
    console.log('[WS Auth] Token preview:', token?.substring(0, 30));

    if (!token) {
      console.log('[WS Auth] ❌ No token provided');
      return next(new Error('Authentication token required'));
    }
    
    // ... rest of auth
  }
});
```

## Expected Behavior After Fix

1. **User logs in** → Token stored in localStorage
2. **AuthContext detects login** → Sets `allowWebSocket` to true  
3. **WebSocket connects** → With valid token in auth header
4. **Backend verifies token** → Authenticates socket connection
5. **Connection established** → Real-time features active

**Logs you should see**:
```
[AuthContext] Initializing authentication...
[AuthContext] Token found, attempting to refresh...
[AuthContext] Auth initialization successful
[AuthContext] Connecting WebSocket with verified token
[WebSocket] connect() called
[WebSocket] Token found: eyJhbGci...
WebSocket connected successfully
```

## Testing Checklist

- [ ] Backend is running and healthy (port 8006)
- [ ] Can register new user via API
- [ ] Can login and receive JWT token
- [ ] Token is stored in localStorage
- [ ] Token is valid (not expired)
- [ ] Frontend shows user as authenticated
- [ ] WebSocket connection succeeds
- [ ] No authentication errors in console

## Prevention - Long Term

### 1. Add Token Expiration Monitoring

```typescript
// In websocket.service.ts
private checkTokenValidity(): boolean {
  const token = apiClient.getToken();
  if (!token) return false;
  
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const isExpired = payload.exp * 1000 < Date.now();
    
    if (isExpired) {
      Logger.warn('Token expired - triggering refresh');
      this.emit('token_expired');
      return false;
    }
    
    return true;
  } catch {
    return false;
  }
}

connect() {
  if (!this.checkTokenValidity()) {
    Logger.error('Cannot connect - invalid token');
    return;
  }
  // ... rest of connect
}
```

### 2. Implement Automatic Token Refresh

Already partially implemented in `auth.ts`. Enhance with:
- Proactive refresh before expiration (e.g., 5 minutes before)
- Retry logic with exponential backoff
- Clear user notifications on failure

### 3. Add Connection State UI

Show WebSocket connection status to users:
```typescript
// Component to display connection state
const ConnectionStatus = () => {
  const isConnected = webSocketService.isConnected();
  
  if (!isConnected) {
    return (
      <div className="connection-warning">
        ⚠️ Real-time updates unavailable
      </div>
    );
  }
  
  return null;
};
```

### 4. Comprehensive Error Handling

```typescript
// Enhanced error handling in WebSocket service
socket.on('connect_error', async (error) => {
  if (error.message === 'Authentication failed') {
    // Try token refresh
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      // Retry connection
      this.connect();
    } else {
      // Show login modal
      emitEvent('auth_required');
    }
  }
});
```

## Files to Review

Key files involved in the authentication flow:

1. **Frontend**:
   - `frontend/src/contexts/AuthContext.tsx` - Auth state management
   - `frontend/src/store/auth.ts` - Auth store with login/logout
   - `frontend/src/services/websocket.service.ts` - WebSocket connection
   - `frontend/src/lib/api.ts` - API client with token management

2. **Backend**:
   - `backend/src/services/websocket.service.ts` - WebSocket auth middleware
   - `backend/src/config/index.ts` - JWT secret configuration
   - `backend/.env` - Environment variables

3. **Debug Tools**:
   - `sunday_com/websocket_debug.html` - Standalone debugging tool
   - `sunday_com_websocket_authentication_analysis.md` - Detailed analysis

## Quick Reference Commands

```bash
# Check backend status
curl http://3.10.213.208:8006/api/v1/health

# Login
curl -X POST http://3.10.213.208:8006/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# In browser console - check token
localStorage.getItem('sunday_auth_token')

# In browser console - check WebSocket
webSocketService.isConnected()
```

## Next Steps

1. **Immediate** (the other agent):
   - Check if logged in on frontend
   - If not, perform login
   - Verify token is stored
   - WebSocket should connect automatically

2. **Short-term** (if issue persists):
   - Use websocket_debug.html tool
   - Check backend logs for auth errors
   - Verify JWT secret matches between frontend/backend

3. **Long-term**:
   - Implement proactive token refresh
   - Add connection state UI
   - Enhance error handling and user feedback

## Contact Points

If issues persist after following this guide:

1. Check backend logs for detailed error messages
2. Use the websocket_debug.html tool for step-by-step diagnosis
3. Review the detailed analysis in sunday_com_websocket_authentication_analysis.md
4. Ensure no firewall/network issues blocking WebSocket connections

---

**Created**: 2025-01-06
**Status**: Ready for implementation
**Priority**: High - Blocking real-time features
