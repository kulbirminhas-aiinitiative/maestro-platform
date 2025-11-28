.PHONY: help install test lint format clean docker-build docker-up docker-down k8s-deploy k8s-delete

help:
	@echo "Available commands:"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linters"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up build artifacts"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-up     - Start Docker Compose services"
	@echo "  docker-down   - Stop Docker Compose services"
	@echo "  k8s-deploy    - Deploy to Kubernetes"
	@echo "  k8s-delete    - Delete from Kubernetes"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	flake8 src/ tests/
	pylint src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker build -t eventsourcing-api:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

k8s-deploy:
	kubectl apply -f kubernetes/namespace.yaml
	kubectl apply -f kubernetes/postgres-deployment.yaml
	kubectl apply -f kubernetes/redis-deployment.yaml
	sleep 30
	kubectl apply -f kubernetes/deployment.yaml
	kubectl apply -f kubernetes/hpa.yaml
	kubectl apply -f kubernetes/ingress.yaml

k8s-delete:
	kubectl delete -f kubernetes/