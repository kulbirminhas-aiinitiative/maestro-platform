# Phase 2: Backend Development Templates

Production-ready backend templates covering modern frameworks, architecture patterns, databases, and authentication across multiple programming languages and paradigms.

## 📚 Overview

This phase contains **18 comprehensive templates** for backend development, organized by technology stack and architectural pattern.

| Category | Templates | Technologies |
|----------|-----------|--------------|
| **Node.js/TypeScript** | 3 | NestJS, Express, Prisma |
| **Python** | 3 | FastAPI, Django REST |
| **Java/Spring** | 2 | Spring Boot, Spring Cloud |
| **Architecture** | 3 | Microservices, Modular Monolith, Serverless |
| **Database & Auth** | 7 | Prisma, SQLAlchemy, OAuth2, JWT |

---

## 🎯 Template Selection Guide

### By Use Case

**Building Enterprise Microservices?**
- ✅ `nestjs-clean-architecture` - TypeScript/Node.js with CQRS
- ✅ `spring-boot-microservices` - Java with Spring Cloud
- ✅ `fastapi-microservices` - Python async with message queues

**Starting a New Product?**
- ✅ `nestjs-modular-monolith` - Start simple, scale later
- ✅ `modular-monolith-dotnet` - .NET 8 with DDD
- ✅ `fastapi-production` - Fast Python APIs

**Building Event-Driven Systems?**
- ✅ `aws-lambda-sam` - Serverless with AWS
- ✅ `nestjs-clean-architecture` - Event Sourcing support

**Need High Performance?**
- ✅ `fastapi-production` - Async Python, 10x faster than Django
- ✅ `nestjs-clean-architecture` - Non-blocking I/O
- ✅ `spring-boot-microservices` - JVM optimization

### By Team Size

**Small Team (1-5 developers)**
- Modular Monolith templates
- Express + Prisma (simple, fast)
- Django REST (batteries included)

**Medium Team (5-15 developers)**
- NestJS with modules
- FastAPI microservices
- Spring Boot with clear boundaries

**Large Team (15+ developers)**
- Microservices architectures
- NestJS Clean Architecture
- Spring Boot Microservices

---

## 🚀 Node.js/TypeScript Templates

### 1. NestJS Clean Architecture (`nestjs-clean-architecture`)

**Best For**: Enterprise microservices, complex domains, high scalability

**Key Features**:
- Clean Architecture layers (Domain, Application, Infrastructure, Presentation)
- CQRS with commands and queries separation
- Event Sourcing for complete audit trail
- Domain-Driven Design tactical patterns
- Repository pattern with Prisma ORM
- Comprehensive testing (unit, integration, e2e)

**Tech Stack**: NestJS 10, TypeScript 5, Prisma 5, Docker

**Quick Start**:
```bash
maestro-template init --template=nestjs-clean-architecture
cd my-service
npm install
npm run dev
```

**Use Cases**: Financial systems, enterprise SaaS, event-driven architectures

---

### 2. NestJS Modular Monolith (`nestjs-modular-monolith`)

**Best For**: Startups, MVPs, growing applications

**Key Features**:
- Modular architecture with bounded contexts
- Prisma for type-safe database access
- JWT authentication and RBAC
- GraphQL and REST APIs
- Easy migration path to microservices

**Tech Stack**: NestJS 10, Prisma 5, PostgreSQL, Docker

**Quick Start**:
```bash
maestro-template init --template=nestjs-modular-monolith
npm install
npm run start:dev
```

**Use Cases**: SaaS applications, e-commerce platforms, internal tools

---

### 3. Express + Prisma + TypeScript (`express-prisma-typescript`)

**Best For**: Simple APIs, rapid prototyping, small services

**Key Features**:
- SOLID principles and clean code
- TDD with Jest and Supertest
- Repository pattern
- Express middleware pipeline
- Prisma for database operations

**Tech Stack**: Express 4, Prisma 5, TypeScript 5

**Quick Start**:
```bash
maestro-template init --template=express-prisma-typescript
npm install
npm test
npm start
```

**Use Cases**: REST APIs, backend-for-frontend, simple CRUD services

---

## 🐍 Python Templates

### 4. FastAPI Production Boilerplate (`fastapi-production`)

**Best For**: High-performance APIs, data science backends, async workloads

**Key Features**:
- Async/await throughout the stack
- SQLAlchemy 2.0 with async support
- Pydantic V2 for validation
- Alembic database migrations
- Poetry for dependency management
- Automatic OpenAPI documentation

**Tech Stack**: FastAPI 0.109, SQLAlchemy 2.0, Pydantic V2, PostgreSQL

**Quick Start**:
```bash
maestro-template init --template=fastapi-production
poetry install
alembic upgrade head
uvicorn app.main:app --reload
```

**Use Cases**: Real-time APIs, ML model serving, data platforms

---

### 5. FastAPI Microservices (`fastapi-microservices`)

**Best For**: Distributed systems, event-driven architectures

**Key Features**:
- Service discovery integration
- RabbitMQ/Kafka message broker
- Distributed tracing
- Circuit breakers
- API Gateway ready

**Tech Stack**: FastAPI, Celery, RabbitMQ, Redis, Docker

**Use Cases**: Large-scale distributed systems, event-driven platforms

---

### 6. Django REST Framework Production (`django-rest-production`)

**Best For**: Content-heavy apps, admin-heavy applications

