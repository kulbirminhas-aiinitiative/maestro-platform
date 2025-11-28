# Phase Type Usage Guide

**Quick Reference**: When to use each phase type in your workflows

**Version**: 1.0.0
**Date**: 2025-10-12

---

## Quick Decision Tree

```
Is this a standard SDLC phase?
├─ YES → Use standard phase IDs
│   ├─ requirements
│   ├─ design
│   ├─ implementation
│   ├─ testing
│   ├─ deployment
│   └─ monitoring
│
└─ NO → Is it a specialized component?
    ├─ Backend API/Service? → backend
    ├─ Frontend UI/UX? → frontend
    ├─ System Architecture? → architecture
    ├─ Microservice? → service_* (e.g., service_auth)
    └─ Other? → custom_component (automatic fallback)
```

---

## Standard SDLC Phases

Use these for traditional waterfall or agile SDLC workflows.

### 1. requirements

**When to Use**:
- Gathering user stories and acceptance criteria
- Defining functional and non-functional requirements
- Creating requirements documents

**Exit Gates** (3):
- ✅ Completeness check (all required fields)
- ⚠️ Stakeholder approval (WARNING)
- ⚠️ Documentation completeness (WARNING)

**Example Workflow**:
```python
Node(
    id="gather_requirements",
    type=NodeType.PHASE,
    executor="requirements_executor",
    phase_type="requirements",
    config={
        "user_stories": ["US-1", "US-2", "US-3"],
        "acceptance_criteria": True
    }
)
```

**Typical Metrics**:
- `requirements_count`: Number of requirements gathered
- `acceptance_criteria_defined`: 0.0-1.0 (percentage)
- `stakeholder_approval`: 0.0-1.0

---

### 2. design

**When to Use**:
- Creating system architecture diagrams
- Designing UX/UI mockups
- Planning data models and APIs

**Exit Gates** (3):
- ✅ Design review approval
- ⚠️ Architecture documented (WARNING)
- ⚠️ Security architecture reviewed (WARNING)

**Example Workflow**:
```python
Node(
    id="system_design",
    type=NodeType.PHASE,
    executor="design_executor",
    phase_type="design",
    config={
        "diagrams": ["architecture.png", "data_model.png"],
        "wireframes": ["home.png", "dashboard.png"]
    }
)
```

**Typical Metrics**:
- `design_review_score`: 0.0-10.0
- `documentation_completeness`: 0.0-1.0
- `security_architecture_reviewed`: 0.0-1.0

---

### 3. implementation

**When to Use**:
- Writing production code
- Implementing features end-to-end
- Building the full system

**Exit Gates** (5):
- 🔴 **Build success** (95%+ rate) - BLOCKING
- 🔴 **Quality threshold** (8.0+ score, 80%+ coverage) - BLOCKING
- 🔴 **Security clean** (0 vulnerabilities) - BLOCKING
- ⚠️ Code review approved (WARNING)
- ⚠️ No stubs remaining (WARNING)

**Example Workflow**:
```python
Node(
    id="implement_feature",
    type=NodeType.PHASE,
    executor="implementation_executor",
    phase_type="implementation",
    config={
        "modules": ["auth", "api", "database"],
        "features": ["login", "signup", "password_reset"]
    }
)
```

**Typical Metrics**:
- `code_quality_score`: 0.0-10.0
- `test_coverage`: 0.0-1.0
- `build_success_rate`: 0.0-1.0
- `security_vulnerabilities`: integer
- `security_scan_complete`: 0.0-1.0

**Special Notes**:
- Only phase with BLOCKING security gates in standard SDLC
- Strictest quality requirements

---

### 4. testing

**When to Use**:
- Running unit, integration, and e2e tests
- QA validation
- Performance testing

**Exit Gates** (4):
- ✅ Test pass rate (95%+)
- ✅ Test coverage (80%+)
- ⚠️ Performance metrics (WARNING)
- ⚠️ Security tests passed (WARNING)

**Example Workflow**:
```python
Node(
    id="qa_testing",
    type=NodeType.PHASE,
    executor="testing_executor",
    phase_type="testing",
    config={
        "test_suites": ["unit", "integration", "e2e"],
        "coverage_threshold": 0.80
    }
)
```

