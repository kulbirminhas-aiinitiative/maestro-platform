"""
Example Workflow Service with UTCP Support

This demonstrates how to create a microservice that:
1. Uses MaestroAPI with UTCP support
2. Exposes workflow capabilities as UTCP tools
3. Can be discovered and called by Claude
"""

from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from maestro_core_api import APIConfig
from maestro_core_api.utcp_extensions import UTCPEnabledAPI


# Models
class WorkflowComplexity(str, Enum):
    """Workflow complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class WorkflowType(str, Enum):
    """Types of workflows."""
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DEVELOPMENT = "development"


class WorkflowRequest(BaseModel):
    """Request to create a workflow."""
    requirements: str = Field(..., description="Detailed workflow requirements")
    complexity: WorkflowComplexity = Field(
        WorkflowComplexity.MODERATE,
        description="Expected complexity level"
    )
    workflow_type: WorkflowType = Field(..., description="Type of workflow to create")
    tags: List[str] = Field(default_factory=list, description="Optional tags")


class WorkflowResponse(BaseModel):
    """Workflow creation response."""
    workflow_id: str
    name: str
    steps: List[Dict[str, Any]]
    estimated_duration: int  # minutes
    complexity: WorkflowComplexity
    status: str


class TeamComposition(BaseModel):
    """Team composition for workflow."""
    architect: bool = True
    developers: int = Field(2, ge=1, le=10)
    testers: int = Field(1, ge=0, le=5)
    devops: int = Field(1, ge=0, le=3)


class TeamRequest(BaseModel):
    """Request to assemble a team."""
    requirements: str = Field(..., description="Project requirements")
    complexity: WorkflowComplexity = Field(
        WorkflowComplexity.MODERATE,
        description="Project complexity"
    )
    composition: Optional[TeamComposition] = None


class TeamResponse(BaseModel):
    """Team assembly response."""
    team_id: str
    members: List[Dict[str, str]]
    capabilities: List[str]
    estimated_velocity: str


# Create UTCP-enabled API
config = APIConfig(
    title="Workflow Engine Service",
    description="MAESTRO Workflow Engine with UTCP support - Creates and manages workflows",
    service_name="workflow-engine",
    version="1.0.0",
    host="0.0.0.0",
    port=8001
)

api = UTCPEnabledAPI(
    config,
    base_url="http://localhost:8001",
    enable_utcp_execution=True
)


# Workflow endpoints
@api.post(
    "/workflows/create",
    response_model=WorkflowResponse,
    summary="Create a new workflow",
    description="Creates a comprehensive workflow based on requirements and complexity",
    tags=["Workflows"]
)
async def create_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """
    Create a new workflow based on requirements.

    This endpoint analyzes the requirements and complexity to generate
    an appropriate workflow with steps, timeline, and resources.
    """
    # Simulate workflow creation
    workflow_id = f"wf-{hash(request.requirements) % 10000:04d}"

    # Generate steps based on complexity
    steps_map = {
        WorkflowComplexity.SIMPLE: [
            {"step": 1, "name": "Setup", "duration": 5},
            {"step": 2, "name": "Execute", "duration": 10},
            {"step": 3, "name": "Validate", "duration": 5}
        ],
        WorkflowComplexity.MODERATE: [
            {"step": 1, "name": "Planning", "duration": 15},
            {"step": 2, "name": "Setup Environment", "duration": 10},
            {"step": 3, "name": "Development", "duration": 30},
            {"step": 4, "name": "Testing", "duration": 20},
            {"step": 5, "name": "Deployment", "duration": 15}
        ],
        WorkflowComplexity.COMPLEX: [
            {"step": 1, "name": "Requirements Analysis", "duration": 30},
            {"step": 2, "name": "Architecture Design", "duration": 45},
            {"step": 3, "name": "Environment Setup", "duration": 20},
            {"step": 4, "name": "Implementation", "duration": 120},
            {"step": 5, "name": "Unit Testing", "duration": 30},
            {"step": 6, "name": "Integration Testing", "duration": 40},
            {"step": 7, "name": "Performance Testing", "duration": 30},
            {"step": 8, "name": "Security Audit", "duration": 25},
            {"step": 9, "name": "Deployment", "duration": 20}
        ],
        WorkflowComplexity.ENTERPRISE: [
            {"step": 1, "name": "Stakeholder Alignment", "duration": 60},
            {"step": 2, "name": "Requirements Gathering", "duration": 90},
            {"step": 3, "name": "Architecture Review", "duration": 120},
            {"step": 4, "name": "Security Planning", "duration": 60},
            {"step": 5, "name": "Infrastructure Setup", "duration": 90},
            {"step": 6, "name": "Development Phase 1", "duration": 240},
            {"step": 7, "name": "Comprehensive Testing", "duration": 180},
            {"step": 8, "name": "Security Penetration Testing", "duration": 120},
            {"step": 9, "name": "Performance Optimization", "duration": 90},
            {"step": 10, "name": "Documentation", "duration": 60},
            {"step": 11, "name": "Staged Deployment", "duration": 120},
            {"step": 12, "name": "Monitoring Setup", "duration": 45}
        ]
    }

    steps = steps_map[request.complexity]
    total_duration = sum(step["duration"] for step in steps)

    return WorkflowResponse(
        workflow_id=workflow_id,
        name=f"{request.workflow_type.value.title()} Workflow",
        steps=steps,
        estimated_duration=total_duration,
        complexity=request.complexity,
        status="created"
    )


@api.post(
    "/teams/assemble",
    response_model=TeamResponse,
    summary="Assemble a team",
    description="Creates a team composition based on project requirements and complexity",
    tags=["Teams"]
)
async def assemble_team(request: TeamRequest) -> TeamResponse:
    """
    Assemble a team for the project.

    Analyzes requirements and complexity to suggest optimal team composition.
    """
    team_id = f"team-{hash(request.requirements) % 10000:04d}"

    # Use provided composition or create default
    composition = request.composition or TeamComposition()

    # Build team members
    members = []

    if composition.architect:
        members.append({"role": "Architect", "name": "Senior Tech Lead", "specialization": "System Design"})

    for i in range(composition.developers):
        specializations = ["Backend", "Frontend", "Full-Stack", "Mobile"]
        members.append({
            "role": "Developer",
            "name": f"Developer {i+1}",
            "specialization": specializations[i % len(specializations)]
        })

    for i in range(composition.testers):
        specializations = ["QA Automation", "Manual Testing", "Performance Testing"]
        members.append({
            "role": "QA Engineer",
            "name": f"QA Engineer {i+1}",
            "specialization": specializations[i % len(specializations)]
        })

    for i in range(composition.devops):
        members.append({
            "role": "DevOps Engineer",
            "name": f"DevOps Engineer {i+1}",
            "specialization": "CI/CD & Infrastructure"
        })

    # Determine capabilities
    capabilities = [
        f"{request.workflow_type.value.title()} workflows",
        "Agile methodologies",
        "CI/CD implementation",
        "Cloud architecture"
    ]

    if composition.testers > 0:
        capabilities.append("Comprehensive testing")

    if composition.devops > 0:
        capabilities.append("Infrastructure automation")

    # Estimate velocity
    velocity_map = {
        WorkflowComplexity.SIMPLE: "20-30 story points/sprint",
        WorkflowComplexity.MODERATE: "40-60 story points/sprint",
        WorkflowComplexity.COMPLEX: "60-80 story points/sprint",
        WorkflowComplexity.ENTERPRISE: "80-120 story points/sprint"
    }

    return TeamResponse(
        team_id=team_id,
        members=members,
        capabilities=capabilities,
        estimated_velocity=velocity_map[request.complexity]
    )


@api.get(
    "/workflows/{workflow_id}/status",
    summary="Get workflow status",
    description="Retrieve the current status of a workflow",
    tags=["Workflows"]
)
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get the current status of a workflow."""
    return {
        "workflow_id": workflow_id,
        "status": "running",
        "progress": 45,
        "current_step": 3,
        "message": "Workflow is progressing normally"
    }


@api.get(
    "/capabilities",
    summary="List service capabilities",
    description="Returns all capabilities this workflow service provides",
    tags=["Service Info"]
)
async def list_capabilities() -> Dict[str, Any]:
    """List all capabilities of this service."""
    return {
        "service": "workflow-engine",
        "capabilities": [
            "Workflow creation and management",
            "Team assembly and composition",
            "Complexity-based planning",
            "Multi-type workflow support (testing, deployment, monitoring, development)"
        ],
        "workflow_types": [t.value for t in WorkflowType],
        "complexity_levels": [c.value for c in WorkflowComplexity],
        "utcp_enabled": True
    }


if __name__ == "__main__":
    print("🚀 Starting Workflow Engine Service with UTCP support...")
    print(f"📡 UTCP Manual available at: http://localhost:8001/utcp-manual.json")
    print(f"🔧 Tools endpoint: http://localhost:8001/utcp/tools")
    print(f"📚 API Docs: http://localhost:8001/docs")
    print()

    api.run()