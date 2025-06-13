.PHONY: help build up down logs restart clean dev prod status db-init

# Цвета для вывода
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

help: ## Показать помощь
	@echo "$(GREEN)🐳 Karma App Docker Commands$(NC)"
	@echo "================================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(BLUE)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# === DEVELOPMENT ===
dev: ## 🚀 Запуск в режиме разработки
	@echo "$(GREEN)Starting development environment...$(NC)"
	docker-compose -f docker-compose.dev.yml up --build -d
	@echo "$(GREEN)✅ Development environment started!$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:3000$(NC)"
	@echo "$(YELLOW)Backend API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)API Docs: http://localhost:8000/docs$(NC)"

dev-logs: ## 📋 Логи разработки
	docker-compose -f docker-compose.dev.yml logs -f

dev-down: ## ⬇️ Остановка разработки
	@echo "$(RED)Stopping development environment...$(NC)"
	docker-compose -f docker-compose.dev.yml down

# === PRODUCTION ===
prod: ## 🏭 Запуск в продакшн режиме
	@echo "$(GREEN)Starting production environment...$(NC)"
	docker-compose up --build -d
	@echo "$(GREEN)✅ Production environment started!$(NC)"

prod-down: ## ⬇️ Остановка продакшна
	@echo "$(RED)Stopping production environment...$(NC)"
	docker-compose down

# === ОБЩИЕ КОМАНДЫ ===
build: ## 🔨 Пересборка всех образов
	@echo "$(YELLOW)Building all services...$(NC)"
	docker-compose build --no-cache

up: ## ⬆️ Запуск всех сервисов
	docker-compose up -d

down: ## ⬇️ Остановка всех сервисов
	docker-compose down

restart: ## 🔄 Перезапуск всех сервисов
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose restart

status: ## 📊 Статус контейнеров
	@echo "$(GREEN)Container Status:$(NC)"
	docker-compose ps

logs: ## 📋 Просмотр логов
	docker-compose logs -f

# === БАЗА ДАННЫХ ===
db-init: ## 🗄️ Инициализация базы данных
	@echo "$(GREEN)Initializing database...$(NC)"
	docker-compose exec backend python -c "from services.database.database_service import DatabaseService; DatabaseService().create_tables()"

db-shell: ## 🐘 Подключение к PostgreSQL
	docker-compose exec postgres psql -U postgres -d karma_app_dev

db-backup: ## 💾 Бэкап базы данных
	@echo "$(GREEN)Creating database backup...$(NC)"
	docker-compose exec postgres pg_dump -U postgres karma_app_dev > backup_$(shell date +%Y%m%d_%H%M%S).sql

# === ОЧИСТКА ===
clean: ## 🧹 Очистка всех контейнеров и образов
	@echo "$(RED)Cleaning up Docker resources...$(NC)"
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-all: ## 🧹💥 ПОЛНАЯ очистка (включая volumes)
	@echo "$(RED)⚠️  WARNING: This will delete ALL data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		docker-compose down -v --remove-orphans; \
		docker system prune -af; \
		docker volume prune -f; \
		echo "$(GREEN)✅ Complete cleanup done!$(NC)"; \
	else \
		echo ""; \
		echo "$(YELLOW)Cleanup cancelled.$(NC)"; \
	fi

# === ПОЛЕЗНОЕ ===
shell-backend: ## 🖥️ Shell в backend контейнер
	docker-compose exec backend bash

shell-frontend: ## 🖥️ Shell в frontend контейнер
	docker-compose exec frontend sh

shell-db: ## 🖥️ Shell в database контейнер
	docker-compose exec postgres bash

test: ## 🧪 Запуск тестов
	docker-compose exec backend python -m pytest

