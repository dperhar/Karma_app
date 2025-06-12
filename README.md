# Karma App

## 🔒 Security & Environment Protection

This project has **100% protection** against accidental `.env` file commits:

### 1. Git Hook Protection
- **Pre-commit hook** automatically blocks any commit containing `.env` files
- Hook is located at `.git/hooks/pre-commit`
- Scans for patterns: `.env`, `.env.*`, `frontend/.env`, `backend/.env`

### 2. .gitignore Protection  
- Comprehensive `.env` patterns in `.gitignore`
- Covers all environment file variations

### 3. Template Files
- Use `.env.example` files for sharing configuration templates
- **Never commit actual `.env` files with sensitive data**

### Setup Instructions
1. Copy `.env.example` to `.env`
2. Fill in your actual values
3. The git hook will prevent accidental commits

### If Hook Blocks Your Commit
```bash
# Remove .env files from staging
git reset HEAD .env
git reset HEAD frontend/.env

# Or remove from git entirely
git rm --cached .env
```

## 🏗️ Refactoring History

### 15.06.2025 - Complete Telegram Authentication System Overhaul

**Objective**: Fix critical frontend initialization bug and implement robust Telegram authentication using proven Telethon approach from v0.27.

#### 🚨 **Critical Bugs Fixed:**

**1. Frontend Initialization Crisis**
- **Fixed Critical Bug**: Resolved `ERR_UNKNOWN_ENV` error that was preventing frontend startup
- **Root Cause**: Flawed logic in `mockTelegramEnv.ts` - SDK environment detection was skipping mock setup when `isTMA("simple")` returned true, even in development
- **Solution**: Completely replaced broken SDK approach with working Telethon implementation from v0.27 repository
- **Impact**: Eliminated race conditions and environment detection problems that were blocking all frontend development

**2. Backend Dependency Injection Failures**
- **Fixed Critical Bug**: Services failing to resolve dependencies causing startup crashes
- **Root Cause**: Manual service instantiation in routes bypassing DI container: `UserService()` instead of using container
- **Solution**: Updated all routes to use proper dependency injection: `container.resolve(TelegramMessengerAuthService)`
- **Impact**: Restored proper service lifecycle management and dependency resolution

