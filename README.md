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

### Refactoring 12.06.2025 - Pruning Legacy Directories

**Objective**: Eliminate structural duplication and remove obsolete files to establish a single source of truth for the codebase structure.

#### ✅ **Major Changes Completed:**

**1. Pruning Legacy Directories**
- **Deleted `karmabackend/`**: Removed the entire obsolete `karmabackend` directory from the project root.
- **Deleted `karmafrontend/`**: Removed the empty `karmafrontend` directory from the project root.

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