**Typical Metrics**:
- `test_pass_rate`: 0.0-1.0
- `test_coverage`: 0.0-1.0
- `performance_benchmark_met`: 0.0-1.0
- `security_tests_passed`: 0.0-1.0

---

### 5. deployment

**When to Use**:
- Deploying to staging/production
- Running deployment scripts
- Release automation

**Exit Gates** (3):
- ✅ Deployment success
- ⚠️ Smoke tests passed (WARNING)
- ⚠️ Rollback plan documented (WARNING)

**Example Workflow**:
```python
Node(
    id="deploy_production",
    type=NodeType.PHASE,
    executor="deployment_executor",
    phase_type="deployment",
    config={
        "environment": "production",
        "strategy": "blue-green",
        "rollback_enabled": True
    }
)
```

**Typical Metrics**:
- `deployment_success`: 0.0-1.0
- `smoke_tests_passed`: 0.0-1.0
- `rollback_plan_exists`: 0.0-1.0

---

### 6. monitoring

**When to Use**:
- Setting up observability
- Configuring alerts and dashboards
- Establishing SLOs

**Exit Gates** (3):
- ✅ Monitoring configured
- ⚠️ Alerts defined (WARNING)
- ⚠️ Dashboards created (WARNING)

**Example Workflow**:
```python
Node(
    id="setup_monitoring",
    type=NodeType.PHASE,
    executor="monitoring_executor",
    phase_type="monitoring",
    config={
        "metrics": ["latency", "error_rate", "throughput"],
        "alerts": ["high_error_rate", "latency_p95"]
    }
)
```

**Typical Metrics**:
- `monitoring_configured`: 0.0-1.0
- `alerts_defined`: integer
- `dashboards_created`: integer

---

## Custom Phase Types (Phase 1)

Use these for specialized workflows or component-based development.

### 7. backend

**When to Use**:
- Building backend APIs and services
- Implementing business logic
- Database operations

**Exit Gates** (6):
- 🔴 **Build success** (95%+) - BLOCKING
- 🔴 **Quality threshold** (8.0+, 80%+ coverage) - BLOCKING
- 🔴 **Security clean** (0 vulnerabilities) - BLOCKING
- 🔴 **Security scanned** (complete) - BLOCKING
- ⚠️ API documented (WARNING)
- ⚠️ Integration tests passed (WARNING)

**Example Workflow**:
```python
Node(
    id="build_backend_api",
    type=NodeType.PHASE,
    executor="backend_executor",
    phase_type="backend",
    config={
        "apis": ["/api/users", "/api/products"],
        "database": "postgresql",
        "authentication": "jwt"
    }
)
```

**Typical Metrics**:
- `code_quality_score`: 0.0-10.0
- `test_coverage`: 0.0-1.0
- `build_success_rate`: 0.0-1.0
- `security_vulnerabilities`: integer
- `security_scan_complete`: 0.0-1.0
- `api_documentation_complete`: 0.0-1.0

**Special Notes**:
- BLOCKING security gates (unlike standard SDLC)
- Higher quality requirements than generic phases

---

### 8. frontend

**When to Use**:
- Building UI components
- Implementing pages and routes
- Styling and responsive design

**Exit Gates** (7):
- 🔴 **Build success** (95%+) - BLOCKING
- 🔴 **Quality threshold** (8.0+, 70%+ coverage) - BLOCKING
- 🔴 **Security clean** (0 vulnerabilities) - BLOCKING
- 🔴 **Security scanned** (complete) - BLOCKING
- ⚠️ Accessibility score (WARNING)
- ⚠️ UI component coverage (WARNING)
- ⚠️ Responsive design validated (WARNING)

**Example Workflow**:
```python
Node(
    id="build_frontend_ui",
    type=NodeType.PHASE,
    executor="frontend_executor",
    phase_type="frontend",
    config={
        "pages": ["home", "dashboard", "profile"],
        "components": ["navbar", "sidebar", "card"],
        "framework": "react"
    }
)
```

**Typical Metrics**:
- `code_quality_score`: 0.0-10.0
- `test_coverage`: 0.0-1.0 (note: 70% threshold, not 80%)
- `build_success_rate`: 0.0-1.0
- `security_vulnerabilities`: integer
- `security_scan_complete`: 0.0-1.0
- `accessibility_score`: 0.0-10.0
- `ui_component_coverage`: 0.0-1.0
- `responsive_design_validated`: 0.0-1.0

