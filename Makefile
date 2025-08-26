.PHONY: help install test run docker-build docker-run docker-stop clean

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

docker-run: ## Run with Docker Compose
	docker-compose -f docker/docker-compose.yml up --build

docker-run-ollama: ## Run with Docker Compose including Ollama
	docker-compose -f docker/docker-compose.yml --profile ollama up --build

docker-stop: ## Stop Docker containers
	docker-compose -f docker/docker-compose.yml down

docker-logs: ## View Docker logs
	docker-compose -f docker/docker-compose.yml logs -f

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

setup-env: ## Copy environment file template
	cp env.example .env
	@echo "Please edit .env file with your configuration"

check-env: ## Check if .env file exists
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup-env' first."; \
		exit 1; \
	fi

start: check-env install run ## Install dependencies and start the application

dev: check-env install-dev run-dev ## Install dev dependencies and start in development mode
