# Car Rental System

A modern car rental management system built with FastAPI and React.

## Project Structure

```
.
├── backend/
│   ├── models/         # SQLAlchemy models
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   ├── repositories/   # Database operations
│   ├── main.py        # FastAPI application
│   └── database.py    # Database configuration
├── frontend/          # React application
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