"""
Pytest Configuration and Shared Fixtures
Provides fixtures for DDF Tri-Modal System testing
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Create logs directory if it doesn't exist
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test isolation"""
    temp_path = tempfile.mkdtemp(prefix="ddf_test_")
    yield Path(temp_path)
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_output_dir(temp_dir):
    """Create temporary output directory"""
    output_dir = temp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_iteration_id():
    """Generate mock iteration ID"""
    return "Iter-20251013-1400-001"


@pytest.fixture
def mock_team_id():
    """Generate mock team ID"""
    return "test_team_001"


@pytest.fixture
def mock_agent_profiles():
    """Generate mock agent profiles for capability matching"""
    return [
        {
            "agent_id": "agent_001",
            "name": "Senior Backend Developer",
            "availability_status": "available",
            "wip_limit": 3,
            "recent_quality_score": 0.95,
            "skills": [
                {"skill_id": "Backend:Python:FastAPI", "proficiency": 5},
                {"skill_id": "Backend:Python:AsyncIO", "proficiency": 4},
            ]
        },
        {
            "agent_id": "agent_002",
            "name": "Frontend Developer",
            "availability_status": "available",
            "wip_limit": 3,
            "recent_quality_score": 0.90,
            "skills": [
                {"skill_id": "Web:React:Hooks", "proficiency": 5},
                {"skill_id": "Web:React:StateManagement", "proficiency": 4},
            ]
        },
        {
            "agent_id": "agent_003",
            "name": "Architect",
            "availability_status": "available",
            "wip_limit": 2,
            "recent_quality_score": 0.98,
            "skills": [
                {"skill_id": "Architecture:APIDesign", "proficiency": 5},
                {"skill_id": "Architecture:DatabaseDesign", "proficiency": 5},
            ]
        },
    ]


# ============================================================================
# DDE Stream Fixtures
# ============================================================================

@pytest.fixture
def sample_execution_manifest():
    """Sample execution manifest for testing"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "timestamp": "2025-10-13T14:00:00Z",
        "project": "TestProject",
        "constraints": {
            "security_standard": "OWASP-L2",
            "library_policy": "InternalOnly",
            "runtime": "Python3.11"
        },
        "policies": [
            {
                "id": "coverage >= 70%",
                "severity": "BLOCKING"
            }
        ],
        "nodes": [
            {
                "id": "IF.AuthAPI",
                "type": "interface",
                "capability": "Architecture:APIDesign",
                "outputs": ["openapi.yaml"],
                "gates": ["openapi-lint", "semver"],
                "estimated_effort": 60
            },
            {
                "id": "BE.AuthService",
                "type": "impl",
                "capability": "Backend:Python:FastAPI",
                "depends_on": ["IF.AuthAPI"],
                "gates": ["unit-tests", "coverage", "contract-tests"],
                "estimated_effort": 120
            }
        ]
    }


@pytest.fixture
def sample_artifact_metadata():
    """Sample artifact metadata"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "node_id": "BE.AuthService",
        "artifact_name": "auth_service.py",
        "capability": "Backend:Python:FastAPI",
        "contract_version": "v1.0",
        "sha256": "abc123def456",
        "timestamp": "2025-10-13T14:30:00Z"
    }


# ============================================================================
# BDV Stream Fixtures
# ============================================================================

@pytest.fixture
def sample_feature_file():
    """Sample Gherkin feature file content"""
    return """
@contract:AuthAPI:v1.0
Feature: User Authentication
  As a registered user
  I want to authenticate with email and password
  So that I can access protected resources

  Background:
    Given the system has registered users
    And the AuthAPI v1.0 contract is available

  Scenario: Successful login with valid credentials
    Given a registered user "alice@example.com" with password "p@ss123"
    When she requests a token via POST /auth/token with:
      | email             | password |
      | alice@example.com | p@ss123  |
    Then the response status is 200
    And the response body contains a JWT token
    And the token has claim "sub=alice@example.com"

  Scenario: Failed login with invalid password
    Given a registered user "alice@example.com" with password "p@ss123"
    When she requests a token via POST /auth/token with:
      | email             | password       |
      | alice@example.com | wrong_password |
    Then the response status is 401
    And the response body contains error "Invalid credentials"
"""


@pytest.fixture
def sample_bdv_result():
    """Sample BDV test result"""
    return {
        "total_scenarios": 10,
        "passed": 8,
        "failed": 1,
        "skipped": 1,
        "duration": 45.2,
        "flake_rate": 0.05,
        "details": [
            {
                "scenario_id": "auth/authentication.feature::Scenario: Successful login",
                "status": "passed",
                "duration": 2.5
            },
            {
                "scenario_id": "auth/authentication.feature::Scenario: Failed login",
                "status": "passed",
                "duration": 2.1
            }
        ]
    }


# ============================================================================
# ACC Stream Fixtures
# ============================================================================

