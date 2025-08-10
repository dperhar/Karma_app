# 📋 Karma App Changelog

All notable changes to this project will be documented in this file.

## [v1.0.0] - 10.08.2025 🥂 First Stable Release

### 🚀 New
- Telegram Feed with source filters (Channels / Groups / Both) and pagination
- Async draft generation pipeline (Celery) with real-time WS updates (Centrifugo)
- One-click “Generate draft” for posts without drafts
- Negative feedback capture and regeneration flow
- Digital Twin (Vibe Profile) analysis tasks (quick and deep modes)
- Posted comments prioritized as style exemplars for future drafts

### 🔧 Improved
- Correct group/channel filtering and type normalization
- Robust message upsert, resolving/creating `original_message_id` automatically
- Default generation temperature set to 0.95
- Frontend real-time draft upsert; no page refresh required
- Deduped feed rendering to prevent duplicate keys and collisions

### 🛡️ Architecture
- API remains thin; heavy work runs in Celery tasks (Telegram, LLM, backfill)
- Repositories isolate DB access; services orchestrate logic
- Strict separation per Hyper-Lean Task-Oriented Architecture

### 🧪 Developer
- New backfill endpoint to deepen feed history
- Clearer logs and safer defaults for dev sessions

— We’re shipping. v1.0 is live. 🥂

## [v0.3.0] - 16.12.2025 🎉 **MAJOR AUTHENTICATION OVERHAUL**

### 🚀 **NEW FEATURES**
- ✅ **QR Authentication System**: Complete Telethon-based QR login flow
- ✅ **Chat List Loading**: Home screen now displays user's Telegram chats and channels
- ✅ **Encrypted Session Storage**: Secure session management with proper encryption
- ✅ **Real-time Authentication**: Seamless QR polling with status updates
- ✅ **2FA Support**: Complete two-factor authentication integration

### 🔧 **MAJOR FIXES**
- 🎯 **Session Management Crisis SOLVED**: Fixed fake session string causing "No valid Telegram session" errors
- 🛡️ **Authentication Architecture**: Overhauled from broken SDK to proven Telethon approach
- ⚡ **Performance**: Optimized chat loading with proper pagination support
- 🔒 **Security**: Implemented proper encrypted session storage in `telegram_connections` table
- 🐛 **Dependency Injection**: Fixed service resolution issues preventing proper singleton behavior

### 🏗️ **ARCHITECTURE IMPROVEMENTS**
- **Backend**: Clean separation between web sessions (user auth) and Telegram sessions (API access)
- **Frontend**: Robust authentication state management with persistent storage
- **Database**: New `telegram_connections` table for encrypted session management
- **API**: Proper `/api/v1` structure with authenticated endpoints

### 🛠️ **TECHNICAL CHANGES**
- **Removed**: Problematic `@telegram-apps/sdk-react` causing initialization errors
- **Added**: Complete Telethon authentication system from proven v0.27 architecture
- **Updated**: Docker environment variables for proper API routing
- **Fixed**: Session singleton registration preventing memory leaks
- **Corrected**: QR login logic using `ImportLoginTokenRequest` instead of `ExportLoginTokenRequest`

### 🎯 **WHAT WORKS NOW**
- ✅ QR code generation and scanning
- ✅ Real-time login status checking
- ✅ 2FA password verification
- ✅ Home page chat list display
- ✅ Settings page user management
- ✅ Persistent authentication across browser sessions
- ✅ Proper error handling and user feedback

### 🔍 **KNOWN ISSUES**
- ⚠️ Individual chat detail loading needs implementation
- ⚠️ Message fetching for specific chats pending
- ⚠️ Chat pagination could be optimized further

### 🧰 **DEVELOPER NOTES**
- All Telegram session strings now properly encrypted before database storage
- Session validation happens automatically on each API request
- Development environment includes comprehensive logging for debugging
- Container architecture ready for production scaling

---

## [v0.2.x] - Previous Iterations
- Initial project setup and architecture exploration
- Multiple authentication approach attempts
- Foundation building and dependency management

---

## [v0.1.x] - Project Genesis  
- Project initialization
- Basic FastAPI + Next.js setup
- Docker containerization
- Database schema design

---

**🎉 CELEBRATION**: v0.3.0 represents a complete breakthrough in authentication architecture! 
The karma-app now has a bulletproof foundation for Telegram integration. 🚀 