# Karma App Backend

A modern karma app backend system built with FastAPI.

## Changelog

### Refactoring 13.06.2025 - Finalization and Cleanup

**Objective**: Finalize the architecture by consolidating API routes and integrating the aiogram worker, and removing all remaining obsolete code.

#### ✅ **Major Changes Completed:**

**1. API Route Consolidation**
- **Deleted Obsolete Directories**: Removed the empty `backend/app/api/auth/` and `backend/app/api/telegram/` directories. All API logic is now cleanly organized under `backend/app/api/v1/` and `backend/app/api/admin/`.

**2. Aiogram Worker Integration**
- **Refactored `TelegramBotService`**: The logic from the `backend/app/worker/` directory has been refactored into a new, robust `TelegramBotService`.
- **Integrated into FastAPI Lifespan**: The bot is now started and stopped gracefully with the main FastAPI application via the `lifespan` manager in `main.py`.
- **Deleted `app/worker/`**: The entire obsolete `app/worker/` directory has been removed, completing the architectural cleanup.

#### 🎯 **Results:**
- ✅ **Simplified API Structure**: The API directory is now cleaner and follows the intended versioned structure.
- ✅ **Integrated Bot**: The aiogram bot is no longer a separate, unmanaged component but an integrated part of the main application.
- ✅ **Codebase Cleanup**: All obsolete directories and files from this phase have been pruned, reducing technical debt.

### Refactoring 12.06.2025 - Telethon Service Consolidation

**Objective**: Create a single, reliable service for all Telegram interactions, eliminating redundancy and confusion.

#### ✅ **Major Changes Completed:**

**1. Consolidated `TelegramService`**
- **Merged Logic**: The new `TelegramService` (`app/services/telegram_service.py`) now contains all logic for client lifecycle management, session decryption, and high-level API calls.
- **Simplified Architecture**: Replaced the complex `RefactoredTelethonClientService`, `ConnectionPool`, `SessionManager`, and `ConnectionMonitor` with a single, streamlined service.

**2. Deleted Redundant Services**
- **Removed 6 files**: `refactored_client_service.py`, `telethon_client.py`, `telethon_service.py` (old), `connection_pool.py`, `connection_monitor.py`, `session_manager.py`.

**3. Updated Dependency Injection**
- **Cleaned `dependencies.py`**: Removed registrations for all obsolete Telethon-related services.
- **Ensured `TelegramService`** is the single source of truth for Telegram interactions in the DI container.

#### 🎯 **Results:**
- ✅ **Single Source of Truth**: All Telegram-related logic is now in one place, improving maintainability.
- ✅ **Reduced Complexity**: The service layer is significantly simpler and easier to understand.
- ✅ **Improved Stability**: Centralized client management and error handling.

### 11.06.2025 - Major Architecture Refactoring
- **Complete restructure from `services.*` to `app.*` module organization**
- **Implemented dependency injection using `punq` container**
- **Updated all import paths across 25+ files**:
  - Scripts: `scripts/check_user.py`, `scripts/create_dev_user.py`, `scripts/setup_mark_zuckerberg_persona.py`
  - All test files in `tests/` directory
  - Middleware: `middleware/auth.py`
- **New DI container setup** in `app/core/dependencies.py`:
  - All repositories registered as singletons
  - All services registered with appropriate scopes
  - Clean dependency resolution for better testability
- **Path structure updates**:
  - `services.domain.*` → `app.services.*`
  - `services.repositories.*` → `app.repositories.*`
  - `models.user.user` → `app.models.user`
  - `routes.dependencies` → `app.dependencies`
- **Added `punq` dependency** to requirements.txt
- **Improved scalability and maintainability** with proper dependency injection patterns

## Project Structure

```
.
├── app/
│   ├── core/           # Core configuration and DI container
│   ├── models/         # SQLAlchemy models
│   ├── api/            # API endpoints
│   ├── services/       # Business logic
│   ├── repositories/   # Database operations
│   ├── schemas/        # Pydantic schemas
│   └── main.py         # FastAPI application
├── scripts/            # Utility scripts
├── tests/              # Test suite
├── middleware/         # Custom middleware
├── alembic/           # Database migrations
├── docker-compose.yml
└── requirements.txt
```

## Requirements

- Docker
- Docker Compose

## Getting Started

1. Clone the repository
2. Start the services:
   ```bash
   docker-compose up --build
   ```
3. Access the applications:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Database Migrations

To create a new migration:
```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

To apply migrations:
```bash
docker-compose exec backend alembic upgrade head
``` 