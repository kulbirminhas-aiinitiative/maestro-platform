# Maestro Hive - Technical Documentation

**Version:** 3.1.0
**Last Updated:** December 2025
**Platform:** Autonomous SDLC Engine with AI Team Orchestration

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Module Reference](#3-module-reference)
4. [Core Components](#4-core-components)
5. [Enterprise Features](#5-enterprise-features)
6. [API Reference](#6-api-reference)
7. [Technology Stack](#7-technology-stack)
8. [Infrastructure](#8-infrastructure)
9. [Testing Framework](#9-testing-framework)
10. [Deployment Guide](#10-deployment-guide)

---

## 1. Executive Summary

### Overview

Maestro Hive is a production-ready autonomous SDLC (Software Development Lifecycle) engine that orchestrates AI-powered teams to deliver software solutions from requirements to deployment. The platform implements an 11-persona team model with sophisticated workflow management, learning capabilities, and enterprise-grade features.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Python Source Files** | 601 |
| **Lines of Code** | ~141,300 |
| **Major Modules** | 61 |
| **AI Personas** | 11 |
| **Enterprise Sub-modules** | 10 |
| **Test Categories** | 8+ |

### Core Capabilities

- **11 Specialized AI Personas** - Complete SDLC coverage
- **Phase-Based Workflow** - Requirements → Design → Implementation → Testing → Deployment
- **DAG Workflow Engine** - Complex task dependencies with parallel execution
- **RBAC Security** - Role-based access control with audit logging
- **Persistent State** - PostgreSQL + Redis for zero data loss
- **Event-Driven Architecture** - Real-time coordination via Kafka
- **Enterprise Features** - Multi-tenancy, OAuth2, CI/CD, resilience patterns

---

## 2. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MAESTRO HIVE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PRESENTATION LAYER                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │   │
│  │  │   CLI    │  │   API    │  │ Frontend │  │ JIRA Plugin  │    │   │
│  │  │(maestro) │  │(FastAPI) │  │ (React)  │  │              │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────▼───────────────────────────────┐   │
│  │                    ORCHESTRATION LAYER                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│  │  │   Unified    │  │     DAG      │  │   Team Execution     │  │   │
│  │  │ Orchestrator │  │   Executor   │  │     Engine v2        │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────▼───────────────────────────────┐   │
│  │                      DOMAIN LAYER                                │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │   │
│  │  │  Personas  │  │   Teams    │  │  Workflow  │  │   SDLC   │  │   │
│  │  │  (Skills,  │  │(Simulation,│  │ (Patterns, │  │ (Phases, │  │   │
│  │  │  Learning) │  │ Benchmark) │  │ Recovery)  │  │ Coords)  │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────▼───────────────────────────────┐   │
│  │                    ENTERPRISE LAYER                              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │   │
│  │  │  Auth   │ │  Ops    │ │ Release │ │Resilience│ │ Tenancy  │  │   │
│  │  │(OAuth2, │ │ (CI/CD, │ │  Mgmt   │ │(Circuit  │ │(Multi-   │  │   │
│  │  │  MFA)   │ │ Canary) │ │         │ │ Breaker) │ │ tenant)  │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────▼───────────────────────────────┐   │
│  │                   INFRASTRUCTURE LAYER                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │   │
│  │  │PostgreSQL│  │  Redis   │  │  Kafka   │  │    Neo4j     │    │   │
│  │  │(Primary) │  │ (Cache)  │  │ (Events) │  │   (Graph)    │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
maestro-hive/
├── src/maestro_hive/          # Main Python package (601 files, ~141K LOC)
│   ├── core/                  # Core orchestration and state management
│   ├── dag/                   # DAG workflow engine
│   ├── teams/                 # Team execution and simulation
│   ├── personas/              # Persona management and learning
│   ├── workflow/              # Workflow patterns and recovery
│   ├── enterprise/            # Enterprise features (10 sub-modules)
│   ├── observability/         # Logging, metrics, tracing
│   ├── compliance/            # Compliance framework
│   ├── qms_ops/               # Quality Management System
│   └── [50+ more modules]     # Specialized capabilities
├── tests/                     # Test suite (8+ categories)
├── frontend/                  # React/TypeScript UI
├── docs/                      # Documentation
├── config/                    # Configuration files
├── docker-compose.yml         # Infrastructure stack
├── pyproject.toml             # Poetry configuration
└── README.md                  # Main documentation
```

---

## 3. Module Reference

### Core Modules (Foundation)

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `core/` | Orchestration engine, state management | `orchestrator.py`, `state_manager.py`, `block_interface.py` |
| `dag/` | DAG workflow engine with parallel execution | `dag_executor.py`, `dag_workflow.py`, `dag_validator_service.py` |
| `workflow/` | Workflow patterns, recovery, validation | `standard_library.py`, `best_practices_enforcer.py`, `workflow_recovery_automation.py` |

### Team & Execution

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `teams/` | Team execution, simulation, benchmarking | `team_execution_v2.py`, `team_simulator.py`, `retrospective_engine.py` |
| `personas/` | Persona management, skills, learning | `skill_registry.py`, `learning_engine.py`, `evolution_tracker.py` |
| `sdlc/` | SDLC coordination and phases | `sdlc_coordinator.py` |
| `execution/` | Execution runtime | `execution_engine.py` |

### Enterprise (10 Sub-modules)

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `enterprise/auth/` | Authentication (OAuth2, MFA, API keys) | `oauth_manager.py`, `mfa_provider.py`, `token_manager.py` |
| `enterprise/operations/` | CI/CD, deployments, monitoring | `cicd_orchestrator.py`, `canary_deployment.py`, `rollback_manager.py` |
| `enterprise/jira_sync/` | JIRA integration | `jira_sync_engine.py`, `conflict_resolver.py` |
| `enterprise/release_management/` | Release orchestration | `branch_strategy.py`, `promotion_gates.py` |
| `enterprise/resilience/` | Fault tolerance patterns | `circuit_breaker.py`, `auto_scaler.py`, `rate_limiter.py` |
| `enterprise/tenancy/` | Multi-tenant support | `tenant_manager.py`, `feature_flags.py`, `isolation.py` |
| `enterprise/product_strategy/` | Roadmap and milestones | `roadmap_manager.py`, `milestone_tracker.py` |
| `enterprise/admin/` | System administration | `config_manager.py`, `migration_runner.py` |

### Knowledge & Learning

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `rag/` | Retrieval Augmented Generation | `rag_engine.py`, `document_store.py` |
| `knowledge/` | Knowledge embeddings | `embedding_generator.py`, `knowledge_store.py` |
| `learning_engine/` | ML-powered learning | `learning_engine.py` |

### Compliance & Governance

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `compliance/` | Compliance framework | `compliance_checker.py`, `audit_trail.py` |
| `gdpr/` | GDPR compliance | `data_subject_rights.py`, `consent_manager.py` |
| `eu_ai_act/` | EU AI Act compliance | `risk_assessment.py`, `transparency.py` |
| `qms_ops/` | Quality Management System | `audit/`, `capa/`, `monitoring/`, `policy/` |

### Observability

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `observability/` | Logging, metrics, tracing | `structured_logger.py`, `metrics_collector.py`, `tracer.py` |

---

## 4. Core Components

### 4.1 Unified Orchestrator

The central coordination point for all workflow execution.

```python
# Location: src/maestro_hive/core/orchestrator.py

class UnifiedOrchestrator:
    """
    Adapter pattern wrapping legacy EpicExecutor.
    Provides BlockInterface compliance.
    """

    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Execute an EPIC workflow.

        Required inputs:
            - epic_key: JIRA EPIC key (e.g., "MD-3021")
            - jira_url: JIRA instance URL
            - jira_token: API token
            - jira_email: User email

        Returns:
            BlockResult with status, output, metrics, errors
        """
```

### 4.2 DAG Workflow Engine

Manages complex task dependencies with parallel execution.

```python
# Location: src/maestro_hive/dag/dag_executor.py

class WorkflowExecutor:
    """
    Async parallel DAG execution with retry logic.
    """

    async def execute(self, dag: WorkflowDAG) -> ExecutionResult:
        """
        Execute workflow with:
        - Parallel node execution
        - Exponential backoff retry
        - State persistence
        - Automatic recovery
        """

# Location: src/maestro_hive/dag/dag_workflow.py

@dataclass
class WorkflowNode:
    """Individual task in the DAG."""
    node_id: str
    name: str
    task_type: str
    dependencies: List[str]
    config: Dict[str, Any]
    retry_policy: RetryPolicy

@dataclass
class WorkflowDAG:
    """Directed Acyclic Graph of tasks."""
    dag_id: str
    nodes: Dict[str, WorkflowNode]
    edges: List[Tuple[str, str]]
    context: WorkflowContext
```

### 4.3 Team Execution Engine

Orchestrates multi-persona collaboration.

```python
# Location: src/maestro_hive/teams/team_execution_v2.py

class TeamExecutionEngineV2:
    """
    Enhanced team execution with:
    - Multi-persona collaboration
    - JIRA task integration
    - Adaptive workflow execution
    - Performance tracking
    """

    async def execute(
        self,
        project: ProjectConfig,
        team_config: TeamConfig
    ) -> ExecutionResult:
        """Execute team workflow."""
```

### 4.4 Persona Learning Engine

Experience-based skill growth for AI personas.

```python
# Location: src/maestro_hive/personas/learning_engine.py

class LearningEngine:
    """
    ML-powered persona learning.

    Features:
    - Experience recording and accumulation
    - Skill level calculation
    - Growth rate tracking
    - Learning history management
    """

    def record_experience(self, experience: Experience) -> ExperienceResult:
        """Record and process a learning experience."""

    def get_skill_level(self, persona_id: str, skill_id: str) -> float:
        """Get current skill level (0.0 to 1.0)."""

    def calculate_growth_rate(self, persona_id: str, skill_id: str) -> float:
        """Calculate skill growth rate."""
```

### 4.5 Evolution Tracker

Tracks persona capability growth and milestones.

```python
# Location: src/maestro_hive/personas/evolution_tracker.py

class EvolutionTracker:
    """
    Tracks persona evolution with:
    - Milestone detection (mastery, expertise, growth spurts)
    - Evolution stages (nascent → developing → competent → proficient → expert)
    - Snapshot history
    - Growth velocity calculation
    """

    def record_skill_update(
        self,
        persona_id: str,
        skill_id: str,
        new_level: float,
        experience_count: int
    ) -> List[Milestone]:
        """Record skill update and detect milestones."""

    def get_evolution_summary(self, persona_id: str) -> Dict[str, Any]:
        """Get comprehensive evolution summary."""
```

---

## 5. Enterprise Features

### 5.1 Authentication (`enterprise/auth/`)

| Component | Purpose |
|-----------|---------|
| `OAuthManager` | OAuth2 provider integration |
| `MFAProvider` | Multi-factor authentication |
| `APIKeyManager` | API key generation and validation |
| `TokenManager` | JWT token management |
| `SessionManager` | Session lifecycle |

### 5.2 Operations (`enterprise/operations/`)

| Component | Purpose |
|-----------|---------|
| `CICDOrchestrator` | CI/CD pipeline management |
| `EnvironmentManager` | Environment provisioning |
| `CanaryDeployment` | Canary release strategy |
| `RollbackManager` | Deployment rollback |
| `MonitoringService` | Production monitoring |

### 5.3 Resilience (`enterprise/resilience/`)

| Pattern | Implementation |
|---------|---------------|
| Circuit Breaker | `CircuitBreaker` class with configurable thresholds |
| Auto Scaling | `AutoScaler` with resource-based scaling |
| Rate Limiting | `RateLimiter` with token bucket algorithm |
| Compensation | `CompensationManager` for saga pattern |

### 5.4 Multi-Tenancy (`enterprise/tenancy/`)

| Component | Purpose |
|-----------|---------|
| `TenantManager` | Tenant lifecycle management |
| `FeatureFlags` | Feature flag management |
| `IsolationManager` | Data isolation enforcement |
| `TenantContext` | Request-scoped tenant context |

---

## 6. API Reference

### Primary Entry Points

#### 1. CLI Entry Point
```bash
# SDLC Team execution
python -m maestro_hive.cli.main execute --epic MD-3021

# Workflow execution
python -m maestro_hive.dag.dag_executor --workflow workflow.yaml
```

#### 2. Python API
```python
from maestro_hive.core.orchestrator import UnifiedOrchestrator
from maestro_hive.dag.dag_executor import WorkflowExecutor
from maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2

# Execute EPIC
orchestrator = UnifiedOrchestrator()
result = orchestrator.execute({
    "epic_key": "MD-3021",
    "jira_url": "https://your-jira.atlassian.net",
    "jira_token": "your-token",
    "jira_email": "your-email"
})

# Execute DAG workflow
executor = WorkflowExecutor()
result = await executor.execute(workflow_dag)

# Execute team workflow
engine = TeamExecutionEngineV2()
result = await engine.execute(project_config, team_config)
```

### Key Data Models

```python
# Block Interface
@dataclass
class BlockResult:
    status: BlockStatus  # SUCCESS, FAILURE, PARTIAL, SKIPPED
    output: Dict[str, Any]
    metrics: Dict[str, float]
    errors: List[str]
    duration_ms: float

# Workflow
@dataclass
class WorkflowContext:
    workflow_id: str
    variables: Dict[str, Any]
    state: WorkflowState
    metadata: Dict[str, Any]

# Experience
@dataclass
class Experience:
    experience_id: str
    persona_id: str
    skill_id: str
    experience_type: ExperienceType
    outcome: LearningOutcome
    outcome_score: float
    context: Dict[str, Any]
    duration_seconds: float
    difficulty_level: float
```

---

## 7. Technology Stack

### Core Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Primary language |
| **HTTP Client** | httpx | 0.28.1+ | Async HTTP |
| **LLM SDK** | Anthropic | 0.40.0+ | Claude API |
| **Validation** | Pydantic | 2.11.10+ | Data validation |

### Observability Stack (MD-1901)

| Technology | Version | Purpose |
|------------|---------|---------|
| structlog | 25.4.0+ | Structured logging |
| prometheus-client | 0.23.1+ | Metrics collection |
| opentelemetry-api | 1.37.0+ | Distributed tracing |
| opentelemetry-sdk | 1.37.0+ | Tracing implementation |
| psutil | 7.1.0+ | System metrics |

### Development Tools

| Tool | Purpose |
|------|---------|
| black | Code formatting (100 char lines) |
| isort | Import sorting |
| flake8 | Linting |
| mypy | Static type checking |
| bandit | Security scanning |
| ruff | Fast linting |
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage reporting |

---

## 8. Infrastructure

### Docker Compose Stack

```yaml
services:
  # Event Streaming
  kafka:           # Confluent 7.5.0
  zookeeper:       # Confluent 7.5.0
  schema-registry: # Confluent 7.5.0

  # Databases
  postgresql:      # Latest - Primary relational data
  neo4j:           # 5.13 Enterprise - Graph database
  redis:           # Latest - Caching, sessions, pub/sub
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Kafka | 9092 | Event streaming |
| Zookeeper | 2181 | Kafka coordination |
| Schema Registry | 8081 | Schema management |
| PostgreSQL | 5432 | Primary database |
| Neo4j | 7474, 7687 | Graph database |
| Redis | 6379 | Cache |

### Environment Configuration

```bash
# Required Environment Variables
ANTHROPIC_API_KEY=your-api-key
JIRA_URL=https://your-jira.atlassian.net
JIRA_TOKEN=your-jira-token
JIRA_EMAIL=your-email

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/maestro
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
```

---

## 9. Testing Framework

### Test Structure

```
tests/
├── integration/           # Integration tests
├── contracts/             # Contract testing
├── e2e_validation/        # End-to-end tests
├── dde/                   # Dual Distributed Execution
│   ├── unit/
│   ├── integration/
│   ├── chaos/             # Chaos engineering
│   └── property/          # Property-based testing
├── bdv/                   # Business Decision Validation
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── security/
├── acc/                   # Algorithmic Confidence Checking
├── tri_audit/             # Tri-modal audit tests
├── personas/              # Persona tests
├── teams/                 # Team tests
└── fixtures/              # Shared fixtures
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/personas/ -v

# With coverage
pytest tests/ --cov=src/maestro_hive --cov-report=html

# Async tests
pytest tests/ -v --asyncio-mode=auto
```

### Test Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

---

## 10. Deployment Guide

### Prerequisites

```bash
# Python 3.11+
python --version  # Should be 3.11+

# Poetry
pip install poetry

# Docker & Docker Compose
docker --version
docker-compose --version
```

### Installation

```bash
# Clone repository
git clone <repo-url>
cd maestro-hive

# Install dependencies
poetry install

# Start infrastructure
docker-compose up -d

# Verify services
docker-compose ps
```

### Configuration

```bash
# Copy example environment
cp .env.example .env

# Edit configuration
vim .env
```

### Running

```bash
# Development mode
poetry run python -m maestro_hive.cli.main

# Production mode
poetry run gunicorn maestro_hive.api:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Health Checks

```bash
# Check Kafka
kafka-broker-api-versions --bootstrap-server localhost:9092

# Check PostgreSQL
psql -h localhost -U maestro -c "SELECT 1"

# Check Redis
redis-cli ping

# Check Neo4j
curl http://localhost:7474
```

---

## Appendix A: 11-Persona SDLC Team

| Phase | Persona | Role | Tools |
|-------|---------|------|-------|
| **Requirements** | Requirements Analyst | `analyst` | 15 |
| **Requirements** | UI/UX Designer | `designer` | 12 |
| **Design** | Solution Architect | `architect` | 18 |
| **Implementation** | Frontend Developer | `developer` | 15 |
| **Implementation** | Backend Developer | `developer` | 15 |
| **Implementation** | DevOps Engineer | `devops` | 16 |
| **Testing** | QA Engineer | `tester` | 14 |
| **Testing** | Security Specialist | `security` | 17 |
| **Deployment** | Deployment Specialist | `deployer` | 14 |
| **Deployment** | Integration Tester | `tester` | 13 |
| **Cross-cutting** | Technical Writer | `writer` | 11 |

---

## Appendix B: Active EPICs Reference

| EPIC | Title | Status |
|------|-------|--------|
| MD-3021 | Persona Evolution & Learning | Done |
| MD-3015 | Autonomous Team Retrospective | In Progress |
| MD-3019 | Team Simulation & Benchmarking | In Progress |
| MD-2961 | Workflow Optimization | In Progress |
| MD-1901 | Observability Infrastructure | In Progress |
| MD-2505 | Block Architecture | In Progress |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | EPIC Compliance Processor | Initial technical documentation |