**Special Notes**:
- Lower test coverage requirement (70% vs 80%)
- Additional UI-specific gates (accessibility, responsiveness)

---

### 9. architecture

**When to Use**:
- High-level system design
- Technology stack decisions
- Architecture reviews and governance

**Exit Gates** (4):
- 🔴 **Architecture documented** - BLOCKING
- 🔴 **Security architecture reviewed** - BLOCKING
- 🔴 **Security scanned** (complete) - BLOCKING
- ⚠️ Design review approval (WARNING)

**Example Workflow**:
```python
Node(
    id="design_architecture",
    type=NodeType.PHASE,
    executor="architecture_executor",
    phase_type="architecture",
    config={
        "components": ["backend", "frontend", "database", "cache"],
        "patterns": ["microservices", "event-driven"],
        "decisions": ["adr-001", "adr-002"]
    }
)
```

**Typical Metrics**:
- `architecture_documented`: 0.0-1.0
- `design_review_score`: 0.0-10.0
- `security_architecture_reviewed`: 0.0-1.0
- `security_scan_complete`: 0.0-1.0

**Special Notes**:
- Focused on documentation and review
- Fewer technical metrics, more governance

---

### 10. service_template (Pattern Match)

**When to Use**:
- Building microservices
- Individual service development
- Service-oriented architecture

**Automatic Mapping**:
- `service_auth` → `service_template`
- `service_payment` → `service_template`
- `service_notification` → `service_template`
- `service_analytics` → `service_template`

**Exit Gates** (6):
- 🔴 **Build success** (95%+) - BLOCKING
- 🔴 **Quality threshold** (8.0+, 80%+ coverage) - BLOCKING
- 🔴 **Security clean** (0 vulnerabilities) - BLOCKING
- 🔴 **Security scanned** (complete) - BLOCKING
- ⚠️ Health check endpoint (WARNING)
- ⚠️ Observability configured (WARNING)

**Example Workflow**:
```python
# Automatically uses service_template SLO
Node(
    id="build_auth_service",
    type=NodeType.PHASE,
    executor="service_executor",
    phase_type="service_auth",  # Maps to service_template
    config={
        "service_name": "authentication",
        "endpoints": ["/login", "/logout", "/refresh"],
        "health_check": "/health"
    }
)
```

**Typical Metrics**:
- `code_quality_score`: 0.0-10.0
- `test_coverage`: 0.0-1.0
- `build_success_rate`: 0.0-1.0
- `security_vulnerabilities`: integer
- `security_scan_complete`: 0.0-1.0
- `health_check_endpoint_exists`: 0.0-1.0
- `observability_configured`: 0.0-1.0

**Special Notes**:
- Pattern matching: any `service_*` phase ID
- Includes service-specific gates (health checks, observability)

---

### 11. custom_component (Generic Fallback)

**When to Use**:
- Any undefined phase type
- Experimental or one-off components
- Temporary development phases

**Automatic Fallback**:
- Any phase ID not matching above patterns → `custom_component`

**Exit Gates** (5):
- 🔴 **Build success** (90%+) - BLOCKING
- 🔴 **Quality threshold** (7.0+, 70%+ coverage) - BLOCKING
- 🔴 **Security clean** (0 vulnerabilities) - BLOCKING
- 🔴 **Security scanned** (complete) - BLOCKING
- ⚠️ Documentation exists (WARNING)

**Example Workflow**:
```python
# Automatically uses custom_component SLO
Node(
    id="build_custom_module",
    type=NodeType.PHASE,
    executor="custom_executor",
    phase_type="my_custom_phase",  # Not defined → fallback
    config={
        "module": "custom_integration",
        "type": "experimental"
    }
)
```

**Typical Metrics**:
- `code_quality_score`: 0.0-10.0
- `test_coverage`: 0.0-1.0
- `build_success_rate`: 0.0-1.0
- `security_vulnerabilities`: integer
- `security_scan_complete`: 0.0-1.0
- `documentation_exists`: 0.0-1.0

**Special Notes**:
- Lower quality thresholds (7.0 vs 8.0, 70% vs 80%)
- Generic validation suitable for any component
- Always includes security gates

