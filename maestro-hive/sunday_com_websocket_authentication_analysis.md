# Sunday.com WebSocket Authentication Issue - Analysis and Resolution

## Issue Summary

The frontend (running on port 3006) is experiencing WebSocket authentication failures with the following errors:

```
[ERROR] WebSocket connection error: Error: Authentication failed
[ERROR] Authentication failed - stopping reconnection attempts
```

## Current State Analysis

### Backend Status ✅
- **Running**: Yes, on port 8006
- **Health Check**: ✅ Returns 200 OK
- **API Endpoints**: ✅ Working properly
- **WebSocket Service**: ✅ Configured with JWT authentication middleware

### Frontend Status ⚠️
- **Running**: Yes, on port 3006
- **API URL**: `http://3.10.213.208:8006` (correct)
- **WebSocket URL**: `ws://3.10.213.208:8006` (correct)
- **Authentication**: ❌ WebSocket failing to authenticate

## Root Cause Analysis

### Issue 1: Missing or Invalid JWT Token

**Location**: `sunday_com/frontend/src/services/websocket.service.ts:49-53`

The WebSocket service attempts to get a token but may not have a valid one:

```typescript
const token = apiClient.getToken()
if (!token) {
  console.warn('[WebSocket] NO TOKEN - aborting connection')
  return
}
```

**Problem**: The token may be:
1. Not set after login (user not properly authenticated)
2. Expired
3. Invalid format
4. Not being passed correctly to Socket.IO

### Issue 2: Authentication Flow Timing

**Location**: `sunday_com/frontend/src/services/websocket.service.ts:36-38`

```typescript
constructor() {
  // Don't auto-connect - let AuthContext connect when user is authenticated
}
```

**Problem**: The WebSocket connection may be attempting before:
- User completes login
- JWT token is stored in localStorage
- API client is initialized with the token

### Issue 3: Backend JWT Verification

**Location**: `sunday_com/backend/src/services/websocket.service.ts:42-88`

The backend expects:
```typescript
const token = socket.handshake.auth.token ||
  socket.handshake.headers.authorization?.replace('Bearer ', '');
```

And verifies with:
```typescript
const decoded = jwt.verify(token, config.jwt.secret) as JwtPayload;
```

**JWT Secret**: `dev-secret-key-for-testing-only` (from backend/.env)

## Resolution Path

### Step 1: Verify User Authentication State

Check if users are properly logging in and JWT tokens are being stored:

```bash
# Check localStorage in browser console:
localStorage.getItem('sunday_auth_token')
```

