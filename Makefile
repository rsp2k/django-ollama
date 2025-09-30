# Django-Ollama Docker Management Makefile

# Environment Configuration
include .env
export

# Default target
.DEFAULT_GOAL := help

.PHONY: help build up down logs restart clean dev prod health status

help: ## Show this help message
	@echo "Django-Ollama Docker Management"
	@echo "==============================="
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Commands
dev: ## Start in development mode with hot reload
	@echo "🚀 Starting Django-Ollama in development mode..."
	@BUILD_TARGET=development docker compose up --build -d
	@echo "✅ Development server running at http://$(DOMAIN)"

dev-logs: ## Follow development logs
	@docker compose logs -f django-ollama

# Production Commands
prod: ## Start in production mode
	@echo "🚀 Starting Django-Ollama in production mode..."
	@BUILD_TARGET=production docker compose up --build -d
	@echo "✅ Production server running at https://$(DOMAIN)"

# Basic Docker Commands
build: ## Build the Docker images
	@echo "🔨 Building Django-Ollama Docker images..."
	@docker compose build

up: ## Start services in background
	@echo "🚀 Starting Django-Ollama services..."
	@docker compose up -d

down: ## Stop and remove services
	@echo "🛑 Stopping Django-Ollama services..."
	@docker compose down

restart: ## Restart all services
	@echo "🔄 Restarting Django-Ollama services..."
	@docker compose restart

logs: ## Show logs from all services
	@docker compose logs -f

# Health and Status
health: ## Check service health
	@echo "🏥 Checking service health..."
	@docker compose ps

status: ## Show service status
	@echo "📊 Service Status:"
	@docker compose ps

# Maintenance Commands
clean: ## Clean up Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	@docker compose down -v
	@docker system prune -f

# Network Commands
network-create: ## Create the caddy network if it doesn't exist
	@docker network inspect caddy >/dev/null 2>&1 || docker network create caddy

# Development helpers
dev-setup: network-create dev ## Complete development setup
	@echo "🎉 Development environment ready!"
	@echo "   Django-Ollama: http://$(DOMAIN)"

prod-setup: network-create prod ## Complete production setup
	@echo "🎉 Production environment ready!"
	@echo "   Django-Ollama: https://$(DOMAIN)"