**3. API Routing Mismatches**
- **Fixed Critical Bug**: Frontend calling `/api/telegram/auth/*` but backend serving `/api/v1/telegram/auth/*`
- **Root Cause**: Environment variable `NEXT_PUBLIC_API_URL=http://localhost:8000/api` missing `/v1` prefix
- **Solution**: Updated docker-compose.yml to `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
- **Impact**: Eliminated all 404 errors and established proper API communication

**4. Session Management Catastrophe**
- **Fixed Critical Bug**: Sessions expiring immediately due to new service instances on each request
- **Root Cause**: `TelegramMessengerAuthService` registered without singleton scope, creating new instances that lose session storage
- **Solution**: Changed registration to `container.register(TelegramMessengerAuthService, scope=Scope.singleton)`
- **Impact**: Sessions now persist correctly across requests, enabling proper QR login flow

#### ✅ **Major Implementation Changes:**

**1. Complete SDK Replacement**
- **Removed**: `@telegram-apps/sdk-react` and `@telegram-apps/telegram-ui` (problematic SDK approach)
- **Implemented**: Proven Telethon user account API from v0.27 (now officially allowed by Telegram policy)
- **Migrated Components**:
  - `useTelegramQRLogin.ts` hook with QR generation and polling
  - `TelegramAuthModal` component with clean UI
  - `auth-service.ts` API client with proper error handling
  - Backend `TelegramMessengerAuthService` with Telethon integration

**2. Authentication Middleware Integration**
- **Added Public Paths**: Updated `AuthMiddleware` to whitelist telegram auth endpoints:
  - `/api/v1/telegram/auth/qr-code`
  - `/api/v1/telegram/auth/check`
  - `/api/v1/telegram/auth/verify-2fa`
- **Result**: Telegram authentication bypasses standard auth requirements

**3. QR Login Flow Correction**
- **Fixed Critical Logic Bug**: `check_qr_login` was calling `ExportLoginTokenRequest` (generates NEW token) instead of `ImportLoginTokenRequest` (checks existing token)
- **Corrected Implementation**: Now properly imports QR token bytes to check authentication status
- **Added 2FA Support**: Proper handling of `SessionPasswordNeededError` with verification flow

**4. Frontend Architecture Simplification**
- **Removed**: Complex SDK initialization with environment detection race conditions
- **Implemented**: Simple API-based flow where frontend handles UI and backend handles all Telegram logic
- **New Flow**: QR generation → polling mechanism → success callback → authenticated state

#### 🔧 **Technical Improvements:**

**1. Container Environment Propagation**
- **Fixed**: Environment variables not propagating to recreated containers
- **Solution**: Complete container recreation with `docker-compose rm -f frontend && docker-compose up -d frontend`
- **Result**: Environment changes now properly applied without caching issues

**2. Import Path Standardization**
- **Updated**: All import paths from legacy structure to new project architecture
- **Fixed**: Backend imports to use `app.core.config`, `app.services.user_service` patterns
- **Cleaned**: Frontend imports to use consistent `@/lib/api/*` structure

**3. Memory Session Storage**
- **Implemented**: Secure session storage with metadata tracking
- **Added**: Automatic cleanup tasks with 5-minute expiration
- **Enhanced**: Session validation with timestamp checks and proper error handling

#### 🎯 **Results:**
- ✅ **Frontend Development Restored**: No more SDK initialization errors, clean local development
- ✅ **Authentication System Working**: Complete QR login flow with 2FA support
- ✅ **Session Persistence**: Proper session management across requests
- ✅ **API Communication**: Frontend and backend properly connected via `/api/v1`
- ✅ **Container Stability**: Environment variables and dependencies properly resolved
- ✅ **Architecture Simplification**: Removed complex SDK dependencies in favor of proven API approach

#### 📱 **User Experience Impact:**
- **QR Code Generation**: Instant, reliable QR code creation for Telegram login
- **Real-time Polling**: Smooth status checking without false "expired" messages
- **2FA Integration**: Seamless two-factor authentication when required
- **Session Management**: Authenticated sessions properly saved and maintained
- **Error Handling**: Clear, actionable error messages instead of cryptic SDK failures

#### 🔐 **Security Enhancements:**
- **Session Encryption**: All session strings encrypted using `EncryptionService`
- **Token Validation**: Proper base64 and format validation for QR tokens
- **Rate Limiting**: Built-in Telegram API rate limiting and human-like behavior
- **Memory Safety**: Automatic session cleanup prevents memory leaks

### 14.06.2025 - Asynchronous Task System Implementation

**Objective**: Transform the application from synchronous blocking operations to a robust asynchronous task system for scalable LLM processing and background operations.

#### ✅ **Major Changes Completed:**

**1. Celery Task Infrastructure**
- **Implemented Comprehensive Task System**: Added three core asynchronous tasks for better performance and user experience
  - `analyze_vibe_profile`: Analyzes user's Telegram message history using LLM to create personalized communication profiles
  - `generate_draft_for_post`: Generates contextual comment drafts based on user's vibe profile and post content
  - `check_for_new_posts_and_generate_drafts`: Scheduled monitoring task that automatically generates drafts for new channel posts
- **Added Celery Beat Scheduling**: Configured automated task scheduling to run every 15 minutes for continuous post monitoring
- **Enhanced Worker Configuration**: Updated `worker.py` with proper crontab scheduling and task routing

**2. API Endpoint Refactoring**
- **Transformed `/regenerate` Endpoint**: Converted from synchronous blocking operation to async task queue with immediate response
- **Updated Response Models**: Changed from `DraftCommentResponse` to `dict` for task status tracking
- **Simplified Authentication Flow**: Streamlined `/analyze-vibe-profile` endpoint to directly dispatch Celery tasks
- **Added Request Schemas**: Implemented `PostData` and `RegenerateRequest` schemas for proper data validation

**3. Advanced LLM Integration**
- **Intelligent Vibe Profile Analysis**: Uses Gemini LLM to analyze user's communication patterns and create detailed profiles including:
  - Tone analysis (casual, formal, sarcastic, etc.)
  - Verbosity patterns (brief, moderate, verbose)
  - Emoji usage patterns
  - Common phrases and expressions
  - Topics of interest
- **Context-Aware Draft Generation**: Generates comments that match user's communication style while considering:
  - User's past rejected drafts (learning from feedback)
  - Post relevance based on user interests
  - Personalized tone and style preferences

**4. Real-time User Notifications**
- **WebSocket Integration**: Comprehensive real-time notifications for all async operations:
  - `vibe_profile_analyzing`: Started analysis notification
  - `vibe_profile_completed`: Successful completion with profile data
  - `vibe_profile_failed`: Error handling with detailed error messages
  - `new_ai_draft`: New draft generated notification
  - `draft_generation_failed`: Draft generation error handling
- **Progress Tracking**: Users receive immediate feedback on task status and completion

**5. Feedback Learning System**
- **Negative Feedback Processing**: System learns from rejected drafts by:
  - Storing rejection reasons in `NegativeFeedbackRepository`
  - Updating draft status to `REJECTED`
  - Incorporating feedback into future generation prompts
- **Intelligent Regeneration**: Improved draft quality through iterative learning from user preferences

**6. Automated Content Monitoring**
- **Channel Monitoring**: Scheduled task automatically:
  - Monitors user's subscribed Telegram channels
  - Detects new posts and messages
  - Generates relevant draft comments based on user's interests
  - Filters content based on user's topics of interest
- **Smart Relevance Filtering**: Only generates drafts for posts that match user's communication preferences and interests

#### 🎯 **Results:**
- ✅ **Non-blocking API**: All LLM operations now run asynchronously, preventing API timeouts
- ✅ **Real-time User Experience**: Immediate task queuing with WebSocket progress updates
- ✅ **Intelligent Draft Generation**: Personalized comments that match user's communication style
- ✅ **Automated Content Discovery**: Continuous monitoring and draft generation for relevant posts
- ✅ **Learning System**: Improved draft quality through feedback incorporation
- ✅ **Scalable Architecture**: Task queue can handle multiple concurrent users and operations

#### 🔧 **Technical Improvements:**
- **Async Task Processing**: Eliminated blocking operations that could cause API timeouts
- **Proper Error Handling**: Comprehensive exception handling with user-friendly error messages
- **Session Management**: Secure handling of Telegram client sessions with automatic cleanup
- **Memory Optimization**: Efficient resource management with proper client disconnection
- **JSON Processing**: Robust LLM response parsing with regex pattern matching for reliable data extraction

#### 📱 **User Experience Impact:**
- **Instant Response**: Users get immediate confirmation that their requests are being processed
- **Progress Visibility**: Real-time updates on long-running operations like vibe analysis
- **Personalized Content**: Drafts that truly sound like the user's own communication style
- **Proactive Suggestions**: Automatic draft generation for relevant new content
- **Improved Quality**: Better drafts through learning from user feedback and preferences

### 14.06.2025 - Critical Frontend Telegram Environment Fix
- **Fixed Critical Bug**: Resolved `TypedError: Unable to retrieve launch parameters from any known source` that was preventing frontend development in local browsers.
- **Root Cause**: The `mockTelegramEnv.ts` was setting `initData: undefined` instead of properly parsing the generated `initDataRaw` using the SDK's `parseInitData` function.
- **Solution**: Changed `initData: undefined` to `initData: parseInitData(initDataRaw)` in the launch parameters object, ensuring all required fields like `platform` are properly available to the SDK.
- **Result**: Frontend now starts successfully in development mode with proper mock Telegram environment, enabling efficient local development and testing.
- **Impact**: Critical fix that restores the frontend development workflow, eliminating the need to test exclusively within Telegram client during development.

### 13.06.2025 - Frontend Development Environment Fix
- **Fixed Critical Bug**: Resolved a cascade of errors in the frontend caused by a flawed Telegram SDK mocking mechanism. The application is now fully functional in a local development environment.
- **Corrected Mock Data**: The `useTelegramMock.ts` hook now generates a valid `initDataRaw` string including a mock hash, satisfying the SDK parser and allowing for successful initialization outside the Telegram client.
- **Telethon Compatibility**: Updated the mock to work with Telethon-based user account setups (now officially allowed by Telegram policy) rather than just bot-based authentication.
- **Improved Error Handling**: Added proper try-catch blocks and warning messages for better debugging experience during development.
- **Result**: The frontend development workflow is restored, enabling developers to build and test components efficiently in a local browser.

### Refactoring 12.06.2025 - Pruning Legacy Directories

**Objective**: Eliminate structural duplication and remove obsolete files to establish a single source of truth for the codebase structure.

#### ✅ **Major Changes Completed:**

**1. Pruning Legacy Directories**
- **Deleted `karmabackend/`**: Removed the entire obsolete `karmabackend` directory from the project root.
- **Deleted `karmafrontend/`**: Removed the empty `karmafrontend` directory from the project root.

**2. Pruning Obsolete Backend Directories**
- **Deleted `backend/services/`**: Removed the entire obsolete `services` directory from the `backend/` root to eliminate structural duplication. All logic has been migrated to the `backend/app/services/` directory.

#### 🎯 **Results:**
- ✅ **Cleaner Project Root**: The project root is now free of confusing legacy directories.
- ✅ **Single Source of Truth**: The `backend/` and `frontend/` directories are now the unambiguous sources of truth.
- ✅ **Reduced Ambiguity**: Eliminates the risk of developers using or referencing outdated code from legacy directories.

### Refactoring 11.06.2025 - Dependency Injection System Overhaul

**Objective**: Reorganize and simplify the dependency injection system by moving it to the core module and cleaning up service registration.

#### ✅ **Major Changes Completed:**

**1. Dependency Container Reorganization**
- **Moved from** `app/services/dependencies.py` **to** `app/core/dependencies.py`
- **Centralized** all dependency management in the core module for better organization
- **Simplified** service registration with cleaner factory functions
- **Improved** separation between repositories and services

**2. Import Path Cleanup**
- **Updated** all import statements across the codebase to use `app.core.dependencies`
- **Fixed** import paths in admin routes (`auth.py`, `menu.py`, `messages.py`, `users.py`)
- **Corrected** service imports in `main.py` to use proper `app.services` paths
- **Added** missing `get_current_admin` imports to admin routes

**3. Service Registration Improvements**
- **Streamlined** service factory functions with lambda expressions
- **Better organized** services into categories (Core, Application, Legacy/Admin)
- **Cleaner** repository registration with consistent patterns
- **Simplified** container initialization logic

**4. Code Cleanup**
- **Removed** duplicate dependency files from multiple locations
- **Deleted** obsolete `services/dependencies.py` files
- **Fixed** router import naming in `main.py` (api_v1_router → api_router)
- **Eliminated** redundant code and factory functions

#### 🎯 **Results:**
- ✅ **Centralized Architecture**: All dependency injection logic is now in `app/core/dependencies.py`
- ✅ **Improved Maintainability**: Cleaner service registration makes it easier to add new services
- ✅ **Better Organization**: Clear separation between core, application, and legacy services
- ✅ **Consistent Imports**: All modules now use the same dependency injection pattern
- ✅ **Reduced Complexity**: Simplified container with less complex factory functions

### Refactoring 11.06.2025 - API v1 Structure Implementation

**Objective**: Restructure the entire API layer to be more modular, scalable, and maintainable by consolidating scattered endpoints into a versioned `/api/v1/` structure.

#### ✅ **Major Changes Completed:**

**1. API Consolidation & Versioning**
- **Nuked the old `app/api/` structure**: Replaced a chaotic mix of over a dozen route files with a clean, versioned API.
- **Introduced `app/api/v1/`**: All primary application endpoints are now organized under a `/api/v1/` prefix, ensuring future compatibility.
- **Consolidated Routes**: Endpoints for authentication, drafts, and users were moved from scattered files into focused modules:
    - `v1/auth.py`: Manages all user authentication, including Telegram QR login and 2FA.
    - `v1/drafts.py`: Handles all CRUD operations for draft comments.
    - `v1/users.py`: Manages user profiles and settings.

**2. Massive Code Cleanup**
- **Deleted Redundant Files**: Removed over 15 legacy route files (`ai_dialogs.py`, `karma.py`, `menu.py`, `telegram/*`, `transcribe.py`, `websocket.py`, etc.).
- **Removed `routes/` Directory**: The entire legacy `routes/` directory and its dependencies were eliminated.
- **Simplified `main.py`**: The main application entry point was cleaned up, going from over 15 router inclusions to just 2 (`admin_router` and `api_v1_router`).

**3. Architecture & Service Improvements**
- **Clean Separation**: `v1/router.py` now acts as the central orchestrator for all v1 endpoints.
- **Domain-Driven Service Location**: The `WebSocketService` was moved to `services/domain/`, aligning with a cleaner domain-driven structure.
- **Corrected Import Paths**: All import paths were updated to reflect the new, cleaner project structure, resolving multiple `ModuleNotFoundError` issues.

#### 🎯 **Results:**
- ✅ **Clean, Versioned API**: The application now exposes a modern, versioned API surface at `/api/v1/`.
- ✅ **Improved Scalability**: The new structure allows for easy addition of future API versions (e.g., `/api/v2/`) without impacting existing clients.
- ✅ **Enhanced Maintainability**: Finding and managing endpoints is now straightforward, significantly reducing cognitive overhead.
- ✅ **Application Stability**: The application now compiles and imports successfully without any path-related errors.

### Refactoring 11.06.2024 - Service Layer & Telegram Integration

**Objective**: Refactor the core service layer, replace the monolithic `TelethonClient`, and introduce a more robust and secure architecture for handling Telegram connections and AI interactions.

#### ✅ **Major Changes Completed:**

**1. Service Refactoring & Decoupling**
- **Replaced `TelethonClient`**: The old, monolithic `TelethonClient` has been deprecated and replaced by a new, more focused `TelegramService`.
- **Introduced `AIService`**: Consolidated all AI and LLM interaction logic into a single `AIService` for better maintainability.
- **Created `DraftService`**: Manages all operations related to creating, updating, and approving draft comments, separating it from the core karma logic.

**2. Improved Telegram Connection Management**
- **New `TelegramConnection` Model**: Introduced a dedicated database model (`TelegramConnection`) to securely store encrypted session strings and connection metadata.
- **`TelegramConnectionRepository`**: Added a new repository to manage all database operations for Telegram connections.
- **`TelegramService`**: The new service now manages the client lifecycle, caching, and secure session handling using the `TelegramConnectionRepository` and `EncryptionService`.

**3. Enhanced Security**
- **Mandatory `ENCRYPTION_KEY`**: The application now requires an `ENCRYPTION_KEY` in the `.env` file to encrypt all sensitive session data at rest, significantly improving security.
- **Decoupled User Model**: Removed the `telegram_session_string` from the `User` model, moving it to the dedicated `TelegramConnection` model.

**4. Dependency Injection & Startup Fixes**
- **Resolved Startup Error**: Fixed the critical `ValueError: No implementation registered for <class 'services.external.telethon_client.TelethonClient'>` by updating the dependency injection container.
- **Cleaned Dependencies**: The dependency container now correctly registers and resolves the new, refactored services (`TelegramService`, `AIService`, `DraftService`).

#### 🎯 **Results:**
- ✅ **Fixed Critical Startup Bug**: The application now starts without dependency injection errors.
- ✅ **Improved Modularity**: Services are now more focused and decoupled, following the Single Responsibility Principle.
- ✅ **Enhanced Security**: Telegram session strings are now securely encrypted in the database.
- ✅ **Robust Architecture**: The new service-oriented architecture is more scalable and easier to maintain and extend.

### Refactoring 10.06.2024 - Backend Architecture Restructuring

**Objective**: Complete backend restructuring for better scalability, cleaner architecture, and improved maintainability.

#### ✅ **Major Changes Completed:**

**1. Directory Structure Reorganization**
- **From**: Mixed `routes/`, `app/`, scattered services
- **To**: Clean FastAPI structure with organized subdirectories

**2. New Backend Structure:**
```
backend/
├── app/
│   ├── main.py                 # ← Simplified entry point
│   ├── core/config.py          # ← Clean Settings class
│   ├── api/                    # ← All API routes organized
│   │   ├── admin/              # ← Admin endpoints
│   │   ├── auth/               # ← Authentication endpoints
│   │   ├── telegram/           # ← Telegram integration
│   │   └── v1/                 # ← API versioning
│   ├── models/                 # ← Flattened model structure
│   ├── schemas/                # ← Clean schema organization
│   ├── repositories/           # ← Data access layer
│   └── services/               # ← Business logic services
├── models/                     # ← Root-level models with subdirs
│   ├── base/                   # ← Base schemas & models
│   ├── user/                   # ← User-related models
│   ├── ai/                     # ← AI-related models
│   └── telegram_messenger/     # ← Telegram models
├── services/                   # ← Organized service structure
│   ├── domain/                 # ← Business logic services
│   ├── external/               # ← External API integrations
│   ├── base/                   # ← Base service classes
│   └── security/               # ← Security services
└── middleware/                 # ← Authentication & middleware
```

**3. Configuration Improvements**
- Simplified `Settings` class with proper defaults
- Added missing configuration variables (DB, S3, Centrifugo, Sessions)
- Better environment variable handling

**4. Import Path Cleanup**
- Fixed all circular import issues
- Standardized import paths across the application
- Removed redundant directory structures

**5. Service Organization**
- Moved services to proper domain/external/base/security structure
- Improved dependency injection container
- Better separation of concerns

#### 🎯 **Results:**
- ✅ FastAPI app imports and runs successfully
- ✅ All critical modules load without errors
- ✅ Routes are properly registered and accessible
- ✅ Clean, scalable architecture for future development
- ✅ Improved maintainability and developer experience

#### 🔧 **Technical Details:**
- **Framework**: FastAPI with clean architecture patterns
- **Structure**: Domain-driven design with clear separation
- **Services**: Dependency injection with proper interfaces
- **Configuration**: Environment-based with sensible defaults

---

## Development Setup

<!-- Rest of README content --> 