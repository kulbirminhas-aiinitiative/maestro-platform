# DAG Workflow Initiation & Contract Implementation Guide

**Complete guide to initiating workflows, contract management, and cross-team coordination**

**Generated**: 2025-10-11
**Status**: ✅ Production Ready
**Version**: 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [How to Initiate DAG Workflows](#how-to-initiate-dag-workflows)
3. [List of All Available DAG Workflows](#list-of-all-available-dag-workflows)
4. [Cross-Node Contract Implementation](#cross-node-contract-implementation)
5. [Context Passing Between Nodes](#context-passing-between-nodes)
6. [Frontend Engineer Visibility](#frontend-engineer-visibility)
7. [Complete Workflow Lifecycle Example](#complete-workflow-lifecycle-example)
8. [API Reference](#api-reference)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The MAESTRO DAG (Directed Acyclic Graph) Workflow System enables parallel execution of SDLC phases with:

- ✅ **Contract-First Design** - API contracts defined before implementation
- ✅ **Parallel Team Work** - Backend and frontend teams work simultaneously
- ✅ **Context Passing** - Automatic data flow between phases
- ✅ **Real-Time Visibility** - Live progress updates for all team members
- ✅ **Quality Gates** - Validation at every phase transition
- ✅ **Recovery & Resume** - Workflow state persistence

### Key Concepts

**WorkflowDAG**: Graph structure defining execution order and dependencies
**WorkflowNode**: Individual execution unit (phase) with inputs/outputs
**WorkflowContext**: State management and data sharing across nodes
**ContractManager**: API contract versioning for parallel team coordination
**DAGExecutor**: Execution engine with retry logic and state persistence

---

## How to Initiate DAG Workflows

There are **three ways** to initiate a DAG workflow:

### Method 1: REST API (Recommended for Frontend Apps)

**Endpoint**: `POST /api/workflows/{workflow_id}/execute`

**Request Body**:
```json
{
  "requirement": "Build a REST API for user authentication with JWT tokens",
  "initial_context": {
    "project_name": "AuthService",
    "target_framework": "FastAPI",
    "database": "PostgreSQL"
  }
}
```

**Response**:
```json
{
  "execution_id": "exec_f47ac10b",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "created_at": "2025-10-11T14:30:00Z",
  "message": "Workflow execution started"
}
```

**Example using curl**:
```bash
curl -X POST http://localhost:8003/api/workflows/sdlc_parallel/execute \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Build a REST API for user authentication",
    "initial_context": {"project_name": "AuthService"}
  }'
```

**Example using TypeScript (Frontend)**:
```typescript
import { dagClient } from './lib/dag-workflow-client';

async function startWorkflow() {
  const execution = await dagClient.executeWorkflow(
    'sdlc_parallel',
    'Build a REST API for user authentication',
    {
      project_name: 'AuthService',
      target_framework: 'FastAPI',
      database: 'PostgreSQL'
    }
  );

  console.log('Started execution:', execution.execution_id);

  // Monitor progress
  await dagClient.pollExecution(execution.execution_id, (status) => {
    console.log(`Progress: ${status.progress_percent}%`);
    console.log(`Completed nodes: ${status.completed_nodes}/${status.total_nodes}`);
  });
}
```

### Method 2: Python Programmatic API

**Direct Execution**:
```python
import asyncio
from dag_compatibility import generate_parallel_workflow
from dag_executor import DAGExecutor, WorkflowContextStore
from team_execution_engine_v2_split import TeamExecutionEngineV2SplitMode

async def execute_workflow():
    # Initialize team engine
    team_engine = TeamExecutionEngineV2SplitMode(
        personas_dir="./src/personas/definitions",
        use_mock_mode=False
    )

    # Generate workflow
    workflow = generate_parallel_workflow(
        workflow_name="sdlc_parallel",
        team_engine=team_engine
    )

    # Create executor
    context_store = WorkflowContextStore()
    executor = DAGExecutor(
        workflow=workflow,
        context_store=context_store
    )

    # Execute
    initial_context = {
        'requirement': 'Build a REST API for user authentication',
        'project_name': 'AuthService',
        'target_framework': 'FastAPI'
    }

    context = await executor.execute(initial_context=initial_context)

    print(f"Workflow completed: {context.execution_id}")
    print(f"Completed nodes: {len(context.node_states)}")

    return context

# Run
asyncio.run(execute_workflow())
```

### Method 3: Command-Line Interface (CLI)

**Using the API server script**:
```bash
# Start the DAG API server
cd /home/ec2-user/projects/maestro-platform/maestro-hive
USE_SQLITE=true python3 dag_api_server_robust.py

# In another terminal, execute workflow
curl -X POST http://localhost:8003/api/workflows/sdlc_parallel/execute \
  -H "Content-Type: application/json" \
  -d '{"requirement": "Build a REST API for user authentication"}'
```

---

## List of All Available DAG Workflows

### 1. `sdlc_linear` - Sequential Linear Workflow

**Architecture**: All phases execute sequentially
**Use Case**: Simple projects, learning, testing
**Execution Time**: ~15-30 minutes (depends on complexity)

**Phases** (6 phases in sequence):
```
requirement_analysis
    ↓
design
    ↓
backend_development
    ↓
frontend_development
    ↓
testing
    ↓
review
```

**Initiate**:
```bash
POST /api/workflows/sdlc_linear/execute
```

**Programmatic**:
```python
from dag_compatibility import generate_linear_workflow
workflow = generate_linear_workflow("sdlc_linear", team_engine)
```

---

### 2. `sdlc_parallel` - Parallel Development Workflow

**Architecture**: Backend and frontend execute in parallel
**Use Case**: Production projects with separate teams
**Execution Time**: ~10-20 minutes (30-40% faster than linear)

**Phases** (6 phases with parallel execution):
```
requirement_analysis
    ↓
design
    ↓
    ├─→ backend_development  (parallel)
    └─→ frontend_development (parallel)
         ↓
       testing (waits for both)
         ↓
       review
```

**Key Features**:
- Backend and frontend teams work simultaneously
- Contract-driven coordination
- Testing waits for both development phases
- Optimal for web applications

**Initiate**:
```bash
POST /api/workflows/sdlc_parallel/execute
```

**Programmatic**:
```python
from dag_compatibility import generate_parallel_workflow
workflow = generate_parallel_workflow("sdlc_parallel", team_engine)
```

---

### 3. `sdlc_validated_linear` - Linear Workflow with Quality Gates

**Architecture**: Sequential with validation nodes after each phase
**Use Case**: High-quality requirements, production deployments
**Execution Time**: ~20-35 minutes (includes validation)

**Phases** (6 phases + 7 validation nodes):
```
requirement_analysis
    ↓
[validate_requirement_analysis]
    ↓
design
    ↓
[validate_design]
    ↓
[handoff: design → backend]
    ↓
backend_development
    ↓
[validate_backend_development]
    ↓
[handoff: backend → frontend]
    ↓
frontend_development
    ↓
[validate_frontend_development]
    ↓
testing
    ↓
[validate_testing]
    ↓
review
    ↓
[final_gap_detection]
```

**Quality Gates**:
- Phase validators check output completeness
- Handoff validators ensure proper context transfer
- Gap detector identifies missing requirements
- Final validation before deployment

**Initiate**:
```bash
POST /api/workflows/sdlc_validated_linear/execute
```

**Programmatic**:
```python
from dag_workflow_with_validation import generate_validated_linear_workflow
workflow = generate_validated_linear_workflow(
    workflow_name="sdlc_validated_linear",
    team_engine=team_engine,
    enable_validation=True,
    enable_handoff_validation=True,
    fail_on_validation_error=True
)
```

---

### 4. `sdlc_validated_parallel` - Parallel Workflow with Quality Gates

**Architecture**: Parallel development with comprehensive validation
**Use Case**: Production-ready systems with quality requirements
**Execution Time**: ~15-25 minutes (parallel + validation)

**Phases** (6 phases + 8 validation nodes):
```
requirement_analysis
    ↓
[validate_requirement_analysis]
    ↓
design
    ↓
[validate_design]
    ↓
    ├─→ backend_development  (parallel)
    │       ↓
    │   [validate_backend]
    │
    └─→ frontend_development (parallel)
            ↓
        [validate_frontend]
         ↓
    [check_implementation_completeness]
         ↓
       testing
         ↓
    [validate_testing]
         ↓
       review
         ↓
    [final_gap_detection]
```

**Key Features**:
- Parallel backend/frontend execution
- Independent validation for each track
- Completeness check before testing
- Comprehensive quality gates
- Best for production deployments

**Initiate**:
```bash
POST /api/workflows/sdlc_validated_parallel/execute
```

**Programmatic**:
```python
from dag_workflow_with_validation import generate_validated_parallel_workflow
workflow = generate_validated_parallel_workflow(
    workflow_name="sdlc_validated_parallel",
    team_engine=team_engine,
    enable_validation=True,
    fail_on_validation_error=True
)
```

---

### 5. `sdlc_subphased` - Granular Sub-Phase Implementation

**Architecture**: Fine-grained implementation with 8 sub-phases
**Use Case**: Complex systems, detailed progress tracking
**Execution Time**: ~25-40 minutes (most detailed)

**Sub-Phases** (14 total nodes):
```
requirement_analysis
    ↓
design
    ↓
backend_models (data models & types)
    ↓ [validate]
backend_core (services & business logic)
    ↓ [validate]
backend_api (routes & controllers)
    ↓ [validate]
backend_middleware (auth, validation)
    ↓ [validate]
    ├─→ frontend_structure (app structure)
    │       ↓ [validate]
    │   frontend_core (components & routing)
    │       ↓ [validate]
    │   frontend_features (feature components)
    │       ↓ [validate]
    │
    └─→ (frontend starts after backend_api ready)
         ↓
    integration (frontend-backend integration)
         ↓
       testing
         ↓
       review
         ↓
    [final_gap_detection]
```

**Key Features**:
- 8 granular implementation sub-phases
- Validation after each sub-phase
- Frontend starts once backend API is ready
- Maximum visibility into progress
- Ideal for complex enterprise systems

**Initiate**:
```bash
POST /api/workflows/sdlc_subphased/execute
```

**Programmatic**:
```python
from dag_workflow_with_validation import generate_subphased_implementation_workflow
workflow = generate_subphased_implementation_workflow(
    workflow_name="sdlc_subphased",
    team_engine=team_engine,
    enable_validation=True
)
```

---

### Querying Available Workflows

**REST API**:
```bash
GET http://localhost:8003/api/workflows
```

**Response**:
```json
[
  {
    "workflow_id": "sdlc_linear",
    "name": "sdlc_linear",
    "description": "Sequential SDLC workflow with 6 phases",
    "node_count": 6,
    "metadata": {
      "type": "linear",
      "phases": ["requirement_analysis", "design", "backend_development",
                 "frontend_development", "testing", "review"]
    }
  },
  {
    "workflow_id": "sdlc_parallel",
    "name": "sdlc_parallel",
    "description": "Parallel SDLC workflow with concurrent backend/frontend",
    "node_count": 6,
    "metadata": {
      "type": "parallel"
    }
  }
]
```

**TypeScript**:
```typescript
import { dagClient } from './lib/dag-workflow-client';

const workflows = await dagClient.getWorkflows();
workflows.forEach(wf => {
  console.log(`${wf.workflow_id}: ${wf.node_count} nodes`);
  console.log(`  Type: ${wf.metadata.type}`);
});
```

---

## Cross-Node Contract Implementation

The **ContractManager** ensures API contracts are defined before implementation, enabling parallel team work.

### Contract Architecture

```
┌─────────────────────┐
│   Design Phase      │
│  (defines contract) │
└──────────┬──────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│  Backend Development │          │ Frontend Development │
│  (implements API)    │          │  (consumes API)      │
│                      │          │                      │
│ • Creates endpoints  │          │ • Uses mock data     │
│ • Returns real data  │          │ • Builds UI          │
└──────────────────────┘          └──────────────────────┘
```

### How Contracts Work

**1. Contract Creation (Design Phase)**

During the design phase, the ContractManager creates API contracts:

```python
from contract_manager import ContractManager

contract_manager = ContractManager()

# Design phase creates contract
contract = await contract_manager.create_contract(
    team_id="design_team",
    contract_name="user_auth_api",
    version="1.0.0",
    contract_type="REST_API",
    specification={
        "base_path": "/api/v1",
        "endpoints": [
            {
                "path": "/auth/login",
                "method": "POST",
                "request_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["email", "password"]
                },
                "response_schema": {
                    "200": {
                        "type": "object",
                        "properties": {
                            "token": {"type": "string"},
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            }
                        }
                    },
                    "401": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"}
                        }
                    }
                }
            },
            {
                "path": "/auth/register",
                "method": "POST",
                "request_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "name": {"type": "string"}
                    },
                    "required": ["email", "password", "name"]
                },
                "response_schema": {
                    "201": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "message": {"type": "string"}
                        }
                    }
                }
            }
        ]
    },
    owner_role="backend_engineer",
    owner_agent="backend_developer",
    consumers=["frontend_developer"]
)

print(f"Contract created: {contract['contract_id']}")
print(f"Status: {contract['status']}")  # "draft"
```

**2. Contract Activation (Backend Development)**

Backend implements the API and activates the contract:

```python
# Backend completes implementation
await contract_manager.evolve_contract(
    team_id="backend_team",
    contract_name="user_auth_api",
    new_version="1.0.0",
    new_specification=contract_spec,  # Same as design
    breaking_changes=False
)

# Activate for consumers
await contract_manager.activate_contract(
    contract_name="user_auth_api",
    version="1.0.0"
)

print("Contract activated - Frontend can now use real API")
```

**3. Contract Consumption (Frontend Development)**

Frontend uses the contract to know what APIs are available:

```typescript
// Frontend receives contract from workflow context
interface AuthAPI {
  login: {
    path: '/api/v1/auth/login',
    method: 'POST',
    request: {
      email: string;
      password: string;
    },
    response: {
      token: string;
      user: {
        id: string;
        email: string;
        name: string;
      }
    }
  };
  register: {
    path: '/api/v1/auth/register',
    method: 'POST',
    request: {
      email: string;
      password: string;
      name: string;
    },
    response: {
      user_id: string;
      message: string;
    }
  };
}

// Frontend can develop against this contract
// Using mock data until backend is ready
```

### Contract Versioning & Evolution

**Adding Non-Breaking Changes**:
```python
# Add new optional field (non-breaking)
await contract_manager.evolve_contract(
    team_id="backend_team",
    contract_name="user_auth_api",
    new_version="1.1.0",
    new_specification={
        # ... existing endpoints ...
        "endpoints": [
            # ... existing endpoints ...
            {
                "path": "/auth/refresh",
                "method": "POST",
                "request_schema": {
                    "type": "object",
                    "properties": {
                        "refresh_token": {"type": "string"}
                    }
                }
            }
        ]
    },
    breaking_changes=False
)
```

**Handling Breaking Changes**:
```python
# Change response schema (breaking)
await contract_manager.evolve_contract(
    team_id="backend_team",
    contract_name="user_auth_api",
    new_version="2.0.0",
    new_specification={
        # Changed response structure
    },
    breaking_changes=True  # Notifies consumers
)

# System notifies all consumers about breaking change
# Frontend must update their code before using v2.0.0
```

### Contract Benefits for Parallel Work

**Backend Team**:
- ✅ Clear API specification from design phase
- ✅ Implementation guidance
- ✅ No waiting for frontend requirements

**Frontend Team**:
- ✅ Can start development immediately after design
- ✅ Use mock data matching contract schema
- ✅ No blocked waiting for backend completion
- ✅ Seamless switch to real API when ready

**Design Team**:
- ✅ Define API contract upfront
- ✅ Ensure consistency across teams
- ✅ Version control for API evolution

---

## Context Passing Between Nodes

The **WorkflowContext** manages state and data flow between workflow nodes.

### Context Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WorkflowContext                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  global_context: {                                      │
│    requirement: "Build user auth API",                  │
│    project_name: "AuthService",                         │
│    workflow_id: "sdlc_parallel"                         │
│  }                                                      │
│                                                         │
│  node_outputs: {                                        │
│    "requirement_analysis": {...},                       │
│    "design": {...},                                     │
│    "backend_development": {...}                         │
│  }                                                      │
│                                                         │
│  artifacts: {                                           │
│    "design": ["/tmp/workflow/design_doc.md"],          │
│    "backend_development": ["/tmp/workflow/api.py"]     │
│  }                                                      │
│                                                         │
│  node_states: {                                         │
│    "requirement_analysis": <completed>,                 │
│    "design": <completed>,                               │
│    "backend_development": <running>                     │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

### How Context Flows

**Phase 1: Requirement Analysis**

Input:
```python
{
  'node_id': 'phase_requirement_analysis',
  'node_name': 'requirement_analysis',
  'node_config': {'phase': 'requirement_analysis'},
  'dependency_outputs': {},  # No dependencies
  'dependency_artifacts': {},
  'global_context': {
    'requirement': 'Build a REST API for user authentication',
    'workflow_id': 'sdlc_parallel'
  },
  'all_outputs': {},
  'all_artifacts': {}
}
```

Output:
```python
{
  'phase': 'requirement_analysis',
  'status': 'completed',
  'output': {
    'functional_requirements': [
      'User registration with email validation',
      'User login with JWT tokens',
      'Password reset functionality'
    ],
    'non_functional_requirements': [
      'Response time < 200ms',
      'Support 10,000 concurrent users'
    ],
    'technical_requirements': {
      'framework': 'FastAPI',
      'database': 'PostgreSQL',
      'authentication': 'JWT'
    }
  },
  'artifacts': ['/tmp/workflow/requirements.md'],
  'contracts': []
}
```

**Phase 2: Design (receives Phase 1 output)**

Input:
```python
{
  'node_id': 'phase_design',
  'node_name': 'design',
  'node_config': {'phase': 'design'},
  'dependency_outputs': {
    'phase_requirement_analysis': {
      'functional_requirements': [...],
      'non_functional_requirements': [...],
      'technical_requirements': {...}
    }
  },
  'dependency_artifacts': {
    'phase_requirement_analysis': ['/tmp/workflow/requirements.md']
  },
  'global_context': {
    'requirement': 'Build a REST API for user authentication',
    'workflow_id': 'sdlc_parallel'
  },
  'all_outputs': {
    'phase_requirement_analysis': {...}
  },
  'all_artifacts': {
    'phase_requirement_analysis': ['/tmp/workflow/requirements.md']
  }
}
```

Output:
```python
{
  'phase': 'design',
  'status': 'completed',
  'output': {
    'architecture': {
      'layers': ['API Layer', 'Service Layer', 'Data Layer'],
      'components': ['AuthController', 'UserService', 'TokenService']
    },
    'api_design': {
      'base_path': '/api/v1',
      'endpoints': [...]
    },
    'database_schema': {
      'tables': ['users', 'tokens', 'sessions']
    }
  },
  'artifacts': [
    '/tmp/workflow/architecture_diagram.png',
    '/tmp/workflow/api_spec.yaml',
    '/tmp/workflow/db_schema.sql'
  ],
  'contracts': [
    {
      'contract_id': 'contract_auth_api_v1',
      'contract_name': 'user_auth_api',
      'version': '1.0.0',
      'specification': {...}
    }
  ]
}
```

**Phase 3a & 3b: Backend + Frontend (parallel, both receive Design output)**

Backend Input:
```python
{
  'node_id': 'phase_backend_development',
  'node_name': 'backend_development',
  'node_config': {'phase': 'backend_development'},
  'dependency_outputs': {
    'phase_requirement_analysis': {...},
    'phase_design': {
      'architecture': {...},
      'api_design': {...},
      'database_schema': {...}
    }
  },
  'dependency_artifacts': {
    'phase_requirement_analysis': ['/tmp/workflow/requirements.md'],
    'phase_design': [
      '/tmp/workflow/architecture_diagram.png',
      '/tmp/workflow/api_spec.yaml',
      '/tmp/workflow/db_schema.sql'
    ]
  },
  'global_context': {...},
  'all_outputs': {
    'phase_requirement_analysis': {...},
    'phase_design': {...}
  },
  'all_artifacts': {...}
}
```

Frontend Input (same dependencies as backend):
```python
{
  'node_id': 'phase_frontend_development',
  'node_name': 'frontend_development',
  'node_config': {'phase': 'frontend_development'},
  'dependency_outputs': {
    'phase_requirement_analysis': {...},
    'phase_design': {...}  # Same design output as backend
  },
  'dependency_artifacts': {
    'phase_requirement_analysis': [...],
    'phase_design': [...]  # Same artifacts as backend
  },
  'global_context': {...},
  'all_outputs': {...},
  'all_artifacts': {...}
}
```

**Phase 4: Testing (receives both Backend + Frontend outputs)**

Input:
```python
{
  'node_id': 'phase_testing',
  'node_name': 'testing',
  'node_config': {'phase': 'testing'},
  'dependency_outputs': {
    'phase_backend_development': {
      'api_endpoints': [...],
      'database_migrations': [...],
      'unit_tests': [...]
    },
    'phase_frontend_development': {
      'components': [...],
      'pages': [...],
      'integration_tests': [...]
    }
  },
  'dependency_artifacts': {
    'phase_backend_development': [
      '/tmp/workflow/backend/api.py',
      '/tmp/workflow/backend/models.py'
    ],
    'phase_frontend_development': [
      '/tmp/workflow/frontend/LoginPage.tsx',
      '/tmp/workflow/frontend/RegisterPage.tsx'
    ]
  },
  'global_context': {...},
  'all_outputs': {
    'phase_requirement_analysis': {...},
    'phase_design': {...},
    'phase_backend_development': {...},
    'phase_frontend_development': {...}
  },
  'all_artifacts': {...}
}
```

### Context Passing Implementation

**PhaseNodeExecutor builds comprehensive context**:

```python
def _build_phase_requirement(self, phase_context: PhaseExecutionContext) -> str:
    """
    Build comprehensive phase requirement with full context.
    This ensures phases receive all previous phase outputs.
    """
    requirement_parts = [f"## Original Requirement:\n{phase_context.requirement}\n"]

    # Add previous phase outputs
    if phase_context.previous_phase_outputs:
        requirement_parts.append("\n## Previous Phase Outputs:")
        for prev_phase, output in phase_context.previous_phase_outputs.items():
            requirement_parts.append(f"\n### {prev_phase}:")
            requirement_parts.append(self._format_output(output))

    # Add artifacts
    if phase_context.previous_phase_artifacts:
        requirement_parts.append("\n## Available Artifacts:")
        for prev_phase, artifacts in phase_context.previous_phase_artifacts.items():
            if artifacts:
                requirement_parts.append(f"\n### {prev_phase}:")
                for artifact in artifacts:
                    requirement_parts.append(f"- {artifact}")

    # Add contracts
    if phase_context.previous_phase_contracts:
        requirement_parts.append("\n## Previous Phase Contracts:")
        for contract in phase_context.previous_phase_contracts:
            requirement_parts.append(self._format_contract(contract))

    return "\n".join(requirement_parts)
```

### Context Persistence

Contexts are persisted to database for recovery:

```python
from database.workflow_store import DatabaseWorkflowContextStore

context_store = DatabaseWorkflowContextStore()

# Save context (automatic during execution)
await context_store.save_context(context)

# Load context (for resume)
context = await context_store.load_context(execution_id)

# Context includes:
# - Node states (pending, running, completed, failed)
# - Node outputs (data from each phase)
# - Artifacts (file paths)
# - Global context (workflow-wide data)
```

---

## Frontend Engineer Visibility

Frontend engineers have **complete visibility** into:
1. What tasks are expected
2. Context of all changes
3. Real-time progress
4. Quality gates and validation

### 1. Task Visibility via Contracts

**What Frontend Engineers See**:

When a frontend engineer starts their phase, they receive:

```json
{
  "phase": "frontend_development",
  "dependencies": {
    "design": {
      "contracts": [
        {
          "contract_id": "contract_auth_api_v1",
          "contract_name": "user_auth_api",
          "version": "1.0.0",
          "status": "active",
          "specification": {
            "base_path": "/api/v1",
            "endpoints": [
              {
                "path": "/auth/login",
                "method": "POST",
                "description": "User login with email and password",
                "request_schema": {
                  "type": "object",
                  "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "minLength": 8}
                  },
                  "required": ["email", "password"]
                },
                "response_schema": {
                  "200": {
                    "description": "Login successful",
                    "type": "object",
                    "properties": {
                      "token": {"type": "string"},
                      "user": {
                        "type": "object",
                        "properties": {
                          "id": {"type": "string"},
                          "email": {"type": "string"},
                          "name": {"type": "string"}
                        }
                      }
                    }
                  },
                  "401": {
                    "description": "Invalid credentials",
                    "type": "object",
                    "properties": {
                      "error": {"type": "string"}
                    }
                  }
                }
              }
            ]
          },
          "mock_data": {
            "/auth/login": {
              "POST": {
                "200": {
                  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                  "user": {
                    "id": "user_123",
                    "email": "demo@example.com",
                    "name": "Demo User"
                  }
                }
              }
            }
          }
        }
      ]
    }
  }
}
```

**Clear Task Expectations**:
- ✅ Build login page with email/password form
- ✅ Build registration page
- ✅ Implement JWT token storage
- ✅ Create user profile page
- ✅ Add error handling for 401 responses
- ✅ Use mock data until backend is ready

### 2. Progress Visibility via REST API

**Get Execution Status**:
```bash
GET /api/executions/{execution_id}
```

**Response**:
```json
{
  "execution_id": "exec_f47ac10b",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "progress_percent": 66.7,
  "completed_nodes": 4,
  "total_nodes": 6,
  "current_phase": "testing",
  "started_at": "2025-10-11T14:30:00Z",
  "node_states": [
    {
      "node_id": "phase_requirement_analysis",
      "status": "completed",
      "started_at": "2025-10-11T14:30:05Z",
      "completed_at": "2025-10-11T14:33:12Z",
      "duration": 187.3,
      "output": {
        "functional_requirements": [...]
      }
    },
    {
      "node_id": "phase_design",
      "status": "completed",
      "started_at": "2025-10-11T14:33:15Z",
      "completed_at": "2025-10-11T14:36:42Z",
      "duration": 207.5,
      "output": {
        "architecture": {...},
        "api_design": {...}
      }
    },
    {
      "node_id": "phase_backend_development",
      "status": "completed",
      "started_at": "2025-10-11T14:36:45Z",
      "completed_at": "2025-10-11T14:42:18Z",
      "duration": 333.2,
      "output": {
        "api_endpoints": [...],
        "database_migrations": [...]
      }
    },
    {
      "node_id": "phase_frontend_development",
      "status": "completed",
      "started_at": "2025-10-11T14:36:45Z",
      "completed_at": "2025-10-11T14:43:02Z",
      "duration": 377.1,
      "output": {
        "components": [...],
        "pages": [...]
      }
    },
    {
      "node_id": "phase_testing",
      "status": "running",
      "started_at": "2025-10-11T14:43:05Z",
      "duration": null
    },
    {
      "node_id": "phase_review",
      "status": "pending",
      "started_at": null,
      "duration": null
    }
  ]
}
```

**TypeScript - Real-Time Status**:
```typescript
import { dagClient } from './lib/dag-workflow-client';

// Poll for updates every 2 seconds
await dagClient.pollExecution(executionId, (status) => {
  console.log(`\n=== Workflow Progress ===`);
  console.log(`Status: ${status.status}`);
  console.log(`Progress: ${status.progress_percent.toFixed(1)}%`);
  console.log(`Completed: ${status.completed_nodes}/${status.total_nodes} nodes`);

  console.log(`\nNode Status:`);
  status.node_states.forEach(node => {
    const icon =
      node.status === 'completed' ? '✅' :
      node.status === 'running' ? '🔄' :
      node.status === 'failed' ? '❌' : '⏸️';

    console.log(`${icon} ${node.node_id}: ${node.status}`);
    if (node.duration) {
      console.log(`   Duration: ${node.duration.toFixed(1)}s`);
    }
  });
});
```

### 3. Real-Time Visibility via WebSocket

**Connect to WebSocket**:
```typescript
const ws = dagClient.connectWebSocket('sdlc_parallel', {
  onOpen: () => {
    console.log('Connected to workflow updates');
  },
  onMessage: (event) => {
    console.log(`Event: ${event.type}`);

    switch (event.type) {
      case 'workflow_started':
        showNotification('Workflow started');
        break;

      case 'node_started':
        console.log(`Phase started: ${event.node_id}`);
        updateUIProgress(event.node_id, 'running');
        break;

      case 'node_completed':
        console.log(`Phase completed: ${event.node_id}`);
        console.log(`Duration: ${event.data.duration}s`);
        updateUIProgress(event.node_id, 'completed');

        // If frontend phase completed, show details
        if (event.node_id === 'phase_frontend_development') {
          showFrontendOutput(event.data.outputs);
        }
        break;

      case 'node_failed':
        console.error(`Phase failed: ${event.node_id}`);
        console.error(`Error: ${event.data.error}`);
        showError(event.node_id, event.data.error);
        break;

      case 'workflow_completed':
        showNotification('Workflow completed successfully!');
        showFinalResults();
        break;
    }
  },
  onError: (error) => {
    console.error('WebSocket error:', error);
  },
  onClose: () => {
    console.log('WebSocket closed');
  }
});
```

**WebSocket Events**:
```typescript
type WebSocketEventType =
  | 'workflow_started'
  | 'node_started'
  | 'node_completed'
  | 'node_failed'
  | 'workflow_completed'
  | 'workflow_failed'
  | 'pong';

interface WebSocketEvent {
  type: WebSocketEventType;
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  node_id?: string;
  data?: {
    phase?: string;
    duration?: number;
    outputs?: any;
    error?: string;
  };
}
```

### 4. Context Visibility

**Frontend Engineer Dashboard Example**:

```typescript
interface FrontendDashboard {
  // Current task
  currentPhase: 'frontend_development';
  status: 'running';

  // What I need to build (from contracts)
  tasks: [
    {
      task: 'Build Login Page',
      requirements: [
        'Email input with validation',
        'Password input with show/hide toggle',
        'Submit button',
        'Error message display for 401 responses'
      ],
      apiEndpoint: '/api/v1/auth/login',
      mockData: { token: '...', user: {...} }
    },
    {
      task: 'Build Registration Page',
      requirements: [
        'Email, password, name inputs',
        'Password strength indicator',
        'Submit button'
      ],
      apiEndpoint: '/api/v1/auth/register',
      mockData: { user_id: '...', message: '...' }
    }
  ];

  // Context from previous phases
  previousPhases: {
    requirementAnalysis: {
      status: 'completed',
      outputs: {
        functional_requirements: [...],
        technical_requirements: {...}
      },
      artifacts: ['/tmp/workflow/requirements.md']
    },
    design: {
      status: 'completed',
      outputs: {
        architecture: {...},
        api_design: {...}
      },
      artifacts: [
        '/tmp/workflow/architecture_diagram.png',
        '/tmp/workflow/api_spec.yaml'
      ],
      contracts: [
        {
          contract_name: 'user_auth_api',
          version: '1.0.0',
          endpoints: [...]
        }
      ]
    }
  };

  // Parallel work status
  parallelPhases: {
    backend_development: {
      status: 'running',  // Backend is still in progress
      progress: 75,
      estimatedCompletion: '2025-10-11T14:42:00Z'
    }
  };

  // Quality gates
  validation: {
    nextGate: 'validate_frontend_development',
    requirements: [
      'All components have unit tests',
      'UI matches design specifications',
      'API integration tested with mocks'
    ]
  };
}
```

### 5. Validation Reports

After each phase, validation reports show quality status:

```json
{
  "validation_id": "validate_frontend_development",
  "phase": "frontend_development",
  "status": "passed",
  "checks": [
    {
      "check": "Components Created",
      "status": "passed",
      "details": {
        "expected": ["LoginPage", "RegisterPage", "UserProfile"],
        "found": ["LoginPage", "RegisterPage", "UserProfile"],
        "missing": []
      }
    },
    {
      "check": "API Integration",
      "status": "passed",
      "details": {
        "endpoints_integrated": [
          "/api/v1/auth/login",
          "/api/v1/auth/register"
        ],
        "mock_data_used": true
      }
    },
    {
      "check": "Unit Tests",
      "status": "warning",
      "details": {
        "coverage": 85,
        "target": 90,
        "message": "Test coverage is 85%, target is 90%"
      }
    }
  ],
  "recommendations": [
    "Add unit tests for error handling in LoginPage",
    "Increase test coverage to meet 90% target"
  ]
}
```

---

## Complete Workflow Lifecycle Example

### End-to-End Example: Building an Authentication API

**Step 1: Initiate Workflow**

```typescript
import { dagClient } from './lib/dag-workflow-client';

const execution = await dagClient.executeWorkflow(
  'sdlc_parallel',
  'Build a REST API for user authentication with JWT tokens',
  {
    project_name: 'AuthService',
    target_framework: 'FastAPI',
    database: 'PostgreSQL'
  }
);

console.log(`Workflow started: ${execution.execution_id}`);
```

**Step 2: Monitor Progress**

```typescript
// Connect WebSocket for real-time updates
const ws = dagClient.connectWebSocket('sdlc_parallel', {
  onMessage: (event) => {
    if (event.type === 'node_completed') {
      console.log(`✅ ${event.node_id} completed in ${event.data.duration}s`);

      // Show phase-specific details
      if (event.node_id === 'phase_design') {
        console.log('Design phase outputs:', event.data.outputs);
        console.log('Contracts created:', event.data.outputs.contracts);
      }
    }
  }
});

// Poll for status updates
await dagClient.pollExecution(execution.execution_id, (status) => {
  console.log(`Progress: ${status.progress_percent}%`);

  // Frontend engineer can see when their phase starts
  const frontendPhase = status.node_states.find(
    n => n.node_id === 'phase_frontend_development'
  );

  if (frontendPhase?.status === 'running') {
    console.log('Frontend development is now in progress!');
    console.log('Check contracts for API specifications');
  }
});
```

**Step 3: Frontend Engineer Sees Contract**

After design phase completes, frontend engineer receives:

```json
{
  "contract_name": "user_auth_api",
  "version": "1.0.0",
  "endpoints": [
    {
      "path": "/api/v1/auth/login",
      "method": "POST",
      "description": "User login endpoint",
      "request": {
        "email": "string (email format)",
        "password": "string (min 8 chars)"
      },
      "responses": {
        "200": {
          "token": "string (JWT)",
          "user": {
            "id": "string",
            "email": "string",
            "name": "string"
          }
        },
        "401": {
          "error": "string"
        }
      },
      "mock_data": {
        "200": {
          "token": "mock_jwt_token_12345",
          "user": {
            "id": "user_001",
            "email": "demo@example.com",
            "name": "Demo User"
          }
        }
      }
    }
  ]
}
```

**Step 4: Frontend Development (Parallel with Backend)**

Frontend engineer builds UI using contract:

```typescript
// LoginPage.tsx
import { useState } from 'react';

interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  token: string;
  user: {
    id: string;
    email: string;
    name: string;
  };
}

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async () => {
    try {
      // Use contract specification
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (response.status === 200) {
        const data: LoginResponse = await response.json();
        localStorage.setItem('token', data.token);
        // Navigate to dashboard
      } else if (response.status === 401) {
        const errorData = await response.json();
        setError(errorData.error);
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    <div>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button onClick={handleLogin}>Login</button>
      {error && <p style={{color: 'red'}}>{error}</p>}
    </div>
  );
}
```

**Step 5: Testing Phase (After Both Complete)**

Testing phase receives outputs from both backend and frontend:

```json
{
  "dependencies": {
    "backend_development": {
      "api_endpoints": [
        "/api/v1/auth/login",
        "/api/v1/auth/register"
      ],
      "database_migrations": ["001_create_users_table.sql"],
      "unit_tests": ["test_auth.py"]
    },
    "frontend_development": {
      "components": ["LoginPage", "RegisterPage"],
      "pages": ["Dashboard"],
      "integration_tests": ["login.test.tsx"]
    }
  }
}
```

**Step 6: Review & Completion**

```typescript
// Final status
const finalStatus = await dagClient.getExecutionStatus(execution.execution_id);

console.log('Workflow completed!');
console.log(`Total duration: ${finalStatus.duration}s`);
console.log(`Phases completed: ${finalStatus.completed_nodes}`);

// All outputs available
console.log('Backend outputs:', finalStatus.node_states.find(
  n => n.node_id === 'phase_backend_development'
).output);

console.log('Frontend outputs:', finalStatus.node_states.find(
  n => n.node_id === 'phase_frontend_development'
).output);

console.log('Testing results:', finalStatus.node_states.find(
  n => n.node_id === 'phase_testing'
).output);
```

---

## API Reference

### REST API Endpoints

**Base URL**: `http://localhost:8003`

#### 1. List All Workflows

```
GET /api/workflows
```

**Response**:
```json
[
  {
    "workflow_id": "sdlc_parallel",
    "name": "sdlc_parallel",
    "description": "Parallel SDLC workflow",
    "node_count": 6,
    "metadata": {"type": "parallel"}
  }
]
```

#### 2. Get Workflow Details

```
GET /api/workflows/{workflow_id}
```

**Response**:
```json
{
  "workflow_id": "sdlc_parallel",
  "name": "sdlc_parallel",
  "nodes": [
    {
      "node_id": "phase_requirement_analysis",
      "name": "requirement_analysis",
      "node_type": "phase",
      "dependencies": []
    },
    {
      "node_id": "phase_design",
      "name": "design",
      "node_type": "phase",
      "dependencies": ["phase_requirement_analysis"]
    }
  ],
  "edges": [
    {
      "from": "phase_requirement_analysis",
      "to": "phase_design"
    }
  ]
}
```

#### 3. Execute Workflow

```
POST /api/workflows/{workflow_id}/execute
```

**Request Body**:
```json
{
  "requirement": "Build a REST API",
  "initial_context": {
    "project_name": "MyAPI"
  }
}
```

**Response**:
```json
{
  "execution_id": "exec_abc123",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "created_at": "2025-10-11T14:30:00Z"
}
```

#### 4. Get Execution Status

```
GET /api/executions/{execution_id}
```

**Response**: See [Progress Visibility](#2-progress-visibility-via-rest-api) section

#### 5. Health Check

```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "type": "SQLite"
  },
  "workflows_registered": 5,
  "active_executions": 2
}
```

### WebSocket API

**URL**: `ws://localhost:8003/ws/workflow/{execution_id}`

**Events**: See [Real-Time Visibility](#3-real-time-visibility-via-websocket) section

---

## Best Practices

### 1. Workflow Selection

**Use `sdlc_linear` when**:
- Learning the system
- Simple projects with minimal complexity
- Testing and debugging

**Use `sdlc_parallel` when**:
- Production web applications
- Separate backend and frontend teams
- Time is critical (30-40% faster)

**Use `sdlc_validated_parallel` when**:
- Production deployments
- Quality requirements are critical
- Need comprehensive validation reports

**Use `sdlc_subphased` when**:
- Complex enterprise systems
- Need fine-grained progress tracking
- Multiple sub-components

### 2. Contract Management

**Do**:
- ✅ Define contracts in design phase
- ✅ Include complete request/response schemas
- ✅ Provide mock data for frontend development
- ✅ Version contracts properly (semver)
- ✅ Document breaking changes

**Don't**:
- ❌ Change contracts without version bump
- ❌ Skip contract validation
- ❌ Make breaking changes in minor versions
- ❌ Forget to notify consumers of changes

### 3. Context Passing

**Do**:
- ✅ Store all relevant outputs in node output
- ✅ Track artifacts (files) explicitly
- ✅ Use global context for workflow-wide data
- ✅ Include error details in failed nodes

**Don't**:
- ❌ Store large binary data in outputs (use artifacts)
- ❌ Assume dependency order (check dependencies)
- ❌ Modify global context from nodes
- ❌ Forget to handle missing dependencies

### 4. Monitoring

**Do**:
- ✅ Use WebSocket for real-time updates
- ✅ Poll API for reliable status checks
- ✅ Log all events for debugging
- ✅ Monitor node duration for performance

**Don't**:
- ❌ Rely only on WebSocket (can disconnect)
- ❌ Poll too frequently (< 1 second)
- ❌ Ignore validation warnings
- ❌ Skip error handling

### 5. Error Handling

**Do**:
- ✅ Implement retry logic for transient errors
- ✅ Provide detailed error messages
- ✅ Log errors with context
- ✅ Handle node failures gracefully

**Don't**:
- ❌ Retry on permanent errors
- ❌ Hide error details from users
- ❌ Continue on critical failures
- ❌ Ignore validation failures

---

## Troubleshooting

### Issue: Workflow Execution Fails Immediately

**Symptoms**:
- Execution status shows "failed"
- No nodes completed

**Causes**:
- Invalid workflow structure
- Missing dependencies
- Team engine not initialized

**Solution**:
```python
# Validate workflow before execution
errors = workflow.validate()
if errors:
    print("Workflow validation errors:")
    for error in errors:
        print(f"  - {error}")

# Check team engine
if not team_engine:
    team_engine = TeamExecutionEngineV2SplitMode(
        personas_dir="./src/personas/definitions"
    )
```

### Issue: Frontend Phase Doesn't Receive Contracts

**Symptoms**:
- Frontend phase starts without contract information
- No API specifications available

**Causes**:
- Design phase didn't create contracts
- Context not passed correctly

**Solution**:
```python
# Check design phase output
status = await dagClient.getExecutionStatus(execution_id)
design_node = next(n for n in status.node_states
                  if n.node_id == 'phase_design')

if 'contracts' not in design_node.output:
    print("Design phase did not create contracts")

# Ensure PhaseNodeExecutor includes contracts
# in _build_phase_requirement()
```

### Issue: Parallel Phases Don't Execute Simultaneously

**Symptoms**:
- Backend and frontend execute sequentially
- No time savings

**Causes**:
- Workflow not configured for parallel execution
- Dependencies incorrect

**Solution**:
```python
# Check node execution mode
backend_node = workflow.nodes['phase_backend_development']
print(f"Execution mode: {backend_node.execution_mode}")
# Should be: ExecutionMode.PARALLEL

# Check dependencies
print(f"Backend deps: {backend_node.dependencies}")
print(f"Frontend deps: {frontend_node.dependencies}")
# Both should depend only on "phase_design", not each other
```

### Issue: Context Not Persisting

**Symptoms**:
- Cannot resume workflow
- Context lost after restart

**Causes**:
- Context store not configured
- Database not connected

**Solution**:
```python
# Use database-backed store
from database.workflow_store import DatabaseWorkflowContextStore

context_store = DatabaseWorkflowContextStore()

# Verify database connection
from database.config import db_engine
if not db_engine._initialized:
    db_engine.initialize()

# Check context saved
contexts = await context_store.list_executions()
print(f"Stored executions: {len(contexts)}")
```

### Issue: WebSocket Connection Fails

**Symptoms**:
- WebSocket closes immediately
- No real-time updates

**Causes**:
- Incorrect WebSocket URL
- CORS issues
- Server not running

**Solution**:
```typescript
// Check WebSocket URL format
// HTTP: http://localhost:8003
// WebSocket: ws://localhost:8003/ws/workflow/{execution_id}

// The client library handles this automatically
const ws = dagClient.connectWebSocket('sdlc_parallel', {
  onError: (error) => {
    console.error('WebSocket error:', error);
    // Fallback to polling
  }
});

// Always implement polling as backup
```

### Issue: Validation Failures Block Workflow

**Symptoms**:
- Workflow stops at validation node
- Phase completed but validation failed

**Causes**:
- Quality gates not met
- `fail_on_validation_error=True`

**Solution**:
```python
# Check validation report
status = await dagClient.getExecutionStatus(execution_id)
validation_node = next(n for n in status.node_states
                      if 'validate_' in n.node_id)

print("Validation status:", validation_node.status)
print("Validation output:", validation_node.output)

# Option 1: Fix issues and retry
# Option 2: Disable strict validation
workflow = generate_validated_parallel_workflow(
    enable_validation=True,
    fail_on_validation_error=False  # Warnings only
)
```

---

## Summary

### Key Takeaways

1. **Initiation**:
   - REST API: `POST /api/workflows/{id}/execute`
   - Python: `DAGExecutor.execute()`
   - 5 workflow types available

2. **Contracts**:
   - Defined in design phase
   - Enable parallel backend/frontend work
   - Version controlled with breaking change detection

3. **Context**:
   - Automatic data flow between nodes
   - Dependency outputs available to all dependents
   - Artifacts tracked separately
   - Global context for workflow-wide data

4. **Visibility**:
   - REST API for status polling
   - WebSocket for real-time updates
   - Complete node-level progress
   - Validation reports for quality gates

5. **Frontend Engineers**:
   - Clear task expectations from contracts
   - Full context from previous phases
   - Real-time progress visibility
   - Quality validation feedback

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-11
**Status**: ✅ Complete

**Related Documentation**:
- [Frontend Integration Guide](./FRONTEND_DAG_INTEGRATION_GUIDE.md)
- [Frontend Quick Start](./FRONTEND_QUICK_START.md)
- [Frontend Integration Summary](./FRONTEND_INTEGRATION_SUMMARY.md)
- [DAG Architecture Guide](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md)
- [DAG Migration Guide](./AGENT3_DAG_MIGRATION_GUIDE.md)

---

**Happy Building! 🚀**
