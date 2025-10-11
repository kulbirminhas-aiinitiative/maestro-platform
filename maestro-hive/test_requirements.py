#!/usr/bin/env python3
"""
Test Requirements - Simple Requirements for Quick Testing

Provides 3 levels of requirements with minimal complexity for fast test execution:
- MINIMAL: Single feature (1-2 phases, ~30 seconds per phase)
- SIMPLE: Basic app (3-4 phases, ~45 seconds per phase)
- STANDARD: Full workflow (all 5 phases, ~60 seconds per phase)

All requirements designed to:
- Execute quickly with minimal personas (1-2 per phase)
- Generate minimal artifacts
- Test core functionality without overhead
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class TestRequirement:
    """Test requirement with metadata"""
    id: str
    name: str
    description: str
    complexity: str
    estimated_phases: List[str]
    estimated_duration_per_phase_seconds: int
    personas_per_phase: int
    expected_artifacts: List[str]
    can_skip_phases: List[str]  # Phases that can be skipped for this requirement


# =============================================================================
# MINIMAL REQUIREMENT - For Quick Tests
# =============================================================================

MINIMAL_REQUIREMENT = TestRequirement(
    id="minimal_01",
    name="Single Health Check Endpoint",
    description="""
Create a single API endpoint that returns health status.

Requirement:
- Single GET /health endpoint
- Returns JSON: {"status": "ok", "timestamp": "<current_time>"}
- No database required
- No authentication required
- No frontend required

Implementation:
- Use FastAPI (Python)
- Single file: main.py
- Run with: uvicorn main:app

Expected Output:
- main.py file with endpoint
- requirements.txt with FastAPI dependency

This is the SIMPLEST possible requirement to test basic phase execution.
""",
    complexity="minimal",
    estimated_phases=["requirements", "implementation"],  # Can skip design, testing, deployment
    estimated_duration_per_phase_seconds=30,
    personas_per_phase=1,
    expected_artifacts=["main.py", "requirements.txt"],
    can_skip_phases=["design", "testing", "deployment"]  # For minimal, these can be skipped
)


# =============================================================================
# SIMPLE REQUIREMENT - For Standard Tests
# =============================================================================

SIMPLE_REQUIREMENT = TestRequirement(
    id="simple_01",
    name="Basic TODO API",
    description="""
Create a simple TODO API with basic CRUD operations.

Requirements:
- POST /todos - Create a new todo
- GET /todos - List all todos
- GET /todos/:id - Get specific todo
- PUT /todos/:id - Update todo
- DELETE /todos/:id - Delete todo

Data Model:
- Todo: {id, title, description, completed, created_at}

Technology:
- Backend: FastAPI (Python)
- Database: SQLite (simple file-based)
- No authentication needed
- No frontend needed

Expected Deliverables:
- main.py (API implementation)
- database.py (SQLite setup)
- models.py (Pydantic models)
- requirements.txt
- README.md with API documentation

Estimated Complexity: Simple CRUD application
Estimated Phases: Requirements, Design, Implementation, Testing
""",
    complexity="simple",
    estimated_phases=["requirements", "design", "implementation", "testing"],
    estimated_duration_per_phase_seconds=45,
    personas_per_phase=2,
    expected_artifacts=[
        "main.py", "database.py", "models.py",
        "requirements.txt", "README.md", "tests.py"
    ],
    can_skip_phases=["deployment"]  # Can skip deployment for simple local testing
)


# =============================================================================
# STANDARD REQUIREMENT - For Complete Workflow Tests
# =============================================================================

STANDARD_REQUIREMENT = TestRequirement(
    id="standard_01",
    name="Full-Stack Task Management App",
    description="""
Create a complete task management application with backend, frontend, and deployment.

Backend Requirements (FastAPI):
- User authentication (JWT tokens)
- User registration and login
- CRUD operations for tasks
- Task assignment to users
- Task filtering (by status, assigned user)
- SQLite database

Frontend Requirements (React):
- Login/Register page
- Dashboard showing user's tasks
- Task creation form
- Task editing form
- Task list with filters
- Simple responsive design

