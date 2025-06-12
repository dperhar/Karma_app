# Authentication Flow Test Guide

## Problem Fixed
The issue was **infinite QR token expiration and regeneration loop** preventing users from completing authentication. The problems were:

1. **Infinite polling on expired tokens** - When QR tokens expired, polling continued indefinitely instead of regenerating new tokens
2. **No error handling for expiration** - "Session expired" errors weren't handled properly
3. **Multiple simultaneous QR generations** - Component re-renders caused duplicate QR code requests
4. **Authentication state not persisting** - After successful auth, the Telegram SDK environment wasn't updated with real user data

## Root Cause Analysis
1. **QR Token Lifecycle Issue**: Tokens expire after ~2 minutes, but polling continued with expired tokens
2. **Missing Error Handling**: `useTelegramQRLogin` didn't handle `{success: false, message: "Session expired"}` responses
3. **No Auto-Regeneration**: When tokens expired, new QR codes weren't automatically generated
4. **Circular Dependencies**: `generateQRCode` and `startPolling` had circular dependency causing re-render issues
5. **Environment Update Missing**: After successful authentication, Telegram SDK still used mock data

## Solution Implemented

### **1. Fixed QR Token Lifecycle Management**
- **Smart Error Handling**: Added detection for expired token responses (`"Session expired"`, `"authorization token has expired"`)
- **Auto-Regeneration**: When tokens expire, automatically clear state and generate new QR codes
- **Polling Cleanup**: Properly stop polling on expiration and start fresh with new tokens

### **2. Prevented Multiple Simultaneous Operations**
- **Generation Guard**: Added `isGeneratingRef` to prevent multiple simultaneous QR code generations
- **Proper Cleanup**: Clear polling intervals and reset flags on component unmount
- **Circular Dependency Fix**: Restructured callback handling to avoid infinite re-renders

### **3. Enhanced Authentication State Management**
- **Environment Update**: After successful 2FA, update Telegram SDK environment with real authenticated user data
- **Session Persistence**: Set session cookie manually for immediate state consistency
- **Dual Auth Check**: Root component checks both session cookie AND environment authentication state
- **Auto-Reload**: Force page reload to ensure all components re-initialize with new authenticated context

### **4. Added Robust Type Safety**
- **TypeScript Fixes**: Proper type assertions for Telegram SDK launch parameters
- **Error Boundaries**: Better error handling and user feedback for various failure states

## Test Steps

### 1. Initial State Check
1. Visit http://localhost:3000
2. Should see QR login modal (not authenticated)
3. No `karma_session` cookie should exist

### 2. QR Authentication Flow
1. Generate QR code - should work instantly
2. Scan QR code with Telegram mobile app
3. Should prompt for 2FA password
4. Enter correct 2FA password

### 3. Expected Results After 2FA
1. "Login Successful!" message with "Updating environment..." 
2. Environment should update with authenticated user ID (118672216)
3. Session cookie `karma_session` should be set
4. Page should auto-reload after 500ms
5. After reload, should go directly to main app (no auth modal)
6. Chat loading should work properly with authenticated `initData`

### 4. Persistent Authentication
1. Refresh page - should stay authenticated
2. Close/reopen browser tab - should stay authenticated  
3. Session should persist until cookie expires (24 hours)

## Debug Information

### Frontend Logs to Watch For
```
# QR Generation & Polling
Generating QR code with initDataRaw: mock_init_data_for_dev
Starting polling with token: AQJq10lo... and initDataRaw: mock_init_data_for_dev

# Normal Flow (User Scans & Enters 2FA)
Polling response: {success: true, data: {requires_2fa: true, status: "2fa_required"}}
Verifying 2FA with code: [password]
2FA verification response: {success: true, data: {user_id: 118672216, status: "success"}}

# Token Expiration & Auto-Regeneration (if QR not scanned in time)
Polling failed: The provided authorization token has expired...
Token expired, stopping polling and will regenerate QR code
QR code expired, generating new one...

# Successful Authentication
🎉 Authentication successful, updating environment...
✅ Telegram environment updated with authenticated user: 118672216
[Page] Starting data load...
[Page] Fetching fresh user data from server
[Page] Loading chats with user-defined limit: 20
```

### Backend Success Indicators
```
INFO: Successful 2FA verification for Telegram user: 118672216
```

### Browser Storage Check
```javascript
// In browser console:
sessionStorage.getItem("env-authenticated") // should be "1"
sessionStorage.getItem("authenticated-user-id") // should be "118672216"
document.cookie.includes("karma_session=") // should be true
```

## Known Working State
- Backend containers: karma-backend, karma-postgres, karma-redis
- Frontend container: karma-frontend  
- All services respond to health checks
- QR generation and 2FA verification endpoints working
- Session management and user data persistence working

## Next Steps
After authentication succeeds, the main app should:
1. Load user data successfully  
2. Load Telegram chats list
3. Display proper navigation and UI
4. Allow interaction with chat data

No more infinite loading screens! 🎉 