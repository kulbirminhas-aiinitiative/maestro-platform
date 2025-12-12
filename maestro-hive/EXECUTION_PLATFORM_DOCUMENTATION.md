# Maestro-Hive Execution Platform - Technical Documentation

**Version**: 3.1.0
**Type**: Autonomous SDLC Engine with AI Team Orchestration
**Location**: `/home/ec2-user/projects/maestro-platform/maestro-hive`
**Total Lines**: 217,207 Python

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technology Stack](#2-technology-stack)
3. [Directory Structure](#3-directory-structure)
4. [Core Architecture](#4-core-architecture)
5. [Data Models](#5-data-models)
6. [Key Components](#6-key-components)
7. [Configuration](#7-configuration)
8. [Testing](#8-testing)
9. [Dependencies & Integrations](#9-dependencies--integrations)
10. [Key EPICs & Features](#10-key-epics--features)
11. [Deployment & Operations](#11-deployment--operations)

---

## 1. Executive Summary

**Maestro-Hive** is an enterprise-grade Autonomous SDLC Engine that enables:

- **Multi-Agent SDLC System**: 11 specialized AI personas collaborating autonomously
- **Distributed Workflow Engine**: DAG-based task orchestration with parallel execution
- **Resilient Execution Environment**: Circuit breakers, auto-scaling, recovery mechanisms
- **Deep Observability**: Span-based distributed tracing (OpenTelemetry)
- **Persona-Level Intelligent Reuse**: V4.1 artifact reuse analysis
- **Secure Sandboxing**: Isolated code execution with resource limits
- **Enterprise Integration**: Jira, Confluence, GitHub with compliance (GDPR, EU AI Act)

### Code Statistics

| Metric | Value |
|--------|-------|
| Total Lines | 217,207 |
| Major Modules | 62 |
| Documentation Files | 50+ |
| Test Coverage | 300+ tests |

---

## 2. Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core runtime |
| FastAPI | Latest | DAG API server |
| Anthropic | 0.40.0+ | Claude API |
| Pydantic | 2.11.10+ | Data validation |
| OpenTelemetry | 1.37.0 | Observability |
| Structlog | 25.4.0 | Logging |
| Prometheus | 0.23.1 | Metrics |

### Data Storage

| Technology | Purpose |
|------------|---------|
| PostgreSQL | Persistent state |
| Redis | Caching, pub-sub |
| SQLite | Fallback (dev) |

### Async/Concurrency

- asyncio
- ThreadPoolExecutor
- aiohttp/httpx

---

## 3. Directory Structure

```
maestro-hive/
├── src/maestro_hive/                    # Main source (62 modules, 217K lines)
│   │
│   ├── execution/                       # [MD-3013] Resilient execution
│   │   ├── task_queue.py               # Distributed task scheduling
│   │   ├── agent_tracer.py             # Span-based observability (547 LOC)
│   │   ├── sandbox_manager.py          # Secure code execution
│   │   └── trace_viewer.py             # Execution visualization
│   │
│   ├── agent_runtime/                   # [AC-2544] Agent lifecycle
│   │   ├── engine.py                   # Main runtime orchestration
│   │   ├── executor.py                 # Task execution
│   │   ├── lifecycle.py                # Session management
│   │   ├── context_manager.py          # Context persistence
│   │   └── models.py                   # AgentState, AgentSession
│   │
│   ├── runtime/                         # [MD-2544] Execution tracking
│   │   └── tracking/
│   │       ├── tracker.py              # ExecutionTracker
│   │       ├── stream.py               # Real-time streaming
│   │       ├── query.py                # Execution history
│   │       └── models.py               # TrackedExecution, TraceContext
│   │
│   ├── teams/                           # [MD-3015, MD-3019, MD-3020] Teams
│   │   ├── team_execution.py           # V3.1 Resumable (2,802 LOC)
│   │   ├── team_execution_v2.py        # V2 patterns (1,795 LOC)
│   │   ├── retrospective_engine.py     # Team retrospectives
│   │   ├── evaluator_persona.py        # Performance evaluation
│   │   ├── process_improver.py         # Workflow optimization
│   │   ├── team_simulator.py           # Scenario simulation
│   │   ├── benchmark_runner.py         # Performance benchmarking
│   │   ├── team_evolver.py             # Team evolution
│   │   └── performance_optimizer.py    # Performance tuning
│   │
│   ├── dag/                             # DAG workflow execution
│   │   ├── dag_executor.py             # Core executor (531 LOC)
│   │   ├── dag_workflow.py             # WorkflowDAG definition
│   │   ├── dag_api_server_robust.py    # REST/WebSocket API
│   │   └── dag_validation_nodes.py     # Phase validation
│   │
│   ├── core/                            # Core engines
│   │   ├── team_execution.py           # Legacy team execution
│   │   ├── team_organization.py        # Team structure (40K+ LOC)
│   │   └── self_reflection/
│   │       ├── refactoring_engine.py   # Code refactoring
│   │       └── self_healing_engine.py  # Self-healing workflows
│   │
│   ├── enterprise/                      # Enterprise features
│   │   ├── resilience/                 # Fault tolerance
│   │   │   ├── circuit_breaker.py      # Circuit breaking
│   │   │   ├── rate_limiter.py         # Rate limiting
│   │   │   ├── compensation.py         # Compensation transactions
│   │   │   ├── auto_scaler.py          # Elastic scaling
│   │   │   └── transaction.py          # Transaction management
│   │   ├── operations/                 # Deployment & monitoring
│   │   │   ├── canary/                 # Canary deployments
│   │   │   ├── cicd/                   # CI/CD integration
│   │   │   ├── monitoring/             # Health & metrics
│   │   │   └── rollback/               # Rollback automation
│   │   ├── jira_sync/                  # Jira integration
│   │   └── auth/                       # Authentication/RBAC
│   │
│   ├── personas/                        # [MD-2812] AI personas
│   │   ├── skill_registry.py           # Persona skills
│   │   ├── skill_injector.py           # Dynamic injection
│   │   ├── trait_manager.py            # Persona traits
│   │   └── evolution_guide.py          # Persona evolution
│   │
│   ├── persona_engine/                  # Persona management
│   │   ├── engine.py                   # Core engine
│   │   ├── models.py                   # Data models
│   │   ├── registry.py                 # Persona registry
│   │   └── validator.py                # Validation
│   │
│   ├── workflow/                        # Workflow management
│   │   ├── workflow_api_v2.py          # WebSocket API
│   │   ├── error_prevention_rag.py     # RAG error prevention
│   │   └── shared_toolkit.py           # Common utilities
│   │
│   ├── quality/                         # Quality management
│   │   └── progressive_quality_manager.py
│   │
│   ├── compliance/                      # GDPR, EU AI Act
│   ├── certification/                   # Certification
│   ├── learning_engine/                 # Learning system
│   ├── rag/                             # RAG templates
│   ├── validation/                      # Validation framework
│   └── security/                        # Security policies
│
├── tests/                               # Test suite
├── docs/                                # Documentation
├── manifests/                           # Kubernetes manifests
├── pyproject.toml                       # Poetry configuration
└── docker-compose.yml                   # Infrastructure
```

---

## 4. Core Architecture

### Main Entry Points

#### 1. Team Execution (SDLC Orchestration)

**File**: `src/maestro_hive/teams/team_execution.py` (2,802 lines)

```python
class AutonomousSDLCEngineV3_1_Resumable:
    """
    V3.1 Features:
    - Persona-level intelligent reuse (V4.1)
    - Resumable sessions across runs
    - RAG integration for templates
    - Quality review with Quality Fabric
    - Template creation from outputs
    """
```

#### 2. DAG Workflow Engine

**File**: `src/maestro_hive/dag/dag_executor.py` (531 lines)

```python
class DAGExecutor:
    """
    Features:
    - Topological execution with parallel groups
    - Retry logic with exponential backoff
    - Conditional node execution
    - State persistence for pause/resume
    - Event-driven progress tracking
    """
```

#### 3. Agent Runtime Engine

**File**: `src/maestro_hive/agent_runtime/engine.py`

```python
class AgentRuntime:
    """
    Features:
    - Session management (create, start, pause, resume, stop)
    - Agent lifecycle tracking
    - Context persistence
    - Concurrent task execution
    """
```

### Architecture Layers

```
Execution Layer (Task scheduling, sandboxing, tracing)
    ↓
Runtime Layer (Agent lifecycle, context management)
    ↓
Orchestration Layer (DAG execution, workflow control)
    ↓
Team Layer (Persona collaboration, retrospectives)
    ↓
Application Layer (CLI, API, WebSocket)
```

### Design Patterns

| Pattern | Purpose |
|---------|---------|
| **Persona-Based** | 11 specialized AI agents |
| **DAG Workflow** | Dependency resolution, parallel execution |
| **Circuit Breaker** | Prevents cascading failures |
| **Rate Limiting** | Throttles concurrent requests |
| **Span-Based Tracing** | Distributed observability |
| **Sandbox Execution** | Isolated code execution |

---

## 5. Data Models

### Task Queue Models

```python
@dataclass
class Task:
    id: str                          # UUID
    name: str                        # Human-readable name
    func: Optional[Callable]         # Async callable
    args: tuple                      # Positional args
    kwargs: Dict[str, Any]           # Keyword args
    priority: TaskPriority           # CRITICAL|HIGH|NORMAL|LOW|BACKGROUND
    timeout: int                     # Seconds
    retry_count: int                 # Current retries
    max_retries: int                 # Max allowed
    status: TaskStatus               # PENDING|RUNNING|COMPLETED|FAILED
    result: Any                      # Execution result
    error: Optional[str]             # Error message

class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4
```

### Agent Session Models

```python
@dataclass
class AgentContext:
    agent_id: UUID
    persona_id: Optional[UUID]
    knowledge_ids: List[UUID]
    state_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class AgentSession:
    id: UUID
    agent_id: UUID
    context: AgentContext
    status: AgentState  # active, paused, stopped, error
    messages: List[Dict[str, str]]
```

### Span-Based Tracing Models

```python
@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    trace_flags: int = 1

@dataclass
class Span:
    name: str
    context: SpanContext
    kind: SpanKind  # INTERNAL|CLIENT|SERVER|PRODUCER|CONSUMER
    status: SpanStatus  # UNSET|OK|ERROR
    start_time: datetime
    end_time: Optional[datetime]
    attributes: Dict[str, Any]
    events: List[SpanEvent]
```

### Workflow DAG Models

```python
@dataclass
class WorkflowNode:
    id: str
    name: str
    node_type: NodeType  # TASK|PARALLEL|CONDITIONAL|DECISION
    executor: Optional[Callable]
    dependencies: List[str]
    status: NodeStatus  # PENDING|RUNNING|COMPLETED|FAILED|SKIPPED
    retry_policy: Optional[RetryPolicy]
    timeout: Optional[int]

@dataclass
class WorkflowDAG:
    workflow_id: str
    name: str
    nodes: Dict[str, WorkflowNode]
    edges: Dict[str, List[str]]
    global_context: Dict[str, Any]
```

### Sandbox Execution Models

```python
@dataclass
class SandboxConfig:
    timeout: int = 30                  # Seconds
    memory_limit: str = "512m"         # Docker format
    cpu_limit: float = 1.0             # CPU cores
    network_enabled: bool = False      # Network access
    max_output_size: int = 1024 * 1024 # 1MB output
    allowed_modules: List[str]         # Whitelist

@dataclass
class ExecutionResult:
    sandbox_id: str
    status: SandboxStatus  # PENDING|RUNNING|COMPLETED|FAILED|TIMEOUT
    stdout: str
    stderr: str
    return_value: Any
    error: Optional[str]
    exit_code: int
    execution_time_ms: float
```

---

## 6. Key Components

### 6.1 Execution Module (MD-3013)

#### TaskQueue

**Purpose**: Priority-based distributed task scheduling

**Features**:
- 5-level priority (CRITICAL → BACKGROUND)
- Fair scheduling with anti-starvation
- Configurable worker pool (default 10)
- Optional state persistence
- Full async/await support

**Key Methods**:
```python
async def enqueue(task: Task) -> str
async def dequeue() -> Optional[Task]
async def execute(task: Task) -> Any
async def get_task_status(task_id: str) -> TaskStatus
async def retry_task(task_id: str) -> bool
```

#### AgentTracer

**Purpose**: OpenTelemetry-compatible distributed tracing

**Features**:
- Hierarchical span nesting
- Performance metrics (duration, status)
- Event recording within spans
- Context propagation across async boundaries

**Usage**:
```python
class AgentTracer:
    def start_span(name: str, kind: SpanKind) -> Span
    def end_span(span: Span) -> None

    @contextmanager
    def traced_operation(name: str, attributes: Dict) -> Generator[Span]:
        ...
```

#### SandboxManager

**Purpose**: Secure isolated code execution

**Features**:
- CPU, memory, timeout constraints
- Network isolation
- Filesystem restrictions
- Process sandboxing

**Key Methods**:
```python
async def execute_code(code: str, config: SandboxConfig) -> ExecutionResult
async def execute_script(script_path: str, config: SandboxConfig) -> ExecutionResult
async def cleanup_sandbox(sandbox_id: str) -> bool
```

### 6.2 Agent Runtime (AC-2544)

**Architecture**:
```
AgentRuntime (main entry point)
├── AgentLifecycle (state transitions)
├── AgentExecutor (task execution)
├── ContextManager (context persistence)
└── AgentSession (per-agent interaction)
    ├── AgentContext (state + persona + knowledge)
    └── ExecutionMetrics (tokens, time, quality)
```

**Lifecycle Methods**:
```python
def register_agent(agent_id: UUID) -> bool
def create_session(agent_id: UUID) -> AgentSession
def start_session(session_id: UUID) -> bool
def pause_session(session_id: UUID) -> bool
def resume_session(session_id: UUID) -> bool
def stop_session(session_id: UUID) -> bool
```

### 6.3 DAG Executor

**Execution Flow**:
```
1. Load DAG (nodes + edges + context)
2. Topological sort → execution groups
3. For each group:
   - Execute nodes in parallel
   - Collect results
   - Update context
4. Conditional branching (if needed)
5. Emit events for monitoring
6. Persist state for recovery
```

**Execution Modes**:

| Mode | Description |
|------|-------------|
| Sequential | One node at a time |
| Parallel | Independent nodes concurrently |
| Conditional | Skip nodes based on expressions |
| Retry | Automatic retry with backoff |

### 6.4 Team Management

| Component | Purpose |
|-----------|---------|
| **RetrospectiveEngine** | Automated team analysis |
| **EvaluatorPersona** | AI performance evaluation |
| **ProcessImprover** | Workflow optimization |
| **TeamSimulator** | Scenario simulation |
| **BenchmarkRunner** | Performance benchmarking |
| **TeamEvolver** | Team composition evolution |
| **PerformanceOptimizer** | Performance tuning |

### 6.5 Enterprise Resilience

#### Circuit Breaker States

| State | Description |
|-------|-------------|
| **CLOSED** | Normal operation |
| **OPEN** | Failures exceeded, reject calls |
| **HALF_OPEN** | Testing recovery |

#### Resilience Components

| Component | Purpose |
|-----------|---------|
| CircuitBreaker | Prevents cascading failures |
| RateLimiter | Throttles concurrent requests |
| AutoScaler | Elastic resource allocation |
| Compensation | Transaction rollback |
| TransactionManager | Distributed coordination |

---

## 7. Configuration

### Environment Variables

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows
POSTGRES_USER=maestro
POSTGRES_PASSWORD=maestro_dev
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50

# DAG API Server
DAG_API_HOST=0.0.0.0
DAG_API_PORT=8080
DAG_API_WORKERS=4

# Claude API
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-opus-4-5

# Feature Flags
USE_SQLITE=false
USE_MOCK_REDIS=false
ENABLE_OBSERVABILITY=true
ENABLE_SANDBOXING=true
```

### pyproject.toml

```toml
[tool.poetry]
name = "maestro-hive"
version = "3.1.0"
description = "Autonomous SDLC Engine with AI Team Orchestration"

[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.40.0"
pydantic = "^2.11.10"
httpx = "^0.28.1"
structlog = "^25.4.0"
prometheus-client = "^0.23.1"
opentelemetry-api = "^1.37.0"
opentelemetry-sdk = "^1.37.0"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## 8. Testing

### Test Structure

```
tests/
├── integration/                     # Integration tests
│   ├── test_parallel_execution.py
│   ├── test_e2e_workflow.py
│   └── test_database_integration.py
├── contracts/                       # Contract tests
│   ├── test_models.py
│   ├── test_artifact_store.py
│   └── test_handoff.py
├── core_infrastructure/             # Core tests
│   ├── test_collaboration_engine.py
│   └── test_team_composer.py
├── personas/                        # Persona tests
├── release_management/              # Release tests
└── certification/                   # Certification tests
```

### Test Commands

```bash
# All tests
pytest

# With coverage
pytest --cov=src/maestro_hive

# Specific suite
pytest tests/integration/test_e2e_workflow.py

# Async tests
pytest tests/integration/ -m asyncio
```

---

## 9. Dependencies & Integrations

### External Services

| Service | Purpose |
|---------|---------|
| **Jira** | Issue tracking, sprints |
| **Confluence** | Documentation |
| **Claude API** | AI inference |
| **PostgreSQL** | Persistent state |
| **Redis** | Caching, pub-sub |

### Maestro Platform Components

```
maestro-hive (execution platform)
├── maestro-engine        # Engine execution
├── maestro-frontend      # UI/UX layer
├── maestro-templates     # RAG template library
├── quality-fabric        # Quality management
└── gateway               # API gateway
```

---

## 10. Key EPICs & Features

| EPIC | Description |
|------|-------------|
| **MD-3013** | Resilient Execution & Observability Grid |
| **MD-3015** | Autonomous Team Retrospective & Evaluation |
| **MD-3019** | Team Simulation & Benchmarking |
| **MD-3020** | Team Evolution & Performance Optimization |
| **MD-2544** | Agent Runtime Engine |
| **MD-2558** | Execution Tracking |
| **AC-2544** | Agent Lifecycle Management |

---

## 11. Deployment & Operations

### Docker Compose

```yaml
services:
  postgres:           # Persistent state
  redis:              # Caching & pub/sub
  dag-api-server:     # REST/WebSocket API
  worker-pool:        # Task execution
  observability:      # Prometheus/Jaeger
```

### Kubernetes Support

- StatefulSet for agent runtime
- Service for API exposure
- ConfigMap for configuration
- PersistentVolume for data

### Monitoring

| Tool | Purpose |
|------|---------|
| Prometheus | Metrics collection |
| Structlog | Structured logging |
| OpenTelemetry | Distributed tracing |
| Jaeger | Trace visualization |
| Grafana | Dashboards |

---

## Summary

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.11+ |
| **Total Lines** | 217,207 |
| **Modules** | 62 |
| **Framework** | FastAPI, async/await |
| **Database** | PostgreSQL + Redis |
| **Observability** | OpenTelemetry 1.37.0 |
| **Core Components** | TaskQueue, AgentRuntime, DAGExecutor |
| **Resilience** | Circuit breaker, rate limiting, auto-scaling |
| **Security** | RBAC, sandboxing, GDPR/EU AI Act compliance |
| **Testing** | 300+ tests (unit, integration, E2E) |
| **Deployment** | Docker Compose, Kubernetes-ready |

---

*Generated: December 2025*
*Maestro-Hive v3.1.0*
