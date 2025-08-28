.PHONY: help install test run docker-build docker-run docker-stop docker-restart docker-logs clean

help: ## Show this help message
	@echo "Slack Bot AI Chat - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html

run: ## Run the application locally
	python start.py

run-dev: ## Run with development settings
	DEBUG=true python start.py

docker-build: ## Build Docker image
	docker build -f docker/Dockerfile -t slack-ai-bot .

docker-run: ## Run with Docker Compose (non-blocking)
	docker-compose -f docker/docker-compose.yml up --build -d

docker-stop: ## Stop Docker containers
	docker-compose -f docker/docker-compose.yml down

docker-restart: ## Stop and start Docker containers
	docker-compose -f docker/docker-compose.yml down
	docker-compose -f docker/docker-compose.yml up --build -d

docker-logs: ## View Docker logs
	docker-compose -f docker/docker-compose.yml logs -f

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

start: install run ## Install dependencies and start the application

dev: install-dev run-dev ## Install dev dependencies and start in development mode

integration-test: ## Run integration tests (containers must be started manually)
	@echo "Running integration tests..."
	@./tests/run_integration_test.sh