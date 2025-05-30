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