**Expected**: A JWT token string (format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

**If null**: User needs to log in first before WebSocket can connect

### Step 2: Ensure WebSocket Connects After Authentication

The WebSocket service should only connect after successful login. Check:

1. **Auth Context** should call `webSocketService.connect()` after login
2. **Token should be available** before connection attempt
3. **Connection should be deferred** until user is authenticated

**Current Code Analysis**:
- ✅ Constructor doesn't auto-connect
- ❌ Need to verify auth context triggers connection
- ❌ Need to verify token is set before connect()

### Step 3: Debug WebSocket Authentication Flow

Add debugging to track the authentication flow:

**Frontend (websocket.service.ts)**:
```typescript
connect() {
  console.log('[WebSocket] connect() called')
  
  const token = apiClient.getToken()
  console.log('[WebSocket] Token:', token ? `${token.substring(0, 20)}...` : 'NONE')
  
  if (!token) {
    console.error('[WebSocket] Cannot connect - no auth token')
    return
  }
  
  // ... rest of connect logic
}
```

**Backend (websocket.service.ts)**:
```typescript
this.io.use(async (socket: AuthenticatedSocket, next) => {
  try {
    const token = socket.handshake.auth.token ||
      socket.handshake.headers.authorization?.replace('Bearer ', '');

    console.log('[WebSocket Auth] Token received:', token ? 'YES' : 'NO')
    console.log('[WebSocket Auth] Token preview:', token?.substring(0, 30))

    if (!token) {
      console.error('[WebSocket Auth] No token provided')
      return next(new Error('Authentication token required'));
    }

    const decoded = jwt.verify(token, config.jwt.secret) as JwtPayload;
    console.log('[WebSocket Auth] Token verified for user:', decoded.sub)
    
    // ... rest of auth logic
  } catch (error) {
    console.error('[WebSocket Auth] Verification failed:', error.message)
    next(new Error('Authentication failed'));
  }
});
```

### Step 4: Verify Token Storage After Login

Ensure the login flow properly stores the token:

**Check**: `sunday_com/frontend/src/store/auth.ts` or auth context

Should include:
```typescript
// After successful login API call:
const response = await api.auth.login({ email, password })

// Store token
apiClient.setToken(response.token)
localStorage.setItem('sunday_auth_token', response.token)

// THEN connect WebSocket
webSocketService.connect()
```

### Step 5: Check Token Expiration

If token exists but auth still fails:

```typescript
// Decode JWT (without verification) to check expiration
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}
```

If expired, trigger token refresh before WebSocket connection.

### Step 6: Verify CORS and WebSocket Configuration

**Backend** should allow WebSocket connections from frontend origin:

```typescript
// sunday_com/backend/src/server.ts or main.ts
const io = new SocketIOServer(server, {
  cors: {
    origin: ['http://localhost:3006', 'http://3.10.213.208:3006'],
    credentials: true
  }
})
```

## Quick Fix Checklist

### Immediate Actions:

1. ✅ **Backend is running** - confirmed on port 8006
2. ⏸️ **User needs to log in** - ensure you're logged in on frontend
3. ⏸️ **Check token in localStorage** - verify token exists
4. ⏸️ **Check token format** - should be valid JWT
5. ⏸️ **Verify WebSocket connection timing** - should connect after login

### Testing Steps:

1. **Open browser console** on `http://localhost:3006` (or frontend URL)

2. **Check if logged in**:
   ```javascript
   localStorage.getItem('sunday_auth_token')
   ```

3. **If no token, log in first**:
   - Navigate to login page
   - Enter credentials
   - Verify token is stored after successful login

4. **Check WebSocket connection**:
   ```javascript
   // In console:
   webSocketService.isConnected()
   ```

5. **Manual token test**:
   ```javascript
   // Get token from localStorage
   const token = localStorage.getItem('sunday_auth_token')
   
   // Manually connect to test
   const io = require('socket.io-client')
   const socket = io('ws://3.10.213.208:8006', {
     auth: { token },
     transports: ['websocket', 'polling']
   })
   
   socket.on('connect', () => console.log('Connected!'))
   socket.on('connect_error', (err) => console.error('Error:', err))
   ```

## Common Issues and Solutions

### Issue: "NO TOKEN - aborting connection"

**Solution**: User is not logged in
- Navigate to login page
- Complete authentication
- WebSocket will connect automatically after login

### Issue: "Authentication failed" even with token

**Solutions**:
1. **Token expired**: 
   - Log out and log back in
   - Implement token refresh mechanism

2. **Wrong JWT secret**: 
   - Verify backend and frontend use same secret
   - Check `backend/.env` JWT_SECRET

3. **Token format issue**:
   - Ensure token includes `Bearer` prefix if expected
   - Check token is not corrupted in localStorage

4. **User doesn't exist**:
   - Backend verifies user exists in database
   - Ensure test user is created

### Issue: Connection attempt before authentication

**Solution**: Modify auth flow to ensure proper ordering:

```typescript
// In auth context or login handler:
async function login(email: string, password: string) {
  try {
    // 1. Login via API
    const response = await api.auth.login({ email, password })
    
    // 2. Store token
    apiClient.setToken(response.token)
    localStorage.setItem('sunday_auth_token', response.token)
    localStorage.setItem('auth_user', JSON.stringify(response.user))
    
    // 3. ONLY NOW connect WebSocket
    webSocketService.connect()
    
    // 4. Update UI state
    setUser(response.user)
    setIsAuthenticated(true)
  } catch (error) {
    console.error('Login failed:', error)
  }
}
```

## Recommended Implementation Changes

### 1. Add Token Validation Before WebSocket Connection

```typescript
// websocket.service.ts
connect() {
  const token = apiClient.getToken()
  
  if (!token) {
    Logger.warn('Cannot connect WebSocket - no authentication token')
    return
  }
  
  // Validate token is not expired
  if (this.isTokenExpired(token)) {
    Logger.warn('Cannot connect WebSocket - token expired')
    // Trigger token refresh
    this.emit('token_expired')
    return
  }
  
  // Prevent duplicate connections
  if (this.socket && this.connected) {
    Logger.info('WebSocket already connected')
    return
  }
  
  // Proceed with connection...
}

private isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}
```

### 2. Add Automatic Reconnection with Token Refresh

```typescript
// In websocket.service.ts
this.socket.on('connect_error', (error: any) => {
  if (error?.message === 'Authentication failed') {
    Logger.error('WebSocket auth failed - attempting token refresh')
    
    // Try to refresh token
    this.attemptTokenRefresh().then(() => {
      // Retry connection with new token
      this.connect()
    }).catch(() => {
      // Token refresh failed - user needs to log in
      Logger.error('Token refresh failed - user must re-authenticate')
      this.emit('auth_required')
      this.disconnect()
    })
  }
})

private async attemptTokenRefresh(): Promise<void> {
  try {
    const refreshToken = localStorage.getItem('sunday_refresh_token')
    if (!refreshToken) throw new Error('No refresh token')
    
    const response = await api.auth.refresh({ refreshToken })
    apiClient.setToken(response.token)
    return Promise.resolve()
  } catch (error) {
    return Promise.reject(error)
  }
}
```

### 3. Add Connection State Management

```typescript
// Create a connection manager
class WebSocketConnectionManager {
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'failed' = 'disconnected'
  private authToken: string | null = null
  
  async connect() {
    if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
      return
    }
    
    // Ensure we have valid auth
    if (!await this.ensureAuthenticated()) {
      this.connectionState = 'failed'
      throw new Error('Not authenticated')
    }
    
    this.connectionState = 'connecting'
    
    try {
      await this.establishConnection()
      this.connectionState = 'connected'
    } catch (error) {
      this.connectionState = 'failed'
      throw error
    }
  }
  
  private async ensureAuthenticated(): Promise<boolean> {
    const token = apiClient.getToken()
    if (!token) return false
    
    if (this.isTokenExpired(token)) {
      try {
        await this.attemptTokenRefresh()
        return true
      } catch {
        return false
      }
    }
    
    return true
  }
}
```

## Production Recommendations

1. **Implement Token Refresh**: Automatic token refresh before expiration
2. **Add Retry Logic**: Exponential backoff with maximum attempts
3. **Monitor Connection Health**: Ping/pong heartbeats
4. **Graceful Degradation**: App should work without WebSocket (polling fallback)
5. **User Notifications**: Clear feedback when real-time features unavailable
6. **Logging**: Comprehensive logging for debugging auth issues
7. **Error Handling**: Specific error messages for different failure modes

## Next Steps

1. **Immediate**: Check if user is logged in and has valid token
2. **Short-term**: Add better error handling and user feedback
3. **Medium-term**: Implement token refresh mechanism
4. **Long-term**: Add comprehensive connection state management

## Testing Commands

```bash
# Check backend health
curl http://3.10.213.208:8006/api/v1/health

# Test login (with valid 8+ char password)
curl -X POST http://3.10.213.208:8006/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Check WebSocket endpoint (from browser console)
const socket = io('ws://3.10.213.208:8006', {
  auth: { token: localStorage.getItem('sunday_auth_token') }
})
```

## Summary

The WebSocket authentication issue is most likely caused by:
1. **Missing authentication** - User not logged in
2. **Token not stored** - Login flow not saving JWT token
3. **Connection timing** - WebSocket connecting before authentication completes

**Quick Resolution**: Ensure user is logged in with valid token before WebSocket attempts to connect.