**Key Features**:
- Django ORM with migrations
- Django Admin for backoffice
- Comprehensive auth system
- REST framework with serializers
- Docker + docker-compose
- CI/CD with GitHub Actions

**Tech Stack**: Django 5, DRF 3.14, PostgreSQL, Celery, Redis

**Use Cases**: CMS platforms, e-commerce, enterprise applications

---

## ☕ Java/Spring Templates

### 7. Spring Boot Microservices (`spring-boot-microservices`)

**Best For**: Enterprise Java applications, large organizations

**Key Features**:
- Spring Cloud for microservices infrastructure
- Eureka service discovery
- Config Server for centralized configuration
- Resilience4j circuit breakers
- Actuator for health checks
- Micrometer + Prometheus metrics

**Tech Stack**: Spring Boot 3.2, Spring Cloud, Java 17/21, Maven

**Quick Start**:
```bash
maestro-template init --template=spring-boot-microservices
./mvnw spring-boot:run
```

**Use Cases**: Enterprise systems, banking, insurance, large-scale platforms

---

### 8. Spring Boot Modular Monolith (`spring-boot-modular-monolith`)

**Best For**: Enterprise applications starting with monolith

**Key Features**:
- Modular architecture with clear boundaries
- Domain-Driven Design
- Module independence
- JPA with separate schemas per module
- Event-driven communication between modules

**Tech Stack**: Spring Boot 3.2, Spring Data JPA, Java 17

**Use Cases**: Enterprise apps planning for future scalability

---

## 🏗️ Architecture Pattern Templates

### 9. Microservices Reference Architecture (`microservices-reference`)

Complete blueprint for microservices with API Gateway, service discovery, configuration management, and observability.

### 10. Modular Monolith (.NET 8) (`modular-monolith-dotnet`)

.NET 8 modular monolith with Clean Architecture, vertical slices, and DDD patterns.

### 11. AWS Lambda Serverless (`aws-lambda-sam`)

Serverless template with AWS SAM for event-driven, pay-per-use applications.

---

## 🗄️ Database & ORM Templates

### 12. Prisma Schema Patterns (`prisma-schema-patterns`)

**Features**: Multi-schema setup, migrations, relationships, indexing strategies

### 13. SQLAlchemy Patterns (`sqlalchemy-patterns`)

**Features**: Repository pattern, async queries, complex relationships, migrations

---

## 🔐 Authentication & Authorization Templates

### 14. OAuth 2.0 + OIDC with Auth0 (`oauth2-oidc-auth0`)

**Features**: SSO, Social login, RBAC, MFA, JWT tokens

### 15. Keycloak Integration (`keycloak-integration`)

**Features**: Self-hosted IAM, realm management, user federation

### 16. JWT Authentication (`jwt-authentication`)

**Features**: Token generation, refresh tokens, validation, blacklisting

---

## 🎯 Choosing the Right Template

### Decision Tree

```
Need authentication?
├─ Yes → oauth2-oidc-auth0 OR keycloak-integration
└─ No → Continue

Team familiar with TypeScript?
├─ Yes → NestJS templates
└─ No → Continue

Need high performance?
├─ Yes → fastapi-production
└─ No → Continue

Large team/complex domain?
├─ Yes → Clean Architecture patterns
└─ No → Express/Django simple templates

Planning to scale to microservices?
├─ Yes → Modular Monolith
└─ No → Traditional monolith
```

---

## 📖 Template Structure

Each template includes:

```
template-name/
├── manifest.yaml           # Template metadata
├── README.md              # Overview and quickstart
├── docs/
│   ├── QUICKSTART.md     # Getting started guide
│   ├── API.md            # API documentation
│   ├── ARCHITECTURE.md   # Architecture decisions
│   └── DEPLOYMENT.md     # Deployment guide
├── examples/
│   ├── basic/            # Basic usage examples
│   ├── advanced/         # Advanced patterns
│   └── production/       # Production configurations
└── templates/
    ├── src/              # Source code templates
    ├── tests/            # Test templates
    └── docker/           # Docker configurations
```

---

## 🚀 Getting Started

1. **Choose a template** based on your requirements
2. **Initialize the project** using MAESTRO CLI
3. **Configure placeholders** for your specific needs
4. **Review the documentation** in the `docs/` folder
5. **Run the post-generation hooks** to set up dependencies
6. **Start developing!**

---

## 💡 Best Practices

### General Guidelines

- Start with modular monolith unless you have specific microservices needs
- Use TypeScript for better type safety and developer experience
- Implement proper error handling and validation from day one
- Set up observability (metrics, logs, traces) early
- Write tests alongside your code (TDD where appropriate)
- Use environment variables for configuration
- Implement health checks for all services
- Follow the principle of least privilege for security

### Architecture Guidelines

- Keep business logic separate from framework code
- Use repository pattern for data access abstraction
- Implement proper layering (presentation, application, domain, infrastructure)
- Use dependency injection for loose coupling
- Follow SOLID principles
- Design for testability

---

## 📚 Additional Resources

- [MAESTRO Templates Documentation](/docs/)
- [Backend Best Practices Guide](/docs/BACKEND_BEST_PRACTICES.md)
- [API Design Guidelines](/docs/API_DESIGN_GUIDE.md)
- [Security Checklist](/docs/SECURITY_CHECKLIST.md)

---

**Phase**: 2 of 5
**Templates**: 18
**Last Updated**: 2025-10-04