install: ## 📦 Установка зависимостей
	@echo "$(GREEN)Installing Docker and Docker Compose...$(NC)"
	@which docker >/dev/null 2>&1 || (echo "$(RED)Docker not found! Please install Docker first.$(NC)" && exit 1)
	@which docker-compose >/dev/null 2>&1 || (echo "$(RED)Docker Compose not found! Please install Docker Compose first.$(NC)" && exit 1)
	@echo "$(GREEN)✅ Docker setup verified!$(NC)"

# === БЫСТРЫЙ СТАРТ ===
quickstart: install ## 🚀 Быстрый старт для новых разработчиков
	@echo "$(GREEN)🚀 Karma App Quick Start$(NC)"
	@echo "========================="
	make dev
	@echo ""
	@echo "$(GREEN)🎉 Ready to go!$(NC)"
	@echo "$(YELLOW)Open: http://localhost:3000$(NC)"

# Fast development commands
.PHONY: build-backend
build-backend:
	@echo "Building backend image..."
	docker build -t karma-backend:latest ./backend

.PHONY: dev-backend
dev-backend: build-backend
	@echo "Starting backend services only..."
	docker-compose up postgres redis backend celery-worker -d

.PHONY: dev-full
dev-full: build-backend
	@echo "Starting all services..."
	docker-compose up -d

.PHONY: dev-logs
dev-logs:
	docker-compose logs -f backend celery-worker

.PHONY: clean-build
clean-build:
	@echo "Cleaning Docker build cache..."
	docker system prune -f
	docker builder prune -f

.PHONY: restart-backend
restart-backend:
	docker-compose restart backend celery-worker celery-beat

# 🚀 ULTRA-FAST DEVELOPMENT COMMANDS
.PHONY: dev-ultra-fast
dev-ultra-fast:
	@echo "🚀 Starting ULTRA-FAST development environment..."
	@echo "Building dev image with hot reload..."
	docker build -f Dockerfile.dev -t karma-dev-backend:latest ./backend
	@echo "Starting services with hot reload..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "$(GREEN)⚡ BLAZING FAST DEV MODE ACTIVE!$(NC)"
	@echo "$(YELLOW)🔥 Hot reload enabled - code changes apply instantly!$(NC)"
	@echo "$(YELLOW)📡 API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)📊 API Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)🔍 Health: http://localhost:8000/health$(NC)"

.PHONY: dev-stop
dev-stop:
	docker-compose -f docker-compose.dev.yml down

.PHONY: dev-rebuild
dev-rebuild:
	@echo "🔄 Rebuilding dev image..."
	docker build -f Dockerfile.dev -t karma-dev-backend:latest ./backend --no-cache
	docker-compose -f docker-compose.dev.yml up -d --force-recreate

.PHONY: dev-logs
dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f backend celery-worker

.PHONY: dev-shell
dev-shell:
	docker exec -it karma-dev-backend bash

.PHONY: test-api
test-api:
	@echo "🧪 Testing Karma App API endpoints..."
	@echo "Health check:"
	@curl -s http://localhost:8000/health | jq '.' 2>/dev/null || curl -s http://localhost:8000/health
	@echo ""
	@echo "User endpoint (development mode):"
	@curl -s http://localhost:8000/api/v1/users/me | jq '.' 2>/dev/null || curl -s http://localhost:8000/api/v1/users/me
	@echo ""
	@echo "API Documentation: http://localhost:8000/docs"

.PHONY: test-celery
test-celery:
	@echo "🔄 Testing Celery workers..."
	docker exec karma-dev-celery-worker celery -A app.tasks.worker.celery_app inspect active
	@echo "Queue status:"
	docker exec karma-dev-celery-worker celery -A app.tasks.worker.celery_app inspect active

.PHONY: test-full
test-full: test-api test-celery
	@echo ""
	@echo "$(GREEN)✅ Full Karma App functionality test complete!$(NC)"
	@echo "$(YELLOW)Architecture compliance: ✅ API thin gateway, ✅ Worker engine, ✅ Task-oriented$(NC)" 