@pytest.fixture
def sample_import_graph():
    """Sample import graph for testing"""
    return {
        "nodes": [
            {"id": "module_a", "path": "src/module_a.py"},
            {"id": "module_b", "path": "src/module_b.py"},
            {"id": "module_c", "path": "src/module_c.py"},
        ],
        "edges": [
            {"from": "module_a", "to": "module_b"},
            {"from": "module_b", "to": "module_c"},
        ]
    }


@pytest.fixture
def sample_architectural_manifest():
    """Sample architectural manifest"""
    return {
        "project": "TestProject",
        "version": "1.0.0",
        "components": [
            {
                "name": "Presentation",
                "paths": ["frontend/src/components/"]
            },
            {
                "name": "BusinessLogic",
                "paths": ["backend/src/services/"]
            },
            {
                "name": "DataAccess",
                "paths": ["backend/src/repositories/"]
            }
        ],
        "rules": [
            {
                "id": "R1",
                "type": "dependency",
                "description": "Presentation can only call BusinessLogic",
                "rule": "Presentation: CAN_CALL(BusinessLogic)",
                "severity": "BLOCKING"
            },
            {
                "id": "R2",
                "type": "dependency",
                "description": "Presentation must not call DataAccess directly",
                "rule": "Presentation: MUST_NOT_CALL(DataAccess)",
                "severity": "BLOCKING"
            }
        ]
    }


@pytest.fixture
def sample_acc_violation():
    """Sample architectural violation"""
    return {
        "rule_id": "R2",
        "source_module": "frontend/src/components/UserList.tsx",
        "target_module": "backend/src/repositories/UserRepository.py",
        "message": "Presentation layer must not call DataAccess directly",
        "severity": "BLOCKING"
    }


# ============================================================================
# Tri-Modal Convergence Fixtures
# ============================================================================

@pytest.fixture
def sample_dde_audit_result():
    """Sample DDE audit result"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "passed": True,
        "score": 1.0,
        "details": {
            "nodes_complete": ["IF.AuthAPI", "BE.AuthService"],
            "nodes_missing": [],
            "gates_passed": [("BE.AuthService", "unit-tests"), ("BE.AuthService", "coverage")],
            "gates_failed": [],
            "artifacts_stamped": [("BE.AuthService", "auth_service.py")],
            "artifacts_missing": [],
            "contracts_locked": ["IF.AuthAPI"]
        }
    }


@pytest.fixture
def sample_bdv_audit_result():
    """Sample BDV audit result"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "passed": True,
        "total_scenarios": 10,
        "passed_scenarios": 10,
        "failed_scenarios": 0,
        "flake_rate": 0.05,
        "contract_mismatches": [],
        "coverage": 0.75
    }


@pytest.fixture
def sample_acc_audit_result():
    """Sample ACC audit result"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "passed": True,
        "blocking_violations": 0,
        "warning_violations": 2,
        "cycles": [],
        "coupling_scores": {
            "BusinessLogic": {"instability": 0.45}
        }
    }


@pytest.fixture
def sample_tri_audit_result_all_pass(
    sample_dde_audit_result,
    sample_bdv_audit_result,
    sample_acc_audit_result
):
    """Sample tri-modal audit result with ALL_PASS verdict"""
    return {
        "iteration_id": "Iter-20251013-1400-001",
        "verdict": "ALL_PASS",
        "can_deploy": True,
        "diagnosis": "All audits passed. Safe to deploy.",
        "recommendations": [],
        "dde_passed": True,
        "bdv_passed": True,
        "acc_passed": True,
        "dde_details": sample_dde_audit_result,
        "bdv_details": sample_bdv_audit_result,
        "acc_details": sample_acc_audit_result
    }


# ============================================================================
# Quality Fabric Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_quality_fabric_response():
    """Mock Quality Fabric API response"""
    return {
        "test_files": [
            {
                "file_path": "tests/test_module.py",
                "content": '''"""Generated test file"""
import pytest

def test_example():
    """Example test case"""
    assert True
''',
                "coverage_estimate": 0.92
            }
        ],
        "summary": {
            "tests_generated": 25,
            "estimated_coverage": 0.92
        }
    }


# ============================================================================
# Async Helpers
# ============================================================================

@pytest.fixture
async def async_client():
    """Async HTTP client for testing APIs"""
    import httpx
    async with httpx.AsyncClient() as client:
        yield client


# ============================================================================
# Database Fixtures (if needed)
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url():
    """Test database URL"""
    return "postgresql://test:test@localhost:5432/ddf_test"


# ============================================================================
# Cleanup Hooks
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Auto-cleanup temporary files after each test"""
    yield
    # Cleanup logic here if needed
    pass


# ============================================================================
# Performance Measurement Fixtures
# ============================================================================

@pytest.fixture
def measure_time():
    """Measure test execution time"""
    import time

    class Timer:
        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            self.end = time.time()
            self.duration = self.end - self.start

    return Timer()
