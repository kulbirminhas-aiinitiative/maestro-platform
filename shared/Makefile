# MAESTRO Shared Libraries - Development Makefile

.PHONY: help install install-dev test test-all lint format type-check security docs clean build publish

# Default target
help: ## Show this help message
	@echo "MAESTRO Shared Libraries Development Commands"
	@echo "============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation targets
install: ## Install all packages in development mode
	poetry install
	@for package in packages/*/; do \
		echo "Installing $$package..."; \
		cd "$$package" && poetry install && cd - > /dev/null; \
	done

install-dev: ## Install development dependencies
	poetry install --with dev,docs
	poetry run pre-commit install

# Testing targets
test: ## Run tests for all packages
	@for package in packages/*/; do \
		echo "Testing $$package..."; \
		cd "$$package" && poetry run pytest tests/ -v && cd - > /dev/null; \
	done

test-package: ## Run tests for specific package (usage: make test-package PACKAGE=core-logging)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make test-package PACKAGE=<package-name>"; \
		exit 1; \
	fi
	cd packages/$(PACKAGE) && poetry run pytest tests/ -v

test-coverage: ## Run tests with coverage report
	@for package in packages/*/; do \
		echo "Testing $$package with coverage..."; \
		cd "$$package" && poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term && cd - > /dev/null; \
	done

test-integration: ## Run integration tests
	poetry run pytest tests/integration/ -v

test-performance: ## Run performance tests
	poetry run pytest tests/performance/ -v --benchmark-only

test-all: test test-integration test-performance ## Run all tests

# Code quality targets
lint: ## Run linting checks
	poetry run ruff check packages/
	poetry run bandit -r packages/ -x tests/

format: ## Format code
	poetry run black packages/
	poetry run isort packages/

format-check: ## Check code formatting
	poetry run black --check packages/
	poetry run isort --check-only packages/

type-check: ## Run type checking
	poetry run mypy packages/

security: ## Run security checks
	poetry run safety check
	poetry run bandit -r packages/ -f json -o security-report.json

pre-commit: ## Run all pre-commit hooks
	poetry run pre-commit run --all-files

# Quality gates (for CI)
quality-gate: format-check lint type-check security ## Run all quality checks

# Documentation targets
docs: ## Build documentation
	cd docs/ && poetry run sphinx-build -b html . _build/html

docs-serve: ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8080

docs-clean: ## Clean documentation build
	rm -rf docs/_build/

# Package management
clean: ## Clean build artifacts
	@for package in packages/*/; do \
		echo "Cleaning $$package..."; \
		cd "$$package" && rm -rf dist/ build/ *.egg-info/ && cd - > /dev/null; \
	done
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: ## Build all packages
	@for package in packages/*/; do \
		echo "Building $$package..."; \
		cd "$$package" && poetry build && cd - > /dev/null; \
	done

build-package: ## Build specific package (usage: make build-package PACKAGE=core-logging)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make build-package PACKAGE=<package-name>"; \
		exit 1; \
	fi
	cd packages/$(PACKAGE) && poetry build

publish: ## Publish all packages to PyPI
	@for package in packages/*/; do \
		echo "Publishing $$package..."; \
		cd "$$package" && poetry publish && cd - > /dev/null; \
	done

publish-test: ## Publish all packages to TestPyPI
	@for package in packages/*/; do \
		echo "Publishing $$package to TestPyPI..."; \
		cd "$$package" && poetry config repositories.testpypi https://test.pypi.org/simple/ && poetry publish -r testpypi && cd - > /dev/null; \
	done

# Development targets
dev-setup: install-dev ## Complete development setup
	poetry run pre-commit install
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works."

dev-test: ## Quick development test (format, lint, test)
	make format
	make lint
	make test

# Database targets (for services using core-db)
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@for package in packages/*/; do \
		if [ -f "$$package/alembic.ini" ]; then \
			echo "Migrating $$package..."; \
			cd "$$package" && poetry run alembic upgrade head && cd - > /dev/null; \
		fi; \
	done

db-revision: ## Create new database revision (usage: make db-revision MESSAGE="description")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Usage: make db-revision MESSAGE='revision description'"; \
		exit 1; \
	fi
	@echo "Creating database revision: $(MESSAGE)"
	poetry run alembic revision --autogenerate -m "$(MESSAGE)"

# Monitoring targets
metrics: ## Show development metrics
	@echo "Package sizes:"
	@du -sh packages/*/ | sort -hr
	@echo "\nTest coverage:"
	@find packages/ -name "htmlcov" -type d | while read dir; do \
		echo "$$dir: $$(grep -o 'pc_cov">[0-9]*%' "$$dir/index.html" 2>/dev/null | head -1 | grep -o '[0-9]*%' || echo 'N/A')"; \
	done

# Utility targets
list-packages: ## List all packages
	@ls -1 packages/

dependencies: ## Show dependency tree
	poetry show --tree

outdated: ## Show outdated dependencies
	poetry show --outdated

update: ## Update all dependencies
	poetry update
	@for package in packages/*/; do \
		echo "Updating $$package..."; \
		cd "$$package" && poetry update && cd - > /dev/null; \
	done

# CI/CD simulation
ci-local: ## Simulate CI pipeline locally
	@echo "Running local CI simulation..."
	make quality-gate
	make test-all
	make build
	@echo "✅ Local CI simulation completed successfully!"

# Release targets
release-check: ## Check if ready for release
	@echo "Checking release readiness..."
	make quality-gate
	make test-all
	make docs
	@echo "✅ Ready for release!"

version-bump: ## Bump version for all packages (usage: make version-bump VERSION=1.1.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make version-bump VERSION=x.y.z"; \
		exit 1; \
	fi
	@for package in packages/*/; do \
		echo "Bumping version for $$package to $(VERSION)..."; \
		cd "$$package" && poetry version $(VERSION) && cd - > /dev/null; \
	done