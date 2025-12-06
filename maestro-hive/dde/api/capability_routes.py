"""
Capability Registry API Endpoints

JIRA: MD-2066 (part of MD-2042)
Description: REST API endpoints for capability registry management.

Endpoints:
- POST   /api/capabilities/agents           - Register new agent
- GET    /api/capabilities/agents           - List all agents
- GET    /api/capabilities/agents/{id}      - Get agent by ID
- PUT    /api/capabilities/agents/{id}      - Update agent
- DELETE /api/capabilities/agents/{id}      - Unregister agent
- POST   /api/capabilities/agents/{id}/capabilities      - Add capability
- PUT    /api/capabilities/agents/{id}/capabilities/{skill_id}  - Update capability
- DELETE /api/capabilities/agents/{id}/capabilities/{skill_id}  - Remove capability
- GET    /api/capabilities                  - List all capabilities
- POST   /api/capabilities/discover         - Find capable agents
- GET    /api/capabilities/health           - Health check
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Local imports
from ..capability_registry import (
    CapabilityRegistry,
    AgentProfile,
    AgentCapability,
    AgentFilters,
    create_registry
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])

# Global registry instance (initialized on startup)
_registry: Optional[CapabilityRegistry] = None


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class RegisterAgentRequest(BaseModel):
    """Request body for registering a new agent."""
    agent_id: Optional[str] = None  # Auto-generated if not provided
    name: str = Field(..., min_length=1, max_length=255)
    persona_type: str = Field(..., min_length=1, max_length=100)
    capabilities: Dict[str, int] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Backend Developer 1",
                "persona_type": "backend_developer",
                "capabilities": {
                    "Backend:Python:FastAPI": 5,
                    "Backend:Python:SQLAlchemy": 4,
                    "Testing:Unit": 4
                }
            }
        }


class UpdateAgentRequest(BaseModel):
    """Request body for updating an agent."""
    name: Optional[str] = None
    availability_status: Optional[str] = Field(None, pattern="^(available|busy|offline)$")
    current_wip: Optional[int] = Field(None, ge=0)
    wip_limit: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class AddCapabilityRequest(BaseModel):
    """Request body for adding a capability."""
    skill_id: str = Field(..., min_length=1)
    proficiency: int = Field(..., ge=1, le=5)
    source: str = Field(default="manual", pattern="^(manual|inferred|historical|assessment)$")


class UpdateCapabilityRequest(BaseModel):
    """Request body for updating a capability."""
    proficiency: int = Field(..., ge=1, le=5)


class DiscoverRequest(BaseModel):
    """Request body for discovering capable agents."""
    required_skills: List[str] = Field(..., min_items=1)
    min_proficiency: int = Field(default=1, ge=1, le=5)
    availability_required: bool = False
    include_parent_matches: bool = True
    limit: int = Field(default=10, ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "required_skills": ["Backend:Python:FastAPI", "Testing:Integration"],
                "min_proficiency": 3,
                "availability_required": True,
                "limit": 5
            }
        }


class AgentResponse(BaseModel):
    """Response model for agent data."""
    agent_id: str
    name: str
    persona_type: str
    availability_status: str
    wip_limit: int
    current_wip: int
    capabilities: List[Dict[str, Any]]
    quality_history: List[float]
    metadata: Dict[str, Any]
    last_active: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class AgentListResponse(BaseModel):
    """Response model for listing agents."""
    agents: List[AgentResponse]
    total: int
    limit: int
    offset: int


class DiscoverResponse(BaseModel):
    """Response model for agent discovery."""
    agents: List[AgentResponse]
    match_scores: Dict[str, float]
    total_found: int


class CapabilityResponse(BaseModel):
    """Response model for capability data."""
    skill_id: str
    category: str
    version: str
    deprecated: bool
    description: Optional[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    agents_registered: int
    capabilities_defined: int
    cache_size: int
    timestamp: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_registry() -> CapabilityRegistry:
    """Get the capability registry instance."""
    global _registry
    if _registry is None:
        # Initialize with default settings
        _registry = create_registry(
            database_url=None,  # Will use in-memory mode
            taxonomy_path="config/capability_taxonomy.yaml"
        )
    return _registry


def init_registry(database_url: Optional[str] = None, taxonomy_path: str = "config/capability_taxonomy.yaml"):
    """Initialize the registry with custom settings."""
    global _registry
    _registry = create_registry(database_url=database_url, taxonomy_path=taxonomy_path)
    return _registry


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.post("/agents", response_model=AgentResponse, status_code=201)
async def register_agent(
    request: RegisterAgentRequest,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Register a new agent with capabilities.

    Creates a new agent profile with the specified capabilities.
    If agent_id is not provided, one will be auto-generated.
    """
    try:
        # Generate agent_id if not provided
        agent_id = request.agent_id
        if not agent_id:
            from uuid import uuid4
            agent_id = f"agent-{uuid4().hex[:12]}"

        # Validate proficiency values
        for skill_id, proficiency in request.capabilities.items():
            if not 1 <= proficiency <= 5:
                raise HTTPException(
                    status_code=400,
                    detail=f"Proficiency for {skill_id} must be between 1 and 5"
                )

        agent = registry.register_agent(
            agent_id=agent_id,
            name=request.name,
            persona_type=request.persona_type,
            capabilities=request.capabilities,
            metadata=request.metadata
        )

        logger.info(f"Registered agent: {agent.agent_id}")
        return AgentResponse(**agent.to_dict())

    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    persona_type: Optional[str] = Query(None, description="Filter by persona type"),
    availability_status: Optional[str] = Query(None, pattern="^(available|busy|offline)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    List all registered agents.

    Supports filtering by persona_type and availability_status.
    Results are paginated with limit and offset.
    """
    try:
        filters = AgentFilters(
            persona_type=persona_type,
            availability_status=availability_status,
            limit=limit,
            offset=offset
        )

        agents = registry.list_agents(filters)

        return AgentListResponse(
            agents=[AgentResponse(**a.to_dict()) for a in agents],
            total=len(agents),
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Get an agent by ID.

    Returns the full agent profile including capabilities and quality history.
    """
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return AgentResponse(**agent.to_dict())


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Update an agent's profile.

    Can update name, availability_status, current_wip, wip_limit, and metadata.
    """
    # Check agent exists
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        # Update status if provided
        if request.availability_status or request.current_wip is not None:
            registry.update_agent_status(
                agent_id=agent_id,
                status=request.availability_status,
                wip=request.current_wip
            )

        # Refresh agent data
        agent = registry.get_agent(agent_id)
        return AgentResponse(**agent.to_dict())

    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Unregister an agent.

    Removes the agent and all associated capabilities from the registry.
    """
    success = registry.unregister_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    logger.info(f"Unregistered agent: {agent_id}")
    return {"success": True, "agent_id": agent_id, "deleted": True}


# ============================================================================
# Capability Endpoints
# ============================================================================

@router.post("/agents/{agent_id}/capabilities")
async def add_capability(
    agent_id: str,
    request: AddCapabilityRequest,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Add a capability to an agent.

    If the capability already exists, it will be updated.
    """
    # Check agent exists
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        success = registry.add_capability(
            agent_id=agent_id,
            skill_id=request.skill_id,
            proficiency=request.proficiency,
            source=request.source
        )

        if success:
            return {
                "success": True,
                "agent_id": agent_id,
                "skill_id": request.skill_id,
                "proficiency": request.proficiency
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add capability")

    except Exception as e:
        logger.error(f"Failed to add capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}/capabilities/{skill_id}")
async def update_capability(
    agent_id: str,
    skill_id: str,
    request: UpdateCapabilityRequest,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Update an agent's capability proficiency.
    """
    # Check agent exists
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Check capability exists
    has_cap = any(c.skill_id == skill_id for c in agent.capabilities)
    if not has_cap:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} does not have capability {skill_id}"
        )

    try:
        success = registry.update_capability(
            agent_id=agent_id,
            skill_id=skill_id,
            proficiency=request.proficiency
        )

        if success:
            return {
                "success": True,
                "agent_id": agent_id,
                "skill_id": skill_id,
                "proficiency": request.proficiency
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update capability")

    except Exception as e:
        logger.error(f"Failed to update capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}/capabilities/{skill_id}")
async def remove_capability(
    agent_id: str,
    skill_id: str,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Remove a capability from an agent.
    """
    # Check agent exists
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        success = registry.remove_capability(agent_id=agent_id, skill_id=skill_id)

        if success:
            return {
                "success": True,
                "agent_id": agent_id,
                "skill_id": skill_id,
                "removed": True
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Capability {skill_id} not found for agent {agent_id}"
            )

    except Exception as e:
        logger.error(f"Failed to remove capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Discovery Endpoints
# ============================================================================

@router.get("/")
async def list_capabilities(
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    List all capabilities from the taxonomy.

    Returns the capability coverage (how many agents have each capability).
    """
    try:
        coverage = registry.get_capability_coverage()

        # Get taxonomy categories
        taxonomy = registry.taxonomy
        categories = {}

        for skill_id, agent_count in coverage.items():
            category = skill_id.split(":")[0] if ":" in skill_id else skill_id
            if category not in categories:
                categories[category] = []
            categories[category].append({
                "skill_id": skill_id,
                "agent_count": agent_count
            })

        return {
            "capabilities": coverage,
            "categories": categories,
            "total_capabilities": len(coverage),
            "total_agents_with_capabilities": sum(1 for c in coverage.values() if c > 0)
        }

    except Exception as e:
        logger.error(f"Failed to list capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover", response_model=DiscoverResponse)
async def discover_agents(
    request: DiscoverRequest,
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Find agents with specific capabilities.

    Returns agents ranked by their match quality for the required skills.
    Supports hierarchical matching (parent skills can match child requirements).
    """
    try:
        agents = registry.find_capable_agents(
            required_skills=request.required_skills,
            min_proficiency=request.min_proficiency,
            availability_required=request.availability_required,
            include_parent_matches=request.include_parent_matches,
            limit=request.limit
        )

        # Calculate match scores
        match_scores = {}
        for agent in agents:
            # Simple score based on matching skills and proficiency
            matching_skills = [
                cap for cap in agent.capabilities
                if cap.skill_id in request.required_skills or
                any(cap.skill_id.startswith(skill) for skill in request.required_skills)
            ]
            if matching_skills:
                avg_prof = sum(c.proficiency for c in matching_skills) / len(matching_skills)
                match_scores[agent.agent_id] = round(avg_prof / 5.0, 3)

        return DiscoverResponse(
            agents=[AgentResponse(**a.to_dict()) for a in agents],
            match_scores=match_scores,
            total_found=len(agents)
        )

    except Exception as e:
        logger.error(f"Failed to discover agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health & Utility Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check(
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Check the health of the capability registry.

    Returns statistics about registered agents and capabilities.
    """
    try:
        agents = registry.list_agents()
        coverage = registry.get_capability_coverage()

        return HealthResponse(
            status="healthy",
            service="capability-registry",
            agents_registered=len(agents),
            capabilities_defined=len(coverage),
            cache_size=len(registry._agent_cache),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="capability-registry",
            agents_registered=0,
            capabilities_defined=0,
            cache_size=0,
            timestamp=datetime.now().isoformat()
        )


@router.post("/quality/{agent_id}")
async def record_quality(
    agent_id: str,
    task_id: str = Query(...),
    quality_score: float = Query(..., ge=0.0, le=1.0),
    execution_time_ms: Optional[int] = Query(None),
    skill_id: Optional[str] = Query(None),
    registry: CapabilityRegistry = Depends(get_registry)
):
    """
    Record a quality score for an agent execution.

    This endpoint is called after task completion to update the agent's quality history.
    """
    # Check agent exists
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        success = registry.record_quality_score(
            agent_id=agent_id,
            task_id=task_id,
            quality_score=quality_score,
            execution_time_ms=execution_time_ms,
            skill_id=skill_id
        )

        if success:
            return {
                "success": True,
                "agent_id": agent_id,
                "task_id": task_id,
                "quality_score": quality_score
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to record quality score")

    except Exception as e:
        logger.error(f"Failed to record quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# App Factory (for standalone testing)
# ============================================================================

def create_app(database_url: Optional[str] = None):
    """Create a FastAPI app with the capability registry routes."""
    from fastapi import FastAPI

    app = FastAPI(
        title="Capability Registry API",
        description="REST API for dynamic agent capability management",
        version="1.0.0"
    )

    # Initialize registry
    init_registry(database_url=database_url)

    # Include router
    app.include_router(router)

    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
