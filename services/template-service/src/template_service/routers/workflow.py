"""
Workflow Router
API endpoints for workflow recommendations and approval
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..models.workflow import (
    Recommendation,
    RecommendationListResponse,
    RecommendationApprovalRequest,
    RecommendationRejectionRequest,
    RecommendationStatus,
    WorkflowRunSummary,
    WorkflowRunListResponse,
    Gap,
    ActionType,
    VariantDecision
)
from ..auth import get_current_active_user, require_admin, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

# Paths for workflow data
RECOMMENDATIONS_DIR = Path("/tmp/maestro_workflow_recommendations")
METRICS_DIR = Path("/tmp/maestro_workflow_metrics")
APPROVAL_TRACKING_FILE = Path("/tmp/maestro_workflow_approvals.json")


def load_approval_tracking() -> dict:
    """Load approval tracking data"""
    if APPROVAL_TRACKING_FILE.exists():
        try:
            return json.loads(APPROVAL_TRACKING_FILE.read_text())
        except Exception as e:
            logger.warning("failed_to_load_approvals", error=str(e))
            return {}
    return {}


def save_approval_tracking(data: dict):
    """Save approval tracking data"""
    try:
        APPROVAL_TRACKING_FILE.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.error("failed_to_save_approvals", error=str(e))
        raise


def load_all_recommendations() -> List[Recommendation]:
    """Load all recommendations from JSON files"""
    recommendations = []

    if not RECOMMENDATIONS_DIR.exists():
        logger.warning("recommendations_dir_not_found", path=str(RECOMMENDATIONS_DIR))
        return recommendations

    # Load approval tracking
    approval_data = load_approval_tracking()

    # Read all recommendation files
    for rec_file in sorted(RECOMMENDATIONS_DIR.glob("*_recommendations.json"), reverse=True):
        try:
            data = json.loads(rec_file.read_text())
            run_id = data.get("run_id", "UNKNOWN")

            for rec_dict in data.get("recommendations", []):
                rec_id = rec_dict.get("recommendation_id")

                # Build recommendation object
                rec = Recommendation(
                    recommendation_id=rec_id,
                    gap=Gap(**rec_dict["gap"]),
                    action_type=ActionType(rec_dict["action_type"]),
                    priority=rec_dict["priority"],
                    template_name=rec_dict["template_name"],
                    template_description=rec_dict["template_description"],
                    persona=rec_dict["persona"],
                    category=rec_dict["category"],
                    language=rec_dict["language"],
                    framework=rec_dict.get("framework"),
                    research_keywords=rec_dict.get("research_keywords", []),
                    confidence=rec_dict.get("confidence", 0.8),
                    variant_decision=VariantDecision(rec_dict["variant_decision"]) if rec_dict.get("variant_decision") else None,
                    base_template_id=rec_dict.get("base_template_id"),
                    base_template_name=rec_dict.get("base_template_name"),
                    similarity_score=rec_dict.get("similarity_score", 0.0),
                    quality_validated=rec_dict.get("quality_validated", False),
                    created_at=datetime.fromisoformat(rec_dict["created_at"]),
                    run_id=run_id,
                    status=RecommendationStatus.PENDING
                )

                # Apply approval tracking if exists
                if rec_id in approval_data:
                    approval_info = approval_data[rec_id]
                    rec.status = RecommendationStatus(approval_info.get("status", "pending"))
                    if approval_info.get("approved_at"):
                        rec.approved_at = datetime.fromisoformat(approval_info["approved_at"])
                    rec.approved_by = approval_info.get("approved_by")
                    if approval_info.get("rejected_at"):
                        rec.rejected_at = datetime.fromisoformat(approval_info["rejected_at"])
                    rec.rejected_by = approval_info.get("rejected_by")
                    rec.rejection_reason = approval_info.get("rejection_reason")

                recommendations.append(rec)

        except Exception as e:
            logger.error("failed_to_load_recommendation_file", file=str(rec_file), error=str(e))
            continue

    return recommendations


@router.get("/recommendations", response_model=RecommendationListResponse)
async def list_recommendations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[RecommendationStatus] = Query(None, description="Filter by status"),
    persona: Optional[str] = Query(None, description="Filter by persona"),
    priority: Optional[int] = Query(None, ge=1, le=10, description="Filter by priority"),
    variant_decision: Optional[VariantDecision] = Query(None, description="Filter by variant decision"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all workflow recommendations with filtering and pagination

    - **status**: Filter by approval status (pending, approved, rejected, etc.)
    - **persona**: Filter by target persona
    - **priority**: Filter by priority level
    - **variant_decision**: Filter by intelligence decision (REUSE, VARIANT, CREATE_NEW)
    - **run_id**: Filter by specific workflow run
    """
    try:
        # Load all recommendations
        all_recommendations = load_all_recommendations()

        # Apply filters
        filtered = all_recommendations

        if status:
            filtered = [r for r in filtered if r.status == status]

        if persona:
            filtered = [r for r in filtered if r.persona == persona]

        if priority:
            filtered = [r for r in filtered if r.priority == priority]

        if variant_decision:
            filtered = [r for r in filtered if r.variant_decision == variant_decision]

        if run_id:
            filtered = [r for r in filtered if r.run_id == run_id]

        # Calculate pagination
        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        return RecommendationListResponse(
            total=total,
            page=page,
            page_size=page_size,
            recommendations=paginated
        )

    except Exception as e:
        logger.error("list_recommendations_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list recommendations: {str(e)}"
        )


