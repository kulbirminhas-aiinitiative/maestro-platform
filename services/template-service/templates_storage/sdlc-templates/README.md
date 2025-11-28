# Comprehensive SDLC Templates Collection

A complete set of production-ready templates covering all phases of the Software Development Life Cycle (SDLC), designed to enable AI agents and development teams to rapidly build, deploy, and maintain robust systems using industry best practices.

## 📋 Overview

This collection contains **60+ templates** organized across 5 major SDLC phases, each following industry-leading methodologies, frameworks, and tools identified through extensive research in 2024-2025.

### Template Categories

| Phase | Templates | Focus Area |
|-------|-----------|------------|
| **[Phase 1: Planning & Requirements](#phase-1-planning--requirements)** | 12 | Project management, requirements, architecture design, API specs |
| **[Phase 2: Backend Development](#phase-2-backend-development)** | 18 | Frameworks, architectures, databases, authentication |
| **[Phase 3: Testing & QA](#phase-3-testing--qa)** | 12 | E2E, unit, integration, performance testing |
| **[Phase 4: DevOps/CI/CD](#phase-4-devops-cicd)** | 15 | CI/CD pipelines, containers, IaC, GitOps |
| **[Phase 5: Operations & Monitoring](#phase-5-operations--monitoring)** | 13 | Observability, logging, error tracking, incidents |

---

## 🎯 Quick Start

### Prerequisites

- MAESTRO Templates System installed
- Access to the template registry
- Appropriate development tools for your stack

### Using Templates

```bash
# List all SDLC templates
maestro-template list --category=sdlc

# Search for specific templates
maestro-template search --query="microservices"

# Create a project from a template
maestro-template init --template=nestjs-clean-architecture

# Validate a template
maestro-template validate /path/to/template
```

### Via API

```bash
# Get templates by phase
curl http://localhost:9600/api/v1/templates?sdlc_phase=backend

# Get a specific template
curl http://localhost:9600/api/v1/templates/{template-id}
```

---

## 📚 Phase 1: Planning & Requirements

Templates for defining scope, gathering requirements, designing architecture, and specifying interfaces.

### Project Management (3 templates)

| Template | Description | Best For |
|----------|-------------|----------|
| **scrum-sprint-template** | Complete Scrum framework with ceremonies | Agile teams, 2-week sprints |
| **kanban-board** | Continuous flow workflow management | Support teams, continuous delivery |
| **shape-up-cycle** | Basecamp's 6-week shaping methodology | Product teams, focused cycles |

### Requirements Documentation (3 templates)

| Template | Description | Best For |
|----------|-------------|----------|
| **prd-template** | Product Requirements Document (Product School style) | Feature definition, stakeholder alignment |
| **bdd-gherkin-user-stories** | Behavior-Driven Development with Given/When/Then | Executable specifications, testing |
| **user-story-mapping** | Journey mapping and prioritization | Product discovery, backlog refinement |

### Architecture Design (3 templates)

| Template | Description | Best For |
|----------|-------------|----------|
| **adr-template** | Architecture Decision Records (MADR format) | Decision tracking, governance |
| **c4-model-diagrams** | Context, Container, Component, Code diagrams | Architecture visualization |
| **system-architecture** | High-level system design document | Technical architecture, patterns |

### API Specification (3 templates)

| Template | Description | Best For |
|----------|-------------|----------|
| **openapi-spec** | OpenAPI 3.1 for REST APIs | API-first development, documentation |
| **graphql-schema** | GraphQL SDL with queries/mutations | Flexible data fetching |
| **grpc-protobuf** | gRPC service definitions | High-performance RPC |

---

## 💻 Phase 2: Backend Development

Templates for implementing business logic, managing databases, and ensuring code quality.

### Node.js/TypeScript (3 templates)

| Template | Description | Key Features |
|----------|-------------|--------------|
| **nestjs-clean-architecture** | Enterprise microservices with CQRS, Event Sourcing | Clean Architecture, DDD, CQRS |
| **nestjs-modular-monolith** | Modular monolith with Prisma | Bounded contexts, scalability |
| **express-prisma-typescript** | Express + Prisma with SOLID principles | TDD, Repository pattern |

### Python (3 templates)

| Template | Description | Key Features |
|----------|-------------|--------------|
| **fastapi-production** | Async FastAPI with SQLAlchemy 2.0, Pydantic V2 | High performance, type-safe |
| **fastapi-microservices** | Microservices with message queues | Event-driven, scalable |
| **django-rest-production** | Django REST Framework with Docker, CI/CD | Batteries-included, robust |

### Java/Spring (2 templates)

| Template | Description | Key Features |
|----------|-------------|--------------|
| **spring-boot-microservices** | Spring Cloud with Eureka, Config Server | Enterprise-grade, resilient |
| **spring-boot-modular-monolith** | Modular architecture with DDD | Clean separation, maintainable |

### Architecture Patterns (3 templates)

| Template | Description | When to Use |
|----------|-------------|-------------|
| **microservices-reference** | Complete microservices architecture | Large-scale, team autonomy |
| **modular-monolith-dotnet** | .NET 8 modular monolith with DDD | Start simple, scale later |
| **aws-lambda-sam** | Serverless with AWS SAM | Event-driven, pay-per-use |

### Database & Auth (4 templates)

| Template | Description | Technology |
|----------|-------------|------------|
| **prisma-schema-patterns** | Database schemas with Prisma | PostgreSQL, MySQL, MongoDB |
| **sqlalchemy-patterns** | Python ORM patterns | Repository, async queries |
| **oauth2-oidc-auth0** | OAuth 2.0 + OIDC with Auth0 | SSO, RBAC |
| **keycloak-integration** | Open-source IAM | Self-hosted auth |
| **jwt-authentication** | JWT token management | Stateless auth |

---

## 🧪 Phase 3: Testing & QA

Templates for ensuring software quality, performance, and reliability.

### End-to-End Testing (3 templates)

| Template | Description | Features |
|----------|-------------|----------|
| **playwright-e2e-suite** | Modern E2E testing with Playwright | Cross-browser, parallel, visual regression |
| **playwright-component-testing** | Component tests with Playwright | React/Vue components |
| **cypress-e2e-framework** | Cypress with best practices | Developer-friendly, real-time |

### Unit & Integration (3 templates)

| Template | Description | Framework |
|----------|-------------|-----------|
| **jest-react-testing** | Jest + React Testing Library | Component tests, hooks |
| **pytest-framework** | Python testing with pytest | Fixtures, async, coverage |
| **junit5-mockito** | Java testing suite | Unit + integration tests |

### API & Performance (4 templates)

| Template | Description | Use Case |
|----------|-------------|----------|
| **postman-newman-collection** | API test automation | CI/CD integration |
| **rest-assured-api** | Java API testing with BDD | Readable API tests |
| **k6-load-testing** | Modern load testing | Smoke, load, stress, spike |
| **k6-grafana-dashboard** | Real-time metrics visualization | Performance monitoring |
| **jmeter-test-plans** | Traditional load testing | Distributed testing |

### Strategy (1 template)

| Template | Description | Guidance |
|----------|-------------|----------|
| **testing-pyramid-strategy** | Test distribution strategy | Unit > Integration > E2E |

---

## 🚀 Phase 4: DevOps/CI/CD

Templates for automating build, test, and deployment processes.

### CI/CD Pipelines (4 templates)

| Template | Description | Platform |
|----------|-------------|----------|
| **github-actions-nodejs** | Node.js CI/CD pipeline | Lint, test, build, deploy |
| **github-actions-python** | Python with Poetry, pytest | Coverage, deployment |
| **github-actions-java** | Maven/Gradle builds | Docker, multi-stage |
| **github-actions-monorepo** | Nx/Turborepo selective builds | Matrix strategy |

### Containerization (3 templates)

| Template | Description | Optimization |
|----------|-------------|--------------|
| **dockerfile-nodejs-multistage** | Optimized Node.js builds | Security, size |
| **dockerfile-python-poetry** | Python with Poetry | Alpine, non-root |
| **docker-compose-dev** | Local development environment | DB, Redis, services |

### Kubernetes & Orchestration (3 templates)

| Template | Description | Features |
|----------|-------------|----------|
| **helm-chart-template** | Production Helm charts | ConfigMaps, Secrets, HPA |
| **kubernetes-manifests** | Raw K8s manifests | Deployments, services, ingress |
| **kustomize-overlays** | Environment-specific patches | Base + overlays |

### Infrastructure as Code (3 templates)

| Template | Description | Provider |
|----------|-------------|----------|
| **terraform-aws-modules** | AWS infrastructure modules | VPC, EKS, RDS, S3 |
| **terraform-multi-cloud** | Multi-cloud IaC | Provider abstraction |
| **aws-cdk-typescript** | AWS CDK in TypeScript | Programmatic IaC |

### GitOps (2 templates)

| Template | Description | Tool |
|----------|-------------|------|
| **argocd-applications** | ArgoCD app manifests | App-of-apps pattern |
| **flux-gitops** | Flux CD configuration | Kustomization, Helm |

---

## 📊 Phase 5: Operations & Monitoring

Templates for production observability, error tracking, and incident management.

### Observability - Metrics (3 templates)

| Template | Description | Components |
|----------|-------------|------------|
| **prometheus-config** | Prometheus scrape configuration | Service discovery, alerts |
| **grafana-dashboards-2024** | Pre-built dashboards | System, app metrics |
| **prometheus-exporters** | Custom exporter templates | Node, blackbox, custom |

### Observability - Tracing (3 templates)

| Template | Description | Language |
|----------|-------------|----------|
| **opentelemetry-nodejs** | OTel instrumentation for Node.js | Auto + manual |
| **opentelemetry-python** | OTel for FastAPI/Django | Traces, metrics, logs |
| **otel-collector-config** | Collector pipelines | Processors, exporters |

### Logging (3 templates)

| Template | Description | Stack |
|----------|-------------|-------|
| **elk-stack-docker** | Elasticsearch, Logstash, Kibana | Complete logging |
| **logstash-pipelines** | Log processing pipelines | Grok patterns, filters |
| **fluentd-config** | Multi-source log aggregation | Lightweight alternative |

### Error Tracking & Incidents (4 templates)

| Template | Description | Platform |
|----------|-------------|----------|
| **sentry-react-integration** | Frontend error tracking | Source maps, releases |
| **sentry-backend-integration** | Backend error tracking | Node.js, Python |
| **blameless-postmortem** | Google SRE postmortem template | Root cause, action items |
| **incident-response-runbook** | Incident management playbook | Detection, triage, escalation |

---

## 🎨 Template Features

All templates include:

✅ **Production-Ready** - Battle-tested patterns and industry best practices
✅ **manifest.yaml** - Complete metadata, placeholders, dependencies, hooks
✅ **Documentation** - README, quickstart guides, API docs, examples
✅ **Best Practices** - Security, performance, scalability, maintainability
✅ **Examples** - Real-world usage scenarios and implementations
✅ **Testing** - Comprehensive test strategies and examples
✅ **CI/CD Ready** - Integration with popular CI/CD platforms
✅ **Observability** - Metrics, logs, traces, health checks

## 🏆 Quality Tiers

Templates are categorized by production readiness:

- **Gold** ⭐⭐⭐ - Industry-leading, extensively tested (NestJS, FastAPI, Playwright, K6, Terraform)
- **Silver** ⭐⭐ - High-quality, well-maintained (Most templates)
- **Bronze** ⭐ - Good starting points, may need customization
- **Standard** - Basic templates for rapid prototyping

## 🔧 Integration with AI Agents

AI agents can leverage these templates by:

1. **Requirement Analysis** - Parse user needs to identify appropriate templates
2. **Template Selection** - Match requirements to SDLC phase and technology stack
3. **Customization** - Use placeholders to configure the template
4. **Generation** - Scaffold the project with selected options
5. **Post-Processing** - Run hooks for installation and validation

## 📖 Best Practices

### Selecting Templates

1. **Match SDLC Phase** - Choose templates for your current development phase
2. **Technology Stack** - Ensure compatibility with your tech stack
3. **Architecture Pattern** - Select appropriate architectural style
4. **Team Size & Complexity** - Consider team size and project complexity
5. **Future Scalability** - Plan for growth and evolution

### Using Templates

1. **Read Documentation** - Review README and quickstart guides
2. **Configure Placeholders** - Set appropriate values for your project
3. **Review Examples** - Study provided examples
4. **Customize as Needed** - Adapt to your specific requirements
5. **Follow Hooks** - Execute post-generation commands

## 🤝 Contributing

To add a new SDLC template:

1. Create template directory under appropriate phase
2. Add `manifest.yaml` following the schema
3. Include comprehensive `README.md`
4. Provide `docs/` and `examples/`
5. Validate with `maestro-template validate`
6. Register with central registry

## 📚 Additional Resources

- **Frontend Templates** - See `/storage/templates/frontend-templates/`
- **Documentation Templates** - See `/documentation_templates/`
- **Project Registry** - See `/config/project-registry.yaml`
- **Template Lifecycle** - See `/docs/TEMPLATE_LIFECYCLE_STRATEGY.md`

## 📜 License

All templates are released under the MIT License unless otherwise specified.

## 🆘 Support

For issues or questions:
- Check individual template documentation
- Review phase-specific README files
- Open an issue in the project repository
- Consult MAESTRO Templates documentation

---

**Version**: 1.0.0
**Last Updated**: 2025-10-04
**Total Templates**: 60+
**Coverage**: Complete SDLC (Planning → Operations)
