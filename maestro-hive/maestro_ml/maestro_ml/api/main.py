#!/usr/bin/env python3
"""
Maestro ML Platform - FastAPI Application

REST API for the ML development platform with meta-learning capabilities.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from maestro_ml.config.settings import get_settings
from maestro_ml.core.database import get_db, init_db
from maestro_ml.models.database import (
    ProjectCreate, ProjectResponse, ProjectSuccessUpdate,
    ArtifactCreate, ArtifactResponse, ArtifactSearch,
    ArtifactUsageCreate, ArtifactUsageResponse,
    MetricCreate, PredictionResponse
)
from maestro_ml.services.artifact_registry import ArtifactRegistry
from maestro_ml.services.metrics_collector import MetricsCollector
from maestro_ml.services.git_integration import GitIntegration, GitHubIntegration
from maestro_ml.services.cicd_integration import GitHubActionsIntegration, PipelineAnalyzer

# Import authentication router and dependencies
from maestro_ml.api.auth import router as auth_router, get_current_user_dependency, get_current_admin_user

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Self-aware ML development platform with meta-learning and team optimization"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# Services
artifact_registry = ArtifactRegistry()
metrics_collector = MetricsCollector()
git_integration = GitIntegration()
pipeline_analyzer = PipelineAnalyzer()


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()


@app.get("/")
async def root():
    """Health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


# ============================================================================
# Project Endpoints
# ============================================================================