@router.get("/recommendations/{recommendation_id}", response_model=Recommendation)
async def get_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific recommendation by ID

    Returns detailed recommendation information including approval status
    """
    try:
        all_recommendations = load_all_recommendations()

        for rec in all_recommendations:
            if rec.recommendation_id == recommendation_id:
                return rec

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_recommendation_error", recommendation_id=recommendation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation: {str(e)}"
        )


@router.post("/recommendations/{recommendation_id}/approve", status_code=status.HTTP_200_OK)
async def approve_recommendation(
    recommendation_id: str,
    request: RecommendationApprovalRequest,
    admin_user: User = Depends(require_admin)
):
    """
    Approve a recommendation for implementation

    - **approved_by**: Username of person approving
    - **notes**: Optional approval notes

    Returns updated recommendation
    """
    try:
        # Check recommendation exists
        all_recommendations = load_all_recommendations()
        rec_exists = any(r.recommendation_id == recommendation_id for r in all_recommendations)

        if not rec_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found"
            )

        # Load approval tracking
        approval_data = load_approval_tracking()

        # Update approval status
        approval_data[recommendation_id] = {
            "status": "approved",
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": request.approved_by,
            "notes": request.notes
        }

        # Save approval tracking
        save_approval_tracking(approval_data)

        logger.info(
            "recommendation_approved",
            recommendation_id=recommendation_id,
            approved_by=request.approved_by
        )

        return {
            "status": "success",
            "message": f"Recommendation {recommendation_id} approved",
            "recommendation_id": recommendation_id,
            "approved_by": request.approved_by,
            "approved_at": approval_data[recommendation_id]["approved_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_recommendation_error", recommendation_id=recommendation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve recommendation: {str(e)}"
        )


@router.post("/recommendations/{recommendation_id}/reject", status_code=status.HTTP_200_OK)
async def reject_recommendation(
    recommendation_id: str,
    request: RecommendationRejectionRequest,
    admin_user: User = Depends(require_admin)
):
    """
    Reject a recommendation

    - **rejected_by**: Username of person rejecting
    - **reason**: Reason for rejection (required)

    Returns confirmation
    """
    try:
        # Check recommendation exists
        all_recommendations = load_all_recommendations()
        rec_exists = any(r.recommendation_id == recommendation_id for r in all_recommendations)

        if not rec_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found"
            )

        # Load approval tracking
        approval_data = load_approval_tracking()

        # Update rejection status
        approval_data[recommendation_id] = {
            "status": "rejected",
            "rejected_at": datetime.utcnow().isoformat(),
            "rejected_by": request.rejected_by,
            "rejection_reason": request.reason
        }

        # Save approval tracking
        save_approval_tracking(approval_data)

        logger.info(
            "recommendation_rejected",
            recommendation_id=recommendation_id,
            rejected_by=request.rejected_by,
            reason=request.reason
        )

        return {
            "status": "success",
            "message": f"Recommendation {recommendation_id} rejected",
            "recommendation_id": recommendation_id,
            "rejected_by": request.rejected_by,
            "rejected_at": approval_data[recommendation_id]["rejected_at"],
            "reason": request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_recommendation_error", recommendation_id=recommendation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject recommendation: {str(e)}"
        )


@router.get("/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of runs to return"),
    current_user: User = Depends(get_current_active_user)
):
    """
    List recent workflow runs

    Returns summary of recent workflow executions with metrics
    """
    try:
        runs = []

        if not METRICS_DIR.exists():
            return WorkflowRunListResponse(total=0, runs=[])

        # Read all metrics files
        for metrics_file in sorted(METRICS_DIR.glob("*_metrics.json"), reverse=True)[:limit]:
            try:
                data = json.loads(metrics_file.read_text())

                run = WorkflowRunSummary(
                    run_id=data["run_id"],
                    run_timestamp=datetime.fromisoformat(data["run_timestamp"]),
                    mode=data["mode"],
                    overall_coverage_before=data["overall_coverage_before"],
                    overall_coverage_after=data["overall_coverage_after"],
                    coverage_improvement=data["coverage_improvement"],
                    total_gaps_identified=data["total_gaps_identified"],
                    critical_gaps=data["critical_gaps"],
                    high_priority_gaps=data["high_priority_gaps"],
                    recommendations_generated=data["recommendations_generated"],
                    templates_auto_generated=data["templates_auto_generated"],
                    templates_synced=data["templates_synced"],
                    templates_reused=data["templates_reused"],
                    templates_variants_created=data["templates_variants_created"],
                    templates_new_created=data["templates_new_created"],
                    quality_gate_checks=data["quality_gate_checks"],
                    quality_gate_failures=data["quality_gate_failures"],
                    similarity_checks_performed=data["similarity_checks_performed"],
                    avg_template_similarity=data["avg_template_similarity"],
                    execution_time_seconds=data["execution_time_seconds"],
                    success=data["success"],
                    errors=data.get("errors", [])
                )

                runs.append(run)

            except Exception as e:
                logger.error("failed_to_load_metrics_file", file=str(metrics_file), error=str(e))
                continue

        return WorkflowRunListResponse(
            total=len(runs),
            runs=runs
        )

    except Exception as e:
        logger.error("list_workflow_runs_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflow runs: {str(e)}"
        )


@router.get("/runs/{run_id}", response_model=WorkflowRunSummary)
async def get_workflow_run(
    run_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific workflow run details

    Returns detailed metrics for a specific workflow execution
    """
    try:
        if not METRICS_DIR.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metrics directory not found"
            )

        # Find metrics file for this run
        for metrics_file in METRICS_DIR.glob(f"{run_id}_metrics.json"):
            data = json.loads(metrics_file.read_text())

            return WorkflowRunSummary(
                run_id=data["run_id"],
                run_timestamp=datetime.fromisoformat(data["run_timestamp"]),
                mode=data["mode"],
                overall_coverage_before=data["overall_coverage_before"],
                overall_coverage_after=data["overall_coverage_after"],
                coverage_improvement=data["coverage_improvement"],
                total_gaps_identified=data["total_gaps_identified"],
                critical_gaps=data["critical_gaps"],
                high_priority_gaps=data["high_priority_gaps"],
                recommendations_generated=data["recommendations_generated"],
                templates_auto_generated=data["templates_auto_generated"],
                templates_synced=data["templates_synced"],
                templates_reused=data["templates_reused"],
                templates_variants_created=data["templates_variants_created"],
                templates_new_created=data["templates_new_created"],
                quality_gate_checks=data["quality_gate_checks"],
                quality_gate_failures=data["quality_gate_failures"],
                similarity_checks_performed=data["similarity_checks_performed"],
                avg_template_similarity=data["avg_template_similarity"],
                execution_time_seconds=data["execution_time_seconds"],
                success=data["success"],
                errors=data.get("errors", [])
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run {run_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_workflow_run_error", run_id=run_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow run: {str(e)}"
        )


@router.get("/stats")
async def get_workflow_stats(current_user: User = Depends(get_current_active_user)):
    """
    Get overall workflow statistics

    Returns aggregated statistics across all recommendations and runs
    """
    try:
        all_recommendations = load_all_recommendations()

        # Count by status
        status_counts = {}
        for rec_status in RecommendationStatus:
            status_counts[rec_status.value] = sum(1 for r in all_recommendations if r.status == rec_status)

        # Count by variant decision
        variant_counts = {
            "REUSE": sum(1 for r in all_recommendations if r.variant_decision == VariantDecision.REUSE),
            "VARIANT": sum(1 for r in all_recommendations if r.variant_decision == VariantDecision.VARIANT),
            "CREATE_NEW": sum(1 for r in all_recommendations if r.variant_decision == VariantDecision.CREATE_NEW),
        }

        # Count by persona
        persona_counts = {}
        for rec in all_recommendations:
            persona_counts[rec.persona] = persona_counts.get(rec.persona, 0) + 1

        # Average similarity score
        avg_similarity = sum(r.similarity_score for r in all_recommendations) / len(all_recommendations) if all_recommendations else 0.0

        return {
            "total_recommendations": len(all_recommendations),
            "by_status": status_counts,
            "by_variant_decision": variant_counts,
            "by_persona": persona_counts,
            "average_similarity_score": round(avg_similarity, 3),
            "pending_approval": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0)
        }

    except Exception as e:
        logger.error("get_workflow_stats_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow stats: {str(e)}"
        )
