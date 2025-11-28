.PHONY: help build up down test clean logs ps

help:
	@echo "Real-Time Analytics Platform - Make Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make up          - Start all services with Docker Compose"
	@echo "  make down        - Stop all services"
	@echo "  make ps          - Show running services"
	@echo "  make logs        - Tail all service logs"
	@echo "  make build       - Build Docker images"
	@echo "  make clean       - Remove all containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run unit tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make simulate    - Generate test traffic"
	@echo ""
	@echo "Production:"
	@echo "  make k8s-deploy  - Deploy to Kubernetes"
	@echo "  make k8s-status  - Check Kubernetes deployment status"
	@echo "  make k8s-clean   - Remove Kubernetes deployment"

up:
	docker-compose up -d

down:
	docker-compose down

ps:
	docker-compose ps

logs:
	docker-compose logs -f

build:
	docker-compose build

clean:
	docker-compose down -v
	docker system prune -f

test:
	cd tests && pip install -r requirements.txt && pytest -v

test-cov:
	cd tests && pip install -r requirements.txt && pytest --cov=../src --cov-report=html -v

simulate:
	curl -X POST http://localhost:8080/api/simulate \
		-H "Content-Type: application/json" \
		-d '{"num_events": 1000, "event_type": "random"}'

k8s-deploy:
	cd k8s && chmod +x deploy.sh && ./deploy.sh

k8s-status:
	kubectl get all -n analytics-platform

k8s-clean:
	kubectl delete namespace analytics-platform