Data Models:
- User: {id, email, password_hash, name, created_at}
- Task: {id, title, description, status, assigned_to, created_at, updated_at}

Technology Stack:
- Backend: Python FastAPI
- Frontend: React + TypeScript
- Database: SQLite
- Authentication: JWT tokens
- Deployment: Docker container

Expected Deliverables:

Backend:
- main.py (FastAPI app)
- models.py (SQLAlchemy models)
- auth.py (Authentication logic)
- database.py (DB connection)
- requirements.txt

Frontend:
- src/App.tsx
- src/components/TaskList.tsx
- src/components/TaskForm.tsx
- src/components/Login.tsx
- package.json

Deployment:
- Dockerfile
- docker-compose.yml
- README.md

Testing:
- Backend tests (pytest)
- Frontend tests (Jest)
- Integration tests

This is a STANDARD full-stack application covering all SDLC phases.
""",
    complexity="standard",
    estimated_phases=["requirements", "design", "implementation", "testing", "deployment"],
    estimated_duration_per_phase_seconds=60,
    personas_per_phase=3,
    expected_artifacts=[
        # Backend
        "backend/main.py", "backend/models.py", "backend/auth.py",
        "backend/database.py", "backend/requirements.txt",
        # Frontend
        "frontend/src/App.tsx", "frontend/src/components/TaskList.tsx",
        "frontend/package.json",
        # Deployment
        "Dockerfile", "docker-compose.yml",
        # Documentation
        "README.md", "API_DOCUMENTATION.md",
        # Tests
        "backend/tests/test_api.py", "frontend/src/App.test.tsx"
    ],
    can_skip_phases=[]  # Standard requirement should go through all phases
)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_requirement(requirement_id: str) -> TestRequirement:
    """Get requirement by ID"""
    requirements = {
        "minimal_01": MINIMAL_REQUIREMENT,
        "simple_01": SIMPLE_REQUIREMENT,
        "standard_01": STANDARD_REQUIREMENT
    }
    return requirements.get(requirement_id)


def get_requirement_by_complexity(complexity: str) -> TestRequirement:
    """Get requirement by complexity level"""
    requirements = {
        "minimal": MINIMAL_REQUIREMENT,
        "simple": SIMPLE_REQUIREMENT,
        "standard": STANDARD_REQUIREMENT
    }
    return requirements.get(complexity)


def list_all_requirements() -> List[TestRequirement]:
    """List all available test requirements"""
    return [
        MINIMAL_REQUIREMENT,
        SIMPLE_REQUIREMENT,
        STANDARD_REQUIREMENT
    ]


def get_requirement_summary() -> str:
    """Get summary of all requirements"""
    reqs = list_all_requirements()

    summary = []
    summary.append("\n" + "="*80)
    summary.append("TEST REQUIREMENTS SUMMARY")
    summary.append("="*80 + "\n")

    for req in reqs:
        summary.append(f"📋 {req.id.upper()}: {req.name}")
        summary.append(f"   Complexity: {req.complexity}")
        summary.append(f"   Phases: {len(req.estimated_phases)} ({', '.join(req.estimated_phases)})")
        summary.append(f"   Duration per phase: ~{req.estimated_duration_per_phase_seconds}s")
        summary.append(f"   Personas per phase: {req.personas_per_phase}")
        summary.append(f"   Expected artifacts: {len(req.expected_artifacts)}")
        if req.can_skip_phases:
            summary.append(f"   Can skip: {', '.join(req.can_skip_phases)}")
        summary.append("")

    summary.append("="*80 + "\n")

    return "\n".join(summary)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print(get_requirement_summary())

    # Example: Get minimal requirement
    minimal = get_requirement_by_complexity("minimal")
    print(f"\nMinimal Requirement Description:")
    print(f"{minimal.description}")

    # Example: Get simple requirement
    simple = get_requirement_by_complexity("simple")
    print(f"\nSimple Requirement: {simple.name}")
    print(f"Expected phases: {simple.estimated_phases}")
    print(f"Can skip: {simple.can_skip_phases}")
