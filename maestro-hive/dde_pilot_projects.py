#!/usr/bin/env python3
"""
DDE Pilot Projects Configuration
MD-759: Execute 3 pilot projects via DDE

This module defines 3 pilot projects to validate the DDE system:
1. API Gateway Microservice - Tests team composition and contract management
2. Data Analytics Dashboard - Tests parallel execution and artifact generation
3. Mobile App Backend - Tests full SDLC blueprint with BDV/ACC integration

Usage:
  python dde_pilot_projects.py [pilot_id]

  pilot_id: 1, 2, or 3 (default: run all)
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

# Import DDE Orchestrator
try:
    from dde_orchestrator import TeamExecutionEngine, ExecutionConfig
    DDE_AVAILABLE = True
except ImportError:
    DDE_AVAILABLE = False
    print("Warning: dde_orchestrator not available, running in config-only mode")

# ============================================================================
# Pilot Project Definitions
# ============================================================================

@dataclass
class PilotProject:
    """Definition of a DDE pilot project"""
    id: str
    name: str
    description: str
    blueprint: str
    team_size: int
    phases: List[str]
    requirements: str
    expected_artifacts: List[str]
    success_criteria: Dict[str, Any]
    config: Dict[str, Any]
    test_scope: Dict[str, Any] = None  # New: Explicit Test Scope for TaaS

# Pilot 1: API Gateway Microservice
PILOT_1_API_GATEWAY = PilotProject(
    id="pilot-001",
    name="API Gateway Microservice",
    description="Build a lightweight API gateway with rate limiting, authentication, and request routing",
    blueprint="api-development",
    team_size=4,
    phases=["design", "implementation", "documentation", "testing", "deployment"],
    requirements="""
    Build an API Gateway microservice with:
    - Rate limiting (token bucket algorithm)
    - JWT authentication middleware
    - Request routing to multiple backends
    - Health check endpoints
    - Prometheus metrics
    - OpenAPI documentation

    Tech Stack: Node.js, Express, Redis, Docker
    """,
    expected_artifacts=[
        "Architecture Design Document",
        "API Specification (OpenAPI 3.0)",
        "Source Code (gateway service)",
        "Unit Tests (>80% coverage)",
        "Integration Tests",
        "Docker Compose configuration",
        "Deployment Guide"
    ],
    success_criteria={
        "min_test_coverage": 80,
        "max_response_time_ms": 50,
        "required_endpoints": ["/health", "/metrics", "/api/*"],
        "documentation_completeness": 90
    },
    config={
        "parallel_execution": True,
        "contract_validation": True,
        "enable_bdv": True,
        "enable_acc": True
    },
    test_scope={
        "project_id": "pilot-001",
        "scope_id": "scope-pilot-001-v2",
        "environment": {
            "type": "docker",
            "image": "node:18-alpine",
            "dependencies": ["redis"]
        },
        "lifecycle": {
            "setup": ["npm install", "docker-compose up -d redis"],
            "teardown": ["docker-compose down"]
        },
        "scenarios": [
            {
                "id": "API-001",
                "name": "Health Check",
                "description": "Verify /health endpoint returns 200 OK and status: up",
                "test_type": "integration",
                "target_component": "gateway",
                "execution": {
                    "command": "curl -f http://localhost:3000/health"
                }
            },
            {
                "id": "API-002",
                "name": "Rate Limiting",
                "description": "Verify 429 Too Many Requests after 100 req/min",
                "test_type": "e2e",
                "target_component": "gateway",
                "execution": {
                    "command": "ab -n 101 -c 10 http://localhost:3000/api/test"
                }
            },
            {
                "id": "SEC-001",
                "name": "JWT Auth",
                "description": "Verify 401 Unauthorized for missing header",
                "test_type": "security",
                "target_component": "gateway",
                "execution": {
                    "command": "curl -I http://localhost:3000/api/protected"
                }
            }
        ]
    }
)

# Pilot 2: Data Analytics Dashboard
PILOT_2_ANALYTICS_DASHBOARD = PilotProject(
    id="pilot-002",
    name="Data Analytics Dashboard",
    description="Create an interactive data analytics dashboard with real-time visualizations",
    blueprint="data-pipeline",
    team_size=5,
    phases=["data_modeling", "backend_api", "visualization", "testing", "deployment"],
    requirements="""
    Build a Data Analytics Dashboard with:
    - Real-time data ingestion pipeline
    - Time-series aggregations (hourly, daily, weekly)
    - Interactive charts (line, bar, pie, heatmap)
    - Custom date range filtering
    - Export to CSV/PDF
    - User dashboard customization

    Tech Stack: React, D3.js, Python FastAPI, PostgreSQL, Redis
    """,
    expected_artifacts=[
        "Data Model Schema",
        "ETL Pipeline Documentation",
        "Backend API Implementation",
        "Frontend Dashboard Components",
        "Chart Library Integration",
        "Performance Tests",
        "User Guide"
    ],
    success_criteria={
        "dashboard_load_time_ms": 2000,
        "chart_render_time_ms": 500,
        "data_freshness_seconds": 60,
        "supported_chart_types": 4
    },
    config={
        "parallel_execution": True,
        "contract_validation": True,
        "enable_bdv": True,
        "enable_acc": True,
        "data_quality_checks": True
    }
)

# Pilot 3: Mobile App Backend
PILOT_3_MOBILE_BACKEND = PilotProject(
    id="pilot-003",
    name="Mobile App Backend",
    description="Develop a full-featured mobile app backend with user management and notifications",
    blueprint="sdlc-standard",
    team_size=6,
    phases=["requirements", "design", "development", "testing", "deployment", "monitoring"],
    requirements="""
    Build a Mobile App Backend with:
    - User registration and authentication (OAuth2, JWT)
    - Profile management with avatar upload
    - Push notification service (FCM, APNS)
    - In-app messaging system
    - Activity feed with pagination
    - Admin dashboard for user management

    Tech Stack: Python Django, PostgreSQL, Redis, Celery, S3, Firebase
    """,
    expected_artifacts=[
        "Requirements Specification",
        "System Architecture Document",
        "Database Schema",
        "REST API Implementation",
        "Push Notification Service",
        "Admin Dashboard",
        "Unit & Integration Tests",
        "Deployment Scripts",
        "Monitoring Dashboard"
    ],
    success_criteria={
        "api_response_time_p95_ms": 200,
        "auth_flow_success_rate": 99.5,
        "notification_delivery_rate": 98,
        "test_coverage": 85,
        "documentation_score": 90
    },
    config={
        "parallel_execution": True,
        "contract_validation": True,
        "enable_bdv": True,
        "enable_acc": True,
        "full_sdlc": True,
        "enable_hitl_gates": True
    }
)

# All pilots
PILOT_PROJECTS = [
    PILOT_1_API_GATEWAY,
    PILOT_2_ANALYTICS_DASHBOARD,
    PILOT_3_MOBILE_BACKEND
]

# ============================================================================
# Execution Functions
# ============================================================================

async def execute_pilot(pilot: PilotProject) -> Dict[str, Any]:
    """Execute a single pilot project through DDE"""

    print(f"\n{'='*60}")
    print(f"PILOT PROJECT: {pilot.name}")
    print(f"ID: {pilot.id}")
    print(f"Blueprint: {pilot.blueprint}")
    print(f"Team Size: {pilot.team_size}")
    print(f"{'='*60}\n")

    start_time = datetime.utcnow()

    result = {
        "pilot_id": pilot.id,
        "name": pilot.name,
        "status": "pending",
        "started_at": start_time.isoformat(),
        "completed_at": None,
        "phases_completed": [],
        "artifacts_generated": [],
        "metrics": {},
        "errors": []
    }

    if not DDE_AVAILABLE:
        # Config-only mode - simulate execution
        print("Running in simulation mode (DDE not available)")

        for phase in pilot.phases:
            print(f"  [SIM] Phase: {phase}")
            result["phases_completed"].append(phase)
            await asyncio.sleep(0.1)

        for artifact in pilot.expected_artifacts:
            print(f"  [SIM] Artifact: {artifact}")
            result["artifacts_generated"].append(artifact)

        result["status"] = "simulated"
        result["metrics"] = {
            "simulated": True,
            "phases_count": len(pilot.phases),
            "artifacts_count": len(pilot.expected_artifacts)
        }
    else:
        # Real DDE execution
        try:
            config = ExecutionConfig(
                mode="parallel" if pilot.config.get("parallel_execution") else "sequential",
                timeout_seconds=3600,
                require_all_contracts=pilot.config.get("contract_validation", True),
                max_parallel_agents=pilot.team_size
            )

            engine = TeamExecutionEngine(config)

            # Execute through DDE
            execution_result = await engine.execute(
                requirement=pilot.requirements,
                blueprint_name=pilot.blueprint,
                project_config=pilot.config
            )

            result["status"] = "completed" if execution_result.success else "failed"
            result["phases_completed"] = execution_result.phases_completed
            result["artifacts_generated"] = execution_result.artifacts
            result["metrics"] = execution_result.metrics

            if execution_result.errors:
                result["errors"] = execution_result.errors

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            print(f"  [ERROR] {e}")

    end_time = datetime.utcnow()
    result["completed_at"] = end_time.isoformat()
    result["duration_seconds"] = (end_time - start_time).total_seconds()

    # Print summary
    print(f"\nPilot {pilot.id} Summary:")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration_seconds']:.2f}s")
    print(f"  Phases: {len(result['phases_completed'])}/{len(pilot.phases)}")
    print(f"  Artifacts: {len(result['artifacts_generated'])}/{len(pilot.expected_artifacts)}")

    return result

async def execute_all_pilots() -> List[Dict[str, Any]]:
    """Execute all pilot projects"""
    results = []

    print("\n" + "="*60)
    print("DDE PILOT PROJECTS EXECUTION")
    print(f"Total Pilots: {len(PILOT_PROJECTS)}")
    print("="*60)

    for pilot in PILOT_PROJECTS:
        result = await execute_pilot(pilot)
        results.append(result)

    # Summary report
    print("\n" + "="*60)
    print("EXECUTION SUMMARY")
    print("="*60)

    successful = sum(1 for r in results if r["status"] in ["completed", "simulated"])
    failed = sum(1 for r in results if r["status"] in ["failed", "error"])

    print(f"Successful: {successful}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")

    total_artifacts = sum(len(r["artifacts_generated"]) for r in results)
    total_phases = sum(len(r["phases_completed"]) for r in results)

    print(f"Total Phases Completed: {total_phases}")
    print(f"Total Artifacts Generated: {total_artifacts}")

    return results

def get_pilot_config(pilot_id: int) -> Dict[str, Any]:
    """Get configuration for a specific pilot"""
    if pilot_id < 1 or pilot_id > len(PILOT_PROJECTS):
        raise ValueError(f"Invalid pilot_id: {pilot_id}. Must be 1-{len(PILOT_PROJECTS)}")

    pilot = PILOT_PROJECTS[pilot_id - 1]
    return asdict(pilot)

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pilot_id = int(sys.argv[1])
        if pilot_id < 1 or pilot_id > len(PILOT_PROJECTS):
            print(f"Error: pilot_id must be 1-{len(PILOT_PROJECTS)}")
            sys.exit(1)

        pilot = PILOT_PROJECTS[pilot_id - 1]
        result = asyncio.run(execute_pilot(pilot))
    else:
        results = asyncio.run(execute_all_pilots())

    print("\nPilot projects execution complete!")
