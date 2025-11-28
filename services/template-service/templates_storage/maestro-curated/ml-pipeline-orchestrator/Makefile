.PHONY: help install test lint format clean docker-build docker-up docker-down k8s-deploy k8s-clean

help:
	@echo "ML Pipeline Orchestration - Available Commands"
	@echo "=============================================="
	@echo "install          - Install dependencies"
	@echo "test             - Run tests"
	@echo "test-cov         - Run tests with coverage"
	@echo "lint             - Run linters"
	@echo "format           - Format code"
	@echo "clean            - Clean generated files"
	@echo "run              - Run API locally"
	@echo "docker-build     - Build Docker image"
	@echo "docker-up        - Start Docker Compose"
	@echo "docker-down      - Stop Docker Compose"
	@echo "k8s-deploy       - Deploy to Kubernetes"
	@echo "k8s-clean        - Clean Kubernetes resources"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=ml_pipeline --cov-report=html --cov-report=term

lint:
	flake8 ml_pipeline/ tests/
	mypy ml_pipeline/

format:
	black ml_pipeline/ tests/ examples/
	isort ml_pipeline/ tests/ examples/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov/
	rm -rf logs/ output/ artifacts/

run:
	python -m uvicorn ml_pipeline.api:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t ml-pipeline:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

k8s-deploy:
	kubectl apply -f kubernetes/

k8s-clean:
	kubectl delete -f kubernetes/

k8s-status:
	kubectl get pods -l app=ml-pipeline
	kubectl get services -l app=ml-pipeline