@app.post("/api/v1/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Create a new ML project (requires authentication)"""
    from maestro_ml.models.database import Project, User
    from sqlalchemy import select
    import uuid
    
    # Get user's tenant_id from database
    user_id = uuid.UUID(current_user["user_id"])
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Create project with user's tenant_id
    new_project = Project(
        name=project.name,
        problem_class=project.problem_class,
        complexity_score=project.complexity_score,
        team_size=project.team_size,
        tenant_id=user.tenant_id,  # Use user's tenant
        meta=project.metadata
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return new_project


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID (requires authentication)"""
    from maestro_ml.models.database import Project
    from sqlalchemy import select

    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    stmt = select(Project).where(Project.id == project_uuid)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@app.patch("/api/v1/projects/{project_id}/success", response_model=ProjectResponse)
async def update_project_success(
    project_id: str,
    success_data: ProjectSuccessUpdate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Update project with success metrics (requires authentication)"""
    from maestro_ml.models.database import Project
    from sqlalchemy import select

    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    stmt = select(Project).where(Project.id == project_uuid)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields
    if success_data.model_accuracy is not None:
        project.model_performance = success_data.model_accuracy
    if success_data.business_impact_usd is not None:
        project.business_impact = success_data.business_impact_usd
    if success_data.deployment_days is not None:
        # Store deployment days in metadata for now
        from datetime import timedelta
        if project.start_date:
            project.completion_date = project.start_date + timedelta(days=success_data.deployment_days)
    if success_data.compute_cost is not None:
        project.compute_cost = success_data.compute_cost

    await db.commit()
    await db.refresh(project)

    return project


# ============================================================================
# Artifact Endpoints (Music Library)
# ============================================================================

@app.post("/api/v1/artifacts", response_model=ArtifactResponse)
async def create_artifact(
    artifact: ArtifactCreate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Register a new artifact in the library (requires authentication)"""
    new_artifact = await artifact_registry.create_artifact(db, artifact)
    return new_artifact


@app.post("/api/v1/artifacts/search", response_model=List[ArtifactResponse])
async def search_artifacts(
    search: ArtifactSearch,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Search artifacts by query, type, tags, or impact score (requires authentication)"""
    artifacts = await artifact_registry.search_artifacts(
        db,
        query=search.query,
        artifact_type=search.type,
        tags=search.tags,
        min_impact_score=search.min_impact_score
    )
    return artifacts


@app.post("/api/v1/artifacts/{artifact_id}/use", response_model=ArtifactUsageResponse)
async def log_artifact_usage(
    artifact_id: str,
    usage_data: ArtifactUsageCreate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Log artifact usage in a project"""
    usage = await artifact_registry.log_usage(
        db,
        artifact_id,
        usage_data.project_id,
        usage_data.impact_score,
        usage_data.context
    )
    return usage


@app.get("/api/v1/artifacts/top")
async def get_top_artifacts(
    artifact_type: Optional[str] = None,
    limit: int = Query(10, le=50),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get top artifacts by impact score (requires authentication)"""
    artifacts = await artifact_registry.get_top_artifacts(db, artifact_type, limit)
    return artifacts


@app.get("/api/v1/artifacts/{artifact_id}/analytics")
async def get_artifact_analytics(
    artifact_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics for a specific artifact (requires authentication)"""
    analytics = await artifact_registry.get_artifact_analytics(db, artifact_id)
    return analytics


# ============================================================================
# Metrics Endpoints
# ============================================================================

@app.post("/api/v1/metrics")
async def create_metric(
    metric: MetricCreate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Save a process metric (requires authentication)"""
    saved_metric = await metrics_collector.save_metric(
        db,
        metric.project_id,
        metric.metric_type,
        metric.metric_value,
        metric.metadata
    )
    return {"status": "saved", "metric_id": str(saved_metric.id)}


@app.get("/api/v1/metrics/{project_id}/summary")
async def get_metrics_summary(
    project_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get metrics summary for a project (requires authentication)"""
    summary = await metrics_collector.get_project_metrics_summary(db, project_id)
    return summary


@app.get("/api/v1/metrics/{project_id}/velocity")
async def get_development_velocity(
    project_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Calculate development velocity score (requires authentication)"""
    velocity = await metrics_collector.calculate_development_velocity(db, project_id)
    return {"project_id": project_id, "velocity_score": velocity}


# ============================================================================
# Recommendations Endpoint (Phase 3 - Placeholder)
# ============================================================================

@app.post("/api/v1/recommendations")
async def get_recommendations(
    problem_class: str,
    complexity_score: int,
    team_size: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendations for team composition and artifact usage (requires authentication)

    Phase 3 feature - currently returns placeholder data
    """
    # This will be replaced with meta-model inference in Phase 3
    return {
        "recommendation": "1-person team with 3 artifacts from library",
        "predicted_success_score": 85.0,
        "predicted_duration_days": 21,
        "predicted_cost": 1500.0,
        "confidence": 0.75,
        "suggested_artifacts": [],
        "team_composition": {
            "size": team_size,
            "roles": ["ml_scientist", "data_engineer"] if team_size >= 2 else ["ml_scientist"]
        }
    }


# ============================================================================
# Team Collaboration Endpoints (Phase 2)
# ============================================================================

@app.get("/api/v1/teams/{project_id}/git-metrics")
async def get_git_metrics(
    project_id: str,
    since_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Get Git metrics for a project's team (requires authentication)

    Collects:
    - Commit frequency
    - Contributor activity
    - Code churn
    - Collaboration patterns
    """
    metrics = await git_integration.collect_metrics(since_days=since_days)
    authors = await git_integration.get_commit_authors(since_days=since_days)
    patterns = await git_integration.detect_collaboration_patterns(since_days=since_days)

    return {
        "project_id": project_id,
        "period_days": since_days,
        "metrics": {
            "commits_per_week": metrics.commits_per_week,
            "unique_contributors": metrics.unique_contributors,
            "code_churn_rate": metrics.code_churn_rate,
            "collaboration_score": metrics.collaboration_score,
            "active_branches": metrics.active_branches
        },
        "contributors": authors,
        "collaboration_patterns": patterns,
        "collected_at": metrics.metadata.get("collection_date")
    }


@app.get("/api/v1/teams/{project_id}/cicd-metrics")
async def get_cicd_metrics(
    project_id: str,
    since_days: int = Query(7, ge=1, le=90),
    ci_provider: str = Query("github_actions", regex="^(github_actions|jenkins|gitlab_ci|circleci)$"),
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Get CI/CD pipeline metrics for a project (requires authentication)

    Supports: GitHub Actions, Jenkins, GitLab CI, CircleCI

    Metrics include:
    - Pipeline success rate
    - Average duration
    - Deployment frequency
    - Failure patterns
    """
    # Create appropriate CI/CD integration based on provider
    # For demo, using GitHub Actions
    if ci_provider == "github_actions":
        cicd = GitHubActionsIntegration(token="", repo="")
        metrics = await cicd.collect_metrics(since_days=since_days)
        runs = await cicd.get_pipeline_runs(since_days=since_days)

        failure_patterns = pipeline_analyzer.identify_failure_patterns(runs)
        lead_time = pipeline_analyzer.calculate_lead_time(runs)

        return {
            "project_id": project_id,
            "period_days": since_days,
            "ci_provider": ci_provider,
            "metrics": {
                "pipeline_success_rate": metrics.pipeline_success_rate,
                "avg_pipeline_duration_minutes": metrics.avg_pipeline_duration_minutes,
                "total_pipeline_runs": metrics.total_pipeline_runs,
                "failed_runs": metrics.failed_runs,
                "deployment_frequency_per_week": metrics.deployment_frequency_per_week,
                "lead_time_hours": lead_time
            },
            "failure_analysis": failure_patterns,
            "source": metrics.metadata
        }

    return {"error": "CI provider not yet implemented"}


@app.get("/api/v1/teams/{project_id}/collaboration-analytics")
async def get_collaboration_analytics(
    project_id: str,
    since_days: int = Query(30, ge=7, le=180),
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Get comprehensive team collaboration analytics (requires authentication)

    Combines:
    - Git metrics
    - Development velocity
    - Team patterns
    - Productivity insights
    """
    git_metrics = await git_integration.collect_metrics(since_days=since_days)
    patterns = await git_integration.detect_collaboration_patterns(since_days=since_days)

    # Calculate team efficiency score
    velocity_response = await get_development_velocity(project_id, db=None)  # Need to fix this

    return {
        "project_id": project_id,
        "period_days": since_days,
        "team_analytics": {
            "team_size": git_metrics.unique_contributors,
            "collaboration_score": git_metrics.collaboration_score,
            "productivity": {
                "commits_per_week": git_metrics.commits_per_week,
                "code_churn_rate": git_metrics.code_churn_rate,
                "active_branches": git_metrics.active_branches
            },
            "patterns": patterns,
            "recommendations": _generate_team_recommendations(git_metrics, patterns)
        }
    }


def _generate_team_recommendations(
    git_metrics,
    patterns: dict
) -> List[str]:
    """Generate actionable recommendations for the team"""
    recommendations = []

    if git_metrics.unique_contributors == 1:
        recommendations.append("Consider adding team members or code reviewers to improve code quality")

    if git_metrics.collaboration_score < 40:
        recommendations.append("Low collaboration score - consider pair programming or code review practices")

    if git_metrics.code_churn_rate > 75:
        recommendations.append("High code churn detected - may indicate unclear requirements or refactoring needs")

    if git_metrics.commits_per_week < 5:
        recommendations.append("Low commit frequency - consider smaller, more frequent commits")

    if patterns.get("high_collaboration"):
        recommendations.append("Great collaboration! Team is working well together")

    return recommendations if recommendations else ["Team metrics look healthy - keep up the good work!"]


@app.post("/api/v1/teams/{project_id}/members")
async def add_team_member(
    project_id: str,
    member_data: dict,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a team member to a project (requires authentication)

    Tracks:
    - Role (data_engineer, ml_scientist, devops, etc.)
    - Experience level
    - Contribution hours
    """
    from maestro_ml.models.database import TeamMember
    import uuid as uuid_lib

    project_uuid = uuid_lib.UUID(project_id) if isinstance(project_id, str) else project_id

    member = TeamMember(
        project_id=project_uuid,
        role=member_data.get("role"),
        experience_level=member_data.get("experience_level", "mid"),
        contribution_hours=member_data.get("contribution_hours", 0.0),
        performance_score=member_data.get("performance_score")
    )

    db.add(member)
    await db.commit()
    await db.refresh(member)

    return {
        "id": str(member.id),
        "project_id": str(member.project_id),
        "role": member.role,
        "experience_level": member.experience_level
    }


@app.get("/api/v1/teams/{project_id}/members")
async def get_team_members(
    project_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get all team members for a project (requires authentication)"""
    from maestro_ml.models.database import TeamMember
    from sqlalchemy import select
    import uuid as uuid_lib

    project_uuid = uuid_lib.UUID(project_id) if isinstance(project_id, str) else project_id

    stmt = select(TeamMember).where(TeamMember.project_id == project_uuid)
    result = await db.execute(stmt)
    members = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "experience_level": m.experience_level,
            "contribution_hours": m.contribution_hours,
            "performance_score": m.performance_score
        }
        for m in members
    ]


# ============================================================================
# ML Phase 3: Spec Similarity & Reuse Recommendations
# ============================================================================

from maestro_ml.services.spec_similarity import SpecSimilarityService
from maestro_ml.services.persona_artifact_matcher import PersonaArtifactMatcher

# Initialize spec similarity service
spec_similarity_service = SpecSimilarityService()
persona_matcher = PersonaArtifactMatcher()


@app.post("/api/v1/ml/embed-specs")
async def embed_specs(
    specs: dict,
    project_id: str,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Embed requirement specs into semantic vector (requires authentication)

    Phase 3 feature for intelligent project similarity detection.
    """
    try:
        embedding = spec_similarity_service.embed_specs(specs, project_id)

        return {
            "project_id": embedding.project_id,
            "embedding_dims": len(embedding.embedding),
            "metadata": embedding.metadata,
            "created_at": embedding.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.post("/api/v1/ml/find-similar-projects")
async def find_similar_projects(
    specs: dict,
    min_similarity: float = Query(0.80, ge=0.0, le=1.0),
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Find projects with similar requirement specs (requires authentication)

    Phase 3 feature - uses vector similarity search.

    Returns:
        List of similar projects with similarity scores
    """
    try:
        similar_projects = spec_similarity_service.find_similar_projects(
            specs=specs,
            min_similarity=min_similarity,
            limit=limit
        )

        return [
            {
                "project_id": proj.project_id,
                "similarity_score": proj.similarity_score,
                "specs": proj.specs,
                "metadata": proj.metadata
            }
            for proj in similar_projects
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


@app.post("/api/v1/ml/analyze-overlap")
async def analyze_overlap(
    new_specs: dict,
    existing_specs: dict,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Detailed feature-by-feature overlap analysis (requires authentication)

    Phase 3 feature - compares specs in detail.

    Returns:
        Overlap percentages, matched/new/modified features
    """
    try:
        overlap_analysis = spec_similarity_service.analyze_overlap(
            new_specs=new_specs,
            existing_specs=existing_specs
        )

        return {
            "overall_overlap": overlap_analysis.overall_overlap,
            "user_stories_overlap": overlap_analysis.user_stories_overlap,
            "functional_requirements_overlap": overlap_analysis.functional_requirements_overlap,
            "data_models_overlap": overlap_analysis.data_models_overlap,
            "api_endpoints_overlap": overlap_analysis.api_endpoints_overlap,
            "matched_user_stories_count": len(overlap_analysis.matched_user_stories),
            "new_user_stories_count": len(overlap_analysis.new_user_stories),
            "modified_user_stories_count": len(overlap_analysis.modified_user_stories),
            "matched_requirements_count": len(overlap_analysis.matched_requirements),
            "new_requirements_count": len(overlap_analysis.new_requirements),
            "matched_models_count": len(overlap_analysis.matched_models),
            "new_models_count": len(overlap_analysis.new_models),
            "modified_models_count": len(overlap_analysis.modified_models),
            "matched_endpoints_count": len(overlap_analysis.matched_endpoints),
            "new_endpoints_count": len(overlap_analysis.new_endpoints),
            "delta_features": overlap_analysis.delta_features,
            "unchanged_features": overlap_analysis.unchanged_features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overlap analysis failed: {str(e)}")


@app.post("/api/v1/ml/estimate-effort")
async def estimate_effort(
    overlap_analysis: dict,
    new_specs: dict,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Estimate development effort for delta work (requires authentication)

    Phase 3 feature - predicts hours needed.

    Returns:
        Effort estimate in hours with breakdown
    """
    try:
        # Reconstruct overlap analysis object (simplified for demo)
        from maestro_ml.services.spec_similarity import OverlapAnalysis

        overlap_obj = OverlapAnalysis(
            overall_overlap=overlap_analysis.get("overall_overlap", 0.0),
            user_stories_overlap=overlap_analysis.get("user_stories_overlap", 0.0),
            functional_requirements_overlap=overlap_analysis.get("functional_requirements_overlap", 0.0),
            data_models_overlap=overlap_analysis.get("data_models_overlap", 0.0),
            api_endpoints_overlap=overlap_analysis.get("api_endpoints_overlap", 0.0),
            matched_user_stories=[],
            new_user_stories=overlap_analysis.get("delta_features", []),
            modified_user_stories=[],
            matched_requirements=[],
            new_requirements=[],
            matched_models=[],
            new_models=[],
            modified_models=[],
            matched_endpoints=[],
            new_endpoints=[],
            delta_features=overlap_analysis.get("delta_features", []),
            unchanged_features=overlap_analysis.get("unchanged_features", [])
        )

        effort_estimate = spec_similarity_service.estimate_effort(
            overlap_analysis=overlap_obj,
            new_specs=new_specs
        )

        return {
            "total_hours": effort_estimate.total_hours,
            "new_feature_hours": effort_estimate.new_feature_hours,
            "modification_hours": effort_estimate.modification_hours,
            "integration_hours": effort_estimate.integration_hours,
            "confidence": effort_estimate.confidence,
            "breakdown": effort_estimate.breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Effort estimation failed: {str(e)}")


@app.post("/api/v1/ml/recommend-reuse-strategy")
async def recommend_reuse_strategy(
    overlap_analysis: dict,
    similar_project: dict,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Get intelligent reuse strategy recommendation (requires authentication)

    Phase 3 feature - recommends clone/hybrid/full SDLC.

    Returns:
        Strategy, personas to run/skip, effort estimates
    """
    try:
        # Reconstruct objects (simplified for demo)
        from maestro_ml.services.spec_similarity import (
            OverlapAnalysis, SimilarProject, EffortEstimate
        )

        overlap_obj = OverlapAnalysis(
            overall_overlap=overlap_analysis.get("overall_overlap", 0.0),
            user_stories_overlap=overlap_analysis.get("user_stories_overlap", 0.0),
            functional_requirements_overlap=overlap_analysis.get("functional_requirements_overlap", 0.0),
            data_models_overlap=overlap_analysis.get("data_models_overlap", 0.0),
            api_endpoints_overlap=overlap_analysis.get("api_endpoints_overlap", 0.0),
            matched_user_stories=[],
            new_user_stories=overlap_analysis.get("delta_features", []),
            modified_user_stories=[],
            matched_requirements=[],
            new_requirements=[],
            matched_models=[],
            new_models=[],
            modified_models=[],
            matched_endpoints=[],
            new_endpoints=[],
            delta_features=overlap_analysis.get("delta_features", []),
            unchanged_features=overlap_analysis.get("unchanged_features", [])
        )

        similar_proj = SimilarProject(
            project_id=similar_project.get("project_id", ""),
            similarity_score=similar_project.get("similarity_score", 0.0),
            specs=similar_project.get("specs", {}),
            metadata=similar_project.get("metadata", {})
        )

        # Create effort estimate
        effort_est = spec_similarity_service.estimate_effort(overlap_obj, {})

        recommendation = spec_similarity_service.recommend_reuse_strategy(
            overlap_analysis=overlap_obj,
            effort_estimate=effort_est,
            similar_project=similar_proj
        )

        return {
            "strategy": recommendation.strategy,
            "base_project_id": recommendation.base_project_id,
            "similarity_score": recommendation.similarity_score,
            "overlap_percentage": recommendation.overlap_percentage,
            "personas_to_run": recommendation.personas_to_run,
            "personas_to_skip": recommendation.personas_to_skip,
            "estimated_effort_hours": recommendation.estimated_effort_hours,
            "estimated_effort_percentage": recommendation.estimated_effort_percentage,
            "confidence": recommendation.confidence,
            "clone_instructions": recommendation.clone_instructions,
            "reasoning": recommendation.reasoning
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


# ============================================================================
# ML Phase 3.1: Persona-Level Granular Artifact Matching
# ============================================================================

@app.post("/api/v1/ml/persona/extract-specs")
async def extract_persona_specs(
    persona_id: str,
    requirements_md: str,
    additional_artifacts: Optional[dict] = None,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Extract specs for a specific persona's domain (requires authentication)

    Phase 3.1 feature - persona-level spec extraction.

    Args:
        persona_id: Persona to extract for (e.g., "system_architect", "frontend_engineer")
        requirements_md: REQUIREMENTS.md content
        additional_artifacts: Optional additional documents

    Returns:
        PersonaDomainSpec with extracted specs for this persona
    """
    try:
        persona_specs = persona_matcher.extract_persona_specs(
            persona_id=persona_id,
            requirements_md=requirements_md,
            additional_artifacts=additional_artifacts
        )

        return {
            "persona_id": persona_specs.persona_id,
            "domain": persona_specs.domain,
            "specs": persona_specs.specs,
            "extracted_from": persona_specs.extracted_from,
            "confidence": persona_specs.confidence
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spec extraction failed: {str(e)}")


@app.post("/api/v1/ml/persona/match-artifacts")
async def match_persona_artifacts(
    persona_id: str,
    new_persona_specs: dict,
    existing_persona_specs: dict,
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Match artifacts for a specific persona between new and existing projects (requires authentication)

    Phase 3.1 feature - granular persona-level matching.

    Returns whether this specific persona's artifacts can be reused,
    even if overall project similarity is low.

    Example:
        Overall project: 50% similar
        BUT system_architect: 95% similar → reuse architecture
        AND frontend_engineer: 88% similar → reuse frontend
        Result: Skip 2 personas, run 8 = 20% savings

    Returns:
        PersonaMatchResult with similarity and reuse decision
    """
    try:
        from maestro_ml.services.persona_artifact_matcher import PersonaDomainSpec

        # Reconstruct PersonaDomainSpec objects
        new_spec = PersonaDomainSpec(
            persona_id=persona_id,
            domain=new_persona_specs.get("domain", ""),
            specs=new_persona_specs.get("specs", {}),
            extracted_from=new_persona_specs.get("extracted_from", ""),
            confidence=new_persona_specs.get("confidence", 0.0)
        )

        existing_spec = PersonaDomainSpec(
            persona_id=persona_id,
            domain=existing_persona_specs.get("domain", ""),
            specs=existing_persona_specs.get("specs", {}),
            extracted_from=existing_persona_specs.get("extracted_from", ""),
            confidence=existing_persona_specs.get("confidence", 0.0)
        )

        match_result = persona_matcher.match_persona_artifacts(
            new_persona_specs=new_spec,
            existing_persona_specs=existing_spec
        )

        return {
            "persona_id": match_result.persona_id,
            "similarity_score": match_result.similarity_score,
            "should_reuse": match_result.should_reuse,
            "source_project_id": match_result.source_project_id,
            "source_artifacts": match_result.source_artifacts,
            "match_details": match_result.match_details,
            "rationale": match_result.rationale
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona matching failed: {str(e)}")


@app.post("/api/v1/ml/persona/build-reuse-map")
async def build_persona_reuse_map(
    new_project_requirements: str,
    existing_project_requirements: str,
    persona_ids: List[str],
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Build complete persona-level reuse map (requires authentication)

    Phase 3.1 feature - analyzes each persona independently
    and builds a granular reuse decision map.

    Generic approach - not hardcoded:
    - Each persona analyzed based on their domain (architecture, frontend, backend, etc.)
    - Independent similarity scores per persona
    - Selective reuse decisions per persona

    Example output:
        Overall project: 52% similar (would normally run full SDLC in V4)

        BUT persona-level analysis:
        - system_architect: 100% match → REUSE (skip)
        - frontend_engineer: 90% match → REUSE (skip)
        - backend_engineer: 35% match → EXECUTE (build fresh)
        - database_engineer: 28% match → EXECUTE (build fresh)
        - security_engineer: 95% match → REUSE (skip)
        - ...

        Result: Fast-track 3 personas, execute 7 = 30% time savings

    Returns:
        PersonaReuseMap with per-persona decisions
    """
    try:
        reuse_map = persona_matcher.build_persona_reuse_map(
            new_project_requirements=new_project_requirements,
            existing_project_requirements=existing_project_requirements,
            persona_ids=persona_ids
        )

        return {
            "overall_similarity": reuse_map.overall_similarity,
            "persona_matches": {
                persona_id: {
                    "similarity_score": match.similarity_score,
                    "should_reuse": match.should_reuse,
                    "source_project_id": match.source_project_id,
                    "rationale": match.rationale,
                    "match_details": match.match_details
                }
                for persona_id, match in reuse_map.persona_matches.items()
            },
            "personas_to_reuse": reuse_map.personas_to_reuse,
            "personas_to_execute": reuse_map.personas_to_execute,
            "estimated_time_savings_percent": reuse_map.estimated_time_savings_percent,
            "summary": {
                "total_personas": len(persona_ids),
                "reuse_count": len(reuse_map.personas_to_reuse),
                "execute_count": len(reuse_map.personas_to_execute),
                "time_savings": f"{reuse_map.estimated_time_savings_percent:.1f}%"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reuse map building failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "maestro_ml.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