---

## Workflow Patterns

### Pattern 1: Standard SDLC Pipeline

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="req", type=NodeType.PHASE, phase_type="requirements", executor="req_exec"),
        Node(id="des", type=NodeType.PHASE, phase_type="design", executor="design_exec"),
        Node(id="imp", type=NodeType.PHASE, phase_type="implementation", executor="impl_exec"),
        Node(id="tst", type=NodeType.PHASE, phase_type="testing", executor="test_exec"),
        Node(id="dep", type=NodeType.PHASE, phase_type="deployment", executor="deploy_exec"),
        Node(id="mon", type=NodeType.PHASE, phase_type="monitoring", executor="monitor_exec"),
    ],
    edges=[
        ("req", "des"),
        ("des", "imp"),
        ("imp", "tst"),
        ("tst", "dep"),
        ("dep", "mon"),
    ]
)
```

**Use Case**: Traditional waterfall project with full SDLC

---

### Pattern 2: Parallel Frontend + Backend

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="arch", type=NodeType.PHASE, phase_type="architecture", executor="arch_exec"),
        Node(id="backend", type=NodeType.PHASE, phase_type="backend", executor="backend_exec"),
        Node(id="frontend", type=NodeType.PHASE, phase_type="frontend", executor="frontend_exec"),
        Node(id="integration", type=NodeType.PHASE, phase_type="testing", executor="test_exec"),
    ],
    edges=[
        ("arch", "backend"),
        ("arch", "frontend"),
        ("backend", "integration"),
        ("frontend", "integration"),
    ]
)
```

**Use Case**: Component-based development with parallel execution

---

### Pattern 3: Microservices Pipeline

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="design", type=NodeType.PHASE, phase_type="architecture", executor="arch_exec"),
        Node(id="auth", type=NodeType.PHASE, phase_type="service_auth", executor="svc_exec"),
        Node(id="payment", type=NodeType.PHASE, phase_type="service_payment", executor="svc_exec"),
        Node(id="notif", type=NodeType.PHASE, phase_type="service_notification", executor="svc_exec"),
        Node(id="test", type=NodeType.PHASE, phase_type="testing", executor="test_exec"),
    ],
    edges=[
        ("design", "auth"),
        ("design", "payment"),
        ("design", "notif"),
        ("auth", "test"),
        ("payment", "test"),
        ("notif", "test"),
    ]
)
```

**Use Case**: Microservices architecture with independent service development

---

### Pattern 4: Hybrid SDLC + Components

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="req", type=NodeType.PHASE, phase_type="requirements", executor="req_exec"),
        Node(id="design", type=NodeType.PHASE, phase_type="design", executor="design_exec"),
        Node(id="backend", type=NodeType.PHASE, phase_type="backend", executor="backend_exec"),
        Node(id="frontend", type=NodeType.PHASE, phase_type="frontend", executor="frontend_exec"),
        Node(id="test", type=NodeType.PHASE, phase_type="testing", executor="test_exec"),
        Node(id="deploy", type=NodeType.PHASE, phase_type="deployment", executor="deploy_exec"),
    ],
    edges=[
        ("req", "design"),
        ("design", "backend"),
        ("design", "frontend"),
        ("backend", "test"),
        ("frontend", "test"),
        ("test", "deploy"),
    ]
)
```

**Use Case**: Best of both worlds - SDLC structure with component-level validation

---

## Comparison Matrix

| Phase Type | Security Gates | Quality Threshold | Test Coverage | Use Case |
|------------|---------------|------------------|---------------|----------|
| **requirements** | ⚠️ WARNING | N/A | N/A | Gathering requirements |
| **design** | ⚠️ WARNING | N/A | N/A | System design |
| **implementation** | 🔴 BLOCKING | 8.0+ | 80%+ | Full implementation |
| **testing** | ⚠️ WARNING | N/A | 80%+ | QA validation |
| **deployment** | ⚠️ WARNING | N/A | N/A | Release automation |
| **monitoring** | ⚠️ WARNING | N/A | N/A | Observability |
| **backend** | 🔴 BLOCKING | 8.0+ | 80%+ | Backend APIs/services |
| **frontend** | 🔴 BLOCKING | 8.0+ | 70%+ | UI/UX development |
| **architecture** | 🔴 BLOCKING | N/A | N/A | System design |
| **service_template** | 🔴 BLOCKING | 8.0+ | 80%+ | Microservices |
| **custom_component** | 🔴 BLOCKING | 7.0+ | 70%+ | Generic fallback |

