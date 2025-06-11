# Karma App Backend

A modern karma app backend system built with FastAPI.

## Changelog

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