---

## Best Practices

### ✅ DO

1. **Use standard phase types** when your workflow matches SDLC patterns
2. **Use custom types** for specialized components (backend, frontend, services)
3. **Name services consistently** for automatic pattern matching (`service_*`)
4. **Mix and match** phase types in the same workflow as needed
5. **Trust the fallback** - undefined phases automatically use `custom_component`

### ❌ DON'T

1. **Don't use arbitrary names** without understanding the fallback behavior
2. **Don't bypass security gates** - they're ALWAYS BLOCKING in custom phases
3. **Don't ignore WARNING gates** - they indicate important quality issues
4. **Don't set unrealistic thresholds** - start lower and increase over time

---

## Quick Reference Table

| If You're Building... | Use Phase Type | Example ID |
|----------------------|----------------|------------|
| User stories | `requirements` | `gather_requirements` |
| UX mockups | `design` | `design_ui` |
| Full system | `implementation` | `implement_system` |
| QA tests | `testing` | `run_qa_tests` |
| Production release | `deployment` | `deploy_prod` |
| Observability | `monitoring` | `setup_monitoring` |
| REST APIs | `backend` | `build_api` |
| React components | `frontend` | `build_ui` |
| System design | `architecture` | `design_architecture` |
| Auth service | `service_auth` | `build_auth_service` |
| Payment service | `service_payment` | `build_payment_service` |
| Custom module | `custom_component` | `custom_module` (automatic) |

---

## Examples from Real Workflows

### Example 1: E-commerce Platform

```python
workflow = WorkflowGraph(
    nodes=[
        # Planning
        Node(id="requirements", phase_type="requirements"),
        Node(id="architecture", phase_type="architecture"),

        # Development (parallel)
        Node(id="product_catalog", phase_type="backend"),
        Node(id="shopping_cart", phase_type="service_cart"),
        Node(id="payment_gateway", phase_type="service_payment"),
        Node(id="storefront_ui", phase_type="frontend"),

        # Validation
        Node(id="integration_tests", phase_type="testing"),
        Node(id="deployment", phase_type="deployment"),
    ],
    edges=[
        ("requirements", "architecture"),
        ("architecture", "product_catalog"),
        ("architecture", "shopping_cart"),
        ("architecture", "payment_gateway"),
        ("architecture", "storefront_ui"),
        ("product_catalog", "integration_tests"),
        ("shopping_cart", "integration_tests"),
        ("payment_gateway", "integration_tests"),
        ("storefront_ui", "integration_tests"),
        ("integration_tests", "deployment"),
    ]
)
```

---

### Example 2: Internal Dashboard

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="design", phase_type="design"),
        Node(id="api_backend", phase_type="backend"),
        Node(id="dashboard_ui", phase_type="frontend"),
        Node(id="e2e_tests", phase_type="testing"),
    ],
    edges=[
        ("design", "api_backend"),
        ("design", "dashboard_ui"),
        ("api_backend", "e2e_tests"),
        ("dashboard_ui", "e2e_tests"),
    ]
)
```

---

### Example 3: Data Pipeline

```python
workflow = WorkflowGraph(
    nodes=[
        Node(id="architecture", phase_type="architecture"),
        Node(id="ingestion", phase_type="service_ingestion"),
        Node(id="processing", phase_type="service_processing"),
        Node(id="storage", phase_type="backend"),
        Node(id="monitoring", phase_type="monitoring"),
    ],
    edges=[
        ("architecture", "ingestion"),
        ("architecture", "processing"),
        ("architecture", "storage"),
        ("ingestion", "monitoring"),
        ("processing", "monitoring"),
        ("storage", "monitoring"),
    ]
)
```

---

## Support

**For more details**:
- Deployment Guide: `/docs/QUALITY_FABRIC_DEPLOYMENT_GUIDE.md`
- Configuration: `/config/phase_slos.yaml`
- Quick Reference: `/reports/QUICK_REFERENCE.md`

**Version**: 1.0.0
**Last Updated**: 2025-10-12
